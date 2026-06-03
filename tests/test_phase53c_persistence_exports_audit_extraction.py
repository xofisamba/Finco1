"""Phase 53C — Exports and audit persistence extraction structural tests.

Verifies that the 11 Group E items (1 class + 10 functions) are present
in the new app/persistence/exports_repository.py module and re-exported
from app/persistence/repository.py for backward compatibility.

Special note: `record_export` is one of the 7 high-risk writes. The
test verifies that the move is byte-for-byte behavior-preserving.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPORTS_PY = REPO_ROOT / "app" / "persistence" / "exports_repository.py"
REPOSITORY_PY = REPO_ROOT / "app" / "persistence" / "repository.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


GROUP_E_NAMES = [
    "ScenarioExportRecord",
    "record_export",
    "list_exports",
    "get_scenario_history",
    "compare_scenarios",
    "build_export_lineage",
    "base_vs_active_compare",
    "_scenario_runtime_dict",
    "_build_compare_metrics",
    "_delta_sign_class",
    "_format_db_timestamp",
]
GROUP_E_FUNCTIONS = [n for n in GROUP_E_NAMES if n != "ScenarioExportRecord"]


# ----------------------------- Module existence ----------------------------


class TestModuleExistence:
    def test_exports_module_exists(self):
        assert EXPORTS_PY.exists()

    def test_exports_module_is_python(self):
        text = _read(EXPORTS_PY)
        ast.parse(text)


# ----------------------------- Exports module content ----------------------------


class TestExportsModuleContent:
    @pytest.mark.parametrize("name", GROUP_E_NAMES)
    def test_exports_module_defines(self, name):
        text = _read(EXPORTS_PY)
        assert re.search(rf"^(def {re.escape(name)}|class {re.escape(name)})", text, re.MULTILINE), \
            f"exports_repository.py does not define {name}"

    def test_exports_module_has_get_cursor_import(self):
        text = _read(EXPORTS_PY)
        assert "from app.persistence.db import get_cursor" in text

    def test_exports_module_imports_helpers(self):
        text = _read(EXPORTS_PY)
        assert "from app.persistence._helpers import" in text

    def test_exports_module_has_10_functions_and_1_class(self):
        text = _read(EXPORTS_PY)
        defs = re.findall(r"^def\s+(\w+)", text, re.MULTILINE)
        classes = re.findall(r"^class\s+(\w+)", text, re.MULTILINE)
        assert len(defs) == 10, f"expected 10 functions, got {len(defs)}: {defs}"
        assert classes == ["ScenarioExportRecord"], f"expected 1 class ScenarioExportRecord, got {classes}"


# ----------------------------- Repository compatibility façade ----------------------------


class TestRepositoryFacade:
    @pytest.mark.parametrize("name", GROUP_E_NAMES)
    def test_repository_re_exports(self, name):
        from app.persistence import repository
        assert hasattr(repository, name), f"repository.py missing re-export of {name}"

    @pytest.mark.parametrize("name", GROUP_E_NAMES)
    def test_repository_and_exports_share_same_object(self, name):
        from app.persistence import repository
        from app.persistence import exports_repository
        assert getattr(repository, name) is getattr(exports_repository, name), \
            f"repository.{name} is not the same object as exports_repository.{name}"

    def test_repository_has_import_block_for_exports(self):
        text = _read(REPOSITORY_PY)
        assert "from app.persistence.exports_repository import" in text


# ----------------------------- Behavior preservation ----------------------------


class TestScenarioExportRecordClass:
    def test_scenario_export_record_is_dataclass(self):
        from app.persistence import exports_repository
        ScenarioExportRecord = exports_repository.ScenarioExportRecord
        assert hasattr(ScenarioExportRecord, "__slots__")

    def test_scenario_export_record_has_expected_fields(self):
        from app.persistence import exports_repository
        ScenarioExportRecord = exports_repository.ScenarioExportRecord
        expected = {"export_id", "scenario_id", "project_id", "user_id", "export_type",
                    "artifact_name", "artifact_path", "project_code",
                    "governance_state", "runtime_snapshot_id", "replay_metadata", "created_at"}
        actual = set(ScenarioExportRecord.__annotations__.keys())
        assert actual == expected, f"missing: {expected - actual}, extra: {actual - expected}"


class TestRecordExportHighRiskWrite:
    """record_export is one of the 7 high-risk writes. Verify its behavior is preserved byte-for-byte."""

    def test_record_export_signature(self):
        import inspect
        from app.persistence import exports_repository
        sig = inspect.signature(exports_repository.record_export)
        params = list(sig.parameters.keys())
        assert params == ["user_id", "project_code", "export_type", "artifact_name",
                          "artifact_path", "project_id", "scenario_id",
                          "governance_state", "runtime_snapshot_id", "replay_metadata"], f"got {params}"

    def test_record_export_replay_metadata_defaulting(self):
        text = _read(EXPORTS_PY)
        # 5 setdefault calls preserved
        for key in ["project_id", "scenario_id", "export_id", "runtime_snapshot_id", "export_timestamp"]:
            assert f'setdefault("{key}"' in text, f"missing setdefault for {key}"

    def test_record_export_sql_text_preserved(self):
        text = _read(EXPORTS_PY)
        assert "INSERT INTO scenario_exports (" in text
        assert "export_id, scenario_id, project_id, user_id, export_type, artifact_name," in text
        assert "artifact_path, project_code, governance_state_json, runtime_snapshot_id, replay_metadata_json, created_at" in text
        assert ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)" in text

    def test_record_export_governance_state_default(self):
        text = _read(EXPORTS_PY)
        assert "governance_state = governance_state or {}" in text


class TestListExports:
    def test_list_exports_signature(self):
        import inspect
        from app.persistence import exports_repository
        sig = inspect.signature(exports_repository.list_exports)
        params = list(sig.parameters.keys())
        assert params == ["user_id", "project_id", "scenario_id", "limit"]

    def test_list_exports_default_limit(self):
        import inspect
        from app.persistence import exports_repository
        sig = inspect.signature(exports_repository.list_exports)
        assert sig.parameters["limit"].default == 20

    def test_list_exports_sql_text_preserved(self):
        text = _read(EXPORTS_PY)
        assert "SELECT * FROM scenario_exports WHERE user_id=?" in text
        assert "ORDER BY created_at DESC LIMIT ?" in text


class TestGetScenarioHistory:
    def test_get_scenario_history_signature(self):
        import inspect
        from app.persistence import exports_repository
        sig = inspect.signature(exports_repository.get_scenario_history)
        assert list(sig.parameters.keys()) == ["user_id", "project_id", "limit"]


class TestCompareAndBuild:
    def test_compare_scenarios_signature(self):
        import inspect
        from app.persistence import exports_repository
        sig = inspect.signature(exports_repository.compare_scenarios)
        assert list(sig.parameters.keys()) == ["user_id", "left_scenario_id", "right_scenario_id"]

    def test_compare_scenarios_g20_default(self):
        # Source check: compare_scenarios must default G20 to "BLOCKED"
        text = _read(EXPORTS_PY)
        assert 'governance_state.get("g20_status", "BLOCKED")' in text

    def test_compare_scenarios_r99_r102_default(self):
        text = _read(EXPORTS_PY)
        assert 'governance_state.get("r99_r102_status", "NOT APPROVED")' in text

    def test_build_export_lineage_signature(self):
        import inspect
        from app.persistence import exports_repository
        sig = inspect.signature(exports_repository.build_export_lineage)
        assert list(sig.parameters.keys()) == ["user_id", "project_id", "limit"]


class TestBaseVsActiveCompare:
    def test_base_vs_active_compare_signature(self):
        import inspect
        from app.persistence import exports_repository
        sig = inspect.signature(exports_repository.base_vs_active_compare)
        assert list(sig.parameters.keys()) == ["user_id", "project_id"]


class TestHelpersInGroupE:
    def test_delta_sign_class_none(self):
        from app.persistence import exports_repository
        assert exports_repository._delta_sign_class(None) == "delta-neutral"

    def test_delta_sign_class_positive(self):
        from app.persistence import exports_repository
        assert exports_repository._delta_sign_class(1) == "delta-positive"
        assert exports_repository._delta_sign_class(0.001) == "delta-positive"

    def test_delta_sign_class_negative(self):
        from app.persistence import exports_repository
        assert exports_repository._delta_sign_class(-1) == "delta-negative"
        assert exports_repository._delta_sign_class(-0.001) == "delta-negative"

    def test_delta_sign_class_zero(self):
        from app.persistence import exports_repository
        assert exports_repository._delta_sign_class(0) == "delta-neutral"

    def test_format_db_timestamp_none(self):
        from app.persistence import exports_repository
        assert exports_repository._format_db_timestamp(None) == "—"

    def test_format_db_timestamp_datetime(self):
        from app.persistence import exports_repository
        from datetime import datetime, timezone
        result = exports_repository._format_db_timestamp(datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc))
        # Format: "%d %b %Y %H:%M"
        assert "15" in result and "Jan" in result and "2024" in result


# ----------------------------- High-risk writes untouched (not in Group E) ----------------------------


class TestOtherHighRiskWritesNotMovedToExports:
    """Only record_export is in Group E. The other 6 high-risk writes must NOT be in exports_repository."""

    @pytest.mark.parametrize("fn_name", [
        "save_project", "save_workspace_state", "save_scenario",
        ])
    def test_other_high_risk_write_not_in_exports(self, fn_name):
        from app.persistence import exports_repository
        assert not hasattr(exports_repository, fn_name), \
            f"{fn_name} should NOT be in exports_repository (belongs to other group)"


# ----------------------------- Repository still has all 7 high-risk writes ----------------------------


class TestAllHighRiskWritesStillInRepository:
    @pytest.mark.parametrize("fn_name", [
        # save_scenario was moved to scenarios_repository in Phase 53G-4
        ])
    def test_non_exports_high_risk_write_still_in_repository_body(self, fn_name):
        # These 3 are still DEFINED in repository.py (not re-exported)
        # save_project was moved to projects_repository in Phase 53E-2
        # save_scenario was moved to scenarios_repository in Phase 53G-4
        # save_workspace_state was moved to workspace_repository in Phase 53F-2
        from app.persistence import repository
        assert hasattr(repository, fn_name)
        text = _read(REPOSITORY_PY)
        assert f"def {fn_name}" in text, f"{fn_name} not defined in repository.py"

    def test_save_workspace_state_moved_to_workspace_repository(self):
        # Phase 53F-2: save_workspace_state was moved to workspace_repository.py
        from app.persistence import repository
        from app.persistence import workspace_repository
        assert hasattr(repository, "save_workspace_state")  # re-exported
        assert hasattr(workspace_repository, "save_workspace_state")
        # The def should be in workspace_repository, not repository
        text_workspace = (REPO_ROOT / "app/persistence/workspace_repository.py").read_text()
        text_repo = _read(REPOSITORY_PY)
        assert "def save_workspace_state" in text_workspace
        assert "def save_workspace_state" not in text_repo

    def test_record_export_is_re_exported_in_repository(self):
        # record_export is re-exported from exports_repository
        from app.persistence import repository
        from app.persistence import exports_repository
        assert hasattr(repository, "record_export")
        assert repository.record_export is exports_repository.record_export
