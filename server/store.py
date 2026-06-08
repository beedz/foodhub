"""SQLite-backed blob store. Holds one JSON document per user."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DOC = {"foods": {}, "log": {}}


def _db_path() -> str:
    return os.environ.get("DATABASE_PATH", "/data/foodhub.db")


def _connect() -> sqlite3.Connection:
    path = _db_path()
    # Ensure parent dir exists (e.g. /data on the Railway volume, or a local dir in dev).
    parent = Path(path).parent
    if str(parent) not in ("", "."):
        parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS store ("
        "  user_id TEXT PRIMARY KEY,"
        "  doc TEXT NOT NULL,"
        "  updated_at TEXT NOT NULL"
        ")"
    )
    return conn


def get_doc(user_id: str) -> tuple[dict, str | None]:
    """Return (document, updated_at). Falls back to a default empty doc."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT doc, updated_at FROM store WHERE user_id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return dict(DEFAULT_DOC), None
    return json.loads(row[0]), row[1]


def put_doc(user_id: str, doc: dict) -> str:
    """Replace the stored document. Returns the new updated_at timestamp."""
    updated_at = datetime.now(timezone.utc).isoformat()
    payload = json.dumps(doc)
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO store (user_id, doc, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET doc = excluded.doc, updated_at = excluded.updated_at",
            (user_id, payload, updated_at),
        )
        conn.commit()
    finally:
        conn.close()
    return updated_at
