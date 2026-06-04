"""Phase 54H — UI no-go copy scanner spec guardrails.

Verifies:
- doc and JSON exist
- 15 forbidden terms documented (13 from 54C + 2 close variants)
- Current state of templates audited
- Allowed contexts (negation + qualification) defined
- Examples of allowed vs blocked copy
- Recommendation to defer scanner implementation
- How UI-2 PRs use the scanner (current + future)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "phase54h_ui_no_go_copy_scanner.md"
JSON_RPT = REPO_ROOT / "reports" / "phase54h_ui_no_go_copy_scanner.json"


class TestDeliverablesExist:
    def test_doc_exists(self):
        assert DOC.exists()

    def test_json_report_exists(self):
        assert JSON_RPT.exists()

    def test_phase_field_is_54h(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["phase"] == "54H"

    def test_recommended_next_step_is_54i(self):
        data = json.loads(JSON_RPT.read_text())
        assert "54I" in data["recommended_next_step"]


class TestForbiddenTerms:
    EXPECTED_TERMS = [
        "bankable", "lender-ready", "certified", "audit-ready",
        "validated", "investor-ready", "SaaS-ready", "production-ready",
        "external validation", "customer reference",
        "investment advice", "guaranteed returns"
    ]

    @pytest.mark.parametrize("term", EXPECTED_TERMS)
    def test_term_in_list(self, term):
        data = json.loads(JSON_RPT.read_text())
        assert term in data["forbidden_terms"]


class TestCurrentState:
    def test_validated_in_templates(self):
        data = json.loads(JSON_RPT.read_text())
        # validated should appear 7+ times in templates (in safe context)
        assert data["current_state_in_templates"]["validated"] >= 7

    def test_bankable_zero(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["current_state_in_templates"]["bankable"] == 0

    def test_lender_ready_zero(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["current_state_in_templates"]["lender-ready"] == 0

    def test_audit_ready_zero(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["current_state_in_templates"]["audit-ready"] == 0

    def test_saas_ready_safe_negation(self):
        data = json.loads(JSON_RPT.read_text())
        safe = data["safe_uses_audit"]["SaaS-ready"]
        assert any("Not SaaS" in s for s in safe)


class TestAllowedContexts:
    def test_validated_allowed_phrases_present(self):
        data = json.loads(JSON_RPT.read_text())
        phrases = data["allowed_contexts"]["validated"]["allowed_phrases"]
        for p in ["validated frozen-template parity", "Validated templates", "UNVALIDATED"]:
            assert p in phrases

    def test_validated_negation_patterns(self):
        data = json.loads(JSON_RPT.read_text())
        patterns = data["allowed_contexts"]["validated"]["negation_patterns"]
        for p in ["not", "un", "separately"]:
            assert p in patterns

    def test_validated_qualification_patterns(self):
        data = json.loads(JSON_RPT.read_text())
        patterns = data["allowed_contexts"]["validated"]["qualification_patterns"]
        for p in ["frozen-template", "pilot", "parity", "Excel", "TUHO", "Oborovo"]:
            assert p in patterns


class TestExamples:
    def test_at_least_5_allowed_examples(self):
        data = json.loads(JSON_RPT.read_text())
        assert len(data["examples"]["allowed"]) >= 5

    def test_at_least_5_blocked_examples(self):
        data = json.loads(JSON_RPT.read_text())
        assert len(data["examples"]["blocked"]) >= 5

    def test_blocked_examples_are_forbidden(self):
        data = json.loads(JSON_RPT.read_text())
        blocked_text = " ".join(data["examples"]["blocked"]).lower()
        for term in ["bankable", "lender-ready", "production-ready", "guaranteed returns"]:
            assert term in blocked_text


class TestRecommendation:
    def test_defer_recommendation(self):
        data = json.loads(JSON_RPT.read_text())
        rec = data["recommendation"]
        assert rec["decision"].startswith("DEFER")

    def test_rationale_present(self):
        data = json.loads(JSON_RPT.read_text())
        rationale = data["recommendation"]["rationale"]
        assert len(rationale) >= 3

    def test_when_to_implement_present(self):
        data = json.loads(JSON_RPT.read_text())
        assert "when_to_implement" in data["recommendation"]
        assert len(data["recommendation"]["when_to_implement"]) >= 1


class TestGuardrailStatus:
    def test_implemented_false(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["implemented_guardrail"] is False

    def test_deferred_guardrail_present(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["deferred_guardrail"]["phase"] is not None


class TestHowUI2UsesScanner:
    def test_now_strategy_present(self):
        data = json.loads(JSON_RPT.read_text())
        assert "now" in data["how_ui2_prs_use_scanner"]

    def test_future_strategy_present(self):
        data = json.loads(JSON_RPT.read_text())
        assert "future" in data["how_ui2_prs_use_scanner"]
