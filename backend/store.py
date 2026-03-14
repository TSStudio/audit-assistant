"""SQLite-backed audit task storage."""

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from .schema import TaskStatus

DB_PATH = Path(__file__).resolve().parent / "audit_store.db"


def _ensure_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audits (
                task_id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                checklist TEXT,
                status TEXT NOT NULL,
                message TEXT,
                progress INTEGER,
                result TEXT,
                issues TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        # Lightweight migration for existing databases
        cur = conn.execute("PRAGMA table_info(audits)")
        cols = {row[1] for row in cur.fetchall()}
        if "checklist" not in cols:
            conn.execute("ALTER TABLE audits ADD COLUMN checklist TEXT")
        if "user_token" not in cols:
            conn.execute("ALTER TABLE audits ADD COLUMN user_token TEXT")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_bases (
                kb_id TEXT PRIMARY KEY,
                user_token TEXT NOT NULL,
                kb_type TEXT NOT NULL,
                name TEXT NOT NULL,
                payload TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_kb_user_type ON knowledge_bases(user_token, kb_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_audits_user_token ON audits(user_token)"
        )
        conn.commit()
    finally:
        conn.close()


def _serialize_json(value: Any) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value)


def _deserialize_json(payload: Optional[str]) -> Any:
    if not payload:
        return None
    try:
        return json.loads(payload)
    except Exception:
        return None


def create_task(
    url: str,
    checklist: Optional[list[str]] = None,
    *,
    user_token: Optional[str] = None,
) -> dict:
    _ensure_db()
    task_id = uuid4().hex
    now = int(time.time())
    status = TaskStatus.running.value
    message = "Audit pipeline queued."
    progress = 0
    checklist = checklist or []

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            INSERT INTO audits (
                task_id, user_token, url, checklist, status, message, progress, result, issues, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                user_token,
                url,
                _serialize_json(checklist),
                status,
                message,
                progress,
                None,
                None,
                now,
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "task_id": task_id,
        "user_token": user_token,
        "url": url,
        "checklist": checklist,
        "status": status,
        "message": message,
        "progress": progress,
        "result": None,
        "issues": [],
        "created_at": now,
        "updated_at": now,
    }


def update_task(
    task_id: str,
    *,
    checklist: Any = None,
    status: Optional[str] = None,
    message: Optional[str] = None,
    progress: Optional[int] = None,
    result: Any = None,
    issues: Any = None,
) -> None:
    _ensure_db()
    fields = []
    values = []

    if checklist is not None:
        fields.append("checklist = ?")
        values.append(_serialize_json(checklist))
    if status is not None:
        fields.append("status = ?")
        values.append(status)
    if message is not None:
        fields.append("message = ?")
        values.append(message)
    if progress is not None:
        fields.append("progress = ?")
        values.append(progress)
    if result is not None:
        fields.append("result = ?")
        values.append(_serialize_json(result))
    if issues is not None:
        fields.append("issues = ?")
        values.append(_serialize_json(issues))

    if not fields:
        return

    fields.append("updated_at = ?")
    values.append(int(time.time()))
    values.append(task_id)

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            f"UPDATE audits SET {', '.join(fields)} WHERE task_id = ?",
            values,
        )
        conn.commit()
    finally:
        conn.close()


def get_task(task_id: str, *, user_token: Optional[str] = None) -> Optional[dict]:
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        if user_token:
            cur = conn.execute(
                """
                SELECT task_id, user_token, url, checklist, status, message, progress, result, issues, created_at, updated_at
                FROM audits WHERE task_id = ? AND user_token = ?
                """,
                (task_id, user_token),
            )
        else:
            cur = conn.execute(
                """
                SELECT task_id, user_token, url, checklist, status, message, progress, result, issues, created_at, updated_at
                FROM audits WHERE task_id = ?
                """,
                (task_id,),
            )
        row = cur.fetchone()
        if not row:
            return None
        (
            task_id,
            user_token,
            url,
            checklist,
            status,
            message,
            progress,
            result,
            issues,
            created_at,
            updated_at,
        ) = row
        return {
            "task_id": task_id,
            "user_token": user_token,
            "url": url,
            "checklist": _deserialize_json(checklist) or [],
            "status": status,
            "message": message,
            "progress": progress,
            "result": _deserialize_json(result),
            "issues": _deserialize_json(issues) or [],
            "created_at": created_at,
            "updated_at": updated_at,
        }
    finally:
        conn.close()


