"""
finco_parity.normalization — Deterministic normalization for legacy-engine snapshots.

Converts a WaterfallResult (and associated schedule payloads) into a canonical
Python dict suitable for deterministic JSON serialization.

Design contract
---------------
- No mutation of source result objects.
- No current timestamps, random IDs, temporary paths, or absolute repository paths
  in the canonical snapshot content.
- Stable key ordering (explicit, not sort-based) where financial meaning dictates order;
  sort_keys=True is applied at the JSON serialization layer for remaining dict nodes.
- None remains distinct from 0.0 (engine did not compute ≠ computed zero).
- Floats are preserved as-is from the engine.  A future tolerance layer (Phase 1B)
  decides whether two values are financially equivalent.  Rounding at this layer would
  hide real differences.
- Dates serialized as ISO-8601 strings ("YYYY-MM-DD").
- Enums serialized as their .value (string or int).
- Dataclasses serialized field-by-field (no repr, no memory addresses).
- Decimal serialized to str then float to preserve precision without JSON ambiguity.
- Unsupported types raise NormalizationError rather than producing unstable repr() strings.

Import boundary
---------------
This module may only import from:
  - Python standard library
  - finco_parity.*
It must NOT import from app.*, domain.*, finco_core.*, finco_app.*, main_web, main_api.
"""
from __future__ import annotations

import dataclasses
import datetime
import enum
import math
from decimal import Decimal
from typing import Any

from finco_parity.schema import UNAVAILABLE


class NormalizationError(TypeError):
    """Raised when an unsupported type is encountered during normalization."""


def _safe_float(v: Any) -> float | None:
    """Convert a value to float, returning None for None input.

    Preserves NaN as None (NaN in a snapshot is meaningless and non-deterministic).
    Preserves ±inf as None (non-serializable in standard JSON).
    """
    if v is None:
        return UNAVAILABLE
    try:
        f = float(v)
    except (TypeError, ValueError):
        return UNAVAILABLE
    if math.isnan(f) or math.isinf(f):
        return UNAVAILABLE
    return f


def _safe_date(v: Any) -> str | None:
    """Serialize a date or datetime to ISO-8601 string, or None."""
    if v is None:
        return UNAVAILABLE
    if isinstance(v, datetime.datetime):
        return v.date().isoformat()
    if isinstance(v, datetime.date):
        return v.isoformat()
    if isinstance(v, str):
        return v
    return UNAVAILABLE


def normalize_value(v: Any) -> Any:
    """Recursively normalize a value to a JSON-serializable, deterministic form.

    Supported types:
        None, bool, int, float, str, Decimal,
        datetime.date, datetime.datetime,
        enum.Enum, dataclass instances,
        dict, list, tuple.

    Raises NormalizationError for unsupported types (e.g. objects with repr
    containing memory addresses, custom classes without dataclass).
    """
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return _safe_float(v)
    if isinstance(v, Decimal):
        return _safe_float(v)
    if isinstance(v, str):
        return v
    if isinstance(v, (datetime.datetime, datetime.date)):
        return _safe_date(v)
    if isinstance(v, enum.Enum):
        return normalize_value(v.value)
    if dataclasses.is_dataclass(v) and not isinstance(v, type):
        return {
            k: normalize_value(getattr(v, k))
            for k in sorted(f.name for f in dataclasses.fields(v))
        }
    if isinstance(v, dict):
        return {str(k): normalize_value(val) for k, val in v.items()}
    if isinstance(v, (list, tuple)):
        return [normalize_value(item) for item in v]
    # Reject anything else rather than producing unstable output.
    raise NormalizationError(
        f"Cannot normalize value of type {type(v).__name__!r}: {v!r}"
    )


def _attr(obj: Any, *names: str, default: Any = UNAVAILABLE) -> Any:
    """Get the first existing attribute from obj, returning default if none found."""
    for name in names:
        val = getattr(obj, name, _SENTINEL)
        if val is not _SENTINEL:
            return val
    return default


_SENTINEL = object()


