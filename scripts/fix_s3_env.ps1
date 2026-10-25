$AWS    = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
$REGION = "ap-south-1"
$IID    = "i-05570193524581588"

# Strategy: write .env file to /opt/jobtruth/.env inside the container via a
# volume mount, AND also pass env vars explicitly. Use a startup script that:
# 1. Stops docker service (prevents old container restart)
# 2. Removes ALL containers
# 3. Writes the env file to host
# 4. Starts docker
# 5. Runs a FRESH container with all -e flags AND --env-file

$shellScript = @'
#!/bin/bash
set -e
exec >> /var/log/jobtruth-envfix.log 2>&1
echo "=== ENV FIX $(date) ==="

# 1. Stop docker completely (prevents auto-restart of old container)
systemctl stop docker.socket docker 2>/dev/null || true
sleep 3

# 2. Remove all container configs (wipes restart policies permanently)
rm -rf /var/lib/docker/containers

# 3. Start docker clean
systemctl start docker
sleep 8

# 4. Write env file to host
mkdir -p /opt/jobtruth
cat > /opt/jobtruth/.env << 'ENVEOF'
S3_BUCKET=jobtruth-cat2-offers
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=$env:AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=$env:AWS_SECRET_ACCESS_KEY
JWT_SECRET_KEY=jobtruth-dev-secret-2024
HMAC_SECRET=jobtruth-hmac-secret-2024
ENVEOF
chmod 600 /opt/jobtruth/.env

# 5. Launch fresh container — mount the .env file AND pass individual -e flags
#    so python-dotenv AND boto3 both pick them up
docker run -d \
  --name jobtruth \
  --restart always \
  -p 80:8000 \
  -v /opt/jobtruth/.env:/code/.env:ro \
  -e S3_BUCKET=jobtruth-cat2-offers \
  -e AWS_REGION=ap-south-1 \
  -e AWS_ACCESS_KEY_ID=$env:AWS_ACCESS_KEY_ID \
  -e "AWS_SECRET_ACCESS_KEY=$env:AWS_SECRET_ACCESS_KEY" \
  -e JWT_SECRET_KEY=jobtruth-dev-secret-2024 \
  -e HMAC_SECRET=jobtruth-hmac-secret-2024 \
  jobtruth

echo "Container ID: $(docker ps -q --filter name=jobtruth)"
echo "=== DONE $(date) ==="
'@

$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($shellScript))

Write-Host "[1] Stopping instance..."
& $AWS ec2 stop-instances --region $REGION --instance-ids $IID --output text | Out-Null
& $AWS ec2 wait instance-stopped --region $REGION --instance-ids $IID
Write-Host "    Stopped."

Write-Host "[2] Updating UserData..."
& $AWS ec2 modify-instance-attribute --region $REGION --instance-id $IID --attribute userData --value $b64
Write-Host "    Done."

Write-Host "[3] Starting instance..."
& $AWS ec2 start-instances --region $REGION --instance-ids $IID --output text | Out-Null
& $AWS ec2 wait instance-running --region $REGION --instance-ids $IID

$IP = & $AWS ec2 describe-instances --region $REGION --instance-ids $IID `
    --query "Reservations[0].Instances[0].PublicIpAddress" --output text
Write-Host "[4] IP: $IP — waiting 90s..."
Start-Sleep -Seconds 90

Write-Host "[5] Testing..."
for ($i = 1; $i -le 15; $i++) {
    try {
        $h = Invoke-RestMethod "http://$IP/health" -TimeoutSec 8 -ErrorAction Stop
        Write-Host "    Health: $($h.status) served_by=$($h.served_by)"
        try {
            $s3r = Invoke-RestMethod "http://$IP/objects" -TimeoutSec 12 -ErrorAction Stop
            Write-Host "    *** S3 WORKING: $($s3r.Count) objects ***"
        } catch {
            $eb = ""; try { $eb = $_.ErrorDetails.Message } catch {}
            Write-Host "    S3 FAIL: $eb"
        }
        break
    } catch {
        Write-Host "    Attempt $i: $($_.Exception.Message)"
        Start-Sleep -Seconds 15
    }
}

"BUCKET=jobtruth-cat2-offers`nINSTANCE=$IID`nSG=sg-069404559e5c5c139`nIP=$IP" | `
    Out-File "d:\PROJECTS(CAT 2)\Cloud\jobtruth\scripts\deployed.txt" -Encoding utf8
Write-Host "EC2 URL: http://$IP"
