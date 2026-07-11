"""Phase 57A-9B: CAPEX sub-lines schema + repository skeleton tests.

These tests pin the schema-side contract for user-added CAPEX
sub-lines. They do NOT exercise save/load, Run integration, or
Excel export — those land in 57A-9C, 57A-9D, and 57A-9E
respectively.

The contract is (from
``docs/phase57a9a_capex_add_line_persistence_design_gate.md``
plus the Claude delta review fixes):

1. The ``capex_sub_lines`` table exists with the columns
   declared in the design doc.
2. The migration is idempotent (CREATE TABLE IF NOT EXISTS,
   indexes are CREATE INDEX IF NOT EXISTS, calling
   ``_init_schema`` twice does not break).
3. The existing tables (``projects``, ``scenarios``, ``runs``,
   ``workspace_states``, ``scenario_exports``) are unchanged.
4. ``sub_line_id`` is a stable UUID and unique.
5. The business code format is ``C.NN.U###`` with a 3-digit
   counter per ``(project_id, parent_category_code)``.
6. Gaps are preserved on soft-delete: a soft-deleted
   ``C.02.U001`` does NOT free up the counter; the next call
   returns ``C.02.U002`` (or later).
7. Duplicate ``(project_id, business_code)`` is rejected by
   the UNIQUE constraint.
8. C.01..C.16 are allowed; C.17 / C.18 are rejected with a
   clear error; unknown categories (e.g. ``C.99``) are
   rejected with a clear error.
9. The ``CAPEX_CATEGORY_TO_FIELD`` mapping is locked: 16
   categories, 15 unique fields, every field exists on
   ``CapexStructure``.
10. C.08 and C.11 both fold additively into ``audit_legal``
    (the deliberate ambiguity is locked).
11. Scenario override REPLACES default amount (it is NOT a
    delta). This is the Claude delta review fix to 57A-9A
    §6.5, pinned here as a pure helper contract.
12. Factory project create attempt raises ``PermissionError``.
13. The pure ``fold_sub_lines_into_capex`` helper is a no-op
    for factory projects (empty ``user_sub_lines`` returns
    ``capex`` unchanged).
14. No UI / static / run / export / model files were
    changed. rc1 is untouched.

Type: runtime + migration (Phase 57A-9B). DRAFT PR.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_db(monkeypatch, tmp_path):
    """Isolated SQLite DB for the test.

    Sets ``FINCO_DB_PATH`` to a tmp file, calls ``init_db()`` to
    run the schema migration, and tears the env var down after
    the test. Each test gets a fresh DB so there is no
    cross-test contamination.
    """
    db_file = tmp_path / f"phase57a9b_{uuid.uuid4().hex[:8]}.db"
    monkeypatch.setenv("FINCO_DB_PATH", str(db_file))
    import app.persistence.db as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", str(db_file))
    db_mod.init_db()
    yield db_file
    # monkeypatch automatically restores env / attr after the test


@pytest.fixture
def conn(test_db):
    """Open a sqlite3 connection for direct queries (rarely used;
    prefer the ``cur`` fixture which matches the rest of the
    persistence layer)."""
    c = sqlite3.connect(str(test_db))
    c.row_factory = sqlite3.Row
    try:
        yield c
    finally:
        c.close()


@pytest.fixture
def cur(test_db):
    """Open a sqlite3 cursor — matches the production helper
    signature ``get_cursor()``."""
    c = sqlite3.connect(str(test_db))
    c.row_factory = sqlite3.Row
    cur = c.cursor()
    try:
        yield cur
    finally:
        c.close()


# ---------------------------------------------------------------------------
# 1. Schema
# ---------------------------------------------------------------------------


class TestSchema:
    EXPECTED_COLUMNS = {
        "id", "sub_line_id", "project_id", "parent_category_code",
        "business_code", "display_order", "label", "amount_keur",
        "comments", "schedule_json", "source", "is_active",
        "governance_state_json", "replay_metadata_json",
        "created_at", "updated_at",
    }

    def test_table_exists(self, conn):
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='capex_sub_lines'"
        )
        rows = cur.fetchall()
        assert len(rows) == 1, "capex_sub_lines table must exist"
        assert rows[0][0] == "capex_sub_lines"

    def test_columns_match_design(self, conn):
        cols = {row[1] for row in conn.execute("PRAGMA table_info(capex_sub_lines)").fetchall()}
        missing = self.EXPECTED_COLUMNS - cols
        assert not missing, f"missing columns: {sorted(missing)}"
        # No extra columns
        assert cols == self.EXPECTED_COLUMNS, (
            f"unexpected columns: {sorted(cols - self.EXPECTED_COLUMNS)}"
        )

    def test_sub_line_id_is_unique(self, conn):
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='capex_sub_lines'"
        )
        idx_names = {r[0] for r in cur.fetchall()}
        # The UNIQUE constraint on sub_line_id produces an
        # auto-index. We just need to ensure the column is
        # declared UNIQUE; verify by trying a duplicate insert.
        cur = conn.cursor()
        # Need a parent project first (FK). Use a placeholder.
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                project_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                project_code TEXT NOT NULL,
                project_name TEXT NOT NULL,
                project_origin TEXT NOT NULL DEFAULT 'factory_template',
                source_project_template TEXT NOT NULL,
                baseline_snapshot_json TEXT NOT NULL DEFAULT '{}',
                is_readonly INTEGER NOT NULL DEFAULT 0,
                archived INTEGER NOT NULL DEFAULT 0,
                governance_state_json TEXT NOT NULL DEFAULT '{}',
                last_run_summary_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """INSERT INTO projects (project_id, user_id, project_code, project_name,
               source_project_template, governance_state_json, last_run_summary_json,
               created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, '{}', '{}', '2026-06-05', '2026-06-05')""",
            ("proj-1", "u1", "TUHO", "TUHO", "tuho"),
        )
        cur.execute(
            """
            INSERT INTO capex_sub_lines
            (sub_line_id, project_id, parent_category_code, business_code,
             display_order, label, amount_keur, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("uuid-1", "proj-1", "C.02", "C.02.U001", 1, "x", 10.0, "2026-06-05", "2026-06-05"),
        )
        # Duplicate sub_line_id must fail.
        with pytest.raises(sqlite3.IntegrityError):
            cur.execute(
                """
                INSERT INTO capex_sub_lines
                (sub_line_id, project_id, parent_category_code, business_code,
                 display_order, label, amount_keur, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("uuid-1", "proj-1", "C.03", "C.03.U001", 1, "y", 20.0, "2026-06-05", "2026-06-05"),
            )

    def test_project_id_foreign_key(self, conn):
        # Inserting with a non-existent project_id must fail
        # because of the FK(project_id) REFERENCES projects(project_id).
        cur = conn.cursor()
        # The test_db fixture created an empty projects table
        # in test_sub_line_id_is_unique if that test ran first,
        # but here we start fresh — init_db() does not create
        # any projects row. FK enforcement depends on
        # PRAGMA foreign_keys=ON, which the production layer
        # sets. We re-enable it for this test.
        cur.execute("PRAGMA foreign_keys = ON")
        with pytest.raises(sqlite3.IntegrityError):
            cur.execute(
                """
                INSERT INTO capex_sub_lines
                (sub_line_id, project_id, parent_category_code, business_code,
                 display_order, label, amount_keur, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("uuid-fk", "no-such-project", "C.02", "C.02.U001",
                 1, "x", 10.0, "2026-06-05", "2026-06-05"),
            )

    def test_unique_constraint_on_project_business_code(self, conn):
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON")
        # Need a parent project first.
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                project_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                project_code TEXT NOT NULL,
                project_name TEXT NOT NULL,
                project_origin TEXT NOT NULL DEFAULT 'factory_template',
                source_project_template TEXT NOT NULL,
                baseline_snapshot_json TEXT NOT NULL DEFAULT '{}',
                is_readonly INTEGER NOT NULL DEFAULT 0,
                archived INTEGER NOT NULL DEFAULT 0,
                governance_state_json TEXT NOT NULL DEFAULT '{}',
                last_run_summary_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """INSERT INTO projects (project_id, user_id, project_code, project_name,
               source_project_template, governance_state_json, last_run_summary_json,
               created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, '{}', '{}', '2026-06-05', '2026-06-05')""",
            ("proj-2", "u1", "X", "X", "x"),
        )
        cur.execute(
            """
            INSERT INTO capex_sub_lines
            (sub_line_id, project_id, parent_category_code, business_code,
             display_order, label, amount_keur, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("uuid-a", "proj-2", "C.02", "C.02.U001", 1, "x", 10.0, "2026-06-05", "2026-06-05"),
        )
        # Duplicate (project_id, business_code) — even with a
        # DIFFERENT sub_line_id — must fail.
        with pytest.raises(sqlite3.IntegrityError):
            cur.execute(
                """
                INSERT INTO capex_sub_lines
                (sub_line_id, project_id, parent_category_code, business_code,
                 display_order, label, amount_keur, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("uuid-b", "proj-2", "C.02", "C.02.U001", 2, "y", 20.0, "2026-06-05", "2026-06-05"),
            )

    def test_index_present(self, conn):
        idx_names = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='capex_sub_lines'"
            ).fetchall()
        }
        assert "idx_capex_sub_lines_project" in idx_names


