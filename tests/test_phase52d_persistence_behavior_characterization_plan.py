"""Phase 52D — Persistence behavior characterization plan structural tests.

Validates the plan doc + JSON reflect the must-pin items from 52B and the
split-group recommendations from 52C.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "phase52d_persistence_behavior_characterization_plan.md"
JSON_REPORT = REPO_ROOT / "reports" / "phase52d_persistence_behavior_characterization_plan.json"
SERVICES_DIR = REPO_ROOT / "app" / "services"
GUARDRAIL_TEST = REPO_ROOT / "tests" / "test_phase51f_parallel_work_guardrails.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _strip_docstrings_and_comments(src: str) -> str:
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    src = re.sub(r"'''[\s\S]*?'''", "", src)
    out = []
    for line in src.splitlines():
        in_string = False
        quote_char = None
        cleaned = []
        for ch in line:
            if ch in ('"', "'") and not in_string:
                in_string = True
                quote_char = ch
                cleaned.append(ch)
            elif ch == quote_char and in_string:
                in_string = False
                quote_char = None
                cleaned.append(ch)
            elif ch == "#" and not in_string:
                break
            else:
                cleaned.append(ch)
        out.append("".join(cleaned))
    return "\n".join(out)


@pytest.fixture(scope="module")
def data() -> Dict[str, Any]:
    return _read_json(JSON_REPORT)


# ----------------------------- doc / JSON exist ----------------------------


class TestDocsAndJsonExist:
    def test_doc_exists(self):
        assert DOC.exists()

    def test_json_exists(self):
        assert JSON_REPORT.exists()

    def test_doc_mentions_phase_52d(self):
        text = _read(DOC)
        assert "Phase 52D" in text

    def test_json_has_high_risk_writes(self, data):
        assert "high_risk_writes" in data
        assert len(data["high_risk_writes"]) == 7

    def test_json_has_must_pin_items(self, data):
        assert "must_pin_items" in data
        assert len(data["must_pin_items"]) == 12

    def test_json_has_behavior_characterization_matrix(self, data):
        assert "behavior_characterization_matrix" in data
        assert len(data["behavior_characterization_matrix"]) == 12

    def test_json_has_phase53_group_test_gates(self, data):
        assert "phase53_group_test_gates" in data
        gates = data["phase53_group_test_gates"]
        for g in ("F_helpers", "D_runs", "E_exports_audit", "A_projects", "C_workspace_state", "B_scenarios"):
            assert g in gates, f"missing gate {g}"

    def test_recommended_next_step_is_52e(self, data):
        assert data.get("recommended_next_step") == "52E persistence hotspot / Phase 53 execution plan"


# ----------------------------- 7 high-risk writes ----------------------------


class TestHighRiskWrites:
    @pytest.mark.parametrize("name", [
        "save_project", "save_workspace_state", "save_scenario", "add_scenario",
        "record_export", "update_scenario_overrides", "get_or_create_base_case_scenario",
    ])
    def test_high_risk_write_present(self, data, name):
        names = {w["name"] for w in data["high_risk_writes"]}
        assert name in names

    def test_save_project_assigned_to_group_A(self, data):
        sp = next(w for w in data["high_risk_writes"] if w["name"] == "save_project")
        assert sp["phase53_group"] == "A"

    def test_save_workspace_state_assigned_to_group_C(self, data):
        sp = next(w for w in data["high_risk_writes"] if w["name"] == "save_workspace_state")
        assert sp["phase53_group"] == "C"

    def test_save_scenario_assigned_to_group_B(self, data):
        sp = next(w for w in data["high_risk_writes"] if w["name"] == "save_scenario")
        assert sp["phase53_group"] == "B"


# ----------------------------- 12 must-pin items ----------------------------


class TestMustPinItems:
    def test_all_12_items_present(self, data):
        ids = {e["id"] for e in data["must_pin_items"]}
        assert ids == set(range(1, 13))

    def test_p0_count_is_7(self, data):
        p0 = [e for e in data["must_pin_items"] if e["priority"] == "P0"]
        assert len(p0) == 7

    def test_p1_count_is_5(self, data):
        p1 = [e for e in data["must_pin_items"] if e["priority"] == "P1"]
        assert len(p1) == 5

    def test_p0_all_required_before_phase53(self, data):
        for e in data["must_pin_items"]:
            if e["priority"] == "P0":
                assert e["required_before_phase53"] is True

    def test_p1_not_required_before_phase53(self, data):
        for e in data["must_pin_items"]:
            if e["priority"] == "P1":
                assert e["required_before_phase53"] is False

    def test_p0_includes_save_project(self, data):
        names = {e["function"] for e in data["must_pin_items"] if e["priority"] == "P0"}
        assert "save_project" in names

    def test_p0_includes_save_workspace_state(self, data):
        names = {e["function"] for e in data["must_pin_items"] if e["priority"] == "P0"}
        assert "save_workspace_state" in names

    def test_p0_includes_add_scenario(self, data):
        names = {e["function"] for e in data["must_pin_items"] if e["priority"] == "P0"}
        assert "add_scenario" in names

    def test_p0_includes_record_export(self, data):
        names = {e["function"] for e in data["must_pin_items"] if e["priority"] == "P0"}
        assert "record_export" in names

    def test_p0_includes_update_scenario_overrides(self, data):
        names = {e["function"] for e in data["must_pin_items"] if e["priority"] == "P0"}
        assert "update_scenario_overrides" in names

    def test_p0_includes_select_scenario(self, data):
        names = {e["function"] for e in data["must_pin_items"] if e["priority"] == "P0"}
        assert "select_scenario" in names

    def test_recommended_test_files_present(self, data):
        for e in data["must_pin_items"]:
            assert e["recommended_test_file"].startswith("tests/test_phase52d_persistence_")
            assert e["recommended_test_file"].endswith(".py")


# ----------------------------- behavior characterization matrix ----------------------------


class TestBehaviorMatrix:
    def test_matrix_has_12_entries(self, data):
        assert len(data["behavior_characterization_matrix"]) == 12

    def test_matrix_entry_has_required_fields(self, data):
        for e in data["behavior_characterization_matrix"]:
            for f in ("id", "function", "current_behavior", "owning_function", "callers", "metadata_fields", "ordering", "existing_tests", "missing_tests", "priority"):
                assert f in e, f"missing {f} in entry {e.get('id')}"

    def test_matrix_priorities_match_must_pin(self, data):
        mp = {e["id"]: e["priority"] for e in data["must_pin_items"]}
        for e in data["behavior_characterization_matrix"]:
            assert mp[e["id"]] == e["priority"]


# ----------------------------- phase 53 test gates ----------------------------


class TestPhase53Gates:
    def test_F_helpers_zero_required_pins(self, data):
        assert data["phase53_group_test_gates"]["F_helpers"]["required_new_pins"] == 0

    def test_D_runs_zero_required_pins(self, data):
        assert data["phase53_group_test_gates"]["D_runs"]["required_new_pins"] == 0

    def test_E_exports_audit_zero_required_pins(self, data):
        assert data["phase53_group_test_gates"]["E_exports_audit"]["required_new_pins"] == 0

    def test_A_projects_requires_save_project_pin(self, data):
        g = data["phase53_group_test_gates"]["A_projects"]
        assert g["required_new_pins"] >= 1
        assert "save_project" in g["notes"]

    def test_C_workspace_state_requires_save_workspace_state_pin(self, data):
        g = data["phase53_group_test_gates"]["C_workspace_state"]
        assert g["required_new_pins"] >= 1
        assert "save_workspace_state" in g["notes"]

    def test_B_scenarios_requires_most_pins(self, data):
        g = data["phase53_group_test_gates"]["B_scenarios"]
        assert g["required_new_pins"] >= 4


# ----------------------------- user sign-off / red flags ----------------------------


class TestUserSignoff:
    def test_user_signoff_required_items_present(self, data):
        assert "user_signoff_required_items" in data
        assert len(data["user_signoff_required_items"]) >= 5

    def test_user_signoff_includes_save_project(self, data):
        items = " ".join(e["item"] for e in data["user_signoff_required_items"])
        assert "save_project" in items

    def test_user_signoff_includes_save_workspace_state(self, data):
        items = " ".join(e["item"] for e in data["user_signoff_required_items"])
        assert "save_workspace_state" in items

    def test_user_signoff_includes_add_scenario(self, data):
        items = " ".join(e["item"] for e in data["user_signoff_required_items"])
        assert "add_scenario" in items

    def test_user_signoff_includes_replay_metadata_shape(self, data):
        items = " ".join(e["item"] for e in data["user_signoff_required_items"])
        assert "replay_metadata" in items

    def test_red_flags_present(self, data):
        assert "red_flags_requiring_user_signoff" in data
        assert len(data["red_flags_requiring_user_signoff"]) >= 10

    def test_red_flags_includes_no_schema_change(self, data):
        flags = " ".join(data["red_flags_requiring_user_signoff"])
        assert "schema" in flags.lower()


# ----------------------------- guardrails + invariants ----------------------------


class TestGuardrailsAndInvariants:
    def test_phase51f_guardrail_file_exists(self):
        assert GUARDRAIL_TEST.exists()

    def test_no_services_import_main_web_or_main_api(self):
        offenders: List[str] = []
        for svc in SERVICES_DIR.glob("*.py"):
            if svc.name == "__init__.py":
                continue
            cleaned = _strip_docstrings_and_comments(_read(svc))
            for line in cleaned.splitlines():
                stripped = line.lstrip()
                if stripped.startswith("import main_web") or stripped.startswith("from main_web"):
                    offenders.append(f"{svc}: {line}")
                if stripped.startswith("import main_api") or stripped.startswith("from main_api"):
                    offenders.append(f"{svc}: {line}")
        assert offenders == [], f"services import main_web/main_api: {offenders}"


# ----------------------------- high-risk to test mapping ----------------------------


class TestHighRiskToTestMapping:
    def test_mapping_count_matches_high_risk_count(self, data):
        assert len(data["high_risk_to_test_mapping"]) == len(data["high_risk_writes"])

    def test_mapping_includes_save_project(self, data):
        names = {e["high_risk_write"] for e in data["high_risk_to_test_mapping"]}
        assert "save_project" in names

    def test_all_p0_pins_required_before_phase53(self, data):
        for e in data["high_risk_to_test_mapping"]:
            assert e["required_before_phase53"] is True
