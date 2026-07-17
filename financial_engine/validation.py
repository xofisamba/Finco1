"""
financial_engine.validation — Deterministic input validation for Phase 2A.

validate_operating_model_input() returns a tuple of ValidationIssue objects.
It does NOT mutate inputs, raise exceptions for expected invalid inputs,
auto-correct values, or silently clamp values.

run_operating_model() refuses to execute when ERROR issues exist.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from financial_engine.inputs import OperatingModelInput


class ValidationSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: str
    severity: ValidationSeverity
    message: str


def _is_finite(v: float | None) -> bool:
    return v is not None and math.isfinite(v)


def _err(code: str, path: str, msg: str) -> ValidationIssue:
    return ValidationIssue(code=code, path=path, severity=ValidationSeverity.ERROR, message=msg)


def _warn(code: str, path: str, msg: str) -> ValidationIssue:
    return ValidationIssue(code=code, path=path, severity=ValidationSeverity.WARNING, message=msg)


def validate_operating_model_input(
    inputs: "OperatingModelInput",
) -> tuple[ValidationIssue, ...]:
    """Validate a Phase 2A OperatingModelInput.

    Returns a deterministically ordered tuple of ValidationIssue objects.
    """
    issues: list[ValidationIssue] = []

    cal = inputs.calendar
    tech = inputs.technical
    rev = inputs.revenue
    opex = inputs.opex
    dep = inputs.depreciation

    # Calendar
    if cal.financial_close is None:
        issues.append(_err("CAL001", "calendar.financial_close", "financial_close is required"))

    if cal.construction_months < 0:
        issues.append(_err("CAL002", "calendar.construction_months",
                           f"construction_months must be non-negative, got {cal.construction_months}"))

    if cal.horizon_years <= 0:
        issues.append(_err("CAL003", "calendar.horizon_years",
                           f"horizon_years must be positive, got {cal.horizon_years}"))

    if cal.ppa_years < 0:
        issues.append(_err("CAL004", "calendar.ppa_years",
                           f"ppa_years must be non-negative, got {cal.ppa_years}"))

    if cal.ppa_years > cal.horizon_years:
        issues.append(_warn("CAL005", "calendar.ppa_years",
                            f"ppa_years ({cal.ppa_years}) exceeds horizon_years ({cal.horizon_years})"))

    # Technical
    if not _is_finite(tech.capacity_mw) or tech.capacity_mw < 0:
        issues.append(_err("TECH001", "technical.capacity_mw",
                           f"capacity_mw must be finite and non-negative, got {tech.capacity_mw}"))

    if not _is_finite(tech.operating_hours_p50) or tech.operating_hours_p50 < 0:
        issues.append(_err("TECH002", "technical.operating_hours_p50",
                           f"operating_hours_p50 must be finite and non-negative"))

    if not _is_finite(tech.operating_hours_p90_10y) or tech.operating_hours_p90_10y < 0:
        issues.append(_err("TECH003", "technical.operating_hours_p90_10y",
                           f"operating_hours_p90_10y must be finite and non-negative"))

    if tech.yield_scenario.value in ("P90-10y",) and tech.operating_hours_p90_10y <= 0:
        issues.append(_err("TECH004", "technical.operating_hours_p90_10y",
                           "P90-10y scenario requires operating_hours_p90_10y > 0"))

    if not _is_finite(tech.pv_degradation):
        issues.append(_err("TECH005", "technical.pv_degradation",
                           "pv_degradation must be finite"))

    if not _is_finite(tech.plant_availability) or not (0.0 <= tech.plant_availability <= 1.0):
        issues.append(_err("TECH006", "technical.plant_availability",
                           f"plant_availability must be finite and in [0, 1], got {tech.plant_availability}"))

    if not _is_finite(tech.grid_availability) or not (0.0 <= tech.grid_availability <= 1.0):
        issues.append(_err("TECH007", "technical.grid_availability",
                           f"grid_availability must be finite and in [0, 1], got {tech.grid_availability}"))

    # Revenue
    if not _is_finite(rev.ppa_base_tariff_eur_mwh):
        issues.append(_err("REV001", "revenue.ppa_base_tariff_eur_mwh",
                           "ppa_base_tariff_eur_mwh must be finite"))

    if not _is_finite(rev.ppa_index):
        issues.append(_err("REV002", "revenue.ppa_index", "ppa_index must be finite"))

    if not (0.0 <= rev.ppa_production_share <= 1.0):
        issues.append(_err("REV003", "revenue.ppa_production_share",
                           f"ppa_production_share must be in [0, 1], got {rev.ppa_production_share}"))

    for i, p in enumerate(rev.market_prices_curve_eur_mwh):
        if not _is_finite(p):
            issues.append(_err("REV004", f"revenue.market_prices_curve_eur_mwh[{i}]",
                               f"market price at index {i} is not finite: {p}"))

    if rev.co2_enabled and not _is_finite(rev.co2_price_eur_mwh):
        issues.append(_err("REV005", "revenue.co2_price_eur_mwh",
                           "co2_price_eur_mwh must be finite when co2_enabled"))

    # OPEX
    for i, item in enumerate(opex.items):
        if not _is_finite(item.y1_amount_keur):
            issues.append(_err("OPEX001", f"opex.items[{i}].y1_amount_keur",
                               f"y1_amount_keur for item {item.name!r} is not finite"))
        if not _is_finite(item.annual_inflation):
            issues.append(_err("OPEX002", f"opex.items[{i}].annual_inflation",
                               f"annual_inflation for item {item.name!r} is not finite"))

    # Depreciation
    if dep.period_count <= 0:
        issues.append(_err("DEP001", "depreciation.period_count",
                           f"period_count must be positive, got {dep.period_count}"))

    if dep.cod_period < 0:
        issues.append(_err("DEP002", "depreciation.cod_period",
                           f"cod_period must be non-negative, got {dep.cod_period}"))

    for i, asset in enumerate(dep.assets):
        if not _is_finite(asset.gross_asset_basis_keur) or asset.gross_asset_basis_keur < 0:
            issues.append(_err("DEP003", f"depreciation.assets[{i}].gross_asset_basis_keur",
                               f"gross_asset_basis_keur for {asset.asset_class!r} must be finite and non-negative"))
        if asset.book_useful_life_years <= 0:
            issues.append(_err("DEP004", f"depreciation.assets[{i}].book_useful_life_years",
                               f"book_useful_life_years for {asset.asset_class!r} must be positive"))
        if asset.tax_useful_life_years <= 0:
            issues.append(_err("DEP005", f"depreciation.assets[{i}].tax_useful_life_years",
                               f"tax_useful_life_years for {asset.asset_class!r} must be positive"))

    return tuple(issues)


def has_errors(issues: tuple[ValidationIssue, ...]) -> bool:
    """Return True if any issue has ERROR severity."""
    return any(i.severity == ValidationSeverity.ERROR for i in issues)
