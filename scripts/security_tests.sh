#!/usr/bin/env bash
# Produces evidence for the "Secure upload" marks. Usage: ./scripts/security_tests.sh http://<EC2-IP-or-render-url>
set -u
BASE=${1:?Usage: $0 BASE_URL}
BUCKET_URL=${2:-}   # optional: https://<bucket>.s3.ap-south-1.amazonaws.com
head -c 300 /dev/urandom > /tmp/fake.pdf; printf 'MZ' | cat - /tmp/fake.pdf > /tmp/evil.pdf
head -c 3000000 /dev/zero > /tmp/big.pdf; printf '%%PDF-1.4' | cat - /tmp/big.pdf > /tmp/big2.pdf
printf '%%PDF-1.4 sample offer letter' > /tmp/ok.pdf

echo "1) EXE bytes renamed .pdf  -> expect 400"
curl -s -o /dev/null -w "HTTP %{http_code}\n" -F "file=@/tmp/evil.pdf" "$BASE/upload"
echo "2) 3 MB file               -> expect 413"
curl -s -o /dev/null -w "HTTP %{http_code}\n" -F "file=@/tmp/big2.pdf" "$BASE/upload"
echo "3) Valid PDF               -> expect 200, integrity_verified true"
RESP=$(curl -s -F "file=@/tmp/ok.pdf" "$BASE/upload"); echo "$RESP"
KEY=$(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('key',''))")
if [ -n "$BUCKET_URL" ] && [ -n "$KEY" ]; then
  echo "4) Direct S3 URL without signature -> expect 403"
  curl -s -o /dev/null -w "HTTP %{http_code}\n" "$BUCKET_URL/$KEY"
  echo "5) Plain http:// to bucket         -> expect 403 (TLS-only policy)"
  curl -s -o /dev/null -w "HTTP %{http_code}\n" "http://${BUCKET_URL#https://}/$KEY"
fi
echo "6) Open temp_download_url, wait 5 minutes, open again -> expect AccessDenied (expired)"
