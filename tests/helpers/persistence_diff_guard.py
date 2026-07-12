"""
tests/helpers/persistence_diff_guard.py

Guardrail helper: validates that changes to app/persistence/ between
the current branch and origin/main are limited to the approved OPEX
custom-row lifecycle additions only.

Approved additions
------------------
- app/persistence/opex_sub_lines.py  — new file; any content is accepted
  (the file itself is reviewed separately and is explicitly approved).
- app/persistence/db.py              — additive only; the added non-blank
  lines must equal APPROVED_OPEX_DB_ADDITIONS exactly (after stripping
  leading/trailing whitespace from each line for indentation tolerance).
  Any deletion, any extra line, or any missing line is a violation.

Any other changed file is unconditionally a violation.

Design
------
The two public entry points are:

  validate_persistence_diff() -> list[str]
      Runs real git commands against the working repository.  Intended for
      use in the three CAPEX phase guardrail tests.

  check_db_diff_text(diff_text: str) -> list[str]
      Parses a raw unified-diff string without touching git.  Intended for
      the self-test suite so tests can run offline and deterministically.

Both return an empty list on success and a list of human-readable violation
strings on failure.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]

_ALLOWED_NEW_PERSISTENCE_FILES = frozenset({
    "app/persistence/opex_sub_lines.py",
})

# STAB-1B: workspace_repository.py changes are approved (composite CAS wiring only).
_ALLOWED_MODIFIED_PERSISTENCE_FILES = frozenset({
    "app/persistence/workspace_repository.py",
})

# The canonical non-blank lines that must appear in db.py — no more, no less.
# Each line is stored stripped; comparison normalises indentation on both sides.
APPROVED_OPEX_DB_ADDITIONS: tuple[str, ...] = (
    "# Workbook V2 PR 11: OPEX custom-row sub-lines table.",
    "conn.execute(",
    '"""',
    "CREATE TABLE IF NOT EXISTS opex_sub_lines (",
    "id                INTEGER PRIMARY KEY AUTOINCREMENT,",
    "sub_line_id       TEXT    NOT NULL UNIQUE,",
    "project_id        TEXT    NOT NULL,",
    "parent_group_code TEXT    NOT NULL,",
    "business_code     TEXT    NOT NULL,",
    "display_order     INTEGER NOT NULL,",
    "label             TEXT    NOT NULL,",
    "amount_keur       REAL    NOT NULL DEFAULT 0.0,",
    "inflation_pct     REAL    NOT NULL DEFAULT 0.0,",
    "comments          TEXT    NOT NULL DEFAULT '',",
    "source            TEXT    NOT NULL DEFAULT 'user',",
    "is_active         INTEGER NOT NULL DEFAULT 1,",
    "created_at        TEXT    NOT NULL,",
    "updated_at        TEXT    NOT NULL,",
    "FOREIGN KEY(project_id) REFERENCES projects(project_id),",
    "UNIQUE(project_id, business_code)",
    ")",
    '"""',
    ")",
    "conn.execute(",
    '"CREATE INDEX IF NOT EXISTS idx_opex_sub_lines_project"',
    '" ON opex_sub_lines(project_id, is_active, parent_group_code, display_order)"',
    ")",
)


# ---------------------------------------------------------------------------
# Git helpers (real repository; not called by self-tests)
# ---------------------------------------------------------------------------

def _git_diff_names(subdir: str = "app/persistence/") -> list[str]:
    r = subprocess.run(
        ["git", "diff", "origin/main", "--name-only", "--", subdir],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    return [f for f in r.stdout.strip().splitlines() if f]


def _git_diff_text(path: str) -> str:
    r = subprocess.run(
        ["git", "diff", "origin/main", "--", path],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    return r.stdout


# ---------------------------------------------------------------------------
# Core diff parser (pure function; used by both paths)
# ---------------------------------------------------------------------------

def check_db_diff_text(diff_text: str) -> list[str]:
    """Validate a raw unified diff for app/persistence/db.py.

    Returns a list of violation strings (empty = approved).

    Rules enforced:
    - No lines may be deleted (i.e. no ``-`` diff lines other than the
      ``---`` file header).
    - The non-blank added lines, after stripping leading/trailing whitespace,
      must equal APPROVED_OPEX_DB_ADDITIONS exactly — no extra lines, no
      missing lines, no reordering.
    """
    violations: list[str] = []
    added_lines: list[str] = []
    deleted_lines: list[str] = []

    for raw in diff_text.splitlines():
        if raw.startswith("+++") or raw.startswith("---"):
            continue
        if raw.startswith("+"):
            added_lines.append(raw[1:])
        elif raw.startswith("-"):
            deleted_lines.append(raw[1:])

    # --- Rule: no deletions ---
    non_blank_deletions = [ln for ln in deleted_lines if ln.strip()]
    for ln in non_blank_deletions:
        violations.append(
            f"db.py: disallowed deletion: {ln!r}"
        )

    if not added_lines:
        violations.append("db.py: no additions found; expected the opex_sub_lines block.")
        return violations

    # --- Rule: added non-blank lines must match approved block exactly ---
    actual = tuple(ln.strip() for ln in added_lines if ln.strip())
    expected = APPROVED_OPEX_DB_ADDITIONS

    if actual != expected:
        # Produce a useful diff-style message.
        actual_set = set(actual)
        expected_set = set(expected)
        extra = [ln for ln in actual if ln not in expected_set]
        missing = [ln for ln in expected if ln not in actual_set]
        # Also catch reordering / count mismatches when sets match.
        if not extra and not missing and actual != expected:
            violations.append(
                "db.py: added lines match approved set but differ in order or count."
            )
        for ln in extra:
            violations.append(
                f"db.py: unapproved added line: {ln!r}"
            )
        for ln in missing:
            violations.append(
                f"db.py: approved line missing from additions: {ln!r}"
            )

    return violations


# ---------------------------------------------------------------------------
# Public entry point for guardrail tests
# ---------------------------------------------------------------------------

def validate_persistence_diff() -> list[str]:
    """Inspect the current branch's changes to app/persistence/ vs origin/main.

    Returns a list of violation strings; empty list means the diff is fully
    within the approved OPEX lifecycle scope.

    Approved scope:
      - app/persistence/opex_sub_lines.py  may appear (new file, approved).
      - app/persistence/db.py  may appear only with the exact OPEX schema
        block additions validated by ``check_db_diff_text``.
      - Any other changed file is an unconditional violation.
    """
    violations: list[str] = []
    changed = set(_git_diff_names())

    for path in changed:
        if path in _ALLOWED_NEW_PERSISTENCE_FILES:
            continue
        elif path in _ALLOWED_MODIFIED_PERSISTENCE_FILES:
            continue
        elif path == "app/persistence/db.py":
            diff_text = _git_diff_text(path)
            violations.extend(check_db_diff_text(diff_text))
        else:
            violations.append(
                f"Unexpected change in {path!r} — only approved OPEX "
                f"persistence additions are permitted on this branch."
            )

    return violations
