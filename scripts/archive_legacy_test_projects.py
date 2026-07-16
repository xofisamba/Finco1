#!/usr/bin/env python3
"""Safe, fail-closed archive tooling for legacy automated-test
projects in the Finco1 persistent database.

Design contract (final integration pass)
========================================

1. **No deployment-specific data in Git.** This script, the
   candidate-rule catalogue, and the operator-local audit
   template are committed. The manifest, the audit report,
   the backup, and the database-specific fingerprints are
   NOT committed. They are generated per-deployment and
   excluded from Git via the
   ``*.archive-manifest.local.json``,
   ``*.archive-audit.local.json``, and
   ``*.archive-inventory.local.json`` patterns in
   ``.gitignore`` and the ``*.db.backup.*.sqlite3`` rule.

2. **Anchored, evidence-backed candidate classification.**
   Every rule uses ``startswith()``, exact-name match, or
   ``re.fullmatch()``. Substring-in-the-middle matching is
   FORBIDDEN. Each rule pairs the matcher with the exact test
   source file and the exact helper function that generates
   it.

3. **Two authoritative logical DB state fingerprints.**

   * ``database.pre_apply_project_state_sha256`` —
     the exact current logical state, computed inside one
     read transaction over the project rows plus the schema
     fingerprint and the canonical table counts. This is the
     fingerprint the *first* apply must match.

   * ``database.replay_state_sha256`` — a deterministic
     normalized state in which every manifest candidate is
     treated as ``archived=1`` and ``updated_at`` is
     normalized to the candidate's ``created_at`` (so the
     replay does not depend on the original
     ``updated_at``). Every non-candidate project row
     remains exact. The schema fingerprint and the canonical
     table counts are still included. This is the fingerprint
     a same-manifest *replay* must match.

   Both fingerprints use the canonical JSON serialization
   that preserves ``None``, empty string, ``0``, and
   ``False`` exactly. They do not use ``value or ""`` for
   authoritative serialization.

   The raw file SHA-256 and size are recorded as
   *informational only* under ``database.raw_file_sha256``
   and ``database.raw_size_bytes``. They are NOT
   authoritative; the logical fingerprints are.

4. **Explicit validation states.** The locked validator
   returns one of:

   * ``NO_CANDIDATES`` — manifest has zero candidates.
     Same-manifest replay returns this with zero writes
     and no backup.

   * ``FIRST_APPLY`` — every manifest candidate is still
     ``archived=0`` and the pre-apply logical fingerprint
     matches. The apply creates one backup, archives the
     active candidates, and verifies the post-update state.

   * ``ALREADY_APPLIED`` — every manifest candidate is
     already ``archived=1``, every identity still matches,
     and the *replay* logical fingerprint matches the
     current logical state. The apply commits the (empty)
     transaction and reports a successful no-op. No second
     backup is created.

   * ``PARTIAL_REPLAY`` — a mix of ``archived=0`` and
     ``archived=1`` candidates. Always fails closed with
     ``"ERROR: partial replay"``. The operator must
     re-generate the manifest so intent is unambiguous.

5. **Exact-path validation.** Apply compares
   ``db_path.expanduser().resolve()`` against the manifest's
   ``database.absolute_path``. Mismatch -> exit non-zero,
   zero writes.

6. **One fail-closed BEGIN IMMEDIATE transaction.** All
   validation, the backup (only for FIRST_APPLY), and the
   updates happen inside a single ``BEGIN IMMEDIATE`` write
   lock. Any failure -> ``ROLLBACK``, zero rows archived.

7. **External backup only.** ``--backup-dir`` must resolve
   to a path OUTSIDE the repository and OUTSIDE the live DB
   directory. Repository paths are rejected. Recommended
   operator path: ``/var/backups/finco``.

8. **Backup filename aligned with the ignore defense.**
   ``finco_runs.db.backup.<UTC-timestamp>.sqlite3`` is the
   default. The ``*.db.backup.*.sqlite3`` rule in
   ``.gitignore`` is a defense-in-depth backstop.

9. **Backup verification compares the entire protected
   state**: ``PRAGMA integrity_check``, every canonical
   table count, the schema fingerprint, and the
   project-state SHA-256. The backup path used for the
   verify is the exact path returned by the backup function.

10. **Structured apply result.** ``apply()`` returns an
    ``ApplyResult`` dataclass, not an ``int``. The CLI prints
    the status, the number of rows archived in this
    invocation, the exact backup path (or ``None``), and the
    post-update project-state SHA-256.

11. **Partial replay never permitted.** The
    ``allow_all_already_archived`` boolean that used to
    permit a partial replay is REMOVED. A partial replay
    always fails closed.

CLI
===

  # 1. Generate a fresh operator-local manifest from the
  #    exact target DB. Operator-local; excluded from Git.
  python scripts/archive_legacy_test_projects.py \\
      --db <exact-db-path> \\
      --generate-manifest <path>.archive-manifest.local.json

  # 2. Dry-run review (default mode). Reports
  #    status=NO_CANDIDATES / FIRST_APPLY / ALREADY_APPLIED /
  #    partial replay / other invalid state.
  python scripts/archive_legacy_test_projects.py \\
      --db <exact-db-path> \\
      --manifest <path>.archive-manifest.local.json

  # 3. Apply. Requires --backup-dir outside the repository
  #    and outside the live DB directory. All validation
  #    and writes happen inside one BEGIN IMMEDIATE
  #    transaction. Same-manifest replay is a no-op.
  python scripts/archive_legacy_test_projects.py \\
      --db <exact-db-path> \\
      --manifest <path>.archive-manifest.local.json \\
      --backup-dir /var/backups/finco \\
      --apply

Scope
=====

This script is a maintenance tool. It does NOT touch:

  * engine equations
  * registry definitions
  * ProjectInputs schemas
  * runtime calculations
  * scenario behavior
  * CAPEX / OPEX / Revenue / Debt / Tax / Financial Statements
  * persistence schema
  * parity targets
  * golden fixtures
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MANIFEST_VERSION = 2
SCHEMA_FINGERPRINT_TABLES: Tuple[str, ...] = (
    "projects",
    "scenarios",
    "runs",
    "workspace_states",
)

# Patterns that NEVER classify as a test artifact (ambiguous
# manual user projects). All comparisons are case-folded.
PROTECTED_KEYWORDS: Tuple[str, ...] = (
    "proba",
    "grubi",
    "idemo",
)

# Origins treated as system-owned and never archived.
NON_USER_ORIGINS: Tuple[str, ...] = (
    "factory_template",
    "saved_baseline",
)

# Canonical template sources. User-created working copies of
# these are NOT classified (template_source protection wins
# over user_origin).
CANONICAL_TEMPLATE_SOURCES: Tuple[str, ...] = (
    "tuho",
    "oborovo",
)

# Project row fields used by the row fingerprint. Any change
# in any of these between generate and apply causes the
# apply to refuse.
ROW_IDENTITY_FIELDS: Tuple[str, ...] = (
    "project_id",
    "user_id",
    "project_code",
    "project_name",
    "project_type",
    "project_origin",
    "source_project_template",
    "template_source",
    "is_readonly",
)

# Project row fields included in the logical project-state
# payload. Sorted by project_id to make the hash deterministic.
PROJECT_STATE_FIELDS: Tuple[str, ...] = (
    "project_id",
    "user_id",
    "project_code",
    "project_name",
    "project_type",
    "project_origin",
    "source_project_template",
    "template_source",
    "archived",
    "is_readonly",
    "created_at",
    "updated_at",
)

# Validation states.
ValidationState = Literal[
    "FIRST_APPLY",
    "ALREADY_APPLIED",
    "NO_CANDIDATES",
    "PARTIAL_REPLAY",
]

# Apply statuses (terminal labels).
APPLY_STATUS_APPLIED = "APPLIED"
APPLY_STATUS_ALREADY_APPLIED = "ALREADY_APPLIED"
APPLY_STATUS_NO_CANDIDATES = "NO_CANDIDATES"


# ---------------------------------------------------------------------------
# Structured result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ManifestValidationResult:
    """The result of running the locked validator against
    the current DB. The state is one of the four
    ``ValidationState`` literals. The caller (apply() or
    main() in dry-run mode) decides what to do with each
    state."""

    state: str  # ValidationState
    active_candidates: Tuple[Dict[str, Any], ...]
    archived_candidates: Tuple[Dict[str, Any], ...]
    pre_update_metadata: Dict[str, Any]
    current_table_counts: Dict[str, int]
    current_project_state_sha256: str
    current_schema_fingerprint: str

    @property
    def is_terminal_noop(self) -> bool:
        return self.state in ("ALREADY_APPLIED", "NO_CANDIDATES")


@dataclass(frozen=True)
class ApplyResult:
    """The result of ``apply()``. Status is one of the three
    ``APPLY_STATUS_*`` constants. The backup path is the
    exact path returned by the backup function for a
    successful first apply, and ``None`` for the two
    terminal-noop states."""

    status: str
    rows_archived_now: int
    backup_path: Optional[str]
    project_state_sha256_after: str
    database_path_resolved: str
    manifest_path_resolved: str


# ---------------------------------------------------------------------------
# Evidence-backed candidate rule catalogue (anchored)
# ---------------------------------------------------------------------------
# Each rule:
#   * ``rule_id``           — stable identifier.
#   * ``description``       — human-readable summary.
#   * ``code_prefixes``     — list of prefixes (lowercased)
#                              matched with ``str.startswith``.
#   * ``name_prefixes``     — list of prefixes (lowercased)
#                              matched with ``str.startswith``.
#   * ``name_fullmatch``    — list of anchored regexes
#                              matched with ``re.fullmatch``.
#   * ``code_fullmatch``    — list of anchored regexes for
#                              project_code.
#   * ``source_test``       — exact path to the test file
#                              that generates the project.
#   * ``source_helper``     — the f-string or function in
#                              the test that names the
#                              project.
#   * ``not_a_user_project`` — the explanation of why a real
#                              user project does not match.

CANDIDATE_RULES: List[Dict[str, Any]] = [
    {
        "rule_id": "ph3-working-copy-series",
        "match_policy": "code_only",
        "description": (
            "Phase 3 working-copy test fixtures. Anchored "
            "regex on project_code: ^ph3-wc-(t\\d+|TEST|test-[a-f0-9]+|debug-[a-f0-9]+)$"
        ),
        "code_prefixes": [],
        "name_prefixes": [],
        "name_fullmatch": [],
        "code_fullmatch": [
            r"^ph3-wc-(t\d+|TEST|test-[a-f0-9]+|debug-[a-f0-9]+)$"
        ],
        "source_test": "tests/test_phase_p2fix1_default_route_rewiring.py",
        "source_helper": (
            "ph3-wc-t1..t8, ph3-wc-TEST, ph3-wc-test-<hex>, "
            "ph3-wc-debug-<hex> created by the ph3-user-* test "
            "users. The regex captures the literal token "
            "patterns that the tests produce."
        ),
        "not_a_user_project": (
            "The anchored regex matches exactly the four "
            "token patterns the test produces. A user project "
            "like 'My ph3-wc-model' (code=ph3-wc-model, "
            "name=My ph3-wc-model documentation) is NOT "
            "classified because 'ph3-wc-model' does not match "
            "any of the four anchored suffixes."
        ),
    },
    {
        "rule_id": "p1-ux-fix1-fixtures",
        "match_policy": "code_only",
        "description": (
            "Phase 1 UX fix test fixtures. Anchored regex on "
            "project_code: ^p1uxfix1-wc-[a-f0-9]+$"
        ),
        "code_prefixes": [],
        "name_prefixes": [],
        "name_fullmatch": [],
        "code_fullmatch": [
            r"^p1uxfix1-wc-[a-f0-9]+$"
        ],
        "source_test": "tests/test_phase_p2fix1_default_route_rewiring.py",
        "source_helper": (
            "P1-UX-FIX-1 working copies created by the P1-UX-FIX-1 "
            "test users (p1uxfix1-b-aa9, p1uxfix1-bad-5) with "
            "an 8-char hex suffix."
        ),
        "not_a_user_project": (
            "The anchored regex requires 'p1uxfix1-wc-' "
            "followed by 8+ hex chars. User projects that "
            "merely contain the prefix as a substring (e.g. "
            "'p1uxfix1b-summary') are NOT classified."
        ),
    },
    {
        "rule_id": "ph2-test-walkthrough",
        "match_policy": "name_and_code",
        "description": (
            "Phase 2 test walkthrough fixture. Exactly one "
            "correlated identity pair."
        ),
        "code_prefixes": [],
        "name_prefixes": [],
        "name_fullmatch": [],
        "code_fullmatch": [],
        "identity_pairs": [
            {
                "name_fullmatch": r"^PH2 Test Walkthrough$",
                "code_fullmatch": r"^ph2-test-walkthrough$",
            },
        ],
        "source_test": (
            "tests/test_phase_pilot_hotfix_2_runtime_scenario_source.py"
        ),
        "source_helper": (
            "line 221: project_code = 'ph2-test-walkthrough' "
            "and project_name = 'PH2 Test Walkthrough' (line 245) "
            "created by the ph2-user test user."
        ),
        "not_a_user_project": (
            "A single correlated pair. A valid PH2 name with "
            "a different valid PH2 code is not classified "
            "because there is exactly one pair and the "
            "matcher requires both fields of that exact pair."
        ),
    },
    {
        "rule_id": "testpilotproj-fixtures",
        "match_policy": "code_only",
        "description": (
            "Generic test pilot fixtures. Anchored regex on "
            "project_code: ^testpilotproj(-\\d+)?$"
        ),
        "code_prefixes": [],
        "name_prefixes": [],
        "name_fullmatch": [],
        "code_fullmatch": [
            r"^testpilotproj(-\d+)?$"
        ],
        "source_test": "tests/test_phase_p2fix1_default_route_rewiring.py",
        "source_helper": (
            "TestPilotProj (and TestPilotProj-2) created by the "
            "legacy QA user."
        ),
        "not_a_user_project": (
            "The anchored regex requires exactly "
            "'testpilotproj' or 'testpilotproj-N' (N is a "
            "digit). User projects that merely contain the "
            "prefix as a substring (e.g. "
            "'testpilotproj-review') are NOT classified."
        ),
    },
    {
        "rule_id": "opex-lifecycle-fixture",
        "match_policy": "name_only",
        "description": (
            "OPEX lifecycle test fixtures. Anchored regex on "
            "project_name: ^OPEX Lifecycle Test "
            "(persist|order|proj-table|concurrent|codes|rollback|dirty|htmx)$"
        ),
        "code_prefixes": [],
        "name_prefixes": [],
        "name_fullmatch": [
            r"^OPEX Lifecycle Test (persist|order|proj-table|concurrent|codes|rollback|dirty|htmx)$"
        ],
        "code_fullmatch": [],
        "source_test": "tests/test_workbook_v2_opex_row_lifecycle.py",
        "source_helper": (
            "line 60: project_name = f\"OPEX Lifecycle Test {suffix}\" "
            "where suffix is one of the eight tokens above."
        ),
        "not_a_user_project": (
            "Anchored regex; user projects that merely "
            "contain the literal prefix as a substring (e.g. "
            "'Acme OPEX Lifecycle Test persist migration') "
            "are NOT classified because the regex must "
            "end exactly at the eighth token."
        ),
    },
    {
        "rule_id": "inputs-test-fixture",
        "match_policy": "name_and_code",
        "description": (
            "Inputs Test sheet fixtures. Seven explicit "
            "correlated identity pairs, one per suffix."
        ),
        "code_prefixes": [],
        "name_prefixes": [],
        "name_fullmatch": [],
        "code_fullmatch": [],
        "identity_pairs": [
            {
                "name_fullmatch": r"^Inputs Test parity-01$",
                "code_fullmatch": r"^inputs-test-parity-01$",
            },
            {
                "name_fullmatch": r"^Inputs Test mwh-units$",
                "code_fullmatch": r"^inputs-test-mwh-units$",
            },
            {
                "name_fullmatch": r"^Inputs Test runtime-matrix$",
                "code_fullmatch": r"^inputs-test-runtime-matrix$",
            },
            {
                "name_fullmatch": r"^Inputs Test html-01$",
                "code_fullmatch": r"^inputs-test-html-01$",
            },
            {
                "name_fullmatch": r"^Inputs Test editable-01$",
                "code_fullmatch": r"^inputs-test-editable-01$",
            },
            {
                "name_fullmatch": r"^Inputs Test prot-ref-01$",
                "code_fullmatch": r"^inputs-test-prot-ref-01$",
            },
            {
                "name_fullmatch": r"^Inputs Test htmx-01$",
                "code_fullmatch": r"^inputs-test-htmx-01$",
            },
        ],
        "source_test": "tests/test_workbook_v2_sheet_inputs.py",
        "source_helper": (
            "line 48: _create_project(client, suffix) calls "
            "/projects/create with project_name = "
            "f'Inputs Test {suffix}'. The seven suffixes are "
            "called at lines 175 (parity-01), 301 (mwh-units), "
            "353 (runtime-matrix), 434 (html-01), 526 "
            "(editable-01), 568 (prot-ref-01), and 592 "
            "(htmx-01). project_code is produced by "
            "_slugify_project_code(project_name) so the code "
            "is 'inputs-test-<suffix>'."
        ),
        "not_a_user_project": (
            "A valid 'Inputs Test html-01' name combined with "
            "the 'inputs-test-runtime-matrix' code is NOT "
            "classified because the pair must come from the "
            "same correlated pair. User projects with names "
            "or codes outside the seven pairs are not "
            "classified."
        ),
    },
    {
        "rule_id": "inputs-slice1-fixture",
        "match_policy": "name_and_code",
        "description": (
            "Inputs Slice 1 fixtures. Fifteen explicit "
            "correlated identity pairs, one per source "
            "suffix. The slugified code suffix must "
            "correspond to the same source suffix as the "
            "name."
        ),
        "code_prefixes": [],
        "name_prefixes": [],
        "name_fullmatch": [],
        "code_fullmatch": [],
        "identity_pairs": [
            {"name_fullmatch": r"^Inputs Slice1 routes$",
             "code_fullmatch": r"^inputs-slice1-routes$"},
            {"name_fullmatch": r"^Inputs Slice1 sequence$",
             "code_fullmatch": r"^inputs-slice1-sequence$"},
            {"name_fullmatch": r"^Inputs Slice1 outside$",
             "code_fullmatch": r"^inputs-slice1-outside$"},
            {"name_fullmatch": r"^Inputs Slice1 unknown$",
             "code_fullmatch": r"^inputs-slice1-unknown$"},
            {"name_fullmatch": r"^Inputs Slice1 name$",
             "code_fullmatch": r"^inputs-slice1-name$"},
            {"name_fullmatch": r"^Inputs Slice1 invalid$",
             "code_fullmatch": r"^inputs-slice1-invalid$"},
            {"name_fullmatch": r"^Inputs Slice1 protected$",
             "code_fullmatch": r"^inputs-slice1-protected$"},
            {"name_fullmatch": r"^Inputs Slice1 stale-retry$",
             "code_fullmatch": r"^inputs-slice1-stale-retry$"},
            {"name_fullmatch": r"^Inputs Slice1 version$",
             "code_fullmatch": r"^inputs-slice1-version$"},
            {"name_fullmatch": r"^Inputs Slice1 cod_date$",
             "code_fullmatch": r"^inputs-slice1-cod-date$"},
            {"name_fullmatch": r"^Inputs Slice1 construction_months$",
             "code_fullmatch": r"^inputs-slice1-construction-months$"},
            {"name_fullmatch": r"^Inputs Slice1 horizon_years$",
             "code_fullmatch": r"^inputs-slice1-horizon-years$"},
            {"name_fullmatch": r"^Inputs Slice1 capacity_mw$",
             "code_fullmatch": r"^inputs-slice1-capacity-mw$"},
            {"name_fullmatch": r"^Inputs Slice1 p50_hours$",
             "code_fullmatch": r"^inputs-slice1-p50-hours$"},
            {"name_fullmatch": r"^Inputs Slice1 runtime$",
             "code_fullmatch": r"^inputs-slice1-runtime$"},
        ],
        "source_test": "tests/test_inputs_slice1_project_schedule_technical.py",
        "source_helper": (
            "line 46: _create_project(client, suffix) calls "
            "/projects/create with project_name = "
            "f'Inputs Slice1 {suffix}'. The fifteen suffixes "
            "are called at lines 229 (routes), 278 "
            "(sequence), 327 (outside), 344 (unknown), 362 "
            "(name), 398 (invalid), 418 (protected), 447 "
            "(stale-retry), 494 (version), 523 (loop over "
            "field_id.split('.')[-1] for the technical "
            "schedule: cod_date, construction_months, "
            "horizon_years, capacity_mw, p50_hours), and 544 "
            "(runtime). project_code is produced by "
            "_slugify_project_code(project_name) so the code "
            "is 'inputs-slice1-<slugified-suffix>'."
        ),
        "not_a_user_project": (
            "Fifteen correlated pairs. A valid 'Inputs "
            "Slice1 runtime' name combined with the "
            "'inputs-slice1-capacity-mw' code is NOT "
            "classified because the pair must come from the "
            "same correlated pair."
        ),
    },
    {
        "rule_id": "p2fix1-route-rewiring-fixture",
        "match_policy": "name_and_code",
        "description": (
            "P2FIX1 route-rewiring fixtures. Two correlated "
            "identity pairs: P2FIX1-WS-<token> requires the "
            "same kind and the same eight-character hex "
            "token in both project_name and project_code; "
            "P2FIX1-Test-<token> requires the same. The "
            "token is captured by the matched name regex and "
            "must equal the token captured by the matched "
            "code regex. A different kind or a different "
            "token is not classified."
        ),
        "code_prefixes": [],
        "name_prefixes": [],
        "name_fullmatch": [],
        "code_fullmatch": [],
        "identity_pairs": [
            {
                "name_fullmatch": (
                    r"^P2FIX1-WS-(?P<token>[a-f0-9]{8})$"
                ),
                "code_fullmatch": (
                    r"^p2fix1-ws-(?P<token>[a-f0-9]{8})$"
                ),
            },
            {
                "name_fullmatch": (
                    r"^P2FIX1-Test-(?P<token>[a-f0-9]{8})$"
                ),
                "code_fullmatch": (
                    r"^p2fix1-test-(?P<token>[a-f0-9]{8})$"
                ),
            },
        ],
        "source_test": "tests/test_phase_p2fix1_default_route_rewiring.py",
        "source_helper": (
            "line 540: project_name = f\"P2FIX1-Test-{unique}\"; "
            "line 565: project_name = f\"P2FIX1-WS-{unique}\" "
            "(unique = uuid4().hex[:8]). The slugify helper "
            "lowercases and replaces non-alphanumeric with '-'."
        ),
        "not_a_user_project": (
            "The same kind (WS or Test) and the same "
            "eight-character hex token must appear in both "
            "project_name and project_code. A WS name with "
            "a Test code, or a WS name with a different "
            "eight-character token, is NOT classified."
        ),
    },
]


# ---------------------------------------------------------------------------
# Canonical serialization helpers
# ---------------------------------------------------------------------------

def _canonical_value(v: Any) -> Any:
    """Return a JSON-canonical representation of ``v`` that
    preserves ``None``, empty string, ``0``, and ``False``
    exactly. We never use ``value or ''`` for authoritative
    fingerprint serialization."""
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return v
    if isinstance(v, (str, float)):
        return v
    # Fall back to string for unknown types so the hash is
    # deterministic.
    return str(v)


def _canonical_row_payload(row: Dict[str, Any], fields: Tuple[str, ...]) -> str:
    """Return a canonical, ordered, JSON-serializable payload
    for a single project row. Uses ``_canonical_value`` so
    ``None``/``""``/``0``/``False`` are preserved exactly."""
    return json.dumps(
        [_canonical_value(row.get(f)) for f in fields],
        sort_keys=False,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


# ---------------------------------------------------------------------------
# Time / paths
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _backup_filename(timestamp: str) -> str:
    return f"finco_runs.db.backup.{timestamp}.sqlite3"


# ---------------------------------------------------------------------------
# Schema / table metadata
# ---------------------------------------------------------------------------

def _has_column(cur: sqlite3.Cursor, table: str, column: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def _schema_fingerprint(cur: sqlite3.Cursor) -> str:
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [r[0] for r in cur.fetchall()]
    payload: List[str] = []
    for t in tables:
        cur.execute(f"PRAGMA table_info({t})")
        cols = [(r[1], r[2]) for r in cur.fetchall()]
        payload.append(f"{t}({','.join(f'{n}:{ty}' for n, ty in cols)})")
    return hashlib.sha256("|".join(payload).encode("utf-8")).hexdigest()


def _table_counts(cur: sqlite3.Cursor) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for t in SCHEMA_FINGERPRINT_TABLES:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            counts[t] = int(cur.fetchone()[0])
        except sqlite3.OperationalError:
            counts[t] = -1
    return counts


# ---------------------------------------------------------------------------
# Row-level helpers
# ---------------------------------------------------------------------------

def _row_fingerprint(row: Dict[str, Any]) -> str:
    """Compute the row fingerprint using canonical
    serialization that preserves ``None``/``""``/``0``/
    ``False`` exactly. The fingerprint covers the nine
    ROW_IDENTITY_FIELDS, sorted by field name for
    determinism."""
    payload = json.dumps(
        {f: _canonical_value(row.get(f)) for f in ROW_IDENTITY_FIELDS},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _is_protected_row(project: Dict[str, Any]) -> bool:
    origin = (project.get("project_origin") or "")
    tpl_src = (project.get("template_source") or "")
    is_readonly = int(project.get("is_readonly") or 0)
    if origin in NON_USER_ORIGINS:
        return True
    if tpl_src in CANONICAL_TEMPLATE_SOURCES:
        return True
    if is_readonly == 1:
        return True
    return False


def _has_protected_keyword(project: Dict[str, Any]) -> bool:
    code = (project.get("project_code") or "").lower()
    name = (project.get("project_name") or "").lower()
    for kw in PROTECTED_KEYWORDS:
        if kw in code or kw in name:
            return True
    return False


MatchPolicy = Literal["code_only", "name_only", "name_and_code"]


def _code_matches(rule: Dict[str, Any], code_lc: str, code: str) -> bool:
    if any(code_lc.startswith(p) for p in rule["code_prefixes"]):
        return True
    if any(re.fullmatch(rx, code) for rx in rule["code_fullmatch"]):
        return True
    return False


def _name_matches(rule: Dict[str, Any], name_lc: str, name: str) -> bool:
    if any(name_lc.startswith(p) for p in rule["name_prefixes"]):
        return True
    if any(re.fullmatch(rx, name) for rx in rule["name_fullmatch"]):
        return True
    return False


def _pair_matches(rule: Dict[str, Any], name: str, code: str) -> bool:
    """Return True iff at least one correlated identity pair
    on the rule matches the given (name, code) pair in its
    entirety — the name regex AND the code regex must both
    fullmatch, and any named capture groups (e.g. ``token``
    in P2FIX1) must agree. A name from pair A combined
    with a code from pair B is NOT a match."""
    pairs = rule.get("identity_pairs") or []
    for pair in pairs:
        name_rx = pair.get("name_fullmatch")
        code_rx = pair.get("code_fullmatch")
        if not name_rx or not code_rx:
            continue
        nm = re.fullmatch(name_rx, name)
        cm = re.fullmatch(code_rx, code)
        if nm is None or cm is None:
            continue
        # All named capture groups must agree between name
        # and code. P2FIX1 uses (?P<token>...) to prove the
        # same kind and the same eight-character token.
        ok = True
        for key in nm.groupdict():
            if nm.group(key) != cm.group(key):
                ok = False
                break
        if ok:
            return True
    return False


def _validate_rule_structure(rule: Dict[str, Any]) -> None:
    """Fail-closed validation of a single rule's structure.
    Unknown match_policy, missing or empty identity_pairs
    on a name_and_code rule, or missing/empty code or name
    matchers on single-field rules, raise SystemExit with
    a precise message. The classifier never silently falls
    back to independent set matching."""
    policy = rule.get("match_policy")
    if policy not in ("code_only", "name_only", "name_and_code"):
        raise SystemExit(
            f"ERROR: rule {rule.get('rule_id')!r} has unknown "
            f"match_policy {policy!r}; expected one of "
            "'code_only', 'name_only', 'name_and_code'."
        )
    if policy == "code_only":
        if not (rule.get("code_prefixes") or rule.get("code_fullmatch")):
            raise SystemExit(
                f"ERROR: rule {rule.get('rule_id')!r} is code_only "
                "but has no code_prefixes and no code_fullmatch."
            )
    elif policy == "name_only":
        if not (rule.get("name_prefixes") or rule.get("name_fullmatch")):
            raise SystemExit(
                f"ERROR: rule {rule.get('rule_id')!r} is name_only "
                "but has no name_prefixes and no name_fullmatch."
            )
    elif policy == "name_and_code":
        pairs = rule.get("identity_pairs")
        if not pairs or not isinstance(pairs, list):
            raise SystemExit(
                f"ERROR: rule {rule.get('rule_id')!r} is "
                "name_and_code but identity_pairs is missing or empty."
            )
        for i, pair in enumerate(pairs):
            if not isinstance(pair, dict):
                raise SystemExit(
                    f"ERROR: rule {rule.get('rule_id')!r} identity_pairs[{i}] "
                    "is not a dict."
                )
            if not pair.get("name_fullmatch") or not pair.get("code_fullmatch"):
                raise SystemExit(
                    f"ERROR: rule {rule.get('rule_id')!r} identity_pairs[{i}] "
                    "must contain both name_fullmatch and code_fullmatch."
                )


def _classify_row(
    project: Dict[str, Any],
) -> Optional[str]:
    """Return the rule_id that classifies this project as a
    test artifact, or None. The match_policy declared on
    each rule controls the matching contract:

      * ``code_only``     — a code_prefixes / code_fullmatch
        on the rule must match the project_code.
      * ``name_only``     — a name_prefixes / name_fullmatch
        on the rule must match the project_name.
      * ``name_and_code`` — at least one correlated
        ``identity_pairs`` entry on the rule must match the
        (project_name, project_code) pair IN ITS ENTIRETY.
        The name regex AND the code regex must both
        fullmatch, and any named capture groups (e.g. the
        P2FIX1 ``token``) must agree. A valid name from
        pair A combined with a valid code from pair B is
        NOT a match.

    Rules whose repository evidence only guarantees one
    field use the single-field policy. Rules that have
    paired name-and-code evidence use the correlated
    identity-pair contract. Unknown or inconsistent rule
    configuration is rejected with SystemExit by
    ``_validate_rule_structure``; the classifier never
    silently falls back to independent set matching."""
    code = (project.get("project_code") or "")
    name = (project.get("project_name") or "")
    code_lc = code.lower()
    name_lc = name.lower()
    for rule in CANDIDATE_RULES:
        _validate_rule_structure(rule)
        policy = rule["match_policy"]
        if policy == "code_only":
            if _code_matches(rule, code_lc, code):
                return rule["rule_id"]
        elif policy == "name_only":
            if _name_matches(rule, name_lc, name):
                return rule["rule_id"]
        elif policy == "name_and_code":
            if _pair_matches(rule, name, code):
                return rule["rule_id"]
    return None


# ---------------------------------------------------------------------------
# Logical state fingerprint
# ---------------------------------------------------------------------------

def _read_projects_for_state(
    cur: sqlite3.Cursor,
) -> List[Dict[str, Any]]:
    cur.execute(
        "SELECT " + ", ".join(PROJECT_STATE_FIELDS) + " FROM projects"
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _state_payload(
    cur: sqlite3.Cursor,
    *,
    replay_candidate_ids: Optional[Set[str]] = None,
    normalize_replay_archived: bool = False,
) -> Tuple[str, str, Dict[str, int]]:
    """Return (project_state_sha256, schema_fingerprint,
    table_counts) computed inside one read transaction.

    Two distinct normalizations are supported:

    * ``replay_candidate_ids`` only — the candidate rows
      have their ``updated_at`` normalized to ``created_at``
      so the fingerprint is independent of when the
      ``updated_at`` was set. ``archived`` is preserved
      exactly. This is the *pre-apply* fingerprint computed
      against the live DB; the live DB may have any
      ``archived`` value.

    * ``replay_candidate_ids`` AND
      ``normalize_replay_archived=True`` — additionally the
      candidate rows have their ``archived`` field forced
      to 1. This is the *replay* fingerprint: it represents
      the post-apply state in which every candidate is
      archived=1 with its ``updated_at`` equal to its
      ``created_at``. A same-manifest replay must match
      this fingerprint.

    Without ``replay_candidate_ids``, the fingerprint is the
    *exact* current logical state. The pre-apply fingerprint
    is what a first apply must match.
    """
    schema_fp = _schema_fingerprint(cur)
    table_counts = _table_counts(cur)
    rows = _read_projects_for_state(cur)
    rows_sorted = sorted(rows, key=lambda r: (r.get("project_id") or ""))
    payload_parts: List[str] = [
        f"schema={schema_fp}",
    ]
    for t, n in sorted(table_counts.items()):
        payload_parts.append(f"{t}_count={n}")
    for row in rows_sorted:
        pid = row.get("project_id") or ""
        normalized: Dict[str, Any] = dict(row)
        if replay_candidate_ids and pid in replay_candidate_ids:
            created_at = row.get("created_at") or ""
            normalized["updated_at"] = created_at
            if normalize_replay_archived:
                normalized["archived"] = 1
        for field_name in PROJECT_STATE_FIELDS:
            payload_parts.append(
                f"{pid}.{field_name}="
                f"{_canonical_row_payload(normalized, (field_name,))[1:-1]}"
            )
    project_state_sha256 = hashlib.sha256(
        "\n".join(payload_parts).encode("utf-8")
    ).hexdigest()
    return project_state_sha256, schema_fp, table_counts


def _read_db_metadata(
    db_path: Path,
    cur: sqlite3.Cursor,
) -> Dict[str, Any]:
    """Read the exact current logical state of the DB. This
    is the metadata the pre-apply fingerprint is based on."""
    project_state_sha256, schema_fp, counts = _state_payload(
        cur, replay_candidate_ids=None
    )
    return {
        "absolute_path": str(db_path.expanduser().resolve()),
        "schema_fingerprint": schema_fp,
        "pre_apply_project_state_sha256": project_state_sha256,
        "table_counts": counts,
    }


def _read_projects(cur: sqlite3.Cursor) -> List[Dict[str, Any]]:
    cur.execute(
        "SELECT project_id, user_id, project_code, project_name,"
        " project_type, project_origin, source_project_template,"
        " template_source, archived, is_readonly, created_at, updated_at"
        " FROM projects"
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def generate_manifest(
    db_path: Path,
    out_path: Path,
) -> Dict[str, Any]:
    """Generate a Manifest v2 from the exact current state
    of ``db_path``. The manifest records both the pre-apply
    and the replay logical fingerprints so a same-manifest
    replay is a verifiable no-op."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    if not _has_column(cur, "projects", "archived"):
        conn.close()
        raise SystemExit("ERROR: 'projects.archived' column missing")

    # Compute metadata + classify inside a single read
    # transaction for WAL determinism.
    cur.execute("BEGIN")
    try:
        db_meta = _read_db_metadata(db_path, cur)
        projects = _read_projects(cur)
    finally:
        cur.execute("COMMIT")
    conn.close()

    candidates: List[Dict[str, Any]] = []
    for p in projects:
        if int(p.get("archived") or 0) == 1:
            continue
        if _is_protected_row(p):
            continue
        if _has_protected_keyword(p):
            continue
        rule_id = _classify_row(p)
        if rule_id is None:
            continue
        candidates.append({
            "project_id": p["project_id"],
            "user_id": p["user_id"],
            "project_code": p["project_code"],
            "project_name": p["project_name"],
            "project_origin": p["project_origin"],
            "template_source": p["template_source"],
            "created_at": p["created_at"],
            "classification_rule": rule_id,
            "row_fingerprint": _row_fingerprint(p),
        })

    # Now compute the replay fingerprint with the candidate
    # set known. The replay fingerprint represents the
    # normalized state in which every candidate is
    # archived=1 and updated_at is the candidate's
    # created_at. This is what a same-manifest replay must
    # match.
    candidate_ids = {c["project_id"] for c in candidates}
    replay_conn = sqlite3.connect(db_path)
    rcur = replay_conn.cursor()
    rcur.execute("BEGIN")
    try:
        replay_state_sha256, replay_schema_fp, replay_counts = (
            _state_payload(
                rcur,
                replay_candidate_ids=candidate_ids,
                normalize_replay_archived=True,
            )
        )
    finally:
        rcur.execute("COMMIT")
    replay_conn.close()
    # Authoritative: the replay schema and table counts MUST
    # match the pre-apply metadata. The pre-apply fingerprint
    # is computed against the same schema/counts, so this is
    # a consistency assertion.
    assert replay_schema_fp == db_meta["schema_fingerprint"], (
        "replay schema fingerprint must equal pre-apply schema fingerprint"
    )
    assert replay_counts == db_meta["table_counts"], (
        "replay table counts must equal pre-apply table counts"
    )

    # File-level fingerprints are informational only; the
    # authoritative state is the logical fingerprint.
    raw_file_sha256 = hashlib.sha256(db_path.read_bytes()).hexdigest()
    raw_size_bytes = db_path.stat().st_size

    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "generated_at": _now_iso(),
        "database": {
            **db_meta,
            "replay_state_sha256": replay_state_sha256,
            "raw_file_sha256": raw_file_sha256,
            "raw_size_bytes": raw_size_bytes,
        },
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
    out_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------

