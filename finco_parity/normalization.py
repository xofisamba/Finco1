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
- None remains distinct from 0.0 (engine did not compute != computed zero).
- Floats are preserved as-is from the engine.  A future tolerance layer (Phase 1B)
  decides whether two values are financially equivalent.  Rounding at this layer would
  hide real differences.
- Dates serialized as ISO-8601 strings ("YYYY-MM-DD").
- Enums serialized as their .value (string or int).
- Dataclasses serialized field-by-field (no repr, no memory addresses).
- Decimal serialized via float().  NOTE: conversion does not preserve arbitrary Decimal
  precision beyond IEEE-754 double (53 bits / ~15-16 significant digits).
- Unsupported types raise NormalizationError rather than producing unstable repr() strings.
- NaN and +-inf inputs raise NormalizationError — they must not reach JSON output.
  The caller serializes with allow_nan=False to enforce this at the boundary.

Field mapping policy
--------------------
Every captured field must correspond to a real, verified attribute on WaterfallPeriod
or WaterfallResult.  If an attribute does not exist, _get_float_series() returns a
list of UNAVAILABLE (None) values and records a warning.  Silent all-None schedules
from typos are caught by real-value tests in test_phase1a_parity_runner.py.

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

from finco_parity.schema import SCHEMA_VERSION, UNAVAILABLE


class NormalizationError(TypeError):
    """Raised when an unsupported or non-serializable type is encountered."""


_ATTR_SENTINEL = object()


def _safe_float(v: Any) -> float:
    """Normalize a numeric value to float.

    Raises NormalizationError for NaN, +-inf, or non-numeric types.
    Does NOT convert to None; callers handle unavailability explicitly.
    """
    if isinstance(v, bool):
        raise NormalizationError(
            f"Expected numeric value, got bool {v!r}."
        )
    try:
        f = float(v)
    except (TypeError, ValueError) as exc:
        raise NormalizationError(
            f"Cannot convert {type(v).__name__!r} to float: {v!r}"
        ) from exc
    if math.isnan(f):
        raise NormalizationError(
            f"NaN encountered in source attribute: {v!r}"
        )
    if math.isinf(f):
        raise NormalizationError(
            f"Infinite value encountered in source attribute: {v!r}"
        )
    return f


def _get_float(obj: Any, attr: str, warnings: list[str]) -> float | None:
    """Get a float attribute from obj.

    Returns UNAVAILABLE (None) if the attribute is absent.
    Returns UNAVAILABLE with a warning for NaN or +-inf engine outputs
    (non-finite values cannot be serialized to standard JSON and have no
    meaningful snapshot value).
    """
    val = getattr(obj, attr, _ATTR_SENTINEL)
    if val is _ATTR_SENTINEL or val is None:
        return UNAVAILABLE
    try:
        return _safe_float(val)
    except NormalizationError:
        warnings.append(
            f"Non-finite value in {attr!r} ({val!r}) converted to unavailable."
        )
        return UNAVAILABLE


def _get_float_series(periods: list[Any], attr: str, warnings: list[str]) -> list[Any]:
    """Extract a per-period float series for a named attribute.

    If the attribute is absent on the first period, returns a list of UNAVAILABLE
    values and appends a warning.  This makes typos in field names detectable via
    real-value tests rather than silently passing.

    NaN or +-inf values from the engine are converted to UNAVAILABLE per period
    (with a warning on first occurrence) since they cannot be JSON-serialized and
    have no meaningful snapshot representation.
    """
    if not periods:
        return []
    if getattr(periods[0], attr, _ATTR_SENTINEL) is _ATTR_SENTINEL:
        warnings.append(
            f"Attribute {attr!r} not found on WaterfallPeriod — series unavailable."
        )
        return [UNAVAILABLE] * len(periods)
    result = []
    nonfinite_warned = False
    for p in periods:
        val = getattr(p, attr, None)
        if val is None:
            result.append(UNAVAILABLE)
        else:
            try:
                result.append(_safe_float(val))
            except NormalizationError:
                if not nonfinite_warned:
                    warnings.append(
                        f"Non-finite value(s) in period series {attr!r} converted to unavailable."
                    )
                    nonfinite_warned = True
                result.append(UNAVAILABLE)
    return result


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

    Raises NormalizationError for NaN/+-inf floats or unsupported types.
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
        return _safe_float(float(v))
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
    raise NormalizationError(
        f"Cannot normalize value of type {type(v).__name__!r}: {v!r}"
    )


