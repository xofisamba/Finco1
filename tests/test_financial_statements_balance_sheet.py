"""Offline Balance Sheet assembly tests."""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.financial_statements import assemble_financial_statements
from domain.inputs import ProjectInfo


def _run_project(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def _snapshot(result):
    return tuple(
        (
            period.revenue_keur,
            period.opex_keur,
            period.tax_keur,
            period.senior_balance_keur,
            period.shl_balance_keur,
            period.distribution_keur,
        )
        for period in result.periods
    )


def test_balance_sheet_assembly_does_not_mutate_waterfall_or_add_flags():
    waterfall = _run_project(create_default_tuho_wind1())
    before = _snapshot(waterfall)

    statements = assemble_financial_statements(waterfall)

    assert statements.balance_sheet.periods
    assert _snapshot(waterfall) == before
    project_info_fields = {field.name for field in fields(ProjectInfo)}
    assert "use_financial_statements_engine" not in project_info_fields
    assert "use_balance_sheet_engine" not in project_info_fields


def test_financial_statements_package_still_has_no_app_imports():
    package_dir = Path(__file__).parents[1] / "domain" / "financial_statements"

    for source_file in package_dir.rglob("*.py"):
        text = source_file.read_text(encoding="utf-8")
        assert "from app" not in text
        assert "import app" not in text


def test_balance_sheet_periods_and_core_formulas_for_tuho_and_oborovo():
    for factory in (create_default_tuho_wind1, create_default_oborovo):
        waterfall = _run_project(factory())
        statements = assemble_financial_statements(waterfall)

        assert len(statements.balance_sheet.periods) == len(waterfall.periods)
        for idx, balance_sheet_period in enumerate(statements.balance_sheet.periods):
            assert balance_sheet_period.net_fixed_assets_keur == pytest.approx(
                balance_sheet_period.gross_fixed_assets_keur
                - balance_sheet_period.accumulated_depreciation_keur
            )
            assert balance_sheet_period.retained_earnings_keur == pytest.approx(
                statements.pnl.periods[idx].retained_earnings_keur
            )
            assert balance_sheet_period.senior_balance_keur == pytest.approx(
                waterfall.periods[idx].senior_balance_keur
            )
            assert balance_sheet_period.shl_balance_keur == pytest.approx(
                waterfall.periods[idx].shl_balance_keur
            )
            assert balance_sheet_period.cash_is_residual is True
            assert balance_sheet_period.balance_check_keur == pytest.approx(0.0, abs=0.0001)


def test_accumulated_depreciation_rolls_forward_from_pnl():
    waterfall = _run_project(create_default_tuho_wind1())
    statements = assemble_financial_statements(waterfall)

    cumulative = 0.0
    for pnl_period, balance_sheet_period in zip(
        statements.pnl.periods,
        statements.balance_sheet.periods,
    ):
        cumulative += max(0.0, -pnl_period.depreciation_keur)
        assert balance_sheet_period.accumulated_depreciation_keur == pytest.approx(cumulative)


def test_balance_sheet_does_not_migrate_source_of_truth():
    project = create_default_tuho_wind1()
    waterfall = _run_project(project)
    statements = assemble_financial_statements(waterfall)

    assert project.financing.use_tuho_r99_input_engine is False
    assert project.info.use_shl_fcf_waterfall_engine is False
    assert statements.balance_sheet.max_abs_balance_check_keur <= 0.0001
