# Project Report: JobTruth — Fake Job & Internship Offer Detector
**Course:** MCA Cloud Computing (CAT II Project)  
**Author:** Ritz (GitHub: ritzs04)  
**Repository:** https://github.com/ritzs04/jobtruth  
**Target AWS Region:** Asia Pacific (Mumbai) `ap-south-1`  

---

## 1. Title & Abstract

**Title:** JobTruth — Cloud-Native Fake Job & Internship Offer Detector

**Abstract:**

Online job scams and fraudulent internship offers have surged dramatically, preying especially on students and fresh graduates. Scammers impersonate reputable brands, demand upfront "registration fees" or security deposits via UPI/cryptocurrency, and utilize spoofed lookalike domains (e.g., `micros0ft-careers.com`).

**JobTruth** is an enterprise-grade cloud-native security utility engineered to detect fraudulent job offers using rule-based explainable risk scoring, SPF/DKIM/DMARC email header verification, and confidential document analysis. The solution implements a multi-cloud hybrid architecture spanning **PaaS (Render)** and **IaaS (Amazon EC2)** coupled with encrypted, tamper-proof object storage on **Amazon S3**.

---

## 2. Problem Statement

Fresh graduates and students are the primary targets of fake job and internship scams in India. These scams share common patterns:

- **Financial solicitation:** Demands for registration fees, security deposits, or training charges via UPI or bank transfer before joining.
- **Lookalike domains:** Spoofed domains such as `infosys-careers.xyz` or `tcs-hr.online` that impersonate legitimate companies.
- **Unverifiable senders:** Emails sent from Gmail/Yahoo accounts claiming to be from multinational corporations.
- **Pressure tactics:** Urgency language ("only today", "limited seats") to prevent the victim from verifying the offer.
- **No interview process:** Promises of direct selection without any technical or HR round.

Existing solutions either require technical expertise or provide only a binary safe/unsafe verdict without explanation. JobTruth solves this by providing an **explainable, scored risk analysis** that shows exactly which signals were detected and why they matter.

---

## 3. Cloud Architecture & Infrastructure Design

The architecture is designed strictly adhering to the AWS Well-Architected Framework (Security, Cost Optimization, Reliability, and Operational Excellence):

```
                                  [ User / Browser ]
                                     |           |
            +------------------------+           +-----------------------+
            | (Public HTTPS)                                             | (Public HTTP/80)
            v                                                            v
+-----------------------+                                   +--------------------------+
|  Public PaaS (Render) |                                   |   Amazon EC2 (IaaS)      |
|  - Python 3.12 Web    |                                   |   - Amazon Linux 2023    |
|  - Render Blueprint   |                                   |   - Docker Container     |
|  - Limited IAM User   |                                   |   - IMDSv2 Attached Role |
+-----------+-----------+                                   +------------+-------------+
            |                                                            |
            | IAM Access Keys (Restricted)                               | EC2 Instance Profile Role
            | (s3:PutObject, s3:GetObject)                               | (Temporary STS Credentials)
            +----------------------------+  +----------------------------+
                                         |  |
                                         v  v
                            +-----------------------------+
                            |     Amazon S3 Bucket        |
                            | - Private (Block Public)    |
                            | - AES-256 Encryption (SSE)  |
                            | - Object Versioning         |
                            | - HTTPS/TLS Only Policy     |
                            | - 30-Day Lifecycle Rule     |
                            | - SHA-256 Checksum Verify   |
                            +-----------------------------+
```

### Layer Descriptions

| Layer | Service | Role |
|---|---|---|
| PaaS | Render | Public-facing FastAPI web app, auto-deployed from GitHub |
| IaaS | Amazon EC2 (t2.micro) | Docker-hosted replica, IMDSv2, no stored credentials |
| Object Storage | Amazon S3 | Encrypted, versioned, private offer letter storage |
| CI/CD | GitHub Actions | Automated lint and test on every push |

### Mapping to Evaluation Criteria (40 Marks)

1. **Public PaaS (Render) [8 Marks]:** Automated build and continuous deployment via `render.yaml` Blueprint connected to GitHub.
2. **Amazon EC2 (IaaS) [8 Marks]:** Provisioned with Amazon Linux 2023, automated userdata Docker build, attached IAM instance profile, and secured ingress via custom Security Group.
3. **Amazon S3 Bucket Management [8 Marks]:** Full lifecycle management with strict Block Public Access, SSE-S3 encryption, Object Versioning, and automated 30-day lifecycle expiration.
4. **Secure File Upload & Integrity [8 Marks]:** Magic-byte verification (`%PDF-`), 2 MB payload ceiling, SHA-256 checksum verification, and short-lived (5-minute) pre-signed download URLs.
5. **Documentation, Presentation & Viva [8 Marks]:** Comprehensive technical documentation, architecture slide deck, and exhaustive viva defense preparation.

