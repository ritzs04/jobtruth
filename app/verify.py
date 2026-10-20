"""Company verification and salary benchmarking."""
import re
from app import db

# Known Indian tech companies
KNOWN_COMPANIES = {
    "tcs": {"name": "Tata Consultancy Services", "website": "tcs.com", "founded": 1968},
    "infosys": {"name": "Infosys", "website": "infosys.com", "founded": 1981},
    "wipro": {"name": "Wipro", "website": "wipro.com", "founded": 1980},
    "hcltech": {"name": "HCL Technologies", "website": "hcltech.com", "founded": 1976},
    "techmahindra": {"name": "Tech Mahindra", "website": "techmahindra.com", "founded": 1986},
    "cognizant": {"name": "Cognizant", "website": "cognizant.com", "founded": 1994},
    "accenture": {"name": "Accenture", "website": "accenture.com", "founded": 1989},
    "capgemini": {"name": "Capgemini", "website": "capgemini.com", "founded": 1967},
    "ltimindtree": {"name": "LTI Mindtree", "website": "ltimindtree.com", "founded": 2011},
    "zoho": {"name": "Zoho", "website": "zoho.com", "founded": 1996},
    "amazon": {"name": "Amazon", "website": "amazon.com", "founded": 1994},
    "google": {"name": "Google", "website": "google.com", "founded": 1998},
    "microsoft": {"name": "Microsoft", "website": "microsoft.com", "founded": 1975},
    "ibm": {"name": "IBM", "website": "ibm.com", "founded": 1911},
    "deloitte": {"name": "Deloitte", "website": "deloitte.com", "founded": 1845},
}

# Salary benchmarks for Indian market (in INR, annual)
SALARY_BENCHMARKS = {
    ("data analyst", "india", "fresher"): 300000,
    ("data analyst", "india", "junior"): 500000,
    ("software engineer", "india", "fresher"): 400000,
    ("software engineer", "india", "junior"): 700000,
    ("systems engineer", "india", "fresher"): 350000,
    ("systems engineer", "india", "junior"): 600000,
    ("business analyst", "india", "fresher"): 350000,
    ("business analyst", "india", "junior"): 550000,
    ("qa engineer", "india", "fresher"): 300000,
    ("qa engineer", "india", "junior"): 500000,
}


def verify_company(company_name: str) -> dict:
    """Verify if a company is real. Returns {is_real, website, founded_year, reason}."""
    cached = db.get_cached_company(company_name)
    if cached:
        return {
            "is_real": bool(cached["is_real"]),
            "website": cached["website"],
            "founded_year": cached["founded_year"],
            "reason": "Cached result"
        }
    
    lower_name = company_name.lower().strip()
    
    # Check against known companies
    for key, info in KNOWN_COMPANIES.items():
        if key in lower_name or lower_name in key:
            db.cache_company(company_name, 1, info["website"], info["founded"])
            return {
                "is_real": True,
                "website": info["website"],
                "founded_year": info["founded"],
                "reason": f"Verified: {info['name']}"
            }
    
    # Check if it looks like a real company (has proper structure)
    if len(company_name) > 2 and not re.search(r"[^a-zA-Z0-9\s&\-]", company_name):
        db.cache_company(company_name, 0, None, None)
        return {
            "is_real": False,
            "website": None,
            "founded_year": None,
            "reason": "Not in verified company database. Verify on official website."
        }
    
    db.cache_company(company_name, 0, None, None)
    return {
        "is_real": False,
        "website": None,
        "founded_year": None,
        "reason": "Company name looks suspicious or unverified."
    }


def benchmark_salary(text: str, role: str = None, location: str = "india", experience: str = "fresher") -> dict:
    """Extract salary from text and compare to benchmark."""
    # Extract salary amounts (handles Rs, INR, ₹)
    salary_pattern = r"(?:rs\.?|₹|inr)\s*(\d{1,3}(?:,?\d{3})*)"
    matches = re.findall(salary_pattern, text.lower())
    
    if not matches:
        return {"offered_salary": None, "benchmark": None, "flag": None}
    
    # Parse first salary mention
    offered = int(matches[0].replace(",", ""))
    
    # Normalize role
    if role:
        role_lower = role.lower()
    else:
        # Try to extract role from text
        role_keywords = ["engineer", "analyst", "developer", "manager", "executive"]
        role_lower = next((kw for kw in role_keywords if kw in text.lower()), "software engineer")
    
    # Get benchmark
    benchmark_key = (role_lower, location.lower(), experience.lower())
    benchmark = db.get_salary_benchmark(role_lower, location.lower(), experience.lower())
    
    if not benchmark:
        benchmark = SALARY_BENCHMARKS.get(benchmark_key)
    
    if not benchmark:
        return {"offered_salary": offered, "benchmark": None, "flag": None}
    
    # Compare
    ratio = offered / benchmark
    if ratio > 2:
        flag = f"Salary is {int(ratio*100)}% above market for {experience} - HIGH RED FLAG"
    elif ratio > 1.5:
        flag = f"Salary is {int(ratio*100)}% above market for {experience} - suspicious"
    elif ratio < 0.5:
        flag = f"Salary is {int(ratio*100)}% below market - unusually low"
    else:
        flag = None
    
    return {
        "offered_salary": offered,
        "benchmark": benchmark,
        "ratio": ratio,
        "flag": flag
    }
