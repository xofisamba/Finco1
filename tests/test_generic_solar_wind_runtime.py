"""Generic solar and wind baseline runtime tests.

Uses only app.project_factories.create_default_solar_project() and
create_default_wind_project() — no Oborovo/TUHO factories, no Excel fixtures.
"""
from dataclasses import replace
import pytest
from app.project_factories import create_default_solar_project, create_default_wind_project
from domain.period_engine import PeriodEngine
from app.waterfall_core import run_waterfall_v3_core


def _run_waterfall_for_inputs(inputs, rate_per_period=None):
    """Run headless waterfall for generic project inputs."""
    engine = PeriodEngine(
        financial_close=inputs.info.financial_close,
        construction_months=inputs.info.construction_months,
        horizon_years=inputs.info.horizon_years,
        ppa_years=inputs.revenue.ppa_term_years,
    )
    all_periods = list(engine.periods())
    op_periods = [p for p in all_periods if p.is_operation]
    if rate_per_period is None:
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


# ---------------------------------------------------------------------------
# Solar tests
# ---------------------------------------------------------------------------

class TestGenericSolarRuntime:
    """Baseline runtime tests for generic solar projects."""

    def test_solar_baseline_runs_full_runtime(self):
        """Solar baseline produces non-zero revenue, EBITDA, and a finite IRR."""
        p = create_default_solar_project()
        result = _run_waterfall_for_inputs(p)
        assert len(result.periods) > 0
        assert result.total_revenue_keur > 0
        assert result.total_ebitda_keur > 0
        assert result.project_irr is not None
        assert 0 < result.project_irr < 5.0  # sanity check
        assert result.total_tax_keur >= 0
        dep_periods = [pr for pr in result.periods if pr.depreciation_keur > 0]
        assert len(dep_periods) > 0

    def test_solar_revenue_hand_checkable_first_operating_year(self):
        """First operating year revenue matches capacity * hours * tariff.

        Hand-check values:
        - capacity_mw = 50
        - operating_hours_p50 = 1500
        - plant_availability = 1.0
        - grid_availability = 1.0
        - degradation = 0.0
        - ppa_base_tariff = 60 EUR/MWh
        - ppa_production_share = 1.0

        Expected generation Y1: 50 * 1500 = 75,000 MWh
        Expected revenue Y1: 75,000 * 60 / 1000 = 4,500 kEUR
        """
        p = create_default_solar_project()
        p = replace(p,
            technical=replace(p.technical,
                capacity_mw=50.0,
                operating_hours_p50=1500.0,
                operating_hours_p90_10y=1500.0,
                plant_availability=1.0,
                grid_availability=1.0,
                pv_degradation=0.0,
            ),
            revenue=replace(p.revenue,
                ppa_base_tariff=60.0,
                ppa_production_share=1.0,
                balancing_cost_pv=0.0,
            ),
        )
        result = _run_waterfall_for_inputs(p)
        op_periods = [pr for pr in result.periods if pr.is_operation]
        # Sum first operating year (may be 1 or 2 semiannual periods)
        y1_periods = [pr for pr in op_periods if pr.year_index == 1]
        y1_revenue = sum(pr.revenue_keur for pr in y1_periods)
        assert 4400 < y1_revenue < 4600, (
            f"Expected ~4,500 kEUR for Y1 revenue, got {y1_revenue}"
        )

    def test_solar_higher_tariff_increases_project_irr(self):
        """Higher PPA tariff increases project IRR."""
        base = create_default_solar_project()
        higher = replace(base,
            revenue=replace(base.revenue, ppa_base_tariff=base.revenue.ppa_base_tariff * 1.2)
        )
        r_base = _run_waterfall_for_inputs(base)
        r_high = _run_waterfall_for_inputs(higher)
        assert r_high.project_irr > r_base.project_irr, (
            f"Expected higher tariff -> higher IRR: {r_high.project_irr} vs {r_base.project_irr}"
        )

    def test_solar_higher_capex_decreases_project_irr(self):
        """Higher CAPEX decreases project IRR."""
        base = create_default_solar_project()
        higher = replace(base,
            capex=replace(base.capex,
                epc_contract=replace(base.capex.epc_contract,
                    amount_keur=base.capex.epc_contract.amount_keur * 1.15)
            )
        )
        r_base = _run_waterfall_for_inputs(base)
        r_high = _run_waterfall_for_inputs(higher)
        assert r_high.project_irr < r_base.project_irr, (
            f"Expected higher CAPEX -> lower IRR: {r_high.project_irr} vs {r_base.project_irr}"
        )


# ---------------------------------------------------------------------------
# Wind tests
# ---------------------------------------------------------------------------

class TestGenericWindRuntime:
    """Baseline runtime tests for generic wind projects."""

    def test_wind_baseline_runs_full_runtime(self):
        """Wind baseline produces non-zero revenue, EBITDA, and a finite IRR."""
        p = create_default_wind_project()
        result = _run_waterfall_for_inputs(p)
        assert len(result.periods) > 0
        assert result.total_revenue_keur > 0
        assert result.total_ebitda_keur > 0
        assert result.project_irr is not None
        assert 0 < result.project_irr < 5.0
        dep_periods = [pr for pr in result.periods if pr.depreciation_keur > 0]
        assert len(dep_periods) > 0

    def test_wind_revenue_hand_checkable_first_operating_year(self):
        """First operating year revenue matches capacity * hours * tariff.

        Hand-check values:
        - capacity_mw = 50
        - operating_hours_p50 = 3000
        - plant_availability = 1.0
        - grid_availability = 1.0
        - degradation = 0.0
        - ppa_base_tariff = 70 EUR/MWh
        - ppa_production_share = 1.0
        - balancing_cost = 0 (explicitly disabled for hand-check)

        Expected generation Y1: 50 * 3000 = 150,000 MWh
        Expected revenue Y1: 150,000 * 70 / 1000 = 10,500 kEUR
        """
        p = create_default_wind_project()
        p = replace(p,
            technical=replace(p.technical,
                capacity_mw=50.0,
                operating_hours_p50=3000.0,
                operating_hours_p90_10y=3000.0,
                plant_availability=1.0,
                grid_availability=1.0,
                pv_degradation=0.0,
            ),
            revenue=replace(p.revenue,
                ppa_base_tariff=70.0,
                ppa_production_share=1.0,
                balancing_cost_pv=0.0,
            ),
        )
        result = _run_waterfall_for_inputs(p)
        op_periods = [pr for pr in result.periods if pr.is_operation]
        y1_periods = [pr for pr in op_periods if pr.year_index == 1]
        y1_revenue = sum(pr.revenue_keur for pr in y1_periods)
        assert 9900 < y1_revenue < 10800, (
            f"Expected ~10,500 kEUR for Y1 revenue, got {y1_revenue}"
        )

    def test_wind_higher_tariff_increases_project_irr(self):
        """Higher PPA tariff increases project IRR for wind."""
        base = create_default_wind_project()
        higher = replace(base,
            revenue=replace(base.revenue, ppa_base_tariff=base.revenue.ppa_base_tariff * 1.2)
        )
        r_base = _run_waterfall_for_inputs(base)
        r_high = _run_waterfall_for_inputs(higher)
        assert r_high.project_irr > r_base.project_irr, (
            f"Expected higher tariff -> higher IRR: {r_high.project_irr} vs {r_base.project_irr}"
        )
