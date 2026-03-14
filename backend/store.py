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
                user_token TEXT NOT NULL,
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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_checklists (
                checklist_id TEXT PRIMARY KEY,
                user_token TEXT NOT NULL,
                name TEXT NOT NULL,
                items TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_references (
                reference_id TEXT PRIMARY KEY,
                user_token TEXT NOT NULL,
                name TEXT NOT NULL,
                filename TEXT,
                collection_name TEXT NOT NULL,
                extracted_text TEXT,
                preview TEXT,
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
                "UPDATE audits SET user_token = 'legacy-user' WHERE user_token IS NULL OR user_token = ''"
            )

        cur_ref = conn.execute("PRAGMA table_info(user_references)")
        ref_cols = {row[1] for row in cur_ref.fetchall()}
        if "extracted_text" not in ref_cols:
            conn.execute("ALTER TABLE user_references ADD COLUMN extracted_text TEXT")
        if "preview" not in ref_cols:
            conn.execute("ALTER TABLE user_references ADD COLUMN preview TEXT")

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_audits_user_updated ON audits(user_token, updated_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_checklists_user_updated ON user_checklists(user_token, updated_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_references_user_updated ON user_references(user_token, updated_at DESC)"
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
    url: str, checklist: Optional[list[str]] = None, user_token: str = ""
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


def get_task(task_id: str, user_token: Optional[str] = None) -> Optional[dict]:
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
            owner_user_token,
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
            "user_token": owner_user_token,
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


def create_user_checklist(user_token: str, name: str, items: list[str]) -> dict:
    _ensure_db()
    checklist_id = uuid4().hex
    now = int(time.time())
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            INSERT INTO user_checklists (checklist_id, user_token, name, items, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (checklist_id, user_token, name, _serialize_json(items) or "[]", now, now),
        )
        conn.commit()
    finally:
        conn.close()
    return {
        "checklist_id": checklist_id,
        "user_token": user_token,
        "name": name,
        "items": items,
        "created_at": now,
        "updated_at": now,
    }


def list_user_checklists(user_token: str) -> list[dict]:
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            """
            SELECT checklist_id, user_token, name, items, created_at, updated_at
            FROM user_checklists
            WHERE user_token = ?
            ORDER BY updated_at DESC
            """,
            (user_token,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    result: list[dict] = []
    for row in rows:
        checklist_id, owner, name, items, created_at, updated_at = row
        result.append(
            {
                "checklist_id": checklist_id,
                "user_token": owner,
                "name": name,
                "items": _deserialize_json(items) or [],
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )
    return result


def get_user_checklists_by_ids(user_token: str, checklist_ids: list[str]) -> list[dict]:
    ids = [str(i).strip() for i in checklist_ids if str(i).strip()]
    if not ids:
        return []
    _ensure_db()
    placeholders = ",".join(["?"] * len(ids))
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            f"""
            SELECT checklist_id, user_token, name, items, created_at, updated_at
            FROM user_checklists
            WHERE user_token = ? AND checklist_id IN ({placeholders})
            """,
            [user_token, *ids],
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    result: list[dict] = []
    for row in rows:
        checklist_id, owner, name, items, created_at, updated_at = row
        result.append(
            {
                "checklist_id": checklist_id,
                "user_token": owner,
                "name": name,
                "items": _deserialize_json(items) or [],
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )
    return result


def create_user_reference(
    user_token: str,
    name: str,
    filename: str,
    collection_name: str,
    extracted_text: str,
    preview: str,
) -> dict:
    _ensure_db()
    reference_id = uuid4().hex
    now = int(time.time())
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            INSERT INTO user_references (
                reference_id, user_token, name, filename, collection_name, extracted_text, preview, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reference_id,
                user_token,
                name,
                filename,
                collection_name,
                extracted_text,
                preview,
                now,
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return {
        "reference_id": reference_id,
        "user_token": user_token,
        "name": name,
        "filename": filename,
        "collection_name": collection_name,
        "preview": preview,
        "created_at": now,
        "updated_at": now,
    }


def list_user_references(user_token: str) -> list[dict]:
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            """
            SELECT reference_id, user_token, name, filename, collection_name, extracted_text, preview, created_at, updated_at
            FROM user_references
            WHERE user_token = ?
            ORDER BY updated_at DESC
            """,
            (user_token,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    result: list[dict] = []
    for row in rows:
        (
            reference_id,
            owner,
            name,
            filename,
            collection_name,
            extracted_text,
            preview,
            created_at,
            updated_at,
        ) = row
        result.append(
            {
                "reference_id": reference_id,
                "user_token": owner,
                "name": name,
                "filename": filename,
                "collection_name": collection_name,
                "extracted_text": extracted_text or "",
                "preview": preview or "",
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )
    return result


def get_user_references_by_ids(user_token: str, reference_ids: list[str]) -> list[dict]:
    ids = [str(i).strip() for i in reference_ids if str(i).strip()]
    if not ids:
        return []
    _ensure_db()
    placeholders = ",".join(["?"] * len(ids))
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            f"""
            SELECT reference_id, user_token, name, filename, collection_name, extracted_text, preview, created_at, updated_at
            FROM user_references
            WHERE user_token = ? AND reference_id IN ({placeholders})
            """,
            [user_token, *ids],
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    result: list[dict] = []
    for row in rows:
        (
            reference_id,
            owner,
            name,
            filename,
            collection_name,
            extracted_text,
            preview,
            created_at,
            updated_at,
        ) = row
        result.append(
            {
                "reference_id": reference_id,
                "user_token": owner,
                "name": name,
                "filename": filename,
                "collection_name": collection_name,
                "extracted_text": extracted_text or "",
                "preview": preview or "",
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )
    return result


def rename_user_reference(
    user_token: str, reference_id: str, new_name: str
) -> Optional[dict]:
    _ensure_db()
    now = int(time.time())
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE user_references SET name = ?, updated_at = ? WHERE reference_id = ? AND user_token = ?",
            (new_name, now, reference_id, user_token),
        )
        conn.commit()
        cur = conn.execute(
            """
            SELECT reference_id, user_token, name, filename, collection_name, preview, created_at, updated_at
            FROM user_references WHERE reference_id = ? AND user_token = ?
            """,
            (reference_id, user_token),
        )
        row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        return None
    ref_id, owner, name, filename, collection_name, preview, created_at, updated_at = (
        row
    )
    return {
        "reference_id": ref_id,
        "user_token": owner,
        "name": name,
        "filename": filename,
        "collection_name": collection_name,
        "preview": preview or "",
        "created_at": created_at,
        "updated_at": updated_at,
    }


def delete_user_reference(user_token: str, reference_id: str) -> Optional[str]:
    """Delete reference entry; returns collection_name so caller can clean up Chroma."""
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            "SELECT collection_name FROM user_references WHERE reference_id = ? AND user_token = ?",
            (reference_id, user_token),
        )
        row = cur.fetchone()
        if not row:
            return None
        collection_name = row[0]
        conn.execute(
            "DELETE FROM user_references WHERE reference_id = ? AND user_token = ?",
            (reference_id, user_token),
        )
        conn.commit()
    finally:
        conn.close()
    return collection_name


def rename_user_checklist(
    user_token: str, checklist_id: str, new_name: str
) -> Optional[dict]:
    _ensure_db()
    now = int(time.time())
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE user_checklists SET name = ?, updated_at = ? WHERE checklist_id = ? AND user_token = ?",
            (new_name, now, checklist_id, user_token),
        )
        conn.commit()
        cur = conn.execute(
            """
            SELECT checklist_id, user_token, name, items, created_at, updated_at
            FROM user_checklists WHERE checklist_id = ? AND user_token = ?
            """,
            (checklist_id, user_token),
        )
        row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        return None
    cid, owner, name, items, created_at, updated_at = row
    return {
        "checklist_id": cid,
        "user_token": owner,
        "name": name,
        "items": _deserialize_json(items) or [],
        "created_at": created_at,
        "updated_at": updated_at,
    }


def delete_user_checklist(user_token: str, checklist_id: str) -> bool:
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            "SELECT checklist_id FROM user_checklists WHERE checklist_id = ? AND user_token = ?",
            (checklist_id, user_token),
        )
        row = cur.fetchone()
        if not row:
            return False
        conn.execute(
            "DELETE FROM user_checklists WHERE checklist_id = ? AND user_token = ?",
            (checklist_id, user_token),
        )
        conn.commit()
    finally:
        conn.close()
    return True
