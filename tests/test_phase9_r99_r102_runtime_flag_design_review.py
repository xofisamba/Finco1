"""Phase 9: R99/R102 Runtime Flag Design Review — tests.

Tests verify:
1. design doc exists
2. gate review report exists
3. state matrix exists
4. required evidence report exists
5. state matrix contains legacy/default state
6. state matrix contains DA runtime-wired staging state
7. state matrix distinguishes staging from G20 promoted state
8. G20 remains BLOCKED
9. Oborovo remains guarded
10. audit_economic_mode is not described as runtime-routable
11. runtime_economic_mode is described as staging only
12. no report claims R99/R102 promotion approved
13. required evidence includes DSCR stability
14. required evidence includes rollback behavior
15. recommended next branch is explicit
"""

import csv
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
REPORTS_DIR = REPO_ROOT / "reports"

DESIGN_DOC = DOCS_DIR / "phase9_r99_r102_runtime_flag_design_review.md"
GATE_REVIEW = REPORTS_DIR / "phase9_r99_r102_runtime_flag_gate_review.csv"
STATE_MATRIX = REPORTS_DIR / "phase9_r99_r102_runtime_flag_state_matrix.csv"
EVIDENCE_CSV = REPORTS_DIR / "phase9_r99_r102_runtime_flag_required_evidence.csv"


# ---------------------------------------------------------------------------
# 1–4. Required files exist
# ---------------------------------------------------------------------------

class TestRequiredFiles:
    def test_design_doc_exists(self):
        assert DESIGN_DOC.exists(), f"Missing: {DESIGN_DOC}"

    def test_gate_review_exists(self):
        assert GATE_REVIEW.exists(), f"Missing: {GATE_REVIEW}"

    def test_state_matrix_exists(self):
        assert STATE_MATRIX.exists(), f"Missing: {STATE_MATRIX}"

    def test_required_evidence_exists(self):
        assert EVIDENCE_CSV.exists(), f"Missing: {EVIDENCE_CSV}"


# ---------------------------------------------------------------------------
# 5–7. State matrix content
# ---------------------------------------------------------------------------

