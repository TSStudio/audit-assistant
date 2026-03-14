"""Multimodal audit using Qwen (DashScope OpenAI-compatible API).

Loads DASHSCOPE_API_KEY and optional BASE/MODEL from env/.env.
Sends a screenshot (or downloaded image) plus structured text summary to the model.
If configuration or image is missing, returns an empty list.
"""

import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

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


def _parse_issues(
    raw: str,
    screenshot_id: Optional[str],
    tile_offset_y: int = 0,
    tile_width: Optional[int] = None,
    tile_height: Optional[int] = None,
    tile_index: int = 0,
) -> List[Issue]:
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

    normalized: List[dict] = []
    used_ids = set()

    for item in data:
        if not isinstance(item, dict):
            continue
        ev = item.get("evidence") or {}
        if not isinstance(ev, dict):
            ev = {}

        # If model placed bbox/quote at top-level, move into evidence.
        if "bbox" in item and "bbox" not in ev:
            ev["bbox"] = item.get("bbox")
        if "quote" in item and "quote" not in ev:
            ev["quote"] = item.get("quote")
        if screenshot_id and not ev.get("screenshot_id"):
            ev["screenshot_id"] = screenshot_id

        # Normalize bbox if model returns as list/tuple [x,y,w,h].
        bbox_val = ev.get("bbox")
        if isinstance(bbox_val, (list, tuple)) and len(bbox_val) == 4:
            try:
                x, y, w, h = bbox_val
                ev["bbox"] = {
                    "x": int(x),
                    "y": int(y),
                    "width": int(w),
                    "height": int(h),
                }
            except Exception:
                pass

        # Shift tile-local bbox to absolute screenshot coordinate system.
        bbox_val = ev.get("bbox")
        if isinstance(bbox_val, dict):
            try:
                x = int(bbox_val.get("x", 0))
                y = int(bbox_val.get("y", 0))
                w = int(bbox_val.get("width", 0))
                h = int(bbox_val.get("height", 0))
                x = max(0, x)
                y = max(0, y)
                if tile_width is not None:
                    x = min(x, max(0, tile_width - 1))
                    w = min(max(1, w), max(1, tile_width - x))
                else:
                    w = max(1, w)
                if tile_height is not None:
                    y = min(y, max(0, tile_height - 1))
                    h = min(max(1, h), max(1, tile_height - y))
                else:
                    h = max(1, h)
                ev["bbox"] = {
                    "x": x,
                    "y": y + max(0, tile_offset_y),
                    "width": w,
                    "height": h,
                }
            except Exception:
                pass

        # Remove duplicated top-level bbox to avoid conflicting fields.
        item = dict(item)
        item.pop("bbox", None)
        item["evidence"] = ev
        normalized.append(item)

    for idx, item in enumerate(normalized, start=1):
        raw_id = item.get("id")
        base = (
            f"mm-c{tile_index}-{raw_id}"
            if raw_id is not None
            else f"mm-c{tile_index}-{idx}"
        )
        dedup = base
        counter = 1
        while dedup in used_ids:
            counter += 1
            dedup = f"{base}-{counter}"
        item["id"] = dedup
        used_ids.add(dedup)

    return normalized


def _encode_original(path: Path) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    if not path.exists():
        return None, None, None
    try:
        suffix = path.suffix.lstrip(".").lower() or "png"
        with Image.open(path) as img:
            width, height = img.size
            buffer = BytesIO()
            image_format = (img.format or suffix or "PNG").upper()
            try:
                img.save(buffer, format=image_format)
            except Exception:
                img.save(buffer, format="PNG")
        b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/{suffix};base64,{b64}", width, height
    except Exception:
        return None, None, None


def _encode_image(img: Image.Image, suffix: str) -> Optional[str]:
    try:
        image_format = (img.format or suffix or "PNG").upper()
        buffer = BytesIO()
        try:
            img.save(buffer, format=image_format)
        except Exception:
            img.save(buffer, format="PNG")
        b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/{suffix};base64,{b64}"
    except Exception:
        return None


def _make_vertical_tiles(
    path: Path,
    max_h_by_w: float = 1.5,
    overlap_ratio: float = 0.08,
) -> Tuple[List[dict], Optional[int], Optional[int]]:
    """Slice one screenshot into vertical tiles with slight overlap.

    Each tile keeps full width, and tile_height <= width * max_h_by_w.
    """

    if not path.exists():
        return [], None, None

    try:
        suffix = path.suffix.lstrip(".").lower() or "png"
        with Image.open(path) as img:
            width, height = img.size
            tile_h_limit = max(1, int(width * max_h_by_w))
            tile_h = min(height, tile_h_limit)
            if tile_h <= 0:
                return [], width, height

            overlap_px = max(24, int(tile_h * overlap_ratio))
            if tile_h >= height:
                overlap_px = 0
            step = max(1, tile_h - overlap_px)

            tiles: List[dict] = []
            y = 0
            index = 0
            while y < height:
                y_end = min(height, y + tile_h)
                y = max(0, y_end - tile_h)
                crop = img.crop((0, y, width, y_end))
                data_url = _encode_image(crop, suffix)
                if data_url:
                    tiles.append(
                        {
                            "index": index,
                            "offset_y": y,
                            "width": width,
                            "height": y_end - y,
                            "data_url": data_url,
                        }
                    )
                index += 1
                if y_end >= height:
                    break
                y += step

            return tiles, width, height
    except Exception:
        return [], None, None