def _resolve_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _is_path_inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _validate_backup_dir(
    backup_dir: Path, db_path: Path, repo_root: Path
) -> None:
    """Refuse backup dirs that resolve to:
       * the repository root or any subdir of it
       * the live DB directory or any subdir of it
       * the live DB file itself"""
    backup_resolved = backup_dir.expanduser().resolve()
    repo_resolved = repo_root.resolve()
    db_resolved = db_path.expanduser().resolve()
    db_dir_resolved = db_resolved.parent

    if backup_resolved == repo_resolved or _is_path_inside(
        backup_resolved, repo_resolved
    ):
        raise SystemExit(
            f"ERROR: --backup-dir {backup_resolved} is inside the "
            f"repository root {repo_resolved}. Use an external "
            "path, e.g. /var/backups/finco."
        )
    if backup_resolved == db_dir_resolved or _is_path_inside(
        backup_resolved, db_dir_resolved
    ):
        raise SystemExit(
            f"ERROR: --backup-dir {backup_resolved} is inside the "
            f"live DB directory {db_dir_resolved}. Use an "
            "external path, e.g. /var/backups/finco."
        )
    if backup_resolved == db_resolved:
        raise SystemExit(
            "ERROR: --backup-dir is the same file as the live DB."
        )


def _create_and_verify_backup(
    db_path: Path,
    backup_path: Path,
    pre_backup_metadata: Dict[str, Any],
) -> Path:
    """Create a timestamped backup via SQLite's backup API
    and verify it against the locked pre-update state.
    Returns the exact path used for the backup."""
    # Use the SQLite backup API for a consistent copy.
    src = sqlite3.connect(str(db_path))
    try:
        dst = sqlite3.connect(str(backup_path))
        try:
            with dst:
                src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    # Verify.
    bconn = sqlite3.connect(str(backup_path))
    try:
        bcur = bconn.cursor()
        bcur.execute("PRAGMA integrity_check")
        ic = bcur.fetchone()
        if not ic or ic[0] != "ok":
            raise SystemExit(
                f"ERROR: backup integrity_check returned {ic!r}"
            )
        bcur.execute("SELECT COUNT(*) FROM projects")
        if int(bcur.fetchone()[0]) != pre_backup_metadata["projects"]:
            raise SystemExit(
                "ERROR: backup projects count does not match "
                "pre-update state"
            )
        bcur.execute("SELECT COUNT(*) FROM scenarios")
        if int(bcur.fetchone()[0]) != pre_backup_metadata["scenarios"]:
            raise SystemExit(
                "ERROR: backup scenarios count does not match "
                "pre-update state"
            )
        bcur.execute("SELECT COUNT(*) FROM runs")
        if int(bcur.fetchone()[0]) != pre_backup_metadata["runs"]:
            raise SystemExit(
                "ERROR: backup runs count does not match "
                "pre-update state"
            )
        bcur.execute("SELECT COUNT(*) FROM workspace_states")
        if int(bcur.fetchone()[0]) != pre_backup_metadata[
            "workspace_states"
        ]:
            raise SystemExit(
                "ERROR: backup workspace_states count does not "
                "match pre-update state"
            )
        # Logical verification.
        bcur.execute("BEGIN")
        try:
            backup_pre_apply, backup_schema, _ = _state_payload(
                bcur, replay_candidate_ids=None
            )
        finally:
            bcur.execute("COMMIT")
        if backup_schema != pre_backup_metadata["schema_fingerprint"]:
            raise SystemExit(
                "ERROR: backup schema fingerprint does not match "
                "pre-update state"
            )
        if backup_pre_apply != pre_backup_metadata[
            "pre_apply_project_state_sha256"
        ]:
            raise SystemExit(
                "ERROR: backup logical pre-apply fingerprint "
                "does not match pre-update state"
            )
    finally:
        bconn.close()
    return backup_path


