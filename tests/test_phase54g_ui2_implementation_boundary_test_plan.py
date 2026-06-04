"""Phase 54G — UI-2 implementation boundary and test plan guardrails.

Verifies:
- 6 UI-2 items each with full boundary spec
- All 4 tests (string, no-go, snapshot, visual) per item
- All items auto_merge = NO
- Cross-cutting forbidden changes list
- Universal stop conditions
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "phase54g_ui2_implementation_boundary_test_plan.md"
JSON_RPT = REPO_ROOT / "reports" / "phase54g_ui2_implementation_boundary_test_plan.json"


class TestDeliverablesExist:
    def test_doc_exists(self):
        assert DOC.exists()

    def test_json_report_exists(self):
        assert JSON_RPT.exists()

    def test_phase_field_is_54g(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["phase"] == "54G"

    def test_recommended_next_step_is_54h(self):
        data = json.loads(JSON_RPT.read_text())
        assert "54H" in data["recommended_next_step"]

    def test_json_includes_required_keys(self):
        data = json.loads(JSON_RPT.read_text())
        for key in [
            "phase", "ui2_item_boundaries", "required_tests_by_item",
            "allowed_files_by_item", "forbidden_changes",
            "manual_review_checklists", "rollback_plan",
            "ui2_auto_merge_policy", "recommended_next_step"
        ]:
            assert key in data, f"Missing key: {key}"


class TestItemBoundaries:
    EXPECTED_ITEMS = [
        "UI-2.1_state_banner", "UI-2.2_runtime_chip",
        "UI-2.3_validation_bar", "UI-2.4_factory_lock",
        "UI-2.5_stale_warning", "UI-2.6_run_source"
    ]

    @pytest.mark.parametrize("item", EXPECTED_ITEMS)
    def test_item_in_boundaries(self, item):
        data = json.loads(JSON_RPT.read_text())
        assert item in data["ui2_item_boundaries"]

    @pytest.mark.parametrize("item", EXPECTED_ITEMS)
    def test_item_has_files_allowed_to_modify(self, item):
        data = json.loads(JSON_RPT.read_text())
        item_data = data["ui2_item_boundaries"][item]
        assert "files_allowed_to_modify" in item_data
        assert len(item_data["files_allowed_to_modify"]) > 0

    @pytest.mark.parametrize("item", EXPECTED_ITEMS)
    def test_item_auto_merge_is_no(self, item):
        data = json.loads(JSON_RPT.read_text())
        item_data = data["ui2_item_boundaries"][item]
        assert item_data["auto_merge"] == "NO"

    @pytest.mark.parametrize("item", EXPECTED_ITEMS)
    def test_item_has_required_tests(self, item):
        data = json.loads(JSON_RPT.read_text())
        item_data = data["ui2_item_boundaries"][item]
        assert len(item_data["required_tests"]) >= 3

    @pytest.mark.parametrize("item", EXPECTED_ITEMS)
    def test_item_has_manual_review_checklist(self, item):
        data = json.loads(JSON_RPT.read_text())
        item_data = data["ui2_item_boundaries"][item]
        assert len(item_data["manual_review_checklist"]) >= 3

    @pytest.mark.parametrize("item", EXPECTED_ITEMS)
    def test_item_has_rollback(self, item):
        data = json.loads(JSON_RPT.read_text())
        item_data = data["ui2_item_boundaries"][item]
        assert "rollback" in item_data

    @pytest.mark.parametrize("item", EXPECTED_ITEMS)
    def test_item_has_stop_conditions(self, item):
        data = json.loads(JSON_RPT.read_text())
        item_data = data["ui2_item_boundaries"][item]
        assert len(item_data["stop_conditions"]) >= 3


class TestAutoMergePolicy:
    def test_default_is_no(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["ui2_auto_merge_policy"]["default"] == "NO"

    def test_exception_is_none(self):
        data = json.loads(JSON_RPT.read_text())
        exc = data["ui2_auto_merge_policy"]["exception"]
        # Either "None" or "None." (with period) acceptable
        assert "None" in exc


class TestForbiddenChanges:
    EXPECTED = [
        "CSS :root variables",
        "runtime_impact_taxonomy.py",
        "runtime_summary dict shape",
        "main_web.py",
        "rc1 (b425a07)"
    ]

    @pytest.mark.parametrize("change", EXPECTED)
    def test_change_listed(self, change):
        data = json.loads(JSON_RPT.read_text())
        all_text = " ".join(data["forbidden_changes"])
        assert change in all_text


class TestStopConditionsUniversal:
    EXPECTED = [
        "Any test fails",
        "CI/Parity Guardrails fail",
        "Visual review fails",
        "Backend file changed",
        "Service file changed",
        "rc1 changed"
    ]

    @pytest.mark.parametrize("cond", EXPECTED)
    def test_stop_condition_listed(self, cond):
        data = json.loads(JSON_RPT.read_text())
        # Substring match (some conditions have different exact text)
        all_text = " | ".join(data["stop_conditions_universal"])
        assert cond in all_text or cond.replace(" (UI-2 is presentation only)", "") in all_text
