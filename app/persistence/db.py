"""Persistence layer for FincoGPT project runs.

Architecture: SQLite (file-based) via Python's built-in sqlite3.
Can be migrated to PostgreSQL later by swapping the db module.

Tables:
- runs: individual project runs (inputs + KPI outputs)
"""

import os
import json
import uuid
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import Optional, List

# ── DB path ───────────────────────────────────────────────────────────────────

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.getenv("FINCO_DB_PATH", os.path.join(DATA_DIR, "finco_runs.db"))

os.makedirs(DATA_DIR, exist_ok=True)

# ── Schema ───────────────────────────────────────────────────────────────────

INIT_SQL = """
CREATE TABLE IF NOT EXISTS runs (
    run_id       TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL,
    project_type TEXT NOT NULL,
    scenario     TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    inputs_json  TEXT NOT NULL,
    kpis_json    TEXT NOT NULL,
    excel_path   TEXT,
    notes        TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_user ON runs(user_id, created_at DESC);
"""

# ── Connection management ───────────────────────────────────────────────────

_connection = None

def get_connection():
    """Get a shared SQLite connection (thread-safe for single process)."""
    global _connection
    if _connection is None:
        import sqlite3
        _connection = sqlite3.connect(DB_PATH, check_same_thread=False)
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA journal_mode=WAL")
        _connection.execute("PRAGMA foreign_keys=ON")
        _connection.executescript(INIT_SQL)
        _connection.commit()
    return _connection

@contextmanager
def get_cursor():
    conn = get_connection()
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()

def close_connection():
    """Close and reset connection (for testing or restart)."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None