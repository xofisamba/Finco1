"""
Phase 29C: Post-Phase 29 Validation Closeout
Tests for post-Phase 29 closeout, Claude review prep, and readiness matrix.
Documentation only. No financial formula changes. No runtime model changes.
"""
import os
import sys
import json

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


class TestPhase29CDocExists:
    def test_phase29c_closeout_doc_exists(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_post_validation_closeout.md")
        assert os.path.exists(path), f"phase29c closeout doc not found at {path}"

    def test_phase29c_claude_review_prompt_exists(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_claude_review_prompt.md")
        assert os.path.exists(path), f"phase29c Claude review prompt not found at {path}"

    def test_phase29c_readiness_matrix_exists(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_readiness_matrix.md")
        assert os.path.exists(path), f"phase29c readiness matrix not found at {path}"


class TestCloseoutListsCompletedPhases:
    def test_closeout_lists_completed_phases(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_post_validation_closeout.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        required = ["Phase 27", "Phase 28", "Phase 29A", "Phase 29B"]
        for phase in required:
            assert phase in content, f"closeout should mention {phase}"


class TestCloseoutDistinguishesValidatedDiagnosticUnvalidated:
    def test_validated_tuho_oborovo(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_post_validation_closeout.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "validated" in content and "tuho" in content, "closeout should state TUHO is validated"
        assert "validated" in content and "oborovo" in content, "closeout should state Oborovo is validated"

    def test_diagnostic_capex_sensitivity(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_post_validation_closeout.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "diagnostic" in content and "capex" in content, \
            "closeout should classify CAPEX sensitivity as diagnostic"

    def test_unvalidated_generic_path(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_post_validation_closeout.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "unvalidated" in content and ("generic" in content or "solar" in content or "wind" in content), \
            "closeout should classify generic path as unvalidated"


class TestClaudePromptRequestsScoringAndCompletion:
    def test_claude_prompt_requests_1_10_scores(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_claude_review_prompt.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "score" in content and ("1–10" in content or "1-10" in content or "1 to 10" in content), \
            "Claude prompt should request 1-10 scores"

    def test_claude_prompt_requests_completion_pct(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_claude_review_prompt.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "trusted pilot" in content and "%" in content, \
            "Claude prompt should request trusted pilot completion %"
        assert "paid pilot" in content and "%" in content, \
            "Claude prompt should request paid pilot completion %"

    def test_claude_prompt_compares_vs_phase24_26a(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_claude_review_prompt.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "phase 24" in content or "phase24" in content, \
            "Claude prompt should reference Phase 24/26A comparison"


class TestClaudePromptMentionsKeyScopeBoundaries:
    def test_frozen_validated_path_mentioned(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_claude_review_prompt.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "tuho" in content or "frozen" in content, \
            "Claude prompt should mention frozen validated path"

    def test_diagnostic_sensitivities_mentioned(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_claude_review_prompt.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "diagnostic" in content or "capex" in content, \
            "Claude prompt should mention diagnostic sensitivities"

    def test_generic_unvalidated_mentioned(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_claude_review_prompt.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "generic" in content and ("unvalidated" in content or "not validated" in content), \
            "Claude prompt should mention generic unvalidated path"

    def test_construction_idc_not_wired_mentioned(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_claude_review_prompt.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "idc" in content or "construction" in content, \
            "Claude prompt should mention construction IDC not wired"

    def test_live_sculpting_not_promoted_mentioned(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_claude_review_prompt.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "sculpt" in content or "live" in content or "not promoted" in content, \
            "Claude prompt should mention live sculpting not promoted"


class TestReadinessMatrixContainsRequiredRows:
    def test_tuho_frozen_row(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_readiness_matrix.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "tuho" in content, "matrix should include TUHO frozen model row"

    def test_oborovo_row(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_readiness_matrix.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "oborovo" in content, "matrix should include Oborovo row"

    def test_generic_path_row(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_readiness_matrix.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "generic" in content, "matrix should include generic path row"

    def test_co2_row(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_readiness_matrix.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "co2" in content, "matrix should include CO2 row"

    def test_capex_sensitivity_row(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_readiness_matrix.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "capex" in content or "sensitivity" in content, \
            "matrix should include CAPEX sensitivity row"

    def test_debt_dscr_shl_row(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_readiness_matrix.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "debt" in content or "dscr" in content or "shl" in content, \
            "matrix should include debt/DSCR/SHL row"

    def test_validation_pack_row(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_readiness_matrix.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "validation" in content, "matrix should include validation pack row"

    def test_backup_row(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_readiness_matrix.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "backup" in content, "matrix should include backup row"

    def test_observability_row(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_readiness_matrix.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "observ" in content or "readyz" in content, \
            "matrix should include observability row"

    def test_auth_row(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_readiness_matrix.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "auth" in content or "single-user" in content, \
            "matrix should include auth row"

    def test_persistence_row(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_readiness_matrix.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "persistence" in content or "scenario" in content or "version" in content, \
            "matrix should include persistence row"

    def test_idc_row(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_readiness_matrix.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "idc" in content or "construction" in content, \
            "matrix should include construction IDC row"

    def test_sculpting_row(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_readiness_matrix.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "sculpt" in content or "live" in content, \
            "matrix should include live sculpting row"

    def test_rbac_sso_row(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_readiness_matrix.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "rbac" in content or "sso" in content or "multi-user" in content, \
            "matrix should include RBAC/SSO row"

    def test_enterprise_row(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_readiness_matrix.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "enterprise" in content, "matrix should include enterprise row"


class TestNonClaimsAreExplicit:
    def test_no_bank_lender_audit_saas_claims(self):
        docs = [
            os.path.join(REPO_ROOT, "docs/phase29c_post_validation_closeout.md"),
            os.path.join(REPO_ROOT, "docs/phase29c_claude_review_prompt.md"),
            os.path.join(REPO_ROOT, "docs/phase29c_readiness_matrix.md"),
        ]
        claims = ["bank approval", "lender approval", "bankable", "lender-ready",
                  "certification", "saas-ready"]
        for path in docs:
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    content = f.read()
                for claim in claims:
                    idx = content.lower().find(claim.lower())
                    if idx >= 0:
                        window = content[max(0, idx-100):idx+len(claim)+60]
                        is_denial = (
                            "no " in window.lower()
                            or "not " in window.lower()
                            or "❌" in window
                            or "unvalidated" in window.lower()
                            or "not validated" in window.lower()
                            or "diagnostic" in window.lower()
                            or "not bank" in window.lower()
                            or "not enterprise" in window.lower()
                        )
                        assert is_denial, f"'{claim}' should be denied in {os.path.basename(path)}"


class TestRecommendedNextPhasesPresent:
    def test_next_phases_recommended(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_post_validation_closeout.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "phase 30" in content or "phase30" in content, \
            "closeout should recommend next phases"
        assert "not to do" in content or "not to build" in content or "should not" in content, \
            "closeout should explain what not to do next"


class TestManifestIfPresentIsValid:
    def test_manifest_if_present_valid(self):
        json_path = os.path.join(REPO_ROOT, "reports/phase29c_post_validation_closeout_manifest.json")
        if os.path.exists(json_path):
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            assert "main_sha" in data or "sha" in data, "manifest should include SHA"
            assert "validated" in str(data).lower() or "tuho" in str(data).lower(), \
                "manifest should mention validated projects"
            assert "unvalidated" in str(data).lower() or "generic" in str(data).lower(), \
                "manifest should mention unvalidated areas"
        else:
            # Absent — closeout explains why
            closeout_path = os.path.join(REPO_ROOT, "docs/phase29c_post_validation_closeout.md")
            with open(closeout_path, encoding="utf-8") as f:
                content = f.read().lower()
            assert "manifest" in content or "json" in content, \
                "closeout should discuss manifest/JSON decision"


class TestNoRuntimeModelFilesChangedOrClaimed:
    def test_no_financial_formula_changes_stated(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_post_validation_closeout.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert ("no financial formula" in content or "no formula" in content or
                "no model changes" in content or "not changed" in content), \
            "closeout should state no financial formula changes"


class TestGuardrailsUnchanged:
    def test_guardrails_unchanged(self):
        import re
        shell_path = os.path.join(REPO_ROOT, "app/templates/partials/workspace_shell.html")
        with open(shell_path, encoding="utf-8") as f:
            content = f.read()
        assert "BLOCKED" in content, "G20 should remain BLOCKED"
        assert "NOT APPROVED" in content, "R99/R102 should remain NOT APPROVED"
        assert not re.search(r"partial[\s_-]pay[\s_-]sweep.*approved", content), \
            "partial_pay_sweep should not be promoted"
        assert not re.search(r"flat[\s_-]dscr.*sculpting.*approved", content), \
            "flat_dscr_sculpted should not be promoted"


class TestPhaseCoverageComplete:
    def test_phase27_phase28_phase29_all_present(self):
        path = os.path.join(REPO_ROOT, "docs/phase29c_post_validation_closeout.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        phases = ["Phase 27", "Phase 28", "Phase 29A", "Phase 29B", "Phase 29C"]
        for phase in phases:
            assert phase in content, f"closeout should mention {phase}"