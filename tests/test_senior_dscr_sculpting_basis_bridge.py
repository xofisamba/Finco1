from dataclasses import replace

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.construction.runtime_adapter import build_runtime_construction_schedule
from tests.test_senior_rate_schedule_project_opt_in import (
    OBOROVO_EXCEL_SENIOR,
    TUHO_EXCEL_SENIOR,
    build_oborovo_senior_rate_config_fixture,
    build_tuho_senior_rate_config_fixture,
)


def _run(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def _with_senior_rate_config(project, config):
    return replace(
        project,
        info=replace(project.info, use_senior_rate_schedule_engine=True),
        financing=replace(project.financing, senior_debt_interest_config=config),
    )


def _senior_row(period, target_dscr):
    cfads = period.ebitda_keur - period.tax_keur
    return {
        "date": period.date.isoformat(),
        "opening": period.senior_balance_keur + period.senior_principal_keur,
        "cfads": cfads,
        "target_dscr": target_dscr,
        "allowed_ds_by_target": cfads / target_dscr,
        "interest": period.senior_interest_keur,
        "principal": period.senior_principal_keur,
        "ds": period.senior_ds_keur,
        "closing": period.senior_balance_keur,
    }


def _target_dscr_for_period(project, op_idx):
    schedule = project.financing.dscr_schedule
    if schedule and op_idx < len(schedule):
        return schedule[op_idx]
    return project.financing.target_dscr


def _tuho_flag_on_result():
    project = create_default_tuho_wind1()
    return project, _run(_with_senior_rate_config(project, build_tuho_senior_rate_config_fixture()))


def _oborovo_flag_on_result():
    project = create_default_oborovo()
    return project, _run(_with_senior_rate_config(project, build_oborovo_senior_rate_config_fixture()))


def test_opening_balance_policy_and_idc_exclusion_preserved():
    cases = (
        (create_default_tuho_wind1, build_tuho_senior_rate_config_fixture(), 43_359.0, 44_878.838),
        (create_default_oborovo, build_oborovo_senior_rate_config_fixture(), 42_852.267, 43_938.299),
    )
    for factory, config, principal_only, principal_plus_idc in cases:
        project = factory()
        result = _run(_with_senior_rate_config(project, config))
        first = result.periods[0]
        opening = first.senior_balance_keur + first.senior_principal_keur
        diagnostic = build_runtime_construction_schedule(project).senior_debt_diagnostic

        assert opening == pytest.approx(principal_only, abs=0.30)
        assert opening == pytest.approx(
            diagnostic.computed_opening_senior_excluding_idc_keur,
            abs=0.30,
        )
        assert opening != pytest.approx(principal_plus_idc, abs=0.30)
        assert opening != pytest.approx(
            diagnostic.computed_opening_senior_including_idc_keur,
            abs=0.30,
        )


def test_first_period_sculpting_diagnostics_are_exposed():
    for project, result in (_tuho_flag_on_result(), _oborovo_flag_on_result()):
        row = _senior_row(result.periods[0], _target_dscr_for_period(project, 0))

        assert row["cfads"] > 0
        assert row["target_dscr"] > 1.0
        assert row["allowed_ds_by_target"] > row["ds"]
        assert row["ds"] == pytest.approx(row["interest"] + row["principal"], abs=0.0001)


def test_tuho_principal_bridge_after_rate_daycount_parity():
    project, result = _tuho_flag_on_result()
    rows = {
        idx: _senior_row(result.periods[idx], _target_dscr_for_period(project, idx))
        for idx in (0, 1, 2, 3, 27)
    }

    assert rows[0]["interest"] == pytest.approx(TUHO_EXCEL_SENIOR[0]["interest"], abs=0.10)
    assert rows[0]["principal"] - TUHO_EXCEL_SENIOR[0]["principal"] == pytest.approx(-116.971, abs=0.01)
    assert rows[0]["ds"] - TUHO_EXCEL_SENIOR[0]["ds"] == pytest.approx(-116.957, abs=0.01)
    assert rows[0]["closing"] - TUHO_EXCEL_SENIOR[0]["closing"] == pytest.approx(117.440, abs=0.01)

    assert rows[1]["ds"] - TUHO_EXCEL_SENIOR[1]["ds"] == pytest.approx(-118.895, abs=0.01)
    assert rows[2]["ds"] - TUHO_EXCEL_SENIOR[2]["ds"] == pytest.approx(-122.379, abs=0.01)
    assert rows[3]["ds"] - TUHO_EXCEL_SENIOR[3]["ds"] == pytest.approx(-124.407, abs=0.01)
    assert rows[27]["ds"] - TUHO_EXCEL_SENIOR[27]["ds"] == pytest.approx(594.710, abs=0.01)


def test_oborovo_principal_bridge_after_rate_daycount_parity():
    project, result = _oborovo_flag_on_result()
    rows = {
        idx: _senior_row(result.periods[idx], _target_dscr_for_period(project, idx))
        for idx in (0, 1, 2, 3, 27)
    }

    assert rows[0]["interest"] == pytest.approx(OBOROVO_EXCEL_SENIOR[0]["interest"], abs=0.10)
    assert rows[0]["principal"] - OBOROVO_EXCEL_SENIOR[0]["principal"] == pytest.approx(-170.959, abs=0.01)
    assert rows[0]["ds"] - OBOROVO_EXCEL_SENIOR[0]["ds"] == pytest.approx(-170.959, abs=0.01)
    assert rows[0]["closing"] - OBOROVO_EXCEL_SENIOR[0]["closing"] == pytest.approx(170.946, abs=0.01)

    assert rows[1]["ds"] - OBOROVO_EXCEL_SENIOR[1]["ds"] == pytest.approx(-168.172, abs=0.01)
    assert rows[2]["ds"] - OBOROVO_EXCEL_SENIOR[2]["ds"] == pytest.approx(-141.422, abs=0.01)
    assert rows[3]["ds"] - OBOROVO_EXCEL_SENIOR[3]["ds"] == pytest.approx(-199.663, abs=0.01)
    assert rows[27]["ds"] - OBOROVO_EXCEL_SENIOR[27]["ds"] == pytest.approx(1_038.351, abs=0.01)


def test_legacy_flag_off_equivalence_preserved_with_diagnostic_fixture_present():
    cases = (
        (create_default_tuho_wind1, build_tuho_senior_rate_config_fixture()),
        (create_default_oborovo, build_oborovo_senior_rate_config_fixture()),
    )
    for factory, config in cases:
        project = factory()
        baseline = _run(project)
        fixture_present = replace(
            project,
            financing=replace(project.financing, senior_debt_interest_config=config),
        )
        flag_off = _run(fixture_present)

        assert flag_off.total_revenue_keur == pytest.approx(baseline.total_revenue_keur, abs=0.0001)
        assert flag_off.total_opex_keur == pytest.approx(baseline.total_opex_keur, abs=0.0001)
        assert flag_off.total_senior_ds_keur == pytest.approx(baseline.total_senior_ds_keur, abs=0.0001)
        assert flag_off.total_shl_service_keur == pytest.approx(baseline.total_shl_service_keur, abs=0.0001)
        assert flag_off.total_distribution_keur == pytest.approx(baseline.total_distribution_keur, abs=0.0001)