def normalize_period_grid(waterfall_result: Any) -> list[dict[str, Any]]:
    """Build the canonical period grid from a WaterfallResult.

    Each row covers one waterfall period (construction or operating).
    Returns periods sorted by period_index ascending.
    """
    periods = getattr(waterfall_result, "periods", []) or []
    rows = []
    for i, p in enumerate(periods):
        row: dict[str, Any] = {
            "period_index": _safe_float(getattr(p, "period", i)) or i,
            "year_index": _safe_float(getattr(p, "year_index", None)),
            "period_in_year": _safe_float(getattr(p, "period_in_year", None)),
            "start_date": _safe_date(getattr(p, "start_date", None)),
            "end_date": _safe_date(getattr(p, "end_date", None)),
            "is_operation": bool(getattr(p, "is_operation", False)),
            "is_construction": bool(getattr(p, "is_construction", False)),
        }
        rows.append(row)
    # Sort by period_index for determinism.
    rows.sort(key=lambda r: r["period_index"])
    return rows


def _extract_period_series(waterfall_result: Any, attr: str) -> list[Any]:
    """Extract a per-period attribute series from WaterfallResult.periods, sorted."""
    periods = getattr(waterfall_result, "periods", []) or []
    if not periods:
        return []
    # Sort by period index for determinism.
    sorted_periods = sorted(periods, key=lambda p: getattr(p, "period", 0))
    return [_safe_float(getattr(p, attr, None)) for p in sorted_periods]


def normalize_operating_schedules(waterfall_result: Any) -> dict[str, Any]:
    """Build the canonical operating schedules section."""
    return {
        "production_mwh": _extract_period_series(waterfall_result, "generation_mwh"),
        "revenue_keur": _extract_period_series(waterfall_result, "revenue_keur"),
        "opex_keur": _extract_period_series(waterfall_result, "opex_keur"),
        "ebitda_keur": _extract_period_series(waterfall_result, "ebitda_keur"),
        "book_depreciation_keur": _extract_period_series(waterfall_result, "depreciation_keur"),
        "tax_depreciation_keur": _extract_period_series(waterfall_result, "tax_depreciation_audit_keur"),
    }


def normalize_tax_and_cfads(waterfall_result: Any) -> dict[str, Any]:
    """Build the canonical tax-and-CFADS section.

    CFADS proxy = cf_after_tax_keur (the period-level cash available after tax,
    before senior debt service).  This is the period attribute closest to a
    standalone CFADS in the current legacy engine.  The report documents the
    ambiguity; the snapshot preserves the current engine value.
    """
    return {
        "taxable_income_keur": _extract_period_series(waterfall_result, "taxable_income_keur"),
        "deductible_interest_keur": _extract_period_series(waterfall_result, "deductible_interest_keur"),
        "disallowed_interest_keur": _extract_period_series(waterfall_result, "disallowed_interest_keur"),
        "cash_tax_keur": _extract_period_series(waterfall_result, "tax_keur"),
        "loss_carryforward_keur": _extract_period_series(waterfall_result, "loss_carryforward_keur"),
        "fiscal_reintegration_keur": _extract_period_series(waterfall_result, "fiscal_reintegration_keur"),
        "cfads_proxy_keur": _extract_period_series(waterfall_result, "cf_after_tax_keur"),
    }


def normalize_financing(waterfall_result: Any) -> dict[str, Any]:
    """Build the canonical financing section (senior debt, SHL, equity)."""
    periods = getattr(waterfall_result, "periods", []) or []
    sorted_periods = sorted(periods, key=lambda p: getattr(p, "period", 0))

    def _series(attr: str) -> list[Any]:
        return [_safe_float(getattr(p, attr, None)) for p in sorted_periods]

    # Opening senior balance = previous period closing + principal (first period: initial draw).
    # The engine stores closing balance on each period; opening is reconstructed here.
    closing_balances = _series("senior_balance_keur")

    return {
        "senior_debt": {
            "closing_keur": closing_balances,
            "interest_keur": _series("senior_interest_keur"),
            "principal_keur": _series("senior_principal_keur"),
            "debt_service_keur": _series("senior_ds_keur"),
            "dscr": _series("dscr"),
            "dsra_keur": _series("dsra_balance_keur"),
            "llcr": UNAVAILABLE,  # LLCR not computed in current legacy engine
        },
        "shl": {
            "opening_keur": _series("shl_opening_keur"),
            "interest_keur": _series("shl_interest_keur"),
            "principal_keur": _series("shl_principal_keur"),
            "closing_keur": _series("shl_balance_keur"),
            "pik_accrual_keur": _series("shl_pik_accrual_keur"),
        },
        "equity": {
            "distributions_keur": _series("distributions_keur"),
            "injections_keur": _series("equity_injection_keur"),
        },
    }


