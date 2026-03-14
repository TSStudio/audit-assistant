import json
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .schema import AuditRequest, AuditStatusResponse
from .ingest import extract_reference_documents, is_supported_reference_file
from .tasks import get_status, start_audit

app = FastAPI(title="Audit Assistant API")

captures_dir = Path(__file__).resolve().parent / "captures"
captures_dir.mkdir(exist_ok=True)
app.mount("/api/captures", StaticFiles(directory=str(captures_dir)), name="captures")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8001", "http://127.0.0.1:8001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/audit", response_model=AuditStatusResponse)
def create_audit(request: AuditRequest):
    return start_audit(str(request.url), checklist=request.checklist, source_mode="url")


async def _parse_reference_files(files: List[UploadFile]) -> List[dict]:
    if not files:
        return []
    payloads: List[tuple[str, bytes]] = []
    unsupported: List[str] = []

    for f in files:
        filename = f.filename or "unnamed"
        try:
            content = await f.read()
        finally:
            await f.close()
        if not content:
            continue
        if not is_supported_reference_file(filename):
            unsupported.append(filename)
            continue
        payloads.append((filename, content))

    if unsupported:
        raise HTTPException(
            status_code=400,
            detail=(
                "unsupported reference file type: "
                + ", ".join(unsupported)
                + " (allowed: txt, docx, pdf)"
            ),
        )
    return extract_reference_documents(payloads)


def _parse_form_checklist(raw: str) -> List[str]:
    value = (raw or "").strip()
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except Exception:
        pass
    return [line.strip() for line in value.splitlines() if line.strip()]


@app.post("/api/audit/upload", response_model=AuditStatusResponse)
async def create_audit_upload(
    file: UploadFile = File(...),
    checklist: str = Form(default="[]"),
    reference_files: List[UploadFile] = File(default=[]),
):
    try:
        content = await file.read()
    finally:
        await file.close()
    if not content:
        raise HTTPException(status_code=400, detail="uploaded file is empty")

    filename = file.filename or "upload.bin"
    label = f"[上传] {filename}"
    parsed_checklist = _parse_form_checklist(checklist)
    reference_docs = await _parse_reference_files(reference_files)
    return start_audit(
        label,
        checklist=parsed_checklist,
        source_mode="upload",
        upload_filename=filename,
        upload_content=content,
        reference_docs=reference_docs,
    )


@app.post("/api/audit/url", response_model=AuditStatusResponse)
async def create_audit_url(
    url: str = Form(...),
    checklist: str = Form(default="[]"),
    reference_files: List[UploadFile] = File(default=[]),
):
    raw_url = (url or "").strip()
    if not raw_url:
        raise HTTPException(status_code=400, detail="url is required")
    if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
        raise HTTPException(status_code=400, detail="url must start with http/https")

    parsed_checklist = _parse_form_checklist(checklist)
    reference_docs = await _parse_reference_files(reference_files)
    return start_audit(
        raw_url,
        checklist=parsed_checklist,
        source_mode="url",
        reference_docs=reference_docs,
    )


@app.get("/api/audit/{task_id}", response_model=AuditStatusResponse)
def read_audit(task_id: str):
    status = get_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="task not found")
    return status
