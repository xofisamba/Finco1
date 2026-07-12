"""
tests/test_persistence_diff_guard.py

Self-tests for tests/helpers/persistence_diff_guard.py.

These tests exercise ``check_db_diff_text`` directly with synthetic diff
strings so they run offline and deterministically (no git state required).

Acceptance cases
----------------
- Only opex_sub_lines.py changed (no db.py diff) — not tested here since
  check_db_diff_text is only called when db.py is in the changed set;
  that path is covered by the integration side in the guardrail tests.
- Exact approved OPEX table + index block in db.py.

Rejection cases
---------------
- OPEX block plus an unrelated added table.
- OPEX block plus an unrelated added index.
- OPEX block plus a deletion from an existing schema line.
- OPEX block plus a changed CAPEX index reference.
- Arbitrary db.py edit that merely contains the word "opex_sub_lines"
  in a comment but adds a different table.
- _ensure_column added inside the OPEX block.
- ALTER TABLE in added lines.
"""
from __future__ import annotations

import textwrap
import unittest

from tests.helpers.persistence_diff_guard import check_db_diff_text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _diff(added_lines: list[str], deleted_lines: list[str] | None = None) -> str:
    """Build a minimal unified-diff string for testing."""
    header = textwrap.dedent("""\
        diff --git a/app/persistence/db.py b/app/persistence/db.py
        index abc1234..def5678 100644
        --- a/app/persistence/db.py
        +++ b/app/persistence/db.py
        @@ -195,6 +195,{n} @@
    """).format(n=len(added_lines))
    lines = []
    for ln in (deleted_lines or []):
        lines.append(f"-{ln}")
    for ln in added_lines:
        lines.append(f"+{ln}")
    return header + "\n".join(lines) + "\n"


# The exact approved block (mirrors the actual PR diff).
_APPROVED_ADDED = [
    "    # Workbook V2 PR 11: OPEX custom-row sub-lines table.",
    "    conn.execute(",
    '        """',
    "        CREATE TABLE IF NOT EXISTS opex_sub_lines (",
    "            id                INTEGER PRIMARY KEY AUTOINCREMENT,",
    "            sub_line_id       TEXT    NOT NULL UNIQUE,",
    "            project_id        TEXT    NOT NULL,",
    "            parent_group_code TEXT    NOT NULL,",
    "            business_code     TEXT    NOT NULL,",
    "            display_order     INTEGER NOT NULL,",
    "            label             TEXT    NOT NULL,",
    "            amount_keur       REAL    NOT NULL DEFAULT 0.0,",
    "            inflation_pct     REAL    NOT NULL DEFAULT 0.0,",
    "            comments          TEXT    NOT NULL DEFAULT '',",
    "            source            TEXT    NOT NULL DEFAULT 'user',",
    "            is_active         INTEGER NOT NULL DEFAULT 1,",
    "            created_at        TEXT    NOT NULL,",
    "            updated_at        TEXT    NOT NULL,",
    "            FOREIGN KEY(project_id) REFERENCES projects(project_id),",
    "            UNIQUE(project_id, business_code)",
    "        )",
    '        """',
    "    )",
    "    conn.execute(",
    '        "CREATE INDEX IF NOT EXISTS idx_opex_sub_lines_project"',
    '        " ON opex_sub_lines(project_id, is_active, parent_group_code, display_order)"',
    "    )",
]


# ---------------------------------------------------------------------------
# Acceptance
# ---------------------------------------------------------------------------

class TestAcceptApprovedBlock(unittest.TestCase):
    """Approved diff: exact OPEX table + index block, no deletions."""

    def test_exact_approved_block_passes(self):
        diff = _diff(_APPROVED_ADDED)
        violations = check_db_diff_text(diff)
        self.assertEqual(violations, [], f"Expected no violations, got: {violations}")


# ---------------------------------------------------------------------------
# Rejection: unrelated additions
# ---------------------------------------------------------------------------

