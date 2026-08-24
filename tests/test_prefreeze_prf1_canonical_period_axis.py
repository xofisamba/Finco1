"""PR-F1 canonical period-axis authority and fail-closed consumer tests.

Correction A: exact-axis membership validation, production-boundary attacks,
and strengthened validate_canonical_period_axis checks.
"""
from __future__ import annotations

import dataclasses
import math
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
    _assemble_post_senior_cash_schedules,
    _build_period_engine,
    _strict_period_map,
    _validate_schedule_axis,
    run_operating_model,
)
from finco_core.engine.period_engine import (
    PeriodAxisConvention,
    PeriodEngine,
    PeriodMeta,
    map_period_vector,
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
        ((0, 0), (1.0, 2.0), "AXIS_PERIOD_DUPLICATE"),
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


def test_unconfigured_depreciation_is_an_explicit_zero_full_axis_schedule():
    clean = from_project_inputs(create_default_solar_project())
    clean = dataclasses.replace(
        clean,
        depreciation=dataclasses.replace(
            clean.depreciation,
            book_capex_items_for_depreciation=(),
            tax_capex_items_for_depreciation=(),
        ),
    )
    result = run_operating_model(clean)
    expected_indices = tuple(p.period_index for p in result.periods)
    assert result.operating_schedules.period_indices == expected_indices
    assert result.operating_schedules.book_depreciation_keur == (0.0,) * len(expected_indices)
    assert result.operating_schedules.tax_depreciation_keur == (0.0,) * len(expected_indices)


# ---------------------------------------------------------------------------
# Correction A: exact-axis membership validation via expected_indices
# ---------------------------------------------------------------------------

def _make_periods(construction_count: int, operating_count: int) -> tuple[PeriodMeta, ...]:
    """Build a minimal valid canonical axis for use in attack tests."""
    from datetime import timedelta
    periods = []
    start = date(2028, 7, 1)
    idx = 0
    for i in range(construction_count):
        end = start + timedelta(days=184)
        is_leap = (end.year % 4 == 0 and (end.year % 100 != 0 or end.year % 400 == 0))
        days = (end - start).days
        periods.append(PeriodMeta(
            index=idx,
            start_date=start,
            end_date=end,
            year_index=0,
            period_in_year=i % 2 + 1,
            is_construction=True,
            is_operation=False,
            is_ppa_active=False,
            days_in_period=days,
            day_fraction=days / (366.0 if is_leap else 365.0),
            is_leap_year=is_leap,
        ))
        idx += 1
        start = end
    for op_pos in range(operating_count):
        end = start + timedelta(days=184)
        is_leap = (end.year % 4 == 0 and (end.year % 100 != 0 or end.year % 400 == 0))
        days = (end - start).days
        periods.append(PeriodMeta(
            index=idx,
            start_date=start,
            end_date=end,
            year_index=op_pos // 2 + 1,
            period_in_year=op_pos % 2 + 1,
            is_construction=False,
            is_operation=True,
            is_ppa_active=True,
            days_in_period=days,
            day_fraction=days / (366.0 if is_leap else 365.0),
            is_leap_year=is_leap,
            operating_period_index=op_pos,
            operating_year_index=op_pos // 2 + 1,
        ))
        idx += 1
        start = end
    return tuple(periods)


@pytest.mark.parametrize(
    "supplied,expected,error_code",
    (
        # missing period: supply 0,2 but expect 0,1,2
        ((0, 2),    (0, 1, 2), "AXIS_PERIOD_MISSING"),
        # extra period: supply 0,1,2,3 but expect 0,1,2
        ((0, 1, 2, 3), (0, 1, 2), "AXIS_PERIOD_EXTRA"),
        # shifted: supply 1,2,3 but expect 0,1,2
        ((1, 2, 3), (0, 1, 2), "AXIS_PERIOD_MISSING"),
        # reordered (same set, wrong order): supply 0,2,1 vs 0,1,2 → shifted
        ((0, 2, 1), (0, 1, 2), "AXIS_PERIOD_SHIFTED"),
        # duplicate raw indices
        ((0, 0, 1),  (0, 1, 2), "AXIS_PERIOD_DUPLICATE"),
        # length mismatch with both missing and extra (mixed overlap)
        ((0, 99),    (0, 1, 2), "AXIS_LENGTH_MISMATCH"),
    ),
)
def test_map_period_vector_exact_axis_membership_attacks(supplied, expected, error_code):
    """Correction A: map_period_vector rejects non-exact axis with specific codes."""
    values = tuple(float(i) for i in range(len(supplied)))
    with pytest.raises(ValueError, match=error_code):
        map_period_vector(
            supplied,
            values,
            label="attack",
            expected_indices=expected,
        )


def test_map_period_vector_exact_axis_passes_valid_vector():
    """Correction A: exact match passes without error."""
    result = map_period_vector(
        (0, 1, 2),
        (1.0, 2.0, 3.0),
        label="valid",
        expected_indices=(0, 1, 2),
    )
    assert result == {0: 1.0, 1: 2.0, 2: 3.0}


# ---------------------------------------------------------------------------
# Correction A: strengthened validate_canonical_period_axis checks
# ---------------------------------------------------------------------------

def test_validate_axis_rejects_construction_after_operation():
    """Construction period after operation begins must fail."""
    periods = _make_periods(1, 4)
    # Flip the last operating period to construction (corrupt phase flag)
    p = periods[-1]
    bad = dataclasses.replace(p, is_construction=True, is_operation=False)
    corrupted = periods[:-1] + (bad,)
    with pytest.raises(ValueError, match="PERIOD_AXIS_CONSTRUCTION_AFTER_OPERATION"):
        validate_canonical_period_axis(corrupted)


def test_validate_axis_rejects_nan_day_fraction():
    """NaN day_fraction must fail with PERIOD_AXIS_DAY_FRACTION_INVALID."""
    periods = _make_periods(1, 4)
    p = periods[0]
    bad = dataclasses.replace(p, day_fraction=float("nan"))
    corrupted = (bad,) + periods[1:]
    with pytest.raises(ValueError, match="PERIOD_AXIS_DAY_FRACTION_INVALID"):
        validate_canonical_period_axis(corrupted)


def test_validate_axis_rejects_infinite_day_fraction():
    """Infinite day_fraction must fail with PERIOD_AXIS_DAY_FRACTION_INVALID."""
    periods = _make_periods(1, 4)
    p = periods[0]
    bad = dataclasses.replace(p, day_fraction=float("inf"))
    corrupted = (bad,) + periods[1:]
    with pytest.raises(ValueError, match="PERIOD_AXIS_DAY_FRACTION_INVALID"):
        validate_canonical_period_axis(corrupted)


def test_validate_axis_rejects_inconsistent_days_in_period():
    """days_in_period wildly inconsistent with date span must fail."""
    periods = _make_periods(1, 4)
    p = periods[0]
    # calendar days would be ~184; set days_in_period to 999
    bad = dataclasses.replace(p, days_in_period=999)
    corrupted = (bad,) + periods[1:]
    with pytest.raises(ValueError, match="PERIOD_AXIS_DAYS_IN_PERIOD_MISMATCH"):
        validate_canonical_period_axis(corrupted)


def test_validate_axis_rejects_terminal_one_day_stub():
    """Final operating period with days_in_period=1 must fail."""
    periods = _make_periods(1, 4)
    p = periods[-1]
    # Shrink to a one-day stub: adjust end_date and days
    from datetime import timedelta
    new_end = p.start_date + timedelta(days=1)
    bad = dataclasses.replace(
        p,
        end_date=new_end,
        days_in_period=1,
        day_fraction=1.0 / 365.0,
    )
    # Reindex so gap doesn't trigger first (all periods up to last are unchanged)
    corrupted = periods[:-1] + (bad,)
    with pytest.raises(ValueError, match="PERIOD_AXIS_TERMINAL_STUB|PERIOD_AXIS_DAYS_IN_PERIOD_MISMATCH"):
        validate_canonical_period_axis(corrupted)


def test_validate_axis_rejects_operating_year_index_incoherence():
    """operating_year_index out of step must fail."""
    periods = _make_periods(1, 4)
    p = periods[1]  # first operating, op_pos=0 → expected year=1
    bad = dataclasses.replace(p, operating_year_index=99)
    corrupted = (periods[0],) + (bad,) + periods[2:]
    with pytest.raises(ValueError, match="PERIOD_AXIS_OPERATING_YEAR_INDEX_INVALID"):
        validate_canonical_period_axis(corrupted)


def test_validate_axis_rejects_period_in_year_incoherence():
    """period_in_year out of step must fail."""
    periods = _make_periods(1, 4)
    p = periods[1]  # first operating, op_pos=0 → expected pip=1
    bad = dataclasses.replace(p, period_in_year=2)
    corrupted = (periods[0],) + (bad,) + periods[2:]
    with pytest.raises(ValueError, match="PERIOD_AXIS_PERIOD_IN_YEAR_INVALID"):
        validate_canonical_period_axis(corrupted)


# ---------------------------------------------------------------------------
# Correction A: production-boundary attacks
# ---------------------------------------------------------------------------

def _make_minimal_mock(period_indices, values):
    """Minimal mock for senior_debt_result or tax_and_cfads with bad axis."""
    class _Mock:
        pass
    m = _Mock()
    m.period_indices = tuple(period_indices)
    m.senior_debt_service_keur = tuple(float(v) for v in values)
    m.cfads_keur = tuple(float(v) for v in values)
    return m


def _make_period_results(periods_meta):
    """Convert PeriodMeta tuple to OperatingPeriodResult tuples for boundaries."""
    from financial_engine.results import OperatingPeriodResult
    return tuple(
        OperatingPeriodResult(
            period_index=p.index,
            period_start=p.start_date,
            period_end=p.end_date,
            year_index=float(p.year_index),
            period_in_year=float(p.period_in_year),
            is_construction=p.is_construction,
            is_operation=p.is_operation,
            is_ppa_active=p.is_ppa_active,
            days_in_period=p.days_in_period,
            day_fraction=p.day_fraction,
            production_mwh=0.0,
            revenue_keur=0.0,
            opex_keur=0.0,
            ebitda_keur=0.0,
            book_depreciation_keur=0.0,
            tax_depreciation_keur=0.0,
            ebit_keur=0.0,
        )
        for p in periods_meta
    )


def _make_mock_tax_cfads(period_indices, value=100.0):
    """Minimal duck-typed mock for TaxAndCfadsSchedules (only fields read by boundary)."""
    class _MockTaxCfads:
        pass
    m = _MockTaxCfads()
    m.period_indices = tuple(period_indices)
    m.cfads_keur = tuple(value for _ in period_indices)
    return m


def test_post_senior_cash_rejects_duplicate_senior_axis():
    """Production boundary: duplicate senior DS period index is rejected (AXIS_PERIOD_DUPLICATE).

    AXIS_PERIOD_DUPLICATE fires before expected_indices is checked, so even
    with a valid senior_axis the duplicate triggers the expected error.
    """
    meta_periods = _make_periods(1, 4)
    period_results = _make_period_results(meta_periods)
    valid_indices = tuple(p.index for p in meta_periods)
    tax_and_cfads = _make_mock_tax_cfads(valid_indices)
    # Senior axis = operating periods (indices 1..4 in a 1-construction 4-operating axis)
    senior_axis = tuple(p.index for p in meta_periods if p.is_operation)

    # Duplicate period 0 in the senior DS vector — AXIS_PERIOD_DUPLICATE fires first
    bad_senior = _make_minimal_mock((0, 0, 2, 3, 4), (50.0, 50.0, 50.0, 50.0, 50.0))
    with pytest.raises(ValueError, match="AXIS_PERIOD_DUPLICATE"):
        _assemble_post_senior_cash_schedules(
            period_results, tax_and_cfads, bad_senior, senior_axis=senior_axis
        )


def test_post_senior_cash_rejects_bad_cfads_axis():
    """Production boundary: bad CFADS axis is rejected at post-senior boundary."""
    meta_periods = _make_periods(1, 4)
    period_results = _make_period_results(meta_periods)
    valid_indices = tuple(p.index for p in meta_periods)
    senior_axis = tuple(p.index for p in meta_periods if p.is_operation)

    # Senior on valid axis
    good_senior = _make_minimal_mock(senior_axis, tuple(50.0 for _ in senior_axis))

    # CFADS on shifted axis (missing period 0, has 5 — indices 1..5 instead of 0..4)
    bad_cfads = _make_mock_tax_cfads((1, 2, 3, 4, 5))

    with pytest.raises(ValueError, match="AXIS_PERIOD_MISSING"):
        _assemble_post_senior_cash_schedules(
            period_results, bad_cfads, good_senior, senior_axis=senior_axis
        )


def test_strict_period_map_missing_period_fails_closed():
    """map_period_vector with expected_indices: missing period → AXIS_PERIOD_MISSING."""
    expected = (1, 2, 3, 4, 5)
    supplied = (1, 2, 4, 5)      # missing 3
    with pytest.raises(ValueError, match="AXIS_PERIOD_MISSING"):
        map_period_vector(
            supplied,
            tuple(float(x) for x in supplied),
            label="senior.interest",
            expected_indices=expected,
        )


def test_strict_period_map_extra_period_fails_closed():
    """map_period_vector with expected_indices: extra period → AXIS_PERIOD_EXTRA."""
    expected = (1, 2, 3, 4, 5)
    supplied = (1, 2, 3, 4, 5, 6)   # extra 6
    with pytest.raises(ValueError, match="AXIS_PERIOD_EXTRA"):
        map_period_vector(
            supplied,
            tuple(float(x) for x in supplied),
            label="senior.interest",
            expected_indices=expected,
        )


def test_strict_period_map_shifted_period_fails_closed():
    """map_period_vector with expected_indices: shifted axis → AXIS_PERIOD_MISSING."""
    expected = (1, 2, 3, 4, 5)
    supplied = (2, 3, 4, 5, 6)    # shifted by 1
    with pytest.raises(ValueError, match="AXIS_PERIOD_MISSING|AXIS_PERIOD_EXTRA"):
        map_period_vector(
            supplied,
            tuple(float(x) for x in supplied),
            label="senior.interest",
            expected_indices=expected,
        )


def test_strict_period_map_reordered_period_fails_closed():
    """map_period_vector with expected_indices: reordered same set → AXIS_PERIOD_SHIFTED."""
    expected = (1, 2, 3, 4, 5)
    supplied = (1, 3, 2, 4, 5)    # 2 and 3 swapped
    with pytest.raises(ValueError, match="AXIS_PERIOD_SHIFTED"):
        map_period_vector(
            supplied,
            tuple(float(x) for x in supplied),
            label="senior.interest",
            expected_indices=expected,
        )


def test_strict_period_map_duplicate_period_fails_closed():
    """map_period_vector with expected_indices: duplicate raw index → AXIS_PERIOD_DUPLICATE."""
    expected = (1, 2, 3, 4, 5)
    supplied = (1, 2, 2, 4, 5)    # duplicate 2
    with pytest.raises(ValueError, match="AXIS_PERIOD_DUPLICATE"):
        map_period_vector(
            supplied,
            tuple(float(x) for x in supplied),
            label="senior.interest",
            expected_indices=expected,
        )


def test_strict_period_map_length_mismatch_fails_closed():
    """map_period_vector with expected_indices: mixed missing+extra → AXIS_LENGTH_MISMATCH."""
    # Supply (1, 99) vs expected (1, 2, 3) → missing=[2,3], extra=[99] → AXIS_LENGTH_MISMATCH
    expected = (1, 2, 3)
    supplied = (1, 99)
    with pytest.raises(ValueError, match="AXIS_LENGTH_MISMATCH"):
        map_period_vector(
            supplied,
            (1.0, 2.0),
            label="senior.interest",
            expected_indices=expected,
        )


# ---------------------------------------------------------------------------
# TASK 2: Day-count validation attacks
# ---------------------------------------------------------------------------

def test_validate_axis_rejects_construction_plus_one():
    """Construction period with +1 day must fail: COD-inclusive rule only applies to
    first operating period with start.day==1."""
    periods = _make_periods(1, 4)
    constr = periods[0]
    calendar_days = (constr.end_date - constr.start_date).days
    denom = 366.0 if constr.is_leap_year else 365.0
    bad = dataclasses.replace(
        constr,
        days_in_period=calendar_days + 1,
        day_fraction=(calendar_days + 1) / denom,
    )
    corrupted = (bad,) + periods[1:]
    with pytest.raises(ValueError, match="PERIOD_AXIS_DAYS_IN_PERIOD_MISMATCH"):
        validate_canonical_period_axis(corrupted)


def test_validate_axis_rejects_non_cod_operating_plus_one():
    """Non-first operating period with +1 day must fail."""
    periods = _make_periods(1, 4)
    # periods[2] is operating index 1 (not the first operating period)
    op = periods[2]
    calendar_days = (op.end_date - op.start_date).days
    denom = 366.0 if op.is_leap_year else 365.0
    bad = dataclasses.replace(
        op,
        days_in_period=calendar_days + 1,
        day_fraction=(calendar_days + 1) / denom,
    )
    corrupted = periods[:2] + (bad,) + periods[3:]
    with pytest.raises(ValueError, match="PERIOD_AXIS_DAYS_IN_PERIOD_MISMATCH"):
        validate_canonical_period_axis(corrupted)


def test_validate_axis_rejects_wrong_day_fraction():
    """day_fraction that does not reconcile to days_in_period / approved_denominator."""
    periods = _make_periods(1, 4)
    op = periods[1]  # first operating
    # Correct days_in_period but wrong fraction (e.g. using wrong denominator 360)
    calendar_days = (op.end_date - op.start_date).days
    bad = dataclasses.replace(op, day_fraction=calendar_days / 360.0)
    corrupted = (periods[0],) + (bad,) + periods[2:]
    with pytest.raises(ValueError, match="PERIOD_AXIS_DAY_FRACTION_RECONCILIATION_FAILED"):
        validate_canonical_period_axis(corrupted)


def test_validate_axis_rejects_wrong_leap_flag():
    """Wrong is_leap_year flag is caught by independent denominator check.

    Attack: flip is_leap_year but keep the ORIGINAL day_fraction (computed with the
    correct denominator).  The validator (Correction D) derives the approved denominator
    INDEPENDENTLY from end_date, then checks is_leap_year against that — the mismatch
    is caught before the fraction check.
    """
    periods = _make_periods(1, 4)
    op = periods[1]  # first operating
    correct_denom = 366.0 if op.is_leap_year else 365.0
    flipped_leap = not op.is_leap_year
    flipped_denom = 366.0 if flipped_leap else 365.0
    # Only meaningful when the denominators differ (they always do: 365 vs 366)
    assert abs(correct_denom - flipped_denom) > 0, "Test requires differing denominators"
    # Keep original day_fraction (correct for correct_denom) but set wrong leap flag.
    # Correction D: validator derives denominator from end_date independently,
    # then validates is_leap_year against it → PERIOD_AXIS_IS_LEAP_YEAR_MISMATCH.
    bad = dataclasses.replace(op, is_leap_year=flipped_leap)
    # day_fraction remains op.days_in_period / correct_denom (via op.day_fraction)
    corrupted = (periods[0],) + (bad,) + periods[2:]
    with pytest.raises(ValueError, match="PERIOD_AXIS_IS_LEAP_YEAR_MISMATCH"):
        validate_canonical_period_axis(corrupted)


def test_validate_axis_cod_inclusive_first_operating_passes():
    """Valid COD-inclusive case: first operating period with start.day==1 and +1 must PASS."""
    from datetime import date, timedelta
    # Build a period set where the first operating period starts on a month-start
    # (COD falls on the 1st) with days_in_period = calendar_days + 1.
    constr_start = date(2030, 1, 1)
    constr_end = date(2030, 6, 30)
    days_c = (constr_end - constr_start).days
    is_leap_c = (constr_end.year % 4 == 0 and (constr_end.year % 100 != 0 or constr_end.year % 400 == 0))
    constr = PeriodMeta(
        index=0, start_date=constr_start, end_date=constr_end,
        year_index=0, period_in_year=1, is_construction=True, is_operation=False,
        is_ppa_active=False, days_in_period=days_c,
        day_fraction=days_c / (366.0 if is_leap_c else 365.0),
        is_leap_year=is_leap_c,
    )
    # First operating period starts on 2030-07-01 (day == 1) — COD-inclusive case
    op_start = constr_end  # 2030-06-30 — but we want start.day == 1, so use July 1
    # Use a COD of July 1 directly
    op_start = date(2030, 7, 1)
    op_end = date(2030, 12, 31)
    cal_days = (op_end - op_start).days
    is_leap_op = (op_end.year % 4 == 0 and (op_end.year % 100 != 0 or op_end.year % 400 == 0))
    denom_op = 366.0 if is_leap_op else 365.0
    op1 = PeriodMeta(
        index=1, start_date=op_start, end_date=op_end,
        year_index=1, period_in_year=1, is_construction=False, is_operation=True,
        is_ppa_active=True, days_in_period=cal_days + 1,  # COD-inclusive +1
        day_fraction=(cal_days + 1) / denom_op,
        is_leap_year=is_leap_op, operating_period_index=0, operating_year_index=1,
    )
    # But we need continuity: op_start must equal constr_end (2030-06-30).
    # This fixture is intentionally only about the day_fraction/days_in_period rule,
    # not date continuity. Build a flat axis where construction ends at 2030-07-01.
    constr2 = PeriodMeta(
        index=0, start_date=date(2030, 1, 1), end_date=date(2030, 7, 1),
        year_index=0, period_in_year=1, is_construction=True, is_operation=False,
        is_ppa_active=False, days_in_period=181,
        day_fraction=181 / 365.0, is_leap_year=False,
    )
    op_start2 = date(2030, 7, 1)
    op_end2 = date(2030, 12, 31)
    cal2 = (op_end2 - op_start2).days  # 183
    is_leap2 = False  # 2030 not leap
    op2 = PeriodMeta(
        index=1, start_date=op_start2, end_date=op_end2,
        year_index=1, period_in_year=1, is_construction=False, is_operation=True,
        is_ppa_active=True, days_in_period=cal2 + 1,
        day_fraction=(cal2 + 1) / 365.0,
        is_leap_year=is_leap2, operating_period_index=0, operating_year_index=1,
    )
    # This must pass (COD-inclusive +1 is permitted)
    validate_canonical_period_axis((constr2, op2))


# ---------------------------------------------------------------------------
# TASK 3 / TASK 4: Real production-boundary attacks via run_senior_debt_model
#
# Error-code precedence (documented here — TASK 4):
#   1. AXIS_PERIOD_DUPLICATE  — duplicate raw indices checked first
#   2. AXIS_LENGTH_MISMATCH   — length differs with both missing and extra
#   3. AXIS_PERIOD_MISSING    — expected index absent from supplied
#   4. AXIS_PERIOD_EXTRA      — supplied index not in expected
#   5. AXIS_PERIOD_SHIFTED    — same set, different order
#
# "Shifted" (different offset range) raises AXIS_PERIOD_MISSING because the
# sets differ.  AXIS_PERIOD_SHIFTED only fires when len matches and sets match
# but order differs.
# ---------------------------------------------------------------------------

def _make_tuho_senior_debt_model_input():
    """Build a minimal but valid SeniorDebtModelInput using tuho wind1 project."""
    from app.project_factories import create_default_tuho_wind1
    from financial_engine.adapters.project_inputs import from_project_inputs
    from financial_engine.inputs import (
        DebtSizingCaseInput,
        SeniorDebtModelInput,
        TaxCalculationInput,
        YieldScenario,
    )
    from financial_engine.orchestrator import run_operating_model
    from financial_engine.senior_debt.inputs import SeniorDebtInputs
    from financial_engine.senior_debt.policy import (
        DayCountConvention,
        SeniorDebtPolicy,
        SeniorDebtSizingMode,
    )

    base_op = from_project_inputs(create_default_tuho_wind1())
    # Find operating period bounds
    base_result = run_operating_model(base_op)
    op_indices = tuple(p.period_index for p in base_result.periods if p.is_operation)
    repayment_start = op_indices[0]
    maturity = op_indices[-1]

    policy = SeniorDebtPolicy(
        policy_id="prf1_attack_policy", policy_version="1.0",
        sizing_mode=SeniorDebtSizingMode.DSCR_SCULPTED,
        target_dscr=1.2, maximum_gearing=None, annual_fixed_rate=0.05,
        periods_per_year=2, day_count_convention=DayCountConvention.ACT_365,
        repayment_start_period_index=repayment_start,
        maturity_period_index=maturity,
        convergence_tolerance_keur=1.0,
        convergence_relative_tolerance=0.001,
        maximum_iterations=300, permit_terminal_balloon=True,
    )
    sd_inputs = SeniorDebtInputs(
        eligible_project_cost_keur=100_000.0,
        initial_debt_guess_keur=60_000.0,
        period_rates=(), explicit_principal_schedule=None,
    )
    bank_case = DebtSizingCaseInput(
        production_yield_scenario=YieldScenario.P90_10Y,
        source_label="prf1_attack_bank_case",
    )
    try:
        from finco_parity.tax_reference_inputs import build_tax_policy, build_opening_loss_vintages
        tax_policy = build_tax_policy("tuho")
        vintages = build_opening_loss_vintages("tuho")
    except Exception:
        from financial_engine.inputs import TaxCalculationInput
        from financial_engine.policies.tax import TaxPolicy, CashTaxTiming, TaxBasisPeriodisation, TaxLossUtilisationGate
        tax_policy = TaxPolicy(
            cit_rate=0.25, cash_tax_timing=CashTaxTiming.TAX_YEAR_LAST_PERIOD,
            tax_basis_periodisation=TaxBasisPeriodisation.CALENDAR_YEAR,
            loss_utilisation_gate=TaxLossUtilisationGate.TAXABLE_INCOME_POSITIVE,
        )
        vintages = ()
    from financial_engine.inputs import TaxCalculationInput
    tax_input = TaxCalculationInput(
        policy=tax_policy, opening_loss_vintages=vintages,
        period_interest=(), period_adjustments=(),
    )
    return SeniorDebtModelInput(
        operating=base_op,
        tax=tax_input,
        senior_debt_policy=policy,
        senior_debt_inputs=sd_inputs,
        debt_sizing_case=bank_case,
    ), repayment_start, maturity


@pytest.fixture(scope="module")
def tuho_sd_model_input():
    """Cached SeniorDebtModelInput for production-boundary attack tests."""
    model_input, repayment_start, maturity = _make_tuho_senior_debt_model_input()
    return model_input, repayment_start, maturity


@pytest.fixture(scope="module")
def tuho_sd_model_senior_axis(tuho_sd_model_input):
    """Independently derived senior axis for the tuho attack fixture."""
    model_input, repayment_start, maturity = tuho_sd_model_input
    from financial_engine.orchestrator import run_operating_model
    base_result = run_operating_model(model_input.operating)
    return tuple(
        p.period_index for p in base_result.periods
        if p.is_operation
        and repayment_start <= p.period_index <= maturity
    )


class TestRealProductionBoundaryAttacks:
    """TASK 3: Real production-boundary attacks through run_senior_debt_model.

    Each attack uses monkeypatch to replace the solver result with an adversarial
    vector at the production consumer boundary, then verifies the exact error code.
    No partial financial result is returned after any failure.
    """

    def test_rb1_shifted_senior_interest_fails_at_production_boundary(
        self, tuho_sd_model_input, tuho_sd_model_senior_axis, monkeypatch
    ):
        """Attack 1: Shifted (same-shape) Senior interest through Senior orchestration path.
        Expected: AXIS_PERIOD_MISSING (supplied set differs from expected)."""
        model_input, _, _ = tuho_sd_model_input
        senior_axis = tuho_sd_model_senior_axis
        # Shift the senior_axis by +1 to get a same-size but wrong set
        shifted_axis = tuple(i + 1 for i in senior_axis)
        from financial_engine.senior_debt import solver as _sd_solver
        orig_solve = _sd_solver.solve_senior_debt

        def bad_solve(*args, **kwargs):
            result = orig_solve(*args, **kwargs)
            # Replace period_indices with shifted set, same length
            class _BadResult:
                def __getattr__(self, name):
                    return getattr(result, name)
            bad = _BadResult()
            object.__setattr__(bad, 'period_indices', shifted_axis)
            object.__setattr__(bad, 'senior_interest_keur', result.senior_interest_keur)
            object.__setattr__(bad, 'senior_debt_service_keur', result.senior_debt_service_keur)
            object.__setattr__(bad, 'senior_principal_keur', result.senior_principal_keur)
            object.__setattr__(bad, 'senior_debt_opening_keur', result.senior_debt_opening_keur)
            object.__setattr__(bad, 'senior_debt_closing_keur', result.senior_debt_closing_keur)
            object.__setattr__(bad, 'senior_dscr', result.senior_dscr)
            object.__setattr__(bad, 'debt_size_keur', result.debt_size_keur)
            object.__setattr__(bad, 'binding_constraint', result.binding_constraint)
            object.__setattr__(bad, 'diagnostics', result.diagnostics)
            return bad

        monkeypatch.setattr(_sd_solver, "solve_senior_debt", bad_solve)
        from financial_engine.orchestrator import run_senior_debt_model
        with pytest.raises(ValueError, match="AXIS_PERIOD_MISSING|AXIS_PERIOD_EXTRA|AXIS_LENGTH_MISMATCH"):
            run_senior_debt_model(model_input)

    def test_rb2_missing_senior_debt_service_period_fails(
        self, tuho_sd_model_input, tuho_sd_model_senior_axis, monkeypatch
    ):
        """Attack 2: Missing one period from Senior DS — AXIS_PERIOD_MISSING."""
        model_input, _, _ = tuho_sd_model_input
        senior_axis = tuho_sd_model_senior_axis
        truncated_axis = senior_axis[:-1]  # drop last period
        from financial_engine.senior_debt import solver as _sd_solver
        orig_solve = _sd_solver.solve_senior_debt

        def bad_solve(*args, **kwargs):
            result = orig_solve(*args, **kwargs)
            class _BadResult:
                def __getattr__(self, name):
                    return getattr(result, name)
            bad = _BadResult()
            object.__setattr__(bad, 'period_indices', truncated_axis)
            object.__setattr__(bad, 'senior_interest_keur', result.senior_interest_keur[:-1])
            object.__setattr__(bad, 'senior_debt_service_keur', result.senior_debt_service_keur[:-1])
            object.__setattr__(bad, 'senior_principal_keur', result.senior_principal_keur[:-1])
            object.__setattr__(bad, 'senior_debt_opening_keur', result.senior_debt_opening_keur[:-1])
            object.__setattr__(bad, 'senior_debt_closing_keur', result.senior_debt_closing_keur[:-1])
            object.__setattr__(bad, 'senior_dscr', result.senior_dscr[:-1])
            object.__setattr__(bad, 'debt_size_keur', result.debt_size_keur)
            object.__setattr__(bad, 'binding_constraint', result.binding_constraint)
            object.__setattr__(bad, 'diagnostics', result.diagnostics)
            return bad

        monkeypatch.setattr(_sd_solver, "solve_senior_debt", bad_solve)
        from financial_engine.orchestrator import run_senior_debt_model
        with pytest.raises(ValueError, match="AXIS_PERIOD_MISSING"):
            run_senior_debt_model(model_input)

    def test_rb3_extra_senior_period_fails(
        self, tuho_sd_model_input, tuho_sd_model_senior_axis, monkeypatch
    ):
        """Attack 3: Extra period in Senior DS — AXIS_PERIOD_EXTRA."""
        model_input, _, _ = tuho_sd_model_input
        senior_axis = tuho_sd_model_senior_axis
        extra_axis = senior_axis + (senior_axis[-1] + 1,)
        from financial_engine.senior_debt import solver as _sd_solver
        orig_solve = _sd_solver.solve_senior_debt

        def bad_solve(*args, **kwargs):
            result = orig_solve(*args, **kwargs)
            class _BadResult:
                def __getattr__(self, name):
                    return getattr(result, name)
            bad = _BadResult()
            object.__setattr__(bad, 'period_indices', extra_axis)
            object.__setattr__(bad, 'senior_interest_keur', result.senior_interest_keur + (0.0,))
            object.__setattr__(bad, 'senior_debt_service_keur', result.senior_debt_service_keur + (0.0,))
            object.__setattr__(bad, 'senior_principal_keur', result.senior_principal_keur + (0.0,))
            object.__setattr__(bad, 'senior_debt_opening_keur', result.senior_debt_opening_keur + (0.0,))
            object.__setattr__(bad, 'senior_debt_closing_keur', result.senior_debt_closing_keur + (0.0,))
            object.__setattr__(bad, 'senior_dscr', result.senior_dscr + (None,))
            object.__setattr__(bad, 'debt_size_keur', result.debt_size_keur)
            object.__setattr__(bad, 'binding_constraint', result.binding_constraint)
            object.__setattr__(bad, 'diagnostics', result.diagnostics)
            return bad

        monkeypatch.setattr(_sd_solver, "solve_senior_debt", bad_solve)
        from financial_engine.orchestrator import run_senior_debt_model
        with pytest.raises(ValueError, match="AXIS_PERIOD_EXTRA"):
            run_senior_debt_model(model_input)

    def test_rb4_reordered_senior_period_fails(
        self, tuho_sd_model_input, tuho_sd_model_senior_axis, monkeypatch
    ):
        """Attack 4: Reordered Senior period (same set, wrong order) — AXIS_PERIOD_SHIFTED."""
        model_input, _, _ = tuho_sd_model_input
        senior_axis = tuho_sd_model_senior_axis
        if len(senior_axis) < 2:
            pytest.skip("Need at least 2 periods to test reorder")
        # Swap first two periods
        reordered = (senior_axis[1], senior_axis[0]) + senior_axis[2:]
        from financial_engine.senior_debt import solver as _sd_solver
        orig_solve = _sd_solver.solve_senior_debt

        def bad_solve(*args, **kwargs):
            result = orig_solve(*args, **kwargs)
            class _BadResult:
                def __getattr__(self, name):
                    return getattr(result, name)
            bad = _BadResult()
            object.__setattr__(bad, 'period_indices', reordered)
            object.__setattr__(bad, 'senior_interest_keur', result.senior_interest_keur)
            object.__setattr__(bad, 'senior_debt_service_keur', result.senior_debt_service_keur)
            object.__setattr__(bad, 'senior_principal_keur', result.senior_principal_keur)
            object.__setattr__(bad, 'senior_debt_opening_keur', result.senior_debt_opening_keur)
            object.__setattr__(bad, 'senior_debt_closing_keur', result.senior_debt_closing_keur)
            object.__setattr__(bad, 'senior_dscr', result.senior_dscr)
            object.__setattr__(bad, 'debt_size_keur', result.debt_size_keur)
            object.__setattr__(bad, 'binding_constraint', result.binding_constraint)
            object.__setattr__(bad, 'diagnostics', result.diagnostics)
            return bad

        monkeypatch.setattr(_sd_solver, "solve_senior_debt", bad_solve)
        from financial_engine.orchestrator import run_senior_debt_model
        with pytest.raises(ValueError, match="AXIS_PERIOD_SHIFTED"):
            run_senior_debt_model(model_input)

    def test_rb5_duplicate_raw_senior_period_fails(
        self, tuho_sd_model_input, tuho_sd_model_senior_axis, monkeypatch
    ):
        """Attack 5: Duplicate raw Senior period before dict construction — AXIS_PERIOD_DUPLICATE."""
        model_input, _, _ = tuho_sd_model_input
        senior_axis = tuho_sd_model_senior_axis
        dup_axis = (senior_axis[0], senior_axis[0]) + senior_axis[1:]
        from financial_engine.senior_debt import solver as _sd_solver
        orig_solve = _sd_solver.solve_senior_debt

        def bad_solve(*args, **kwargs):
            result = orig_solve(*args, **kwargs)
            class _BadResult:
                def __getattr__(self, name):
                    return getattr(result, name)
            bad = _BadResult()
            object.__setattr__(bad, 'period_indices', dup_axis)
            object.__setattr__(bad, 'senior_interest_keur', (0.0,) + result.senior_interest_keur)
            object.__setattr__(bad, 'senior_debt_service_keur', (0.0,) + result.senior_debt_service_keur)
            object.__setattr__(bad, 'senior_principal_keur', (0.0,) + result.senior_principal_keur)
            object.__setattr__(bad, 'senior_debt_opening_keur', (0.0,) + result.senior_debt_opening_keur)
            object.__setattr__(bad, 'senior_debt_closing_keur', (0.0,) + result.senior_debt_closing_keur)
            object.__setattr__(bad, 'senior_dscr', (None,) + result.senior_dscr)
            object.__setattr__(bad, 'debt_size_keur', result.debt_size_keur)
            object.__setattr__(bad, 'binding_constraint', result.binding_constraint)
            object.__setattr__(bad, 'diagnostics', result.diagnostics)
            return bad

        monkeypatch.setattr(_sd_solver, "solve_senior_debt", bad_solve)
        from financial_engine.orchestrator import run_senior_debt_model
        with pytest.raises(ValueError, match="AXIS_PERIOD_DUPLICATE"):
            run_senior_debt_model(model_input)

    def test_rb6_shifted_full_axis_cfads_fails(
        self, tuho_sd_model_input, monkeypatch
    ):
        """Attack 6: Shifted full-axis CFADS at Base CFADS boundary — AXIS_PERIOD_MISSING.

        Injects a TaxAndCfadsSchedules whose period_indices are shifted by +1 at the
        _assemble_post_senior_cash_schedules boundary via monkeypatching
        _assemble_tax_cfads_schedules in the orchestrator.
        """
        model_input, _, _ = tuho_sd_model_input
        import financial_engine.orchestrator as _orch_module
        orig_assemble = _orch_module._assemble_tax_cfads_schedules

        def bad_assemble(base_result, tax_result, period_results, cfads_results):
            schedules = orig_assemble(base_result, tax_result, period_results, cfads_results)
            # Replace period_indices with axis shifted by +1
            import dataclasses as _dc
            shifted = tuple(i + 1 for i in schedules.period_indices)
            return _dc.replace(schedules, period_indices=shifted)

        monkeypatch.setattr(_orch_module, "_assemble_tax_cfads_schedules", bad_assemble)
        from financial_engine.orchestrator import run_senior_debt_model
        with pytest.raises(ValueError, match="AXIS_PERIOD_MISSING|AXIS_PERIOD_EXTRA|AXIS_PERIOD_SHIFTED"):
            run_senior_debt_model(model_input)

    def test_rb9_no_partial_financial_result_returned_after_failure(
        self, tuho_sd_model_input, tuho_sd_model_senior_axis, monkeypatch
    ):
        """Attack 10: Verify no partial result is returned after axis failure.
        The orchestrator must raise, never return a ProjectModelResult."""
        model_input, _, _ = tuho_sd_model_input
        senior_axis = tuho_sd_model_senior_axis
        shifted = tuple(i + 1 for i in senior_axis)
        from financial_engine.senior_debt import solver as _sd_solver
        orig_solve = _sd_solver.solve_senior_debt

        def bad_solve(*args, **kwargs):
            result = orig_solve(*args, **kwargs)
            class _BadResult:
                def __getattr__(self, name):
                    return getattr(result, name)
            bad = _BadResult()
            object.__setattr__(bad, 'period_indices', shifted)
            object.__setattr__(bad, 'senior_interest_keur', result.senior_interest_keur)
            object.__setattr__(bad, 'senior_debt_service_keur', result.senior_debt_service_keur)
            object.__setattr__(bad, 'senior_principal_keur', result.senior_principal_keur)
            object.__setattr__(bad, 'senior_debt_opening_keur', result.senior_debt_opening_keur)
            object.__setattr__(bad, 'senior_debt_closing_keur', result.senior_debt_closing_keur)
            object.__setattr__(bad, 'senior_dscr', result.senior_dscr)
            object.__setattr__(bad, 'debt_size_keur', result.debt_size_keur)
            object.__setattr__(bad, 'binding_constraint', result.binding_constraint)
            object.__setattr__(bad, 'diagnostics', result.diagnostics)
            return bad

        monkeypatch.setattr(_sd_solver, "solve_senior_debt", bad_solve)
        from financial_engine.orchestrator import run_senior_debt_model
        from financial_engine.results import ProjectModelResult
        returned = None
        try:
            returned = run_senior_debt_model(model_input)
        except ValueError:
            pass
        assert returned is None, (
            "Axis failure must raise ValueError; no ProjectModelResult must be returned"
        )


# ---------------------------------------------------------------------------
# TASK 5: Classification governance
# ---------------------------------------------------------------------------

def test_correction_c_classification_status():
    """Correction C (TASK 5): Documents implemented attack categories.

    EXACT_MEMBERSHIP_CLOSED and FREEZE_COMPLETE are NOT claimed here.
    Classification awaits independent exact-head CI review.

    Correction C attack categories (proof tests follow in this file):
      rc_bank1 — Bank-only shifted CFADS → BANK_AXIS_PERIOD_SHIFTED
      rc_bank2 — Bank-only missing tax period → BANK_AXIS_PERIOD_MISSING
      rc_bank3 — Bank-only extra CFADS period → BANK_AXIS_PERIOD_EXTRA
      rc_bank4 — Duplicate raw Bank tax period → BANK_AXIS_PERIOD_DUPLICATE
      rc_bank5 — Duplicate raw Bank CFADS period → BANK_AXIS_PERIOD_DUPLICATE
      rc_bank6 — Base/Bank axes different lengths → BASE_BANK_AXIS_MISMATCH
      rc_wf1   — Shifted SHL at waterfall consumer → AXIS_PERIOD_MISSING/SHIFTED
      rc_sr1   — Shifted post-Senior at sponsor-return consumer → AXIS_PERIOD_MISSING
      rc_cod1  — Fake month-start first operation whose start is not COD → error
      rc_cod2  — Coordinated wrong leap + adjusted fraction → reconciliation error
      rc_np    — No partial waterfall/sponsor result after failure
    """
    # Proof is provided by the attack tests below; this test is the registry.
    attacks_implemented = [
        "rc_bank1_shifted_cfads",
        "rc_bank2_missing_tax_period",
        "rc_bank3_extra_cfads_period",
        "rc_bank4_duplicate_bank_tax_period",
        "rc_bank5_duplicate_bank_cfads_period",
        "rc_bank6_base_bank_axis_mismatch",
        "rc_wf1_shifted_shl_at_waterfall",
        "rc_sr1_shifted_post_senior_at_sponsor_return",
        "rc_cod1_fake_month_start_not_cod",
        "rc_cod2_coordinated_leap_fraction",
        "rc_np_no_partial_waterfall_after_failure",
    ]
    assert len(attacks_implemented) == 11, "Update this registry when attacks change"


# ---------------------------------------------------------------------------
# Correction C TASK 2: Bank-only axis attacks
# ---------------------------------------------------------------------------

def _make_mock_bank_phase2a(period_indices):
    """Build a minimal mock bank_phase2a_result for unit-testing _build_debt_sizing_schedules_from_bank."""
    from financial_engine.results import OperatingPeriodResult, OperatingSchedules
    from datetime import date, timedelta

    start = date(2028, 7, 1)
    periods = []
    for i, idx in enumerate(period_indices):
        end = start + timedelta(days=182)
        is_constr = (i == 0)
        periods.append(OperatingPeriodResult(
            period_index=idx, period_start=start, period_end=end,
            year_index=float(0 if is_constr else (i // 2)),
            period_in_year=float((i % 2) + 1),
            is_construction=is_constr, is_operation=not is_constr,
            is_ppa_active=not is_constr,
            days_in_period=182, day_fraction=182 / 365.0,
            production_mwh=100.0, revenue_keur=10.0, opex_keur=5.0,
            ebitda_keur=5.0, book_depreciation_keur=1.0, tax_depreciation_keur=1.0,
            ebit_keur=4.0,
        ))
        start = end

    op_indices = tuple(p.period_index for p in periods if p.is_operation)
    n_op = len(op_indices)

    class _MockSched:
        period_indices = op_indices
        production_mwh = tuple(100.0 for _ in op_indices)
        revenue_keur = tuple(10.0 for _ in op_indices)
        opex_keur = tuple(5.0 for _ in op_indices)
        ebitda_keur = tuple(5.0 for _ in op_indices)
        bank_cfads_keur = tuple(4.0 for _ in op_indices)

    class _MockResult:
        pass

    r = _MockResult()
    r.periods = tuple(periods)
    r.operating_schedules = _MockSched()
    return r


def _make_mock_bank_tax(period_indices):
    """Build a minimal mock bank tax result."""
    class _MockPr:
        def __init__(self, idx):
            self.period_index = idx
            self.cash_tax_keur = 0.5

    class _MockTax:
        pass

    t = _MockTax()
    t.period_results = tuple(_MockPr(idx) for idx in period_indices)
    t.annual_results = ()
    t.terminal_unpaid_tax_keur = 0.0
    return t


def _make_mock_bank_cfads(period_indices):
    """Build minimal mock bank CFADS results."""
    class _MockCr:
        def __init__(self, idx):
            self.period_index = idx
            self.cfads_keur = 4.0
            self.ebitda_keur = 5.0
    return tuple(_MockCr(idx) for idx in period_indices)


def _make_mock_senior_result(senior_indices):
    """Build minimal mock senior debt result."""
    class _MockSd:
        pass
    sd = _MockSd()
    sd.period_indices = tuple(senior_indices)
    sd.senior_debt_service_keur = tuple(2.0 for _ in senior_indices)
    sd.senior_dscr = tuple(2.0 for _ in senior_indices)
    return sd


class TestBankAxisAttacks:
    """TASK 2: Bank tax and CFADS axis validation at _build_debt_sizing_schedules_from_bank.

    Each attack calls _build_debt_sizing_schedules_from_bank directly with
    crafted (corrupted) mock inputs and verifies the exact deterministic error code.
    No partial DebtSizingSchedules is returned after any failure.
    """

    def _call_bank(self, bank_indices, tax_indices, cfads_indices, senior_indices, base_periods=None):
        """Helper: call _build_debt_sizing_schedules_from_bank with mock args."""
        from financial_engine.orchestrator import _build_debt_sizing_schedules_from_bank
        bank_phase2a = _make_mock_bank_phase2a(bank_indices)
        tax_result = _make_mock_bank_tax(tax_indices)
        cfads_results = _make_mock_bank_cfads(cfads_indices)
        sd_result = _make_mock_senior_result(senior_indices)
        return _build_debt_sizing_schedules_from_bank(
            bank_phase2a_result=bank_phase2a,
            final_bank_tax_result=tax_result,
            final_bank_cfads_results=cfads_results,
            senior_debt_result=sd_result,
            senior_axis=tuple(senior_indices),
            base_periods=base_periods,
        )

    def test_rc_bank_valid_passes(self):
        """Sanity: valid Bank axis round-trip succeeds."""
        indices = (0, 1, 2, 3, 4)
        senior = (1, 2, 3, 4)
        result = self._call_bank(indices, indices, indices, senior)
        assert result is not None

    def test_rc_bank1_shifted_cfads(self):
        """Bank CFADS axis shifted vs Bank full axis → BANK_AXIS_PERIOD_MISSING."""
        bank_indices = (0, 1, 2, 3, 4)
        shifted_cfads = (1, 2, 3, 4, 5)  # shifted by +1
        tax_indices = bank_indices
        senior = (1, 2, 3, 4)
        with pytest.raises(ValueError, match="BANK_AXIS_PERIOD_MISSING"):
            self._call_bank(bank_indices, tax_indices, shifted_cfads, senior)

    def test_rc_bank2_missing_tax_period(self):
        """Bank tax result missing a period → BANK_AXIS_PERIOD_MISSING."""
        bank_indices = (0, 1, 2, 3, 4)
        truncated_tax = (0, 1, 2, 3)  # missing 4
        cfads_indices = bank_indices
        senior = (1, 2, 3, 4)
        with pytest.raises(ValueError, match="BANK_AXIS_PERIOD_MISSING"):
            self._call_bank(bank_indices, truncated_tax, cfads_indices, senior)

    def test_rc_bank3_extra_cfads_period(self):
        """Bank CFADS extra period → BANK_AXIS_PERIOD_EXTRA."""
        bank_indices = (0, 1, 2, 3, 4)
        extra_cfads = (0, 1, 2, 3, 4, 9999)
        tax_indices = bank_indices
        senior = (1, 2, 3, 4)
        with pytest.raises(ValueError, match="BANK_AXIS_PERIOD_EXTRA"):
            self._call_bank(bank_indices, tax_indices, extra_cfads, senior)

    def test_rc_bank4_duplicate_bank_tax_period(self):
        """Duplicate raw Bank tax period → BANK_AXIS_PERIOD_DUPLICATE."""
        bank_indices = (0, 1, 2, 3, 4)
        dup_tax = (0, 0, 1, 2, 3, 4)  # duplicate 0
        cfads_indices = bank_indices
        senior = (1, 2, 3, 4)
        with pytest.raises(ValueError, match="BANK_AXIS_PERIOD_DUPLICATE"):
            self._call_bank(bank_indices, dup_tax, cfads_indices, senior)

    def test_rc_bank5_duplicate_bank_cfads_period(self):
        """Duplicate raw Bank CFADS period → BANK_AXIS_PERIOD_DUPLICATE."""
        bank_indices = (0, 1, 2, 3, 4)
        dup_cfads = (0, 1, 1, 2, 3, 4)  # duplicate 1
        tax_indices = bank_indices
        senior = (1, 2, 3, 4)
        with pytest.raises(ValueError, match="BANK_AXIS_PERIOD_DUPLICATE"):
            self._call_bank(bank_indices, tax_indices, dup_cfads, senior)

    def test_rc_bank6_base_bank_axis_mismatch(self):
        """Base and Bank axes with different dates → BASE_BANK_AXIS_MISMATCH."""
        from datetime import date, timedelta
        from financial_engine.results import OperatingPeriodResult

        bank_indices = (0, 1, 2, 3, 4)
        # Build a base_periods with DIFFERENT period_start for period 1
        base_start = date(2028, 7, 1)
        base_periods_list = []
        s = base_start
        for i, idx in enumerate(bank_indices):
            e = s + timedelta(days=182)
            is_constr = (i == 0)
            base_periods_list.append(OperatingPeriodResult(
                period_index=idx, period_start=s, period_end=e,
                year_index=float(0 if is_constr else (i // 2)),
                period_in_year=float((i % 2) + 1),
                is_construction=is_constr, is_operation=not is_constr,
                is_ppa_active=not is_constr,
                days_in_period=182, day_fraction=182 / 365.0,
                production_mwh=0.0, revenue_keur=0.0, opex_keur=0.0,
                ebitda_keur=0.0, book_depreciation_keur=0.0, tax_depreciation_keur=0.0,
                ebit_keur=0.0,
            ))
            s = e
        # The bank phase2a will have different period_start (different start date)
        # We shift the bank by 1 day
        bank_phase2a = _make_mock_bank_phase2a(bank_indices)
        # Manually adjust the first bank period start by 1 day to create mismatch
        import dataclasses as _dc
        bad_first = _dc.replace(
            bank_phase2a.periods[0],
            period_start=bank_phase2a.periods[0].period_start + timedelta(days=1),
        )
        bank_phase2a.periods = (bad_first,) + bank_phase2a.periods[1:]

        tax_indices = bank_indices
        cfads_indices = bank_indices
        senior = (1, 2, 3, 4)
        from financial_engine.orchestrator import _build_debt_sizing_schedules_from_bank
        tax_result = _make_mock_bank_tax(tax_indices)
        cfads_results = _make_mock_bank_cfads(cfads_indices)
        sd_result = _make_mock_senior_result(senior)
        with pytest.raises(ValueError, match="BASE_BANK_AXIS_MISMATCH"):
            _build_debt_sizing_schedules_from_bank(
                bank_phase2a_result=bank_phase2a,
                final_bank_tax_result=tax_result,
                final_bank_cfads_results=cfads_results,
                senior_debt_result=sd_result,
                senior_axis=tuple(senior),
                base_periods=tuple(base_periods_list),
            )


# ---------------------------------------------------------------------------
# Correction C TASK 4: Downstream E2E attacks — waterfall and sponsor returns
# ---------------------------------------------------------------------------

class TestDownstreamConsumerAttacks:
    """TASK 4: Real production-boundary attacks at waterfall and sponsor-return consumers."""

    def test_rc_wf1_shifted_shl_at_waterfall(self, monkeypatch):
        """Shifted SHL schedule at shareholder-waterfall consumption.

        Monkeypatches compute_shareholder_loan_schedules to return a schedule
        whose period_indices are shifted by +1. The waterfall now validates
        SHL against the independently-derived full axis and must raise an error.
        No partial waterfall result is returned.
        """
        from app.project_factories import create_default_solar_project
        from financial_engine.shareholder_waterfall.model import run_project_shareholder_waterfall_model
        import financial_engine.shl.production as _shl_prod

        project = create_default_solar_project()
        orig_compute_shl = _shl_prod.compute_shareholder_loan_schedules

        call_count = [0]

        def bad_shl(periods, shl_model_input, available_cash, diagnostics=None):
            result = orig_compute_shl(periods, shl_model_input, available_cash, diagnostics=diagnostics)
            call_count[0] += 1
            # Only corrupt the second call (gated SHL in waterfall)
            if call_count[0] == 2:
                import dataclasses as _dc
                shifted = tuple(i + 1 for i in result.period_indices)
                return _dc.replace(result, period_indices=shifted)
            return result

        monkeypatch.setattr(_shl_prod, "compute_shareholder_loan_schedules", bad_shl)
        with pytest.raises(ValueError, match="AXIS_PERIOD_MISSING|AXIS_PERIOD_EXTRA|AXIS_PERIOD_SHIFTED|AXIS_LENGTH_MISMATCH"):
            run_project_shareholder_waterfall_model(project)

    def test_rc_sr1_shifted_post_senior_at_sponsor_return(self, monkeypatch):
        """Shifted post-Senior schedule at sponsor-return consumption.

        Monkeypatches run_project_financing_model to return a result with a
        corrupted post_senior_cash.period_indices. Sponsor returns validates
        this against the independently-derived full axis and must raise an error.
        """
        from app.project_factories import create_default_solar_project
        from financial_engine.sponsor_returns.model import run_project_sponsor_returns_model
        import financial_engine.sponsor_returns.model as _sr_mod
        import dataclasses as _dc

        project = create_default_solar_project()
        orig_run_financing = _sr_mod.run_project_financing_model

        def bad_financing(project_inputs, **kwargs):
            result = orig_run_financing(project_inputs, **kwargs)
            model = result.project_model_result
            psc = model.post_senior_cash
            if psc is None:
                return result
            # Shift post_senior_cash period_indices by +1
            shifted_psc = _dc.replace(
                psc,
                period_indices=tuple(i + 1 for i in psc.period_indices),
            )
            bad_model = _dc.replace(model, post_senior_cash=shifted_psc)
            return _dc.replace(result, project_model_result=bad_model)

        monkeypatch.setattr(_sr_mod, "run_project_financing_model", bad_financing)
        with pytest.raises(ValueError, match="AXIS_PERIOD_MISSING|AXIS_PERIOD_EXTRA|AXIS_PERIOD_SHIFTED|AXIS_LENGTH_MISMATCH"):
            run_project_sponsor_returns_model(project)

    def test_rc_np_no_partial_waterfall_after_failure(self, monkeypatch):
        """No partial waterfall result returned after any axis failure.

        Verifies via strict pytest.raises that run_project_shareholder_waterfall_model
        raises ValueError and never returns a result when SHL axis is corrupt.
        The extra-period attack triggers AXIS_PERIOD_EXTRA.
        """
        from app.project_factories import create_default_solar_project
        from financial_engine.shareholder_waterfall.model import run_project_shareholder_waterfall_model
        import financial_engine.shl.production as _shl_prod

        project = create_default_solar_project()
        orig_compute_shl = _shl_prod.compute_shareholder_loan_schedules
        call_count = [0]

        def bad_shl(periods, shl_model_input, available_cash, diagnostics=None):
            result = orig_compute_shl(periods, shl_model_input, available_cash, diagnostics=diagnostics)
            call_count[0] += 1
            if call_count[0] == 2:
                import dataclasses as _dc
                # Extra period — triggers AXIS_PERIOD_EXTRA
                return _dc.replace(
                    result,
                    period_indices=result.period_indices + (9999,),
                    shl_opening_keur=result.shl_opening_keur + (0.0,),
                    shl_gross_interest_keur=result.shl_gross_interest_keur + (0.0,),
                    shl_cash_interest_keur=result.shl_cash_interest_keur + (0.0,),
                    shl_pik_interest_keur=result.shl_pik_interest_keur + (0.0,),
                    shl_principal_keur=result.shl_principal_keur + (0.0,),
                    shl_closing_keur=result.shl_closing_keur + (0.0,),
                    shl_debt_service_keur=result.shl_debt_service_keur + (0.0,),
                )
            return result

        monkeypatch.setattr(_shl_prod, "compute_shareholder_loan_schedules", bad_shl)
        # Strict: must raise ValueError with AXIS_PERIOD_EXTRA; no partial result returned.
        with pytest.raises(ValueError, match="AXIS_PERIOD_EXTRA"):
            run_project_shareholder_waterfall_model(project)


# ---------------------------------------------------------------------------
# Correction C TASK 3: COD-authoritative day-count attacks
# ---------------------------------------------------------------------------

def test_rc_cod1_fake_month_start_not_cod_is_rejected():
    """Fake month-start first operating period whose start is not the actual COD.

    When cod_date is provided to validate_canonical_period_axis(), the +1
    exception MUST require start_date == cod_date exactly.  A period that
    merely starts on day-1-of-month but is NOT the COD must be rejected.
    """
    from datetime import date, timedelta
    # Build an axis where COD is 2030-01-01 but we supply a first operating
    # period starting on 2030-02-01 (also day==1, but NOT the COD) with +1 days.
    constr = PeriodMeta(
        index=0, start_date=date(2029, 7, 1), end_date=date(2030, 1, 1),
        year_index=0, period_in_year=1, is_construction=True, is_operation=False,
        is_ppa_active=False, days_in_period=184,
        day_fraction=184 / 365.0, is_leap_year=False,
    )
    # First operating period starts 2030-02-01 (day==1, but COD is 2030-01-01)
    op_start = date(2030, 2, 1)
    op_end = date(2030, 6, 30)
    cal_days = (op_end - op_start).days  # 149
    is_leap = False
    denom = 365.0
    # Insert a gap-filling period between construction end (2030-01-01) and op_start
    # — actually we need continuity. Let's make construction end at 2030-02-01.
    constr2 = PeriodMeta(
        index=0, start_date=date(2029, 7, 1), end_date=date(2030, 2, 1),
        year_index=0, period_in_year=1, is_construction=True, is_operation=False,
        is_ppa_active=False, days_in_period=215,
        day_fraction=215 / 365.0, is_leap_year=False,
    )
    op1_bad = PeriodMeta(
        index=1, start_date=op_start, end_date=op_end,
        year_index=1, period_in_year=1, is_construction=False, is_operation=True,
        is_ppa_active=True,
        days_in_period=cal_days + 1,  # +1 on a fake-COD period — should be rejected
        day_fraction=(cal_days + 1) / denom,
        is_leap_year=is_leap, operating_period_index=0, operating_year_index=1,
    )
    # cod_date = 2030-01-01, but op_start = 2030-02-01 → should reject +1
    with pytest.raises(ValueError, match="PERIOD_AXIS_DAYS_IN_PERIOD_MISMATCH"):
        validate_canonical_period_axis((constr2, op1_bad), cod_date=date(2030, 1, 1))


def test_rc_cod2_coordinated_leap_fraction_rejected():
    """Coordinated wrong leap flag + recomputed day fraction must fail (Correction D).

    Attack: flip is_leap_year AND recompute day_fraction to be consistent with the
    wrong flag.  Prior to Correction D this coordinated mutation passed because the
    validator derived the approved denominator from is_leap_year itself (a tautology).

    Correction D derives the denominator INDEPENDENTLY from end_date, so the flipped
    is_leap_year does not match the independently-derived expected value →
    PERIOD_AXIS_IS_LEAP_YEAR_MISMATCH is raised even when day_fraction is internally
    consistent with the wrong flag.
    """
    periods = _make_periods(1, 4)
    op = periods[1]  # first operating period
    # Coordinated attack: flip is_leap_year AND recompute day_fraction with wrong denom.
    # Both fields are mutated consistently so the (old) is_leap_year-derived check passes.
    flipped_leap = not op.is_leap_year
    wrong_denom = 366.0 if flipped_leap else 365.0
    bad = dataclasses.replace(
        op,
        is_leap_year=flipped_leap,
        day_fraction=op.days_in_period / wrong_denom,  # consistent with wrong flag
    )
    corrupted = (periods[0],) + (bad,) + periods[2:]
    # Correction D: the validator derives the denominator independently from end_date.
    # is_leap_year (flipped) != independently-derived expected → IS_LEAP_YEAR_MISMATCH.
    with pytest.raises(ValueError, match=r"^PERIOD_AXIS_IS_LEAP_YEAR_MISMATCH(?:\b|:)"):
        validate_canonical_period_axis(corrupted)


def test_rc_tuho_cod_inclusive_first_operation_passes():
    """Valid TUHO COD-inclusive first operation PASSES when cod_date is provided.

    TUHO: COD = 2030-01-01 (month start), first operating period starts 2030-01-01,
    ends 2030-06-30, days = 181 (calendar: 180 + 1 COD-inclusive).
    """
    from financial_engine.orchestrator import _build_period_engine
    from financial_engine.adapters.project_inputs import from_project_inputs
    project = create_default_tuho_wind1()
    clean = from_project_inputs(project)
    engine = _build_period_engine(clean)
    periods = engine.periods()
    # Validation with the engine's COD must pass
    validate_canonical_period_axis(periods, cod_date=engine.cod)
    operating = tuple(p for p in periods if p.is_operation)
    assert operating[0].start_date == engine.cod
    assert engine.cod.day == 1
    # The +1 was applied
    calendar_days = (operating[0].end_date - operating[0].start_date).days
    assert operating[0].days_in_period == calendar_days + 1
