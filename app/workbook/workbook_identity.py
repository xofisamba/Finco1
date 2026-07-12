"""STAB-1B — Composite Workbook V2 Identity.

Single canonical assembler for the full engine-effective workbook state.

Problem
-------
Before STAB-1B, ``ProjectInputSet.content_hash`` was a SHA-256 over scalar
snapshot values only.  Two workbooks could share the same scalar hash while
producing different engine outputs if they had different CAPEX/OPEX custom
sub-lines or were running under different scenarios.

Solution
--------
``CompositeWorkbookIdentity`` assembles one deterministic hash over five
axes:

1. Scalar state      — canonical ``ProjectInputSet`` scalar snapshot
2. CAPEX rows        — every active custom sub-line (engine-effective fields only)
3. OPEX rows         — every active custom sub-line (engine-effective fields only)
4. Scenario state    — active scenario identity + all effective overrides
5. Registry version  — ``WORKBOOK.version`` so schema changes rotate the hash

Include / exclude policy (by axis)
-----------------------------------
Scalar  — all fields that reach the adapter (``snapshot_origin`` non-empty
          values + provenance keys + workbook version).  Unknown legacy keys
          are included if non-empty because they may affect legacy adapter
          materialisation.

CAPEX   — ``sub_line_id``, ``parent_category_code``, ``amount_keur``.
          ``schedule_json`` is omitted: it is decomposed from ``amount_keur``
          by the schedule calculator; hashing ``amount_keur`` covers the same
          financial meaning without schedule-format variance.
          Excluded: ``label``, ``comments``, ``business_code``, ``source``,
          ``governance_state``, ``replay_metadata``, ``created_at``,
          ``updated_at``, ``id``, ``display_order``.

OPEX    — ``sub_line_id``, ``parent_group_code``, ``business_code``,
          ``amount_keur``, ``inflation_pct``.  ``business_code`` is included
          because it becomes the ``OpexItem.name`` seen by downstream code
          (though it does not affect numeric KPIs, naming uniqueness is an
          invariant).
          Excluded: ``label``, ``comments``, ``source``, ``created_at``,
          ``updated_at``, ``id``, ``display_order``.

Scenario — ``scenario_id`` (stable identity), ``scenario_name``
           (display, but included so rename is visible), and every key in
           ``overrides_json`` including the reserved opaque keys
           ``_capex_sub_line_overrides`` and ``_opex_sub_line_overrides``.
           Excluded: ``base_input_set`` (redundant — covered by Scalar axis),
           timestamps, audit fields.

Registry — ``WORKBOOK.version`` (already included via Scalar axis; also
           stored as explicit registry_version key so registry-only changes
           are visible even when scalar snapshot is unchanged).

Ordering / determinism
-----------------------
CAPEX rows are sorted by ``sub_line_id`` (UUID) — independent of
``display_order`` so presentation reorders do not affect identity.
OPEX rows are sorted by ``sub_line_id``.
Scenario ``overrides_json`` is sorted recursively.

Reorder semantics
-----------------
``display_order`` is presentation-only for both CAPEX and OPEX:
the engine folds rows purely by amount/type, commutatively.
Reordering rows MUST NOT change the composite identity.

Legacy migration
----------------
Scalar-only hashes stored before STAB-1B will not match the composite hash
even when all row tables are empty, because the composite hash includes an
explicit ``_schema: "composite_v1"`` discriminator key that scalar-only
hashes lack.

Transition: ``v2_atomic_draft_update`` re-derives the composite hash from
the live state on every CAS check.  Old scalar-only tokens stored in
``draft_content_hash`` are never consulted for the gating comparison
(the column is updated on every successful write, migrating in-place).

A legacy token submitted by a client that loaded before STAB-1B will be
rejected with a normal 409 StaleContentError — the user refreshes and
gets a composite token.  This is the correct behaviour: the workbook state
on disk has not changed, but the identity representation has been upgraded.

Transactional consistency
--------------------------
``assemble_for_workspace`` reads scalar state from a pre-loaded
``WorkspaceStateRecord`` and calls two DB queries for CAPEX/OPEX rows.
These are separate reads in sequence, not a single BEGIN … COMMIT.

Known limitation (deferred): if a CAPEX or OPEX row is mutated between the
workspace read and the row query, the assembled identity may be inconsistent.
The row-command path uses its own ``BEGIN EXCLUSIVE`` transaction and the
workspace record is re-read there.  Full transactional consistency across all
three reads is deferred to a future migration of the scalar snapshot into the
same row-table transaction.

``assemble_transactional`` (used by ``v2_atomic_draft_update``) takes a
SQLite connection cursor that already holds a ``BEGIN EXCLUSIVE`` lock — it
reads all three tables inside that lock window, closing the race.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

logger = logging.getLogger(__name__)

# Discriminator key — absent from pre-STAB-1B scalar-only hashes, so a
# composite hash is never mistaken for a legacy hash.
_SCHEMA_VERSION = "composite_v1"


# ---------------------------------------------------------------------------
# Canonical row types (engine-effective fields only)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, order=True)
class CanonicalCapexRow:
    """Engine-effective CAPEX sub-line fingerprint."""
    sub_line_id: str
    parent_category_code: str
    amount_keur: float


@dataclass(frozen=True, order=True)
class CanonicalOpexRow:
    """Engine-effective OPEX sub-line fingerprint."""
    sub_line_id: str
    parent_group_code: str
    business_code: str
    amount_keur: float
    inflation_pct: float


@dataclass(frozen=True)
class CanonicalScenarioState:
    """Engine-effective scenario identity."""
    scenario_id: Optional[str]      # None → Base Case (no active scenario)
    scenario_name: Optional[str]    # display only but included for visibility
    overrides: Mapping[str, Any]    # full overrides_json dict, including reserved keys

    def to_payload(self) -> dict:
        """Deterministic serialisable form."""
        return {
            "scenario_id": self.scenario_id or "",
            "scenario_name": self.scenario_name or "",
            "overrides": _sort_dict_recursive(dict(self.overrides)),
        }


# ---------------------------------------------------------------------------
# Identity payload
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CompositeWorkbookIdentity:
    """Full engine-effective workbook state identity for Workbook V2.

    Construct via ``assemble_for_workspace()`` or ``assemble_from_parts()``.
    """
    workbook_version: str
    scalar_snapshot: Mapping[str, str]    # non-empty snapshot_origin values
    template_source: str
    project_origin: str
    capex_rows: tuple[CanonicalCapexRow, ...]
    opex_rows: tuple[CanonicalOpexRow, ...]
    scenario: CanonicalScenarioState
    composite_hash: str                   # SHA-256 of the full payload


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sort_dict_recursive(d: Any) -> Any:
    """Recursively sort dict keys for deterministic serialisation."""
    if isinstance(d, dict):
        return {k: _sort_dict_recursive(d[k]) for k in sorted(d)}
    if isinstance(d, (list, tuple)):
        return [_sort_dict_recursive(i) for i in d]
    return d


def _compute_composite_hash(
    workbook_version: str,
    scalar_snapshot: Mapping[str, str],
    template_source: str,
    project_origin: str,
    capex_rows: Sequence[CanonicalCapexRow],
    opex_rows: Sequence[CanonicalOpexRow],
    scenario: CanonicalScenarioState,
) -> str:
    """Deterministic SHA-256 over the full composite workbook state.

    The ``_schema`` key is a discriminator that ensures composite hashes
    can never collide with pre-STAB-1B scalar-only hashes.
    """
    payload: dict[str, Any] = {
        "_schema": _SCHEMA_VERSION,
        "_workbook_version": workbook_version,
        "_template_source": template_source,
        "_project_origin": project_origin,
        "scalar": {
            f"snap:{k}": v
            for k, v in sorted(scalar_snapshot.items())
            if v
        },
        "capex_rows": [
            {
                "sub_line_id": r.sub_line_id,
                "parent_category_code": r.parent_category_code,
                "amount_keur": r.amount_keur,
            }
            for r in sorted(capex_rows)
        ],
        "opex_rows": [
            {
                "sub_line_id": r.sub_line_id,
                "parent_group_code": r.parent_group_code,
                "business_code": r.business_code,
                "amount_keur": r.amount_keur,
                "inflation_pct": r.inflation_pct,
            }
            for r in sorted(opex_rows)
        ],
        "scenario": scenario.to_payload(),
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Row loaders
# ---------------------------------------------------------------------------

def _load_canonical_capex_rows(project_id: str) -> tuple[CanonicalCapexRow, ...]:
    """Load active CAPEX sub-lines and extract engine-effective fields."""
    if not project_id:
        return ()
    try:
        from app.persistence.capex_sub_lines import get_active_sub_lines_for_project
        rows = get_active_sub_lines_for_project(project_id)
        return tuple(
            CanonicalCapexRow(
                sub_line_id=r.sub_line_id,
                parent_category_code=r.parent_category_code,
                amount_keur=float(r.amount_keur),
            )
            for r in rows
        )
    except Exception:
        logger.exception("STAB-1B: failed to load CAPEX rows; project_id=%s", project_id)
        return ()


def _load_canonical_opex_rows(project_id: str) -> tuple[CanonicalOpexRow, ...]:
    """Load active OPEX sub-lines and extract engine-effective fields."""
    if not project_id:
        return ()
    try:
        from app.persistence.opex_sub_lines import get_active_sub_lines_for_project
        rows = get_active_sub_lines_for_project(project_id)
        return tuple(
            CanonicalOpexRow(
                sub_line_id=r.sub_line_id,
                parent_group_code=r.parent_group_code,
                business_code=r.business_code,
                amount_keur=float(r.amount_keur),
                inflation_pct=float(r.inflation_pct),
            )
            for r in rows
        )
    except Exception:
        logger.exception("STAB-1B: failed to load OPEX rows; project_id=%s", project_id)
        return ()


def _canonical_scenario(
    active_scenario_id: Optional[str],
    active_scenario_name: Optional[str],
    user_id: str,
) -> CanonicalScenarioState:
    """Load and canonicalise the active scenario."""
    if not active_scenario_id:
        return CanonicalScenarioState(
            scenario_id=None,
            scenario_name=None,
            overrides={},
        )
    try:
        from app.persistence.scenarios_repository import get_scenario
        rec = get_scenario(active_scenario_id, user_id)
        if rec is None:
            return CanonicalScenarioState(
                scenario_id=active_scenario_id,
                scenario_name=active_scenario_name,
                overrides={},
            )
        return CanonicalScenarioState(
            scenario_id=rec.scenario_id,
            scenario_name=rec.scenario_name,
            overrides=dict(rec.overrides or {}),
        )
    except Exception:
        logger.exception(
            "STAB-1B: failed to load scenario; scenario_id=%s", active_scenario_id
        )
        return CanonicalScenarioState(
            scenario_id=active_scenario_id,
            scenario_name=active_scenario_name,
            overrides={},
        )


# ---------------------------------------------------------------------------
# Public assembly entry points
# ---------------------------------------------------------------------------

def assemble_from_parts(
    scalar_snapshot: Mapping[str, str],
    template_source: str,
    project_origin: str,
    workbook_version: str,
    capex_rows: Sequence[CanonicalCapexRow],
    opex_rows: Sequence[CanonicalOpexRow],
    scenario: CanonicalScenarioState,
) -> CompositeWorkbookIdentity:
    """Build a ``CompositeWorkbookIdentity`` from pre-loaded parts.

    This is the pure / testable entry point — no DB reads.
    """
    h = _compute_composite_hash(
        workbook_version=workbook_version,
        scalar_snapshot=scalar_snapshot,
        template_source=template_source,
        project_origin=project_origin,
        capex_rows=capex_rows,
        opex_rows=opex_rows,
        scenario=scenario,
    )
    return CompositeWorkbookIdentity(
        workbook_version=workbook_version,
        scalar_snapshot=scalar_snapshot,
        template_source=template_source,
        project_origin=project_origin,
        capex_rows=tuple(sorted(capex_rows)),
        opex_rows=tuple(sorted(opex_rows)),
        scenario=scenario,
        composite_hash=h,
    )


def assemble_for_workspace(
    ws: Any,  # WorkspaceStateRecord
    *,
    user_id: str,
    project_id: str,
    workbook_version: str,
) -> CompositeWorkbookIdentity:
    """Assemble the composite identity for a WorkspaceStateRecord.

    Reads CAPEX rows, OPEX rows, and the active scenario from the DB.
    The scalar state is taken from ``ws.draft_snapshot``.

    Note: three separate reads (workspace already read by caller; CAPEX/OPEX
    rows and scenario each require one additional query).  Full transactional
    consistency across all reads is a deferred improvement.
    """
    from app.workbook.registry import WORKBOOK as _wb
    _wv = workbook_version or _wb.version

    scalar_snapshot = dict(ws.draft_snapshot or {})
    template_source = scalar_snapshot.get("template_source", "")
    project_origin = scalar_snapshot.get("project_origin", "")

    capex_rows = _load_canonical_capex_rows(project_id)
    opex_rows = _load_canonical_opex_rows(project_id)
    scenario = _canonical_scenario(
        active_scenario_id=ws.active_scenario_id,
        active_scenario_name=ws.active_scenario_name,
        user_id=user_id,
    )

    return assemble_from_parts(
        scalar_snapshot=scalar_snapshot,
        template_source=template_source,
        project_origin=project_origin,
        workbook_version=_wv,
        capex_rows=capex_rows,
        opex_rows=opex_rows,
        scenario=scenario,
    )


def assemble_transactional(
    draft_snapshot_json: str,
    project_id: str,
    user_id: str,
    active_scenario_id: Optional[str],
    active_scenario_name: Optional[str],
    cursor: Any,  # sqlite3.Cursor already inside BEGIN EXCLUSIVE
    workbook_version: str,
) -> CompositeWorkbookIdentity:
    """Assemble composite identity inside an existing exclusive transaction.

    Used by ``v2_atomic_draft_update``.  All three reads happen while the
    BEGIN EXCLUSIVE lock is held, providing transactional consistency across
    scalar + row + scenario state.

    Args:
        draft_snapshot_json: raw JSON string of ``draft_snapshot_json`` column.
        project_id: project UUID.
        user_id: user UUID (needed for scenario query).
        active_scenario_id: from workspace row.
        active_scenario_name: from workspace row.
        cursor: SQLite cursor, already inside BEGIN EXCLUSIVE.
        workbook_version: WORKBOOK.version string.

    Returns:
        ``CompositeWorkbookIdentity`` with consistent hash.
    """
    import json as _json
    from app.workbook.registry import WORKBOOK as _wb
    _wv = workbook_version or _wb.version

    scalar_snapshot = _json.loads(draft_snapshot_json or "{}")
    template_source = scalar_snapshot.get("template_source", "")
    project_origin = scalar_snapshot.get("project_origin", "")

    # --- CAPEX rows (inside transaction) ---
    capex_rows: list[CanonicalCapexRow] = []
    try:
        cursor.execute(
            "SELECT sub_line_id, parent_category_code, amount_keur "
            "FROM capex_sub_lines "
            "WHERE project_id=? AND is_active=1",
            (project_id,),
        )
        for r in cursor.fetchall():
            capex_rows.append(CanonicalCapexRow(
                sub_line_id=r["sub_line_id"],
                parent_category_code=r["parent_category_code"],
                amount_keur=float(r["amount_keur"]),
            ))
    except Exception:
        logger.exception("STAB-1B: CAPEX row read failed inside transaction; project_id=%s", project_id)

    # --- OPEX rows (inside transaction) ---
    opex_rows: list[CanonicalOpexRow] = []
    try:
        cursor.execute(
            "SELECT sub_line_id, parent_group_code, business_code, amount_keur, inflation_pct "
            "FROM opex_sub_lines "
            "WHERE project_id=? AND is_active=1",
            (project_id,),
        )
        for r in cursor.fetchall():
            opex_rows.append(CanonicalOpexRow(
                sub_line_id=r["sub_line_id"],
                parent_group_code=r["parent_group_code"],
                business_code=r["business_code"],
                amount_keur=float(r["amount_keur"]),
                inflation_pct=float(r["inflation_pct"]),
            ))
    except Exception:
        logger.exception("STAB-1B: OPEX row read failed inside transaction; project_id=%s", project_id)

    # --- Scenario (inside transaction) ---
    scenario_overrides: dict = {}
    if active_scenario_id:
        try:
            cursor.execute(
                "SELECT overrides_json FROM scenarios WHERE scenario_id=?",
                (active_scenario_id,),
            )
            row = cursor.fetchone()
            if row:
                scenario_overrides = _json.loads(row["overrides_json"] or "{}")
        except Exception:
            logger.exception("STAB-1B: scenario read failed inside transaction; scenario_id=%s", active_scenario_id)

    scenario = CanonicalScenarioState(
        scenario_id=active_scenario_id,
        scenario_name=active_scenario_name,
        overrides=scenario_overrides,
    )

    return assemble_from_parts(
        scalar_snapshot=scalar_snapshot,
        template_source=template_source,
        project_origin=project_origin,
        workbook_version=_wv,
        capex_rows=capex_rows,
        opex_rows=opex_rows,
        scenario=scenario,
    )
