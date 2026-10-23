import socket
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import storage
from app.pii import redact
from app.rules import analyze, analyze_headers

app = FastAPI(title="JobTruth", description="Fake job and internship offer detector")
STATIC = Path(__file__).resolve().parent.parent / "public"


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


@app.get("/health")
def health():
    return {"status": "ok", "served_by": socket.gethostname()}


# keep last: the static mount captures every unmatched path
app.mount("/", StaticFiles(directory=STATIC, html=True), name="public")
