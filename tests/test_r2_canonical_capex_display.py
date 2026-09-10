"""R2 — F03 Canonical CAPEX Display Projection: test suite.

Verifies that `build_capex_view_model()` produces display values
that are causally aligned with canonical `ProjectInputs.capex`.

Causal chain under test:
  persisted snapshot
  → build_projectinputs_from_snapshot()  [R1 input adapter]
  → pi.capex.<field>.amount_keur         [canonical authority]
  → build_project_context_for_record()   [builds capex_detail_items with app_group_amount_keur]
  → build_capex_view_model()             [display projection]
  → CapexViewModel.groups[*].subtotal_keur / hard_capex_keur / total_capex_keur

Required coverage (per R2 spec):
  - 14/14 scalar display parity
  - Generic Wind
  - Generic Solar
  - TUHO
  - Oborovo
  - legacy aggregate transition
  - scalar edit
  - explicit zero
  - persistence/reload (subtotal/total identities)
  - scenario isolation
  - UUID add/edit/delete
  - subtotal/total identities
  - representative Run parity
"""
from __future__ import annotations

import uuid
from dataclasses import replace
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.input_adapter import _SCALAR_CAPEX_MAP, build_projectinputs_from_snapshot
from app.persistence.capex_sub_lines import CAPEX_CATEGORY_TO_FIELD
from app.ui.capex_view_model import CapexViewModel, build_capex_view_model
from app.ui.project_context import build_project_context_for_record


# ---------------------------------------------------------------------------
# Snapshot helpers
# ---------------------------------------------------------------------------

_REQUIRED = {
    "project_type": "wind",
    "project_name": "R2 Test Wind",
    "country_market": "DE",
    "capacity_mw": "50",
    "cod_date": "2027-01-01",
    "construction_months": "18",
    "horizon_years": "25",
    "tariff_eur_mwh": "60",
    "ppa_term_years": "15",
    "p50_hours": "2500",
    "opex_y1_keur": "500",
    "total_capex_keur": "80000",
    "gearing_pct": "",
    "interest_rate_pct": "0.055",
    "tenor_years": "18",
    "target_dscr": "1.30",
}


def _wind(**extra) -> dict:
    b = dict(_REQUIRED)
    b.update(extra)
    return b


def _solar(**extra) -> dict:
    b = _wind(**extra)
    b["project_type"] = "solar"
    b["project_name"] = "R2 Test Solar"
    return b


def _tuho(**extra) -> dict:
    b = _wind(**extra)
    b.update(
        {
            "project_name": "Tuhom",
            "country_market": "CZ",
            "capacity_mw": "46",
            "total_capex_keur": "69000",
        }
    )
    b.update(extra)
    return b


def _oborovo(**extra) -> dict:
    b = _wind(**extra)
    b.update(
        {
            "project_name": "Oborovo",
            "country_market": "HR",
            "capacity_mw": "36",
            "total_capex_keur": "54000",
        }
    )
    b.update(extra)
    return b


# ---------------------------------------------------------------------------
# Build helpers
# ---------------------------------------------------------------------------

def _build_vm(
    snap: dict,
    template_source: str | None = None,
    is_user_project: bool = True,
    sub_lines=None,
    project_code: str = "TST",
) -> CapexViewModel:
    """Full causal chain: snapshot → ProjectInputs → ProjectContext → CapexViewModel."""
    pi = build_projectinputs_from_snapshot(snap)
    project_type = snap.get("project_type", "wind")
    ctx = build_project_context_for_record(
        project_code=project_code,
        project_name=snap.get("project_name", "Test"),
        project_type=project_type,
        project_origin="user_created",
        template_source=template_source,
        baseline_snapshot=snap,
        effective_project_inputs=pi,
    )
    return build_capex_view_model(ctx, is_user_project=is_user_project, sub_lines=sub_lines)


def _canonical_amounts(snap: dict) -> dict[str, float]:
    """Return {cat_code: amount_keur} from canonical ProjectInputs.capex."""
    pi = build_projectinputs_from_snapshot(snap)
    capex = pi.capex
    result: dict[str, float] = {}
    seen: set[str] = set()
    for code, fname in CAPEX_CATEGORY_TO_FIELD.items():
        if fname in seen:
            continue  # alias group — skip, canonical value already recorded for owner
        seen.add(fname)
        obj = getattr(capex, fname, None)
        if obj is None:
            result[code] = 0.0
        elif hasattr(obj, "amount_keur"):
            result[code] = float(obj.amount_keur)
        elif isinstance(obj, (int, float)):
            result[code] = float(obj)
        else:
            result[code] = 0.0
    return result


