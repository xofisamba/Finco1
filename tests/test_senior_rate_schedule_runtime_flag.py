from dataclasses import replace

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.ui_runner import _build_period_engine
from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
from domain.senior_rate_schedule import (
    SeniorDayCountConvention,
    SeniorDebtInterestConfig,
    SeniorHedgeConfig,
    SeniorRateMode,
    SeniorRateSchedule,
    build_senior_period_rate_schedule,
)


def _run(project):
    engine = _build_period_engine(project)
    config = WaterfallRunConfig.from_inputs(project, engine)
    return WaterfallRunner(project, engine).run(config)


def _first_senior_period(result):
    first = result.periods[0]
    return {
        "date": first.date,
        "opening": first.senior_balance_keur + first.senior_principal_keur,
        "interest": first.senior_interest_keur,
        "principal": first.senior_principal_keur,
        "ds": first.senior_ds_keur,
        "closing": first.senior_balance_keur,
    }


def _with_senior_rate_config(project, config):
    return replace(
        project,
        info=replace(project.info, use_senior_rate_schedule_engine=True),
        financing=replace(project.financing, senior_debt_interest_config=config),
    )


def _explicit_config(rate, first_fraction, tenor_periods=28):
    return SeniorDebtInterestConfig(
        enabled=True,
        rate_schedule=SeniorRateSchedule(
            mode=SeniorRateMode.EXPLICIT_ALL_IN_SCHEDULE,
            explicit_all_in_rates=(rate,) * tenor_periods,
        ),
        day_count=SeniorDayCountConvention.EXPLICIT_FRACTIONS,
        explicit_period_fractions=(first_fraction,) + (0.5,) * (tenor_periods - 1),
    )


def test_senior_rate_schedule_flag_defaults_false():
    assert create_default_tuho_wind1().info.use_senior_rate_schedule_engine is False
    assert create_default_oborovo().info.use_senior_rate_schedule_engine is False
    assert create_default_tuho_wind1().financing.senior_debt_interest_config.enabled is False


def test_legacy_flag_off_equivalence_for_tuho_and_oborovo():
    for factory in (create_default_tuho_wind1, create_default_oborovo):
        base_project = factory()
        baseline = _run(base_project)
        project = replace(
            base_project,
            financing=replace(
                base_project.financing,
                senior_debt_interest_config=_explicit_config(0.08, 0.75),
            ),
        )
        flag_false = _run(project)

        assert flag_false.total_revenue_keur == pytest.approx(baseline.total_revenue_keur, abs=0.0001)
        assert flag_false.total_opex_keur == pytest.approx(baseline.total_opex_keur, abs=0.0001)
        assert flag_false.total_senior_ds_keur == pytest.approx(baseline.total_senior_ds_keur, abs=0.0001)
        assert flag_false.total_shl_service_keur == pytest.approx(baseline.total_shl_service_keur, abs=0.0001)
        assert flag_false.total_distribution_keur == pytest.approx(baseline.total_distribution_keur, abs=0.0001)
        baseline_first = _first_senior_period(baseline)
        flag_false_first = _first_senior_period(flag_false)
        assert flag_false_first["date"] == baseline_first["date"]
        for key in ("opening", "interest", "principal", "ds", "closing"):
            assert flag_false_first[key] == pytest.approx(baseline_first[key], abs=0.0001)


def test_opening_policy_unchanged_with_flag_on():
    cases = (
        (create_default_tuho_wind1, _explicit_config(0.0595, 181 / 360), 43_359.0, 44_878.838),
        (create_default_oborovo, _explicit_config(0.0595136, 184 / 360), 42_852.267, 43_938.299),
    )
    for factory, config, principal_only, principal_plus_idc in cases:
        first = _first_senior_period(_run(_with_senior_rate_config(factory(), config)))

        assert first["opening"] == pytest.approx(principal_only, abs=0.30)
        assert first["opening"] != pytest.approx(principal_plus_idc, abs=0.30)


