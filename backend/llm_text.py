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


def audit_text(bundle: ArticleBundle) -> List[Issue]:
    """Call text LLM to flag typos/format issues. Returns an Issue list."""

    if not bundle.text_blocks:
        return []

    snippet = "\n\n".join([b.text for b in bundle.text_blocks])
    # debug
    print("snippet:", snippet)
    prompt = (
        "寻找 typo/前后矛盾（人名错误）/语病（杂糅）/信息错误 in the following text blocks. 因为你不是多模态模型所以不会给你表格/图片，表格实际上是存在的，不要输出图片/表格不存在问题。由于前处理环节可能会在句子中间插入换行，无需在意句子中间多出的换行符。文字块拆解是程序进行的，并不代表段落结构，仅顺序可信，请勿认为一个block只有标题就没有内容，内容可能在下一个block。请发掘尽可能多的上述问题（至于内容问题，请不要指出。禁止利用我没给你的场外信息指出“某文段未在某文章出现”或“某书病粗存在”之类的问题，因为LLM存在幻觉）"
        'Return JSON {"issues":[{"id":0 (int),"type":"conflict|typo|format|other"(str),"severity":"suggest|warn"(str),"evidence":{"text_block_id":"##ID:x##","quote":"..."},"recommendation":"..."}]}. Return in chinese.\n\n'
        f"TEXT:\n{snippet}"
    )

    raw = _call_llm(prompt)
    print("## LLM Raw Response:\n", raw)  # Debug logging
    if not raw:
        return []
    return _parse_issues(raw)
