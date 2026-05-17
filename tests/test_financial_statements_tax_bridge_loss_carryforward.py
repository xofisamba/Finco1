"""Tax bridge and loss carry-forward tests for offline statements."""

from __future__ import annotations

import pytest

from app.project_factories import create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.financial_statements import assemble_financial_statements
from domain.financial_statements.templates.croatia import (
    build_croatia_financial_statements_config,
)


def _run_project(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def test_croatia_template_encodes_phase_two_tax_bridge_metadata():
    config = build_croatia_financial_statements_config(project_code="TUHO-WIND-1")

    assert config.project_code == "TUHO-WIND-1"
    assert config.cit_rate == pytest.approx(0.18)
    assert config.period_frequency == "semiannual"
    assert config.cash_tax_timing == "annual_h2_diagnostic"
    assert config.loss_carryforward_years == 5


def test_tax_bridge_fields_are_visible_and_match_waterfall_audit_fields():
    waterfall = _run_project(create_default_tuho_wind1())
    statements = assemble_financial_statements(
        waterfall,
        config=build_croatia_financial_statements_config(project_code="TUHO-WIND-1"),
    )

    assert len(statements.tax_bridge.periods) == len(waterfall.periods)
    for source, bridge in zip(waterfall.periods, statements.tax_bridge.periods):
        assert bridge.tax_depreciation_keur == pytest.approx(source.tax_depreciation_audit_keur)
        assert bridge.fiscal_reintegration_keur == pytest.approx(
            source.fiscal_reintegration_audit_keur
        )
        assert bridge.tax_loss_opening_keur == pytest.approx(source.tax_loss_opening_audit_keur)
        assert bridge.tax_loss_used_keur == pytest.approx(source.tax_loss_used_audit_keur)
        assert bridge.tax_loss_closing_keur == pytest.approx(source.tax_loss_closing_audit_keur)
        assert bridge.cit_accrual_keur == pytest.approx(source.cit_accrual_audit_keur)
        assert bridge.cash_tax_current_period_keur == pytest.approx(
            source.cash_tax_current_period_audit_keur
        )
        assert bridge.cash_tax_excel_style_h2_diagnostic_keur == pytest.approx(
            source.cash_tax_excel_style_h2_diagnostic_keur
        )


def test_loss_carryforward_presentation_is_audit_only_and_does_not_accept_r99():
    waterfall = _run_project(create_default_tuho_wind1())
    statements = assemble_financial_statements(waterfall)

    for pnl_period, tax_period in zip(statements.pnl.periods, statements.tax_bridge.periods):
        assert pnl_period.losses_n_1_keur == pytest.approx(-tax_period.tax_loss_opening_keur)
        assert pnl_period.allocated_losses_keur == pytest.approx(tax_period.tax_loss_used_keur)
        assert pnl_period.losses_n_keur == pytest.approx(-tax_period.tax_loss_closing_keur)
        assert tax_period.r99_runtime_source_accepted is False

    assert statements.tax_bridge.total_cit_accrual_keur == pytest.approx(
        sum(period.tax_keur for period in waterfall.periods)
    )
