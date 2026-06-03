"""Phase 53A — Persistence helpers extraction structural tests.

Verifies that all 10 Group F helper functions are present in the new
app/persistence/_helpers.py module and re-exported from
app/persistence/repository.py for backward compatibility.
"""
from __future__ import annotations

import ast
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HELPERS_PY = REPO_ROOT / "app" / "persistence" / "_helpers.py"
REPOSITORY_PY = REPO_ROOT / "app" / "persistence" / "repository.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


GROUP_F_FUNCTIONS = [
    "_now_utc",
    "_to_json",
    "_from_json",
    "_from_iso",
    "_safe_number",
    "_metric_value",
    "snapshots_equal",
    "_strip_empty_fields",
    "_get_least_created_scenario_for_project",
]
GROUP_F_CONSTANTS = ["SCENARIO_INPUT_FIELDS"]


# ----------------------------- Module existence ----------------------------


class TestModuleExistence:
    def test_helpers_module_exists(self):
        assert HELPERS_PY.exists(), f"missing {HELPERS_PY}"

    def test_helpers_module_is_python(self):
        text = _read(HELPERS_PY)
        # Must compile
        ast.parse(text)

    def test_repository_module_unchanged_path(self):
        assert REPOSITORY_PY.exists()


# ----------------------------- Helpers module contains all 10 functions ----------------------------


class TestHelpersModuleContent:
    @pytest.mark.parametrize("name", GROUP_F_FUNCTIONS + GROUP_F_CONSTANTS)
    def test_helpers_module_defines(self, name):
        text = _read(HELPERS_PY)
        # def name, def name(...), or name: ... = ... (for constants)
        assert re.search(rf"^(def|{re.escape(name)}\s*=)", text, re.MULTILINE), \
            f"_helpers.py does not define {name}"

    def test_helpers_module_has_get_cursor_import(self):
        text = _read(HELPERS_PY)
        assert "from app.persistence.db import get_cursor" in text

    def test_helpers_module_has_9_definitions(self):
        text = _read(HELPERS_PY)
        defs = re.findall(r"^def\s+(\w+)", text, re.MULTILINE)
        assert len(defs) == 9, f"expected 9 defs (10th is constant), got {len(defs)}: {defs}"

    def test_helpers_module_includes_scenario_input_fields_with_21_keys(self):
        text = _read(HELPERS_PY)
        m = re.search(r"SCENARIO_INPUT_FIELDS:\s*set\[str\]\s*=\s*\{([^}]+)\}", text, re.DOTALL)
        assert m, "SCENARIO_INPUT_FIELDS not found in expected form"
        keys = re.findall(r'"(\w+)"', m.group(1))
        assert len(keys) == 21, f"expected 21 keys, got {len(keys)}"


# ----------------------------- Repository compatibility façade ----------------------------


class TestRepositoryFacade:
    @pytest.mark.parametrize("name", GROUP_F_FUNCTIONS + GROUP_F_CONSTANTS)
    def test_repository_re_exports_function(self, name):
        from app.persistence import repository
        assert hasattr(repository, name), f"repository.py missing re-export of {name}"

    @pytest.mark.parametrize("name", GROUP_F_FUNCTIONS)
    def test_repository_and_helpers_share_same_object(self, name):
        from app.persistence import repository
        from app.persistence import _helpers
        # The repository re-export and the helpers definition should be the same object
        assert getattr(repository, name) is getattr(_helpers, name), \
            f"repository.{name} is not the same object as _helpers.{name}"

    def test_repository_has_import_block_for_helpers(self):
        text = _read(REPOSITORY_PY)
        assert "from app.persistence._helpers import" in text

    def test_repository_no_longer_imports_json(self):
        # The `import json` line was removed from repository.py
        # (json is still used in _helpers.py)
        text = _read(REPOSITORY_PY)
        # Use a regex that matches "import json" not "import json..."
        # We expect it NOT to be there as a top-level import
        # Look for "^import json" at start of line
        for line in text.splitlines():
            if line.startswith("import json"):
                pytest.fail(f"repository.py still has 'import json': {line!r}")


# ----------------------------- Behavior preservation ----------------------------


