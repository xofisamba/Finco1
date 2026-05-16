import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.construction.runtime_adapter import build_runtime_construction_schedule


TUHO_EXCEL_FIRST = {
    "opening": 43_358.530568,
    "all_in_rate": 0.0595,
    "period_fraction": 0.502777777778,
    "interest": 1_297.082486,
    "principal": 819.278908,
    "ds": 2_116.361394,
    "closing": 42_539.251660,
    "dscr_target": 1.2,
    "cfads_senior": 3_070.175837,
}

OBOROVO_EXCEL_FIRST = {
    "opening": 42_852.278763,
    "all_in_rate": 0.0595136,
    "period_fraction": 0.511111111111,
    "interest": 1_303.483282,
    "principal": 935.650131,
    "ds": 2_239.133413,
    "closing": 41_916.628631,
    "dscr_actual": 1.15,
    "cfads_senior": 2_575.003425,
}


def _run(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def _first_senior_row(project):
    result = _run(project)
    period = result.periods[0]
    opening = period.senior_balance_keur + period.senior_principal_keur
    return {
        "opening": opening,
        "interest": period.senior_interest_keur,
        "principal": period.senior_principal_keur,
        "ds": period.senior_ds_keur,
        "closing": period.senior_balance_keur,
        "annual_rate": project.financing.all_in_rate,
        "period_fraction": 0.5,
        "cfads": period.ebitda_keur - period.tax_keur,
        "dscr": period.dscr,
    }


def test_opening_balance_policy_still_principal_only():
    for factory in (create_default_tuho_wind1, create_default_oborovo):
        project = factory()
        row = _first_senior_row(project)
        diagnostic = build_runtime_construction_schedule(project).senior_debt_diagnostic

        assert row["opening"] == pytest.approx(
            diagnostic.computed_opening_senior_excluding_idc_keur,
            abs=0.30,
        )
        assert row["opening"] != pytest.approx(
            diagnostic.computed_opening_senior_including_idc_keur,
            abs=0.30,
        )


def test_excel_period_fraction_diagnostics_are_exposed_as_constants():
    assert TUHO_EXCEL_FIRST["period_fraction"] == pytest.approx(181 / 360, abs=0.000001)
    assert OBOROVO_EXCEL_FIRST["period_fraction"] == pytest.approx(184 / 360, abs=0.000001)


def test_tuho_rate_daycount_bridge_identifies_interest_basis_gap():
    row = _first_senior_row(create_default_tuho_wind1())

    excel_interest_recalc = (
        TUHO_EXCEL_FIRST["opening"]
        * TUHO_EXCEL_FIRST["all_in_rate"]
        * TUHO_EXCEL_FIRST["period_fraction"]
    )
    python_interest_recalc = row["opening"] * row["annual_rate"] * row["period_fraction"]

    assert excel_interest_recalc == pytest.approx(TUHO_EXCEL_FIRST["interest"], abs=0.001)
    assert python_interest_recalc == pytest.approx(row["interest"], abs=0.001)
    assert TUHO_EXCEL_FIRST["all_in_rate"] - row["annual_rate"] == pytest.approx(0.0020, abs=0.0001)
    assert TUHO_EXCEL_FIRST["period_fraction"] - row["period_fraction"] == pytest.approx(
        0.0027778,
        abs=0.000001,
    )
    assert row["interest"] - TUHO_EXCEL_FIRST["interest"] == pytest.approx(-50.511236, abs=0.001)


def test_oborovo_rate_daycount_bridge_identifies_interest_basis_gap():
    row = _first_senior_row(create_default_oborovo())

    excel_interest_recalc = (
        OBOROVO_EXCEL_FIRST["opening"]
        * OBOROVO_EXCEL_FIRST["all_in_rate"]
        * OBOROVO_EXCEL_FIRST["period_fraction"]
    )
    python_interest_recalc = row["opening"] * row["annual_rate"] * row["period_fraction"]

    assert excel_interest_recalc == pytest.approx(OBOROVO_EXCEL_FIRST["interest"], abs=0.001)
    assert python_interest_recalc == pytest.approx(row["interest"], abs=0.001)
    assert OBOROVO_EXCEL_FIRST["all_in_rate"] - row["annual_rate"] == pytest.approx(
        0.0030136,
        abs=0.000001,
    )
    assert OBOROVO_EXCEL_FIRST["period_fraction"] - row["period_fraction"] == pytest.approx(
        0.0111111,
        abs=0.000001,
    )
    assert row["interest"] - OBOROVO_EXCEL_FIRST["interest"] == pytest.approx(-92.906747, abs=0.001)


def test_dscr_sculpting_diagnostics_show_cfads_basis_gap():
    tuho = _first_senior_row(create_default_tuho_wind1())
    oborovo = _first_senior_row(create_default_oborovo())

    assert tuho["cfads"] - TUHO_EXCEL_FIRST["cfads_senior"] == pytest.approx(0.018348, abs=0.001)
    assert tuho["dscr"] > TUHO_EXCEL_FIRST["dscr_target"]

    assert oborovo["cfads"] - OBOROVO_EXCEL_FIRST["cfads_senior"] == pytest.approx(0.327889, abs=0.001)
    assert oborovo["dscr"] > OBOROVO_EXCEL_FIRST["dscr_actual"]