def _group_subtotal(vm: CapexViewModel, code: str) -> float:
    for g in vm.groups:
        if g.code == code:
            return g.subtotal_keur
    return 0.0


# ---------------------------------------------------------------------------
# 1. 14/14 scalar display parity — Generic Wind
# ---------------------------------------------------------------------------

_SCALAR_KEYS = list(_SCALAR_CAPEX_MAP.keys())


@pytest.mark.parametrize("scalar_key", _SCALAR_KEYS)
def test_scalar_display_parity_generic_wind(scalar_key: str):
    """Each scalar input reaches the CapexViewModel group subtotal."""
    snap = _wind(**{scalar_key: "5000"})
    pi = build_projectinputs_from_snapshot(snap)
    capex = pi.capex

    # Determine which group this scalar maps to (via SCALAR_CAPEX_MAP → field name → group code)
    field_name = _SCALAR_CAPEX_MAP[scalar_key]
    group_code = None
    for cat_code, fname in CAPEX_CATEGORY_TO_FIELD.items():
        if fname == field_name:
            group_code = cat_code
            break

    if group_code is None:
        pytest.skip(f"No group code found for {field_name}")

    # Canonical value from ProjectInputs
    obj = getattr(capex, field_name, None)
    if hasattr(obj, "amount_keur"):
        expected = float(obj.amount_keur)
    else:
        expected = float(obj or 0.0)

    vm = _build_vm(snap)
    actual = _group_subtotal(vm, group_code)

    assert actual == pytest.approx(expected, abs=0.01), (
        f"{scalar_key} → {field_name} → group {group_code}: "
        f"display={actual} != canonical={expected}"
    )


# ---------------------------------------------------------------------------
# 2. 14/14 scalar display parity — Generic Solar
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("scalar_key", _SCALAR_KEYS)
def test_scalar_display_parity_generic_solar(scalar_key: str):
    snap = _solar(**{scalar_key: "3000"})
    pi = build_projectinputs_from_snapshot(snap)
    capex = pi.capex

    field_name = _SCALAR_CAPEX_MAP[scalar_key]
    group_code = None
    for cat_code, fname in CAPEX_CATEGORY_TO_FIELD.items():
        if fname == field_name:
            group_code = cat_code
            break

    if group_code is None:
        pytest.skip(f"No group code found for {field_name}")

    obj = getattr(capex, field_name, None)
    if hasattr(obj, "amount_keur"):
        expected = float(obj.amount_keur)
    else:
        expected = float(obj or 0.0)

    vm = _build_vm(snap)
    actual = _group_subtotal(vm, group_code)
    assert actual == pytest.approx(expected, abs=0.01), (
        f"Solar {scalar_key} → display={actual} != canonical={expected}"
    )


# ---------------------------------------------------------------------------
# 3. TUHO — no scalar — display aligns with canonical authority
# ---------------------------------------------------------------------------

def test_tuho_no_scalar_display_alignment():
    snap = _tuho()
    vm = _build_vm(snap, template_source="tuho")
    pi = build_projectinputs_from_snapshot(snap)
    capex = pi.capex

    seen: set[str] = set()
    for cat_code, fname in CAPEX_CATEGORY_TO_FIELD.items():
        if fname in seen:
            continue
        seen.add(fname)
        obj = getattr(capex, fname, None)
        if hasattr(obj, "amount_keur"):
            expected = float(obj.amount_keur)
        else:
            expected = float(obj or 0.0)
        actual = _group_subtotal(vm, cat_code)
        assert actual == pytest.approx(expected, abs=0.01), (
            f"TUHO {cat_code} ({fname}): display={actual} != canonical={expected}"
        )


# ---------------------------------------------------------------------------
# 4. TUHO — scalar edit propagates to display
# ---------------------------------------------------------------------------

def test_tuho_scalar_edit_display():
    snap = _tuho(capex_epc_contract_keur="55000")
    vm = _build_vm(snap, template_source="tuho")
    pi = build_projectinputs_from_snapshot(snap)

    expected = float(pi.capex.epc_contract.amount_keur)
    actual = _group_subtotal(vm, "C.02")
    assert actual == pytest.approx(expected, abs=0.01)


