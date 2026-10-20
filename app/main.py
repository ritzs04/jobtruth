import socket
import json
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, status, Depends
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import storage, auth, db, verify, security, batch, pdf
from app.pii import redact
from app.rules import analyze, analyze_headers
from app.i18n import get_text, get_supported_languages

app = FastAPI(title="JobTruth", description="Fake job and internship offer detector")
STATIC = Path(__file__).resolve().parent.parent / "public"


class TextReq(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


class HeaderReq(BaseModel):
    raw_headers: str = Field(min_length=1, max_length=20000)


class ScamReportReq(BaseModel):
    domain: str = Field(min_length=1, max_length=255)
    company_name: str = Field(min_length=1, max_length=255)
    reason: str = Field(min_length=1, max_length=1000)


class CompanyLookupReq(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)


class DomainCheckReq(BaseModel):
    domain: str = Field(min_length=1, max_length=255)


class LanguageReq(BaseModel):
    lang: str = Field(default="en")


class ComparisonReq(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    analyses: list = Field(min_items=2, max_items=3)


@app.post("/register")
def register(req: auth.UserRegister):
    if len(req.password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 6 characters")
    hashed = auth.hash_password(req.password)
    user_id = db.create_user(req.email, hashed)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    token = auth.create_access_token(req.email)
    return {"access_token": token, "token_type": "bearer", "email": req.email}


@app.post("/login")
def login(req: auth.UserLogin):
    user = db.get_user_by_email(req.email)
    if not user or not auth.verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = auth.create_access_token(req.email)
    return {"access_token": token, "token_type": "bearer", "email": req.email}


@app.post("/analyze")
def run_analyze(req: TextReq):
    result = analyze(req.text)
    result["redacted_preview"] = redact(req.text)[:300]
    result["served_by"] = socket.gethostname()
    return result


@app.post("/analyze-save")
def analyze_and_save(req: TextReq, user: dict = Depends(auth.get_current_user)):
    result = analyze(req.text)
    result["redacted_preview"] = redact(req.text)[:300]
    result["served_by"] = socket.gethostname()
    db.save_analysis(user["id"], req.text, result["trust_score"], result["label"], json.dumps(result["flags"]))
    return result


@app.get("/my-analyses")
def my_analyses(user: dict = Depends(auth.get_current_user)):
    return db.get_user_analyses(user["id"])


@app.post("/headers")
def run_headers(req: HeaderReq):
    result = analyze_headers(req.raw_headers)
    result["served_by"] = socket.gethostname()
    return result


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    data = await file.read(storage.MAX_BYTES + 1)
    return storage.secure_upload(data)


@app.get("/objects")
def objects():
    return storage.list_objects()


@app.get("/versions")
def versions():
    return storage.list_versions()


@app.delete("/objects/{key:path}")
def remove(key: str):
    return storage.delete_object(key)


@app.get("/health")
def health():
    return {"status": "ok", "served_by": socket.gethostname()}


@app.post("/report-scam")
def report_scam(req: ScamReportReq, user: dict = Depends(auth.get_current_user)):
    db.report_scam(req.domain, req.company_name, req.reason, user["email"])
    return {"status": "reported", "message": "Thank you for reporting this scam"}


@app.get("/scams")
def get_scams():
    return db.get_top_scams(50)


@app.post("/verify-company")
def verify_company(req: CompanyLookupReq):
    result = verify.verify_company(req.company_name)
    scam_count = db.get_scam_count(req.company_name)
    result["scam_reports"] = scam_count
    return result


@app.post("/benchmark-salary")
def benchmark_salary(req: TextReq):
    result = verify.benchmark_salary(req.text)
    return result


@app.post("/check-domain-age")
def check_domain_age(req: DomainCheckReq):
    result = security.check_domain_age(req.domain)
    return result


@app.post("/check-breach")
def check_breach(req: TextReq):
    # Extract email from text
    import re
    emails = re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", req.text)
    if not emails:
        return {"breached": False, "breaches": [], "flag": None}
    result = security.check_breach_database(emails[0])
    return result


@app.post("/batch-analyze")
async def batch_analyze_csv(file: UploadFile = File(...), user: dict = Depends(auth.get_current_user)):
    content = await file.read()
    try:
        rows = batch.parse_csv(content)
        results = batch.batch_analyze(rows)
        return {"total": len(rows), "results": results}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/languages")
def get_languages():
    return {"supported": get_supported_languages()}


@app.get("/translate/{key}")
def translate(key: str, lang: str = "en"):
    text = get_text(key, lang)
    return {"key": key, "lang": lang, "text": text}


@app.post("/export-pdf")
def export_pdf(req: TextReq):
    result = analyze(req.text)
    pdf_bytes = pdf.generate_pdf_report(result, req.text)
    return {"pdf_base64": pdf_bytes.hex(), "filename": "jobtruth_report.pdf"}


@app.post("/save-comparison")
def save_comparison(req: ComparisonReq, user: dict = Depends(auth.get_current_user)):
    comparison_id = db.save_comparison(user["id"], req.name, json.dumps(req.analyses))
    return {"id": comparison_id, "name": req.name, "message": "Comparison saved"}


@app.get("/my-comparisons")
def my_comparisons(user: dict = Depends(auth.get_current_user)):
    return db.get_user_comparisons(user["id"])


@app.get("/comparison/{comparison_id}")
def get_comparison(comparison_id: int, user: dict = Depends(auth.get_current_user)):
    comp = db.get_comparison(comparison_id)
    if not comp or comp["user_id"] != user["id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comparison not found")
    comp["analyses"] = json.loads(comp["analyses_json"])
    return comp


# keep last: the static mount captures every unmatched path
app.mount("/", StaticFiles(directory=STATIC, html=True), name="public")

