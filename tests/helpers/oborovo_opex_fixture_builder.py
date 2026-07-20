"""TEST-ONLY helper: translate the authoritative Oborovo OPEX fixture into
generic hierarchical OPEX inputs.

PURPOSE
-------
Prove that the generic OpexModelInput / OpexCalculationContext architecture
can represent the authoritative Oborovo workbook structure without any
project-specific calculation logic.

CONSTRAINTS
-----------
* This file MUST NOT be imported by any production/runtime code.
* It reads from tests/fixtures/excel_oborovo_opex_structural_truth.json only.
* No fallback to hardcoded values except where the fixture explicitly records
  a zero (D/F auxiliary rows).

USAGE
-----
>>> from tests.helpers.oborovo_opex_fixture_builder import (
...     build_oborovo_opex_model_input,
...     build_oborovo_calculation_context,
...     OBOROVO_HORIZON_YEARS,
... )
"""
from __future__ import annotations

import json
from pathlib import Path

from finco_core.opex.hierarchical import (
    OpexActivationMode,
    OpexActivationSchedule,
    OpexCalculationContext,
    OpexCategoryCalculationType,
    OpexCategoryInput,
    OpexEscalationConvention,
    OpexModelInput,
    OpexSubitemInput,
)

_FIXTURE_PATH = (
    Path(__file__).parents[1] / "fixtures" / "excel_oborovo_opex_structural_truth.json"
)

OBOROVO_HORIZON_YEARS: int = 30


def _load_fixture() -> dict:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Subitem builder
# ---------------------------------------------------------------------------


def _build_subitem(si_key: str, si: dict) -> OpexSubitemInput:
    """Translate one fixture subitem dict into an OpexSubitemInput."""
    flags_raw: list = si.get("activation_cached_y1_y30") or []
    flags: tuple[bool, ...] = tuple(bool(f or 0) for f in flags_raw)

    # Detect activation mode from fixture fields
    if si.get("activation_formula_y1"):
        # Formula-driven: SENIOR_DEBT_TENOR_ACTIVE (e.g. B.11.3)
        mode = OpexActivationMode.SENIOR_DEBT_TENOR_ACTIVE
        schedule = None
    elif all(bool(f or 0) for f in flags_raw):
        # Every year is active → ALWAYS
        mode = OpexActivationMode.ALWAYS
        schedule = None
    else:
        # Sparse or mixed flags → MANUAL
        mode = OpexActivationMode.MANUAL
        schedule = OpexActivationSchedule(annual_flags=flags)

    return OpexSubitemInput(
        code=si_key,
        name=si.get("name") or "",
        base_amount_keur=float(si["budget"]["cached_value"] or 0),
        activation_mode=mode,
        activation_schedule=schedule,
    )


# ---------------------------------------------------------------------------
# Category builder
# ---------------------------------------------------------------------------


def _build_category(cat_code: str, cat: dict, fixture: dict) -> OpexCategoryInput:
    """Translate one fixture category dict into an OpexCategoryInput."""
    if cat_code == "B.13":
        cont = cat["contingency"]
        return OpexCategoryInput(
            code=cat_code,
            name=cat.get("name") or "Contingencies",
            calculation_type=OpexCategoryCalculationType.PERCENTAGE_OF_SELECTED_BASES,
            percentage_rate=float(cont["contingency_rate"]),
            percentage_base_codes=tuple(cont["contingency_base_codes"]),
        )

    # Determine escalation convention.
    # B.07 uses PRE_OPERATION_BASE (inflation exponent = year, not year-1).
    # No other special-casing by code: the convention is carried in the input.
    if cat_code == "B.07":
        convention = OpexEscalationConvention.PRE_OPERATION_BASE
    else:
        convention = OpexEscalationConvention.YEAR_1_AS_BASE

    inflation = float(cat["inflation"]["cached_value"] or 0)
    subitems_raw: dict = cat.get("subitems") or {}
    subitems = tuple(_build_subitem(key, si) for key, si in subitems_raw.items())

    return OpexCategoryInput(
        code=cat_code,
        name=cat.get("name") or cat_code,
        calculation_type=OpexCategoryCalculationType.SUBITEM_SUM,
        inflation_rate=inflation,
        escalation_convention=convention,
        subitems=subitems,
    )


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------


def build_oborovo_opex_model_input() -> OpexModelInput:
    """Build a generic OpexModelInput from the authoritative Oborovo fixture.

    Category order preserved from fixture insertion order.
    """
    fixture = _load_fixture()
    categories = tuple(
        _build_category(code, cat, fixture)
        for code, cat in fixture["categories"].items()
    )
    return OpexModelInput(categories=categories)


def build_oborovo_calculation_context() -> OpexCalculationContext:
    """Build the OpexCalculationContext from the authoritative Oborovo fixture.

    Reads D (Salary) and F (Taxes) annual series from auxiliary_rows; does NOT
    hardcode them as zero even though they happen to be zero in the current
    base-case scenario.
    """
    fixture = _load_fixture()
    tenor: int = int(fixture["inputs"]["senior_debt_tenor"]["cached_value"])

    aux = fixture.get("auxiliary_rows", {})
    ext_series: list[tuple[str, tuple[float, ...]]] = []
    for code in ("D", "F"):
        if code in aux:
            raw = aux[code].get("annual_cached_y1_y30") or []
            ext_series.append((code, tuple(float(v or 0) for v in raw)))

    return OpexCalculationContext(
        senior_debt_tenor_years=tenor,
        external_annual_series=tuple(ext_series),
    )


def get_fixture_category_annual(cat_code: str, year_idx: int) -> float:
    """Return the Excel-cached annual value for category cat_code at year_idx (0-based)."""
    fixture = _load_fixture()
    vals = fixture["categories"][cat_code]["annual"]["cached_values_y1_y30"]
    return float(vals[year_idx] or 0)


def get_fixture_total_annual(year_idx: int) -> float:
    """Return the Excel-cached total OPEX (incl. contingencies) at year_idx (0-based)."""
    fixture = _load_fixture()
    total = sum(
        float((cat["annual"]["cached_values_y1_y30"][year_idx]) or 0)
        for cat in fixture["categories"].values()
    )
    return total
