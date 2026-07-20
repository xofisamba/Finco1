"""tests.test_recon_fix02b_hierarchical_opex_engine

Generic hierarchical OPEX engine tests.

Structure:
  1. Basic construction & sanity
  2. Validation — every error code
  3. Activation: ALWAYS / MANUAL / SENIOR_DEBT_TENOR_ACTIVE
  4. Escalation: YEAR_1_AS_BASE / PRE_OPERATION_BASE
  5. Annual calculation — SUBITEM_SUM
  6. Annual calculation — PERCENTAGE_OF_SELECTED_BASES (contingency)
  7. Period calculation — basic, H1/H2 overrides
  8. Identity independence
  9. Oborovo structural proof — B.01–B.13 × Y1–Y30 (390 + 30 parametrized)
 10. Specific behaviour: B.02, B.07, B.08, B.10, B.11, B.12, B.13

Production code must not import finco_recon or fixture files.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from finco_core.opex.hierarchical import (
    OpexActivationMode,
    OpexActivationSchedule,
    OpexAmountBasis,
    OpexCalculationContext,
    OpexCategoryCalculationType,
    OpexCategoryInput,
    OpexEscalationConvention,
    OpexModelInput,
    OpexSubitemInput,
    OpexValidationIssue,
    ValidationSeverity,
    compute_annual,
    compute_periods,
    has_errors,
    validate_opex_model_input,
)

# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------


def _simple_model(*items, extra_categories=()) -> OpexModelInput:
    """Build a minimal OpexModelInput with a single 'CAT' category."""
    cat = OpexCategoryInput(
        code="CAT",
        name="Test Category",
        inflation_rate=0.0,
        subitems=tuple(items),
    )
    return OpexModelInput(categories=(cat, *extra_categories))


def _always(code: str, amount: float) -> OpexSubitemInput:
    return OpexSubitemInput(code=code, name=code, base_amount_keur=amount)


def _manual(
    code: str,
    amount: float,
    flags: tuple[bool, ...],
    overrides: tuple[tuple[tuple[int, int], bool], ...] = (),
) -> OpexSubitemInput:
    return OpexSubitemInput(
        code=code,
        name=code,
        base_amount_keur=amount,
        activation_mode=OpexActivationMode.MANUAL,
        activation_schedule=OpexActivationSchedule(
            annual_flags=flags, period_overrides=overrides
        ),
    )


def _tenor_active(code: str, amount: float) -> OpexSubitemInput:
    return OpexSubitemInput(
        code=code,
        name=code,
        base_amount_keur=amount,
        activation_mode=OpexActivationMode.SENIOR_DEBT_TENOR_ACTIVE,
    )


_CTX_ZERO = OpexCalculationContext()
_CTX_TENOR14 = OpexCalculationContext(senior_debt_tenor_years=14)

HORIZON = 30


@dataclass
class _FakePeriod:
    """Minimal stand-in for PeriodMeta used in period tests."""

    index: int
    year_index: int
    period_in_year: int
    day_fraction: float
    is_operation: bool = True


def _annual_periods(n_years: int) -> list[_FakePeriod]:
    """Return n_years full-year operation periods."""
    return [
        _FakePeriod(index=i, year_index=i, period_in_year=1, day_fraction=1.0)
        for i in range(1, n_years + 1)
    ]


def _semi_periods(n_years: int) -> list[_FakePeriod]:
    """Return 2 × n_years equal semestrial operation periods."""
    periods = []
    idx = 1
    for yr in range(1, n_years + 1):
        periods.append(_FakePeriod(index=idx, year_index=yr, period_in_year=1, day_fraction=0.5))
        idx += 1
        periods.append(_FakePeriod(index=idx, year_index=yr, period_in_year=2, day_fraction=0.5))
        idx += 1
    return periods


# ---------------------------------------------------------------------------
# 1. Basic construction & sanity
# ---------------------------------------------------------------------------


def test_model_input_is_frozen():
    model = _simple_model(_always("A", 100.0))
    with pytest.raises((TypeError, AttributeError)):
        model.categories = ()  # type: ignore[misc]


def test_activation_schedule_is_frozen():
    sched = OpexActivationSchedule(annual_flags=(True, False))
    with pytest.raises((TypeError, AttributeError)):
        sched.annual_flags = ()  # type: ignore[misc]


def test_compute_annual_returns_correct_year_count():
    model = _simple_model(_always("A", 100.0))
    results = compute_annual(model, _CTX_ZERO, horizon_years=5)
    assert len(results) == 5


def test_compute_annual_year_indices():
    model = _simple_model(_always("A", 100.0))
    results = compute_annual(model, _CTX_ZERO, horizon_years=3)
    assert [r.year_index for r in results] == [1, 2, 3]


def test_always_active_flat_no_inflation():
    model = _simple_model(_always("A", 200.0))
    results = compute_annual(model, _CTX_ZERO, horizon_years=3)
    assert all(abs(r.total_keur - 200.0) < 1e-9 for r in results)


def test_two_subitems_summed():
    model = _simple_model(_always("A", 100.0), _always("B", 50.0))
    results = compute_annual(model, _CTX_ZERO, horizon_years=1)
    assert abs(results[0].total_keur - 150.0) < 1e-9


def test_subitem_result_detail_populated():
    model = _simple_model(_always("A", 123.0))
    results = compute_annual(model, _CTX_ZERO, horizon_years=1)
    cat = results[0].categories[0]
    assert len(cat.subitems) == 1
    si = cat.subitems[0]
    assert si.code == "A"
    assert si.active is True
    assert abs(si.annual_keur - 123.0) < 1e-9


# ---------------------------------------------------------------------------
# 2. Validation — error codes
# ---------------------------------------------------------------------------


def test_validate_passes_minimal_model():
    model = _simple_model(_always("A", 10.0))
    issues = validate_opex_model_input(model, _CTX_ZERO, horizon_years=5)
    assert not has_errors(issues)


def test_validate_OPX001_duplicate_category_code():
    cat_a = OpexCategoryInput(code="CAT", name="A", subitems=(_always("x", 1.0),))
    cat_b = OpexCategoryInput(code="CAT", name="B", subitems=(_always("y", 1.0),))
    model = OpexModelInput(categories=(cat_a, cat_b))
    issues = validate_opex_model_input(model, _CTX_ZERO, horizon_years=5)
    assert any(i.code == "OPX001" and i.severity == ValidationSeverity.ERROR for i in issues)


def test_validate_OPX010_duplicate_subitem_code():
    cat = OpexCategoryInput(
        code="C",
        name="C",
        subitems=(_always("dup", 1.0), _always("dup", 2.0)),
    )
    model = OpexModelInput(categories=(cat,))
    issues = validate_opex_model_input(model, _CTX_ZERO, horizon_years=5)
    assert any(i.code == "OPX010" for i in issues)


def test_validate_OPX011_unsupported_amount_basis():
    si = OpexSubitemInput(
        code="X", name="X", base_amount_keur=1.0,
        amount_basis=OpexAmountBasis.ONE_OFF,
    )
    model = _simple_model(si)
    issues = validate_opex_model_input(model, _CTX_ZERO, horizon_years=5)
    assert any(i.code == "OPX011" for i in issues)


def test_validate_OPX020_tenor_active_without_tenor():
    model = _simple_model(_tenor_active("T", 100.0))
    issues = validate_opex_model_input(model, _CTX_ZERO, horizon_years=5)
    assert any(i.code == "OPX020" for i in issues)


def test_validate_OPX020_passes_with_tenor():
    model = _simple_model(_tenor_active("T", 100.0))
    issues = validate_opex_model_input(model, _CTX_TENOR14, horizon_years=5)
    assert not any(i.code == "OPX020" for i in issues)


def test_validate_OPX030_percentage_with_subitems():
    cat = OpexCategoryInput(
        code="P",
        name="P",
        calculation_type=OpexCategoryCalculationType.PERCENTAGE_OF_SELECTED_BASES,
        percentage_rate=0.04,
        percentage_base_codes=("X",),
        subitems=(_always("s", 1.0),),
    )
    model = OpexModelInput(categories=(cat,))
    issues = validate_opex_model_input(model, _CTX_ZERO, horizon_years=5)
    assert any(i.code == "OPX030" for i in issues)


def test_validate_OPX031_percentage_no_base_codes():
    cat = OpexCategoryInput(
        code="P", name="P",
        calculation_type=OpexCategoryCalculationType.PERCENTAGE_OF_SELECTED_BASES,
        percentage_rate=0.04,
    )
    model = OpexModelInput(categories=(cat,))
    issues = validate_opex_model_input(model, _CTX_ZERO, horizon_years=5)
    assert any(i.code == "OPX031" for i in issues)


def test_validate_OPX033_self_reference():
    cat = OpexCategoryInput(
        code="P", name="P",
        calculation_type=OpexCategoryCalculationType.PERCENTAGE_OF_SELECTED_BASES,
        percentage_rate=0.04,
        percentage_base_codes=("P",),
    )
    model = OpexModelInput(categories=(cat,))
    issues = validate_opex_model_input(model, _CTX_ZERO, horizon_years=5)
    assert any(i.code == "OPX033" for i in issues)


def test_validate_OPX040_missing_base_code():
    base_cat = OpexCategoryInput(code="B", name="B", subitems=(_always("x", 1.0),))
    pct_cat = OpexCategoryInput(
        code="P", name="P",
        calculation_type=OpexCategoryCalculationType.PERCENTAGE_OF_SELECTED_BASES,
        percentage_rate=0.04,
        percentage_base_codes=("B", "MISSING"),
    )
    model = OpexModelInput(categories=(base_cat, pct_cat))
    issues = validate_opex_model_input(model, _CTX_ZERO, horizon_years=5)
    assert any(i.code == "OPX060" for i in issues)


def test_validate_OPX061_circular_pct_dependency():
    cat_a = OpexCategoryInput(
        code="A", name="A",
        calculation_type=OpexCategoryCalculationType.PERCENTAGE_OF_SELECTED_BASES,
        percentage_rate=0.1,
        percentage_base_codes=("B",),
    )
    cat_b = OpexCategoryInput(
        code="B", name="B",
        calculation_type=OpexCategoryCalculationType.PERCENTAGE_OF_SELECTED_BASES,
        percentage_rate=0.1,
        percentage_base_codes=("A",),
    )
    model = OpexModelInput(categories=(cat_a, cat_b))
    issues = validate_opex_model_input(model, _CTX_ZERO, horizon_years=5)
    assert any(i.code == "OPX061" for i in issues)


def test_validate_OPX050_manual_without_schedule():
    si = OpexSubitemInput(
        code="X", name="X", base_amount_keur=1.0,
        activation_mode=OpexActivationMode.MANUAL,
    )
    model = _simple_model(si)
    issues = validate_opex_model_input(model, _CTX_ZERO, horizon_years=5)
    assert any(i.code == "OPX050" for i in issues)


def test_validate_OPX051_schedule_too_short():
    si = _manual("X", 1.0, (True, True))  # 2-year schedule
    model = _simple_model(si)
    issues = validate_opex_model_input(model, _CTX_ZERO, horizon_years=5)
    assert any(i.code == "OPX051" for i in issues)


def test_validate_OPX052_override_out_of_horizon():
    si = _manual("X", 1.0, (True,) * 5, overrides=(((10, 1), False),))
    model = _simple_model(si)
    issues = validate_opex_model_input(model, _CTX_ZERO, horizon_years=5)
    assert any(i.code == "OPX052" for i in issues)


def test_validate_OPX053_override_bad_half():
    si = _manual("X", 1.0, (True,) * 5, overrides=(((3, 3), False),))
    model = _simple_model(si)
    issues = validate_opex_model_input(model, _CTX_ZERO, horizon_years=5)
    assert any(i.code == "OPX053" for i in issues)


def test_validate_OPX040_external_series_resolves_missing():
    """External series can satisfy a base code reference."""
    pct_cat = OpexCategoryInput(
        code="P", name="P",
        calculation_type=OpexCategoryCalculationType.PERCENTAGE_OF_SELECTED_BASES,
        percentage_rate=0.04,
        percentage_base_codes=("EXT",),
    )
    model = OpexModelInput(categories=(pct_cat,))
    ctx = OpexCalculationContext(
        external_annual_series=(("EXT", (100.0,) * 5),)
    )
    issues = validate_opex_model_input(model, ctx, horizon_years=5)
    assert not any(i.code == "OPX060" for i in issues)


def test_validate_OPX040_inflation_below_bound():
    cat = OpexCategoryInput(
        code="C", name="C",
        inflation_rate=-1.5,
        subitems=(_always("x", 1.0),),
    )
    model = OpexModelInput(categories=(cat,))
    issues = validate_opex_model_input(model, _CTX_ZERO, horizon_years=5)
    assert any(i.code == "OPX040" and i.severity == ValidationSeverity.ERROR for i in issues)


# ---------------------------------------------------------------------------
# 3. Activation: ALWAYS / MANUAL / SENIOR_DEBT_TENOR_ACTIVE
# ---------------------------------------------------------------------------


def test_always_active_all_years():
    model = _simple_model(_always("A", 50.0))
    results = compute_annual(model, _CTX_ZERO, horizon_years=10)
    for r in results:
        si = r.categories[0].subitems[0]
        assert si.active is True


def test_manual_active_years_exact():
    flags = (True, False, True, False, True)
    model = _simple_model(_manual("A", 100.0, flags))
    results = compute_annual(model, _CTX_ZERO, horizon_years=5)
    actives = [r.categories[0].subitems[0].active for r in results]
    assert actives == [True, False, True, False, True]


def test_manual_inactive_contributes_zero():
    flags = (True, False)
    model = _simple_model(_manual("A", 100.0, flags))
    results = compute_annual(model, _CTX_ZERO, horizon_years=2)
    assert abs(results[1].total_keur) < 1e-9


def test_senior_debt_tenor_active_boundary():
    model = _simple_model(_tenor_active("A", 100.0))
    ctx = OpexCalculationContext(senior_debt_tenor_years=3)
    results = compute_annual(model, ctx, horizon_years=5)
    actives = [r.categories[0].subitems[0].active for r in results]
    assert actives == [True, True, True, False, False]


def test_senior_debt_tenor_active_y_equals_tenor_is_active():
    ctx = OpexCalculationContext(senior_debt_tenor_years=5)
    model = _simple_model(_tenor_active("A", 10.0))
    results = compute_annual(model, ctx, horizon_years=5)
    assert results[4].categories[0].subitems[0].active is True


def test_senior_debt_tenor_different_tenors_same_amount():
    """Changing only the tenor changes activation, not amount values."""
    model = _simple_model(_tenor_active("A", 100.0))
    r14 = compute_annual(model, OpexCalculationContext(senior_debt_tenor_years=14), horizon_years=30)
    r10 = compute_annual(model, OpexCalculationContext(senior_debt_tenor_years=10), horizon_years=30)
    # Y5 is active under both
    assert abs(r14[4].total_keur - r10[4].total_keur) < 1e-9
    # Y12 active under tenor=14 but not tenor=10
    assert r14[11].total_keur > 0
    assert abs(r10[11].total_keur) < 1e-9


def test_manual_then_switch_to_senior_debt_tenor_active():
    """Same subitem can be reconfigured from MANUAL to SENIOR_DEBT_TENOR_ACTIVE."""
    manual_flags = (True,) * 5 + (False,) * 25
    si_manual = _manual("A", 100.0, manual_flags)
    si_auto = _tenor_active("A", 100.0)
    ctx = OpexCalculationContext(senior_debt_tenor_years=14)
    r_manual = compute_annual(_simple_model(si_manual), ctx, horizon_years=30)
    r_auto = compute_annual(_simple_model(si_auto), ctx, horizon_years=30)
    # Y14: auto is active, manual is inactive
    assert r_auto[13].total_keur > 0
    assert abs(r_manual[13].total_keur) < 1e-9


# ---------------------------------------------------------------------------
# 4. Escalation: YEAR_1_AS_BASE / PRE_OPERATION_BASE
# ---------------------------------------------------------------------------


def test_year_1_as_base_y1_equals_budget():
    cat = OpexCategoryInput(
        code="C", name="C",
        inflation_rate=0.05,
        escalation_convention=OpexEscalationConvention.YEAR_1_AS_BASE,
        subitems=(_always("A", 200.0),),
    )
    model = OpexModelInput(categories=(cat,))
    results = compute_annual(model, _CTX_ZERO, horizon_years=3)
    assert abs(results[0].total_keur - 200.0) < 1e-9


def test_year_1_as_base_escalation():
    cat = OpexCategoryInput(
        code="C", name="C",
        inflation_rate=0.02,
        escalation_convention=OpexEscalationConvention.YEAR_1_AS_BASE,
        subitems=(_always("A", 100.0),),
    )
    results = compute_annual(OpexModelInput(categories=(cat,)), _CTX_ZERO, horizon_years=3)
    assert abs(results[0].total_keur - 100.0) < 1e-9
    assert abs(results[1].total_keur - 102.0) < 1e-9
    assert abs(results[2].total_keur - 104.04) < 1e-9


def test_pre_operation_base_y1():
    cat = OpexCategoryInput(
        code="C", name="C",
        inflation_rate=0.02,
        escalation_convention=OpexEscalationConvention.PRE_OPERATION_BASE,
        subitems=(_always("A", 204.0),),
    )
    results = compute_annual(OpexModelInput(categories=(cat,)), _CTX_ZERO, horizon_years=1)
    assert abs(results[0].total_keur - 204.0 * 1.02) < 1e-9


def test_pre_operation_base_differs_from_year_1_as_base():
    cat_y1 = OpexCategoryInput(
        code="C", name="C", inflation_rate=0.05,
        escalation_convention=OpexEscalationConvention.YEAR_1_AS_BASE,
        subitems=(_always("A", 100.0),),
    )
    cat_pre = OpexCategoryInput(
        code="C", name="C", inflation_rate=0.05,
        escalation_convention=OpexEscalationConvention.PRE_OPERATION_BASE,
        subitems=(_always("A", 100.0),),
    )
    r_y1 = compute_annual(OpexModelInput(categories=(cat_y1,)), _CTX_ZERO, horizon_years=2)
    r_pre = compute_annual(OpexModelInput(categories=(cat_pre,)), _CTX_ZERO, horizon_years=2)
    # Y1: Y_1_AS_BASE = 100, PRE_OP = 105
    assert r_pre[0].total_keur > r_y1[0].total_keur
    # Both escalate from different bases
    assert abs(r_y1[0].total_keur - 100.0) < 1e-9
    assert abs(r_pre[0].total_keur - 105.0) < 1e-9


def test_zero_inflation_flat_both_conventions():
    for conv in (OpexEscalationConvention.YEAR_1_AS_BASE, OpexEscalationConvention.PRE_OPERATION_BASE):
        cat = OpexCategoryInput(
            code="C", name="C", inflation_rate=0.0,
            escalation_convention=conv,
            subitems=(_always("A", 50.0),),
        )
        results = compute_annual(OpexModelInput(categories=(cat,)), _CTX_ZERO, horizon_years=5)
        assert all(abs(r.total_keur - 50.0) < 1e-9 for r in results), (
            f"{conv}: expected 50.0 for all years"
        )


# ---------------------------------------------------------------------------
# 5. Annual calculation — SUBITEM_SUM
# ---------------------------------------------------------------------------


def test_inactive_subitem_not_in_sum():
    si_on = _always("ON", 100.0)
    si_off = _manual("OFF", 999.0, (False,) * 5)
    cat = OpexCategoryInput(code="C", name="C", inflation_rate=0.0, subitems=(si_on, si_off))
    results = compute_annual(OpexModelInput(categories=(cat,)), _CTX_ZERO, horizon_years=5)
    assert all(abs(r.total_keur - 100.0) < 1e-9 for r in results)


def test_escalation_applied_after_sumproduct():
    si_a = _always("A", 100.0)
    si_b = _manual("B", 50.0, (True,) + (False,) * 4)
    cat = OpexCategoryInput(
        code="C", name="C", inflation_rate=0.1,
        escalation_convention=OpexEscalationConvention.YEAR_1_AS_BASE,
        subitems=(si_a, si_b),
    )
    results = compute_annual(OpexModelInput(categories=(cat,)), _CTX_ZERO, horizon_years=2)
    # Y1: (100+50)×1.0 = 150
    assert abs(results[0].total_keur - 150.0) < 1e-9
    # Y2: (100+0)×1.1 = 110
    assert abs(results[1].total_keur - 110.0) < 1e-9


# ---------------------------------------------------------------------------
# 6. Annual calculation — PERCENTAGE_OF_SELECTED_BASES
# ---------------------------------------------------------------------------


def test_contingency_references_category():
    base_cat = OpexCategoryInput(code="B", name="B",
                                  subitems=(_always("x", 1000.0),))
    pct_cat = OpexCategoryInput(
        code="P", name="P",
        calculation_type=OpexCategoryCalculationType.PERCENTAGE_OF_SELECTED_BASES,
        percentage_rate=0.04,
        percentage_base_codes=("B",),
    )
    model = OpexModelInput(categories=(base_cat, pct_cat))
    results = compute_annual(model, _CTX_ZERO, horizon_years=1)
    assert abs(results[0].categories[1].annual_keur - 40.0) < 1e-9


def test_contingency_references_external_series():
    pct_cat = OpexCategoryInput(
        code="P", name="P",
        calculation_type=OpexCategoryCalculationType.PERCENTAGE_OF_SELECTED_BASES,
        percentage_rate=0.1,
        percentage_base_codes=("EXT",),
    )
    model = OpexModelInput(categories=(pct_cat,))
    ctx = OpexCalculationContext(external_annual_series=(("EXT", (500.0,) * 5),))
    results = compute_annual(model, ctx, horizon_years=5)
    assert all(abs(r.total_keur - 50.0) < 1e-9 for r in results)


def test_contingency_tracks_base_step_change():
    """When a base category activates a subitem mid-run, contingency must follow."""
    si_always = _always("A", 100.0)
    si_step = _manual("B", 200.0, (False,) * 5 + (True,) * 5)
    base_cat = OpexCategoryInput(code="BASE", name="BASE",
                                  subitems=(si_always, si_step))
    pct_cat = OpexCategoryInput(
        code="PCT", name="PCT",
        calculation_type=OpexCategoryCalculationType.PERCENTAGE_OF_SELECTED_BASES,
        percentage_rate=0.1,
        percentage_base_codes=("BASE",),
    )
    model = OpexModelInput(categories=(base_cat, pct_cat))
    results = compute_annual(model, _CTX_ZERO, horizon_years=10)
    assert abs(results[0].categories[1].annual_keur - 10.0) < 1e-9   # 10% of 100
    assert abs(results[5].categories[1].annual_keur - 30.0) < 1e-9   # 10% of 300


def test_contingency_d_f_external_non_zero():
    """Synthetic D/F non-zero values must propagate to the derived category."""
    base_cat = OpexCategoryInput(code="BASE", name="BASE",
                                  subitems=(_always("x", 1000.0),))
    pct_cat = OpexCategoryInput(
        code="PCT", name="PCT",
        calculation_type=OpexCategoryCalculationType.PERCENTAGE_OF_SELECTED_BASES,
        percentage_rate=0.04,
        percentage_base_codes=("BASE", "D", "F"),
    )
    model = OpexModelInput(categories=(base_cat, pct_cat))
    d_series = (200.0,) * 3
    f_series = (100.0,) * 3
    ctx = OpexCalculationContext(
        external_annual_series=(("D", d_series), ("F", f_series))
    )
    results = compute_annual(model, ctx, horizon_years=3)
    # PCT = 4% × (1000 + 200 + 100) = 4% × 1300 = 52
    assert all(abs(r.categories[1].annual_keur - 52.0) < 1e-9 for r in results)


# ---------------------------------------------------------------------------
# 7. Period calculation — basic and H1/H2 overrides
# ---------------------------------------------------------------------------


def test_period_full_year_equals_annual():
    model = _simple_model(_always("A", 100.0))
    annual = compute_annual(model, _CTX_ZERO, horizon_years=3)
    periods = compute_periods(model, _CTX_ZERO, _annual_periods(3))
    for yr in range(3):
        assert abs(periods[yr].total_keur - annual[yr].total_keur) < 1e-9


def test_period_semiannual_halves_sum_to_annual():
    model = _simple_model(_always("A", 100.0))
    annual = compute_annual(model, _CTX_ZERO, horizon_years=5)
    periods = compute_periods(model, _CTX_ZERO, _semi_periods(5))
    for yr in range(5):
        h1 = periods[yr * 2]
        h2 = periods[yr * 2 + 1]
        assert abs(h1.total_keur + h2.total_keur - annual[yr].total_keur) < 1e-9


def test_period_partial_first_year():
    """A partial first period (day_fraction < 1) should prorate correctly."""
    model = _simple_model(_always("A", 120.0))
    p = _FakePeriod(index=1, year_index=1, period_in_year=1, day_fraction=0.25)
    results = compute_periods(model, _CTX_ZERO, [p])
    assert abs(results[0].total_keur - 30.0) < 1e-9


def test_period_two_periods_same_year():
    """Two periods in the same year sum to annual × (df1 + df2)."""
    model = _simple_model(_always("A", 100.0))
    p1 = _FakePeriod(index=1, year_index=1, period_in_year=1, day_fraction=0.3)
    p2 = _FakePeriod(index=2, year_index=1, period_in_year=2, day_fraction=0.7)
    results = compute_periods(model, _CTX_ZERO, [p1, p2])
    assert abs(results[0].total_keur + results[1].total_keur - 100.0) < 1e-9


def test_period_non_operation_excluded():
    """Construction periods (is_operation=False) produce no OPEX."""
    model = _simple_model(_always("A", 100.0))
    constr = _FakePeriod(index=0, year_index=0, period_in_year=1, day_fraction=0.5, is_operation=False)
    oper = _FakePeriod(index=1, year_index=1, period_in_year=1, day_fraction=1.0)
    results = compute_periods(model, _CTX_ZERO, [constr, oper])
    assert len(results) == 1
    assert results[0].period_index == 1


def test_h1h2_annual_y5_on_both_halves():
    flags = (True,) * 10
    model = _simple_model(_manual("A", 100.0, flags))
    periods = compute_periods(model, _CTX_ZERO, _semi_periods(10))
    y5_h1 = periods[8]   # (year 5 − 1) * 2 = 8
    y5_h2 = periods[9]
    assert y5_h1.categories[0].subitems[0].active is True
    assert y5_h2.categories[0].subitems[0].active is True


def test_h1h2_annual_y5_off_both_halves():
    flags = (True,) * 4 + (False,) + (True,) * 5
    model = _simple_model(_manual("A", 100.0, flags))
    periods = compute_periods(model, _CTX_ZERO, _semi_periods(10))
    y5_h1 = periods[8]
    y5_h2 = periods[9]
    assert y5_h1.categories[0].subitems[0].active is False
    assert y5_h2.categories[0].subitems[0].active is False


def test_h1h2_override_y5_on_h1_off():
    """Annual Y5 ON + H1 override OFF → H1=False, H2=True."""
    flags = (True,) * 10
    si = _manual("A", 100.0, flags, overrides=(((5, 1), False),))
    model = _simple_model(si)
    periods = compute_periods(model, _CTX_ZERO, _semi_periods(10))
    y5_h1 = periods[8]
    y5_h2 = periods[9]
    assert y5_h1.categories[0].subitems[0].active is False
    assert y5_h2.categories[0].subitems[0].active is True


def test_h1h2_override_y5_off_h2_on():
    """Annual Y5 OFF + H2 override ON → H1=False, H2=True."""
    flags = (True,) * 4 + (False,) + (True,) * 5
    si = _manual("A", 100.0, flags, overrides=(((5, 2), True),))
    model = _simple_model(si)
    periods = compute_periods(model, _CTX_ZERO, _semi_periods(10))
    y5_h1 = periods[8]
    y5_h2 = periods[9]
    assert y5_h1.categories[0].subitems[0].active is False
    assert y5_h2.categories[0].subitems[0].active is True


def test_h1h2_keur_reflects_active_half_only():
    """Only the active half contributes kEUR; the inactive half is zero."""
    flags = (True,) * 10
    si = _manual("A", 100.0, flags, overrides=(((3, 2), False),))
    model = _simple_model(si)
    periods = compute_periods(model, _CTX_ZERO, _semi_periods(10))
    y3_h1 = periods[4]
    y3_h2 = periods[5]
    assert abs(y3_h1.total_keur - 50.0) < 1e-9
    assert abs(y3_h2.total_keur) < 1e-9


def test_period_contingency_follows_h1h2_base():
    """H1 deactivation of a base subitem propagates to contingency in that period."""
    si_base = _manual("A", 1000.0, (True,) * 5, overrides=(((2, 1), False),))
    base_cat = OpexCategoryInput(code="B", name="B", subitems=(si_base,))
    pct_cat = OpexCategoryInput(
        code="P", name="P",
        calculation_type=OpexCategoryCalculationType.PERCENTAGE_OF_SELECTED_BASES,
        percentage_rate=0.1,
        percentage_base_codes=("B",),
    )
    model = OpexModelInput(categories=(base_cat, pct_cat))
    periods = compute_periods(model, _CTX_ZERO, _semi_periods(5))
    y2_h1 = periods[2]
    y2_h2 = periods[3]
    # H1: base is OFF → contingency is 0; H2: base is ON → contingency = 10% × 1000 × 0.5
    assert abs(y2_h1.categories[1].period_keur) < 1e-9
    assert abs(y2_h2.categories[1].period_keur - 50.0) < 1e-9


# ---------------------------------------------------------------------------
# 8. Identity independence
# ---------------------------------------------------------------------------


def _make_model_with_codes(cat_code: str, si_code: str, amount: float) -> OpexModelInput:
    cat = OpexCategoryInput(
        code=cat_code,
        name=f"Cat {cat_code}",
        subitems=(OpexSubitemInput(code=si_code, name=f"SI {si_code}", base_amount_keur=amount),),
    )
    return OpexModelInput(categories=(cat,))


@pytest.mark.parametrize("cat_code, si_code", [
    ("B.08", "B.08.3"),
    ("OBOROVO_SPECIAL", "MY_SUBITEM"),
    ("X", "Y"),
    ("oborovo", "balancing"),
])
def test_identity_independence_cat_and_si_codes(cat_code: str, si_code: str):
    """Financial results must be identical regardless of category/subitem codes."""
    m1 = _make_model_with_codes(cat_code, si_code, 500.0)
    m2 = _make_model_with_codes("ARBITRARY_CODE", "ANOTHER_CODE", 500.0)
    r1 = compute_annual(m1, _CTX_ZERO, horizon_years=5)
    r2 = compute_annual(m2, _CTX_ZERO, horizon_years=5)
    for y in range(5):
        assert abs(r1[y].total_keur - r2[y].total_keur) < 1e-9


def test_identity_independence_name_does_not_affect_calculation():
    si_a = OpexSubitemInput(code="X", name="Some Name", base_amount_keur=300.0)
    si_b = OpexSubitemInput(code="X", name="Totally Different Name", base_amount_keur=300.0)
    cat_a = OpexCategoryInput(code="C", name="Cat A", subitems=(si_a,))
    cat_b = OpexCategoryInput(code="C", name="Cat B", subitems=(si_b,))
    r_a = compute_annual(OpexModelInput(categories=(cat_a,)), _CTX_ZERO, horizon_years=3)
    r_b = compute_annual(OpexModelInput(categories=(cat_b,)), _CTX_ZERO, horizon_years=3)
    for y in range(3):
        assert abs(r_a[y].total_keur - r_b[y].total_keur) < 1e-9


# ---------------------------------------------------------------------------
# 9. Oborovo structural proof — B.01–B.13 × Y1–Y30
# ---------------------------------------------------------------------------

from tests.helpers.oborovo_opex_fixture_builder import (
    OBOROVO_HORIZON_YEARS,
    build_oborovo_calculation_context,
    build_oborovo_opex_model_input,
    get_fixture_category_annual,
    get_fixture_total_annual,
)

_OBOROVO_CATEGORIES = [
    "B.01", "B.02", "B.03", "B.04", "B.05", "B.06",
    "B.07", "B.08", "B.09", "B.10", "B.11", "B.12", "B.13",
]
_RECON_TOLERANCE = 1e-6  # kEUR — max observed delta ~5e-14 kEUR


@pytest.fixture(scope="module")
def oborovo_model() -> OpexModelInput:
    return build_oborovo_opex_model_input()


@pytest.fixture(scope="module")
def oborovo_ctx() -> OpexCalculationContext:
    return build_oborovo_calculation_context()


@pytest.fixture(scope="module")
def oborovo_annual_results(oborovo_model, oborovo_ctx):
    return compute_annual(oborovo_model, oborovo_ctx, horizon_years=OBOROVO_HORIZON_YEARS)


def test_oborovo_model_has_13_categories(oborovo_model):
    assert len(oborovo_model.categories) == 13


def test_oborovo_model_validates(oborovo_model, oborovo_ctx):
    issues = validate_opex_model_input(oborovo_model, oborovo_ctx, horizon_years=OBOROVO_HORIZON_YEARS)
    assert not has_errors(issues), [str(i) for i in issues if i.severity == ValidationSeverity.ERROR]


@pytest.mark.parametrize("cat_code", _OBOROVO_CATEGORIES)
@pytest.mark.parametrize("year_idx", list(range(OBOROVO_HORIZON_YEARS)))
def test_oborovo_category_annual_parity(oborovo_annual_results, cat_code, year_idx):
    """Generic engine must reproduce every Excel-cached annual category value Y1–Y30."""
    engine_val = next(
        r.annual_keur for r in oborovo_annual_results[year_idx].categories
        if r.code == cat_code
    )
    excel_val = get_fixture_category_annual(cat_code, year_idx)
    assert abs(engine_val - excel_val) < _RECON_TOLERANCE, (
        f"{cat_code} Y{year_idx + 1}: engine={engine_val:.10f} "
        f"excel={excel_val:.10f} (delta={abs(engine_val - excel_val):.2e} kEUR)"
    )


@pytest.mark.parametrize("year_idx", list(range(OBOROVO_HORIZON_YEARS)))
def test_oborovo_total_annual_parity(oborovo_annual_results, year_idx):
    """Total annual OPEX must match fixture for every year Y1–Y30."""
    engine_total = oborovo_annual_results[year_idx].total_keur
    excel_total = get_fixture_total_annual(year_idx)
    assert abs(engine_total - excel_total) < _RECON_TOLERANCE, (
        f"Total Y{year_idx + 1}: engine={engine_total:.10f} "
        f"excel={excel_total:.10f} (delta={abs(engine_total - excel_total):.2e} kEUR)"
    )


# ---------------------------------------------------------------------------
# 10. Specific category behaviour
# ---------------------------------------------------------------------------


def test_b02_manual_flags_reproduce_workbook_label_discrepancy(oborovo_annual_results):
    """B.02 results must follow actual flags (Y1-only for B.02.1) not misleading labels."""
    y1 = oborovo_annual_results[0]
    y2 = oborovo_annual_results[1]
    b02_y1 = next(c.annual_keur for c in y1.categories if c.code == "B.02")
    b02_y2 = next(c.annual_keur for c in y2.categories if c.code == "B.02")
    # B.02.1 (179 kEUR) active only Y1; B.02.2 (117 kEUR) active from Y2
    # So Y1 > Y2 (before inflation scaling)
    assert b02_y1 > b02_y2, (
        f"B.02 Y1={b02_y1:.4f} should exceed Y2={b02_y2:.4f} "
        "(B.02.1 active only in Y1)"
    )


def test_b07_pre_operation_base_y1_value(oborovo_annual_results):
    """B.07 Y1 must use PRE_OPERATION_BASE (204 × 1.02 = 208.08 kEUR)."""
    b07_y1 = next(
        c.annual_keur
        for c in oborovo_annual_results[0].categories
        if c.code == "B.07"
    )
    assert abs(b07_y1 - 208.08) < 0.1, f"B.07 Y1={b07_y1:.4f} kEUR (expected ~208.08)"


def test_b07_pre_op_and_year_1_as_base_differ():
    """PRE_OPERATION_BASE Y1 > YEAR_1_AS_BASE Y1 when inflation > 0."""
    base_204 = 204.0
    inf = 0.02
    cat_y1 = OpexCategoryInput(
        code="B07", name="Lease Y1-base", inflation_rate=inf,
        escalation_convention=OpexEscalationConvention.YEAR_1_AS_BASE,
        subitems=(_always("L", base_204),),
    )
    cat_pre = OpexCategoryInput(
        code="B07", name="Lease pre-op", inflation_rate=inf,
        escalation_convention=OpexEscalationConvention.PRE_OPERATION_BASE,
        subitems=(_always("L", base_204),),
    )
    r_y1 = compute_annual(OpexModelInput(categories=(cat_y1,)), _CTX_ZERO, horizon_years=1)
    r_pre = compute_annual(OpexModelInput(categories=(cat_pre,)), _CTX_ZERO, horizon_years=1)
    assert abs(r_y1[0].total_keur - base_204) < 1e-9
    assert abs(r_pre[0].total_keur - base_204 * 1.02) < 1e-9
    assert r_pre[0].total_keur > r_y1[0].total_keur


def test_b08_zero_inflation_and_step_at_y11(oborovo_annual_results):
    """B.08 must be flat Y1-Y10, jump at Y11, flat Y11-Y30."""
    b08_vals = [
        next(c.annual_keur for c in r.categories if c.code == "B.08")
        for r in oborovo_annual_results
    ]
    # Y1-Y10 flat
    assert all(abs(v - b08_vals[0]) < 1e-6 for v in b08_vals[:10]), (
        "B.08 Y1-Y10 must be flat"
    )
    # Y11 significantly higher (B.08.3 activates)
    assert b08_vals[10] > b08_vals[9] * 2, (
        f"B.08 Y11={b08_vals[10]:.4f} should be > 2× Y10={b08_vals[9]:.4f}"
    )
    # Y11-Y30 flat
    assert all(abs(v - b08_vals[10]) < 1e-6 for v in b08_vals[10:]), (
        "B.08 Y11-Y30 must be flat"
    )


def test_b10_audit_step_down(oborovo_annual_results):
    """B.10 Y1-Y2 (higher audit fee) must exceed Y3+ (lower audit fee)."""
    b10_vals = [
        next(c.annual_keur for c in r.categories if c.code == "B.10")
        for r in oborovo_annual_results
    ]
    assert b10_vals[0] > b10_vals[2], "B.10 Y1 must exceed Y3 (auditor step-down)"
    assert b10_vals[1] > b10_vals[2], "B.10 Y2 must exceed Y3 (auditor step-down)"


def test_b11_senior_debt_tenor_active_14_years(oborovo_annual_results, oborovo_ctx):
    """B.11 must be active for exactly senior_debt_tenor_years years."""
    tenor = oborovo_ctx.senior_debt_tenor_years  # 14
    b11_vals = [
        next(c.annual_keur for c in r.categories if c.code == "B.11")
        for r in oborovo_annual_results
    ]
    assert all(v > 0 for v in b11_vals[:tenor]), "B.11 must be active Y1-Y14"
    assert all(abs(v) < 1e-9 for v in b11_vals[tenor:]), "B.11 must be zero Y15-Y30"


def test_b11_tenor_change_propagates_without_flag_edit(oborovo_model, oborovo_ctx):
    """Changing only senior_debt_tenor_years changes B.11 activation range."""
    # oborovo_model references D/F external series; carry them in both contexts
    ext = oborovo_ctx.external_annual_series
    ctx_14 = OpexCalculationContext(senior_debt_tenor_years=14, external_annual_series=ext)
    ctx_10 = OpexCalculationContext(senior_debt_tenor_years=10, external_annual_series=ext)
    r14 = compute_annual(oborovo_model, ctx_14, horizon_years=30)
    r10 = compute_annual(oborovo_model, ctx_10, horizon_years=30)
    b11_14 = [next(c.annual_keur for c in r.categories if c.code == "B.11") for r in r14]
    b11_10 = [next(c.annual_keur for c in r.categories if c.code == "B.11") for r in r10]
    assert b11_14[13] > 0      # Y14 active under tenor=14
    assert abs(b11_10[13]) < 1e-9   # Y14 inactive under tenor=10 (only Y1-Y10 active)
    assert b11_10[9] > 0       # Y10 active under tenor=10


def test_b11_manual_override_replaces_auto_driver(oborovo_model, oborovo_ctx):
    """Switching B.11.3 from SENIOR_DEBT_TENOR_ACTIVE to MANUAL overrides the driver."""
    # Find B.11 category and build a version with B.11.3 as MANUAL (Y1-Y5 only)
    b11_cat = next(c for c in oborovo_model.categories if c.code == "B.11")
    new_subitems = []
    for si in b11_cat.subitems:
        if si.code == "B.11.3":
            new_si = OpexSubitemInput(
                code=si.code, name=si.name,
                base_amount_keur=si.base_amount_keur,
                activation_mode=OpexActivationMode.MANUAL,
                activation_schedule=OpexActivationSchedule(
                    annual_flags=(True,) * 5 + (False,) * 25
                ),
            )
        else:
            new_si = si
        new_subitems.append(new_si)
    new_b11 = OpexCategoryInput(
        code=b11_cat.code, name=b11_cat.name,
        inflation_rate=b11_cat.inflation_rate,
        escalation_convention=b11_cat.escalation_convention,
        subitems=tuple(new_subitems),
    )
    modified_cats = tuple(
        new_b11 if c.code == "B.11" else c
        for c in oborovo_model.categories
    )
    modified_model = OpexModelInput(categories=modified_cats)
    results = compute_annual(modified_model, oborovo_ctx, horizon_years=30)
    b11_vals = [next(c.annual_keur for c in r.categories if c.code == "B.11") for r in results]
    # Manual: active Y1-Y5 only, regardless of tenor=14
    assert all(v > 0 for v in b11_vals[:5]), "Manual B.11 should be active Y1-Y5"
    assert all(abs(v) < 1e-9 for v in b11_vals[5:]), "Manual B.11 should be zero Y6-Y30"


def test_b12_monitoring_expiry(oborovo_annual_results):
    """B.12 Y3 must be lower than Y1-Y2 (monitoring subitems expire at Y3)."""
    b12_vals = [
        next(c.annual_keur for c in r.categories if c.code == "B.12")
        for r in oborovo_annual_results
    ]
    assert b12_vals[0] > b12_vals[2], "B.12 Y1 must exceed Y3 (monitoring expiry)"
    assert b12_vals[1] > b12_vals[2], "B.12 Y2 must exceed Y3 (monitoring expiry)"


def test_b13_propagates_b08_activation_at_y11(oborovo_annual_results):
    """B.08 step-up at Y11 must cause a corresponding jump in B.13."""
    b13_vals = [
        next(c.annual_keur for c in r.categories if c.code == "B.13")
        for r in oborovo_annual_results
    ]
    b13_y10 = b13_vals[9]
    b13_y11 = b13_vals[10]
    assert b13_y11 > b13_y10 * 1.1, (
        f"B.13 Y11={b13_y11:.4f} should be substantially above Y10={b13_y10:.4f} "
        "due to B.08.3 activation"
    )


def test_b13_propagates_b11_expiry_at_y15(oborovo_annual_results, oborovo_ctx):
    """B.11 expiry at Y15 (tenor=14) must cause B.13 to dip relative to trend."""
    tenor = oborovo_ctx.senior_debt_tenor_years  # 14
    b13_vals = [
        next(c.annual_keur for c in r.categories if c.code == "B.13")
        for r in oborovo_annual_results
    ]
    assert b13_vals[tenor] < b13_vals[tenor - 1], (
        f"B.13 Y{tenor + 1}={b13_vals[tenor]:.4f} must be less than "
        f"Y{tenor}={b13_vals[tenor - 1]:.4f} due to B.11 expiry"
    )


def test_b13_d_f_external_non_zero_propagates():
    """Synthetic non-zero D/F must increase B.13 value."""
    from tests.helpers.oborovo_opex_fixture_builder import _load_fixture
    fixture = _load_fixture()
    model = build_oborovo_opex_model_input()
    # Normal context (D=F=0)
    ctx_zero = build_oborovo_calculation_context()
    # Augmented context with D=500 and F=300 per year
    ctx_nonzero = OpexCalculationContext(
        senior_debt_tenor_years=ctx_zero.senior_debt_tenor_years,
        external_annual_series=(("D", (500.0,) * 30), ("F", (300.0,) * 30)),
    )
    r_zero = compute_annual(model, ctx_zero, horizon_years=30)
    r_nonzero = compute_annual(model, ctx_nonzero, horizon_years=30)
    b13_zero = [next(c.annual_keur for c in r.categories if c.code == "B.13") for r in r_zero]
    b13_nonzero = [next(c.annual_keur for c in r.categories if c.code == "B.13") for r in r_nonzero]
    # B.13 with D=500, F=300 should be 4%×(500+300)=32 kEUR more per year
    for y in range(30):
        expected_uplift = 0.04 * (500.0 + 300.0)
        assert abs(b13_nonzero[y] - b13_zero[y] - expected_uplift) < 1e-6, (
            f"Y{y + 1}: D/F uplift expected={expected_uplift:.4f}, "
            f"got={b13_nonzero[y] - b13_zero[y]:.4f}"
        )


def test_unchecked_helpers_not_in_public_all():
    """Unchecked internal helpers must not be part of the public __all__."""
    import finco_core.opex.hierarchical as hierarchical
    assert "_compute_annual_unchecked" not in hierarchical.__all__
    assert "_compute_periods_unchecked" not in hierarchical.__all__


def test_unchecked_helpers_not_exposed_as_package_attributes():
    """Unchecked helpers must not be importable directly from the package."""
    import finco_core.opex.hierarchical as hierarchical
    assert not hasattr(hierarchical, "_compute_annual_unchecked")
    assert not hasattr(hierarchical, "_compute_periods_unchecked")


def test_production_code_does_not_import_fixture():
    """Verify production code does not import finco_recon or test fixtures."""
    import importlib
    import inspect
    import finco_core.opex.hierarchical._calculator as calc_mod
    import finco_core.opex.hierarchical._inputs as inputs_mod
    import finco_core.opex.hierarchical._validation as val_mod

    for mod in (calc_mod, inputs_mod, val_mod):
        src = inspect.getsource(mod)
        assert "finco_recon" not in src, f"{mod.__name__} must not import finco_recon"
        assert "excel_oborovo_opex_structural_truth" not in src, (
            f"{mod.__name__} must not reference the fixture file"
        )
        assert "15a621c4" not in src, (
            f"{mod.__name__} must not contain the workbook SHA256"
        )


# ---------------------------------------------------------------------------
# 11. Hardening — new validation codes and fail-fast behavior
# ---------------------------------------------------------------------------

from finco_core.opex.hierarchical import OpexInputValidationError
from finco_core.opex.hierarchical._calculator import (
    _compute_annual_unchecked,
    _compute_periods_unchecked,
)


# --- OPX034: duplicate percentage_base_codes --------------------------------


def test_validate_OPX034_duplicate_percentage_base_code():
    """Duplicate base code in percentage_base_codes must be rejected (OPX034)."""
    base_cat = OpexCategoryInput(code="B.01", name="B01", subitems=(_always("x", 100.0),))
    base_cat2 = OpexCategoryInput(code="B.02", name="B02", subitems=(_always("y", 100.0),))
    pct_cat = OpexCategoryInput(
        code="P", name="P",
        calculation_type=OpexCategoryCalculationType.PERCENTAGE_OF_SELECTED_BASES,
        percentage_rate=0.04,
        percentage_base_codes=("B.01", "B.01", "B.02"),  # B.01 duplicated
    )
    model = OpexModelInput(categories=(base_cat, base_cat2, pct_cat))
    issues = validate_opex_model_input(model, _CTX_ZERO, horizon_years=5)
    assert any(i.code == "OPX034" and i.severity == ValidationSeverity.ERROR for i in issues), (
        "Expected OPX034 for duplicate base code"
    )


def test_OPX034_duplicate_base_code_blocks_compute():
    """compute_annual must raise for OPX034 — must not silently double-count."""
    base_cat = OpexCategoryInput(code="B", name="B", subitems=(_always("x", 100.0),))
    pct_cat = OpexCategoryInput(
        code="P", name="P",
        calculation_type=OpexCategoryCalculationType.PERCENTAGE_OF_SELECTED_BASES,
        percentage_rate=0.04,
        percentage_base_codes=("B", "B"),  # duplicate
    )
    model = OpexModelInput(categories=(base_cat, pct_cat))
    with pytest.raises(OpexInputValidationError) as exc_info:
        compute_annual(model, _CTX_ZERO, horizon_years=5)
    assert any(i.code == "OPX034" for i in exc_info.value.issues)


# --- OPX070: duplicate external_annual_series codes -------------------------


def test_validate_OPX070_duplicate_external_series():
    """Duplicate external series code must be rejected (OPX070)."""
    ctx = OpexCalculationContext(
        external_annual_series=(
            ("D", (100.0,) * 5),
            ("D", (200.0,) * 5),  # duplicate
        )
    )
    model = _simple_model(_always("A", 10.0))
    issues = validate_opex_model_input(model, ctx, horizon_years=5)
    assert any(i.code == "OPX070" and i.severity == ValidationSeverity.ERROR for i in issues)


def test_OPX070_duplicate_external_blocks_compute():
    """compute_annual must raise for OPX070."""
    pct_cat = OpexCategoryInput(
        code="P", name="P",
        calculation_type=OpexCategoryCalculationType.PERCENTAGE_OF_SELECTED_BASES,
        percentage_rate=0.1,
        percentage_base_codes=("D",),
    )
    model = OpexModelInput(categories=(pct_cat,))
    ctx = OpexCalculationContext(
        external_annual_series=(("D", (100.0,) * 5), ("D", (200.0,) * 5))
    )
    with pytest.raises(OpexInputValidationError) as exc_info:
        compute_annual(model, ctx, horizon_years=5)
    assert any(i.code == "OPX070" for i in exc_info.value.issues)


# --- OPX071: external series code collides with category code ---------------


def test_validate_OPX071_external_code_collides_with_category():
    """External series code matching a category code must be rejected (OPX071)."""
    cat = OpexCategoryInput(code="B.01", name="B01", subitems=(_always("x", 100.0),))
    ctx = OpexCalculationContext(
        external_annual_series=(("B.01", (50.0,) * 5),)  # collides with category
    )
    model = OpexModelInput(categories=(cat,))
    issues = validate_opex_model_input(model, ctx, horizon_years=5)
    assert any(i.code == "OPX071" and i.severity == ValidationSeverity.ERROR for i in issues)


def test_OPX071_collision_blocks_compute():
    """compute_annual must raise for OPX071."""
    cat = OpexCategoryInput(code="BASE", name="B", subitems=(_always("x", 100.0),))
    ctx = OpexCalculationContext(external_annual_series=(("BASE", (50.0,) * 5),))
    model = OpexModelInput(categories=(cat,))
    with pytest.raises(OpexInputValidationError) as exc_info:
        compute_annual(model, ctx, horizon_years=5)
    assert any(i.code == "OPX071" for i in exc_info.value.issues)


# --- OPX072: external series shorter than required horizon ------------------


def test_validate_OPX072_short_external_series():
    """External series used by a pct category that is shorter than horizon must error (OPX072)."""
    pct_cat = OpexCategoryInput(
        code="P", name="P",
        calculation_type=OpexCategoryCalculationType.PERCENTAGE_OF_SELECTED_BASES,
        percentage_rate=0.04,
        percentage_base_codes=("EXT",),
    )
    model = OpexModelInput(categories=(pct_cat,))
    ctx = OpexCalculationContext(
        external_annual_series=(("EXT", (100.0,) * 3),)  # only 3 years, horizon=10
    )
    issues = validate_opex_model_input(model, ctx, horizon_years=10)
    assert any(i.code == "OPX072" and i.severity == ValidationSeverity.ERROR for i in issues)


def test_OPX072_short_series_blocks_compute():
    """compute_annual must raise for OPX072 — must not silently zero missing years."""
    pct_cat = OpexCategoryInput(
        code="P", name="P",
        calculation_type=OpexCategoryCalculationType.PERCENTAGE_OF_SELECTED_BASES,
        percentage_rate=0.1,
        percentage_base_codes=("EXT",),
    )
    model = OpexModelInput(categories=(pct_cat,))
    ctx = OpexCalculationContext(external_annual_series=(("EXT", (100.0,) * 2),))
    with pytest.raises(OpexInputValidationError) as exc_info:
        compute_annual(model, ctx, horizon_years=5)
    assert any(i.code == "OPX072" for i in exc_info.value.issues)


def test_OPX072_exact_horizon_length_is_valid():
    """External series of exactly horizon_years length must pass validation."""
    pct_cat = OpexCategoryInput(
        code="P", name="P",
        calculation_type=OpexCategoryCalculationType.PERCENTAGE_OF_SELECTED_BASES,
        percentage_rate=0.04,
        percentage_base_codes=("EXT",),
    )
    model = OpexModelInput(categories=(pct_cat,))
    ctx = OpexCalculationContext(external_annual_series=(("EXT", (100.0,) * 5),))
    issues = validate_opex_model_input(model, ctx, horizon_years=5)
    assert not any(i.code == "OPX072" for i in issues)


def test_OPX072_longer_than_horizon_is_valid():
    """External series longer than horizon must not trigger OPX072."""
    pct_cat = OpexCategoryInput(
        code="P", name="P",
        calculation_type=OpexCategoryCalculationType.PERCENTAGE_OF_SELECTED_BASES,
        percentage_rate=0.04,
        percentage_base_codes=("EXT",),
    )
    model = OpexModelInput(categories=(pct_cat,))
    ctx = OpexCalculationContext(external_annual_series=(("EXT", (100.0,) * 30),))
    issues = validate_opex_model_input(model, ctx, horizon_years=5)
    assert not any(i.code == "OPX072" for i in issues)


# --- OPX054: duplicate period override keys ----------------------------------


def test_validate_OPX054_duplicate_period_override_key():
    """Duplicate (year, half) key in period_overrides must be rejected (OPX054)."""
    si = _manual(
        "A", 100.0, (True,) * 5,
        overrides=(((3, 1), True), ((3, 1), False)),  # same key, different values
    )
    model = _simple_model(si)
    issues = validate_opex_model_input(model, _CTX_ZERO, horizon_years=5)
    assert any(i.code == "OPX054" and i.severity == ValidationSeverity.ERROR for i in issues)


def test_OPX054_duplicate_override_blocks_compute():
    """compute_annual must raise for OPX054."""
    si = _manual(
        "A", 100.0, (True,) * 5,
        overrides=(((2, 1), True), ((2, 1), False)),
    )
    model = _simple_model(si)
    with pytest.raises(OpexInputValidationError) as exc_info:
        compute_annual(model, _CTX_ZERO, horizon_years=5)
    assert any(i.code == "OPX054" for i in exc_info.value.issues)


def test_OPX054_different_keys_do_not_trigger():
    """Different (year, half) pairs must not trigger OPX054."""
    si = _manual(
        "A", 100.0, (True,) * 5,
        overrides=(((2, 1), True), ((2, 2), False), ((3, 1), True)),
    )
    model = _simple_model(si)
    issues = validate_opex_model_input(model, _CTX_ZERO, horizon_years=5)
    assert not any(i.code == "OPX054" for i in issues)


# --- Fail-fast: typed exception carries all issues --------------------------


def test_OpexInputValidationError_exposes_issues_attribute():
    """OpexInputValidationError must expose the full issues tuple."""
    si = OpexSubitemInput(
        code="X", name="X", base_amount_keur=1.0,
        activation_mode=OpexActivationMode.MANUAL,  # no schedule → OPX050
    )
    model = _simple_model(si)
    with pytest.raises(OpexInputValidationError) as exc_info:
        compute_annual(model, _CTX_ZERO, horizon_years=5)
    err = exc_info.value
    assert hasattr(err, "issues")
    assert isinstance(err.issues, tuple)
    assert len(err.issues) > 0
    assert any(i.code == "OPX050" for i in err.issues)


def test_OpexInputValidationError_message_contains_error_codes():
    """Exception message must contain the error code(s)."""
    si = OpexSubitemInput(
        code="X", name="X", base_amount_keur=1.0,
        activation_mode=OpexActivationMode.MANUAL,
    )
    model = _simple_model(si)
    with pytest.raises(OpexInputValidationError) as exc_info:
        compute_annual(model, _CTX_ZERO, horizon_years=5)
    assert "OPX050" in str(exc_info.value)


# --- Fail-fast: invalid MANUAL schedule cannot produce output ---------------


def test_invalid_manual_schedule_cannot_produce_annual_output():
    """MANUAL subitem with schedule shorter than horizon must not produce annual results."""
    si = _manual("A", 100.0, (True, True))  # 2 flags, horizon=10
    model = _simple_model(si)
    with pytest.raises(OpexInputValidationError) as exc_info:
        compute_annual(model, _CTX_ZERO, horizon_years=10)
    assert any(i.code == "OPX051" for i in exc_info.value.issues)


def test_invalid_manual_schedule_cannot_produce_period_output():
    """MANUAL subitem with schedule shorter than horizon must not produce period results."""
    si = _manual("A", 100.0, (True, True))  # 2 flags, horizon=5 from periods
    model = _simple_model(si)
    periods = _annual_periods(5)
    with pytest.raises(OpexInputValidationError) as exc_info:
        compute_periods(model, _CTX_ZERO, periods)
    assert any(i.code == "OPX051" for i in exc_info.value.issues)


# --- Fail-fast: zero tenor with SENIOR_DEBT_TENOR_ACTIVE --------------------


def test_zero_tenor_cannot_produce_annual_output():
    """SENIOR_DEBT_TENOR_ACTIVE with zero tenor must not produce annual output."""
    model = _simple_model(_tenor_active("A", 100.0))
    with pytest.raises(OpexInputValidationError) as exc_info:
        compute_annual(model, _CTX_ZERO, horizon_years=5)
    assert any(i.code == "OPX020" for i in exc_info.value.issues)


def test_zero_tenor_cannot_produce_period_output():
    """SENIOR_DEBT_TENOR_ACTIVE with zero tenor must not produce period output."""
    model = _simple_model(_tenor_active("A", 100.0))
    with pytest.raises(OpexInputValidationError) as exc_info:
        compute_periods(model, _CTX_ZERO, _annual_periods(5))
    assert any(i.code == "OPX020" for i in exc_info.value.issues)


# --- _ext_value asserts on missing data (no silent zero) --------------------


def test_ext_value_asserts_on_missing_code():
    """_ext_value must raise AssertionError when the code is not in ext lookup."""
    from finco_core.opex.hierarchical._calculator import _ext_value
    ext = {"D": (100.0, 200.0)}
    with pytest.raises(AssertionError, match="not in external_annual_series"):
        _ext_value(ext, "MISSING", 0)


def test_ext_value_asserts_on_out_of_range_year():
    """_ext_value must raise AssertionError when year_idx is out of range."""
    from finco_core.opex.hierarchical._calculator import _ext_value
    ext = {"D": (100.0, 200.0)}
    with pytest.raises(AssertionError, match="out of range"):
        _ext_value(ext, "D", 5)


def test_ext_value_returns_explicit_zero():
    """An explicit 0.0 in the series is a valid value and must be returned."""
    from finco_core.opex.hierarchical._calculator import _ext_value
    ext = {"D": (100.0, 0.0, 50.0)}
    assert _ext_value(ext, "D", 1) == 0.0


def test_missing_short_external_series_cannot_silently_zero():
    """A short external series must not silently produce zeros for missing years.

    Verifies that the validation gate (OPX072) is the only path, and that
    bypassing validation and calling _compute_annual_unchecked directly with
    a too-short series raises AssertionError rather than silently returning 0.
    """
    pct_cat = OpexCategoryInput(
        code="P", name="P",
        calculation_type=OpexCategoryCalculationType.PERCENTAGE_OF_SELECTED_BASES,
        percentage_rate=0.1,
        percentage_base_codes=("EXT",),
    )
    model = OpexModelInput(categories=(pct_cat,))
    ctx = OpexCalculationContext(external_annual_series=(("EXT", (100.0, 200.0)),))
    # Public API must refuse
    with pytest.raises(OpexInputValidationError) as exc_info:
        compute_annual(model, ctx, horizon_years=5)
    assert any(i.code == "OPX072" for i in exc_info.value.issues)
    # Internal unchecked function must also fail hard, not silently return 0
    with pytest.raises(AssertionError):
        _compute_annual_unchecked(model, ctx, horizon_years=5)
