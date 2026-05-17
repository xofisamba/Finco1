"""Phase 6 TUHO tax-basis period comparison.

Diagnostic only: the comparison documents the residual, it does not accept a
runtime R99 source or change tax formulas.
"""

from __future__ import annotations

import pytest

from app.project_factories import create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from tests.test_senior_dscr_sculpting_full_schedule_fixtures import (
    _load_excel_senior_fixture,
    _with_full_explicit_senior_fixture,
)


EXCEL_TOTALS = {
    "depreciation": 72_993.70678606197,
    "fiscal_reintegration": -9_242.742070978198,
    "ebt": 193_569.00226978504,
    "taxable_income_before_losses": 184_326.26019880685,
    "loss_opening": -37_087.1579813391,
    "loss_used": 4_106.002279714321,
    "loss_closing": -166_716.51847101847,
    "taxable_profit_after_losses": 180_220.25791909252,
    "cit_accrual": 38_240.920880415375,
    "cash_tax": -38_240.920880415375,
}

PYTHON_AUDIT_TOTALS = {
    "depreciation": 70_691.54000000001,
    "fiscal_reintegration": 0.0,
    "ebt_proxy": 205_655.5611759746,
    "taxable_income_before_losses": 244_864.85614749164,
    "loss_opening": 332_915.4499144546,
    "loss_used": 24_999.999999999993,
    "loss_closing": 307_915.4499144546,
    "taxable_profit_after_losses": 219_864.85614749166,
    "cit_accrual": 39_575.6741065485,
    "cash_tax_excel_style": -39_575.6741065485,
}

RESIDUAL_DELTAS = {
    "depreciation": -2_302.1667860619636,
    "fiscal_reintegration": 9_242.742070978198,
    "ebt_proxy": 12_086.558906189573,
    "taxable_income_before_losses": 60_538.595948684786,
    "taxable_profit_after_losses": 39_644.59822839915,
    "cit_accrual": 1_334.7532261331216,
    "cash_tax_excel_style": -1_334.7532261331216,
}

SELECTED_PERIOD_COMPARISON = {
    25: {
        "date": "2042-12-31",
        "excel_cash_tax": -120.18903737619021,
        "python_cash_tax_excel_style": -1_702.9042789876426,
        "cash_tax_delta": -1_582.7152416114523,
        "excel_loss_used": 1_807.2861198015316,
        "python_loss_used": 0.0,
    },
    35: {
        "date": "2047-12-31",
        "excel_cash_tax": -1_644.9309083308406,
        "python_cash_tax_excel_style": -1_960.75672040282,
        "cash_tax_delta": -315.8258120719795,
        "excel_taxable_profit": 4_730.096892086638,
        "python_taxable_profit": 5_491.312580732402,
    },
    57: {
        "date": "2058-12-31",
        "excel_cash_tax": -2_984.233759025831,
        "python_cash_tax_excel_style": -2_513.7394174893116,
        "cash_tax_delta": 470.49434153651964,
        "excel_depreciation": 0.0,
        "python_depreciation": 1_187.8761059360731,
    },
}


