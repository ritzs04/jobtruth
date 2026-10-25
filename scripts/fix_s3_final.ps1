$AWS    = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
$REGION = "ap-south-1"
$IID    = "i-05570193524581588"

# Key insight: Docker restores the container BEFORE UserData runs.
# Fix: stop docker service first, then remove all containers, then start fresh.
$shellScript = @'
#!/bin/bash
exec >> /var/log/jobtruth-start.log 2>&1
echo "=== Startup $(date) ==="

# Step 1: stop docker so containers can't auto-restart
systemctl stop docker

# Step 2: wipe all container configs (removes restart policies)
rm -rf /var/lib/docker/containers/*

# Step 3: start docker fresh
systemctl start docker
sleep 5

# Step 4: launch with correct credentials
/usr/bin/docker run -d --name jobtruth --restart always -p 80:8000 \
  -e S3_BUCKET=jobtruth-cat2-offers \
  -e AWS_REGION=ap-south-1 \
  -e AWS_ACCESS_KEY_ID=$env:AWS_ACCESS_KEY_ID \
  -e "AWS_SECRET_ACCESS_KEY=$env:AWS_SECRET_ACCESS_KEY" \
  -e JWT_SECRET_KEY=jobtruth-dev-secret-2024 \
  -e HMAC_SECRET=jobtruth-hmac-secret-2024 \
  jobtruth

echo "=== Done $(date) ==="
'@

$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($shellScript))

Write-Host "[1] Stopping instance..."
& $AWS ec2 stop-instances --region $REGION --instance-ids $IID --output text | Out-Null
Write-Host "    Waiting..."
& $AWS ec2 wait instance-stopped --region $REGION --instance-ids $IID
Write-Host "    Stopped."

Write-Host "[2] Updating UserData (stop docker, wipe containers, fresh start)..."
& $AWS ec2 modify-instance-attribute --region $REGION --instance-id $IID --attribute userData --value $b64
Write-Host "    Done."

Write-Host "[3] Starting instance..."
& $AWS ec2 start-instances --region $REGION --instance-ids $IID --output text | Out-Null
& $AWS ec2 wait instance-running --region $REGION --instance-ids $IID
Write-Host "    Running."

$IP = & $AWS ec2 describe-instances --region $REGION --instance-ids $IID `
    --query "Reservations[0].Instances[0].PublicIpAddress" --output text
Write-Host "[4] IP: $IP"

Write-Host "[5] Waiting 120s..."
Start-Sleep -Seconds 120

Write-Host "[6] Testing health + S3..."
for ($i = 1; $i -le 15; $i++) {
    try {
        $h = Invoke-RestMethod "http://$IP/health" -TimeoutSec 8 -ErrorAction Stop
        Write-Host "    Health OK: served_by=$($h.served_by)"
        try {
            $s3r = Invoke-RestMethod "http://$IP/objects" -TimeoutSec 12 -ErrorAction Stop
            Write-Host "    S3 WORKING! Objects=$($s3r.Count)"
        } catch {
            $errBody = ""
            try { $errBody = $_.ErrorDetails.Message } catch {}
            Write-Host "    S3 FAIL: $errBody"
        }
        break
    } catch {
        $e1 = $_.Exception.Message
        Write-Host "    Attempt $i/15: $e1"
        Start-Sleep -Seconds 15
    }
}

"BUCKET=jobtruth-cat2-offers`nINSTANCE=$IID`nSG=sg-069404559e5c5c139`nIP=$IP" | `
    Out-File "d:\PROJECTS(CAT 2)\Cloud\jobtruth\scripts\deployed.txt" -Encoding utf8
Write-Host "URL: http://$IP"
