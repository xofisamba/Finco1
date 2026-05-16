from dataclasses import replace

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.senior_rate_schedule import (
    SeniorDayCountConvention,
    SeniorDebtInterestConfig,
    SeniorRateMode,
    SeniorRateSchedule,
)


TUHO_EXCEL_SENIOR = {
    0: {"interest": 1_297.082, "principal": 819.279, "ds": 2_116.361, "closing": 42_539.252},
    1: {"interest": 1_293.666, "principal": 857.773, "ds": 2_151.439, "closing": 41_681.478},
    2: {"interest": 1_246.913, "principal": 897.779, "ds": 2_144.692, "closing": 40_783.700},
    3: {"interest": 1_240.278, "principal": 939.961, "ds": 2_180.239, "closing": 39_843.738},
    27: {"interest": 83.960, "principal": 2_760.833, "ds": 2_844.793, "closing": 0.0},
}

OBOROVO_EXCEL_SENIOR = {
    0: {"interest": 1_303.483, "principal": 935.650, "ds": 2_239.133, "closing": 41_916.629},
    1: {"interest": 1_254.234, "principal": 948.392, "ds": 2_202.626, "closing": 40_968.237},
    2: {"interest": 1_222.505, "principal": 1_018.020, "ds": 2_240.525, "closing": 39_950.217},
    3: {"interest": 1_179.169, "principal": 1_091.108, "ds": 2_270.277, "closing": 38_859.108},
    27: {"interest": 43.235, "principal": 1_464.204, "ds": 1_507.439, "closing": 0.0},
}


