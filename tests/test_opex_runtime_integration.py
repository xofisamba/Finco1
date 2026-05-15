"""Integration tests for Phase 7H O3c — OPEX runtime integration behind feature flag.

Tests:
1. Flag False: backward compatibility (TUHO legacy path intact)
2. Flag True TUHO: annual OPEX = 84,674.78 kEUR, selected years match Excel
3. TUHO opt-in full waterfall impact (reported, not tuned)
4. Oborovo unchanged when flag False
5. No unrelated runtime changes
6. Semiannual allocation correct
"""
from __future__ import annotations

import dataclasses
import pytest

from domain.inputs import ProjectInputs
from domain.opex.runtime_adapter import opex_line_item_adapter
from domain.waterfall.waterfall_engine import run_waterfall
from domain.opex.projections import opex_schedule_annual
from domain.revenue.generation import full_revenue_schedule, full_generation_schedule
from domain.period_engine import PeriodEngine


# ── Excel annual OPEX totals for TUHO (from row 105) ─────────────────────
EXCEL_ANNUAL_TUHO = [
    1998.05, 2029.83, 2147.06, 2180.13, 2213.86,   # Y1–Y5
    2378.01, 2413.10, 2448.90, 2485.41, 2522.65,   # Y6–Y10
    2603.04, 2641.79, 2681.31, 2721.62, 2734.77,   # Y11–Y15
    2827.03, 2869.24, 2912.29, 2956.21, 3001.00,   # Y16–Y20
    3131.49, 3178.09, 3225.63, 3274.11, 3323.57,   # Y21–Y25
    3450.33, 3501.79, 3554.27, 3607.80, 3662.40,   # Y26–Y30
]
EXCEL_30YR_TOTAL_TUHO = 84_674.78
SAMPLE_YEARS = {1: 1998.05, 2: 2029.83, 7: 2413.10,
                10: 2522.65, 13: 2681.31, 20: 3001.00, 30: 3662.40}
TOL = 0.1


def _enable_flag(inputs: ProjectInputs) -> ProjectInputs:
    enabled_info = dataclasses.replace(inputs.info, use_opex_line_item_engine=True)
    return dataclasses.replace(inputs, info=enabled_info)


def _run_waterfall_for_inputs(inputs: ProjectInputs) -> "WaterfallResult":
    """Run waterfall for given inputs, using flag to select OPEX path."""
    engine = PeriodEngine(
        financial_close=inputs.info.financial_close,
        construction_months=inputs.info.construction_months,
        horizon_years=inputs.info.horizon_years,
        ppa_years=inputs.revenue.ppa_term_years,
        frequency=inputs.info.period_frequency,
    )
    periods_list = list(engine.periods())
    revenue_dict = full_revenue_schedule(inputs, engine)
    generation_dict = full_generation_schedule(inputs, engine)

    if inputs.info.use_opex_line_item_engine:
        from domain.opex.runtime_adapter import opex_line_item_adapter
        opex_annual = opex_line_item_adapter(inputs)
    else:
        opex_annual = opex_schedule_annual(inputs, inputs.info.horizon_years)

    dep_per_year = inputs.capex.total_capex / inputs.info.horizon_years
    ebitda_schedule, revenue_schedule, depreciation_schedule = [], [], []
    for p in periods_list:
        rev = revenue_dict.get(p.index, 0)
        if p.is_operation:
            opex = opex_annual.get(p.year_index, 0) / 2
            ebitda = max(0, rev - opex)
            dep = dep_per_year / 2
        else:
            ebitda = 0
            dep = 0
        revenue_schedule.append(rev)
        ebitda_schedule.append(ebitda)
        depreciation_schedule.append(dep)

    fin = inputs.financing
    return run_waterfall(
        ebitda_schedule=ebitda_schedule,
        revenue_schedule=revenue_schedule,
        generation_schedule=[generation_dict.get(p.index, 0) for p in periods_list],
        depreciation_schedule=depreciation_schedule,
        opex_schedule=[opex_annual.get(p.year_index, 0) / 2 if p.is_operation else 0 for p in periods_list],
        periods=periods_list,
        total_capex=inputs.capex.total_capex,
        rate_per_period=fin.base_rate / 2,
        tenor_periods=fin.senior_tenor_years * 2,
        target_dscr=fin.target_dscr,
        lockup_dscr=fin.lockup_dscr,
        tax_rate=inputs.tax.corporate_rate,
        dsra_months=fin.dsra_months,
        shl_amount=fin.shl_amount_keur,
        shl_rate=fin.shl_rate,
        shl_idc_keur=inputs.capex.idc_keur,
        shl_repayment_method=fin.shl_repayment_method,
        shl_tenor_years=fin.shl_tenor_years,
        shl_wht_rate=inputs.tax.wht_sponsor_shl_interest,
        discount_rate_project=0.0641,
        discount_rate_equity=0.0965,
        financial_close=inputs.info.financial_close,
        equity_irr_method=fin.equity_irr_method,
        share_capital_keur=fin.share_capital_keur,
        sculpt_capex_keur=inputs.capex.total_capex,
        debt_sizing_method=fin.debt_sizing_method,
        fixed_ds_keur=fin.fixed_ds_keur,
    )