# ---------------------------------------------------------------------------
# Locked validation helper
# ---------------------------------------------------------------------------

def validate_manifest_against_connection(
    conn: sqlite3.Connection,
    manifest: Dict[str, Any],
) -> ManifestValidationResult:
    """Re-validate every assertion of the manifest against
    the database state observed inside the caller's open
    transaction. Returns a ``ManifestValidationResult``.

    The validation state is decided by the validator, not
    by the caller. Partial replay ALWAYS fails closed; there
    is no boolean parameter that could allow it.

    The caller is responsible for COMMIT/ROLLBACK."""
    cur = conn.cursor()
    db_path = Path(conn.execute("PRAGMA database_list").fetchone()[2])

    # 1. exact path
    manifest_path = Path(
        manifest["database"]["absolute_path"]
    ).expanduser().resolve()
    db_path_resolved = db_path.expanduser().resolve()
    if manifest_path != db_path_resolved:
        raise SystemExit(
            f"ERROR: manifest database path {manifest_path} does not "
            f"match live DB path {db_path_resolved}. Generate a new "
            "manifest for this exact DB."
        )

    # 2. schema fingerprint
    schema_fp = _schema_fingerprint(cur)
    if schema_fp != manifest["database"]["schema_fingerprint"]:
        raise SystemExit(
            "ERROR: schema fingerprint does not match the manifest."
        )

    # 3. table counts
    counts = _table_counts(cur)
    manifest_counts = manifest["database"].get("table_counts", {})
    for t, n in manifest_counts.items():
        if counts.get(t, -1) != n:
            raise SystemExit(
                f"ERROR: table count for {t!r} changed since the "
                "manifest was generated. Re-generate."
            )

    # 4. every candidate identity
    active: List[Dict[str, Any]] = []
    already_archived: List[Dict[str, Any]] = []
    candidate_ids: Set[str] = set()
    for cand in manifest["candidates"]:
        pid = cand["project_id"]
        candidate_ids.add(pid)
        cur.execute(
            "SELECT project_id, user_id, project_code, project_name,"
            " project_type, project_origin, source_project_template,"
            " template_source, is_readonly, archived"
            " FROM projects WHERE project_id = ?",
            (pid,),
        )
        row = cur.fetchone()
        if row is None:
            raise SystemExit(
                f"ERROR: manifest candidate {pid!r} no longer exists"
            )
        cols = [d[0] for d in cur.description]
        row_d = dict(zip(cols, row))
        if _row_fingerprint(row_d) != cand["row_fingerprint"]:
            raise SystemExit(
                f"ERROR: manifest candidate {pid!r} identity changed "
                "(user_id, project_code, project_name, project_origin, "
                "template_source or is_readonly). Re-generate."
            )
        if _is_protected_row(row_d):
            raise SystemExit(
                f"ERROR: manifest candidate {pid!r} is now a "
                "protected row. Refusing to archive."
            )
        if _has_protected_keyword(row_d):
            raise SystemExit(
                f"ERROR: manifest candidate {pid!r} matches a "
                "protected keyword. Refusing to archive."
            )
        rule_id = _classify_row(row_d)
        if rule_id != cand["classification_rule"]:
            raise SystemExit(
                f"ERROR: manifest candidate {pid!r} no longer matches "
                f"classification_rule={cand['classification_rule']!r} "
                f"(now {rule_id!r})."
            )
        if int(row_d.get("archived") or 0) == 1:
            already_archived.append(cand)
        else:
            active.append(cand)

    # 5. Determine the validation state.
    n_total = len(manifest["candidates"])
    n_active = len(active)
    n_archived = len(already_archived)

    if n_total == 0:
        state: str = "NO_CANDIDATES"
    elif n_active == 0 and n_archived == n_total:
        state = "ALREADY_APPLIED"
    elif n_active == n_total and n_archived == 0:
        state = "FIRST_APPLY"
    else:
        # Partial replay: ALWAYS fail closed.
        raise SystemExit(
            "ERROR: partial replay: "
            f"{n_active} manifest candidates are still active "
            f"and {n_archived} are already archived. "
            "Re-generate the manifest so operator intent is "
            "unambiguous."
        )

    # 6. Validate the appropriate logical fingerprint.
    if state == "FIRST_APPLY":
        # Pre-apply fingerprint must match.
        if conn.in_transaction:
            current_state_sha, _, _ = _state_payload(
                cur, replay_candidate_ids=None
            )
        else:
            cur.execute("BEGIN")
            try:
                current_state_sha, _, _ = _state_payload(
                    cur, replay_candidate_ids=None
                )
            finally:
                cur.execute("COMMIT")
        if current_state_sha != manifest["database"][
            "pre_apply_project_state_sha256"
        ]:
            raise SystemExit(
                "ERROR: pre-apply logical fingerprint does not match "
                "the manifest. Re-generate the manifest."
            )
    elif state == "ALREADY_APPLIED":
        # Replay fingerprint must match. The replay fingerprint
        # represents the DB state with every manifest candidate
        # treated as archived=1 and updated_at=created_at. The
        # current DB after a successful first apply satisfies
        # archived=1 for the candidate set, but its updated_at
        # will be the archive timestamp. The replay fingerprint
        # therefore normalizes updated_at to created_at and
        # archived to 1 so it is independent of the live
        # updated_at.
        if conn.in_transaction:
            current_state_sha, _, _ = _state_payload(
                cur,
                replay_candidate_ids=candidate_ids,
                normalize_replay_archived=True,
            )
        else:
            cur.execute("BEGIN")
            try:
                current_state_sha, _, _ = _state_payload(
                    cur,
                    replay_candidate_ids=candidate_ids,
                    normalize_replay_archived=True,
                )
            finally:
                cur.execute("COMMIT")
        if current_state_sha != manifest["database"][
            "replay_state_sha256"
        ]:
            raise SystemExit(
                "ERROR: replay logical fingerprint does not match "
                "the manifest. A non-candidate row changed, a "
                "candidate identity changed, a candidate became "
                "protected, a candidate disappeared, or a "
                "protected table count changed. Re-generate."
            )
    # NO_CANDIDATES: no logical-fingerprint comparison; the
    # state is decided purely by the candidate_count.

    pre_update_metadata: Dict[str, Any] = {
        "projects": counts["projects"],
        "scenarios": counts["scenarios"],
        "runs": counts["runs"],
        "workspace_states": counts["workspace_states"],
        "schema_fingerprint": schema_fp,
        "pre_apply_project_state_sha256": (
            manifest["database"]["pre_apply_project_state_sha256"]
        ),
    }
    return ManifestValidationResult(
        state=state,
        active_candidates=tuple(active),
        archived_candidates=tuple(already_archived),
        pre_update_metadata=pre_update_metadata,
        current_table_counts=counts,
        current_project_state_sha256=(
            manifest["database"]["pre_apply_project_state_sha256"]
            if state == "FIRST_APPLY"
            else manifest["database"]["replay_state_sha256"]
        ),
        current_schema_fingerprint=schema_fp,
    )


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------

