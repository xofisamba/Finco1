"""Output contract test — ensures WaterfallResult has stable field names.

Prevents accidental breaking of downstream UI/reporting.
"""
import pytest
from app.project_factories import create_default_solar_project
from domain.period_engine import PeriodEngine
from app.waterfall_core import run_waterfall_v3_core


def _run_waterfall_for_inputs(inputs):
    engine = PeriodEngine(
        financial_close=inputs.info.financial_close,
        construction_months=inputs.info.construction_months,
        horizon_years=inputs.info.horizon_years,
        ppa_years=inputs.revenue.ppa_term_years,
    )
    all_periods = list(engine.periods())
    op_periods = [p for p in all_periods if p.is_operation]
    return run_waterfall_v3_core(
        inputs=inputs,
        engine=engine,
        rate_per_period=inputs.financing.all_in_rate / 2,
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


class TestOutputContract:
    """Verify WaterfallResult exposes required fields."""

    def test_waterfall_result_has_required_summary_fields(self):
        """Result must expose total_revenue, total_ebitda, total_tax, project_irr, equity_irr."""
        p = create_default_solar_project()
        result = _run_waterfall_for_inputs(p)
        # Summary scalars
        assert hasattr(result, 'total_revenue_keur')
        assert hasattr(result, 'total_ebitda_keur')
        assert hasattr(result, 'total_tax_keur')
        assert hasattr(result, 'project_irr')
        assert hasattr(result, 'equity_irr')
        # Positive values sanity check
        assert result.total_revenue_keur > 0
        assert result.total_ebitda_keur > 0

    def test_waterfall_result_has_periods_list(self):
        """Result must expose a list of WaterfallPeriod objects."""
        p = create_default_solar_project()
        result = _run_waterfall_for_inputs(p)
        assert hasattr(result, 'periods')
        assert len(result.periods) > 0

    def test_waterfall_period_has_required_fields(self):
        """Each period must expose revenue, EBITDA, depreciation, tax, DSCR, and distributions."""
        p = create_default_solar_project()
        result = _run_waterfall_for_inputs(p)
        op_periods = [pr for pr in result.periods if pr.is_operation]
        assert len(op_periods) > 0
        for pr in op_periods:
            assert hasattr(pr, 'revenue_keur')
            assert hasattr(pr, 'ebitda_keur')
            assert hasattr(pr, 'depreciation_keur')
            assert hasattr(pr, 'taxable_profit_keur')
            assert hasattr(pr, 'tax_keur')
            assert hasattr(pr, 'senior_ds_keur')
            assert hasattr(pr, 'shl_service_keur')
            assert hasattr(pr, 'distribution_keur')
            assert hasattr(pr, 'dscr')

    def test_sponsor_irr_field_exists_if_defined(self):
        """If sponsor_irr is defined on the result, it must be a float."""
        p = create_default_solar_project()
        result = _run_waterfall_for_inputs(p)
        if hasattr(result, 'sponsor_irr'):
            assert isinstance(result.sponsor_irr, float)
