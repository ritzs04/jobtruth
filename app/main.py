import socket
import os
import json
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
    redacted = redact(req.text)
    result["redacted_preview"] = redacted[:300]
    result["served_by"] = socket.gethostname()
    # Persist a privacy-safe record (only the PII-redacted text) under the shared
    # guest user so the public scam counter reflects real usage. Never store the
    # raw paste, and never let analytics break the core analysis.
    try:
        db.save_analysis(db.ensure_guest_user(), redacted, result["trust_score"],
                         result["label"], json.dumps(result["flags"]))
    except Exception:
        pass
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
    c.execute("SELECT COUNT(*) FROM analyses WHERE label = 'High Risk'")
    scams_detected = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM scam_reports")
    reports = c.fetchone()[0]
    conn.close()
    return {"scams_detected": scams_detected, "scams_reported": reports}


_COMPANY_SUFFIXES = {
    "private", "limited", "pvt", "ltd", "llp", "inc", "corp", "corporation",
    "india", "global", "group", "solutions", "solution", "services", "service",
    "technologies", "technology", "infotech", "consultancy", "consultant",
    "consultants", "enterprises", "enterprise", "associates", "associate",
    "company", "careers", "career", "recruitment", "hiring", "staffing",
}


def _brand_words(name_lower: str) -> list:
    """Meaningful brand tokens (len>=4, suffixes removed) used to confirm a match."""
    return [w for w in name_lower.split() if len(w) >= 4 and w not in _COMPANY_SUFFIXES]


def _wikipedia_match(name_lower: str) -> bool:
    """True if Wikipedia has an article whose title contains the company's brand word."""
    import urllib.request, urllib.parse, json
    words = _brand_words(name_lower)
    if not words:
        return False
    q = urllib.parse.quote_plus(name_lower)
    url = (f"https://en.wikipedia.org/w/api.php?action=query&list=search"
           f"&srsearch={q}&srprop=&format=json&srlimit=5")
    req = urllib.request.Request(url, headers={"User-Agent": "JobTruth/1.0 (company verify)"})
    with urllib.request.urlopen(req, timeout=8) as r:
        data = json.loads(r.read().decode("utf-8", errors="ignore"))
    titles = [h.get("title", "").lower() for h in data.get("query", {}).get("search", [])]
    return any(any(w in t for w in words) for t in titles)


def _company_domain_resolves(name_lower: str) -> bool:
    """True if a domain derived from the company name resolves in DNS (real website)."""
    import socket, re
    slug = re.sub(r"\b(?:" + "|".join(sorted(_COMPANY_SUFFIXES, key=len, reverse=True)) + r")\b", " ", name_lower)
    slug = re.sub(r"[^a-z0-9]", "", slug)
    if len(slug) < 4:
        return False
    for tld in (".com", ".in", ".co.in", ".org"):
        try:
            socket.gethostbyname(slug + tld)
            return True  # domain is registered and resolves -> a real website exists
        except (socket.gaierror, Exception):
            continue
    return False


def _web_search_check(company_name: str) -> bool:
    """Return True if the company has a verifiable public presence online.

    Search-engine result scraping (Google/DuckDuckGo) is unreliable from a server
    -- Google serves a consent wall with no result links and DuckDuckGo rate-limits
    automated requests, so both return empty pages. This instead verifies the
    company through two stable, no-key, non-throttling sources:
      1. Wikipedia's public API -- a notable company has an article whose title
         contains the company's brand word.
      2. A registered domain derived from the company name -- if <brand>.com/.in
         resolves in DNS, the company owns a real website.
    Any network failure fails closed (returns False) so the caller shows
    "could not be verified -- be cautious".
    """
    name_lower = company_name.lower()
    try:
        if _wikipedia_match(name_lower):
            return True
    except Exception:
        pass
    try:
        if _company_domain_resolves(name_lower):
            return True
    except Exception:
        pass
    return False


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

    # NOTE: cache is write-only; results are recomputed so lookalike warnings are never lost.

    # Strip common suffixes to get the core brand name
    core = re.sub(
        r'\b(pvt|private|ltd|limited|llp|inc|corp|corporation|india|global|group'
        r'|solutions?|services?|technologies|infotech|consultancy|consultants?'
        r'|associates?|enterprises?|careers?|recruitment|hiring|hr|staffing)\b',
        '', name_lower
    ).strip()

    # Words scammers append to real brand names (e.g. 'Infosys Careers Pvt Ltd')
    FAKE_MARKERS = {'career','careers','recruit','recruitment','hiring','hr','job','jobs','placement','staffing'}
    has_marker = any(w in FAKE_MARKERS for w in re.findall(r'[a-z]+', name_lower))

    # Direct set lookup on core (fast, exact)
    matched = core if core in KNOWN_COMPANIES else None

    # If no exact match, try each word in core against the set
    if not matched:
        for word in core.split():
            if len(word) >= 4 and word in KNOWN_COMPANIES:
                matched = word
                break

    # Known brand + fake-recruiter marker => lookalike, not a genuine match
    lookalike = None
    if matched and has_marker:
        lookalike, matched = matched, None

    # Lookalike: a known brand word appears in the original name + suspicious suffix
    if not matched and not lookalike:
        for brand in KNOWN_COMPANIES:
            if len(brand) >= 4 and brand in name_lower and any(p in name_lower for p in SUSPICIOUS_PATTERNS):
                lookalike = brand
                break

    if matched:
        is_real, note = 1, f"Matches known company: {matched.title()}"
    elif lookalike:
        is_real = 0
        note = (f"\u26a0\ufe0f Looks like a lookalike of '{lookalike.title()}'. "
                "Scammers add words like 'careers' or 'recruitment' to fake real brands. "
                "Verify on the official website.")
    else:
        # Fallback: verify a real public presence (Wikipedia article or a registered
        # company domain) -- search-engine scraping is unreliable from a server.
        found_on_web = _web_search_check(name_clean)
        if found_on_web:
            is_real = 1
            note = ("Found a public presence (Wikipedia article or a registered company "
                    "website). Always verify on mca.gov.in before sharing personal details.")
        else:
            is_real = 0
            note = ("Not found in the verified company list, Wikipedia or as a registered "
                    "website. This company could not be verified \u2014 be cautious.")

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