def create_knowledge_base(
    user_token: str,
    kb_type: str,
    name: str,
    payload: Any,
) -> dict:
    _ensure_db()
    kb_id = uuid4().hex
    now = int(time.time())

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            INSERT INTO knowledge_bases (
                kb_id, user_token, kb_type, name, payload, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                kb_id,
                user_token,
                kb_type,
                name,
                _serialize_json(payload),
                now,
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "kb_id": kb_id,
        "user_token": user_token,
        "kb_type": kb_type,
        "name": name,
        "payload": payload,
        "created_at": now,
        "updated_at": now,
    }


def list_knowledge_bases(user_token: str, kb_type: str) -> list[dict]:
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            """
            SELECT kb_id, user_token, kb_type, name, payload, created_at, updated_at
            FROM knowledge_bases
            WHERE user_token = ? AND kb_type = ?
            ORDER BY updated_at DESC
            """,
            (user_token, kb_type),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    out: list[dict] = []
    for row in rows:
        kb_id, user_token, kb_type, name, payload, created_at, updated_at = row
        out.append(
            {
                "kb_id": kb_id,
                "user_token": user_token,
                "kb_type": kb_type,
                "name": name,
                "payload": _deserialize_json(payload),
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )
    return out


def get_knowledge_bases_by_ids(
    user_token: str,
    kb_type: str,
    kb_ids: list[str],
) -> list[dict]:
    if not kb_ids:
        return []

    _ensure_db()
    placeholders = ", ".join(["?"] * len(kb_ids))
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            f"""
            SELECT kb_id, user_token, kb_type, name, payload, created_at, updated_at
            FROM knowledge_bases
            WHERE user_token = ? AND kb_type = ? AND kb_id IN ({placeholders})
            """,
            [user_token, kb_type, *kb_ids],
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    out: list[dict] = []
    for row in rows:
        kb_id, user_token, kb_type, name, payload, created_at, updated_at = row
        out.append(
            {
                "kb_id": kb_id,
                "user_token": user_token,
                "kb_type": kb_type,
                "name": name,
                "payload": _deserialize_json(payload),
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )
    return out


def get_knowledge_base(
    user_token: str,
    kb_type: str,
    kb_id: str,
) -> Optional[dict]:
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            """
            SELECT kb_id, user_token, kb_type, name, payload, created_at, updated_at
            FROM knowledge_bases
            WHERE user_token = ? AND kb_type = ? AND kb_id = ?
            """,
            (user_token, kb_type, kb_id),
        )
        row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        return None

    rid, user_token, kb_type, name, payload, created_at, updated_at = row
    return {
        "kb_id": rid,
        "user_token": user_token,
        "kb_type": kb_type,
        "name": name,
        "payload": _deserialize_json(payload),
        "created_at": created_at,
        "updated_at": updated_at,
    }


def update_knowledge_base(
    user_token: str,
    kb_type: str,
    kb_id: str,
    *,
    name: str,
    payload: Any,
) -> Optional[dict]:
    _ensure_db()
    now = int(time.time())
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            """
            UPDATE knowledge_bases
            SET name = ?, payload = ?, updated_at = ?
            WHERE user_token = ? AND kb_type = ? AND kb_id = ?
            """,
            (
                name,
                _serialize_json(payload),
                now,
                user_token,
                kb_type,
                kb_id,
            ),
        )
        conn.commit()
        changed = cur.rowcount
    finally:
        conn.close()

    if not changed:
        return None
    return get_knowledge_base(user_token, kb_type, kb_id)


def delete_knowledge_base(
    user_token: str,
    kb_type: str,
    kb_id: str,
) -> bool:
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            """
            DELETE FROM knowledge_bases
            WHERE user_token = ? AND kb_type = ? AND kb_id = ?
            """,
            (user_token, kb_type, kb_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