class TestStateMatrix:
    def _rows(self):
        with open(STATE_MATRIX, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_has_legacy_default_state(self):
        rows = self._rows()
        ids = {r["state_id"] for r in rows}
        assert "legacy_default" in ids, f"legacy_default not in {ids}"

    def test_has_da_runtime_wired_staging_state(self):
        rows = self._rows()
        ids = {r["state_id"] for r in rows}
        assert "da_runtime_wired_staging" in ids, f"da_runtime_wired_staging not in {ids}"

    def test_distinguishes_staging_from_g20(self):
        rows = self._rows()
        by_id = {r["state_id"]: r for r in rows}
        staging = by_id.get("da_runtime_wired_staging")
        g20 = by_id.get("future_g20_promoted_candidate")
        assert staging is not None, "da_runtime_wired_staging not found"
        assert g20 is not None, "future_g20_promoted_candidate not found"
        # Distinguish by g20_status: staging is NOT_APPLICABLE, G20 is CANDIDATE
        assert staging["g20_status"] != g20["g20_status"], (
            f"staging g20_status={staging['g20_status']} must differ from "
            f"G20 g20_status={g20['g20_status']}"
        )
        # Distinguish by r99_status: staging BLOCKED, G20 APPROVED (future)
        assert staging["r99_status"] != g20["r99_status"], (
            f"staging r99_status={staging['r99_status']} must differ from "
            f"G20 r99_status={g20['r99_status']}"
        )

    def test_g20_not_described_as_implemented(self):
        rows = self._rows()
        g20_row = next((r for r in rows if r["state_id"] == "future_g20_promoted_candidate"), None)
        assert g20_row is not None
        # Notes should indicate not implemented
        notes = g20_row.get("notes", "")
        assert "not implemented" in notes.lower() or "not approved" in notes.lower(), (
            f"G20 state must say 'not implemented' or 'not approved', got: {notes}"
        )


# ---------------------------------------------------------------------------
# 8. G20 remains BLOCKED
# ---------------------------------------------------------------------------

class TestG20Blocked:
    def test_gate_review_g20_is_blocked(self):
        with open(GATE_REVIEW, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        g20 = next((r for r in rows if r["gate_id"] == "G20"), None)
        assert g20 is not None, "G20 gate not found in gate review"
        assert g20["current_status"] == "BLOCKED", (
            f"G20 must be BLOCKED, got {g20['current_status']}"
        )


# ---------------------------------------------------------------------------
# 9. Oborovo remains guarded
# ---------------------------------------------------------------------------

class TestOborovoGuarded:
    def test_gate_review_g09_guarded(self):
        with open(GATE_REVIEW, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        g09 = next((r for r in rows if r["gate_id"] == "G09"), None)
        assert g09 is not None, "G09 gate not found"
        assert g09["current_status"] == "READY", (
            f"G09 (Oborovo guard) must be READY, got {g09['current_status']}"
        )

    def test_state_matrix_oborovo_guarded_state_exists(self):
        with open(STATE_MATRIX, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        ids = {r["state_id"] for r in rows}
        assert "oborovo_guarded" in ids, f"oborovo_guarded not in {ids}"

    def test_state_matrix_oborovo_fires_guard(self):
        with open(STATE_MATRIX, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        ob = next((r for r in rows if r["state_id"] == "oborovo_guarded"), None)
        assert ob is not None
        assert "guard" in ob["oborovo_behavior"].lower(), (
            f"Oborovo behavior must mention guard, got: {ob['oborovo_behavior']}"
        )


# ---------------------------------------------------------------------------
# 10–11. Mode contract clarity
# ---------------------------------------------------------------------------

class TestModeContract:
    def test_design_doc_audit_mode_not_routable(self):
        with open(DESIGN_DOC, encoding="utf-8") as f:
            content = f.read()
        # audit_economic_mode must be described as never routed
        assert "audit_economic_mode" in content
        # Must say it's comparison only or never routed
        assert (
            "never routed" in content.lower() or
            "comparison only" in content.lower() or
            "not routed" in content.lower()
        ), "audit_economic_mode must be described as never/not routed to runtime"

    def test_design_doc_runtime_mode_is_staging_only(self):
        with open(DESIGN_DOC, encoding="utf-8") as f:
            content = f.read()
        # runtime_economic_mode must be described as staging, not G20
        assert "runtime_economic_mode" in content
        assert (
            "pre-g20" in content.lower() or
            "pre-g20" in content.lower() or
            "staging" in content.lower()
        ), "runtime_economic_mode must be described as staging (pre-G20)"


# ---------------------------------------------------------------------------
# 12. No report claims R99/R102 promotion approved
# ---------------------------------------------------------------------------

class TestNoPromotionClaimed:
    def test_gate_review_no_promotion_approved(self):
        with open(GATE_REVIEW, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            status = r["current_status"]
            gate_id = r["gate_id"]
            if status == "APPROVED":
                assert gate_id not in ("G10", "G20", "G07", "G08"), (
                    f"Gate {gate_id} claims APPROVED — R99/R102 promotion not approved"
                )


# ---------------------------------------------------------------------------
# 13. DSCR stability evidence required
# ---------------------------------------------------------------------------

class TestDSCRStabilityEvidence:
    def test_required_evidence_includes_dscr_stability(self):
        with open(EVIDENCE_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        names = {r["evidence_name"].lower() for r in rows}
        dscr_hits = [r for r in rows if "dscr" in r["evidence_name"].lower() or "stability" in r["evidence_name"].lower()]
        assert len(dscr_hits) > 0, (
            f"Required evidence must include DSCR stability, got: {names}"
        )
        # At least one DSCR entry must be PARTIAL or AVAILABLE
        statuses = {r["current_status"] for r in dscr_hits}
        assert any(s in ("PARTIAL", "AVAILABLE", "G07_PARTIAL") for s in statuses), (
            f"DSCR evidence must be PARTIAL or AVAILABLE, got: {statuses}"
        )


# ---------------------------------------------------------------------------
# 14. Rollback evidence required
# ---------------------------------------------------------------------------

class TestRollbackEvidence:
    def test_required_evidence_includes_rollback(self):
        with open(EVIDENCE_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        rollback_rows = [r for r in rows if "rollback" in r["evidence_name"].lower()]
        assert len(rollback_rows) > 0, "Required evidence must include rollback behavior"
        # Status must be AVAILABLE
        statuses = {r["current_status"] for r in rollback_rows}
        assert statuses.issubset({"AVAILABLE", "PARTIAL"}), (
            f"Rollback evidence must be AVAILABLE or PARTIAL, got: {statuses}"
        )


# ---------------------------------------------------------------------------
# 15. Recommended next branch is explicit
# ---------------------------------------------------------------------------

class TestRecommendedNextBranch:
    def test_design_doc_recommended_next_branch_explicit(self):
        with open(DESIGN_DOC, encoding="utf-8") as f:
            content = f.read()
        assert "phase9-r99-r102-runtime-flag-readiness-fixes" in content, (
            "Design doc must include recommended next branch: phase9-r99-r102-runtime-flag-readiness-fixes"
        )

    def test_design_doc_mentions_blockers(self):
        with open(DESIGN_DOC, encoding="utf-8") as f:
            content = f.read()
        assert "BLOCKED" in content or "blocker" in content.lower(), (
            "Design doc must clearly state blockers"
        )

    def test_design_doc_explicit_conclusions(self):
        with open(DESIGN_DOC, encoding="utf-8") as f:
            content = f.read()
        required_conclusions = [
            "R99/R102 runtime promotion is NOT approved",
            "G20 remains BLOCKED",
            "pre-G20 staging",
            "Oborovo remains excluded",
        ]
        for conclusion in required_conclusions:
            assert conclusion in content, (
                f"Design doc must include: '{conclusion}'"
            )


# ---------------------------------------------------------------------------
# Gate review completeness
# ---------------------------------------------------------------------------

class TestGateReviewCompleteness:
    def test_has_required_gates(self):
        with open(GATE_REVIEW, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        gate_ids = {r["gate_id"] for r in rows}
        required_gates = {"G01", "G02", "G03", "G04", "G05", "G06", "G09", "G10", "G20"}
        missing = required_gates - gate_ids
        assert not missing, f"Gate review missing required gates: {missing}"

    def test_g07_g08_not_ready(self):
        with open(GATE_REVIEW, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        by_id = {r["gate_id"]: r for r in rows}
        for gid in ("G07", "G08"):
            assert gid in by_id, f"{gid} not in gate review"
            assert by_id[gid]["current_status"] != "READY", (
                f"{gid} must NOT be READY before R99/R102 implementation"
            )