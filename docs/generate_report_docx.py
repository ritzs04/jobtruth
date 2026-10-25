from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

doc = Document()

# ── Page margins ──────────────────────────────────────────────────────────────
for section in doc.sections:
    section.top_margin    = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin   = Cm(3.0)
    section.right_margin  = Cm(2.5)

BLACK = RGBColor(0, 0, 0)
TNR   = "Times New Roman"

def para(text, size=12, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT, space_before=0, space_after=6):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after  = Pt(space_after)
    run = p.add_run(text)
    run.font.name  = TNR
    run.font.size  = Pt(size)
    run.font.bold  = bold
    run.font.color.rgb = BLACK
    return p

def heading1(text):
    return para(text, size=16, bold=True, space_before=14, space_after=6)

def heading2(text):
    return para(text, size=14, bold=True, space_before=10, space_after=4)

def body(text, indent=False):
    p = para(text, size=12, bold=False, space_before=0, space_after=4)
    if indent:
        p.paragraph_format.left_indent = Pt(18)
    return p

def bullet(text):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(text)
    run.font.name  = TNR
    run.font.size  = Pt(12)
    run.font.color.rgb = BLACK
    return p

def add_table(headers, rows, col_widths=None):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    # header row
    for i, h in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(h)
        run.font.name  = TNR
        run.font.size  = Pt(11)
        run.font.bold  = True
        run.font.color.rgb = BLACK
        # grey fill
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"),   "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"),  "D9D9D9")
        tcPr.append(shd)
    # data rows
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            cell = t.rows[r + 1].cells[c]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            run = p.add_run(str(val))
            run.font.name  = TNR
            run.font.size  = Pt(11)
            run.font.color.rgb = BLACK
    if col_widths:
        for r in t.rows:
            for i, w in enumerate(col_widths):
                r.cells[i].width = Inches(w)
    doc.add_paragraph()
    return t

def caption(text):
    p = para(f"Figure: {text}", size=11, bold=False,
             align=WD_ALIGN_PARAGRAPH.CENTER, space_before=2, space_after=8)
    p.runs[0].italic = True
    return p

def add_architecture_diagram():
    """Draw the cloud architecture as a formatted monospace block inside a table."""
    arch = [
        "                        [ User / Browser ]",
        "                           |           |",
        "        +------------------+           +-------------------+",
        "        | (Public HTTPS)                   (Public HTTP/80) |",
        "        v                                                   v",
        "+---------------------+                    +-------------------------+",
        "| Public PaaS (Render)|                    |   Amazon EC2 (IaaS)     |",
        "| - Python 3.12 Web   |                    |   - Amazon Linux 2023   |",
        "| - Render Blueprint  |                    |   - Docker Container    |",
        "| - Limited IAM User  |                    |   - IMDSv2 + Role       |",
        "+----------+----------+                    +-----------+-------------+",
        "           |                                           |",
        "           | IAM Keys (s3:PutObject, s3:GetObject)     | EC2 Instance Profile",
        "           +---------------------+  +------------------+",
        "                                 |  |",
        "                                 v  v",
        "                    +--------------------------------+",
        "                    |       Amazon S3 Bucket         |",
        "                    |  - Private (Block Public)      |",
        "                    |  - AES-256 Encryption (SSE-S3) |",
        "                    |  - Object Versioning Enabled   |",
        "                    |  - HTTPS/TLS Only Policy       |",
        "                    |  - 30-Day Lifecycle Rule        |",
        "                    |  - SHA-256 Checksum Verify     |",
        "                    +--------------------------------+",
    ]
    t = doc.add_table(rows=1, cols=1)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = t.rows[0].cells[0]
    # light blue fill
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  "EBF3FB")
    tcPr.append(shd)
    first = True
    for line in arch:
        if first:
            p = cell.paragraphs[0]
            first = False
        else:
            p = cell.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after  = Pt(0)
        run = p.add_run(line)
        run.font.name  = "Courier New"
        run.font.size  = Pt(8)
        run.font.color.rgb = BLACK
    doc.add_paragraph()