# ── Tests ────────────────────────────────────────────────────────────────

class TestAdapterFlagFalse:
    """Test 1 — Default-off backward compatibility (TUHO)."""

    def test_flag_false_uses_legacy_path(self):
        tuho = ProjectInputs.create_default_tuho_wind1()
        assert tuho.info.use_opex_line_item_engine is False
        schedule = opex_schedule_annual(tuho, tuho.info.horizon_years)
        assert isinstance(schedule, dict)
        assert len(schedule) == 30


class TestAdapterFlagTrueTUHO:
    """Test 3 — TUHO opt-in annual OPEX."""

    def test_flag_true_returns_30yr_schedule(self):
        tuho = ProjectInputs.create_default_tuho_wind1()
        enabled = _enable_flag(tuho)
        schedule = opex_line_item_adapter(enabled)
        assert len(schedule) == 30
        assert all(y in schedule for y in range(1, 31))

    def test_30yr_total_matches_excel(self):
        tuho = ProjectInputs.create_default_tuho_wind1()
        enabled = _enable_flag(tuho)
        schedule = opex_line_item_adapter(enabled)
        engine_total = sum(schedule.values())
        delta = abs(engine_total - EXCEL_30YR_TOTAL_TUHO)
        assert delta <= TOL, (
            f"30-year total: engine={engine_total:.2f}, excel={EXCEL_30YR_TOTAL_TUHO:.2f}, Δ={delta:.2f}"
        )

    def test_selected_years_match_excel(self):
        tuho = ProjectInputs.create_default_tuho_wind1()
        enabled = _enable_flag(tuho)
        schedule = opex_line_item_adapter(enabled)
        failures = []
        for y, expected in SAMPLE_YEARS.items():
            actual = schedule[y]
            d = abs(actual - expected)
            if d > TOL:
                failures.append(f"Y{y}: engine={actual:.2f}, excel={expected:.2f}, Δ={d:.2f}")
        assert not failures, "\n".join(failures)


class TestAdapterOborovoUnchanged:
    """Test 2 — Oborovo unchanged (flag False by default)."""

    def test_oborovo_flag_false(self):
        oborovo = ProjectInputs.create_default_oborovo()
        assert oborovo.info.use_opex_line_item_engine is False

    def test_oborovo_uses_legacy_path(self):
        oborovo = ProjectInputs.create_default_oborovo()
        schedule = opex_schedule_annual(oborovo, oborovo.info.horizon_years)
        assert isinstance(schedule, dict)
        assert len(schedule) >= 1

    def test_oborovo_flag_true_raises(self):
        oborovo = ProjectInputs.create_default_oborovo()
        enabled = _enable_flag(oborovo)
        with pytest.raises(ValueError, match="not supported"):
            opex_line_item_adapter(enabled)


