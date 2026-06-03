"""Phase 51M-1 — POST /projects/create golden characterization.

Pins the current behavior of POST /projects/create
(create_project_route) in main_web.py BEFORE the future
51M-2 vertical extraction.

This is a characterization-only phase. No production code is
changed. The test file is the only deliverable that may be
modified by the characterization itself (to add new tests and
helpers).

18 categories covered (per spec):

1. Route existence and size.
2. Auth/session behavior.
3. form inputs and validation.
4. user_id source from auth/session.
5. project creation behavior.
6. default scenario/workspace behavior if present.
7. project type/template behavior.
8. intended persistence writes.
9. call ordering if order matters.
10. replay_metadata behavior.
11. governance_state behavior.
12. response type/template/context/JSON payload.
13. HTMX headers or absence.
14. redirect/status behavior.
15. error/fallback behavior.
16. forbidden side effects absent.
17. existing service-backed routes remain intact.
18. Phase 51F guardrails remain green.

Recommended future 51M-2 extraction boundary:

- New module: ``app/services/projects_create_service.py``
- Dataclass ``ProjectsCreateRouteOutcome`` with
  ``template_name``, ``context``, ``payload``, ``status_code``,
  ``headers``, ``is_redirect``, ``redirect_url``.
- Dataclass ``ProjectsCreateRouteDeps`` with ~10 callables:
  ``get_project_by_code``, ``create_project_record``,
  ``save_workspace_state``, ``_submitted_new_project_defaults``,
  ``_coerce_form_text``, ``_canonical_project_type``,
  ``_normalize_template_source``, ``_validate_new_project_payload``,
  ``_slugify_project_code``, ``_project_baseline_snapshot``,
  ``_apply_new_project_required_inputs``,
  ``_governance_snapshot``, ``_replay_metadata_for_project``,
  ``_new_project_validation_error_context``,
  ``_template_source_label``, ``render_template_response``.
- ``async def execute_projects_create_route(*, request,
  submitted, user, deps) -> ProjectsCreateRouteOutcome``.

Why a separate module (not extending scenario_state_service.py
or scenarios_add_service.py):

- scenario_state_service.py is data-layer only.
- scenarios_add_service.py is for /scenarios/add (creates a
  new ScenarioRecord from form + base case lookup). Project
  creation is a different concern (creates ProjectRecord +
  workspace state, no base case inheritance).
- save_run_service.py, run_service.py, etc. are unrelated.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_WEB = REPO_ROOT / "main_web.py"
SERVICES_DIR = REPO_ROOT / "app" / "services"


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
# 1. Route existence and size
# ─────────────────────────────────────────────────────────────────────────────


class TestRouteExistence:
    def test_route_exists(self):
        """POST /projects/create exists in main_web.py."""
        body = _route_body("/projects/create")
        assert body is not None

    def test_route_size_is_characteristic(self):
        """Pin current route size. Pre-extraction 117 non-blank
        (Phase 51I hotspot estimate). After 51M-2 it should shrink
        significantly."""
        body = _route_body("/projects/create")
        non_blank = [l for l in body.splitlines() if l.strip()]
        assert 95 <= len(non_blank) <= 140, (
            f"/projects/create is {len(non_blank)} non-blank lines; "
            f"expected 95-140 (pre-extraction characteristic)"
        )

    def test_no_execute_pattern_yet(self):
        """Pre-extraction: the route does NOT use a
        service.execute_*_route() pattern."""
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        assert "execute_projects_create_route(" not in clean
        text = _read(MAIN_WEB)
        assert "class ProjectsCreateRouteDeps" not in text


# ─────────────────────────────────────────────────────────────────────────────
# 2. Auth/session behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestAuthenticationBehavior:
    def test_route_uses_get_current_user(self):
        """Auth check: route uses get_current_user(request)."""
        body = _route_body("/projects/create")
        assert "get_current_user(request)" in body

    def test_route_uses_user_user_id(self):
        """user_id is derived from user.user_id."""
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        assert "user.user_id" in clean

    def test_unauth_returns_302_to_login(self):
        """Unauthenticated POST /projects/create returns 302 redirect
        to /login (NOT 401 JSON, NOT 200)."""
        from fastapi.testclient import TestClient

        from app.persistence.db import init_db
        from main_web import app

        init_db()
        c = TestClient(app)
        r = c.post("/projects/create", data={}, follow_redirects=False)
        assert r.status_code == 422, (
            f"Expected 422 (Form missing) or 302 (auth), got {r.status_code}; "
            f"body: {r.text[:200]}"
        )
        # If unauth and Form fields present, expect 302.
        r = c.post(
            "/projects/create",
            data={"project_name": "X", "project_type": "Solar"},
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert "/login" in r.headers.get("location", "")

    def test_unauth_no_json_response(self):
        """Unauthenticated request does NOT return JSON."""
        from fastapi.testclient import TestClient

        from app.persistence.db import init_db
        from main_web import app

        init_db()
        c = TestClient(app)
        r = c.post(
            "/projects/create",
            data={"project_name": "X", "project_type": "Solar"},
            follow_redirects=False,
        )
        assert not r.headers.get(
            "content-type", ""
        ).startswith("application/json")

    def test_unauth_no_htmx_redirect_header(self):
        """Unauthenticated request does NOT use HX-Redirect."""
        from fastapi.testclient import TestClient

        from app.persistence.db import init_db
        from main_web import app

        init_db()
        c = TestClient(app)
        r = c.post(
            "/projects/create",
            data={"project_name": "X", "project_type": "Solar"},
            follow_redirects=False,
        )
        assert "HX-Redirect" not in r.headers


# ─────────────────────────────────────────────────────────────────────────────
# 3. Form inputs
# ─────────────────────────────────────────────────────────────────────────────


class TestFormInputBehavior:
    def test_route_uses_fastapi_form(self):
        """The route uses FastAPI Form() parameters (not await request.form())."""
        body = _route_body("/projects/create")
        # The signature uses Form(...) for each parameter
        assert "Form(...)" in body or "Form(" in body
        # The route does NOT use await request.form() (it uses
        # the FastAPI Form dependency injection).
        assert "await request.form()" not in body

    def test_route_signature_has_18_form_fields(self):
        """The route signature has 18 form fields (project_name,
        project_type, template_source, country_market, capacity_mw,
        cod_date, construction_months, horizon_years,
        tariff_eur_mwh, ppa_term_years, p50_hours, opex_y1_keur,
        total_capex_keur, gearing_pct, interest_rate_pct,
        tenor_years, target_dscr)."""
        body = _route_body("/projects/create")
        expected_fields = [
            "project_name", "project_type", "template_source",
            "country_market", "capacity_mw", "cod_date",
            "construction_months", "horizon_years", "tariff_eur_mwh",
            "ppa_term_years", "p50_hours", "opex_y1_keur",
            "total_capex_keur", "gearing_pct", "interest_rate_pct",
            "tenor_years", "target_dscr",
        ]
        for field in expected_fields:
            assert f"{field}:" in body, (
                f"Route signature missing field '{field}'"
            )

    def test_default_country_market_is_croatia(self):
        """country_market defaults to 'Croatia'."""
        body = _route_body("/projects/create")
        assert 'country_market: str = Form("Croatia")' in body

    def test_default_target_dscr_is_1_20(self):
        """target_dscr defaults to '1.20'."""
        body = _route_body("/projects/create")
        assert 'target_dscr: str = Form("1.20")' in body

    def test_default_template_source_is_empty(self):
        """template_source defaults to '' (no template)."""
        body = _route_body("/projects/create")
        assert 'template_source: str = Form("")' in body


# ─────────────────────────────────────────────────────────────────────────────
# 4. user_id from session
# ─────────────────────────────────────────────────────────────────────────────


class TestUserIdSource:
    def test_user_id_never_from_form(self):
        """user_id is always derived from user.user_id, NEVER from form."""
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        # No form.get('user_id') or similar
        assert 'form.get("user_id"' not in clean
        assert "user.user_id" in clean


# ─────────────────────────────────────────────────────────────────────────────
# 5. Project creation behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestProjectCreationBehavior:
    def test_route_calls_submitted_new_project_defaults(self):
        """The route calls _submitted_new_project_defaults() to get
        the baseline submitted dict."""
        body = _route_body("/projects/create")
        assert "_submitted_new_project_defaults()" in body

    def test_route_coerces_form_text(self):
        """The route coerces form text via _coerce_form_text(project_name)."""
        body = _route_body("/projects/create")
        assert "_coerce_form_text(project_name)" in body

    def test_route_canonicalizes_project_type(self):
        """The route canonicalizes the project type via
        _canonical_project_type(project_type)."""
        body = _route_body("/projects/create")
        assert "_canonical_project_type(project_type)" in body

    def test_route_normalizes_template_source(self):
        """The route normalizes the template source via
        _normalize_template_source(template_source, canonical_type)."""
        body = _route_body("/projects/create")
        assert "_normalize_template_source(template_source, canonical_type)" in body

    def test_route_validates_new_project_payload(self):
        """The route validates the payload via
        _validate_new_project_payload(submitted)."""
        body = _route_body("/projects/create")
        assert "_validate_new_project_payload(submitted)" in body

    def test_route_slugs_project_code(self):
        """The route slugifies the project code via
        _slugify_project_code(clean_name)."""
        body = _route_body("/projects/create")
        assert "_slugify_project_code(clean_name)" in body

    def test_route_handles_project_code_uniqueness(self):
        """The route handles project_code uniqueness: if
        get_project_by_code returns non-None, it appends a
        numeric suffix and retries."""
        body = _route_body("/projects/create")
        assert "get_project_by_code(user.user_id, project_code) is not None" in body
        assert 'project_code = f"{base_slug}-{suffix}"' in body

    def test_route_creates_project_record(self):
        """The route calls create_project_record(...) with the
        correct kwargs (user_id, project_code, project_name,
        project_type, project_origin='user_created',
        template_source, baseline_snapshot, governance_state,
        replay_metadata)."""
        body = _route_body("/projects/create")
        assert "create_project_record(" in body
        assert "user_id=user.user_id" in body
        assert "project_code=project_code" in body
        assert "project_name=clean_name" in body
        assert "project_type=canonical_type" in body
        assert 'project_origin="user_created"' in body
        assert "template_source=normalized_source" in body
        assert "baseline_snapshot=baseline_snapshot" in body
        assert "governance_state=" in body
        assert "replay_metadata=" in body

    def test_route_saves_workspace_state(self):
        """The route calls save_workspace_state(...) to initialize
        the workspace for the new project."""
        body = _route_body("/projects/create")
        assert "save_workspace_state(" in body
        # Required kwargs
        assert "user_id=user.user_id" in body
        assert "project_id=project_record.project_id" in body
        assert "project_code=project_record.project_code" in body
        assert "draft_snapshot=baseline_snapshot" in body
        assert "saved_snapshot=baseline_snapshot" in body
        assert "dirty=False" in body
        assert "governance_state=" in body
        assert "replay_metadata=" in body


# ─────────────────────────────────────────────────────────────────────────────
# 6. Default scenario/workspace behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestDefaultScenarioWorkspaceBehavior:
    def test_route_initializes_workspace_with_baseline_snapshot(self):
        """The route initializes the workspace with the
        baseline_snapshot (NOT with a form-snapshot from
        /scenarios/save). The draft and saved snapshots are both
        baseline_snapshot."""
        body = _route_body("/projects/create")
        # draft_snapshot = baseline_snapshot
        assert "draft_snapshot=baseline_snapshot" in body
        # saved_snapshot = baseline_snapshot
        assert "saved_snapshot=baseline_snapshot" in body
        # dirty = False (no unsaved edits)
        assert "dirty=False" in body

    def test_route_does_not_create_scenario_explicitly(self):
        """The route does NOT call add_scenario(...) or
        create_scenario(...). It only creates the ProjectRecord
        and WorkspaceState. The Base Case scenario is created
        later (via factory helpers)."""
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        assert "add_scenario(" not in clean
        assert "create_scenario(" not in clean
        assert "save_scenario(" not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 7. Project type/template behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestProjectTypeTemplateBehavior:
    def test_template_source_validation_for_wind(self):
        """If normalized_source is 'tuho' or 'generic_wind',
        canonical_type must be 'Wind'. Otherwise validation fails."""
        body = _route_body("/projects/create")
        assert 'normalized_source in {"tuho", "generic_wind"}' in body
        assert 'canonical_type != "Wind"' in body
        assert "Wind templates require project type Wind." in body

    def test_template_source_validation_for_solar(self):
        """If normalized_source is 'oborovo' or 'generic_solar',
        canonical_type must be 'Solar'. Otherwise validation fails."""
        body = _route_body("/projects/create")
        assert 'normalized_source in {"oborovo", "generic_solar"}' in body
        assert 'canonical_type != "Solar"' in body
        assert "Solar templates require project type Solar." in body

    def test_route_uses_project_baseline_snapshot(self):
        """The route builds the baseline snapshot via
        _project_baseline_snapshot(canonical_type, normalized_source)."""
        body = _route_body("/projects/create")
        assert "_project_baseline_snapshot(canonical_type, normalized_source)" in body

    def test_route_applies_required_inputs(self):
        """The route applies required inputs to the baseline
        snapshot via _apply_new_project_required_inputs(...)."""
        body = _route_body("/projects/create")
        assert "_apply_new_project_required_inputs(" in body


# ─────────────────────────────────────────────────────────────────────────────
# 8. Intended persistence writes
# ─────────────────────────────────────────────────────────────────────────────


class TestPersistenceSideEffects:
    """Pin intended persistence calls."""

    def test_get_project_by_code_called(self):
        """get_project_by_code is called in a loop to find a
        unique project_code."""
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        assert "get_project_by_code(" in clean

    def test_create_project_record_called_once(self):
        """create_project_record is called exactly once per success."""
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        assert clean.count("create_project_record(") == 1

    def test_save_workspace_state_called_once(self):
        """save_workspace_state is called exactly once per success
        to initialize the workspace."""
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        assert clean.count("save_workspace_state(") == 1

    def test_governance_snapshot_called_twice(self):
        """_governance_snapshot is called twice per success (once
        for create_project_record, once for save_workspace_state)."""
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        assert clean.count("_governance_snapshot(") == 2

    def test_replay_metadata_for_project_called_twice(self):
        """_replay_metadata_for_project is called twice per success
        (once for create_project_record, once for save_workspace_state)."""
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        assert clean.count("_replay_metadata_for_project(") == 2

    def test_no_template_response_uses_render_args(self):
        """The success response uses templates.TemplateResponse
        with name='partials/new_project_result.html' and
        headers={'HX-Redirect': f'/?project=...'}."""
        body = _route_body("/projects/create")
        assert 'name="partials/new_project_result.html"' in body
        assert "HX-Redirect" in body
        assert "templates.TemplateResponse(" in body


# ─────────────────────────────────────────────────────────────────────────────
# 9. Call ordering
# ─────────────────────────────────────────────────────────────────────────────


class TestCallOrdering:
    def test_ordering_auth_form_coerce_validate_project_create_workspace(self):
        """Order: get_current_user -> _submitted_new_project_defaults
        + form values -> _coerce_form_text -> _canonical_project_type
        -> _normalize_template_source -> _validate_new_project_payload
        -> template validation -> [loop] get_project_by_code ->
        _project_baseline_snapshot ->
        _apply_new_project_required_inputs -> create_project_record
        -> save_workspace_state -> TemplateResponse."""
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        positions = {
            "auth": body.find("get_current_user(request)"),
            "submitted_defaults": clean.find("_submitted_new_project_defaults()"),
            "coerce_form_text": clean.find("_coerce_form_text("),
            "canonical_project_type": clean.find("_canonical_project_type("),
            "normalize_template_source": clean.find("_normalize_template_source("),
            "validate_new_project_payload": clean.find("_validate_new_project_payload("),
            "project_baseline_snapshot": clean.find("_project_baseline_snapshot("),
            "create_project_record": clean.find("create_project_record("),
            "save_workspace_state": clean.find("save_workspace_state("),
            "template_response": clean.rfind("templates.TemplateResponse("),
        }
        for k, v in positions.items():
            assert v != -1, f"{k} not found in route body"
        # Ordering assertions
        assert positions["auth"] < positions["submitted_defaults"]
        assert positions["submitted_defaults"] < positions["coerce_form_text"]
        assert positions["coerce_form_text"] < positions["canonical_project_type"]
        assert positions["canonical_project_type"] < positions["normalize_template_source"]
        assert positions["normalize_template_source"] < positions["validate_new_project_payload"]
        assert positions["validate_new_project_payload"] < positions["project_baseline_snapshot"]
        assert positions["project_baseline_snapshot"] < positions["create_project_record"]
        assert positions["create_project_record"] < positions["save_workspace_state"]
        assert positions["save_workspace_state"] < positions["template_response"]


# ─────────────────────────────────────────────────────────────────────────────
# 10. replay_metadata
# ─────────────────────────────────────────────────────────────────────────────


class TestReplayMetadata:
    def test_create_project_record_export_type(self):
        """The replay_metadata for create_project_record uses
        export_type='project_record_created'."""
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        # The export_type for create_project_record
        assert 'export_type="project_record_created"' in clean

    def test_save_workspace_state_export_type(self):
        """The replay_metadata for save_workspace_state uses
        export_type='workspace_project_created'."""
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        assert 'export_type="workspace_project_created"' in clean


# ─────────────────────────────────────────────────────────────────────────────
# 11. governance_state
# ─────────────────────────────────────────────────────────────────────────────


class TestGovernanceState:
    def test_governance_state_uses_governance_snapshot(self):
        """The route passes _governance_snapshot(project_code) to
        both create_project_record and save_workspace_state."""
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        assert "_governance_snapshot(project_code)" in clean
        assert clean.count("_governance_snapshot(project_code)") == 2


# ─────────────────────────────────────────────────────────────────────────────
# 12. Response behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestResponseBehavior:
    def test_success_uses_new_project_result_template(self):
        """The success response uses templates.TemplateResponse
        rendering the partials/new_project_result.html template."""
        body = _route_body("/projects/create")
        assert 'name="partials/new_project_result.html"' in body

    def test_success_template_context_includes_project_record(self):
        """The success template context includes 'project_record'
        and 'template_source_label'."""
        body = _route_body("/projects/create")
        assert '"project_record": project_record' in body
        assert '"template_source_label": _template_source_label(normalized_source)' in body

    def test_validation_error_uses_new_project_form_template(self):
        """The 400 validation error response uses
        partials/new_project_form.html with the
        _new_project_validation_error_context."""
        body = _route_body("/projects/create")
        assert 'name="partials/new_project_form.html"' in body
        assert "_new_project_validation_error_context(submitted, validation_errors)" in body
        assert "status_code=400" in body

    def test_no_full_workspace_render(self):
        """The success response is NOT a full workspace render.
        It returns the partials/new_project_result.html template
        with HX-Redirect header (different from /scenarios/save
        and /scenarios/{id}/duplicate which return full workspace
        renders)."""
        body = _route_body("/projects/create")
        # The success template is partials/new_project_result.html
        # (NOT scenarios/_workspace_partial.html)
        assert "scenarios/_workspace_partial.html" not in body
        assert 'name="partials/new_project_result.html"' in body


# ─────────────────────────────────────────────────────────────────────────────
# 13. HTMX headers
# ─────────────────────────────────────────────────────────────────────────────


class TestHtmxHeaders:
    def test_success_emits_hx_redirect(self):
        """The success response emits HX-Redirect
        (different from /scenarios/save which uses
        HX-Trigger: scenarioAdded, and /scenarios/{id}/duplicate
        which doesn't emit HX headers)."""
        body = _route_body("/projects/create")
        assert "HX-Redirect" in body
        assert "templates.TemplateResponse(" in body

    def test_validation_error_no_hx_redirect(self):
        """The 400 validation error response does NOT emit
        HX-Redirect (it returns the form template with errors)."""
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        # The single HX-Redirect reference is in the success path
        assert clean.count("HX-Redirect") == 1


# ─────────────────────────────────────────────────────────────────────────────
# 14. Redirect/status behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestRedirectStatus:
    def test_auth_redirect_uses_redirectresponse(self):
        """The 302 auth redirect uses RedirectResponse(url='/login',
        status_code=302)."""
        body = _route_body("/projects/create")
        assert "RedirectResponse(url=\"/login\", status_code=302)" in body

    def test_validation_error_status_400(self):
        """The 400 validation error response uses status_code=400."""
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        assert "status_code=400" in clean


# ─────────────────────────────────────────────────────────────────────────────
# 15. Error/fallback behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestErrorFallback:
    def test_no_broad_except_in_route(self):
        """The route does NOT wrap the body in broad `except Exception:`."""
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        assert "except Exception:" not in clean

    def test_validation_errors_append_messages(self):
        """The route appends validation error messages:
        - "Wind templates require project type Wind."
        - "Solar templates require project type Solar."
        """
        body = _route_body("/projects/create")
        for msg in (
            "Wind templates require project type Wind.",
            "Solar templates require project type Solar.",
        ):
            assert msg in body, f"Missing validation message: {msg}"


# ─────────────────────────────────────────────────────────────────────────────
# 16. Forbidden side effects absent
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
        "run_project",
        "build_institutional_workbook_export",
        "build_excel_export_for_post_request",
        "build_runtime_summary_csv_export",
        "build_values_only_export_for_project",
    )

    def test_route_does_not_call_record_export_family(self):
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        for helper in (
            "record_export(",
            "record_download_export(",
            "record_runtime_summary_export(",
            "record_institutional_workbook_export(",
        ):
            assert helper not in clean

    def test_route_does_not_call_record_workspace_runtime(self):
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        # Note: save_workspace_state is OK (it's an intended write
        # to initialize the workspace). record_workspace_runtime is
        # NOT used here.
        assert "record_workspace_runtime(" not in clean

    def test_route_does_not_call_update_scenario_last_run_summary(self):
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        assert "update_scenario_last_run_summary(" not in clean

    def test_route_does_not_call_save_run(self):
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        assert "save_run(" not in clean

    def test_route_does_not_call_run_project(self):
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        assert "run_project(" not in clean

    def test_route_does_not_call_excel_export_builders(self):
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        for helper in (
            "build_institutional_workbook_export(",
            "build_excel_export_for_post_request(",
            "build_runtime_summary_csv_export(",
            "build_values_only_export_for_project(",
        ):
            assert helper not in clean

    def test_route_does_not_use_db_or_session_directly(self):
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        for forbidden in (
            "db.add",
            "db.commit",
            "db.flush",
            "session.add",
            "session.commit",
        ):
            assert forbidden not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 17. Existing service-backed routes remain intact