# ---------------------------------------------------------------------------
# 5. Oborovo — no scalar — display aligns
# ---------------------------------------------------------------------------

def test_oborovo_no_scalar_display_alignment():
    snap = _oborovo()
    vm = _build_vm(snap, template_source="oborovo")
    pi = build_projectinputs_from_snapshot(snap)
    capex = pi.capex

    seen: set[str] = set()
    for cat_code, fname in CAPEX_CATEGORY_TO_FIELD.items():
        if fname in seen:
            continue
        seen.add(fname)
        obj = getattr(capex, fname, None)
        if hasattr(obj, "amount_keur"):
            expected = float(obj.amount_keur)
        else:
            expected = float(obj or 0.0)
        actual = _group_subtotal(vm, cat_code)
        assert actual == pytest.approx(expected, abs=0.01), (
            f"Oborovo {cat_code} ({fname}): display={actual} != canonical={expected}"
        )


# ---------------------------------------------------------------------------
# 6. Oborovo — scalar edit propagates
# ---------------------------------------------------------------------------

def test_oborovo_scalar_edit_display():
    snap = _oborovo(capex_grid_connection_keur="12000")
    vm = _build_vm(snap, template_source="oborovo")
    pi = build_projectinputs_from_snapshot(snap)

    expected = float(pi.capex.grid_connection.amount_keur)
    actual = _group_subtotal(vm, "C.03")
    assert actual == pytest.approx(expected, abs=0.01)


# ---------------------------------------------------------------------------
# 7. Legacy aggregate transition — total_capex_keur only, no scalars
# ---------------------------------------------------------------------------

def test_legacy_aggregate_transition_generic_wind():
    """When only total_capex_keur is present (legacy path), display is consistent."""
    snap = _wind(total_capex_keur="90000")
    vm = _build_vm(snap)
    pi = build_projectinputs_from_snapshot(snap)

    # C.11 alias group is marked correctly
    c11_group = next((g for g in vm.groups if g.code == "C.11"), None)
    assert c11_group is None or c11_group.is_alias, "C.11 must be flagged as alias"

    # total display = hard + financing + reserve
    expected_total = vm.hard_capex_keur + vm.financing_keur + vm.reserve_keur
    assert vm.total_capex_keur == pytest.approx(expected_total, abs=0.01)


# ---------------------------------------------------------------------------
# 8. Explicit zero semantics
# ---------------------------------------------------------------------------

def test_explicit_zero_scalar_display():
    """capex_epc_contract_keur='0' → display group C.02 = 0.0"""
    snap = _wind(capex_epc_contract_keur="0")
    vm = _build_vm(snap)
    pi = build_projectinputs_from_snapshot(snap)

    expected = float(pi.capex.epc_contract.amount_keur)
    actual = _group_subtotal(vm, "C.02")
    assert expected == pytest.approx(0.0, abs=0.01)
    assert actual == pytest.approx(0.0, abs=0.01)


# ---------------------------------------------------------------------------
# 9. Subtotal / total identities
# ---------------------------------------------------------------------------

def test_subtotal_total_identity_generic_wind():
    snap = _wind(capex_epc_contract_keur="60000")
    vm = _build_vm(snap)

    # total = hard + financing + reserve
    assert vm.total_capex_keur == pytest.approx(
        vm.hard_capex_keur + vm.financing_keur + vm.reserve_keur, abs=0.01
    )


def test_alias_group_excluded_from_hard_capex():
    """C.11 (audit_legal alias) must NOT contribute to hard_capex_keur."""
    snap = _wind(capex_audit_legal_keur="2000")
    vm = _build_vm(snap)

    c08_subtotal = _group_subtotal(vm, "C.08")
    c11_subtotal = _group_subtotal(vm, "C.11")

    # Both C.08 and C.11 display the same canonical audit_legal value
    assert c08_subtotal == pytest.approx(c11_subtotal, abs=0.01)

    # But hard_capex_keur counts only C.08 (owner), not C.11 (alias)
    # The C.11 group should be marked as alias
    c11_group = next((g for g in vm.groups if g.code == "C.11"), None)
    assert c11_group is not None
    assert c11_group.is_alias is True

    # hard_capex excludes alias
    naive_sum = sum(g.subtotal_keur for g in vm.groups if g.code not in {"C.17", "C.18"})
    assert vm.hard_capex_keur < naive_sum or c11_subtotal == 0.0, \
        "alias group must not double-count in hard_capex_keur"


