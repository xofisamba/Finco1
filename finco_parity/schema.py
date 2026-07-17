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

Unavailability levels
---------------------
- UNAVAILABLE (None): sentinel for "field requested but engine did not produce it".
- unavailable_sections: top-level sections that could not be captured at all.
- unavailable_fields: per-section dict of field names that are explicitly absent.
- An all-None schedule list is NOT automatically a successfully captured schedule;
  real-value tests in test_phase1a_parity_runner.py verify numeric content.
"""
from __future__ import annotations

import math
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
    "unavailable_fields",
    "period_grid",
    "operating_schedules",
    "tax_and_cfads",
    "financing",
    "financial_statements",
    "returns",
})

# Required keys within operating_schedules.
_REQUIRED_OPERATING_SCHEDULES = frozenset({
    "production_mwh",
    "revenue_keur",
    "opex_keur",
    "ebitda_keur",
    "book_depreciation_keur",
    "tax_depreciation_keur",
})

# Required keys within financing.senior_debt.
_REQUIRED_SENIOR_DEBT = frozenset({
    "closing_keur",
    "interest_keur",
    "principal_keur",
    "debt_service_keur",
    "dscr",
    "llcr",
})

# Required keys within financing.shl.
_REQUIRED_SHL = frozenset({
    "closing_keur",
    "interest_keur",
    "principal_keur",
    "service_keur",
})

# Required keys within financing.equity.
_REQUIRED_EQUITY = frozenset({
    "distribution_keur",
})

# Required period-grid row keys (structural, not value).
_REQUIRED_PERIOD_ROW_KEYS = frozenset({
    "period_index",
    "date",
    "year_index",
    "period_in_year",
    "is_operation",
    "start_date",
    "is_construction",
})

# Required keys within returns.
_REQUIRED_RETURNS = frozenset({
    "project_irr",
    "equity_irr",
    "sponsor_irr",
    "min_llcr",
    "total_distribution_keur",
    "total_revenue_keur",
})

# Required provenance keys (must be non-empty strings).
_REQUIRED_PROVENANCE = frozenset({
    "baseline_id",
    "engine_designation",
    "baseline_commit_sha",
    "run_path_id",
    "input_source_id",
})


class SnapshotValidationError(ValueError):
    """Raised when a snapshot dict fails structural validation."""


def _check_no_nonfinite(section_name: str, data: Any, path: str = "") -> None:
    """Recursively check that no non-finite floats exist in data."""
    if isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            raise SnapshotValidationError(
                f"Non-finite float at {path or section_name}: {data!r}"
            )
    elif isinstance(data, list):
        for i, item in enumerate(data):
            _check_no_nonfinite(section_name, item, f"{path or section_name}[{i}]")
    elif isinstance(data, dict):
        for k, v in data.items():
            _check_no_nonfinite(section_name, v, f"{path or section_name}.{k}")


def _check_series_lengths(section: str, data: dict, required_keys: frozenset, n_periods: int) -> None:
    """Verify that each list-valued field in data has length n_periods."""
    for field in required_keys:
        val = data.get(field)
        if val is not None and isinstance(val, list):
            if len(val) != n_periods:
                raise SnapshotValidationError(
                    f"{section}.{field} length {len(val)} != period_grid length {n_periods}"
                )


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    """Validate structural integrity of a snapshot dict.

    Checks performed:
    1.  Top-level type and required keys.
    2.  schema_version matches SCHEMA_VERSION.
    3.  Required provenance values are non-empty strings.
    4.  period_grid: list, each row is a dict with required keys; indices sorted/unique.
    5.  operating_schedules: required keys; series lengths match period count.
    6.  tax_and_cfads: dict present; series lengths match period count.
    7.  financing.senior_debt: required keys; series lengths match.
    8.  financing.shl: required keys; series lengths match.
    9.  financing.equity: required key; series length matches.
    10. returns: required keys all present.
    11. warnings and unavailable_sections are lists.
    12. unavailable_fields is a dict mapping str→list-of-str.
    13. financial_statements key present (value may be None/unavailable).
    14. unavailable_sections consistency: sections listed must not have data.
    15. No non-finite floats in any section.

    Does NOT validate financial values.
    """
    if not isinstance(snapshot, dict):
        raise SnapshotValidationError(
            f"Snapshot must be a dict, got {type(snapshot).__name__}"
        )

    # 1. Required top-level keys
    missing = _REQUIRED_TOP_LEVEL - snapshot.keys()
    if missing:
        raise SnapshotValidationError(
            f"Snapshot missing required keys: {sorted(missing)}"
        )

    # 2. schema_version
    sv = snapshot.get("schema_version")
    if sv != SCHEMA_VERSION:
        raise SnapshotValidationError(
            f"schema_version mismatch: expected {SCHEMA_VERSION!r}, got {sv!r}"
        )

    # 3. Provenance strings
    for key in _REQUIRED_PROVENANCE:
        val = snapshot.get(key)
        if not isinstance(val, str) or not val:
            raise SnapshotValidationError(
                f"{key!r} must be a non-empty string, got {val!r}"
            )

    # 4. period_grid
    period_grid = snapshot["period_grid"]
    if not isinstance(period_grid, list):
        raise SnapshotValidationError("period_grid must be a list")

    period_indices: list[int | float] = []
    for i, row in enumerate(period_grid):
        if not isinstance(row, dict):
            raise SnapshotValidationError(
                f"period_grid[{i}] must be a dict, got {type(row).__name__}"
            )
        missing_row = _REQUIRED_PERIOD_ROW_KEYS - row.keys()
        if missing_row:
            raise SnapshotValidationError(
                f"period_grid[{i}] missing keys: {sorted(missing_row)}"
            )
        pi = row["period_index"]
        if not isinstance(pi, (int, float)) or (isinstance(pi, float) and math.isnan(pi)):
            raise SnapshotValidationError(
                f"period_grid[{i}].period_index must be numeric, got {pi!r}"
            )
        period_indices.append(pi)

    if len(period_indices) != len(set(period_indices)):
        raise SnapshotValidationError("period_grid contains duplicate period_index values")

    if period_indices != sorted(period_indices):
        raise SnapshotValidationError("period_grid is not sorted by period_index")

    n_periods = len(period_grid)

    # 5. operating_schedules
    op = snapshot["operating_schedules"]
    if not isinstance(op, dict):
        raise SnapshotValidationError("operating_schedules must be a dict")

    missing_op = _REQUIRED_OPERATING_SCHEDULES - op.keys()
    if missing_op:
        raise SnapshotValidationError(
            f"operating_schedules missing required keys: {sorted(missing_op)}"
        )

    if n_periods > 0:
        for field in _REQUIRED_OPERATING_SCHEDULES:
            val = op[field]
            if val is not None:
                if not isinstance(val, list):
                    raise SnapshotValidationError(
                        f"operating_schedules.{field} must be a list, got {type(val).__name__}"
                    )
                if len(val) != n_periods:
                    raise SnapshotValidationError(
                        f"operating_schedules.{field} length {len(val)} != "
                        f"period_grid length {n_periods}"
                    )

    # 6. tax_and_cfads
    tax = snapshot["tax_and_cfads"]
    if not isinstance(tax, dict):
        raise SnapshotValidationError("tax_and_cfads must be a dict")

    if n_periods > 0:
        for field, val in tax.items():
            if val is not None and isinstance(val, list) and len(val) != n_periods:
                raise SnapshotValidationError(
                    f"tax_and_cfads.{field} length {len(val)} != period_grid length {n_periods}"
                )

    # 7. financing
    fin = snapshot["financing"]
    if not isinstance(fin, dict):
        raise SnapshotValidationError("financing must be a dict")

    senior = fin.get("senior_debt")
    if not isinstance(senior, dict):
        raise SnapshotValidationError("financing.senior_debt must be a dict")

    missing_sd = _REQUIRED_SENIOR_DEBT - senior.keys()
    if missing_sd:
        raise SnapshotValidationError(
            f"financing.senior_debt missing required keys: {sorted(missing_sd)}"
        )

    if n_periods > 0:
        _check_series_lengths("financing.senior_debt", senior, _REQUIRED_SENIOR_DEBT, n_periods)

    # 8. financing.shl
    shl = fin.get("shl")
    if shl is not None:
        if not isinstance(shl, dict):
            raise SnapshotValidationError("financing.shl must be a dict")
        missing_shl = _REQUIRED_SHL - shl.keys()
        if missing_shl:
            raise SnapshotValidationError(
                f"financing.shl missing required keys: {sorted(missing_shl)}"
            )
        if n_periods > 0:
            _check_series_lengths("financing.shl", shl, _REQUIRED_SHL, n_periods)

    # 9. financing.equity
    equity = fin.get("equity")
    if equity is not None:
        if not isinstance(equity, dict):
            raise SnapshotValidationError("financing.equity must be a dict")
        missing_eq = _REQUIRED_EQUITY - equity.keys()
        if missing_eq:
            raise SnapshotValidationError(
                f"financing.equity missing required keys: {sorted(missing_eq)}"
            )
        if n_periods > 0:
            _check_series_lengths("financing.equity", equity, _REQUIRED_EQUITY, n_periods)

    # 10. returns
    ret = snapshot["returns"]
    if not isinstance(ret, dict):
        raise SnapshotValidationError("returns must be a dict")

    missing_ret = _REQUIRED_RETURNS - ret.keys()
    if missing_ret:
        raise SnapshotValidationError(
            f"returns missing required keys: {sorted(missing_ret)}"
        )

    # 11. warnings and unavailable_sections
    warnings_val = snapshot["warnings"]
    if not isinstance(warnings_val, list):
        raise SnapshotValidationError("warnings must be a list")

    unavailable_sections = snapshot["unavailable_sections"]
    if not isinstance(unavailable_sections, list):
        raise SnapshotValidationError("unavailable_sections must be a list")

    # 12. unavailable_fields
    unavailable_fields = snapshot["unavailable_fields"]
    if not isinstance(unavailable_fields, dict):
        raise SnapshotValidationError("unavailable_fields must be a dict")
    for section_path, fields in unavailable_fields.items():
        if not isinstance(section_path, str):
            raise SnapshotValidationError(
                f"unavailable_fields key must be a string, got {type(section_path).__name__}"
            )
        if not isinstance(fields, list) or not all(isinstance(f, str) for f in fields):
            raise SnapshotValidationError(
                f"unavailable_fields[{section_path!r}] must be a list of strings"
            )

    # 13. financial_statements key already checked by required-keys check.

    # 14. unavailable_sections consistency: financial_statements listed → value must be None
    if "financial_statements" in unavailable_sections:
        fs = snapshot.get("financial_statements")
        if fs is not None:
            raise SnapshotValidationError(
                "financial_statements listed in unavailable_sections but has non-None value"
            )

    # 15. No non-finite numbers anywhere
    for section in ("period_grid", "operating_schedules", "tax_and_cfads", "financing", "returns"):
        if section in snapshot:
            _check_no_nonfinite(section, snapshot[section])


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
        "unavailable_fields": {},
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
            "taxable_profit_keur": [],
            "taxable_income_before_losses_audit_keur": [],
            "taxable_profit_after_losses_audit_keur": [],
            "cit_accrual_audit_keur": [],
            "cash_tax_current_period_audit_keur": [],
            "corporate_tax_cash_keur": [],
            "tax_keur": [],
            "cash_tax_bridge_reconciliation_keur": [],
            "tax_loss_opening_audit_keur": [],
            "tax_loss_used_audit_keur": [],
            "tax_loss_closing_audit_keur": [],
            "tax_depreciation_audit_keur": [],
            "fiscal_reintegration_audit_keur": [],
            "cf_after_tax_keur": [],
            "r69_fcf_banks_keur": [],
            "r84_fcf_junior_keur": [],
            "r99_fcf_for_distribution_keur": [],
            "r102_fcf_for_shl_keur": [],
            "fcf_for_shl_keur": [],
        },
        "financing": {
            "senior_debt": {
                "opening_keur": [],
                "drawdown_keur": [],
                "closing_keur": [],
                "interest_keur": [],
                "principal_keur": [],
                "debt_service_keur": [],
                "dscr": [],
                "llcr": [],
                "plcr": [],
                "dsra_balance_keur": [],
                "dsra_contribution_keur": [],
                "cash_sweep_keur": [],
            },
            "shl": {
                "opening_keur": [],
                "interest_keur": [],
                "principal_keur": [],
                "service_keur": [],
                "closing_keur": [],
                "pik_keur": [],
                "gross_accrued_interest_keur": [],
            },
            "equity": {
                "distribution_keur": [],
                "injections_keur": [],
                "cf_after_reserves_keur": [],
                "lockup_active": [],
            },
        },
        "financial_statements": UNAVAILABLE,
        "returns": {
            "project_irr": UNAVAILABLE,
            "equity_irr": UNAVAILABLE,
            "sponsor_irr": UNAVAILABLE,
            "project_npv": UNAVAILABLE,
            "equity_npv": UNAVAILABLE,
            "avg_dscr": UNAVAILABLE,
            "min_dscr": UNAVAILABLE,
            "actual_avg_dscr": UNAVAILABLE,
            "actual_min_dscr": UNAVAILABLE,
            "min_llcr": UNAVAILABLE,
            "min_plcr": UNAVAILABLE,
            "periods_in_lockup": UNAVAILABLE,
            "total_revenue_keur": UNAVAILABLE,
            "total_opex_keur": UNAVAILABLE,
            "total_ebitda_keur": UNAVAILABLE,
            "total_tax_keur": UNAVAILABLE,
            "total_senior_ds_keur": UNAVAILABLE,
            "total_shl_service_keur": UNAVAILABLE,
            "total_distribution_keur": UNAVAILABLE,
            "equity_irr_method": "",
        },
    }
