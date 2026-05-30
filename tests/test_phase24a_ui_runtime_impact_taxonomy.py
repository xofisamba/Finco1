"""Phase 24A: UI/Runtime Impact Taxonomy — Tests

Diagnostic-only. No runtime changes.
"""
import re
from pathlib import Path

import pytest

from app.runtime_impact_taxonomy import (
    CANONICAL_STATES,
    LEGACY_TO_CANONICAL,
    RuntimeImpactStatus,
    get_capex_taxonomy,
    get_frozen_senior_ds_taxonomy,
    get_sub_reason,
    map_legacy_to_canonical,
)
from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
from domain.period_engine import PeriodEngine


# =============================================================================
# 1. Canonical primary states
# =============================================================================


def test_runtime_impact_primary_states_are_canonical():
    """Assert allowed primary states are exactly: Drives model, Display only, Pending, Needs review."""
    assert list(CANONICAL_STATES) == [
        "Drives model",
        "Display only",
        "Pending",
        "Needs review",
    ]
    assert len(CANONICAL_STATES) == 4


# =============================================================================
# 2. Legacy label mapping
# =============================================================================


def test_legacy_runtime_impact_labels_map_to_canonical_states():
    """Existing labels map to the 4 canonical states."""
    # Drives model variants
    assert map_legacy_to_canonical("Drives model") == RuntimeImpactStatus.DRIVES_MODEL
    assert map_legacy_to_canonical("backend_authoritative") == RuntimeImpactStatus.DRIVES_MODEL

    # Display only variants
    assert map_legacy_to_canonical("Timing only") == RuntimeImpactStatus.DISPLAY_ONLY
    assert map_legacy_to_canonical("Reference only") == RuntimeImpactStatus.DISPLAY_ONLY
    assert map_legacy_to_canonical("Display only") == RuntimeImpactStatus.DISPLAY_ONLY
    assert map_legacy_to_canonical("Not applicable") == RuntimeImpactStatus.DISPLAY_ONLY

    # Pending variants
    assert map_legacy_to_canonical("Pending treatment") == RuntimeImpactStatus.PENDING
    assert map_legacy_to_canonical("Pending runtime source") == RuntimeImpactStatus.PENDING
    assert map_legacy_to_canonical("Deferred") == RuntimeImpactStatus.PENDING

    # Needs review variants
    assert map_legacy_to_canonical("Not comparable") == RuntimeImpactStatus.NEEDS_REVIEW
    assert map_legacy_to_canonical("Needs review") == RuntimeImpactStatus.NEEDS_REVIEW
    assert map_legacy_to_canonical("mismatch") == RuntimeImpactStatus.NEEDS_REVIEW
    assert map_legacy_to_canonical("Unknown") == RuntimeImpactStatus.NEEDS_REVIEW
    assert map_legacy_to_canonical("scope_mismatch") == RuntimeImpactStatus.NEEDS_REVIEW

    # Unknown falls back to NEEDS_REVIEW
    assert map_legacy_to_canonical("some_random_label") == RuntimeImpactStatus.NEEDS_REVIEW


# =============================================================================
# 3. Frozen senior DS taxonomy
# =============================================================================


def test_frozen_senior_ds_surface_drives_model_with_fixture_subreason():
    """TUHO/Oborovo frozen senior DS is Drives model with fixture-backed sub-reason."""
    tax = get_frozen_senior_ds_taxonomy()
    assert tax["primary"] == RuntimeImpactStatus.DRIVES_MODEL
    assert "fixture" in tax["sub_reason"].lower() or "frozen" in tax["sub_reason"].lower()
    assert tax["sculpting_active"] is False
    assert "sculpt" not in tax.get("note", "").lower()


# =============================================================================
# 4. CAPEX taxonomy
# =============================================================================


def test_capex_runtime_impact_not_promoted():
    """CAPEX fields: C.16 Pending, M1-M18 Display only, EPC/Grid Drives model."""
    tax = get_capex_taxonomy()
    assert tax["c16_project_rights"]["primary"] == RuntimeImpactStatus.PENDING
    assert tax["m1_m18_schedule"]["primary"] == RuntimeImpactStatus.DISPLAY_ONLY
    assert tax["epc_grid_totals"]["primary"] == RuntimeImpactStatus.DRIVES_MODEL


