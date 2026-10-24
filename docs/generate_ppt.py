import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

PRIMARY = RGBColor(24, 43, 73)     # Deep navy
ACCENT = RGBColor(220, 53, 69)     # Crimson red
TEXT = RGBColor(40, 40, 40)        # Dark grey
BG_LIGHT = RGBColor(245, 247, 250)

slides_data = [
    {
        'title': 'JobTruth: Fake Job & Internship Offer Detector',
        'subtitle': 'Cloud Computing CAT II Project\nAuthor: Ritz (PG MCA)\nGitHub: github.com/ritzs04/jobtruth\nDeployment: Render (PaaS) & AWS EC2 (IaaS) + S3 (Hardened Storage)',
        'bullets': []
    },
    {
        'title': '1. Problem Statement & Motivation',
        'subtitle': 'Why JobTruth?',
        'bullets': [
            'Rampant surge in fraudulent job/internship offers targeting college graduates and students.',
            'Common Fraud Vectors: Upfront registration/security deposit fees requested via UPI handles.',
            'Deceptive Tactics: Typo-squatted lookalike domains (e.g., micros0ft-careers.com) and unauthorized Telegram/WhatsApp HR interviews.',
            'Email Forgery: Spoofed email sender addresses failing SPF, DKIM, and DMARC verification.',
            'Our Solution: A centralized, explainable cloud-native risk engine with hardened S3 evidentiary storage.'
        ]
    },
    {
        'title': '2. High-Level Cloud Architecture',
        'subtitle': 'Hybrid Cloud Deployment Strategy',
        'bullets': [
            'Dual Hosting Model: Contrasting Public PaaS (Render) vs. Public IaaS (Amazon EC2).',
            'Application Layer: FastAPI (Python 3.12) ASGI microservice with sub-second response times.',
            'Storage Layer: Amazon S3 private bucket with AES-256 server-side encryption and versioning.',
            'Security Posture: Zero permanent secrets on EC2 (IMDSv2 instance role), least-privilege IAM policies, TLS-only bucket policies.',
            'Continuous Integration: GitHub Actions pipeline automatically validating unit and security tests on every commit.'
        ]
    },
    {
        'title': '3. Public PaaS Deployment (Render) — Mark 1',
        'subtitle': 'Infrastructure-as-Code via Blueprint',
        'bullets': [
            'Automated Blueprint: Declared in render.yaml with Python 3.12 runtime and uvicorn command.',
            'Zero-Ops CI/CD: Automated build and deployment directly linked to GitHub repository main branch.',
            'Health Check Probes: Automated health monitoring at /health endpoint ensuring zero-downtime rolling deploys.',
            'Security Scoping: Render communicates with AWS S3 using restricted IAM user keys limited only to offers/* prefix.'
        ]
    },
    {
        'title': '4. Amazon EC2 IaaS Deployment — Mark 2',
        'subtitle': 'Root-Level Control & Containerization',
        'bullets': [
            'Instance Configuration: Amazon Linux 2023 on t2.micro/t3.micro (AWS Free Tier eligible).',
            'Automated Cloud-Init Provisioning: UserData script installs Docker, clones repository, builds image, and launches container on port 80.',
            'IMDSv2 Hardening: Instance Metadata Service v2 with HttpPutResponseHopLimit=2 allows Docker container to securely assume the EC2 IAM role.',
            'Network Defense: Custom Security Group (jobtruth-sg) restricts inbound port 80 to web traffic and port 22 to administrator IP only.'
        ]
    },
    {
        'title': '5. Amazon S3 Bucket Architecture — Mark 3',
        'subtitle': 'Confidentiality, Versioning & Lifecycle',
        'bullets': [
            'Block Public Access: All 4 public access blocks strictly enabled (zero public leaks).',
            'Default Encryption: Server-Side Encryption (SSE-S3) with AES-256 standard.',
            'Object Versioning: Enabled to preserve original uploaded documents against tampering or accidental deletion.',
            'Lifecycle Rules: Automated 30-day expiration rule (expire-offers) cleans current and non-current versions to stay free tier compliant.',
            'Transport Security: Explicit S3 bucket policy denying all non-HTTPS (aws:SecureTransport: false) connections.'
        ]
    },
    {
        'title': '6. Secure File Upload & Integrity — Mark 4',
        'subtitle': 'Defense-in-Depth Payload Security',
        'bullets': [
            'Magic-Byte Validation: Inspects first 5 bytes (%PDF-) rejecting disguised executables (.exe) or scripts.',
            'Payload Ceiling: Enforces strict 2 MB maximum upload size returning HTTP 413 on violations.',
            'Integrity Verification: Client/server SHA-256 digest verified and pinned to S3 object metadata.',
            'Time-Limited Access: Download links generated as 5-minute pre-signed URLs; direct bucket access returns HTTP 403 Forbidden.',
            'PII Redaction: Sanitizes phone numbers, personal emails, and national identity numbers before display.'
        ]
    },
    {
        'title': '7. Verification & Automated Test Results',
        'subtitle': 'Comprehensive Security Test Suite',
        'bullets': [
            'Unit Tests: 16/16 pytest test cases passing in 2.5s covering rules, PII redaction, and endpoints.',
            'Malicious Executable Renamed .pdf: HTTP 400 Bad Request (Blocked).',
            'Oversized 3 MB Payload: HTTP 413 Payload Too Large (Blocked).',
            'Valid PDF Upload: HTTP 200 OK + SHA-256 integrity verified.',
            'Direct S3 / Insecure HTTP URL: HTTP 403 Forbidden (Blocked).',
            'Pre-signed URL after 5 minutes: HTTP 403 AccessDenied (Expired).'
        ]
    },
    {
        'title': '8. Cost Optimization & Safety Guardrails',
        'subtitle': 'Strict 100% Free Tier Compliance',
        'bullets': [
            'EC2: 750 monthly free hours on t2.micro/t3.micro.',
            'S3: Well below 5 GB Standard Storage limit and 2,000 PUT requests.',
            'Render: Free web service tier (0.1 CPU, 512 MB RAM).',
            'AWS Budgets: Proactively configured with .01 zero-spend alert and .00 safety alert.',
            'Teardown Automation: scripts/teardown.sh removes all instances, security groups, and buckets in one command.'
        ]
    },
    {
        'title': '9. Conclusion & Key Takeaways',
        'subtitle': 'CAT II Cloud Computing Evaluation Summary',
        'bullets': [
            'Successfully implemented and contrasted both PaaS (Render) and IaaS (Amazon EC2).',
            'Enforced production-grade security: IMDSv2, least privilege IAM, S3 hardening, and magic-byte checks.',
            'Delivered complete documentation, automated CI/CD, and transparent viva defense.',
            'Thank You! Open for Viva Questions.'
        ]
    }
]

