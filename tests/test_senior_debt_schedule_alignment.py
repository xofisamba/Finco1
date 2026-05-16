from dataclasses import replace

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.construction.runtime_adapter import build_runtime_construction_schedule


def _run(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def _with_construction_flag(project, enabled=True):
    return replace(project, info=replace(project.info, use_construction_schedule_engine=enabled))


def _first_senior_period(result):
    first = result.periods[0]
    opening_balance = first.senior_balance_keur + first.senior_principal_keur
    return {
        "date": first.date,
        "opening": opening_balance,
        "interest": first.senior_interest_keur,
        "principal": first.senior_principal_keur,
        "ds": first.senior_ds_keur,
        "closing": first.senior_balance_keur,
    }


def test_tuho_opening_senior_debt_remains_principal_only():
    project = create_default_tuho_wind1()
    result = _run(project)
    first = _first_senior_period(result)
    diagnostic = build_runtime_construction_schedule(project).senior_debt_diagnostic

    assert first["opening"] == pytest.approx(43_359.0, abs=0.01)
    assert first["opening"] == pytest.approx(
        diagnostic.computed_opening_senior_excluding_idc_keur,
        abs=0.30,
    )
    assert first["opening"] != pytest.approx(
        diagnostic.computed_opening_senior_including_idc_keur,
        abs=0.30,
    )
    assert diagnostic.computed_senior_idc_keur == pytest.approx(1_519.564, abs=0.01)


def test_oborovo_opening_senior_debt_remains_principal_only():
    project = create_default_oborovo()
    result = _run(project)
    first = _first_senior_period(result)
    diagnostic = build_runtime_construction_schedule(project).senior_debt_diagnostic

    assert first["opening"] == pytest.approx(42_852.267, abs=0.01)
    assert first["opening"] == pytest.approx(
        diagnostic.computed_opening_senior_excluding_idc_keur,
        abs=0.01,
    )
    assert first["opening"] != pytest.approx(
        diagnostic.computed_opening_senior_including_idc_keur,
        abs=0.30,
    )
    assert diagnostic.computed_senior_idc_keur == pytest.approx(1_086.032, abs=0.01)


def test_commitment_fees_are_not_added_to_operating_senior_opening_debt():
    tuho = create_default_tuho_wind1()
    oborovo = create_default_oborovo()

    tuho_first = _first_senior_period(_run(tuho))
    oborovo_first = _first_senior_period(_run(oborovo))

    tuho_commitment_fee = 166.718
    oborovo_commitment_fee = 188.563

    assert tuho_first["opening"] != pytest.approx(
        tuho.financing.fixed_debt_keur + tuho.capex.idc_keur + tuho_commitment_fee,
        abs=0.30,
    )
    assert oborovo_first["opening"] != pytest.approx(
        oborovo.financing.fixed_debt_keur + oborovo.capex.idc_keur + oborovo_commitment_fee,
        abs=0.30,
    )


def test_first_operating_senior_diagnostics_are_visible_for_tuho():
    first = _first_senior_period(_run(create_default_tuho_wind1()))

    assert first["date"].isoformat() == "2030-06-30"
    assert first["opening"] == pytest.approx(43_359.0, abs=0.01)
    assert first["principal"] == pytest.approx(742.535, abs=0.01)
    assert first["interest"] == pytest.approx(1_246.571, abs=0.01)
    assert first["ds"] == pytest.approx(1_989.107, abs=0.01)
    assert first["closing"] == pytest.approx(42_616.465, abs=0.01)


def test_first_operating_senior_diagnostics_are_visible_for_oborovo():
    first = _first_senior_period(_run(create_default_oborovo()))

    assert first["date"].isoformat() == "2030-12-31"
    assert first["opening"] == pytest.approx(42_852.267, abs=0.01)
    assert first["principal"] == pytest.approx(844.906, abs=0.01)
    assert first["interest"] == pytest.approx(1_210.577, abs=0.01)
    assert first["ds"] == pytest.approx(2_055.482, abs=0.01)
    assert first["closing"] == pytest.approx(42_007.361, abs=0.01)


def test_flag_on_diagnostics_do_not_change_first_senior_period_outputs():
    for factory in (create_default_tuho_wind1, create_default_oborovo):
        baseline = _first_senior_period(_run(factory()))
        flag_on = _first_senior_period(_run(_with_construction_flag(factory(), True)))

        assert flag_on["date"] == baseline["date"]
        for key in ("opening", "interest", "principal", "ds", "closing"):
            assert flag_on[key] == pytest.approx(baseline[key], abs=0.0001)
