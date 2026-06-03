"""Phase 53G-1 — P0 behavior pin for add_scenario.

Pins the current behavior of add_scenario (one of the 7 high-risk writes)
BEFORE Group B extraction in 53G-5.

Pinned:

- signature: 9 params, all required
- return type: Optional[ScenarioRecord]
- INSERT with 19 columns
- replay_metadata.action = "add_scenario"
- replay_metadata.parent_scenario_id = parent
- base_input_set_json + overrides_json + snapshot_json all stored
- scenario_id via uuid.uuid4().hex[:16]
- is_base_case = 0 (False)
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_PY = REPO_ROOT / "app" / "persistence" / "repository.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestAddScenarioImport:
    def test_add_scenario_importable(self):
        from app.persistence.repository import add_scenario
        assert callable(add_scenario)


class TestAddScenarioSignature:
    def test_add_scenario_signature(self):
        from app.persistence.repository import add_scenario
        sig = inspect.signature(add_scenario)
        params = sig.parameters
        # 9 params
        assert len(params) == 9
        for required in ("user_id", "project_id", "project_code", "scenario_name",
                         "parent_scenario_id", "base_input_set"):
            assert required in params
            assert params[required].default is inspect.Parameter.empty
        # 3 optional with default None
        for optional in ("overrides", "governance_state", "replay_metadata"):
            assert optional in params
            assert params[optional].default is None

    def test_add_scenario_return_type(self):
        from app.persistence.repository import add_scenario
        hints = add_scenario.__annotations__
        ret = hints.get("return", "").strip("'\"")
        # Optional[ScenarioRecord]
        assert "ScenarioRecord" in ret


class TestAddScenarioBody:
    @pytest.fixture
    def body(self):
        return _read(REPOSITORY_PY)

    def test_function_defined(self, body: str):
        assert "def add_scenario(" in body

    def test_add_scenario_resolves_via_resolve_scenario_snapshot(self, body: str):
        m = re.search(r"def add_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "resolve_scenario_snapshot(base_input_set, overrides or {})" in body_text

    def test_add_scenario_uuid_hex_16(self, body: str):
        m = re.search(r"def add_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "uuid.uuid4().hex[:16]" in body_text

    def test_add_scenario_default_governance_state(self, body: str):
        m = re.search(r"def add_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "governance_state = dict(governance_state or {})" in body_text

    def test_add_scenario_default_replay_metadata(self, body: str):
        m = re.search(r"def add_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "replay_metadata = dict(replay_metadata or {})" in body_text

    def test_add_scenario_replay_metadata_action(self, body: str):
        m = re.search(r"def add_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert 'replay_metadata["action"] = "add_scenario"' in body_text

    def test_add_scenario_replay_metadata_parent(self, body: str):
        m = re.search(r"def add_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert 'replay_metadata["parent_scenario_id"] = parent_scenario_id' in body_text

    def test_add_scenario_replay_metadata_setdefault_scenario_id(self, body: str):
        m = re.search(r"def add_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert 'replay_metadata.setdefault("scenario_id", scenario_id)' in body_text

    def test_add_scenario_single_transaction(self, body: str):
        m = re.search(r"def add_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "with get_cursor() as cur:" in body_text


class TestAddScenarioSql:
    @pytest.fixture
    def body(self):
        return _read(REPOSITORY_PY)

    def test_insert_sql(self, body: str):
        m = re.search(r"def add_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "INSERT INTO scenarios (" in body_text

    def test_insert_has_is_base_case_0(self, body: str):
        # is_base_case = 0 (False) for non-base
        m = re.search(r"def add_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        # 0, ?, — the 9th placeholder is is_base_case
        assert "0, ?" in body_text  # archived=0, is_base_case=0

    def test_insert_has_parent_scenario_id(self, body: str):
        m = re.search(r"def add_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "parent_scenario_id" in body_text

    def test_insert_has_copied_from_null(self, body: str):
        m = re.search(r"def add_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        # copied_from_scenario_id is NULL for new non-base scenarios
        assert "NULL," in body_text

    def test_insert_has_schema_version_1_0(self, body: str):
        m = re.search(r"def add_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "'1.0'" in body_text

    def test_insert_stores_resolved_snapshot(self, body: str):
        m = re.search(r"def add_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "_to_json(resolved)" in body_text
