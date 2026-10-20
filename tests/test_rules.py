from app.pii import redact
from app.rules import analyze, analyze_headers, levenshtein

SCAM = ("URGENT! Selected for work from home. No interview needed. Pay registration fee "
        "of Rs 1500 via UPI id jobs@ybl. Contact on WhatsApp. hr.recruit@gmail.com")
CLEAN = ("Infosys invites applications for the Systems Engineer role. Please apply at "
         "careers@infosys.com. Selection includes an online test and two interview rounds.")


def codes(r):
    return {f["code"] for f in r["flags"]}


def test_scam_scores_below_40():
    r = analyze(SCAM)
    assert r["trust_score"] < 40 and r["label"] == "High Risk"
    assert {"PAYMENT", "CHAT_ONLY", "FREE_EMAIL", "NO_INTERVIEW", "URGENCY", "UPI_BANK"} <= codes(r)


def test_clean_scores_70_or_more():
    r = analyze(CLEAN)
    assert r["trust_score"] >= 70 and r["label"] == "Looks Safe"


def test_gmail_recruiter_flagged():
    assert "FREE_EMAIL" in codes(analyze("Send CV to hiring.team@gmail.com"))


def test_lookalike_domain_flagged():
    assert "LOOKALIKE_DOMAIN" in codes(analyze("Mail hr@infosys-careers.com"))
    assert "LOOKALIKE_DOMAIN" in codes(analyze("Mail hr@infosis.com"))


def test_official_domain_not_flagged():
    assert "LOOKALIKE_DOMAIN" not in codes(analyze("Mail hr@infosys.com"))


def test_suspicious_tld():
    assert "SUSPICIOUS_TLD" in codes(analyze("Mail jobs@quickhire.xyz"))


def test_score_is_bounded():
    assert 0 <= analyze(SCAM * 5)["trust_score"] <= 100


def test_redaction():
    out = redact("Call +91 98765 43210 or mail a.b@gmail.com, id 1234 5678 9012")
    assert "98765" not in out and "gmail" not in out and "5678" not in out


def test_levenshtein():
    assert levenshtein("infosys", "infosis") == 1


def test_headers_pass_and_fail():
    ok = analyze_headers("Authentication-Results: mx.google.com; spf=pass; dkim=pass; dmarc=pass")
    assert ok["verdict"] == "Authenticated"
    bad = analyze_headers("Authentication-Results: mx.google.com;\n spf=softfail; dkim=none; dmarc=fail")
    assert bad["verdict"] == "Failed checks" and len(bad["flags"]) == 3
    assert analyze_headers("Subject: hi")["verdict"] == "Unverifiable"