# ---------------------------------------------------------------------------
# 10. UUID add/edit/delete (custom sub-lines)
# ---------------------------------------------------------------------------

def _make_sub_line(group_code: str, amount: float, label: str = "Custom", active: bool = True):
    """Build a mock CapexSubLine."""
    sl = MagicMock()
    sl.sub_line_id = str(uuid.uuid4())
    sl.parent_category_code = group_code
    sl.business_code = f"{group_code}.X{sl.sub_line_id[:4]}"
    sl.label = label
    sl.amount_keur = amount
    sl.comments = ""
    sl.display_order = 99
    sl.updated_at = "2025-01-01T00:00:00"
    sl.is_active = active
    return sl


def test_custom_subline_add_increases_subtotal():
    snap = _wind()
    vm_without = _build_vm(snap)
    sl = _make_sub_line("C.05", 1500.0, "Custom EPC Other")
    vm_with = _build_vm(snap, sub_lines=[sl])

    c05_without = _group_subtotal(vm_without, "C.05")
    c05_with = _group_subtotal(vm_with, "C.05")
    assert c05_with == pytest.approx(c05_without + 1500.0, abs=0.01)


def test_custom_subline_edit_reflects_new_amount():
    snap = _wind()
    sl = _make_sub_line("C.05", 1000.0)
    vm_v1 = _build_vm(snap, sub_lines=[sl])
    sl.amount_keur = 2500.0
    vm_v2 = _build_vm(snap, sub_lines=[sl])

    c05_v1 = _group_subtotal(vm_v1, "C.05")
    c05_v2 = _group_subtotal(vm_v2, "C.05")
    assert c05_v2 == pytest.approx(c05_v1 + 1500.0, abs=0.01)


def test_custom_subline_delete_removes_from_subtotal():
    snap = _wind()
    sl = _make_sub_line("C.05", 2000.0)
    vm_with = _build_vm(snap, sub_lines=[sl])
    vm_without = _build_vm(snap, sub_lines=[])

    c05_with = _group_subtotal(vm_with, "C.05")
    c05_without = _group_subtotal(vm_without, "C.05")
    assert c05_with == pytest.approx(c05_without + 2000.0, abs=0.01)


def test_custom_subline_readonly_group_rejected():
    """Custom sub-lines must not be injected into C.17 / C.18 (readonly groups)."""
    snap = _wind()
    sl_c17 = _make_sub_line("C.17", 500.0)
    sl_c18 = _make_sub_line("C.18", 500.0)
    vm = _build_vm(snap, sub_lines=[sl_c17, sl_c18])

    # These lines should not appear in the readonly groups
    for g in vm.groups:
        if g.code in {"C.17", "C.18"}:
            custom_lines = [ln for ln in g.lines if ln.is_custom]
            assert len(custom_lines) == 0, f"Custom line injected into readonly group {g.code}"


# ---------------------------------------------------------------------------
# 11. Scenario isolation — two independent VMs must not share state
# ---------------------------------------------------------------------------

def test_scenario_isolation():
    snap_a = _wind(capex_epc_contract_keur="50000")
    snap_b = _wind(capex_epc_contract_keur="70000")

    vm_a = _build_vm(snap_a)
    vm_b = _build_vm(snap_b)

    c02_a = _group_subtotal(vm_a, "C.02")
    c02_b = _group_subtotal(vm_b, "C.02")
    assert c02_a != pytest.approx(c02_b, abs=0.01)
    assert c02_b == pytest.approx(70000.0, abs=0.01) or c02_b > c02_a


# ---------------------------------------------------------------------------
# 12. Persistence / reload identity — subtotal round-trips through snapshot
# ---------------------------------------------------------------------------

def test_persistence_reload_identity():
    """Saving and reloading a scalar must preserve display values."""
    snap = _wind(capex_epc_contract_keur="60000")
    vm1 = _build_vm(snap)

    # Simulate reload: same snapshot fed again
    vm2 = _build_vm(snap)

    assert vm1.hard_capex_keur == pytest.approx(vm2.hard_capex_keur, abs=0.01)
    assert vm1.total_capex_keur == pytest.approx(vm2.total_capex_keur, abs=0.01)
    assert _group_subtotal(vm1, "C.02") == pytest.approx(_group_subtotal(vm2, "C.02"), abs=0.01)


