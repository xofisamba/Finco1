"""Phase 54J — UI-2 readiness closeout and prompt pack guardrails.

Verifies:
- doc and JSON exist
- 54F-54I summary present
- Final UI-2 boundaries locked
- 6 missing context keys
- First implementation prompt for UI-2.1 complete
- Second prompt preview for UI-2.2
- Hard gates for UI-2 runtime PRs
- Visual review checklist
- Recommendation: wait for user/Claude review
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "phase54j_ui2_readiness_closeout_prompt_pack.md"
JSON_RPT = REPO_ROOT / "reports" / "phase54j_ui2_readiness_closeout_prompt_pack.json"


class TestDeliverablesExist:
    def test_doc_exists(self):
        assert DOC.exists()

    def test_json_report_exists(self):
        assert JSON_RPT.exists()

    def test_phase_field_is_54j(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["phase"] == "54J"


class TestUI2ReadinessSummary:
    EXPECTED_PHASES = ["54F", "54G", "54H", "54I"]

    @pytest.mark.parametrize("phase", EXPECTED_PHASES)
    def test_phase_in_summary(self, phase):
        data = json.loads(JSON_RPT.read_text())
        assert phase in data["ui2_readiness_summary"]


class TestFinalContextMap:
    EXPECTED_MISSING = [
        "validation_summary", "is_factory_template",
        "inputs_changed_since_run", "runtime_summary.run_id"
    ]

    @pytest.mark.parametrize("key", EXPECTED_MISSING)
    def test_missing_key_in_map(self, key):
        data = json.loads(JSON_RPT.read_text())
        items = data["final_context_map"]["items"]
        keys = [i["key"] for i in items]
        assert key in keys

    def test_locked(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["final_context_map"]["locked"] is True


class TestFirstImplementationPrompt:
    def test_id_is_ui21(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["first_implementation_prompt"]["id"] == "UI-2.1"

    def test_auto_merge_no(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["first_implementation_prompt"]["auto_merge"] == "NO"

    def test_files_allowed_to_create_present(self):
        data = json.loads(JSON_RPT.read_text())
        files = data["first_implementation_prompt"]["files_allowed_to_create"]
        assert any("_state_banner.html" in f for f in files)

    def test_no_go_copy_checks_present(self):
        data = json.loads(JSON_RPT.read_text())
        checks = data["first_implementation_prompt"]["no_go_copy_checks"]
        assert len(checks) >= 4
        # Real-time must be mentioned
        assert any("real-time" in c for c in checks)

    def test_required_tests_present(self):
        data = json.loads(JSON_RPT.read_text())
        tests = data["first_implementation_prompt"]["required_tests"]
        assert len(tests) >= 4

    def test_rollback_plan_present(self):
        data = json.loads(JSON_RPT.read_text())
        plan = data["first_implementation_prompt"]["rollback_plan"]
        assert len(plan) >= 3


class TestSecondPromptPreview:
    def test_id_is_ui22(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["second_prompt_preview"]["id"] == "UI-2.2"

    def test_auto_merge_no(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["second_prompt_preview"]["auto_merge"] == "NO"

    def test_stackable_with_ui21(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["second_prompt_preview"]["stackable_with_ui21"] is True


class TestHardGates:
    EXPECTED_SUBSTRINGS = [
        "51F", "52F", "53I", "rc1",
        "no backend files modified", "no service files modified",
        "user has reviewed", "user has signed off"
    ]

    @pytest.mark.parametrize("gate", EXPECTED_SUBSTRINGS)
    def test_gate_in_hard_gates(self, gate):
        data = json.loads(JSON_RPT.read_text())
        gates = " ".join(data["hard_gates"]["per_ui2_pr"])
        assert gate in gates, f"'{gate}' not in hard gates"


class TestVisualReviewChecklist:
    EXPECTED = [
        "HTML variants render",
        "no forbidden UI claims",
        "54C locked spec",
        "54C spec",
        "additive and clearly marked",
        "no existing classes/helpers removed",
        "rollback plan feasible"
    ]

    @pytest.mark.parametrize("item", EXPECTED)
    def test_item_in_checklist(self, item):
        data = json.loads(JSON_RPT.read_text())
        checklist = " ".join(data["visual_review_checklist"])
        assert item in checklist or item.lower() in checklist.lower()


class TestRecommendation:
    def test_decision_is_wait(self):
        data = json.loads(JSON_RPT.read_text())
        assert "WAIT" in data["recommendation"]["decision"]

    def test_rationale_present(self):
        data = json.loads(JSON_RPT.read_text())
        assert len(data["recommendation"]["rationale"]) >= 3

    def test_alternative_present(self):
        data = json.loads(JSON_RPT.read_text())
        assert "alternative" in data["recommendation"]


class TestStackabilityRecommendation:
    def test_ui21_ui22_stackable(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["stackability_recommendation"]["ui21_and_ui22_stackable_as_drafts"] is True

    def test_only_one_ready_at_a_time(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["stackability_recommendation"]["only_one_ready_at_a_time"] is True