---

## 4. All Features — Screenshots as Evidence

> **Note to evaluator:** Screenshots below correspond to each live feature of the deployed application. Each screenshot is captioned with the feature name, the API endpoint exercised, and the expected behaviour verified.

---

### Feature 1 — Landing Page & Hero Section

**URL:** `https://jobtruth.onrender.com/`  
**What it shows:** The public landing page with the annotated scam example card (score 0/100, High Risk), navigation to all four tools, and the "Check an offer" CTA.

```
SCREENSHOT PLACEHOLDER — landing_page.png
[ Full-page screenshot of the JobTruth homepage showing:
  - Header with brand logo and nav links
  - Hero headline: "Check a job offer before you pay, share or sign anything."
  - Annotated scam message card with highlighted warning signs and score stamp "0 / 100 High risk"
  - Two CTA buttons: "Check an offer" and "See what it looks for" ]
```

---

### Feature 2 — Offer Message Analyzer (High Risk Result)

**Endpoint:** `POST /analyze`  
**Input:** Scam message containing registration fee, UPI ID, Gmail recruiter, no-interview promise, urgency.  
**Expected output:** Trust score ≤ 39, label "High Risk", all penalty flags listed with reasons.

```
SCREENSHOT PLACEHOLDER — analyze_high_risk.png
[ Screenshot of the "Offer message" tab showing:
  - Textarea filled with scam text
  - Result panel: animated ring gauge showing score (e.g. 0/100) in red
  - Verdict: "High Risk"
  - Flag list: PAYMENT −40, UPI_BANK −25, FREE_EMAIL −20, NO_INTERVIEW −15,
    UNREALISTIC_PAY −15, URGENCY −10, CHAT_ONLY −15
  - Redacted preview at the bottom
  - "Served by" hostname ]
```

---

### Feature 3 — Offer Message Analyzer (Looks Safe Result)

**Endpoint:** `POST /analyze`  
**Input:** Genuine Infosys offer mentioning official domain `careers@infosys.com`, interview process, no payment.  
**Expected output:** Trust score ≥ 70, label "Looks Safe", positive COMPANY_EMAIL flag.

```
SCREENSHOT PLACEHOLDER — analyze_safe.png
[ Screenshot of the "Offer message" tab showing:
  - Textarea filled with genuine Infosys offer text
  - Result panel: animated ring gauge showing score (e.g. 110 capped to 100) in green
  - Verdict: "Looks Safe"
  - Flag list: COMPANY_EMAIL +10
  - Disclaimer text visible ]
```

---

### Feature 4 — Suspicious Result (Score 40–69)

**Endpoint:** `POST /analyze`  
**Input:** Offer with a custom domain but using WhatsApp contact and urgency language.  
**Expected output:** Trust score between 40–69, label "Suspicious", amber colour.

```
SCREENSHOT PLACEHOLDER — analyze_suspicious.png
[ Screenshot showing:
  - Ring gauge in amber/orange
  - Verdict: "Suspicious"
  - Flags: CHAT_ONLY −15, URGENCY −10, CUSTOM_DOMAIN +5 ]
```

---

### Feature 5 — Email Header Verification (Failed SPF/DKIM/DMARC)

**Endpoint:** `POST /headers`  
**Input:** Raw email headers with `dkim=fail`, `spf=softfail`, `dmarc=fail` from `infosys-careers.xyz`.  
**Expected output:** Verdict "Failed checks", three red chips (SPF: softfail, DKIM: fail, DMARC: fail).

```
SCREENSHOT PLACEHOLDER — headers_fail.png
[ Screenshot of the "Email headers" tab showing:
  - Textarea with pasted Authentication-Results header block
  - Verdict: "Failed checks" in red
  - Three chips: SPF: softfail (red), DKIM: fail (red), DMARC: fail (red)
  - Three penalty flags each −15 explaining spoofing risk ]
```

---

### Feature 6 — Email Header Verification (Authenticated)

