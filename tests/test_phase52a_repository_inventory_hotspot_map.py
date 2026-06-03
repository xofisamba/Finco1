"""Phase 52A — Repository inventory and hotspot map structural tests.

Validates the inventory doc + JSON reflect the current state of
app/persistence/* and don't overfit to specific prose.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "phase52a_repository_inventory_hotspot_map.md"
JSON_REPORT = REPO_ROOT / "reports" / "phase52a_repository_inventory_hotspot_map.json"
PERSISTENCE_DIR = REPO_ROOT / "app" / "persistence"
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
        assert DOC.exists(), f"missing {DOC}"

    def test_json_exists(self):
        assert JSON_REPORT.exists(), f"missing {JSON_REPORT}"

    def test_doc_mentions_phase_52a(self):
        text = _read(DOC)
        assert "Phase 52A" in text

    def test_doc_mentions_repository_py(self):
        text = _read(DOC)
        assert "app/persistence/repository.py" in text

    def test_json_has_function_inventory(self, data):
        assert "function_inventory" in data
        assert len(data["function_inventory"]) > 0

    def test_json_includes_repository_persistence_path(self, data):
        paths = [f["path"] for f in data["persistence_files"]]
        assert "app/persistence/repository.py" in paths

    def test_json_includes_domain_summary(self, data):
        assert "domain_summary" in data
        ds = data["domain_summary"]
        # All domains present
        for d in ("projects", "scenarios", "workspace_state", "runs", "exports", "helpers"):
            assert d in ds

    def test_json_includes_hotspot_ranking(self, data):
        assert "hotspot_ranking" in data
        hr = data["hotspot_ranking"]
        assert "largest_functions" in hr
        assert "most_called_functions" in hr
        assert "write_heavy_functions" in hr
        assert "governance_replay_metadata_touchers" in hr

    def test_json_includes_recommended_next_step(self, data):
        assert data.get("recommended_next_step") == "52B persistence side-effect map"

    def test_json_includes_base_sha(self, data):
        assert data.get("base_sha") == "e51a16db61c8981adc21700a671c91bac0d88d2d"

    def test_json_includes_risks(self, data):
        assert "risks" in data
        assert len(data["risks"]) > 0


# ----------------------------- function inventory ----------------------------


class TestFunctionInventoryConsistency:
    def test_function_inventory_is_nonempty(self, data):
        assert len(data["function_inventory"]) >= 60

    def test_function_inventory_has_unique_names(self, data):
        names = [f["name"] for f in data["function_inventory"]]
        assert len(names) == len(set(names)), "duplicate function names"

    def test_function_inventory_includes_save_workspace_state(self, data):
        names = {f["name"] for f in data["function_inventory"]}
        assert "save_workspace_state" in names

    def test_function_inventory_includes_save_project(self, data):
        names = {f["name"] for f in data["function_inventory"]}
        assert "save_project" in names

    def test_function_inventory_includes_save_scenario(self, data):
        names = {f["name"] for f in data["function_inventory"]}
        assert "save_scenario" in names

    def test_function_inventory_includes_record_export(self, data):
        names = {f["name"] for f in data["function_inventory"]}
        assert "record_export" in names

    def test_function_inventory_includes_save_run(self, data):
        names = {f["name"] for f in data["function_inventory"]}
        assert "save_run" in names

    def test_function_inventory_includes_update_scenario_overrides(self, data):
        names = {f["name"] for f in data["function_inventory"]}
        assert "update_scenario_overrides" in names

    def test_function_inventory_includes_bind_workspace_to_scenario(self, data):
        names = {f["name"] for f in data["function_inventory"]}
        assert "bind_workspace_to_scenario" in names

    def test_function_inventory_includes_select_scenario(self, data):
        names = {f["name"] for f in data["function_inventory"]}
        assert "select_scenario" in names

    def test_function_inventory_includes_rename_scenario(self, data):
        names = {f["name"] for f in data["function_inventory"]}
        assert "rename_scenario" in names

    def test_function_inventory_includes_archive_scenario(self, data):
        names = {f["name"] for f in data["function_inventory"]}
        assert "archive_scenario" in names

    def test_function_inventory_includes_duplicate_scenario(self, data):
        names = {f["name"] for f in data["function_inventory"]}
        assert "duplicate_scenario" in names

    def test_function_inventory_includes_add_scenario(self, data):
        names = {f["name"] for f in data["function_inventory"]}
        assert "add_scenario" in names

    def test_function_inventory_includes_record_workspace_runtime(self, data):
        names = {f["name"] for f in data["function_inventory"]}
        assert "record_workspace_runtime" in names

    def test_function_inventory_includes_discard_workspace_draft(self, data):
        names = {f["name"] for f in data["function_inventory"]}
        assert "discard_workspace_draft" in names

    def test_function_inventory_includes_update_scenario_last_run_summary(self, data):
        names = {f["name"] for f in data["function_inventory"]}
        assert "update_scenario_last_run_summary" in names

    def test_function_inventory_includes_compare_scenarios(self, data):
        names = {f["name"] for f in data["function_inventory"]}
        assert "compare_scenarios" in names

    def test_function_inventory_includes_build_export_lineage(self, data):
        names = {f["name"] for f in data["function_inventory"]}
        assert "build_export_lineage" in names

    def test_function_inventory_includes_base_vs_active_compare(self, data):
        names = {f["name"] for f in data["function_inventory"]}
        assert "base_vs_active_compare" in names

    def test_function_inventory_includes_runtime_guard_for_snapshot(self, data):
        names = {f["name"] for f in data["function_inventory"]}
        assert "runtime_guard_for_snapshot" in names

    def test_function_inventory_classification_values(self, data):
        valid = {"read", "write", "mixed", "helper"}
        for f in data["function_inventory"]:
            assert f["classification"] in valid, f"bad classification: {f['name']}: {f['classification']}"

    def test_function_inventory_domain_values(self, data):
        valid = {"projects", "scenarios", "workspace_state", "runs", "exports", "governance", "audit", "helpers"}
        for f in data["function_inventory"]:
            assert f["domain"] in valid, f"bad domain: {f['name']}: {f['domain']}"

    def test_function_inventory_risk_values(self, data):
        valid = {"low", "medium", "high"}
        for f in data["function_inventory"]:
            assert f["risk"] in valid, f"bad risk: {f['name']}: {f['risk']}"

    def test_function_inventory_includes_specific_function_locs(self, data):
        by_name = {f["name"]: f for f in data["function_inventory"]}
        # save_workspace_state should be at line 1496
        assert by_name["save_workspace_state"]["line"] == 1496
        # save_project should be at line 686
        assert by_name["save_project"]["line"] == 686


# ----------------------------- domain + read/write summary ----------------------------


class TestReadWriteAndDomainSummary:
    def test_read_write_summary_present(self, data):
        assert "read_write_summary" in data
        s = data["read_write_summary"]
        for k in ("write", "read", "mixed", "helper", "total_repository_py"):
            assert k in s
        assert s["total_repository_py"] == sum([s["write"], s["read"], s["mixed"], s["helper"]])

    def test_domain_summary_present(self, data):
        assert "domain_summary" in data
        ds = data["domain_summary"]
        # Total should match function_inventory
        fi = len(data["function_inventory"])
        # Helpers is in domain_summary too
        assert ds["total_repository_py"] == fi

    def test_repository_py_is_god_module(self, data):
        for f in data["persistence_files"]:
            if f["path"] == "app/persistence/repository.py":
                assert f["loc"] >= 2000, f"repository.py should be >= 2000 LOC, got {f['loc']}"


# ----------------------------- direct DB / session usage ----------------------------


class TestDirectDbSessionSummary:
    def test_direct_db_session_summary_present(self, data):
        assert "direct_db_session_usage_summary" in data

    def test_no_direct_db_access_outside_persistence(self, data):
        summary = data["direct_db_session_usage_summary"]
        assert summary["direct_db_access_outside_app_persistence"] == 0
        assert summary["raw_db_connections_in_services_or_routes"] == 0
        assert summary["orm_session_add_or_session_commit"] == 0
        assert summary["explicit_cur_commit_calls"] == 0

    def test_choke_point_is_get_cursor(self, data):
        summary = data["direct_db_session_usage_summary"]
        assert "get_cursor" in summary["choke_point"]


# ----------------------------- caller summary ----------------------------


class TestCallerSummary:
    def test_caller_summary_present(self, data):
        assert "caller_summary_if_available" in data

    def test_top_10_most_coupled_caller_files_present(self, data):
        cs = data["caller_summary_if_available"]
        assert "top_10_most_coupled_caller_files" in cs
        assert len(cs["top_10_most_coupled_caller_files"]) == 10

    def test_main_web_in_top_caller_files(self, data):
        cs = data["caller_summary_if_available"]
        files = [f["file"] for f in cs["top_10_most_coupled_caller_files"]]
        assert "main_web.py" in files

    def test_no_services_import_main_web_or_main_api(self):
        # Phase 51F invariant — verify services are still clean
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

    def test_no_main_api_imports_of_app_persistence_backup_restore(self, data):
        # backup_restore is a test-only module
        cs = data["caller_summary_if_available"]
        prod_imports = cs["production_imports_of_app_persistence_backup_restore"]
        assert prod_imports == []


# ----------------------------- do-not-touch list ----------------------------


class TestDoNotTouchList:
    def test_do_not_touch_list_present(self, data):
        assert "do_not_touch_yet_list" in data
        assert len(data["do_not_touch_yet_list"]) > 0

    def test_do_not_touch_includes_save_project(self, data):
        names = {e["function"] for e in data["do_not_touch_yet_list"]}
        assert "save_project" in names

    def test_do_not_touch_includes_save_workspace_state(self, data):
        names = {e["function"] for e in data["do_not_touch_yet_list"]}
        assert "save_workspace_state" in names

    def test_do_not_touch_includes_save_scenario(self, data):
        names = {e["function"] for e in data["do_not_touch_yet_list"]}
        assert "save_scenario" in names

    def test_do_not_touch_includes_get_cursor(self, data):
        names = {e["function"] for e in data["do_not_touch_yet_list"]}
        assert "get_cursor" in names


# ----------------------------- recommended 52B input list ----------------------------


class TestRecommended52BList:
    def test_recommended_52b_input_list_present(self, data):
        assert "recommended_52b_input_list" in data
        assert len(data["recommended_52b_input_list"]) >= 10

    def test_recommended_52b_includes_save_project(self, data):
        assert "save_project" in data["recommended_52b_input_list"]

    def test_recommended_52b_includes_save_workspace_state(self, data):
        assert "save_workspace_state" in data["recommended_52b_input_list"]

    def test_recommended_52b_includes_save_scenario(self, data):
        assert "save_scenario" in data["recommended_52b_input_list"]

    def test_recommended_52b_includes_bind_workspace_to_scenario(self, data):
        assert "bind_workspace_to_scenario" in data["recommended_52b_input_list"]

    def test_recommended_52b_includes_save_run(self, data):
        assert "save_run" in data["recommended_52b_input_list"]


# ----------------------------- persistence files ----------------------------


class TestPersistenceFiles:
    def test_persistence_files_present(self, data):
        assert "persistence_files" in data
        paths = [f["path"] for f in data["persistence_files"]]
        for required in (
            "app/persistence/__init__.py",
            "app/persistence/db.py",
            "app/persistence/repository.py",
            "app/persistence/backup_restore.py",
            "app/persistence/provenance.py",
        ):
            assert required in paths

    def test_persistence_files_loc_matches_actual(self, data):
        for entry in data["persistence_files"]:
            p = REPO_ROOT / entry["path"]
            if not p.exists():
                continue
            actual_loc = sum(1 for _ in p.open(encoding="utf-8"))
            assert actual_loc == entry["loc"], f"{entry['path']}: expected {entry['loc']} LOC, got {actual_loc}"


# ----------------------------- guardrails ----------------------------


class TestGuardrailsFile:
    def test_phase51f_guardrail_test_exists(self):
        assert GUARDRAIL_TEST.exists(), "Phase 51F guardrail test missing"
