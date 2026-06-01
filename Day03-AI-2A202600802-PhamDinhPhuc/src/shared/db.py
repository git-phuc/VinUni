from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared.common import ROOT_DIR


DEFAULT_DB_PATH = ROOT_DIR / "data" / "day03.sqlite3"


def db_path() -> Path:
    override = os.environ.get("DAY03_DB_PATH")
    return Path(override) if override else DEFAULT_DB_PATH


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                raw_note TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                raw_note TEXT NOT NULL,
                result_json TEXT NOT NULL,
                trace_json TEXT NOT NULL DEFAULT '[]',
                score_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS final_notes (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                content_json TEXT NOT NULL,
                approved_by TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );
            """
        )


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def create_session(title: str | None = None, raw_note: str = "") -> dict[str, Any]:
    init_db()
    now = utc_now()
    session_id = new_id("ses")
    clean_note = raw_note.strip()
    clean_title = (title or clean_note[:72] or "Phiên làm việc mới").strip()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO sessions (id, title, raw_note, status, created_at, updated_at)
            VALUES (?, ?, ?, 'draft', ?, ?)
            """,
            (session_id, clean_title, clean_note, now, now),
        )
    return get_session(session_id) or {}


def touch_session(session_id: str, raw_note: str | None = None, title: str | None = None, status: str | None = None) -> None:
    fields: list[str] = ["updated_at = ?"]
    values: list[Any] = [utc_now()]
    if raw_note is not None:
        fields.append("raw_note = ?")
        values.append(raw_note.strip())
    if title is not None and title.strip():
        fields.append("title = ?")
        values.append(title.strip())
    if status is not None:
        fields.append("status = ?")
        values.append(status)
    values.append(session_id)
    with connect() as conn:
        conn.execute(f"UPDATE sessions SET {', '.join(fields)} WHERE id = ?", values)


def list_sessions(limit: int = 50) -> list[dict[str, Any]]:
    init_db()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT s.*,
                   (SELECT mode FROM runs WHERE session_id = s.id ORDER BY created_at DESC LIMIT 1) AS last_mode,
                   (SELECT created_at FROM runs WHERE session_id = s.id ORDER BY created_at DESC LIMIT 1) AS last_run_at
            FROM sessions s
            ORDER BY s.updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_session(session_id: str) -> dict[str, Any] | None:
    init_db()
    with connect() as conn:
        session = row_to_dict(conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone())
        if not session:
            return None
        messages = conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        ).fetchall()
        runs = conn.execute(
            "SELECT * FROM runs WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,),
        ).fetchall()
        finals = conn.execute(
            "SELECT * FROM final_notes WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,),
        ).fetchall()
    session["messages"] = [dict(row) for row in messages]
    session["runs"] = [decode_run(row) for row in runs]
    session["final_notes"] = [decode_final(row) for row in finals]
    return session


def add_message(session_id: str, role: str, content: str) -> dict[str, Any]:
    init_db()
    now = utc_now()
    message = {
        "id": new_id("msg"),
        "session_id": session_id,
        "role": role,
        "content": content.strip(),
        "created_at": now,
    }
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO messages (id, session_id, role, content, created_at)
            VALUES (:id, :session_id, :role, :content, :created_at)
            """,
            message,
        )
    touch_session(session_id)
    return message


def add_run(
    session_id: str,
    mode: str,
    raw_note: str,
    result: dict[str, Any],
    trace: list[dict[str, Any]] | None = None,
    score: dict[str, Any] | None = None,
) -> dict[str, Any]:
    init_db()
    now = utc_now()
    run = {
        "id": new_id("run"),
        "session_id": session_id,
        "mode": mode,
        "raw_note": raw_note.strip(),
        "result_json": json.dumps(result, ensure_ascii=False),
        "trace_json": json.dumps(trace or [], ensure_ascii=False),
        "score_json": json.dumps(score or {}, ensure_ascii=False),
        "created_at": now,
    }
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO runs (id, session_id, mode, raw_note, result_json, trace_json, score_json, created_at)
            VALUES (:id, :session_id, :mode, :raw_note, :result_json, :trace_json, :score_json, :created_at)
            """,
            run,
        )
    touch_session(session_id, raw_note=raw_note)
    return decode_run(run)


def add_final_note(session_id: str, content: dict[str, Any], approved_by: str = "") -> dict[str, Any]:
    init_db()
    now = utc_now()
    final_note = {
        "id": new_id("fin"),
        "session_id": session_id,
        "content_json": json.dumps(content, ensure_ascii=False),
        "approved_by": approved_by.strip(),
        "created_at": now,
    }
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO final_notes (id, session_id, content_json, approved_by, created_at)
            VALUES (:id, :session_id, :content_json, :approved_by, :created_at)
            """,
            final_note,
        )
    touch_session(session_id, status="finalized")
    return decode_final(final_note)


def latest_run(session: dict[str, Any]) -> dict[str, Any] | None:
    runs = session.get("runs") or []
    return runs[0] if runs else None


def decode_run(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    data = dict(row)
    return {
        "id": data["id"],
        "session_id": data["session_id"],
        "mode": data["mode"],
        "raw_note": data["raw_note"],
        "result": json.loads(data["result_json"]),
        "trace": json.loads(data["trace_json"] or "[]"),
        "score": json.loads(data["score_json"] or "{}"),
        "created_at": data["created_at"],
    }


def decode_final(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    data = dict(row)
    return {
        "id": data["id"],
        "session_id": data["session_id"],
        "content": json.loads(data["content_json"]),
        "approved_by": data["approved_by"],
        "created_at": data["created_at"],
    }