class TestRejectUnrelatedTable(unittest.TestCase):
    """Reject: OPEX block plus an additional unrelated CREATE TABLE."""

    def test_extra_table_rejected(self):
        extra = _APPROVED_ADDED + [
            "    conn.execute(",
            '        "CREATE TABLE IF NOT EXISTS some_other_table (id INTEGER)"',
            "    )",
        ]
        diff = _diff(extra)
        violations = check_db_diff_text(diff)
        self.assertTrue(
            any("some_other_table" in v for v in violations),
            f"Expected violation for extra table, got: {violations}",
        )


class TestRejectUnrelatedIndex(unittest.TestCase):
    """Reject: OPEX block plus an unrelated CREATE INDEX."""

    def test_extra_index_rejected(self):
        extra = _APPROVED_ADDED + [
            "    conn.execute(",
            '        "CREATE INDEX IF NOT EXISTS idx_some_other ON some_table(id)"',
            "    )",
        ]
        diff = _diff(extra)
        violations = check_db_diff_text(diff)
        self.assertTrue(
            any("idx_some_other" in v for v in violations),
            f"Expected violation for extra index, got: {violations}",
        )


class TestRejectCapexReference(unittest.TestCase):
    """Reject: any addition referencing capex_sub_lines."""

    def test_capex_reference_rejected(self):
        # Simulate a diff that adds the OPEX block but also sneaks in a
        # capex_sub_lines reference (e.g. an accidental copy-paste).
        extra = _APPROVED_ADDED + [
            "    # also touching capex_sub_lines by mistake",
        ]
        diff = _diff(extra)
        violations = check_db_diff_text(diff)
        self.assertTrue(
            any("capex_sub_lines" in v for v in violations),
            f"Expected CAPEX-reference violation, got: {violations}",
        )


class TestRejectEnsureColumn(unittest.TestCase):
    """Reject: _ensure_column call added inside the block."""

    def test_ensure_column_rejected(self):
        extra = _APPROVED_ADDED + [
            '    _ensure_column(conn, "opex_sub_lines", "new_col", "TEXT")',
        ]
        diff = _diff(extra)
        violations = check_db_diff_text(diff)
        self.assertTrue(
            any("_ensure_column" in v for v in violations),
            f"Expected _ensure_column violation, got: {violations}",
        )


class TestRejectAlterTable(unittest.TestCase):
    """Reject: ALTER TABLE in added lines."""

    def test_alter_table_rejected(self):
        extra = _APPROVED_ADDED + [
            "    conn.execute('ALTER TABLE runs ADD COLUMN foo TEXT')",
        ]
        diff = _diff(extra)
        violations = check_db_diff_text(diff)
        self.assertTrue(
            any("ALTER TABLE" in v for v in violations),
            f"Expected ALTER TABLE violation, got: {violations}",
        )


# ---------------------------------------------------------------------------
# Rejection: deletions
# ---------------------------------------------------------------------------

class TestRejectDeletion(unittest.TestCase):
    """Reject: any existing schema line deleted alongside the OPEX addition."""

    def test_deletion_rejected(self):
        diff = _diff(
            added_lines=_APPROVED_ADDED,
            deleted_lines=["    _ensure_column(conn, 'runs', 'some_col', 'TEXT')"],
        )
        violations = check_db_diff_text(diff)
        self.assertTrue(
            any("deletion" in v.lower() or "delet" in v.lower() for v in violations),
            f"Expected deletion violation, got: {violations}",
        )

    def test_capex_index_deletion_rejected(self):
        diff = _diff(
            added_lines=_APPROVED_ADDED,
            deleted_lines=[
                '    "CREATE INDEX IF NOT EXISTS idx_capex_sub_lines_project"',
                '    " ON capex_sub_lines(project_id, is_active, parent_category_code, display_order)"',
            ],
        )
        violations = check_db_diff_text(diff)
        self.assertTrue(
            any("deletion" in v.lower() or "delet" in v.lower() for v in violations),
            f"Expected deletion violation for CAPEX index removal, got: {violations}",
        )


# ---------------------------------------------------------------------------
# Rejection: superficial opex_sub_lines mention, wrong content
# ---------------------------------------------------------------------------

