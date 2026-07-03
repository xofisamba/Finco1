"""Tax bridge runtime flag tests (Stack Z: TUHO defaults to flag-on)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner


EXCEL_R67_TOTAL_KEUR = -38_240.920880415375
PYTHON_TAX_BRIDGE_R67_DIAGNOSTIC_TOTAL_KEUR = -43_512.3619042104
PYTHON_TAX_BRIDGE_R67_DIAGNOSTIC_DELTA_KEUR = -5_271.441023795022


def _run(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def _key_totals(result):
    return (
        result.total_revenue_keur,
        result.total_opex_keur,
        result.total_ebitda_keur,
        result.total_tax_keur,
        result.total_senior_ds_keur,
        result.total_shl_service_keur,
        result.total_distribution_keur,
    )


def _period_cash_snapshot(result):
    return tuple(
        (
            period.revenue_keur,
            period.opex_keur,
            period.senior_ds_keur,
            period.shl_service_keur,
            period.distribution_keur,
            period.corporate_tax_cash_keur,
            period.r99_fcf_for_distribution_keur,
            period.r102_fcf_for_shl_keur,
        )
        for period in result.periods
    )


def _assert_nested_snapshot_close(left, right, *, abs_tol=0.0001):
    assert len(left) == len(right)
    for left_row, right_row in zip(left, right):
        assert left_row == pytest.approx(right_row, abs=abs_tol)


def _tuho_flag_on_project():
    # Stack Z: factory already has use_tax_bridge_engine=True; kept for clarity.
    return create_default_tuho_wind1()


def _tuho_flag_off_project():
    project = create_default_tuho_wind1()
    return replace(project, info=replace(project.info, use_tax_bridge_engine=False))


def test_tax_bridge_flag_tuho_defaults_true():
    # Stack Z: TUHO factory opts in to tax bridge engine; Oborovo remains False.
    assert create_default_tuho_wind1().info.use_tax_bridge_engine is True
    assert create_default_oborovo().info.use_tax_bridge_engine is False


def test_tuho_default_is_flag_on_and_deterministic():
    # Stack Z: two runs of the default (flag-on) project produce bit-identical results.
    run_a = _run(create_default_tuho_wind1())
    run_b = _run(create_default_tuho_wind1())

    assert _key_totals(run_a) == pytest.approx(_key_totals(run_b), abs=0.0001)
    _assert_nested_snapshot_close(
        _period_cash_snapshot(run_a),
        _period_cash_snapshot(run_b),
    )


def test_oborovo_flag_off_is_bit_identical_with_default_project():
    baseline = _run(create_default_oborovo())
    flag_off = _run(create_default_oborovo())

    assert _key_totals(flag_off) == pytest.approx(_key_totals(baseline), abs=0.0001)
    _assert_nested_snapshot_close(
        _period_cash_snapshot(flag_off),
        _period_cash_snapshot(baseline),
    )


def test_oborovo_flag_on_is_rejected():
    project = create_default_oborovo()
    project = replace(project, info=replace(project.info, use_tax_bridge_engine=True))

    with pytest.raises(ValueError, match="Tax bridge runtime engine.*TUHO-WIND-1"):
        _run(project)


def test_tuho_flag_on_uses_excel_style_h2_cash_tax_as_runtime_cash_tax():
    result = _run(_tuho_flag_on_project())

    for period in result.periods:
        if period.period_in_year == 1:
            assert period.corporate_tax_cash_keur == pytest.approx(0.0)
        else:
            assert period.corporate_tax_cash_keur == pytest.approx(
                -period.cash_tax_excel_style_h2_diagnostic_keur,
                abs=0.0001,
            )
        assert period.cash_tax_current_period_audit_keur == pytest.approx(
            period.corporate_tax_cash_keur,
            abs=0.0001,
        )
        assert period.cf_after_tax_keur == pytest.approx(
            period.ebitda_keur - period.corporate_tax_cash_keur,
            abs=0.0001,
        )


def test_tuho_flag_on_measures_accrued_cit_and_r67_against_excel():
    result = _run(_tuho_flag_on_project())
    accrued_cit_total = sum(period.cit_accrual_audit_keur for period in result.periods)
    runtime_cash_tax_total = sum(period.corporate_tax_cash_keur for period in result.periods)
    diagnostic_r67_total = sum(
        period.cash_tax_excel_style_h2_diagnostic_keur for period in result.periods
    )

    assert accrued_cit_total == pytest.approx(result.total_tax_keur, abs=0.0001)
    assert diagnostic_r67_total == pytest.approx(
        PYTHON_TAX_BRIDGE_R67_DIAGNOSTIC_TOTAL_KEUR,
        abs=0.01,
    )
    assert runtime_cash_tax_total == pytest.approx(
        -PYTHON_TAX_BRIDGE_R67_DIAGNOSTIC_TOTAL_KEUR,
        abs=0.01,
    )
    assert diagnostic_r67_total - EXCEL_R67_TOTAL_KEUR == pytest.approx(
        PYTHON_TAX_BRIDGE_R67_DIAGNOSTIC_DELTA_KEUR,
        abs=0.01,
    )


def test_tuho_flag_on_measures_r99_r102_impact_but_does_not_accept_source():
    legacy = _run(_tuho_flag_off_project())
    flag_on = _run(_tuho_flag_on_project())

    legacy_r99_total = sum(period.r99_fcf_for_distribution_keur for period in legacy.periods)
    flag_on_r99_total = sum(period.r99_fcf_for_distribution_keur for period in flag_on.periods)
    assert flag_on_r99_total != pytest.approx(legacy_r99_total, abs=0.01)

    for period in flag_on.periods:
        assert period.r99_fcf_for_distribution_keur == pytest.approx(
            period.r102_fcf_for_shl_keur,
            abs=0.0001,
        )

    assert _tuho_flag_on_project().financing.use_tuho_r99_input_engine is False
    assert _tuho_flag_on_project().info.use_shl_fcf_waterfall_engine is False


def test_tuho_flag_on_does_not_drift_unrelated_operating_engines():
    legacy = _run(_tuho_flag_off_project())
    flag_on = _run(_tuho_flag_on_project())

    assert flag_on.total_revenue_keur == pytest.approx(legacy.total_revenue_keur, abs=0.0001)
    assert flag_on.total_opex_keur == pytest.approx(legacy.total_opex_keur, abs=0.0001)
    assert flag_on.total_ebitda_keur == pytest.approx(legacy.total_ebitda_keur, abs=0.0001)
    assert flag_on.total_tax_keur != pytest.approx(legacy.total_tax_keur, abs=0.01)
    assert flag_on.total_senior_ds_keur == pytest.approx(
        legacy.total_senior_ds_keur,
        abs=0.0001,
    )
    assert flag_on.total_shl_service_keur == pytest.approx(
        legacy.total_shl_service_keur,
        abs=0.0001,
    )