def normalize_returns(waterfall_result: Any) -> dict[str, Any]:
    """Build the canonical aggregate returns section."""
    return {
        "project_irr": _safe_float(getattr(waterfall_result, "project_irr", None)),
        "equity_irr": _safe_float(getattr(waterfall_result, "equity_irr", None)),
        "avg_dscr": _safe_float(getattr(waterfall_result, "avg_dscr", None)),
        "actual_avg_dscr": _safe_float(getattr(waterfall_result, "actual_avg_dscr", None)),
        "min_dscr": _safe_float(getattr(waterfall_result, "min_dscr", None)),
        "actual_min_dscr": _safe_float(getattr(waterfall_result, "actual_min_dscr", None)),
        "total_revenue_keur": _safe_float(getattr(waterfall_result, "total_revenue_keur", None)),
        "total_ebitda_keur": _safe_float(getattr(waterfall_result, "total_ebitda_keur", None)),
        "total_opex_keur": _safe_float(getattr(waterfall_result, "total_opex_keur", None)),
        "total_tax_keur": _safe_float(getattr(waterfall_result, "total_tax_keur", None)),
        "total_senior_ds_keur": _safe_float(getattr(waterfall_result, "total_senior_ds_keur", None)),
        "total_distributions_keur": _safe_float(
            getattr(waterfall_result, "total_distributions_keur", None)
        ),
        "equity_irr_method": str(getattr(waterfall_result, "equity_irr_method", UNAVAILABLE) or ""),
    }


def normalize_financial_statements(fs_payload: Any) -> Any:
    """Normalize a financial statements payload (dict or FinancialStatementsResult).

    Returns UNAVAILABLE if the payload is None or empty.
    """
    if fs_payload is None:
        return UNAVAILABLE
    if isinstance(fs_payload, dict):
        if not fs_payload:
            return UNAVAILABLE
        return normalize_value(fs_payload)
    # Dataclass or object — use normalize_value which handles dataclasses.
    try:
        return normalize_value(fs_payload)
    except NormalizationError:
        return UNAVAILABLE


def normalize_snapshot(
    waterfall_result: Any,
    *,
    baseline_id: str,
    engine_designation: str,
    baseline_commit_sha: str,
    run_path_id: str,
    input_source_id: str,
    warnings: list[str] | None = None,
    unavailable_sections: list[str] | None = None,
    financial_statements_payload: Any = UNAVAILABLE,
) -> dict[str, Any]:
    """Build a fully normalized snapshot dict from a WaterfallResult.

    This is the primary public API of this module.  It is called by
    legacy_snapshot.py after running the engine.

    Parameters
    ----------
    waterfall_result
        The WaterfallResult object returned by the legacy engine.
    baseline_id
        Stable baseline identifier (e.g. "tuho_wind1").
    engine_designation
        String identifying the engine version (e.g. "legacy_waterfall_v3").
    baseline_commit_sha
        Git SHA of the repository at capture time (passed in by the runner,
        not read from the filesystem here to avoid environment dependency).
    run_path_id
        Identifier for the canonical run path used (e.g. "ui_runner.run_demo_project").
    input_source_id
        Identifier for the input source (e.g. "project_factories.create_default_tuho_wind1").
    warnings
        List of warning strings emitted during the run.
    unavailable_sections
        List of section names that could not be captured.
    financial_statements_payload
        FS payload dict/object from assemble_financial_statements(), or UNAVAILABLE.
    """
    snap: dict[str, Any] = {
        "schema_version": "1.0.0",
        "baseline_id": baseline_id,
        "engine_designation": engine_designation,
        "baseline_commit_sha": baseline_commit_sha,
        "run_path_id": run_path_id,
        "input_source_id": input_source_id,
        "warnings": list(warnings or []),
        "unavailable_sections": list(unavailable_sections or []),
        "period_grid": normalize_period_grid(waterfall_result),
        "operating_schedules": normalize_operating_schedules(waterfall_result),
        "tax_and_cfads": normalize_tax_and_cfads(waterfall_result),
        "financing": normalize_financing(waterfall_result),
        "financial_statements": normalize_financial_statements(financial_statements_payload),
        "returns": normalize_returns(waterfall_result),
    }
    return snap