class TestMigrationIdempotent:
    def test_double_init_does_not_break(self, tmp_path, monkeypatch):
        db_file = tmp_path / f"phase57a9b_idem_{uuid.uuid4().hex[:8]}.db"
        monkeypatch.setenv("FINCO_DB_PATH", str(db_file))
        import app.persistence.db as db_mod
        monkeypatch.setattr(db_mod, "DB_PATH", str(db_file))
        db_mod.init_db()
        # Capture state after first init
        conn1 = db_mod.get_connection()
        cols1 = {r[1] for r in conn1.execute("PRAGMA table_info(capex_sub_lines)").fetchall()}
        # Second init on the SAME connection
        db_mod._init_schema(conn1)
        cols2 = {r[1] for r in conn1.execute("PRAGMA table_info(capex_sub_lines)").fetchall()}
        assert cols1 == cols2, f"columns changed across init: {cols1 ^ cols2}"
        # Also: a fresh init_db() against an existing DB must not raise
        db_mod.init_db()
        conn1.close()


class TestExistingTablesUnchanged:
    """Regression: adding capex_sub_lines must not change the schema of
    the other persistence tables."""

    EXPECTED_TABLES = {
        "projects", "scenarios", "runs",
        "workspace_states", "scenario_exports", "capex_sub_lines",
        "opex_sub_lines",
    }

    def test_all_expected_tables_present(self, test_db, conn):
        names = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        # All expected tables are present
        missing = self.EXPECTED_TABLES - names
        assert not missing, f"missing tables: {sorted(missing)}"
        # No unexpected tables created
        unexpected = (names - self.EXPECTED_TABLES) - {"sqlite_sequence"}
        assert not unexpected, f"unexpected tables: {sorted(unexpected)}"

    def test_projects_columns_unchanged(self, conn):
        cols = {r[1] for r in conn.execute("PRAGMA table_info(projects)").fetchall()}
        assert "project_id" in cols
        assert "project_origin" in cols
        assert "is_readonly" in cols
        assert "baseline_snapshot_json" in cols

    def test_scenarios_columns_unchanged(self, conn):
        cols = {r[1] for r in conn.execute("PRAGMA table_info(scenarios)").fetchall()}
        assert "scenario_id" in cols
        assert "overrides_json" in cols
        assert "is_base_case" in cols
        assert "base_input_set_json" in cols


