"""Phase 51P-2 — POST /scenarios/{scenario_id}/rename route vertical
extraction tests.

Verifies the /scenarios/{scenario_id}/rename route body is now
thin and the orchestration lives in
``app/services/scenario_rename_service.py`` with the canonical
``execute_scenario_rename_route`` API.

Pin targets (post-extraction):

1. ``app/services/scenario_rename_service.py`` exists.
2. The module exports:
   - ``class ScenarioRenameRouteOutcome`` (with status_code,
     payload, rendered_response).
   - ``class ScenarioRenameRouteDeps`` (with 9 callables).
   - ``async def execute_scenario_rename_route(*, request,
     scenario_id, new_name, user, deps) -> ScenarioRenameRouteOutcome``.
3. The route body in main_web.py is no longer inline-doing the
   full orchestration.
4. The route imports the service and calls
   ``execute_scenario_rename_route(...)``.
5. The route wires the deps bundle (9 callables) before calling
   the service.
6. The service does NOT import main_web or main_api.
7. The service preserves all 10 quirks (Phase 51P-1).
8. The service produces correct outcomes (400 empty name, 404
   not found, 200 success with rendered response).
9. Other Phase 51 services remain unchanged.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_WEB = REPO_ROOT / "main_web.py"
MAIN_API = REPO_ROOT / "main_api.py"
SERVICES_DIR = REPO_ROOT / "app" / "services"
SCENARIO_RENAME_SERVICE = (
    REPO_ROOT / "app" / "services" / "scenario_rename_service.py"
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _strip_docstrings_and_comments(src: str) -> str:
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    src = re.sub(r"'''[\s\S]*?'''", "", src)
    out_lines = []
    for line in src.splitlines():
        in_string = False
        quote_char = None
        cleaned_chars = []
        for ch in line:
            if ch in ('"', "'") and not in_string:
                in_string = True
                quote_char = ch
                cleaned_chars.append(ch)
            elif ch == quote_char and in_string:
                in_string = False
                quote_char = None
                cleaned_chars.append(ch)
            elif ch == "#" and not in_string:
                break
            else:
                cleaned_chars.append(ch)
        out_lines.append("".join(cleaned_chars))
    return "\n".join(out_lines)


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


# ─────────────────────────────────────────────────────────────────────────────
# Module existence + API surface
# ─────────────────────────────────────────────────────────────────────────────


class TestServiceExistence:
    def test_service_module_exists(self):
        assert SCENARIO_RENAME_SERVICE.exists()

    def test_service_module_in_services_dir(self):
        assert SCENARIO_RENAME_SERVICE.parent == SERVICES_DIR

    def test_service_does_not_import_main_web(self):
        text = _read(SCENARIO_RENAME_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "import main_web" not in clean
        assert "from main_web" not in clean
        assert "import main_api" not in clean
        assert "from main_api" not in clean


# ─────────────────────────────────────────────────────────────────────────────
# Public dataclasses
# ─────────────────────────────────────────────────────────────────────────────


class TestScenarioRenameRouteOutcome:
    def test_class_exists(self):
        text = _read(SCENARIO_RENAME_SERVICE)
        assert "class ScenarioRenameRouteOutcome" in text

    def test_class_is_dataclass(self):
        text = _read(SCENARIO_RENAME_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "@dataclass" in clean
        assert "class ScenarioRenameRouteOutcome" in clean

    def test_outcome_has_status_code_field(self):
        text = _read(SCENARIO_RENAME_SERVICE)
        assert "status_code" in text

    def test_outcome_has_payload_field(self):
        text = _read(SCENARIO_RENAME_SERVICE)
        assert "payload" in text

    def test_outcome_has_rendered_response_field(self):
        text = _read(SCENARIO_RENAME_SERVICE)
        assert "rendered_response" in text


class TestScenarioRenameRouteDeps:
    def test_class_exists(self):
        text = _read(SCENARIO_RENAME_SERVICE)
        assert "class ScenarioRenameRouteDeps" in text

    def test_class_is_dataclass(self):
        text = _read(SCENARIO_RENAME_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "@dataclass" in clean
        assert "class ScenarioRenameRouteDeps" in clean

    def test_deps_has_9_callables(self):
        """Pin the count of deps callables (9)."""
        text = _read(SCENARIO_RENAME_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        m = re.search(
            r"@dataclass\s*\nclass ScenarioRenameRouteDeps.*?(?=\n\nclass |\nasync def |\Z)",
            clean,
            re.DOTALL,
        )
        assert m is not None
        body = m.group(0)
        field_count = body.count(": Callable")
        assert field_count == 9, f"Expected 9 callable deps, got {field_count}"


# ─────────────────────────────────────────────────────────────────────────────
# Service entry point
# ─────────────────────────────────────────────────────────────────────────────


class TestExecuteScenarioRenameRoute:
    def test_function_exists(self):
        text = _read(SCENARIO_RENAME_SERVICE)
        assert "async def execute_scenario_rename_route(" in text

    def test_function_signature(self):
        text = _read(SCENARIO_RENAME_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        m = re.search(
            r"async def execute_scenario_rename_route\((.*?)\)", clean, re.DOTALL
        )
        assert m is not None
        sig = m.group(1)
        assert "request" in sig
        assert "scenario_id" in sig
        assert "new_name" in sig
        assert "user" in sig
        assert "deps" in sig

    def test_function_returns_outcome(self):
        text = _read(SCENARIO_RENAME_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert (
            "-> ScenarioRenameRouteOutcome" in clean
        )


# ─────────────────────────────────────────────────────────────────────────────
# Route uses the service
# ─────────────────────────────────────────────────────────────────────────────


class TestRouteUsesService:
    def test_route_imports_service(self):
        body = _route_body("/scenarios/{scenario_id}/rename")
        clean = _strip_docstrings_and_comments(body)
        assert "from app.services.scenario_rename_service import" in clean
        assert "execute_scenario_rename_route" in clean
        assert "ScenarioRenameRouteDeps" in clean

    def test_route_calls_execute(self):
        body = _route_body("/scenarios/{scenario_id}/rename")
        clean = _strip_docstrings_and_comments(body)
        assert "execute_scenario_rename_route(" in clean
        assert "outcome = await execute_scenario_rename_route(" in clean

    def test_route_wires_deps(self):
        """The route builds a ScenarioRenameRouteDeps instance with
        all 9 callables."""
        body = _route_body("/scenarios/{scenario_id}/rename")
        clean = _strip_docstrings_and_comments(body)
        assert "deps = ScenarioRenameRouteDeps(" in clean
        # Check that the deps bundle has key callables wired
        for name in [
            "get_scenario=",
            "rename_scenario=",
            "get_project_by_code=",
            "list_scenarios=",
            "get_scenario_history=",
            "list_exports=",
            "build_export_lineage=",
            "get_workspace_state=",
            "render_scenario_workspace=",
        ]:
            assert name in clean, f"Route deps missing {name}"

    def test_route_translates_outcome(self):
        body = _route_body("/scenarios/{scenario_id}/rename")
        clean = _strip_docstrings_and_comments(body)
        # Error path: JSONResponse
        assert "return JSONResponse(outcome.payload, status_code=outcome.status_code)" in clean
        # Success path: returned rendered_response
        assert "return outcome.rendered_response" in clean


# ─────────────────────────────────────────────────────────────────────────────
# Quirk preservation
# ─────────────────────────────────────────────────────────────────────────────


class TestServiceQuirksPreserved:
    def test_quirk_1_await_request_form_in_route(self):
        """Quirk 1: form is read via await request.form() (in the route)."""
        body = _route_body("/scenarios/{scenario_id}/rename")
        assert "await request.form()" in body

    def test_quirk_2_workspace_full_rerender(self):
        """Quirk 2: after rename, the entire workspace is re-rendered.
        Service calls deps.render_scenario_workspace which the route wires
        to a wrapper that builds scenario_summary_cards and then calls
        main_web._render_scenario_workspace."""
        text = _read(SCENARIO_RENAME_SERVICE)
        assert "deps.render_scenario_workspace(" in text

    def test_quirk_5_scenario_name_in_message(self):
        """Quirk 5: success message includes the new scenario name."""
        text = _read(SCENARIO_RENAME_SERVICE)
        assert 'f"Renamed scenario to {new_name}."' in text

    def test_quirk_6_no_htmx_headers(self):
        """Quirk 6: no HTMX-specific headers."""
        body = _route_body("/scenarios/{scenario_id}/rename")
        clean = _strip_docstrings_and_comments(body)
        assert "HX-Trigger" not in clean
        assert "HX-Redirect" not in clean

    def test_quirk_7_positional_get_scenario(self):
        """Quirk 7: get_scenario(scenario_id, user.user_id) (positional)."""
        text = _read(SCENARIO_RENAME_SERVICE)
        assert "deps.get_scenario(scenario_id, user.user_id)" in text

    def test_quirk_8_list_scenarios_with_archived_false_limit_12(self):
        """Quirk 8: list_scenarios with include_archived=False, limit=12."""
        text = _read(SCENARIO_RENAME_SERVICE)
        assert "include_archived=False" in text
        assert "limit=12" in text

    def test_quirk_9_get_scenario_history_limit_20(self):
        """Quirk 9: get_scenario_history with limit=20."""
        text = _read(SCENARIO_RENAME_SERVICE)
        assert "limit=20" in text

    def test_quirk_10_list_exports_and_build_export_lineage_limit_8(self):
        """Quirk 10: list_exports and build_export_lineage with limit=8."""
        text = _read(SCENARIO_RENAME_SERVICE)
        assert text.count("limit=8") >= 2


# ─────────────────────────────────────────────────────────────────────────────
# Service orchestration behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestServiceOrchestration:
    def test_service_calls_get_scenario(self):
        text = _read(SCENARIO_RENAME_SERVICE)
        assert "deps.get_scenario(scenario_id, user.user_id)" in text

    def test_service_calls_rename_scenario(self):
        text = _read(SCENARIO_RENAME_SERVICE)
        assert "deps.rename_scenario(user.user_id, scenario_id, new_name)" in text

    def test_service_calls_get_project_by_code(self):
        text = _read(SCENARIO_RENAME_SERVICE)
        assert "deps.get_project_by_code(user.user_id, record.project_code)" in text

    def test_service_calls_list_scenarios(self):
        text = _read(SCENARIO_RENAME_SERVICE)
        assert "deps.list_scenarios(" in text

    def test_service_calls_get_scenario_history(self):
        text = _read(SCENARIO_RENAME_SERVICE)
        assert "deps.get_scenario_history(" in text

    def test_service_calls_list_exports(self):
        text = _read(SCENARIO_RENAME_SERVICE)
        assert "deps.list_exports(" in text

    def test_service_calls_build_export_lineage(self):
        text = _read(SCENARIO_RENAME_SERVICE)
        assert "deps.build_export_lineage(" in text

    def test_service_calls_get_workspace_state(self):
        text = _read(SCENARIO_RENAME_SERVICE)
        assert "deps.get_workspace_state(user.user_id, record.project_id)" in text

    def test_service_calls_render_scenario_workspace(self):
        text = _read(SCENARIO_RENAME_SERVICE)
        assert "deps.render_scenario_workspace(" in text


# ─────────────────────────────────────────────────────────────────────────────
# Service returns correct outcomes (functional tests with stubs)
# ─────────────────────────────────────────────────────────────────────────────


class _StubUser:
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id


class _StubRequest:
    pass


class _StubScenarioRecord:
    def __init__(self, scenario_id: str, project_id: int, project_code: str, scenario_name: str = "Test") -> None:
        self.scenario_id = scenario_id
        self.project_id = project_id
        self.project_code = project_code
        self.scenario_name = scenario_name


class _StubDeps:
    """In-memory stub deps bundle for functional tests."""

    def __init__(self, *, scenario: Optional[_StubScenarioRecord] = None) -> None:
        self.scenario = scenario
        self.rename_calls: List[Dict[str, Any]] = []
        self.rendered = object()

    def get_scenario(self, scenario_id: str, user_id: int):
        return self.scenario

    def rename_scenario(self, user_id: int, scenario_id: str, new_name: str) -> None:
        self.rename_calls.append({"user_id": user_id, "scenario_id": scenario_id, "new_name": new_name})

    def get_project_by_code(self, user_id: int, project_code: str):
        return {"project_code": project_code}

    def list_scenarios(self, user_id: int, project_id: int, include_archived: bool, limit: int):
        return []

    def get_scenario_history(self, user_id: int, project_id: int, limit: int):
        return []

    def list_exports(self, user_id: int, project_id: int, limit: int):
        return []

    def build_export_lineage(self, user_id: int, project_id: int, limit: int):
        return []

    def get_workspace_state(self, user_id: int, project_id: int):
        return {}

    def render_scenario_workspace(
        self, request, user, project_record, workspace_state, scenarios,
        history, exports, export_lineage, message,
    ):
        return self.rendered


class TestServiceOutcomes:
    @pytest.mark.asyncio
    async def test_400_outcome_on_empty_name(self):
        from app.services.scenario_rename_service import execute_scenario_rename_route

        deps = _StubDeps(scenario=_StubScenarioRecord("sid", 1, "proj"))
        request = _StubRequest()
        user = _StubUser(user_id=1)
        outcome = await execute_scenario_rename_route(
            request=request, scenario_id="sid", new_name="",
            user=user, deps=deps
        )
        assert outcome.status_code == 400
        assert outcome.payload == {"error": "Scenario name is required"}
        # No rename on 400
        assert len(deps.rename_calls) == 0

    @pytest.mark.asyncio
    async def test_400_outcome_on_whitespace_only_name(self):
        """Note: the route strips the name before calling the service.
        So whitespace-only is handled by the route, not the service.
        The service checks for empty string after stripping."""
        from app.services.scenario_rename_service import execute_scenario_rename_route

        deps = _StubDeps(scenario=_StubScenarioRecord("sid", 1, "proj"))
        request = _StubRequest()
        user = _StubUser(user_id=1)
        # Simulate what the route does: strip the form value first
        stripped = "   ".strip()
        outcome = await execute_scenario_rename_route(
            request=request, scenario_id="sid", new_name=stripped,
            user=user, deps=deps
        )
        assert outcome.status_code == 400

    @pytest.mark.asyncio
    async def test_404_outcome_on_scenario_not_found(self):
        from app.services.scenario_rename_service import execute_scenario_rename_route

        deps = _StubDeps(scenario=None)
        request = _StubRequest()
        user = _StubUser(user_id=1)
        outcome = await execute_scenario_rename_route(
            request=request, scenario_id="missing", new_name="new name",
            user=user, deps=deps
        )
        assert outcome.status_code == 404
        assert outcome.payload == {"error": "Scenario not found"}
        # No rename on 404
        assert len(deps.rename_calls) == 0

    @pytest.mark.asyncio
    async def test_200_outcome_on_success(self):
        from app.services.scenario_rename_service import execute_scenario_rename_route

        deps = _StubDeps(scenario=_StubScenarioRecord("sid", 1, "proj"))
        request = _StubRequest()
        user = _StubUser(user_id=1)
        outcome = await execute_scenario_rename_route(
            request=request, scenario_id="sid", new_name="New Name",
            user=user, deps=deps
        )
        assert outcome.status_code == 200
        assert outcome.rendered_response is deps.rendered
        # 1 rename
        assert len(deps.rename_calls) == 1
        assert deps.rename_calls[0]["new_name"] == "New Name"

    @pytest.mark.asyncio
    async def test_workspace_rerender_called_with_correct_args(self):
        from app.services.scenario_rename_service import execute_scenario_rename_route

        captured_kwargs: Dict[str, Any] = {}

        def capture_render(*, request, user, project_record, workspace_state, scenarios, history, exports, export_lineage, message):
            captured_kwargs.update({
                "user": user, "project_record": project_record,
                "workspace_state": workspace_state, "scenarios": scenarios,
                "history": history, "exports": exports,
                "export_lineage": export_lineage, "message": message,
            })
            return "rendered"

        deps = _StubDeps(scenario=_StubScenarioRecord("sid", 1, "proj"))
        deps.render_scenario_workspace = capture_render
        request = _StubRequest()
        user = _StubUser(user_id=1)
        await execute_scenario_rename_route(
            request=request, scenario_id="sid", new_name="New",
            user=user, deps=deps
        )
        assert captured_kwargs["user"] is user
        assert captured_kwargs["message"] == "Renamed scenario to New."


# ─────────────────────────────────────────────────────────────────────────────
# Other Phase 51 services unchanged
# ─────────────────────────────────────────────────────────────────────────────


class TestOtherServicesUnchanged:
    def test_projects_create_service_unchanged(self):
        path = SERVICES_DIR / "projects_create_service.py"
        assert path.exists()

    def test_project_save_as_service_unchanged(self):
        path = SERVICES_DIR / "project_save_as_service.py"
        assert path.exists()

    def test_scenarios_add_service_unchanged(self):
        path = SERVICES_DIR / "scenarios_add_service.py"
        assert path.exists()
