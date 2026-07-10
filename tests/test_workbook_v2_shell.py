"""
Tests for the Workbook V2 feature-flagged shell (PR 5).

Covers:
- Flag-off: /v2/workbook route is NOT registered when FINCO_WORKBOOK_V2 is unset.
- Flag-on:  /v2/workbook route IS registered when FINCO_WORKBOOK_V2=1.
- Router module imports cleanly (no circular imports, no engine side effects).
- v2 router uses WorkbookService.build_draft_input_set_from_workspace (not saved).
- v2 router uses WorkbookService.runtime_hydration_script for sessionStorage.
- Template context keys are correct.
- No legacy ambiguous helpers (_collect_form_snapshot, _strip_empty_fields) used.
"""
from __future__ import annotations

import importlib
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clear_v2_import_cache() -> None:
    """Remove app.v2 modules from sys.modules so re-import is clean."""
    for key in list(sys.modules.keys()):
        if "app.v2" in key or key == "main_web":
            del sys.modules[key]


def _make_ws(project_code: str = "tuho") -> MagicMock:
    ws = MagicMock()
    ws.draft_snapshot = {
        "project_name": "Test",
        "capex_meur": "100",
        "template_source": project_code,
    }
    ws.saved_snapshot = {
        "project_name": "Test",
        "capex_meur": "80",
        "template_source": project_code,
    }
    ws.project_code = project_code
    ws.last_runtime_snapshot_id = "20260710T120000Z"
    ws.last_runtime_summary = {"project_irr": 0.08}
    ws.last_runtime_at = None
    ws.last_runtime_origin = "saved_state"
    ws.last_financial_statements = {}
    ws.last_debt_schedule = {}
    ws.last_tax_schedule = {}
    ws.last_distribution_schedule = {}
    ws.last_sponsor_schedule = {}
    return ws


# ---------------------------------------------------------------------------
# Router module contract
# ---------------------------------------------------------------------------

class TestV2RouterModule(unittest.TestCase):

    def test_router_module_imports_cleanly(self):
        from app.v2 import router as router_mod
        self.assertIsNotNone(router_mod)

    def test_router_object_exists(self):
        from app.v2.router import router
        from fastapi import APIRouter
        self.assertIsInstance(router, APIRouter)

    def test_v2_workbook_route_registered(self):
        from app.v2.router import router
        paths = [r.path for r in router.routes]
        self.assertIn("/workbook", paths)

    def test_router_does_not_call_legacy_snapshot_helpers(self):
        import app.v2.router as mod
        # Strip the module docstring before checking — the docstring may
        # mention these names as scope constraints ("No legacy X").
        # What must not appear is an actual call or import.
        src = open(mod.__file__).read()
        # Everything after the closing triple-quote of the module docstring.
        code_body = src.split('"""', 2)[-1]
        self.assertNotIn("_collect_form_snapshot", code_body)
        self.assertNotIn("_strip_empty_fields", code_body)

    def test_router_does_not_import_waterfall_runner(self):
        import app.v2.router as mod
        src = open(mod.__file__).read()
        self.assertNotIn("WaterfallRunner", src)
        self.assertNotIn("run_project", src)

    def test_router_uses_workbook_service(self):
        import app.v2.router as mod
        src = open(mod.__file__).read()
        self.assertIn("WorkbookService", src)

    def test_router_uses_draft_method_not_saved(self):
        import app.v2.router as mod
        src = open(mod.__file__).read()
        self.assertIn("build_draft_input_set_from_workspace", src)
        self.assertNotIn("build_saved_input_set_from_workspace", src)

    def test_router_uses_runtime_hydration_script(self):
        import app.v2.router as mod
        src = open(mod.__file__).read()
        self.assertIn("runtime_hydration_script", src)


# ---------------------------------------------------------------------------
# Feature flag gate in main_web.py
# ---------------------------------------------------------------------------

class TestFeatureFlagGate(unittest.TestCase):

    def _routes_from_main_web(self, flag_value: str | None):
        """Import main_web with a given env flag value and return route paths."""
        _clear_v2_import_cache()
        env = os.environ.copy()
        if flag_value is None:
            env.pop("FINCO_WORKBOOK_V2", None)
        else:
            env["FINCO_WORKBOOK_V2"] = flag_value

        with patch.dict(os.environ, env, clear=True):
            import main_web as mw
            paths = set()
            for route in mw.app.routes:
                p = getattr(route, "path", None)
                if p:
                    paths.add(p)
            return paths

    def test_flag_off_no_v2_routes(self):
        paths = self._routes_from_main_web(None)
        v2_paths = {p for p in paths if p.startswith("/v2")}
        self.assertEqual(v2_paths, set(), f"Expected no /v2 routes, got {v2_paths}")

    def test_flag_empty_string_no_v2_routes(self):
        paths = self._routes_from_main_web("")
        v2_paths = {p for p in paths if p.startswith("/v2")}
        self.assertEqual(v2_paths, set())

    def test_flag_on_1_registers_v2_workbook(self):
        paths = self._routes_from_main_web("1")
        self.assertIn("/v2/workbook", paths)

    def test_flag_on_true_registers_v2_workbook(self):
        paths = self._routes_from_main_web("true")
        self.assertIn("/v2/workbook", paths)

    def test_flag_on_yes_registers_v2_workbook(self):
        paths = self._routes_from_main_web("yes")
        self.assertIn("/v2/workbook", paths)

    def test_flag_off_legacy_index_still_present(self):
        paths = self._routes_from_main_web(None)
        self.assertIn("/", paths)

    def test_flag_on_legacy_index_still_present(self):
        paths = self._routes_from_main_web("1")
        self.assertIn("/", paths)


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------

class TestV2Template(unittest.TestCase):

    def _template_path(self) -> str:
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(here, "app", "templates", "v2", "workbook.html")

    def test_template_file_exists(self):
        self.assertTrue(os.path.isfile(self._template_path()))

    def test_template_has_hydration_script_slot(self):
        content = open(self._template_path()).read()
        self.assertIn("hydration_script", content)

    def test_template_has_project_data_attributes(self):
        content = open(self._template_path()).read()
        self.assertIn("data-project", content)
        self.assertIn("data-workbook-version", content)
        self.assertIn("data-content-hash", content)

    def test_template_has_v2_shell_root(self):
        content = open(self._template_path()).read()
        self.assertIn("v2-workbook-shell", content)


if __name__ == "__main__":
    unittest.main()
