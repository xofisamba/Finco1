"""
tests/helpers/persistence_diff_guard.py

Guardrail helper: validates that changes to app/persistence/ between
the current branch and origin/main are limited to the approved OPEX
custom-row lifecycle additions only.

Approved additions
------------------
- app/persistence/opex_sub_lines.py  — new file; any content is accepted
  (the file itself is reviewed separately and is explicitly approved).
- app/persistence/db.py              — additive only; the only permitted
  changes are:
    1. A single CREATE TABLE IF NOT EXISTS opex_sub_lines block
    2. A single CREATE INDEX IF NOT EXISTS idx_opex_sub_lines_project
  Any deletion, any modification to an existing line, or any addition
  outside those two DDL objects is a violation.

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

import re
import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]

_ALLOWED_NEW_PERSISTENCE_FILES = frozenset({
    "app/persistence/opex_sub_lines.py",
})

# The exact table name and index name that are permitted to be added to db.py.
_APPROVED_TABLE = "opex_sub_lines"
_APPROVED_INDEX = "idx_opex_sub_lines_project"


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
    - Added lines (``+`` lines, excluding the ``+++`` header) must
      collectively:
        a. Include a ``CREATE TABLE IF NOT EXISTS opex_sub_lines`` block.
        b. Include a ``CREATE INDEX IF NOT EXISTS idx_opex_sub_lines_project``
           definition.
        c. Contain no ``CREATE TABLE`` for any table other than
           ``opex_sub_lines``.
        d. Contain no ``CREATE INDEX`` for any index other than
           ``idx_opex_sub_lines_project``.
        e. Contain no reference to ``capex_sub_lines`` (prevents accidental
           CAPEX schema changes slipping through).
        f. Contain no ``_ensure_column`` calls (existing schema migration
           helpers must not be touched).
        g. Contain no ``ALTER TABLE`` statements.
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
        # No additions at all — nothing to approve.
        violations.append("db.py: no additions found; expected the opex_sub_lines block.")
        return violations

    added_text = "\n".join(added_lines)

    # --- Rule a: opex_sub_lines table must be added ---
    if _APPROVED_TABLE not in added_text:
        violations.append(
            f"db.py: expected {_APPROVED_TABLE!r} CREATE TABLE not found in additions."
        )

    # --- Rule b: idx_opex_sub_lines_project index must be added ---
    if _APPROVED_INDEX not in added_text:
        violations.append(
            f"db.py: expected {_APPROVED_INDEX!r} CREATE INDEX not found in additions."
        )

    # --- Rule c: no other CREATE TABLE ---
    for m in re.finditer(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)",
        added_text,
        re.IGNORECASE,
    ):
        name = m.group(1)
        if name.lower() != _APPROVED_TABLE:
            violations.append(
                f"db.py: disallowed CREATE TABLE {name!r} in additions."
            )

    # --- Rule d: no other CREATE INDEX ---
    for m in re.finditer(
        r"CREATE\s+INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)",
        added_text,
        re.IGNORECASE,
    ):
        name = m.group(1)
        if name.lower() != _APPROVED_INDEX:
            violations.append(
                f"db.py: disallowed CREATE INDEX {name!r} in additions."
            )

    # --- Rule e: no capex references ---
    if "capex_sub_lines" in added_text.lower():
        violations.append(
            "db.py: additions reference capex_sub_lines — CAPEX schema must not be touched."
        )

    # --- Rule f: no _ensure_column calls ---
    if "_ensure_column" in added_text:
        violations.append(
            "db.py: additions include _ensure_column call — "
            "existing schema migration order must not be modified."
        )

    # --- Rule g: no ALTER TABLE ---
    if re.search(r"ALTER\s+TABLE", added_text, re.IGNORECASE):
        violations.append(
            "db.py: additions include ALTER TABLE — only additive DDL is permitted."
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
            # New OPEX persistence module — always approved.
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
