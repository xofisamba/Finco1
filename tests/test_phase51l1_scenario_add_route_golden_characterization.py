"""Phase 51L-1 — POST /scenarios/add golden characterization.

Pins the current behavior of POST /scenarios/add
(add_scenario_endpoint) in main_web.py BEFORE the future
51L-2 vertical extraction.

This is a characterization-only phase. No production code is
changed.

18 categories covered (per spec):

1. Route existence and size.
2. Auth/session behavior.
3. Form input behavior.
4. user_id source from auth/session, not form.
5. active_project behavior.
6. Scenario creation behavior.
7. Workspace/snapshot behavior.
8. Intended persistence writes.
9. Call ordering if order matters.
10. replay_metadata export_type values if present.
11. governance_state behavior if present.
12. Response type/template/context/JSON payload.
13. HTMX headers or absence.
14. Redirect/status behavior.
15. Error/fallback behavior.
16. Forbidden side effects absent.
17. Existing service-backed routes remain intact.
18. Phase 51F guardrails remain green.

Recommended future 51L-2 extraction boundary:

- New module: ``app/services/scenarios_add_service.py``
- Dataclass ``ScenariosAddRouteOutcome`` with
  ``template_name``, ``context``, ``payload``, ``status_code``,
  ``headers``, ``is_redirect``, ``redirect_url``.
- Dataclass ``ScenariosAddRouteDeps`` with ~10 callables:
  ``get_project_record``, ``list_scenarios``,
  ``_get_least_created_scenario_for_project``,
  ``promote_scenario_to_base_case``, ``add_scenario``,
  ``get_workspace_state``, ``build_scenario_tab_context``,
  ``render_template_response``.
- ``async def execute_scenarios_add_route(*, request,
  form, user, deps) -> ScenariosAddRouteOutcome``.

Why not extend ``scenario_state_service.py``: data-layer only.
Why not extend ``scenario_state_route_service.py``: draft/discard
only (no new scenario creation).
Why not extend ``scenarios_save_service.py``: save creates from
form snapshot; add creates from parent base case (different
parent inheritance).
Why not extend ``scenario_duplicate_service.py``: duplicate
copies an existing ScenarioRecord; add creates a new one with
parent inheritance from base case.
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
        """POST /scenarios/add exists in main_web.py."""
        body = _route_body("/scenarios/add")
        assert body is not None

    def test_route_size_is_characteristic(self):
        """Pin current route size. Pre-extraction ~62 non-blank
        (Phase 51I hotspot estimate). After 51L-2 it should shrink
        to ~25-30 non-blank (thin route)."""
        body = _route_body("/scenarios/add")
        non_blank = [l for l in body.splitlines() if l.strip()]
        assert 50 <= len(non_blank) <= 85, (
            f"/scenarios/add is {len(non_blank)} non-blank lines; "
            f"expected 50-85 (pre-extraction characteristic)"
        )

    def test_no_execute_pattern_yet(self):
        """Pre-extraction: the route does NOT use a
        service.execute_*_route() pattern."""
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        assert "execute_scenarios_add_route(" not in clean
        # And the deps class is not yet defined
        text = _read(MAIN_WEB)
        assert "class ScenariosAddRouteDeps" not in text
        assert "class ScenariosAddDeps" not in text


# ─────────────────────────────────────────────────────────────────────────────
# 2. Auth/session behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestAuthenticationBehavior:
    def test_route_uses_get_current_user(self):
        """Auth check: route uses get_current_user(request)."""
        body = _route_body("/scenarios/add")
        assert "get_current_user(request)" in body

    def test_route_uses_user_user_id(self):
        """user_id is derived from user.user_id."""
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        assert "user.user_id" in clean

    def test_unauth_returns_302_to_login(self):
        """Unauthenticated POST /scenarios/add returns 302 redirect
        to /login (NOT 401 JSON, NOT 200)."""
        from fastapi.testclient import TestClient

        from app.persistence.db import init_db
        from main_web import app

        init_db()
        c = TestClient(app)
        r = c.post("/scenarios/add", data={}, follow_redirects=False)
        assert r.status_code == 302, (
            f"Expected 302, got {r.status_code}; body: {r.text[:200]}"
        )
        assert "/login" in r.headers.get("location", "")

    def test_unauth_no_json_response(self):
        """Unauthenticated request does NOT return JSON."""
        from fastapi.testclient import TestClient

        from app.persistence.db import init_db
        from main_web import app

        init_db()
        c = TestClient(app)
        r = c.post("/scenarios/add", data={}, follow_redirects=False)
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
        r = c.post("/scenarios/add", data={}, follow_redirects=False)
        assert "HX-Redirect" not in r.headers


# ─────────────────────────────────────────────────────────────────────────────
# 3. Form input behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestFormInputBehavior:
    def test_route_reads_form(self):
        """The route reads the form via await request.form()."""
        body = _route_body("/scenarios/add")
        assert "await request.form()" in body

    def test_route_reads_project_code_field(self):
        """The route reads the project_code field via
        form.get('project_code', '').strip()."""
        body = _route_body("/scenarios/add")
        assert 'form.get("project_code", "").strip()' in body

    def test_route_reads_scenario_name_field(self):
        """The route reads the scenario_name field via
        form.get('scenario_name', '').strip()."""
        body = _route_body("/scenarios/add")
        assert 'form.get("scenario_name", "").strip()' in body

    def test_route_does_not_call_collect_form_snapshot(self):
        """The route does NOT call _collect_form_snapshot (unlike
        /scenarios/save). It reads individual form fields."""
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        assert "_collect_form_snapshot" not in clean

    def test_missing_project_code_returns_400(self):
        """If project_code is empty, the route returns 400 JSON."""
        body = _route_body("/scenarios/add")
        assert "if not project_code:" in body
        assert 'JSONResponse({"error": "project_code is required"}' in body
        assert "status_code=400" in body

    def test_missing_scenario_name_returns_400(self):
        """If scenario_name is empty, the route returns 400 JSON."""
        body = _route_body("/scenarios/add")
        assert "if not scenario_name:" in body
        assert 'JSONResponse({"error": "scenario_name is required"}' in body


# ─────────────────────────────────────────────────────────────────────────────
# 4. user_id from session, not form
# ─────────────────────────────────────────────────────────────────────────────


class TestUserIdSource:
    def test_user_id_never_from_form(self):
        """user_id is always derived from user.user_id, NEVER from form."""
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        # No form.get('user_id') or similar
        assert 'form.get("user_id"' not in clean
        assert "user.user_id" in clean


# ─────────────────────────────────────────────────────────────────────────────
# 5. active_project behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestActiveProjectBehavior:
    def test_route_resolves_project_record(self):
        """The route resolves the project via
        get_project_record(user_id=user.user_id, project_code=project_code)."""
        body = _route_body("/scenarios/add")
        assert "get_project_record(user_id=user.user_id, project_code=project_code)" in body

    def test_project_not_found_returns_404(self):
        """If project_record is None, the route returns 404 JSON."""
        body = _route_body("/scenarios/add")
        assert "if project_record is None:" in body
        assert 'JSONResponse({"error": "Project not found"}' in body
        assert "status_code=404" in body

    def test_non_user_created_project_returns_403(self):
        """If project_origin is NOT user_created, the route returns
        403 JSON (forbidden)."""
        body = _route_body("/scenarios/add")
        assert "if project_record.project_origin != \"user_created\":" in body
        assert 'JSONResponse({"error": "Add Scenario is only available for user-created projects"}' in body
        assert "status_code=403" in body


# ─────────────────────────────────────────────────────────────────────────────
# 6. Scenario creation behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestScenarioCreationBehavior:
    def test_route_finds_base_case_scenario(self):
        """The route finds the Base Case scenario for the project
        via list_scenarios + a for-loop checking is_base_case."""
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        assert "list_scenarios(user.user_id, project_id=project_record.project_id" in clean
        assert "is_base_case" in clean

    def test_route_promotes_oldest_scenario_if_no_base_case(self):
        """If no base_case exists, the route promotes the oldest
        scenario to base_case via
        promote_scenario_to_base_case(...)."""
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        assert "promote_scenario_to_base_case" in clean
        assert "_get_least_created_scenario_for_project" in clean

    def test_route_calls_add_scenario(self):
        """The route calls add_scenario(...) with the right kwargs."""
        body = _route_body("/scenarios/add")
        assert "add_scenario(" in body
        # Required args
        assert "user_id=user.user_id" in body
        assert "project_id=project_record.project_id" in body
        assert "project_code=project_record.project_code" in body
        assert "scenario_name=scenario_name" in body
        assert "parent_scenario_id=base_case.scenario_id" in body
        assert "base_input_set=" in body
        assert "overrides={}" in body
        assert "governance_state={}" in body
        assert "replay_metadata=" in body

    def test_route_handles_add_scenario_failure(self):
        """If add_scenario returns None, the route returns 500 JSON."""
        body = _route_body("/scenarios/add")
        assert "if new_scenario is None:" in body
        assert 'JSONResponse({"error": "Failed to create scenario"}' in body
        assert "status_code=500" in body


# ─────────────────────────────────────────────────────────────────────────────
# 7. Workspace/snapshot behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestSnapshotWorkspaceBehavior:
    def test_route_resolves_workspace_state(self):
        """The route resolves workspace_state via
        get_workspace_state(user.user_id, project_record.project_id)."""
        body = _route_body("/scenarios/add")
        assert "get_workspace_state(user.user_id, project_record.project_id)" in body

    def test_base_input_set_uses_base_case_snapshot_or_base_input_set(self):
        """base_input_set falls back from base_case.snapshot to
        base_case.base_input_set to {}."""
        body = _route_body("/scenarios/add")
        assert "base_case.snapshot or base_case.base_input_set or {}" in body


# ─────────────────────────────────────────────────────────────────────────────
# 8. Intended persistence writes
# ─────────────────────────────────────────────────────────────────────────────


class TestPersistenceSideEffects:
    """Pin intended persistence calls."""

    def test_get_project_record_called_once(self):
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        assert clean.count("get_project_record(") == 1

    def test_list_scenarios_called_for_base_case_lookup(self):
        """list_scenarios is called to find the base case."""
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        # 2 calls: 1 for base case lookup, 1 for render context
        assert clean.count("list_scenarios(") == 2

    def test_add_scenario_called_once(self):
        """add_scenario is called exactly once per success."""
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        assert clean.count("add_scenario(") == 1

    def test_promote_scenario_to_base_case_conditional(self):
        """promote_scenario_to_base_case is called only when needed
        (no base case found in the scenarios list)."""
        body = _route_body("/scenarios/add")
        assert "promote_scenario_to_base_case" in body

    def test_get_workspace_state_called_once(self):
        """get_workspace_state is called exactly once for the
        render context."""
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        assert clean.count("get_workspace_state(") == 1


# ─────────────────────────────────────────────────────────────────────────────
# 9. Call ordering
# ─────────────────────────────────────────────────────────────────────────────


class TestCallOrdering:
    def test_ordering_auth_form_validation_project_lookup_base_case_add(self):
        """Order: get_current_user -> await request.form() ->
        form.get (project_code, scenario_name) -> 400 checks ->
        get_project_record -> 404 check -> 403 check ->
        list_scenarios (for base case) -> promote_scenario_to_base_case
        (if needed) -> add_scenario -> 500 check -> list_scenarios
        (for render) -> get_workspace_state -> TemplateResponse."""
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        positions = {
            "auth": body.find("get_current_user(request)"),
            "form": body.find("await request.form()"),
            "get_project_record": clean.find("get_project_record(user_id=user.user_id"),
            "list_scenarios_first": clean.find("list_scenarios(user.user_id, project_id=project_record.project_id, include_archived=False)"),
            "add_scenario": clean.find("add_scenario("),
            "list_scenarios_second": clean.find("list_scenarios(user.user_id, project_id=project_record.project_id, include_archived=False, limit=12)"),
            "get_workspace_state": clean.find("get_workspace_state("),
            "template_response": clean.find("templates.TemplateResponse("),
        }
        for k, v in positions.items():
            assert v != -1, f"{k} not found in route body"
        # Ordering assertions
        assert positions["auth"] < positions["form"]
        assert positions["form"] < positions["get_project_record"]
        assert positions["get_project_record"] < positions["list_scenarios_first"]
        assert positions["list_scenarios_first"] < positions["add_scenario"]
        assert positions["add_scenario"] < positions["list_scenarios_second"]
        assert positions["list_scenarios_second"] < positions["get_workspace_state"]
        assert positions["get_workspace_state"] < positions["template_response"]


# ─────────────────────────────────────────────────────────────────────────────
# 10. replay_metadata
# ─────────────────────────────────────────────────────────────────────────────


class TestReplayMetadata:
    def test_replay_metadata_has_required_fields(self):
        """The replay_metadata dict has 3 fields: action,
        parent_scenario_id, project_code. (Different from
        /scenarios/save which uses export_type.)"""
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        assert '"action": "add_scenario"' in clean
        assert '"parent_scenario_id": base_case.scenario_id' in clean
        assert '"project_code": project_code' in clean


# ─────────────────────────────────────────────────────────────────────────────
# 11. governance_state
# ─────────────────────────────────────────────────────────────────────────────


class TestGovernanceState:
    def test_governance_state_passed_as_empty_dict(self):
        """The route passes governance_state={} (empty dict) to
        add_scenario (the repository function is the single source
        of truth for governance)."""
        body = _route_body("/scenarios/add")
        assert "governance_state={}" in body


# ─────────────────────────────────────────────────────────────────────────────
# 12. Response behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestResponseBehavior:
    def test_success_response_uses_template_response(self):
        """The success response is templates.TemplateResponse
        rendering the partials/scenario_tab.html template."""
        body = _route_body("/scenarios/add")
        assert 'name="partials/scenario_tab.html"' in body
        assert "templates.TemplateResponse(" in body

    def test_template_context_uses_build_scenario_tab_context(self):
        """The template context is built via
        _build_scenario_tab_context(user, project_record, scenarios, ws)."""
        body = _route_body("/scenarios/add")
        assert "_build_scenario_tab_context(user, project_record, scenarios, ws)" in body

    def test_400_response_uses_jsonresponse(self):
        """The 400 responses (missing project_code or scenario_name)
        are JSON."""
        body = _route_body("/scenarios/add")
        assert 'JSONResponse({"error": "project_code is required"}' in body
        assert 'JSONResponse({"error": "scenario_name is required"}' in body

    def test_404_response_uses_jsonresponse(self):
        """The 404 response (project not found) is JSON."""
        body = _route_body("/scenarios/add")
        assert 'JSONResponse({"error": "Project not found"}' in body

    def test_403_response_uses_jsonresponse(self):
        """The 403 response (non-user_created project) is JSON."""
        body = _route_body("/scenarios/add")
        assert 'JSONResponse({"error": "Add Scenario is only available for user-created projects"}' in body

    def test_500_response_uses_jsonresponse(self):
        """The 500 response (add_scenario failure) is JSON."""
        body = _route_body("/scenarios/add")
        assert 'JSONResponse({"error": "Failed to create scenario"}' in body


# ─────────────────────────────────────────────────────────────────────────────
# 13. HTMX headers
# ─────────────────────────────────────────────────────────────────────────────


class TestHtmxHeaders:
    def test_success_emits_hx_trigger_scenario_added(self):
        """The success response emits HX-Trigger: scenarioAdded
        (different from /scenarios/save which doesn't set any
        HX-Trigger, and /save-run which sets HX-Trigger:
        refreshHistory)."""
        body = _route_body("/scenarios/add")
        assert 'HX-Trigger' in body
        assert "scenarioAdded" in body

    def test_error_responses_no_hx_trigger(self):
        """The 400/403/404/500 error responses do NOT set
        HX-Trigger (they're JSON)."""
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        # No HX-Trigger in JSON error paths
        # (The single HX-Trigger reference is in the success
        # TemplateResponse call.)
        assert clean.count("HX-Trigger") == 1


# ─────────────────────────────────────────────────────────────────────────────
# 14. Redirect/status behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestRedirectStatus:
    def test_auth_redirect_uses_redirectresponse(self):
        """The 302 auth redirect uses RedirectResponse(url='/login',
        status_code=302)."""
        body = _route_body("/scenarios/add")
        assert "RedirectResponse(url=\"/login\", status_code=302)" in body

    def test_status_codes_summary(self):
        """Status codes: 302 (auth), 400 (missing fields), 403
        (non-user_created), 404 (project not found), 500
        (add_scenario failure), 200 (success)."""
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        # 302 (auth)
        assert "status_code=302" in body
        # 400 (missing project_code + missing scenario_name)
        assert clean.count("status_code=400") == 2
        # 403 (non-user_created)
        assert "status_code=403" in body
        # 404 (project not found)
        assert "status_code=404" in body
        # 500 (add_scenario failure)
        assert "status_code=500" in body


# ─────────────────────────────────────────────────────────────────────────────
# 15. Error/fallback behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestErrorFallback:
    def test_no_broad_except_in_route(self):
        """The route does NOT wrap the body in broad
        `except Exception:`. Errors propagate to FastAPI's default
        500 (except the explicit add_scenario failure check)."""
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        # The only "except Exception:" should NOT be present
        # in the route body (the 500 JSON is explicit, not via
        # broad except).
        assert "except Exception:" not in clean

    def test_explicit_error_paths(self):
        """The route has 4 explicit error paths:
        - 400 missing project_code
        - 400 missing scenario_name
        - 404 project not found
        - 403 non-user_created project
        - 500 add_scenario failure
        """
        body = _route_body("/scenarios/add")
        for error in (
            '"project_code is required"',
            '"scenario_name is required"',
            '"Project not found"',
            '"Add Scenario is only available for user-created projects"',
            '"Failed to create scenario"',
        ):
            assert error in body, f"Missing error path: {error}"


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
        "save_project",
        "run_project",
        "build_institutional_workbook_export",
        "build_excel_export_for_post_request",
        "build_runtime_summary_csv_export",
        "build_values_only_export_for_project",
    )

    def test_route_does_not_call_record_export_family(self):
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        for helper in (
            "record_export(",
            "record_download_export(",
            "record_runtime_summary_export(",
            "record_institutional_workbook_export(",
        ):
            assert helper not in clean

    def test_route_does_not_call_record_workspace_runtime(self):
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        assert "record_workspace_runtime(" not in clean

    def test_route_does_not_call_update_scenario_last_run_summary(self):
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        assert "update_scenario_last_run_summary(" not in clean

    def test_route_does_not_call_save_run(self):
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        assert "save_run(" not in clean

    def test_route_does_not_call_save_project(self):
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        assert "save_project(" not in clean

    def test_route_does_not_call_run_project(self):
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        assert "run_project(" not in clean

    def test_route_does_not_call_excel_export_builders(self):
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        for helper in (
            "build_institutional_workbook_export(",
            "build_excel_export_for_post_request(",
            "build_runtime_summary_csv_export(",
            "build_values_only_export_for_project(",
        ):
            assert helper not in clean

    def test_route_does_not_use_db_or_session_directly(self):
        body = _route_body("/scenarios/add")
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
            _get_least_created_scenario_for_project,
            add_scenario,
            get_project_record,
            get_workspace_state,
            list_scenarios,
            promote_scenario_to_base_case,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Behavior quirks (to be preserved in future 51L-2)
