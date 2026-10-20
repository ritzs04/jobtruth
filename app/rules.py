"""Explainable rule engine: Trust score = 100 - penalties + positives."""
import re

FREE_MAIL = {"gmail.com", "yahoo.com", "yahoo.in", "outlook.com", "hotmail.com",
             "rediffmail.com", "ymail.com", "proton.me", "protonmail.com"}
BAD_TLDS = (".xyz", ".top", ".click", ".info", ".work", ".site", ".online", ".buzz", ".icu")

# company token -> official domain
COMPANIES = {
    "tcs": "tcs.com", "infosys": "infosys.com", "wipro": "wipro.com",
    "hcltech": "hcltech.com", "techmahindra": "techmahindra.com",
    "cognizant": "cognizant.com", "accenture": "accenture.com",
    "capgemini": "capgemini.com", "ltimindtree": "ltimindtree.com",
    "zoho": "zoho.com", "amazon": "amazon.com", "google": "google.com",
    "microsoft": "microsoft.com", "ibm": "ibm.com", "deloitte": "deloitte.com",
}

# (code, penalty, regex, explanation)
RULES = [
    ("PAYMENT", 40,
     r"(registration|security|training|processing|kit|joining|refundable)\s*(fee|fees|deposit|amount|charges?)"
     r"|pay\s*(rs\.?|₹|inr)|send\s+money|pay\s+to\s+(confirm|secure|book)",
     "Asks the candidate for money. Genuine employers do not charge candidates."),
    ("UPI_BANK", 25,
     r"\b[\w.\-]{2,}@(upi|ybl|okaxis|oksbi|okhdfcbank|okicici|paytm|apl|ibl|axl)\b"
     r"|upi\s*id|account\s*(number|no)|\bifsc\b|google\s*pay|phonepe",
     "Mentions UPI or bank details, which often means a payment is being requested."),
    ("CHAT_ONLY", 15, r"whatsapp|telegram",
     "Contact is through WhatsApp/Telegram instead of an official company channel."),
    ("URGENCY", 10, r"urgent|immediately|today only|limited seats|within 24 hours|last chance",
     "Uses pressure and urgency to rush your decision."),
    ("NO_INTERVIEW", 15, r"no interview|without (an )?interview|direct (joining|selection)",
     "Promises a job without an interview process."),
    ("UNREALISTIC_PAY", 15,
     r"earn\s+.{0,25}(per day|daily|per week|weekly)"
     r"|(₹|rs\.?|inr)\s?\d{1,3}(,?\d{3})+\s*(per|/)\s*(day|week)",
     "Salary claim looks unrealistic for a fresher."),
]

DISCLAIMER = ("These are risk indicators, not proof. Always verify the company "
              "independently on its official website.")


def levenshtein(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _main_label(domain: str) -> str:
    parts = domain.split(".")
    if len(parts) >= 3 and parts[-2] in {"co", "com", "org", "net", "ac", "edu"}:
        return parts[-3]
    return parts[-2] if len(parts) >= 2 else parts[0]


def check_domain(domain: str):
    """Return (code, impact, reason) for one email domain."""
    domain = domain.lower().strip(".")
    if domain in FREE_MAIL:
        return ("FREE_EMAIL", -20, f"Recruiter uses a personal email domain ({domain}).")
    for legit in COMPANIES.values():
        if domain == legit or domain.endswith("." + legit):
            return ("COMPANY_EMAIL", 10,
                    f"Email domain {domain} matches a known official company domain.")
    label = _main_label(domain)
    tokens = [t for t in re.split(r"[-_0-9]+", label) if t]
    for name, legit in COMPANIES.items():
        near = len(name) >= 5 and 0 < levenshtein(label, name) <= 2
        if label == name or name in tokens or near:
            return ("LOOKALIKE_DOMAIN", -15,
                    f"Domain {domain} imitates {legit} but is not the official domain.")
    if domain.endswith(BAD_TLDS):
        return ("SUSPICIOUS_TLD", -15,
                f"Domain {domain} uses a TLD often seen in throwaway scam domains.")
    return ("CUSTOM_DOMAIN", 5,
            f"Uses its own domain ({domain}). Check its age and website before trusting it.")


def analyze(text: str) -> dict:
    score, flags, seen = 100, [], set()
    low = text.lower()

    for code, penalty, pattern, why in RULES:
        if re.search(pattern, low):
            score -= penalty
            flags.append({"code": code, "impact": -penalty, "reason": why})
            seen.add(code)

    for domain in dict.fromkeys(re.findall(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)", low)):
        code, impact, reason = check_domain(domain)
        if code in seen:
            continue
        if impact > 0 and any(f["impact"] < 0 and f["code"] in
                              {"FREE_EMAIL", "LOOKALIKE_DOMAIN", "SUSPICIOUS_TLD"} for f in flags):
            continue  # no bonus when another recruiter address is bad
        score += impact
        flags.append({"code": code, "impact": impact, "reason": reason})
        seen.add(code)

    score = max(0, min(100, score))
    label = "Looks Safe" if score >= 70 else "Suspicious" if score >= 40 else "High Risk"
    return {"trust_score": score, "label": label, "flags": flags, "disclaimer": DISCLAIMER}


def analyze_headers(raw: str) -> dict:
    """Parse SPF / DKIM / DMARC verdicts from an Authentication-Results header."""
    unfolded = re.sub(r"\r?\n[ \t]+", " ", raw)
    m = re.search(r"^authentication-results:\s*(.+)$", unfolded, re.I | re.M)
    if not m:
        return {"verdict": "Unverifiable", "results": {}, "flags": [{
            "code": "NO_AUTH_HEADER", "impact": -10,
            "reason": "No Authentication-Results header found, so the sender cannot be verified."}],
            "disclaimer": DISCLAIMER}
    body = m.group(1).lower()
    results, flags = {}, []
    for mech in ("spf", "dkim", "dmarc"):
        r = re.search(rf"\b{mech}=(\w+)", body)
        results[mech] = r.group(1) if r else "missing"
        if results[mech] != "pass":
            flags.append({"code": f"{mech.upper()}_{results[mech].upper()}", "impact": -15,
                          "reason": f"{mech.upper()} result is '{results[mech]}': the sender may be spoofed."})
    verdict = "Authenticated" if not flags else "Failed checks"
    return {"verdict": verdict, "results": results, "flags": flags, "disclaimer": DISCLAIMER}
