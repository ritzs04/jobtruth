# JobTruth: Fake Job and Internship Offer Detector

Explainable, rule-based risk scoring for job offers, plus secure offer-letter storage on AWS S3.
Built for the CAT II cloud project: PaaS (Render), IaaS (EC2), S3 management, secure upload.

## Features
- `POST /analyze` trust score (0-100) with every reason listed; lookalike-domain check (Levenshtein), UPI/bank detection
- `POST /headers` SPF / DKIM / DMARC check from raw email headers
- `POST /upload` magic-byte validation, 2 MB limit, SSE-S3, SHA-256 checksum verified by S3, 5-minute presigned URL
- `GET /objects`, `GET /versions`, `DELETE /objects/{key}` bucket management
- PII redaction (phone, email, Aadhaar-like numbers); wording is "risk indicators", never "this is a scam"

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest -v
export S3_BUCKET=your-bucket AWS_REGION=ap-south-1     # needs `aws configure` first; Windows: use set
uvicorn app.main:app --reload                          # http://127.0.0.1:8000
```
Without S3 the analyzer and header checker still work; only upload and bucket management need AWS.

## Deploy
1. **AWS (EC2 + S3 + IAM):** `REPO_URL=https://github.com/YOU/jobtruth.git ./scripts/setup_aws.sh` (needs `aws configure`; use Git Bash or WSL on Windows)
2. **Render (PaaS):** New > Blueprint > select this repo. Set `S3_BUCKET` (from the script output) and the keys of a separate IAM user that has only the S3 policy. Never commit keys.
3. **Evidence:** `./scripts/security_tests.sh http://<EC2-IP>` and screenshot the output.
4. **Cleanup after the viva:** `./scripts/teardown.sh`

## Security design
| Threat | Control |
|---|---|
| Malicious file renamed .pdf | Magic-byte validation, size limit |
| Bucket data leak | Block Public Access, SSE-S3, TLS-only bucket policy |
| Tampering in transit/at rest | SHA-256 checksum verified by S3, versioning |
| Stolen credentials | EC2 IAM role (no keys on server), least-privilege policy, container runs as non-root |
| Privacy exposure | PII redaction, random object names, 30-day lifecycle deletion, presigned URLs |

## Limitations
Rule-based (no live company verification); EC2 bare IP serves HTTP (production: ALB/CloudFront + ACM certificate); Render free tier sleeps when idle.
