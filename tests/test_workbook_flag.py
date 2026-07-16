"""Unit tests for app.utils.workbook_flag — flag parsing, URL helper, inactive guard.

Tests cover:
  - env_flag(): absent/truthy/falsy/unknown values
  - workbook_v2_active() and inputs_slice1_active(): default-on when absent
  - project_workbook_url(): URL encoding, sheet param
  - require_v2_active(): returns 409 when V2 is inactive
"""
from __future__ import annotations

import os

import pytest


# ---------------------------------------------------------------------------
# env_flag
# ---------------------------------------------------------------------------

class TestEnvFlag:
    def _call(self, name: str, default: bool, env_val: str | None) -> bool:
        from app.utils.workbook_flag import env_flag
        original = os.environ.pop(name, None)
        try:
            if env_val is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = env_val
            return env_flag(name, default=default)
        finally:
            if original is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = original

    @pytest.mark.parametrize("val", ["1", "true", "TRUE", "yes", "YES", "on", "ON"])
    def test_truthy_values(self, val):
        assert self._call("_TEST_FLAG", default=False, env_val=val) is True

    @pytest.mark.parametrize("val", ["0", "false", "FALSE", "no", "NO", "off", "OFF"])
    def test_falsy_values(self, val):
        assert self._call("_TEST_FLAG", default=True, env_val=val) is False

    def test_absent_uses_default_true(self):
        assert self._call("_TEST_FLAG", default=True, env_val=None) is True

    def test_absent_uses_default_false(self):
        assert self._call("_TEST_FLAG", default=False, env_val=None) is False

    def test_empty_string_uses_default(self):
        assert self._call("_TEST_FLAG", default=True, env_val="") is True

    def test_whitespace_stripped(self):
        assert self._call("_TEST_FLAG", default=False, env_val="  1  ") is True

    def test_unknown_value_returns_false(self):
        assert self._call("_TEST_FLAG", default=True, env_val="maybe") is False


# ---------------------------------------------------------------------------
# workbook_v2_active / inputs_slice1_active — default-on semantics
# ---------------------------------------------------------------------------

class TestDefaultOnFlags:
    def _set(self, name: str, val: str | None):
        if val is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = val

    def test_workbook_v2_active_absent(self, monkeypatch):
        monkeypatch.delenv("FINCO_WORKBOOK_V2", raising=False)
        from app.utils.workbook_flag import workbook_v2_active
        assert workbook_v2_active() is True

    def test_workbook_v2_active_truthy(self, monkeypatch):
        monkeypatch.setenv("FINCO_WORKBOOK_V2", "1")
        from app.utils.workbook_flag import workbook_v2_active
        assert workbook_v2_active() is True

    def test_workbook_v2_active_falsy(self, monkeypatch):
        monkeypatch.setenv("FINCO_WORKBOOK_V2", "0")
        from app.utils.workbook_flag import workbook_v2_active
        assert workbook_v2_active() is False

    def test_inputs_slice1_active_absent(self, monkeypatch):
        monkeypatch.delenv("FINCO_INPUTS_SLICE1_ENABLED", raising=False)
        from app.utils.workbook_flag import inputs_slice1_active
        assert inputs_slice1_active() is True

    def test_inputs_slice1_active_truthy(self, monkeypatch):
        monkeypatch.setenv("FINCO_INPUTS_SLICE1_ENABLED", "true")
        from app.utils.workbook_flag import inputs_slice1_active
        assert inputs_slice1_active() is True

    def test_inputs_slice1_active_falsy(self, monkeypatch):
        monkeypatch.setenv("FINCO_INPUTS_SLICE1_ENABLED", "false")
        from app.utils.workbook_flag import inputs_slice1_active
        assert inputs_slice1_active() is False


# ---------------------------------------------------------------------------
# project_workbook_url
# ---------------------------------------------------------------------------

class TestProjectWorkbookUrl:
    def test_basic(self):
        from app.utils.workbook_flag import project_workbook_url
        url = project_workbook_url("PROJ-01")
        assert url == "/v2/workbook?project=PROJ-01"

    def test_with_sheet(self):
        from app.utils.workbook_flag import project_workbook_url
        url = project_workbook_url("PROJ-01", sheet="inputs")
        assert "project=PROJ-01" in url
        assert "sheet=inputs" in url
        assert url.startswith("/v2/workbook?")

    def test_url_encodes_project_code(self):
        from app.utils.workbook_flag import project_workbook_url
        url = project_workbook_url("MY PROJECT")
        assert "MY+PROJECT" in url or "MY%20PROJECT" in url

    def test_empty_code_gives_empty_param(self):
        from app.utils.workbook_flag import project_workbook_url
        url = project_workbook_url("")
        assert "project=" in url

    def test_no_sheet_param_when_none(self):
        from app.utils.workbook_flag import project_workbook_url
        url = project_workbook_url("ABC")
        assert "sheet=" not in url


# ---------------------------------------------------------------------------
# TestInactiveSurfaceGuard — require_v2_active raises 409 when inactive
# ---------------------------------------------------------------------------

class TestInactiveSurfaceGuard:
    """Verify the FastAPI dependency rejects requests when V2 is inactive."""

    def test_require_v2_active_raises_when_inactive(self, monkeypatch):
        monkeypatch.setenv("FINCO_WORKBOOK_V2", "0")
        import importlib
        import app.utils.workbook_flag as wf
        importlib.reload(wf)  # re-evaluate with new env
        from fastapi import HTTPException

        import asyncio
        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(wf.require_v2_active())
        assert exc_info.value.status_code == 409

    def test_require_v2_active_passes_when_active(self, monkeypatch):
        monkeypatch.setenv("FINCO_WORKBOOK_V2", "1")
        import importlib
        import app.utils.workbook_flag as wf
        importlib.reload(wf)
        import asyncio
        # Should not raise
        asyncio.get_event_loop().run_until_complete(wf.require_v2_active())

    def test_require_v2_active_passes_when_absent(self, monkeypatch):
        monkeypatch.delenv("FINCO_WORKBOOK_V2", raising=False)
        import importlib
        import app.utils.workbook_flag as wf
        importlib.reload(wf)
        import asyncio
        # Absent → active → no raise
        asyncio.get_event_loop().run_until_complete(wf.require_v2_active())
