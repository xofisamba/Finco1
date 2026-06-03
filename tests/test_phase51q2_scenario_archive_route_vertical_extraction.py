"""Phase 51Q-2 — POST /scenarios/{scenario_id}/archive route vertical
extraction tests.

Verifies the /scenarios/{scenario_id}/archive route body is now
thin and the orchestration lives in
``app/services/scenario_archive_service.py`` with the canonical
``execute_scenario_archive_route`` API.
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
SCENARIO_ARCHIVE_SERVICE = (
    REPO_ROOT / "app" / "services" / "scenario_archive_service.py"
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
        assert SCENARIO_ARCHIVE_SERVICE.exists()

    def test_service_module_in_services_dir(self):
        assert SCENARIO_ARCHIVE_SERVICE.parent == SERVICES_DIR

    def test_service_does_not_import_main_web(self):
        text = _read(SCENARIO_ARCHIVE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "import main_web" not in clean
        assert "from main_web" not in clean
        assert "import main_api" not in clean
        assert "from main_api" not in clean


class TestScenarioArchiveRouteOutcome:
    def test_class_exists(self):
        text = _read(SCENARIO_ARCHIVE_SERVICE)
        assert "class ScenarioArchiveRouteOutcome" in text

    def test_class_is_dataclass(self):
        text = _read(SCENARIO_ARCHIVE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "@dataclass" in clean
        assert "class ScenarioArchiveRouteOutcome" in clean

    def test_outcome_has_status_code_field(self):
        assert "status_code" in _read(SCENARIO_ARCHIVE_SERVICE)

    def test_outcome_has_payload_field(self):
        assert "payload" in _read(SCENARIO_ARCHIVE_SERVICE)

    def test_outcome_has_rendered_response_field(self):
        assert "rendered_response" in _read(SCENARIO_ARCHIVE_SERVICE)


class TestScenarioArchiveRouteDeps:
    def test_class_exists(self):
        assert "class ScenarioArchiveRouteDeps" in _read(SCENARIO_ARCHIVE_SERVICE)

    def test_class_is_dataclass(self):
        text = _read(SCENARIO_ARCHIVE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "@dataclass" in clean
        assert "class ScenarioArchiveRouteDeps" in clean

    def test_deps_has_9_callables(self):
        text = _read(SCENARIO_ARCHIVE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        m = re.search(
            r"@dataclass\s*\nclass ScenarioArchiveRouteDeps.*?(?=\n\nclass |\nasync def |\Z)",
            clean,
            re.DOTALL,
        )
        assert m is not None
        body = m.group(0)
        field_count = body.count(": Callable")
        assert field_count == 9, f"Expected 9 callable deps, got {field_count}"


class TestExecuteScenarioArchiveRoute:
    def test_function_exists(self):
        assert "async def execute_scenario_archive_route(" in _read(SCENARIO_ARCHIVE_SERVICE)

    def test_function_signature(self):
        text = _read(SCENARIO_ARCHIVE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        m = re.search(
            r"async def execute_scenario_archive_route\((.*?)\)", clean, re.DOTALL
        )
        assert m is not None
        sig = m.group(1)
        assert "request" in sig
        assert "scenario_id" in sig
        assert "user" in sig
        assert "deps" in sig

    def test_function_returns_outcome(self):
        text = _read(SCENARIO_ARCHIVE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "-> ScenarioArchiveRouteOutcome" in clean


# ─────────────────────────────────────────────────────────────────────────────
# Route uses the service
# ─────────────────────────────────────────────────────────────────────────────


class TestRouteUsesService:
    def test_route_imports_service(self):
        body = _route_body("/scenarios/{scenario_id}/archive")
        clean = _strip_docstrings_and_comments(body)
        assert "from app.services.scenario_archive_service import" in clean
        assert "execute_scenario_archive_route" in clean
        assert "ScenarioArchiveRouteDeps" in clean

    def test_route_calls_execute(self):
        body = _route_body("/scenarios/{scenario_id}/archive")
        clean = _strip_docstrings_and_comments(body)
        assert "execute_scenario_archive_route(" in clean
        assert "outcome = await execute_scenario_archive_route(" in clean

    def test_route_wires_deps(self):
        body = _route_body("/scenarios/{scenario_id}/archive")
        clean = _strip_docstrings_and_comments(body)
        assert "deps = ScenarioArchiveRouteDeps(" in clean
        for name in [
            "get_scenario=",
            "archive_scenario=",
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
        body = _route_body("/scenarios/{scenario_id}/archive")
        clean = _strip_docstrings_and_comments(body)
        assert "return JSONResponse(outcome.payload, status_code=outcome.status_code)" in clean
        assert "return outcome.rendered_response" in clean


# ─────────────────────────────────────────────────────────────────────────────
# Quirk preservation
# ─────────────────────────────────────────────────────────────────────────────


class TestServiceQuirksPreserved:
    def test_quirk_1_soft_archive(self):
        """Quirk 1: this is a SOFT archive (no delete)."""
        text = _read(SCENARIO_ARCHIVE_SERVICE)
        assert "deps.archive_scenario" in text

    def test_quirk_3_include_archived_false_limit_12(self):
        text = _read(SCENARIO_ARCHIVE_SERVICE)
        assert "include_archived=False" in text
        assert "limit=12" in text

    def test_quirk_9_get_scenario_history_limit_20(self):
        text = _read(SCENARIO_ARCHIVE_SERVICE)
        assert "limit=20" in text

    def test_quirk_10_list_exports_and_build_export_lineage_limit_8(self):
        text = _read(SCENARIO_ARCHIVE_SERVICE)
        assert text.count("limit=8") >= 2

    def test_quirk_6_message_uses_scenario_name(self):
        text = _read(SCENARIO_ARCHIVE_SERVICE)
        assert 'f"Archived {record.scenario_name}."' in text

    def test_quirk_7_no_htmx_headers(self):
        body = _route_body("/scenarios/{scenario_id}/archive")
        clean = _strip_docstrings_and_comments(body)
        assert "HX-Trigger" not in clean
        assert "HX-Redirect" not in clean

    def test_quirk_8_no_form_input(self):
        body = _route_body("/scenarios/{scenario_id}/archive")
        clean = _strip_docstrings_and_comments(body)
        assert "await request.form()" not in clean

    def test_quirk_9_positional_get_scenario(self):
        text = _read(SCENARIO_ARCHIVE_SERVICE)
        assert "deps.get_scenario(scenario_id, user.user_id)" in text

    def test_quirk_10_archive_scenario_takes_no_name(self):
        text = _read(SCENARIO_ARCHIVE_SERVICE)
        assert "deps.archive_scenario(user.user_id, scenario_id)" in text


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
    def __init__(self, *, scenario: Optional[_StubScenarioRecord] = None) -> None:
        self.scenario = scenario
        self.archive_calls: List[Dict[str, Any]] = []
        self.rendered = object()

    def get_scenario(self, scenario_id: str, user_id: int):
        return self.scenario

    def archive_scenario(self, user_id: int, scenario_id: str) -> None:
        self.archive_calls.append({"user_id": user_id, "scenario_id": scenario_id})

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
    async def test_404_outcome_on_scenario_not_found(self):
        from app.services.scenario_archive_service import execute_scenario_archive_route

        deps = _StubDeps(scenario=None)
        request = _StubRequest()
        user = _StubUser(user_id=1)
        outcome = await execute_scenario_archive_route(
            request=request, scenario_id="missing", user=user, deps=deps
        )
        assert outcome.status_code == 404
        assert outcome.payload == {"error": "Scenario not found"}
        assert len(deps.archive_calls) == 0

    @pytest.mark.asyncio
    async def test_200_outcome_on_success(self):
        from app.services.scenario_archive_service import execute_scenario_archive_route

        deps = _StubDeps(scenario=_StubScenarioRecord("sid", 1, "proj", "Test Scenario"))
        request = _StubRequest()
        user = _StubUser(user_id=1)
        outcome = await execute_scenario_archive_route(
            request=request, scenario_id="sid", user=user, deps=deps
        )
        assert outcome.status_code == 200
        assert outcome.rendered_response is deps.rendered
        assert len(deps.archive_calls) == 1
        assert deps.archive_calls[0]["scenario_id"] == "sid"

    @pytest.mark.asyncio
    async def test_archive_scenario_called_with_user_id_scenario_id_only(self):
        from app.services.scenario_archive_service import execute_scenario_archive_route

        deps = _StubDeps(scenario=_StubScenarioRecord("sid", 1, "proj"))
        request = _StubRequest()
        user = _StubUser(user_id=1)
        await execute_scenario_archive_route(
            request=request, scenario_id="sid", user=user, deps=deps
        )
        # 2-arg call
        assert "scenario_id" in deps.archive_calls[0]
        assert "user_id" in deps.archive_calls[0]
        # No new_name field
        assert "new_name" not in deps.archive_calls[0]