# ─────────────────────────────────────────────────────────────────────────────


class TestArchitectureGuardrails:
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
            ("/scenarios/add", "execute_scenarios_add_route("),
        ],
    )
    def test_other_routes_remain_service_backed(self, route: str, marker: str):
        """All previously-extracted routes remain service-backed."""
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
        assert m is not None, f"Route {route} not found"
        body = m.group(0)
        clean = _strip_docstrings_and_comments(body)
        assert marker in clean

    @pytest.mark.parametrize(
        "service_file",
        [
            "run_service.py",
            "compare_service.py",
            "validation_service.py",
            "download_service.py",
            "save_run_service.py",
            "scenarios_save_service.py",
            "scenario_state_service.py",
            "scenario_state_route_service.py",
            "scenario_duplicate_service.py",
            "scenarios_add_service.py",
            "export_service.py",
            "export_audit_service.py",
        ],
    )
    def test_no_service_imports_main_web_or_main_api(self, service_file: str):
        path = SERVICES_DIR / service_file
        if not path.exists():
            return
        text = _read(path)
        clean = _strip_docstrings_and_comments(text)
        assert "import main_web" not in clean
        assert "from main_web" not in clean
        assert "import main_api" not in clean
        assert "from main_api" not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 18. Phase 51F guardrails (smoke check)
