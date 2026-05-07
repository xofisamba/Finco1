"""Persistence layer for FincoGPT project runs.

Architecture: SQLite (file-based) via Python's built-in sqlite3.
Can be migrated to PostgreSQL later by swapping the db module.

SQLite connection strategy: connection-per-operation.
Each get_cursor() / get_connection() call creates a fresh connection,
uses it, and closes it. This is safe under gunicorn multi-thread workers
because SQLite's file-level locking serializes writes, while WAL allows
concurrent reads across connections.

Tables:
- runs: individual project runs (inputs + KPI outputs)
"""

import os
from contextlib import contextmanager

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
# Strategy: connection-per-operation (no shared global connection).
# Each call to get_connection() opens a fresh connection to DB_PATH.
# This is safe under threaded gunicorn workers — SQLite handles
# file-level locking + WAL for concurrent access.
#
# Idempotency: PRAGMA journal_mode=WAL and CREATE TABLE IF NOT EXISTS
# mean init is safe to call on every get_connection() call.
#
# Future PostgreSQL migration: replace this module with SQLAlchemy engine;
# keep the same get_connection() / get_cursor() API.

def get_connection():
    """Return a new SQLite connection to finco_runs.db.
    
    Connection-per-operation: each call creates a fresh connection.
    WAL mode and schema init are applied on every new connection.
    """
    import sqlite3
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    # Schema init: idempotent, safe to call on every new connection
    _init_schema(conn)
    return conn


def _init_schema(conn):
    """Run schema creation on an open connection (idempotent)."""
    conn.execute("""
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
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_user ON runs(user_id, created_at DESC)")
    conn.commit()


@contextmanager
def get_cursor():
    """Context manager: opens a connection, yields cursor, auto-closes.
    
    Usage:
        with get_cursor() as cur:
            cur.execute("SELECT ...")
            rows = cur.fetchall()
        # connection automatically closed and committed
    """
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
        conn.close()


def init_db():
    """Explicitly initialise the DB schema (idempotent). Call at app startup.
    
    Safe to call multiple times — CREATE TABLE IF NOT EXISTS ensures idempotency.
    """
    conn = get_connection()
    conn.close()  # schema init happens inside get_connection via _init_schema()