def add_flow_diagram():
    """Request flow as a simple arrow table."""
    steps = [
        ("1", "User Browser", "Submits offer text / email headers / PDF file via HTTPS"),
        ("2", "Render PaaS / EC2 IaaS", "FastAPI receives request, validates input (magic byte, size)"),
        ("3", "Rules Engine", "Scores offer text; checks SPF/DKIM/DMARC from headers"),
        ("4", "Amazon S3", "PDF uploaded with SHA-256 checksum; SSE-S3 encryption applied"),
        ("5", "S3 Integrity Check", "head_object with ChecksumMode=ENABLED verifies hash"),
        ("6", "API Response", "JSON returned: trust score, flags, encryption status, pre-signed URL"),
        ("7", "User Browser", "Displays animated ring gauge, verdict, flag list, redacted preview"),
    ]
    headers = ["Step", "Component", "Action"]
    rows = steps
    add_table(headers, rows, col_widths=[0.5, 1.8, 4.0])

# ══════════════════════════════════════════════════════════════════════════════
#  COVER PAGE
# ══════════════════════════════════════════════════════════════════════════════
para("", size=12)
para("MCA Cloud Computing — CAT II Project Report", size=14, bold=True,
     align=WD_ALIGN_PARAGRAPH.CENTER, space_before=20)
para("", size=12)
para("JobTruth", size=28, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=10)
para("Cloud-Native Fake Job & Internship Offer Detector", size=16, bold=True,
     align=WD_ALIGN_PARAGRAPH.CENTER, space_before=6)
para("", size=12)
para("", size=12)

info = [
    ("Author",      "Ritz"),
    ("GitHub",      "github.com/ritzs04/jobtruth"),
    ("AWS Region",  "Asia Pacific (Mumbai) — ap-south-1"),
    ("Deployment",  "Render PaaS  +  Amazon EC2 (IaaS)  +  Amazon S3"),
]
for label, value in info:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(4)
    r1 = p.add_run(f"{label}: ")
    r1.font.name = TNR; r1.font.size = Pt(12); r1.font.bold = True; r1.font.color.rgb = BLACK
    r2 = p.add_run(value)
    r2.font.name = TNR; r2.font.size = Pt(12); r2.font.bold = False; r2.font.color.rgb = BLACK

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════════════
#  1. TITLE & ABSTRACT
# ══════════════════════════════════════════════════════════════════════════════
heading1("1.  Title & Abstract")
heading2("Title")
body("JobTruth — Cloud-Native Fake Job & Internship Offer Detector")
heading2("Abstract")
body(
    "Online job scams and fraudulent internship offers have surged dramatically, preying especially "
    "on students and fresh graduates. Scammers impersonate reputable brands, demand upfront "
    "registration fees or security deposits via UPI/cryptocurrency, and utilise spoofed lookalike "
    "domains (e.g., micros0ft-careers.com)."
)
body(
    "JobTruth is an enterprise-grade cloud-native security utility engineered to detect fraudulent "
    "job offers using rule-based explainable risk scoring, SPF/DKIM/DMARC email header verification, "
    "and confidential document analysis. The solution implements a multi-cloud hybrid architecture "
    "spanning PaaS (Render) and IaaS (Amazon EC2) coupled with encrypted, tamper-proof object "
    "storage on Amazon S3."
)

# ══════════════════════════════════════════════════════════════════════════════
#  2. PROBLEM STATEMENT
# ══════════════════════════════════════════════════════════════════════════════
heading1("2.  Problem Statement")
body(
    "Fresh graduates and students are the primary targets of fake job and internship scams in India. "
    "These scams share common patterns:"
)
for b in [
    "Financial solicitation: Demands for registration fees, security deposits, or training charges via UPI or bank transfer before joining.",
    "Lookalike domains: Spoofed domains such as infosys-careers.xyz or tcs-hr.online that impersonate legitimate companies.",
    "Unverifiable senders: Emails sent from Gmail/Yahoo accounts claiming to be from multinational corporations.",
    "Pressure tactics: Urgency language (\"only today\", \"limited seats\") to prevent the victim from verifying the offer.",
    "No interview process: Promises of direct selection without any technical or HR round.",
]:
    bullet(b)