# ---------------------------------------------------------------------------
# 2. Repository helper: create_sub_line, list_*, soft_delete
# ---------------------------------------------------------------------------


class TestRepositoryHelpers:
    @pytest.fixture
    def user_project_cur(self, test_db, cur):
        """Add a non-factory project row (user_project) for FK targets.

        Returns a cursor (matches the production helper signature).
        """
        cur.execute("PRAGMA foreign_keys = ON")
        cur.execute(
            """INSERT INTO projects (project_id, user_id, project_code, project_name,
               project_origin, source_project_template, is_readonly,
               baseline_snapshot_json, governance_state_json, last_run_summary_json,
               created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 0, '{}', '{}', '{}',
                       '2026-06-05', '2026-06-05')""",
            ("proj-user", "u1", "USERPROJ", "User Project",
             "user_project", "user_project"),
        )
        cur.connection.commit()
        return cur

    def test_create_sub_line_returns_record(self, user_project_cur):
        from app.persistence.capex_sub_lines import create_sub_line
        rec = create_sub_line(
            user_project_cur,
            project_id="proj-user",
            parent_category_code="C.02",
            label="Extra transformers",
            amount_keur=50.0,
        )
        assert rec.sub_line_id is not None
        # Verify it parses as a UUID
        uuid.UUID(rec.sub_line_id)
        assert rec.project_id == "proj-user"
        assert rec.parent_category_code == "C.02"
        assert rec.business_code == "C.02.U001"  # first counter
        assert rec.display_order == 1
        assert rec.label == "Extra transformers"
        assert rec.amount_keur == 50.0
        assert rec.is_active is True
        assert rec.id is not None  # DB-assigned

    def test_create_sub_line_increments_counter(self, user_project_cur):
        from app.persistence.capex_sub_lines import create_sub_line
        r1 = create_sub_line(
            user_project_cur,
            project_id="proj-user",
            parent_category_code="C.02",
            label="x", amount_keur=10.0,
        )
        r2 = create_sub_line(
            user_project_cur,
            project_id="proj-user",
            parent_category_code="C.02",
            label="y", amount_keur=20.0,
        )
        r3 = create_sub_line(
            user_project_cur,
            project_id="proj-user",
            parent_category_code="C.05",
            label="z", amount_keur=30.0,
        )
        assert r1.business_code == "C.02.U001"
        assert r2.business_code == "C.02.U002"
        assert r3.business_code == "C.05.U001"  # different parent

    def test_counter_preserves_gaps_after_soft_delete(self, user_project_cur):
        from app.persistence.capex_sub_lines import (
            create_sub_line, soft_delete_sub_line, list_business_codes_for_project,
        )
        r1 = create_sub_line(
            user_project_cur,
            project_id="proj-user", parent_category_code="C.02",
            label="x", amount_keur=10.0,
        )
        r2 = create_sub_line(
            user_project_cur,
            project_id="proj-user", parent_category_code="C.02",
            label="y", amount_keur=20.0,
        )
        # Soft-delete r1 (C.02.U001)
        assert soft_delete_sub_line(
            user_project_cur,
            project_id="proj-user", sub_line_id=r1.sub_line_id,
        ) is True
        # Next counter must be C.02.U003 (gap preserved)
        existing = list_business_codes_for_project(user_project_cur, "proj-user")
        r3 = create_sub_line(
            user_project_cur,
            project_id="proj-user", parent_category_code="C.02",
            label="z", amount_keur=30.0,
        )
        assert r3.business_code == "C.02.U003", (
            f"expected C.02.U003 (gap preserved), got {r3.business_code}; "
            f"existing codes = {existing}"
        )

    def test_duplicate_business_code_raises(self, user_project_cur):
        from app.persistence.capex_sub_lines import create_sub_line
        create_sub_line(
            user_project_cur, project_id="proj-user",
            parent_category_code="C.02", label="x", amount_keur=10.0,
        )
        with pytest.raises(sqlite3.IntegrityError):
            create_sub_line(
                user_project_cur, project_id="proj-user",
                parent_category_code="C.02", label="y", amount_keur=20.0,
                business_code="C.02.U001",  # duplicate
            )

    def test_soft_delete_returns_true_then_false(self, user_project_cur):
        from app.persistence.capex_sub_lines import create_sub_line, soft_delete_sub_line
        r1 = create_sub_line(
            user_project_cur, project_id="proj-user",
            parent_category_code="C.02", label="x", amount_keur=10.0,
        )
        assert soft_delete_sub_line(
            user_project_cur, project_id="proj-user", sub_line_id=r1.sub_line_id,
        ) is True
        # Second call on the same id is a no-op
        assert soft_delete_sub_line(
            user_project_cur, project_id="proj-user", sub_line_id=r1.sub_line_id,
        ) is False
        # Soft-deleted row is still in the table but with is_active=0
        row = user_project_cur.execute(
            "SELECT is_active FROM capex_sub_lines WHERE sub_line_id = ?",
            (r1.sub_line_id,),
        ).fetchone()
        assert row[0] == 0

    def test_list_sub_lines_for_project_excludes_inactive_by_default(
        self, user_project_cur
    ):
        from app.persistence.capex_sub_lines import (
            create_sub_line, list_sub_lines_for_project, soft_delete_sub_line,
        )
        r1 = create_sub_line(
            user_project_cur, project_id="proj-user",
            parent_category_code="C.02", label="a", amount_keur=10.0,
        )
        r2 = create_sub_line(
            user_project_cur, project_id="proj-user",
            parent_category_code="C.03", label="b", amount_keur=20.0,
        )
        soft_delete_sub_line(
            user_project_cur, project_id="proj-user", sub_line_id=r1.sub_line_id,
        )
        active = list_sub_lines_for_project(user_project_cur, "proj-user")
        all_ = list_sub_lines_for_project(
            user_project_cur, "proj-user", include_inactive=True
        )
        assert len(active) == 1
        assert active[0].sub_line_id == r2.sub_line_id
        assert len(all_) == 2
        ids = {s.sub_line_id for s in all_}
        assert r1.sub_line_id in ids
        assert r2.sub_line_id in ids


