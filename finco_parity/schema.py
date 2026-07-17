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
  Every all-None period series MUST be listed.  A populated field MUST NOT be listed.
- An all-None schedule list is NOT automatically a successfully captured schedule;
  real-value tests in test_phase1a_parity_runner.py verify numeric content.
"""
from __future__ import annotations

import math
import re
from typing import Any

SCHEMA_VERSION = "1.0.0"

# Sentinel: field was requested but the legacy engine did not produce it.
UNAVAILABLE = None

# ISO-8601 date pattern for period-row date validation.
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

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

# Required keys within operating_schedules — all emitted by normalize_operating_schedules().
_REQUIRED_OPERATING_SCHEDULES = frozenset({
    "production_mwh",
    "revenue_keur",
    "opex_keur",
    "ebitda_keur",
    "book_depreciation_keur",
    "tax_depreciation_keur",
})

# Required keys within tax_and_cfads — all emitted by normalize_tax_and_cfads().
_REQUIRED_TAX_AND_CFADS = frozenset({
    "taxable_profit_keur",
    "taxable_income_before_losses_audit_keur",
    "taxable_profit_after_losses_audit_keur",
    "cit_accrual_audit_keur",
    "cash_tax_current_period_audit_keur",
    "corporate_tax_cash_keur",
    "tax_keur",
    "cash_tax_bridge_reconciliation_keur",
    "tax_loss_opening_audit_keur",
    "tax_loss_used_audit_keur",
    "tax_loss_closing_audit_keur",
    "tax_depreciation_audit_keur",
    "fiscal_reintegration_audit_keur",
    "cf_after_tax_keur",
    "r69_fcf_banks_keur",
    "r84_fcf_junior_keur",
    "r99_fcf_for_distribution_keur",
    "r102_fcf_for_shl_keur",
    "fcf_for_shl_keur",
})

# Required keys within financing.senior_debt — all 12 emitted by normalize_financing().
_REQUIRED_SENIOR_DEBT = frozenset({
    "opening_keur",
    "drawdown_keur",
    "closing_keur",
    "interest_keur",
    "principal_keur",
    "debt_service_keur",
    "dscr",
    "llcr",
    "plcr",
    "dsra_balance_keur",
    "dsra_contribution_keur",
    "cash_sweep_keur",
})

# Required keys within financing.shl — all 7 emitted by normalize_financing().
_REQUIRED_SHL = frozenset({
    "opening_keur",
    "interest_keur",
    "principal_keur",
    "service_keur",
    "closing_keur",
    "pik_keur",
    "gross_accrued_interest_keur",
})

# Required keys within financing.equity — all 4 emitted by normalize_financing().
_REQUIRED_EQUITY = frozenset({
    "distribution_keur",
    "injections_keur",
    "cf_after_reserves_keur",
    "lockup_active",
})

# Required period-grid row keys (structural; types validated separately).
_REQUIRED_PERIOD_ROW_KEYS = frozenset({
    "period_index",
    "date",
    "year_index",
    "period_in_year",
    "is_operation",
    "start_date",
    "is_construction",
})

# Nullable period-row fields (the only ones that may be None / all-None).
_NULLABLE_PERIOD_ROW_FIELDS = frozenset({"start_date", "is_construction"})

# Required keys within returns — full contract of normalize_returns().
_REQUIRED_RETURNS = frozenset({
    "project_irr",
    "equity_irr",
    "sponsor_irr",
    "project_npv",
    "equity_npv",
    "avg_dscr",
    "min_dscr",
    "actual_avg_dscr",
    "actual_min_dscr",
    "min_llcr",
    "min_plcr",
    "periods_in_lockup",
    "total_revenue_keur",
    "total_opex_keur",
    "total_ebitda_keur",
    "total_tax_keur",
    "total_senior_ds_keur",
    "total_shl_service_keur",
    "total_distribution_keur",
    "equity_irr_method",
})

# Required provenance keys (must be non-empty strings).
_REQUIRED_PROVENANCE = frozenset({
    "baseline_id",
    "engine_designation",
    "baseline_commit_sha",
    "run_path_id",
    "input_source_id",
})

# Required top-level keys in a FinancialStatements dict (when not None).
_REQUIRED_FINANCIAL_STATEMENTS_KEYS = frozenset({"pnl", "balance_sheet", "pf_cash_waterfall"})

# Valid unavailable_sections names.
_KNOWN_UNAVAILABLE_SECTIONS = frozenset({"financial_statements"})

# Valid unavailable_fields section paths and the fields allowed within each.
_KNOWN_UNAVAILABLE_FIELDS: dict[str, frozenset[str]] = {
    "period_grid": _NULLABLE_PERIOD_ROW_FIELDS,
    "operating_schedules": _REQUIRED_OPERATING_SCHEDULES,
    "tax_and_cfads": _REQUIRED_TAX_AND_CFADS,
    "financing.senior_debt": _REQUIRED_SENIOR_DEBT,
    "financing.shl": _REQUIRED_SHL,
    "financing.equity": _REQUIRED_EQUITY,
    "returns": _REQUIRED_RETURNS,
}


class SnapshotValidationError(ValueError):
    """Raised when a snapshot dict fails structural validation."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

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


