"""Parity test: utils/cache cached_run_waterfall_v3 vs app/waterfall_core.run_waterfall_v3_core.

Ensures the delegation from utils/cache → waterfall_core produces identical results.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.project_factories import create_default_solar_project
from domain.period_engine import PeriodEngine
from utils.cache import cached_run_waterfall_v3
from app.waterfall_core import run_waterfall_v3_core


def _make_engine(inputs):
    return PeriodEngine(
        financial_close=inputs.info.financial_close,
        construction_months=inputs.info.construction_months,
        horizon_years=inputs.info.horizon_years,
        ppa_years=inputs.revenue.ppa_term_years,
    )


def _run_both(project):
    """Run waterfall via both paths and return project_irr."""
    engine = _make_engine(project)
    all_periods = list(engine.periods())
    op_periods = [p for p in all_periods if p.is_operation]

    # Direct call to run_waterfall_v3_core
    direct = run_waterfall_v3_core(
        inputs=project,
        engine=engine,
        rate_per_period=project.financing.all_in_rate / 2,
        tenor_periods=len(op_periods),
        target_dscr=project.financing.target_dscr,
        lockup_dscr=project.financing.lockup_dscr,
        tax_rate=project.tax.corporate_rate,
        dsra_months=project.financing.dsra_months,
        shl_amount=project.financing.shl_amount_keur,
        shl_rate=project.financing.shl_rate,
        shl_idc_keur=0.0,
        shl_repayment_method="bullet",
        equity_irr_method="equity_only",
        share_capital_keur=project.financing.share_capital_keur,
        sculpt_capex_keur=project.capex.sculpt_capex_keur,
        debt_sizing_method=project.financing.debt_sizing_method,
    )

    # Cached version (bypass @st.cache_data via monkeypatch)
    with patch("utils.cache.st.cache_data", lambda **kw: lambda f: f):
        cached = cached_run_waterfall_v3(
            inputs=project,
            engine=engine,
            rate_per_period=project.financing.all_in_rate / 2,
            tenor_periods=len(op_periods),
            target_dscr=project.financing.target_dscr,
            lockup_dscr=project.financing.lockup_dscr,
            tax_rate=project.tax.corporate_rate,
            dsra_months=project.financing.dsra_months,
            shl_amount=project.financing.shl_amount_keur,
            shl_rate=project.financing.shl_rate,
            shl_idc_keur=0.0,
            shl_repayment_method="bullet",
            equity_irr_method="equity_only",
            share_capital_keur=project.financing.share_capital_keur,
            sculpt_capex_keur=project.capex.sculpt_capex_keur,
            debt_sizing_method=project.financing.debt_sizing_method,
        )

    return direct, cached


def test_cached_and_direct_produce_identical_project_irr():
    """cached_run_waterfall_v3 and run_waterfall_v3_core give same project_irr."""
    project = create_default_solar_project()
    direct, cached = _run_both(project)

    assert abs(direct.project_irr - cached.project_irr) <= 1e-6, (
        f"project_irr mismatch: direct={direct.project_irr}, "
        f"cached={cached.project_irr}, diff={abs(direct.project_irr - cached.project_irr)}"
    )


def test_cached_and_direct_produce_identical_equity_irr():
    """Equity IRR also matches between the two paths."""
    project = create_default_solar_project()
    direct, cached = _run_both(project)

    assert abs(direct.equity_irr - cached.equity_irr) <= 1e-6, (
        f"equity_irr mismatch: direct={direct.equity_irr}, "
        f"cached={cached.equity_irr}"
    )
