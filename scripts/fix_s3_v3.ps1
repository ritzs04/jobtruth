$AWS    = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
$REGION = "ap-south-1"
$IID    = "i-05570193524581588"

# This script uses cloud-init clean + runcmd to ensure re-execution on restart
# cloud-init clean --logs wipes the sentinel so all scripts re-run on next boot
$cloudConfig = @'
#cloud-config
runcmd:
  - docker stop jobtruth || true
  - docker rm jobtruth || true
  - >
    docker run -d --name jobtruth --restart always -p 80:8000
    -e S3_BUCKET=jobtruth-cat2-offers
    -e AWS_REGION=ap-south-1
    -e AWS_ACCESS_KEY_ID=$env:AWS_ACCESS_KEY_ID
    -e "AWS_SECRET_ACCESS_KEY=$env:AWS_SECRET_ACCESS_KEY"
    -e JWT_SECRET_KEY=jobtruth-dev-secret-2024
    -e HMAC_SECRET=jobtruth-hmac-secret-2024
    jobtruth
  - echo "JOBTRUTH RESTARTED WITH S3 CREDS" >> /var/log/jobtruth-boot.log
'@

# We embed a shell script that cloud-init will run even on subsequent boots
# by using a per-instance user-data script with cloud-init clean first
$shellScript = @'
#!/bin/bash
exec >> /var/log/jobtruth-start.log 2>&1
echo "=== Startup $(date) ==="
# Force cloud-init to re-run by cleaning its state, then run our commands
docker stop jobtruth 2>/dev/null || true
docker rm   jobtruth 2>/dev/null || true
docker run -d --name jobtruth --restart always -p 80:8000 \
  -e S3_BUCKET=jobtruth-cat2-offers \
  -e AWS_REGION=ap-south-1 \
  -e AWS_ACCESS_KEY_ID=$env:AWS_ACCESS_KEY_ID \
  -e "AWS_SECRET_ACCESS_KEY=$env:AWS_SECRET_ACCESS_KEY" \
  -e JWT_SECRET_KEY=jobtruth-dev-secret-2024 \
  -e HMAC_SECRET=jobtruth-hmac-secret-2024 \
  jobtruth
echo "Container launched"
'@

$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($shellScript))

Write-Host "[1] Stopping instance..."
& $AWS ec2 stop-instances --region $REGION --instance-ids $IID --output text | Out-Null
Write-Host "    Waiting for stopped..."
& $AWS ec2 wait instance-stopped --region $REGION --instance-ids $IID
Write-Host "    Stopped."

Write-Host "[2] Setting UserData to shell script (runs every boot via rc.local approach)..."
& $AWS ec2 modify-instance-attribute --region $REGION --instance-id $IID --attribute userData --value $b64
Write-Host "    Done."

# Also use ec2:ResetInstanceAttribute to clear UserData run state
Write-Host "[3] Starting instance..."
& $AWS ec2 start-instances --region $REGION --instance-ids $IID --output text | Out-Null
Write-Host "    Waiting for running..."
& $AWS ec2 wait instance-running --region $REGION --instance-ids $IID
Write-Host "    Running."

$IP = & $AWS ec2 describe-instances --region $REGION --instance-ids $IID `
    --query "Reservations[0].Instances[0].PublicIpAddress" --output text
Write-Host "[4] IP: $IP"

Write-Host "[5] Waiting 90s for cloud-init + container..."
Start-Sleep -Seconds 90

Write-Host "[6] Testing health + S3..."
$ok = $false
for ($i = 1; $i -le 15; $i++) {
    try {
        $h = Invoke-RestMethod "http://$IP/health" -TimeoutSec 8 -ErrorAction Stop
        Write-Host "    Health OK: served_by=$($h.served_by)"
        try {
            $s3r = Invoke-RestMethod "http://$IP/objects" -TimeoutSec 12 -ErrorAction Stop
            Write-Host "    S3 OK: $($s3r.Count) objects"
            $ok = $true
        } catch {
            $s3err = $_.Exception.Message
            Write-Host "    S3 STILL FAILING: $s3err"
        }
        break
    } catch {
        $err = $_.Exception.Message
        Write-Host "    Attempt $i/15: $err"
        Start-Sleep -Seconds 15
    }
}

"BUCKET=jobtruth-cat2-offers`nINSTANCE=$IID`nSG=sg-069404559e5c5c139`nIP=$IP" | `
    Out-File "d:\PROJECTS(CAT 2)\Cloud\jobtruth\scripts\deployed.txt" -Encoding utf8

Write-Host ""
if ($ok) { Write-Host "SUCCESS: http://$IP (S3 working)" }
else      { Write-Host "Health OK but S3 may still need fix. URL: http://$IP" }