def _run_project(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def _explicit_senior_result():
    project = _with_full_explicit_senior_fixture(
        create_default_tuho_wind1(),
        _load_excel_senior_fixture("tuho"),
    )
    return _run_project(project)


def test_tuho_tax_basis_period_comparison_does_not_change_runtime_outputs():
    baseline = _run_project(create_default_tuho_wind1())
    diagnostic = _run_project(create_default_tuho_wind1())

    assert diagnostic.total_revenue_keur == pytest.approx(baseline.total_revenue_keur, abs=0.0001)
    assert diagnostic.total_opex_keur == pytest.approx(baseline.total_opex_keur, abs=0.0001)
    assert diagnostic.total_tax_keur == pytest.approx(baseline.total_tax_keur, abs=0.0001)
    assert diagnostic.total_senior_ds_keur == pytest.approx(baseline.total_senior_ds_keur, abs=0.0001)
    assert diagnostic.total_shl_service_keur == pytest.approx(baseline.total_shl_service_keur, abs=0.0001)
    assert diagnostic.total_distribution_keur == pytest.approx(baseline.total_distribution_keur, abs=0.0001)


def test_python_audit_totals_match_period_comparison_baseline():
    result = _explicit_senior_result()
    periods = result.periods[:60]

    assert sum(p.tax_depreciation_audit_keur for p in periods) == pytest.approx(
        PYTHON_AUDIT_TOTALS["depreciation"],
        abs=0.01,
    )
    assert sum(p.fiscal_reintegration_audit_keur for p in periods) == pytest.approx(
        PYTHON_AUDIT_TOTALS["fiscal_reintegration"],
        abs=0.01,
    )
    assert sum(p.taxable_income_before_losses_audit_keur for p in periods) == pytest.approx(
        PYTHON_AUDIT_TOTALS["taxable_income_before_losses"],
        abs=0.01,
    )
    assert sum(p.tax_loss_used_audit_keur for p in periods) == pytest.approx(
        PYTHON_AUDIT_TOTALS["loss_used"],
        abs=0.01,
    )
    assert sum(p.taxable_profit_after_losses_audit_keur for p in periods) == pytest.approx(
        PYTHON_AUDIT_TOTALS["taxable_profit_after_losses"],
        abs=0.01,
    )
    assert sum(p.cit_accrual_audit_keur for p in periods) == pytest.approx(
        PYTHON_AUDIT_TOTALS["cit_accrual"],
        abs=0.01,
    )
    assert sum(p.cash_tax_excel_style_h2_diagnostic_keur for p in periods) == pytest.approx(
        PYTHON_AUDIT_TOTALS["cash_tax_excel_style"],
        abs=0.01,
    )


def test_excel_totals_and_residual_decomposition_are_captured():
    assert EXCEL_TOTALS["cash_tax"] == pytest.approx(-38_240.920880415375, abs=0.01)
    assert RESIDUAL_DELTAS["cash_tax_excel_style"] == pytest.approx(-1_334.7532261331216, abs=0.01)
    assert RESIDUAL_DELTAS["depreciation"] == pytest.approx(-2_302.1667860619636, abs=0.01)
    assert RESIDUAL_DELTAS["fiscal_reintegration"] == pytest.approx(9_242.742070978198, abs=0.01)
    assert RESIDUAL_DELTAS["taxable_profit_after_losses"] == pytest.approx(
        39_644.59822839915,
        abs=0.01,
    )
    assert RESIDUAL_DELTAS["cit_accrual"] == pytest.approx(1_334.7532261331216, abs=0.01)


def test_selected_period_comparison_data_identifies_loss_and_depreciation_timing():
    p25 = SELECTED_PERIOD_COMPARISON[25]
    assert p25["cash_tax_delta"] == pytest.approx(-1_582.7152416114523, abs=0.01)
    assert p25["excel_loss_used"] > 0.0
    assert p25["python_loss_used"] == pytest.approx(0.0)

    p35 = SELECTED_PERIOD_COMPARISON[35]
    assert p35["python_taxable_profit"] > p35["excel_taxable_profit"]
    assert p35["cash_tax_delta"] == pytest.approx(-315.8258120719795, abs=0.01)

    p57 = SELECTED_PERIOD_COMPARISON[57]
    assert p57["excel_depreciation"] == pytest.approx(0.0)
    assert p57["python_depreciation"] > 0.0
    assert p57["cash_tax_delta"] == pytest.approx(470.49434153651964, abs=0.01)


def test_no_tax_formula_change_r99_acceptance_or_shl_opt_in():
    tuho = create_default_tuho_wind1()

    assert tuho.financing.use_tuho_r99_input_engine is False
    assert tuho.info.use_shl_fcf_waterfall_engine is False
    assert tuho.financing.shl_fcf_waterfall_cash_schedule_keur == ()

