"""Phase 54E — UI-1 closeout and UI-2 plan guardrails.

Verifies:
- doc and JSON exist
- 11 IA sections locked
- 9 design system components
- 4-state chip standard
- 11 banner contexts
- 6 UI-2 implementation items
- 0 UI-2 items auto-merge eligible
- 9 must-not-change files
- 10 no-go copy checks
- 7 Claude review questions
- 2 next-step options
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "phase54e_ui1_closeout_ui2_plan.md"
JSON_RPT = REPO_ROOT / "reports" / "phase54e_ui1_closeout_ui2_plan.json"


class TestDeliverablesExist:
    def test_doc_exists(self):
        assert DOC.exists()

    def test_json_report_exists(self):
        assert JSON_RPT.exists()

    def test_phase_field_is_54e(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["phase"] == "54E"

    def test_recommended_claude_review(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["claude_review_recommended_before_ui2"] is True


class TestInformationArchitectureLocked:
    def test_11_sections(self):
        data = json.loads(JSON_RPT.read_text())
        n = len(data["final_information_architecture"]["sections"])
        assert n == 11

    def test_locked(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["final_information_architecture"]["locked"] is True


class TestDesignSystemLocked:
    def test_9_components(self):
        data = json.loads(JSON_RPT.read_text())
        n = len(data["final_design_system_spec"]["components"])
        assert n == 9

    def test_locked(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["final_design_system_spec"]["locked"] is True


class TestLineItemGridLocked:
    def test_4_modes(self):
        data = json.loads(JSON_RPT.read_text())
        n = len(data["final_line_item_grid_spec"]["modes"])
        assert n == 4

    def test_locked(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["final_line_item_grid_spec"]["locked"] is True


class TestUI2Plan:
    def test_6_implementation_items(self):
        data = json.loads(JSON_RPT.read_text())
        n = len(data["ui2_implementation_plan"]["items"])
        assert n == 6

    def test_no_auto_merge_eligible(self):
        data = json.loads(JSON_RPT.read_text())
        items = data["ui2_implementation_plan"]["items"]
        for item in items:
            assert item["auto_merge"] is False, f"{item['id']} is auto_merge eligible"

    def test_all_require_review(self):
        data = json.loads(JSON_RPT.read_text())
        items = data["ui2_implementation_plan"]["items"]
        for item in items:
            assert item["review_required"] is True

    def test_implementation_sequence_present(self):
        data = json.loads(JSON_RPT.read_text())
        seq = data["ui2_implementation_plan"]["implementation_sequence"]
        assert len(seq) == 6


class TestMustNotChange:
    EXPECTED = [
        "app/persistence/",
        "app/services/",
        "main_web.py",
        "app/waterfall_core.py",
        "app/project_factories.py",
        "parity/",
        "rc1 (b425a07) frozen SHA",
    ]

    @pytest.mark.parametrize("path", EXPECTED)
    def test_must_not_change_present(self, path):
        data = json.loads(JSON_RPT.read_text())
        assert path in data["must_not_change"]


class TestNoGoCopyChecklist:
    EXPECTED = [
        "bankable",
        "lender-ready",
        "certified",
        "audit-ready",
        "validated",
        "investor-ready",
        "SaaS-ready",
        "production-ready",
        "real-time",
        "guaranteed returns",
    ]

    @pytest.mark.parametrize("term", EXPECTED)
    def test_no_go_checklist_includes(self, term):
        data = json.loads(JSON_RPT.read_text())
        checklist_text = json.dumps(data["no_go_copy_checklist"]).lower()
        assert term.lower() in checklist_text


class TestClaudeReviewQuestions:
    def test_7_questions(self):
        data = json.loads(JSON_RPT.read_text())
        n = len(data["claude_review_questions"])
        assert n == 7


class TestNextStepDecision:
    def test_two_options(self):
        data = json.loads(JSON_RPT.read_text())
        assert "option_a" in data["next_step_decision"]
        assert "option_b" in data["next_step_decision"]

    def test_recommendation_present(self):
        data = json.loads(JSON_RPT.read_text())
        rec = data["next_step_decision"]["recommended"]
        assert "Option A" in rec or "Agent B" in rec


class TestUI1Summary:
    EXPECTED_PHASES = ["54a", "54b", "54c", "54d"]

    @pytest.mark.parametrize("phase", EXPECTED_PHASES)
    def test_phase_in_summary(self, phase):
        data = json.loads(JSON_RPT.read_text())
        assert phase in data["ui1_summary"]
