import json
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .schema import (
    AuditRequest,
    AuditStatusResponse,
    ChecklistLibraryItem,
    ReferenceLibraryItem,
    RenameRequest,
)
from .ingest import extract_reference_documents, is_supported_reference_file
from .rag import index_reference_document, make_reference_collection_name
from .store import (
    create_user_checklist,
    create_user_reference,
    delete_user_checklist,
    delete_user_reference,
    get_user_checklists_by_ids,
    get_user_references_by_ids,
    list_user_checklists,
    list_user_references,
    rename_user_checklist,
    rename_user_reference,
)
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


def _parse_form_ids(raw: str) -> List[str]:
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


@app.post("/api/audit", response_model=AuditStatusResponse)
def create_audit(
    request: AuditRequest,
    user_token: str = Header(default="", alias="X-User-Token"),
):
    token = (user_token or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="missing user token")
    return start_audit(
        str(request.url),
        checklist=request.checklist,
        source_mode="url",
        user_token=token,
    )


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
    checklist_ids: str = Form(default="[]"),
    reference_ids: str = Form(default="[]"),
    reference_files: List[UploadFile] = File(default=[]),
    user_token: str = Header(default="", alias="X-User-Token"),
):
    token = (user_token or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="missing user token")

    try:
        content = await file.read()
    finally:
        await file.close()
    if not content:
        raise HTTPException(status_code=400, detail="uploaded file is empty")

    filename = file.filename or "upload.bin"
    label = f"[上传] {filename}"
    parsed_checklist = _parse_form_checklist(checklist)
    selected_checklist_ids = _parse_form_ids(checklist_ids)
    selected_reference_ids = _parse_form_ids(reference_ids)

    if selected_checklist_ids:
        selected_lists = get_user_checklists_by_ids(token, selected_checklist_ids)
        for item in selected_lists:
            for ck in item.get("items") or []:
                text = str(ck).strip()
                if text and text not in parsed_checklist:
                    parsed_checklist.append(text)

    reference_docs = []
    selected_refs = get_user_references_by_ids(token, selected_reference_ids)
    for item in selected_refs:
        reference_docs.append(
            {
                "name": item.get("name") or item.get("filename") or "reference",
                "collection_name": item.get("collection_name"),
                "text": item.get("extracted_text") or item.get("preview") or "",
            }
        )
    reference_docs.extend(await _parse_reference_files(reference_files))

    return start_audit(
        label,
        checklist=parsed_checklist,
        user_token=token,
        source_mode="upload",
        upload_filename=filename,
        upload_content=content,
        reference_docs=reference_docs,
    )


@app.post("/api/audit/url", response_model=AuditStatusResponse)
async def create_audit_url(
    url: str = Form(...),
    checklist: str = Form(default="[]"),
    checklist_ids: str = Form(default="[]"),
    reference_ids: str = Form(default="[]"),
    reference_files: List[UploadFile] = File(default=[]),
    user_token: str = Header(default="", alias="X-User-Token"),
):
    token = (user_token or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="missing user token")

    raw_url = (url or "").strip()
    if not raw_url:
        raise HTTPException(status_code=400, detail="url is required")
    if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
        raise HTTPException(status_code=400, detail="url must start with http/https")

    parsed_checklist = _parse_form_checklist(checklist)
    selected_checklist_ids = _parse_form_ids(checklist_ids)
    selected_reference_ids = _parse_form_ids(reference_ids)

    if selected_checklist_ids:
        selected_lists = get_user_checklists_by_ids(token, selected_checklist_ids)
        for item in selected_lists:
            for ck in item.get("items") or []:
                text = str(ck).strip()
                if text and text not in parsed_checklist:
                    parsed_checklist.append(text)

    reference_docs = []
    selected_refs = get_user_references_by_ids(token, selected_reference_ids)
    for item in selected_refs:
        reference_docs.append(
            {
                "name": item.get("name") or item.get("filename") or "reference",
                "collection_name": item.get("collection_name"),
                "text": item.get("extracted_text") or item.get("preview") or "",
            }
        )
    reference_docs.extend(await _parse_reference_files(reference_files))

    return start_audit(
        raw_url,
        checklist=parsed_checklist,
        user_token=token,
        source_mode="url",
        reference_docs=reference_docs,
    )


@app.get("/api/audit/{task_id}", response_model=AuditStatusResponse)
def read_audit(
    task_id: str, user_token: str = Header(default="", alias="X-User-Token")
):
    token = (user_token or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="missing user token")
    status = get_status(task_id, token)
    if not status:
        raise HTTPException(status_code=404, detail="task not found")
    return status


