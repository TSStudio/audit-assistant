"""Multimodal audit using DashScope-compatible VLM.

The screenshot is cut into vertical chunks with slight overlap.
Each chunk is sent to VLM concurrently, and the model must return pixel bounding boxes.
Chunk-local boxes are mapped back to full-image coordinates.
"""

import base64
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

from .schema import ArticleBundle, Issue


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


def _encode_image_to_data_url(image: Image.Image, suffix: str = "png") -> Optional[str]:
    try:
        out = BytesIO()
        ext = (suffix or "png").lower().lstrip(".")
        fmt = "JPEG" if ext in {"jpg", "jpeg"} else "PNG"
        image.save(out, format=fmt)
        mime = "jpeg" if fmt == "JPEG" else "png"
        b64 = base64.b64encode(out.getvalue()).decode("ascii")
        return f"data:image/{mime};base64,{b64}"
    except Exception:
        return None


def _slice_image_vertical(
    path: Path,
    *,
    max_vertical_ratio: float = 1.5,
    overlap_ratio: float = 0.08,
    min_overlap_px: int = 24,
    max_overlap_px: int = 120,
) -> tuple[list[dict], Optional[int], Optional[int]]:
    if not path.exists():
        return [], None, None

    try:
        with Image.open(path) as img:
            src = img.convert("RGB")
            width, height = src.size
            suffix = path.suffix.lstrip(".").lower() or "png"

            max_chunk_height = max(1, int(width * max_vertical_ratio))
            if height <= max_chunk_height:
                data_url = _encode_image_to_data_url(src, suffix)
                if not data_url:
                    return [], width, height
                return (
                    [
                        {
                            "chunk_index": 1,
                            "chunk_count": 1,
                            "x_offset": 0,
                            "y_offset": 0,
                            "width": width,
                            "height": height,
                            "image_data_url": data_url,
                        }
                    ],
                    width,
                    height,
                )

            overlap = int(max_chunk_height * overlap_ratio)
            overlap = max(min_overlap_px, overlap)
            overlap = min(max_overlap_px, overlap)
            overlap = min(overlap, max_chunk_height - 1)

            chunks: list[dict] = []
            y0 = 0
            while y0 < height:
                y1 = min(height, y0 + max_chunk_height)
                crop = src.crop((0, y0, width, y1))
                data_url = _encode_image_to_data_url(crop, suffix)
                if data_url:
                    chunks.append(
                        {
                            "chunk_index": len(chunks) + 1,
                            "x_offset": 0,
                            "y_offset": y0,
                            "width": width,
                            "height": y1 - y0,
                            "image_data_url": data_url,
                        }
                    )
                if y1 >= height:
                    break
                next_y = y1 - overlap
                if next_y <= y0:
                    next_y = y0 + 1
                y0 = next_y

            chunk_count = len(chunks)
            for chunk in chunks:
                chunk["chunk_count"] = chunk_count
            return chunks, width, height
    except Exception:
        return [], None, None


def _normalize_bbox(
    bbox_val,
    *,
    chunk_w: int,
    chunk_h: int,
    x_offset: int,
    y_offset: int,
    full_w: int,
    full_h: int,
) -> Optional[dict]:
    raw = None
    if isinstance(bbox_val, (list, tuple)) and len(bbox_val) == 4:
        try:
            raw = {
                "x": int(bbox_val[0]),
                "y": int(bbox_val[1]),
                "width": int(bbox_val[2]),
                "height": int(bbox_val[3]),
            }
        except Exception:
            raw = None
    elif isinstance(bbox_val, dict):
        try:
            raw = {
                "x": int(bbox_val.get("x", 0)),
                "y": int(bbox_val.get("y", 0)),
                "width": int(bbox_val.get("width", 0)),
                "height": int(bbox_val.get("height", 0)),
            }
        except Exception:
            raw = None

    if not raw:
        return None

    x0 = max(0, min(raw["x"], chunk_w - 1))
    y0 = max(0, min(raw["y"], chunk_h - 1))
    w = max(1, min(raw["width"], chunk_w - x0))
    h = max(1, min(raw["height"], chunk_h - y0))

    gx = max(0, min(x_offset + x0, full_w - 1))
    gy = max(0, min(y_offset + y0, full_h - 1))
    gw = max(1, min(w, full_w - gx))
    gh = max(1, min(h, full_h - gy))
    return {"x": gx, "y": gy, "width": gw, "height": gh}


def _parse_issues(
    raw: str,
    *,
    screenshot_id: Optional[str],
    chunk_meta: dict,
    full_size: tuple[int, int],
) -> List[Issue]:
    try:
        data = json.loads((raw or "").strip())
    except Exception:
        print("Failed to parse Multimodal LLM response")
        return []

    if isinstance(data, dict) and "issues" in data:
        data = data.get("issues", [])
    if not isinstance(data, list):
        return []

    chunk_w = int(chunk_meta.get("width") or 1)
    chunk_h = int(chunk_meta.get("height") or 1)
    x_offset = int(chunk_meta.get("x_offset") or 0)
    y_offset = int(chunk_meta.get("y_offset") or 0)
    full_w, full_h = full_size

    normalized: list[dict] = []
    for idx, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            continue

        item = dict(item)
        ev = item.get("evidence") or {}
        if not isinstance(ev, dict):
            ev = {}

        if "bbox" in item and "bbox" not in ev:
            ev["bbox"] = item.get("bbox")
        if "quote" in item and "quote" not in ev:
            ev["quote"] = item.get("quote")

        bbox = _normalize_bbox(
            ev.get("bbox"),
            chunk_w=chunk_w,
            chunk_h=chunk_h,
            x_offset=x_offset,
            y_offset=y_offset,
            full_w=full_w,
            full_h=full_h,
        )
        if bbox:
            ev["bbox"] = bbox
        elif "bbox" in ev:
            ev.pop("bbox", None)

        if screenshot_id and not ev.get("screenshot_id"):
            ev["screenshot_id"] = screenshot_id

        item.pop("bbox", None)
        if not item.get("id"):
            item["id"] = f"mm-c{chunk_meta.get('chunk_index', 0)}-{idx}"
        item["evidence"] = ev
        normalized.append(item)

    return normalized


