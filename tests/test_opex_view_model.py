"""
Tests for OpexViewModel builder and compute_year_values formula.

Uses the live TUHO and Oborovo project contexts.
Tests structural correctness, year-value formula accuracy, KPI derivations,
and editability contract.
"""

import math
import pytest

from app.ui.project_context import get_project_context
from app.ui.opex_view_model import (
    OpexGroupVM,
    OpexLineVM,
    OpexViewModel,
    build_opex_view_model,
    compute_year_values,
    DEFAULT_DISPLAY_YEARS,
    MAX_DISPLAY_YEARS,
    _CONTINGENCY_CODE,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def tuho_ctx():
    return get_project_context("tuho")


@pytest.fixture(scope="module")
def oborovo_ctx():
    return get_project_context("oborovo")


@pytest.fixture(scope="module")
def tuho_vm(tuho_ctx):
    return build_opex_view_model(tuho_ctx, is_user_project=False)


@pytest.fixture(scope="module")
def tuho_vm_user(tuho_ctx):
    return build_opex_view_model(tuho_ctx, is_user_project=True)


@pytest.fixture(scope="module")
def oborovo_vm(oborovo_ctx):
    return build_opex_view_model(oborovo_ctx, is_user_project=False)


# ---------------------------------------------------------------------------
# compute_year_values — pure formula tests
# ---------------------------------------------------------------------------

class TestComputeYearValues:
    def test_y1_equals_input(self):
        vals = compute_year_values(100.0, 2.0, 5)
        assert abs(vals[0] - 100.0) < 1e-9

    def test_y2_escalated(self):
        vals = compute_year_values(100.0, 2.0, 5)
        assert abs(vals[1] - 102.0) < 1e-9

    def test_y5_formula(self):
        # Y5 = 100 × 1.02^4
        vals = compute_year_values(100.0, 2.0, 5)
        expected = 100.0 * (1.02 ** 4)
        assert abs(vals[4] - expected) < 1e-9

    def test_length_equals_n_years(self):
        vals = compute_year_values(500.0, 3.0, 10)
        assert len(vals) == 10

    def test_zero_inflation_flat(self):
        vals = compute_year_values(200.0, 0.0, 5)
        assert all(abs(v - 200.0) < 1e-9 for v in vals)

    def test_zero_y1_stays_zero(self):
        vals = compute_year_values(0.0, 5.0, 10)
        assert all(abs(v) < 1e-9 for v in vals)

    def test_n_years_one_returns_y1(self):
        vals = compute_year_values(300.0, 2.0, 1)
        assert len(vals) == 1
        assert abs(vals[0] - 300.0) < 1e-9

    def test_monotone_increasing_with_positive_inflation(self):
        vals = compute_year_values(100.0, 5.0, 10)
        assert all(vals[i] < vals[i + 1] for i in range(len(vals) - 1))


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

class TestOpexViewModelStructure:
    def test_returns_opex_view_model(self, tuho_vm):
        assert isinstance(tuho_vm, OpexViewModel)

    def test_thirteen_groups(self, tuho_vm):
        # B.01–B.13
        assert len(tuho_vm.groups) == 13

    def test_group_codes_b01_to_b13(self, tuho_vm):
        codes = [g.code for g in tuho_vm.groups]
        assert codes[0] == "B.01"
        assert codes[-1] == "B.13"

    def test_all_groups_are_opex_group_vm(self, tuho_vm):
        for g in tuho_vm.groups:
            assert isinstance(g, OpexGroupVM)

    def test_all_lines_are_opex_line_vm(self, tuho_vm):
        for g in tuho_vm.groups:
            for ln in g.lines:
                assert isinstance(ln, OpexLineVM)

    def test_lines_have_correct_parent_code(self, tuho_vm):
        for g in tuho_vm.groups:
            for ln in g.lines:
                assert ln.parent_code == g.code

    def test_b13_is_contingency(self, tuho_vm):
        b13 = next(g for g in tuho_vm.groups if g.code == "B.13")
        assert b13.is_contingency is True

    def test_non_b13_not_contingency(self, tuho_vm):
        for g in tuho_vm.groups:
            if g.code != "B.13":
                assert g.is_contingency is False

    def test_project_name_populated(self, tuho_vm, tuho_ctx):
        assert tuho_vm.project_name == tuho_ctx.name

    def test_capacity_mw_populated(self, tuho_vm, tuho_ctx):
        assert tuho_vm.capacity_mw == tuho_ctx.capacity_mw

    def test_p50_annual_mwh(self, tuho_vm, tuho_ctx):
        expected = tuho_ctx.operating_hours_p50 * tuho_ctx.capacity_mw
        assert abs(tuho_vm.p50_annual_mwh - expected) < 1e-6

    def test_oborovo_thirteen_groups(self, oborovo_vm):
        assert len(oborovo_vm.groups) == 13


# ---------------------------------------------------------------------------
# Display years
# ---------------------------------------------------------------------------

class TestDisplayYears:
    def test_default_display_years(self, tuho_vm):
        assert tuho_vm.display_years == DEFAULT_DISPLAY_YEARS

    def test_year_values_length_matches_display_years(self, tuho_vm):
        for g in tuho_vm.groups:
            for ln in g.lines:
                assert len(ln.year_values) == tuho_vm.display_years

    def test_subtotal_per_year_length_matches_display_years(self, tuho_vm):
        for g in tuho_vm.groups:
            assert len(g.subtotal_per_year) == tuho_vm.display_years

    def test_total_excl_length_matches_display_years(self, tuho_vm):
        assert len(tuho_vm.total_excl_contingency) == tuho_vm.display_years

    def test_total_incl_length_matches_display_years(self, tuho_vm):
        assert len(tuho_vm.total_incl_contingency) == tuho_vm.display_years

    def test_custom_display_years_5(self, tuho_ctx):
        vm5 = build_opex_view_model(tuho_ctx, display_years=5)
        assert vm5.display_years == 5
        for g in vm5.groups:
            for ln in g.lines:
                assert len(ln.year_values) == 5

    def test_display_years_clamped_to_max(self, tuho_ctx):
        vm = build_opex_view_model(tuho_ctx, display_years=9999)
        assert vm.display_years == MAX_DISPLAY_YEARS

    def test_display_years_clamped_to_min_1(self, tuho_ctx):
        vm = build_opex_view_model(tuho_ctx, display_years=0)
        assert vm.display_years == 1


# ---------------------------------------------------------------------------
# Totals and KPIs
# ---------------------------------------------------------------------------

class TestTotalsAndKPIs:
    def test_total_excl_y1_equals_sum_of_non_contingency_group_subtotals(self, tuho_vm):
        non_cont = [g for g in tuho_vm.groups if not g.is_contingency]
        expected_y1 = sum(g.subtotal_per_year[0] for g in non_cont)
        assert abs(tuho_vm.total_excl_contingency[0] - expected_y1) < 1e-6

    def test_total_incl_y1_applies_contingency_rate(self, tuho_vm):
        excl_y1 = tuho_vm.total_excl_contingency[0]
        rate = tuho_vm.contingency_rate
        expected = excl_y1 * (1.0 + rate / 100.0)
        assert abs(tuho_vm.total_incl_contingency[0] - expected) < 1e-6

    def test_total_incl_gte_total_excl_for_positive_rate(self, tuho_vm):
        for yr in range(tuho_vm.display_years):
            assert tuho_vm.total_incl_contingency[yr] >= tuho_vm.total_excl_contingency[yr]

    def test_group_subtotal_per_year_y1_equals_sum_active_line_y1(self, tuho_vm):
        for g in tuho_vm.groups:
            if g.is_contingency:
                continue
            active = [ln for ln in g.lines if ln.is_active and not ln.is_contingency]
            expected = sum(ln.year_values[0] for ln in active)
            assert abs(g.subtotal_per_year[0] - expected) < 1e-6

    def test_opex_per_mw_y1_formula(self, tuho_vm):
        expected = tuho_vm.total_incl_contingency[0] / tuho_vm.capacity_mw
        assert abs(tuho_vm.opex_per_mw_y1 - expected) < 1e-6

    def test_opex_per_mwh_y1_formula(self, tuho_vm):
        expected = tuho_vm.total_incl_contingency[0] * 1000.0 / tuho_vm.p50_annual_mwh
        assert abs(tuho_vm.opex_per_mwh_y1 - expected) < 1e-6

    def test_opex_per_mwh_positive(self, tuho_vm):
        assert tuho_vm.opex_per_mwh_y1 > 0

    def test_contingency_rate_from_project_ctx(self, tuho_vm, tuho_ctx):
        assert abs(tuho_vm.contingency_rate - tuho_ctx.opex_contingency_pct) < 1e-9

    def test_b13_subtotal_per_year_is_zero(self, tuho_vm):
        # B.13 is a contingency group — subtotal from sub-lines is 0
        # (contingency is applied at the total level, not summed from lines)
        b13 = next(g for g in tuho_vm.groups if g.code == "B.13")
        assert all(v == 0 for v in b13.subtotal_per_year)

    def test_total_excl_is_positive(self, tuho_vm):
        assert tuho_vm.total_excl_contingency[0] > 0

    def test_oborovo_kpis_are_positive(self, oborovo_vm):
        assert oborovo_vm.opex_per_mw_y1 > 0
        assert oborovo_vm.opex_per_mwh_y1 > 0


# ---------------------------------------------------------------------------
# Editability
# ---------------------------------------------------------------------------

class TestEditabilityContract:
    def test_non_user_no_lines_editable(self, tuho_vm):
        all_lines = [ln for g in tuho_vm.groups for ln in g.lines]
        assert not any(ln.is_editable for ln in all_lines)

    def test_user_project_editable_lines_exist(self, tuho_vm_user):
        all_lines = [ln for g in tuho_vm_user.groups for ln in g.lines]
        assert any(ln.is_editable for ln in all_lines)

    def test_contingency_lines_never_editable_even_for_user(self, tuho_vm_user):
        b13 = next(g for g in tuho_vm_user.groups if g.code == "B.13")
        assert not any(ln.is_editable for ln in b13.lines)

    def test_is_group_always_false_on_lines(self, tuho_vm):
        for g in tuho_vm.groups:
            for ln in g.lines:
                assert ln.is_group is False

    def test_is_contingency_true_on_b13_lines(self, tuho_vm):
        b13 = next(g for g in tuho_vm.groups if g.code == "B.13")
        for ln in b13.lines:
            assert ln.is_contingency is True

    def test_is_contingency_false_on_non_b13_lines(self, tuho_vm):
        for g in tuho_vm.groups:
            if g.code == "B.13":
                continue
            for ln in g.lines:
                assert ln.is_contingency is False

    def test_custom_and_active_defaults(self, tuho_vm):
        """Future fields: is_custom=False, is_active=True for all template lines."""
        for g in tuho_vm.groups:
            for ln in g.lines:
                assert ln.is_custom is False
                assert ln.is_active is True

    def test_is_user_project_flag_propagates(self, tuho_vm, tuho_vm_user):
        assert tuho_vm.is_user_project is False
        assert tuho_vm_user.is_user_project is True


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_zero_capacity_does_not_raise(self):
        import dataclasses
        ctx = get_project_context("tuho")
        patched = dataclasses.replace(ctx, capacity_mw=0.0)
        vm = build_opex_view_model(patched)
        assert vm.opex_per_mw_y1 == 0.0
        assert vm.opex_per_mwh_y1 == 0.0

    def test_zero_p50_hours_does_not_raise(self):
        import dataclasses
        ctx = get_project_context("tuho")
        patched = dataclasses.replace(ctx, operating_hours_p50=0.0)
        vm = build_opex_view_model(patched)
        assert vm.opex_per_mwh_y1 == 0.0

    def test_b01_has_lines(self, tuho_vm):
        b01 = next(g for g in tuho_vm.groups if g.code == "B.01")
        assert len(b01.lines) > 0

    def test_b01_lines_have_year_values(self, tuho_vm):
        b01 = next(g for g in tuho_vm.groups if g.code == "B.01")
        for ln in b01.lines:
            assert len(ln.year_values) == tuho_vm.display_years