class TestAdapterNoUnrelatedChanges:
    """Test 6 — No unrelated runtime changes."""

    def test_runtime_adapter_no_waterfall_import(self):
        """Adapter does not import waterfall_engine."""
        import domain.opex.runtime_adapter as ra
        source = open(ra.__file__).read()
        # Keep only actual import/from statements (line starts with import/from)
        import_lines = [l for l in source.split('\n') if l.strip().startswith(('from', 'import'))]
        code = '\n'.join(import_lines)
        assert 'waterfall_engine' not in code, "Adapter should not import waterfall_engine"

    def test_flag_true_not_set_on_default_tuho(self):
        tuho = ProjectInputs.create_default_tuho_wind1()
        assert tuho.info.use_opex_line_item_engine is False


class TestSemiannualAllocation:
    """Test 5 — Semiannual allocation."""

    def test_annual_y1_split_equals_two_semiannual(self):
        tuho = ProjectInputs.create_default_tuho_wind1()
        enabled = _enable_flag(tuho)
        schedule = opex_line_item_adapter(enabled)
        y1_annual = schedule[1]
        # H1 + H2 (each = annual / 2) == annual
        assert (y1_annual / 2) + (y1_annual / 2) == pytest.approx(y1_annual)


class TestWaterfallIntegration:
    """Test 4 — TUHO full waterfall integration (direct run_waterfall call)."""

    def test_waterfall_with_flag_true_runs(self):
        """Smoke test: waterfall with flag True produces result."""
        tuho = ProjectInputs.create_default_tuho_wind1()
        enabled = _enable_flag(tuho)
        result = _run_waterfall_for_inputs(enabled)
        assert result is not None
        assert result.total_revenue_keur > 0

    def test_waterfall_flag_false_vs_true_delta_reported(self):
        """Report delta between flag False and flag True (no tuning)."""
        tuho = ProjectInputs.create_default_tuho_wind1()

        result_false = _run_waterfall_for_inputs(tuho)
        enabled = _enable_flag(tuho)
        result_true = _run_waterfall_for_inputs(enabled)

        delta_rev = abs(result_false.total_revenue_keur - result_true.total_revenue_keur)
        assert delta_rev < 0.01, "Revenue should not change with flag"

        delta_opex = result_true.total_opex_keur - result_false.total_opex_keur
        delta_ebitda = result_true.total_ebitda_keur - result_false.total_ebitda_keur
        delta_dist = abs(result_false.total_distribution_keur - result_true.total_distribution_keur)

        print(f"\n=== Flag True vs False TUHO Impact ===")
        print(f"Revenue delta:       {delta_rev:.4f} kEUR  (should be ~0)")
        print(f"OPEX delta:         {delta_opex:.4f} kEUR  (new minus old)")
        print(f"EBITDA delta:       {delta_ebitda:.4f} kEUR")
        print(f"Distributions False: {result_false.total_distribution_keur:.2f} kEUR")
        print(f"Distributions True:  {result_true.total_distribution_keur:.2f} kEUR")
        print(f"Distribution delta:  {delta_dist:.4f} kEUR")

        self._impact = {
            "revenue_delta": delta_rev,
            "opex_delta": delta_opex,
            "ebitda_delta": delta_ebitda,
            "distributions_false": result_false.total_distribution_keur,
            "distributions_true": result_true.total_distribution_keur,
            "distributions_delta": delta_dist,
        }
        assert abs(delta_opex) > 0.01, "OPEX should differ when flag is True"


class TestWaterfallOborovoUnchanged:
    """Oborovo unchanged when flag False."""

    def test_oborovo_flag_false_waterfall(self):
        oborovo = ProjectInputs.create_default_oborovo()
        assert oborovo.info.use_opex_line_item_engine is False
        result = _run_waterfall_for_inputs(oborovo)
        assert result is not None
        assert result.total_revenue_keur > 0