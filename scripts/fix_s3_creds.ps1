$AWS    = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
$REGION = "ap-south-1"
$IID    = "i-05570193524581588"

# Build the startup script that runs on EC2 at boot
$script = @'
#!/bin/bash
exec >> /var/log/jobtruth-start.log 2>&1
echo "=== JobTruth startup $(date) ==="
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
echo "Container started"
'@

$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($script))

Write-Host "[1] Updating UserData with full credentials..."
& $AWS ec2 modify-instance-attribute `
    --region $REGION `
    --instance-id $IID `
    --attribute userData `
    --value $b64
Write-Host "    Done"

Write-Host "[2] Starting instance..."
& $AWS ec2 start-instances --region $REGION --instance-ids $IID --output text
Write-Host "    Waiting for running state..."
& $AWS ec2 wait instance-running --region $REGION --instance-ids $IID
Write-Host "    Running"

Write-Host "[3] Getting public IP..."
$IP = & $AWS ec2 describe-instances --region $REGION --instance-ids $IID `
    --query "Reservations[0].Instances[0].PublicIpAddress" --output text
Write-Host "    IP: $IP"

Write-Host "[4] Waiting 45s for container to start..."
Start-Sleep -Seconds 45

Write-Host "[5] Testing health..."
for ($i = 1; $i -le 10; $i++) {
    try {
        $r = Invoke-RestMethod "http://$IP/health" -TimeoutSec 10
        Write-Host "    LIVE: status=$($r.status), served_by=$($r.served_by)"
        break
    } catch {
        Write-Host "    Attempt $i/10 - waiting..."
        Start-Sleep -Seconds 20
    }
}

Write-Host "[6] Testing S3 list objects..."
try {
    $r = Invoke-RestMethod "http://$IP/objects" -TimeoutSec 15
    Write-Host "    S3 OK - $($r.Count) objects"
} catch {
    Write-Host "    S3 FAILED: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "New IP: $IP"
"BUCKET=jobtruth-cat2-offers`nINSTANCE=$IID`nSG=sg-069404559e5c5c139`nIP=$IP" | `
    Out-File "d:\PROJECTS(CAT 2)\Cloud\jobtruth\scripts\deployed.txt" -Encoding utf8
Write-Host "deployed.txt updated"
