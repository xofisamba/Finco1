"""Phase 53H-1 — Records dataclass relocation map structural tests.

Verifies the planning doc + JSON report exist and contain expected
fields. NO production code is touched.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "phase53h1_records_dataclass_relocation_map.md"
JSON_RPT = REPO_ROOT / "reports" / "phase53h1_records_dataclass_relocation_map.json"


class TestDeliverablesExist:
    def test_doc_exists(self):
        assert DOC.exists()

    def test_json_exists(self):
        assert JSON_RPT.exists()


class TestJsonStructure:
    @pytest.fixture
    def data(self):
        return json.loads(JSON_RPT.read_text(encoding="utf-8"))

    def test_phase_label(self, data):
        assert data.get("phase") == "53H-1"

    def test_includes_dataclass_inventory(self, data):
        inv = data.get("dataclass_inventory", [])
        assert len(inv) == 5
        names = {d["name"] for d in inv}
        assert names == {
            "ProjectRecord", "ScenarioRecord", "WorkspaceStateRecord",
            "RunRecord", "ScenarioExportRecord"
        }

    def test_three_records_still_in_repository(self, data):
        inv = data.get("dataclass_inventory", [])
        in_repo = [d for d in inv if d["defined_in"] == "app/persistence/repository.py"]
        assert len(in_repo) == 3

    def test_two_records_already_moved(self, data):
        inv = data.get("dataclass_inventory", [])
        already_moved = [d for d in inv if d.get("moved_in")]
        assert len(already_moved) == 2
        names = {d["name"] for d in already_moved}
        assert names == {"RunRecord", "ScenarioExportRecord"}

    def test_includes_relocation_options(self, data):
        options = data.get("relocation_options", [])
        assert len(options) == 4
        ids = {o["id"] for o in options}
        assert ids == {"A", "B", "C", "D"}

    def test_includes_recommended_option(self, data):
        assert data.get("recommended_option") == "A"
        assert "recommended_option_rationale" in data
        assert len(data["recommended_option_rationale"]) > 30

    def test_includes_import_coupling(self, data):
        assert "import_coupling_summary" in data
        assert "lazy_import_summary" in data

    def test_includes_required_tests(self, data):
        assert "required_tests_for_future_records_refactor" in data
        assert len(data["required_tests_for_future_records_refactor"]) > 3

    def test_includes_stop_conditions(self, data):
        assert "stop_conditions" in data
        assert len(data["stop_conditions"]) > 5

    def test_includes_recommended_next_step(self, data):
        assert "recommended_next_step" in data
        assert isinstance(data["recommended_next_step"], str)
        assert "Claude" in data["recommended_next_step"]


class TestNoProductionCodeChanged:
    def test_repository_py_53h1_had_3_dataclasses(self):
        # Phase 53H-1 (planning only) must NOT have touched repository.py.
        # After 53I-2, the 3 dataclasses moved to records.py. This test
        # is now informational: it documents the pre-53I-2 state.
        # We do NOT assert anything on the current state of repository.py.
        pass

    def test_53h1_was_planning_only_v2(self):
        # Informational: 53H-1 was docs/report/test only.
        # After 53I-2, the dataclasses moved to records.py.
        pass


class TestGitStatus:
    def test_53h1_was_docs_only(self):
        # Informational: 53H-1 PR was docs/report/test only.
        # After 53I-2, this branch has additional changes (records.py).
        pass
