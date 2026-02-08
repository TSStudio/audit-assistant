"""Multimodal audit using Qwen (DashScope OpenAI-compatible API).

Loads DASHSCOPE_API_KEY and optional BASE/MODEL from env/.env.
Sends a screenshot (or downloaded image) plus structured text summary to the model.
If configuration or image is missing, returns an empty list.
"""

import base64
import json
import os
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

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
    grid_meta: Optional[Dict[str, float]] = None,
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

    def _col_to_idx(col: str) -> Optional[int]:
        if not isinstance(col, str) or not col:
            return None
        letter = col.strip().upper()[0]
        if "A" <= letter <= "H":
            return ord(letter) - ord("A")
        return None

    def _grid_to_bbox(grid: dict) -> Optional[dict]:
        if not grid_meta:
            return None
        col_w = grid_meta.get("col_width") or 1
        row_h = grid_meta.get("row_height") or 1
        img_w = grid_meta.get("width") or col_w * 8
        img_h = grid_meta.get("height") or row_h
        c0 = _col_to_idx(grid.get("col_begin"))
        c1 = _col_to_idx(grid.get("col_end"))
        r0 = grid.get("row_begin")
        r1 = grid.get("row_end")
        if c0 is None or c1 is None or r0 is None or r1 is None:
            return None
        try:
            c0, c1 = int(c0), int(c1)
            r0, r1 = int(r0) - 1, int(r1) - 1  # rows are 1-based from prompt
        except Exception:
            return None
        c0, c1 = sorted((c0, c1))
        r0, r1 = sorted((r0, r1))
        x0 = int(round(c0 * col_w))
        x1 = int(round((c1 + 1) * col_w))
        y0 = int(round(r0 * row_h))
        y1 = int(round((r1 + 1) * row_h))
        x1 = min(x1, int(img_w))
        y1 = min(y1, int(img_h))
        width = max(1, x1 - x0)
        height = max(1, y1 - y0)
        return {"x": x0, "y": y0, "width": width, "height": height}

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

        # Convert grid coordinates to pixel bbox if provided.
        bbox_grid = ev.get("bbox_grid") or item.get("bbox_grid") or ev.get("grid")
        if isinstance(bbox_grid, dict):
            grid_bbox = _grid_to_bbox(bbox_grid)
            if grid_bbox:
                ev.setdefault("bbox_grid", bbox_grid)
                ev.setdefault("bbox", grid_bbox)

        # Remove duplicated top-level bbox to avoid conflicting fields.
        item = dict(item)
        item.pop("bbox", None)
        item.pop("bbox_grid", None)
        item["evidence"] = ev
        normalized.append(item)

    for idx, item in enumerate(normalized, start=1):
        raw_id = item.get("id")
        base = f"mm-{raw_id}" if raw_id is not None else f"mm-{idx}"
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


