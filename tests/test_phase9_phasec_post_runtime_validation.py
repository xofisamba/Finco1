"""Phase 9: Phase C Post-Runtime Validation tests.

Tests that all Phase C runtime integrations on main are correctly documented,
gates are appropriately marked, and R99/R102 promotion remains BLOCKED.

No runtime behavior is changed in this branch.
"""

import csv
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
REPORTS_DIR = REPO_ROOT / "reports"
GATE_REFRESH = REPORTS_DIR / "phase9_phasec_gate_refresh.csv"
VALIDATION_MATRIX = REPORTS_DIR / "phase9_phasec_runtime_validation_matrix.csv"
VALIDATION_RESULTS = REPORTS_DIR / "phase9_phasec_runtime_validation_results.csv"
POST_RUNTIME_DOC = DOCS_DIR / "phase9_phasec_post_runtime_validation.md"


# ---------------------------------------------------------------------------
# 1. All required reports exist
# ---------------------------------------------------------------------------

class TestReportsExist:
    def test_gate_refresh_exists(self):
        assert GATE_REFRESH.exists(), f"Missing: {GATE_REFRESH}"

    def test_validation_matrix_exists(self):
        assert VALIDATION_MATRIX.exists(), f"Missing: {VALIDATION_MATRIX}"

    def test_validation_results_exists(self):
        assert VALIDATION_RESULTS.exists(), f"Missing: {VALIDATION_RESULTS}"

    def test_post_runtime_doc_exists(self):
        assert POST_RUNTIME_DOC.exists(), f"Missing: {POST_RUNTIME_DOC}"


# ---------------------------------------------------------------------------
# 2. Required columns in reports
# ---------------------------------------------------------------------------