def _dedupe_issues(issues: List[dict]) -> List[dict]:
    seen = set()
    result: List[dict] = []
    for item in issues:
        if not isinstance(item, dict):
            continue
        ev = item.get("evidence") if isinstance(item.get("evidence"), dict) else {}
        bbox = ev.get("bbox") if isinstance(ev.get("bbox"), dict) else {}
        quote = " ".join(str(ev.get("quote") or "").strip().lower().split())
        try:
            x = int(bbox.get("x", 0)) // 24
            y = int(bbox.get("y", 0)) // 24
            w = int(bbox.get("width", 0)) // 24
            h = int(bbox.get("height", 0)) // 24
        except Exception:
            x = y = w = h = 0
        key = (
            str(item.get("type") or "").strip().lower(),
            quote,
            x,
            y,
            w,
            h,
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _select_image_path(bundle: ArticleBundle) -> Optional[Path]:
    if bundle.screenshots:
        shot_path = Path(bundle.screenshots[0].filename)
        if shot_path.exists():
            return shot_path
    return None


def _call_vlm(
    image_data_url: str,
    summary_text: str,
    *,
    chunk_meta: dict,
    enable_thinking: bool = True,
    temperature: float = 0.5,
) -> Optional[str]:
    cfg = _get_config()
    if not cfg["api_key"] or not cfg["model"] or not cfg["base_url"]:
        return None

    client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])
    chunk_w = chunk_meta.get("width")
    chunk_h = chunk_meta.get("height")

    try:
        completion = client.chat.completions.create(
            model=cfg["model"],
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是视觉-文字审校员，必须返回 JSON 对象。"
                        '输出格式: {"issues":[{"id":"str","type":"image_text_mismatch|ocr_error|qr_error|layout_issue|other","severity":"info|warn|error","evidence":{"bbox":{"x":int,"y":int,"width":int,"height":int},"quote":"...","reason":"..."},"recommendation":"..."}]}.'
                        "bbox 必须是当前切片坐标系像素位置，不允许用网格、归一化比例或整图坐标。"
                        f"当前切片尺寸 width={chunk_w} height={chunk_h}，x/y 必须在切片内。"
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "请审核这张切片中的视觉与文本问题。"
                                "只输出 JSON。问题尽量全面，且必须提供 bbox。\n\n"
                                f"补充上下文:\n{summary_text}"
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                    ],
                },
            ],
            temperature=temperature,
            extra_body={
                "chat_template_kwargs": {"enable_thinking": bool(enable_thinking)}
            },
            response_format={"type": "json_object"},
        )
        return completion.choices[0].message.content
    except Exception:
        return None


def audit_multimodal(
    bundle: ArticleBundle,
    checklist: Optional[List[str]] = None,
    reference_context: str = "",
    enable_thinking: bool = True,
) -> List[Issue]:
    """Run VLM audit by splitting screenshot into overlapped vertical chunks."""

    image_path = _select_image_path(bundle)
    if not image_path:
        return []

    chunks, width, height = _slice_image_vertical(image_path)
    if not chunks or not width or not height:
        return []

    screenshot_id = bundle.screenshots[0].id if bundle.screenshots else None
    checklist = [item.strip() for item in (checklist or []) if item and item.strip()]

    summary_base = {
        "source_url": bundle.source_url,
        "checklist": checklist,
        "reference_context": (reference_context or "")[:6000],
        "target_image": {
            "filename": image_path.name,
            "width": width,
            "height": height,
            "screenshot_id": screenshot_id,
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
            for t in bundle.text_blocks[:8]
        ],
    }

    all_issues: list[dict] = []

    def _run_one_chunk(chunk: dict) -> list[dict]:
        payload = dict(summary_base)
        payload["chunk"] = {
            "index": chunk.get("chunk_index"),
            "count": chunk.get("chunk_count"),
            "x_offset": chunk.get("x_offset"),
            "y_offset": chunk.get("y_offset"),
            "width": chunk.get("width"),
            "height": chunk.get("height"),
            "notes": "bbox 使用当前切片坐标系，后端会自动映射到整图坐标。",
        }
        raw = _call_vlm(
            chunk.get("image_data_url") or "",
            json.dumps(payload, ensure_ascii=False),
            chunk_meta=chunk,
            enable_thinking=enable_thinking,
            temperature=0.5,
        )
        print(
            f"## Raw Multimodal LLM Response [chunk {chunk.get('chunk_index')}/{chunk.get('chunk_count')}]",
            raw,
        )
        if not raw:
            return []
        return _parse_issues(
            raw,
            screenshot_id=screenshot_id,
            chunk_meta=chunk,
            full_size=(width, height),
        )

    max_workers = min(4, len(chunks))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_run_one_chunk, chunk) for chunk in chunks]
        for future in as_completed(futures):
            try:
                all_issues.extend(future.result() or [])
            except Exception:
                continue

    return _dedupe_issues(all_issues)
