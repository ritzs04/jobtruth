import socket
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import storage, db
from app.auth import UserRegister, UserLogin, Token, hash_password, verify_password, create_access_token
from app.pii import redact
from app.rules import analyze, analyze_headers

app = FastAPI(title="JobTruth", description="Fake job and internship offer detector")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
STATIC = Path(__file__).resolve().parent.parent / "public"

KNOWN_COMPANIES = {
    # IT / Tech (Indian)
    "infosys","tcs","tata consultancy services","wipro","hcl","hcl technologies",
    "tech mahindra","mphasis","hexaware","mindtree","l&t infotech","ltimindtree",
    "persistent systems","niit technologies","zensar","cyient","mastech",
    "kpit","sonata software","happiest minds","coforge","birlasoft",
    # Global tech
    "accenture","ibm","cognizant","capgemini","deloitte","pwc","kpmg","ey",
    "amazon","google","microsoft","oracle","sap","salesforce","adobe",
    "meta","apple","intel","qualcomm","cisco","hp","dell","lenovo",
    "zoho","freshworks","chargebee","browserstack","postman","hasura",
    "razorpay","instamojo","cashfree","payu",
    # Indian startups / unicorns
    "flipkart","zomato","swiggy","paytm","byju","byjus","ola","uber",
    "meesho","zerodha","cred","dream11","nykaa","policybazaar",
    "phonepe","groww","upstox","slice","unacademy","vedantu","lenskart",
    "sharechat","moj","dailyhunt","verse","spinny","cars24","droom",
    "urban company","urbanclap","dunzo","rapido","porter","shiprocket",
    "delhivery","ecom express","xpressbees","shadowfax",
    # Banking / Finance
    "reliance","hdfc","hdfc bank","icici","icici bank","sbi","state bank of india",
    "axis bank","kotak","kotak mahindra","yes bank","indusind","bajaj finance",
    "bajaj finserv","lic","npci","rbl bank","federal bank","idfc first bank",
    "bandhan bank","au small finance bank","paytm payments bank",
    # Telecom / Infra
    "airtel","bharti airtel","jio","reliance jio","vodafone","bsnl","mtnl",
    # Conglomerates / Manufacturing
    "tata","mahindra","l&t","larsen and toubro","bajaj","hero","honda",
    "maruti","maruti suzuki","hyundai","tvs","ashok leyland","bhel","ongc",
    "ioc","indian oil","ntpc","power grid","gail","adani","jsw","vedanta",
    # Pharma / FMCG
    "sun pharma","dr reddy","cipla","lupin","hul","hindustan unilever",
    "itc","nestle","dabur","marico","godrej","britannia","amul",
    "zydus","torrent pharma","alkem","mankind pharma",
    # E-commerce / Retail
    "myntra","snapdeal","bigbasket","grofers","blinkit","jiomart","amazon india",
    "tata cliq","ajio","reliance retail","dmart","avenue supermarts",
    # Media / Entertainment
    "hotstar","disney hotstar","netflix","sony liv","zee5","jio cinema",
    "times of india","ndtv","republic","india today",
    # Education
    "byju","byjus","unacademy","vedantu","toppr","testbook","gradeup",
    "great learning","upgrad","simplilearn","coursera","udemy",
}

SUSPICIOUS_PATTERNS = [
    "career","careers","recruit","recruitment","hr","hiring","jobs","job",
    "placement","staffing","consultant","consultancy","pvt","private","limited",
    "solution","solutions","service","services","global","india","infotech",
    "tech","technologies","group","associate","associates","enterprise","enterprises",
]


class TextReq(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


class HeaderReq(BaseModel):
    raw_headers: str = Field(min_length=1, max_length=20000)


@app.post("/analyze")
def run_analyze(req: TextReq):
    result = analyze(req.text)
    result["redacted_preview"] = redact(req.text)[:300]
    result["served_by"] = socket.gethostname()
    return result


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


@app.post("/auth/register", response_model=Token)
def register(req: UserRegister):
    from fastapi import HTTPException
    pw_hash = hash_password(req.password)
    user_id = db.create_user(req.email, pw_hash)
    if not user_id:
        raise HTTPException(400, "Email already registered")
    token = create_access_token(req.email)
    return {"access_token": token, "token_type": "bearer"}


@app.post("/auth/login", response_model=Token)
def login(req: UserLogin):
    from fastapi import HTTPException
    user = db.get_user_by_email(req.email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    token = create_access_token(req.email)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/stats")
def stats():
    import sqlite3
    from app.db import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM analyses")
    analyses = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM scam_reports")
    reports = c.fetchone()[0]
    conn.close()
    return {"scams_detected": analyses, "scams_reported": reports}


@app.get("/company/verify")
def verify_company(name: str):
    import re
    name_clean = name.strip()
    # If user pastes a URL, extract the domain brand (e.g. https://www.zoho.com/ -> zoho)
    if name_clean.startswith('http') or '.' in name_clean:
        domain = re.sub(r'https?://(www\.)?', '', name_clean).split('/')[0].split('.')[0]
        if domain:
            name_clean = domain
    name_lower = name_clean.lower()

    cached = db.get_cached_company(name_lower)
    if cached:
        return {"company_name": name_clean, "is_real": cached["is_real"], "lookalike": None,
                "note": cached.get("note", "Cached result."),
                "verify_url": "https://www.mca.gov.in/content/mca/global/en/mca/master-data/MDS.html"}

    # Strip common suffixes to get the core brand name
    core = re.sub(
        r'\b(pvt|private|ltd|limited|llp|inc|corp|corporation|india|global|group'
        r'|solutions?|services?|technologies|infotech|consultancy|consultants?'
        r'|associates?|enterprises?|careers?|recruitment|hiring|hr|staffing)\b',
        '', name_lower
    ).strip()

    # Direct set lookup on core (fast, exact)
    matched = core if core in KNOWN_COMPANIES else None

    # If no exact match, try each word in core against the set
    if not matched:
        for word in core.split():
            if len(word) >= 4 and word in KNOWN_COMPANIES:
                matched = word
                break

    # Lookalike: a known brand word appears in the original name + suspicious suffix
    lookalike = None
    if not matched:
        for brand in KNOWN_COMPANIES:
            if len(brand) >= 4 and brand in name_lower and any(p in name_lower for p in SUSPICIOUS_PATTERNS):
                lookalike = brand
                break

    if matched:
        is_real, note = 1, f"Matches known company: {matched.title()}"
    elif lookalike:
        is_real = 0
        note = (f"⚠️ Looks like a lookalike of '{lookalike.title()}'. "
                "Scammers add words like 'careers' or 'recruitment' to fake real brands. "
                "Verify on the official website.")
    else:
        is_real = 0
        note = "Not found in the verified company list. Always verify on mca.gov.in before sharing personal details."

    db.cache_company(name_lower, is_real)
    return {
        "company_name": name_clean,
        "is_real": is_real,
        "lookalike": lookalike,
        "note": note,
        "verify_url": "https://www.mca.gov.in/content/mca/global/en/mca/master-data/MDS.html",
    }


@app.get("/health")
def health():
    return {"status": "ok", "served_by": socket.gethostname()}


# Serve index.html explicitly for root and unknown paths (GET only)
@app.get("/")
def root():
    return FileResponse(STATIC / "index.html")

# Static assets (css, js, images etc.) — mounted under /static
app.mount("/static", StaticFiles(directory=STATIC), name="static")
