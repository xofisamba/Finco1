"""Phase 51R-2 — POST /scenarios/{scenario_id}/update-overrides route
vertical extraction tests.
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
SCENARIO_UPDATE_OVERRIDES_SERVICE = (
    REPO_ROOT / "app" / "services" / "scenario_update_overrides_service.py"
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


# ─────────────────────────────────────────────────────────────────────────────
# Module existence + API surface
# ─────────────────────────────────────────────────────────────────────────────


class TestServiceExistence:
    def test_service_module_exists(self):
        assert SCENARIO_UPDATE_OVERRIDES_SERVICE.exists()

    def test_service_does_not_import_main_web(self):
        text = _read(SCENARIO_UPDATE_OVERRIDES_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "import main_web" not in clean
        assert "from main_web" not in clean
        assert "import main_api" not in clean
        assert "from main_api" not in clean


class TestScenarioUpdateOverridesRouteOutcome:
    def test_class_exists(self):
        assert "class ScenarioUpdateOverridesRouteOutcome" in _read(SCENARIO_UPDATE_OVERRIDES_SERVICE)

    def test_class_is_dataclass(self):
        text = _read(SCENARIO_UPDATE_OVERRIDES_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "@dataclass" in clean
        assert "class ScenarioUpdateOverridesRouteOutcome" in clean

    def test_outcome_has_template_name_field(self):
        assert "template_name" in _read(SCENARIO_UPDATE_OVERRIDES_SERVICE)

    def test_outcome_has_context_field(self):
        assert "context" in _read(SCENARIO_UPDATE_OVERRIDES_SERVICE)

    def test_outcome_has_payload_field(self):
        assert "payload" in _read(SCENARIO_UPDATE_OVERRIDES_SERVICE)

    def test_outcome_has_status_code_field(self):
        assert "status_code" in _read(SCENARIO_UPDATE_OVERRIDES_SERVICE)

    def test_outcome_has_headers_field(self):
        assert "headers" in _read(SCENARIO_UPDATE_OVERRIDES_SERVICE)

    def test_default_template_name_is_scenario_tab(self):
        assert 'template_name: str = "partials/scenario_tab.html"' in _read(SCENARIO_UPDATE_OVERRIDES_SERVICE)


class TestScenarioUpdateOverridesRouteDeps:
    def test_class_exists(self):
        assert "class ScenarioUpdateOverridesRouteDeps" in _read(SCENARIO_UPDATE_OVERRIDES_SERVICE)

    def test_deps_has_6_callables(self):
        text = _read(SCENARIO_UPDATE_OVERRIDES_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        m = re.search(
            r"@dataclass\s*\nclass ScenarioUpdateOverridesRouteDeps.*?(?=\n\nclass |\nasync def |\Z)",
            clean,
            re.DOTALL,
        )
        assert m is not None
        body = m.group(0)
        field_count = body.count(": Callable")
        assert field_count == 6, f"Expected 6 callable deps, got {field_count}"


class TestExecuteScenarioUpdateOverridesRoute:
    def test_function_exists(self):
        assert "async def execute_scenario_update_overrides_route(" in _read(SCENARIO_UPDATE_OVERRIDES_SERVICE)

    def test_function_signature(self):
        text = _read(SCENARIO_UPDATE_OVERRIDES_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        m = re.search(
            r"async def execute_scenario_update_overrides_route\((.*?)\)", clean, re.DOTALL
        )
        assert m is not None
        sig = m.group(1)
        assert "request" in sig
        assert "scenario_id" in sig
        assert "overrides" in sig
        assert "user" in sig
        assert "deps" in sig


# ─────────────────────────────────────────────────────────────────────────────
# Route uses the service
# ─────────────────────────────────────────────────────────────────────────────


class TestRouteUsesService:
    def test_route_imports_service(self):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        clean = _strip_docstrings_and_comments(body)
        assert "from app.services.scenario_update_overrides_service import" in clean
        assert "execute_scenario_update_overrides_route" in clean
        assert "ScenarioUpdateOverridesRouteDeps" in clean

    def test_route_calls_execute(self):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        clean = _strip_docstrings_and_comments(body)
        assert "execute_scenario_update_overrides_route(" in clean
        assert "outcome = await execute_scenario_update_overrides_route(" in clean

    def test_route_wires_deps(self):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        clean = _strip_docstrings_and_comments(body)
        assert "deps = ScenarioUpdateOverridesRouteDeps(" in clean
        for name in [
            "get_scenario=",
            "update_scenario_overrides=",
            "get_project_record=",
            "get_workspace_state=",
            "list_scenarios=",
            "build_scenario_tab_context=",
        ]:
            assert name in clean, f"Route deps missing {name}"

    def test_route_translates_outcome(self):
        body = _route_body("/scenarios/{scenario_id}/update-overrides")
        clean = _strip_docstrings_and_comments(body)
        # Error path
        assert "JSONResponse(outcome.payload, status_code=outcome.status_code)" in clean
        # Success path
        assert "templates.TemplateResponse(" in clean
        assert "name=outcome.template_name" in clean
        assert "headers=outcome.headers" in clean


# ─────────────────────────────────────────────────────────────────────────────
# Quirk preservation
# ─────────────────────────────────────────────────────────────────────────────


class TestServiceQuirksPreserved:
    def test_quirk_3_is_base_case_gate(self):
        text = _read(SCENARIO_UPDATE_OVERRIDES_SERVICE)
        assert "if record.is_base_case:" in text
        assert "Cannot override Base Case via this endpoint" in text

    def test_quirk_4_500_on_update_failure(self):
        text = _read(SCENARIO_UPDATE_OVERRIDES_SERVICE)
        assert "if updated is None:" in text
        assert "Failed to update overrides" in text
        assert "status_code=500" in text

    def test_quirk_5_partial_template(self):
        text = _read(SCENARIO_UPDATE_OVERRIDES_SERVICE)
        assert 'partials/scenario_tab.html' in text

    def test_quirk_6_hx_trigger_overrides_updated(self):
        text = _read(SCENARIO_UPDATE_OVERRIDES_SERVICE)
        assert '"HX-Trigger": "overridesUpdated"' in text

    def test_quirk_7_no_hx_redirect(self):
        text = _read(SCENARIO_UPDATE_OVERRIDES_SERVICE)
        assert "HX-Redirect" not in text

    def test_quirk_9_positional_get_scenario(self):
        text = _read(SCENARIO_UPDATE_OVERRIDES_SERVICE)
        assert "deps.get_scenario(scenario_id, user.user_id)" in text

    def test_quirk_10_get_project_record_keyword(self):
        text = _read(SCENARIO_UPDATE_OVERRIDES_SERVICE)
        # The service calls get_project_record with user_id and project_code kwargs
        assert "deps.get_project_record(" in text
        assert "user_id=user.user_id" in text
        assert "project_code=record.project_code" in text


# ─────────────────────────────────────────────────────────────────────────────
# Service returns correct outcomes (functional tests with stubs)
# ─────────────────────────────────────────────────────────────────────────────


class _StubUser:
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id


class _StubRequest:
    pass


class _StubScenarioRecord:
    def __init__(self, scenario_id: str, is_base_case: bool = False) -> None:
        self.scenario_id = scenario_id
        self.is_base_case = is_base_case
        self.project_code = "proj"
        self.project_id = 1


class _StubDeps:
    def __init__(self, *, scenario: Optional[_StubScenarioRecord] = None, update_result: Any = object()) -> None:
        self.scenario = scenario
        self.update_result = update_result
        self.update_calls: List[Dict[str, Any]] = []

    def get_scenario(self, scenario_id: str, user_id: int):
        return self.scenario

    def update_scenario_overrides(self, user_id: int, scenario_id: str, overrides: dict) -> Any:
        self.update_calls.append({"user_id": user_id, "scenario_id": scenario_id, "overrides": overrides})
        return self.update_result

    def get_project_record(self, *, user_id: int, project_code: str):
        return {"project_code": project_code}

    def get_workspace_state(self, user_id: int, project_id: int):
        return {"state": "ws"}

    def list_scenarios(self, user_id: int, project_id: int, include_archived: bool, limit: int):
        return []

    def build_scenario_tab_context(self, user, project_record, scenarios, ws):
        return {"built": True, "user": user}


class TestServiceOutcomes:
    @pytest.mark.asyncio
    async def test_404_outcome_on_scenario_not_found(self):
        from app.services.scenario_update_overrides_service import execute_scenario_update_overrides_route

        deps = _StubDeps(scenario=None)
        request = _StubRequest()
        user = _StubUser(user_id=1)
        outcome = await execute_scenario_update_overrides_route(
            request=request, scenario_id="missing", overrides={}, user=user, deps=deps
        )
        assert outcome.status_code == 404
        assert outcome.payload == {"error": "Scenario not found"}
        assert len(deps.update_calls) == 0

    @pytest.mark.asyncio
    async def test_400_outcome_on_base_case(self):
        from app.services.scenario_update_overrides_service import execute_scenario_update_overrides_route

        deps = _StubDeps(scenario=_StubScenarioRecord("sid", is_base_case=True))
        request = _StubRequest()
        user = _StubUser(user_id=1)
        outcome = await execute_scenario_update_overrides_route(
            request=request, scenario_id="sid", overrides={}, user=user, deps=deps
        )
        assert outcome.status_code == 400
        assert outcome.payload == {"error": "Cannot override Base Case via this endpoint"}
        assert len(deps.update_calls) == 0

    @pytest.mark.asyncio
    async def test_500_outcome_on_update_failure(self):
        from app.services.scenario_update_overrides_service import execute_scenario_update_overrides_route

        deps = _StubDeps(scenario=_StubScenarioRecord("sid"), update_result=None)
        request = _StubRequest()
        user = _StubUser(user_id=1)
        outcome = await execute_scenario_update_overrides_route(
            request=request, scenario_id="sid", overrides={}, user=user, deps=deps
        )
        assert outcome.status_code == 500
        assert outcome.payload == {"error": "Failed to update overrides"}

    @pytest.mark.asyncio
    async def test_200_outcome_on_success(self):
        from app.services.scenario_update_overrides_service import execute_scenario_update_overrides_route

        deps = _StubDeps(scenario=_StubScenarioRecord("sid"))
        request = _StubRequest()
        user = _StubUser(user_id=1)
        outcome = await execute_scenario_update_overrides_route(
            request=request, scenario_id="sid", overrides={"x": 1}, user=user, deps=deps
        )
        assert outcome.status_code == 200
        assert outcome.template_name == "partials/scenario_tab.html"
        assert outcome.headers == {"HX-Trigger": "overridesUpdated"}
        assert outcome.context == {"built": True, "user": user}
        assert len(deps.update_calls) == 1
        assert deps.update_calls[0]["overrides"] == {"x": 1}