def _encode_grid_image(
    path: Path,
    grid_cols: int = 8,
    grid_row_height: int = 150,
) -> Tuple[
    Optional[str],
    Optional[dict],
    Optional[str],
]:
    """Encode grid-overlaid image as data URL, returning grid meta and saved path."""

    if not path.exists():
        return None, None, None

    try:
        grid_path: Optional[Path] = None
        suffix = path.suffix.lstrip(".").lower() or "png"
        with Image.open(path) as img:
            width, height = img.size
            base = img.convert("RGBA")

            overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            font = ImageFont.load_default()
            try:
                font_path = Path(__file__).resolve().parent / "fonts" / "SIMHEI.TTF"
                if font_path.exists():
                    font = ImageFont.truetype(str(font_path), 14)
            except Exception:
                pass

            col_width = width / float(max(grid_cols, 1))
            total_rows = max(1, int((height + grid_row_height - 1) // grid_row_height))

            for col_idx in range(grid_cols):
                for row_idx in range(total_rows):
                    x0 = int(round(col_idx * col_width))
                    x1 = (
                        int(round((col_idx + 1) * col_width))
                        if col_idx < grid_cols - 1
                        else width
                    )
                    y0 = row_idx * grid_row_height
                    y1 = min(height, (row_idx + 1) * grid_row_height)
                    draw.rectangle(
                        [x0, y0, x1, y1],
                        fill=(0, 0, 0, 0),
                        outline=(255, 0, 0, 80),
                        width=2,
                    )
                    label = f"{chr(ord('A') + col_idx)}{row_idx + 1}"
                    draw.text((x0 + 4, y0 + 2), label, fill=(255, 0, 0, 80), font=font)

            composed = Image.alpha_composite(base, overlay).convert("RGB")

            image_format = (img.format or suffix or "PNG").upper()
            buffer = BytesIO()
            try:
                composed.save(buffer, format=image_format)
            except Exception:
                composed.save(buffer, format="PNG")

            try:
                grid_path = path.with_name(f"{path.stem}-grid{path.suffix}")
                composed.save(grid_path)
            except Exception:
                grid_path = None

        grid_meta = {
            "width": width,
            "height": height,
            "col_width": col_width,
            "row_height": grid_row_height,
            "cols": grid_cols,
            "rows": total_rows,
        }
        b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
        return (
            f"data:image/{suffix};base64,{b64}",
            grid_meta,
            str(grid_path) if grid_path else None,
        )
    except Exception:
        return None, None, None


def _select_image_path(bundle: ArticleBundle) -> Optional[Path]:
    # Only use the first captured screenshot for multimodal analysis
    if bundle.screenshots:
        shot_path = Path(bundle.screenshots[0].filename)
        if shot_path.exists():
            return shot_path
    return None


def _call_vlm(
    image_data_urls: List[str],
    summary_text: str,
    image_size: Tuple[Optional[int], Optional[int]],
    grid_meta: Optional[Dict[str, float]] = None,
) -> Optional[str]:
    cfg = _get_config()
    if not cfg["api_key"] or not cfg["model"] or not cfg["base_url"]:
        return None

    client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])

    w, h = image_size
    size_clause = f"当前图片尺寸为 width={w or 'unknown'} height={h or 'unknown'}。"
    grid_clause = ""
    if grid_meta:
        grid_clause = (
            f"图片已叠加网格，横向固定 {grid_meta.get('cols', 8)} 列，左到右标号 A-H；"
            f"纵向自上而下每行 {grid_meta.get('row_height', 150)} 像素，行号从 1 开始。"
            "bbox 只能使用网格坐标，字段 bbox_grid: {col_begin:'A'-'H', col_end:'A'-'H', row_begin:int, row_end:int}。"
            "不要输出像素 bbox。"
        )

    try:
        if image_data_urls:
            print("url0", image_data_urls[0][:50], "...")
        completion = client.chat.completions.create(
            model=cfg["model"],
            messages=[
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
                "bbox_grid": {{"col_begin":"A-H","col_end":"A-H","row_begin":int,"row_end":int}},
        "quote": "与证据相关的原文/识别文本",
        "reason": "为什么这是问题"
      }},
      "recommendation": "如何修改"
    }}
  ]
}}
{size_clause} {grid_clause}
你会收到两张图：第一张是原始截图（用于阅读和判断问题，不带网格）；第二张是叠加网格的同一张截图（只用于定位）。请基于第一张图理解内容，在第二张网格图上用 bbox_grid 给出位置，不要输出像素 bbox。
约束：col_begin/col_end 取 A-H，row_begin/row_end 为正整数且 row_begin <= row_end。
如果不确定，宁可给出覆盖证据区域的较大网格范围，但必须贴近证据位置。"""
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
                        *[
                            {"type": "image_url", "image_url": {"url": url}}
                            for url in image_data_urls
                        ],
                    ],
                },
            ],
            response_format={"type": "json_object"},
        )
        return completion.choices[0].message.content
    except Exception:
        return None


def audit_multimodal(
    bundle: ArticleBundle, checklist: Optional[List[str]] = None
) -> List[Issue]:
    """Call Qwen VLM with an image and structured summary to check consistency."""

    image_path = _select_image_path(bundle)
    if not image_path:
        return []

    original_data_url, width, height = _encode_original(image_path)
    grid_data_url, grid_meta, grid_path = _encode_grid_image(image_path)
    if not original_data_url or not grid_data_url:
        return []

    checklist = [item.strip() for item in (checklist or []) if item and item.strip()]
    summary = {
        "source_url": bundle.source_url,
        "checklist": checklist,
        "target_image": {
            "filename": image_path.name,
            "width": width,
            "height": height,
            "screenshot_id": bundle.screenshots[0].id if bundle.screenshots else None,
            "grid": grid_meta,
            "grid_image": Path(grid_path).name if grid_path else None,
            "grid_image_path": grid_path,
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
                    "grid": grid_meta,
                    "grid_image": grid_path,
                    "summary": summary,
                },
                ensure_ascii=False,
            ),
        )
    except Exception:
        pass

    summary_payload = json.dumps(summary, ensure_ascii=False)
    raw = _call_vlm(
        [original_data_url, grid_data_url],
        summary_payload,
        (width, height),
        grid_meta=grid_meta,
    )
    print("## Raw Multimodal LLM Response", raw)
    if not raw:
        return []
    screenshot_id = bundle.screenshots[0].id if bundle.screenshots else None
    return _parse_issues(raw, screenshot_id, grid_meta)
