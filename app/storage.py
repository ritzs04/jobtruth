"""Secure S3 storage: confidentiality (SSE, private, presigned) + integrity (SHA-256)."""
import base64
import hashlib
import os
import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException

PREFIX = "offers/"
MAX_BYTES = 2 * 1024 * 1024
MAGIC = {b"%PDF": ("application/pdf", "pdf"),
         b"\x89PNG": ("image/png", "png"),
         b"\xff\xd8\xff": ("image/jpeg", "jpg")}

_client = None


def get_s3():
    global _client
    if _client is None:
        _client = boto3.client("s3", region_name=os.getenv("AWS_REGION", "ap-south-1"),
                               config=Config(signature_version="s3v4"))
    return _client


def bucket() -> str:
    name = os.getenv("S3_BUCKET")
    if not name:
        raise HTTPException(500, "S3_BUCKET environment variable is not set")
    return name


def secure_upload(data: bytes) -> dict:
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File too large (max 2 MB)")
    match = next((v for m, v in MAGIC.items() if data.startswith(m)), None)
    if not match:  # real content check, not the filename
        raise HTTPException(400, "Only PDF, PNG or JPG files are allowed")
    ctype, ext = match

    digest = hashlib.sha256(data).digest()
    b64 = base64.b64encode(digest).decode()
    key = f"{PREFIX}{uuid.uuid4()}.{ext}"
    s3, b = get_s3(), bucket()
    try:
        s3.put_object(Bucket=b, Key=key, Body=data, ContentType=ctype,
                      ServerSideEncryption="AES256", ChecksumSHA256=b64)
        head = s3.head_object(Bucket=b, Key=key, ChecksumMode="ENABLED")
        url = s3.generate_presigned_url("get_object", Params={"Bucket": b, "Key": key},
                                        ExpiresIn=300)
    except (ClientError, BotoCoreError) as e:
        raise HTTPException(502, f"Storage error: {e}")
    return {"key": key, "sha256_hex": digest.hex(),
            "integrity_verified": head.get("ChecksumSHA256") == b64,
            "encryption": head.get("ServerSideEncryption"),
            "version_id": head.get("VersionId"),
            "temp_download_url": url, "url_expires_in_seconds": 300}


def list_objects() -> list:
    try:
        resp = get_s3().list_objects_v2(Bucket=bucket(), Prefix=PREFIX)
    except (ClientError, BotoCoreError) as e:
        raise HTTPException(502, f"Storage error: {e}")
    return [{"key": o["Key"], "size": o["Size"], "last_modified": o["LastModified"].isoformat()}
            for o in resp.get("Contents", [])]


def list_versions() -> list:
    try:
        resp = get_s3().list_object_versions(Bucket=bucket(), Prefix=PREFIX)
    except (ClientError, BotoCoreError) as e:
        raise HTTPException(502, f"Storage error: {e}")
    out = [{"key": v["Key"], "version_id": v["VersionId"], "is_latest": v["IsLatest"],
            "type": "version"} for v in resp.get("Versions", [])]
    out += [{"key": d["Key"], "version_id": d["VersionId"], "is_latest": d["IsLatest"],
             "type": "delete-marker"} for d in resp.get("DeleteMarkers", [])]
    return out


def delete_object(key: str) -> dict:
    if not key.startswith(PREFIX) or ".." in key:
        raise HTTPException(400, f"Key must start with {PREFIX}")
    try:
        get_s3().delete_object(Bucket=bucket(), Key=key)
    except (ClientError, BotoCoreError) as e:
        raise HTTPException(502, f"Storage error: {e}")
    return {"deleted": key, "note": "Bucket is versioned: a delete marker was added and the file is recoverable."}
