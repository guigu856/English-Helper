"""SQLite connection + schema bootstrap."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS queries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key    TEXT NOT NULL UNIQUE,
    text         TEXT NOT NULL,
    task         TEXT NOT NULL,
    target_lang  TEXT NOT NULL,
    model        TEXT NOT NULL,
    result       TEXT NOT NULL,
    is_starred   INTEGER NOT NULL DEFAULT 0,
    hit_count    INTEGER NOT NULL DEFAULT 1,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_cache_key ON queries(cache_key);
CREATE INDEX IF NOT EXISTS idx_starred   ON queries(is_starred);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection and ensure schema exists."""
    p = Path(db_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: cache reads/writes are issued from the
    # StreamWorker QThread (not the Qt GUI thread). Concurrent access is
    # naturally serialized — at most one StreamWorker is alive at any time
    # (PopupWindow._cancel_worker before each new run, plus HotkeyBridge._busy
    # lock dropping rapid double-presses).
    conn = sqlite3.connect(
        str(p),
        detect_types=sqlite3.PARSE_DECLTYPES,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn
