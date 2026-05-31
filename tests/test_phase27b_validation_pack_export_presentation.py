"""
Phase 27B: Validation Pack Export / Presentation
Tests for stakeholder-ready validation package documents.
Documentation/presentation only. No financial formula changes.
"""
import os
import json
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestPhase27BDocExists:
    def test_phase27b_doc_exists(self):
        path = os.path.join(REPO_ROOT, "docs/phase27b_validation_pack_export_presentation.md")
        assert os.path.exists(path), f"phase27b doc not found at {path}"


class TestDocExistence:
    def test_executive_summary_exists(self):
        path = os.path.join(REPO_ROOT, "docs/validation_pack_executive_summary.md")
        assert os.path.exists(path), f"executive summary not found at {path}"

    def test_validation_pack_index_exists(self):
        path = os.path.join(REPO_ROOT, "docs/validation_pack_index.md")
        assert os.path.exists(path), f"validation pack index not found at {path}"

    def test_external_reviewer_checklist_exists(self):
        path = os.path.join(REPO_ROOT, "docs/external_reviewer_checklist.md")
        assert os.path.exists(path), f"external reviewer checklist not found at {path}"


class TestExecutiveSummaryContent:
    def test_executive_summary_contains_validated_scope(self):
        path = os.path.join(REPO_ROOT, "docs/validation_pack_executive_summary.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "tuho" in content and "oborovo" in content, \
            "TUHO and Oborovo should appear as validated scope"
        assert "frozen" in content, "frozen-template path should be mentioned"
        assert "generic" in content and ("unvalidated" in content or "not validated" in content), \
            "Generic/new-project path should be flagged as unvalidated"

    def test_executive_summary_contains_key_anchors(self):
        path = os.path.join(REPO_ROOT, "docs/validation_pack_executive_summary.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # TUHO senior debt 43,359.0 kEUR
        assert "43,359" in content, "TUHO senior debt 43,359.0 kEUR should be mentioned"
        # Oborovo senior debt 42,852.27 kEUR
        assert "42,852" in content, "Oborovo senior debt 42,852.27 kEUR should be mentioned"
        # Oborovo SHL opening approx 15,790 kEUR
        assert "15,790" in content, "Oborovo SHL opening approx 15,790 kEUR should be mentioned"
        # First valid Oborovo distribution op_idx 39 / 2050-06-30
        assert "op_idx 39" in content or "2050-06-30" in content, \
            "Oborovo first valid distribution (op_idx 39 / 2050-06-30) should be mentioned"
        # Oborovo op_idx 27 residual +16.84 kEUR within tolerance
        assert "16.84" in content or "16.84" in content.replace(",", ""), \
            "Oborovo op_idx 27 residual (+16.84 kEUR) should be mentioned"


class TestIndexLinks:
    def test_index_links_core_pack_documents(self):
        path = os.path.join(REPO_ROOT, "docs/validation_pack_index.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # Core validation pack docs
        assert "phase27_frozen_path_external_validation_pack" in content, \
            "Index should reference phase27_frozen_path_external_validation_pack.md"
        assert "phase27_validation_evidence_matrix" in content, \
            "Index should reference phase27_validation_evidence_matrix.md"
        # Pilot and operational docs
        assert "pilot_user_guide" in content, \
            "Index should reference pilot_user_guide.md"
        assert "deployment_runbook" in content, \
            "Index should reference deployment_runbook.md"
        # Phase 23 docs
        assert "phase23u" in content.lower(), "Index should reference phase23u doc"
        assert "phase23t" in content.lower() or "phase23o" in content.lower() or "phase23l" in content.lower(), \
            "Index should reference relevant Phase 23 docs"


class TestReviewerChecklist:
    def test_reviewer_checklist_contains_review_sections(self):
        path = os.path.join(REPO_ROOT, "docs/external_reviewer_checklist.md")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        sections = [
            ("tuho" in content and ("review" in content or "check" in content)),
            ("oborovo" in content and ("review" in content or "check" in content)),
            ("senior debt" in content),
            ("dscr" in content or "debt service coverage" in content),
            ("shl" in content and ("distribution" in content or "lock" in content)),
            ("residual" in content or "materiality" in content),
            ("limitation" in content or "non-claim" in content),
        ]
        assert all(sections), "Reviewer checklist should have all required review sections"


class TestNonClaims:
    def test_non_claims_are_explicit(self):
        docs = [
            os.path.join(REPO_ROOT, "docs/validation_pack_executive_summary.md"),
            os.path.join(REPO_ROOT, "docs/external_reviewer_checklist.md"),
        ]
        claims = ["bank approval", "lender approval", "credit approval", "certified audit",
                  "external audit", "saas-ready", "enterprise-ready", "multi-tenant"]
        for doc_path in docs:
            if os.path.exists(doc_path):
                with open(doc_path, encoding="utf-8") as f:
                    content = f.read().lower()
                for claim in claims:
                    idx = content.find(claim)
                    if idx >= 0:
                        window = content[max(0, idx-80):idx+len(claim)+30]
                        is_denial = (
                            "not" in window
                            or "❌" in window
                            or "internal" in window
                            or "informal" in window
                            or "non-certification" in window
                        )
                        assert is_denial, f"'{claim}' should be denied in {os.path.basename(doc_path)}"


class TestManifest:
    def test_manifest_if_present_is_valid(self):
        json_path = os.path.join(REPO_ROOT, "reports/phase27b_validation_pack_manifest.json")
        if os.path.exists(json_path):
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            assert "tuho" in str(data.get("projects", [])).lower(), \
                "Manifest should include TUHO"
            assert "oborovo" in str(data.get("projects", [])).lower(), \
                "Manifest should include Oborovo"
            limitations = str(data.get("limitations", []))
            assert "generic" in limitations.lower() or "unvalidated" in limitations.lower(), \
                "Manifest should mention generic path unvalidated"
            assert data.get("no_financial_formula_changes") or data.get("no_formula_changes"), \
                "Manifest should confirm no financial formula changes"
        else:
            # Manifest not present — Phase 27B doc explains why
            doc_path = os.path.join(REPO_ROOT, "docs/phase27b_validation_pack_export_presentation.md")
            assert os.path.exists(doc_path), "phase27b doc should exist (manifest explained there)"
            with open(doc_path, encoding="utf-8") as f:
                content = f.read().lower()
            # Doc should explain manifest was skipped
            assert "manifest" in content, "phase27b doc should discuss manifest decision"


class TestPDFDecision:
    def test_pdf_not_claimed_if_not_generated(self):
        doc_path = os.path.join(REPO_ROOT, "docs/phase27b_validation_pack_export_presentation.md")
        with open(doc_path, encoding="utf-8") as f:
            content = f.read().lower()
        # Should mention PDF as "PDF-ready markdown", not generated PDF
        if "pdf" in content:
            assert "pdf-ready" in content or "markdown" in content, \
                "PDF reference should clarify it is PDF-ready markdown, not generated PDF"
        # Should not claim a PDF was generated
        assert not re.search(r"generated\s+pdf|pdf\s+generated|auto-generated\s+pdf", content), \
            "Should not claim a PDF was auto-generated"


class TestNoRuntimeModelChanges:
    def test_no_runtime_model_files_changed_or_claimed(self):
        doc_path = os.path.join(REPO_ROOT, "docs/phase27b_validation_pack_export_presentation.md")
        with open(doc_path, encoding="utf-8") as f:
            content = f.read().lower()
        assert "no runtime formula changes" in content or "no financial formula changes" in content, \
            "phase27b doc should state no financial formula changes"
        assert "no model files changed" in content or "no runtime model changes" in content, \
            "phase27b doc should state no model files changed"


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
