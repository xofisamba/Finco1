"""Phase 53G-1 — P0 behavior pin for get_or_create_base_case_scenario.

Pins the current behavior of get_or_create_base_case_scenario (one of
the 7 high-risk writes) BEFORE Group B extraction in 53G-7.

Pinned:

- signature: 8 params, 6 required + 2 optional
- SELECT existing: WHERE is_base_case=1 AND archived=0
- If exists: returns ScenarioRecord.from_row(row)
- If not exists: INSERT with is_base_case=1, parent_scenario_id=NULL,
  schema_version='1.0', overrides_json={}, last_run_summary_json={}
- replay_metadata.is_base_case = True
- Returns the new ScenarioRecord with is_base_case=True
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_PY = REPO_ROOT / "app" / "persistence" / "repository.py"
SCENARIOS_PY = REPO_ROOT / "app" / "persistence" / "scenarios_repository.py"
# After Phase 53G-7, get_or_create_base_case_scenario lives in scenarios_repository.py
PIN_TARGET = SCENARIOS_PY


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestBaseCaseImport:
    def test_importable(self):
        from app.persistence.repository import get_or_create_base_case_scenario
        assert callable(get_or_create_base_case_scenario)


class TestBaseCaseSignature:
    def test_signature(self):
        from app.persistence.repository import get_or_create_base_case_scenario
        sig = inspect.signature(get_or_create_base_case_scenario)
        params = sig.parameters
        # 9 params: 8 required + 1 optional
        assert len(params) == 9
        for required in ("user_id", "project_id", "project_code", "project_name",
                         "project_type", "source_project_template",
                         "base_input_set", "governance_state"):
            assert required in params
            assert params[required].default is inspect.Parameter.empty
        # 1 optional: replay_metadata
        assert params["replay_metadata"].default is None

    def test_return_type(self):
        from app.persistence.repository import get_or_create_base_case_scenario
        hints = get_or_create_base_case_scenario.__annotations__
        ret = hints.get("return", "").strip("'\"")
        assert "ScenarioRecord" in ret


class TestBaseCaseBody:
    @pytest.fixture
    def body(self):
        return _read(PIN_TARGET)

    def test_function_defined(self, body: str):
        # After Phase 53G-7, get_or_create_base_case_scenario lives in scenarios_repository.py
        assert "def get_or_create_base_case_scenario(" in body

    def test_function_not_defined_in_repository(self):
        # The def should NOT be in repository.py
        text_repo = _read(REPOSITORY_PY)
        assert "def get_or_create_base_case_scenario" not in text_repo

    def test_select_existing_with_is_base_case_1(self, body: str):
        m = re.search(r"def get_or_create_base_case_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "is_base_case=1" in body_text
        assert "archived=0" in body_text

    def test_returns_existing_via_from_row(self, body: str):
        m = re.search(r"def get_or_create_base_case_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "return ScenarioRecord.from_row(row)" in body_text

    def test_replay_metadata_setdefault(self, body: str):
        m = re.search(r"def get_or_create_base_case_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert 'rm.setdefault("project_id", project_id)' in body_text
        assert 'rm.setdefault("scenario_id", scenario_id)' in body_text

    def test_replay_metadata_is_base_case_true(self, body: str):
        m = re.search(r"def get_or_create_base_case_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert 'rm["is_base_case"] = True' in body_text

    def test_uses_two_transactions(self, body: str):
        m = re.search(r"def get_or_create_base_case_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        n = body_text.count("with get_cursor() as cur:")
        assert n == 2, f"Expected 2 transactions (SELECT + INSERT), got {n}"


class TestBaseCaseSql:
    @pytest.fixture
    def body(self):
        return _read(PIN_TARGET)

    def test_select_sql(self, body: str):
        m = re.search(r"def get_or_create_base_case_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "SELECT * FROM scenarios" in body_text
        assert "WHERE user_id=? AND project_id=? AND is_base_case=1 AND archived=0" in body_text
        assert "LIMIT 1" in body_text

    def test_insert_columns(self, body: str):
        m = re.search(r"def get_or_create_base_case_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        # The 19 columns
        for col in [
            "scenario_id", "project_id", "user_id", "scenario_name", "project_code",
            "source_project_template", "copied_from_scenario_id", "archived",
            "is_base_case", "parent_scenario_id",
            "base_input_set_json", "overrides_json", "schema_version",
            "snapshot_json", "governance_state_json", "last_run_summary_json",
            "replay_metadata_json", "created_at", "updated_at",
        ]:
            assert col in body_text, f"Missing column: {col}"

    def test_insert_is_base_case_1(self, body: str):
        m = re.search(r"def get_or_create_base_case_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        # is_base_case = 1
        assert "1, 1, NULL" in body_text or ", 1, NULL" in body_text

    def test_insert_schema_version_1_0(self, body: str):
        m = re.search(r"def get_or_create_base_case_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "'1.0'" in body_text

    def test_insert_overrides_empty(self, body: str):
        m = re.search(r"def get_or_create_base_case_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        # overrides_json = {}
        assert "_to_json({})" in body_text


class TestBaseCaseReturns:
    @pytest.fixture
    def body(self):
        return _read(PIN_TARGET)

    def test_returned_scenario_has_is_base_case_true(self, body: str):
        m = re.search(r"def get_or_create_base_case_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "is_base_case=True," in body_text

    def test_returned_scenario_name_fallback(self, body: str):
        m = re.search(r"def get_or_create_base_case_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        # If no name, defaults to "Base Case"
        assert '"Base Case"' in body_text or "'Base Case'" in body_text