def _validate_series(section: str, field: str, val: Any, n_periods: int) -> None:
    """Validate that val is a list of exactly n_periods elements.

    Raises SnapshotValidationError if val is not a list (including None or scalar),
    or if its length does not match n_periods.
    """
    if not isinstance(val, list):
        raise SnapshotValidationError(
            f"{section}.{field} must be a list of length {n_periods}, "
            f"got {type(val).__name__!r}: {val!r}"
        )
    if len(val) != n_periods:
        raise SnapshotValidationError(
            f"{section}.{field} length {len(val)} != period_grid length {n_periods}"
        )


def _get_series_for_path(snapshot: dict, section_path: str, field: str) -> list | None:
    """Return the list value for a field in the given section path, or None if not found."""
    if section_path == "period_grid":
        pg = snapshot.get("period_grid", [])
        return [row.get(field) for row in pg]
    elif section_path == "operating_schedules":
        return snapshot.get("operating_schedules", {}).get(field)
    elif section_path == "tax_and_cfads":
        return snapshot.get("tax_and_cfads", {}).get(field)
    elif section_path == "financing.senior_debt":
        return snapshot.get("financing", {}).get("senior_debt", {}).get(field)
    elif section_path == "financing.shl":
        return snapshot.get("financing", {}).get("shl", {}).get(field)
    elif section_path == "financing.equity":
        return snapshot.get("financing", {}).get("equity", {}).get(field)
    elif section_path == "returns":
        return snapshot.get("returns", {}).get(field)
    return None


def _enumerate_all_period_series(snapshot: dict, n_periods: int):
    """Yield (section_path, field_name, list_value) for every period-series field."""
    if n_periods == 0:
        return
    pg = snapshot.get("period_grid", [])
    for field in sorted(_NULLABLE_PERIOD_ROW_FIELDS):
        yield "period_grid", field, [row.get(field) for row in pg]

    for section_path, required_keys in [
        ("operating_schedules", _REQUIRED_OPERATING_SCHEDULES),
        ("tax_and_cfads", _REQUIRED_TAX_AND_CFADS),
        ("financing.senior_debt", _REQUIRED_SENIOR_DEBT),
        ("financing.shl", _REQUIRED_SHL),
        ("financing.equity", _REQUIRED_EQUITY),
    ]:
        section = _get_section_dict(snapshot, section_path)
        if not isinstance(section, dict):
            continue
        for field in sorted(required_keys):
            val = section.get(field)
            if isinstance(val, list):
                yield section_path, field, val


def _get_section_dict(snapshot: dict, section_path: str) -> Any:
    """Resolve a section-path string to the corresponding dict in snapshot."""
    if section_path == "operating_schedules":
        return snapshot.get("operating_schedules")
    elif section_path == "tax_and_cfads":
        return snapshot.get("tax_and_cfads")
    elif section_path == "financing.senior_debt":
        return snapshot.get("financing", {}).get("senior_debt")
    elif section_path == "financing.shl":
        return snapshot.get("financing", {}).get("shl")
    elif section_path == "financing.equity":
        return snapshot.get("financing", {}).get("equity")
    elif section_path == "returns":
        return snapshot.get("returns")
    return None


def _is_all_none(series: list) -> bool:
    return len(series) > 0 and all(v is None for v in series)


# ---------------------------------------------------------------------------
# Semantic unavailable_fields validation
# ---------------------------------------------------------------------------

