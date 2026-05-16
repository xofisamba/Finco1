from dataclasses import replace

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.construction.runtime_adapter import build_runtime_construction_schedule


TUHO_EXCEL_FIRST = {
    "opening": 43_358.530568,
    "interest": 1_297.082486,
    "principal": 819.278908,
    "ds": 2_116.361394,
    "closing": 42_539.251660,
}

OBOROVO_EXCEL_FIRST = {
    "opening": 42_852.278763,
    "interest": 1_303.483282,
    "principal": 935.650131,
    "ds": 2_239.133413,
    "closing": 41_916.628631,
}


def _run(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def _with_construction_flag(project, enabled=True):
    return replace(project, info=replace(project.info, use_construction_schedule_engine=enabled))


def _senior_row(period):
    opening = period.senior_balance_keur + period.senior_principal_keur
    return {
        "date": period.date,
        "opening": opening,
        "interest": period.senior_interest_keur,
        "principal": period.senior_principal_keur,
        "ds": period.senior_ds_keur,
        "closing": period.senior_balance_keur,
        "dscr": period.dscr,
        "cfads": period.ebitda_keur - period.tax_keur,
    }


def test_opening_balance_policy_preserved_for_senior_interest_timing_work():
    cases = (
        (create_default_tuho_wind1, 43_359.0, 44_878.838),
        (create_default_oborovo, 42_852.267, 43_938.299),
    )

    for factory, principal_only, principal_plus_idc in cases:
        project = factory()
        first = _senior_row(_run(project).periods[0])
        diagnostic = build_runtime_construction_schedule(project).senior_debt_diagnostic

        assert first["opening"] == pytest.approx(principal_only, abs=0.30)
        assert first["opening"] == pytest.approx(
            diagnostic.computed_opening_senior_excluding_idc_keur,
            abs=0.30,
        )
        assert first["opening"] != pytest.approx(principal_plus_idc, abs=0.30)


def test_senior_idc_is_excluded_from_operating_opening_debt():
    for factory in (create_default_tuho_wind1, create_default_oborovo):
        project = factory()
        first = _senior_row(_run(project).periods[0])
        diagnostic = build_runtime_construction_schedule(project).senior_debt_diagnostic

        assert diagnostic.computed_senior_idc_keur > 0
        assert first["opening"] != pytest.approx(
            diagnostic.computed_opening_senior_including_idc_keur,
            abs=0.30,
        )


def test_period_diagnostics_are_available_for_first_four_and_final_senior_period():
    for factory in (create_default_tuho_wind1, create_default_oborovo):
        result = _run(factory())
        active = [p for p in result.periods if p.senior_ds_keur > 0]

        assert len(active) == 28
        rows = [_senior_row(p) for p in active[:4] + active[-1:]]
        for row in rows:
            assert row["opening"] >= 0
            assert row["interest"] >= 0
            assert row["principal"] >= 0
            assert row["ds"] == pytest.approx(row["interest"] + row["principal"], abs=0.0001)
            assert row["closing"] >= 0
            assert row["cfads"] > 0


def test_tuho_first_period_excel_vs_python_bridge_is_diagnostic():
    first = _senior_row(_run(create_default_tuho_wind1()).periods[0])

    assert first["date"].isoformat() == "2030-06-30"
    assert first["opening"] - TUHO_EXCEL_FIRST["opening"] == pytest.approx(0.469432, abs=0.001)
    assert first["interest"] - TUHO_EXCEL_FIRST["interest"] == pytest.approx(-50.511236, abs=0.001)
    assert first["principal"] - TUHO_EXCEL_FIRST["principal"] == pytest.approx(-76.743464, abs=0.001)
    assert first["ds"] - TUHO_EXCEL_FIRST["ds"] == pytest.approx(-127.254700, abs=0.001)
    assert first["closing"] - TUHO_EXCEL_FIRST["closing"] == pytest.approx(77.212896, abs=0.001)


def test_oborovo_first_period_excel_vs_python_bridge_is_diagnostic():
    first = _senior_row(_run(create_default_oborovo()).periods[0])

    assert first["date"].isoformat() == "2030-12-31"
    assert first["opening"] - OBOROVO_EXCEL_FIRST["opening"] == pytest.approx(-0.012037, abs=0.001)
    assert first["interest"] - OBOROVO_EXCEL_FIRST["interest"] == pytest.approx(-92.906747, abs=0.001)
    assert first["principal"] - OBOROVO_EXCEL_FIRST["principal"] == pytest.approx(-90.744258, abs=0.001)
    assert first["ds"] - OBOROVO_EXCEL_FIRST["ds"] == pytest.approx(-183.651005, abs=0.001)
    assert first["closing"] - OBOROVO_EXCEL_FIRST["closing"] == pytest.approx(90.732222, abs=0.001)


def test_construction_diagnostic_flag_does_not_change_senior_schedule_outputs():
    for factory in (create_default_tuho_wind1, create_default_oborovo):
        baseline = _run(factory())
        flag_on = _run(_with_construction_flag(factory(), True))

        for baseline_period, flag_period in zip(baseline.periods, flag_on.periods):
            assert flag_period.senior_interest_keur == pytest.approx(
                baseline_period.senior_interest_keur,
                abs=0.0001,
            )
            assert flag_period.senior_principal_keur == pytest.approx(
                baseline_period.senior_principal_keur,
                abs=0.0001,
            )
            assert flag_period.senior_ds_keur == pytest.approx(
                baseline_period.senior_ds_keur,
                abs=0.0001,
            )
            assert flag_period.senior_balance_keur == pytest.approx(
                baseline_period.senior_balance_keur,
                abs=0.0001,
            )
