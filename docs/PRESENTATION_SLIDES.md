# JobTruth — Cloud Computing CAT II Presentation Slides

---

## Slide 1: Title Slide
- **Title:** JobTruth: Fake Job and Internship Offer Detector
- **Subtitle:** Multi-Cloud Deployment (Render PaaS & AWS EC2 IaaS) with Hardened AWS S3 Object Storage
- **Student Name:** Ritz (PG MCA)
- **GitHub:** `github.com/ritzs04/jobtruth`
- **Course:** Cloud Computing (CAT II)

---

## Slide 2: Problem Statement & Motivation
- **The Challenge:** Rapid rise in fake internship letters and fraudulent recruitment drives targeting students.
- **Common Patterns:**
  - Demands for registration/security deposits via UPI or QR code.
  - Lookalike / typo-squatted domains (`google-recruitment-team.com`).
  - Telegram/WhatsApp interview invitations.
  - Forged email headers lacking SPF/DKIM authentication.
- **The Solution:** A unified, explainable cloud detection system with secure evidentiary document archiving.

---

## Slide 3: Architecture Overview
- **Frontend / Client:** Responsive web UI with real-time risk indicators and drag-and-drop document upload.
- **Application Layer:** FastAPI (Python 3.12) ASGI service.
- **Deployment Strategy:**
  1. **PaaS (Platform as a Service):** Render with GitHub CI/CD automation.
  2. **IaaS (Infrastructure as a Service):** Amazon EC2 running Docker on Amazon Linux 2023.
- **Storage Layer:** Amazon S3 with end-to-end encryption, versioning, and lifecycle management.

---

## Slide 4: Public PaaS Deployment (Render) — Mark 1
- **Blueprint Automation:** Infrastructure-as-code via `render.yaml`.
- **Zero-Touch CI/CD:** Auto-builds from GitHub `main` branch.
- **Environment Isolation:** S3 integration via restricted IAM service credentials.
- **Health Checks:** Automated probe at `/health` to ensure zero-downtime rolling updates.

---

## Slide 5: Amazon EC2 (IaaS) Implementation — Mark 2
- **Instance Configuration:** `t3.micro` / `t2.micro` within AWS Free Tier.
- **Automated Provisioning:** EC2 UserData script clones repo, builds Docker image, and launches container.
- **Security Hardening:**
  - Token-based Instance Metadata Service (IMDSv2) with hop limit = 2.
  - Zero hardcoded access keys on the instance.
  - Custom Security Group: Ingress restricted to HTTP (80) and SSH (22 from admin IP only).

---

## Slide 6: Amazon S3 Bucket Architecture — Mark 3
- **Block Public Access:** All 4 public access blocks enabled (BlockPublicAcls, IgnorePublicAcls, BlockPublicPolicy, RestrictPublicBuckets).
- **Server-Side Encryption:** SSE-S3 using AES-256 algorithm by default.
- **Object Versioning:** Enabled to preserve historical evidence and prevent accidental deletion.
- **Lifecycle Policies:** Automated 30-day expiration of current and non-current versions to prevent storage creep.
- **TLS Enforcement:** Strict bucket policy explicitly denying all non-HTTPS (`aws:SecureTransport: false`) requests.

---

## Slide 7: Secure File Upload & Integrity — Mark 4
- **Defense-in-Depth Validation:**
  - **Magic-Byte Inspection:** Verifies `%PDF-` file header (prevents disguised `.exe` / malware payloads).
  - **Size Guardrails:** Strict 2 MB payload ceiling.
  - **Integrity Guarantee:** SHA-256 digest calculated and verified during S3 PutObject.
  - **Confidential Retrieval:** 5-minute pre-signed URLs; direct bucket URLs reject with HTTP 403.
- **Privacy Assurance:** PII redaction engine strips phone numbers, emails, and sensitive identifiers.

---

## Slide 8: Live Verification & Security Test Suite
- Automated testing via `scripts/security_tests.sh`:
  1. Executable file disguised as `.pdf` ➔ **400 Bad Request**
  2. Oversized 3MB file ➔ **413 Payload Too Large**
  3. Legitimate PDF upload ➔ **200 OK + SHA-256 verified**
  4. Direct S3 Object URL ➔ **403 Forbidden**
  5. Insecure HTTP S3 URL ➔ **403 Forbidden**
  6. Expired pre-signed URL ➔ **403 AccessDenied**

---

## Slide 9: Cost & Resource Optimization
- **AWS Free Tier Strict Compliance:**
  - EC2: 750 free hours/month.
  - S3: Standard Tier under 5 GB, < 2,000 requests.
- **Financial Safety Net:**
  - \$0.01 Zero-Spend Alert in AWS Budgets.
  - \$1.00 Monthly Cost Threshold Alert.
  - Automated `teardown.sh` script to delete all resources post-viva.

---

## Slide 10: Conclusion & Key Learnings
- Successfully demonstrated hybrid deployment comparing PaaS (Render) vs. IaaS (Amazon EC2).
- Enforced enterprise cloud security best practices (IMDSv2, least privilege IAM, S3 hardening).
- Built a practical, explainable tool solving a real-world student vulnerability.
- Thank You! Questions & Viva Discussion.