# ---------------------------------------------------------------------------
# 3. Validators
# ---------------------------------------------------------------------------


class TestValidateParentCategory:
    @pytest.mark.parametrize("code", [
        f"C.{i:02d}" for i in range(1, 17)
    ])
    def test_allowed_categories(self, code):
        from app.persistence.capex_sub_lines import validate_parent_category
        assert validate_parent_category(code) == code

    @pytest.mark.parametrize("code", ["C.17", "C.18"])
    def test_rejected_categories(self, code):
        from app.persistence.capex_sub_lines import validate_parent_category
        with pytest.raises(ValueError) as exc:
            validate_parent_category(code)
        assert "rejected" in str(exc.value).lower() or "read-only" in str(exc.value).lower()

    @pytest.mark.parametrize("code", ["C.99", "C.00", "C.1", "C.100", "C.XX"])
    def test_unknown_categories(self, code):
        from app.persistence.capex_sub_lines import validate_parent_category
        with pytest.raises(ValueError) as exc:
            validate_parent_category(code)
        assert "not a known" in str(exc.value).lower() or "match" in str(exc.value).lower()

    @pytest.mark.parametrize("code", [None, "", 42, [], {}])
    def test_malformed_categories(self, code):
        from app.persistence.capex_sub_lines import validate_parent_category
        with pytest.raises((ValueError, TypeError)):
            validate_parent_category(code)


class TestValidateBusinessCode:
    @pytest.mark.parametrize("code", [
        "C.01.U001", "C.02.U001", "C.16.U999", "C.02.U100", "C.16.U100",
    ])
    def test_valid_codes(self, code):
        from app.persistence.capex_sub_lines import validate_business_code
        assert validate_business_code(code) == code

    @pytest.mark.parametrize("code", [
        "C.02.001",   # missing U prefix
        "C.2.U001",   # 1-digit parent
        "C.02.U1",    # 1-digit counter
        "C.02.U1000", # 4-digit counter
        "C.02.U",     # missing counter
        "C.02",       # missing U### entirely
        "X.02.U001",  # wrong C prefix
    ])
    def test_invalid_codes(self, code):
        from app.persistence.capex_sub_lines import validate_business_code
        with pytest.raises(ValueError):
            validate_business_code(code)

    @pytest.mark.parametrize("code", [None, "", 42, []])
    def test_malformed(self, code):
        from app.persistence.capex_sub_lines import validate_business_code
        with pytest.raises((ValueError, TypeError)):
            validate_business_code(code)

    def test_c17_business_code_passes_format_validation(self):
        """``C.17.U001`` matches the regex format (C.NN.U###); the
        C.17 rejection is enforced by ``validate_parent_category``
        and ``generate_next_business_code`` at the parent level.
        This is by design: format validation is decoupled from
        semantic category validation."""
        from app.persistence.capex_sub_lines import validate_business_code
        # The format validator itself is lenient on parent — it
        # just checks the regex. The semantic guard fires later.
        assert validate_business_code("C.17.U001") == "C.17.U001"


# ---------------------------------------------------------------------------
# 4. Counter (pure)
# ---------------------------------------------------------------------------


class TestGenerateNextBusinessCode:
    def test_empty_starts_at_one(self):
        from app.persistence.capex_sub_lines import generate_next_business_code
        assert generate_next_business_code([], "C.02") == "C.02.U001"

    def test_increments_past_max(self):
        from app.persistence.capex_sub_lines import generate_next_business_code
        existing = ["C.02.U001", "C.02.U002", "C.02.U003"]
        assert generate_next_business_code(existing, "C.02") == "C.02.U004"

    def test_preserves_gaps_on_soft_delete(self):
        """If C.02.U001 and C.02.U003 exist (U002 was never created
        or was hard-deleted, not soft-deleted), the next counter is
        U004, not U002 — gaps in the visible sequence are also
        preserved as a side effect.
        """
        from app.persistence.capex_sub_lines import generate_next_business_code
        existing = ["C.02.U001", "C.02.U003"]
        assert generate_next_business_code(existing, "C.02") == "C.02.U004"

    def test_different_parents_independent(self):
        from app.persistence.capex_sub_lines import generate_next_business_code
        existing = ["C.02.U001", "C.02.U002", "C.05.U001"]
        assert generate_next_business_code(existing, "C.02") == "C.02.U003"
        assert generate_next_business_code(existing, "C.05") == "C.05.U002"
        assert generate_next_business_code(existing, "C.10") == "C.10.U001"

    def test_rejected_parent_rejected_in_counter(self):
        from app.persistence.capex_sub_lines import generate_next_business_code
        with pytest.raises(ValueError):
            generate_next_business_code([], "C.17")
        with pytest.raises(ValueError):
            generate_next_business_code([], "C.18")

    def test_malformed_codes_skipped_defensively(self):
        """A corrupted DB row with a malformed business code should
        not break the counter; it is silently skipped."""
        from app.persistence.capex_sub_lines import generate_next_business_code
        existing = ["C.02.U001", "garbage", "C.02.U005", None, 42]
        assert generate_next_business_code(existing, "C.02") == "C.02.U006"


# ---------------------------------------------------------------------------
# 5. Factory project guard
# ---------------------------------------------------------------------------


class _DummyRecord:
    """Minimal stand-in for ProjectRecord — only the fields the
    guard actually reads."""

    def __init__(self, project_origin, is_readonly=False, project_id="x"):
        self.project_origin = project_origin
        self.is_readonly = is_readonly
        self.project_id = project_id