blank_slide_layout = prs.slide_layouts[6]

for i, data in enumerate(slides_data):
    slide = prs.slides.add_slide(blank_slide_layout)
    
    # Title box
    txBox = slide.shapes.add_textbox(Inches(0.8), Inches(0.6), Inches(11.7), Inches(1.2))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = data['title']
    p.font.size = Pt(28 if i > 0 else 34)
    p.font.bold = True
    p.font.color.rgb = PRIMARY
    
    # Subtitle
    if data['subtitle']:
        p2 = tf.add_paragraph()
        p2.text = data['subtitle']
        p2.font.size = Pt(14 if i > 0 else 18)
        p2.font.color.rgb = ACCENT if i == 0 else TEXT
    
    # Bullets
    if data['bullets']:
        bodyBox = slide.shapes.add_textbox(Inches(0.8), Inches(2.2), Inches(11.7), Inches(4.8))
        btf = bodyBox.text_frame
        btf.word_wrap = True
        for b_idx, bullet in enumerate(data['bullets']):
            bp = btf.paragraphs[0] if b_idx == 0 else btf.add_paragraph()
            bp.text = f'•  {bullet}'
            bp.font.size = Pt(17)
            bp.font.color.rgb = TEXT
            bp.space_after = Pt(14)

out_path = r'D:\PROJECTS(CAT 2)\Cloud\jobtruth\docs\JobTruth_Presentation.pptx'
prs.save(out_path)
print('PPTX generated successfully at:', out_path)
