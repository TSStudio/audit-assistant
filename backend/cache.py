"""SQLite-backed cache for audit results with TTL."""

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Optional, Tuple

from .schema import ArticleBundle, Issue

DB_PATH = Path(__file__).resolve().parent / "audit_cache.db"
DEFAULT_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", 7200))


def _ensure_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_cache (
                url TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def load_cached_audit(
    url: str, ttl_seconds: int = DEFAULT_TTL_SECONDS
) -> Optional[Tuple[ArticleBundle, list[Issue]]]:
    """Return cached bundle/issues for url when not expired."""

    _ensure_db()
    now = int(time.time())
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            "SELECT payload, created_at FROM audit_cache WHERE url = ?", (url,)
        )
        row = cur.fetchone()
        if not row:
            return None
        payload, created_at = row
        if created_at + ttl_seconds < now:
            conn.execute("DELETE FROM audit_cache WHERE url = ?", (url,))
            conn.commit()
            return None
        data = json.loads(payload)
        bundle = ArticleBundle.model_validate(data.get("bundle", {}))
        issues_data = data.get("issues") or []
        issues: list[Issue] = []
        fallback_items: list[dict] = []
        for item in issues_data:
            try:
                issues.append(Issue.model_validate(item))
            except Exception:
                if isinstance(item, dict):
                    fallback_items.append(item)
        # If strict validation dropped everything, fall back to raw dicts so frontend still sees issues.
        if not issues and fallback_items:
            return bundle, fallback_items
        return bundle, issues
    finally:
        conn.close()


def save_audit(url: str, bundle: ArticleBundle, issues: list[Issue]) -> None:
    """Persist audit result for url."""

    _ensure_db()
    serialized_issues = []
    for item in issues:
        if isinstance(item, Issue):
            serialized_issues.append(item.model_dump(mode="json"))
        elif isinstance(item, dict):
            serialized_issues.append(item)
        else:
            try:
                serialized_issues.append(
                    Issue.model_validate(item).model_dump(mode="json")
                )
            except Exception:
                continue

    payload = json.dumps(
        {
            "bundle": bundle.model_dump(mode="json"),
            "issues": serialized_issues,
        }
    )
    now = int(time.time())
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            INSERT INTO audit_cache (url, payload, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                payload = excluded.payload,
                created_at = excluded.created_at
            """,
            (url, payload, now),
        )
        conn.commit()
    finally:
        conn.close()


def delete_cached_audit(url: str) -> None:
    """Remove cached entry for the given URL."""

    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DELETE FROM audit_cache WHERE url = ?", (url,))
        conn.commit()
    finally:
        conn.close()