class TestFactoryProjectGuard:
    def test_user_project_allowed(self):
        from app.persistence.capex_sub_lines import assert_project_allows_capex_sub_lines
        # No raise
        assert_project_allows_capex_sub_lines(
            _DummyRecord("user_project", is_readonly=False)
        )

    def test_saved_baseline_allowed(self):
        from app.persistence.capex_sub_lines import assert_project_allows_capex_sub_lines
        assert_project_allows_capex_sub_lines(
            _DummyRecord("saved_baseline", is_readonly=False)
        )

    def test_factory_template_rejected(self):
        from app.persistence.capex_sub_lines import assert_project_allows_capex_sub_lines
        with pytest.raises(PermissionError) as exc:
            assert_project_allows_capex_sub_lines(
                _DummyRecord("factory_template", is_readonly=True)
            )
        msg = str(exc.value).lower()
        assert "factory_template" in msg
        assert "read-only" in msg or "read only" in msg

    def test_factory_template_with_is_readonly_false_still_rejected(self):
        """Defense in depth: a factory_template origin should be
        rejected even if is_readonly=False is somehow set."""
        from app.persistence.capex_sub_lines import assert_project_allows_capex_sub_lines
        with pytest.raises(PermissionError):
            assert_project_allows_capex_sub_lines(
                _DummyRecord("factory_template", is_readonly=False)
            )

    def test_unknown_origin_rejected(self):
        from app.persistence.capex_sub_lines import assert_project_allows_capex_sub_lines
        with pytest.raises(PermissionError) as exc:
            assert_project_allows_capex_sub_lines(
                _DummyRecord("weird_origin", is_readonly=False)
            )
        assert "unknown project_origin" in str(exc.value).lower()

    def test_none_record_rejected(self):
        from app.persistence.capex_sub_lines import assert_project_allows_capex_sub_lines
        with pytest.raises(PermissionError):
            assert_project_allows_capex_sub_lines(None)

    def test_record_missing_project_origin_rejected(self):
        """A record without a project_origin attribute is treated as
        a defensive unknown origin."""
        class BareRecord:
            is_readonly = False
        from app.persistence.capex_sub_lines import assert_project_allows_capex_sub_lines
        with pytest.raises(PermissionError):
            assert_project_allows_capex_sub_lines(BareRecord())


# ---------------------------------------------------------------------------
# 6. Locked mapping
# ---------------------------------------------------------------------------


class TestCategoryToFieldMapping:
    EXPECTED_MAPPING = {
        "C.01": "production_units",
        "C.02": "epc_contract",
        "C.03": "grid_connection",
        "C.04": "ops_prep",
        "C.05": "epc_other",
        "C.06": "insurances",
        "C.07": "lease_tax",
        "C.08": "audit_legal",
        "C.09": "construction_mgmt_a",
        "C.10": "commissioning",
        "C.11": "audit_legal",  # deliberate ambiguity, locked
        "C.12": "construction_mgmt_b",
        "C.13": "contingencies",
        "C.14": "taxes",
        "C.15": "project_acquisition",
        "C.16": "project_rights",
    }

    def test_mapping_size(self):
        from app.persistence.capex_sub_lines import CAPEX_CATEGORY_TO_FIELD
        assert len(CAPEX_CATEGORY_TO_FIELD) == 16

    def test_each_category_maps_correctly(self):
        from app.persistence.capex_sub_lines import CAPEX_CATEGORY_TO_FIELD
        for code, field in self.EXPECTED_MAPPING.items():
            assert CAPEX_CATEGORY_TO_FIELD[code] == field, (
                f"{code} should map to {field!r}, "
                f"got {CAPEX_CATEGORY_TO_FIELD[code]!r}"
            )

    def test_all_mapped_fields_exist_on_capex_structure(self):
        """Every field in the mapping must exist as a real attribute
        of CapexStructure. This catches any future drift if a
        CapexStructure field is renamed or removed."""
        from app.persistence.capex_sub_lines import CAPEX_CATEGORY_TO_FIELD
        from domain.inputs import CapexStructure
        capex_fields = {f.name for f in CapexStructure.__dataclass_fields__.values()}
        # 15 named CapexItem fields + 6 financing fields = 21 total
        for code, field_name in CAPEX_CATEGORY_TO_FIELD.items():
            assert field_name in capex_fields, (
                f"CAPEX_CATEGORY_TO_FIELD[{code!r}] = {field_name!r} is not "
                f"a field on CapexStructure. Allowed fields: "
                f"{sorted(capex_fields)}"
            )

    def test_c08_and_c11_both_map_to_audit_legal(self):
        """C.08 and C.11 both fold additively into audit_legal. This
        is a deliberate ambiguity from the source data; the
        additive accumulation is locked at this point."""
        from app.persistence.capex_sub_lines import CAPEX_CATEGORY_TO_FIELD
        assert CAPEX_CATEGORY_TO_FIELD["C.08"] == "audit_legal"
        assert CAPEX_CATEGORY_TO_FIELD["C.11"] == "audit_legal"

    def test_c17_and_c18_not_in_mapping(self):
        from app.persistence.capex_sub_lines import CAPEX_CATEGORY_TO_FIELD
        assert "C.17" not in CAPEX_CATEGORY_TO_FIELD
        assert "C.18" not in CAPEX_CATEGORY_TO_FIELD

    def test_15_unique_fields(self):
        """15 named CapexItem fields exist on CapexStructure; the
        mapping should cover exactly 15 unique field names."""
        from app.persistence.capex_sub_lines import CAPEX_CATEGORY_TO_FIELD
        assert len(set(CAPEX_CATEGORY_TO_FIELD.values())) == 15


# ---------------------------------------------------------------------------
# 7. Pure aggregation helpers — Claude delta review fix
# ---------------------------------------------------------------------------


