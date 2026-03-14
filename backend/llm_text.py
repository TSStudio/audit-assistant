"""Text-only LLM audit.

Loads API settings from environment/.env and calls a chat-like endpoint expected to
return JSON issues. If configuration is missing or the call fails, returns an empty list.
"""

import json
import os
from typing import List, Optional
from uuid import uuid4

from dotenv import load_dotenv
from openai import OpenAI

from .schema import ArticleBundle, Issue, IssueEvidence, IssueType, Severity


load_dotenv()


def _get_config():
    return {
        "endpoint": os.getenv("API_ENDPOINT_LLM"),
        "api_key": os.getenv("API_KEY_LLM"),
        "model": os.getenv("MODEL_LLM", "gpt-4o-mini"),
    }


def _issue_from_dict(data: dict) -> Issue:
    def _coerce_type(value) -> IssueType:
        try:
            return IssueType(value)
        except Exception:
            if isinstance(value, str) and value.lower() == "conflict":
                return IssueType.compliance
            return IssueType.typo

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
        type=_coerce_type(data.get("type", IssueType.typo)),
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
        print("Failed to parse LLM response as JSON.")
        return []

    if isinstance(data, dict) and "issues" in data:
        data = data.get("issues", [])
    if not isinstance(data, list):
        print("LLM response 'issues' is not a list.")
        return []
    return data


def _issue_to_dict(item) -> Optional[dict]:
    if isinstance(item, Issue):
        try:
            return item.model_dump(mode="json")
        except Exception:
            return None
    if isinstance(item, dict):
        return dict(item)
    return None


def _merge_key(issue: dict) -> str:
    evidence = issue.get("evidence") if isinstance(issue, dict) else {}
    if not isinstance(evidence, dict):
        evidence = {}

    issue_type = str(issue.get("type") or "").strip().lower()
    text_block_id = str(evidence.get("text_block_id") or "").strip().lower()
    image_id = str(evidence.get("image_id") or "").strip().lower()
    quote = " ".join(str(evidence.get("quote") or "").strip().lower().split())
    bbox = evidence.get("bbox")
    bbox_key = ""
    if isinstance(bbox, dict):
        try:
            bbox_key = (
                f"{int(bbox.get('x', 0))},{int(bbox.get('y', 0))},"
                f"{int(bbox.get('width', 0))},{int(bbox.get('height', 0))}"
            )
        except Exception:
            bbox_key = ""

    # Key designed for coarse duplicate removal in fallback mode.
    return "|".join([issue_type, text_block_id, image_id, quote, bbox_key])


def merge_llm_vlm_issues(
    issues_text: Optional[List],
    issues_vlm: Optional[List],
) -> List[dict]:
    """Merge text-LLM and VLM issues with text-LLM priority on duplicates."""

    text_items = [d for d in (_issue_to_dict(i) for i in (issues_text or [])) if d]
    vlm_items = [d for d in (_issue_to_dict(i) for i in (issues_vlm or [])) if d]

    if not text_items and not vlm_items:
        return []
    if not text_items:
        return vlm_items
    if not vlm_items:
        return text_items

    prompt = (
        "你是审核结果合并器。请合并两组问题列表：\n"
        "A=文本LLM结果（优先级更高）\n"
        "B=视觉VLM结果\n\n"
        "要求：\n"
        "1) 识别语义上重复的问题（即使表达不同）。\n"
        "2) 若重复，保留A对应项，删除B对应项。\n"
        "3) 若不重复，保留。\n"
        '4) 输出必须是 JSON 对象，形如 {"issues":[...]}。\n'
        "5) 每项字段仅使用现有字段（id/type/severity/evidence/recommendation/confidence），不要新增字段。\n"
        "6) 中文输出即可。\n\n"
        f"A_JSON:\n{json.dumps(text_items, ensure_ascii=False)[:45000]}\n\n"
        f"B_JSON:\n{json.dumps(vlm_items, ensure_ascii=False)[:45000]}"
    )

    raw = _call_llm(prompt)
    merged = _parse_issues(raw) if raw else []
    if isinstance(merged, list) and merged:
        return [d for d in merged if isinstance(d, dict)]

    # Fallback: exact-ish key de-dup, text LLM has priority.
    seen = set()
    result: List[dict] = []
    for item in text_items:
        key = _merge_key(item)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    for item in vlm_items:
        key = _merge_key(item)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _call_llm(prompt: str) -> Optional[str]:
    cfg = _get_config()
    if not cfg["endpoint"] or not cfg["model"]:
        print("LLM config missing, skipping LLM call.")
        return None

    try:
        client = OpenAI(api_key=cfg["api_key"], base_url=cfg["endpoint"])
        completion = client.chat.completions.create(
            model=cfg["model"],
            messages=[
                {
                    "role": "system",
                    "content": "You are a text quality auditor. Return JSON with an 'issues' array.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        return completion.choices[0].message.content
    except Exception:
        return None


def audit_text(
    bundle: ArticleBundle,
    checklist: Optional[List[str]] = None,
    reference_context: str = "",
) -> List[Issue]:
    """Call text LLM to flag typos/format issues. Returns an Issue list."""

    if not bundle.text_blocks:
        return []

    snippet = "\n\n".join([b.text for b in bundle.text_blocks])
    # debug
    print("snippet:", snippet)
    checklist = [item.strip() for item in (checklist or []) if item and item.strip()]
    extra_clause = ""
    if checklist:
        extra_clause = "\n\n额外审核清单（逐项检查并尽量发现相关问题）：\n" + "\n".join(
            [f"- {item}" for item in checklist]
        )

    reference_clause = ""
    ref = (reference_context or "").strip()
    if ref:
        reference_clause = (
            "\n\n补充参考资料（优先用于核对人名、身份、时间、组织关系；"
            "如果与正文冲突，请指出冲突并给出证据）：\n"
            f"{ref[:12000]}"
        )

    prompt = (
        "寻找 typo/前后矛盾（人名错误）/语病（杂糅）/信息错误 in the following text blocks. 但不要输出图片/表格不存在的相关问题；由于前处理环节可能会在句子中间插入换行，无需在意句子中间多出的换行符。文字块拆解是程序进行的，并不代表段落结构，仅顺序可信，请勿认为一个block只有标题就没有内容，内容可能在下一个block。请发掘尽可能多的上述问题（至于内容问题，请不要指出。禁止利用我没给你的场外信息指出“某文段未在某文章出现”或“某书并不存在”之类的问题，因为你存在幻觉）"
        'Return JSON {"issues":[{"id":0 (int),"type":"conflict|typo|format|other"(str),"severity":"suggest|warn"(str),"evidence":{"text_block_id":"##ID:x##","quote":"..."},"recommendation":"..."}]}. Return in chinese.\n\n'
        f"TEXT:\n{snippet}"
        f"{extra_clause}"
        f"{reference_clause}"
    )

    raw = _call_llm(prompt)
    print("## LLM Raw Response:\n", raw)  # Debug logging
    if not raw:
        return []
    return _parse_issues(raw)
