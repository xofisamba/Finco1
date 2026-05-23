"""Lightweight SQLite persistence for runs, scenarios, and exports."""

import os
from contextlib import contextmanager

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.getenv("FINCO_DB_PATH", os.path.join(DATA_DIR, "finco_runs.db"))

os.makedirs(DATA_DIR, exist_ok=True)


def get_connection():
    """Return a fresh SQLite connection with schema ensured."""
    import sqlite3

    conn = sqlite3.connect(DB_PATH, timeout=30.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    _init_schema(conn)
    return conn


def _init_schema(conn):
    """Run schema creation on an open connection (idempotent)."""
    conn.execute(
        """
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
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_user ON runs(user_id, created_at DESC)")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            project_id               TEXT PRIMARY KEY,
            user_id                  TEXT NOT NULL,
            project_code             TEXT NOT NULL,
            project_name             TEXT NOT NULL,
            source_project_template  TEXT NOT NULL,
            governance_state_json    TEXT NOT NULL,
            last_run_summary_json    TEXT NOT NULL,
            created_at               TEXT NOT NULL,
            updated_at               TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_user_code ON projects(user_id, project_code)"
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scenarios (
            scenario_id               TEXT PRIMARY KEY,
            project_id                TEXT NOT NULL,
            user_id                   TEXT NOT NULL,
            scenario_name             TEXT NOT NULL,
            project_code              TEXT NOT NULL,
            source_project_template   TEXT NOT NULL,
            copied_from_scenario_id   TEXT,
            archived                  INTEGER NOT NULL DEFAULT 0,
            snapshot_json             TEXT NOT NULL,
            governance_state_json     TEXT NOT NULL,
            last_run_summary_json     TEXT NOT NULL,
            created_at                TEXT NOT NULL,
            updated_at                TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(project_id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_scenarios_user_project ON scenarios(user_id, project_id, archived, updated_at DESC)"
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scenario_exports (
            export_id                 TEXT PRIMARY KEY,
            scenario_id               TEXT,
            project_id                TEXT,
            user_id                   TEXT NOT NULL,
            export_type               TEXT NOT NULL,
            artifact_name             TEXT NOT NULL,
            artifact_path             TEXT,
            project_code              TEXT NOT NULL,
            governance_state_json     TEXT NOT NULL,
            runtime_snapshot_id       TEXT,
            created_at                TEXT NOT NULL,
            FOREIGN KEY(scenario_id) REFERENCES scenarios(scenario_id),
            FOREIGN KEY(project_id) REFERENCES projects(project_id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_exports_user_project ON scenario_exports(user_id, project_id, created_at DESC)"
    )
    conn.commit()


@contextmanager
def get_cursor():
    """Open a connection, yield a cursor, and close it automatically."""
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
    """Explicitly initialize the DB schema."""
    conn = get_connection()
    conn.close()
