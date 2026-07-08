"""
Tests for CapexViewModel builder.

Uses live TUHO and Oborovo project contexts. Tests structural correctness,
stable row identity, editability contract, flag semantics, and derived totals.
"""

import dataclasses
import pytest

from app.ui.project_context import get_project_context
from app.ui.capex_view_model import (
    AddCapexLineCommand,
    CapexGroupVM,
    CapexLineVM,
    CapexViewModel,
    DeactivateCapexLineCommand,
    UpdateCapexLineCommand,
    build_capex_view_model,
    _READONLY_GROUP_CODES,
    _CONTINGENCY_CODE,
    _FINANCING_CODE,
    _RESERVE_CODE,
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
    return build_capex_view_model(tuho_ctx, is_user_project=False)


@pytest.fixture(scope="module")
def tuho_vm_user(tuho_ctx):
    return build_capex_view_model(tuho_ctx, is_user_project=True)


@pytest.fixture(scope="module")
def oborovo_vm(oborovo_ctx):
    return build_capex_view_model(oborovo_ctx, is_user_project=False)


def _all_lines(vm: CapexViewModel) -> list[CapexLineVM]:
    return [ln for g in vm.groups for ln in g.lines]


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

class TestStructure:
    def test_returns_capex_view_model(self, tuho_vm):
        assert isinstance(tuho_vm, CapexViewModel)

    def test_eighteen_groups(self, tuho_vm):
        assert len(tuho_vm.groups) == 18

    def test_group_codes_c01_to_c18(self, tuho_vm):
        codes = [g.code for g in tuho_vm.groups]
        assert codes[0] == "C.01"
        assert codes[-1] == "C.18"

    def test_all_groups_are_capex_group_vm(self, tuho_vm):
        for g in tuho_vm.groups:
            assert isinstance(g, CapexGroupVM)

    def test_all_lines_are_capex_line_vm(self, tuho_vm):
        for ln in _all_lines(tuho_vm):
            assert isinstance(ln, CapexLineVM)

    def test_lines_parent_code_matches_group(self, tuho_vm):
        for g in tuho_vm.groups:
            for ln in g.lines:
                assert ln.parent_code == g.code

    def test_project_name_populated(self, tuho_vm, tuho_ctx):
        assert tuho_vm.project_name == tuho_ctx.name

    def test_capacity_mw_populated(self, tuho_vm, tuho_ctx):
        assert tuho_vm.capacity_mw == tuho_ctx.capacity_mw

    def test_oborovo_eighteen_groups(self, oborovo_vm):
        assert len(oborovo_vm.groups) == 18

    def test_is_group_always_false_on_lines(self, tuho_vm):
        for ln in _all_lines(tuho_vm):
            assert ln.is_group is False


# ---------------------------------------------------------------------------
# Row identity — row_id, source, unit, notes, display_order, validation_status
# ---------------------------------------------------------------------------

class TestRowIdentity:
    def test_every_line_has_row_id(self, tuho_vm):
        for ln in _all_lines(tuho_vm):
            assert ln.row_id and isinstance(ln.row_id, str)

    def test_row_id_is_deterministic(self, tuho_ctx):
        vm1 = build_capex_view_model(tuho_ctx, is_user_project=False)
        vm2 = build_capex_view_model(tuho_ctx, is_user_project=False)
        ids1 = [ln.row_id for ln in _all_lines(vm1)]
        ids2 = [ln.row_id for ln in _all_lines(vm2)]
        assert ids1 == ids2

    def test_row_id_contains_project_code(self, tuho_vm, tuho_ctx):
        for ln in _all_lines(tuho_vm):
            assert tuho_ctx.code in ln.row_id

    def test_row_id_contains_parent_and_line_code(self, tuho_vm):
        for ln in _all_lines(tuho_vm):
            assert ln.parent_code in ln.row_id
            assert ln.code in ln.row_id

    def test_row_ids_are_unique_within_project(self, tuho_vm):
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
        valid = {"ok", "unmapped", "partial", "mismatch", "backend_calculated", "unknown"}
        for ln in _all_lines(tuho_vm):
            assert ln.validation_status in valid

    def test_no_missing_names(self, tuho_vm):
        for ln in _all_lines(tuho_vm):
            assert ln.name and ln.name.strip()

    def test_oborovo_row_ids_differ_from_tuho(self, tuho_vm, oborovo_vm):
        tuho_ids = set(ln.row_id for ln in _all_lines(tuho_vm))
        oborovo_ids = set(ln.row_id for ln in _all_lines(oborovo_vm))
        assert tuho_ids.isdisjoint(oborovo_ids)


# ---------------------------------------------------------------------------
# CAPEX-specific flags: C.13, C.17, C.18
# ---------------------------------------------------------------------------

class TestCapexFlags:
    def test_c13_group_is_contingency(self, tuho_vm):
        c13 = next(g for g in tuho_vm.groups if g.code == _CONTINGENCY_CODE)
        assert c13.is_contingency is True

    def test_c13_lines_are_contingency(self, tuho_vm):
        c13 = next(g for g in tuho_vm.groups if g.code == _CONTINGENCY_CODE)
        for ln in c13.lines:
            assert ln.is_contingency is True

    def test_c13_lines_are_derived(self, tuho_vm):
        c13 = next(g for g in tuho_vm.groups if g.code == _CONTINGENCY_CODE)
        for ln in c13.lines:
            assert ln.is_derived is True

    def test_c13_lines_are_read_only(self, tuho_vm_user):
        c13 = next(g for g in tuho_vm_user.groups if g.code == _CONTINGENCY_CODE)
        for ln in c13.lines:
            assert ln.is_read_only is True

    def test_c17_group_is_readonly(self, tuho_vm):
        c17 = next(g for g in tuho_vm.groups if g.code == _FINANCING_CODE)
        assert c17.is_readonly is True

    def test_c17_group_is_financing(self, tuho_vm):
        c17 = next(g for g in tuho_vm.groups if g.code == _FINANCING_CODE)
        assert c17.is_financing is True

    def test_c17_lines_are_financing(self, tuho_vm):
        c17 = next(g for g in tuho_vm.groups if g.code == _FINANCING_CODE)
        for ln in c17.lines:
            assert ln.is_financing is True

    def test_c17_lines_are_derived(self, tuho_vm):
        c17 = next(g for g in tuho_vm.groups if g.code == _FINANCING_CODE)
        for ln in c17.lines:
            assert ln.is_derived is True

    def test_c17_lines_are_read_only(self, tuho_vm_user):
        c17 = next(g for g in tuho_vm_user.groups if g.code == _FINANCING_CODE)
        for ln in c17.lines:
            assert ln.is_read_only is True
            assert ln.is_editable is False

    def test_c17_lines_have_readonly_financing_alias(self, tuho_vm):
        c17 = next(g for g in tuho_vm.groups if g.code == _FINANCING_CODE)
        for ln in c17.lines:
            assert ln.is_readonly_financing is True

    def test_c18_group_is_readonly(self, tuho_vm):
        c18 = next(g for g in tuho_vm.groups if g.code == _RESERVE_CODE)
        assert c18.is_readonly is True

    def test_c18_group_is_reserve(self, tuho_vm):
        c18 = next(g for g in tuho_vm.groups if g.code == _RESERVE_CODE)
        assert c18.is_reserve is True

    def test_c18_lines_are_reserve(self, tuho_vm):
        c18 = next(g for g in tuho_vm.groups if g.code == _RESERVE_CODE)
        for ln in c18.lines:
            assert ln.is_reserve is True

    def test_c18_lines_are_derived(self, tuho_vm):
        c18 = next(g for g in tuho_vm.groups if g.code == _RESERVE_CODE)
        for ln in c18.lines:
            assert ln.is_derived is True

    def test_c01_not_contingency_not_financing_not_reserve(self, tuho_vm):
        c01 = next(g for g in tuho_vm.groups if g.code == "C.01")
        assert c01.is_contingency is False
        assert c01.is_financing is False
        assert c01.is_reserve is False
        for ln in c01.lines:
            assert ln.is_contingency is False
            assert ln.is_financing is False
            assert ln.is_reserve is False
            assert ln.is_readonly_financing is False


# ---------------------------------------------------------------------------
# Editability contract
# ---------------------------------------------------------------------------

class TestEditability:
    def test_non_user_no_editable_lines(self, tuho_vm):
        assert not any(ln.is_editable for ln in _all_lines(tuho_vm))

    def test_non_user_all_lines_read_only(self, tuho_vm):
        assert all(ln.is_read_only for ln in _all_lines(tuho_vm))

    def test_user_project_has_editable_lines(self, tuho_vm_user):
        assert any(ln.is_editable for ln in _all_lines(tuho_vm_user))

    def test_user_project_c17_never_editable(self, tuho_vm_user):
        c17 = next(g for g in tuho_vm_user.groups if g.code == _FINANCING_CODE)
        assert not any(ln.is_editable for ln in c17.lines)

    def test_user_project_c18_never_editable(self, tuho_vm_user):
        c18 = next(g for g in tuho_vm_user.groups if g.code == _RESERVE_CODE)
        assert not any(ln.is_editable for ln in c18.lines)

    def test_user_project_c13_never_editable(self, tuho_vm_user):
        c13 = next(g for g in tuho_vm_user.groups if g.code == _CONTINGENCY_CODE)
        assert not any(ln.is_editable for ln in c13.lines)

    def test_editable_and_read_only_are_mutually_exclusive(self, tuho_vm_user):
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
# Derived fields — per_mw, subtotals, totals
# ---------------------------------------------------------------------------

class TestDerivedFields:
    def test_per_mw_formula(self, tuho_vm, tuho_ctx):
        capacity = tuho_ctx.capacity_mw
        for ln in _all_lines(tuho_vm):
            expected = ln.amount_keur / capacity if capacity > 0 else 0.0
            assert abs(ln.per_mw - expected) < 1e-6

    def test_group_subtotal_equals_sum_of_active_lines(self, tuho_vm):
        for g in tuho_vm.groups:
            active = [ln for ln in g.lines if ln.is_active]
            expected = sum(ln.amount_keur for ln in active)
            assert abs(g.subtotal_keur - expected) < 1e-6

    def test_hard_capex_excludes_c17_c18(self, tuho_vm):
        readonly_sum = sum(
            g.subtotal_keur for g in tuho_vm.groups
            if g.code in _READONLY_GROUP_CODES
        )
        expected_hard = tuho_vm.total_capex_keur - readonly_sum
        assert abs(tuho_vm.hard_capex_keur - expected_hard) < 1e-6

    def test_total_capex_equals_hard_plus_financing_plus_reserve(self, tuho_vm):
        expected = (
            tuho_vm.hard_capex_keur
            + tuho_vm.financing_keur
            + tuho_vm.reserve_keur
        )
        assert abs(tuho_vm.total_capex_keur - expected) < 1e-6

    def test_total_per_mw_consistent(self, tuho_vm, tuho_ctx):
        capacity = tuho_ctx.capacity_mw
        expected = tuho_vm.total_capex_keur / capacity
        assert abs(tuho_vm.total_per_mw - expected) < 1e-6

    def test_c17_financing_keur_is_c17_subtotal(self, tuho_vm):
        c17 = next(g for g in tuho_vm.groups if g.code == _FINANCING_CODE)
        assert abs(tuho_vm.financing_keur - c17.subtotal_keur) < 1e-6

    def test_c18_reserve_keur_is_c18_subtotal(self, tuho_vm):
        c18 = next(g for g in tuho_vm.groups if g.code == _RESERVE_CODE)
        assert abs(tuho_vm.reserve_keur - c18.subtotal_keur) < 1e-6

    def test_c01_has_nonzero_subtotal(self, tuho_vm):
        c01 = next(g for g in tuho_vm.groups if g.code == "C.01")
        assert c01.subtotal_keur > 0

    def test_oborovo_total_positive(self, oborovo_vm):
        assert oborovo_vm.total_capex_keur > 0


# ---------------------------------------------------------------------------
# Segmented totals: editable_total_keur, derived_total_keur
# ---------------------------------------------------------------------------

class TestSegmentedTotals:
    def test_editable_total_exists(self, tuho_vm_user):
        assert isinstance(tuho_vm_user.editable_total_keur, float)

    def test_derived_total_exists(self, tuho_vm):
        assert isinstance(tuho_vm.derived_total_keur, float)

    def test_non_user_editable_total_is_zero(self, tuho_vm):
        assert tuho_vm.editable_total_keur == 0.0

    def test_user_project_editable_total_positive(self, tuho_vm_user):
        assert tuho_vm_user.editable_total_keur > 0

    def test_editable_total_matches_sum_of_editable_lines(self, tuho_vm_user):
        lines = _all_lines(tuho_vm_user)
        expected = sum(ln.amount_keur for ln in lines if ln.is_editable and ln.is_active)
        assert abs(tuho_vm_user.editable_total_keur - expected) < 1e-6

    def test_derived_total_matches_sum_of_derived_lines(self, tuho_vm):
        lines = _all_lines(tuho_vm)
        expected = sum(ln.amount_keur for ln in lines if ln.is_derived and ln.is_active)
        assert abs(tuho_vm.derived_total_keur - expected) < 1e-6

    def test_derived_total_includes_c17_c18_c13(self, tuho_vm):
        # derived_total must be at least the sum of C.17 + C.13 lines
        financing = next(g for g in tuho_vm.groups if g.code == _FINANCING_CODE)
        contingency = next(g for g in tuho_vm.groups if g.code == _CONTINGENCY_CODE)
        min_derived = financing.subtotal_keur + contingency.subtotal_keur
        assert tuho_vm.derived_total_keur >= min_derived - 1e-6


# ---------------------------------------------------------------------------
# Zero capacity edge case
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_zero_capacity_no_raise(self):
        ctx = get_project_context("tuho")
        patched = dataclasses.replace(ctx, capacity_mw=0.0)
        vm = build_capex_view_model(patched)
        assert vm.total_per_mw == 0.0
        for g in vm.groups:
            assert g.subtotal_per_mw == 0.0


# ---------------------------------------------------------------------------
# Mutation command dataclasses
# ---------------------------------------------------------------------------

class TestMutationCommands:
    def test_add_command_instantiates(self):
        cmd = AddCapexLineCommand(
            project_code="tuho",
            parent_group_code="C.05",
            name="Custom Equipment",
            amount_keur=150.0,
        )
        assert cmd.parent_group_code == "C.05"
        assert cmd.amount_keur == 150.0

    def test_update_command_instantiates(self):
        cmd = UpdateCapexLineCommand(
            project_code="tuho",
            line_code="C.05.01",
            new_amount_keur=200.0,
        )
        assert cmd.new_amount_keur == 200.0

    def test_deactivate_command_instantiates(self):
        cmd = DeactivateCapexLineCommand(
            project_code="tuho",
            line_code="C.05.01",
        )
        assert cmd.line_code == "C.05.01"

    def test_commands_are_frozen(self):
        cmd = AddCapexLineCommand(
            project_code="tuho",
            parent_group_code="C.05",
            name="Test",
            amount_keur=100.0,
        )
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            cmd.amount_keur = 999.0  # type: ignore
