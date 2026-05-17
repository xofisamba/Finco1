"""Phase 6 tax bridge consumption of offline interest limitation."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner


EXCEL_TUHO_R34_TOTAL_KEUR = -9_242.742070978198
EXCEL_R67_TOTAL_KEUR = -38_240.920880415375
LEGACY_RUNTIME_R67_CASH_TAX_KEUR = -20_140.22414240874
FLAG_ON_R67_CASH_TAX_KEUR = -32_091.92156395798


def _run(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def _tuho_flag_on_project():
    project = create_default_tuho_wind1()
    return replace(project, info=replace(project.info, use_tax_bridge_engine=True))


def _oborovo_flag_on_project():
    project = create_default_oborovo()
    return replace(project, info=replace(project.info, use_tax_bridge_engine=True))


def _key_runtime_totals(result):
    return (
        result.total_revenue_keur,
        result.total_opex_keur,
        result.total_ebitda_keur,
        result.total_senior_ds_keur,
        result.total_shl_service_keur,
        result.total_distribution_keur,
    )


def test_flag_off_tuho_and_oborovo_are_unchanged():
    tuho_a = _run(create_default_tuho_wind1())
    tuho_b = _run(create_default_tuho_wind1())
    oborovo_a = _run(create_default_oborovo())
    oborovo_b = _run(create_default_oborovo())

    assert _key_runtime_totals(tuho_b) == pytest.approx(_key_runtime_totals(tuho_a), abs=0.0001)
    assert tuho_b.total_tax_keur == pytest.approx(tuho_a.total_tax_keur, abs=0.0001)
    assert _key_runtime_totals(oborovo_b) == pytest.approx(
        _key_runtime_totals(oborovo_a),
        abs=0.0001,
    )
    assert oborovo_b.total_tax_keur == pytest.approx(oborovo_a.total_tax_keur, abs=0.0001)


def test_tuho_flag_on_consumes_interest_limitation_r34():
    result = _run(_tuho_flag_on_project())

    cumulative_r34 = sum(period.fiscal_reintegration_audit_keur for period in result.periods)

    assert cumulative_r34 == pytest.approx(EXCEL_TUHO_R34_TOTAL_KEUR, abs=0.01)
    assert any(period.fiscal_reintegration_audit_keur < 0.0 for period in result.periods)
    assert result.periods[-1].fiscal_reintegration_audit_keur == pytest.approx(0.0)


def test_tuho_flag_on_moves_runtime_cash_tax_toward_excel_r67():
    legacy = _run(create_default_tuho_wind1())
    flag_on = _run(_tuho_flag_on_project())

    legacy_r67_cash_tax = -sum(period.corporate_tax_cash_keur for period in legacy.periods)
    flag_on_r67_cash_tax = -sum(period.corporate_tax_cash_keur for period in flag_on.periods)

    assert legacy_r67_cash_tax == pytest.approx(LEGACY_RUNTIME_R67_CASH_TAX_KEUR, abs=0.01)
    assert flag_on_r67_cash_tax == pytest.approx(FLAG_ON_R67_CASH_TAX_KEUR, abs=0.01)
    assert abs(flag_on_r67_cash_tax - EXCEL_R67_TOTAL_KEUR) < abs(
        legacy_r67_cash_tax - EXCEL_R67_TOTAL_KEUR
    )


def test_tuho_flag_on_measures_r99_r102_but_does_not_accept_runtime_source():
    legacy = _run(create_default_tuho_wind1())
    flag_on = _run(_tuho_flag_on_project())

    legacy_r99 = sum(period.r99_fcf_for_distribution_keur for period in legacy.periods)
    flag_on_r99 = sum(period.r99_fcf_for_distribution_keur for period in flag_on.periods)

    assert flag_on_r99 != pytest.approx(legacy_r99, abs=0.01)
    assert _tuho_flag_on_project().financing.use_tuho_r99_input_engine is False
    assert _tuho_flag_on_project().info.use_shl_fcf_waterfall_engine is False
    for period in flag_on.periods:
        assert period.r99_fcf_for_distribution_keur == pytest.approx(
            period.r102_fcf_for_shl_keur,
            abs=0.0001,
        )


def test_oborovo_flag_on_remains_guarded():
    with pytest.raises(ValueError, match="Tax bridge runtime engine.*TUHO-WIND-1"):
        _run(_oborovo_flag_on_project())


def test_tuho_flag_on_does_not_drift_unrelated_runtime_engines():
    legacy = _run(create_default_tuho_wind1())
    flag_on = _run(_tuho_flag_on_project())

    assert _key_runtime_totals(flag_on) == pytest.approx(_key_runtime_totals(legacy), abs=0.0001)
