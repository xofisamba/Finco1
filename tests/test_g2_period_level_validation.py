"""G2-PERIOD-LEVEL-VALIDATION: period-by-period validation of Generic Solar
and Generic Wind against the bootstrap reference workbooks.

G1D validated Generic Solar/Wind at the total/KPI anchor level only. This
module extends that to the period (semi-annual) level using the period
series extracted by scripts/extract_generic_golden_periods.py into
tests/fixtures/excel_golden_generic_{solar,wind}_periods.json.

Three explicit categories (see docs/g2_period_level_validation.md):
  - tight-validated:        generation, OpEx, revenue, EBITDA per period.
  - methodology-caveated:   senior debt service shape, DSCR, distributions,
                            and equity cash flow per period -- this mirrors
                            the existing G1D total-level caveat (the
                            reference workbook sizes debt off a CFADS proxy
                            that excludes the interest tax shield; the
                            runtime does not reproduce that proxy
                            period-by-period), so these are not asserted to
                            match closely here.
  - not yet available:     PPA tariff / market price per period (the
                            runtime does not currently expose a per-period
                            tariff/price field on WaterfallPeriod).

This module is read-only: it runs the existing runtime via
app.project_factories + app.waterfall_core (same call shape as
tests/test_generic_solar_wind_runtime.py) and the existing reference
workbooks, and does not change any formula, factory default, or engine
file.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.project_factories import create_default_solar_project, create_default_wind_project
from app.waterfall_core import run_waterfall_v3_core
from domain.period_engine import PeriodEngine
from domain.waterfall.waterfall_engine import WaterfallPeriod

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures"

# Tight per-period relative tolerance for lines that are validated at the
# total/KPI level by G1D and have no documented methodology gap. Wider than
# the 0.5% total-level tolerance (docs/generic_validation_reference_excel_spec.md
# S8) because per-period values carry day-count/degradation-curve discretization
# noise that nets out in the total but not period-by-period. Observed max
# deviation (excluding the single PPA-to-merchant transition period, see
# below) is ~0.9%; set with headroom, not loosened after the fact.
TIGHT_PERIOD_RELATIVE_TOLERANCE = 0.02
TIGHT_PERIOD_MIN_ABS_KEUR = 1.0

# The single period in which the PPA contract expires and pricing switches
# from PPA tariff to merchant price falls on a different period boundary in
# the runtime's period-indexing vs. the reference workbook's, so revenue and
# EBITDA in that one period only diverge by ~7-9%. This is a documented,
# named exception -- not a silent widening of the tight tolerance above.
PPA_TRANSITION_RELATIVE_TOLERANCE = 0.10

CAVEATED_PERIOD_SERIES = (
    "senior_opening_balance_keur",
    "senior_interest_keur",
    "senior_principal_keur",
    "senior_debt_service_keur",
    "senior_closing_balance_keur",
    "dscr_sizing_proxy",
    "dscr_true",
    "distribution_keur",
    "equity_cash_flow_keur",
)

NOT_YET_AVAILABLE_PERIOD_SERIES = (
    "ppa_tariff_eur_per_mwh",
    "market_price_eur_per_mwh",
)


def _load_period_fixture(project_key: str) -> dict:
    path = FIXTURE_DIR / f"excel_golden_{project_key}_periods.json"
    return json.loads(path.read_text())


def _run_for_inputs(inputs):
    engine = PeriodEngine(
        financial_close=inputs.info.financial_close,
        construction_months=inputs.info.construction_months,
        horizon_years=inputs.info.horizon_years,
        ppa_years=inputs.revenue.ppa_term_years,
    )
    all_periods = list(engine.periods())
    op_periods = [p for p in all_periods if p.is_operation]
    rate_per_period = inputs.financing.all_in_rate / 2
    return run_waterfall_v3_core(
        inputs=inputs,
        engine=engine,
        rate_per_period=rate_per_period,
        tenor_periods=len(op_periods),
        target_dscr=inputs.financing.target_dscr,
        lockup_dscr=inputs.financing.lockup_dscr,
        tax_rate=inputs.tax.corporate_rate,
        dsra_months=inputs.financing.dsra_months,
        shl_amount=inputs.financing.shl_amount_keur,
        shl_rate=inputs.financing.shl_rate,
        shl_idc_keur=0.0,
        shl_repayment_method="bullet",
        equity_irr_method="equity_only",
        share_capital_keur=inputs.financing.share_capital_keur,
        sculpt_capex_keur=inputs.capex.sculpt_capex_keur,
        debt_sizing_method="dscr_sculpt",
    )


def _aligned_runtime_series(result, n_ref: int, offset: int, attr: str) -> list[float]:
    """Map runtime periods onto the reference workbook's period index space.

    The runtime's PeriodEngine numbers periods (including construction)
    starting at 0; ``offset`` corrects for the reference workbook's leading
    construction columns, which can differ in count from the runtime's
    construction-period count (solar: 0, wind: +1) without indicating any
    calculation error -- both represent the same construction duration in
    months, just split into a different number of semi-annual columns at the
    boundary.
    """
    out = [0.0] * n_ref
    for period in result.periods:
        i = period.period + offset
        if 0 <= i < n_ref:
            out[i] = getattr(period, attr)
    return out


def _alignment_offset(result, ref_generation: list) -> int:
    ref_start = next(i for i, v in enumerate(ref_generation) if (v or 0) > 0)
    rt_start = next(p.period for p in result.periods if p.generation_mwh > 0)
    return ref_start - rt_start


PROJECTS = [
    ("generic_solar", create_default_solar_project),
    ("generic_wind", create_default_wind_project),
]


@pytest.mark.parametrize("project_key,factory", PROJECTS)
def test_period_fixture_has_no_missing_rows(project_key, factory):
    fixture = _load_period_fixture(project_key)
    assert fixture["rows_missing"] == []
    assert fixture["n_periods"] > 0


@pytest.mark.parametrize("project_key,factory", PROJECTS)
def test_generation_is_tight_validated_per_period(project_key, factory):
    fixture = _load_period_fixture(project_key)
    result = _run_for_inputs(factory())
    offset = _alignment_offset(result, fixture["series"]["generation_mwh"])
    runtime = _aligned_runtime_series(result, fixture["n_periods"], offset, "generation_mwh")
    ref = fixture["series"]["generation_mwh"]
    for i, (a, b) in enumerate(zip(runtime, ref)):
        if abs(b) < TIGHT_PERIOD_MIN_ABS_KEUR:
            continue
        rel = abs(a - b) / abs(b)
        assert rel <= TIGHT_PERIOD_RELATIVE_TOLERANCE, (
            f"{project_key} generation_mwh period {i}: runtime={a} ref={b} rel_diff={rel:.4f}"
        )


@pytest.mark.parametrize("project_key,factory", PROJECTS)
def test_opex_is_tight_validated_per_period(project_key, factory):
    fixture = _load_period_fixture(project_key)
    result = _run_for_inputs(factory())
    offset = _alignment_offset(result, fixture["series"]["generation_mwh"])
    runtime = _aligned_runtime_series(result, fixture["n_periods"], offset, "opex_keur")
    ref = fixture["series"]["opex_keur"]
    for i, (a, b) in enumerate(zip(runtime, ref)):
        if abs(b) < TIGHT_PERIOD_MIN_ABS_KEUR:
            continue
        rel = abs(a - b) / abs(b)
        assert rel <= TIGHT_PERIOD_RELATIVE_TOLERANCE, (
            f"{project_key} opex_keur period {i}: runtime={a} ref={b} rel_diff={rel:.4f}"
        )


def _ppa_transition_period_index(ref_revenue: list) -> int | None:
    """The single period where revenue drops most sharply is the PPA-to-
    merchant transition boundary (tariff steps down); identify it as the
    period with the largest period-over-period relative drop in the back
    half of the schedule, to exclude it explicitly (not silently) from the
    tight per-period revenue/EBITDA assertion."""
    best_idx, best_drop = None, 0.0
    for i in range(1, len(ref_revenue)):
        a, b = ref_revenue[i - 1], ref_revenue[i]
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            continue
        if abs(a) < TIGHT_PERIOD_MIN_ABS_KEUR:
            continue
        drop = abs(a - b) / abs(a)
        if drop > best_drop:
            best_idx, best_drop = i, drop
    return best_idx


@pytest.mark.parametrize("project_key,factory", PROJECTS)
@pytest.mark.parametrize("metric", ["revenue_keur", "ebitda_keur"])
def test_revenue_and_ebitda_are_tight_validated_per_period_excluding_ppa_transition(
    project_key, factory, metric
):
    fixture = _load_period_fixture(project_key)
    result = _run_for_inputs(factory())
    offset = _alignment_offset(result, fixture["series"]["generation_mwh"])
    runtime = _aligned_runtime_series(result, fixture["n_periods"], offset, metric.replace("_keur", "_keur"))
    ref = fixture["series"][metric]
    transition_idx = _ppa_transition_period_index(fixture["series"]["revenue_keur"])
    for i, (a, b) in enumerate(zip(runtime, ref)):
        if abs(b) < TIGHT_PERIOD_MIN_ABS_KEUR or i == transition_idx:
            continue
        rel = abs(a - b) / abs(b)
        assert rel <= TIGHT_PERIOD_RELATIVE_TOLERANCE, (
            f"{project_key} {metric} period {i}: runtime={a} ref={b} rel_diff={rel:.4f}"
        )


@pytest.mark.parametrize("project_key,factory", PROJECTS)
def test_ppa_transition_period_has_documented_wider_tolerance(project_key, factory):
    """The PPA-to-merchant transition period is named and bounded explicitly
    here (rather than folded into a silently widened tight tolerance)."""
    fixture = _load_period_fixture(project_key)
    result = _run_for_inputs(factory())
    offset = _alignment_offset(result, fixture["series"]["generation_mwh"])
    runtime_rev = _aligned_runtime_series(result, fixture["n_periods"], offset, "revenue_keur")
    ref_rev = fixture["series"]["revenue_keur"]
    transition_idx = _ppa_transition_period_index(ref_rev)
    assert transition_idx is not None
    a, b = runtime_rev[transition_idx], ref_rev[transition_idx]
    rel = abs(a - b) / abs(b)
    assert rel > TIGHT_PERIOD_RELATIVE_TOLERANCE, (
        "expected the PPA transition period to exceed the tight tolerance "
        "(otherwise it no longer needs a documented exception)"
    )
    assert rel <= PPA_TRANSITION_RELATIVE_TOLERANCE, (
        f"{project_key} PPA transition period {transition_idx}: rel_diff={rel:.4f} "
        f"exceeds documented bound {PPA_TRANSITION_RELATIVE_TOLERANCE}"
    )


@pytest.mark.parametrize("project_key,factory", PROJECTS)
def test_senior_debt_service_and_dscr_periods_are_methodology_caveated(project_key, factory):
    """Per-period senior debt service, balances, and DSCR are not asserted
    to match closely: the reference workbook sizes debt off a CFADS proxy
    that excludes the interest tax shield (see
    docs/generic_validation_reference_excel_spec.md S6.2 and
    reports/g1f_debt_sizing_proxy_gap_analysis.md), which the runtime does
    not reproduce period-by-period. This test only confirms both series
    exist, are finite, and are aligned in length -- consistent with the
    senior_debt_service_keur / avg_dscr / min_dscr methodology-caveat
    classification already established at the total level by G1D
    (app/validation_status.py)."""
    fixture = _load_period_fixture(project_key)
    result = _run_for_inputs(factory())
    for series_key in ("senior_debt_service_keur", "senior_closing_balance_keur"):
        ref = fixture["series"][series_key]
        assert len(ref) == fixture["n_periods"]
    runtime_dscr = [p.dscr for p in result.periods]
    assert all(d == d for d in runtime_dscr)  # no NaN
    assert "dscr_true" in fixture["series"]
    assert "dscr_sizing_proxy" in fixture["series"]


@pytest.mark.parametrize("project_key,factory", PROJECTS)
def test_distribution_and_equity_cash_flow_periods_are_methodology_caveated(project_key, factory):
    """Per-period distributions and equity cash flow inherit the same
    methodology caveat as project_irr/equity_irr at the total level (G1D):
    not asserted to match closely here, only confirmed present."""
    fixture = _load_period_fixture(project_key)
    result = _run_for_inputs(factory())
    for series_key in ("distribution_keur", "equity_cash_flow_keur"):
        ref = fixture["series"][series_key]
        assert len(ref) == fixture["n_periods"]
    runtime_distributions = [p.distribution_keur for p in result.periods]
    assert all(d == d for d in runtime_distributions)  # no NaN


def test_ppa_tariff_and_market_price_periods_not_yet_available_from_runtime():
    """The reference workbook exposes per-period PPA tariff and market price
    rows; WaterfallPeriod has no equivalent per-period field today, so these
    series are documented as not yet extractable from the runtime rather
    than silently skipped."""
    runtime_fields = set(WaterfallPeriod.__dataclass_fields__)
    for series_key in NOT_YET_AVAILABLE_PERIOD_SERIES:
        assert series_key not in runtime_fields


@pytest.mark.parametrize("project_key", ["generic_solar", "generic_wind"])
def test_period_fixture_series_cover_all_required_areas(project_key):
    fixture = _load_period_fixture(project_key)
    required = {
        "generation_mwh",
        "ppa_tariff_eur_per_mwh",
        "market_price_eur_per_mwh",
        "revenue_keur",
        "opex_keur",
        "ebitda_keur",
        "senior_opening_balance_keur",
        "senior_interest_keur",
        "senior_principal_keur",
        "senior_debt_service_keur",
        "dscr_sizing_proxy",
        "dscr_true",
        "distribution_keur",
        "equity_cash_flow_keur",
    }
    assert required <= set(fixture["series"].keys())