class TestRejectMereWordPresence(unittest.TestCase):
    """Reject: diff containing 'opex_sub_lines' in a comment but adding a
    different/additional table — the old keyword-only guard would pass this."""

    def test_comment_plus_wrong_table_rejected(self):
        # Only a comment mentioning opex_sub_lines + a CREATE TABLE for
        # something_else, NO actual opex_sub_lines table.
        diff = _diff([
            "    # references opex_sub_lines indirectly",
            "    conn.execute('CREATE TABLE IF NOT EXISTS something_else (id INTEGER)')",
        ])
        violations = check_db_diff_text(diff)
        # Must flag: opex_sub_lines table not found AND something_else table present
        self.assertTrue(
            any("opex_sub_lines" in v or "something_else" in v for v in violations),
            f"Expected violations for misleading opex_sub_lines mention, got: {violations}",
        )

    def test_opex_word_in_comment_plus_extra_table_rejected(self):
        """OPEX block present AND an extra unrelated table — both the mention
        of opex_sub_lines and the extra table must be caught."""
        extra = _APPROVED_ADDED + [
            "    # extra opex_sub_lines comment that the old guard would ignore",
            "    conn.execute('CREATE TABLE IF NOT EXISTS extra_table (id INTEGER)')",
        ]
        diff = _diff(extra)
        violations = check_db_diff_text(diff)
        self.assertTrue(
            any("extra_table" in v for v in violations),
            f"Expected extra_table violation despite opex_sub_lines keyword, got: {violations}",
        )


# ---------------------------------------------------------------------------
# Rejection: exact OPEX block plus extra lines that the denylist would miss
# ---------------------------------------------------------------------------

class TestRejectExtraHarmlessLookingLines(unittest.TestCase):
    """Reject additions that pass every denylist rule but are not the approved
    block — e.g. arbitrary Python, PRAGMA, extra conn.execute, extra comment."""

    def test_extra_python_assignment_rejected(self):
        extra = _APPROVED_ADDED + [
            "    _SCHEMA_VERSION = 2",
        ]
        diff = _diff(extra)
        violations = check_db_diff_text(diff)
        self.assertTrue(
            violations,
            "Expected violation for extra Python assignment alongside OPEX block.",
        )
        self.assertTrue(
            any("_SCHEMA_VERSION" in v or "unapproved" in v.lower() for v in violations),
            f"Expected unapproved-line violation, got: {violations}",
        )

    def test_extra_pragma_rejected(self):
        extra = _APPROVED_ADDED + [
            '    conn.execute("PRAGMA foreign_keys = OFF")',
        ]
        diff = _diff(extra)
        violations = check_db_diff_text(diff)
        self.assertTrue(
            violations,
            "Expected violation for PRAGMA statement alongside OPEX block.",
        )
        self.assertTrue(
            any("PRAGMA" in v or "unapproved" in v.lower() for v in violations),
            f"Expected unapproved-line violation for PRAGMA, got: {violations}",
        )

    def test_extra_conn_execute_rejected(self):
        extra = _APPROVED_ADDED + [
            "    conn.execute(",
            '        "SELECT 1"',
            "    )",
        ]
        diff = _diff(extra)
        violations = check_db_diff_text(diff)
        self.assertTrue(
            violations,
            "Expected violation for extra conn.execute alongside OPEX block.",
        )
        self.assertTrue(
            any("unapproved" in v.lower() or "SELECT" in v or "conn.execute" in v
                for v in violations),
            f"Expected unapproved-line violation for extra conn.execute, got: {violations}",
        )

    def test_extra_comment_rejected(self):
        extra = _APPROVED_ADDED + [
            "    # harmless-looking extra comment",
        ]
        diff = _diff(extra)
        violations = check_db_diff_text(diff)
        self.assertTrue(
            violations,
            "Expected violation for unapproved comment alongside OPEX block.",
        )
        self.assertTrue(
            any("unapproved" in v.lower() or "harmless" in v or "comment" in v.lower()
                for v in violations),
            f"Expected unapproved-line violation for extra comment, got: {violations}",
        )


if __name__ == "__main__":
    unittest.main()