@app.get("/api/kb/checklists", response_model=List[ChecklistLibraryItem])
def get_checklist_library(user_token: str = Header(default="", alias="X-User-Token")):
    token = (user_token or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="missing user token")
    rows = list_user_checklists(token)
    return [
        ChecklistLibraryItem(
            checklist_id=row["checklist_id"],
            name=row["name"],
            items=row.get("items") or [],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


@app.post("/api/kb/checklists", response_model=ChecklistLibraryItem)
async def create_checklist_library_item(
    name: str = Form(default=""),
    items: str = Form(default="[]"),
    user_token: str = Header(default="", alias="X-User-Token"),
):
    token = (user_token or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="missing user token")
    parsed_items = _parse_form_checklist(items)
    if not parsed_items:
        raise HTTPException(status_code=400, detail="checklist items cannot be empty")
    safe_name = (name or "").strip() or f"清单-{uuid4().hex[:6]}"
    row = create_user_checklist(token, safe_name, parsed_items)
    return ChecklistLibraryItem(
        checklist_id=row["checklist_id"],
        name=row["name"],
        items=row.get("items") or [],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@app.get("/api/kb/references", response_model=List[ReferenceLibraryItem])
def get_reference_library(user_token: str = Header(default="", alias="X-User-Token")):
    token = (user_token or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="missing user token")
    rows = list_user_references(token)
    return [
        ReferenceLibraryItem(
            reference_id=row["reference_id"],
            name=row["name"],
            filename=row.get("filename"),
            collection_name=row["collection_name"],
            preview=row.get("preview") or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


@app.post("/api/kb/references", response_model=List[ReferenceLibraryItem])
async def create_reference_library_items(
    files: List[UploadFile] = File(default=[]),
    names: str = Form(default="[]"),
    user_token: str = Header(default="", alias="X-User-Token"),
):
    token = (user_token or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="missing user token")

    parsed_docs = await _parse_reference_files(files)
    if not parsed_docs:
        raise HTTPException(status_code=400, detail="no valid reference files uploaded")

    custom_names: List[str] = []
    try:
        parsed_names = json.loads(names or "[]")
        if isinstance(parsed_names, list):
            custom_names = [str(n).strip() for n in parsed_names]
    except Exception:
        pass

    created: List[ReferenceLibraryItem] = []
    for idx, doc in enumerate(parsed_docs):
        doc_name = (
            (custom_names[idx] if idx < len(custom_names) and custom_names[idx] else "")
            or str(doc.get("name") or "reference").strip()
            or "reference"
        )
        doc_text = str(doc.get("text") or "").strip()
        if not doc_text:
            continue
        reference_id = uuid4().hex
        collection_name = make_reference_collection_name(reference_id)
        index_reference_document(collection_name, doc_name, doc_text)

        preview = doc_text[:300]
        saved = create_user_reference(
            user_token=token,
            name=doc_name,
            filename=doc_name,
            collection_name=collection_name,
            extracted_text=doc_text,
            preview=preview,
        )
        created.append(
            ReferenceLibraryItem(
                reference_id=saved["reference_id"],
                name=saved["name"],
                filename=saved.get("filename"),
                collection_name=saved["collection_name"],
                preview=saved.get("preview") or "",
                created_at=saved["created_at"],
                updated_at=saved["updated_at"],
            )
        )
    if not created:
        raise HTTPException(
            status_code=400, detail="uploaded references contain no readable text"
        )
    return created


@app.patch("/api/kb/references/{reference_id}", response_model=ReferenceLibraryItem)
def rename_reference_item(
    reference_id: str,
    body: RenameRequest,
    user_token: str = Header(default="", alias="X-User-Token"),
):
    token = (user_token or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="missing user token")
    new_name = (body.name or "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="name cannot be empty")
    updated = rename_user_reference(token, reference_id, new_name)
    if not updated:
        raise HTTPException(status_code=404, detail="reference not found")
    return ReferenceLibraryItem(
        reference_id=updated["reference_id"],
        name=updated["name"],
        filename=updated.get("filename"),
        collection_name=updated["collection_name"],
        preview=updated.get("preview") or "",
        created_at=updated["created_at"],
        updated_at=updated["updated_at"],
    )


@app.delete("/api/kb/references/{reference_id}")
def delete_reference_item(
    reference_id: str,
    user_token: str = Header(default="", alias="X-User-Token"),
):
    token = (user_token or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="missing user token")
    from .rag import delete_reference_collection

    collection_name = delete_user_reference(token, reference_id)
    if collection_name is None:
        raise HTTPException(status_code=404, detail="reference not found")
    delete_reference_collection(collection_name)
    return {"ok": True}


@app.patch("/api/kb/checklists/{checklist_id}", response_model=ChecklistLibraryItem)
def rename_checklist_item(
    checklist_id: str,
    body: RenameRequest,
    user_token: str = Header(default="", alias="X-User-Token"),
):
    token = (user_token or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="missing user token")
    new_name = (body.name or "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="name cannot be empty")
    updated = rename_user_checklist(token, checklist_id, new_name)
    if not updated:
        raise HTTPException(status_code=404, detail="checklist not found")
    return ChecklistLibraryItem(
        checklist_id=updated["checklist_id"],
        name=updated["name"],
        items=updated.get("items") or [],
        created_at=updated["created_at"],
        updated_at=updated["updated_at"],
    )


@app.delete("/api/kb/checklists/{checklist_id}")
def delete_checklist_item(
    checklist_id: str,
    user_token: str = Header(default="", alias="X-User-Token"),
):
    token = (user_token or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="missing user token")
    ok = delete_user_checklist(token, checklist_id)
    if not ok:
        raise HTTPException(status_code=404, detail="checklist not found")
    return {"ok": True}
