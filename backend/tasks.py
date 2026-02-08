"""Task orchestration with persistent storage."""

from threading import Thread
from typing import List, Optional, Tuple
from uuid import uuid4

from .capture import capture_article
from .llm_multimodal import audit_multimodal
from .llm_text import audit_text
from .parser import enrich_bundle
from .schema import (
    ArticleBundle,
    AuditStatusResponse,
    Issue,
    IssueEvidence,
    TaskStatus,
)
from .store import create_task, get_task, update_task
from .vision import analyze_images


def start_audit(url: str, checklist: Optional[List[str]] = None) -> AuditStatusResponse:
    record = create_task(str(url), checklist=checklist or [])
    task_id = record["task_id"]

    thread = Thread(
        target=_run_pipeline,
        args=(task_id, str(url), record.get("checklist") or []),
        daemon=True,
    )
    thread.start()

    return AuditStatusResponse(
        task_id=task_id,
        status=TaskStatus.running,
        result=None,
        issues=[],
        checklist=record.get("checklist") or [],
        message=record.get("message"),
        progress=record.get("progress", 0),
    )


def _run_pipeline(
    task_id: str, url: str, checklist: Optional[List[str]] = None
) -> None:
    try:
        bundle, issues = run_pipeline(task_id, url, checklist=checklist or [])
        complete_task(task_id, bundle, issues)
    except Exception as exc:  # noqa: BLE001
        fail_task(task_id, f"Audit failed: {exc}")


def _coerce_issues(raw: Optional[List]) -> List[Issue]:
    """Best-effort conversion of arbitrary issue payloads into Issue models.

    Drops entries that cannot be validated to avoid breaking the response model.
    """

    def _normalize_issue_dict(data: dict) -> dict:
        if not isinstance(data, dict):
            return {}
        mapped = dict(data)

        # Coerce id to string
        try:
            mapped["id"] = str(mapped.get("id") or uuid4().hex)
        except Exception:
            mapped["id"] = uuid4().hex

        issue_type = (mapped.get("type") or "").lower()
        if issue_type == "conflict":
            mapped["type"] = "compliance"
        elif issue_type == "format":
            mapped["type"] = "layout"
        elif issue_type == "other":
            mapped["type"] = "compliance"
        elif issue_type not in {
            "typo",
            "link",
            "qrcode",
            "image_text_mismatch",
            "compliance",
            "layout",
        }:
            mapped["type"] = "typo"

        sev = (mapped.get("severity") or "").lower()
        if sev == "suggest":
            mapped["severity"] = "info"
        elif sev not in {"info", "warn", "critical"}:
            mapped["severity"] = "warn"

        ev = mapped.get("evidence") or {}
        if isinstance(ev, dict):
            allowed_keys = {
                "text_block_id",
                "link_id",
                "image_id",
                "screenshot_id",
                "bbox",
                "quote",
            }
            mapped["evidence"] = {
                k: v for k, v in ev.items() if k in allowed_keys and v is not None
            }
        return mapped

    cleaned: List[Issue] = []
    for item in raw or []:
        try:
            if isinstance(item, Issue):
                cleaned.append(item)
            elif isinstance(item, dict):
                mapped = _normalize_issue_dict(item)
                cleaned.append(Issue.model_validate(mapped))
        except Exception:
            continue
    return cleaned


def _update_progress(task_id: str, progress: int, message: str) -> None:
    update_task(task_id, progress=progress, message=message)


def _attach_bboxes_from_text_blocks(
    bundle: ArticleBundle, issues: Optional[list]
) -> list:
    """Copy text block bounding boxes onto issue evidence for frontend rendering."""

    block_map = {b.id: b for b in bundle.text_blocks if b.bbox is not None}
    screenshot_id = bundle.screenshots[0].id if bundle.screenshots else None
    patched: list = []

    def _resolve_block(ev_text_block_id: Optional[str]):
        if not ev_text_block_id:
            return None
        if ev_text_block_id in block_map:
            return block_map[ev_text_block_id]
        if ev_text_block_id.startswith("##ID:"):
            try:
                idx = int(ev_text_block_id.replace("##ID:", "").replace("##", ""))
                return block_map.get(f"t{idx}")
            except Exception:
                return None
        return None

    for item in issues or []:
        try:
            if isinstance(item, Issue):
                ev: IssueEvidence = item.evidence or IssueEvidence()
                if ev.bbox is None:
                    block = _resolve_block(ev.text_block_id)
                else:
                    block = None
                if block:
                    updated_ev = ev.model_copy(
                        update={
                            "bbox": block.bbox,
                            "screenshot_id": ev.screenshot_id or screenshot_id,
                        }
                    )
                    patched.append(item.model_copy(update={"evidence": updated_ev}))
                else:
                    patched.append(item)
            elif isinstance(item, dict):
                ev = item.get("evidence") or {}
                block = None
                if ev.get("bbox") is None:
                    block = _resolve_block(ev.get("text_block_id"))
                if block:
                    ev = dict(ev)
                    ev["bbox"] = (
                        block.bbox.model_dump()
                        if hasattr(block.bbox, "model_dump")
                        else block.bbox
                    )
                    if screenshot_id and not ev.get("screenshot_id"):
                        ev["screenshot_id"] = screenshot_id
                    item = dict(item, evidence=ev)
                patched.append(item)
            else:
                patched.append(item)
        except Exception:
            patched.append(item)

    return patched


def run_pipeline(
    task_id: str, url: str, checklist: Optional[List[str]] = None
) -> Tuple[ArticleBundle, list[Issue]]:
    """Run the full audit pipeline synchronously with progress updates."""

    _update_progress(task_id, 5, "Starting capture")
    bundle = capture_article(url)

    _update_progress(task_id, 25, "Parsing & enriching")
    bundle = enrich_bundle(bundle, url)

    _update_progress(task_id, 45, "Analyzing images")
    bundle = analyze_images(bundle)

    _update_progress(task_id, 65, "Text LLM audit")
    issues_text = audit_text(bundle, checklist=checklist or [])

    # Attach bounding boxes from captured text blocks so the frontend can render directly.
    issues_text = _attach_bboxes_from_text_blocks(bundle, issues_text)

    _update_progress(task_id, 85, "Multimodal LLM audit")
    issues_mm = audit_multimodal(bundle, checklist=checklist or [])

    issues = issues_text + issues_mm
    try:
        print(
            f"[pipeline] issues_text={len(issues_text)}, issues_mm={len(issues_mm)}, total={len(issues)}"
        )
    except Exception:
        pass
    return bundle, issues


def get_status(task_id: str) -> Optional[AuditStatusResponse]:
    record = get_task(task_id)
    if not record:
        return None
    bundle = None
    if record.get("result"):
        try:
            bundle = ArticleBundle.model_validate(record["result"])
        except Exception:
            bundle = None
    issues = _coerce_issues(record.get("issues") or [])
    return AuditStatusResponse(
        task_id=record["task_id"],
        status=TaskStatus(record["status"]),
        result=bundle,
        issues=issues,
        checklist=record.get("checklist") or [],
        message=record.get("message"),
        progress=record.get("progress"),
    )


def complete_task(task_id: str, bundle: ArticleBundle, issues=None) -> None:
    issues = _coerce_issues(issues)
    update_task(
        task_id,
        status=TaskStatus.completed.value,
        message="Audit completed.",
        progress=100,
        result=bundle.model_dump(mode="json"),
        issues=[issue.model_dump(mode="json") for issue in issues],
    )


def fail_task(task_id: str, message: str) -> None:
    update_task(task_id, status=TaskStatus.failed.value, message=message)