**Endpoint:** `POST /headers`  
**Input:** Headers with `spf=pass`, `dkim=pass`, `dmarc=pass`.  
**Expected output:** Verdict "Authenticated", three green chips.

```
SCREENSHOT PLACEHOLDER — headers_pass.png
[ Screenshot showing:
  - Verdict: "Authenticated" in green
  - Three chips: SPF: pass (green), DKIM: pass (green), DMARC: pass (green)
  - No penalty flags ]
```

---

### Feature 7 — Secure File Upload (Success + Integrity Verified)

**Endpoint:** `POST /upload`  
**Input:** A valid PDF offer letter (≤ 2 MB).  
**Expected output:** HTTP 200, encryption = AES256, integrity_verified = true, SHA-256 hex, version ID, 5-minute pre-signed URL.

```
SCREENSHOT PLACEHOLDER — upload_success.png
[ Screenshot of the "Offer letter file" tab showing:
  - File picker with a PDF selected
  - Result panel after upload:
    - Verdict: "Stored and verified" in green
    - Encryption: AES256 (green)
    - Integrity: SHA-256 matches (green)
    - SHA-256 hex fingerprint
    - Object key: offers/<uuid>.pdf
    - Version ID from S3
    - Private link: "Open (expires in 300 seconds)" ]
```

---

### Feature 8 — File Upload Rejected: Wrong File Type (Magic Byte Check)

**Endpoint:** `POST /upload`  
**Input:** An executable or text file renamed as `.pdf`.  
**Expected output:** HTTP 400 — "Only PDF, PNG or JPG files are allowed".

```
SCREENSHOT PLACEHOLDER — upload_bad_type.png
[ Screenshot showing:
  - Upload rejected error message in red:
    "Upload rejected: Only PDF, PNG or JPG files are allowed"
  - Demonstrates magic-byte validation (content checked, not filename) ]
```

---

### Feature 9 — File Upload Rejected: Oversized File

**Endpoint:** `POST /upload`  
**Input:** A file larger than 2 MB.  
**Expected output:** HTTP 413 — "File too large (max 2 MB)".

```
SCREENSHOT PLACEHOLDER — upload_too_large.png
[ Screenshot showing:
  - Upload rejected error message in red:
    "Upload rejected: File too large (max 2 MB)" ]
```

---

### Feature 10 — Stored Files List

**Endpoint:** `GET /objects`  
**What it shows:** Table of all objects currently in the `offers/` S3 prefix with key, size in KB, and upload timestamp. Delete button per row.

```
SCREENSHOT PLACEHOLDER — stored_files.png
[ Screenshot of the "Stored files" tab showing:
  - Table with columns: File | Size | Uploaded | (Delete button)
  - One or more rows with offers/<uuid>.pdf entries
  - Delete button visible per row ]
```

---

### Feature 11 — Object Versioning List

**Endpoint:** `GET /versions`  
**What it shows:** All S3 object versions and delete markers, proving versioning is enabled and files are recoverable after deletion.

```
SCREENSHOT PLACEHOLDER — versions_list.png
[ Screenshot showing:
  - Table with columns: File | Type | Current | Version ID
  - Rows showing "version" and "delete-marker" types
  - Multiple version IDs for the same key proving versioning is active ]
```

---

### Feature 12 — Health Check Endpoint

**Endpoint:** `GET /health`  
**What it shows:** JSON response `{"status": "ok", "served_by": "<hostname>"}` confirming the service is live and identifying which host (Render PaaS or EC2 IaaS) served the request.

```
SCREENSHOT PLACEHOLDER — health_check.png
[ Browser or curl screenshot showing:
  {"status": "ok", "served_by": "srv-xxxx"} from Render
  or
  {"status": "ok", "served_by": "ip-172-xx-xx-xx"} from EC2 ]
```

---

### Feature 13 — PaaS Deployment on Render

**What it shows:** The Render dashboard confirming the `jobtruth` web service is live, deployed from the GitHub repository via `render.yaml` Blueprint, with health check passing at `/health`.

```
SCREENSHOT PLACEHOLDER — render_dashboard.png
[ Screenshot of Render.com dashboard showing:
  - Service name: jobtruth
  - Status: Live (green)
  - Deploy triggered from GitHub commit
  - Health check: /health passing
  - Environment variables: AWS_REGION, S3_BUCKET set (values hidden) ]
```

---

### Feature 14 — IaaS Deployment on Amazon EC2