body(
    "Existing solutions either require technical expertise or provide only a binary safe/unsafe verdict "
    "without explanation. JobTruth solves this by providing an explainable, scored risk analysis that "
    "shows exactly which signals were detected and why they matter."
)

# ══════════════════════════════════════════════════════════════════════════════
#  3. CLOUD ARCHITECTURE
# ══════════════════════════════════════════════════════════════════════════════
heading1("3.  Cloud Architecture & Infrastructure Design")
body(
    "The architecture adheres strictly to the AWS Well-Architected Framework pillars: Security, "
    "Cost Optimisation, Reliability, and Operational Excellence."
)

heading2("3.1  Architecture Diagram")
add_architecture_diagram()
caption("Multi-Cloud Hybrid Architecture — Render PaaS + Amazon EC2 + Amazon S3")

heading2("3.2  Request Flow Diagram")
add_flow_diagram()
caption("End-to-End Request Flow from User Browser to Amazon S3")

heading2("3.3  Layer Descriptions")
add_table(
    ["Layer", "Service", "Role"],
    [
        ["PaaS",           "Render",                  "Public-facing FastAPI web app, auto-deployed from GitHub"],
        ["IaaS",           "Amazon EC2 (t2.micro)",   "Docker-hosted replica, IMDSv2, no stored credentials"],
        ["Object Storage", "Amazon S3",               "Encrypted, versioned, private offer letter storage"],
        ["CI/CD",          "GitHub Actions",          "Automated lint and test on every push"],
    ],
    col_widths=[1.2, 1.8, 3.8],
)

heading2("3.4  Mapping to Evaluation Criteria (40 Marks)")
add_table(
    ["Criterion", "Marks", "Implementation"],
    [
        ["Public PaaS (Render)",          "8", "Automated build and continuous deployment via render.yaml Blueprint connected to GitHub."],
        ["Amazon EC2 (IaaS)",             "8", "Amazon Linux 2023, automated userdata Docker build, attached IAM instance profile, custom Security Group."],
        ["Amazon S3 Bucket Management",   "8", "Block Public Access, SSE-S3 encryption, Object Versioning, 30-day lifecycle expiration."],
        ["Secure File Upload & Integrity","8", "Magic-byte verification, 2 MB ceiling, SHA-256 checksum, 5-minute pre-signed download URLs."],
        ["Docs, Presentation & Viva",     "8", "Comprehensive technical documentation, architecture slide deck, viva defence preparation."],
    ],
    col_widths=[2.2, 0.7, 3.9],
)

# ══════════════════════════════════════════════════════════════════════════════
#  4. FEATURES & SCREENSHOTS
# ══════════════════════════════════════════════════════════════════════════════
heading1("4.  All Features — Screenshots as Evidence")
body(
    "The following table summarises all 20 features of the deployed application. "
    "Each entry lists the API endpoint exercised and the expected behaviour verified."
)

