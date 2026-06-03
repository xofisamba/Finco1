"""Phase 51M-2 — POST /projects/create route vertical extraction tests.

Verifies the /projects/create route body is now thin and the
orchestration lives in
``app/services/projects_create_service.py`` with the canonical
``execute_projects_create_route`` API.

Pin targets (post-extraction):

1. ``app/services/projects_create_service.py`` exists.
2. The module exports:
   - ``class ProjectsCreateRouteOutcome`` (with template_name,
     context, payload, status_code, headers, is_redirect,
     redirect_url).
   - ``class ProjectsCreateRouteDeps`` (with 16 callables).
   - ``async def execute_projects_create_route(*, request,
     submitted, user, deps) -> ProjectsCreateRouteOutcome``.
3. The route body in main_web.py is thinner than pre-extraction
   (was 117 non-blank; should be ~93).
4. The route imports the service and calls
   ``execute_projects_create_route(...)``.
5. The route wires the deps bundle (16 callables) before calling
   the service.
6. The route does NOT import any forbidden helper
   (e.g. _coerce_form_text is in deps, not in the route body).
7. The service does NOT import main_web or main_api.
8. The service preserves all 10 quirks (Phase 51M-1).
9. The service produces correct outcomes (validation error
   and success).
10. Other Phase 51 services remain unchanged.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_WEB = REPO_ROOT / "main_web.py"
MAIN_API = REPO_ROOT / "main_api.py"
SERVICES_DIR = REPO_ROOT / "app" / "services"
PROJECTS_CREATE_SERVICE = (
    REPO_ROOT / "app" / "services" / "projects_create_service.py"
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _strip_docstrings_and_comments(src: str) -> str:
    """Remove docstrings and Python comments so substring checks
    see only executable code."""
    # Triple-quoted docstrings
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    src = re.sub(r"'''[\s\S]*?'''", "", src)
    # Line comments (best-effort, no # inside strings)
    out_lines = []
    for line in src.splitlines():
        # Strip trailing comment (avoid breaking on '#' inside strings;
        # this is a best-effort helper for test code).
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
        assert PROJECTS_CREATE_SERVICE.exists()

    def test_service_module_in_services_dir(self):
        assert PROJECTS_CREATE_SERVICE.parent == SERVICES_DIR

    def test_service_does_not_import_main_web(self):
        text = _read(PROJECTS_CREATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "import main_web" not in clean
        assert "from main_web" not in clean
        assert "import main_api" not in clean
        assert "from main_api" not in clean


# ─────────────────────────────────────────────────────────────────────────────
# Public dataclasses
# ─────────────────────────────────────────────────────────────────────────────


class TestProjectsCreateRouteOutcome:
    def test_class_exists(self):
        text = _read(PROJECTS_CREATE_SERVICE)
        assert "class ProjectsCreateRouteOutcome" in text

    def test_class_is_dataclass(self):
        text = _read(PROJECTS_CREATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "@dataclass" in clean
        assert "class ProjectsCreateRouteOutcome" in clean

    def test_outcome_has_template_name_field(self):
        text = _read(PROJECTS_CREATE_SERVICE)
        assert "template_name" in text

    def test_outcome_has_context_field(self):
        text = _read(PROJECTS_CREATE_SERVICE)
        assert "context" in text

    def test_outcome_has_payload_field(self):
        text = _read(PROJECTS_CREATE_SERVICE)
        assert "payload" in text

    def test_outcome_has_status_code_field(self):
        text = _read(PROJECTS_CREATE_SERVICE)
        assert "status_code" in text

    def test_outcome_has_headers_field(self):
        text = _read(PROJECTS_CREATE_SERVICE)
        assert "headers" in text

    def test_outcome_has_is_redirect_field(self):
        text = _read(PROJECTS_CREATE_SERVICE)
        assert "is_redirect" in text

    def test_outcome_has_redirect_url_field(self):
        text = _read(PROJECTS_CREATE_SERVICE)
        assert "redirect_url" in text

    def test_default_template_name_is_success_template(self):
        text = _read(PROJECTS_CREATE_SERVICE)
        assert 'template_name: str = "partials/new_project_result.html"' in text


class TestProjectsCreateRouteDeps:
    def test_class_exists(self):
        text = _read(PROJECTS_CREATE_SERVICE)
        assert "class ProjectsCreateRouteDeps" in text

    def test_class_is_dataclass(self):
        text = _read(PROJECTS_CREATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "@dataclass" in clean
        assert "class ProjectsCreateRouteDeps" in clean

    def test_deps_has_16_callables(self):
        """Pin the count of deps callables (16)."""
        text = _read(PROJECTS_CREATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # Find the class block
        m = re.search(
            r"@dataclass\s*\nclass ProjectsCreateRouteDeps.*?(?=\n\nclass |\nasync def |\Z)",
            clean,
            re.DOTALL,
        )
        assert m is not None
        body = m.group(0)
        # Count fields ending in `:` that are callables
        field_count = body.count(": Callable")
        assert field_count == 16, f"Expected 16 callable deps, got {field_count}"


# ─────────────────────────────────────────────────────────────────────────────
# Service entry point
# ─────────────────────────────────────────────────────────────────────────────


class TestExecuteProjectsCreateRoute:
    def test_function_exists(self):
        text = _read(PROJECTS_CREATE_SERVICE)
        assert "async def execute_projects_create_route(" in text

    def test_function_signature(self):
        text = _read(PROJECTS_CREATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        m = re.search(
            r"async def execute_projects_create_route\((.*?)\)", clean, re.DOTALL
        )
        assert m is not None
        sig = m.group(1)
        assert "request" in sig
        assert "submitted" in sig
        assert "user" in sig
        assert "deps" in sig

    def test_function_returns_outcome(self):
        text = _read(PROJECTS_CREATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert (
            "-> ProjectsCreateRouteOutcome" in clean
        )


# ─────────────────────────────────────────────────────────────────────────────
# Route is thinner
# ─────────────────────────────────────────────────────────────────────────────


class TestRouteThinning:
    def test_route_size_shrinks(self):
        """Post-extraction: route body is 60-110 non-blank lines."""
        body = _route_body("/projects/create")
        non_blank = [l for l in body.splitlines() if l.strip()]
        assert 60 <= len(non_blank) <= 110, (
            f"/projects/create is {len(non_blank)} non-blank; expected 60-110"
        )

    def test_route_imports_service(self):
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        assert "from app.services.projects_create_service import" in clean
        assert "execute_projects_create_route" in clean
        assert "ProjectsCreateRouteDeps" in clean

    def test_route_calls_execute(self):
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        assert "execute_projects_create_route(" in clean
        assert "outcome = await execute_projects_create_route(" in clean

    def test_route_wires_deps(self):
        """The route builds a ProjectsCreateRouteDeps instance with
        all 16 callables."""
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        assert "deps = ProjectsCreateRouteDeps(" in clean
        # Check that the deps bundle has key callables wired
        for name in [
            "submitted_new_project_defaults=",
            "coerce_form_text=",
            "canonical_project_type=",
            "normalize_template_source=",
            "validate_new_project_payload=",
            "slugify_project_code=",
            "get_project_by_code=",
            "project_baseline_snapshot=",
            "apply_new_project_required_inputs=",
            "create_project_record=",
            "save_workspace_state=",
            "governance_snapshot=",
            "replay_metadata_for_project=",
            "new_project_validation_error_context=",
            "template_source_label=",
            "render_template_response=",
        ]:
            assert name in clean, f"Route deps missing {name}"

    def test_route_returns_template_response_with_outcome(self):
        """The route uses ``templates.TemplateResponse(...,
        name=outcome.template_name, context=outcome.context,
        status_code=outcome.status_code, headers=outcome.headers or None)``."""
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        assert "name=outcome.template_name" in clean
        assert "context=outcome.context" in clean
        assert "status_code=outcome.status_code" in clean
        assert "headers=outcome.headers" in clean

    def test_route_has_auth_redirect(self):
        """Auth redirect is route-owned."""
        body = _route_body("/projects/create")
        assert "RedirectResponse(url=\"/login\", status_code=302)" in body

    def test_route_has_fastapi_form_injection(self):
        """The route signature has FastAPI Form() injection."""
        body = _route_body("/projects/create")
        assert "Form(" in body

    def test_route_does_not_have_inline_coerce(self):
        """The route does NOT call _coerce_form_text inline; it
        passes the helper via deps.coerce_form_text."""
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        # _coerce_form_text should only appear in the deps wiring
        # line, not in the body of the route (after the
        # ``deps = ProjectsCreateRouteDeps(`` block).
        # Split at the deps line and check the rest.
        marker = "deps = ProjectsCreateRouteDeps("
        idx = clean.find(marker)
        assert idx != -1
        after_deps = clean[idx + len(marker):]
        # Find the closing of the deps bundle (matching paren)
        depth = 1
        i = 0
        while i < len(after_deps) and depth > 0:
            if after_deps[i] == "(":
                depth += 1
            elif after_deps[i] == ")":
                depth -= 1
            i += 1
        post_deps = after_deps[i:]
        # The post-deps code (the orchestration call) should NOT
        # call _coerce_form_text directly (it uses deps.coerce_form_text).
        assert "_coerce_form_text(submitted" not in post_deps
        assert "_coerce_form_text(clean_name)" not in post_deps

    def test_route_does_not_have_inline_validate(self):
        """The route does NOT call _validate_new_project_payload
        inline; the service handles validation."""
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        # Same split as above
        marker = "deps = ProjectsCreateRouteDeps("
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
        assert "_validate_new_project_payload(submitted)" not in post_deps


# ─────────────────────────────────────────────────────────────────────────────
# Quirk preservation in service
# ─────────────────────────────────────────────────────────────────────────────


class TestServiceQuirksPreserved:
    def test_quirk_1_no_form_in_service(self):
        """Quirk 1: service does NOT use Form() or await request.form()."""
        text = _read(PROJECTS_CREATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "Form(" not in clean
        assert "await request.form()" not in clean

    def test_quirk_2_hx_redirect_in_service(self):
        """Quirk 2: service produces HX-Redirect on success."""
        text = _read(PROJECTS_CREATE_SERVICE)
        assert "HX-Redirect" in text
        assert 'f"/?project={project_record.project_code}"' in text

    def test_quirk_3_partial_template_render(self):
        """Quirk 3: service uses partials/new_project_result.html
        on success and partials/new_project_form.html on error."""
        text = _read(PROJECTS_CREATE_SERVICE)
        assert "partials/new_project_result.html" in text
        assert "partials/new_project_form.html" in text

    def test_quirk_4_uniqueness_loop_in_service(self):
        """Quirk 4: service handles project code uniqueness via
        while loop with -2, -3, ... suffixes."""
        text = _read(PROJECTS_CREATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert (
            "deps.get_project_by_code(user.user_id, project_code) is not None"
            in clean
        )
        assert 'project_code = f"{base_slug}-{suffix}"' in clean
        assert "suffix += 1" in clean

    def test_quirk_5_replay_metadata_export_types(self):
        """Quirk 5: service uses export_type values:
        'project_record_created' and 'workspace_project_created'."""
        text = _read(PROJECTS_CREATE_SERVICE)
        assert 'export_type="project_record_created"' in text
        assert 'export_type="workspace_project_created"' in text

    def test_quirk_6_template_source_validation(self):
        """Quirk 6: service validates that wind templates require
        Wind type and solar templates require Solar type."""
        text = _read(PROJECTS_CREATE_SERVICE)
        assert "Wind templates require" in text
        assert "Solar templates require" in text

    def test_quirk_7_save_workspace_state_args(self):
        """Quirk 7: service calls save_workspace_state with
        draft=saved=baseline_snapshot, dirty=False."""
        text = _read(PROJECTS_CREATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "deps.save_workspace_state(" in clean
        assert "draft_snapshot=baseline_snapshot" in clean
        assert "saved_snapshot=baseline_snapshot" in clean
        assert "dirty=False" in clean

    def test_quirk_8_project_origin_user_created(self):
        """Quirk 8: service uses project_origin='user_created' only."""
        text = _read(PROJECTS_CREATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert 'project_origin="user_created"' in clean
        # No 403 gate for non-user_created
        assert "status_code=403" not in clean

    def test_quirk_9_no_scenario_in_service(self):
        """Quirk 9: service does NOT call add_scenario or
        save_scenario."""
        text = _read(PROJECTS_CREATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "add_scenario(" not in clean
        assert "save_scenario(" not in clean
        assert "create_scenario(" not in clean

    def test_quirk_10_target_dscr_default_in_route(self):
        """Quirk 10: target_dscr default is in the route (Form
        injection), not the service."""
        body = _route_body("/projects/create")
        assert 'target_dscr: str = Form("1.20")' in body


# ─────────────────────────────────────────────────────────────────────────────
# Service orchestration behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestServiceOrchestration:
    def test_service_calls_coerce_canonicalize_normalize(self):
        """Service calls deps.coerce_form_text, deps.canonical_project_type,
        deps.normalize_template_source in order."""
        text = _read(PROJECTS_CREATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "deps.coerce_form_text(submitted[" in clean
        assert "deps.canonical_project_type(submitted[" in clean
        assert "deps.normalize_template_source(" in clean

    def test_service_calls_validation(self):
        text = _read(PROJECTS_CREATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "deps.validate_new_project_payload(submitted)" in clean

    def test_service_calls_slugify(self):
        text = _read(PROJECTS_CREATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "deps.slugify_project_code(clean_name)" in clean

    def test_service_calls_baseline_snapshot_and_apply(self):
        text = _read(PROJECTS_CREATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "deps.project_baseline_snapshot(" in clean
        assert "deps.apply_new_project_required_inputs(" in clean

    def test_service_calls_create_project_record(self):
        text = _read(PROJECTS_CREATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "deps.create_project_record(" in clean

    def test_service_calls_save_workspace_state(self):
        text = _read(PROJECTS_CREATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "deps.save_workspace_state(" in clean

    def test_service_calls_governance_snapshot_twice(self):
        """_governance_snapshot is called twice (create + save)."""
        text = _read(PROJECTS_CREATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert clean.count("deps.governance_snapshot(") == 2

    def test_service_calls_replay_metadata_twice(self):
        text = _read(PROJECTS_CREATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert clean.count("deps.replay_metadata_for_project(") == 2


# ─────────────────────────────────────────────────────────────────────────────
# Service returns correct outcomes (functional tests with stubs)
# ─────────────────────────────────────────────────────────────────────────────


class _StubUser:
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id


class _StubProjectRecord:
    def __init__(self, project_id: int, project_code: str) -> None:
        self.project_id = project_id
        self.project_code = project_code


class _StubRequest:
    pass


class _StubDeps:
    """In-memory stub deps bundle for functional tests."""

    def __init__(self, *, existing_codes: List[str] = None) -> None:
        self.existing_codes = existing_codes or []
        self.create_calls: List[Dict[str, Any]] = []
        self.save_calls: List[Dict[str, Any]] = []

    def submitted_new_project_defaults(self) -> dict:
        return {
            "project_name": "",
            "project_type": "Wind",
            "template_source": "",
            "country_market": "Croatia",
        }

    def coerce_form_text(self, value: str) -> str:
        return value.strip()

    def canonical_project_type(self, value: str) -> str:
        return "Wind" if value.lower() == "wind" else "Solar"

    def normalize_template_source(self, value: str, canonical: str) -> str:
        if not value:
            return ""
        return value.lower()

    def validate_new_project_payload(self, submitted: dict) -> list:
        errors = []
        if not submitted.get("project_name", "").strip():
            errors.append("project_name is required")
        if not submitted.get("project_type"):
            errors.append("project_type is required")
        return errors

    def slugify_project_code(self, value: str) -> str:
        return value.lower().replace(" ", "-")

    def get_project_by_code(self, user_id: int, project_code: str):
        if project_code in self.existing_codes:
            return _StubProjectRecord(99, project_code)
        return None

    def project_baseline_snapshot(self, canonical: str, source: str) -> dict:
        return {"canonical_type": canonical, "template_source": source}

    def apply_new_project_required_inputs(
        self, snapshot: dict, **kwargs
    ) -> dict:
        snapshot.update(kwargs)
        return snapshot

    def create_project_record(self, **kwargs) -> _StubProjectRecord:
        self.create_calls.append(kwargs)
        return _StubProjectRecord(
            project_id=len(self.create_calls),
            project_code=kwargs["project_code"],
        )

    def save_workspace_state(self, **kwargs) -> None:
        self.save_calls.append(kwargs)

    def governance_snapshot(self, project_code: str) -> dict:
        return {"project_code": project_code, "is_locked": False}

    def replay_metadata_for_project(
        self, project_code: str, project_id, export_type: str
    ) -> dict:
        return {
            "project_code": project_code,
            "export_type": export_type,
        }

    def new_project_validation_error_context(
        self, submitted: dict, errors: list
    ) -> dict:
        return {
            "submitted": submitted,
            "errors": errors,
        }

    def template_source_label(self, source: str) -> str:
        return f"Template: {source or 'blank'}"

    def render_template_response(self, *args, **kwargs):
        # The route uses templates.TemplateResponse directly; this
        # callable is here for symmetry with the dataclass API
        # (render_template_response is not used in the service
        # body since the route owns rendering).
        return None


class TestServiceOutcomes:
    @pytest.mark.asyncio
    async def test_validation_error_outcome(self):
        from app.services.projects_create_service import execute_projects_create_route

        deps = _StubDeps()
        request = _StubRequest()
        user = _StubUser(user_id=1)
        submitted = {
            "project_name": "",
            "project_type": "Wind",
            "template_source": "",
        }
        outcome = await execute_projects_create_route(
            request=request, submitted=submitted, user=user, deps=deps
        )
        assert outcome.status_code == 400
        assert outcome.template_name == "partials/new_project_form.html"
        assert "errors" in outcome.context

    @pytest.mark.asyncio
    async def test_success_outcome_creates_project_and_workspace(self):
        from app.services.projects_create_service import execute_projects_create_route

        deps = _StubDeps()
        request = _StubRequest()
        user = _StubUser(user_id=1)
        submitted = {
            "project_name": "My Project",
            "project_type": "Wind",
            "template_source": "",
        }
        outcome = await execute_projects_create_route(
            request=request, submitted=submitted, user=user, deps=deps
        )
        assert outcome.status_code == 200
        assert outcome.template_name == "partials/new_project_result.html"
        assert "HX-Redirect" in outcome.headers
        # 1 create + 1 save
        assert len(deps.create_calls) == 1
        assert len(deps.save_calls) == 1

    @pytest.mark.asyncio
    async def test_uniqueness_loop(self):
        from app.services.projects_create_service import execute_projects_create_route

        deps = _StubDeps(existing_codes=["my-project", "my-project-2"])
        request = _StubRequest()
        user = _StubUser(user_id=1)
        submitted = {
            "project_name": "My Project",
            "project_type": "Wind",
            "template_source": "",
        }
        outcome = await execute_projects_create_route(
            request=request, submitted=submitted, user=user, deps=deps
        )
        assert outcome.status_code == 200
        assert deps.create_calls[0]["project_code"] == "my-project-3"

    @pytest.mark.asyncio
    async def test_template_source_validation_wind(self):
        """Wind template + Solar type → validation error."""
        from app.services.projects_create_service import execute_projects_create_route

        deps = _StubDeps()
        request = _StubRequest()
        user = _StubUser(user_id=1)
        submitted = {
            "project_name": "My Project",
            "project_type": "Solar",  # mismatch
            "template_source": "tuho",  # wind template
        }
        outcome = await execute_projects_create_route(
            request=request, submitted=submitted, user=user, deps=deps
        )
        assert outcome.status_code == 400
        # The error context should mention wind
        assert any("Wind" in str(e) for e in outcome.context.get("errors", []))

    @pytest.mark.asyncio
    async def test_template_source_validation_solar(self):
        """Solar template + Wind type → validation error."""
        from app.services.projects_create_service import execute_projects_create_route

        deps = _StubDeps()
        request = _StubRequest()
        user = _StubUser(user_id=1)
        submitted = {
            "project_name": "My Project",
            "project_type": "Wind",  # mismatch
            "template_source": "oborovo",  # solar template
        }
        outcome = await execute_projects_create_route(
            request=request, submitted=submitted, user=user, deps=deps
        )
        assert outcome.status_code == 400
        assert any("Solar" in str(e) for e in outcome.context.get("errors", []))

    @pytest.mark.asyncio
    async def test_hx_redirect_includes_project_code(self):
        from app.services.projects_create_service import execute_projects_create_route

        deps = _StubDeps()
        request = _StubRequest()
        user = _StubUser(user_id=1)
        submitted = {
            "project_name": "My Project",
            "project_type": "Wind",
            "template_source": "",
        }
        outcome = await execute_projects_create_route(
            request=request, submitted=submitted, user=user, deps=deps
        )
        assert outcome.headers["HX-Redirect"] == "/?project=my-project"

    @pytest.mark.asyncio
    async def test_replay_metadata_export_types(self):
        from app.services.projects_create_service import execute_projects_create_route

        deps = _StubDeps()
        request = _StubRequest()
        user = _StubUser(user_id=1)
        submitted = {
            "project_name": "My Project",
            "project_type": "Wind",
            "template_source": "",
        }
        await execute_projects_create_route(
            request=request, submitted=submitted, user=user, deps=deps
        )
        # create_record: export_type='project_record_created'
        assert (
            deps.create_calls[0]["replay_metadata"]["export_type"]
            == "project_record_created"
        )
        # save_workspace: export_type='workspace_project_created'
        assert (
            deps.save_calls[0]["replay_metadata"]["export_type"]
            == "workspace_project_created"
        )

    @pytest.mark.asyncio
    async def test_governance_snapshot_in_both_calls(self):
        from app.services.projects_create_service import execute_projects_create_route

        deps = _StubDeps()
        request = _StubRequest()
        user = _StubUser(user_id=1)
        submitted = {
            "project_name": "My Project",
            "project_type": "Wind",
            "template_source": "",
        }
        await execute_projects_create_route(
            request=request, submitted=submitted, user=user, deps=deps
        )
        # Both create and save should have governance_state
        assert "governance_state" in deps.create_calls[0]
        assert "governance_state" in deps.save_calls[0]

    @pytest.mark.asyncio
    async def test_save_workspace_uses_baseline_snapshot(self):
        from app.services.projects_create_service import execute_projects_create_route

        deps = _StubDeps()
        request = _StubRequest()
        user = _StubUser(user_id=1)
        submitted = {
            "project_name": "My Project",
            "project_type": "Wind",
            "template_source": "",
        }
        await execute_projects_create_route(
            request=request, submitted=submitted, user=user, deps=deps
        )
        save_kwargs = deps.save_calls[0]
        # draft = saved = baseline_snapshot
        assert save_kwargs["draft_snapshot"] == save_kwargs["saved_snapshot"]
        assert save_kwargs["dirty"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Other Phase 51 services unchanged
# ─────────────────────────────────────────────────────────────────────────────


class TestOtherServicesUnchanged:
    def test_scenarios_save_service_unchanged(self):
        """The /scenarios/save service module is unchanged."""
        path = SERVICES_DIR / "scenarios_save_service.py"
        assert path.exists()
        text = _read(path)
        assert "execute_scenarios_save_route" in text

    def test_scenario_duplicate_service_unchanged(self):
        path = SERVICES_DIR / "scenario_duplicate_service.py"
        assert path.exists()
        text = _read(path)
        assert "execute_scenario_duplicate_route" in text

    def test_scenarios_add_service_unchanged(self):
        path = SERVICES_DIR / "scenarios_add_service.py"
        assert path.exists()
        text = _read(path)
        assert "execute_scenarios_add_route" in text
