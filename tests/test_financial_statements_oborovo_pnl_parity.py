"""Oborovo offline P&L assembly tests."""

from __future__ import annotations

import pytest

from app.project_factories import create_default_oborovo
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.financial_statements import assemble_financial_statements
from domain.financial_statements.excel_mapping import PNL_ROW_BY_CODE


def _run_project(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def test_oborovo_pnl_rows_generated_for_all_periods():
    waterfall = _run_project(create_default_oborovo())
    statements = assemble_financial_statements(waterfall)

    assert len(statements.pnl.periods) == len(waterfall.periods)
    for period in statements.pnl.periods:
        assert set(period.row_values()) == set(PNL_ROW_BY_CODE)


def test_oborovo_pnl_assembly_uses_existing_waterfall_period_fields():
    waterfall = _run_project(create_default_oborovo())
    statements = assemble_financial_statements(waterfall)
    source = waterfall.periods[0]
    pnl = statements.pnl.periods[0]

    assert pnl.revenues_keur == pytest.approx(source.revenue_keur)
    assert pnl.operating_expenses_keur == pytest.approx(-source.opex_keur)
    assert pnl.depreciation_keur == pytest.approx(-source.tax_depreciation_audit_keur)
    assert pnl.senior_interest_expense_keur == pytest.approx(-source.senior_interest_keur)
    assert pnl.shl_interest_expense_keur == pytest.approx(-source.shl_interest_keur)


def test_oborovo_assembly_does_not_change_runtime_totals():
    waterfall = _run_project(create_default_oborovo())
    before = (
        waterfall.total_revenue_keur,
        waterfall.total_opex_keur,
        waterfall.total_tax_keur,
        waterfall.total_senior_ds_keur,
        waterfall.total_distribution_keur,
    )

    assemble_financial_statements(waterfall)

    after = (
        waterfall.total_revenue_keur,
        waterfall.total_opex_keur,
        waterfall.total_tax_keur,
        waterfall.total_senior_ds_keur,
        waterfall.total_distribution_keur,
    )
    assert after == pytest.approx(before)
