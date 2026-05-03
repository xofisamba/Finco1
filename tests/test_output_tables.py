"""Tests for output table adapters."""
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
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

class MockPeriod:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class MockResult:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_dashboard_kpis_handles_missing_fields():
    result = MockResult()
    kpis = build_dashboard_kpis(result)
    assert isinstance(kpis, dict)
    assert kpis.get("project_irr") is None
    assert kpis.get("equity_irr") is None
    assert kpis.get("min_dscr") is None

def test_waterfall_table_has_expected_rows():
    result = MockResult(periods=[
        MockPeriod(revenue_keur=100, opex_keur=20, ebitda_keur=80, cfads_keur=70),
    ])
    df = build_waterfall_table(result)
    assert "Revenue" in df.index
    assert "EBITDA" in df.index
    assert "CFADS" in df.index
    assert "Senior Debt Service" in df.index

def test_waterfall_table_uses_period_dates_as_columns():
    result = MockResult(periods=[
        MockPeriod(end_date="2025-12-31", revenue_keur=100, ebitda_keur=80, cfads_keur=70,
                   senior_debt_service_keur=30, shl_service_keur=0, dsra_contribution_keur=0,
                   distributions_keur=40, cash_balance_keur=10, senior_debt_balance_keur=70,
                   shl_balance_keur=0),
    ])
    df = build_waterfall_table(result)
    assert "2025-12-31" in df.columns

def test_debt_table_has_dscr_row():
    result = MockResult(periods=[
        MockPeriod(dscr=1.45, senior_debt_service_keur=30, senior_debt_balance_keur=70,
                   senior_interest_keur=10, senior_principal_keur=20, llcr=1.5, plcr=1.2),
    ])
    df = build_debt_table(result)
    assert "DSCR" in df.index
    assert df.loc["DSCR"].iloc[0] == 1.45

def test_returns_table_includes_sponsor_irr():
    result = MockResult(project_irr=0.09, equity_irr=0.12, sponsor_irr=0.15)
    df = build_returns_table(result)
    assert "Sponsor IRR" in df.index

def test_portfolio_table_has_pooled_cfads_and_dscr():
    pr = MagicMock()
    pr.total_revenue_keur = 100_000.0
    pr.total_ebitda_keur = 80_000.0
    pr.total_tax_keur = 5_000.0
    pr.total_cfads_keur = 75_000.0
    pr.portfolio_senior_debt_service_keur = 40_000.0
    pr.portfolio_dscr = 1.5
    df = build_portfolio_table(pr)
    assert "Pooled CFADS" in df.index
    assert "Portfolio DSCR" in df.index

def test_output_tables_do_not_import_streamlit():
    import ast
    import inspect
    import app.output_tables as mod
    source = inspect.getsource(mod)
    tree = ast.parse(source)
    # Check for any Streamlit import (Import or ImportFrom nodes)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any("streamlit" in alias.name for alias in node.names):
                pytest.fail("streamlit imported in output_tables.py")
        elif isinstance(node, ast.ImportFrom):
            if node.module and "streamlit" in node.module:
                pytest.fail("streamlit imported in output_tables.py")