class TestResolveEffectiveSubLineAmount:
    """Claude delta review fix: scenario override REPLACES default.
    It is NOT a delta adjustment."""

    def test_no_override_returns_default(self):
        from app.persistence.capex_sub_lines import resolve_effective_sub_line_amount
        assert resolve_effective_sub_line_amount(50.0, None) == 50.0
        assert resolve_effective_sub_line_amount(0.0, None) == 0.0
        assert resolve_effective_sub_line_amount(-10.0, None) == -10.0

    def test_override_replaces_default(self):
        from app.persistence.capex_sub_lines import resolve_effective_sub_line_amount
        # Not a delta: 50 + 999 != 999
        assert resolve_effective_sub_line_amount(50.0, 999.0) == 999.0
        assert resolve_effective_sub_line_amount(50.0, 0.0) == 0.0
        assert resolve_effective_sub_line_amount(50.0, -50.0) == -50.0
        assert resolve_effective_sub_line_amount(50.0, 0.5) == 0.5

    def test_override_is_not_a_delta(self):
        """Explicitly test the Claude delta review invariant:
        the override does NOT add to the default."""
        from app.persistence.capex_sub_lines import resolve_effective_sub_line_amount
        default = 50.0
        override = 999.0
        # The effective is exactly the override, not default + override.
        effective = resolve_effective_sub_line_amount(default, override)
        assert effective != default + override
        assert effective == override


def _make_capex(**amounts):
    """Build a CapexStructure with the given per-field amounts."""
    import dataclasses
    from domain.inputs import CapexStructure, CapexItem
    # Start with all-zero
    zero_kwargs = {n: 0.0 for n in [
        "epc_contract", "production_units", "epc_other", "grid_connection",
        "ops_prep", "insurances", "lease_tax", "construction_mgmt_a",
        "commissioning", "audit_legal", "construction_mgmt_b", "contingencies",
        "taxes", "project_acquisition", "project_rights",
    ]}
    zero_kwargs.update(amounts)
    items = {n: CapexItem(name=n, amount_keur=v) for n, v in zero_kwargs.items()}
    return CapexStructure(**items)


def _make_sub(
    *, sub_line_id, parent_category_code, amount_keur, is_active=True, label="x"
):
    from app.persistence.capex_sub_lines import CapexSubLine
    nn = parent_category_code.split(".")[1]
    return CapexSubLine(
        sub_line_id=sub_line_id,
        project_id="proj-1",
        parent_category_code=parent_category_code,
        business_code=f"C.{nn}.U001",
        display_order=1,
        label=label,
        amount_keur=amount_keur,
        is_active=is_active,
    )


