"""Checkpointer adapter.

Provides LangGraph checkpointers for persistence/recovery:
- "none"     -> no persistence
- "memory"   -> in-process MemorySaver (default; good for tests/CI)
- "sqlite"   -> SqliteSaver backed by an on-disk DB with WAL mode (survives process restart)
- "postgres" -> PostgresSaver (optional extension)
"""

from __future__ import annotations

from typing import Any


def _sqlite_path(database_url: str | None) -> str:
    """Resolve a filesystem path from an optional sqlite URL or plain path."""
    if not database_url:
        return "checkpoints.db"
    # Accept both "sqlite:///file.db" style URLs and bare paths.
    for prefix in ("sqlite:///", "sqlite://"):
        if database_url.startswith(prefix):
            return database_url[len(prefix):] or "checkpoints.db"
    return database_url


def build_checkpointer(kind: str = "memory", database_url: str | None = None) -> Any | None:
    """Return a LangGraph checkpointer for the requested backend."""
    if kind == "none":
        return None

    if kind == "memory":
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()

    if kind == "sqlite":
        import sqlite3

        from langgraph.checkpoint.sqlite import SqliteSaver

        path = _sqlite_path(database_url)
        # check_same_thread=False so the same connection works across LangGraph's threads.
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")  # durable + concurrent reads while writing
        # langgraph-checkpoint-sqlite 3.x: construct with conn= (NOT from_conn_string()).
        saver = SqliteSaver(conn=conn)
        saver.setup()  # create checkpoint tables if missing
        return saver

    if kind == "postgres":
        from langgraph.checkpoint.postgres import PostgresSaver

        if not database_url:
            raise ValueError("postgres checkpointer requires database_url")
        saver = PostgresSaver.from_conn_string(database_url)
        saver.setup()
        return saver

    raise ValueError(f"Unknown checkpointer kind: {kind}")
