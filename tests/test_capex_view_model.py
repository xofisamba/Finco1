"""
Tests for CapexViewModel builder.

Uses the live TUHO and Oborovo project contexts (same as production data).
Tests structural correctness, editability contract, and derived totals.
Does NOT test equality with project_ctx.total_capex_keur because that field
is derived from the engine separately from capex_detail_items.
"""

import pytest

from app.ui.project_context import get_project_context
from app.ui.capex_view_model import (
    CapexGroupVM,
    CapexLineVM,
    CapexViewModel,
    build_capex_view_model,
    _READONLY_GROUP_CODES,
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


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

class TestCapexViewModelStructure:
    def test_returns_capex_view_model(self, tuho_vm):
        assert isinstance(tuho_vm, CapexViewModel)

    def test_eighteen_groups(self, tuho_vm):
        assert len(tuho_vm.groups) == 18

    def test_group_codes_c01_to_c18(self, tuho_vm):
        codes = [g.code for g in tuho_vm.groups]
        assert codes[0] == "C.01"
        assert codes[-1] == "C.18"
        assert "C.17" in codes
        assert "C.18" in codes

    def test_all_groups_are_capex_group_vm(self, tuho_vm):
        for g in tuho_vm.groups:
            assert isinstance(g, CapexGroupVM)

    def test_all_lines_are_capex_line_vm(self, tuho_vm):
        for g in tuho_vm.groups:
            for ln in g.lines:
                assert isinstance(ln, CapexLineVM)

    def test_lines_have_correct_parent_code(self, tuho_vm):
        for g in tuho_vm.groups:
            for ln in g.lines:
                assert ln.parent_code == g.code

    def test_project_name_populated(self, tuho_vm, tuho_ctx):
        assert tuho_vm.project_name == tuho_ctx.name

    def test_capacity_mw_populated(self, tuho_vm, tuho_ctx):
        assert tuho_vm.capacity_mw == tuho_ctx.capacity_mw

    def test_oborovo_eighteen_groups(self, oborovo_vm):
        assert len(oborovo_vm.groups) == 18


# ---------------------------------------------------------------------------
# Readonly contract — C.17 and C.18
# ---------------------------------------------------------------------------

class TestReadonlyContract:
    def test_c17_group_is_readonly(self, tuho_vm):
        c17 = next(g for g in tuho_vm.groups if g.code == "C.17")
        assert c17.is_readonly is True

    def test_c18_group_is_readonly(self, tuho_vm):
        c18 = next(g for g in tuho_vm.groups if g.code == "C.18")
        assert c18.is_readonly is True

    def test_c01_not_readonly(self, tuho_vm):
        c01 = next(g for g in tuho_vm.groups if g.code == "C.01")
        assert c01.is_readonly is False

    def test_c17_lines_all_readonly_financing(self, tuho_vm):
        c17 = next(g for g in tuho_vm.groups if g.code == "C.17")
        for ln in c17.lines:
            assert ln.is_readonly_financing is True

    def test_c18_lines_all_readonly_financing(self, tuho_vm):
        c18 = next(g for g in tuho_vm.groups if g.code == "C.18")
        for ln in c18.lines:
            assert ln.is_readonly_financing is True

    def test_c01_lines_not_readonly_financing(self, tuho_vm):
        c01 = next(g for g in tuho_vm.groups if g.code == "C.01")
        assert all(not ln.is_readonly_financing for ln in c01.lines)


# ---------------------------------------------------------------------------
# Editability — user vs non-user project
# ---------------------------------------------------------------------------

class TestEditabilityContract:
    def test_non_user_project_no_lines_editable(self, tuho_vm):
        all_lines = [ln for g in tuho_vm.groups for ln in g.lines]
        assert not any(ln.is_editable for ln in all_lines)

    def test_user_project_editable_lines_exist(self, tuho_vm_user):
        all_lines = [ln for g in tuho_vm_user.groups for ln in g.lines]
        assert any(ln.is_editable for ln in all_lines)

    def test_user_project_c17_lines_never_editable(self, tuho_vm_user):
        c17 = next(g for g in tuho_vm_user.groups if g.code == "C.17")
        assert not any(ln.is_editable for ln in c17.lines)

    def test_user_project_c18_lines_never_editable(self, tuho_vm_user):
        c18 = next(g for g in tuho_vm_user.groups if g.code == "C.18")
        assert not any(ln.is_editable for ln in c18.lines)

    def test_is_group_false_for_all_lines(self, tuho_vm):
        for g in tuho_vm.groups:
            for ln in g.lines:
                assert ln.is_group is False

    def test_custom_and_active_defaults(self, tuho_vm):
        """Future fields: is_custom=False, is_active=True for all template lines."""
        for g in tuho_vm.groups:
            for ln in g.lines:
                assert ln.is_custom is False
                assert ln.is_active is True


# ---------------------------------------------------------------------------
# Derived fields — per_mw and totals
# ---------------------------------------------------------------------------

class TestDerivedFields:
    def test_per_mw_equals_amount_divided_by_capacity(self, tuho_vm, tuho_ctx):
        capacity = tuho_ctx.capacity_mw
        for g in tuho_vm.groups:
            for ln in g.lines:
                expected = ln.amount_keur / capacity if capacity > 0 else 0.0
                assert abs(ln.per_mw - expected) < 1e-6

    def test_group_subtotal_equals_sum_of_active_lines(self, tuho_vm):
        for g in tuho_vm.groups:
            active = [ln for ln in g.lines if ln.is_active]
            expected = sum(ln.amount_keur for ln in active)
            assert abs(g.subtotal_keur - expected) < 1e-6

    def test_group_subtotal_per_mw_consistent(self, tuho_vm, tuho_ctx):
        capacity = tuho_ctx.capacity_mw
        for g in tuho_vm.groups:
            expected = g.subtotal_keur / capacity if capacity > 0 else 0.0
            assert abs(g.subtotal_per_mw - expected) < 1e-6

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
        c17 = next(g for g in tuho_vm.groups if g.code == "C.17")
        assert abs(tuho_vm.financing_keur - c17.subtotal_keur) < 1e-6

    def test_c18_reserve_keur_is_c18_subtotal(self, tuho_vm):
        c18 = next(g for g in tuho_vm.groups if g.code == "C.18")
        assert abs(tuho_vm.reserve_keur - c18.subtotal_keur) < 1e-6

    def test_hard_capex_per_mw_consistent(self, tuho_vm, tuho_ctx):
        expected = tuho_vm.hard_capex_keur / tuho_ctx.capacity_mw
        assert abs(tuho_vm.hard_capex_per_mw - expected) < 1e-6

    def test_c01_has_nonzero_subtotal(self, tuho_vm):
        # TUHO C.01 = wind turbines, ~35,000 kEUR
        c01 = next(g for g in tuho_vm.groups if g.code == "C.01")
        assert c01.subtotal_keur > 0

    def test_oborovo_total_capex_positive(self, oborovo_vm):
        assert oborovo_vm.total_capex_keur > 0

    def test_is_user_project_flag_propagates(self, tuho_vm, tuho_vm_user):
        assert tuho_vm.is_user_project is False
        assert tuho_vm_user.is_user_project is True

    def test_zero_capacity_does_not_raise(self):
        """per_mw should be 0.0 when capacity_mw == 0, not a ZeroDivisionError."""
        ctx = get_project_context("tuho")
        # Patch capacity via object.__setattr__ since frozen dataclass
        import dataclasses
        patched = dataclasses.replace(ctx, capacity_mw=0.0)
        vm = build_capex_view_model(patched)
        assert vm.total_per_mw == 0.0
        for g in vm.groups:
            assert g.subtotal_per_mw == 0.0
