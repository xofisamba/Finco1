"""Tax bridge flag-on consumption of rolling loss carry-forward."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner


EXCEL_R67_TOTAL_KEUR = -38_240.920880415375
LEGACY_RUNTIME_R67_CASH_TAX_KEUR = -20_140.22414240874
FLAG_ON_R67_WITH_R34_AND_ROLLING_LOSSES_KEUR = -36_091.61517762715
TUHO_R34_TOTAL_KEUR = -9_242.742070978198


def _run(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def _tuho_flag_on_project():
    project = create_default_tuho_wind1()
    return replace(project, info=replace(project.info, use_tax_bridge_engine=True))


def test_flag_off_tuho_and_oborovo_remain_legacy():
    tuho_a = _run(create_default_tuho_wind1())
    tuho_b = _run(create_default_tuho_wind1())
    oborovo_a = _run(create_default_oborovo())
    oborovo_b = _run(create_default_oborovo())

    assert tuho_b.total_tax_keur == pytest.approx(tuho_a.total_tax_keur, abs=0.0001)
    assert oborovo_b.total_tax_keur == pytest.approx(oborovo_a.total_tax_keur, abs=0.0001)
    assert sum(p.corporate_tax_cash_keur for p in tuho_b.periods) == pytest.approx(
        sum(p.corporate_tax_cash_keur for p in tuho_a.periods),
        abs=0.0001,
    )


def test_tuho_flag_on_uses_rolling_loss_carryforward_audit_rows():
    result = _run(_tuho_flag_on_project())

    assert sum(p.fiscal_reintegration_audit_keur for p in result.periods) == pytest.approx(
        TUHO_R34_TOTAL_KEUR,
        abs=0.01,
    )
    assert result.periods[0].tax_loss_opening_audit_keur == pytest.approx(25_000.0)
    assert any(p.taxable_income_before_losses_audit_keur < 0.0 for p in result.periods)
    assert any(p.tax_loss_closing_audit_keur > p.tax_loss_opening_audit_keur for p in result.periods)
    assert all(p.tax_loss_used_audit_keur >= 0.0 for p in result.periods)
    assert all(p.taxable_profit_after_losses_audit_keur >= 0.0 for p in result.periods)


def test_tuho_flag_on_r67_moves_closer_to_excel_after_rolling_losses():
    legacy = _run(create_default_tuho_wind1())
    flag_on = _run(_tuho_flag_on_project())

    legacy_r67_cash_tax = -sum(p.corporate_tax_cash_keur for p in legacy.periods)
    flag_on_r67_cash_tax = -sum(p.corporate_tax_cash_keur for p in flag_on.periods)

    assert legacy_r67_cash_tax == pytest.approx(LEGACY_RUNTIME_R67_CASH_TAX_KEUR, abs=0.01)
    assert flag_on_r67_cash_tax == pytest.approx(
        FLAG_ON_R67_WITH_R34_AND_ROLLING_LOSSES_KEUR,
        abs=0.01,
    )
    assert abs(flag_on_r67_cash_tax - EXCEL_R67_TOTAL_KEUR) < abs(
        legacy_r67_cash_tax - EXCEL_R67_TOTAL_KEUR
    )


def test_r99_r102_remain_audit_only_after_loss_carryforward_change():
    legacy = _run(create_default_tuho_wind1())
    flag_on = _run(_tuho_flag_on_project())

    assert sum(p.r99_fcf_for_distribution_keur for p in flag_on.periods) != pytest.approx(
        sum(p.r99_fcf_for_distribution_keur for p in legacy.periods),
        abs=0.01,
    )
    for period in flag_on.periods:
        assert period.r99_fcf_for_distribution_keur == pytest.approx(
            period.r102_fcf_for_shl_keur,
            abs=0.0001,
        )

    project = _tuho_flag_on_project()
    assert project.financing.use_tuho_r99_input_engine is False
    assert project.info.use_shl_fcf_waterfall_engine is False


def test_oborovo_flag_on_still_raises_value_error():
    project = create_default_oborovo()
    project = replace(project, info=replace(project.info, use_tax_bridge_engine=True))

    with pytest.raises(ValueError, match="Tax bridge runtime engine.*TUHO-WIND-1"):
        _run(project)


def test_no_project_factory_opt_in_or_unrelated_runtime_drift():
    assert create_default_tuho_wind1().info.use_tax_bridge_engine is False
    assert create_default_oborovo().info.use_tax_bridge_engine is False

    legacy = _run(create_default_tuho_wind1())
    flag_on = _run(_tuho_flag_on_project())

    assert flag_on.total_revenue_keur == pytest.approx(legacy.total_revenue_keur, abs=0.0001)
    assert flag_on.total_opex_keur == pytest.approx(legacy.total_opex_keur, abs=0.0001)
    assert flag_on.total_senior_ds_keur == pytest.approx(legacy.total_senior_ds_keur, abs=0.0001)
    assert flag_on.total_shl_service_keur == pytest.approx(
        legacy.total_shl_service_keur,
        abs=0.0001,
    )