# ─────────────────────────────────────────────────────────────────────────────


class TestPhase51FGuardrailsSmokeCheck:
    def test_app_still_imports(self):
        from main_web import app
        assert app is not None

    def test_repository_functions_exist(self):
        from app.persistence.repository import (  # noqa: F401
            create_project_record,
            get_project_by_code,
            save_workspace_state,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Behavior quirks (to be preserved in future 51M-2)
# ─────────────────────────────────────────────────────────────────────────────


class TestBehaviorQuirks:
    """Pin behavior quirks that 51M-2 must preserve."""

    def test_quirk_1_uses_fastapi_form_injection(self):
        """Quirk 1: the route uses FastAPI Form() parameters (NOT
        await request.form() or _collect_form_snapshot)."""
        body = _route_body("/projects/create")
        assert "Form(" in body
        assert "await request.form()" not in body
        assert "_collect_form_snapshot" not in body

    def test_quirk_2_hx_redirect_on_success(self):
        """Quirk 2: the success response emits HX-Redirect
        (different from /scenarios/save which uses
        HX-Trigger: scenarioAdded, and /scenarios/{id}/duplicate
        which doesn't emit HX headers)."""
        body = _route_body("/projects/create")
        assert "HX-Redirect" in body
        assert 'HX-Redirect": f"/?project={project_record.project_code}"' in body

    def test_quirk_3_partial_template_render(self):
        """Quirk 3: the success response is a partial template
        render (partials/new_project_result.html), NOT a full
        workspace render."""
        body = _route_body("/projects/create")
        assert 'name="partials/new_project_result.html"' in body

    def test_quirk_4_project_code_uniqueness_loop(self):
        """Quirk 4: the route handles project_code uniqueness via
        a while loop that appends -2, -3, ... suffixes."""
        body = _route_body("/projects/create")
        assert "while get_project_by_code(user.user_id, project_code) is not None:" in body
        assert 'project_code = f"{base_slug}-{suffix}"' in body
        assert "suffix += 1" in body

    def test_quirk_5_replay_metadata_uses_export_type(self):
        """Quirk 5: the replay_metadata uses export_type values:
        'project_record_created' and 'workspace_project_created'.
        Different from /scenarios/add (which uses action='add_scenario')
        and /scenarios/save (which uses export_type='saved_scenario_snapshot')."""
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        assert 'export_type="project_record_created"' in clean
        assert 'export_type="workspace_project_created"' in clean
        # And NO "action" key in the replay_metadata
        assert '"action"' not in clean

    def test_quirk_6_template_source_validation(self):
        """Quirk 6: the route validates that wind templates require
        Wind project type, and solar templates require Solar
        project type. (Different from /scenarios/save and
        /scenarios/{id}/duplicate which don't have this check.)"""
        body = _route_body("/projects/create")
        assert 'normalized_source in {"tuho", "generic_wind"}' in body
        assert 'normalized_source in {"oborovo", "generic_solar"}' in body
        assert "Wind templates require project type Wind." in body
        assert "Solar templates require project type Solar." in body

    def test_quirk_7_save_workspace_state_initializes(self):
        """Quirk 7: the route calls save_workspace_state with
        draft_snapshot = saved_snapshot = baseline_snapshot and
        dirty = False (no unsaved edits on a freshly created
        project)."""
        body = _route_body("/projects/create")
        assert "draft_snapshot=baseline_snapshot" in body
        assert "saved_snapshot=baseline_snapshot" in body
        assert "dirty=False" in body

    def test_quirk_8_origin_user_created_only(self):
        """Quirk 8: the route creates the project with
        project_origin='user_created' (NOT factory_template or
        saved_baseline). The route does NOT have a branch for
        non-user_created projects; it always creates a
        user_created project."""
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        assert 'project_origin="user_created"' in clean
        # No "user_created" gate (no 403 check)
        assert "status_code=403" not in clean
        assert "non-user_created" not in body

    def test_quirk_9_no_scenario_created_directly(self):
        """Quirk 9: the route does NOT call add_scenario(...) or
        save_scenario(...). It only creates ProjectRecord and
        WorkspaceState. The Base Case scenario is created later
        (via factory helpers or on first /scenarios/save)."""
        body = _route_body("/projects/create")
        clean = _strip_docstrings_and_comments(body)
        assert "add_scenario(" not in clean
        assert "save_scenario(" not in clean
        assert "create_scenario(" not in clean

    def test_quirk_10_form_default_target_dscr(self):
        """Quirk 10: target_dscr defaults to '1.20' (this is the
        standard DSCR target for new projects)."""
        body = _route_body("/projects/create")
        assert 'target_dscr: str = Form("1.20")' in body


# ─────────────────────────────────────────────────────────────────────────────
# Recommended 51M-2 extraction boundary
# ─────────────────────────────────────────────────────────────────────────────


class TestExtractionBoundaryRecommendation:
    def test_projects_create_service_does_not_exist_yet(self):
        """Pre-51M-2: projects_create_service.py does NOT exist."""
        path = SERVICES_DIR / "projects_create_service.py"
        assert not path.exists(), (
            f"{path} must NOT exist before Phase 51M-2"
        )

    def test_recommended_module_name(self):
        """The recommended 51M-2 module is
        app/services/projects_create_service.py."""
        path = SERVICES_DIR / "projects_create_service.py"
        assert not path.exists()
