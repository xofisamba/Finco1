"""Phase 53G-1 — P0 behavior pin for update_scenario_overrides.

Pins the current behavior of update_scenario_overrides (one of the 7
high-risk writes) BEFORE Group B extraction in 53G-6.

Pinned:

- signature: 3 params (user_id, scenario_id, overrides)
- return type: Optional[ScenarioRecord]
- Rejects base-case scenarios (returns None)
- Filters overrides to SCENARIO_INPUT_FIELDS only (silently drops unknown)
- Re-resolves effective snapshot via resolve_scenario_snapshot
- Atomic UPDATE on overrides_json, snapshot_json, updated_at
- Returns the updated ScenarioRecord with merged overrides and resolved snapshot
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


class TestUpdateOverridesImport:
    def test_update_scenario_overrides_importable(self):
        from app.persistence.repository import update_scenario_overrides
        assert callable(update_scenario_overrides)


class TestUpdateOverridesSignature:
    def test_signature(self):
        from app.persistence.repository import update_scenario_overrides
        sig = inspect.signature(update_scenario_overrides)
        params = sig.parameters
        assert len(params) == 3
        for required in ("user_id", "scenario_id", "overrides"):
            assert required in params
            assert params[required].default is inspect.Parameter.empty

    def test_return_type(self):
        from app.persistence.repository import update_scenario_overrides
        hints = update_scenario_overrides.__annotations__
        ret = hints.get("return", "").strip("'\"")
        assert "ScenarioRecord" in ret


class TestUpdateOverridesBody:
    @pytest.fixture
    def body(self):
        return _read(REPOSITORY_PY)

    def test_function_defined(self, body: str):
        assert "def update_scenario_overrides(" in body

    def test_calls_get_scenario_first(self, body: str):
        m = re.search(r"def update_scenario_overrides\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "record = get_scenario(scenario_id, user_id)" in body_text

    def test_returns_none_if_scenario_missing(self, body: str):
        m = re.search(r"def update_scenario_overrides\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "if record is None:" in body_text
        assert "return None" in body_text

    def test_returns_none_for_base_case(self, body: str):
        m = re.search(r"def update_scenario_overrides\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "if record.is_base_case:" in body_text
        assert "return None  # base-case overrides" in body_text

    def test_filters_to_scenario_input_fields(self, body: str):
        m = re.search(r"def update_scenario_overrides\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "if key in SCENARIO_INPUT_FIELDS:" in body_text

    def test_merges_existing_overrides(self, body: str):
        m = re.search(r"def update_scenario_overrides\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "merged = dict(record.overrides)" in body_text

    def test_re_resolves_snapshot(self, body: str):
        m = re.search(r"def update_scenario_overrides\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "resolve_scenario_snapshot(record.base_input_set, merged)" in body_text

    def test_uses_now_utc(self, body: str):
        m = re.search(r"def update_scenario_overrides\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "now = _now_utc()" in body_text

    def test_uses_single_transaction(self, body: str):
        m = re.search(r"def update_scenario_overrides\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "with get_cursor() as cur:" in body_text

    def test_returns_record_with_merged_overrides(self, body: str):
        m = re.search(r"def update_scenario_overrides\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "record.overrides = merged" in body_text
        assert "record.snapshot = resolved" in body_text
        assert "record.updated_at = now" in body_text
        assert "return record" in body_text


class TestUpdateOverridesSql:
    @pytest.fixture
    def body(self):
        return _read(REPOSITORY_PY)

    def test_update_sql(self, body: str):
        m = re.search(r"def update_scenario_overrides\(.*?(?=\n\ndef |\Z)", body, re.DOTALL)
        body_text = m.group(0)
        assert "UPDATE scenarios" in body_text
        assert "SET overrides_json=?, snapshot_json=?, updated_at=?" in body_text
        assert "WHERE scenario_id=? AND user_id=?" in body_text
