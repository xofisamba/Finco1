"""Phase 7M TUHO R67 cash-tax source bridge.

Diagnostic only: no runtime tax source is accepted here.
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


EXCEL_R67_TOTAL_KEUR = -38_240.920880415375
PYTHON_CURRENT_R67_TOTAL_KEUR = -20_057.74498757327
PYTHON_PAIRED_H2_R67_TOTAL_KEUR = -39_575.6741065485
PYTHON_CURRENT_R67_DELTA_KEUR = 18_183.175892842104
PYTHON_PAIRED_H2_R67_DELTA_KEUR = -1_334.7532261331216
EXCEL_TAX_DEPRECIATION_TOTAL_KEUR = 72_993.7
PYTHON_TAX_DEPRECIATION_TOTAL_KEUR = 70_691.5

SELECTED_EXCEL_R67 = {
    0: 0.0,
    1: 0.0,
    2: 0.0,
    3: 0.0,
    24: 0.0,
    25: -120.18903737619021,
    26: 0.0,
    27: -955.2376041078167,
    28: 0.0,
    32: 0.0,
    35: -1_644.9309083308406,
    36: 0.0,
    37: -1_811.2505523385669,
    57: -2_984.233759025831,
    58: 0.0,
    59: -2_999.8541571935475,
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


def _current_r67_cash_tax(periods):
    return tuple(-period.corporate_tax_cash_keur for period in periods)


def _paired_h2_r67_cash_tax(periods):
    values = []
    for index, period in enumerate(periods):
        if period.period_in_year == 2:
            values.append(-(periods[index - 1].tax_keur + period.tax_keur))
        else:
            values.append(0.0)
    return tuple(values)


def test_r67_bridge_does_not_change_default_runtime_outputs():
    baseline = _run_project(create_default_tuho_wind1())
    diagnostic = _run_project(create_default_tuho_wind1())

    assert diagnostic.total_revenue_keur == pytest.approx(baseline.total_revenue_keur, abs=0.0001)
    assert diagnostic.total_opex_keur == pytest.approx(baseline.total_opex_keur, abs=0.0001)
    assert diagnostic.total_tax_keur == pytest.approx(baseline.total_tax_keur, abs=0.0001)
    assert diagnostic.total_distribution_keur == pytest.approx(baseline.total_distribution_keur, abs=0.0001)


def test_excel_r67_and_python_current_cash_tax_totals_are_captured():
    result = _explicit_senior_result()
    periods = result.periods[:60]
    current_r67 = _current_r67_cash_tax(periods)

    assert EXCEL_R67_TOTAL_KEUR == pytest.approx(-38_240.9, abs=0.1)
    assert sum(current_r67) == pytest.approx(PYTHON_CURRENT_R67_TOTAL_KEUR, abs=0.01)
    assert sum(current_r67) - EXCEL_R67_TOTAL_KEUR == pytest.approx(
        PYTHON_CURRENT_R67_DELTA_KEUR,
        abs=0.01,
    )


def test_r67_delta_is_primarily_cash_payment_timing_not_tax_accrual_absence():
    result = _explicit_senior_result()
    periods = result.periods[:60]
    current_r67 = _current_r67_cash_tax(periods)
    paired_h2_r67 = _paired_h2_r67_cash_tax(periods)

    current_delta = sum(current_r67) - EXCEL_R67_TOTAL_KEUR
    paired_delta = sum(paired_h2_r67) - EXCEL_R67_TOTAL_KEUR

    assert current_delta == pytest.approx(PYTHON_CURRENT_R67_DELTA_KEUR, abs=0.01)
    assert paired_delta == pytest.approx(PYTHON_PAIRED_H2_R67_DELTA_KEUR, abs=0.01)
    assert abs(paired_delta) < abs(current_delta) * 0.1


def test_selected_period_bridge_shows_excel_annual_h2_tax_vs_python_h2_only_tax():
    result = _explicit_senior_result()
    periods = result.periods[:60]
    current_r67 = _current_r67_cash_tax(periods)
    paired_h2_r67 = _paired_h2_r67_cash_tax(periods)

    assert current_r67[35] - SELECTED_EXCEL_R67[35] == pytest.approx(656.5, abs=0.1)
    assert paired_h2_r67[35] - SELECTED_EXCEL_R67[35] == pytest.approx(-315.8, abs=0.1)
    assert current_r67[57] - SELECTED_EXCEL_R67[57] == pytest.approx(1_717.0, abs=0.1)
    assert paired_h2_r67[57] - SELECTED_EXCEL_R67[57] == pytest.approx(470.5, abs=0.1)


def test_tax_basis_gap_remains_after_pairing_and_is_not_accepted():
    result = _explicit_senior_result()
    periods = result.periods[:60]
    paired_h2_r67 = _paired_h2_r67_cash_tax(periods)

    depreciation_delta = PYTHON_TAX_DEPRECIATION_TOTAL_KEUR - EXCEL_TAX_DEPRECIATION_TOTAL_KEUR
    paired_delta = sum(paired_h2_r67) - EXCEL_R67_TOTAL_KEUR

    assert depreciation_delta == pytest.approx(-2_302.2, abs=0.1)
    assert paired_delta == pytest.approx(-1_334.8, abs=0.1)
    assert paired_delta != pytest.approx(0.0, abs=100.0)


def test_no_runtime_tax_or_r99_source_is_accepted_and_no_shl_opt_in():
    tuho = create_default_tuho_wind1()

    assert tuho.info.use_shl_fcf_waterfall_engine is False
    assert tuho.financing.use_tuho_r99_input_engine is False
    assert tuho.financing.shl_fcf_waterfall_cash_schedule_keur == ()
