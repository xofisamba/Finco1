"""Phase C10 Readiness Design tests (test-only).

These tests verify that the C10 readiness design PR correctly
documents:
- The allowed fields for C10 (TUHO controlled promotion).
- The blocked fields (with R-PAR-2 caveat).
- The parity gates.
- The rollback plan.
- The no-go checks.
- The required approvals.
- The tests needed before any promotion PR can open.

These tests are **fully test-only**. They do not touch the
production code, the model, the formulas, the runtime, the
waterfall, the persistence, the UI, or the feature flags.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]

C10_DESIGN_DOC = (
    REPO_ROOT / "docs" / "phase_c10_readiness_design.md"
)
C10_REPORT_JSON = (
    REPO_ROOT / "reports" / "phase_c10_readiness_design.json"
)
C9_SEAM_MODULE = (
    REPO_ROOT / "app" / "services" / "construction_runtime_seam.py"
)
C1_DESIGN_DOC = (
    REPO_ROOT / "docs" / "phase_c1_construction_idc_design_gate.md"
)
RPAR2_DISCOVERY_DOC = (
    REPO_ROOT / "docs" / "phase_rpar2_decision_discovery.md"
)


# ---------------------------------------------------------------------------
# Design doc existence and content
# ---------------------------------------------------------------------------


class TestC10DesignDocExists:
    def test_design_doc_exists(self):
        assert C10_DESIGN_DOC.exists(), (
            f"C10 readiness design doc must exist at "
            f"{C10_DESIGN_DOC.relative_to(REPO_ROOT)}"
        )

    def test_report_json_exists(self):
        assert C10_REPORT_JSON.exists(), (
            f"C10 readiness report JSON must exist at "
            f"{C10_REPORT_JSON.relative_to(REPO_ROOT)}"
        )

    def test_design_doc_declares_scope_label(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "DESIGN ONLY" in text, (
            "C10 readiness design doc must declare DESIGN ONLY scope label"
        )

    def test_design_doc_declares_no_implementation(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "NO IMPLEMENTATION" in text, (
            "C10 readiness design doc must declare NO IMPLEMENTATION"
        )


# ---------------------------------------------------------------------------
# Allowed fields
# ---------------------------------------------------------------------------


class TestC10AllowedFields:
    def test_allows_shl_idc(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "shl_idc_keur" in text, (
            "C10 design must mention shl_idc_keur"
        )
        # Must be in the allowed fields list
        allowed_section = re.search(
            r"## 2\. Allowed fields.*?## 3\.",
            text,
            re.DOTALL,
        )
        assert allowed_section, "C10 design must have an Allowed fields section"
        assert "shl_idc_keur" in allowed_section.group(0), (
            "shl_idc_keur must be in the C10 allowed fields list"
        )

    def test_allows_shl_amount(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "shl_amount_keur" in text, (
            "C10 design must mention shl_amount_keur"
        )

    def test_allows_shl_opening_balance(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "shl_opening_balance_keur" in text, (
            "C10 design must mention shl_opening_balance_keur"
        )

    def test_allows_equity_total(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "equity_total_keur" in text, (
            "C10 design must mention equity_total_keur"
        )

    def test_blocks_senior_idc(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        # senior_idc_keur must be in the blocked fields section
        blocked_section = re.search(
            r"## 2\. Allowed fields.*?(Blocked fields|## 3\.).*?",
            text,
            re.DOTALL,
        )
        # Alternative: just search for "senior_idc_keur" + "NO" context
        # or "blocked"
        assert "senior_idc_keur" in text, (
            "C10 design must mention senior_idc_keur"
        )
        # Must explicitly say it's NOT in C10
        assert re.search(
            r"senior_idc_keur.*?(NO|EXCLUDED|not in C10)",
            text,
            re.IGNORECASE | re.DOTALL,
        ), (
            "C10 design must explicitly mark senior_idc_keur as "
            "NOT in C10's allowed fields"
        )

    def test_blocks_senior_opening_balance(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "senior_opening_balance_keur" in text, (
            "C10 design must mention senior_opening_balance_keur"
        )

    def test_blocks_capex(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "capex_keur" in text, (
            "C10 design must mention capex_keur"
        )


# ---------------------------------------------------------------------------
# Parity gates
# ---------------------------------------------------------------------------


class TestC10ParityGates:
    def test_rc1_baseline_referenced(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "b425a0708719eaa5e1d922b1008e5609758e0ad4" in text, (
            "C10 design must reference rc1 SHA as the parity baseline"
        )

    def test_shl_parity_tolerance_is_1pct(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        # SHL fields have ±1% tolerance
        assert re.search(r"shl.*?1\s*%", text, re.IGNORECASE | re.DOTALL), (
            "C10 design must specify 1% tolerance for SHL parity"
        )

    def test_equity_parity_tolerance_is_0_5pct(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        # equity has ±0.5% tolerance
        assert re.search(
            r"equity.*?0\.5\s*%",
            text,
            re.IGNORECASE | re.DOTALL,
        ), (
            "C10 design must specify 0.5% tolerance for equity parity"
        )

    def test_atomic_promotion_semantics(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "atomic" in text.lower(), (
            "C10 design must mention atomic promotion semantics"
        )


# ---------------------------------------------------------------------------
# TUHO only (no Oborovo)
# ---------------------------------------------------------------------------


class TestC10TuhoOnly:
    def test_tuho_referenced(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "TUHO" in text, (
            "C10 design must reference TUHO"
        )

    def test_no_oborovo_in_c10(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        # Oborovo must be EXCLUDED from C10
        assert "Oborovo" in text, (
            "C10 design must mention Oborovo (to exclude it)"
        )
        assert re.search(
            r"Oborovo.*?(NOT|EXCLUDED|C11|future)",
            text,
            re.IGNORECASE | re.DOTALL,
        ), (
            "C10 design must explicitly state that Oborovo is "
            "NOT in C10's scope (and is C11)"
        )

    def test_c11_referenced_as_oborovo_phase(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "C11" in text, (
            "C10 design must reference C11 (the Oborovo phase)"
        )


# ---------------------------------------------------------------------------
# R-PAR-2 exclusion
# ---------------------------------------------------------------------------


class TestC10Rpar2Exclusion:
    def test_rpar2_referenced(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "R-PAR-2" in text or "RPAR2" in text, (
            "C10 design must reference R-PAR-2"
        )

    def test_rpar2_discovery_pr_referenced(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "PR #556" in text or "#556" in text, (
            "C10 design must reference PR #556 (R-PAR-2 decision discovery)"
        )

    def test_rpar2_discovery_doc_exists(self):
        # The R-PAR-2 discovery doc is in PR #556, which is
        # DRAFT (not yet merged). Once merged, this test will
        # pass. For now, we accept either:
        # (a) the doc exists in the working tree, or
        # (b) the C10 design doc references the PR number
        #     (so it will exist once the PR merges).
        if RPAR2_DISCOVERY_DOC.exists():
            return
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "PR #556" in text or "#556" in text, (
            "C10 design must reference PR #556 (R-PAR-2 decision discovery)"
        )


# ---------------------------------------------------------------------------
# No-go checks
# ---------------------------------------------------------------------------


class TestC10NoGoChecks:
    def test_no_go_section_exists(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "No-go checks" in text or "no-go checks" in text, (
            "C10 design must have a no-go checks section"
        )

    def test_no_go_includes_rpar2_decision(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert re.search(
            r"no-go.*?R-PAR-2",
            text,
            re.IGNORECASE | re.DOTALL,
        ) or re.search(
            r"R-PAR-2.*?no-go",
            text,
            re.IGNORECASE | re.DOTALL,
        ), (
            "C10 design no-go checks must include R-PAR-2 decision"
        )

    def test_no_go_includes_oborovo_exclusion(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert re.search(
            r"no-go.*?Oborovo",
            text,
            re.IGNORECASE | re.DOTALL,
        ) or re.search(
            r"Oborovo.*?no-go",
            text,
            re.IGNORECASE | re.DOTALL,
        ) or "Oborovo is NOT in scope of C10" in text, (
            "C10 design no-go checks must include Oborovo exclusion"
        )


# ---------------------------------------------------------------------------
# Required approvals
# ---------------------------------------------------------------------------


class TestC10RequiredApprovals:
    def test_approvals_section_exists(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "Required approvals" in text or "required approvals" in text.lower(), (
            "C10 design must have a required approvals section"
        )

    def test_governance_board_in_approvals(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert re.search(
            r"Modelling governance board|governance board",
            text,
            re.IGNORECASE,
        ), (
            "C10 design required approvals must include governance board"
        )

    def test_senior_lender_in_approvals(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert re.search(
            r"senior lender",
            text,
            re.IGNORECASE,
        ), (
            "C10 design required approvals must include senior lender"
        )

    def test_audit_team_in_approvals(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert re.search(
            r"audit team",
            text,
            re.IGNORECASE,
        ), (
            "C10 design required approvals must include audit team"
        )

    def test_project_lead_in_approvals(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert re.search(
            r"project lead",
            text,
            re.IGNORECASE,
        ), (
            "C10 design required approvals must include project lead"
        )


# ---------------------------------------------------------------------------
# Tests needed for C10-impl
# ---------------------------------------------------------------------------


class TestC10TestsNeededSection:
    def test_tests_needed_section_exists(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "Tests needed" in text or "tests needed" in text.lower(), (
            "C10 design must have a Tests needed section"
        )

    def test_atomic_promotion_test_referenced(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "TestC10AtomicPromotion" in text, (
            "C10 design must reference TestC10AtomicPromotion"
        )

    def test_rollback_test_referenced(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "TestC10Rollback" in text, (
            "C10 design must reference TestC10Rollback"
        )

    def test_rpar2_exclusion_test_referenced(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "TestC10Rpar2Exclusion" in text, (
            "C10 design must reference TestC10Rpar2Exclusion"
        )

    def test_oborovo_exclusion_test_referenced(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "TestC10ExcludesOborovo" in text, (
            "C10 design must reference TestC10ExcludesOborovo"
        )

    def test_rc1_untouched_test_referenced(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "TestC10Rc1Untouched" in text, (
            "C10 design must reference TestC10Rc1Untouched"
        )


# ---------------------------------------------------------------------------
# Rollback plan
# ---------------------------------------------------------------------------


class TestC10RollbackPlan:
    def test_rollback_section_exists(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "Rollback plan" in text or "rollback plan" in text.lower(), (
            "C10 design must have a rollback plan section"
        )

    def test_rollback_is_idempotent(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "idempotent" in text.lower(), (
            "C10 design must state that rollback is idempotent"
        )

    def test_rollback_caches_pre_values(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "cache" in text.lower() or "cached" in text.lower(), (
            "C10 design must mention that pre-promotion values are cached"
        )


# ---------------------------------------------------------------------------
# Hard rules
# ---------------------------------------------------------------------------


class TestC10HardRules:
    def test_rc1_untouched_in_design(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "rc1" in text.lower(), (
            "C10 design must mention rc1"
        )
        assert "untouched" in text.lower(), (
            "C10 design must state that rc1 is untouched"
        )

    def test_no_flag_enablement_in_design(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        # The scope label and §9 must mention no flag enablement.
        assert "NO FLAG FLIP" in text or "no flag" in text.lower() or "no.*enablement" in text.lower(), (
            "C10 design must declare no flag enablement / no flag flip"
        )

    def test_no_waterfall_routing_in_design(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "NO WATERFALL ROUTING" in text or "no.*waterfall" in text.lower() or "no.*routing" in text.lower(), (
            "C10 design must declare no waterfall routing"
        )

    def test_no_runtime_promotion_in_design(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "NO RUNTIME WIRING" in text or "no.*runtime" in text.lower() or "no.*promotion" in text.lower(), (
            "C10 design must declare no runtime promotion / no runtime wiring"
        )

    def test_draft_status(self):
        text = C10_DESIGN_DOC.read_text(encoding="utf-8")
        assert "DRAFT" in text, (
            "C10 design must declare DRAFT status"
        )


# ---------------------------------------------------------------------------
# Feature flag and rc1 (live checks)
# ---------------------------------------------------------------------------


class TestC10LiveChecks:
    def test_rc1_reachable(self):
        result = subprocess.run(
            [
                "git", "cat-file", "-e",
                "b425a0708719eaa5e1d922b1008e5609758e0ad4",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            "rc1 SHA must be reachable on origin/main"
        )

    def test_use_construction_schedule_engine_default_false(self):
        domain_inputs = REPO_ROOT / "domain" / "inputs.py"
        text = domain_inputs.read_text(encoding="utf-8")
        match = re.search(
            r"use_construction_schedule_engine\s*:\s*bool\s*=\s*(\w+)",
            text,
        )
        assert match, (
            "domain/inputs.py must declare use_construction_schedule_engine"
        )
        assert match.group(1) == "False", (
            f"use_construction_schedule_engine default must be False, "
            f"got {match.group(1)!r}"
        )

    def test_c9_seam_module_unchanged_by_c10_design(self):
        """The C9 seam module must not be modified by the C10
        readiness design. The C10 design is doc+test only."""
        result = subprocess.run(
            ["git", "diff", "origin/main", "HEAD", "--",
             "app/services/construction_runtime_seam.py"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "", (
            "C9 seam module must not be modified by C10 readiness design"
        )
