from dataclasses import replace

import pytest

from app.project_factories import (
    create_default_oborovo,
    create_default_solar_project,
    create_default_tuho_wind1,
    create_default_tuho_wind1_legacy_calibration,
)
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner


def _with_construction_flag(project, enabled):
    return replace(project, info=replace(project.info, use_construction_schedule_engine=enabled))


def _run(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def _key_outputs(result):
    first = result.periods[0]
    return {
        "revenue": result.total_revenue_keur,
        "opex": result.total_opex_keur,
        "senior_ds": result.total_senior_ds_keur,
        "shl_service": result.total_shl_service_keur,
        "distributions": result.total_distribution_keur,
        "opening_senior_proxy": first.senior_interest_keur + first.senior_principal_keur,
        "opening_shl_proxy": first.shl_balance_keur - first.shl_pik_keur + first.shl_principal_keur,
    }


def test_construction_schedule_engine_flag_defaults_false():
    assert create_default_tuho_wind1().info.use_construction_schedule_engine is False
    assert create_default_oborovo().info.use_construction_schedule_engine is False
    assert create_default_solar_project().info.use_construction_schedule_engine is False


def test_tuho_flag_false_matches_legacy_outputs():
    # STALE_LEGACY_CONSTRUCTION_DIAGNOSTIC_TEST_CONTRACT:
    # This test validates the construction-flag behavior against the legacy waterfall
    # runner (WaterfallRunner). After B3 Continuation A, create_default_tuho_wind1()
    # is a clean-production factory routed through run_clean_production(), which is
    # incompatible with WaterfallRunner's SHL two-pass assumption. The intended
    # historical contract uses the legacy calibration factory, which retains the
    # frozen Senior schedule and is compatible with the legacy waterfall runner.
    baseline = _run(create_default_tuho_wind1_legacy_calibration())
    flag_false = _run(_with_construction_flag(create_default_tuho_wind1_legacy_calibration(), False))

    assert _key_outputs(flag_false) == pytest.approx(_key_outputs(baseline), abs=0.0001)
    assert not hasattr(flag_false, "construction_schedule_diagnostic")


def test_oborovo_flag_false_matches_legacy_outputs():
    baseline = _run(create_default_oborovo())
    flag_false = _run(_with_construction_flag(create_default_oborovo(), False))

    assert _key_outputs(flag_false) == pytest.approx(_key_outputs(baseline), abs=0.0001)
    assert not hasattr(flag_false, "construction_schedule_diagnostic")


def test_tuho_flag_true_attaches_diagnostic_without_changing_financial_outputs():
    # STALE_LEGACY_CONSTRUCTION_DIAGNOSTIC_TEST_CONTRACT:
    # Uses the legacy calibration factory for the same reason as
    # test_tuho_flag_false_matches_legacy_outputs above.
    # The expected opening_shl_balance (32703.864 kEUR) is the legacy calibration
    # value; the clean B3 result (32261.528 kEUR) is a different authority.
    baseline = _run(create_default_tuho_wind1_legacy_calibration())
    flag_true = _run(_with_construction_flag(create_default_tuho_wind1_legacy_calibration(), True))

    assert _key_outputs(flag_true) == pytest.approx(_key_outputs(baseline), abs=0.0001)
    diagnostic = flag_true.construction_schedule_diagnostic
    assert diagnostic.opening_shl_balance_keur == pytest.approx(32703.864, abs=0.01)
    assert any("double_count_guard" in note for note in diagnostic.validation_notes)


def test_oborovo_flag_true_attaches_diagnostic_without_changing_financial_outputs():
    baseline = _run(create_default_oborovo())
    flag_true = _run(_with_construction_flag(create_default_oborovo(), True))

    assert _key_outputs(flag_true) == pytest.approx(_key_outputs(baseline), abs=0.0001)
    diagnostic = flag_true.construction_schedule_diagnostic
    assert diagnostic.opening_shl_balance_keur == pytest.approx(15790.436, abs=0.01)
    assert any("shl_idc_keur differs" in note for note in diagnostic.validation_notes)


def test_unsupported_project_flag_true_raises_clear_error():
    project = _with_construction_flag(create_default_solar_project(), True)

    with pytest.raises(ValueError, match="Construction schedule runtime engine"):
        _run(project)
