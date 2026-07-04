"""Phase 53G-1 — P0 behavior pin for save_scenario.

Pins the current behavior of save_scenario (one of the 7 high-risk writes)
BEFORE Group B extraction in 53G-4.

Pinned:

- signature: 10 params
- return type: ScenarioRecord
- INSERT-only (no UPSERT)
- replay_metadata.setdefault for project_id and scenario_id
- Single-transaction pattern
- 14 INSERT columns
- 13 VALUES placeholders
- uuid.uuid4().hex[:16] for scenario_id
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_PY = REPO_ROOT / "app" / "persistence" / "repository.py"
SCENARIOS_PY = REPO_ROOT / "app" / "persistence" / "scenarios_repository.py"
# After Phase 53G-4, save_scenario lives in scenarios_repository.py
PIN_TARGET = SCENARIOS_PY


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestSaveScenarioImport:
    def test_save_scenario_importable_from_repository(self):
        from app.persistence.repository import save_scenario
        assert callable(save_scenario)


class TestSaveScenarioSignature:
    def test_save_scenario_signature(self):
        from app.persistence.repository import save_scenario
        sig = inspect.signature(save_scenario)
        params = sig.parameters
        # 11 params: user_id, project_id, scenario_name, project_code,
        # source_project_template, snapshot, governance_state, last_run_summary,
        # copied_from_scenario_id, replay_metadata, full_inputs (V3-8)
        assert len(params) == 11
        for required in ("user_id", "project_id", "scenario_name",
                         "project_code", "source_project_template", "snapshot"):
            assert required in params
            assert params[required].default is inspect.Parameter.empty
        for optional, default in [
            ("governance_state", None),
            ("last_run_summary", None),
            ("copied_from_scenario_id", None),
            ("replay_metadata", None),
        ]:
            assert optional in params
            assert params[optional].default == default

    def test_save_scenario_return_type(self):
        from app.persistence.repository import save_scenario
        hints = save_scenario.__annotations__
        ret = hints.get("return", "").strip("'\"")
        assert ret == "ScenarioRecord"


class TestSaveScenarioBody:
    @pytest.fixture
    def body(self):
        return _read(PIN_TARGET)

    def test_function_defined_in_scenarios_repository(self, body: str):
        # After Phase 53G-4, save_scenario lives in scenarios_repository.py
        assert "def save_scenario(" in body

    def test_function_not_defined_in_repository(self):
        # The def should be in scenarios_repository, not repository
        text_repo = _read(REPOSITORY_PY)
        assert "def save_scenario" not in text_repo

    def test_save_scenario_uses_uuid_hex_16(self, body: str):
        m = re.search(r"def save_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "uuid.uuid4().hex[:16]" in body_text

    def test_save_scenario_uses_now_utc(self, body: str):
        m = re.search(r"def save_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "_now_utc()" in body_text

    def test_save_scenario_default_governance_state_to_empty_dict(self, body: str):
        m = re.search(r"def save_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "governance_state = governance_state or {}" in body_text

    def test_save_scenario_default_last_run_summary_to_empty_dict(self, body: str):
        m = re.search(r"def save_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "last_run_summary = last_run_summary or {}" in body_text

    def test_save_scenario_default_replay_metadata_via_dict(self, body: str):
        m = re.search(r"def save_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "replay_metadata = dict(replay_metadata or {})" in body_text

    def test_save_scenario_replay_metadata_setdefault(self, body: str):
        m = re.search(r"def save_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert 'replay_metadata.setdefault("project_id", project_id)' in body_text
        assert 'replay_metadata.setdefault("scenario_id", scenario_id)' in body_text

    def test_save_scenario_uses_single_transaction(self, body: str):
        m = re.search(r"def save_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "with get_cursor() as cur:" in body_text

    def test_save_scenario_returns_scenario_record(self, body: str):
        m = re.search(r"def save_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "return ScenarioRecord(" in body_text


class TestSaveScenarioSql:
    @pytest.fixture
    def body(self):
        return _read(PIN_TARGET)

    def test_insert_sql(self, body: str):
        m = re.search(r"def save_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "INSERT INTO scenarios (" in body_text

    def test_insert_columns_count(self, body: str):
        m = re.search(r"def save_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        # 14 columns in the INSERT
        cols = [
            "scenario_id", "project_id", "user_id", "scenario_name", "project_code",
            "source_project_template", "copied_from_scenario_id", "archived",
            "snapshot_json", "governance_state_json", "last_run_summary_json", "replay_metadata_json",
            "created_at", "updated_at",
        ]
        for col in cols:
            assert col in body_text, f"Missing column: {col}"

    def test_insert_archived_0(self, body: str):
        # archived is set to 0 (False) at insert
        m = re.search(r"def save_scenario\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "0, 0," in body_text or "VALUES (?, ?, ?, ?, ?, ?, ?, 0, " in body_text
