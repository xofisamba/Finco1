"""PR-F1 canonical period-axis authority and fail-closed consumer tests."""
from __future__ import annotations

import dataclasses
from datetime import date

import pytest

from app.project_factories import (
    create_default_bess_project,
    create_default_oborovo,
    create_default_solar_bess_project,
    create_default_solar_project,
    create_default_tuho_wind1,
    create_default_wind_bess_project,
    create_default_wind_project,
)
from financial_engine.adapters.project_inputs import from_project_inputs
from financial_engine.orchestrator import (
    _build_period_engine,
    _strict_period_map,
    _validate_schedule_axis,
    run_operating_model,
)
from finco_core.engine.period_engine import (
    PeriodAxisConvention,
    PeriodEngine,
    validate_canonical_period_axis,
)


def _axis(project):
    clean = from_project_inputs(project)
    result = run_operating_model(clean)
    return clean, result.periods


def _assert_axis(periods, *, construction_count, final_end):
    construction = tuple(p for p in periods if p.is_construction)
    operating = tuple(p for p in periods if p.is_operation)
    assert len(construction) == construction_count
    assert len(operating) == 60
    assert tuple(p.period_index for p in periods) == tuple(range(len(periods)))
    assert all(p.days_in_period > 0 for p in periods)
    assert all(b.period_start == a.period_end for a, b in zip(periods, periods[1:]))
    assert operating[-1].period_end == final_end
    assert operating[-1].days_in_period > 1


def _expected_semiannual_ends(first_end: date, count: int) -> tuple[date, ...]:
    ends = []
    current = first_end
    for _ in range(count):
        ends.append(current)
        current = (
            date(current.year, 12, 31)
            if current.month == 6
            else date(current.year + 1, 6, 30)
        )
    return tuple(ends)


def test_tuho_full_production_axis_matches_source_evidence():
    clean, periods = _axis(create_default_tuho_wind1())
    assert clean.calendar.cod_date == date(2030, 1, 1)
    _assert_axis(periods, construction_count=1, final_end=date(2059, 12, 31))
    operating = tuple(p for p in periods if p.is_operation)
    assert (operating[0].period_start, operating[0].period_end) == (
        date(2030, 1, 1), date(2030, 6, 30)
    )
    assert operating[0].days_in_period == 181
    engine_operating = _build_period_engine(clean).operation_periods()
    assert tuple(p.operating_period_index for p in engine_operating) == tuple(range(60))
    assert tuple(p.period_end for p in operating) == tuple(p.end_date for p in engine_operating)


def test_oborovo_full_production_axis_matches_source_evidence():
    clean, periods = _axis(create_default_oborovo())
    assert clean.calendar.cod_date == date(2030, 6, 29)
    _assert_axis(periods, construction_count=1, final_end=date(2060, 6, 30))
    operating = tuple(p for p in periods if p.is_operation)
    assert (operating[0].period_start, operating[0].period_end) == (
        date(2030, 6, 30), date(2030, 12, 31)
    )
    assert operating[0].days_in_period == 184


@pytest.mark.parametrize(
    "factory",
    (create_default_tuho_wind1, create_default_oborovo),
)
def test_ui_runner_uses_the_same_typed_axis_as_clean_orchestration(factory):
    from app.ui_runner import _build_period_engine as build_ui_period_engine

    project = factory()
    ui_axis = build_ui_period_engine(project).periods()
    clean_axis = _build_period_engine(from_project_inputs(project)).periods()
    assert ui_axis == clean_axis