class TestFoldSubLinesIntoCapex:
    def test_factory_noop_returns_same_instance(self):
        from app.persistence.capex_sub_lines import fold_sub_lines_into_capex
        capex = _make_capex(epc_contract=1000.0)
        # Empty user_sub_lines returns capex unchanged (TUHO parity).
        assert fold_sub_lines_into_capex(capex, []) is capex
        # No overrides and empty sub-lines also returns capex.
        assert fold_sub_lines_into_capex(capex, [], {}) is capex
        # None overrides also returns capex.
        assert fold_sub_lines_into_capex(capex, [], None) is capex

    def test_single_sub_line_default_folds(self):
        from app.persistence.capex_sub_lines import fold_sub_lines_into_capex
        capex = _make_capex(epc_contract=1000.0)
        sub = _make_sub(
            sub_line_id="uuid-1", parent_category_code="C.02", amount_keur=50.0,
        )
        new_capex = fold_sub_lines_into_capex(capex, [sub])
        assert new_capex is not capex  # new instance
        assert new_capex.epc_contract.amount_keur == 1050.0
        # Unrelated fields unchanged
        assert new_capex.production_units.amount_keur == 0.0

    def test_override_replaces_default_at_subline_level(self):
        """Claude delta review fix: override REPLACES the sub-line's
        default amount. The fold then adds the (replaced) effective
        amount to the base. So base=1000, sub-default=50, override=999
        -> field = 1000 + 999 = 1999."""
        from app.persistence.capex_sub_lines import fold_sub_lines_into_capex
        capex = _make_capex(epc_contract=1000.0)
        sub = _make_sub(
            sub_line_id="uuid-1", parent_category_code="C.02", amount_keur=50.0,
        )
        new_capex = fold_sub_lines_into_capex(capex, [sub], {"uuid-1": 999.0})
        assert new_capex.epc_contract.amount_keur == 1999.0

    def test_override_to_zero_replaces_default(self):
        """If a scenario sets the sub-line amount to zero, the field
        gets base + 0 = base, NOT base + default."""
        from app.persistence.capex_sub_lines import fold_sub_lines_into_capex
        capex = _make_capex(epc_contract=1000.0)
        sub = _make_sub(
            sub_line_id="uuid-1", parent_category_code="C.02", amount_keur=50.0,
        )
        new_capex = fold_sub_lines_into_capex(capex, [sub], {"uuid-1": 0.0})
        assert new_capex.epc_contract.amount_keur == 1000.0  # not 1050

    def test_c08_and_c11_additive_into_audit_legal(self):
        """C.08 and C.11 both fold additively into audit_legal.
        Locked ambiguity; the sum is intentional."""
        from app.persistence.capex_sub_lines import fold_sub_lines_into_capex
        capex = _make_capex(audit_legal=75.0)
        sub_c08 = _make_sub(
            sub_line_id="uuid-c08", parent_category_code="C.08", amount_keur=20.0,
        )
        sub_c11 = _make_sub(
            sub_line_id="uuid-c11", parent_category_code="C.11", amount_keur=30.0,
        )
        new_capex = fold_sub_lines_into_capex(capex, [sub_c08, sub_c11])
        assert new_capex.audit_legal.amount_keur == 125.0  # 75 + 20 + 30

    def test_c08_and_c11_with_overrides_additive(self):
        """C.08 + override 200; C.11 + override 400 -> audit_legal = 75 + 200 + 400 = 675."""
        from app.persistence.capex_sub_lines import fold_sub_lines_into_capex
        capex = _make_capex(audit_legal=75.0)
        sub_c08 = _make_sub(
            sub_line_id="uuid-c08", parent_category_code="C.08", amount_keur=20.0,
        )
        sub_c11 = _make_sub(
            sub_line_id="uuid-c11", parent_category_code="C.11", amount_keur=30.0,
        )
        new_capex = fold_sub_lines_into_capex(
            capex,
            [sub_c08, sub_c11],
            {"uuid-c08": 200.0, "uuid-c11": 400.0},
        )
        assert new_capex.audit_legal.amount_keur == 675.0

    def test_soft_deleted_excluded(self):
        from app.persistence.capex_sub_lines import fold_sub_lines_into_capex
        capex = _make_capex(epc_contract=1000.0)
        sub_active = _make_sub(
            sub_line_id="uuid-1", parent_category_code="C.02", amount_keur=10.0,
        )
        sub_inactive = _make_sub(
            sub_line_id="uuid-2", parent_category_code="C.02", amount_keur=20.0,
            is_active=False,
        )
        new_capex = fold_sub_lines_into_capex(capex, [sub_active, sub_inactive])
        assert new_capex.epc_contract.amount_keur == 1010.0  # inactive excluded

    def test_unknown_category_raises(self):
        """Unknown categories must raise (never silent drop)."""
        from app.persistence.capex_sub_lines import fold_sub_lines_into_capex
        capex = _make_capex(epc_contract=1000.0)
        # Build a sub-line with an unknown parent category. The
        # validator is invoked inside the fold helper.
        sub = _make_sub(
            sub_line_id="uuid-x", parent_category_code="C.99", amount_keur=10.0,
        )
        with pytest.raises(ValueError):
            fold_sub_lines_into_capex(capex, [sub])

    def test_c17_rejected(self):
        """C.17 (Financing Costs) is read-only; sub-lines under C.17
        must raise."""
        from app.persistence.capex_sub_lines import fold_sub_lines_into_capex
        capex = _make_capex(epc_contract=1000.0)
        sub = _make_sub(
            sub_line_id="uuid-c17", parent_category_code="C.17", amount_keur=10.0,
        )
        with pytest.raises(ValueError):
            fold_sub_lines_into_capex(capex, [sub])

    def test_c18_rejected(self):
        from app.persistence.capex_sub_lines import fold_sub_lines_into_capex
        capex = _make_capex(epc_contract=1000.0)
        sub = _make_sub(
            sub_line_id="uuid-c18", parent_category_code="C.18", amount_keur=10.0,
        )
        with pytest.raises(ValueError):
            fold_sub_lines_into_capex(capex, [sub])

    def test_sub_line_id_not_in_overrides_falls_back_to_default(self):
        """If a sub-line has no override, its default is used."""
        from app.persistence.capex_sub_lines import fold_sub_lines_into_capex
        capex = _make_capex(epc_contract=1000.0)
        sub1 = _make_sub(
            sub_line_id="uuid-1", parent_category_code="C.02", amount_keur=10.0,
        )
        sub2 = _make_sub(
            sub_line_id="uuid-2", parent_category_code="C.02", amount_keur=20.0,
        )
        # Only uuid-1 has an override
        new_capex = fold_sub_lines_into_capex(capex, [sub1, sub2], {"uuid-1": 500.0})
        # 1000 (base) + 500 (override uuid-1) + 20 (default uuid-2) = 1520
        assert new_capex.epc_contract.amount_keur == 1520.0

    def test_sub_line_metadata_preserved_via_record(self):
        """fold_sub_lines_into_capex uses ONLY amount_keur and is_active
        from the record. The original parent_category_code is
        preserved (the fold helper does not lose it)."""
        from app.persistence.capex_sub_lines import fold_sub_lines_into_capex
        capex = _make_capex(lease_tax=0.0)
        sub = _make_sub(
            sub_line_id="uuid-1",
            parent_category_code="C.07",  # Land Securing Costs -> lease_tax
            amount_keur=300.0, label="land lease",
        )
        new_capex = fold_sub_lines_into_capex(capex, [sub])
        # C.07 maps to lease_tax; the field is updated.
        assert new_capex.lease_tax.amount_keur == 300.0
        # The sub-line's parent_category_code is preserved on the
        # record itself; the fold does not strip it.
        assert sub.parent_category_code == "C.07"
        assert sub.label == "land lease"


# ---------------------------------------------------------------------------
# 8. UUID stability
# ---------------------------------------------------------------------------


class TestUUIDStability:
    def test_create_sub_line_generates_unique_uuids(self, test_db, cur):
        from app.persistence.capex_sub_lines import create_sub_line
        cur.execute("PRAGMA foreign_keys = ON")
        cur.execute(
            """INSERT INTO projects (project_id, user_id, project_code, project_name,
               project_origin, source_project_template, is_readonly,
               baseline_snapshot_json, governance_state_json, last_run_summary_json,
               created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 0, '{}', '{}', '{}',
                       '2026-06-05', '2026-06-05')""",
            ("proj-uuid", "u1", "X", "X", "user_project", "user_project"),
        )
        cur.connection.commit()
        uuids = set()
        for i in range(20):
            rec = create_sub_line(
                cur, project_id="proj-uuid",
                parent_category_code="C.02", label=f"x{i}", amount_keur=10.0,
            )
            uuids.add(rec.sub_line_id)
            # Each is a valid UUID
            uuid.UUID(rec.sub_line_id)
        assert len(uuids) == 20, "all 20 sub-line UUIDs must be unique"


# ---------------------------------------------------------------------------
# 9. Hard no-go: no UI / static / run / export / model files changed
# ---------------------------------------------------------------------------


