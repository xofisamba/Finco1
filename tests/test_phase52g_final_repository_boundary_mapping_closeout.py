"""Phase 52G — Final closeout structural tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "phase52g_final_repository_boundary_mapping_closeout.md"
JSON_REPORT = REPO_ROOT / "reports" / "phase52g_final_repository_boundary_mapping_closeout.json"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def data() -> Dict[str, Any]:
    return _read_json(JSON_REPORT)


class TestDocsAndJsonExist:
    def test_doc_exists(self):
        assert DOC.exists()
    def test_json_exists(self):
        assert JSON_REPORT.exists()
    def test_doc_mentions_phase_52g(self):
        assert "Phase 52G" in _read(DOC)


class TestPhase52PRs:
    def test_phase52_prs_count(self, data):
        assert len(data["phase52_prs"]) == 6
        phases = [p["phase"] for p in data["phase52_prs"]]
        assert phases == ["52A","52B","52C","52D","52E","52F"]


class TestFinalPersistenceInventory:
    def test_persistence_files_count(self, data):
        assert len(data["final_persistence_inventory"]["files"]) == 5

    def test_total_loc(self, data):
        assert data["final_persistence_inventory"]["total_loc"] == 2953

    def test_repository_py_function_counts(self, data):
        c = data["final_persistence_inventory"]["repository_py_function_counts"]
        assert c["total"] == 61
        assert c["write"] == 22
        assert c["read"] == 16
        assert c["mixed"] == 5
        assert c["helper"] == 18

    def test_repository_py_domain_counts(self, data):
        d = data["final_persistence_inventory"]["repository_py_domain_counts"]
        assert d["total"] == 61


class TestFinalSideEffectMap:
    def test_high_risk_writes_count(self, data):
        assert len(data["final_side_effect_map_summary"]["high_risk_writes"]) == 7

    def test_must_pin_items_count(self, data):
        c = data["final_side_effect_map_summary"]["must_pin_items_count"]
        assert c["P0"] == 7
        assert c["P1"] == 5
        assert c["total"] == 12

    def test_metadata_columns_count(self, data):
        assert len(data["final_side_effect_map_summary"]["metadata_columns"]) >= 4


class TestFinalCallerGraph:
    def test_top_4_caller_files(self, data):
        assert len(data["final_caller_graph_summary"]["top_4_caller_files"]) == 4

    def test_main_web_in_top(self, data):
        files = {f["file"] for f in data["final_caller_graph_summary"]["top_4_caller_files"]}
        assert "main_web.py" in files


class TestPhase53Order:
    def test_phase53_order_count(self, data):
        assert len(data["phase53_order"]) == 7

    def test_F_first(self, data):
        assert data["phase53_order"][0]["group"] == "F"

    def test_B_last(self, data):
        assert data["phase53_order"][-1]["group"] == "B"


class TestPhase53AutomationPolicy:
    def test_auto_merge_groups(self, data):
        assert set(data["phase53_automation_policy"]["auto_merge_groups"]) == {"F","D","E","A-reads"}

    def test_sign_off_groups(self, data):
        assert "B" in data["phase53_automation_policy"]["sign_off_required_groups"]

    def test_hard_stop_conditions_count(self, data):
        assert len(data["phase53_automation_policy"]["hard_stop_conditions"]) >= 9


class TestNoGoClaims:
    def test_no_go_claims_present(self, data):
        assert "no_go_claims" in data
        assert len(data["no_go_claims"]) >= 5

    def test_G20_blocked(self, data):
        claims = " ".join(data["no_go_claims"])
        assert "G20" in claims and "BLOCKED" in claims


class TestRc1:
    def test_rc1_frozen_sha(self, data):
        assert data["rc1_status"]["frozen_sha"] == "b425a0708719eaa5e1d922b1008e5609758e0ad4"
        assert data["rc1_status"]["in_merge_diff"] is False


class TestReadinessDelta:
    def test_files_mapped(self, data):
        assert data["readiness_delta"]["persistence_files_mapped"]["post"] == 5

    def test_functions_inventoried(self, data):
        assert data["readiness_delta"]["functions_inventoried"]["post"] == 89

    def test_behavioral_guardrails(self, data):
        assert data["readiness_delta"]["behavioral_guardrails"]["post"] == 31


class TestClaudeReviewRecommendation:
    def test_recommendation_present(self, data):
        assert "claude_review_recommendation" in data
        assert data["claude_review_recommendation"]["proceed_directly"] is True


class TestRecommendedNextStep:
    def test_recommended_next_step(self, data):
        assert data.get("recommended_next_step") == "Phase 53A — Extract Group F (helpers)"


class TestKnownFailures:
    def test_known_failures_documented(self, data):
        assert "known_failures" in data
        names = {f["name"] for f in data["known_failures"]}
        assert "tests/test_persistence.py" in names
        assert "tests/test_repository.py" in names
