"""Phase 53B — Run persistence extraction structural tests.

Verifies that the 6 Group D items (1 class + 5 functions) are present
in the new app/persistence/runs_repository.py module and re-exported
from app/persistence/repository.py for backward compatibility.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNS_PY = REPO_ROOT / "app" / "persistence" / "runs_repository.py"
REPOSITORY_PY = REPO_ROOT / "app" / "persistence" / "repository.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


GROUP_D_NAMES = [
    "RunRecord", "save_run", "get_run", "list_runs", "delete_run", "count_runs",
]
GROUP_D_FUNCTIONS = ["save_run", "get_run", "list_runs", "delete_run", "count_runs"]


# ----------------------------- Module existence ----------------------------


class TestModuleExistence:
    def test_runs_module_exists(self):
        assert RUNS_PY.exists()

    def test_runs_module_is_python(self):
        text = _read(RUNS_PY)
        ast.parse(text)


# ----------------------------- Runs module content ----------------------------


class TestRunsModuleContent:
    @pytest.mark.parametrize("name", GROUP_D_NAMES)
    def test_runs_module_defines(self, name):
        text = _read(RUNS_PY)
        assert re.search(rf"^(def {re.escape(name)}|class {re.escape(name)})", text, re.MULTILINE), \
            f"runs_repository.py does not define {name}"

    def test_runs_module_has_get_cursor_import(self):
        text = _read(RUNS_PY)
        assert "from app.persistence.db import get_cursor" in text

    def test_runs_module_imports_helpers(self):
        text = _read(RUNS_PY)
        assert "from app.persistence._helpers import" in text

    def test_runs_module_has_5_functions_and_1_class(self):
        text = _read(RUNS_PY)
        defs = re.findall(r"^def\s+(\w+)", text, re.MULTILINE)
        classes = re.findall(r"^class\s+(\w+)", text, re.MULTILINE)
        assert len(defs) == 5, f"expected 5 functions, got {len(defs)}"
        assert classes == ["RunRecord"], f"expected 1 class RunRecord, got {classes}"


# ----------------------------- Repository compatibility façade ----------------------------


class TestRepositoryFacade:
    @pytest.mark.parametrize("name", GROUP_D_NAMES)
    def test_repository_re_exports(self, name):
        from app.persistence import repository
        assert hasattr(repository, name), f"repository.py missing re-export of {name}"

    @pytest.mark.parametrize("name", GROUP_D_NAMES)
    def test_repository_and_runs_share_same_object(self, name):
        from app.persistence import repository
        from app.persistence import runs_repository
        assert getattr(repository, name) is getattr(runs_repository, name), \
            f"repository.{name} is not the same object as runs_repository.{name}"

    def test_repository_has_import_block_for_runs(self):
        text = _read(REPOSITORY_PY)
        assert "from app.persistence.runs_repository import" in text


# ----------------------------- Behavior preservation ----------------------------


class TestRunRecordClass:
    def test_run_record_is_dataclass(self):
        from app.persistence import runs_repository
        RunRecord = runs_repository.RunRecord
        # Should have slots
        assert hasattr(RunRecord, "__slots__")

    def test_run_record_has_expected_fields(self):
        from app.persistence import runs_repository
        RunRecord = runs_repository.RunRecord
        # Use __annotations__ to check fields
        expected = {"run_id", "user_id", "project_type", "scenario", "created_at",
                    "inputs", "kpis", "excel_path", "notes", "replay_metadata"}
        actual = set(RunRecord.__annotations__.keys())
        assert actual == expected, f"missing: {expected - actual}, extra: {actual - expected}"


class TestSaveRun:
    def test_save_run_signature(self):
        import inspect
        from app.persistence import runs_repository
        sig = inspect.signature(runs_repository.save_run)
        params = list(sig.parameters.keys())
        assert params == ["user_id", "project_type", "scenario", "inputs", "kpis",
                          "excel_path", "notes", "replay_metadata"], f"got {params}"

    def test_save_run_returns_run_record(self):
        from app.persistence import runs_repository
        RunRecord = runs_repository.RunRecord
        # Check return type annotation by string form
        import inspect
        sig = inspect.signature(runs_repository.save_run)
        # The return_annotation is the string 'RunRecord' (forward ref) due to
        # the local-class pattern. We check the class name instead.
        ann = sig.return_annotation
        if isinstance(ann, str):
            assert ann == "RunRecord"
        else:
            assert ann is RunRecord

    def test_save_run_replay_metadata_defaulting(self):
        # Read the source and verify the defaulting pattern is preserved
        text = _read(RUNS_PY)
        # Should have setdefault for run_id and runtime_timestamp
        assert 'setdefault("run_id"' in text
        assert 'setdefault("runtime_timestamp"' in text

    def test_save_run_sql_text_preserved(self):
        text = _read(RUNS_PY)
        # Verify the INSERT INTO runs SQL is byte-for-byte preserved
        assert "INSERT INTO runs (run_id, user_id, project_type, scenario, created_at, inputs_json, kpis_json, excel_path, notes, replay_metadata_json)" in text


class TestGetRunListRun:
    def test_get_run_signature(self):
        import inspect
        from app.persistence import runs_repository
        sig = inspect.signature(runs_repository.get_run)
        assert list(sig.parameters.keys()) == ["run_id", "user_id"]

    def test_list_runs_signature(self):
        import inspect
        from app.persistence import runs_repository
        sig = inspect.signature(runs_repository.list_runs)
        assert list(sig.parameters.keys()) == ["user_id", "limit"]
        # Default value of limit is 20
        assert sig.parameters["limit"].default == 20

    def test_list_runs_sql_text_preserved(self):
        text = _read(RUNS_PY)
        assert "SELECT * FROM runs WHERE user_id=? ORDER BY created_at DESC LIMIT ?" in text

    def test_get_run_sql_text_preserved(self):
        text = _read(RUNS_PY)
        assert "SELECT * FROM runs WHERE run_id=? AND user_id=?" in text


class TestDeleteRunCountRun:
    def test_delete_run_signature(self):
        import inspect
        from app.persistence import runs_repository
        sig = inspect.signature(runs_repository.delete_run)
        assert list(sig.parameters.keys()) == ["run_id", "user_id"]

    def test_delete_run_sql_text_preserved(self):
        text = _read(RUNS_PY)
        assert "DELETE FROM runs WHERE run_id=? AND user_id=?" in text

    def test_count_runs_signature(self):
        import inspect
        from app.persistence import runs_repository
        sig = inspect.signature(runs_repository.count_runs)
        assert list(sig.parameters.keys()) == ["user_id"]

    def test_count_runs_sql_text_preserved(self):
        text = _read(RUNS_PY)
        assert "SELECT COUNT(*) FROM runs WHERE user_id=?" in text


# ----------------------------- High-risk writes untouched ----------------------------


class TestHighRiskWritesUntouched:
    @pytest.mark.parametrize("fn_name", [
        # save_scenario was moved to scenarios_repository in Phase 53G-4
        ])
    def test_high_risk_write_still_in_repository(self, fn_name):
        from app.persistence import repository
        assert hasattr(repository, fn_name), f"{fn_name} missing from repository"
        text = _read(REPOSITORY_PY)
        assert f"def {fn_name}" in text, f"{fn_name} not defined in repository.py"