features = [
    ["1",  "Landing Page & Hero Section",                    "GET /",          "Homepage with annotated scam card (score 0/100, High Risk) and CTA buttons."],
    ["2",  "Offer Analyzer — High Risk",                     "POST /analyze",  "Score ≤ 39, label High Risk, all penalty flags listed with reasons."],
    ["3",  "Offer Analyzer — Looks Safe",                    "POST /analyze",  "Score ≥ 70, label Looks Safe, positive COMPANY_EMAIL flag."],
    ["4",  "Offer Analyzer — Suspicious",                    "POST /analyze",  "Score 40–69, label Suspicious, amber colour."],
    ["5",  "Email Header Verification — Failed SPF/DKIM/DMARC","POST /headers","Verdict Failed checks, three red chips."],
    ["6",  "Email Header Verification — Authenticated",      "POST /headers",  "Verdict Authenticated, three green chips."],
    ["7",  "Secure File Upload — Success",                   "POST /upload",   "HTTP 200, AES256 encryption, integrity_verified=true, SHA-256, version ID, pre-signed URL."],
    ["8",  "File Upload Rejected — Wrong Type",              "POST /upload",   "HTTP 400 — Only PDF, PNG or JPG files are allowed (magic-byte check)."],
    ["9",  "File Upload Rejected — Oversized",               "POST /upload",   "HTTP 413 — File too large (max 2 MB)."],
    ["10", "Stored Files List",                              "GET /objects",   "Table of all objects in offers/ prefix with key, size, timestamp, delete button."],
    ["11", "Object Versioning List",                         "GET /versions",  "All S3 versions and delete markers proving versioning is active."],
    ["12", "Health Check Endpoint",                          "GET /health",    "JSON {status: ok, served_by: <hostname>} identifying Render or EC2 host."],
    ["13", "PaaS Deployment on Render",                      "Dashboard",      "Service live, deployed from GitHub via render.yaml, health check passing."],
    ["14", "IaaS Deployment on Amazon EC2",                  "AWS Console",    "Instance Running, Amazon Linux 2023, IAM role jobtruth-ec2-role attached."],
    ["15", "Amazon S3 Bucket Configuration",                 "AWS Console",    "Block Public Access ON, SSE-S3, Versioning Enabled, lifecycle rule expire-offers."],
    ["16", "S3 Bucket Policy — HTTPS-Only",                  "AWS Console",    "Deny policy on aws:SecureTransport=false enforcing TLS for all S3 API calls."],
    ["17", "IAM Least-Privilege Policy",                     "AWS Console",    "jobtruth-render-policy: only s3:PutObject + s3:GetObject on offers/* prefix."],
    ["18", "GitHub Actions CI Pipeline",                     "GitHub",         "Lint (flake8) and unit tests (pytest) both green on every push to main."],
    ["19", "PII Redaction in Analysis Preview",              "POST /analyze",  "Phone, email, Aadhaar-pattern replaced with [REDACTED] before UI render."],
    ["20", "Dark Mode Support",                              "Browser",        "Full dark theme via prefers-color-scheme: dark CSS variable theming."],
]
add_table(
    ["#", "Feature", "Endpoint", "Expected Behaviour"],
    features,
    col_widths=[0.3, 1.7, 1.2, 3.1],
)

# ══════════════════════════════════════════════════════════════════════════════
#  5. SECURITY DESIGN
# ══════════════════════════════════════════════════════════════════════════════
heading1("5.  Security Design")
add_table(
    ["Control", "Implementation", "Standard / Rationale"],
    [
        ["Encryption at Rest",       "SSE-S3 (AES-256) on every S3 object",                          "AWS default encryption; protects stored offer letters"],
        ["Encryption in Transit",    "S3 bucket policy denies aws:SecureTransport=false",             "Enforces HTTPS/TLS for all S3 API calls"],
        ["Block Public Access",      "All four S3 Block Public Access settings enabled",              "Prevents accidental public exposure of offer letters"],
        ["Object Versioning",        "S3 versioning enabled on bucket",                               "Protects against accidental overwrite and malicious deletion"],
        ["Lifecycle Management",     "30-day expiration rule on offers/*",                            "Storage minimisation; reduces attack surface over time"],
        ["Integrity Verification",   "SHA-256 checksum verified via ChecksumMode=ENABLED",            "Detects tampering or corruption in transit/at rest"],
        ["Magic Byte Validation",    "First 4 bytes checked: %PDF, PNG, JPEG signatures",             "Prevents disguised executables; filename is not trusted"],
        ["File Size Limit",          "2 MB hard ceiling enforced before S3 write",                    "Prevents DoS via large payload; enforced server-side"],
        ["Pre-signed URL Expiry",    "ExpiresIn=300 (5 minutes)",                                     "Limits window for credential-free access to stored files"],
        ["Least-Privilege IAM",      "Render IAM user: only s3:PutObject + s3:GetObject on offers/*","Principle of least privilege; no delete or list at root"],
        ["IMDSv2 on EC2",            "HttpTokens=required, HttpPutResponseHopLimit=2",                "Prevents SSRF-based metadata credential theft"],
        ["No Stored Credentials",    "EC2 uses attached instance profile role (STS temp credentials)","Eliminates long-lived key exposure on the instance"],
        ["JWT Authentication",       "HS256 JWT, 7-day expiry, bcrypt password hashing",              "Stateless auth; passwords never stored in plaintext"],
        ["PII Redaction",            "Phone, email, Aadhaar-pattern stripped before preview render",  "Prevents accidental PII display in the UI"],
        ["Security Group",           "Ingress: TCP 80 (public), TCP 22 (admin IP only)",              "Minimises EC2 attack surface"],
        ["HTTPS on PaaS",            "Render provides automatic TLS certificate",                     "All browser traffic encrypted end-to-end"],
        ["AWS Budget Alert",         "$0.01 zero-spend + $1.00 alert threshold",                      "Detects unexpected resource usage immediately"],
    ],
    col_widths=[1.6, 2.4, 2.7],
)