def _run(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def _senior_row(period):
    return {
        "date": period.date.isoformat(),
        "opening": period.senior_balance_keur + period.senior_principal_keur,
        "interest": period.senior_interest_keur,
        "principal": period.senior_principal_keur,
        "ds": period.senior_ds_keur,
        "closing": period.senior_balance_keur,
    }


def _explicit_config(default_rate, rate_overrides, fraction_overrides, tenor_periods=28):
    rates = [default_rate] * tenor_periods
    fractions = [0.5] * tenor_periods
    for idx, value in rate_overrides.items():
        rates[idx] = value
    for idx, value in fraction_overrides.items():
        fractions[idx] = value
    return SeniorDebtInterestConfig(
        enabled=True,
        rate_schedule=SeniorRateSchedule(
            mode=SeniorRateMode.EXPLICIT_ALL_IN_SCHEDULE,
            explicit_all_in_rates=tuple(rates),
        ),
        day_count=SeniorDayCountConvention.EXPLICIT_FRACTIONS,
        explicit_period_fractions=tuple(fractions),
    )


def build_tuho_senior_rate_config_fixture():
    """Partial Excel-backed TUHO senior rate fixture for opt-in evaluation."""
    return _explicit_config(
        default_rate=0.0575,
        rate_overrides={0: 0.0595, 1: 0.0595, 2: 0.0595, 3: 0.0595, 27: 0.0595},
        fraction_overrides={
            0: 181 / 360,
            1: 184 / 360,
            2: 181 / 360,
            3: 184 / 360,
            27: 184 / 360,
        },
    )


def build_oborovo_senior_rate_config_fixture():
    """Partial Excel-backed Oborovo senior rate fixture for opt-in evaluation."""
    return _explicit_config(
        default_rate=0.0565,
        rate_overrides={
            0: 0.0595136,
            1: 0.0595136,
            2: 0.0583832,
            3: 0.0583832,
            27: 0.0584072,
        },
        fraction_overrides={
            0: 184 / 360,
            1: 181 / 360,
            2: 184 / 360,
            3: 182 / 360,
            27: 182 / 360,
        },
    )


def _with_senior_rate_config(project, config):
    return replace(
        project,
        info=replace(project.info, use_senior_rate_schedule_engine=True),
        financing=replace(project.financing, senior_debt_interest_config=config),
    )


def test_project_factories_do_not_enable_senior_rate_schedule_engine():
    assert create_default_tuho_wind1().info.use_senior_rate_schedule_engine is False
    assert create_default_oborovo().info.use_senior_rate_schedule_engine is False


def test_legacy_flag_off_unchanged_with_project_fixture_config_present():
    cases = (
        (create_default_tuho_wind1, build_tuho_senior_rate_config_fixture()),
        (create_default_oborovo, build_oborovo_senior_rate_config_fixture()),
    )
    for factory, fixture_config in cases:
        project = factory()
        baseline = _run(project)
        configured_but_flag_off = replace(
            project,
            financing=replace(project.financing, senior_debt_interest_config=fixture_config),
        )
        result = _run(configured_but_flag_off)

        assert result.total_revenue_keur == pytest.approx(baseline.total_revenue_keur, abs=0.0001)
        assert result.total_opex_keur == pytest.approx(baseline.total_opex_keur, abs=0.0001)
        assert result.total_senior_ds_keur == pytest.approx(baseline.total_senior_ds_keur, abs=0.0001)
        assert result.total_shl_service_keur == pytest.approx(baseline.total_shl_service_keur, abs=0.0001)
        assert result.total_distribution_keur == pytest.approx(baseline.total_distribution_keur, abs=0.0001)


def test_tuho_flag_on_first_period_interest_matches_excel_fixture():
    result = _run(
        _with_senior_rate_config(create_default_tuho_wind1(), build_tuho_senior_rate_config_fixture())
    )
    first = _senior_row(result.periods[0])

    assert first["opening"] == pytest.approx(43_359.0, abs=0.30)
    assert first["interest"] == pytest.approx(TUHO_EXCEL_SENIOR[0]["interest"], abs=0.10)


def test_oborovo_flag_on_first_period_interest_matches_excel_fixture():
    result = _run(
        _with_senior_rate_config(create_default_oborovo(), build_oborovo_senior_rate_config_fixture())
    )
    first = _senior_row(result.periods[0])

    assert first["opening"] == pytest.approx(42_852.267, abs=0.05)
    assert first["interest"] == pytest.approx(OBOROVO_EXCEL_SENIOR[0]["interest"], abs=0.10)


def test_senior_opening_balance_policy_preserved_under_project_opt_in():
    cases = (
        (create_default_tuho_wind1, build_tuho_senior_rate_config_fixture(), 43_359.0, 44_878.838),
        (create_default_oborovo, build_oborovo_senior_rate_config_fixture(), 42_852.267, 43_938.299),
    )
    for factory, fixture_config, principal_only, principal_plus_idc in cases:
        result = _run(_with_senior_rate_config(factory(), fixture_config))
        first = _senior_row(result.periods[0])

        assert first["opening"] == pytest.approx(principal_only, abs=0.30)
        assert first["opening"] != pytest.approx(principal_plus_idc, abs=0.30)


def test_partial_fixture_documents_total_senior_ds_movement_not_full_parity():
    tuho_base = _run(create_default_tuho_wind1())
    tuho_flag = _run(
        _with_senior_rate_config(create_default_tuho_wind1(), build_tuho_senior_rate_config_fixture())
    )
    oborovo_base = _run(create_default_oborovo())
    oborovo_flag = _run(
        _with_senior_rate_config(create_default_oborovo(), build_oborovo_senior_rate_config_fixture())
    )

    assert tuho_flag.total_senior_ds_keur != pytest.approx(tuho_base.total_senior_ds_keur, abs=0.01)
    assert oborovo_flag.total_senior_ds_keur != pytest.approx(oborovo_base.total_senior_ds_keur, abs=0.01)

    assert tuho_flag.total_senior_ds_keur - tuho_base.total_senior_ds_keur == pytest.approx(
        340.789,
        abs=0.01,
    )
    assert oborovo_flag.total_senior_ds_keur - oborovo_base.total_senior_ds_keur == pytest.approx(
        392.098,
        abs=0.01,
    )

    # Rate/day-count fixes interest first; DS and balances still expose sculpting gaps.
    tuho_first = _senior_row(tuho_flag.periods[0])
    oborovo_first = _senior_row(oborovo_flag.periods[0])
    assert abs(tuho_first["ds"] - TUHO_EXCEL_SENIOR[0]["ds"]) > 100.0
    assert abs(oborovo_first["ds"] - OBOROVO_EXCEL_SENIOR[0]["ds"]) > 100.0


def test_no_non_senior_cashflow_lines_move_when_flag_on_before_financing_feedback():
    for factory, fixture_config in (
        (create_default_tuho_wind1, build_tuho_senior_rate_config_fixture()),
        (create_default_oborovo, build_oborovo_senior_rate_config_fixture()),
    ):
        baseline = _run(factory())
        flag_on = _run(_with_senior_rate_config(factory(), fixture_config))

        assert flag_on.total_revenue_keur == pytest.approx(baseline.total_revenue_keur, abs=0.0001)
        assert flag_on.total_opex_keur == pytest.approx(baseline.total_opex_keur, abs=0.0001)