def test_tuho_first_period_interest_parity_with_flag_on():
    project = _with_senior_rate_config(
        create_default_tuho_wind1(),
        _explicit_config(0.0595, 181 / 360),
    )
    first = _first_senior_period(_run(project))

    assert first["opening"] == pytest.approx(43_358.531, abs=0.50)
    assert first["interest"] == pytest.approx(1_297.082, abs=0.10)


def test_oborovo_first_period_interest_parity_with_flag_on():
    project = _with_senior_rate_config(
        create_default_oborovo(),
        _explicit_config(0.0595136, 184 / 360),
    )
    first = _first_senior_period(_run(project))

    assert first["opening"] == pytest.approx(42_852.279, abs=0.05)
    assert first["interest"] == pytest.approx(1_303.483, abs=0.10)


def test_hedge_blend_calculates_oborovo_style_first_period_rate():
    schedule = SeniorRateSchedule(
        mode=SeniorRateMode.HEDGE_BLEND,
        margin_rate=0.0265,
        hedge=SeniorHedgeConfig(
            hedge_pct=0.8,
            fixed_base_rate=0.032,
            floating_base_rate_curve=(0.037068,),
        ),
    )

    assert schedule.all_in_rate_for_period(0) == pytest.approx(0.0595136, abs=1e-9)


def test_explicit_fraction_schedule_validation():
    project = create_default_tuho_wind1()
    engine = _build_period_engine(project)
    periods = [p for p in engine.periods() if p.is_operation]

    with pytest.raises(ValueError, match="explicit_period_fractions"):
        build_senior_period_rate_schedule(
            SeniorDebtInterestConfig(
                enabled=True,
                rate_schedule=SeniorRateSchedule(flat_all_in_rate=0.0595),
                day_count=SeniorDayCountConvention.EXPLICIT_FRACTIONS,
                explicit_period_fractions=(0.5,),
            ),
            periods,
            28,
        )

    with pytest.raises(ValueError, match="fractions must be non-negative"):
        build_senior_period_rate_schedule(
            SeniorDebtInterestConfig(
                enabled=True,
                rate_schedule=SeniorRateSchedule(flat_all_in_rate=0.0595),
                day_count=SeniorDayCountConvention.EXPLICIT_FRACTIONS,
                explicit_period_fractions=(-0.5,) + (0.5,) * 27,
            ),
            periods,
            28,
        )


def test_explicit_all_in_schedule_validation():
    project = create_default_tuho_wind1()
    engine = _build_period_engine(project)
    periods = [p for p in engine.periods() if p.is_operation]

    with pytest.raises(ValueError, match="explicit_all_in_rates"):
        build_senior_period_rate_schedule(
            SeniorDebtInterestConfig(
                enabled=True,
                rate_schedule=SeniorRateSchedule(
                    mode=SeniorRateMode.EXPLICIT_ALL_IN_SCHEDULE,
                    explicit_all_in_rates=(0.0595,),
                ),
            ),
            periods,
            28,
        )

    with pytest.raises(ValueError, match="rate values must be non-negative"):
        build_senior_period_rate_schedule(
            SeniorDebtInterestConfig(
                enabled=True,
                rate_schedule=SeniorRateSchedule(
                    mode=SeniorRateMode.EXPLICIT_ALL_IN_SCHEDULE,
                    explicit_all_in_rates=(-0.01,) + (0.0595,) * 27,
                ),
            ),
            periods,
            28,
        )


def test_act_360_uses_inclusive_excel_style_day_count_for_tuho_first_period():
    project = create_default_tuho_wind1()
    engine = _build_period_engine(project)
    periods = [p for p in engine.periods() if p.is_operation]
    schedule = build_senior_period_rate_schedule(
        SeniorDebtInterestConfig(
            enabled=True,
            rate_schedule=SeniorRateSchedule(flat_all_in_rate=0.0595),
            day_count=SeniorDayCountConvention.ACT_360,
        ),
        periods,
        28,
    )

    assert schedule[0] == pytest.approx(0.0595 * 181 / 360, abs=1e-12)
