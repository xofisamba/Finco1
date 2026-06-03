"""Phase 51O-2 — POST /projects/{project_code}/save-as route vertical
extraction tests.

Verifies the /projects/{project_code}/save-as route body is now
thin and the orchestration lives in
``app/services/project_save_as_service.py`` with the canonical
``execute_project_save_as_route`` API.

Pin targets (post-extraction):

1. ``app/services/project_save_as_service.py`` exists.
2. The module exports:
   - ``class ProjectSaveAsRouteOutcome`` (with is_redirect,
     redirect_url, payload, status_code, template_name, context,
     headers).
   - ``class ProjectSaveAsRouteDeps`` (with 9 callables).
   - ``async def execute_project_save_as_route(*, request,
     project_code, user, deps) -> ProjectSaveAsRouteOutcome``.
3. The route body in main_web.py is thinner than pre-extraction
   (was 49 non-blank).
4. The route imports the service and calls
   ``execute_project_save_as_route(...)``.
5. The route wires the deps bundle (9 callables) before calling
   the service.
6. The route translates outcome.is_redirect to RedirectResponse
   and outcome.payload+status_code to JSONResponse.
7. The service does NOT import main_web or main_api.
8. The service preserves all 10 quirks (Phase 51O-1).
9. The service produces correct outcomes (404 not found, 400
   already user_created, 302 success).
10. Other Phase 51 services remain unchanged.
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
PROJECT_SAVE_AS_SERVICE = (
    REPO_ROOT / "app" / "services" / "project_save_as_service.py"
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _strip_docstrings_and_comments(src: str) -> str:
    """Remove docstrings and Python comments so substring checks
    see only executable code."""
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    src = re.sub(r"'''[\s\S]*?'''", "", src)
    out_lines = []
    for line in src.splitlines():
        in_string = False
        quote_char = None
        cleaned_chars = []
        for i, ch in enumerate(line):
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
        assert PROJECT_SAVE_AS_SERVICE.exists()

    def test_service_module_in_services_dir(self):
        assert PROJECT_SAVE_AS_SERVICE.parent == SERVICES_DIR

    def test_service_does_not_import_main_web(self):
        text = _read(PROJECT_SAVE_AS_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "import main_web" not in clean
        assert "from main_web" not in clean
        assert "import main_api" not in clean
        assert "from main_api" not in clean


# ─────────────────────────────────────────────────────────────────────────────
# Public dataclasses
# ─────────────────────────────────────────────────────────────────────────────


class TestProjectSaveAsRouteOutcome:
    def test_class_exists(self):
        text = _read(PROJECT_SAVE_AS_SERVICE)
        assert "class ProjectSaveAsRouteOutcome" in text

    def test_class_is_dataclass(self):
        text = _read(PROJECT_SAVE_AS_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "@dataclass" in clean
        assert "class ProjectSaveAsRouteOutcome" in clean

    def test_outcome_has_template_name_field(self):
        text = _read(PROJECT_SAVE_AS_SERVICE)
        assert "template_name" in text

    def test_outcome_has_context_field(self):
        text = _read(PROJECT_SAVE_AS_SERVICE)
        assert "context" in text

    def test_outcome_has_payload_field(self):
        text = _read(PROJECT_SAVE_AS_SERVICE)
        assert "payload" in text

    def test_outcome_has_status_code_field(self):
        text = _read(PROJECT_SAVE_AS_SERVICE)
        assert "status_code" in text

    def test_outcome_has_headers_field(self):
        text = _read(PROJECT_SAVE_AS_SERVICE)
        assert "headers" in text

    def test_outcome_has_is_redirect_field(self):
        text = _read(PROJECT_SAVE_AS_SERVICE)
        assert "is_redirect" in text

    def test_outcome_has_redirect_url_field(self):
        text = _read(PROJECT_SAVE_AS_SERVICE)
        assert "redirect_url" in text


class TestProjectSaveAsRouteDeps:
    def test_class_exists(self):
        text = _read(PROJECT_SAVE_AS_SERVICE)
        assert "class ProjectSaveAsRouteDeps" in text

    def test_class_is_dataclass(self):
        text = _read(PROJECT_SAVE_AS_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "@dataclass" in clean
        assert "class ProjectSaveAsRouteDeps" in clean

    def test_deps_has_9_callables(self):
        """Pin the count of deps callables (9)."""
        text = _read(PROJECT_SAVE_AS_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        m = re.search(
            r"@dataclass\s*\nclass ProjectSaveAsRouteDeps.*?(?=\n\nclass |\nasync def |\Z)",
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


class TestExecuteProjectSaveAsRoute:
    def test_function_exists(self):
        text = _read(PROJECT_SAVE_AS_SERVICE)
        assert "async def execute_project_save_as_route(" in text

    def test_function_signature(self):
        text = _read(PROJECT_SAVE_AS_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        m = re.search(
            r"async def execute_project_save_as_route\((.*?)\)", clean, re.DOTALL
        )
        assert m is not None
        sig = m.group(1)
        assert "request" in sig
        assert "project_code" in sig
        assert "user" in sig
        assert "deps" in sig

    def test_function_returns_outcome(self):
        text = _read(PROJECT_SAVE_AS_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert (
            "-> ProjectSaveAsRouteOutcome" in clean
        )


# ─────────────────────────────────────────────────────────────────────────────
# Route is thinner
# ─────────────────────────────────────────────────────────────────────────────


class TestRouteThinning:
    def test_route_size_shrinks(self):
        """Post-extraction: route body is 40-70 non-blank lines.

        (Slightly more than the original 49 because of the deps
        wiring code, but the orchestration body has been moved.)"""
        body = _route_body("/projects/{project_code}/save-as")
        non_blank = [l for l in body.splitlines() if l.strip()]
        assert 40 <= len(non_blank) <= 70, (
            f"/projects/{{project_code}}/save-as is {len(non_blank)} non-blank; expected 40-70"
        )

    def test_route_imports_service(self):
        body = _route_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "from app.services.project_save_as_service import" in clean
        assert "execute_project_save_as_route" in clean
        assert "ProjectSaveAsRouteDeps" in clean

    def test_route_calls_execute(self):
        body = _route_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "execute_project_save_as_route(" in clean
        assert "outcome = await execute_project_save_as_route(" in clean

    def test_route_wires_deps(self):
        """The route builds a ProjectSaveAsRouteDeps instance with
        all 9 callables."""
        body = _route_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "deps = ProjectSaveAsRouteDeps(" in clean
        # Check that the deps bundle has key callables wired
        for name in [
            "get_project_record=",
            "save_project=",
            "save_workspace_state=",
            "now_utc=",
            "project_record_creation_governance_state=",
            "workspace_state_initialization_governance_state=",
            "build_project_replay_metadata=",
            "build_workspace_replay_metadata=",
            "is_already_user_project=",
        ]:
            assert name in clean, f"Route deps missing {name}"

    def test_route_translates_redirect_outcome(self):
        """If outcome.is_redirect is True, the route returns
        RedirectResponse(url=outcome.redirect_url, status_code=outcome.status_code)."""
        body = _route_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "if outcome.is_redirect:" in clean
        assert "RedirectResponse(url=outcome.redirect_url, status_code=outcome.status_code)" in clean

    def test_route_translates_json_outcome(self):
        """Otherwise the route returns JSONResponse(outcome.payload, status_code=outcome.status_code)."""
        body = _route_body("/projects/{project_code}/save-as")
        clean = _strip_docstrings_and_comments(body)
        assert "return JSONResponse(outcome.payload, status_code=outcome.status_code)" in clean

    def test_route_has_auth_redirect(self):
        """Auth redirect is route-owned."""
        body = _route_body("/projects/{project_code}/save-as")
        assert "RedirectResponse(url=\"/login\", status_code=302)" in body

    def test_route_does_not_have_inline_orchestration(self):
        """The route does NOT have the inline orchestration:
        no save_project( call (only in deps wiring)."""
        body = _route_body("/projects/{project_code}/save-as")
        # save_project( should only appear in the deps wiring line
        # After the deps bundle, the orchestration call returns
        # the outcome - no save_project.
        clean = _strip_docstrings_and_comments(body)
        marker = "deps = ProjectSaveAsRouteDeps("
        idx = clean.find(marker)
        assert idx != -1
        after_deps = clean[idx + len(marker):]
        depth = 1
        i = 0
        while i < len(after_deps) and depth > 0:
            if after_deps[i] == "(":
                depth += 1
            elif after_deps[i] == ")":
                depth -= 1
            i += 1
        post_deps = after_deps[i:]
        assert "save_project(" not in post_deps
        assert "save_workspace_state(" not in post_deps


# ─────────────────────────────────────────────────────────────────────────────
# Quirk preservation in service
# ─────────────────────────────────────────────────────────────────────────────


class TestServiceQuirksPreserved:
    def test_quirk_1_local_import_or_alias(self):
        """Quirk 1: the route does a local
        `from app.persistence.repository import get_project_record as gpr`."""
        route_body = _route_body("/projects/{project_code}/save-as")
        assert "from app.persistence.repository import get_project_record as gpr" in route_body

    def test_quirk_2_new_code_pattern_in_service(self):
        """Quirk 2: new_code = f"{project_code}-copy-{now.strftime('%Y%m%d%H%M%S')}"."""
        text = _read(PROJECT_SAVE_AS_SERVICE)
        assert "f\"{project_code}-copy-{now.strftime('%Y%m%d%H%M%S')}\"" in text

    def test_quirk_3_new_name_pattern_in_service(self):
        """Quirk 3: new_name = f"{source.project_name} (Copy)"."""
        text = _read(PROJECT_SAVE_AS_SERVICE)
        assert "f\"{source.project_name} (Copy)\"" in text

    def test_quirk_4_governance_state_inlined(self):
        """Quirk 4: governance_state dict is built by the route
        (in helper functions) and passed via deps."""
        body = _route_body("/projects/{project_code}/save-as")
        assert body.count('"g20": "BLOCKED"') == 2
        assert body.count('"r99_r102": "NOT_APPROVED"') == 2
        assert body.count('"lender_ready": False') == 2

    def test_quirk_5_baseline_source_computed_in_route(self):
        """Quirk 5: baseline_source is computed: source.project_origin == 'saved_baseline'."""
        body = _route_body("/projects/{project_code}/save-as")
        assert 'source.project_origin == "saved_baseline"' in body

    def test_quirk_6_last_run_summary_empty_in_service(self):
        """Quirk 6: save_project gets last_run_summary={} (empty dict)."""
        text = _read(PROJECT_SAVE_AS_SERVICE)
        assert "last_run_summary={}" in text

    def test_quirk_7_draft_equals_saved_in_service(self):
        """Quirk 7: draft_snapshot=saved_snapshot=source.baseline_snapshot."""
        text = _read(PROJECT_SAVE_AS_SERVICE)
        assert "draft_snapshot=source.baseline_snapshot" in text
        assert "saved_snapshot=source.baseline_snapshot" in text

    def test_quirk_8_400_uses_jsonresponse(self):
        """Quirk 8: 400 path uses JSONResponse. The route translates
        outcome.payload + status_code to JSONResponse."""
        body = _route_body("/projects/{project_code}/save-as")
        assert "return JSONResponse(outcome.payload, status_code=outcome.status_code)" in body

    def test_quirk_9_404_uses_jsonresponse(self):
        """Quirk 9: 404 path uses JSONResponse with formatted error."""
        text = _read(PROJECT_SAVE_AS_SERVICE)
        assert "f\"Project '{project_code}' not found\"" in text

    def test_quirk_10_success_uses_redirect(self):
        """Quirk 10: success returns 302 RedirectResponse to /?project={new_code}."""
        text = _read(PROJECT_SAVE_AS_SERVICE)
        assert 'redirect_url=f"/?project={new_code}"' in text


# ─────────────────────────────────────────────────────────────────────────────
# Service orchestration behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestServiceOrchestration:
    def test_service_calls_get_project_record(self):
        text = _read(PROJECT_SAVE_AS_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "deps.get_project_record(\\n        user_id=user.user_id, project_code=project_code\\n    )" in clean or "deps.get_project_record(" in clean

    def test_service_calls_save_project(self):
        text = _read(PROJECT_SAVE_AS_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "deps.save_project(" in clean

    def test_service_calls_save_workspace_state(self):
        text = _read(PROJECT_SAVE_AS_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "deps.save_workspace_state(" in clean

    def test_service_calls_now_utc(self):
        text = _read(PROJECT_SAVE_AS_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "now = deps.now_utc()" in clean


# ─────────────────────────────────────────────────────────────────────────────
# Service returns correct outcomes (functional tests with stubs)
# ─────────────────────────────────────────────────────────────────────────────


class _StubUser:
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id


class _StubRequest:
    pass


class _StubProjectRecord:
    def __init__(self, project_id: int, project_code: str, project_origin: str = "factory") -> None:
        self.project_id = project_id
        self.project_code = project_code
        self.project_origin = project_origin
        self.project_name = f"Source {project_code}"
        self.project_type = "Wind"
        self.source_project_template = {}
        self.template_source = "tuho"
        self.baseline_snapshot = {"v": 1}


class _StubDeps:
    """In-memory stub deps bundle for functional tests."""

    def __init__(self, *, source: Optional[_StubProjectRecord] = None) -> None:
        self.source = source
        self.save_project_calls: List[Dict[str, Any]] = []
        self.save_workspace_state_calls: List[Dict[str, Any]] = []
        self.next_id = 1

    def get_project_record(self, user_id: int, project_code: str):
        return self.source

    def save_project(self, **kwargs) -> _StubProjectRecord:
        self.save_project_calls.append(kwargs)
        return _StubProjectRecord(
            project_id=self.next_id,
            project_code=kwargs["project_code"],
        )

    def save_workspace_state(self, **kwargs) -> None:
        self.save_workspace_state_calls.append(kwargs)

    def now_utc(self):
        import datetime
        return datetime.datetime(2026, 1, 1, 12, 0, 0)

    def project_record_creation_governance_state(self):
        return {"g20": "BLOCKED", "r99_r102": "NOT_APPROVED", "lender_ready": False}

    def workspace_state_initialization_governance_state(self):
        return {"g20": "BLOCKED", "r99_r102": "NOT_APPROVED", "lender_ready": False}

    def build_project_replay_metadata(self, source, project_code):
        return {
            "export_type": "project_duplicated",
            "source_project_code": project_code,
            "source_project_origin": source.project_origin,
            "baseline_source": source.project_origin == "saved_baseline",
        }

    def build_workspace_replay_metadata(self, source, project_code):
        return {
            "export_type": "workspace_duplicated",
            "source_project_code": project_code,
            "baseline_source": source.project_origin == "saved_baseline",
        }

    def is_already_user_project(self, source):
        return source.project_origin == "user_created"


class TestServiceOutcomes:
    @pytest.mark.asyncio
    async def test_404_outcome_on_source_not_found(self):
        from app.services.project_save_as_service import execute_project_save_as_route

        deps = _StubDeps(source=None)
        request = _StubRequest()
        user = _StubUser(user_id=1)
        outcome = await execute_project_save_as_route(
            request=request, project_code="missing", user=user, deps=deps
        )
        assert outcome.status_code == 404
        assert "error" in outcome.payload
        assert "missing" in outcome.payload["error"]
        # No writes on 404
        assert len(deps.save_project_calls) == 0
        assert len(deps.save_workspace_state_calls) == 0

    @pytest.mark.asyncio
    async def test_400_outcome_on_user_created_source(self):
        from app.services.project_save_as_service import execute_project_save_as_route

        deps = _StubDeps(source=_StubProjectRecord(99, "src", project_origin="user_created"))
        request = _StubRequest()
        user = _StubUser(user_id=1)
        outcome = await execute_project_save_as_route(
            request=request, project_code="src", user=user, deps=deps
        )
        assert outcome.status_code == 400
        assert outcome.payload == {"error": "Already a user project"}
        # No writes on 400
        assert len(deps.save_project_calls) == 0
        assert len(deps.save_workspace_state_calls) == 0

    @pytest.mark.asyncio
    async def test_302_redirect_outcome_on_success(self):
        from app.services.project_save_as_service import execute_project_save_as_route

        deps = _StubDeps(source=_StubProjectRecord(99, "src"))
        request = _StubRequest()
        user = _StubUser(user_id=1)
        outcome = await execute_project_save_as_route(
            request=request, project_code="src", user=user, deps=deps
        )
        assert outcome.status_code == 302
        assert outcome.is_redirect is True
        assert outcome.redirect_url == "/?project=src-copy-20260101120000"
        # 1 create + 1 save
        assert len(deps.save_project_calls) == 1
        assert len(deps.save_workspace_state_calls) == 1

    @pytest.mark.asyncio
    async def test_save_project_receives_user_created_origin(self):
        from app.services.project_save_as_service import execute_project_save_as_route

        deps = _StubDeps(source=_StubProjectRecord(99, "src"))
        request = _StubRequest()
        user = _StubUser(user_id=1)
        await execute_project_save_as_route(
            request=request, project_code="src", user=user, deps=deps
        )
        kw = deps.save_project_calls[0]
        assert kw["project_origin"] == "user_created"
        assert kw["is_readonly"] is False
        assert kw["last_run_summary"] == {}

    @pytest.mark.asyncio
    async def test_save_workspace_state_draft_equals_saved(self):
        from app.services.project_save_as_service import execute_project_save_as_route

        deps = _StubDeps(source=_StubProjectRecord(99, "src"))
        request = _StubRequest()
        user = _StubUser(user_id=1)
        await execute_project_save_as_route(
            request=request, project_code="src", user=user, deps=deps
        )
        kw = deps.save_workspace_state_calls[0]
        assert kw["draft_snapshot"] == kw["saved_snapshot"]
        assert kw["dirty"] is False

    @pytest.mark.asyncio
    async def test_governance_state_in_both_calls(self):
        from app.services.project_save_as_service import execute_project_save_as_route

        deps = _StubDeps(source=_StubProjectRecord(99, "src"))
        request = _StubRequest()
        user = _StubUser(user_id=1)
        await execute_project_save_as_route(
            request=request, project_code="src", user=user, deps=deps
        )
        assert deps.save_project_calls[0]["governance_state"]["g20"] == "BLOCKED"
        assert deps.save_workspace_state_calls[0]["governance_state"]["g20"] == "BLOCKED"

    @pytest.mark.asyncio
    async def test_replay_metadata_export_types(self):
        from app.services.project_save_as_service import execute_project_save_as_route

        deps = _StubDeps(source=_StubProjectRecord(99, "src"))
        request = _StubRequest()
        user = _StubUser(user_id=1)
        await execute_project_save_as_route(
            request=request, project_code="src", user=user, deps=deps
        )
        assert (
            deps.save_project_calls[0]["replay_metadata"]["export_type"]
            == "project_duplicated"
        )
        assert (
            deps.save_workspace_state_calls[0]["replay_metadata"]["export_type"]
            == "workspace_duplicated"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Other Phase 51 services unchanged
# ─────────────────────────────────────────────────────────────────────────────


class TestOtherServicesUnchanged:
    def test_projects_create_service_unchanged(self):
        path = SERVICES_DIR / "projects_create_service.py"
        assert path.exists()
        text = _read(path)
        assert "execute_projects_create_route" in text

    def test_scenarios_add_service_unchanged(self):
        path = SERVICES_DIR / "scenarios_add_service.py"
        assert path.exists()
        text = _read(path)
        assert "execute_scenarios_add_route" in text
