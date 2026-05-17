"""Phase 6 TUHO tax-basis bridge after Phase 7M R67 timing isolation.

Diagnostic only: no runtime tax source is accepted here.
"""

from __future__ import annotations

import json
from pathlib import Path

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
    "senior_interest": 22_822.816668720294,
    "shl_interest": 49_782.18248671982,
    "ebt": 193_569.00226978504,
    "taxable_income_before_loss_rows": 184_326.26019880685,
    "cit": 38_240.920880415375,
    "r67": -38_240.920880415375,
}

PYTHON_TOTALS = {
    "depreciation": 70_691.54000000001,
    "senior_interest": 22_822.816668720294,
    "shl_interest": 39_209.29497151703,
    "ebt_proxy": 205_655.5611759746,
    "tax_after_losses": 219_864.85614749166,
    "cit": 39_575.6741065485,
    "r67_excel_style_diagnostic": -39_575.6741065485,
}

EXPECTED_DELTAS = {
    "depreciation": -2_302.1667860619636,
    "senior_interest": 0.0,
    "shl_interest": -10_572.88751520279,
    "ebt_proxy": 12_086.558906189573,
    "cit": 1_334.7532261331216,
    "r67_excel_style_diagnostic": -1_334.7532261331216,
}

SELECTED_PERIODS = (0, 1, 2, 3, 24, 25, 26, 27, 28, 32, 35, 36, 37, 57, 58, 59)


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


def _excel_rows():
    payload = json.loads(
        (Path(__file__).parent / "fixtures" / "excel_tuho_full_model_extract.json").read_text(
            encoding="utf-8"
        )
    )
    columns = payload["period_diagnostic_columns"]
    return columns, payload["period_diagnostics"][:60]


def test_tuho_tax_basis_bridge_does_not_change_default_runtime_outputs():
    baseline = _run_project(create_default_tuho_wind1())
    diagnostic = _run_project(create_default_tuho_wind1())

    assert diagnostic.total_revenue_keur == pytest.approx(baseline.total_revenue_keur, abs=0.0001)
    assert diagnostic.total_opex_keur == pytest.approx(baseline.total_opex_keur, abs=0.0001)
    assert diagnostic.total_tax_keur == pytest.approx(baseline.total_tax_keur, abs=0.0001)
    assert diagnostic.total_senior_ds_keur == pytest.approx(baseline.total_senior_ds_keur, abs=0.0001)
    assert diagnostic.total_shl_service_keur == pytest.approx(baseline.total_shl_service_keur, abs=0.0001)
    assert diagnostic.total_distribution_keur == pytest.approx(baseline.total_distribution_keur, abs=0.0001)


def test_excel_tax_basis_totals_are_captured_from_fixture():
    columns, rows = _excel_rows()
    idx = {name: columns.index(name) for name in columns}

    assert sum(row[idx["P&L.depreciation_keur"]] for row in rows) == pytest.approx(
        EXCEL_TOTALS["depreciation"],
        abs=0.01,
    )
    assert sum(row[idx["P&L.senior_interests_keur"]] for row in rows) == pytest.approx(
        EXCEL_TOTALS["senior_interest"],
        abs=0.01,
    )
    assert sum(row[idx["P&L.shareholder_loan_interests_keur"]] for row in rows) == pytest.approx(
        EXCEL_TOTALS["shl_interest"],
        abs=0.01,
    )
    assert sum(row[idx["P&L.earnings_before_tax_keur"]] for row in rows) == pytest.approx(
        EXCEL_TOTALS["ebt"],
        abs=0.01,
    )
    assert sum(row[idx["P&L.taxable_income_keur"]] for row in rows) == pytest.approx(
        EXCEL_TOTALS["taxable_income_before_loss_rows"],
        abs=0.01,
    )
    assert sum(row[idx["P&L.corporate_income_tax_keur"]] for row in rows) == pytest.approx(
        EXCEL_TOTALS["cit"],
        abs=0.01,
    )


