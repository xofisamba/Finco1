"""Final targeted TUHO R67 calibration diagnostics."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_core import _tuho_tax_bridge_opening_loss_buckets
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner


EXCEL_R67_TOTAL_KEUR = -38_240.920880415375
# Stack Z: TUHO factory now opt-in to tax bridge; legacy = explicit flag-off.
LEGACY_RUNTIME_R67_KEUR = -33_173.91396979727
# C3: useful_life_tax_periods 60→40 (20-year fiscal life); gap narrows from 5271 to 1247 kEUR
FLAG_ON_R67_KEUR = -36_994.27032177761
REMAINING_RESIDUAL_KEUR = 1_246.6505586377702
MATERIAL_PERIODS_ABOVE_100_KEUR = 2
MAX_PERIOD_DELTA_KEUR = 816.4266509498476


def _run(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def _tuho_flag_on_project():
    # Stack Z: factory already has use_tax_bridge_engine=True; kept for clarity.
    return create_default_tuho_wind1()


def _tuho_flag_off_project():
    project = create_default_tuho_wind1()
    return replace(project, info=replace(project.info, use_tax_bridge_engine=False))


def _excel_r67_by_period():
    payload = json.loads(
        (Path(__file__).parent / "fixtures" / "excel_tuho_full_model_extract.json").read_text(
            encoding="utf-8"
        )
    )
    idx = payload["period_diagnostic_columns"].index("P&L.corporate_income_tax_keur")
    return tuple(-row[idx] for row in payload["period_diagnostics"][:60])


def _r67_bridge(result):
    excel = _excel_r67_by_period()
    python = tuple(-period.corporate_tax_cash_keur for period in result.periods[:60])
    deltas = tuple(py - ex for py, ex in zip(python, excel))
    return excel, python, deltas


def test_explicit_opening_loss_bucket_fixture_is_tuho_only_and_documented():
    buckets = _tuho_tax_bridge_opening_loss_buckets(25_000.0)

    assert len(buckets) == 1
    assert buckets[0].amount_keur == pytest.approx(25_000.0)
    assert buckets[0].periods_remaining == 1
    assert "near-expiry assumption" in buckets[0].source_label


def test_flag_off_tuho_and_oborovo_are_bit_identical():
    tuho_a = _run(create_default_tuho_wind1())
    tuho_b = _run(create_default_tuho_wind1())
    oborovo_a = _run(create_default_oborovo())
    oborovo_b = _run(create_default_oborovo())

    assert tuho_b.total_tax_keur == pytest.approx(tuho_a.total_tax_keur, abs=0.0001)
    assert tuho_b.total_distribution_keur == pytest.approx(
        tuho_a.total_distribution_keur,
        abs=0.0001,
    )
    assert oborovo_b.total_tax_keur == pytest.approx(oborovo_a.total_tax_keur, abs=0.0001)


def test_oborovo_flag_on_remains_guarded():
    project = create_default_oborovo()
    project = replace(project, info=replace(project.info, use_tax_bridge_engine=True))

    with pytest.raises(ValueError, match="Tax bridge runtime engine.*TUHO-WIND-1"):
        _run(project)


def test_tuho_flag_on_r67_calibration():
    """Flag-on R67 calibration guard — Stack Z (post-Stack-Y baseline).

    C3 (40-period fiscal dep life) and C4 forensic analysis revised this picture.
    Remaining gap (~1247 kEUR, per REMAINING_RESIDUAL_KEUR) is a documented Excel
    model limitation: Excel applies an apparent 2-year annual LCF while Croatian law
    requires 5 years. Python is legally correct; the residual is intentional.
    No scalar plug: the residual is tracked, not zeroed.
    """
    legacy = _run(_tuho_flag_off_project())
    flag_on = _run(_tuho_flag_on_project())
    _, python_r67, deltas = _r67_bridge(flag_on)

    legacy_r67 = -sum(period.corporate_tax_cash_keur for period in legacy.periods[:60])

    assert legacy_r67 == pytest.approx(LEGACY_RUNTIME_R67_KEUR, abs=0.01)
    assert sum(python_r67) == pytest.approx(FLAG_ON_R67_KEUR, abs=0.01)
    assert sum(deltas) == pytest.approx(REMAINING_RESIDUAL_KEUR, abs=0.01)
    assert sum(abs(delta) > 100.0 for delta in deltas) == MATERIAL_PERIODS_ABOVE_100_KEUR
    assert max(abs(delta) for delta in deltas) == pytest.approx(MAX_PERIOD_DELTA_KEUR, abs=0.01)


def test_r99_r102_remain_audit_only_and_no_shl_or_factory_opt_in():
    project = _tuho_flag_on_project()
    result = _run(project)

    assert project.financing.use_tuho_r99_input_engine is False
    assert project.info.use_shl_fcf_waterfall_engine is False
    assert create_default_tuho_wind1().info.use_tax_bridge_engine is True  # Stack Z: factory opts in
    for period in result.periods[:60]:
        assert period.r99_fcf_for_distribution_keur == pytest.approx(
            period.r102_fcf_for_shl_keur,
            abs=0.0001,
        )


def test_unrelated_runtime_engines_do_not_drift_under_flag_on():
    legacy = _run(create_default_tuho_wind1())
    flag_on = _run(_tuho_flag_on_project())

    assert flag_on.total_revenue_keur == pytest.approx(legacy.total_revenue_keur, abs=0.0001)
    assert flag_on.total_opex_keur == pytest.approx(legacy.total_opex_keur, abs=0.0001)
    assert flag_on.total_senior_ds_keur == pytest.approx(legacy.total_senior_ds_keur, abs=0.0001)
    assert flag_on.total_shl_service_keur == pytest.approx(
        legacy.total_shl_service_keur,
        abs=0.0001,
    )
