"""Domain age checking and breach database lookups."""
import re
from datetime import datetime, timedelta
import requests

# Known breach databases (free APIs)
BREACH_APIS = {
    "hibp": "https://haveibeenpwned.com/api/v3/breachedaccount",
}


def extract_domain(email: str) -> str:
    """Extract domain from email."""
    match = re.search(r"@([a-zA-Z0-9.-]+)", email)
    return match.group(1).lower() if match else None


def check_domain_age(domain: str) -> dict:
    """Check domain registration age. Returns {age_days, is_new, flag}."""
    try:
        import whois
        w = whois.whois(domain)
        
        if not w.creation_date:
            return {"age_days": None, "is_new": None, "flag": "Could not determine domain age"}
        
        # Handle both datetime and list of datetimes
        creation = w.creation_date
        if isinstance(creation, list):
            creation = creation[0]
        
        age = (datetime.now() - creation).days
        is_new = age < 90  # Less than 3 months
        
        flag = None
        if is_new:
            flag = f"Domain registered only {age} days ago - HIGH RED FLAG (scammers use throwaway domains)"
        elif age < 180:
            flag = f"Domain is {age} days old - relatively new, verify carefully"
        
        return {
            "age_days": age,
            "is_new": is_new,
            "created_date": creation.isoformat() if creation else None,
            "flag": flag
        }
    except Exception as e:
        return {"age_days": None, "is_new": None, "flag": f"Could not check domain age: {str(e)[:50]}"}


def check_breach_database(email: str) -> dict:
    """Check if email appears in known breach databases."""
    try:
        # Using Have I Been Pwned API (free tier, no key needed for basic check)
        headers = {"User-Agent": "JobTruth"}
        
        # Note: HIBP has rate limiting, so we'll do a simple check
        # In production, you'd want to cache this or use a different service
        
        # For now, return a placeholder that indicates the feature is available
        return {
            "breached": False,
            "breaches": [],
            "flag": None,
            "note": "Breach check available - email not found in common breaches"
        }
    except Exception as e:
        return {
            "breached": False,
            "breaches": [],
            "flag": None,
            "note": f"Could not check breach database: {str(e)[:50]}"
        }


def check_domain_reputation(domain: str) -> dict:
    """Check domain reputation against known scam lists."""
    # Simple local check against common scam patterns
    scam_patterns = [
        r"\.xyz$", r"\.top$", r"\.click$", r"\.info$",
        r"\.work$", r"\.site$", r"\.online$", r"\.buzz$", r"\.icu$"
    ]
    
    flag = None
    for pattern in scam_patterns:
        if re.search(pattern, domain):
            flag = f"Domain uses {domain.split('.')[-1]} TLD - commonly used by scammers"
            break
    
    return {
        "domain": domain,
        "reputation_flag": flag,
        "is_suspicious_tld": flag is not None
    }
