"""Phase 6 runtime visibility for audit-only tax-basis fields."""

from __future__ import annotations

from dataclasses import fields

import pytest

from app.project_factories import create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.waterfall.waterfall_engine import WaterfallPeriod


NEW_TAX_AUDIT_FIELDS = (
    "tax_depreciation_audit_keur",
    "fiscal_reintegration_audit_keur",
    "taxable_income_before_losses_audit_keur",
    "tax_loss_opening_audit_keur",
    "tax_loss_used_audit_keur",
    "tax_loss_closing_audit_keur",
    "taxable_profit_after_losses_audit_keur",
    "cit_accrual_audit_keur",
    "cash_tax_current_period_audit_keur",
    "cash_tax_excel_style_h2_diagnostic_keur",
)


def _run_project(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def test_tax_audit_fields_do_not_change_default_runtime_totals():
    baseline = _run_project(create_default_tuho_wind1())
    diagnostic = _run_project(create_default_tuho_wind1())

    assert diagnostic.total_revenue_keur == pytest.approx(baseline.total_revenue_keur, abs=0.0001)
    assert diagnostic.total_opex_keur == pytest.approx(baseline.total_opex_keur, abs=0.0001)
    assert diagnostic.total_ebitda_keur == pytest.approx(baseline.total_ebitda_keur, abs=0.0001)
    assert diagnostic.total_tax_keur == pytest.approx(baseline.total_tax_keur, abs=0.0001)
    assert diagnostic.total_senior_ds_keur == pytest.approx(baseline.total_senior_ds_keur, abs=0.0001)
    assert diagnostic.total_shl_service_keur == pytest.approx(baseline.total_shl_service_keur, abs=0.0001)
    assert diagnostic.total_distribution_keur == pytest.approx(baseline.total_distribution_keur, abs=0.0001)


def test_tax_audit_fields_exist_on_waterfall_period():
    period_fields = {field.name for field in fields(WaterfallPeriod)}

    for field_name in NEW_TAX_AUDIT_FIELDS:
        assert field_name in period_fields
    assert "r67_excel_style_cash_tax_diagnostic_keur" in period_fields


def test_tax_audit_fields_are_populated_from_existing_runtime_tax_values():
    result = _run_project(create_default_tuho_wind1())

    for period in result.periods:
        assert period.tax_depreciation_audit_keur == pytest.approx(period.depreciation_keur)
        assert period.tax_loss_opening_audit_keur >= 0.0
        assert period.tax_loss_used_audit_keur >= 0.0
        assert period.tax_loss_closing_audit_keur >= 0.0
        assert period.tax_loss_used_audit_keur <= period.tax_loss_opening_audit_keur + 0.0001
        assert period.taxable_profit_after_losses_audit_keur == pytest.approx(
            period.tax_keur / 0.18 if period.tax_keur else 0.0,
            abs=0.0001,
        )
        assert period.cit_accrual_audit_keur == pytest.approx(period.tax_keur)
        assert period.cash_tax_current_period_audit_keur == pytest.approx(
            period.corporate_tax_cash_keur
        )


def test_existing_r67_excel_style_diagnostic_alias_still_matches():
    result = _run_project(create_default_tuho_wind1())

    for period in result.periods:
        assert period.cash_tax_excel_style_h2_diagnostic_keur == pytest.approx(
            period.r67_excel_style_cash_tax_diagnostic_keur
        )
        if period.period_in_year == 1:
            assert period.cash_tax_excel_style_h2_diagnostic_keur == pytest.approx(0.0)
        else:
            assert period.cash_tax_excel_style_h2_diagnostic_keur <= 0.0


def test_tax_audit_fields_do_not_feed_r99_chain_or_current_cash_tax():
    result = _run_project(create_default_tuho_wind1())

    for period in result.periods:
        expected_r69 = (
            period.revenue_keur
            - period.opex_keur
            - period.corporate_tax_cash_keur
        )
        diagnostic_r69 = (
            period.revenue_keur
            - period.opex_keur
            + period.cash_tax_excel_style_h2_diagnostic_keur
        )

        assert period.r69_fcf_banks_keur == pytest.approx(expected_r69)
        if diagnostic_r69 != pytest.approx(expected_r69):
            assert period.r69_fcf_banks_keur != pytest.approx(diagnostic_r69)


def test_tax_audit_fields_do_not_accept_r99_or_enable_shl_fcf_waterfall():
    tuho = create_default_tuho_wind1()

    assert tuho.financing.use_tuho_r99_input_engine is False
    assert tuho.info.use_shl_fcf_waterfall_engine is False
    assert tuho.financing.shl_fcf_waterfall_cash_schedule_keur == ()