@pytest.mark.parametrize(
    "factory,first_start,first_end,ppa_end",
    (
        (create_default_tuho_wind1, date(2030, 1, 1), date(2030, 6, 30), date(2042, 1, 1)),
        (create_default_oborovo, date(2030, 6, 30), date(2030, 12, 31), date(2042, 6, 30)),
    ),
)
def test_source_projects_have_exact_full_period_metadata_vectors(
    factory, first_start, first_end, ppa_end
):
    clean = from_project_inputs(factory())
    periods = _build_period_engine(clean).periods()
    operating = tuple(p for p in periods if p.is_operation)
    expected_ends = _expected_semiannual_ends(first_end, 60)
    expected_starts = (first_start,) + expected_ends[:-1]
    expected_days = tuple(
        (end - start).days + (1 if start.day == 1 and start == clean.calendar.cod_date else 0)
        for start, end in zip(expected_starts, expected_ends)
    )
    assert tuple(p.end_date for p in operating) == expected_ends
    assert tuple(p.start_date for p in operating) == expected_starts
    assert tuple(p.days_in_period for p in operating) == expected_days
    assert tuple(p.operating_period_index for p in operating) == tuple(range(60))
    assert tuple(p.operating_year_index for p in operating) == tuple(i // 2 + 1 for i in range(60))
    assert tuple(p.period_in_year for p in operating) == tuple(i % 2 + 1 for i in range(60))
    assert tuple(p.is_ppa_active for p in operating) == tuple(
        start < ppa_end for start in expected_starts
    )
    assert all(p.is_operation and not p.is_construction for p in operating)


@pytest.mark.parametrize(
    "factory",
    (
        create_default_solar_project,
        create_default_wind_project,
        create_default_bess_project,
        create_default_solar_bess_project,
        create_default_wind_bess_project,
    ),
)
def test_generic_project_matrix_uses_one_canonical_axis(factory):
    project = factory()
    _, periods = _axis(project)
    operating = tuple(p for p in periods if p.is_operation)
    assert len(operating) == project.info.horizon_years * 2
    assert all(p.days_in_period > 0 for p in periods)
    assert operating[-1].days_in_period > 1


@pytest.mark.parametrize("construction_months", (6, 12, 18))
@pytest.mark.parametrize("financial_close", (
    date(2028, 7, 1),
    date(2029, 1, 1),
    date(2029, 6, 30),
    date(2029, 7, 1),
    date(2029, 12, 31),
    date(2029, 6, 29),
))
def test_calendar_boundary_matrix_has_exact_horizon_without_terminal_stub(
    financial_close, construction_months
):
    engine = PeriodEngine(
        financial_close=financial_close,
        construction_months=construction_months,
        cod_date=None,
        horizon_years=30,
        ppa_years=12,
    )
    periods = engine.periods()
    operating = engine.operation_periods()
    validate_canonical_period_axis(periods, expected_operating_periods=60)
    assert len(operating) == 60
    assert operating[-1].days_in_period > 1
    assert any(p.is_leap_year for p in operating)


def test_explicit_cod_must_match_typed_duration():
    with pytest.raises(ValueError, match="PERIOD_AXIS_COD_MISMATCH"):
        PeriodEngine(
            financial_close=date(2029, 7, 1),
            construction_months=6,
            cod_date=date(2030, 1, 2),
            horizon_years=30,
            ppa_years=12,
        )


@pytest.mark.parametrize(
    "indices,values,error",
    (
        ((0, 1), (1.0,), "LENGTH_MISMATCH"),
        ((0, 0), (1.0, 2.0), "DUPLICATE_INDICES"),
        ((1, 0), (1.0, 2.0), "OUT_OF_ORDER"),
        ((0, 2), (1.0, 2.0), None),
    ),
)
def test_parallel_period_mapping_attacks_fail_closed(indices, values, error):
    if error is None:
        assert _strict_period_map(indices, values, label="attack") == {0: 1.0, 2: 2.0}
    else:
        with pytest.raises(ValueError, match=error):
            _strict_period_map(indices, values, label="attack")


@pytest.mark.parametrize(
    "schedule",
    (
        {0: 1.0, 1: 2.0},       # missing
        {0: 1.0, 1: 2.0, 2: 3.0, 3: 4.0},  # extra
        {1: 1.0, 2: 2.0, 3: 3.0},          # shifted
        {0: 1.0, 2: 3.0, 1: 2.0},          # out of order
    ),
)
def test_schedule_axis_missing_extra_shifted_and_order_attacks_fail_closed(schedule):
    with pytest.raises(ValueError, match="PERIOD_SCHEDULE_AXIS_MISMATCH"):
        _validate_schedule_axis((0, 1, 2), schedule, label="attack")


def test_adapter_preserves_explicit_cod_and_rejects_payload_disagreement():
    project = create_default_tuho_wind1()
    clean = from_project_inputs(project)
    assert clean.calendar.cod_date == project.info.cod_date
    bad = dataclasses.replace(
        clean,
        calendar=dataclasses.replace(clean.calendar, cod_date=date(2030, 1, 2)),
    )
    with pytest.raises(ValueError, match="PERIOD_AXIS_COD_MISMATCH"):
        run_operating_model(bad)
