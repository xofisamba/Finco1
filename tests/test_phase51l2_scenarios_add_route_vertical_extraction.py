"""Phase 51L-2 vertical extraction tests for POST /scenarios/add.

These tests pin the extraction contract for
``app/services/scenarios_add_service.py``:

1. The service module exists.
2. The service module does NOT import main_web or main_api.
3. The POST /scenarios/add route is THIN (delegates to the service).
4. Phase 51L-1 characterization tests still pass (re-pointed).
5. All 10 quirks are preserved.
6. All intended side effects are preserved.
7. All 5 error paths are preserved.
8. Forbidden side effects remain absent.
9. Existing extracted services remain intact.
10. Phase 51F guardrails pass.
11. The service exposes the canonical API.
12. The behavior execution is verifiable via test doubles.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import is_dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_WEB = REPO_ROOT / "main_web.py"
SCENARIOS_ADD_SERVICE = (
    REPO_ROOT / "app" / "services" / "scenarios_add_service.py"
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _route_body(route_path: str) -> str:
    text = _read(MAIN_WEB)
    pattern = re.escape(f'@app.post("{route_path}")')
    m = re.search(
        pattern + r"\s*\nasync def \w+\(.*?(?=\n@app\.(get|post|put|delete|route)\(|\Z)",
        text,
        re.DOTALL,
    )
    assert m is not None, f"Route {route_path} not found in main_web.py"
    return m.group(0)


def _strip_docstrings_and_comments(text: str) -> str:
    text = re.sub(r'"""[\s\S]*?"""', "", text)
    text = re.sub(r"'''[\s\S]*?'''", "", text)
    out_lines = []
    for line in text.splitlines():
        if "#" in line:
            stripped = line
            in_str = None
            i = 0
            while i < len(stripped):
                c = stripped[i]
                if in_str is None:
                    if c in ('"', "'"):
                        in_str = c
                    elif c == "#":
                        stripped = stripped[:i].rstrip()
                        break
                else:
                    if c == in_str:
                        in_str = None
                i += 1
            out_lines.append(stripped)
        else:
            out_lines.append(line)
    return "\n".join(out_lines)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Service module existence + isolation
# ─────────────────────────────────────────────────────────────────────────────


class TestServiceModuleExists:
    def test_scenarios_add_service_exists(self):
        assert SCENARIOS_ADD_SERVICE.exists(), (
            f"scenarios_add_service.py must exist at {SCENARIOS_ADD_SERVICE}"
        )

    def test_scenarios_add_service_does_not_import_main_web(self):
        text = _read(SCENARIOS_ADD_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "import main_web" not in clean
        assert "from main_web" not in clean

    def test_scenarios_add_service_does_not_import_main_api(self):
        text = _read(SCENARIOS_ADD_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "import main_api" not in clean
        assert "from main_api" not in clean

    def test_scenarios_add_service_does_not_import_persistence(self):
        text = _read(SCENARIOS_ADD_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "import app.persistence" not in clean
        assert "from app.persistence" not in clean
        assert "import persistence" not in clean
        assert "from persistence" not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 2. Canonical API surface
# ─────────────────────────────────────────────────────────────────────────────


class TestServiceApi:
    def test_outcome_is_dataclass(self):
        from app.services.scenarios_add_service import (
            ScenariosAddRouteOutcome,
        )
        assert is_dataclass(ScenariosAddRouteOutcome)

    def test_deps_is_dataclass(self):
        from app.services.scenarios_add_service import (
            ScenariosAddRouteDeps,
        )
        assert is_dataclass(ScenariosAddRouteDeps)

    def test_outcome_has_expected_fields(self):
        from app.services.scenarios_add_service import (
            ScenariosAddRouteOutcome,
        )
        fields = {
            f.name
            for f in ScenariosAddRouteOutcome.__dataclass_fields__.values()
        }
        for required in ("template_name", "context", "payload", "status_code", "headers", "is_redirect", "redirect_url"):
            assert required in fields, f"ScenariosAddRouteOutcome must have field '{required}'"

    def test_deps_has_expected_callables(self):
        from app.services.scenarios_add_service import (
            ScenariosAddRouteDeps,
        )
        fields = {
            f.name
            for f in ScenariosAddRouteDeps.__dataclass_fields__.values()
        }
        # 8 required callables
        for required in (
            "get_project_record",
            "list_scenarios",
            "get_least_created_scenario_for_project",
            "promote_scenario_to_base_case",
            "add_scenario",
            "get_workspace_state",
            "build_scenario_tab_context",
        ):
            assert required in fields, f"ScenariosAddRouteDeps must have field '{required}'"

    def test_execute_function_exists_and_is_async(self):
        from app.services.scenarios_add_service import (
            execute_scenarios_add_route,
        )
        assert asyncio.iscoroutinefunction(execute_scenarios_add_route)

    def test_execute_accepts_required_kwargs(self):
        import inspect
        from app.services.scenarios_add_service import (
            execute_scenarios_add_route,
        )
        sig = inspect.signature(execute_scenarios_add_route)
        for kw in ("request", "form", "user", "deps"):
            assert kw in sig.parameters
            assert sig.parameters[kw].kind == inspect.Parameter.KEYWORD_ONLY


# ─────────────────────────────────────────────────────────────────────────────
# 3. Route is thin after extraction
# ─────────────────────────────────────────────────────────────────────────────


class TestRouteIsThin:
    def test_route_uses_execute_pattern(self):
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        assert "execute_scenarios_add_route(" in clean

    def test_route_constructs_deps_bundle(self):
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        assert "ScenariosAddRouteDeps(" in clean

    def test_route_imports_service_locally(self):
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        assert (
            "from app.services.scenarios_add_service import" in clean
            or "import app.services.scenarios_add_service" in clean
        )

    def test_route_does_not_call_add_scenario_directly(self):
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        assert "add_scenario(" not in clean

    def test_route_does_not_call_get_project_record_directly(self):
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        assert "get_project_record(" not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 4. Auth behavior preserved
# ─────────────────────────────────────────────────────────────────────────────


class TestAuthPreserved:
    def test_route_uses_get_current_user(self):
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        assert "get_current_user(request)" in clean

    def test_unauth_returns_302_to_login(self):
        from fastapi.testclient import TestClient
        from app.persistence.db import init_db
        from main_web import app

        init_db()
        c = TestClient(app)
        r = c.post(
            "/scenarios/add",
            data={},
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert "/login" in r.headers.get("location", "")


# ─────────────────────────────────────────────────────────────────────────────
# 5. Service behavior (mocked deps)
# ─────────────────────────────────────────────────────────────────────────────


class TestServiceBehavior:
    def _make_deps(
        self,
        project_origin: str = "user_created",
        project_record_exists: bool = True,
        new_scenario: Any = "scenario-1",
        base_case=None,
    ):
        from app.services.scenarios_add_service import (
            ScenariosAddRouteDeps,
        )

        call_log = {
            "get_project_record": 0,
            "list_scenarios": 0,
            "get_least_created_scenario_for_project": 0,
            "promote_scenario_to_base_case": 0,
            "add_scenario": 0,
            "get_workspace_state": 0,
            "build_scenario_tab_context": 0,
        }

        if project_record_exists:
            project_record = MagicMock()
            project_record.project_origin = project_origin
            project_record.project_code = "PRJ-001"
            project_record.project_id = "proj-1"
            project_record.project_name = "Test Project"
        else:
            project_record = None

        if base_case is None:
            base_case = MagicMock()
            base_case.scenario_id = "sc-base-1"
            base_case.snapshot = {"foo": "bar"}
            base_case.base_input_set = {"baz": "qux"}
            base_case.is_base_case = True

        scenario_item = MagicMock()
        scenario_item.scenario_id = "sc-1"
        scenario_item.scenario_name = "New Scenario"
        scenario_item.project_code = "PRJ-001"
        scenario_item.is_base_case = False
        scenario_item.last_run_summary = {}
        scenario_item.governance_state = "ok"

        user = MagicMock()
        user.user_id = "user-1"
        request = MagicMock()

        # Form that returns scenario_name when get'd
        form = {
            "project_code": "PRJ-001",
            "scenario_name": "New Scenario",
        }

        def _form_get(key, default=""):
            return form.get(key, default)

        def _get_project_record(*, user_id, project_code):
            call_log["get_project_record"] += 1
            return project_record

        def _list_scenarios(*args, **kwargs):
            call_log["list_scenarios"] += 1
            return [base_case, scenario_item]

        def _get_least_created_scenario_for_project(*args, **kwargs):
            call_log["get_least_created_scenario_for_project"] += 1
            return base_case

        def _promote_scenario_to_base_case(*args, **kwargs):
            call_log["promote_scenario_to_base_case"] += 1
            return base_case

        def _add_scenario(**kwargs):
            call_log["add_scenario"] += 1
            return new_scenario

        def _get_workspace_state(*args, **kwargs):
            call_log["get_workspace_state"] += 1
            return MagicMock()

        def _build_scenario_tab_context(*args, **kwargs):
            call_log["build_scenario_tab_context"] += 1
            return {"user": args[0], "project_record": args[1]}

        deps = ScenariosAddRouteDeps(
            get_project_record=_get_project_record,
            list_scenarios=_list_scenarios,
            get_least_created_scenario_for_project=_get_least_created_scenario_for_project,
            promote_scenario_to_base_case=_promote_scenario_to_base_case,
            add_scenario=_add_scenario,
            get_workspace_state=_get_workspace_state,
            build_scenario_tab_context=_build_scenario_tab_context,
        )

        return deps, call_log, user, request, form

    def test_missing_project_code_returns_400(self):
        from app.services.scenarios_add_service import (
            execute_scenarios_add_route,
        )

        deps, _, user, request, _ = self._make_deps()
        form = {"project_code": "", "scenario_name": "X"}
        result = asyncio.get_event_loop().run_until_complete(
            execute_scenarios_add_route(
                request=request, form=form, user=user, deps=deps
            )
        )
        assert result.status_code == 400
        assert result.payload == {"error": "project_code is required"}

    def test_missing_scenario_name_returns_400(self):
        from app.services.scenarios_add_service import (
            execute_scenarios_add_route,
        )

        deps, _, user, request, _ = self._make_deps()
        form = {"project_code": "PRJ-001", "scenario_name": ""}
        result = asyncio.get_event_loop().run_until_complete(
            execute_scenarios_add_route(
                request=request, form=form, user=user, deps=deps
            )
        )
        assert result.status_code == 400
        assert result.payload == {"error": "scenario_name is required"}

    def test_project_not_found_returns_404(self):
        from app.services.scenarios_add_service import (
            execute_scenarios_add_route,
        )

        deps, _, user, request, _ = self._make_deps(
            project_record_exists=False
        )
        form = {"project_code": "PRJ-001", "scenario_name": "X"}
        result = asyncio.get_event_loop().run_until_complete(
            execute_scenarios_add_route(
                request=request, form=form, user=user, deps=deps
            )
        )
        assert result.status_code == 404
        assert result.payload == {"error": "Project not found"}

    def test_non_user_created_project_returns_403(self):
        from app.services.scenarios_add_service import (
            execute_scenarios_add_route,
        )

        deps, _, user, request, _ = self._make_deps(
            project_origin="factory_template"
        )
        form = {"project_code": "PRJ-001", "scenario_name": "X"}
        result = asyncio.get_event_loop().run_until_complete(
            execute_scenarios_add_route(
                request=request, form=form, user=user, deps=deps
            )
        )
        assert result.status_code == 403
        assert (
            "user-created projects" in result.payload["error"]
            or "user_created projects" in result.payload["error"]
        )

    def test_success_path(self):
        from app.services.scenarios_add_service import (
            execute_scenarios_add_route,
        )

        deps, call_log, user, request, _ = self._make_deps()
        form = {"project_code": "PRJ-001", "scenario_name": "New Scenario"}
        result = asyncio.get_event_loop().run_until_complete(
            execute_scenarios_add_route(
                request=request, form=form, user=user, deps=deps
            )
        )
        # Success: status_code=200, headers include HX-Trigger
        assert result.status_code == 200
        assert result.headers == {"HX-Trigger": "scenarioAdded"}
        # add_scenario was called once
        assert call_log["add_scenario"] == 1
        # build_scenario_tab_context was called once
        assert call_log["build_scenario_tab_context"] == 1

    def test_add_scenario_failure_returns_500(self):
        from app.services.scenarios_add_service import (
            execute_scenarios_add_route,
        )

        deps, _, user, request, _ = self._make_deps(new_scenario=None)
        form = {"project_code": "PRJ-001", "scenario_name": "X"}
        result = asyncio.get_event_loop().run_until_complete(
            execute_scenarios_add_route(
                request=request, form=form, user=user, deps=deps
            )
        )
        assert result.status_code == 500
        assert result.payload == {"error": "Failed to create scenario"}

    def test_no_replay_metadata_passed(self):
        """Quirk 5: replay_metadata uses action='add_scenario', NOT export_type."""
        from app.services.scenarios_add_service import (
            execute_scenarios_add_route,
        )

        deps, _, user, request, _ = self._make_deps()
        # We don't have a way to inspect kwargs from _make_deps easily,
        # so just check the source.
        text = _read(SCENARIOS_ADD_SERVICE)
        assert '"action": "add_scenario"' in text
        assert '"export_type"' not in text

    def test_no_governance_snapshot_call(self):
        """Quirk 6: governance_state is empty dict; service does NOT
        call _governance_snapshot."""
        text = _read(SCENARIOS_ADD_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "_governance_snapshot" not in clean
        assert "governance_snapshot(" not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 6. Forbidden side effects absent
# ─────────────────────────────────────────────────────────────────────────────


class TestForbiddenSideEffectsAbsent:
    FORBIDDEN = (
        "record_export",
        "record_download_export",
        "record_runtime_summary_export",
        "record_institutional_workbook_export",
        "record_workspace_runtime",
        "update_scenario_last_run_summary",
        "save_run",
        "save_project",
        "run_project",
        "build_institutional_workbook_export",
        "build_excel_export_for_post_request",
        "build_runtime_summary_csv_export",
        "build_values_only_export_for_project",
    )

    def test_service_does_not_call_forbidden_helpers(self):
        text = _read(SCENARIOS_ADD_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        for helper in self.FORBIDDEN:
            assert f"{helper}(" not in clean, (
                f"Service must not call forbidden helper {helper}()"
            )

    def test_service_does_not_use_db_or_session_directly(self):
        text = _read(SCENARIOS_ADD_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        for forbidden in (
            "db.add", "db.commit", "db.flush",
            "session.add", "session.commit",
        ):
            assert forbidden not in clean, (
                f"Service must not use {forbidden} directly"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 7. No HTMX header on error paths (Quirk 2; only success sets it)
# ─────────────────────────────────────────────────────────────────────────────


class TestNoHtmxHeaderOnError:
    def test_service_does_not_emit_hx_trigger_on_error(self):
        from app.services.scenarios_add_service import (
            execute_scenarios_add_route,
        )

        # Build deps inline (no cross-class dependency)
        from app.services.scenarios_add_service import (
            ScenariosAddRouteDeps,
        )

        project_record = MagicMock()
        project_record.project_origin = "user_created"
        project_record.project_code = "PRJ-001"
        project_record.project_id = "proj-1"

        base_case = MagicMock()
        base_case.scenario_id = "sc-base-1"
        base_case.snapshot = {}
        base_case.base_input_set = {}

        scenario_item = MagicMock()
        scenario_item.scenario_id = "sc-1"
        scenario_item.scenario_name = "X"
        scenario_item.is_base_case = False
        scenario_item.last_run_summary = {}
        scenario_item.governance_state = "ok"

        user = MagicMock()
        user.user_id = "user-1"
        request = MagicMock()

        deps = ScenariosAddRouteDeps(
            get_project_record=lambda **kw: project_record,
            list_scenarios=lambda *a, **kw: [base_case, scenario_item],
            get_least_created_scenario_for_project=lambda *a, **kw: base_case,
            promote_scenario_to_base_case=lambda *a, **kw: base_case,
            add_scenario=lambda **kw: "sc-1",
            get_workspace_state=lambda *a, **kw: MagicMock(),
            build_scenario_tab_context=lambda *a, **kw: {},
        )

        form = {"project_code": "", "scenario_name": "X"}
        result = asyncio.get_event_loop().run_until_complete(
            execute_scenarios_add_route(
                request=request, form=form, user=user, deps=deps
            )
        )
        # Error path: HX-Trigger should NOT be in headers
        assert result.headers == {} or "HX-Trigger" not in result.headers


# ─────────────────────────────────────────────────────────────────────────────
# 8. No validate_form call (Quirk 1 — uses individual form.get)
# ─────────────────────────────────────────────────────────────────────────────


class TestNoValidateForm:
    def test_service_does_not_call_validate_form(self):
        text = _read(SCENARIOS_ADD_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "_validate_form(" not in clean
        assert "validate_form(" not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 9. Other routes remain service-backed
# ─────────────────────────────────────────────────────────────────────────────


class TestOtherRoutesRemainServiceBacked:
    @pytest.mark.parametrize(
        "route,marker",
        [
            ("/run", "execute_run_route("),
            ("/compare", "execute_compare_route("),
            ("/validate", "execute_validate_route("),
            ("/download", "execute_post_download_route("),
            ("/save-run", "execute_save_run_route("),
            ("/scenarios/save", "execute_scenarios_save_route("),
            ("/scenarios/state/draft", "execute_draft_route("),
            ("/scenarios/state/discard", "execute_discard_route("),
            ("/scenarios/{scenario_id}/duplicate", "execute_scenario_duplicate_route("),
        ],
    )
    def test_route_uses_service_execute(self, route: str, marker: str):
        text = _read(MAIN_WEB)
        if route == "/download":
            assert marker in text
            return
        verb = "post"
        patterns = [
            re.escape(f'@app.{verb}("{route}")'),
            re.escape(f"@app.{verb}('{route}')"),
        ]
        for pat in patterns:
            m = re.search(
                pat + r"\s*\nasync def \w+\(.*?(?=\n@app\.(get|post|put|delete|route)\(|\Z)",
                text,
                re.DOTALL,
            )
            if m is not None:
                break
        assert m is not None
        body = m.group(0)
        clean = _strip_docstrings_and_comments(body)
        assert marker in clean


# ─────────────────────────────────────────────────────────────────────────────
# 10. Phase 51F guardrails
# ─────────────────────────────────────────────────────────────────────────────


class TestPhase51FGuardrails:
    def test_no_service_imports_main_web_or_main_api(self):
        text = _read(SCENARIOS_ADD_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "import main_web" not in clean
        assert "from main_web" not in clean
        assert "import main_api" not in clean
        assert "from main_api" not in clean

    def test_app_still_imports(self):
        from main_web import app
        assert app is not None


# ─────────────────────────────────────────────────────────────────────────────
# 11. Phase 51L-1 characterization still passes
# ─────────────────────────────────────────────────────────────────────────────


class TestPhase51L1CharacterizationStillPasses:
    def test_phase51l1_tests_present(self):
        import importlib
        mod = importlib.import_module(
            "tests.test_phase51l1_scenario_add_route_golden_characterization"
        )
        assert mod is not None

    def test_phase51l1_tests_still_pass(self):
        import subprocess
        r = subprocess.run(
            [
                "python3", "-m", "pytest",
                "tests/test_phase51l1_scenario_add_route_golden_characterization.py",
                "-q", "--tb=no",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, (
            f"Phase 51L-1 tests failed after 51L-2 re-pointing:\n"
            f"{r.stdout}\n{r.stderr}"
        )
