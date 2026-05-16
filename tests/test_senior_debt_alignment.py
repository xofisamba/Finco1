from dataclasses import replace

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.construction.runtime_adapter import build_runtime_construction_schedule


def _with_construction_flag(project, enabled=True):
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
        "first_senior_interest": first.senior_interest_keur,
        "first_senior_principal": first.senior_principal_keur,
        "first_senior_closing_balance": first.senior_balance_keur,
    }


def test_flag_off_senior_outputs_remain_unchanged_for_tuho_and_oborovo():
    for factory in (create_default_tuho_wind1, create_default_oborovo):
        baseline = _run(factory())
        flag_false = _run(_with_construction_flag(factory(), False))

        assert _key_outputs(flag_false) == pytest.approx(_key_outputs(baseline), abs=0.0001)


def test_tuho_senior_opening_reconciliation_is_attached_diagnostically():
    result = build_runtime_construction_schedule(create_default_tuho_wind1())
    senior = result.senior_debt_diagnostic

    assert senior.opening_balance_source == "manual_fixed_debt_keur_diagnostic_only"
    assert senior.manual_opening_senior_balance_keur == pytest.approx(43359.0, abs=0.01)
    assert senior.computed_senior_principal_draw_keur == pytest.approx(43359.274, abs=0.01)
    assert senior.computed_senior_idc_keur == pytest.approx(1519.564, abs=0.01)
    assert senior.computed_opening_senior_excluding_idc_keur == pytest.approx(43359.274, abs=0.01)
    assert senior.computed_opening_senior_including_idc_keur == pytest.approx(44878.838, abs=0.01)
    assert senior.opening_balance_delta_excluding_idc_keur == pytest.approx(-0.274, abs=0.01)
    assert senior.opening_balance_delta_including_idc_keur == pytest.approx(-1519.838, abs=0.01)
    assert "no construction IDC is added" in " ".join(senior.repayment_timing_notes)


def test_oborovo_senior_opening_reconciliation_is_attached_diagnostically():
    result = build_runtime_construction_schedule(create_default_oborovo())
    senior = result.senior_debt_diagnostic

    assert senior.manual_opening_senior_balance_keur == pytest.approx(42852.267, abs=0.01)
    assert senior.computed_senior_principal_draw_keur == pytest.approx(42852.267, abs=0.01)
    assert senior.computed_senior_idc_keur == pytest.approx(1086.032, abs=0.01)
    assert senior.computed_opening_senior_excluding_idc_keur == pytest.approx(42852.267, abs=0.01)
    assert senior.computed_opening_senior_including_idc_keur == pytest.approx(43938.299, abs=0.01)
    assert senior.opening_balance_delta_excluding_idc_keur == pytest.approx(0.0, abs=0.01)
    assert senior.opening_balance_delta_including_idc_keur == pytest.approx(-1086.032, abs=0.01)


def test_flag_on_does_not_double_count_senior_idc_or_change_senior_outputs():
    for factory in (create_default_tuho_wind1, create_default_oborovo):
        baseline = _run(factory())
        flag_true = _run(_with_construction_flag(factory()))

        assert _key_outputs(flag_true) == pytest.approx(_key_outputs(baseline), abs=0.0001)
        diagnostic = flag_true.construction_schedule_diagnostic.senior_debt_diagnostic
        assert diagnostic.computed_senior_idc_keur > 0
        assert diagnostic.manual_opening_senior_balance_keur == pytest.approx(
            diagnostic.computed_opening_senior_excluding_idc_keur,
            abs=0.30,
        )
        assert diagnostic.manual_opening_senior_balance_keur != pytest.approx(
            diagnostic.computed_opening_senior_including_idc_keur,
            abs=0.30,
        )


def test_senior_timing_diagnostics_are_present_when_flag_on():
    result = _run(_with_construction_flag(create_default_tuho_wind1()))
    senior = result.construction_schedule_diagnostic.senior_debt_diagnostic

    assert any("first operating period" in note for note in senior.repayment_timing_notes)
    assert any("COD balance is audit-only" in note for note in senior.cod_transition_notes)