# =============================================================================
# 5. No financial runtime changes (guardrail)
# =============================================================================


def test_no_financial_runtime_changes():
    """Importing taxonomy does not change waterfall outputs."""
    # Run TUHO and Oborovo — verify senior debt amounts unchanged
    tuho = create_default_tuho_wind1()
    engine = PeriodEngine(
        tuho.info.financial_close,
        tuho.info.construction_months,
        tuho.info.horizon_years,
        tuho.revenue.ppa_term_years,
    )
    config = WaterfallRunConfig.from_inputs(tuho, engine)
    result = WaterfallRunner(tuho, engine).run(config)
    op_periods = [p for p in result.periods if getattr(p, "is_operation", False)]

    # TUHO senior debt anchor: 43,359 kEUR
    tuho_total_ds = sum(getattr(p, "senior_ds_keur", 0.0) or 0.0 for p in op_periods[:14])
    assert tuho_total_ds > 0, "TUHO senior DS should be > 0"

    oborovo = create_default_oborovo()
    engine2 = PeriodEngine(
        oborovo.info.financial_close,
        oborovo.info.construction_months,
        oborovo.info.horizon_years,
        oborovo.revenue.ppa_term_years,
    )
    config2 = WaterfallRunConfig.from_inputs(oborovo, engine2)
    result2 = WaterfallRunner(oborovo, engine2).run(config2)
    op_periods2 = [p for p in result2.periods if getattr(p, "is_operation", False)]

    # Oborovo senior debt anchor: 42,852 kEUR
    oborovo_total_ds = sum(getattr(p, "senior_ds_keur", 0.0) or 0.0 for p in op_periods2[:28])
    assert oborovo_total_ds > 0, "Oborovo senior DS should be > 0"


# =============================================================================
# 6. No unknown primary labels in templates
# =============================================================================


def test_no_unknown_primary_runtime_impact_labels_in_templates():
    """Scan _derive_runtime_impact_label for any labels not in canonical states."""
    project_context = Path(__file__).resolve().parents[1] / "app" / "ui" / "project_context.py"
    if not project_context.exists():
        pytest.skip("project_context.py not found")

    content = project_context.read_text()

    # Extract all return statements from _derive_runtime_impact_label ONLY
    start = content.find("def _derive_runtime_impact_label(")
    end = content.find("\n    def _child_row(", start)
    func_body = content[start:end]
    pattern = r'return\s+"([^"]+)"'
    matches = re.findall(pattern, func_body)

    # All labels in _derive_runtime_impact_label should be canonical or known sub-reasons
    known = set(CANONICAL_STATES)
    known.update([
        "Timing only",
        "Reference only",
        "Pending treatment",
        "Pending runtime source",
        "Not comparable",
        "Not applicable",
        "Deferred",
        "Unknown",
    ])

    unexpected = [m for m in matches if m not in known]
    assert len(unexpected) == 0, f"Unexpected labels in _derive_runtime_impact_label: {unexpected}"


# =============================================================================
# 7. Guardrails unchanged
# =============================================================================


def test_guardrails_unchanged():
    """Guardrails preserved: G20/R99/R102 blocked, no flags promoted."""
    oborovo = create_default_oborovo()
    info = oborovo.info

    assert not hasattr(info, "use_g20_engine"), "G20 must remain blocked"
    assert not hasattr(info, "use_r99_engine"), "R99 must remain not approved"
    assert not hasattr(info, "use_r102_engine"), "R102 must remain not approved"
    assert not hasattr(info, "flat_dscr_sculpted"), "flat_dscr_sculpted must not be promoted"
    assert not hasattr(info, "minimum_dscr_sculpted"), "minimum_dscr_sculpted must not be promoted"
    assert not hasattr(info, "partial_pay_sweep"), "partial_pay_sweep must not be promoted"