def _validate_unavailable_fields(
    snapshot: dict, unavailable_fields: dict, n_periods: int
) -> None:
    """Validate unavailable_fields against the real snapshot.

    Rules enforced:
    1.  Every section path must be a known path.
    2.  Every field name must be known for its section.
    3.  No duplicate field names within a section.
    4.  Field lists must be sorted.
    5.  For a declared-unavailable field, the actual value must be all-None.
    6.  A populated (any non-None) field must not be declared unavailable.
    7.  Every period series that is all-None must be declared unavailable.
    8.  An all-None series not listed must fail.
    9.  Unknown section paths must fail.
    """
    # Rules 1, 2, 3, 4, 5, 6
    for section_path, fields in unavailable_fields.items():
        # 1. Known section path
        if section_path not in _KNOWN_UNAVAILABLE_FIELDS:
            raise SnapshotValidationError(
                f"unavailable_fields contains unknown section path {section_path!r}. "
                f"Valid paths: {sorted(_KNOWN_UNAVAILABLE_FIELDS)}"
            )
        known_for_section = _KNOWN_UNAVAILABLE_FIELDS[section_path]

        # 3. No duplicates
        if len(fields) != len(set(fields)):
            raise SnapshotValidationError(
                f"unavailable_fields[{section_path!r}] contains duplicate field names"
            )

        for field in fields:
            # 2. Known field name (checked before sort so we report the unknown name clearly)
            if field not in known_for_section:
                raise SnapshotValidationError(
                    f"unavailable_fields[{section_path!r}] contains unknown field {field!r}. "
                    f"Valid fields: {sorted(known_for_section)}"
                )

        # 4. Sorted (checked after field validation for a cleaner error on unknown fields)
        if list(fields) != sorted(fields):
            raise SnapshotValidationError(
                f"unavailable_fields[{section_path!r}] must be sorted; "
                f"got {list(fields)!r}, expected {sorted(fields)!r}"
            )

        for field in fields:
            if n_periods == 0:
                continue

            # 5 & 6. Check actual value consistency
            actual = _get_series_for_path(snapshot, section_path, field)
            if actual is None:
                # Field not found in section; skip consistency check
                continue
            if isinstance(actual, list):
                populated = any(v is not None for v in actual)
                if populated:
                    raise SnapshotValidationError(
                        f"unavailable_fields declares {section_path!r}.{field!r} unavailable "
                        f"but the field has non-None values"
                    )
            else:
                # Scalar return value
                if actual is not None:
                    raise SnapshotValidationError(
                        f"unavailable_fields declares {section_path!r}.{field!r} unavailable "
                        f"but the field has non-None value {actual!r}"
                    )

    if n_periods == 0:
        return

    # Rules 7 & 8: every all-None series must be listed
    declared: dict[str, set[str]] = {
        path: set(fields) for path, fields in unavailable_fields.items()
    }
    for section_path, field, series in _enumerate_all_period_series(snapshot, n_periods):
        if _is_all_none(series):
            declared_for_section = declared.get(section_path, set())
            if field not in declared_for_section:
                raise SnapshotValidationError(
                    f"{section_path}.{field} is an all-None series but is not listed "
                    f"in unavailable_fields[{section_path!r}]"
                )


# ---------------------------------------------------------------------------
# Primary validation entry point
# ---------------------------------------------------------------------------

