# Project Report: JobTruth — Fake Job & Internship Offer Detector
**Course:** MCA Cloud Computing (CAT II Project)  
**Author:** Ritz (GitHub: ritzs04)  
**Repository:** https://github.com/ritzs04/jobtruth  
**Target AWS Region:** Asia Pacific (Mumbai) `ap-south-1`  

---

## 1. Executive Summary & Problem Statement

Online job scams and fraudulent internship offers have surged dramatically, preying especially on students and fresh graduates. Scammers impersonate reputable brands, demand upfront "registration fees" or security deposits via UPI/cryptocurrency, and utilize spoofed lookalike domains (e.g., `micros0ft-careers.com`).

**JobTruth** is an enterprise-grade cloud-native security utility engineered to detect fraudulent job offers using rule-based explainable risk scoring, SPF/DKIM/DMARC email header verification, and confidential document analysis. The solution implements a multi-cloud hybrid architecture spanning **PaaS (Render)** and **IaaS (Amazon EC2)** coupled with encrypted, tamper-proof object storage on **Amazon S3**.

---

## 2. Cloud Architecture & Infrastructure Design

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

### Mapping to Evaluation Criteria (40 Marks):
1. **Public PaaS (Render) [8 Marks]:** Automated build and continuous deployment via `render.yaml` Blueprint connected to GitHub.
2. **Amazon EC2 (IaaS) [8 Marks]:** Provisioned with Amazon Linux 2023, automated userdata Docker build, attached IAM instance profile, and secured ingress via custom Security Group.
3. **Amazon S3 Bucket Management [8 Marks]:** Full lifecycle management with strict Block Public Access, SSE-S3 encryption, Object Versioning, and automated 30-day lifecycle expiration.
4. **Secure File Upload & Integrity [8 Marks]:** Magic-byte verification (`%PDF-`), 2 MB payload ceiling, SHA-256 checksum verification, and short-lived (5-minute) pre-signed download URLs.
5. **Documentation, Presentation & Viva [8 Marks]:** Comprehensive technical documentation, architecture slide deck, and exhaustive viva defense preparation.

---

## 3. Component Deep Dive

### 3.1 Application Layer (FastAPI & Rule Engine)
- **Framework:** FastAPI running on Python 3.12 with Uvicorn ASGI server.
- **Explainable Scoring Engine:** Calculates risk score (0-100) based on weighted heuristics:
  - Financial solicitation (UPI ID detection, upfront deposit requests).
  - Lookalike domain detection via Levenshtein distance against known tech firms.
  - Suspicious communication channels (Telegram, WhatsApp recruitment).
  - Non-corporate email domains (Gmail/Yahoo used for multinational corporate offers).
- **Email Header Verification:** Parses `Authentication-Results` and `Received-SPF` headers to check SPF, DKIM, and DMARC alignment.
- **Privacy & PII Protection:** Strips sensitive data (phone numbers, email addresses, Aadhaar-like identifiers) before rendering analysis previews.

### 3.2 PaaS Deployment (Render)
- Defined declaratively in `render.yaml`.
- Health check monitoring configured at `/health`.
- Connected to GitHub repository for automated CI/CD upon branch updates.
- Configured with least-privilege IAM credentials scoped strictly to `s3:PutObject` and `s3:GetObject` on `offers/*`.

### 3.3 IaaS Deployment (Amazon EC2)
- **Instance Type:** `t3.micro` / `t2.micro` (AWS Free Tier eligible: 750 hours/month).
- **AMI:** Amazon Linux 2023 (`al2023-ami-kernel-default-x86_64`).
- **Security:**
  - Token-based Instance Metadata Service (IMDSv2) enforced with `HttpPutResponseHopLimit=2` to securely bridge containerized credentials.
  - Zero permanent credentials stored on the instance; uses temporary STS credentials via attached IAM Role (`jobtruth-ec2-role`).
  - Security Group ingress limited to TCP Port 80 (HTTP) for public access and TCP Port 22 (SSH) restricted to admin IP.

### 3.4 S3 Security & Storage Architecture
- **Confidentiality:** Server-Side Encryption with Amazon S3 managed keys (`AES256`).
- **Data Protection in Transit:** Explicit bucket policy denying all `aws:SecureTransport == false` traffic.
- **Integrity Verification:** The SHA-256 hash calculated prior to upload is validated against Amazon S3 storage metadata.
- **Versioning:** Enabled to prevent malicious overwrite or accidental loss of original uploaded evidence.
- **Lifecycle Management:** Rule `expire-offers` automatically removes objects and noncurrent versions after 30 days to enforce storage minimization and zero cost.

---

## 4. Verification and Security Test Results

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

## 5. Cost Optimization & Free Tier Compliance

- **EC2:** Under 750 free hours of `t2.micro`/`t3.micro`.
- **S3:** Under 5 GB Standard Storage and < 2000 PUT requests.
- **Render:** Free web service plan (0.1 CPU, 512 MB RAM).
- **Guardrails:** AWS Budget configured with \$0.01 zero-spend threshold and \$1.00 alert trigger.

---

## 6. Conclusion

JobTruth successfully demonstrates a resilient cloud architecture that integrates PaaS agility with IaaS control, anchored by industry-standard cloud security practices on Amazon Web Services.