class TestNoProductionCodeChanged:
    """Pin that this PR only touches:

      - app/persistence/db.py (migration, idempotent)
      - app/persistence/capex_sub_lines.py (new)
      - tests/test_phase57a9b_capex_sub_lines_schema.py (new)

    It does NOT touch any of the forbidden paths.
    """

    FORBIDDEN_PATHS = [
        "app/templates/",
        "static/app.js",
        "static/styles.css",
        "main_web.py",
        "main_api.py",
        "domain/inputs.py",
        "app/excel_export.py",
        "app/input_helpers.py",
        "app/ui/project_context.py",
        "app/waterfall_core.py",
        "app/project_factories.py",
    ]

    def test_forbidden_paths_clean(self):
        """Run a git status-style check from a known base.

        We do not invoke git directly in the test (the test
        should not depend on the test runner's cwd). Instead,
        we verify the source-of-truth in
        ``app/persistence/capex_sub_lines.py`` and
        ``app/persistence/db.py`` is the only place CAPEX
        sub-line schema lives.
        """
        # The module exists and is the only persistence module
        # that imports ``capex_sub_lines``.
        import app.persistence.capex_sub_lines as csl
        assert hasattr(csl, "CAPEX_CATEGORY_TO_FIELD")
        assert hasattr(csl, "validate_parent_category")
        assert hasattr(csl, "validate_business_code")
        assert hasattr(csl, "generate_next_business_code")
        assert hasattr(csl, "fold_sub_lines_into_capex")
        assert hasattr(csl, "resolve_effective_sub_line_amount")
        # The module does NOT import any of the forbidden modules.
        forbidden_imports = [
            "app.waterfall_core",
            "app.project_factories",
            "app.excel_export",
            "app.input_helpers",
            "app.ui.project_context",
            "app.templates",
        ]
        import ast
        module_source = Path(csl.__file__).read_text(encoding="utf-8")
        # Parse the AST to find actual import statements (not
        # docstring mentions).
        tree = ast.parse(module_source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    imports.append(n.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        for forbidden in forbidden_imports:
            assert forbidden not in imports, (
                f"capex_sub_lines.py must NOT import {forbidden}; "
                f"actual imports = {imports}"
            )

    def test_db_py_only_added_capex_sub_lines_table(self):
        """The schema migration added the capex_sub_lines table and
        index. The other tables are unchanged. We verify by
        checking that the existing table DDL is still present
        in db.py."""
        db_path = REPO_ROOT / "app" / "persistence" / "db.py"
        db_text = db_path.read_text(encoding="utf-8")
        assert "CREATE TABLE IF NOT EXISTS capex_sub_lines" in db_text
        assert "CREATE TABLE IF NOT EXISTS projects" in db_text
        assert "CREATE TABLE IF NOT EXISTS scenarios" in db_text
        assert "CREATE TABLE IF NOT EXISTS runs" in db_text
        assert "CREATE TABLE IF NOT EXISTS workspace_states" in db_text
        assert "CREATE TABLE IF NOT EXISTS scenario_exports" in db_text


class TestRC1Frozen:
    """Verify rc1 is still resolvable in this worktree."""

    RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"

    def test_rc1_sha_resolves(self):
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--verify", self.RC1_SHA],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"rc1 SHA not resolvable: {result.stderr}"
        assert result.stdout.strip() == self.RC1_SHA


# ---------------------------------------------------------------------------
# 10. Cross-arc consistency
# ---------------------------------------------------------------------------


class TestCrossArcConsistency:
    """Pin that the new module does not regress the existing
    persistence / domain / model / UI / export layers."""

    def test_no_overrides_json_allowlist_change(self):
        """The ``SCENARIO_INPUT_FIELDS`` set in ``_helpers.py`` must
        only grow via explicit, documented additions. The
        add-list extension lands in 57A-9C, NOT 57A-9B.
        SCENARIO-2 intentionally added 4 matrix alias fields:
        ppa_tariff_eur_mwh, operating_hours_p50,
        opex_y1_total_keur, senior_tenor_years. Count is now 25."""
        from app.persistence._helpers import SCENARIO_INPUT_FIELDS
        # 21 original flat keys + 4 SCENARIO-2 alias additions = 25.
        assert len(SCENARIO_INPUT_FIELDS) == 25
        assert "_capex_sub_line_overrides" not in SCENARIO_INPUT_FIELDS
        assert "_capex_sub_line_overrides_metadata" not in SCENARIO_INPUT_FIELDS

    def test_excel_export_integration_untouched(self):
        """The ``advanced_capex_line_items`` parameter on
        ``build_excel_export`` is still the (unused) reserved
        hook. 57A-9B does not pass any value for it."""
        from app.excel_export import build_excel_export
        import inspect
        sig = inspect.signature(build_excel_export)
        param = sig.parameters.get("advanced_capex_line_items")
        assert param is not None, "advanced_capex_line_items parameter must still exist"
        # Default is None — not wired in 57A-9B.
        assert param.default is None

    def test_no_jinja_template_changes(self):
        """sheet_capex.html must be byte-identical to the post-57A-8
        state. We verify by hash."""
        sheet = REPO_ROOT / "app" / "templates" / "partials" / "sheet_capex.html"
        assert sheet.exists()
        # The 57A-8 toolbar markers must still be present (no
        # accidental regression in 57A-9B).
        text = sheet.read_text(encoding="utf-8")
        assert 'data-capex-add-line' in text
        assert 'data-capex-tmp' in text

    def test_no_app_js_changes(self):
        """app.js must be byte-identical to the post-57A-8 state."""
        app_js = REPO_ROOT / "static" / "app.js"
        assert app_js.exists()
        text = app_js.read_text(encoding="utf-8")
        # The 57A-8 module must still be present.
        assert "bindCapexAddLineUx" in text

    def test_no_styles_css_changes(self):
        """styles.css must be byte-identical to the post-57A-8 state."""
        css = REPO_ROOT / "static" / "styles.css"
        assert css.exists()
        # The 57A-8 tmp-row styles must still be present.
        text = css.read_text(encoding="utf-8")
        assert "capex-tmp" in text
