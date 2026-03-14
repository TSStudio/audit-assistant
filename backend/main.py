import json
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .schema import AuditRequest, AuditStatusResponse
from .ingest import extract_reference_documents, is_supported_reference_file
from .rag import delete_reference_documents, index_reference_documents
from .store import (
    create_knowledge_base,
    delete_knowledge_base,
    get_knowledge_base,
    get_knowledge_bases_by_ids,
    list_knowledge_bases,
    update_knowledge_base,
)
from .tasks import get_status, start_audit

app = FastAPI(title="Audit Assistant API")

captures_dir = Path(__file__).resolve().parent / "captures"
captures_dir.mkdir(exist_ok=True)
app.mount("/api/captures", StaticFiles(directory=str(captures_dir)), name="captures")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8001", "http://127.0.0.1:8001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


USER_TOKEN_COOKIE = "audit_user_token"


class ChecklistKBCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    items: List[str] = Field(default_factory=list)


class KBRenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)


def _coerce_user_token(request: Request) -> str:
    raw = (
        request.cookies.get(USER_TOKEN_COOKIE)
        or request.headers.get("X-User-Token")
        or ""
    )
    token = str(raw).strip()
    if not token:
        raise HTTPException(status_code=400, detail="missing user token")
    if len(token) > 128:
        raise HTTPException(status_code=400, detail="invalid user token")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
    if any(ch not in allowed for ch in token):
        raise HTTPException(status_code=400, detail="invalid user token")
    return token


def _parse_form_id_list(raw: str) -> List[str]:
    value = (raw or "").strip()
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            ids = [str(item).strip() for item in parsed if str(item).strip()]
            return list(dict.fromkeys(ids))
    except Exception:
        pass
    ids = [line.strip() for line in value.splitlines() if line.strip()]
    return list(dict.fromkeys(ids))


def _parse_form_bool(raw: str, default: bool = False) -> bool:
    value = str(raw or "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on", "y", "t"}


def _collect_reference_docs_from_selected_kbs(
    user_token: str,
    selected_reference_ids: List[str],
) -> List[dict]:
    if not selected_reference_ids:
        return []
    selected = get_knowledge_bases_by_ids(
        user_token,
        "reference",
        selected_reference_ids,
    )
    docs: List[dict] = []
    for item in selected:
        payload = item.get("payload") or {}
        if isinstance(payload, dict):
            text = str(payload.get("text") or "").strip()
            if text:
                docs.append(
                    {
                        "name": str(
                            payload.get("name") or item.get("name") or "reference"
                        ),
                        "text": text,
                    }
                )
    return docs


def _collect_checklist_from_selected_kbs(
    user_token: str,
    selected_checklist_ids: List[str],
) -> List[str]:
    if not selected_checklist_ids:
        return []
    selected = get_knowledge_bases_by_ids(
        user_token,
        "checklist",
        selected_checklist_ids,
    )
    merged: List[str] = []
    for item in selected:
        payload = item.get("payload") or {}
        if isinstance(payload, dict) and isinstance(payload.get("items"), list):
            merged.extend([str(v).strip() for v in payload["items"] if str(v).strip()])
    return list(dict.fromkeys(merged))


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/audit", response_model=AuditStatusResponse)
def create_audit(request: AuditRequest, req: Request):
    user_token = _coerce_user_token(req)
    return start_audit(
        str(request.url),
        checklist=request.checklist,
        fast_mode=request.fast_mode,
        source_mode="url",
        user_token=user_token,
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
    request: Request,
    file: UploadFile = File(...),
    checklist: str = Form(default="[]"),
    reference_files: List[UploadFile] = File(default=[]),
    selected_checklist_ids: str = Form(default="[]"),
    selected_reference_ids: str = Form(default="[]"),
    fast_mode: str = Form(default="false"),
):
    user_token = _coerce_user_token(request)
    try:
        content = await file.read()
    finally:
        await file.close()
    if not content:
        raise HTTPException(status_code=400, detail="uploaded file is empty")

    filename = file.filename or "upload.bin"
    label = f"[上传] {filename}"
    parsed_checklist = _parse_form_checklist(checklist)
    checklist_from_kb = _collect_checklist_from_selected_kbs(
        user_token,
        _parse_form_id_list(selected_checklist_ids),
    )
    reference_docs = await _parse_reference_files(reference_files)
    selected_reference_id_list = _parse_form_id_list(selected_reference_ids)
    reference_docs.extend(
        _collect_reference_docs_from_selected_kbs(
            user_token, selected_reference_id_list
        )
    )
    final_checklist = list(dict.fromkeys([*checklist_from_kb, *parsed_checklist]))
    return start_audit(
        label,
        checklist=final_checklist,
        fast_mode=_parse_form_bool(fast_mode, default=False),
        source_mode="upload",
        upload_filename=filename,
        upload_content=content,
        reference_docs=reference_docs,
        reference_kb_ids=selected_reference_id_list,
        user_token=user_token,
    )


