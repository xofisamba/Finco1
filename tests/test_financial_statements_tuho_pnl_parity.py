"""TUHO offline P&L assembly tests."""

from __future__ import annotations

import pytest

from app.project_factories import create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.financial_statements import assemble_financial_statements
from domain.financial_statements.excel_mapping import PNL_ROW_BY_CODE


def _run_project(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def test_tuho_pnl_rows_generated_for_all_periods():
    waterfall = _run_project(create_default_tuho_wind1())
    statements = assemble_financial_statements(waterfall)

    assert len(statements.pnl.periods) == len(waterfall.periods)
    assert {mapping.row_code for mapping in statements.pnl.row_mapping} == set(PNL_ROW_BY_CODE)
    for period in statements.pnl.periods:
        assert set(period.row_values()) == set(PNL_ROW_BY_CODE)


def test_tuho_pnl_assembly_uses_existing_waterfall_period_fields():
    waterfall = _run_project(create_default_tuho_wind1())
    statements = assemble_financial_statements(waterfall)
    source = waterfall.periods[0]
    pnl = statements.pnl.periods[0]

    assert pnl.revenues_keur == pytest.approx(source.revenue_keur)
    assert pnl.operating_expenses_keur == pytest.approx(-source.opex_keur)
    assert pnl.depreciation_keur == pytest.approx(-source.tax_depreciation_audit_keur)
    assert pnl.senior_interest_expense_keur == pytest.approx(-source.senior_interest_keur)
    assert pnl.shl_interest_expense_keur == pytest.approx(-source.shl_interest_keur)
    assert pnl.net_dividends_keur == pytest.approx(-source.distribution_keur)


def test_tuho_pnl_subtotals_and_retained_earnings_formula_hold():
    waterfall = _run_project(create_default_tuho_wind1())
    statements = assemble_financial_statements(waterfall)
    first = statements.pnl.periods[0]

    assert first.total_expenses_keur == pytest.approx(
        first.operating_expenses_keur
        + first.local_tax_keur
        + first.wht_on_interests_keur
        + first.depreciation_keur
    )
    assert first.ebit_keur == pytest.approx(first.revenues_keur + first.total_expenses_keur)
    assert first.earnings_before_tax_keur == pytest.approx(
        first.ebit_keur + first.financial_earnings_keur
    )
    assert first.net_income_keur == pytest.approx(
        first.earnings_before_tax_keur + first.cit_accrual_keur
    )

    for idx, period in enumerate(statements.pnl.periods):
        previous_retained = statements.pnl.periods[idx - 1].retained_earnings_keur if idx else 0.0
        source_dividends = waterfall.periods[idx].distribution_keur
        assert period.retained_earnings_keur == pytest.approx(
            previous_retained + period.net_income_keur - source_dividends
        )


def test_tuho_pnl_totals_are_row_sum_of_period_values():
    statements = assemble_financial_statements(_run_project(create_default_tuho_wind1()))

    for row_code in ("R8", "R10", "R13", "R24", "R27", "R46", "R50"):
        assert statements.pnl.total_for_row(row_code) == pytest.approx(
            sum(period.row_values()[row_code] for period in statements.pnl.periods)
        )
