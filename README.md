# JobTruth — Fake Job & Internship Offer Detector

[![CI](https://github.com/ritzs04/jobtruth/actions/workflows/ci.yml/badge.svg)](https://github.com/ritzs04/jobtruth/actions/workflows/ci.yml)
[![Live on Render](https://img.shields.io/badge/Live-Render-46E3B7?logo=render&logoColor=white)](https://jobtruth.onrender.com)

**Live URL → https://jobtruth.onrender.com**

Explainable, rule-based risk scoring for job offers — with secure offer-letter storage on AWS S3.  
Built for the CAT II cloud project: IaaS (AWS EC2) + PaaS (Render) + S3 managed storage.

---

## Features

| Feature | Endpoint |
|---------|----------|
| Offer text analysis — trust score 0–100, flag-by-flag explanations | `POST /analyze` |
| Email header analysis — SPF / DKIM / DMARC verification | `POST /headers` |
| Company verification — 200+ known companies + lookalike detection | `GET /company/verify` |
| Secure document upload — magic-byte check, 2 MB limit, AES-256, SHA-256 checksum | `POST /upload` |
| Bucket management — list, version history, delete | `GET /objects` `GET /versions` `DELETE /objects/{key}` |
| User auth — bcrypt hashed passwords, 7-day JWT tokens | `POST /auth/register` `POST /auth/login` |
| PII redaction — phone, email, Aadhaar patterns stripped before storage | built-in |
| Live scam statistics | `GET /stats` |

---

## Run Locally

```bash
# Clone
git clone https://github.com/ritzs04/jobtruth.git
cd jobtruth

# Virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

# Install
pip install -r requirements-dev.txt

# Environment (copy and fill in your AWS credentials)
copy .env.example .env   # Windows
# cp .env.example .env   # Mac/Linux

# Run tests
pytest -v

# Start server
uvicorn app.main:app --reload
# Open http://127.0.0.1:8000
```

> Without AWS credentials, `/analyze`, `/headers`, and `/company/verify` all work.  
> Only `/upload`, `/objects`, `/versions`, and `/delete` need S3.

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `S3_BUCKET` | AWS S3 bucket name |
| `AWS_REGION` | AWS region (e.g. `ap-south-1`) |
| `AWS_ACCESS_KEY_ID` | IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key |
| `JWT_SECRET_KEY` | Secret for signing JWT tokens |
| `HMAC_SECRET` | HMAC signing secret |

Copy `.env.example` to `.env` and fill in the values. **Never commit `.env`.**

---

## Deploy on Render (PaaS)

1. Fork this repo on GitHub
2. Go to [render.com](https://render.com) → **New → Blueprint**
3. Select your fork — Render auto-detects `render.yaml`
4. Add secrets in the Render dashboard:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `JWT_SECRET_KEY`
   - `HMAC_SECRET`
5. Click **Apply** — your app is live at `https://jobtruth.onrender.com`

---

## Deploy on AWS EC2 (IaaS)

```bash
# Requires: aws configure, Git Bash / WSL on Windows
REPO_URL=https://github.com/ritzs04/jobtruth.git ./scripts/setup_aws.sh
```

The script:
- Launches a `t3.micro` in `ap-south-1`
- Creates an S3 bucket with encryption + versioning + block-public-access
- Creates an IAM role with least-privilege S3 policy
- Installs Docker and runs the container on port 80

---

## Security Design

| Threat | Control |
|--------|---------|
| Malicious file disguised as .pdf | Magic-byte validation (not filename) |
| S3 data leak | Block Public Access + presigned URLs (5 min expiry) |
| Tampering in transit/at rest | SHA-256 checksum verified by S3, AES-256 SSE |
| Credential exposure | Env vars only, never committed; `.env` in `.gitignore` |
| Weak passwords | bcrypt (work factor 12) |
| JWT forgery | HS256 + secret env var, 7-day expiry |
| Path traversal | Key must start with `offers/`, no `..` allowed |
| Container privilege escalation | Non-root `appuser` in Dockerfile |
| PII in logs | Redactor strips email, phone, Aadhaar before DB write |
| Lookalike domains | Levenshtein ≤ 2 against 15 known company domains |

---

## Project Structure

```
jobtruth/
├── app/
│   ├── main.py        # FastAPI routes
│   ├── rules.py       # Risk scoring rule engine
│   ├── auth.py        # JWT + bcrypt auth
│   ├── db.py          # SQLite models
│   ├── storage.py     # S3 operations
│   ├── pii.py         # PII redaction
│   ├── security.py    # Domain age / breach checks
│   └── verify.py      # Company verification helpers
├── public/
│   └── index.html     # Single-page frontend
├── tests/
│   ├── test_rules.py
│   └── test_upload.py
├── docs/              # Project documentation
├── scripts/           # AWS setup + deployment scripts
├── Dockerfile
├── render.yaml        # Render PaaS config
└── requirements.txt
```

---

## Cleanup

```bash
./scripts/teardown.sh   # Terminates EC2, deletes S3 bucket, removes IAM role
```
