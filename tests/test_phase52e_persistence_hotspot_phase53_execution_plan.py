"""Phase 52E — Persistence hotspot and Phase 53 execution plan structural tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "phase52e_persistence_hotspot_phase53_execution_plan.md"
JSON_REPORT = REPO_ROOT / "reports" / "phase52e_persistence_hotspot_phase53_execution_plan.json"


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
    def test_doc_mentions_phase_52e(self):
        assert "Phase 52E" in _read(DOC)


class TestPhase53RefactorOrder:
    def test_phase53_refactor_order_present(self, data):
        assert "phase53_refactor_order" in data
        order = data["phase53_refactor_order"]
        assert len(order) == 6
        groups = [o["group"] for o in order]
        assert groups == ["F", "D", "E", "A-reads", "C", "B"]

    def test_group_F_first(self, data):
        assert data["phase53_refactor_order"][0]["group"] == "F"

    def test_group_B_last(self, data):
        assert data["phase53_refactor_order"][-1]["group"] == "B"

    def test_total_function_count_at_least_27(self, data):
        total = sum(o["function_count"] for o in data["phase53_refactor_order"])
        assert total >= 27


class TestPhase53GroupPlans:
    def test_all_six_groups_planned(self, data):
        plans = data["phase53_group_plans"]
        for g in ("F_helpers", "D_runs", "E_exports_audit", "A_projects_reads", "C_workspace_state", "B_scenarios"):
            assert g in plans

    def test_F_helpers_zero_required_pins(self, data):
        assert data["phase53_group_plans"]["F_helpers"]["required_pins"] == 0

    def test_D_runs_zero_required_pins(self, data):
        assert data["phase53_group_plans"]["D_runs"]["required_pins"] == 0

    def test_E_exports_audit_zero_required_pins(self, data):
        assert data["phase53_group_plans"]["E_exports_audit"]["required_pins"] == 0

    def test_C_workspace_state_requires_pin(self, data):
        assert data["phase53_group_plans"]["C_workspace_state"]["required_pins"] >= 1

    def test_B_scenarios_requires_5_pins(self, data):
        assert data["phase53_group_plans"]["B_scenarios"]["required_pins"] == 5

    def test_compatibility_facade_for_all_groups(self, data):
        for plan in data["phase53_group_plans"].values():
            assert plan["compatibility_facade"] is True

    def test_single_owner_required_for_C_and_B(self, data):
        assert data["phase53_group_plans"]["C_workspace_state"]["single_owner_required"] is True
        assert data["phase53_group_plans"]["B_scenarios"]["single_owner_required"] is True

    def test_F_helpers_no_single_owner(self, data):
        assert data["phase53_group_plans"]["F_helpers"]["single_owner_required"] is False


class TestAutoMergePolicy:
    def test_auto_merge_policy_present(self, data):
        assert "auto_merge_policy" in data
        policy = data["auto_merge_policy"]
        for k in ("allowed", "review_required", "sign_off_required"):
            assert k in policy

    def test_allowed_includes_F_D_E(self, data):
        assert "Group F" in data["auto_merge_policy"]["allowed"]
        assert "Group D" in data["auto_merge_policy"]["allowed"]
        assert "Group E" in data["auto_merge_policy"]["allowed"]

    def test_sign_off_required_includes_B(self, data):
        assert "Group B" in data["auto_merge_policy"]["sign_off_required"]


class TestParallelization:
    def test_do_not_parallelize_rules_present(self, data):
        assert "do_not_parallelize_rules" in data
        assert len(data["do_not_parallelize_rules"]) >= 4

    def test_safe_parallelization_rules_present(self, data):
        assert "safe_parallelization_rules" in data
        assert len(data["safe_parallelization_rules"]) >= 4

    def test_do_not_parallelize_C_and_B(self, data):
        rules = " ".join(data["do_not_parallelize_rules"])
        assert "Group C" in rules
        assert "Group B" in rules


class TestStopConditions:
    def test_stop_conditions_present(self, data):
        assert "stop_conditions" in data
        assert len(data["stop_conditions"]) >= 8

    def test_stop_includes_no_schema_change(self, data):
        conds = " ".join(data["stop_conditions"])
        assert "schema" in conds.lower()

    def test_stop_includes_no_replay_metadata_change(self, data):
        conds = " ".join(data["stop_conditions"])
        assert "replay_metadata" in conds


class TestPRSequence:
    def test_pr_sequence_present(self, data):
        assert "phase53_pr_sequence_proposal" in data
        seq = data["phase53_pr_sequence_proposal"]
        assert len(seq) >= 8

    def test_pr_sequence_total_new_tests_at_least_7(self, data):
        seq = data["phase53_pr_sequence_proposal"]
        total = sum(p["new_tests"] for p in seq)
        assert total >= 7


class TestSecondOrderHotspotMap:
    def test_function_hotspots_present(self, data):
        assert "second_order_hotspot_map" in data
        assert "function_hotspots" in data["second_order_hotspot_map"]
        assert len(data["second_order_hotspot_map"]["function_hotspots"]) == 10

    def test_caller_hotspots_present(self, data):
        assert "caller_hotspots" in data["second_order_hotspot_map"]
        assert len(data["second_order_hotspot_map"]["caller_hotspots"]) == 10

    def test_write_risk_hotspots_present(self, data):
        assert "write_risk_hotspots" in data["second_order_hotspot_map"]
        assert len(data["second_order_hotspot_map"]["write_risk_hotspots"]) == 7


class TestRecommendedNextStep:
    def test_recommended_next_step(self, data):
        assert data.get("recommended_next_step") == "52F guardrail specifications/tests"


class TestNoProductionCodeChanged:
    def test_no_production_code_changed(self, data):
        assert data.get("type") == "docs/report/test only"
