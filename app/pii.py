"""Redact personal data before text is returned or logged."""
import re

AADHAAR = re.compile(r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)")
PHONE = re.compile(r"(?<!\d)(?:\+91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def redact(text: str) -> str:
    text = EMAIL.sub("[EMAIL]", text)
    text = AADHAAR.sub("[ID-NUMBER]", text)   # before phone: 12 digits
    text = PHONE.sub("[PHONE]", text)
    return text
