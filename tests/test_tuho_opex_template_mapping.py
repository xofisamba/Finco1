import pytest

from domain.opex.engine import compute_annual_opex
from domain.opex.line_items import OpexBasis
from domain.opex.templates.tuho import B02_EXPLICIT_SCHEDULE, B11_ACTIVE_FLAGS, build_tuho_opex_template

EXCEL_ANNUAL_TOTALS = (
    1998.05,
    2029.83,
    2147.06,
    2180.13,
    2213.86,
    2378.01,
    2413.10,
    2448.90,
    2485.41,
    2522.65,
    2603.04,
    2641.79,
    2681.31,
    2721.62,
    2734.77,
    2827.03,
    2869.24,
    2912.29,
    2956.21,
    3001.00,
    3131.49,
    3178.09,
    3225.63,
    3274.11,
    3323.57,
    3450.33,
    3501.79,
    3554.27,
    3607.80,
    3662.40,
)


def _template_by_code():
    return {group.code: group for group in build_tuho_opex_template()}


def test_build_tuho_opex_template_builds_groups_b01_to_b13():
    groups = build_tuho_opex_template()

    assert [group.code for group in groups] == [f"B.{idx:02d}" for idx in range(1, 14)]


def test_tuho_template_all_annual_totals_match_excel():
    result = compute_annual_opex(build_tuho_opex_template(), years=30)

    assert result.total_by_year_keur == pytest.approx(EXCEL_ANNUAL_TOTALS, abs=0.01)


def test_tuho_template_30_year_total_matches_excel():
    result = compute_annual_opex(build_tuho_opex_template(), years=30)

    assert result.grand_total_keur == pytest.approx(84_674.78, abs=0.01)


def test_b02_explicit_schedule_values_and_no_inflation():
    groups = _template_by_code()
    item = groups["B.02"].item_by_code("B.02.1")
    result = compute_annual_opex([groups["B.02"]], years=30)

    assert item.basis == OpexBasis.EXPLICIT_SCHEDULE
    assert item.explicit_schedule_keur == B02_EXPLICIT_SCHEDULE
    assert result.item_result(30, "B.02", "B.02.1").total_keur == 828.0


def test_b11_active_flags_are_explicit_full_horizon():
    groups = _template_by_code()
    item = groups["B.11"].item_by_code("B.11.1")

    assert item.active_flags == B11_ACTIVE_FLAGS
    assert len(item.active_flags) == 30
    assert item.active_flags[:14] == (True,) * 14
    assert item.active_flags[14:] == (False,) * 16


def test_b13_equals_six_percent_of_b01_to_b12_without_self_reference():
    groups = build_tuho_opex_template()
    result = compute_annual_opex(groups, years=30)
    groups_by_code = {group.code: group for group in groups}
    b13_item = groups_by_code["B.13"].item_by_code("B.13.1")

    assert b13_item.basis == OpexBasis.PCT_OF_SELECTED_GROUPS
    assert "B.13" not in b13_item.selected_group_codes
    assert b13_item.budget_keur == 6.0
    assert groups_by_code["B.13"].contingency_pct == 0.0

    for year in range(1, 31):
        selected = sum(result.group_result(year, f"B.{idx:02d}").group_total_keur for idx in range(1, 13))
        b13 = result.group_result(year, "B.13").group_total_keur
        assert b13 == pytest.approx(selected * 0.06, abs=0.01)


def test_selected_annual_values_match_excel():
    result = compute_annual_opex(build_tuho_opex_template(), years=30)

    for year in (1, 2, 3, 10, 15, 20, 25, 30):
        assert result.total_for_year(year) == pytest.approx(EXCEL_ANNUAL_TOTALS[year - 1], abs=0.01)
