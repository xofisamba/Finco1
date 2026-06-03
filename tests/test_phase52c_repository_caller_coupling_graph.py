"""Phase 52C — Repository caller and coupling graph structural tests.

Validates the caller graph doc + JSON reflect the current call topology
of app/persistence/repository.py.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "phase52c_repository_caller_coupling_graph.md"
JSON_REPORT = REPO_ROOT / "reports" / "phase52c_repository_caller_coupling_graph.json"
SERVICES_DIR = REPO_ROOT / "app" / "services"
PERSISTENCE_DIR = REPO_ROOT / "app" / "persistence"


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

    def test_doc_mentions_phase_52c(self):
        text = _read(DOC)
        assert "Phase 52C" in text

    def test_json_has_caller_graph(self, data):
        assert "caller_graph" in data
        cg = data["caller_graph"]
        assert "top_15_most_called_functions" in cg
        assert "top_10_most_coupled_caller_files" in cg
        assert len(cg["top_15_most_called_functions"]) == 15
        assert len(cg["top_10_most_coupled_caller_files"]) == 10

    def test_json_includes_coupling_hotspots(self, data):
        assert "coupling_hotspots" in data
        assert len(data["coupling_hotspots"]) >= 3

    def test_json_includes_phase53_candidate_split_groups(self, data):
        assert "phase53_candidate_split_groups" in data
        groups = data["phase53_candidate_split_groups"]
        for g in ("A_projects", "B_scenarios", "C_workspace_state", "D_runs", "E_exports_audit", "F_helpers"):
            assert g in groups, f"missing group {g}"

    def test_json_includes_single_owner_zones(self, data):
        assert "single_owner_zones" in data
        assert len(data["single_owner_zones"]) >= 10

    def test_json_includes_parallel_safe_zones(self, data):
        assert "parallel_safe_zones" in data
        assert len(data["parallel_safe_zones"]) >= 3

    def test_json_includes_do_not_parallelize_zones(self, data):
        assert "do_not_parallelize_zones" in data
        assert len(data["do_not_parallelize_zones"]) >= 3

    def test_json_includes_recommended_next_step(self, data):
        assert data.get("recommended_next_step") == "52D behavior characterization plan"

    def test_no_production_code_changed(self, data):
        # Phase 52C is docs/report/test only
        for k in ("type",):
            assert data.get(k) == "docs/report/test only"


# ----------------------------- caller graph ----------------------------


class TestCallerGraph:
    def test_get_scenario_is_top_called(self, data):
        top = data["caller_graph"]["top_15_most_called_functions"]
        first = top[0]
        assert first["name"] in ("get_scenario", "list_scenarios")

    def test_save_workspace_state_in_top(self, data):
        names = {e["name"] for e in data["caller_graph"]["top_15_most_called_functions"]}
        assert "save_workspace_state" in names

    def test_save_project_in_top(self, data):
        names = {e["name"] for e in data["caller_graph"]["top_15_most_called_functions"]}
        assert "save_project" in names

    def test_record_export_in_top(self, data):
        names = {e["name"] for e in data["caller_graph"]["top_15_most_called_functions"]}
        assert "record_export" in names

    def test_top_caller_is_scenario_duplicate_service(self, data):
        top = data["caller_graph"]["top_10_most_coupled_caller_files"]
        assert "scenario_duplicate_service.py" in top[0]["file"]

    def test_main_web_in_top_coupled_caller_files(self, data):
        files = {e["file"] for e in data["caller_graph"]["top_10_most_coupled_caller_files"]}
        assert "main_web.py" in files

    def test_coupling_hotspots_includes_main_web(self, data):
        names = " ".join(h["hotspot"] for h in data["coupling_hotspots"])
        assert "main_web.py" in names


# ----------------------------- direct import summary ----------------------------


class TestDirectImportSummary:
    def test_direct_import_summary_present(self, data):
        assert "direct_import_summary" in data
        s = data["direct_import_summary"]
        assert "production_imports" in s
        # production_files_with_direct_imports lives in caller_file_summary
        cfs = data.get("caller_file_summary", {})
        assert cfs.get("production_files_with_direct_imports") == 4

    def test_main_web_has_repository_bulk_import(self, data):
        prod = data["direct_import_summary"]["production_imports"]
        main_web_imports = [p for p in prod if p["caller"] == "main_web.py"]
        assert len(main_web_imports) >= 3

    def test_scenario_state_service_in_production_imports(self, data):
        prod = data["direct_import_summary"]["production_imports"]
        callers = {p["caller"] for p in prod}
        assert "app/services/scenario_state_service.py" in callers

    def test_export_audit_service_in_production_imports(self, data):
        prod = data["direct_import_summary"]["production_imports"]
        callers = {p["caller"] for p in prod}
        assert "app/services/export_audit_service.py" in callers

    def test_project_save_as_service_in_production_imports(self, data):
        prod = data["direct_import_summary"]["production_imports"]
        callers = {p["caller"] for p in prod}
        assert "app/services/project_save_as_service.py" in callers

    def test_runtime_summary_in_production_imports(self, data):
        prod = data["direct_import_summary"]["production_imports"]
        callers = {p["caller"] for p in prod}
        assert "app/export/runtime_summary.py" in callers

    def test_direct_persistence_db_imports_in_services_or_routes(self, data):
        # No service or route imports app.persistence.db directly
        s = data["direct_import_summary"]
        assert s["services_or_routes_importing_persistence_db_directly"] == 0


# ----------------------------- circular import check ----------------------------


class TestCircularImportCheck:
    def test_circular_import_check_present(self, data):
        assert "circular_import_check" in data

    def test_internal_cycles_is_zero(self, data):
        assert data["circular_import_check"]["internal_cycles"] == 0

    def test_cross_package_cycles_is_zero(self, data):
        assert data["circular_import_check"]["cross_package_cycles"] == 0

    def test_is_strict_dag(self, data):
        assert data["circular_import_check"]["is_strict_dag"] is True

    def test_no_real_cycles_in_actual_code(self):
        # Verify by parsing the source
        import ast
        modules = {}
        for f in PERSISTENCE_DIR.glob('*.py'):
            if f.name == '__init__.py':
                continue
            name = f'app.persistence.{f.stem}'
            src = f.read_text()
            tree = ast.parse(src)
            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and (node.module == 'app.persistence' or node.module.startswith('app.persistence.')):
                        imports.add(node.module)
            modules[name] = imports
        # Check no cycles
        for m, imps in modules.items():
            for i in imps:
                if i.startswith('app.persistence.'):
                    assert m not in modules.get(i, set()), f"cycle: {m} <-> {i}"


# ----------------------------- phase 53 split groups ----------------------------


class TestPhase53SplitGroups:
    def test_group_A_projects_present(self, data):
        g = data["phase53_candidate_split_groups"]["A_projects"]
        assert len(g["functions"]) >= 10
        assert "save_project" in g["functions"]
        assert "get_project_record" in g["functions"]

    def test_group_B_scenarios_present(self, data):
        g = data["phase53_candidate_split_groups"]["B_scenarios"]
        assert len(g["functions"]) >= 10
        assert "save_scenario" in g["functions"]
        assert "add_scenario" in g["functions"]
        assert "duplicate_scenario" in g["functions"]

    def test_group_C_workspace_state_present(self, data):
        g = data["phase53_candidate_split_groups"]["C_workspace_state"]
        assert len(g["functions"]) >= 5
        assert "save_workspace_state" in g["functions"]
        assert "get_workspace_state" in g["functions"]

    def test_group_D_runs_present(self, data):
        g = data["phase53_candidate_split_groups"]["D_runs"]
        assert "save_run" in g["functions"]
        assert "get_run" in g["functions"]
        assert "list_runs" in g["functions"]

    def test_group_E_exports_audit_present(self, data):
        g = data["phase53_candidate_split_groups"]["E_exports_audit"]
        assert "record_export" in g["functions"]
        assert "build_export_lineage" in g["functions"]
        assert "list_exports" in g["functions"]

    def test_group_F_helpers_present(self, data):
        g = data["phase53_candidate_split_groups"]["F_helpers"]
        assert "_now_utc" in g["functions"]
        assert "_to_json" in g["functions"]
        assert "_from_json" in g["functions"]
        assert "_from_iso" in g["functions"]

    def test_total_functions_across_all_groups_covers_inventory(self, data):
        # Sum of functions in all 6 groups should be at least the 27 key functions
        groups = data["phase53_candidate_split_groups"]
        total = sum(len(g["functions"]) for g in groups.values())
        assert total >= 27


# ----------------------------- single-owner / parallel-safe / do-not-parallelize ----------------------------


class TestZones:
    def test_single_owner_zones_count(self, data):
        # Should be at least 10
        assert len(data["single_owner_zones"]) >= 10

    def test_single_owner_record_export(self, data):
        names = {z["function"] for z in data["single_owner_zones"]}
        assert "record_export" in names

    def test_single_owner_build_export_lineage(self, data):
        names = {z["function"] for z in data["single_owner_zones"]}
        assert "build_export_lineage" in names

    def test_parallel_safe_includes_group_d(self, data):
        zones = " ".join(z["zone"] for z in data["parallel_safe_zones"])
        assert "Group D" in zones

    def test_parallel_safe_includes_group_f(self, data):
        zones = " ".join(z["zone"] for z in data["parallel_safe_zones"])
        assert "Group F" in zones

    def test_do_not_parallelize_includes_workspace_convergence(self, data):
        names = " ".join(z["zone"] for z in data["do_not_parallelize_zones"])
        assert "save_workspace_state" in names


# ----------------------------- refactor recommendations ----------------------------


class TestRefactorRecommendations:
    def test_recommendations_present(self, data):
        assert "refactor_recommendations" in data
        r = data["refactor_recommendations"]
        assert "refactor_order" in r
        assert "compatibility_facade" in r
        assert "direct_import_preservation" in r

    def test_refactor_order_starts_with_helpers(self, data):
        order = data["refactor_recommendations"]["refactor_order"]
        assert "F" in order[0]

    def test_refactor_order_ends_with_scenarios(self, data):
        order = data["refactor_recommendations"]["refactor_order"]
        assert "B" in order[-1]

    def test_compatibility_facade_recommended(self, data):
        assert data["refactor_recommendations"]["compatibility_facade"].startswith("yes")
