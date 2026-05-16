import pytest

from domain.opex.engine import compute_annual_opex
from domain.opex.line_items import (
    ManualOverride,
    OpexBasis,
    OpexGroup,
    OpexItem,
    OpexItemStep,
)


def group(code, items, inflation=0.02, wth=0.0):
    return OpexGroup(code=code, name=code, inflation_rate=inflation, wth_rate=wth, items=tuple(items))


def item(code, budget, basis=OpexBasis.FIXED_ANNUAL_KEUR, **kwargs):
    return OpexItem(code=code, name=code, budget_keur=budget, basis=basis, group_code=code[:4], **kwargs)


def test_fixed_annual_with_inflation():
    result = compute_annual_opex([group("B.01", [item("B.01.1", 100.0)])], years=3)

    assert result.total_by_year_keur == pytest.approx((100.0, 102.0, 104.04))


def test_active_flags_and_inactive_basis():
    result = compute_annual_opex(
        [
            group(
                "B.01",
                [
                    item("B.01.1", 100.0, active_flags=(True, False, True)),
                    item("B.01.2", 50.0, basis=OpexBasis.INACTIVE),
                ],
            )
        ],
        years=3,
    )

    assert result.total_by_year_keur == pytest.approx((100.0, 0.0, 104.04))


def test_inactive_flag_wins_over_manual_override():
    result = compute_annual_opex(
        [
            group(
                "B.01",
                [
                    item(
                        "B.01.1",
                        100.0,
                        active_flags=(False,),
                        manual_overrides=(ManualOverride(1, 999.0),),
                    )
                ],
            )
        ],
        years=1,
    )

    assert result.total_for_year(1) == 0.0


def test_manual_override_is_not_inflated():
    result = compute_annual_opex(
        [
            group(
                "B.01",
                [item("B.01.1", 100.0, manual_overrides=(ManualOverride(2, 111.0),))],
            )
        ],
        years=2,
    )

    annual = result.item_result(2, "B.01", "B.01.1")
    assert annual.total_keur == 111.0
    assert annual.calculated_keur == pytest.approx(102.0)
    assert annual.is_manual_override is True


def test_explicit_schedule_is_not_inflated():
    result = compute_annual_opex(
        [
            group(
                "B.01",
                [
                    item(
                        "B.01.1",
                        0.0,
                        basis=OpexBasis.EXPLICIT_SCHEDULE,
                        explicit_schedule_keur=(10.0, 20.0, 30.0),
                    )
                ],
            )
        ],
        years=3,
    )

    assert result.total_by_year_keur == pytest.approx((10.0, 20.0, 30.0))


def test_eur_per_mw_year_and_eur_per_mwh():
    result = compute_annual_opex(
        [
            group(
                "B.01",
                [
                    item("B.01.1", 1000.0, basis=OpexBasis.EUR_PER_MW_YEAR),
                    item("B.01.2", 2.0, basis=OpexBasis.EUR_PER_MWH),
                ],
                inflation=0.0,
            )
        ],
        years=1,
        capacity_mw=50.0,
        production_mwh_by_year=[25_000.0],
    )

    assert result.total_for_year(1) == pytest.approx(100.0)


def test_percent_of_revenue():
    result = compute_annual_opex(
        [group("B.01", [item("B.01.1", 0.05, basis=OpexBasis.PCT_OF_REVENUE)], inflation=0.0)],
        years=1,
        revenue_keur_by_year=[1000.0],
    )

    assert result.total_for_year(1) == 50.0


def test_group_totals_and_result_helpers():
    result = compute_annual_opex(
        [group("B.01", [item("B.01.1", 100.0), item("B.01.2", 50.0)], inflation=0.0)],
        years=1,
    )

    assert result.group_result(1, "B.01").group_total_keur == 150.0
    assert result.item_result(1, "B.01", "B.01.2").total_keur == 50.0
    assert result.grand_total_keur == 150.0


def test_pct_of_selected_groups_two_pass_and_order_independent():
    base_a = group("B.01", [item("B.01.1", 100.0)], inflation=0.0)
    base_b = group("B.02", [item("B.02.1", 50.0)], inflation=0.0)
    contingency = group(
        "B.13",
        [
            OpexItem(
                code="B.13.1",
                name="Contingency",
                budget_keur=6.0,
                basis=OpexBasis.PCT_OF_SELECTED_GROUPS,
                group_code="B.13",
                selected_group_codes=("B.01", "B.02"),
            )
        ],
        inflation=0.0,
    )

    first = compute_annual_opex([base_a, base_b, contingency], years=1)
    second = compute_annual_opex([contingency, base_b, base_a], years=1)

    assert first.group_result(1, "B.13").group_total_keur == pytest.approx(9.0)
    assert second.group_result(1, "B.13").group_total_keur == pytest.approx(9.0)
    assert first.total_for_year(1) == second.total_for_year(1)


def test_wth_is_added_and_exposed():
    result = compute_annual_opex([group("B.01", [item("B.01.1", 100.0)], inflation=0.0, wth=0.1)], years=1)

    annual = result.item_result(1, "B.01", "B.01.1")
    assert annual.wth_keur == 10.0
    assert annual.total_keur == 110.0


def test_step_change_resets_inflation():
    result = compute_annual_opex(
        [
            group(
                "B.01",
                [
                    item(
                        "B.01.1",
                        100.0,
                        step_changes=(OpexItemStep(3, 200.0),),
                    )
                ],
            )
        ],
        years=4,
    )

    assert result.total_by_year_keur == pytest.approx((100.0, 102.0, 200.0, 204.0))