def _select_image_path(bundle: ArticleBundle) -> Optional[Path]:
    # Only use the first captured screenshot for multimodal analysis
    if bundle.screenshots:
        shot_path = Path(bundle.screenshots[0].filename)
        if shot_path.exists():
            return shot_path
    return None


def _call_vlm(
    image_data_url: str,
    summary_text: str,
    image_size: Tuple[Optional[int], Optional[int]],
    *,
    enable_thinking: bool = True,
) -> Optional[str]:
    cfg = _get_config()
    if not cfg["api_key"] or not cfg["model"] or not cfg["base_url"]:
        return None

    client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])

    w, h = image_size
    size_clause = f"当前切块尺寸为 width={w or 'unknown'} height={h or 'unknown'}。"

    try:
        req_kwargs = {
            "model": cfg["model"],
            "temperature": 0.5,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"""你是视觉-文字审校员。必须返回 JSON 对象，字段：
{{
  "issues": [
    {{
      "id": "str",
      "type": "image_text_mismatch|ocr_error|qr_error|layout_issue|other",
      "severity": "info|warn|error",
      "evidence": {{
        "bbox": {{"x":int,"y":int,"width":int,"height":int}},
        "quote": "与证据相关的原文/识别文本",
        "reason": "为什么这是问题"
      }},
      "recommendation": "如何修改"
    }}
  ]
}}
{size_clause}
bbox 必须是像素坐标，并且是当前切块内的相对坐标（左上角为 0,0）。
约束：x>=0,y>=0,width>0,height>0，且 bbox 不能超出当前切块边界。
如果不确定，宁可给出覆盖证据区域的较大 bbox，但必须贴近证据位置。"""
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "查找图片中可能出现的问题。"
                                "返回json结果。填充bbox。用中文回答。 **尽可能多地查找问题**。至少找出一个问题！\n\n"
                                f"补充上下文（JSON 摘要或额外说明）：\n{summary_text}"
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                    ],
                },
            ],
            "response_format": {"type": "json_object"},
        }
        if not enable_thinking:
            req_kwargs["extra_body"] = {
                "chat_template_kwargs": {"enable_thinking": False}
            }

        try:
            completion = client.chat.completions.create(**req_kwargs)
        except Exception:
            # Fallback for endpoints that reject extra_body.
            if not enable_thinking:
                req_kwargs.pop("extra_body", None)
                completion = client.chat.completions.create(**req_kwargs)
            else:
                raise
        return completion.choices[0].message.content
    except Exception:
        return None


def audit_multimodal(
    bundle: ArticleBundle,
    checklist: Optional[List[str]] = None,
    reference_context: str = "",
    *,
    enable_thinking: bool = True,
) -> List[Issue]:
    """Call Qwen VLM on overlapped vertical tiles and merge all issues."""

    image_path = _select_image_path(bundle)
    if not image_path:
        return []

    tiles, width, height = _make_vertical_tiles(image_path)
    if not tiles:
        return []

    checklist = [item.strip() for item in (checklist or []) if item and item.strip()]
    summary = {
        "source_url": bundle.source_url,
        "checklist": checklist,
        "reference_context": (reference_context or "")[:6000],
        "target_image": {
            "filename": image_path.name,
            "width": width,
            "height": height,
            "screenshot_id": bundle.screenshots[0].id if bundle.screenshots else None,
            "tile_count": len(tiles),
            "tile_rule": "vertical tiles with full width, height<=1.5*width, slight overlap",
        },
        "qrcodes": [
            {
                "id": qr.id,
                "image_id": qr.image_id,
                "decoded_text": qr.decoded_text,
                "bbox": (
                    qr.bbox.model_dump() if hasattr(qr.bbox, "model_dump") else None
                ),
            }
            for qr in bundle.qrcodes
        ],
        "ocr_texts": [
            {
                "id": o.id,
                "image_id": o.image_id,
                "text": o.text,
                "bbox": o.bbox.model_dump() if hasattr(o.bbox, "model_dump") else None,
            }
            for o in bundle.ocr_texts
        ],
        "text_blocks": [
            {
                "id": t.id,
                "text": t.text[:500],
                "bbox": t.bbox.model_dump() if t.bbox else None,
            }
            for t in bundle.text_blocks[:3]
        ],
    }

    try:
        print(
            "## Multimodal Prompt Payload:",
            json.dumps(
                {
                    "image_size": [width, height],
                    "tile_count": len(tiles),
                    "summary": summary,
                },
                ensure_ascii=False,
            ),
        )
    except Exception:
        pass
    screenshot_id = bundle.screenshots[0].id if bundle.screenshots else None
    summary_payload = json.dumps(summary, ensure_ascii=False)

    merged: List[dict] = []
    worker_count = max(1, min(6, len(tiles)))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(
                _call_vlm,
                tile["data_url"],
                summary_payload,
                (tile["width"], tile["height"]),
                enable_thinking=enable_thinking,
            ): tile
            for tile in tiles
        }

        for future in as_completed(futures):
            tile = futures[future]
            try:
                raw = future.result()
            except Exception:
                raw = None
            print(f"## Raw Multimodal LLM Response (tile={tile['index']})", raw)
            if not raw:
                continue
            merged.extend(
                _parse_issues(
                    raw,
                    screenshot_id,
                    tile_offset_y=int(tile.get("offset_y") or 0),
                    tile_width=int(tile.get("width") or 0) or None,
                    tile_height=int(tile.get("height") or 0) or None,
                    tile_index=int(tile.get("index") or 0),
                )
            )

    return merged