@app.post("/api/audit/url", response_model=AuditStatusResponse)
async def create_audit_url(
    request: Request,
    url: str = Form(...),
    checklist: str = Form(default="[]"),
    reference_files: List[UploadFile] = File(default=[]),
    selected_checklist_ids: str = Form(default="[]"),
    selected_reference_ids: str = Form(default="[]"),
    fast_mode: str = Form(default="false"),
):
    user_token = _coerce_user_token(request)
    raw_url = (url or "").strip()
    if not raw_url:
        raise HTTPException(status_code=400, detail="url is required")
    if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
        raise HTTPException(status_code=400, detail="url must start with http/https")

    parsed_checklist = _parse_form_checklist(checklist)
    checklist_from_kb = _collect_checklist_from_selected_kbs(
        user_token,
        _parse_form_id_list(selected_checklist_ids),
    )
    reference_docs = await _parse_reference_files(reference_files)
    selected_reference_id_list = _parse_form_id_list(selected_reference_ids)
    reference_docs.extend(
        _collect_reference_docs_from_selected_kbs(
            user_token, selected_reference_id_list
        )
    )
    final_checklist = list(dict.fromkeys([*checklist_from_kb, *parsed_checklist]))
    return start_audit(
        raw_url,
        checklist=final_checklist,
        fast_mode=_parse_form_bool(fast_mode, default=False),
        source_mode="url",
        reference_docs=reference_docs,
        reference_kb_ids=selected_reference_id_list,
        user_token=user_token,
    )


@app.get("/api/audit/{task_id}", response_model=AuditStatusResponse)
def read_audit(task_id: str, request: Request):
    user_token = _coerce_user_token(request)
    status = get_status(task_id, user_token=user_token)
    if not status:
        raise HTTPException(status_code=404, detail="task not found")
    return status


@app.get("/api/kb/checklists")
def list_checklist_kb(request: Request):
    user_token = _coerce_user_token(request)
    items = list_knowledge_bases(user_token, "checklist")
    return {
        "items": [
            {
                "kb_id": item["kb_id"],
                "name": item["name"],
                "items": (item.get("payload") or {}).get("items") or [],
                "created_at": item["created_at"],
                "updated_at": item["updated_at"],
            }
            for item in items
        ]
    }


@app.post("/api/kb/checklists")
def create_checklist_kb(payload: ChecklistKBCreateRequest, request: Request):
    user_token = _coerce_user_token(request)
    items = [str(v).strip() for v in payload.items if str(v).strip()]
    if not items:
        raise HTTPException(status_code=400, detail="checklist items are empty")
    record = create_knowledge_base(
        user_token=user_token,
        kb_type="checklist",
        name=payload.name.strip(),
        payload={"items": list(dict.fromkeys(items))},
    )
    return {
        "kb_id": record["kb_id"],
        "name": record["name"],
        "items": record["payload"]["items"],
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
    }


