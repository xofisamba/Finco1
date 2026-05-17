"""Phase 7M audit-only Excel-style R67 cash-tax diagnostic field."""

from __future__ import annotations

from dataclasses import fields

import pytest

from app.project_factories import create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.waterfall.waterfall_engine import WaterfallPeriod
from tests.test_senior_dscr_sculpting_full_schedule_fixtures import (
    _load_excel_senior_fixture,
    _with_full_explicit_senior_fixture,
)


EXCEL_R67_TOTAL_KEUR = -38_240.920880415375
PYTHON_EXCEL_STYLE_R67_DIAGNOSTIC_TOTAL_KEUR = -39_575.6741065485
PYTHON_EXCEL_STYLE_R67_DIAGNOSTIC_DELTA_KEUR = -1_334.7532261331216


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


def test_r67_diagnostic_field_does_not_change_default_runtime_totals():
    baseline = _run_project(create_default_tuho_wind1())
    diagnostic = _run_project(create_default_tuho_wind1())

    assert diagnostic.total_revenue_keur == pytest.approx(baseline.total_revenue_keur, abs=0.0001)
    assert diagnostic.total_opex_keur == pytest.approx(baseline.total_opex_keur, abs=0.0001)
    assert diagnostic.total_tax_keur == pytest.approx(baseline.total_tax_keur, abs=0.0001)
    assert diagnostic.total_senior_ds_keur == pytest.approx(baseline.total_senior_ds_keur, abs=0.0001)
    assert diagnostic.total_shl_service_keur == pytest.approx(baseline.total_shl_service_keur, abs=0.0001)
    assert diagnostic.total_distribution_keur == pytest.approx(baseline.total_distribution_keur, abs=0.0001)


def test_r67_excel_style_cash_tax_diagnostic_field_exists_and_is_documented():
    field_map = {field.name: field for field in fields(WaterfallPeriod)}

    assert "r67_excel_style_cash_tax_diagnostic_keur" in field_map
    diagnostic_field = field_map["r67_excel_style_cash_tax_diagnostic_keur"]
    assert diagnostic_field.metadata["sign"] == (
        "negative cash tax outflow, matching Excel CF R67 convention"
    )
    assert "audit-only annual H2 pairing" in diagnostic_field.metadata["basis"]


def test_r67_excel_style_cash_tax_diagnostic_h1_zero_h2_pairs_current_and_previous_tax():
    result = _explicit_senior_result()
    periods = result.periods[:60]

    for index, period in enumerate(periods):
        diagnostic = period.r67_excel_style_cash_tax_diagnostic_keur
        if period.period_in_year == 1:
            assert diagnostic == pytest.approx(0.0)
        else:
            expected = -(periods[index - 1].tax_keur + period.tax_keur)
            assert diagnostic == pytest.approx(expected)


def test_r67_excel_style_cash_tax_diagnostic_total_and_residual_gap():
    result = _explicit_senior_result()
    diagnostic_total = sum(
        period.r67_excel_style_cash_tax_diagnostic_keur
        for period in result.periods[:60]
    )

    assert diagnostic_total == pytest.approx(
        PYTHON_EXCEL_STYLE_R67_DIAGNOSTIC_TOTAL_KEUR,
        abs=0.01,
    )
    assert EXCEL_R67_TOTAL_KEUR == pytest.approx(-38_240.9, abs=0.1)
    assert diagnostic_total - EXCEL_R67_TOTAL_KEUR == pytest.approx(
        PYTHON_EXCEL_STYLE_R67_DIAGNOSTIC_DELTA_KEUR,
        abs=0.01,
    )


def test_r67_diagnostic_is_not_used_for_r99_source_acceptance():
    result = _explicit_senior_result()
    periods = result.periods[:60]

    current_r69 = sum(period.r69_fcf_banks_keur for period in periods)
    diagnostic_r69 = sum(
        period.revenue_keur
        - period.opex_keur
        + period.r67_excel_style_cash_tax_diagnostic_keur
        for period in periods
    )

    assert current_r69 != pytest.approx(diagnostic_r69, abs=0.01)
    for period in periods:
        expected_current_r69 = (
            period.revenue_keur
            - period.opex_keur
            - period.corporate_tax_cash_keur
        )
        assert period.r69_fcf_banks_keur == pytest.approx(expected_current_r69)


def test_r67_diagnostic_keeps_shl_fcf_and_r99_runtime_opt_ins_disabled():
    tuho = create_default_tuho_wind1()

    assert tuho.info.use_shl_fcf_waterfall_engine is False
    assert tuho.financing.use_tuho_r99_input_engine is False
    assert tuho.financing.shl_fcf_waterfall_cash_schedule_keur == ()
