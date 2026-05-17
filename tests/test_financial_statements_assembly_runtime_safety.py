"""Runtime-safety tests for offline financial statements assembly."""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import pytest

from app.project_factories import create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.financial_statements import assemble_financial_statements
from domain.inputs import ProjectInfo


def _run_project(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def _runtime_totals(result):
    return {
        "revenue": result.total_revenue_keur,
        "opex": result.total_opex_keur,
        "ebitda": result.total_ebitda_keur,
        "tax": result.total_tax_keur,
        "senior_ds": result.total_senior_ds_keur,
        "shl_service": result.total_shl_service_keur,
        "distribution": result.total_distribution_keur,
    }


def _period_snapshot(result):
    return tuple(
        (
            period.revenue_keur,
            period.opex_keur,
            period.tax_keur,
            period.senior_ds_keur,
            period.shl_service_keur,
            period.distribution_keur,
            period.r99_fcf_for_distribution_keur,
            period.cash_tax_excel_style_h2_diagnostic_keur,
        )
        for period in result.periods
    )


def test_offline_assembly_does_not_change_runtime_outputs_or_mutate_waterfall():
    waterfall = _run_project(create_default_tuho_wind1())
    totals_before = _runtime_totals(waterfall)
    periods_before = _period_snapshot(waterfall)

    statements = assemble_financial_statements(waterfall)

    assert statements.pnl.periods
    assert _runtime_totals(waterfall) == pytest.approx(totals_before)
    assert _period_snapshot(waterfall) == periods_before


def test_financial_statements_package_has_no_app_imports():
    package_dir = Path(__file__).parents[1] / "domain" / "financial_statements"

    for source_file in package_dir.rglob("*.py"):
        text = source_file.read_text(encoding="utf-8")
        assert "from app" not in text
        assert "import app" not in text


def test_financial_statements_stage_does_not_add_project_info_flags():
    project_info_fields = {field.name for field in fields(ProjectInfo)}

    assert "use_financial_statements_engine" not in project_info_fields
    assert "use_financial_statements_runtime" not in project_info_fields
    assert "use_pnl_assembly_engine" not in project_info_fields


def test_stage_two_does_not_accept_r99_or_enable_shl_fcf():
    project = create_default_tuho_wind1()
    waterfall = _run_project(project)
    statements = assemble_financial_statements(waterfall)

    assert project.financing.use_tuho_r99_input_engine is False
    assert project.info.use_shl_fcf_waterfall_engine is False
    assert all(period.r99_runtime_source_accepted is False for period in statements.tax_bridge.periods)
