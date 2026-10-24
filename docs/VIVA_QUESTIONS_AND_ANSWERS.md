# JobTruth: Comprehensive Viva Questions & Model Answers
**Target Audience:** MCA External/Internal Viva Examiner & Evaluation Panel  
**Course:** Cloud Computing (CAT II Project)  
**Student:** Ritz (GitHub: ritzs04)  

---

## Category 1: Public PaaS (Render) [Marking Criterion 1]

### Q1. What is PaaS and how does Render qualify as PaaS in your project?
**Answer:**  
Platform as a Service (PaaS) abstracts away operating system patching, runtime configuration, and server hardware management. In our project, Render acts as the PaaS layer: we provide a declarative blueprint file (`render.yaml`) specifying Python 3.12, the build command (`pip install -r requirements.txt`), and the entry point (`uvicorn app.main:app`). Render automatically provisions the execution container, wires continuous integration from GitHub, handles SSL certificates, and exposes a secure HTTPS endpoint.

### Q2. How is deployment on Render triggered and managed?
**Answer:**  
Render connects directly to our GitHub repository (`ritzs04/jobtruth`). Whenever changes are committed and pushed to the `main` branch, a webhook triggers a new build pipeline. Render compiles dependencies, runs health checks against `/health`, and performs a zero-downtime blue/green deployment.

### Q3. Why use both PaaS (Render) and IaaS (EC2) in the same project?
**Answer:**  
To contrast modern cloud deployment paradigms:
- **PaaS (Render):** Optimized for developer velocity, automated zero-ops deployment, and built-in managed HTTPS.
- **IaaS (EC2):** Provides full root-level control over the OS, network configuration (Security Groups), custom container orchestration (Docker), and direct attachment of AWS IAM Instance Profiles without storing hardcoded static credentials.

---

## Category 2: Amazon EC2 & IaaS [Marking Criterion 2]

### Q4. How is the EC2 instance provisioned and configured without manual SSH?
**Answer:**  
The EC2 instance is provisioned automatically via `scripts/setup_aws.sh` using the AWS CLI and an EC2 UserData script. When the instance boots, the cloud-init agent executes `/tmp/userdata.sh`:
1. Installs Docker and Git via `dnf`.
2. Starts and enables the Docker daemon.
3. Clones `https://github.com/ritzs04/jobtruth.git`.
4. Builds the container image and runs it with `-p 80:8000`.

### Q5. What is IMDSv2 and why is `HttpPutResponseHopLimit=2` configured?
**Answer:**  
IMDSv2 (Instance Metadata Service Version 2) is a session-oriented security mechanism that protects against SSRF (Server-Side Request Forgery) attacks targeting cloud credentials. Setting `HttpPutResponseHopLimit=2` allows the container running inside Docker to traverse the Linux bridge network (hop 1) to reach the host metadata service (hop 2), enabling the application inside Docker to seamlessly obtain temporary IAM credentials without storing access keys on disk.

### Q6. How is network security enforced on your EC2 instance?
**Answer:**  
Through an AWS Security Group (`jobtruth-sg`):
- Port 80 (HTTP) is open to `0.0.0.0/0` so users can access the web application.
- Port 22 (SSH) is strictly locked down to the administrator's specific public IP (`/32 CIDR`), preventing automated brute-force attacks across the internet.

---

## Category 3: Amazon S3 Bucket Architecture [Marking Criterion 3]

### Q7. Explain your S3 bucket security configuration.
**Answer:**  
The S3 bucket is hardened with defense-in-depth:
1. **Block Public Access:** All four BPA flags are enabled, ensuring no object can ever be made public via ACL or policy.
2. **Server-Side Encryption:** SSE-S3 (`AES256`) is enforced by default.
3. **Bucket Policy:** Enforces TLS by explicitly denying any request where `aws:SecureTransport == false`.
4. **Versioning:** Enabled to maintain immutable revisions of uploaded offer letters.

### Q8. What is the purpose of S3 Lifecycle Rules in JobTruth?
**Answer:**  
We configured a lifecycle rule (`expire-offers`) with a 30-day expiration for both current and non-current versions under the `offers/` prefix. This enforces data minimization (GDPR/privacy compliance) and prevents unnecessary storage consumption, keeping usage well within AWS Free Tier limits.

### Q9. Why are S3 bucket names globally unique?
**Answer:**  
Because Amazon S3 forms a global namespace where every bucket is accessible via DNS-addressable endpoints (e.g., `<bucket-name>.s3.ap-south-1.amazonaws.com`). In our setup script, we generate unique names dynamically using timestamps (`jobtruth-$(date +%s)`).

---

## Category 4: Secure File Upload, Confidentiality & Integrity [Marking Criterion 4]

### Q10. How does JobTruth prevent malicious files disguised as PDFs?
**Answer:**  
JobTruth inspects the raw file **magic bytes** rather than trusting the user-supplied MIME type or file extension. The first 5 bytes must strictly match `%PDF-`. An executable (`.exe` starting with `MZ`) renamed to `.pdf` is immediately rejected with `HTTP 400 Bad Request`. Furthermore, an upload cap of 2 MB is strictly enforced (`HTTP 413 Payload Too Large`).

### Q11. How is data integrity guaranteed during upload to S3?
**Answer:**  
Before transmitting the file to S3, the server computes a cryptographic SHA-256 digest of the payload. During `s3.put_object()`, the checksum is supplied and stored in metadata (`ChecksumSHA256`). When requested, the hash can be re-verified against the source document to prove that no tampering occurred in transit or at rest.

### Q12. If the S3 bucket is private, how do authorized users view their offer letters?
**Answer:**  
Via **Pre-signed URLs** generated by the AWS SDK (`boto3.generate_presigned_url`). The URL contains a cryptographic signature using the server's IAM credentials and expires strictly after 300 seconds (5 minutes). Direct unauthenticated requests to the S3 URL return `HTTP 403 Forbidden`.

---

## Category 5: Risk Scoring Algorithm & Compliance [Marking Criterion 5]

### Q13. How does the fake job analysis engine calculate risk?
**Answer:**  
JobTruth uses a transparent, explainable heuristic scoring engine (0-100 scale):
- **High risk (+40):** Financial demands (UPI handles, upfront equipment fees, registration charges).
- **Medium risk (+25):** Lookalike company domains calculated via Levenshtein edit distance (e.g., `amaz0n-jobs.com` vs `amazon.com`).
- **Suspicious channels (+20):** Conducting interviews over Telegram, WhatsApp, or personal Google Meet without official correspondence.
- **Header anomalies (+30):** Missing or failing SPF, DKIM, or DMARC authentication records in raw email headers.

### Q14. What PII protections are implemented?
**Answer:**  
Regex redaction filters sanitize Indian phone numbers, personal email addresses, and 12-digit Aadhaar/national ID patterns before storing or displaying analysis previews, preventing unauthorized exposure of candidate personal data.

### Q15. How did you ensure this project stays 100% within the AWS Free Tier?
**Answer:**  
1. Configured AWS Budgets with a \$0.01 zero-spend threshold and \$1.00 monthly cap.
2. Utilized `t3.micro`/`t2.micro` instances (under the 750 free monthly hours).
3. Configured 30-day lifecycle auto-deletion on S3.
4. Created an automated teardown script (`scripts/teardown.sh`) that terminates the EC2 instance, deletes the security group, purges all object versions, and deletes the S3 bucket and IAM roles in one command after evaluation.