def validate_snapshot(snapshot: dict[str, Any]) -> None:
    """Validate structural integrity of a snapshot dict.

    Checks performed:
    1.  Top-level type and required keys.
    2.  schema_version matches SCHEMA_VERSION.
    3.  Required provenance values are non-empty strings.
    4.  period_grid: list, each row is a dict with required keys and correct types;
        indices sorted/unique.
    5.  operating_schedules: required keys; all values are lists of length n_periods.
    6.  tax_and_cfads: required keys; all values are lists of length n_periods.
    7.  financing (mandatory dict with three mandatory sub-sections).
    8.  financing.senior_debt: all 12 required keys; strict list length.
    9.  financing.shl: all 7 required keys; strict list length.
    10. financing.equity: all 4 required keys; strict list length.
    11. returns: full contract of 20 required keys.
    12. warnings is a list.
    13. unavailable_sections: list, known names, no duplicates, sorted.
    14. unavailable_fields: dict, semantic validation (9 rules).
    15. financial_statements bidirectional consistency.
    16. When financial_statements is available, validate top-level structure.
    17. No non-finite floats in any section.

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
    sv = snapshot["schema_version"]
    if sv != SCHEMA_VERSION:
        raise SnapshotValidationError(
            f"schema_version mismatch: expected {SCHEMA_VERSION!r}, got {sv!r}"
        )

    # 3. Provenance strings
    for key in _REQUIRED_PROVENANCE:
        val = snapshot[key]
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
        # Type validation for each row field
        _validate_period_row_types(i, row)
        pi = row["period_index"]
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
            _validate_series("operating_schedules", field, op[field], n_periods)

    # 6. tax_and_cfads
    tax = snapshot["tax_and_cfads"]
    if not isinstance(tax, dict):
        raise SnapshotValidationError("tax_and_cfads must be a dict")

    if not tax:
        raise SnapshotValidationError("tax_and_cfads must not be empty")

    missing_tax = _REQUIRED_TAX_AND_CFADS - tax.keys()
    if missing_tax:
        raise SnapshotValidationError(
            f"tax_and_cfads missing required keys: {sorted(missing_tax)}"
        )

    if n_periods > 0:
        for field in _REQUIRED_TAX_AND_CFADS:
            _validate_series("tax_and_cfads", field, tax[field], n_periods)

    # 7. financing
    fin = snapshot["financing"]
    if not isinstance(fin, dict):
        raise SnapshotValidationError("financing must be a dict")

    # 8. financing.senior_debt
    senior = fin.get("senior_debt")
    if not isinstance(senior, dict):
        raise SnapshotValidationError("financing.senior_debt must be a dict")

    missing_sd = _REQUIRED_SENIOR_DEBT - senior.keys()
    if missing_sd:
        raise SnapshotValidationError(
            f"financing.senior_debt missing required keys: {sorted(missing_sd)}"
        )

    if n_periods > 0:
        for field in _REQUIRED_SENIOR_DEBT:
            _validate_series("financing.senior_debt", field, senior[field], n_periods)

    # 9. financing.shl (mandatory)
    shl = fin.get("shl")
    if not isinstance(shl, dict):
        raise SnapshotValidationError(
            "financing.shl must be a dict (mandatory section)"
        )

    missing_shl = _REQUIRED_SHL - shl.keys()
    if missing_shl:
        raise SnapshotValidationError(
            f"financing.shl missing required keys: {sorted(missing_shl)}"
        )

    if n_periods > 0:
        for field in _REQUIRED_SHL:
            _validate_series("financing.shl", field, shl[field], n_periods)

    # 10. financing.equity (mandatory)
    equity = fin.get("equity")
    if not isinstance(equity, dict):
        raise SnapshotValidationError(
            "financing.equity must be a dict (mandatory section)"
        )

    missing_eq = _REQUIRED_EQUITY - equity.keys()
    if missing_eq:
        raise SnapshotValidationError(
            f"financing.equity missing required keys: {sorted(missing_eq)}"
        )

    if n_periods > 0:
        for field in _REQUIRED_EQUITY:
            _validate_series("financing.equity", field, equity[field], n_periods)

    # 11. returns
    ret = snapshot["returns"]
    if not isinstance(ret, dict):
        raise SnapshotValidationError("returns must be a dict")

    missing_ret = _REQUIRED_RETURNS - ret.keys()
    if missing_ret:
        raise SnapshotValidationError(
            f"returns missing required keys: {sorted(missing_ret)}"
        )

    # 12. warnings
    warnings_val = snapshot["warnings"]
    if not isinstance(warnings_val, list):
        raise SnapshotValidationError("warnings must be a list")

    # 13. unavailable_sections
    unavailable_sections = snapshot["unavailable_sections"]
    if not isinstance(unavailable_sections, list):
        raise SnapshotValidationError("unavailable_sections must be a list")

    for name in unavailable_sections:
        if not isinstance(name, str):
            raise SnapshotValidationError(
                f"unavailable_sections entries must be strings, got {type(name).__name__}"
            )
        if name not in _KNOWN_UNAVAILABLE_SECTIONS:
            raise SnapshotValidationError(
                f"unavailable_sections contains unknown name {name!r}. "
                f"Valid names: {sorted(_KNOWN_UNAVAILABLE_SECTIONS)}"
            )

    if len(unavailable_sections) != len(set(unavailable_sections)):
        raise SnapshotValidationError("unavailable_sections contains duplicate entries")

    if list(unavailable_sections) != sorted(unavailable_sections):
        raise SnapshotValidationError("unavailable_sections must be sorted")

    # 14. unavailable_fields
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

    _validate_unavailable_fields(snapshot, unavailable_fields, n_periods)

    # 15. financial_statements bidirectional consistency
    fs = snapshot["financial_statements"]
    fs_listed = "financial_statements" in unavailable_sections

    if fs is None and not fs_listed:
        raise SnapshotValidationError(
            "financial_statements is None but 'financial_statements' is not listed "
            "in unavailable_sections — add it to unavailable_sections"
        )

    if fs is not None and fs_listed:
        raise SnapshotValidationError(
            "financial_statements is available (non-None) but 'financial_statements' "
            "is listed in unavailable_sections — remove it from unavailable_sections"
        )

    # 16. When FS is available, validate top-level structure
    if fs is not None:
        if not isinstance(fs, dict):
            raise SnapshotValidationError(
                f"financial_statements must be a dict or None, got {type(fs).__name__}"
            )
        missing_fs = _REQUIRED_FINANCIAL_STATEMENTS_KEYS - fs.keys()
        if missing_fs:
            raise SnapshotValidationError(
                f"financial_statements missing required keys: {sorted(missing_fs)}"
            )

    # 17. No non-finite numbers anywhere
    for section in ("period_grid", "operating_schedules", "tax_and_cfads", "financing", "returns"):
        _check_no_nonfinite(section, snapshot[section])


def _validate_period_row_types(i: int, row: dict) -> None:
    """Validate the types of period-grid row fields."""
    # period_index: must be int (not float, not bool)
    pi = row["period_index"]
    if isinstance(pi, bool) or not isinstance(pi, int):
        raise SnapshotValidationError(
            f"period_grid[{i}].period_index must be an integer, got {type(pi).__name__!r}: {pi!r}"
        )

    # date: must be ISO date string (not None)
    date_val = row["date"]
    if not isinstance(date_val, str) or not _ISO_DATE_RE.match(date_val):
        raise SnapshotValidationError(
            f"period_grid[{i}].date must be an ISO date string (YYYY-MM-DD), got {date_val!r}"
        )

    # year_index: must be numeric (int or float), not bool
    yi = row["year_index"]
    if isinstance(yi, bool) or not isinstance(yi, (int, float)):
        raise SnapshotValidationError(
            f"period_grid[{i}].year_index must be numeric (int or float), "
            f"got {type(yi).__name__!r}: {yi!r}"
        )

    # period_in_year: must be numeric (int or float), not bool
    piy = row["period_in_year"]
    if isinstance(piy, bool) or not isinstance(piy, (int, float)):
        raise SnapshotValidationError(
            f"period_grid[{i}].period_in_year must be numeric (int or float), "
            f"got {type(piy).__name__!r}: {piy!r}"
        )

    # is_operation: must be bool
    is_op = row["is_operation"]
    if not isinstance(is_op, bool):
        raise SnapshotValidationError(
            f"period_grid[{i}].is_operation must be bool, got {type(is_op).__name__!r}: {is_op!r}"
        )

    # start_date: ISO date string or None
    sd = row["start_date"]
    if sd is not None:
        if not isinstance(sd, str) or not _ISO_DATE_RE.match(sd):
            raise SnapshotValidationError(
                f"period_grid[{i}].start_date must be an ISO date string or None, got {sd!r}"
            )

    # is_construction: bool or None
    ic = row["is_construction"]
    if ic is not None and not isinstance(ic, bool):
        raise SnapshotValidationError(
            f"period_grid[{i}].is_construction must be bool or None, "
            f"got {type(ic).__name__!r}: {ic!r}"
        )


# ---------------------------------------------------------------------------
# Empty snapshot factory
# ---------------------------------------------------------------------------

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
    Note: with an empty period_grid, series length and unavailable-fields checks
    do not apply, so this template validates successfully as-is.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "baseline_id": baseline_id,
        "engine_designation": engine_designation,
        "baseline_commit_sha": baseline_commit_sha,
        "run_path_id": run_path_id,
        "input_source_id": input_source_id,
        "warnings": [],
        "unavailable_sections": ["financial_statements"],
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
