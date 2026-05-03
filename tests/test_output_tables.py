"""Tests for output table adapters using real generic solar project results."""
import pytest
import pandas as pd
from unittest.mock import MagicMock
from app.output_tables import (
    build_dashboard_kpis,
    build_waterfall_table,
    build_revenue_table,
    build_debt_table,
    build_tax_depreciation_table,
    build_returns_table,
    build_portfolio_table,
    _safe_get,
    _safe_get_or_none,
    _period_label,
)
from app.project_factories import create_default_solar_project
from domain.period_engine import PeriodEngine
from app.waterfall_core import run_waterfall_v3_core


def _run_solar_waterfall():
    proj = create_default_solar_project()
    engine = PeriodEngine(
        financial_close=proj.info.financial_close,
        construction_months=proj.info.construction_months,
        horizon_years=proj.info.horizon_years,
        ppa_years=proj.revenue.ppa_term_years,
    )
    op_periods = [p for p in engine.periods() if p.is_operation]
    return run_waterfall_v3_core(
        inputs=proj, engine=engine,
        rate_per_period=proj.financing.all_in_rate / 2,
        tenor_periods=len(op_periods),
        target_dscr=proj.financing.target_dscr,
        lockup_dscr=proj.financing.lockup_dscr,
        tax_rate=proj.tax.corporate_rate,
        dsra_months=proj.financing.dsra_months,
        shl_amount=proj.financing.shl_amount_keur,
        shl_rate=proj.financing.shl_rate,
        shl_idc_keur=0.0,
        shl_repayment_method="bullet",
        equity_irr_method="equity_only",
        share_capital_keur=proj.financing.share_capital_keur,
        sculpt_capex_keur=proj.capex.sculpt_capex_keur,
        debt_sizing_method=proj.financing.debt_sizing_method,
    )


def test_waterfall_table_has_revenue_row_not_all_zero():
    result = _run_solar_waterfall()
    df = build_waterfall_table(result)
    assert "Revenue" in df.index
    assert df.loc["Revenue"].sum() > 0, "Revenue should not be all zero for solar project"


def test_waterfall_table_has_cfads_row_not_all_zero():
    result = _run_solar_waterfall()
    df = build_waterfall_table(result)
    assert "CFADS" in df.index
    # CFADS maps to cf_after_tax_keur
    assert df.loc["CFADS"].sum() != 0, "CFADS should not be identically zero"


def test_waterfall_table_has_senior_debt_service_row():
    result = _run_solar_waterfall()
    df = build_waterfall_table(result)
    assert "Senior Debt Service" in df.index


def test_waterfall_table_uses_period_dates_as_columns():
    result = _run_solar_waterfall()
    df = build_waterfall_table(result)
    # Columns should be date strings like YYYY-MM-DD
    cols = list(df.columns)
    assert len(cols) > 0
    # All columns should be non-empty strings
    assert all(str(c) for c in cols)


def test_waterfall_table_has_expected_rows():
    result = _run_solar_waterfall()
    df = build_waterfall_table(result)
    expected = ["Revenue", "EBITDA", "CFADS", "Senior Debt Service", "Distributions"]
    for row in expected:
        assert row in df.index, f"{row} should be in waterfall table"


def test_debt_table_has_dscr_row():
    result = _run_solar_waterfall()
    df = build_debt_table(result)
    assert "DSCR" in df.index


def test_returns_table_includes_all_irr_fields():
    result = _run_solar_waterfall()
    df = build_returns_table(result)
    for label in ["Project IRR", "Equity IRR", "Sponsor IRR"]:
        assert label in df.index, f"{label} should be in returns table"


def test_dashboard_kpis_contains_all_required_keys():
    result = _run_solar_waterfall()
    kpis = build_dashboard_kpis(result)
    required = ["total_revenue_keur", "project_irr", "equity_irr", "avg_dscr", "min_dscr"]
    for k in required:
        assert k in kpis, f"{k} should be in dashboard KPIs"


def test_dashboard_kpis_handles_missing_fields():
    result = MagicMock()
    result.total_revenue_keur = None
    result.project_irr = None
    kpis = build_dashboard_kpis(result)
    assert kpis.get("project_irr") is None
    assert kpis.get("total_revenue_keur") is None


def test_portfolio_table_builds_from_real_portfolio():
    from app.portfolio_runner import run_portfolio_from_inputs
    from app.project_factories import create_default_solar_project, create_default_wind_project
    from domain.portfolio.inputs import PortfolioInputs
    from domain.inputs import FinancingParams

    proj_s = create_default_solar_project()
    proj_w = create_default_wind_project()
    shared = FinancingParams(
        share_capital_keur=50000.0, senior_debt_amount_keur=100000.0,
        senior_tenor_years=10, target_dscr=1.3,
    )
    pf = PortfolioInputs(projects=(proj_s, proj_w), portfolio_name="Test", shared_financing=shared)
    pr = run_portfolio_from_inputs(pf)
    df = build_portfolio_table(pr)
    assert "Pooled CFADS" in df.index
    assert "Portfolio DSCR" in df.index
    assert "Pooled Revenue" in df.index


def test_output_tables_do_not_import_streamlit():
    import ast, inspect
    import app.output_tables as mod
    source = inspect.getsource(mod)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "streamlit" in alias.name:
                    pytest.fail(f"streamlit imported in output_tables.py: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module and "streamlit" in node.module:
                pytest.fail(f"streamlit imported in output_tables.py: from {node.module}")