**What it shows:** AWS Console EC2 Instances page showing the `jobtruth` instance running on Amazon Linux 2023, with instance type, public IP, and the attached IAM role (`jobtruth-ec2-role`).

```
SCREENSHOT PLACEHOLDER — ec2_instance.png
[ Screenshot of AWS EC2 Console showing:
  - Instance state: Running (green)
  - Instance type: t2.micro / t3.micro
  - AMI: Amazon Linux 2023
  - IAM role: jobtruth-ec2-role
  - Public IPv4 DNS visible
  - Security group: jobtruth-sg ]
```

---

### Feature 15 — Amazon S3 Bucket Configuration

**What it shows:** AWS S3 Console showing the bucket with Block Public Access enabled, SSE-S3 encryption, versioning enabled, and the lifecycle rule `expire-offers`.

```
SCREENSHOT PLACEHOLDER — s3_bucket.png
[ Screenshot of AWS S3 Console showing:
  - Bucket name: jobtruth-offers-<account-id>
  - Block Public Access: all four settings ON (green ticks)
  - Default encryption: SSE-S3 (AES-256)
  - Versioning: Enabled
  - Lifecycle rule: expire-offers (30 days expiration) ]
```

---

### Feature 16 — S3 Bucket Policy (HTTPS-Only Enforcement)

**What it shows:** The bucket policy JSON denying any request where `aws:SecureTransport` is `false`, enforcing TLS for all data in transit.

```
SCREENSHOT PLACEHOLDER — s3_bucket_policy.png
[ Screenshot of S3 Bucket Policy editor showing:
  {
    "Effect": "Deny",
    "Principal": "*",
    "Action": "s3:*",
    "Resource": ["arn:aws:s3:::jobtruth-offers-.../*",
                 "arn:aws:s3:::jobtruth-offers-..."],
    "Condition": {"Bool": {"aws:SecureTransport": "false"}}
  } ]
```

---

### Feature 17 — IAM Least-Privilege Policy

**What it shows:** AWS IAM Console showing the `jobtruth-render-policy` scoped to only `s3:PutObject` and `s3:GetObject` on the `offers/*` prefix, and the `jobtruth-ec2-role` with the same policy attached.

```
SCREENSHOT PLACEHOLDER — iam_policy.png
[ Screenshot of AWS IAM Policy showing:
  - Actions: s3:PutObject, s3:GetObject
  - Resource: arn:aws:s3:::jobtruth-offers-.../offers/*
  - No s3:DeleteObject, no s3:ListBucket at root level ]
```

---

### Feature 18 — GitHub Actions CI Pipeline

**What it shows:** The `.github/workflows/ci.yml` pipeline passing on a recent commit — lint (flake8) and unit tests (pytest) both green.

```
SCREENSHOT PLACEHOLDER — github_actions.png
[ Screenshot of GitHub Actions run showing:
  - Workflow: CI
  - Jobs: lint ✓, test ✓
  - All steps green
  - Triggered by push to main branch ]
```

---

### Feature 19 — PII Redaction in Analysis Preview

**Endpoint:** `POST /analyze` (field: `redacted_preview`)  
**What it shows:** The "What was checked" preview at the bottom of the analysis result, where phone numbers, email addresses, and Aadhaar-like numbers are replaced with `[REDACTED]` before display.

```
SCREENSHOT PLACEHOLDER — pii_redaction.png
[ Screenshot of analysis result bottom section showing:
  "What was checked (personal details hidden):"
  "...contact [REDACTED] or email [REDACTED] for registration..."
  Demonstrating PII stripping before any preview is rendered ]
```

---

### Feature 20 — Dark Mode Support

**What it shows:** The full application rendered in dark mode (triggered by OS `prefers-color-scheme: dark`), confirming accessibility and CSS variable theming.

```
SCREENSHOT PLACEHOLDER — dark_mode.png
[ Screenshot of the application in dark mode showing:
  - Dark navy background (#0b1220)
  - All text, cards, and result panels correctly themed
  - No contrast issues ]
```

---

## 5. Security Design Table

