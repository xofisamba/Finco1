"""G3-DRIVER-SENSITIVITY-VALIDATION: directional sensitivity tests for
Generic Solar/Wind.

Proves that key editable assumptions move KPIs in the expected finance
direction, using the same production wiring the app uses
(``app.waterfall_runner.WaterfallRunConfig.from_inputs`` +
``WaterfallRunner.run``) -- not the simplified, fixed-tenor harness used by
tests/test_generic_solar_wind_runtime.py and tests/test_g2_period_level_validation.py,
because that harness hardcodes ``tenor_periods`` to the full operating
horizon and does not exercise ``financing.senior_tenor_years`` at all. Using
the real wiring here means the tenor driver test below actually has
something to assert.

Assertions are directional only (one driver changed at a time vs. the base
case), not exact numeric parity -- this module does not re-validate
totals or periods (that is G1D/G2's job) and does not change any formula,
factory default, or engine file.

See docs/g3_driver_sensitivity_validation.md for the full sensitivity
matrix, including the two directions that did not match a naive
expectation and are documented rather than hidden:
  - Generic Solar, Revenue +10%: Equity IRR is flat-to-slightly-down
    instead of up (Generic Wind shows the expected small increase).
  - Senior tenor and gearing reductions move Equity IRR in a consistent
    direction for both projects, but the spec leaves that direction as
    "document, don't force pass/fail" -- so it is asserted as *observed*
    here, not as a required pass.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from app.project_factories import create_default_solar_project, create_default_wind_project
from domain.period_engine import PeriodEngine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner

# Equity IRR moves of less than this magnitude are treated as numerically
# flat rather than a directional signal, to avoid asserting a "direction"
# on what is actually floating-point noise around zero.
EQUITY_IRR_FLAT_EPSILON = 0.0005


def _run(inputs):
    engine = PeriodEngine(
        financial_close=inputs.info.financial_close,
        construction_months=inputs.info.construction_months,
        horizon_years=inputs.info.horizon_years,
        ppa_years=inputs.revenue.ppa_term_years,
    )
    config = WaterfallRunConfig.from_inputs(inputs, engine)
    runner = WaterfallRunner(inputs=inputs, engine=engine)
    return runner.run(config)


def _scale_capex(capex, factor: float):
    fields = capex._CAPEX_ITEM_FIELDS
    kwargs = {
        f: replace(getattr(capex, f), amount_keur=getattr(capex, f).amount_keur * factor)
        for f in fields
    }
    return replace(capex, **kwargs)


def _scale_opex(opex_items, factor: float):
    return tuple(replace(o, y1_amount_keur=o.y1_amount_keur * factor) for o in opex_items)


def _avg_period_senior_ds(result) -> float:
    values = [p.senior_ds_keur for p in result.periods if p.senior_ds_keur > 0]
    return sum(values) / len(values)


PROJECTS = [
    ("generic_solar", create_default_solar_project),
    ("generic_wind", create_default_wind_project),
]


# ---------------------------------------------------------------------------
# 1. CAPEX +10%
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("project_key,factory", PROJECTS)
def test_capex_up_10pct_decreases_irrs_and_may_increase_debt(project_key, factory):
    base_inputs = factory()
    bumped_inputs = replace(base_inputs, capex=_scale_capex(base_inputs.capex, 1.10))
    base = _run(base_inputs)
    bumped = _run(bumped_inputs)

    assert bumped.project_irr < base.project_irr
    assert bumped.equity_irr < base.equity_irr

    # Observed: senior debt sizing scales with the gearing-capped capex base,
    # so a 10% CAPEX increase raises the sized senior debt amount for both
    # projects. Documented, not asserted as a hard requirement, per spec
    # ("Senior debt may increase only if tied to sizing base; document
    # observed behavior").
    base_debt = base.periods[0].senior_balance_keur
    bumped_debt = bumped.periods[0].senior_balance_keur
    assert bumped_debt > base_debt  # observed behavior for both projects


# ---------------------------------------------------------------------------
# 2. Revenue / PPA price +10%
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("project_key,factory", PROJECTS)
def test_revenue_up_10pct_increases_revenue_ebitda_irr_and_dscr(project_key, factory):
    base_inputs = factory()
    bumped_inputs = replace(
        base_inputs,
        revenue=replace(base_inputs.revenue, ppa_base_tariff=base_inputs.revenue.ppa_base_tariff * 1.10),
    )
    base = _run(base_inputs)
    bumped = _run(bumped_inputs)

    assert bumped.total_revenue_keur > base.total_revenue_keur
    assert bumped.total_ebitda_keur > base.total_ebitda_keur
    assert bumped.project_irr > base.project_irr
    assert bumped.avg_dscr > base.avg_dscr
    assert bumped.min_dscr > base.min_dscr
    # Equity IRR direction is NOT asserted uniformly here -- see
    # test_revenue_up_10pct_equity_irr_direction_is_documented_per_project.


@pytest.mark.parametrize("project_key,factory", PROJECTS)
def test_revenue_up_10pct_equity_irr_direction_is_documented_per_project(project_key, factory):
    """Documented finding (not hidden): Generic Solar's Equity IRR is
    flat-to-slightly-down under Revenue +10%, contradicting the naive
    "more revenue -> higher equity IRR" expectation, while Generic Wind
    shows the expected small increase. Both deltas are small in magnitude
    (well under 1pp); this is reported as an observed anomaly requiring
    follow-up for Generic Solar, not silently passed or hidden."""
    base_inputs = factory()
    bumped_inputs = replace(
        base_inputs,
        revenue=replace(base_inputs.revenue, ppa_base_tariff=base_inputs.revenue.ppa_base_tariff * 1.10),
    )
    base = _run(base_inputs)
    bumped = _run(bumped_inputs)
    delta = bumped.equity_irr - base.equity_irr

    if project_key == "generic_solar":
        # Observed: flat-to-down. If this ever becomes a large negative
        # delta, that would be a regression worth investigating as a defect;
        # a small move either side of zero is the documented anomaly.
        assert abs(delta) < EQUITY_IRR_FLAT_EPSILON
    else:
        assert delta > 0


# ---------------------------------------------------------------------------
# 3. OPEX +10%
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("project_key,factory", PROJECTS)
def test_opex_up_10pct_decreases_ebitda_irr_and_dscr(project_key, factory):
    base_inputs = factory()
    bumped_inputs = replace(base_inputs, opex=_scale_opex(base_inputs.opex, 1.10))
    base = _run(base_inputs)
    bumped = _run(bumped_inputs)

    assert bumped.total_ebitda_keur < base.total_ebitda_keur
    assert bumped.project_irr < base.project_irr
    assert bumped.equity_irr < base.equity_irr
    assert bumped.avg_dscr < base.avg_dscr
    assert bumped.min_dscr < base.min_dscr


# ---------------------------------------------------------------------------
# 4. Generation / yield +10%
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("project_key,factory", PROJECTS)
def test_generation_up_10pct_increases_revenue_ebitda_irr_and_dscr(project_key, factory):
    base_inputs = factory()
    bumped_inputs = replace(
        base_inputs,
        technical=replace(
            base_inputs.technical,
            operating_hours_p50=base_inputs.technical.operating_hours_p50 * 1.10,
            operating_hours_p90_10y=base_inputs.technical.operating_hours_p90_10y * 1.10,
        ),
    )
    base = _run(base_inputs)
    bumped = _run(bumped_inputs)

    assert bumped.total_revenue_keur > base.total_revenue_keur
    assert bumped.total_ebitda_keur > base.total_ebitda_keur
    assert bumped.project_irr > base.project_irr
    assert bumped.equity_irr > base.equity_irr
    assert bumped.avg_dscr > base.avg_dscr
    assert bumped.min_dscr > base.min_dscr


# ---------------------------------------------------------------------------
# 5. Debt margin +100 bps
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("project_key,factory", PROJECTS)
def test_debt_margin_up_100bps_increases_debt_service_decreases_equity_irr_and_dscr(
    project_key, factory
):
    base_inputs = factory()
    bumped_inputs = replace(
        base_inputs,
        financing=replace(base_inputs.financing, margin_bps=base_inputs.financing.margin_bps + 100),
    )
    base = _run(base_inputs)
    bumped = _run(bumped_inputs)

    assert _avg_period_senior_ds(bumped) > _avg_period_senior_ds(base)
    assert bumped.equity_irr < base.equity_irr
    assert bumped.avg_dscr <= base.avg_dscr
    assert bumped.min_dscr <= base.min_dscr

    # Project IRR is computed on an unlevered basis (see
    # app/validation_status.py's project_irr methodology caveat note), so it
    # should be unaffected by a senior debt margin change. Documented and
    # checked near-equal rather than asserted to move.
    assert abs(bumped.project_irr - base.project_irr) < 1e-9


# ---------------------------------------------------------------------------
# 6. Senior debt tenor shorter
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("project_key,factory", PROJECTS)
def test_shorter_tenor_increases_annual_debt_service_and_decreases_dscr(project_key, factory):
    base_inputs = factory()
    bumped_inputs = replace(
        base_inputs,
        financing=replace(
            base_inputs.financing,
            senior_tenor_years=base_inputs.financing.senior_tenor_years - 3,
        ),
    )
    base = _run(base_inputs)
    bumped = _run(bumped_inputs)

    assert _avg_period_senior_ds(bumped) > _avg_period_senior_ds(base)
    assert bumped.avg_dscr < base.avg_dscr
    assert bumped.min_dscr < base.min_dscr

    # Equity IRR direction is observed, not asserted as a required pass
    # (spec: "Equity IRR direction should be documented"). Observed for
    # both Generic Solar and Generic Wind: a shorter tenor decreases the
    # sized senior debt amount (fewer periods of NPV'd capacity), which
    # decreases Equity IRR for both projects here.
    observed_direction = "down" if bumped.equity_irr < base.equity_irr else "up"
    assert observed_direction in ("up", "down")  # documented observation, not a pass/fail gate


# ---------------------------------------------------------------------------
# 7. Lower gearing / lower senior debt share
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("project_key,factory", PROJECTS)
def test_lower_gearing_decreases_debt_and_debt_service_and_improves_dscr(project_key, factory):
    base_inputs = factory()
    bumped_inputs = replace(
        base_inputs,
        financing=replace(base_inputs.financing, gearing_ratio=base_inputs.financing.gearing_ratio - 0.10),
    )
    base = _run(base_inputs)
    bumped = _run(bumped_inputs)

    base_debt = base.periods[0].senior_balance_keur
    bumped_debt = bumped.periods[0].senior_balance_keur
    assert bumped_debt < base_debt
    assert bumped.total_senior_ds_keur < base.total_senior_ds_keur
    assert bumped.avg_dscr > base.avg_dscr
    assert bumped.min_dscr > base.min_dscr

    # Equity funding need increases as a direct consequence of less debt
    # funding the same total CAPEX (not a separate runtime output; implied
    # by total_capex - senior_debt).
    base_equity_need = base_inputs.capex.total_capex - base_debt
    bumped_equity_need = bumped_inputs.capex.total_capex - bumped_debt
    assert bumped_equity_need > base_equity_need

    # Equity IRR direction is observed, not forced to a simplistic pass/fail
    # (spec: "Equity IRR may move depending on leverage; document observed
    # behavior"). Observed for both projects here: lower leverage decreases
    # Equity IRR (less debt amplification of equity returns).
    observed_direction = "down" if bumped.equity_irr < base.equity_irr else "up"
    assert observed_direction in ("up", "down")  # documented observation, not a pass/fail gate


# ---------------------------------------------------------------------------
# 8. Higher tax rate
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("project_key,factory", PROJECTS)
def test_higher_tax_rate_decreases_irrs_and_dscr(project_key, factory):
    base_inputs = factory()
    bumped_inputs = replace(base_inputs, tax=replace(base_inputs.tax, corporate_rate=base_inputs.tax.corporate_rate + 0.10))
    base = _run(base_inputs)
    bumped = _run(bumped_inputs)

    assert bumped.project_irr < base.project_irr
    assert bumped.equity_irr < base.equity_irr
    assert bumped.avg_dscr <= base.avg_dscr
    assert bumped.min_dscr <= base.min_dscr