def normalize_period_grid(waterfall_result: Any, warnings: list[str]) -> list[dict[str, Any]]:
    """Build the canonical period grid from a WaterfallResult.

    IMPORTANT: WaterfallResult.periods contains operation-only periods.
    The legacy engine (run_waterfall_v3_core) passes only operation periods
    into run_waterfall().  There is no native construction-period axis in the
    WaterfallResult.

    WaterfallPeriod native fields captured:
      period (int)    — period index
      date            — period-end date (only date stored; no start_date)
      year_index (int)
      period_in_year (int)
      is_operation (bool)

    Fields explicitly unavailable (not present on WaterfallPeriod):
      start_date      — only period-end date is stored
      end_date        — alias for date; captured there
      is_construction — not a WaterfallPeriod attribute

    Returns periods sorted by period_index ascending.
    """
    periods = getattr(waterfall_result, "periods", []) or []
    rows = []
    for i, p in enumerate(periods):
        period_idx = getattr(p, "period", i)
        row: dict[str, Any] = {
            "period_index": period_idx,
            "date": _safe_date(getattr(p, "date", None)),
            "year_index": _get_float(p, "year_index", warnings),
            "period_in_year": _get_float(p, "period_in_year", warnings),
            "is_operation": bool(getattr(p, "is_operation", True)),
            # Explicitly unavailable (not WaterfallPeriod attributes):
            "start_date": UNAVAILABLE,
            "is_construction": UNAVAILABLE,
        }
        rows.append(row)
    rows.sort(key=lambda r: r["period_index"])
    return rows


def normalize_operating_schedules(waterfall_result: Any, warnings: list[str]) -> dict[str, Any]:
    """Build the canonical operating schedules section."""
    periods = sorted(
        getattr(waterfall_result, "periods", []) or [],
        key=lambda p: getattr(p, "period", 0),
    )
    return {
        "production_mwh": _get_float_series(periods, "generation_mwh", warnings),
        "revenue_keur": _get_float_series(periods, "revenue_keur", warnings),
        "opex_keur": _get_float_series(periods, "opex_keur", warnings),
        "ebitda_keur": _get_float_series(periods, "ebitda_keur", warnings),
        "book_depreciation_keur": _get_float_series(periods, "depreciation_keur", warnings),
        "tax_depreciation_keur": _get_float_series(periods, "tax_depreciation_audit_keur", warnings),
    }


def normalize_tax_and_cfads(waterfall_result: Any, warnings: list[str]) -> dict[str, Any]:
    """Build the canonical tax-and-CFADS section.

    Tax field classification (verified against WaterfallPeriod definition):
    - taxable_profit_keur: taxable income before loss carryforward
    - taxable_income_before_losses_audit_keur: audit alias for pre-LCF taxable income
    - taxable_profit_after_losses_audit_keur: taxable income after loss carryforward
    - cit_accrual_audit_keur: CIT accrual (P&L expense)
    - cash_tax_current_period_audit_keur: current-period cash CIT payment
    - corporate_tax_cash_keur: primary cash tax field
    - tax_keur: legacy field (ambiguous; DO NOT classify as authoritative cash tax)
    - tax_loss_opening/used/closing_audit_keur: loss carryforward movement
    - fiscal_reintegration_audit_keur: fiscal reintegration adjustment
    - cash_tax_bridge_reconciliation_keur: diagnostic bridge (not primary)

    CFADS variants — all captured; canonical selection deferred to Phase 1B:
    - cf_after_tax_keur: CF after tax, before senior DS (primary proxy)
    - r69_fcf_banks_keur: FCF to banks (pre-DS, post-tax)
    - r84_fcf_junior_keur: FCF after senior DS
    - r99_fcf_for_distribution_keur: FCF for distribution (post-DA)
    - r102_fcf_for_shl_keur: FCF for SHL service
    - fcf_for_shl_keur: SHL FCF (waterfall approach)
    """
    periods = sorted(
        getattr(waterfall_result, "periods", []) or [],
        key=lambda p: getattr(p, "period", 0),
    )
    return {
        "taxable_profit_keur": _get_float_series(periods, "taxable_profit_keur", warnings),
        "taxable_income_before_losses_audit_keur": _get_float_series(
            periods, "taxable_income_before_losses_audit_keur", warnings
        ),
        "taxable_profit_after_losses_audit_keur": _get_float_series(
            periods, "taxable_profit_after_losses_audit_keur", warnings
        ),
        "cit_accrual_audit_keur": _get_float_series(periods, "cit_accrual_audit_keur", warnings),
        "cash_tax_current_period_audit_keur": _get_float_series(
            periods, "cash_tax_current_period_audit_keur", warnings
        ),
        "corporate_tax_cash_keur": _get_float_series(periods, "corporate_tax_cash_keur", warnings),
        "tax_keur": _get_float_series(periods, "tax_keur", warnings),
        "cash_tax_bridge_reconciliation_keur": _get_float_series(
            periods, "cash_tax_bridge_reconciliation_keur", warnings
        ),
        "tax_loss_opening_audit_keur": _get_float_series(
            periods, "tax_loss_opening_audit_keur", warnings
        ),
        "tax_loss_used_audit_keur": _get_float_series(periods, "tax_loss_used_audit_keur", warnings),
        "tax_loss_closing_audit_keur": _get_float_series(
            periods, "tax_loss_closing_audit_keur", warnings
        ),
        "tax_depreciation_audit_keur": _get_float_series(
            periods, "tax_depreciation_audit_keur", warnings
        ),
        "fiscal_reintegration_audit_keur": _get_float_series(
            periods, "fiscal_reintegration_audit_keur", warnings
        ),
        # CFADS variants — canonical owner unresolved until Phase 1B
        "cf_after_tax_keur": _get_float_series(periods, "cf_after_tax_keur", warnings),
        "r69_fcf_banks_keur": _get_float_series(periods, "r69_fcf_banks_keur", warnings),
        "r84_fcf_junior_keur": _get_float_series(periods, "r84_fcf_junior_keur", warnings),
        "r99_fcf_for_distribution_keur": _get_float_series(
            periods, "r99_fcf_for_distribution_keur", warnings
        ),
        "r102_fcf_for_shl_keur": _get_float_series(periods, "r102_fcf_for_shl_keur", warnings),
        "fcf_for_shl_keur": _get_float_series(periods, "fcf_for_shl_keur", warnings),
    }


