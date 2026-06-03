"""Phase 52B — Persistence side-effect map structural tests.

Validates the side-effect doc + JSON reflect the current state of
app/persistence/repository.py and don't overfit to specific prose.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "phase52b_persistence_side_effect_map.md"
JSON_REPORT = REPO_ROOT / "reports" / "phase52b_persistence_side_effect_map.json"
SERVICES_DIR = REPO_ROOT / "app" / "services"
PERSISTENCE_DIR = REPO_ROOT / "app" / "persistence"
REPOSITORY_PY = PERSISTENCE_DIR / "repository.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def data() -> Dict[str, Any]:
    return _read_json(JSON_REPORT)


# ----------------------------- doc / JSON exist ----------------------------


class TestDocsAndJsonExist:
    def test_doc_exists(self):
        assert DOC.exists(), f"missing {DOC}"

    def test_json_exists(self):
        assert JSON_REPORT.exists(), f"missing {JSON_REPORT}"

    def test_doc_mentions_phase_52b(self):
        text = _read(DOC)
        assert "Phase 52B" in text

    def test_json_has_side_effect_inventory(self, data):
        assert "side_effect_inventory" in data
        assert len(data["side_effect_inventory"]) >= 15

    def test_json_includes_high_risk_writes(self, data):
        assert "high_risk_writes" in data
        assert len(data["high_risk_writes"]) >= 6

    def test_json_includes_must_pin_before_refactor(self, data):
        assert "must_pin_before_refactor" in data
        assert len(data["must_pin_before_refactor"]) >= 10

    def test_json_includes_safe_low_risk_functions(self, data):
        assert "safe_low_risk_functions" in data
        assert len(data["safe_low_risk_functions"]) >= 15

    def test_json_includes_recommended_next_step(self, data):
        assert data.get("recommended_next_step") == "52C caller/coupling graph"


# ----------------------------- side-effect inventory ----------------------------


class TestSideEffectInventory:
    def test_all_15_key_functions_present(self, data):
        names = {e["function"] for e in data["side_effect_inventory"]}
        for required in (
            "save_project", "save_workspace_state", "save_scenario",
            "bind_workspace_to_scenario", "save_run", "rename_scenario",
            "archive_scenario", "select_scenario", "update_scenario_overrides",
            "duplicate_scenario", "add_scenario", "record_export",
            "record_workspace_runtime", "discard_workspace_draft",
            "update_scenario_last_run_summary",
        ):
            assert required in names, f"missing {required}"

    def test_classification_values(self, data):
        valid = {"high", "medium", "low"}
        for e in data["side_effect_inventory"]:
            assert e["risk"] in valid, f"bad risk: {e['function']}: {e['risk']}"

    def test_pinned_by_tests_for_all_15(self, data):
        for e in data["side_effect_inventory"]:
            assert e["pinned_by_tests"] is True, f"unpinned: {e['function']}"

    def test_idempotency_risk_present(self, data):
        for e in data["side_effect_inventory"]:
            assert "idempotency_risk" in e
            assert e["idempotency_risk"]

    def test_ordering_field_present(self, data):
        for e in data["side_effect_inventory"]:
            assert "ordering" in e
            assert e["ordering"]

    def test_commit_flush_field_present(self, data):
        for e in data["side_effect_inventory"]:
            assert "commit_flush" in e
            assert e["commit_flush"]

    def test_metadata_written_field_present(self, data):
        for e in data["side_effect_inventory"]:
            assert "metadata_written" in e

    def test_replay_metadata_defaulting_for_save_scenario(self, data):
        save_scenario = next(e for e in data["side_effect_inventory"] if e["function"] == "save_scenario")
        meta = " ".join(save_scenario["metadata_written"]).lower()
        assert "scenario_id" in meta
        assert "project_id" in meta

    def test_replay_metadata_defaulting_for_add_scenario(self, data):
        add = next(e for e in data["side_effect_inventory"] if e["function"] == "add_scenario")
        meta = " ".join(add["metadata_written"]).lower()
        assert "add_scenario" in meta
        assert "parent_scenario_id" in meta

    def test_replay_metadata_defaulting_for_record_export(self, data):
        rec = next(e for e in data["side_effect_inventory"] if e["function"] == "record_export")
        meta = " ".join(rec["metadata_written"]).lower()
        assert "export_id" in meta
        assert "export_timestamp" in meta

    def test_update_scenario_overrides_has_base_case_gate(self, data):
        up = next(e for e in data["side_effect_inventory"] if e["function"] == "update_scenario_overrides")
        ef = up["error_fallback"].lower()
        assert "is_base_case" in ef

    def test_save_workspace_state_preserves_runtime_fields(self, data):
        save = next(e for e in data["side_effect_inventory"] if e["function"] == "save_workspace_state")
        flds = " ".join(save["fields_written_update"]).lower()
        assert "last_runtime_snapshot" in flds
        assert "last_runtime_summary" in flds
        assert "last_runtime_origin" in flds

    def test_record_workspace_runtime_origin_gate(self, data):
        rec = next(e for e in data["side_effect_inventory"] if e["function"] == "record_workspace_runtime")
        flds = " ".join(rec["fields_written"]).lower()
        assert "saved_state" in flds

    def test_select_scenario_action_tag(self, data):
        sel = next(e for e in data["side_effect_inventory"] if e["function"] == "select_scenario")
        flds = " ".join(sel["fields_written"]).lower()
        assert "select_scenario" in flds


# ----------------------------- write function summary ----------------------------


class TestWriteFunctionSummary:
    def test_write_function_summary_present(self, data):
        assert "write_function_summary" in data
        s = data["write_function_summary"]
        assert s["total_write_functions"] >= 15
        assert s["all_use_get_cursor_context"] is True
        assert s["all_single_transaction"] is True


# ----------------------------- metadata behavior ----------------------------


class TestMetadataBehavior:
    def test_metadata_behavior_present(self, data):
        assert "metadata_behavior_summary" in data
        mb = data["metadata_behavior_summary"]
        # 4 main JSON columns
        assert "replay_metadata_json" in mb
        assert "governance_state_json" in mb
        assert "last_run_summary_json" in mb
        assert "last_runtime_summary_json" in mb

    def test_replay_metadata_touched_by_most_writes(self, data):
        mb = data["metadata_behavior_summary"]
        assert mb["replay_metadata_json"]["functions_writing_count"] >= 10


# ----------------------------- commit/flush ----------------------------


class TestCommitFlush:
    def test_commit_flush_summary_present(self, data):
        assert "commit_flush_summary" in data
        c = data["commit_flush_summary"]
        assert c["explicit_cur_commit_calls"] == 0
        assert c["explicit_cur_flush_calls"] == 0
        assert c["nested_transactions"] == 0
        assert c["savepoints"] == 0
        assert c["all_15_functions_single_transaction"] is True


# ----------------------------- ordering ----------------------------


class TestOrderingDependencies:
    def test_ordering_dependencies_present(self, data):
        assert "ordering_dependencies" in data
        assert len(data["ordering_dependencies"]) >= 10

    def test_save_project_comes_before_save_scenario(self, data):
        deps = data["ordering_dependencies"]
        sp = next(d for d in deps if "save_project" in d["sequence"])
        assert sp["required"] is True


# ----------------------------- must-pin-before-refactor ----------------------------


class TestMustPinList:
    def test_must_pin_includes_save_project(self, data):
        names = {e["function"] for e in data["must_pin_before_refactor"]}
        assert "save_project" in names

    def test_must_pin_includes_save_workspace_state(self, data):
        names = {e["function"] for e in data["must_pin_before_refactor"]}
        assert "save_workspace_state" in names

    def test_must_pin_includes_add_scenario(self, data):
        names = {e["function"] for e in data["must_pin_before_refactor"]}
        assert "add_scenario" in names

    def test_must_pin_includes_record_export(self, data):
        names = {e["function"] for e in data["must_pin_before_refactor"]}
        assert "record_export" in names

    def test_must_pin_includes_update_scenario_overrides(self, data):
        names = {e["function"] for e in data["must_pin_before_refactor"]}
        assert "update_scenario_overrides" in names

    def test_must_pin_includes_select_scenario(self, data):
        names = {e["function"] for e in data["must_pin_before_refactor"]}
        assert "select_scenario" in names

    def test_must_pin_includes_discard_workspace_draft(self, data):
        names = {e["function"] for e in data["must_pin_before_refactor"]}
        assert "discard_workspace_draft" in names

    def test_must_pin_includes_record_workspace_runtime(self, data):
        names = {e["function"] for e in data["must_pin_before_refactor"]}
        assert "record_workspace_runtime" in names

    def test_must_pin_includes_bind_workspace_to_scenario(self, data):
        names = {e["function"] for e in data["must_pin_before_refactor"]}
        assert "bind_workspace_to_scenario" in names


# ----------------------------- safe low-risk functions ----------------------------


class TestSafeLowRiskFunctions:
    def test_safe_includes_rename_scenario(self, data):
        names = {f["function"] for f in data["safe_low_risk_functions"]}
        assert "rename_scenario" in names

    def test_safe_includes_archive_scenario(self, data):
        names = {f["function"] for f in data["safe_low_risk_functions"]}
        assert "archive_scenario" in names

    def test_safe_count_at_least_15(self, data):
        assert len(data["safe_low_risk_functions"]) >= 15


# ----------------------------- 52C input list ----------------------------


class TestRecommended52CList:
    def test_recommended_52c_input_list_present(self, data):
        assert "recommended_52c_input_list" in data
        assert len(data["recommended_52c_input_list"]) >= 5

    def test_recommended_52c_includes_save_project(self, data):
        assert "save_project" in data["recommended_52c_input_list"]

    def test_recommended_52c_includes_save_workspace_state(self, data):
        assert "save_workspace_state" in data["recommended_52c_input_list"]

    def test_recommended_52c_includes_record_export(self, data):
        assert "record_export" in data["recommended_52c_input_list"]


# ----------------------------- transactional model vs actual code ----------------------------


class TestTransactionalModelConsistency:
    def test_no_explicit_commit_in_repository(self):
        # Read raw repository.py and check no `cur.commit(` or `cur.flush(` or `conn.commit(` calls
        text = _read(REPOSITORY_PY)
        # Strip docstrings and comments
        text2 = re.sub(r'"""[\s\S]*?"""', "", text)
        text2 = re.sub(r"'''[\s\S]*?'''", "", text2)
        # Look for explicit commit/flush
        for line in text2.splitlines():
            stripped = line.lstrip()
            # Skip comments
            if stripped.startswith("#"):
                continue
            assert "cur.commit" not in stripped, f"explicit cur.commit found: {line}"
            assert "cur.flush" not in stripped, f"explicit cur.flush found: {line}"
            assert "connection.commit" not in stripped, f"explicit connection.commit found: {line}"
            assert "conn.commit" not in stripped, f"explicit conn.commit found: {line}"

    def test_repository_uses_get_cursor(self):
        text = _read(REPOSITORY_PY)
        assert "from app.persistence.db import get_cursor" in text
        # count "with get_cursor()" usages
        n = len(re.findall(r"with\s+get_cursor\(\)\s+as\s+cur", text))
        assert n >= 20, f"expected >= 20 with get_cursor() blocks, got {n}"