# ══════════════════════════════════════════════════════════════════════════════
#  6. VERIFICATION & SECURITY TEST RESULTS
# ══════════════════════════════════════════════════════════════════════════════
heading1("6.  Verification and Security Test Results")
body("The suite scripts/security_tests.sh verifies defensive controls against malicious attacks:")
add_table(
    ["Test", "Simulated Attack", "Expected Result", "Status"],
    [
        ["1", "Executable (MZ PE header) renamed as .pdf",       "HTTP 400 Bad Request",          "PASS"],
        ["2", "3 MB oversized payload submitted to /upload",     "HTTP 413 Payload Too Large",    "PASS"],
        ["3", "Legitimate PDF with SHA-256 hash",                "HTTP 200 OK (integrity verified)","PASS"],
        ["4", "Direct unauthenticated S3 object URL access",     "HTTP 403 Forbidden",            "PASS"],
        ["5", "Insecure HTTP request directly to S3 endpoint",   "HTTP 403 Forbidden (TLS Policy)","PASS"],
        ["6", "Accessing pre-signed URL after 300 seconds",      "HTTP 403 AccessDenied",         "PASS"],
    ],
    col_widths=[0.4, 2.5, 2.2, 0.7],
)

# ══════════════════════════════════════════════════════════════════════════════
#  7. COST OPTIMISATION
# ══════════════════════════════════════════════════════════════════════════════
heading1("7.  Cost Optimisation & Free Tier Compliance")
for b in [
    "EC2: Under 750 free hours of t2.micro/t3.micro per month.",
    "S3: Under 5 GB Standard Storage and fewer than 2,000 PUT requests.",
    "Render: Free web service plan (0.1 CPU, 512 MB RAM).",
    "Guardrails: AWS Budget configured with $0.01 zero-spend threshold and $1.00 alert trigger.",
]:
    bullet(b)

# ══════════════════════════════════════════════════════════════════════════════
#  8. CONCLUSION
# ══════════════════════════════════════════════════════════════════════════════
heading1("8.  Conclusion")
body(
    "JobTruth successfully demonstrates a resilient cloud architecture that integrates PaaS agility "
    "with IaaS control, anchored by industry-standard cloud security practices on Amazon Web Services."
)
body("The project delivers:")
for b in [
    "Explainable risk scoring — every flag shows its impact and reason, not just a verdict.",
    "Multi-layer cloud security — encryption at rest and in transit, integrity verification, least-privilege IAM, IMDSv2, and pre-signed URL expiry all working together.",
    "Hybrid deployment — the same Docker image runs on both Render (PaaS) and EC2 (IaaS), with the served_by field in every API response proving which host answered.",
    "Zero-cost operation — the entire stack runs within AWS Free Tier and Render's free plan, with budget alerts as a safety net.",
    "Production-grade practices — CI/CD via GitHub Actions, PII redaction, magic-byte file validation, and automated lifecycle management demonstrate readiness beyond a student prototype.",
]:
    bullet(b)
body(
    "The architecture is extensible: adding an RDS database for user history, an SQS queue for batch "
    "analysis, or a CloudFront distribution for global CDN would each slot in without redesigning the core."
)

# ══════════════════════════════════════════════════════════════════════════════
#  Save
# ══════════════════════════════════════════════════════════════════════════════
out = "JobTruth_Project_Report.docx"
doc.save(out)
print(f"Saved: {out}")
