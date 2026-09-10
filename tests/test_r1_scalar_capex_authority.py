"""R1 Correction C — Scalar CAPEX Authority: seeded-legacy-total baseline + causal closure.

Authority order (Correction C — complete):
  factory/template
  → legacy aggregate normalization (total_capex_keur ≠ factory → _zero_financial + _apply_capex_total)
  → scalar user inputs (individual line amounts)
  → UUID replacement sub-lines
  → derived contingency
  → engine IDC / template-locked financing
  → derived reserves

Key invariants:
  1. epc_contract is NOT used as a balancing plug after a scalar edit.
  2. For seeded projects (TUHO/Oborovo) whose persisted total_capex_keur differs
     materially from the calibrated factory total, the pre-edit effective CAPEX state
     is reconstructed before applying the scalar (Correction C).  Untouched lines
     never silently revert toward the pristine seeded factory.

Full causal test suite:

1.  All 14 scalar keys individually reach ProjectInputs.capex.<field>.amount_keur (F02 defect)
2.  Scalar CAPEX edit increases total by exact delta — epc NOT moved as plug
3.  Scalar CAPEX edit decreases total by exact delta (inverse)
4.  Multiple scalar edits: net total delta equals sum of per-line deltas
5.  When capex_epc_contract_keur is explicitly set, it takes authority; total unchanged
6.  Legacy-only total_capex_keur path (no scalars) unchanged (backwards compat)
7.  TUHO: no scalar edit — CAPEX structure and financing authority preserved
8.  TUHO: scalar equal to effective value — no economic change, no financing reset
9.  TUHO: material scalar CAPEX change — edited field changes by exact delta; others unchanged
10. Oborovo: same three scenarios as TUHO
11. Explicit zero semantics (capex_epc_contract_keur='0' → 0.0)
12. Empty-string scalar treated as absent
13. V2 WorkbookService path: draft and saved
14. V2 partial scalar + total: total reflects correct delta
15. Atomic persistence round-trip: save → reload → WorkbookService → to_projectinputs()
16. Scenario isolation: CAPEX scalar via ScenarioManager multiplier
17. Engine fingerprint (Generic Wind): scalar mutation → hard_project_capex_keur changes
18. Engine fingerprint (Generic Solar): scalar mutation → hard_project_capex_keur changes
19. UUID sub-line interaction — no double counting
20. Scalar map completeness: 14 entries, all valid CapexStructure fields
21. Registry completeness: all 14 keys in WORKBOOK bound fields
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import pytest

from app.input_adapter import (
    _SCALAR_CAPEX_MAP,
    build_projectinputs_from_snapshot,
)


# ── shared snapshot helpers ────────────────────────────────────────────────────

_REQUIRED_FIELDS = {
    "project_type": "wind",
    "project_name": "Test Wind",
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


def _base_wind(**extra) -> dict:
    """Minimal valid Generic Wind user-project snapshot."""
    base = dict(_REQUIRED_FIELDS)
    base.update(extra)
    return base


def _base_solar(**extra) -> dict:
    """Minimal valid Generic Solar user-project snapshot."""
    base = _base_wind(**extra)
    base["project_type"] = "solar"
    base["project_name"] = "Test Solar"
    return base


def _tuho_snap(**extra) -> dict:
    """Minimal snapshot for a TUHO-template working copy."""
    base = _base_wind(**extra)
    base.update({
        "project_type": "wind",
        "template_source": "tuho",
        "active_project": "tuho-test-copy",
        "project_origin": "user_created",
        "project_name": "TUHO Copy",
        "country_market": "HR",
    })
    return base


def _oborovo_snap(**extra) -> dict:
    """Minimal snapshot for an Oborovo-template working copy."""
    base = _base_wind(**extra)
    base.update({
        "project_type": "solar",
        "template_source": "oborovo",
        "active_project": "obo-test-copy",
        "project_origin": "user_created",
        "project_name": "Oborovo Copy",
        "country_market": "HR",
    })
    return base


def _get(pi, field_name: str) -> float:
    """Return amount_keur for a named CapexItem field."""
    return getattr(pi.capex, field_name).amount_keur


def _make_ws(snapshot: dict) -> Any:
    """Create a WorkspaceStateRecord for V2 path testing."""
    from app.persistence.records import WorkspaceStateRecord
    now = datetime(2026, 9, 10, 12, 0, 0)
    return WorkspaceStateRecord(
        workspace_id="ws-test",
        project_id="proj-test",
        user_id="user-test",
        project_code="test-proj",
        active_scenario_id=None,
        active_scenario_name=None,
        draft_snapshot=snapshot,
        saved_snapshot=snapshot,
        last_runtime_snapshot={},
        last_runtime_summary={},
        last_runtime_snapshot_id=None,
        last_runtime_origin=None,
        last_runtime_scenario_id=None,
        last_financial_statements={},
        last_debt_schedule={},
        last_tax_schedule={},
        last_distribution_schedule={},
        last_sponsor_schedule={},
        dirty=False,
        governance_state={},
        replay_metadata={},
        created_at=now,
        updated_at=now,
        last_runtime_at=None,
    )


# ── 1. F02 causal coverage: all 14 scalar keys reach ProjectInputs ────────────

@pytest.mark.parametrize("snap_key,field_name", list(_SCALAR_CAPEX_MAP.items()))
def test_scalar_key_reaches_projectinputs_wind(snap_key: str, field_name: str):
    """Each of the 14 scalar keys flows through to capex.<field>.amount_keur (Generic Wind)."""
    injected = 1234.56
    pi = build_projectinputs_from_snapshot(_base_wind(**{snap_key: str(injected)}))
    assert _get(pi, field_name) == pytest.approx(injected, rel=1e-6), (
        f"F02 Wind: '{snap_key}' did not reach capex.{field_name}.amount_keur"
    )


@pytest.mark.parametrize("snap_key,field_name", list(_SCALAR_CAPEX_MAP.items()))
def test_scalar_key_reaches_projectinputs_solar(snap_key: str, field_name: str):
    """Each of the 14 scalar keys flows through to capex.<field>.amount_keur (Generic Solar)."""
    injected = 987.65
    pi = build_projectinputs_from_snapshot(_base_solar(**{snap_key: str(injected)}))
    assert _get(pi, field_name) == pytest.approx(injected, rel=1e-6), (
        f"F02 Solar: '{snap_key}' did not reach capex.{field_name}.amount_keur"
    )


# ── 2–4. Correct authority order: scalar edit changes total, NOT epc as plug ──
#
# Generic Wind factory CAPEX (from create_default_wind_project()):
#   epc_contract=30000, epc_other=6000, grid_connection=3000, audit_legal=4000
#   total=43000
#
# After legacy normalization with total_capex_keur=80000
# (_apply_capex_total sets epc = 80000 − 13000 = 67000):
#   epc_contract=67000, epc_other=6000, grid_connection=3000, audit_legal=4000
#   total=80000
#
# A scalar edit on grid_connection: 3000 → 5000 (delta +2000):
#   epc stays at 67000 (not used as plug), total = 82000


def test_scalar_grid_increase_raises_total_not_epc():
    """Scalar grid +2000 → total increases by 2000; epc_contract does not move.

    Correction B P1: the pre-edit effective baseline is established first via
    _apply_capex_total(80000), giving epc=67000. Then the scalar overwrites
    grid=5000. The total becomes 82000 (+2000 delta). epc remains at 67000.
    """
    snap = _base_wind(total_capex_keur="80000", capex_grid_connection_keur="5000")
    pi = build_projectinputs_from_snapshot(snap)

    assert _get(pi, "grid_connection") == pytest.approx(5000.0), "grid_connection not set"
    assert _get(pi, "epc_contract") == pytest.approx(67000.0, rel=1e-5), (
        "epc_contract must NOT move as a balancing plug after a scalar edit"
    )
    assert pi.capex.total_capex == pytest.approx(82000.0, rel=1e-4), (
        "total must increase by exactly the scalar delta (+2000)"
    )


def test_scalar_grid_decrease_lowers_total_not_epc():
    """Scalar grid −2000 (3000 → 1000) → total decreases by 2000; epc unchanged.

    Pre-edit effective baseline: epc=67000, grid=3000.
    Scalar: grid=1000 (delta −2000). Expected total=78000.
    """
    snap = _base_wind(total_capex_keur="80000", capex_grid_connection_keur="1000")
    pi = build_projectinputs_from_snapshot(snap)

    assert _get(pi, "grid_connection") == pytest.approx(1000.0)
    assert _get(pi, "epc_contract") == pytest.approx(67000.0, rel=1e-5), (
        "epc_contract must NOT compensate for the grid reduction"
    )
    assert pi.capex.total_capex == pytest.approx(78000.0, rel=1e-4), (
        "total must decrease by exactly the scalar delta (−2000)"
    )


def test_multiple_scalar_edits_net_delta():
    """Multiple scalar edits: net total delta = sum of per-line deltas.

    Pre-edit baseline (total=80000): epc=67000, grid=3000, audit=4000.
    Edits: grid 3000→5000 (+2000), audit 4000→6000 (+2000). Net delta=+4000.
    Expected total=84000. epc must remain at 67000.
    """
    snap = _base_wind(
        total_capex_keur="80000",
        capex_grid_connection_keur="5000",
        capex_audit_legal_keur="6000",
    )
    pi = build_projectinputs_from_snapshot(snap)

    assert _get(pi, "grid_connection") == pytest.approx(5000.0)
    assert _get(pi, "audit_legal") == pytest.approx(6000.0)
    assert _get(pi, "epc_contract") == pytest.approx(67000.0, rel=1e-5), (
        "epc_contract must NOT absorb the combined delta"
    )
    # total = 67000 + 6000 + 5000 + 6000 = 84000
    assert pi.capex.total_capex == pytest.approx(84000.0, rel=1e-4)


def test_epc_scalar_takes_authority_total_not_used_for_epc():
    """When capex_epc_contract_keur is explicitly set, it takes authority.

    No legacy normalization for epc — the scalar wins directly.
    Other factory items remain; total = scalar_epc + factory_others.
    """
    snap = _base_wind(total_capex_keur="80000", capex_epc_contract_keur="25000")
    pi = build_projectinputs_from_snapshot(snap)
    assert _get(pi, "epc_contract") == pytest.approx(25000.0)
    # total = 25000 + epc_other(6000) + grid(3000) + audit(4000) = 38000
    assert pi.capex.total_capex == pytest.approx(38000.0, rel=1e-4)


def test_legacy_only_total_capex_path_unchanged():
    """No scalar keys → legacy total_capex_keur path unchanged (backwards compat)."""
    pi_80k = build_projectinputs_from_snapshot(_base_wind(total_capex_keur="80000"))
    pi_60k = build_projectinputs_from_snapshot(_base_wind(total_capex_keur="60000"))
    assert pi_80k.capex.total_capex == pytest.approx(80000.0, rel=1e-4)
    assert pi_60k.capex.total_capex == pytest.approx(60000.0, rel=1e-4)
    # Different totals → different epc_contract (legacy path active)
    assert _get(pi_80k, "epc_contract") != pytest.approx(_get(pi_60k, "epc_contract"), abs=100)


# ── 5–6. Generic Solar: same authority rules ──────────────────────────────────
#
# Generic Solar factory: epc_contract=20000, production_units=3000,
#   epc_other=5000, grid_connection=2000, audit_legal=3000. total=33000.
# After _apply_capex_total(80000): epc = 80000 − 13000 = 67000.


def test_solar_scalar_grid_increase_raises_total_not_epc():
    """Generic Solar: scalar grid +2000 → total +2000; epc stays at 67000."""
    snap = _base_solar(total_capex_keur="80000", capex_grid_connection_keur="4000")
    pi = build_projectinputs_from_snapshot(snap)

    # Solar pre-edit baseline: epc=67000, grid=2000
    assert _get(pi, "grid_connection") == pytest.approx(4000.0)
    assert _get(pi, "epc_contract") == pytest.approx(67000.0, rel=1e-5), (
        "Solar: epc_contract must not move as balancing plug"
    )
    # total = 67000 + 3000 + 5000 + 4000 + 3000 = 82000 (grid went 2000→4000: +2000)
    assert pi.capex.total_capex == pytest.approx(82000.0, rel=1e-4)


# ── 7–9. TUHO: three authority scenarios ──────────────────────────────────────
#
# TUHO factory (from create_default_tuho_wind1()):
#   epc_contract=13560.0, grid_connection=100.0, audit_legal=40.0
#   total=70691.54, use_frozen_excel_senior_debt_schedule=False


def test_tuho_no_scalar_preserves_capex_structure():
    """TUHO: no scalar edit → factory CAPEX structure preserved exactly.

    When a TUHO working-copy snapshot carries no scalar CAPEX keys, the
    effective CAPEX must equal the factory line-by-line (seeded base path).
    """
    from app.project_factories import create_default_tuho_wind1
    tuho_factory = create_default_tuho_wind1()

    snap = _tuho_snap(total_capex_keur=str(tuho_factory.capex.total_capex))
    pi = build_projectinputs_from_snapshot(snap)

    assert _get(pi, "epc_contract") == pytest.approx(
        tuho_factory.capex.epc_contract.amount_keur, rel=1e-4
    ), "TUHO epc_contract drifted without any scalar edit"
    assert _get(pi, "grid_connection") == pytest.approx(
        tuho_factory.capex.grid_connection.amount_keur, rel=1e-4
    ), "TUHO grid_connection drifted without any scalar edit"
    assert pi.capex.total_capex == pytest.approx(
        tuho_factory.capex.total_capex, rel=1e-4
    ), "TUHO total_capex drifted without any scalar edit"
    # Financing authority preserved
    assert pi.financing.use_frozen_excel_senior_debt_schedule == (
        tuho_factory.financing.use_frozen_excel_senior_debt_schedule
    )


def test_tuho_scalar_equal_to_effective_value_no_change():
    """TUHO: scalar equal to factory grid_connection value → no economic change.

    Setting capex_grid_connection_keur=100 (= factory 100.0) must produce
    an identical CAPEX structure and leave financing authority unchanged.
    """
    from app.project_factories import create_default_tuho_wind1
    tuho_factory = create_default_tuho_wind1()
    factory_grid = tuho_factory.capex.grid_connection.amount_keur  # 100.0

    snap = _tuho_snap(
        total_capex_keur=str(tuho_factory.capex.total_capex),
        capex_grid_connection_keur=str(factory_grid),
    )
    pi = build_projectinputs_from_snapshot(snap)

    # No economic change
    assert _get(pi, "grid_connection") == pytest.approx(factory_grid, rel=1e-6)
    assert _get(pi, "epc_contract") == pytest.approx(
        tuho_factory.capex.epc_contract.amount_keur, rel=1e-4
    ), "epc_contract must not move when scalar equals effective value"
    assert pi.capex.total_capex == pytest.approx(
        tuho_factory.capex.total_capex, rel=1e-4
    ), "total_capex must not change when scalar equals effective value"
    # Financing preserved (no material change to trigger reset)
    assert pi.financing.use_frozen_excel_senior_debt_schedule == (
        tuho_factory.financing.use_frozen_excel_senior_debt_schedule
    )


def test_tuho_material_scalar_edit_changes_only_edited_field():
    """TUHO: material scalar change → edited field changes by exact delta; others unchanged.

    grid_connection: 100 → 5000 (delta +4900).
    epc_contract must NOT move to compensate.
    total must increase by exactly +4900.
    use_frozen_excel_senior_debt_schedule=False (factory) → remains False.
    """
    from app.project_factories import create_default_tuho_wind1
    tuho_factory = create_default_tuho_wind1()

    snap = _tuho_snap(
        total_capex_keur=str(tuho_factory.capex.total_capex),
        capex_grid_connection_keur="5000",
    )
    pi = build_projectinputs_from_snapshot(snap)

    assert _get(pi, "grid_connection") == pytest.approx(5000.0)
    # delta = 5000 - 100 = +4900
    assert pi.capex.total_capex == pytest.approx(
        tuho_factory.capex.total_capex + 4900.0, rel=1e-4
    ), "TUHO total must increase by exactly the grid delta (+4900)"
    # epc_contract must NOT move
    assert _get(pi, "epc_contract") == pytest.approx(
        tuho_factory.capex.epc_contract.amount_keur, rel=1e-4
    ), "TUHO epc_contract must not absorb the grid edit delta"
    # TUHO factory has use_frozen=False; material change does not trigger reset
    # because reset only fires when use_frozen IS True
    assert pi.financing.use_frozen_excel_senior_debt_schedule == (
        tuho_factory.financing.use_frozen_excel_senior_debt_schedule
    )


# ── 10. Oborovo: three authority scenarios ─────────────────────────────────────
#
# Oborovo factory: epc_contract=26430.0, grid_connection=4050.0
#   total=55999.09, use_frozen_excel_senior_debt_schedule=False
#   fixed_debt_keur=42852.27


def test_oborovo_no_scalar_preserves_capex_structure():
    """Oborovo: no scalar edit → factory CAPEX structure preserved."""
    from app.project_factories import create_default_oborovo
    obo_factory = create_default_oborovo()

    snap = _oborovo_snap(total_capex_keur=str(obo_factory.capex.total_capex))
    pi = build_projectinputs_from_snapshot(snap)

    assert _get(pi, "epc_contract") == pytest.approx(
        obo_factory.capex.epc_contract.amount_keur, rel=1e-4
    )
    assert _get(pi, "grid_connection") == pytest.approx(
        obo_factory.capex.grid_connection.amount_keur, rel=1e-4
    )
    assert pi.capex.total_capex == pytest.approx(obo_factory.capex.total_capex, rel=1e-4)
    assert pi.financing.use_frozen_excel_senior_debt_schedule == (
        obo_factory.financing.use_frozen_excel_senior_debt_schedule
    )


def test_oborovo_scalar_equal_to_effective_value_preserves_financing():
    """Oborovo: scalar equal to factory epc_contract → fixed_debt_keur preserved.

    fixed_debt_keur is a calibrated financing value; it must not reset when
    there is no material CAPEX change.
    """
    from app.project_factories import create_default_oborovo
    obo_factory = create_default_oborovo()
    factory_epc = obo_factory.capex.epc_contract.amount_keur  # 26430.0

    snap = _oborovo_snap(
        total_capex_keur=str(obo_factory.capex.total_capex),
        capex_epc_contract_keur=str(factory_epc),
    )
    pi = build_projectinputs_from_snapshot(snap)

    assert _get(pi, "epc_contract") == pytest.approx(factory_epc, rel=1e-6)
    assert pi.capex.total_capex == pytest.approx(obo_factory.capex.total_capex, rel=1e-4)
    # No material change → financing preserved
    assert pi.financing.use_frozen_excel_senior_debt_schedule == (
        obo_factory.financing.use_frozen_excel_senior_debt_schedule
    )
    assert pi.financing.fixed_debt_keur == pytest.approx(
        obo_factory.financing.fixed_debt_keur, rel=1e-4
    )


def test_oborovo_material_scalar_edit_changes_only_edited_field():
    """Oborovo: material scalar on epc → only epc changes; grid unchanged; total correct.

    epc: 26430 → 40000 (delta +13570). grid must remain at 4050 (factory).
    use_frozen=False (factory) → remains False (no frozen-schedule reset triggers).
    """
    from app.project_factories import create_default_oborovo
    obo_factory = create_default_oborovo()

    snap = _oborovo_snap(
        total_capex_keur=str(obo_factory.capex.total_capex),
        capex_epc_contract_keur="40000",
    )
    pi = build_projectinputs_from_snapshot(snap)

    assert _get(pi, "epc_contract") == pytest.approx(40000.0)
    # grid must NOT move
    assert _get(pi, "grid_connection") == pytest.approx(
        obo_factory.capex.grid_connection.amount_keur, rel=1e-4
    ), "Oborovo grid_connection must not change when only epc scalar is edited"
    # total increases by exactly the epc delta
    expected_total = obo_factory.capex.total_capex + (40000.0 - obo_factory.capex.epc_contract.amount_keur)
    assert pi.capex.total_capex == pytest.approx(expected_total, rel=1e-4)
    # use_frozen was False; no reset needed
    assert pi.financing.use_frozen_excel_senior_debt_schedule == (
        obo_factory.financing.use_frozen_excel_senior_debt_schedule
    )


# ── 11. Explicit zero semantics ────────────────────────────────────────────────

def test_explicit_zero_sets_field_to_zero():
    """capex_epc_contract_keur='0' must set epc_contract.amount_keur = 0.0."""
    pi = build_projectinputs_from_snapshot(_base_wind(capex_epc_contract_keur="0"))
    assert _get(pi, "epc_contract") == pytest.approx(0.0, abs=1e-9)


def test_explicit_zero_epc_with_total_epc_wins():
    """Explicit epc=0 + total=80000 → epc=0 (scalar wins for epc_contract)."""
    pi = build_projectinputs_from_snapshot(
        _base_wind(total_capex_keur="80000", capex_epc_contract_keur="0")
    )
    assert _get(pi, "epc_contract") == pytest.approx(0.0, abs=1e-9)


def test_explicit_zero_non_epc_field():
    """capex_grid_connection_keur='0' sets grid_connection=0 (valid zero override)."""
    pi = build_projectinputs_from_snapshot(_base_wind(capex_grid_connection_keur="0"))
    assert _get(pi, "grid_connection") == pytest.approx(0.0, abs=1e-9)


def test_empty_string_scalar_treated_as_absent():
    """Empty-string scalar key treated as absent → uses legacy total path."""
    snap_empty = _base_wind(total_capex_keur="80000", capex_epc_contract_keur="")
    pi_empty = build_projectinputs_from_snapshot(snap_empty)
    snap_no_scalar = _base_wind(total_capex_keur="80000")
    pi_no_scalar = build_projectinputs_from_snapshot(snap_no_scalar)
    assert _get(pi_empty, "epc_contract") == pytest.approx(
        _get(pi_no_scalar, "epc_contract"), rel=1e-6
    )


# ── 12–13. V2 WorkbookService path ────────────────────────────────────────────

def test_v2_draft_input_set_scalar_reaches_projectinputs():
    """V2 draft path: scalar flows through WorkbookService → to_projectinputs()."""
    from app.workbook.service import WorkbookService

    snap = _base_wind(capex_grid_connection_keur="7500")
    pi = WorkbookService.to_projectinputs(
        WorkbookService.build_draft_input_set_from_workspace(_make_ws(snap))
    )
    assert pi.capex.grid_connection.amount_keur == pytest.approx(7500.0)


def test_v2_saved_input_set_scalar_reaches_projectinputs():
    """V2 saved path: scalar flows through WorkbookService → to_projectinputs()."""
    from app.workbook.service import WorkbookService

    snap = _base_wind(capex_epc_other_keur="8888")
    pi = WorkbookService.to_projectinputs(
        WorkbookService.build_saved_input_set_from_workspace(_make_ws(snap))
    )
    assert pi.capex.epc_other.amount_keur == pytest.approx(8888.0)


def test_v2_scalar_edit_correct_total_delta():
    """V2: scalar grid edit → total reflects correct delta, epc not moved.

    Grid edit via V2 path: grid 3000→7500 (+4500).
    Pre-edit baseline (total=80000): epc=67000.
    After scalar: epc=67000, total=84500.
    """
    from app.workbook.service import WorkbookService

    snap = _base_wind(total_capex_keur="80000", capex_grid_connection_keur="7500")
    pi = WorkbookService.to_projectinputs(
        WorkbookService.build_draft_input_set_from_workspace(_make_ws(snap))
    )

    assert pi.capex.grid_connection.amount_keur == pytest.approx(7500.0)
    assert pi.capex.epc_contract.amount_keur == pytest.approx(67000.0, rel=1e-5), (
        "V2: epc_contract must not move as balancing plug"
    )
    # total = 67000 + 6000 + 7500 + 4000 = 84500 (grid went 3000→7500: +4500)
    assert pi.capex.total_capex == pytest.approx(84500.0, rel=1e-4)


# ── 14. Atomic persistence round-trip ─────────────────────────────────────────

def test_atomic_persistence_roundtrip_scalar_capex():
    """Atomic persistence: save workspace → reload → WorkbookService → scalar reaches ProjectInputs.

    Causal chain: snapshot dict → save_workspace_state → get_workspace_state
    → WorkbookService.build_draft_input_set_from_workspace → to_projectinputs()
    → capex.grid_connection.amount_keur == 7500.

    Also verifies: epc_contract stays at 67000 (Correction B: not used as plug),
    total_capex = 84500 (legacy baseline 80000 + delta 4500).
    """
    import app.persistence.db as db_mod
    from app.persistence.projects_repository import save_project
    from app.persistence.workspace_repository import save_workspace_state, get_workspace_state
    from app.workbook.service import WorkbookService

    db_file = f"/tmp/r1_persist_test_{uuid.uuid4().hex[:8]}.db"
    old_path = db_mod.DB_PATH
    db_mod.DB_PATH = db_file
    os.environ["FINCO_DB_PATH"] = db_file

    try:
        proj = save_project("user1", "r1-persist-test", "R1 Persist Test", "wind",
                            project_type="wind")

        snap = _base_wind(total_capex_keur="80000", capex_grid_connection_keur="7500")

        save_workspace_state(
            user_id="user1",
            project_id=proj.project_id,
            project_code="r1-persist-test",
            draft_snapshot=snap,
            saved_snapshot=snap,
        )

        ws_reloaded = get_workspace_state("user1", proj.project_id)
        assert ws_reloaded is not None, "Workspace not found after save"

        pis = WorkbookService.build_draft_input_set_from_workspace(ws_reloaded)
        pi = WorkbookService.to_projectinputs(pis)

        assert pi.capex.grid_connection.amount_keur == pytest.approx(7500.0), (
            "Scalar did not survive persistence round-trip"
        )
        assert pi.capex.epc_contract.amount_keur == pytest.approx(67000.0, rel=1e-5), (
            "epc_contract must not be used as plug after reload"
        )
        # delta = 7500 - 3000 = 4500 → total = 80000 + 4500 = 84500
        assert pi.capex.total_capex == pytest.approx(84500.0, rel=1e-4), (
            "total_capex must reflect correct delta after persistence round-trip"
        )
    finally:
        db_mod.DB_PATH = old_path
        os.environ.pop("FINCO_DB_PATH", None)
        if os.path.exists(db_file):
            os.remove(db_file)


# ── 15. Scenario isolation via ScenarioManager multiplier ─────────────────────

def test_scenario_multiplier_capex_isolation():
    """ScenarioManager 'Downside' applies capex_multiplier=1.05 to Base.

    The scenario multiplier scales total CAPEX proportionally. The Base
    ProjectInputs is unchanged by the alternate scenario resolution.

    CAPEX scalars are not in SCENARIO_INPUT_FIELDS (they are factory-project
    fields, not scenario-overridable), so scenario isolation is through the
    existing ScenarioManager.apply_overrides() multiplier contract.
    """
    from app.scenario_manager import ScenarioManager

    base_pi = build_projectinputs_from_snapshot(_base_wind(total_capex_keur="80000"))
    base_total = base_pi.capex.total_capex

    mgr = ScenarioManager("wind")
    downside_pi = mgr.apply_overrides(base_pi, "Downside")
    downside_total = downside_pi.capex.total_capex

    # Downside applies capex_multiplier=1.05
    assert downside_total == pytest.approx(base_total * 1.05, rel=1e-4), (
        "Downside scenario must scale total CAPEX by 1.05"
    )
    # Base unchanged after alternate scenario resolution
    assert base_pi.capex.total_capex == pytest.approx(base_total, rel=1e-8), (
        "Base ProjectInputs must be unchanged after alternate scenario resolution"
    )


# ── 16. Engine fingerprint: Generic Wind ──────────────────────────────────────

def test_engine_fingerprint_wind_scalar_mutation():
    """Generic Wind scalar mutation → hard_project_capex_keur changes in engine output.

    Causal chain: snapshot scalar → ProjectInputs → classify_production_authority
    → run_project_shareholder_waterfall_model → financing_result.project_uses.
    hard_project_capex_keur.

    Baseline (factory): hard_capex = 43000.
    Mutation: capex_epc_contract_keur=50000 → total=63000.
    Expected mutated hard_capex = 63000.
    """
    from app.services.production_financial_authority import run_clean_production

    # Baseline: factory (no scalar, no legacy total)
    from app import project_factories as pf
    pi_base = pf.create_default_wind_project()
    r_base = run_clean_production(pi_base, "Base", project_type="Wind")
    base_hard_capex = r_base.g2c_result.financing_result.project_uses.hard_project_capex_keur
    assert base_hard_capex == pytest.approx(43000.0, rel=1e-4), (
        "Wind factory hard_project_capex_keur baseline should be 43000"
    )

    # Mutation: epc scalar epc=50000. When capex_epc_contract_keur is supplied,
    # the scalar takes authority and total_capex_keur is NOT used to re-force epc.
    # total = 50000 (epc) + 6000 (epc_other) + 3000 (grid) + 4000 (audit) = 63000.
    pi_mut = build_projectinputs_from_snapshot(
        _base_wind(capex_epc_contract_keur="50000")
    )
    assert pi_mut.capex.total_capex == pytest.approx(63000.0, rel=1e-4)

    r_mut = run_clean_production(pi_mut, "Base", project_type="Wind")
    mut_hard_capex = r_mut.g2c_result.financing_result.project_uses.hard_project_capex_keur

    assert mut_hard_capex == pytest.approx(63000.0, rel=1e-4), (
        f"Wind mutated hard_capex should be 63000; got {mut_hard_capex}"
    )
    assert mut_hard_capex != pytest.approx(base_hard_capex, abs=1000), (
        "Scalar mutation must produce different engine hard_project_capex_keur"
    )


# ── 17. Engine fingerprint: Generic Solar ─────────────────────────────────────

def test_engine_fingerprint_solar_scalar_mutation():
    """Generic Solar scalar mutation → hard_project_capex_keur changes in engine output.

    Baseline (factory): hard_capex = 33000.
    Mutation: capex_epc_contract_keur=40000 → total = 40000 + 3000 + 5000 + 2000 + 3000 = 53000.
    Expected mutated hard_capex = 53000.
    """
    from app.services.production_financial_authority import run_clean_production
    from app import project_factories as pf

    pi_base = pf.create_default_solar_project()
    r_base = run_clean_production(pi_base, "Base", project_type="Solar")
    base_hard_capex = r_base.g2c_result.financing_result.project_uses.hard_project_capex_keur
    assert base_hard_capex == pytest.approx(33000.0, rel=1e-4)

    # Mutation: epc=40000 scalar. When capex_epc_contract_keur is supplied,
    # scalar takes authority; total = 40000 + 3000 + 5000 + 2000 + 3000 = 53000.
    pi_mut = build_projectinputs_from_snapshot(
        _base_solar(capex_epc_contract_keur="40000")
    )
    assert pi_mut.capex.total_capex == pytest.approx(53000.0, rel=1e-4)

    r_mut = run_clean_production(pi_mut, "Base", project_type="Solar")
    mut_hard_capex = r_mut.g2c_result.financing_result.project_uses.hard_project_capex_keur

    assert mut_hard_capex == pytest.approx(53000.0, rel=1e-4), (
        f"Solar mutated hard_capex should be 53000; got {mut_hard_capex}"
    )
    assert mut_hard_capex != pytest.approx(base_hard_capex, abs=1000)


# ── 18. UUID sub-line interaction (no double counting) ────────────────────────

def test_scalar_plus_uuid_subline_no_double_counting():
    """UUID sub-lines REPLACE the scalar base (replace semantics, no double counting).

    Pipeline: scalar sets epc_contract=5000 → apply_user_sub_lines_replacing_base
    zeros the C.02 category base → adds sub-line amounts.
    Result = 8000, NOT 5000 + 8000 = 13000.
    """
    from app.services.capex_sub_lines_integration import apply_user_sub_lines_replacing_base
    from app.persistence.capex_sub_lines import CapexSubLine
    from app.services import capex_sub_lines_integration as csi

    snap = _base_wind(capex_epc_contract_keur="5000")
    pi = build_projectinputs_from_snapshot(snap)
    assert _get(pi, "epc_contract") == pytest.approx(5000.0)

    mock_sub = CapexSubLine(
        sub_line_id=str(uuid.uuid4()),
        project_id="proj-test",
        parent_category_code="C.02",
        business_code="C.02.01",
        label="Custom EPC Component",
        amount_keur=8000.0,
        display_order=1,
        is_active=True,
        comments=None,
        schedule_json=None,
        scalar_metadata=None,
        source=None,
        governance_state={},
        replay_metadata={},
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
        id=None,
    )

    with patch.object(csi, "_load_active_sub_lines", return_value=[mock_sub]):
        capex_after = apply_user_sub_lines_replacing_base(pi.capex, project_id="proj-test")

    assert capex_after.epc_contract.amount_keur == pytest.approx(8000.0), (
        f"UUID sub-line double counting: expected 8000, got {capex_after.epc_contract.amount_keur}"
    )


# ── 19. Stateless independence ─────────────────────────────────────────────────

def test_resolve_is_stateless_independent_calls():
    """Two independent calls with identical snapshots produce identical ProjectInputs."""
    snap = _base_wind(capex_epc_contract_keur="12345.67")
    pi_1 = build_projectinputs_from_snapshot(snap)
    pi_2 = build_projectinputs_from_snapshot(snap)
    assert pi_1.capex.epc_contract.amount_keur == pi_2.capex.epc_contract.amount_keur


def test_different_snapshots_dont_bleed():
    """Scalar values from one snapshot do not affect a subsequent resolution."""
    snap_a = _base_wind(capex_epc_contract_keur="5000", capex_grid_connection_keur="1000")
    snap_b = _base_wind(capex_epc_contract_keur="40000", capex_ops_prep_keur="3000")

    pi_a = build_projectinputs_from_snapshot(snap_a)
    pi_b = build_projectinputs_from_snapshot(snap_b)

    assert _get(pi_a, "epc_contract") == pytest.approx(5000.0)
    assert _get(pi_a, "grid_connection") == pytest.approx(1000.0)
    assert _get(pi_a, "ops_prep") == pytest.approx(0.0)

    assert _get(pi_b, "epc_contract") == pytest.approx(40000.0)
    assert _get(pi_b, "ops_prep") == pytest.approx(3000.0)


# ── 20–21. Scalar map completeness ────────────────────────────────────────────

def test_scalar_map_has_exactly_14_entries():
    """_SCALAR_CAPEX_MAP must contain exactly 14 entries."""
    assert len(_SCALAR_CAPEX_MAP) == 14


def test_scalar_map_all_values_are_valid_capex_fields():
    """All field_name values in _SCALAR_CAPEX_MAP must be CapexItem fields."""
    pi = build_projectinputs_from_snapshot(_base_wind())
    for snap_key, field_name in _SCALAR_CAPEX_MAP.items():
        item = getattr(pi.capex, field_name, None)
        assert item is not None, f"capex.{field_name} not found (from key {snap_key})"
        assert hasattr(item, "amount_keur"), (
            f"capex.{field_name} has no amount_keur (from key {snap_key})"
        )


def test_scalar_map_keys_match_registry_snapshot_keys():
    """All _SCALAR_CAPEX_MAP keys must correspond to BOUND fields in the workbook registry."""
    from app.workbook.registry import WORKBOOK
    from app.workbook.specs import BindingStatus

    registry_snapshot_keys: set = set()
    for sheet in WORKBOOK.sheets:
        for section in sheet.sections:
            for field in section.fields:
                bs = getattr(field, "binding_status", None)
                sk = getattr(field, "snapshot_key", None)
                if (
                    sk
                    and bs == BindingStatus.BOUND
                    and sk.startswith("capex_")
                    and sk.endswith("_keur")
                ):
                    registry_snapshot_keys.add(sk)

    missing_from_registry = set(_SCALAR_CAPEX_MAP.keys()) - registry_snapshot_keys
    assert not missing_from_registry, (
        f"Scalar keys not in registry bound fields: {missing_from_registry}"
    )


# ── 22. Smoke ─────────────────────────────────────────────────────────────────

def test_r1_introduces_no_new_adapter_failures():
    """Core adapter smoke: build_projectinputs_from_snapshot works for wind and solar."""
    for snap in [_base_wind(), _base_solar()]:
        pi = build_projectinputs_from_snapshot(snap)
        assert pi is not None
        assert pi.capex.total_capex > 0


# ── 23. Correction C: seeded projects with a legacy total ─────────────────────
#
# Before R1, seeded TUHO/Oborovo working copies could have a persisted
# total_capex_keur different from the calibrated factory total.  The pre-R1
# seeded path detected the divergence, zeroed financial sub-fields, and called
# _apply_capex_total to reproduce the legacy aggregate.
#
# A subsequent scalar edit must:
#   1. Reconstruct that SAME pre-edit effective baseline (Correction C).
#   2. Apply the scalar on top.
# It must NOT revert untouched lines toward the pristine seeded factory.
#
# Helper: materialise pre-R1 effective baseline for a seeded project.

def _pre_r1_seeded_effective(factory_pi, legacy_total: float):
    """Return (pi, epc, grid) after applying pre-R1 legacy-total normalization."""
    from app.input_adapter import _zero_financial_capex_subfields, _apply_capex_total
    p = _zero_financial_capex_subfields(factory_pi)
    p = _apply_capex_total(p, legacy_total)
    return p, p.capex.epc_contract.amount_keur, p.capex.grid_connection.amount_keur


# ── Case A: factory total + no scalar ─────────────────────────────────────────

def test_tuho_A_factory_total_no_scalar_preserves_factory():
    """TUHO A: legacy total == factory total, no scalar → factory CAPEX preserved."""
    from app.project_factories import create_default_tuho_wind1
    fac = create_default_tuho_wind1()
    pi = build_projectinputs_from_snapshot(
        _tuho_snap(total_capex_keur=str(fac.capex.total_capex))
    )
    assert _get(pi, "epc_contract") == pytest.approx(fac.capex.epc_contract.amount_keur, rel=1e-4)
    assert _get(pi, "grid_connection") == pytest.approx(fac.capex.grid_connection.amount_keur, rel=1e-4)
    assert pi.capex.total_capex == pytest.approx(fac.capex.total_capex, rel=1e-4)
    assert pi.financing.use_frozen_excel_senior_debt_schedule == fac.financing.use_frozen_excel_senior_debt_schedule


def test_oborovo_A_factory_total_no_scalar_preserves_factory():
    """Oborovo A: legacy total == factory total, no scalar → factory CAPEX preserved."""
    from app.project_factories import create_default_oborovo
    fac = create_default_oborovo()
    pi = build_projectinputs_from_snapshot(
        _oborovo_snap(total_capex_keur=str(fac.capex.total_capex))
    )
    assert _get(pi, "epc_contract") == pytest.approx(fac.capex.epc_contract.amount_keur, rel=1e-4)
    assert _get(pi, "grid_connection") == pytest.approx(fac.capex.grid_connection.amount_keur, rel=1e-4)
    assert pi.capex.total_capex == pytest.approx(fac.capex.total_capex, rel=1e-4)
    assert pi.financing.use_frozen_excel_senior_debt_schedule == fac.financing.use_frozen_excel_senior_debt_schedule


# ── Case B: factory total + equal-value scalar ────────────────────────────────

def test_tuho_B_factory_total_equal_scalar_no_economic_change():
    """TUHO B: legacy total == factory total + scalar = factory grid → no economic change."""
    from app.project_factories import create_default_tuho_wind1
    fac = create_default_tuho_wind1()
    factory_grid = fac.capex.grid_connection.amount_keur
    pi = build_projectinputs_from_snapshot(
        _tuho_snap(total_capex_keur=str(fac.capex.total_capex),
                   capex_grid_connection_keur=str(factory_grid))
    )
    assert _get(pi, "grid_connection") == pytest.approx(factory_grid, rel=1e-6)
    assert _get(pi, "epc_contract") == pytest.approx(fac.capex.epc_contract.amount_keur, rel=1e-4)
    assert pi.capex.total_capex == pytest.approx(fac.capex.total_capex, rel=1e-4)
    assert pi.financing.use_frozen_excel_senior_debt_schedule == fac.financing.use_frozen_excel_senior_debt_schedule


def test_oborovo_B_factory_total_equal_scalar_no_economic_change():
    """Oborovo B: legacy total == factory total + scalar = factory grid → no economic change."""
    from app.project_factories import create_default_oborovo
    fac = create_default_oborovo()
    factory_grid = fac.capex.grid_connection.amount_keur
    pi = build_projectinputs_from_snapshot(
        _oborovo_snap(total_capex_keur=str(fac.capex.total_capex),
                      capex_grid_connection_keur=str(factory_grid))
    )
    assert _get(pi, "grid_connection") == pytest.approx(factory_grid, rel=1e-6)
    assert _get(pi, "epc_contract") == pytest.approx(fac.capex.epc_contract.amount_keur, rel=1e-4)
    assert pi.capex.total_capex == pytest.approx(fac.capex.total_capex, rel=1e-4)
    assert pi.financing.use_frozen_excel_senior_debt_schedule == fac.financing.use_frozen_excel_senior_debt_schedule


# ── Case C: factory total + material scalar ───────────────────────────────────

def test_tuho_C_factory_total_material_scalar_only_edited_field_changes():
    """TUHO C: legacy total == factory total + material scalar → only edited field changes.

    grid: factory 100 → 5000 (+4900). epc must NOT absorb the delta.
    Total increases by exactly +4900.
    """
    from app.project_factories import create_default_tuho_wind1
    fac = create_default_tuho_wind1()
    pi = build_projectinputs_from_snapshot(
        _tuho_snap(total_capex_keur=str(fac.capex.total_capex),
                   capex_grid_connection_keur="5000")
    )
    assert _get(pi, "grid_connection") == pytest.approx(5000.0)
    assert _get(pi, "epc_contract") == pytest.approx(fac.capex.epc_contract.amount_keur, rel=1e-4), (
        "TUHO C: epc must not absorb the grid scalar delta"
    )
    assert pi.capex.total_capex == pytest.approx(
        fac.capex.total_capex + (5000.0 - fac.capex.grid_connection.amount_keur), rel=1e-4
    )


def test_oborovo_C_factory_total_material_scalar_only_edited_field_changes():
    """Oborovo C: legacy total == factory total + material scalar → only edited field changes.

    epc: 26430 → 40000 (+13570). grid must remain at factory 4050.
    """
    from app.project_factories import create_default_oborovo
    fac = create_default_oborovo()
    pi = build_projectinputs_from_snapshot(
        _oborovo_snap(total_capex_keur=str(fac.capex.total_capex),
                      capex_epc_contract_keur="40000")
    )
    assert _get(pi, "epc_contract") == pytest.approx(40000.0)
    assert _get(pi, "grid_connection") == pytest.approx(fac.capex.grid_connection.amount_keur, rel=1e-4)
    assert pi.capex.total_capex == pytest.approx(
        fac.capex.total_capex + (40000.0 - fac.capex.epc_contract.amount_keur), rel=1e-4
    )


# ── Case D: legacy total materially above factory + scalar increase ────────────

def test_tuho_D_legacy_above_factory_scalar_increase_uses_effective_baseline():
    """TUHO D (Correction C): legacy=80000 > factory(70691.54), scalar grid=500.

    Pre-edit effective: epc≈22868.46, grid=100, total=80000.
    Scalar grid 100→500 (+400).
    Expected: epc≈22868.46 (pre-edit effective), grid=500, total=80400.
    epc must NOT revert to factory 13560.
    """
    from app.project_factories import create_default_tuho_wind1
    fac = create_default_tuho_wind1()
    legacy_total = 80000.0
    _, pre_edit_epc, pre_edit_grid = _pre_r1_seeded_effective(fac, legacy_total)

    pi = build_projectinputs_from_snapshot(
        _tuho_snap(total_capex_keur=str(legacy_total), capex_grid_connection_keur="500")
    )

    assert _get(pi, "grid_connection") == pytest.approx(500.0), "TUHO D: grid not set"
    assert _get(pi, "epc_contract") == pytest.approx(pre_edit_epc, rel=1e-4), (
        f"TUHO D: epc={_get(pi,'epc_contract'):.2f} must equal pre-edit effective "
        f"{pre_edit_epc:.2f}, not factory {fac.capex.epc_contract.amount_keur:.2f}"
    )
    assert pi.capex.total_capex == pytest.approx(legacy_total + (500.0 - pre_edit_grid), rel=1e-4), (
        "TUHO D: total must be legacy_total + scalar_delta"
    )


def test_oborovo_D_legacy_above_factory_scalar_increase_uses_effective_baseline():
    """Oborovo D (Correction C): legacy=70000 > factory(55999.09), scalar grid=5000.

    Pre-edit effective: epc≈40430.91, grid=4050, total=70000.
    Scalar grid 4050→5000 (+950).
    Expected: epc≈40430.91 (pre-edit effective), grid=5000, total=70950.
    epc must NOT revert to factory 26430.
    """
    from app.project_factories import create_default_oborovo
    fac = create_default_oborovo()
    legacy_total = 70000.0
    _, pre_edit_epc, pre_edit_grid = _pre_r1_seeded_effective(fac, legacy_total)

    pi = build_projectinputs_from_snapshot(
        _oborovo_snap(total_capex_keur=str(legacy_total), capex_grid_connection_keur="5000")
    )

    assert _get(pi, "grid_connection") == pytest.approx(5000.0), "Oborovo D: grid not set"
    assert _get(pi, "epc_contract") == pytest.approx(pre_edit_epc, rel=1e-4), (
        f"Oborovo D: epc={_get(pi,'epc_contract'):.2f} must equal pre-edit effective "
        f"{pre_edit_epc:.2f}, not factory {fac.capex.epc_contract.amount_keur:.2f}"
    )
    assert pi.capex.total_capex == pytest.approx(legacy_total + (5000.0 - pre_edit_grid), rel=1e-4)


# ── Case E: legacy total materially above factory + scalar decrease ────────────

def test_tuho_E_legacy_above_factory_scalar_decrease_uses_effective_baseline():
    """TUHO E (Correction C): legacy=80000, scalar grid=50 (decrease, 100→50).

    Pre-edit effective: epc≈22868.46, grid=100, total=80000.
    Scalar grid 100→50 (−50). Expected: epc≈22868.46, total=79950.
    """
    from app.project_factories import create_default_tuho_wind1
    fac = create_default_tuho_wind1()
    legacy_total = 80000.0
    _, pre_edit_epc, pre_edit_grid = _pre_r1_seeded_effective(fac, legacy_total)

    pi = build_projectinputs_from_snapshot(
        _tuho_snap(total_capex_keur=str(legacy_total), capex_grid_connection_keur="50")
    )

    assert _get(pi, "grid_connection") == pytest.approx(50.0)
    assert _get(pi, "epc_contract") == pytest.approx(pre_edit_epc, rel=1e-4), (
        "TUHO E: epc must stay at pre-edit effective after scalar decrease"
    )
    assert pi.capex.total_capex == pytest.approx(legacy_total + (50.0 - pre_edit_grid), rel=1e-4)


def test_oborovo_E_legacy_above_factory_scalar_decrease_uses_effective_baseline():
    """Oborovo E (Correction C): legacy=70000, scalar grid=3000 (decrease, 4050→3000).

    Pre-edit effective: epc≈40430.91, grid=4050, total=70000.
    Scalar grid 4050→3000 (−1050). Expected: epc≈40430.91, total=68950.
    """
    from app.project_factories import create_default_oborovo
    fac = create_default_oborovo()
    legacy_total = 70000.0
    _, pre_edit_epc, pre_edit_grid = _pre_r1_seeded_effective(fac, legacy_total)

    pi = build_projectinputs_from_snapshot(
        _oborovo_snap(total_capex_keur=str(legacy_total), capex_grid_connection_keur="3000")
    )

    assert _get(pi, "grid_connection") == pytest.approx(3000.0)
    assert _get(pi, "epc_contract") == pytest.approx(pre_edit_epc, rel=1e-4), (
        "Oborovo E: epc must stay at pre-edit effective after scalar decrease"
    )
    assert pi.capex.total_capex == pytest.approx(legacy_total + (3000.0 - pre_edit_grid), rel=1e-4)


# ── Case F: legacy total materially below factory + scalar ─────────────────────

def test_tuho_F_legacy_below_factory_scalar_uses_effective_baseline():
    """TUHO F (Correction C): legacy=60000 < factory(70691.54), scalar grid=500.

    Pre-edit effective: epc≈2868.46, grid=100, total=60000.
    Scalar grid 100→500 (+400). Expected: epc≈2868.46, total=60400.
    epc must NOT revert to factory 13560.
    """
    from app.project_factories import create_default_tuho_wind1
    fac = create_default_tuho_wind1()
    legacy_total = 60000.0
    _, pre_edit_epc, pre_edit_grid = _pre_r1_seeded_effective(fac, legacy_total)

    pi = build_projectinputs_from_snapshot(
        _tuho_snap(total_capex_keur=str(legacy_total), capex_grid_connection_keur="500")
    )

    assert _get(pi, "grid_connection") == pytest.approx(500.0)
    assert _get(pi, "epc_contract") == pytest.approx(pre_edit_epc, rel=1e-4), (
        f"TUHO F: epc={_get(pi,'epc_contract'):.2f} must equal pre-edit effective "
        f"{pre_edit_epc:.2f}, not factory {fac.capex.epc_contract.amount_keur:.2f}"
    )
    assert pi.capex.total_capex == pytest.approx(legacy_total + (500.0 - pre_edit_grid), rel=1e-4)
    # pre_edit_epc (≈2868) is materially lower than factory epc (13560)
    assert abs(_get(pi, "epc_contract") - fac.capex.epc_contract.amount_keur) > 1000, (
        "TUHO F: pre-edit effective epc must differ materially from factory epc"
    )


def test_oborovo_F_legacy_below_factory_scalar_uses_effective_baseline():
    """Oborovo F (Correction C): legacy=40000 < factory(55999.09), scalar grid=5000.

    Pre-edit effective: epc≈10430.91, grid=4050, total=40000.
    Scalar grid 4050→5000 (+950). Expected: epc≈10430.91, total=40950.
    """
    from app.project_factories import create_default_oborovo
    fac = create_default_oborovo()
    legacy_total = 40000.0
    _, pre_edit_epc, pre_edit_grid = _pre_r1_seeded_effective(fac, legacy_total)

    pi = build_projectinputs_from_snapshot(
        _oborovo_snap(total_capex_keur=str(legacy_total), capex_grid_connection_keur="5000")
    )

    assert _get(pi, "grid_connection") == pytest.approx(5000.0)
    assert _get(pi, "epc_contract") == pytest.approx(pre_edit_epc, rel=1e-4), (
        f"Oborovo F: epc={_get(pi,'epc_contract'):.2f} must equal pre-edit effective "
        f"{pre_edit_epc:.2f}, not factory {fac.capex.epc_contract.amount_keur:.2f}"
    )
    assert pi.capex.total_capex == pytest.approx(legacy_total + (5000.0 - pre_edit_grid), rel=1e-4)
    assert abs(_get(pi, "epc_contract") - fac.capex.epc_contract.amount_keur) > 1000


# ── 24. Correction C engine parity ────────────────────────────────────────────
#
# For at least one seeded legacy-total case: prove via canonical engine run that
# the CAPEX delta originates from the intended scalar edit and that no unrelated
# CAPEX authority was silently lost.
#
# TUHO/Oborovo have calibrated SHL schedules that fail at maturity when CAPEX
# changes (SHL_MATURITY_RESIDUAL_FAILS_CLOSED) and also have sponsor_funding_mode=None
# which blocks the G2A financing model.  Direct engine runs on the seeded templates
# after a CAPEX change require full financing recalibration — outside R1 scope.
#
# Canonical engine proof: use Generic Wind with legacy-total path (same adapter
# code path as seeded Correction C) and prove hard_project_capex_keur delta.
# The causal invariant is shared: the effective-baseline reconstruction and
# scalar application are identical code for factory and seeded projects.

def test_correction_c_engine_parity_legacy_total_scalar_delta():
    """Engine parity: Generic Wind legacy-total effective baseline + scalar → correct engine delta.

    Pre-scalar: legacy_total=80000, no scalar. Effective baseline: epc=67000, grid=3000.
    Post-scalar: same legacy_total + scalar grid=5000 (delta +2000). Expected total=82000.

    Canonical engine (run_project_shareholder_waterfall_model) must produce:
      post.hard_project_capex_keur − pre.hard_project_capex_keur == +2000 exactly.

    This proves the Correction C effective-baseline reconstruction flows through to
    the canonical engine output: the output delta equals the intended CAPEX edit.
    """
    from app.services.production_financial_authority import run_clean_production

    # Pre-scalar effective ProjectInputs (legacy total=80000, no scalar).
    pi_pre = build_projectinputs_from_snapshot(_base_wind(total_capex_keur="80000"))
    assert pi_pre.capex.total_capex == pytest.approx(80000.0, rel=1e-4)
    assert _get(pi_pre, "epc_contract") == pytest.approx(67000.0, rel=1e-4)
    assert _get(pi_pre, "grid_connection") == pytest.approx(3000.0)

    # Post-scalar: grid 3000 → 5000 (delta +2000). epc must remain at 67000.
    pi_post = build_projectinputs_from_snapshot(
        _base_wind(total_capex_keur="80000", capex_grid_connection_keur="5000")
    )
    assert _get(pi_post, "epc_contract") == pytest.approx(67000.0, rel=1e-4), (
        "Correction C: epc must remain at pre-edit effective (67000) after scalar"
    )
    assert pi_post.capex.total_capex == pytest.approx(82000.0, rel=1e-4)

    # Canonical engine runs — prove delta == scalar delta.
    r_pre = run_clean_production(pi_pre, "Base", project_type="Wind")
    r_post = run_clean_production(pi_post, "Base", project_type="Wind")
    pre_hard = r_pre.g2c_result.financing_result.project_uses.hard_project_capex_keur
    post_hard = r_post.g2c_result.financing_result.project_uses.hard_project_capex_keur

    assert post_hard - pre_hard == pytest.approx(2000.0, rel=1e-4), (
        f"Engine hard_project_capex_keur delta must equal scalar delta (+2000); "
        f"got pre={pre_hard:.2f} post={post_hard:.2f} delta={post_hard-pre_hard:.2f}"
    )
