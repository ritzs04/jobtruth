$AWS    = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
$REGION = "ap-south-1"
$IID    = "i-05570193524581588"

# cloud-config with "bootcmd" runs on EVERY boot (not just first boot)
$cloudConfig = @'
#cloud-config
bootcmd:
  - |
    docker stop jobtruth 2>/dev/null || true
    docker rm   jobtruth 2>/dev/null || true
    docker run -d --name jobtruth --restart always -p 80:8000 \
      -e S3_BUCKET=jobtruth-cat2-offers \
      -e AWS_REGION=ap-south-1 \
      -e AWS_ACCESS_KEY_ID=$env:AWS_ACCESS_KEY_ID \
      -e "AWS_SECRET_ACCESS_KEY=$env:AWS_SECRET_ACCESS_KEY" \
      -e JWT_SECRET_KEY=jobtruth-dev-secret-2024 \
      -e HMAC_SECRET=jobtruth-hmac-secret-2024 \
      jobtruth && echo "JOBTRUTH STARTED" >> /var/log/jobtruth-boot.log
'@

$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($cloudConfig))

Write-Host "[1] Stopping instance..."
& $AWS ec2 stop-instances --region $REGION --instance-ids $IID --output text | Out-Null
Write-Host "    Waiting for stopped..."
& $AWS ec2 wait instance-stopped --region $REGION --instance-ids $IID
Write-Host "    Stopped."

Write-Host "[2] Updating UserData (cloud-config bootcmd)..."
& $AWS ec2 modify-instance-attribute --region $REGION --instance-id $IID --attribute userData --value $b64
Write-Host "    Done."

Write-Host "[3] Starting instance..."
& $AWS ec2 start-instances --region $REGION --instance-ids $IID --output text | Out-Null
Write-Host "    Waiting for running..."
& $AWS ec2 wait instance-running --region $REGION --instance-ids $IID
Write-Host "    Running."

$IP = & $AWS ec2 describe-instances --region $REGION --instance-ids $IID `
    --query "Reservations[0].Instances[0].PublicIpAddress" --output text
Write-Host "[4] New IP: $IP"

Write-Host "[5] Waiting 60s for container boot..."
Start-Sleep -Seconds 60

Write-Host "[6] Testing..."
for ($i = 1; $i -le 12; $i++) {
    try {
        $h = Invoke-RestMethod "http://$IP/health" -TimeoutSec 8
        Write-Host "    Health: $($h.status) served_by=$($h.served_by)"
        $s3 = Invoke-RestMethod "http://$IP/objects" -TimeoutSec 12
        Write-Host "    S3 objects: $($s3.Count) items -- S3 IS WORKING"
        break
    } catch {
        Write-Host "    Attempt $i/12: $($_.Exception.Message)"
        Start-Sleep -Seconds 15
    }
}

"BUCKET=jobtruth-cat2-offers`nINSTANCE=$IID`nSG=sg-069404559e5c5c139`nIP=$IP" | `
    Out-File "d:\PROJECTS(CAT 2)\Cloud\jobtruth\scripts\deployed.txt" -Encoding utf8
Write-Host ""
Write-Host "URL: http://$IP"
