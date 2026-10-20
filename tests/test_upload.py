import base64
import datetime
import hashlib

import pytest
from fastapi.testclient import TestClient

from app import storage
from app.main import app

client = TestClient(app)


class FakeS3:
    def __init__(self):
        self.put = None
        self.deleted = []

    def put_object(self, **kw):
        self.put = kw

    def head_object(self, **kw):
        return {"ChecksumSHA256": self.put["ChecksumSHA256"],
                "ServerSideEncryption": self.put["ServerSideEncryption"], "VersionId": "v1"}

    def generate_presigned_url(self, op, Params, ExpiresIn):
        return f"https://signed.example/{Params['Key']}?exp={ExpiresIn}"

    def list_objects_v2(self, **kw):
        return {"Contents": [{"Key": "offers/a.pdf", "Size": 10,
                              "LastModified": datetime.datetime(2026, 1, 1)}]}

    def delete_object(self, **kw):
        self.deleted.append(kw["Key"])


@pytest.fixture
def fake(monkeypatch):
    f = FakeS3()
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    monkeypatch.setattr(storage, "get_s3", lambda: f)
    return f


def test_valid_pdf_uploaded_with_integrity(fake):
    data = b"%PDF-1.4 offer letter"
    r = client.post("/upload", files={"file": ("offer.pdf", data, "application/pdf")})
    assert r.status_code == 200
    body = r.json()
    assert body["integrity_verified"] is True
    assert body["encryption"] == "AES256"
    assert body["sha256_hex"] == hashlib.sha256(data).hexdigest()
    assert fake.put["ChecksumSHA256"] == base64.b64encode(hashlib.sha256(data).digest()).decode()
    assert body["key"].startswith("offers/") and body["url_expires_in_seconds"] == 300


def test_fake_pdf_rejected_by_magic_bytes(fake):
    r = client.post("/upload", files={"file": ("evil.pdf", b"MZ\x90\x00 exe bytes", "application/pdf")})
    assert r.status_code == 400 and fake.put is None


def test_oversize_rejected(fake):
    big = b"%PDF-" + b"0" * (2 * 1024 * 1024)
    r = client.post("/upload", files={"file": ("big.pdf", big, "application/pdf")})
    assert r.status_code == 413 and fake.put is None


def test_list_and_delete(fake):
    assert client.get("/objects").json()[0]["key"] == "offers/a.pdf"
    assert client.delete("/objects/offers/a.pdf").status_code == 200
    assert fake.deleted == ["offers/a.pdf"]


def test_delete_outside_prefix_blocked(fake):
    assert client.delete("/objects/secret/x.pdf").status_code == 400


def test_health_and_analyze_endpoint():
    assert client.get("/health").json()["status"] == "ok"
    r = client.post("/analyze", json={"text": "Pay registration fee, mail hr@gmail.com"})
    assert r.status_code == 200 and "served_by" in r.json()
