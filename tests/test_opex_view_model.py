"""
Tests for OpexViewModel builder and compute_year_values formula.

Uses live TUHO and Oborovo project contexts.
Tests structural correctness, row identity, year-value formula accuracy,
KPI derivations, denominator-None contract, and editability contract.
"""

import dataclasses
import pytest

from app.ui.project_context import get_project_context
from app.ui.opex_view_model import (
    AddOpexLineCommand,
    DeactivateOpexLineCommand,
    OpexGroupVM,
    OpexLineVM,
    OpexViewModel,
    UpdateOpexLineCommand,
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
    # Default display years = 30
    return build_opex_view_model(tuho_ctx, is_user_project=False)


@pytest.fixture(scope="module")
def tuho_vm_user(tuho_ctx):
    return build_opex_view_model(tuho_ctx, is_user_project=True)


@pytest.fixture(scope="module")
def tuho_vm_10(tuho_ctx):
    return build_opex_view_model(tuho_ctx, display_years=10)


@pytest.fixture(scope="module")
def oborovo_vm(oborovo_ctx):
    return build_opex_view_model(oborovo_ctx, is_user_project=False)


def _all_lines(vm: OpexViewModel) -> list[OpexLineVM]:
    return [ln for g in vm.groups for ln in g.lines]


# ---------------------------------------------------------------------------
# compute_year_values — pure formula
# ---------------------------------------------------------------------------

class TestComputeYearValues:
    def test_y1_equals_input(self):
        vals = compute_year_values(100.0, 2.0, 5)
        assert abs(vals[0] - 100.0) < 1e-9

    def test_y2_escalated(self):
        vals = compute_year_values(100.0, 2.0, 5)
        assert abs(vals[1] - 102.0) < 1e-9

    def test_y5_formula(self):
        vals = compute_year_values(100.0, 2.0, 5)
        expected = 100.0 * (1.02 ** 4)
        assert abs(vals[4] - expected) < 1e-9

    def test_length_equals_n_years(self):
        assert len(compute_year_values(500.0, 3.0, 10)) == 10

    def test_zero_inflation_flat(self):
        vals = compute_year_values(200.0, 0.0, 5)
        assert all(abs(v - 200.0) < 1e-9 for v in vals)

    def test_zero_y1_stays_zero(self):
        assert all(abs(v) < 1e-9 for v in compute_year_values(0.0, 5.0, 10))

    def test_n_years_one_returns_y1(self):
        vals = compute_year_values(300.0, 2.0, 1)
        assert len(vals) == 1
        assert abs(vals[0] - 300.0) < 1e-9

    def test_monotone_increasing_positive_inflation(self):
        vals = compute_year_values(100.0, 5.0, 10)
        assert all(vals[i] < vals[i + 1] for i in range(len(vals) - 1))

    def test_30_years_length(self):
        assert len(compute_year_values(100.0, 2.0, 30)) == 30


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

class TestStructure:
    def test_returns_opex_view_model(self, tuho_vm):
        assert isinstance(tuho_vm, OpexViewModel)

    def test_thirteen_groups(self, tuho_vm):
        assert len(tuho_vm.groups) == 13

    def test_group_codes_b01_to_b13(self, tuho_vm):
        codes = [g.code for g in tuho_vm.groups]
        assert codes[0] == "B.01"
        assert codes[-1] == "B.13"

    def test_all_groups_are_opex_group_vm(self, tuho_vm):
        for g in tuho_vm.groups:
            assert isinstance(g, OpexGroupVM)

    def test_all_lines_are_opex_line_vm(self, tuho_vm):
        for ln in _all_lines(tuho_vm):
            assert isinstance(ln, OpexLineVM)

    def test_lines_parent_code_matches_group(self, tuho_vm):
        for g in tuho_vm.groups:
            for ln in g.lines:
                assert ln.parent_code == g.code

    def test_b13_is_contingency(self, tuho_vm):
        b13 = next(g for g in tuho_vm.groups if g.code == _CONTINGENCY_CODE)
        assert b13.is_contingency is True

    def test_non_b13_not_contingency(self, tuho_vm):
        for g in tuho_vm.groups:
            if g.code != _CONTINGENCY_CODE:
                assert g.is_contingency is False

    def test_project_name_populated(self, tuho_vm, tuho_ctx):
        assert tuho_vm.project_name == tuho_ctx.name

    def test_capacity_mw_populated(self, tuho_vm, tuho_ctx):
        assert tuho_vm.capacity_mw == tuho_ctx.capacity_mw

    def test_p50_annual_mwh(self, tuho_vm, tuho_ctx):
        expected = tuho_ctx.operating_hours_p50 * tuho_ctx.capacity_mw
        assert abs(tuho_vm.p50_annual_mwh - expected) < 1e-6

    def test_is_group_always_false_on_lines(self, tuho_vm):
        for ln in _all_lines(tuho_vm):
            assert ln.is_group is False

    def test_oborovo_thirteen_groups(self, oborovo_vm):
        assert len(oborovo_vm.groups) == 13

    def test_b01_has_lines(self, tuho_vm):
        b01 = next(g for g in tuho_vm.groups if g.code == "B.01")
        assert len(b01.lines) > 0


# ---------------------------------------------------------------------------
# Row identity — row_id, source, unit, notes, display_order, validation_status
# ---------------------------------------------------------------------------

class TestRowIdentity:
    def test_every_line_has_row_id(self, tuho_vm):
        for ln in _all_lines(tuho_vm):
            assert ln.row_id and isinstance(ln.row_id, str)

    def test_row_id_is_deterministic(self, tuho_ctx):
        vm1 = build_opex_view_model(tuho_ctx)
        vm2 = build_opex_view_model(tuho_ctx)
        ids1 = [ln.row_id for ln in _all_lines(vm1)]
        ids2 = [ln.row_id for ln in _all_lines(vm2)]
        assert ids1 == ids2

    def test_row_id_contains_project_code(self, tuho_vm, tuho_ctx):
        for ln in _all_lines(tuho_vm):
            assert tuho_ctx.code in ln.row_id

    def test_row_ids_are_unique(self, tuho_vm):
        ids = [ln.row_id for ln in _all_lines(tuho_vm)]
        assert len(ids) == len(set(ids))

    def test_every_line_has_source(self, tuho_vm):
        for ln in _all_lines(tuho_vm):
            assert ln.source and isinstance(ln.source, str)

    def test_every_line_unit_is_keur(self, tuho_vm):
        for ln in _all_lines(tuho_vm):
            assert ln.unit == "kEUR"

    def test_every_line_has_notes_field(self, tuho_vm):
        for ln in _all_lines(tuho_vm):
            assert isinstance(ln.notes, str)

    def test_every_line_has_display_order(self, tuho_vm):
        for ln in _all_lines(tuho_vm):
            assert isinstance(ln.display_order, int)
            assert ln.display_order >= 1

    def test_display_order_starts_at_1_per_group(self, tuho_vm):
        for g in tuho_vm.groups:
            if g.lines:
                assert g.lines[0].display_order == 1

    def test_every_line_has_validation_status(self, tuho_vm):
        for ln in _all_lines(tuho_vm):
            assert isinstance(ln.validation_status, str)
            assert ln.validation_status  # not empty

    def test_no_missing_names(self, tuho_vm):
        for ln in _all_lines(tuho_vm):
            assert ln.name and ln.name.strip()

    def test_oborovo_row_ids_differ_from_tuho(self, tuho_vm, oborovo_vm):
        tuho_ids = set(ln.row_id for ln in _all_lines(tuho_vm))
        obo_ids = set(ln.row_id for ln in _all_lines(oborovo_vm))
        assert tuho_ids.isdisjoint(obo_ids)


# ---------------------------------------------------------------------------
# OPEX-specific flags: B.13, is_fixed, is_variable
# ---------------------------------------------------------------------------

class TestOpexFlags:
    def test_b13_lines_are_contingency(self, tuho_vm):
        b13 = next(g for g in tuho_vm.groups if g.code == _CONTINGENCY_CODE)
        for ln in b13.lines:
            assert ln.is_contingency is True

    def test_b13_lines_are_derived(self, tuho_vm):
        b13 = next(g for g in tuho_vm.groups if g.code == _CONTINGENCY_CODE)
        for ln in b13.lines:
            assert ln.is_derived is True

    def test_b13_lines_are_read_only_even_for_user(self, tuho_vm_user):
        b13 = next(g for g in tuho_vm_user.groups if g.code == _CONTINGENCY_CODE)
        for ln in b13.lines:
            assert ln.is_read_only is True
            assert ln.is_editable is False

    def test_non_b13_lines_not_contingency(self, tuho_vm):
        for g in tuho_vm.groups:
            if g.code == _CONTINGENCY_CODE:
                continue
            for ln in g.lines:
                assert ln.is_contingency is False

    def test_non_b13_lines_not_derived(self, tuho_vm):
        for g in tuho_vm.groups:
            if g.code == _CONTINGENCY_CODE:
                continue
            for ln in g.lines:
                assert ln.is_derived is False

    def test_is_fixed_default_true(self, tuho_vm):
        for ln in _all_lines(tuho_vm):
            assert ln.is_fixed is True

    def test_is_variable_default_false(self, tuho_vm):
        for ln in _all_lines(tuho_vm):
            assert ln.is_variable is False

    def test_wht_flag_is_bool(self, tuho_vm):
        for ln in _all_lines(tuho_vm):
            assert isinstance(ln.wht_flag, bool)


# ---------------------------------------------------------------------------
# Display years
# ---------------------------------------------------------------------------

class TestDisplayYears:
    def test_default_display_years_is_30(self, tuho_vm):
        assert tuho_vm.display_years == DEFAULT_DISPLAY_YEARS
        assert tuho_vm.display_years == 30

    def test_display_years_10(self, tuho_vm_10):
        assert tuho_vm_10.display_years == 10

    def test_year_values_length_30(self, tuho_vm):
        for ln in _all_lines(tuho_vm):
            assert len(ln.year_values) == 30

    def test_year_values_length_10(self, tuho_vm_10):
        for ln in _all_lines(tuho_vm_10):
            assert len(ln.year_values) == 10

    def test_subtotal_per_year_length_30(self, tuho_vm):
        for g in tuho_vm.groups:
            assert len(g.subtotal_per_year) == 30

    def test_subtotal_per_year_length_10(self, tuho_vm_10):
        for g in tuho_vm_10.groups:
            assert len(g.subtotal_per_year) == 10

    def test_total_excl_length_30(self, tuho_vm):
        assert len(tuho_vm.total_excl_contingency) == 30

    def test_total_incl_length_30(self, tuho_vm):
        assert len(tuho_vm.total_incl_contingency) == 30

    def test_contingency_by_year_length_30(self, tuho_vm):
        assert len(tuho_vm.contingency_by_year) == 30

    def test_display_years_clamped_to_max(self, tuho_ctx):
        vm = build_opex_view_model(tuho_ctx, display_years=9999)
        assert vm.display_years == MAX_DISPLAY_YEARS

    def test_display_years_clamped_to_min_1(self, tuho_ctx):
        vm = build_opex_view_model(tuho_ctx, display_years=0)
        assert vm.display_years == 1


# ---------------------------------------------------------------------------
# Totals and contingency breakdown
# ---------------------------------------------------------------------------

class TestTotalsAndContingency:
    def test_total_excl_y1_equals_sum_of_non_contingency_groups(self, tuho_vm):
        non_cont = [g for g in tuho_vm.groups if not g.is_contingency]
        expected_y1 = sum(g.subtotal_per_year[0] for g in non_cont)
        assert abs(tuho_vm.total_excl_contingency[0] - expected_y1) < 1e-6

    def test_contingency_by_year_formula(self, tuho_vm):
        rate = tuho_vm.contingency_rate
        for yr in range(tuho_vm.display_years):
            expected = tuho_vm.total_excl_contingency[yr] * rate / 100.0
            assert abs(tuho_vm.contingency_by_year[yr] - expected) < 1e-6

    def test_total_incl_equals_excl_plus_contingency(self, tuho_vm):
        for yr in range(tuho_vm.display_years):
            expected = (
                tuho_vm.total_excl_contingency[yr]
                + tuho_vm.contingency_by_year[yr]
            )
            assert abs(tuho_vm.total_incl_contingency[yr] - expected) < 1e-6

    def test_total_incl_gte_excl_for_positive_rate(self, tuho_vm):
        for yr in range(tuho_vm.display_years):
            assert tuho_vm.total_incl_contingency[yr] >= tuho_vm.total_excl_contingency[yr]

    def test_y1_total_opex_equals_total_incl_y1(self, tuho_vm):
        assert abs(tuho_vm.y1_total_opex - tuho_vm.total_incl_contingency[0]) < 1e-9

    def test_final_year_total_opex_equals_total_incl_last(self, tuho_vm):
        assert abs(
            tuho_vm.final_year_total_opex - tuho_vm.total_incl_contingency[-1]
        ) < 1e-9

    def test_final_year_total_gte_y1_for_positive_inflation(self, tuho_vm):
        # With positive inflation the final year total should exceed Y1
        assert tuho_vm.final_year_total_opex >= tuho_vm.y1_total_opex

    def test_contingency_by_year_exists(self, tuho_vm):
        assert isinstance(tuho_vm.contingency_by_year, tuple)
        assert len(tuho_vm.contingency_by_year) == tuho_vm.display_years

    def test_y1_total_opex_exists(self, tuho_vm):
        assert isinstance(tuho_vm.y1_total_opex, float)

    def test_final_year_total_opex_exists(self, tuho_vm):
        assert isinstance(tuho_vm.final_year_total_opex, float)

    def test_b13_subtotal_per_year_is_zero(self, tuho_vm):
        b13 = next(g for g in tuho_vm.groups if g.code == _CONTINGENCY_CODE)
        assert all(v == 0 for v in b13.subtotal_per_year)

    def test_contingency_rate_from_project_ctx(self, tuho_vm, tuho_ctx):
        assert abs(tuho_vm.contingency_rate - tuho_ctx.opex_contingency_pct) < 1e-9

    def test_group_subtotal_y1_equals_sum_active_line_y1(self, tuho_vm):
        for g in tuho_vm.groups:
            if g.is_contingency:
                continue
            active = [ln for ln in g.lines if ln.is_active and not ln.is_contingency]
            expected = sum(ln.year_values[0] for ln in active)
            assert abs(g.subtotal_per_year[0] - expected) < 1e-6


# ---------------------------------------------------------------------------
# KPIs — denominator-None contract
# ---------------------------------------------------------------------------

class TestKPIDenominatorContract:
    def test_opex_per_mw_y1_is_float_when_capacity_positive(self, tuho_vm):
        assert isinstance(tuho_vm.opex_per_mw_y1, float)

    def test_opex_per_mwh_y1_is_float_when_p50_positive(self, tuho_vm):
        assert isinstance(tuho_vm.opex_per_mwh_y1, float)

    def test_opex_per_mw_none_when_zero_capacity(self):
        ctx = get_project_context("tuho")
        patched = dataclasses.replace(ctx, capacity_mw=0.0)
        vm = build_opex_view_model(patched)
        assert vm.opex_per_mw_y1 is None

    def test_opex_per_mwh_none_when_zero_capacity(self):
        ctx = get_project_context("tuho")
        patched = dataclasses.replace(ctx, capacity_mw=0.0)
        vm = build_opex_view_model(patched)
        # p50_annual_mwh = 0 * hours = 0 → None
        assert vm.opex_per_mwh_y1 is None

    def test_opex_per_mwh_none_when_zero_p50_hours(self):
        ctx = get_project_context("tuho")
        patched = dataclasses.replace(ctx, operating_hours_p50=0.0)
        vm = build_opex_view_model(patched)
        assert vm.opex_per_mwh_y1 is None

    def test_kpi_values_not_fake_zero(self, tuho_vm):
        # For a valid project with positive capacity and p50 hours, KPIs must be positive
        assert tuho_vm.opex_per_mw_y1 is not None
        assert tuho_vm.opex_per_mw_y1 > 0
        assert tuho_vm.opex_per_mwh_y1 is not None
        assert tuho_vm.opex_per_mwh_y1 > 0

    def test_opex_per_mw_formula(self, tuho_vm):
        expected = tuho_vm.y1_total_opex / tuho_vm.capacity_mw
        assert abs(tuho_vm.opex_per_mw_y1 - expected) < 1e-6

    def test_opex_per_mwh_formula(self, tuho_vm):
        expected = tuho_vm.y1_total_opex * 1000.0 / tuho_vm.p50_annual_mwh
        assert abs(tuho_vm.opex_per_mwh_y1 - expected) < 1e-6

    def test_oborovo_kpis_are_positive(self, oborovo_vm):
        assert oborovo_vm.opex_per_mw_y1 is not None
        assert oborovo_vm.opex_per_mw_y1 > 0
        assert oborovo_vm.opex_per_mwh_y1 is not None
        assert oborovo_vm.opex_per_mwh_y1 > 0


# ---------------------------------------------------------------------------
# Editability contract
# ---------------------------------------------------------------------------

class TestEditability:
    def test_non_user_no_editable_lines(self, tuho_vm):
        assert not any(ln.is_editable for ln in _all_lines(tuho_vm))

    def test_non_user_all_read_only(self, tuho_vm):
        assert all(ln.is_read_only for ln in _all_lines(tuho_vm))

    def test_user_project_has_editable_lines(self, tuho_vm_user):
        assert any(ln.is_editable for ln in _all_lines(tuho_vm_user))

    def test_b13_never_editable(self, tuho_vm_user):
        b13 = next(g for g in tuho_vm_user.groups if g.code == _CONTINGENCY_CODE)
        assert not any(ln.is_editable for ln in b13.lines)

    def test_editable_and_read_only_mutually_exclusive(self, tuho_vm_user):
        for ln in _all_lines(tuho_vm_user):
            assert not (ln.is_editable and ln.is_read_only)

    def test_custom_and_active_defaults(self, tuho_vm):
        for ln in _all_lines(tuho_vm):
            assert ln.is_custom is False
            assert ln.is_active is True

    def test_is_user_project_false(self, tuho_vm):
        assert tuho_vm.is_user_project is False

    def test_is_user_project_true(self, tuho_vm_user):
        assert tuho_vm_user.is_user_project is True


# ---------------------------------------------------------------------------
# Mutation command dataclasses
# ---------------------------------------------------------------------------

class TestMutationCommands:
    def test_add_command_instantiates(self):
        cmd = AddOpexLineCommand(
            project_code="tuho",
            parent_group_code="B.06",
            name="Extra Insurance",
            y1_keur=50.0,
            inflation_pct=2.0,
        )
        assert cmd.parent_group_code == "B.06"
        assert cmd.y1_keur == 50.0

    def test_update_command_instantiates(self):
        cmd = UpdateOpexLineCommand(
            project_code="tuho",
            line_code="B.06.01",
            new_y1_keur=75.0,
        )
        assert cmd.new_y1_keur == 75.0

    def test_deactivate_command_instantiates(self):
        cmd = DeactivateOpexLineCommand(
            project_code="tuho",
            line_code="B.06.01",
        )
        assert cmd.line_code == "B.06.01"

    def test_commands_are_frozen(self):
        cmd = AddOpexLineCommand(
            project_code="tuho",
            parent_group_code="B.06",
            name="Test",
            y1_keur=10.0,
        )
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            cmd.y1_keur = 999.0  # type: ignore
