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


def create_task(url: str) -> dict:
    _ensure_db()
    task_id = uuid4().hex
    now = int(time.time())
    status = TaskStatus.running.value
    message = "Audit pipeline queued."
    progress = 0

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            INSERT INTO audits (
                task_id, url, status, message, progress, result, issues, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                url,
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
        "url": url,
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
    status: Optional[str] = None,
    message: Optional[str] = None,
    progress: Optional[int] = None,
    result: Any = None,
    issues: Any = None,
) -> None:
    _ensure_db()
    fields = []
    values = []

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


def get_task(task_id: str) -> Optional[dict]:
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            """
            SELECT task_id, url, status, message, progress, result, issues, created_at, updated_at
            FROM audits WHERE task_id = ?
            """,
            (task_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        (
            task_id,
            url,
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
            "url": url,
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