# ─────────────────────────────────────────────────────────────────────────────


class TestBehaviorQuirks:
    """Pin behavior quirks that 51L-2 must preserve."""

    def test_quirk_1_form_input_instead_of_snapshot(self):
        """Quirk 1: the route reads INDIVIDUAL form fields
        (project_code, scenario_name) instead of using
        _collect_form_snapshot. Different from /scenarios/save
        which uses collect_form_snapshot."""
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        assert "form.get(" in clean
        assert "_collect_form_snapshot" not in clean

    def test_quirk_2_hx_trigger_scenario_added_on_success(self):
        """Quirk 2: the success response emits
        HX-Trigger: scenarioAdded (different from /scenarios/save
        which doesn't emit HX-Trigger, and /save-run which emits
        HX-Trigger: refreshHistory)."""
        body = _route_body("/scenarios/add")
        assert 'HX-Trigger' in body
        assert "scenarioAdded" in body

    def test_quirk_3_partial_template_response(self):
        """Quirk 3: the success response is a partial template
        render (partials/scenario_tab.html), NOT a full workspace
        render (different from /scenarios/save which returns a
        full workspace render)."""
        body = _route_body("/scenarios/add")
        assert 'name="partials/scenario_tab.html"' in body

    def test_quirk_4_promote_oldest_scenario_fallback(self):
        """Quirk 4: if no base_case exists but other scenarios do,
        the route promotes the OLDEST scenario to base_case via
        promote_scenario_to_base_case(...). This handles imported
        projects without a designated base case."""
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        assert "promote_scenario_to_base_case" in clean
        assert "_get_least_created_scenario_for_project" in clean
        assert "oldest" in clean

    def test_quirk_5_replay_metadata_uses_action_not_export_type(self):
        """Quirk 5: replay_metadata uses ``action='add_scenario'``
        instead of ``export_type=...`` (different from
        /scenarios/save which uses export_type)."""
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        assert '"action": "add_scenario"' in clean
        # No export_type in the replay_metadata
        assert '"export_type"' not in clean

    def test_quirk_6_governance_state_is_empty_dict(self):
        """Quirk 6: the route passes governance_state={} (empty
        dict). The repository function add_scenario is the single
        source of truth for the new scenario's governance state."""
        body = _route_body("/scenarios/add")
        assert "governance_state={}" in body

    def test_quirk_7_overrides_is_empty_dict(self):
        """Quirk 7: the route passes overrides={} (empty dict).
        New scenarios start with no overrides; the user can add
        overrides later."""
        body = _route_body("/scenarios/add")
        assert "overrides={}" in body

    def test_quirk_8_user_created_project_required(self):
        """Quirk 8: only user_created projects can add scenarios.
        factory_template and saved_baseline return 403."""
        body = _route_body("/scenarios/add")
        assert 'project_record.project_origin != "user_created"' in body
        assert "status_code=403" in body

    def test_quirk_9_base_input_set_fallback_chain(self):
        """Quirk 9: base_input_set falls back from
        base_case.snapshot to base_case.base_input_set to {}."""
        body = _route_body("/scenarios/add")
        assert "base_case.snapshot or base_case.base_input_set or {}" in body

    def test_quirk_10_re_read_scenarios_after_add(self):
        """Quirk 10: after add_scenario, the route re-reads the
        scenarios list (without include_archived=False) and the
        workspace state for the render context. This ensures the
        new scenario is in the rendered scenario tab."""
        body = _route_body("/scenarios/add")
        clean = _strip_docstrings_and_comments(body)
        # list_scenarios is called twice: once for base case
        # lookup (without limit), once for render (with limit=12).
        assert clean.count("list_scenarios(") == 2
        # The second call has limit=12
        assert "list_scenarios(user.user_id, project_id=project_record.project_id, include_archived=False, limit=12)" in body


# ─────────────────────────────────────────────────────────────────────────────
# Recommended 51L-2 extraction boundary
# ─────────────────────────────────────────────────────────────────────────────


class TestExtractionBoundaryRecommendation:
    def test_scenarios_add_service_does_not_exist_yet(self):
        """Pre-51L-2: scenarios_add_service.py does NOT exist."""
        path = SERVICES_DIR / "scenarios_add_service.py"
        assert not path.exists(), (
            f"{path} must NOT exist before Phase 51L-2"
        )

    def test_recommended_module_name(self):
        """The recommended 51L-2 module is
        app/services/scenarios_add_service.py (NOT extension of
        scenario_state_service.py, scenario_state_route_service.py,
        scenarios_save_service.py, or scenario_duplicate_service.py)."""
        path = SERVICES_DIR / "scenarios_add_service.py"
        assert not path.exists()