class TestReportColumns:
    def test_gate_refresh_columns(self):
        with open(GATE_REFRESH, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        required = ["gate_id", "gate_name", "previous_status", "current_status",
                    "evidence", "blocker", "required_next_action", "owner_module", "notes"]
        assert list(rows[0].keys()) == required

    def test_validation_matrix_columns(self):
        with open(VALIDATION_MATRIX, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        required = ["case_id", "project", "da_runtime_wiring", "shl_r102_input",
                    "sponsor_handoff_input", "tax_bridge", "expected_runtime_change",
                    "expected_status", "notes"]
        assert list(rows[0].keys()) == required

    def test_validation_results_columns(self):
        with open(VALIDATION_RESULTS, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        required = ["case_id", "project", "status", "distribution_total_keur",
                    "sponsor_distribution_total_keur", "shl_r102_applied_keur",
                    "baseline_delta_keur", "r99_r102_status", "oborovo_guard_status",
                    "hidden_coupling_detected", "notes"]
        assert list(rows[0].keys()) == required


# ---------------------------------------------------------------------------
# 3. Gate refresh marks integrations READY
# ---------------------------------------------------------------------------

class TestGateRefresh:
    def _gates(self):
        with open(GATE_REFRESH, newline="", encoding="utf-8") as f:
            return {r["gate_id"]: r for r in csv.DictReader(f)}

    def test_g01_shl_r102_is_ready(self):
        g = self._gates()["G01"]
        assert g["current_status"] == "READY", f"G01 status: {g['current_status']}"

    def test_g02_sponsor_handoff_is_ready(self):
        g = self._gates()["G02"]
        assert g["current_status"] == "READY", f"G02 status: {g['current_status']}"

    def test_g03_da_runtime_wiring_is_ready(self):
        g = self._gates()["G03"]
        assert g["current_status"] == "READY", f"G03 status: {g['current_status']}"

    def test_g04_taxbridge_dualrun_is_ready(self):
        g = self._gates()["G04"]
        assert g["current_status"] == "READY", f"G04 status: {g['current_status']}"

    def test_g05_da_dualrun_economic_is_ready(self):
        g = self._gates()["G05"]
        assert g["current_status"] == "READY", f"G05 status: {g['current_status']}"

    def test_g06_phase_c_combo_is_ready(self):
        g = self._gates()["G06"]
        assert g["current_status"] == "READY", f"G06 status: {g['current_status']}"

    def test_g07_r99_r102_promotion_is_blocked(self):
        g = self._gates()["G07"]
        assert g["current_status"] == "BLOCKED", f"G07 status: {g['current_status']}"

    def test_g08_oborovo_promotion_is_blocked(self):
        g = self._gates()["G08"]
        assert g["current_status"] == "BLOCKED", f"G08 status: {g['current_status']}"


# ---------------------------------------------------------------------------
# 4. G20 / R99-R102 promotion remains BLOCKED everywhere
# ---------------------------------------------------------------------------

class TestR99R102Blocked:
    def test_no_gate_claims_r99_r102_promotion_approved(self):
        with open(GATE_REFRESH, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            assert r["current_status"] != "APPROVED" or r["gate_id"] not in ("G07", "G08"), (
                f"Gate {r['gate_id']} claims R99/R102 promotion approved — must remain BLOCKED"
            )

    def test_validation_results_show_r99_r102_blocked(self):
        with open(VALIDATION_RESULTS, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            if r["project"] == "TUHO-WIND-1":
                assert r["r99_r102_status"] in ("BLOCKED", "BLOCKED_GOVERNED"), (
                    f"{r['case_id']}: R99/R102 must be BLOCKED, got {r['r99_r102_status']}"
                )


# ---------------------------------------------------------------------------
# 5. Default behavior / no drift cases present
# ---------------------------------------------------------------------------

class TestNoBaselineDrift:
    def test_tuho_baseline_default_is_present(self):
        with open(VALIDATION_RESULTS, newline="", encoding="utf-8") as f:
            rows = {r["case_id"]: r for r in csv.DictReader(f)}
        r = rows["tuho_baseline_default"]
        assert r["status"] == "PASS"
        assert abs(float(r["distribution_total_keur"]) - 326_165) < 1000, (
            f"Expected ~326,165 kEUR, got {r['distribution_total_keur']}"
        )
        assert abs(float(r["baseline_delta_keur"])) < 0.01, "baseline should have zero delta"

    def test_oborovo_baseline_default_is_present(self):
        with open(VALIDATION_RESULTS, newline="", encoding="utf-8") as f:
            rows = {r["case_id"]: r for r in csv.DictReader(f)}
        r = rows["oborovo_baseline_default"]
        assert r["status"] == "PASS"
        assert abs(float(r["distribution_total_keur"]) - 181_019) < 1000, (
            f"Expected ~181,019 kEUR, got {r['distribution_total_keur']}"
        )

    def test_tuho_da_wiring_delta_approx_expected(self):
        with open(VALIDATION_RESULTS, newline="", encoding="utf-8") as f:
            rows = {r["case_id"]: r for r in csv.DictReader(f)}
        r = rows["tuho_da_wiring_only"]
        assert r["status"] == "PASS"
        assert -44_000 < float(r["baseline_delta_keur"]) < -40_000, (
            f"Expected delta ~-41,613 kEUR, got {r['baseline_delta_keur']}"
        )
        assert abs(float(r["distribution_total_keur"]) - 284_552) < 500, (
            f"Expected ~284,552 kEUR, got {r['distribution_total_keur']}"
        )


# ---------------------------------------------------------------------------
# 6. Oborovo guard cases are present
# ---------------------------------------------------------------------------

class TestOborovoGuard:
    def test_oborovo_da_wiring_guard_fires(self):
        with open(VALIDATION_RESULTS, newline="", encoding="utf-8") as f:
            rows = {r["case_id"]: r for r in csv.DictReader(f)}
        r = rows["oborovo_da_wiring_guard"]
        assert r["status"] == "PASS"
        assert r["oborovo_guard_status"] == "GUARD_FIRED", (
            f"Oborovo guard should fire, got {r['oborovo_guard_status']}"
        )

    def test_oborovo_distribution_unchanged_when_guard_fires(self):
        with open(VALIDATION_RESULTS, newline="", encoding="utf-8") as f:
            rows = {r["case_id"]: r for r in csv.DictReader(f)}
        base = rows["oborovo_baseline_default"]
        wired = rows["oborovo_da_wiring_guard"]
        assert abs(float(base["distribution_total_keur"]) -
                   float(wired["distribution_total_keur"])) < 0.01, (
            "Oborovo distribution must not change when guard fires"
        )


# ---------------------------------------------------------------------------
# 7. No report claims R99/R102 promotion approved
# ---------------------------------------------------------------------------

class TestNoR99R102PromotionClaimed:
    def test_gate_refresh_no_approved_status_for_r99_r102(self):
        with open(GATE_REFRESH, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            if "r99" in r["gate_name"].lower() or "g20" in r["gate_name"].lower():
                assert r["current_status"] != "APPROVED", (
                    f"Gate {r['gate_id']} ({r['gate_name']}) claims APPROVED — R99/R102 must remain BLOCKED"
                )

    def test_doc_mentions_r99_r102_blocked(self):
        with open(POST_RUNTIME_DOC, encoding="utf-8") as f:
            content = f.read()
        assert "BLOCKED" in content
        assert "R99" in content or "R99/R102" in content, (
            "Doc must mention R99/R102 status"
        )


# ---------------------------------------------------------------------------
# 8. Recommended next branch is correct
# ---------------------------------------------------------------------------

class TestNextBranchRecommendation:
    def test_doc_recommends_correct_next_branch(self):
        with open(POST_RUNTIME_DOC, encoding="utf-8") as f:
            content = f.read()
        assert "phase9-r99-r102-runtime-flag-design-review" in content, (
            "Recommended next branch should be phase9-r99-r102-runtime-flag-design-review"
        )