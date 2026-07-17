"""
finco_parity.schema — Versioned snapshot schema for legacy-engine characterization.

A "snapshot" is a deterministic, normalized, offline record of one legacy-engine
run for one baseline project.  The schema defines what fields are expected, which
are optional, and what sentinel value distinguishes "not calculated" from zero.

Design invariants
-----------------
- SCHEMA_VERSION is bumped whenever the schema changes in a backward-incompatible way.
- All numeric fields that the engine may not populate use None, not 0.0.
  The tolerance layer (Phase 1B) decides whether a numeric difference matters.
  The snapshot layer preserves the engine output faithfully.
- The schema is a plain Python dict-of-dicts description; validation uses
  validate_snapshot() which checks structural presence, not financial values.
- Production code never imports this module.
"""
from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "1.0.0"

# Sentinel: field was requested but the legacy engine did not produce it.
UNAVAILABLE = None

# Required top-level keys in every snapshot.
_REQUIRED_TOP_LEVEL = frozenset({
    "schema_version",
    "baseline_id",
    "engine_designation",
    "baseline_commit_sha",
    "run_path_id",
    "input_source_id",
    "warnings",
    "unavailable_sections",
    "period_grid",
    "operating_schedules",
    "financing",
    "returns",
})

# Optional top-level keys (present only when engine produces them).
_OPTIONAL_TOP_LEVEL = frozenset({
    "tax_and_cfads",
    "financial_statements",
})


class SnapshotValidationError(ValueError):
    """Raised when a snapshot dict fails structural validation."""


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    """Validate structural presence of required snapshot sections.

    Raises SnapshotValidationError on the first structural problem found.
    Does not validate financial values.
    """
    if not isinstance(snapshot, dict):
        raise SnapshotValidationError(
            f"Snapshot must be a dict, got {type(snapshot).__name__}"
        )

    sv = snapshot.get("schema_version")
    if sv != SCHEMA_VERSION:
        raise SnapshotValidationError(
            f"schema_version mismatch: expected {SCHEMA_VERSION!r}, got {sv!r}"
        )

    missing = _REQUIRED_TOP_LEVEL - snapshot.keys()
    if missing:
        raise SnapshotValidationError(
            f"Snapshot missing required keys: {sorted(missing)}"
        )

    baseline_id = snapshot.get("baseline_id")
    if not isinstance(baseline_id, str) or not baseline_id:
        raise SnapshotValidationError("baseline_id must be a non-empty string")

    period_grid = snapshot.get("period_grid")
    if not isinstance(period_grid, list):
        raise SnapshotValidationError("period_grid must be a list")

    # Each period grid entry must have period_index.
    for i, row in enumerate(period_grid):
        if not isinstance(row, dict):
            raise SnapshotValidationError(
                f"period_grid[{i}] must be a dict, got {type(row).__name__}"
            )
        if "period_index" not in row:
            raise SnapshotValidationError(
                f"period_grid[{i}] missing 'period_index'"
            )

    op = snapshot.get("operating_schedules")
    if not isinstance(op, dict):
        raise SnapshotValidationError("operating_schedules must be a dict")

    fin = snapshot.get("financing")
    if not isinstance(fin, dict):
        raise SnapshotValidationError("financing must be a dict")

    ret = snapshot.get("returns")
    if not isinstance(ret, dict):
        raise SnapshotValidationError("returns must be a dict")

    warnings = snapshot.get("warnings")
    if not isinstance(warnings, list):
        raise SnapshotValidationError("warnings must be a list")

    unavailable = snapshot.get("unavailable_sections")
    if not isinstance(unavailable, list):
        raise SnapshotValidationError("unavailable_sections must be a list")


def build_empty_snapshot(
    *,
    baseline_id: str,
    engine_designation: str,
    baseline_commit_sha: str,
    run_path_id: str,
    input_source_id: str,
) -> dict[str, Any]:
    """Return a structurally valid empty snapshot with all required keys present.

    Callers populate the period_grid, schedules and returns fields by running
    the legacy engine and calling the normalization layer.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "baseline_id": baseline_id,
        "engine_designation": engine_designation,
        "baseline_commit_sha": baseline_commit_sha,
        "run_path_id": run_path_id,
        "input_source_id": input_source_id,
        "warnings": [],
        "unavailable_sections": [],
        "period_grid": [],
        "operating_schedules": {
            "production_mwh": [],
            "revenue_keur": [],
            "opex_keur": [],
            "ebitda_keur": [],
            "book_depreciation_keur": [],
            "tax_depreciation_keur": [],
        },
        "tax_and_cfads": {
            "taxable_income_keur": [],
            "deductible_interest_keur": [],
            "cash_tax_keur": [],
            "loss_carryforward_keur": [],
            "cfads_proxy_keur": [],
        },
        "financing": {
            "senior_debt": {
                "opening_keur": [],
                "drawdown_keur": [],
                "interest_keur": [],
                "principal_keur": [],
                "debt_service_keur": [],
                "closing_keur": [],
                "dscr": [],
                "llcr": UNAVAILABLE,
                "dsra_keur": [],
            },
            "shl": {
                "opening_keur": [],
                "interest_keur": [],
                "principal_keur": [],
                "closing_keur": [],
            },
            "equity": {
                "injections_keur": [],
                "distributions_keur": [],
            },
        },
        "financial_statements": UNAVAILABLE,
        "returns": {
            "project_irr": UNAVAILABLE,
            "equity_irr": UNAVAILABLE,
            "avg_dscr": UNAVAILABLE,
            "actual_avg_dscr": UNAVAILABLE,
            "min_dscr": UNAVAILABLE,
            "total_revenue_keur": UNAVAILABLE,
            "total_ebitda_keur": UNAVAILABLE,
            "total_opex_keur": UNAVAILABLE,
            "total_tax_keur": UNAVAILABLE,
            "total_distributions_keur": UNAVAILABLE,
        },
    }