def normalize_financing(waterfall_result: Any, warnings: list[str]) -> dict[str, Any]:
    """Build the canonical financing section (senior debt, SHL, equity).

    Field policy (verified against WaterfallPeriod definition):
    - llcr, plcr: real WaterfallPeriod attributes — captured.
    - opening senior balance and drawdown: NOT native attributes — unavailable.
    - shl_opening_keur: NOT a native attribute — unavailable.
    - equity_injection_keur: NOT a native attribute — unavailable.
    - distribution_keur: correct singular attribute (NOT distributions_keur).
    """
    periods = sorted(
        getattr(waterfall_result, "periods", []) or [],
        key=lambda p: getattr(p, "period", 0),
    )
    n = len(periods)

    return {
        "senior_debt": {
            # opening_keur and drawdown_keur are not native WaterfallPeriod fields
            "opening_keur": [UNAVAILABLE] * n,
            "drawdown_keur": [UNAVAILABLE] * n,
            "closing_keur": _get_float_series(periods, "senior_balance_keur", warnings),
            "interest_keur": _get_float_series(periods, "senior_interest_keur", warnings),
            "principal_keur": _get_float_series(periods, "senior_principal_keur", warnings),
            "debt_service_keur": _get_float_series(periods, "senior_ds_keur", warnings),
            "dscr": _get_float_series(periods, "dscr", warnings),
            "llcr": _get_float_series(periods, "llcr", warnings),
            "plcr": _get_float_series(periods, "plcr", warnings),
            "dsra_balance_keur": _get_float_series(periods, "dsra_balance_keur", warnings),
            "dsra_contribution_keur": _get_float_series(periods, "dsra_contribution_keur", warnings),
            "cash_sweep_keur": _get_float_series(periods, "cash_sweep_keur", warnings),
        },
        "shl": {
            # shl_opening_keur is not a native WaterfallPeriod attribute
            "opening_keur": [UNAVAILABLE] * n,
            "interest_keur": _get_float_series(periods, "shl_interest_keur", warnings),
            "principal_keur": _get_float_series(periods, "shl_principal_keur", warnings),
            "service_keur": _get_float_series(periods, "shl_service_keur", warnings),
            "closing_keur": _get_float_series(periods, "shl_balance_keur", warnings),
            "pik_keur": _get_float_series(periods, "shl_pik_keur", warnings),
            "gross_accrued_interest_keur": _get_float_series(
                periods, "shl_gross_accrued_interest_keur", warnings
            ),
        },
        "equity": {
            # distribution_keur is the correct singular attribute
            "distribution_keur": _get_float_series(periods, "distribution_keur", warnings),
            # equity injection is not a native WaterfallPeriod attribute
            "injections_keur": [UNAVAILABLE] * n,
            "cf_after_reserves_keur": _get_float_series(
                periods, "cf_after_reserves_keur", warnings
            ),
            "lockup_active": [bool(getattr(p, "lockup_active", False)) for p in periods],
        },
    }