def apply(
    db_path: Path,
    manifest_path: Path,
    backup_dir: Path,
) -> ApplyResult:
    """Apply a manifest against ``db_path`` with full
    fail-closed locking. Returns an ``ApplyResult``."""
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("manifest_version") != MANIFEST_VERSION:
        raise SystemExit(
            f"ERROR: manifest_version {manifest.get('manifest_version')!r} "
            f"is not supported; expected {MANIFEST_VERSION}"
        )

    repo_root = _resolve_repo_root()
    _validate_backup_dir(backup_dir, db_path, repo_root)
    if not backup_dir.is_dir():
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise SystemExit(
                f"ERROR: backup directory {backup_dir!r} is not "
                f"writable: {e!r}"
            )

    conn = sqlite3.connect(str(db_path))
    db_path_resolved = db_path.expanduser().resolve()
    manifest_path_resolved = manifest_path.expanduser().resolve()
    try:
        # Acquire the write lock immediately so all
        # subsequent reads and the backup (if needed) see a
        # consistent state.
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        # 1. full validation under the lock. The validator
        #    decides the state; we do not have a boolean
        #    override.
        result = validate_manifest_against_connection(conn, manifest)

        if result.state == "NO_CANDIDATES":
            # Nothing to do. COMMIT, report NO_CANDIDATES.
            cur.execute("COMMIT")
            return ApplyResult(
                status=APPLY_STATUS_NO_CANDIDATES,
                rows_archived_now=0,
                backup_path=None,
                project_state_sha256_after=(
                    result.current_project_state_sha256
                ),
                database_path_resolved=str(db_path_resolved),
                manifest_path_resolved=str(manifest_path_resolved),
            )

        if result.state == "ALREADY_APPLIED":
            # Same-manifest replay. All candidates are
            # already archived, every identity still matches,
            # and the replay fingerprint matches. COMMIT,
            # report ALREADY_APPLIED, no backup.
            cur.execute("COMMIT")
            return ApplyResult(
                status=APPLY_STATUS_ALREADY_APPLIED,
                rows_archived_now=0,
                backup_path=None,
                project_state_sha256_after=(
                    result.current_project_state_sha256
                ),
                database_path_resolved=str(db_path_resolved),
                manifest_path_resolved=str(manifest_path_resolved),
            )

        # state == "FIRST_APPLY"
        # 2. backup under the lock, AFTER the validator has
        #    classified the state as FIRST_APPLY.
        timestamp = _now_compact()
        backup_path = backup_dir / _backup_filename(timestamp)
        exact_backup_path = _create_and_verify_backup(
            db_path, backup_path, result.pre_update_metadata
        )
        # 3. update exactly the active candidates.
        for cand in result.active_candidates:
            cur.execute(
                "UPDATE projects SET archived = 1, updated_at = ?"
                " WHERE project_id = ? AND archived = 0",
                (_now_iso(), cand["project_id"]),
            )
        # 4. verify every manifest candidate is archived.
        for cand in manifest["candidates"]:
            cur.execute(
                "SELECT archived FROM projects WHERE project_id = ?",
                (cand["project_id"],),
            )
            r = cur.fetchone()
            if r is None or int(r[0] or 0) != 1:
                cur.execute("ROLLBACK")
                # Remove the just-created backup so a retry is
                # a clean re-apply.
                try:
                    exact_backup_path.unlink()
                except OSError:
                    pass
                raise SystemExit(
                    f"ERROR: post-update verification failed for "
                    f"{cand['project_id']!r}"
                )
        # 5. Read the post-update logical fingerprint for
        #    the ApplyResult. This is the pre-apply
        #    fingerprint re-computed against the now-archived
        #    DB. We are still inside the outer BEGIN
        #    IMMEDIATE transaction; _state_payload is read-
        #    only and does not need its own BEGIN when the
        #    connection is already in a transaction.
        if conn.in_transaction:
            post_state_sha, _, _ = _state_payload(
                cur, replay_candidate_ids=None
            )
        else:
            cur.execute("BEGIN")
            try:
                post_state_sha, _, _ = _state_payload(
                    cur, replay_candidate_ids=None
                )
            finally:
                cur.execute("COMMIT")
        cur.execute("COMMIT")
        return ApplyResult(
            status=APPLY_STATUS_APPLIED,
            rows_archived_now=len(result.active_candidates),
            backup_path=str(exact_backup_path),
            project_state_sha256_after=post_state_sha,
            database_path_resolved=str(db_path_resolved),
            manifest_path_resolved=str(manifest_path_resolved),
        )
    except SystemExit:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    except sqlite3.Error as e:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise SystemExit(f"ERROR: transaction failed: {e!r}")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Dry-run (delegates to the locked validator but does not
# acquire the write lock)
# ---------------------------------------------------------------------------

def dry_run(
    db_path: Path,
    manifest_path: Path,
) -> ManifestValidationResult:
    """Run the validator without acquiring the write lock.
    Used by the CLI to report the validation state without
    performing any writes."""
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("manifest_version") != MANIFEST_VERSION:
        raise SystemExit(
            f"ERROR: manifest_version {manifest.get('manifest_version')!r} "
            f"is not supported; expected {MANIFEST_VERSION}"
        )
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("BEGIN")
    try:
        return validate_manifest_against_connection(conn, manifest)
    finally:
        cur.execute("COMMIT")
        conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_validation_result(
    result: ManifestValidationResult,
    *,
    is_dry_run: bool,
) -> None:
    label = "DRY-RUN" if is_dry_run else "VALIDATE"
    state = result.state
    if state == "NO_CANDIDATES":
        print(
            f"{label}. status=NO_CANDIDATES "
            f"candidate_count=0 "
            f"rows_archived_now=0"
        )
    elif state == "FIRST_APPLY":
        print(
            f"{label}. status=FIRST_APPLY "
            f"active_count={len(result.active_candidates)} "
            f"already_archived_count=0"
        )
    elif state == "ALREADY_APPLIED":
        print(
            f"{label}. status=ALREADY_APPLIED "
            f"active_count=0 "
            f"already_archived_count={len(result.archived_candidates)}"
        )
    else:
        # PARTIAL_REPLAY is raised as SystemExit; this branch
        # is only reached if a future state is added.
        print(
            f"{label}. status={state} "
            f"active_count={len(result.active_candidates)} "
            f"already_archived_count={len(result.archived_candidates)}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Safe, fail-closed archive tooling for legacy "
            "automated test projects. See module docstring."
        )
    )
    parser.add_argument("--db", required=True, help="Path to the SQLite DB file")
    parser.add_argument(
        "--generate-manifest",
        default=None,
        help=(
            "Path to write the manifest JSON. Operator-local; "
            "excluded from Git via *.archive-manifest.local.json."
        ),
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help="Path to an existing manifest JSON (for --apply or dry-run review).",
    )
    parser.add_argument(
        "--backup-dir",
        default=None,
        help=(
            "Directory for the timestamped backup. REQUIRED for "
            "--apply. Must be OUTSIDE the repository and OUTSIDE "
            "the live DB directory. Recommended: /var/backups/finco."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Actually perform the archive. Without this flag, "
            "the command is a dry-run that validates and prints "
            "but writes nothing."
        ),
    )
    parser.add_argument(
        "--audit-report",
        default=None,
        help=(
            "Path to write the operator-local audit JSON. "
            "Excluded from Git via *.archive-audit.local.json. "
            "Only written on --apply."
        ),
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.is_file():
        print(f"ERROR: db file not found: {db_path}", file=sys.stderr)
        return 2

    if args.generate_manifest:
        if args.apply or args.manifest:
            print(
                "ERROR: --generate-manifest is mutually exclusive "
                "with --apply and --manifest",
                file=sys.stderr,
            )
            return 2
        out = Path(args.generate_manifest)
        manifest = generate_manifest(db_path, out)
        print(f"Generated manifest v{manifest['manifest_version']}: {out}")
        print(
            f"DB logical state: pre_apply_project_state_sha256="
            f"{manifest['database']['pre_apply_project_state_sha256'][:16]}..."
            f" replay_state_sha256="
            f"{manifest['database']['replay_state_sha256'][:16]}..."
            f" schema={manifest['database']['schema_fingerprint'][:16]}..."
        )
        print(f"Candidate count: {manifest['candidate_count']}")
        print("Manifest is operator-local. Do NOT commit it to Git.")
        return 0

    if not args.manifest:
        print(
            "ERROR: --manifest is required for dry-run review or --apply",
            file=sys.stderr,
        )
        return 2

    manifest_path = Path(args.manifest)
    if not manifest_path.is_file():
        print(
            f"ERROR: manifest file not found: {manifest_path}",
            file=sys.stderr,
        )
        return 2
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("manifest_version") != MANIFEST_VERSION:
        print(
            f"ERROR: manifest_version {manifest.get('manifest_version')!r} "
            f"is not supported; expected {MANIFEST_VERSION}",
            file=sys.stderr,
        )
        return 3

    # Dry-run review: delegate to the locked validator but
    # do not acquire the write lock.
    try:
        result = dry_run(db_path, manifest_path)
    except SystemExit as exc:
        # The validator already printed a precise error. Echo
        # the exact reason to stdout so the operator can read
        # it without scrolling.
        print(str(exc), file=sys.stderr)
        return 4

    _print_validation_result(result, is_dry_run=True)

    if not args.apply:
        return 0

    if not args.backup_dir:
        print(
            "ERROR: --apply requires --backup-dir pointing to a "
            "directory outside the repository and outside the live "
            "DB directory. Recommended: /var/backups/finco.",
            file=sys.stderr,
        )
        return 5
    backup_dir = Path(args.backup_dir)
    apply_result = apply(db_path, manifest_path, backup_dir)
    print(
        f"APPLIED. status={apply_result.status} "
        f"rows_archived_now={apply_result.rows_archived_now} "
        f"backup_path={apply_result.backup_path or 'null'}"
    )
    if args.audit_report:
        audit_path = Path(args.audit_report)
        audit = {
            "manifest_version": manifest.get("manifest_version"),
            "generated_at": manifest.get("generated_at"),
            "applied_at": _now_iso(),
            "db_path_resolved": apply_result.database_path_resolved,
            "db_project_state_sha256_after": (
                apply_result.project_state_sha256_after
            ),
            "candidate_count": manifest.get("candidate_count", 0),
            "rows_archived_now": apply_result.rows_archived_now,
            "status": apply_result.status,
            "backup_dir": str(backup_dir.expanduser().resolve()),
            "backup_path": apply_result.backup_path,
        }
        audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True))
        print(f"Audit report (operator-local): {audit_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
