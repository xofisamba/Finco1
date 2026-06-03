"""Phase 51S-2 — POST /scenarios/{scenario_id}/select route vertical
extraction tests.
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
SCENARIO_SELECT_SERVICE = (
    REPO_ROOT / "app" / "services" / "scenario_select_service.py"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _strip_docstrings_and_comments(src: str) -> str:
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    src = re.sub(r"'''[\s\S]*?'''", "", src)
    out = []
    for line in src.splitlines():
        in_string = False
        quote_char = None
        cleaned = []
        for ch in line:
            if ch in ('"', "'") and not in_string:
                in_string = True
                quote_char = ch
                cleaned.append(ch)
            elif ch == quote_char and in_string:
                in_string = False
                quote_char = None
                cleaned.append(ch)
            elif ch == "#" and not in_string:
                break
            else:
                cleaned.append(ch)
        out.append("".join(cleaned))
    return "\n".join(out)


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


class TestServiceExistence:
    def test_service_module_exists(self):
        assert SCENARIO_SELECT_SERVICE.exists()

    def test_service_does_not_import_main_web(self):
        text = _read(SCENARIO_SELECT_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "import main_web" not in clean
        assert "from main_web" not in clean
        assert "import main_api" not in clean
        assert "from main_api" not in clean


class TestScenarioSelectRouteOutcome:
    def test_class_exists(self):
        assert "class ScenarioSelectRouteOutcome" in _read(SCENARIO_SELECT_SERVICE)

    def test_class_is_dataclass(self):
        text = _read(SCENARIO_SELECT_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "@dataclass" in clean
        assert "class ScenarioSelectRouteOutcome" in clean

    def test_outcome_has_status_code_field(self):
        assert "status_code" in _read(SCENARIO_SELECT_SERVICE)

    def test_outcome_has_payload_field(self):
        assert "payload" in _read(SCENARIO_SELECT_SERVICE)

    def test_outcome_has_headers_field(self):
        assert "headers" in _read(SCENARIO_SELECT_SERVICE)

    def test_outcome_has_template_name_field(self):
        assert "template_name" in _read(SCENARIO_SELECT_SERVICE)

    def test_outcome_has_context_field(self):
        assert "context" in _read(SCENARIO_SELECT_SERVICE)


class TestScenarioSelectRouteDeps:
    def test_class_exists(self):
        assert "class ScenarioSelectRouteDeps" in _read(SCENARIO_SELECT_SERVICE)

    def test_deps_has_6_callables(self):
        text = _read(SCENARIO_SELECT_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        m = re.search(
            r"@dataclass\s*\nclass ScenarioSelectRouteDeps.*?(?=\n\nclass |\nasync def |\Z)",
            clean,
            re.DOTALL,
        )
        assert m is not None
        body = m.group(0)
        field_count = body.count(": Callable")
        assert field_count == 6, f"Expected 6 callable deps, got {field_count}"


class TestExecuteScenarioSelectRoute:
    def test_function_exists(self):
        assert "async def execute_scenario_select_route(" in _read(SCENARIO_SELECT_SERVICE)

    def test_function_signature(self):
        text = _read(SCENARIO_SELECT_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        m = re.search(
            r"async def execute_scenario_select_route\((.*?)\)", clean, re.DOTALL
        )
        assert m is not None
        sig = m.group(1)
        assert "request" in sig
        assert "scenario_id" in sig
        assert "user" in sig
        assert "deps" in sig


class TestRouteUsesService:
    def test_route_imports_service(self):
        body = _route_body("/scenarios/{scenario_id}/select")
        clean = _strip_docstrings_and_comments(body)
        assert "from app.services.scenario_select_service import" in clean
        assert "execute_scenario_select_route" in clean
        assert "ScenarioSelectRouteDeps" in clean

    def test_route_calls_execute(self):
        body = _route_body("/scenarios/{scenario_id}/select")
        clean = _strip_docstrings_and_comments(body)
        assert "execute_scenario_select_route(" in clean

    def test_route_wires_deps(self):
        body = _route_body("/scenarios/{scenario_id}/select")
        clean = _strip_docstrings_and_comments(body)
        assert "deps = ScenarioSelectRouteDeps(" in clean
        for name in [
            "get_scenario=",
            "select_scenario=",
            "get_workspace_state=",
            "get_project_record=",
            "list_scenarios=",
            "build_scenario_tab_context=",
        ]:
            assert name in clean, f"Route deps missing {name}"

    def test_route_translates_outcome(self):
        body = _route_body("/scenarios/{scenario_id}/select")
        clean = _strip_docstrings_and_comments(body)
        assert "JSONResponse(outcome.payload, status_code=outcome.status_code)" in clean
        assert "templates.TemplateResponse(" in clean
        assert "name=outcome.template_name" in clean
        assert "headers=outcome.headers" in clean


class TestServiceQuirksPreserved:
    def test_quirk_1_select_scenario_takes_project_id(self):
        text = _read(SCENARIO_SELECT_SERVICE)
        assert "deps.select_scenario(user.user_id, record.project_id, scenario_id)" in text

    def test_quirk_2_returns_bool_check(self):
        text = _read(SCENARIO_SELECT_SERVICE)
        assert "if not ok:" in text

    def test_quirk_3_500_on_failure(self):
        text = _read(SCENARIO_SELECT_SERVICE)
        assert "status_code=500" in text
        assert "Failed to select scenario" in text

    def test_quirk_4_partial_template(self):
        text = _read(SCENARIO_SELECT_SERVICE)
        assert "partials/scenario_tab.html" in text

    def test_quirk_5_hx_trigger_json(self):
        text = _read(SCENARIO_SELECT_SERVICE)
        assert "scenarioSelected:" in text
        assert "scenario_id" in text

    def test_quirk_7_no_hx_redirect(self):
        text = _read(SCENARIO_SELECT_SERVICE)
        assert "HX-Redirect" not in text

    def test_quirk_8_positional_get_scenario(self):
        text = _read(SCENARIO_SELECT_SERVICE)
        assert "deps.get_scenario(scenario_id, user.user_id)" in text


# Functional tests with stubs
class _StubUser:
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id


class _StubRequest:
    pass


class _StubScenarioRecord:
    def __init__(self, scenario_id: str) -> None:
        self.scenario_id = scenario_id
        self.project_code = "proj"
        self.project_id = 1


class _StubDeps:
    def __init__(self, *, scenario=None, select_result=True) -> None:
        self.scenario = scenario
        self.select_result = select_result
        self.select_calls = []

    def get_scenario(self, scenario_id, user_id):
        return self.scenario

    def select_scenario(self, user_id, project_id, scenario_id):
        self.select_calls.append((user_id, project_id, scenario_id))
        return self.select_result

    def get_workspace_state(self, user_id, project_id):
        return {}

    def get_project_record(self, *, user_id, project_code):
        return {"project_code": project_code}

    def list_scenarios(self, user_id, project_id, include_archived, limit):
        return []

    def build_scenario_tab_context(self, user, project_record, scenarios, ws):
        return {"ctx": True}


class TestServiceOutcomes:
    @pytest.mark.asyncio
    async def test_404_outcome_on_scenario_not_found(self):
        from app.services.scenario_select_service import execute_scenario_select_route

        deps = _StubDeps(scenario=None)
        request = _StubRequest()
        user = _StubUser(user_id=1)
        outcome = await execute_scenario_select_route(
            request=request, scenario_id="missing", user=user, deps=deps
        )
        assert outcome.status_code == 404
        assert outcome.payload == {"error": "Scenario not found"}
        assert len(deps.select_calls) == 0

    @pytest.mark.asyncio
    async def test_500_outcome_on_select_failure(self):
        from app.services.scenario_select_service import execute_scenario_select_route

        deps = _StubDeps(scenario=_StubScenarioRecord("sid"), select_result=False)
        request = _StubRequest()
        user = _StubUser(user_id=1)
        outcome = await execute_scenario_select_route(
            request=request, scenario_id="sid", user=user, deps=deps
        )
        assert outcome.status_code == 500
        assert outcome.payload == {"error": "Failed to select scenario"}

    @pytest.mark.asyncio
    async def test_200_outcome_on_success(self):
        from app.services.scenario_select_service import execute_scenario_select_route

        deps = _StubDeps(scenario=_StubScenarioRecord("sid"))
        request = _StubRequest()
        user = _StubUser(user_id=1)
        outcome = await execute_scenario_select_route(
            request=request, scenario_id="sid", user=user, deps=deps
        )
        assert outcome.status_code == 200
        assert outcome.template_name == "partials/scenario_tab.html"
        assert outcome.context == {"ctx": True}
        # HX-Trigger has scenario_id embedded
        assert "scenarioSelected:" in outcome.headers["HX-Trigger"]
        assert "sid" in outcome.headers["HX-Trigger"]
        # select_scenario called with 3 args
        assert len(deps.select_calls) == 1
        assert deps.select_calls[0] == (1, 1, "sid")