@app.patch("/api/kb/checklists/{kb_id}")
def rename_checklist_kb(kb_id: str, payload: KBRenameRequest, request: Request):
    user_token = _coerce_user_token(request)
    item = get_knowledge_base(user_token, "checklist", kb_id)
    if not item:
        raise HTTPException(status_code=404, detail="knowledge base not found")
    updated = update_knowledge_base(
        user_token,
        "checklist",
        kb_id,
        name=payload.name.strip(),
        payload=item.get("payload") or {"items": []},
    )
    if not updated:
        raise HTTPException(status_code=404, detail="knowledge base not found")
    return {
        "kb_id": updated["kb_id"],
        "name": updated["name"],
        "items": (updated.get("payload") or {}).get("items") or [],
        "created_at": updated["created_at"],
        "updated_at": updated["updated_at"],
    }


@app.delete("/api/kb/checklists/{kb_id}")
def remove_checklist_kb(kb_id: str, request: Request):
    user_token = _coerce_user_token(request)
    deleted = delete_knowledge_base(user_token, "checklist", kb_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="knowledge base not found")
    return {"ok": True}


@app.get("/api/kb/references")
def list_reference_kb(request: Request):
    user_token = _coerce_user_token(request)
    items = list_knowledge_bases(user_token, "reference")
    return {
        "items": [
            {
                "kb_id": item["kb_id"],
                "name": item["name"],
                "source_name": (item.get("payload") or {}).get("name") or item["name"],
                "created_at": item["created_at"],
                "updated_at": item["updated_at"],
            }
            for item in items
        ]
    }


@app.post("/api/kb/references/upload")
async def create_reference_kb_upload(
    request: Request,
    files: List[UploadFile] = File(default=[]),
):
    user_token = _coerce_user_token(request)
    docs = await _parse_reference_files(files)
    if not docs:
        raise HTTPException(status_code=400, detail="no valid reference files uploaded")

    created: List[dict] = []
    for doc in docs:
        source_name = str(doc.get("name") or "reference")
        text = str(doc.get("text") or "").strip()
        if not text:
            continue
        record = create_knowledge_base(
            user_token=user_token,
            kb_type="reference",
            name=source_name,
            payload={"name": source_name, "text": text},
        )
        index_reference_documents(
            user_token=user_token,
            kb_id=record["kb_id"],
            docs=[{"name": source_name, "text": text}],
        )
        created.append(
            {
                "kb_id": record["kb_id"],
                "name": record["name"],
                "source_name": source_name,
                "created_at": record["created_at"],
                "updated_at": record["updated_at"],
            }
        )

    if not created:
        raise HTTPException(
            status_code=400, detail="no text extracted from uploaded files"
        )
    return {"items": created}


@app.patch("/api/kb/references/{kb_id}")
def rename_reference_kb(kb_id: str, payload: KBRenameRequest, request: Request):
    user_token = _coerce_user_token(request)
    item = get_knowledge_base(user_token, "reference", kb_id)
    if not item:
        raise HTTPException(status_code=404, detail="knowledge base not found")

    current_payload = item.get("payload") or {}
    text = str(current_payload.get("text") or "").strip()
    new_name = payload.name.strip()
    new_payload = {"name": new_name, "text": text}

    updated = update_knowledge_base(
        user_token,
        "reference",
        kb_id,
        name=new_name,
        payload=new_payload,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="knowledge base not found")

    if text:
        index_reference_documents(
            user_token=user_token,
            kb_id=kb_id,
            docs=[{"name": new_name, "text": text}],
        )

    return {
        "kb_id": updated["kb_id"],
        "name": updated["name"],
        "source_name": (updated.get("payload") or {}).get("name") or updated["name"],
        "created_at": updated["created_at"],
        "updated_at": updated["updated_at"],
    }


@app.delete("/api/kb/references/{kb_id}")
def remove_reference_kb(kb_id: str, request: Request):
    user_token = _coerce_user_token(request)
    deleted = delete_knowledge_base(user_token, "reference", kb_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="knowledge base not found")
    delete_reference_documents(user_token, kb_id)
    return {"ok": True}