def normalize_returns(waterfall_result: Any, warnings: list[str]) -> dict[str, Any]:
    """Build the canonical aggregate returns section.

    All attributes verified against current WaterfallResult definition.
    Correct: total_distribution_keur (singular, not total_distributions_keur).
    """
    def _s(attr: str) -> float | None:
        return _get_float(waterfall_result, attr, warnings)

    return {
        "project_irr": _s("project_irr"),
        "equity_irr": _s("equity_irr"),
        "sponsor_irr": _s("sponsor_irr"),
        "project_npv": _s("project_npv"),
        "equity_npv": _s("equity_npv"),
        "avg_dscr": _s("avg_dscr"),
        "min_dscr": _s("min_dscr"),
        "actual_avg_dscr": _s("actual_avg_dscr"),
        "actual_min_dscr": _s("actual_min_dscr"),
        "min_llcr": _s("min_llcr"),
        "min_plcr": _s("min_plcr"),
        "periods_in_lockup": getattr(waterfall_result, "periods_in_lockup", UNAVAILABLE),
        "total_revenue_keur": _s("total_revenue_keur"),
        "total_opex_keur": _s("total_opex_keur"),
        "total_ebitda_keur": _s("total_ebitda_keur"),
        "total_tax_keur": _s("total_tax_keur"),
        "total_senior_ds_keur": _s("total_senior_ds_keur"),
        "total_shl_service_keur": _s("total_shl_service_keur"),
        # Correct attribute: total_distribution_keur (singular)
        "total_distribution_keur": _s("total_distribution_keur"),
        "equity_irr_method": str(getattr(waterfall_result, "equity_irr_method", "") or ""),
    }


def normalize_financial_statements(fs_payload: Any, warnings: list[str]) -> Any:
    """Normalize a financial statements payload (dict or dataclass).

    Returns UNAVAILABLE if the payload is None or empty.
    Warnings record failure type without absolute paths or memory addresses.
    """
    if fs_payload is None:
        return UNAVAILABLE
    if isinstance(fs_payload, dict):
        if not fs_payload:
            return UNAVAILABLE
        try:
            return normalize_value(fs_payload)
        except NormalizationError as exc:
            warnings.append(f"financial_statements normalization failed: {type(exc).__name__}")
            return UNAVAILABLE
    try:
        return normalize_value(fs_payload)
    except NormalizationError as exc:
        warnings.append(f"financial_statements normalization failed: {type(exc).__name__}")
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
    unavailable_fields: dict[str, list[str]] | None = None,
    financial_statements_payload: Any = UNAVAILABLE,
) -> dict[str, Any]:
    """Build a fully normalized snapshot dict from a WaterfallResult.

    This is the primary public API of this module.  Called by legacy_snapshot.py.

    Parameters
    ----------
    waterfall_result
        The WaterfallResult object returned by the legacy engine.
    baseline_id
        Stable baseline identifier (e.g. "tuho").
    engine_designation
        String identifying the engine version.
    baseline_commit_sha
        Git SHA of the repository at capture time (passed in by the runner).
    run_path_id
        Identifier for the canonical run path.
    input_source_id
        Identifier for the input source.
    warnings
        Initial list of warning strings; will be extended during normalization.
    unavailable_sections
        Section names that could not be captured at all.
    unavailable_fields
        Per-section mapping of field names that are explicitly unavailable.
    financial_statements_payload
        FS payload dict/object, or UNAVAILABLE.
    """
    collected_warnings: list[str] = list(warnings or [])

    snap: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "baseline_id": baseline_id,
        "engine_designation": engine_designation,
        "baseline_commit_sha": baseline_commit_sha,
        "run_path_id": run_path_id,
        "input_source_id": input_source_id,
        "warnings": collected_warnings,
        "unavailable_sections": list(unavailable_sections or []),
        "unavailable_fields": dict(unavailable_fields or {}),
        "period_grid": normalize_period_grid(waterfall_result, collected_warnings),
        "operating_schedules": normalize_operating_schedules(waterfall_result, collected_warnings),
        "tax_and_cfads": normalize_tax_and_cfads(waterfall_result, collected_warnings),
        "financing": normalize_financing(waterfall_result, collected_warnings),
        "financial_statements": normalize_financial_statements(
            financial_statements_payload, collected_warnings
        ),
        "returns": normalize_returns(waterfall_result, collected_warnings),
    }
    return snap
