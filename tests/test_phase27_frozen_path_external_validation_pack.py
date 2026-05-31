"""
Phase 27: Frozen-Path External Validation Pack
Tests for validation pack completeness and non-overclaiming.
Documentation/testing only. No financial formula changes.
"""
import os
import json
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestPhase27DocExists:
    def test_phase27_validation_pack_exists(self):
        path = os.path.join(REPO_ROOT, "docs/phase27_frozen_path_external_validation_pack.md")
        assert os.path.exists(path), f"validation pack not found at {path}"

    def test_phase27_evidence_matrix_exists(self):
        path = os.path.join(REPO_ROOT, "docs/phase27_validation_evidence_matrix.md")
        assert os.path.exists(path), f"evidence matrix not found at {path}"


class TestValidatedScope:
    def test_validation_pack_contains_validated_scope(self):
        path = os.path.join(REPO_ROOT, "docs/phase27_frozen_path_external_validation_pack.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        # TUHO and Oborovo should be listed as validated
        assert "tuho" in content and "oborovo" in content, \
            "TUHO and Oborovo should both appear as validated scope"
        # Should mention frozen-template
        assert "frozen" in content, "frozen-template path should be mentioned"
        # Generic/new-project should be flagged as unvalidated
        assert "generic" in content and ("unvalidated" in content or "not validated" in content), \
            "Generic/new-project path should be flagged as unvalidated"


class TestTUHOAnchors:
    def test_validation_pack_contains_tuho_anchors(self):
        path = os.path.join(REPO_ROOT, "docs/phase27_frozen_path_external_validation_pack.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # Senior debt amount: 43,359.0 kEUR
        assert "43,359" in content, "TUHO senior debt amount 43,359.0 kEUR should be mentioned"
        # Selected senior DS parity
        assert "senior ds" in content.lower() or "senior debt service" in content.lower(), \
            "TUHO senior DS fixture parity should be mentioned"


class TestOborovoAnchors:
    def test_validation_pack_contains_oborovo_anchors(self):
        path = os.path.join(REPO_ROOT, "docs/phase27_frozen_path_external_validation_pack.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # Senior debt amount: 42,852.27 kEUR
        assert "42,852" in content, "Oborovo senior debt amount 42,852.27 kEUR should be mentioned"
        # SHL amount: 14,621.0 kEUR
        assert "14,621" in content, "Oborovo SHL amount 14,621.0 kEUR should be mentioned"
        # SHL IDC: 1,169.0 kEUR
        assert "1,169" in content, "Oborovo SHL IDC 1,169.0 kEUR should be mentioned"
        # Opening SHL approx 15,790.0 kEUR
        assert "15,790" in content, "Oborovo opening SHL approx 15,790.0 kEUR should be mentioned"
        # First valid distribution around op_idx 39 / 2050-06-30
        assert "op_idx 39" in content or "39" in content, \
            "Oborovo first valid distribution (op_idx 39) should be mentioned"


class TestKnownResiduals:
    def test_validation_pack_classifies_known_residuals(self):
        path = os.path.join(REPO_ROOT, "docs/phase27_frozen_path_external_validation_pack.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        # Oborovo op_idx 27 residual around +16.84 kEUR
        assert "16.84" in content or "16.84" in content.replace(",", ""), \
            "Oborovo op_idx 27 residual (+16.84 kEUR) should be mentioned"
        # Should classify it as within tolerance / low materiality
        assert ("tolerance" in content or "low" in content or "materiality" in content), \
            "Op_idx 27 residual should be classified as within tolerance / low materiality"
        # DSCR deviations above target as expected under frozen DS path
        assert "expected" in content and ("dscr" in content or "frozen" in content), \
            "DSCR deviations above target should be classified as expected under frozen DS path"


class TestEvidenceMatrix:
    def test_evidence_matrix_links_claims_to_tests_or_docs(self):
        path = os.path.join(REPO_ROOT, "docs/phase27_validation_evidence_matrix.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # Should reference phase23u, phase23t, phase23o, phase23l, etc.
        assert "phase23u" in content.lower(), "Evidence matrix should reference phase23u doc"
        assert "phase23t" in content.lower() or "phase23o" in content.lower() or "phase23l" in content.lower(), \
            "Evidence matrix should reference phase23 parity docs"
        # Should have table structure (markdown table)
        assert "|" in content and "---" in content, \
            "Evidence matrix should have markdown table structure"


class TestNonClaims:
    def test_non_claims_are_explicit(self):
        path = os.path.join(REPO_ROOT, "docs/phase27_frozen_path_external_validation_pack.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        claims = ["bank approval", "lender approval", "external audit", "certification", "saas-ready"]
        for claim in claims:
            # Should appear in a denial context
            idx = content.find(claim)
            if idx >= 0:
                window = content[max(0, idx-120):idx+len(claim)+20]
                # Denial: "not", "❌", or "not provided" near the claim
                is_denial = (
                    "not" in window
                    or "❌" in window
                    or "internal pilot" in window
                )
                assert is_denial, f"'{claim}' should be explicitly denied (not bank/lender/audit/saas claim)"


class TestPendingItems:
    def test_pending_items_are_explicit(self):
        path = os.path.join(REPO_ROOT, "docs/phase27_frozen_path_external_validation_pack.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        # CAPEX / C.16 / M1-M18 / IDC runtime pending
        pending_mentions = [
            ("capex" in content or "construction idc" in content),
            ("m1" in content or "m1–m18" in content or "m1-m18" in content),
            ("c.16" in content or "c16" in content),
        ]
        assert any(pending_mentions), \
            "CAPEX/C.16/M1-M18/IDC pending items should be mentioned"
        # Generic path unvalidated
        assert "generic" in content and ("unvalidated" in content or "not validated" in content), \
            "Generic path unvalidated should be explicit"
        # Sculpting solver not promoted
        assert "sculpting" not in content or "not promoted" in content or "not approved" in content, \
            "Sculpting solver should be noted as not promoted"


class TestNoRuntimeModelChanges:
    def test_no_runtime_model_files_changed_or_claimed(self):
        path = os.path.join(REPO_ROOT, "docs/phase27_frozen_path_external_validation_pack.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "no runtime formula changes" in content or "no financial formula changes" in content, \
            "validation pack should state no financial formula changes"
        assert "no model files changed" in content or "no runtime model changes" in content, \
            "validation pack should state no model files changed"


class TestJSONSummary:
    def test_json_summary_if_present_is_valid(self):
        # JSON is optional for this phase — document why
        json_path = os.path.join(REPO_ROOT, "reports/phase27_frozen_path_validation_summary.json")
        if os.path.exists(json_path):
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            assert "tuho" in data.get("projects", []) or "TUHO" in str(data.get("projects", [])), \
                "JSON projects should include TUHO"
            assert "oborovo" in data.get("projects", []) or "OBOROVO" in str(data.get("projects", [])), \
                "JSON projects should include Oborovo"
            limitations = data.get("limitations", [])
            assert any("generic" in str(lim).lower() for lim in limitations), \
                "JSON limitations should mention generic path unvalidated"
        else:
            # JSON not present — this is the expected path for Phase 27
            # The markdown evidence matrix provides the same information more readably
            pack_path = os.path.join(REPO_ROOT, "docs/phase27_frozen_path_external_validation_pack.md")
            matrix_path = os.path.join(REPO_ROOT, "docs/phase27_validation_evidence_matrix.md")
            assert os.path.exists(pack_path), "validation pack should exist (JSON skipped)"
            assert os.path.exists(matrix_path), "evidence matrix should exist (JSON skipped)"


class TestGuardrailsUnchanged:
    def test_guardrails_unchanged(self):
        shell_path = os.path.join(REPO_ROOT, "app/templates/partials/workspace_shell.html")
        with open(shell_path, encoding="utf-8") as f:
            content = f.read()
        assert "BLOCKED" in content, "G20 should remain BLOCKED"
        assert "NOT APPROVED" in content, "R99/R102 should remain NOT APPROVED"

    def test_partial_pay_sweep_not_promoted(self):
        shell_path = os.path.join(REPO_ROOT, "app/templates/partials/workspace_shell.html")
        with open(shell_path, encoding="utf-8") as f:
            content = f.read().lower()
        assert not re.search(r"partial[\s_-]pay[\s_-]sweep.*approved", content), \
            "partial_pay_sweep should not be promoted"

    def test_flat_min_dscr_sculpting_not_promoted(self):
        shell_path = os.path.join(REPO_ROOT, "app/templates/partials/workspace_shell.html")
        with open(shell_path, encoding="utf-8") as f:
            content = f.read().lower()
        assert not re.search(r"flat[\s_-]dscr.*sculpting.*approved", content), \
            "flat_dscr_sculpted should not be promoted"
        assert not re.search(r"minimum[\s_-]dscr.*sculpting.*approved", content), \
            "minimum_dscr_sculpted should not be promoted"