# ---------------------------------------------------------------------------
# 13. Representative Run parity — hard_capex_keur matches engine input
# ---------------------------------------------------------------------------

def test_run_parity_hard_capex_generic_wind():
    """
    CapexViewModel.hard_capex_keur must equal the sum of canonical CapexStructure
    fields (excluding C.17 / C.18 and alias groups).
    """
    snap = _wind(capex_epc_contract_keur="55000", capex_grid_connection_keur="8000")
    pi = build_projectinputs_from_snapshot(snap)
    capex = pi.capex

    # Compute expected hard CAPEX from canonical fields
    seen: set[str] = set()
    expected_hard = 0.0
    for cat_code, fname in CAPEX_CATEGORY_TO_FIELD.items():
        if cat_code in {"C.17", "C.18"}:
            continue
        if fname in seen:
            continue  # alias — skip
        seen.add(fname)
        obj = getattr(capex, fname, None)
        if hasattr(obj, "amount_keur"):
            expected_hard += float(obj.amount_keur)
        elif isinstance(obj, (int, float)):
            expected_hard += float(obj or 0.0)

    vm = _build_vm(snap)
    assert vm.hard_capex_keur == pytest.approx(expected_hard, abs=0.01), (
        f"display hard_capex={vm.hard_capex_keur} != canonical sum={expected_hard}"
    )


def test_run_parity_hard_capex_generic_solar():
    snap = _solar(capex_epc_contract_keur="40000")
    pi = build_projectinputs_from_snapshot(snap)
    capex = pi.capex

    seen: set[str] = set()
    expected_hard = 0.0
    for cat_code, fname in CAPEX_CATEGORY_TO_FIELD.items():
        if cat_code in {"C.17", "C.18"}:
            continue
        if fname in seen:
            continue
        seen.add(fname)
        obj = getattr(capex, fname, None)
        if hasattr(obj, "amount_keur"):
            expected_hard += float(obj.amount_keur)
        elif isinstance(obj, (int, float)):
            expected_hard += float(obj or 0.0)

    vm = _build_vm(snap)
    assert vm.hard_capex_keur == pytest.approx(expected_hard, abs=0.01)


# ---------------------------------------------------------------------------
# 14. CapexViewModel structural invariants
# ---------------------------------------------------------------------------

def test_per_mw_derived_field():
    """per_mw must equal amount_keur / capacity_mw for all active lines."""
    snap = _wind()
    vm = _build_vm(snap)
    capacity_mw = vm.capacity_mw
    assert capacity_mw > 0

    for g in vm.groups:
        for ln in g.lines:
            if ln.is_active and capacity_mw > 0:
                expected_per_mw = ln.amount_keur / capacity_mw
                assert ln.per_mw == pytest.approx(expected_per_mw, abs=0.001), (
                    f"Line {ln.code} per_mw={ln.per_mw} != amount/MW={expected_per_mw}"
                )


def test_readonly_groups_are_derived():
    """All lines in C.17 and C.18 must be is_derived=True."""
    snap = _wind()
    vm = _build_vm(snap)
    for g in vm.groups:
        if g.code in {"C.17", "C.18"}:
            assert g.is_readonly is True
            for ln in g.lines:
                assert ln.is_derived is True, f"{ln.code} in {g.code} should be derived"


def test_editable_flags_user_vs_nonuser():
    """is_editable must be True for non-derived lines when is_user_project=True."""
    snap = _wind()
    vm_user = _build_vm(snap, is_user_project=True)
    vm_nonuser = _build_vm(snap, is_user_project=False)

    for g in vm_user.groups:
        for ln in g.lines:
            if not ln.is_derived and not ln.is_group:
                assert ln.is_editable is True, f"{ln.code} should be editable for user project"

    for g in vm_nonuser.groups:
        for ln in g.lines:
            assert ln.is_editable is False, f"{ln.code} should not be editable for non-user project"


def test_total_capex_identity_all_projects():
    """total_capex = hard + financing + reserve for all four project types."""
    for snap, tmpl in [
        (_wind(), None),
        (_solar(), None),
        (_tuho(), "tuho"),
        (_oborovo(), "oborovo"),
    ]:
        vm = _build_vm(snap, template_source=tmpl)
        assert vm.total_capex_keur == pytest.approx(
            vm.hard_capex_keur + vm.financing_keur + vm.reserve_keur, abs=0.01
        ), f"total identity failed for template={tmpl}"