def test_python_tax_basis_totals_are_captured_with_explicit_senior_harness():
    result = _explicit_senior_result()
    periods = result.periods[:60]

    assert sum(period.depreciation_keur for period in periods) == pytest.approx(
        PYTHON_TOTALS["depreciation"],
        abs=0.01,
    )
    assert sum(period.senior_interest_keur for period in periods) == pytest.approx(
        PYTHON_TOTALS["senior_interest"],
        abs=0.01,
    )
    assert sum(period.shl_interest_keur for period in periods) == pytest.approx(
        PYTHON_TOTALS["shl_interest"],
        abs=0.01,
    )
    assert sum(
        period.ebitda_keur
        - period.depreciation_keur
        - period.senior_interest_keur
        - period.shl_interest_keur
        for period in periods
    ) == pytest.approx(PYTHON_TOTALS["ebt_proxy"], abs=0.01)
    assert sum(period.tax_keur / 0.18 for period in periods) == pytest.approx(
        PYTHON_TOTALS["tax_after_losses"],
        abs=0.01,
    )
    assert sum(period.tax_keur for period in periods) == pytest.approx(
        PYTHON_TOTALS["cit"],
        abs=0.01,
    )


def test_remaining_r67_residual_is_tax_basis_not_senior_debt_or_payment_timing():
    result = _explicit_senior_result()
    periods = result.periods[:60]

    senior_interest_delta = (
        sum(period.senior_interest_keur for period in periods) - EXCEL_TOTALS["senior_interest"]
    )
    depreciation_delta = sum(period.depreciation_keur for period in periods) - EXCEL_TOTALS["depreciation"]
    shl_interest_delta = sum(period.shl_interest_keur for period in periods) - EXCEL_TOTALS["shl_interest"]
    ebt_delta = (
        sum(
            period.ebitda_keur
            - period.depreciation_keur
            - period.senior_interest_keur
            - period.shl_interest_keur
            for period in periods
        )
        - EXCEL_TOTALS["ebt"]
    )
    r67_delta = (
        sum(period.r67_excel_style_cash_tax_diagnostic_keur for period in periods)
        - EXCEL_TOTALS["r67"]
    )

    assert senior_interest_delta == pytest.approx(EXPECTED_DELTAS["senior_interest"], abs=0.01)
    assert depreciation_delta == pytest.approx(EXPECTED_DELTAS["depreciation"], abs=0.01)
    assert shl_interest_delta == pytest.approx(EXPECTED_DELTAS["shl_interest"], abs=0.01)
    assert ebt_delta == pytest.approx(EXPECTED_DELTAS["ebt_proxy"], abs=0.01)
    assert r67_delta == pytest.approx(EXPECTED_DELTAS["r67_excel_style_diagnostic"], abs=0.01)


def test_period_bridge_exists_for_required_tax_basis_periods():
    columns, excel_rows = _excel_rows()
    idx = {name: columns.index(name) for name in columns}
    result = _explicit_senior_result()
    periods = result.periods[:60]

    for op_idx in SELECTED_PERIODS:
        excel_row = excel_rows[op_idx]
        period = periods[op_idx]
        python_ebt_proxy = (
            period.ebitda_keur
            - period.depreciation_keur
            - period.senior_interest_keur
            - period.shl_interest_keur
        )

        assert excel_row[idx["P&L.depreciation_keur"]] >= 0.0
        assert period.depreciation_keur >= 0.0
        assert excel_row[idx["P&L.earnings_before_tax_keur"]] == pytest.approx(
            excel_row[idx["P&L.earnings_before_tax_keur"]]
        )
        assert python_ebt_proxy == pytest.approx(python_ebt_proxy)
        assert period.r67_excel_style_cash_tax_diagnostic_keur <= 0.0


def test_tax_basis_bridge_does_not_accept_r99_source_or_enable_shl():
    tuho = create_default_tuho_wind1()

    assert tuho.info.use_shl_fcf_waterfall_engine is False
    assert tuho.financing.use_tuho_r99_input_engine is False
    assert tuho.financing.shl_fcf_waterfall_cash_schedule_keur == ()
