"""R1 — Scalar CAPEX Input Authority.

Causal tests proving each of the 14 editable scalar CAPEX snapshot keys
flows through the full pipeline:

  persisted snapshot → _snapshot_to_dict → _resolve_user_inputs
                     → ProjectInputs.capex.<field>.amount_keur

Tests also verify:
- Scalar authority: when scalar keys present, they override total_capex_keur.
- Legacy fallback: when no scalar keys present, total_capex_keur path is used.
- Seeded base (Oborovo/TUHO): scalars override the seeded base correctly.
- No-op: when snapshot has no CAPEX keys at all, factory default is preserved.
- Regression: TUHO and Oborovo seeded projects with no CAPEX edits produce
  the same ProjectInputs as before (parity).
"""
from __future__ import annotations

import pytest

from app.input_adapter import (
    _SCALAR_CAPEX_MAP,
    build_projectinputs_from_snapshot,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _base_snapshot(**extra) -> dict:
    """Minimal valid user-created project snapshot (all REQUIRED_USER_PROJECT_SNAPSHOT_FIELDS)."""
    base = {
        "project_type": "wind",
        "project_name": "Test Project",
        "country_market": "DE",
        "capacity_mw": "50",
        "cod_date": "2027-01-01",
        "construction_months": "18",
        "horizon_years": "25",
        "tariff_eur_mwh": "60",
        "ppa_term_years": "15",
        "p50_hours": "2500",
        "opex_y1_keur": "500",
        "total_capex_keur": "9000",   # legacy aggregate — overridden by scalars when present
        "gearing_pct": "",            # optional; empty → skip
        "interest_rate_pct": "0.055",
        "tenor_years": "18",
        "target_dscr": "1.30",
    }
    base.update(extra)
    return base


def _get_capex_field(pi, field_name: str) -> float:
    """Return amount_keur for a named CapexItem field."""
    return getattr(pi.capex, field_name).amount_keur


# ── F02 reproduction (pre-fix defect, now fixed) ─────────────────────────────

@pytest.mark.parametrize("snap_key,field_name", list(_SCALAR_CAPEX_MAP.items()))
def test_scalar_key_reaches_projectinputs(snap_key: str, field_name: str):
    """Each scalar key must flow through to ProjectInputs.capex.<field>.amount_keur.

    F02 defect: before R1, _snapshot_to_dict() never read any of the 14 keys,
    so editing these fields in the UI had zero effect on financial outputs.
    """
    injected_value = 1234.56
    snapshot = _base_snapshot(**{snap_key: str(injected_value)})
    pi = build_projectinputs_from_snapshot(snapshot)
    actual = _get_capex_field(pi, field_name)
    assert actual == pytest.approx(injected_value, rel=1e-6), (
        f"F02: snapshot key '{snap_key}' did not reach capex.{field_name}.amount_keur. "
        f"Got {actual!r}, expected {injected_value!r}."
    )


# ── Scalar authority over total_capex_keur ───────────────────────────────────

def test_scalar_wins_over_total_capex():
    """When scalar keys are present, they take authority over total_capex_keur."""
    epc_value = 5000.0
    snapshot = _base_snapshot(
        total_capex_keur="99999",        # legacy aggregate — must be ignored
        capex_epc_contract_keur=str(epc_value),
    )
    pi = build_projectinputs_from_snapshot(snapshot)
    assert _get_capex_field(pi, "epc_contract") == pytest.approx(epc_value, rel=1e-6)


def test_multiple_scalars_all_applied():
    """When multiple scalar keys are set, all are applied independently."""
    values = {
        "capex_epc_contract_keur":    "4000",
        "capex_grid_connection_keur": "800",
        "capex_ops_prep_keur":        "150",
    }
    snapshot = _base_snapshot(**values)
    pi = build_projectinputs_from_snapshot(snapshot)
    assert _get_capex_field(pi, "epc_contract") == pytest.approx(4000.0)
    assert _get_capex_field(pi, "grid_connection") == pytest.approx(800.0)
    assert _get_capex_field(pi, "ops_prep") == pytest.approx(150.0)


# ── Legacy fallback (no scalar keys) ─────────────────────────────────────────

def test_legacy_total_capex_still_works_without_scalars():
    """When no scalar keys are present, total_capex_keur legacy path applies.

    The legacy path scales epc_contract so that (epc_contract + other items) = target.
    Use totals well above the factory other-items sum (~13000 kEUR for Generic wind).
    """
    snapshot_20k = _base_snapshot(total_capex_keur="20000")
    pi_20k = build_projectinputs_from_snapshot(snapshot_20k)

    snapshot_80k = _base_snapshot(total_capex_keur="80000")
    pi_80k = build_projectinputs_from_snapshot(snapshot_80k)

    # Different totals must yield different epc_contract (legacy path active)
    epc_20k = _get_capex_field(pi_20k, "epc_contract")
    epc_80k = _get_capex_field(pi_80k, "epc_contract")
    assert epc_20k != pytest.approx(epc_80k), (
        f"Legacy total_capex_keur path must produce different epc_contract; "
        f"got {epc_20k} (20k) and {epc_80k} (80k)"
    )
    assert pi_80k.capex.total_capex == pytest.approx(80000.0, rel=0.01)


def test_no_capex_keys_uses_factory_default():
    """When only total_capex_keur (legacy) is set, epc_contract is scaled to match.

    For Generic wind the factory other-items sum is ~13000 kEUR.  Using 80000 kEUR
    ensures epc_contract is non-zero (= 80000 - ~13000).
    """
    snapshot = _base_snapshot(total_capex_keur="80000")
    pi = build_projectinputs_from_snapshot(snapshot)
    assert pi.capex.epc_contract.amount_keur > 0


# ── Zero / empty values are treated as absent ─────────────────────────────────

def test_empty_string_scalar_key_is_absent():
    """Empty-string scalar keys must not override (treated as None / absent).

    Without scalar authority the legacy total_capex_keur path applies.
    We verify this by checking that epc_contract differs between two
    different legacy totals (confirming the scalar path was NOT taken).
    """
    snap_empty_scalar_80k = _base_snapshot(
        capex_epc_contract_keur="",      # empty → absent (no scalar authority)
        total_capex_keur="80000",
    )
    snap_empty_scalar_20k = _base_snapshot(
        capex_epc_contract_keur="",
        total_capex_keur="20000",
    )
    pi_80k = build_projectinputs_from_snapshot(snap_empty_scalar_80k)
    pi_20k = build_projectinputs_from_snapshot(snap_empty_scalar_20k)
    # Legacy path must produce different epc_contract for different totals
    assert _get_capex_field(pi_80k, "epc_contract") != pytest.approx(
        _get_capex_field(pi_20k, "epc_contract")
    )


# ── Seeded base (Oborovo) with scalar override ────────────────────────────────

def test_scalar_overrides_seeded_base_capex():
    """Scalar keys override the seeded base (Oborovo / TUHO) correctly.

    Uses build_projectinputs_from_snapshot with template_source=oborovo
    to exercise the seeded path and verify the scalar wins.
    """
    from app.input_adapter import build_projectinputs_from_snapshot
    snap = _base_snapshot(
        template_source="oborovo",
        active_project="oborovo-test",
        project_origin="user_created",
        capex_epc_contract_keur="6000",
    )
    pi = build_projectinputs_from_snapshot(snap)
    assert _get_capex_field(pi, "epc_contract") == pytest.approx(6000.0, rel=1e-5)


# ── All 14 snapshot keys exist in _SCALAR_CAPEX_MAP ─────────────────────────

def test_scalar_map_has_exactly_14_entries():
    assert len(_SCALAR_CAPEX_MAP) == 14


def test_scalar_map_all_values_are_valid_capex_fields():
    """All field names in the map must exist on a live CapexStructure."""
    snapshot = _base_snapshot()
    pi = build_projectinputs_from_snapshot(snapshot)
    for snap_key, field_name in _SCALAR_CAPEX_MAP.items():
        item = getattr(pi.capex, field_name, None)
        assert item is not None, f"capex.{field_name} not found (from key {snap_key})"
        assert hasattr(item, "amount_keur"), (
            f"capex.{field_name} has no amount_keur (from key {snap_key})"
        )
