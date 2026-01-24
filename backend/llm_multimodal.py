"""Multimodal audit using Qwen (DashScope OpenAI-compatible API).

Loads DASHSCOPE_API_KEY and optional BASE/MODEL from env/.env.
Sends a screenshot (or downloaded image) plus structured text summary to the model.
If configuration or image is missing, returns an empty list.
"""

import base64
import json
import os
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from dotenv import load_dotenv
from openai import OpenAI

from .schema import ArticleBundle, Issue, IssueEvidence, IssueType, Severity


load_dotenv()


def _get_config():
    return {
        "api_key": os.getenv("DASHSCOPE_API_KEY"),
        "base_url": os.getenv(
            "DASHSCOPE_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
        "model": os.getenv("MODEL_VLM", "qwen3-vl-plus"),
    }


def _issue_from_dict(data: dict) -> Issue:
    def _coerce_type(value) -> IssueType:
        try:
            return IssueType(value)
        except Exception:
            if isinstance(value, str) and value.lower() == "conflict":
                return IssueType.image_text_mismatch
            return IssueType.image_text_mismatch

    def _coerce_severity(value) -> Severity:
        try:
            return Severity(value)
        except Exception:
            if isinstance(value, str) and value.lower() == "suggest":
                return Severity.info
            return Severity.warn

    evidence_data = data.get("evidence", {}) if isinstance(data, dict) else {}
    return Issue(
        id=data.get("id") or uuid4().hex,
        type=_coerce_type(data.get("type", IssueType.image_text_mismatch)),
        severity=_coerce_severity(data.get("severity", Severity.warn)),
        evidence=IssueEvidence(
            **{k: v for k, v in evidence_data.items() if v is not None}
        ),
        recommendation=data.get("recommendation"),
        confidence=data.get("confidence"),
    )


def _parse_issues(raw: str) -> List[Issue]:
    raw = raw.strip()
    try:
        data = json.loads(raw)
    except Exception:
        print("Failed to parse Multimodal LLM Response")
        return []

    if isinstance(data, dict) and "issues" in data:
        data = data.get("issues", [])
    if not isinstance(data, list):
        return []
    return data


def _encode_image(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    try:
        data = path.read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        suffix = path.suffix.lstrip(".") or "png"
        return f"data:image/{suffix};base64,{b64}"
    except Exception:
        return None


def _select_image_path(bundle: ArticleBundle) -> Optional[Path]:
    # Prefer first screenshot, fallback to first downloaded image with local_path
    if bundle.screenshots:
        shot_path = Path(bundle.screenshots[0].filename)
        if shot_path.exists():
            return shot_path
    for img in bundle.images:
        if img.local_path and Path(img.local_path).exists():
            return Path(img.local_path)
    return None


def _call_vlm(image_data_url: str, summary_text: str) -> Optional[str]:
    cfg = _get_config()
    if not cfg["api_key"] or not cfg["model"] or not cfg["base_url"]:
        return None

    client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])

    try:
        completion = client.chat.completions.create(
            model=cfg["model"],
            messages=[
                {
                    "role": "system",
                    "content": 'You are a visual-text consistency auditor. Return JSON with an \'issues\' array.{"issues":[{"id":0 (int),"type":"conflict|other"(str),"severity":"suggest|warn"(str),"evidence":{"image_id|qrcode_id|text_block_id":"...","quote":"..."},"recommendation":"..."}]}',
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                        {
                            "type": "text",
                            "text": (
                                "Check if the visual content conflicts with the text/QR summary. "
                                'Return JSON {"issues":[{id,type,severity,evidence:{image_id|qrcode_id|text_block_id,quote},recommendation}]}.Respond in Chinese.\n'
                                + summary_text
                            ),
                        },
                    ],
                },
            ],
            response_format={"type": "json_object"},
        )
        return completion.choices[0].message.content
    except Exception:
        return None


def audit_multimodal(bundle: ArticleBundle) -> List[Issue]:
    """Call Qwen VLM with an image and structured summary to check consistency."""

    image_path = _select_image_path(bundle)
    if not image_path:
        return []

    summary = {
        "source_url": bundle.source_url,
        "qrcodes": [
            {"id": qr.id, "image_id": qr.image_id, "decoded_text": qr.decoded_text}
            for qr in bundle.qrcodes
        ],
        "ocr_texts": [
            {"id": o.id, "image_id": o.image_id, "text": o.text}
            for o in bundle.ocr_texts
        ],
        "text_blocks": [
            {"id": t.id, "text": t.text[:500]} for t in bundle.text_blocks[:3]
        ],
    }

    image_data_url = _encode_image(image_path)
    if not image_data_url:
        return []

    raw = _call_vlm(image_data_url, json.dumps(summary, ensure_ascii=False))
    print("## Raw Multimodal LLM Response", raw)
    if not raw:
        return []
    return _parse_issues(raw)
