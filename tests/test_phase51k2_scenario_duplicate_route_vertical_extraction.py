"""Phase 51K-2 vertical extraction tests for POST /scenarios/{scenario_id}/duplicate.

These tests pin the extraction contract for
``app/services/scenario_duplicate_service.py``:

1. The service module exists.
2. The service module does NOT import main_web or main_api.
3. The POST /scenarios/{scenario_id}/duplicate route is THIN
   (delegates to the service).
4. Phase 51K-1 characterization tests still pass (re-pointed).
5. All characterized behaviors are preserved.
6. All 10 quirks are preserved.
7. Intended side effects are preserved.
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
SCENARIO_DUPLICATE_SERVICE = (
    REPO_ROOT / "app" / "services" / "scenario_duplicate_service.py"
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _route_body(route_path: str) -> str:
    text = _read(MAIN_WEB)
    patterns = [
        re.escape(f'@app.post("{route_path}")'),
        re.escape(f"@app.post('{route_path}')"),
    ]
    for pat in patterns:
        m = re.search(
            pat + r"\s*\nasync def \w+\(.*?(?=\n@app\.(get|post|put|delete|route)\(|\Z)",
            text,
            re.DOTALL,
        )
        if m is not None:
            return m.group(0)
    raise AssertionError(f"Route {route_path} not found in main_web.py")


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
    def test_scenario_duplicate_service_exists(self):
        assert SCENARIO_DUPLICATE_SERVICE.exists(), (
            f"scenario_duplicate_service.py must exist at {SCENARIO_DUPLICATE_SERVICE}"
        )

    def test_scenario_duplicate_service_does_not_import_main_web(self):
        text = _read(SCENARIO_DUPLICATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "import main_web" not in clean
        assert "from main_web" not in clean

    def test_scenario_duplicate_service_does_not_import_main_api(self):
        text = _read(SCENARIO_DUPLICATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "import main_api" not in clean
        assert "from main_api" not in clean

    def test_scenario_duplicate_service_does_not_import_persistence(self):
        text = _read(SCENARIO_DUPLICATE_SERVICE)
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
        from app.services.scenario_duplicate_service import (
            ScenarioDuplicateRouteOutcome,
        )
        assert is_dataclass(ScenarioDuplicateRouteOutcome)

    def test_deps_is_dataclass(self):
        from app.services.scenario_duplicate_service import (
            ScenarioDuplicateRouteDeps,
        )
        assert is_dataclass(ScenarioDuplicateRouteDeps)

    def test_outcome_has_expected_fields(self):
        from app.services.scenario_duplicate_service import (
            ScenarioDuplicateRouteOutcome,
        )
        fields = {
            f.name
            for f in ScenarioDuplicateRouteOutcome.__dataclass_fields__.values()
        }
        for required in ("template_name", "context", "payload", "status_code", "headers", "is_redirect", "redirect_url"):
            assert required in fields, f"ScenarioDuplicateRouteOutcome must have field '{required}'"

    def test_deps_has_expected_callables(self):
        from app.services.scenario_duplicate_service import (
            ScenarioDuplicateRouteDeps,
        )
        fields = {
            f.name
            for f in ScenarioDuplicateRouteDeps.__dataclass_fields__.values()
        }
        # 9 required callables
        for required in (
            "get_scenario",
            "duplicate_scenario",
            "get_project_by_code",
            "list_scenarios",
            "get_scenario_history",
            "list_exports",
            "build_export_lineage",
            "get_workspace_state",
            "render_scenario_workspace",
        ):
            assert required in fields, f"ScenarioDuplicateRouteDeps must have field '{required}'"

    def test_execute_function_exists_and_is_async(self):
        from app.services.scenario_duplicate_service import (
            execute_scenario_duplicate_route,
        )
        assert asyncio.iscoroutinefunction(execute_scenario_duplicate_route)

    def test_execute_accepts_required_kwargs(self):
        import inspect
        from app.services.scenario_duplicate_service import (
            execute_scenario_duplicate_route,
        )
        sig = inspect.signature(execute_scenario_duplicate_route)
        for kw in ("request", "scenario_id", "user", "deps"):
            assert kw in sig.parameters, f"execute must accept '{kw}'"
            assert sig.parameters[kw].kind == inspect.Parameter.KEYWORD_ONLY, (
                f"execute's '{kw}' must be keyword-only"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Route is thin after extraction
# ─────────────────────────────────────────────────────────────────────────────


class TestRouteIsThin:
    def test_route_uses_execute_pattern(self):
        body = _route_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert "execute_scenario_duplicate_route(" in clean

    def test_route_constructs_deps_bundle(self):
        body = _route_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert "ScenarioDuplicateRouteDeps(" in clean

    def test_route_imports_service_locally(self):
        body = _route_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert (
            "from app.services.scenario_duplicate_service import" in clean
            or "import app.services.scenario_duplicate_service" in clean
        )

    def test_route_does_not_call_duplicate_scenario_directly(self):
        body = _route_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        # Should only appear in deps bundle, not as a callable call
        assert "duplicate_scenario(" not in clean

    def test_route_does_not_call_get_scenario_directly(self):
        body = _route_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert "get_scenario(" not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 4. Auth behavior preserved
# ─────────────────────────────────────────────────────────────────────────────


class TestAuthPreserved:
    def test_route_uses_get_current_user(self):
        body = _route_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert "get_current_user(request)" in clean

    def test_unauth_returns_302_to_login(self):
        from fastapi.testclient import TestClient
        from app.persistence.db import init_db
        from main_web import app

        init_db()
        c = TestClient(app)
        r = c.post(
            "/scenarios/some-id/duplicate",
            data={},
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert "/login" in r.headers.get("location", "")


# ─────────────────────────────────────────────────────────────────────────────
# 5. Service behavior (mocked deps)
# ─────────────────────────────────────────────────────────────────────────────


class TestServiceBehavior:
    def _make_deps(self, original_scenario="default"):
        from app.services.scenario_duplicate_service import (
            ScenarioDuplicateRouteDeps,
        )

        call_log = {
            "get_scenario": 0,
            "duplicate_scenario": 0,
            "get_project_by_code": 0,
            "list_scenarios": 0,
            "get_scenario_history": 0,
            "list_exports": 0,
            "build_export_lineage": 0,
            "get_workspace_state": 0,
            "render_scenario_workspace": 0,
        }

        # Use a sentinel to distinguish "default" (create a real
        # MagicMock) from "explicit None" (return None for 404 path).
        if original_scenario == "default":
            original_scenario = MagicMock()
            original_scenario.scenario_id = "sc-orig-123"
            original_scenario.scenario_name = "Test Scenario"
            original_scenario.project_code = "PRJ-001"
            original_scenario.project_id = "proj-456"
        # If original_scenario is None, the get_scenario mock
        # returns None (404 path).

        project_record = MagicMock()
        project_record.project_code = "PRJ-001"

        scenario_item = MagicMock()
        scenario_item.scenario_id = "sc-new-789"
        scenario_item.scenario_name = "Test Scenario (copy)"
        scenario_item.project_code = "PRJ-001"
        scenario_item.updated_at = "2026-06-03T00:00:00"
        scenario_item.copied_from_scenario_id = "sc-orig-123"
        scenario_item.last_run_summary = {
            "project_irr": 0.15, "equity_irr": 0.20, "avg_dscr": 1.4
        }
        scenario_item.governance_state = "ok"

        user = MagicMock()
        user.user_id = "user-999"

        request = MagicMock()

        def _get_scenario(scenario_id_arg, user_id_arg):
            call_log["get_scenario"] += 1
            return original_scenario

        def _duplicate_scenario(user_id_arg, scenario_id_arg):
            call_log["duplicate_scenario"] += 1

        def _get_project_by_code(user_id_arg, project_code_arg):
            call_log["get_project_by_code"] += 1
            return project_record

        def _list_scenarios(*args, **kwargs):
            call_log["list_scenarios"] += 1
            return [scenario_item]

        def _get_scenario_history(*args, **kwargs):
            call_log["get_scenario_history"] += 1
            return []

        def _list_exports(*args, **kwargs):
            call_log["list_exports"] += 1
            return []

        def _build_export_lineage(*args, **kwargs):
            call_log["build_export_lineage"] += 1
            return [
                {"scenario_name": "Test Scenario (copy)"},
                {"scenario_name": "Test Scenario (copy)"},
                {"scenario_name": "Other"},
            ]

        def _get_workspace_state(*args, **kwargs):
            call_log["get_workspace_state"] += 1
            return MagicMock()

        def _render_scenario_workspace(*args, **kwargs):
            call_log["render_scenario_workspace"] += 1
            return MagicMock(name="rendered_workspace")

        deps = ScenarioDuplicateRouteDeps(
            get_scenario=_get_scenario,
            duplicate_scenario=_duplicate_scenario,
            get_project_by_code=_get_project_by_code,
            list_scenarios=_list_scenarios,
            get_scenario_history=_get_scenario_history,
            list_exports=_list_exports,
            build_export_lineage=_build_export_lineage,
            get_workspace_state=_get_workspace_state,
            render_scenario_workspace=_render_scenario_workspace,
        )

        return deps, call_log, user, request

    def test_success_branch_calls_duplicate_scenario_once(self):
        from app.services.scenario_duplicate_service import (
            execute_scenario_duplicate_route,
        )

        deps, call_log, user, request = self._make_deps()
        result = asyncio.get_event_loop().run_until_complete(
            execute_scenario_duplicate_route(
                request=request, scenario_id="sc-orig-123", user=user, deps=deps
            )
        )
        assert result is not None
        assert call_log["duplicate_scenario"] == 1

    def test_404_branch_does_not_duplicate(self):
        from app.services.scenario_duplicate_service import (
            execute_scenario_duplicate_route,
        )

        deps, call_log, user, request = self._make_deps(original_scenario=None)
        result = asyncio.get_event_loop().run_until_complete(
            execute_scenario_duplicate_route(
                request=request, scenario_id="nonexistent", user=user, deps=deps
            )
        )
        assert result.status_code == 404
        assert result.payload == {"error": "Scenario not found"}
        assert call_log["duplicate_scenario"] == 0
        assert call_log["get_project_by_code"] == 0
        assert call_log["list_scenarios"] == 0
        assert call_log["render_scenario_workspace"] == 0

    def test_read_only_queries_called_once_each(self):
        from app.services.scenario_duplicate_service import (
            execute_scenario_duplicate_route,
        )

        deps, call_log, user, request = self._make_deps()
        asyncio.get_event_loop().run_until_complete(
            execute_scenario_duplicate_route(
                request=request, scenario_id="sc-orig-123", user=user, deps=deps
            )
        )
        assert call_log["list_scenarios"] == 1
        assert call_log["get_scenario_history"] == 1
        assert call_log["list_exports"] == 1
        assert call_log["build_export_lineage"] == 1

    def test_success_message_includes_original_scenario_name(self):
        from app.services.scenario_duplicate_service import (
            execute_scenario_duplicate_route,
        )

        deps, _, user, request = self._make_deps()
        render_calls = []
        original = deps.render_scenario_workspace

        def _tracking(*args, **kwargs):
            render_calls.append((args, kwargs))
            return original(*args, **kwargs)

        deps.render_scenario_workspace = _tracking
        asyncio.get_event_loop().run_until_complete(
            execute_scenario_duplicate_route(
                request=request, scenario_id="sc-orig-123", user=user, deps=deps
            )
        )
        # The success render is called with message="Duplicated Test Scenario."
        assert len(render_calls) == 1
        _, kwargs = render_calls[0]
        assert kwargs.get("message") == "Duplicated Test Scenario."

    def test_scenario_summary_cards_have_10_fields(self):
        from app.services.scenario_duplicate_service import (
            execute_scenario_duplicate_route,
        )

        deps, _, user, request = self._make_deps()
        render_calls = []
        original = deps.render_scenario_workspace

        def _tracking(*args, **kwargs):
            render_calls.append((args, kwargs))
            return original(*args, **kwargs)

        deps.render_scenario_workspace = _tracking
        asyncio.get_event_loop().run_until_complete(
            execute_scenario_duplicate_route(
                request=request, scenario_id="sc-orig-123", user=user, deps=deps
            )
        )
        args, _ = render_calls[0]
        # positional: request, user, project_record, workspace_state,
        #             scenarios, history, exports, export_lineage,
        #             scenario_summary_cards
        cards = args[8]
        assert len(cards) == 1
        card = cards[0]
        for required in (
            "scenario_id", "scenario_name", "project_code",
            "updated_at", "copied_from_scenario_id",
            "project_irr", "equity_irr", "avg_dscr",
            "export_count", "governance_state",
        ):
            assert required in card

    def test_export_count_computed_per_scenario_name(self):
        from app.services.scenario_duplicate_service import (
            execute_scenario_duplicate_route,
        )

        deps, _, user, request = self._make_deps()
        render_calls = []
        original = deps.render_scenario_workspace

        def _tracking(*args, **kwargs):
            render_calls.append((args, kwargs))
            return original(*args, **kwargs)

        deps.render_scenario_workspace = _tracking
        asyncio.get_event_loop().run_until_complete(
            execute_scenario_duplicate_route(
                request=request, scenario_id="sc-orig-123", user=user, deps=deps
            )
        )
        args, _ = render_calls[0]
        cards = args[8]
        # Our scenario has 2 entries in lineage, "Other" has 1
        assert cards[0]["export_count"] == 2

    def test_no_replay_metadata_passed_to_duplicate_scenario(self):
        """Quirk 1: duplicate_scenario is called WITHOUT replay_metadata."""
        from app.services.scenario_duplicate_service import (
            execute_scenario_duplicate_route,
        )

        call_args = {}
        original_duplicate = None

        def _tracking(*args, **kwargs):
            call_args["args"] = args
            call_args["kwargs"] = kwargs
            return None

        deps, _, user, request = self._make_deps()
        deps.duplicate_scenario = _tracking
        asyncio.get_event_loop().run_until_complete(
            execute_scenario_duplicate_route(
                request=request, scenario_id="sc-orig-123", user=user, deps=deps
            )
        )
        # 2 positional args (user.user_id, scenario_id), no kwargs
        assert len(call_args["args"]) == 2
        assert call_args["kwargs"] == {}

    def test_no_governance_snapshot_call(self):
        """Quirk 4: the service does NOT call _governance_snapshot."""
        text = _read(SCENARIO_DUPLICATE_SERVICE)
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
        text = _read(SCENARIO_DUPLICATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        for helper in self.FORBIDDEN:
            assert f"{helper}(" not in clean, (
                f"Service must not call forbidden helper {helper}()"
            )

    def test_service_does_not_use_db_or_session_directly(self):
        text = _read(SCENARIO_DUPLICATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        for forbidden in (
            "db.add", "db.commit", "db.flush",
            "session.add", "session.commit",
        ):
            assert forbidden not in clean, (
                f"Service must not use {forbidden} directly"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 7. No HTMX header on success (Quirk 9)
# ─────────────────────────────────────────────────────────────────────────────


class TestNoHtmxHeader:
    def test_service_does_not_emit_hx_trigger(self):
        text = _read(SCENARIO_DUPLICATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "HX-Trigger" not in clean
        assert "HX-Redirect" not in clean

    def test_route_does_not_emit_hx_trigger(self):
        body = _route_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert "HX-Trigger" not in clean
        assert "HX-Redirect" not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 8. No validate_form call (Quirk 8 — path-parameter-only)
# ─────────────────────────────────────────────────────────────────────────────


class TestNoValidateForm:
    def test_service_does_not_call_validate_form(self):
        text = _read(SCENARIO_DUPLICATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "_validate_form(" not in clean
        assert "validate_form(" not in clean

    def test_service_does_not_read_form(self):
        text = _read(SCENARIO_DUPLICATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # The service does not call await request.form() or
        # _collect_form_snapshot (Quirk 8: path-parameter-only).
        assert "await request.form()" not in clean
        assert "_collect_form_snapshot" not in clean

    def test_route_does_not_read_form(self):
        body = _route_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert "await request.form()" not in clean


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
        ],
    )
    def test_route_uses_service_execute(self, route: str, marker: str):
        text = _read(MAIN_WEB)
        if route == "/download":
            assert marker in text
            return
        verb = "post"
        pattern = re.escape(f'@app.{verb}("{route}")')
        m = re.search(
            pattern + r"\s*\nasync def \w+\(.*?(?=\n@app\.(get|post|put|delete|route)\(|\Z)",
            text,
            re.DOTALL,
        )
        assert m is not None
        body = m.group(0)
        clean = _strip_docstrings_and_comments(body)
        assert marker in clean


# ─────────────────────────────────────────────────────────────────────────────
# 10. Phase 51F guardrails
# ─────────────────────────────────────────────────────────────────────────────


class TestPhase51FGuardrails:
    def test_no_service_imports_main_web_or_main_api(self):
        text = _read(SCENARIO_DUPLICATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "import main_web" not in clean
        assert "from main_web" not in clean
        assert "import main_api" not in clean
        assert "from main_api" not in clean

    def test_app_still_imports(self):
        from main_web import app
        assert app is not None


# ─────────────────────────────────────────────────────────────────────────────
# 11. Phase 51K-1 characterization still passes
# ─────────────────────────────────────────────────────────────────────────────


class TestPhase51K1CharacterizationStillPasses:
    def test_phase51k1_tests_present(self):
        import importlib
        mod = importlib.import_module(
            "tests.test_phase51k1_scenario_duplicate_route_golden_characterization"
        )
        assert mod is not None

    def test_phase51k1_tests_still_pass(self):
        import subprocess
        r = subprocess.run(
            [
                "python3", "-m", "pytest",
                "tests/test_phase51k1_scenario_duplicate_route_golden_characterization.py",
                "-q", "--tb=no",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, (
            f"Phase 51K-1 tests failed after 51K-2 re-pointing:\n"
            f"{r.stdout}\n{r.stderr}"
        )