class TestBehaviorPreserved:
    def test_now_utc_returns_utc_datetime(self):
        from app.persistence import repository
        result = repository._now_utc()
        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_to_json_empty_dict(self):
        from app.persistence import repository
        result = repository._to_json({})
        assert result == "{}"

    def test_to_json_none_returns_empty_object(self):
        from app.persistence import repository
        result = repository._to_json(None)
        parsed = json.loads(result)
        assert parsed == {}

    def test_to_json_sorts_keys(self):
        from app.persistence import repository
        # b before a in insertion order
        result = repository._to_json({"b": 1, "a": 2})
        assert result == '{"a": 2, "b": 1}'

    def test_from_json_none_returns_default(self):
        from app.persistence import repository
        result = repository._from_json(None, "default")
        assert result == "default"

    def test_from_json_empty_string_returns_default(self):
        from app.persistence import repository
        result = repository._from_json("", "default")
        assert result == "default"

    def test_from_json_valid_string_parses(self):
        from app.persistence import repository
        result = repository._from_json('{"a": 1}', {})
        assert result == {"a": 1}

    def test_from_iso_passes_through_datetime(self):
        from app.persistence import repository
        dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
        result = repository._from_iso(dt)
        assert result is dt

    def test_from_iso_parses_string(self):
        from app.persistence import repository
        result = repository._from_iso("2024-01-01T00:00:00+00:00")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1

    def test_safe_number_none(self):
        from app.persistence import repository
        assert repository._safe_number(None) is None

    def test_safe_number_empty_string(self):
        from app.persistence import repository
        assert repository._safe_number("") is None

    def test_safe_number_invalid_string(self):
        from app.persistence import repository
        assert repository._safe_number("abc") is None

    def test_safe_number_valid_string(self):
        from app.persistence import repository
        assert repository._safe_number("3.14") == 3.14

    def test_safe_number_int(self):
        from app.persistence import repository
        assert repository._safe_number(42) == 42.0

    def test_safe_number_not_available(self):
        from app.persistence import repository
        assert repository._safe_number("NOT_AVAILABLE") is None

    def test_safe_number_missing(self):
        from app.persistence import repository
        assert repository._safe_number("MISSING") is None

    def test_snapshots_equal_same(self):
        from app.persistence import repository
        assert repository.snapshots_equal({"a": 1}, {"a": 1}) is True

    def test_snapshots_equal_different(self):
        from app.persistence import repository
        assert repository.snapshots_equal({"a": 1}, {"a": 2}) is False

    def test_snapshots_equal_handles_none(self):
        from app.persistence import repository
        assert repository.snapshots_equal(None, {"a": 1}) is False
        assert repository.snapshots_equal({"a": 1}, None) is False
        assert repository.snapshots_equal(None, None) is True

    def test_strip_empty_fields(self):
        from app.persistence import repository
        result = repository._strip_empty_fields({"a": 1, "b": "", "c": "x"})
        assert result == {"a": 1, "c": "x"}

    def test_strip_empty_fields_handles_none(self):
        from app.persistence import repository
        result = repository._strip_empty_fields(None)
        assert result == {}

    def test_scenario_input_fields_contains_known_keys(self):
        from app.persistence import repository
        s = repository.SCENARIO_INPUT_FIELDS
        assert "project_name" in s
        assert "capacity_mw" in s
        assert "tariff_eur_mwh" in s
        assert "gearing_pct" in s
        assert "target_dscr" in s
        assert isinstance(s, set)


# ----------------------------- High-risk writes untouched ----------------------------


class TestHighRiskWritesUntouched:
    """Group F extraction must not touch any high-risk write function."""

    @pytest.mark.parametrize("fn_name", [
        "save_project", "save_workspace_state", "save_scenario",
        "add_scenario", "update_scenario_overrides",
        "get_or_create_base_case_scenario",
    ])
    def test_high_risk_write_still_in_repository(self, fn_name):
        from app.persistence import repository
        assert hasattr(repository, fn_name), f"{fn_name} missing from repository"
        # And it should be a function defined in repository.py, not in _helpers.py
        text = _read(REPOSITORY_PY)
        assert f"def {fn_name}" in text, f"{fn_name} not defined in repository.py"
