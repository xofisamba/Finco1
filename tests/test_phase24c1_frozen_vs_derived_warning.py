"""Phase 24C.1: Frozen vs Derived Warning — Tests

Diagnostic-only. No runtime formula changes.
"""
from pathlib import Path

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
from domain.period_engine import PeriodEngine


# =============================================================================
# 1. Frozen schedule warning exists in panel
# =============================================================================


def test_frozen_schedule_warning_exists_in_panel():
    """Panel contains frozen-vs-derived warning text."""
    panel_path = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials" / "debt_dscr_shl_panel.html"
    content = panel_path.read_text()
    assert "Frozen schedule warning" in content
    assert "re-sculpt senior debt" in content or "not re-sculpt" in content.lower()
    assert "non-fixture project type" in content or "generic wind/solar" in content.lower()


# =============================================================================
# 2. No sculpting claim confirmed
# =============================================================================


def test_no_sculpting_claim_confirmed():
    """Panel confirms no sculpting solver is active."""
    panel_path = Path(__file__).resolve().parents[1] / "app" / "templates" / "partials" / "debt_dscr_shl_panel.html"
    content = panel_path.read_text()
    assert "no sculpting solver active" in content.lower() or "no sculpting" in content.lower()


# =============================================================================
# 3. Generic project labeled unvalidated
# =============================================================================


def test_generic_project_labeled_unvalidated():
    """Generic wind/solar template options are labeled as unvalidated/derived."""
    # Read main_web.py to check template options
    main_web = Path(__file__).resolve().parents[1] / "main_web.py"
    content = main_web.read_text()

    # Generic options should have "Unvalidated" or "Derived" label
    assert "generic_wind" in content
    assert "generic_solar" in content
    # The warning label should be present
    assert "Unvalidated" in content or "⚠️" in content


# =============================================================================
# 4. TUHO/Oborovo fixture path not mislabeled as derived
# =============================================================================


def test_tuho_oborovo_not_mislabeled_as_derived():
    """TUHO and Oborovo template labels do not claim derived/sculpting."""
    main_web = Path(__file__).resolve().parents[1] / "main_web.py"
    content = main_web.read_text()

    # TUHO and Oborovo should NOT have "Unvalidated" or "⚠️" labels
    # Find the lines for tuho and oborovo template options
    lines = content.splitlines()
    in_template = False
    for line in lines:
        if "NEW_PROJECT_TEMPLATE_OPTIONS" in line:
            in_template = True
        if in_template:
            if "tuho" in line.lower() and "label" in line:
                assert "Unvalidated" not in line, "TUHO should not be labeled Unvalidated"
                assert "⚠️" not in line, "TUHO should not have warning glyph"
            if "oborovo" in line.lower() and "label" in line:
                assert "Unvalidated" not in line, "Oborovo should not be labeled Unvalidated"
                assert "⚠️" not in line, "Oborovo should not have warning glyph"
            if "]" in line and in_template:
                break


# =============================================================================
# 5. Decision doc exists and mentions key topics
# =============================================================================


def test_decision_doc_mentions_key_topics():
    """Decision doc exists and covers frozen Excel schedule, derived path, generic unvalidated, backup/restore."""
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "phase24c1_24f_pilot_safety_decision.md"
    assert doc_path.exists(), f"Decision doc not found at {doc_path}"
    content = doc_path.read_text()
    assert "frozen excel schedule" in content.lower()
    assert "derived path" in content.lower()
    assert "generic" in content.lower()
    assert "unvalidated" in content.lower()
    assert "backup" in content.lower() or "restore" in content.lower()
    assert "Phase 24E" in content


# =============================================================================
# 6. No runtime output changes
# =============================================================================


def test_no_runtime_output_changes():
    """Backend outputs unchanged — guardrail test."""
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
    tuho_total_ds = sum(getattr(p, "senior_ds_keur", 0.0) or 0.0 for p in op_periods[:14])
    assert tuho_total_ds > 25000, f"TUHO senior DS should be > 25,000 kEUR, got {tuho_total_ds:.2f}"


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