| Control | Implementation | Standard / Rationale |
|---|---|---|
| Encryption at Rest | SSE-S3 (AES-256) on every S3 object | AWS default encryption; protects stored offer letters |
| Encryption in Transit | S3 bucket policy denies `aws:SecureTransport=false` | Enforces HTTPS/TLS for all S3 API calls |
| Block Public Access | All four S3 Block Public Access settings enabled | Prevents accidental public exposure of offer letters |
| Object Versioning | S3 versioning enabled on bucket | Protects against accidental overwrite and malicious deletion |
| Lifecycle Management | 30-day expiration rule on `offers/*` | Storage minimization; reduces attack surface over time |
| Integrity Verification | SHA-256 checksum sent with upload, verified via `ChecksumMode=ENABLED` on `head_object` | Detects tampering or corruption in transit/at rest |
| Magic Byte Validation | First 4 bytes checked against `%PDF`, `\x89PNG`, `\xff\xd8\xff` | Prevents disguised executables; filename is not trusted |
| File Size Limit | 2 MB hard ceiling enforced before S3 write | Prevents DoS via large payload; enforced server-side |
| Pre-signed URL Expiry | `ExpiresIn=300` (5 minutes) | Limits window for credential-free access to stored files |
| Least-Privilege IAM | Render IAM user: only `s3:PutObject` + `s3:GetObject` on `offers/*` | Principle of least privilege; no delete or list at root |
| IMDSv2 on EC2 | `HttpTokens=required`, `HttpPutResponseHopLimit=2` | Prevents SSRF-based metadata credential theft |
| No Stored Credentials on EC2 | EC2 uses attached instance profile role (STS temporary credentials) | Eliminates long-lived key exposure on the instance |
| JWT Authentication | HS256 JWT, 7-day expiry, bcrypt password hashing | Stateless auth; passwords never stored in plaintext |
| PII Redaction | Phone, email, Aadhaar-pattern stripped before preview render | Prevents accidental PII display in the UI |
| Security Group | Ingress: TCP 80 (public), TCP 22 (admin IP only) | Minimises EC2 attack surface |
| HTTPS on PaaS | Render provides automatic TLS certificate | All browser traffic encrypted end-to-end |
| AWS Budget Alert | $0.01 zero-spend threshold + $1.00 alert | Detects unexpected resource usage immediately |

---

## 6. Verification and Security Test Results

The suite `scripts/security_tests.sh` verifies defensive controls against malicious attacks:

| Test Case | Simulated Attack | Expected Result | Status |
|---|---|---|---|
| 1. Magic Byte Validation | Executable (`MZ` PE header) renamed as `.pdf` | `HTTP 400 Bad Request` | PASS |
| 2. File Size Enforcement | 3 MB oversized payload submitted to `/upload` | `HTTP 413 Payload Too Large` | PASS |
| 3. Valid Upload & Integrity | Legitimate PDF document with SHA-256 hash | `HTTP 200 OK` (integrity verified) | PASS |
| 4. Public Access Blocking | Direct unauthenticated S3 object URL access | `HTTP 403 Forbidden` | PASS |
| 5. In-Transit Encryption | Insecure HTTP request directly to S3 endpoint | `HTTP 403 Forbidden` (TLS Policy) | PASS |
| 6. Pre-signed Expiration | Accessing pre-signed URL after 300 seconds | `HTTP 403 AccessDenied` | PASS |

---

## 7. Cost Optimization & Free Tier Compliance

- **EC2:** Under 750 free hours of `t2.micro`/`t3.micro`.
- **S3:** Under 5 GB Standard Storage and < 2000 PUT requests.
- **Render:** Free web service plan (0.1 CPU, 512 MB RAM).
- **Guardrails:** AWS Budget configured with $0.01 zero-spend threshold and $1.00 alert trigger.

---

## 8. Conclusion

JobTruth successfully demonstrates a resilient cloud architecture that integrates PaaS agility with IaaS control, anchored by industry-standard cloud security practices on Amazon Web Services.

The project delivers:

- **Explainable AI-style risk scoring** — every flag shows its impact and reason, not just a verdict.
- **Multi-layer cloud security** — encryption at rest and in transit, integrity verification, least-privilege IAM, IMDSv2, and pre-signed URL expiry all working together.
- **Hybrid deployment** — the same Docker image runs on both Render (PaaS) and EC2 (IaaS), with the `served_by` field in every API response proving which host answered.
- **Zero-cost operation** — the entire stack runs within AWS Free Tier and Render's free plan, with budget alerts as a safety net.
- **Production-grade practices** — CI/CD via GitHub Actions, PII redaction, magic-byte file validation, and automated lifecycle management demonstrate readiness beyond a student prototype.

The architecture is extensible: adding an RDS database for user history, an SQS queue for batch analysis, or a CloudFront distribution for global CDN would each slot in without redesigning the core.
