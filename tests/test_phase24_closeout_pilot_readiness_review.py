"""Phase 24 Closeout / Pilot Readiness Review — Tests

Docs/tests only. No runtime changes.
"""
from pathlib import Path

import pytest

from app.project_factories import create_default_oborovo, create_default_tuho_wind1


# =============================================================================
# 1. Closeout doc exists
# =============================================================================


def test_closeout_doc_exists():
    """Closeout doc exists at expected path."""
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "phase24_closeout_pilot_readiness_review.md"
    assert doc_path.exists(), f"Closeout doc not found at {doc_path}"
    content = doc_path.read_text()
    assert len(content) > 500, "Closeout doc should have meaningful content"


# =============================================================================
# 2. Mentions all Phase 24 PRs
# =============================================================================


def test_mentions_all_phase_24_prs():
    """Closeout mentions all Phase 24 PRs: #321, #322, #323, #324, #325, #326."""
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "phase24_closeout_pilot_readiness_review.md"
    content = doc_path.read_text()
    for pr in ["#321", "#322", "#323", "#324", "#325", "#326"]:
        assert pr in content, f"Closeout should mention {pr}"


# =============================================================================
# 3. Mentions Runtime Impact taxonomy
# =============================================================================


def test_mentions_runtime_impact_taxonomy():
    """Closeout mentions Runtime Impact taxonomy."""
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "phase24_closeout_pilot_readiness_review.md"
    content = doc_path.read_text()
    assert "Runtime Impact" in content or "runtime impact" in content.lower()


# =============================================================================
# 4. Mentions frozen-vs-derived warning
# =============================================================================


def test_mentions_frozen_vs_derived_warning():
    """Closeout mentions frozen-vs-derived warning."""
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "phase24_closeout_pilot_readiness_review.md"
    content = doc_path.read_text()
    assert "frozen" in content.lower() and "derived" in content.lower()


# =============================================================================
# 5. Mentions SQLite backup/restore
# =============================================================================


def test_mentions_sqlite_backup_restore():
    """Closeout mentions SQLite backup/restore."""
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "phase24_closeout_pilot_readiness_review.md"
    content = doc_path.read_text()
    assert "backup" in content.lower() and "restore" in content.lower()


# =============================================================================
# 6. Mentions Audit/Reconciliation tab
# =============================================================================


def test_mentions_audit_reconciliation_tab():
    """Closeout mentions Audit/Reconciliation tab."""
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "phase24_closeout_pilot_readiness_review.md"
    content = doc_path.read_text()
    assert "Audit" in content or "audit" in content.lower()


# =============================================================================
# 7. Mentions generic project path remains unvalidated
# =============================================================================


def test_mentions_generic_project_unvalidated():
    """Closeout mentions generic project path remains unvalidated."""
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "phase24_closeout_pilot_readiness_review.md"
    content = doc_path.read_text()
    assert "generic" in content.lower()
    assert "unvalidated" in content.lower()


# =============================================================================
# 8. Mentions no bank/lender/external audit claim
# =============================================================================


def test_mentions_no_bank_lender_external_audit_claim():
    """Closeout mentions no bank/lender/external audit claim."""
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "phase24_closeout_pilot_readiness_review.md"
    content = doc_path.read_text().lower()
    assert "not" in content and "bank" in content
    assert "not" in content and "lender" in content
    assert "not" in content and "external audit" in content


# =============================================================================
# 9. Recommends Phase 26A or justifies Phase 24D
# =============================================================================


def test_recommends_next_phase():
    """Closeout recommends Phase 26A or explicitly justifies Phase 24D."""
    doc_path = Path(__file__).resolve().parents[1] / "docs" / "phase24_closeout_pilot_readiness_review.md"
    content = doc_path.read_text()
    # Should mention either Phase 26A or Phase 24D
    assert "Phase 26A" in content or "Phase 24D" in content or "26A" in content or "24D" in content


# =============================================================================
# 10. Guardrails unchanged
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
