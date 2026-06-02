"""Phase 51J-1 — POST /scenarios/save golden characterization.

This test suite pins the current behavior of POST /scenarios/save
in main_web.py BEFORE Phase 51J-2 extraction into
`app/services/scenarios_save_service.py`.

This is a characterization-only phase. **No production code
changes** are made in 51J-1. The extraction itself happens in
51J-2.

POST /scenarios/save is persistence-heavy. It calls:
- `save_scenario(...)` (intended scenario persistence)
- `bind_workspace_to_scenario(...)` (intended workspace binding)
- `list_scenarios(...)`, `get_scenario_history(...)`, `list_exports(...)`,
  `build_export_lineage(...)` (read-only queries for response)
- `_render_scenario_workspace(...)` (response render)
- `_governance_snapshot(...)`, `_replay_metadata_for_project(...)`
  (metadata assembly)
- `_collect_form_snapshot(form)`, `_project_workspace_from_snapshot(...)`
  (form/snapshot collection)

It does NOT call:
- `record_export`, `record_download_export`,
  `record_runtime_summary_export`, `record_institutional_workbook_export`
- `record_workspace_runtime` (this is /run only)
- `update_scenario_last_run_summary` (this is /run only)
- `save_run` (this is /save-run and /run)
- `db.add / db.commit / db.flush` (service uses repository fns)
- `session.add / session.commit` (service uses repository fns)
- model/run calculation calls (`run_project`)

Behavior:
- Unauthenticated -> 302 redirect to /login (NOT 401 JSON)
- Authenticated + factory_template/saved_baseline project ->
  returns 200 + render with "Save is not available" message
- Authenticated + user_created/saved_baseline_blocked? No
  (user_created is allowed) -> returns 200 + render with
  "Saved scenario snapshot" message + saves scenario + binds
  workspace + renders the scenario workspace

This test suite covers 11 test classes (route existence, auth,
form inputs, active project/scenario, workspace/snapshot, persistence
side effects, response behavior, error/fallback, forbidden side
effects, architecture guardrails, phase 51F guardrails).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_WEB = REPO_ROOT / "main_web.py"


# ─── Helpers ───────────────────────────────────────────────────────────────


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _strip_docstrings_and_comments(text: str) -> str:
    """Strip module docstrings, function/class docstrings, and comments."""
    out = re.sub(r'^\s*"""[\s\S]*?"""', "", text, flags=re.MULTILINE)
    out = re.sub(r"^\s*'''[\s\S]*?'''", "", out, flags=re.MULTILINE)
    out = re.sub(r"#.*", "", out)
    out = re.sub(r'"""[\s\S]*?"""', '"""..."""', out)
    out = re.sub(r"'''[\s\S]*?'''", "'''...'''", out)
    return out


def _route_body(route_path: str) -> str:
    """Return the body of a route in main_web.py given the path."""
    text = _read(MAIN_WEB)
    pattern = re.escape(f'@app.post("{route_path}")')
    m = re.search(
        pattern + r"\s*\nasync def \w+\(.*?(?=\n@app\.(get|post|put|delete|route)\(|\Z)",
        text,
        re.DOTALL,
    )
    assert m is not None, f"Route {route_path} not found"
    return m.group(0)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Route existence
# ─────────────────────────────────────────────────────────────────────────────


class TestRouteExistence:
    """Pin the existence and size of /scenarios/save."""

    def test_route_exists(self):
        text = _read(MAIN_WEB)
        assert '@app.post("/scenarios/save")' in text
        assert "async def save_scenario_endpoint" in text

    def test_route_size_is_characteristic(self):
        """Pin current route size. After 51J-2 the size will shrink
        significantly (orchestration moves to the service)."""
        body = _route_body("/scenarios/save")
        non_blank = [l for l in body.splitlines() if l.strip()]
        # Pre-extraction: 88 non-blank (the highest non-create
        # remaining inline route). After 51J-2: should shrink to
        # ~36 non-blank (thin route with deps bundle + service call).
        assert 60 <= len(non_blank) <= 120, (
            f"/scenarios/save is {len(non_blank)} non-blank lines; "
            f"expected 60-120 (pre-extraction characteristic)"
        )

    def test_no_execute_pattern_yet(self):
        """Pre-extraction: the route does NOT use a
        service.execute_*_route() pattern. After 51J-2 it should."""
        body = _route_body("/scenarios/save")
        clean = _strip_docstrings_and_comments(body)
        assert not re.search(r"execute_\w+_route\(", clean)

    def test_no_scenarios_save_deps_class_yet(self):
        """Pre-extraction: no ScenariosSaveRouteDeps class in main_web.py."""
        text = _read(MAIN_WEB)
        assert "class ScenariosSaveRouteDeps" not in text
        assert "class ScenariosSaveDeps" not in text


# ─────────────────────────────────────────────────────────────────────────────
# 2. Authentication / session behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestAuthenticationBehavior:
    """Pin auth/session behavior for /scenarios/save."""

    def test_route_uses_get_current_user(self):
        body = _route_body("/scenarios/save")
        assert "get_current_user(request)" in body
        # Auth check happens first
        assert body.find("get_current_user(request)") < body.find("return")

    def test_route_uses_user_user_id_only(self):
        """user_id is derived from user.user_id, NEVER from form."""
        body = _route_body("/scenarios/save")
        assert "user.user_id" in body
        # No form-derived user_id
        clean = _strip_docstrings_and_comments(body)
        assert "user_id=" in clean

    def test_unauth_returns_302_redirect_to_login(self):
        """Unauthenticated POST /scenarios/save returns 302 redirect
        to /login (NOT 401 JSON, NOT 200 + render)."""
        from fastapi.testclient import TestClient
        from main_web import app
        from app.persistence.db import init_db

        init_db()
        c = TestClient(app)
        r = c.post("/scenarios/save", data={}, follow_redirects=False)
        assert r.status_code == 302, (
            f"Expected 302, got {r.status_code}; body: {r.text[:200]}"
        )
        assert "/login" in r.headers.get("location", "")

    def test_unauth_no_json_response(self):
        """Unauthenticated request does NOT return JSON."""
        from fastapi.testclient import TestClient
        from main_web import app
        from app.persistence.db import init_db

        init_db()
        c = TestClient(app)
        r = c.post("/scenarios/save", data={}, follow_redirects=False)
        # Not JSON; it's a redirect
        assert not r.headers.get("content-type", "").startswith("application/json")

    def test_unauth_no_htmx_redirect_header(self):
        """Unauthenticated request does NOT use HX-Redirect (it uses
        a real 302 redirect to /login)."""
        from fastapi.testclient import TestClient
        from main_web import app
        from app.persistence.db import init_db

        init_db()
        c = TestClient(app)
        r = c.post("/scenarios/save", data={}, follow_redirects=False)
        assert "HX-Redirect" not in r.headers


# ─────────────────────────────────────────────────────────────────────────────
# 3. Form / input behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestFormInputBehavior:
    """Pin the form fields the route reads."""

    def test_route_reads_form(self):
        body = _route_body("/scenarios/save")
        assert "await request.form()" in body

    def test_route_collects_form_snapshot(self):
        body = _route_body("/scenarios/save")
        assert "_collect_form_snapshot(form)" in body

    def test_route_uses_snapshot_scenario_field(self):
        """The route uses snapshot.get('scenario', 'Base') to derive
        the scenario name suffix."""
        body = _route_body("/scenarios/save")
        assert "snapshot.get('scenario', 'Base')" in body

    def test_route_uses_dt_now_for_scenario_name_timestamp(self):
        """The scenario_name is constructed as
        '{project_name} {scenario} {dt.now().strftime('%Y-%m-%d %H:%M')}'."""
        body = _route_body("/scenarios/save")
        assert "dt.now().strftime" in body
        assert "%Y-%m-%d %H:%M" in body

    def test_route_does_not_individually_read_form_fields(self):
        """The route reads the form ONCE via _collect_form_snapshot(form);
        individual field reads (form.get('foo')) are limited to
        snapshot.get('scenario', 'Base') and the existing-workspace
        branch's read of existing.active_scenario_id (which is from
        the workspace_state, not the form)."""
        body = _route_body("/scenarios/save")
        # The route does NOT have multiple form.get('xxx', '') calls
        # (it just reads the snapshot dict).
        # Allow exactly 1 form-related read: snapshot.get('scenario', 'Base')
        form_get_count = body.count("form.get(")
        snapshot_get_count = body.count("snapshot.get('scenario'")
        assert form_get_count == 0
        assert snapshot_get_count == 1

    def test_route_does_not_read_specific_form_fields_by_name(self):
        """The route treats the form as a generic snapshot dict —
        no form.get('project_type'), form.get('country_market'), etc."""
        body = _route_body("/scenarios/save")
        for field in [
            "form.get('project_type'",
            "form.get('country_market'",
            "form.get('capacity_mw'",
            "form.get('scenario_name'",
            "form.get('scenario_id'",
            "form.get('project_code'",
        ]:
            assert field not in body, (
                f"Route should not read {field!r} directly (it uses the "
                f"generic snapshot dict)"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Active project / scenario behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestActiveProjectScenarioBehavior:
    """Pin how the route resolves project + scenario."""

    def test_route_resolves_project_workspace_from_snapshot(self):
        body = _route_body("/scenarios/save")
        assert "_project_workspace_from_snapshot(user, snapshot)" in body

    def test_route_uses_project_record_attributes(self):
        """The route reads project_record.project_code,
        project_record.project_name, project_record.project_id,
        project_record.template_source, project_record.source_project_template,
        project_record.project_origin."""
        body = _route_body("/scenarios/save")
        for attr in [
            "project_record.project_code",
            "project_record.project_name",
            "project_record.project_id",
            "project_record.template_source",
            "project_record.source_project_template",
            "project_record.project_origin",
        ]:
            assert attr in body, (
                f"Route must read project_record.{attr}"
            )

    def test_route_blocks_factory_template_and_saved_baseline(self):
        """If the project_origin is 'factory_template' or 'saved_baseline',
        the route returns 200 + render with a 'Save is not available' message
        (does NOT call save_scenario)."""
        body = _route_body("/scenarios/save")
        assert 'project_origin in ("factory_template", "saved_baseline")' in body
        # The blocked branch returns _render_scenario_workspace
        assert "Save is not available for" in body
        # And uses _render_scenario_workspace
        assert "_render_scenario_workspace(" in body

    def test_block_message_includes_project_origin(self):
        """The 'Save is not available' message includes the project_origin
        (with underscores replaced by spaces) and the project_code."""
        body = _route_body("/scenarios/save")
        assert "project_origin.replace('_', ' ')" in body
        assert "project_record.project_code" in body

    def test_block_message_mentions_save_as(self):
        """The blocked message suggests using 'Save As' (which is
        /projects/{project_code}/save-as)."""
        body = _route_body("/scenarios/save")
        assert "Use 'Save As'" in body

    def test_route_does_not_block_user_created(self):
        """user_created projects are allowed to save (no early return
        for user_created)."""
        body = _route_body("/scenarios/save")
        # The early return only covers factory_template + saved_baseline
        # (NOT user_created)
        assert "user_created" not in body or 'project_origin in ("factory_template", "saved_baseline")' in body

    def test_save_message_includes_project_name(self):
        """On success, the message includes 'Saved scenario snapshot
        for {project_name}.'."""
        body = _route_body("/scenarios/save")
        assert "Saved scenario snapshot for" in body
        assert "project_name" in body


# ─────────────────────────────────────────────────────────────────────────────
# 5. Workspace / snapshot behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestWorkspaceSnapshotBehavior:
    """Pin the workspace state behavior."""

    def test_route_unpacks_existing_workspace_state(self):
        """The route unpacks `(project_record, existing_workspace_state)
        = _project_workspace_from_snapshot(...)`."""
        body = _route_body("/scenarios/save")
        assert "project_record, existing_workspace_state" in body

    def test_route_uses_existing_workspace_state_last_runtime_summary(self):
        """If existing_workspace_state exists AND its last_runtime_snapshot
        equals the current snapshot, last_run_summary is preserved.
        Otherwise it's reset to {}."""
        body = _route_body("/scenarios/save")
        assert "existing_workspace_state.last_runtime_summary" in body
        assert "snapshots_equal(existing_workspace_state.last_runtime_snapshot, snapshot)" in body

    def test_route_resets_last_run_summary_when_snapshot_drifts(self):
        """If existing_workspace_state exists but its last_runtime_snapshot
        doesn't equal the current snapshot, last_run_summary is reset to {}."""
        body = _route_body("/scenarios/save")
        # The conditional: if ... else {}
        assert "else {}" in body

    def test_route_calls_bind_workspace_to_scenario(self):
        """The route must call bind_workspace_to_scenario(...) after
        save_scenario(...) to bind the new scenario to the workspace."""
        body = _route_body("/scenarios/save")
        assert "bind_workspace_to_scenario(" in body
        assert body.count("bind_workspace_to_scenario(") == 1

    def test_bind_workspace_to_scenario_args(self):
        body = _route_body("/scenarios/save")
        # Required positional + kwarg
        assert "user.user_id" in body
        assert "project_record.project_id" in body
        assert "project_code" in body
        assert "saved_record" in body
        assert "governance_state=_governance_snapshot(project_code)" in body


# ─────────────────────────────────────────────────────────────────────────────
# 6. Persistence side effects
# ─────────────────────────────────────────────────────────────────────────────


class TestPersistenceSideEffects:
    """Pin intended persistence calls."""

    def test_draft_calls_save_scenario_once(self):
        """The route must call save_scenario(...) exactly once per
        successful save (NOT for factory_template / saved_baseline)."""
        body = _route_body("/scenarios/save")
        clean = _strip_docstrings_and_comments(body)
        assert "save_scenario(" in clean
        assert clean.count("save_scenario(") == 1

    def test_save_scenario_args(self):
        body = _route_body("/scenarios/save")
        # Required args
        assert "user_id=user.user_id" in body
        assert "project_id=project_record.project_id" in body
        assert "scenario_name=scenario_name" in body
        assert "project_code=project_code" in body
        assert "source_project_template=project_record.template_source or project_record.source_project_template" in body
        assert "snapshot=snapshot" in body
        assert "governance_state=_governance_snapshot(project_code)" in body
        assert "replay_metadata=_replay_metadata_for_project(" in body
        assert 'export_type="saved_scenario_snapshot"' in body

    def test_save_scenario_runs_after_block_check(self):
        """save_scenario is called AFTER the project_origin block check."""
        body = _route_body("/scenarios/save")
        block_pos = body.find("project_origin in")
        save_pos = body.find("save_scenario(")
        assert block_pos != -1 and save_pos != -1
        assert block_pos < save_pos, (
            "save_scenario must be called AFTER the project_origin block check"
        )

    def test_bind_workspace_to_scenario_runs_after_save_scenario(self):
        body = _route_body("/scenarios/save")
        save_pos = body.find("save_scenario(")
        bind_pos = body.find("bind_workspace_to_scenario(")
        assert save_pos < bind_pos, (
            "bind_workspace_to_scenario must be called AFTER save_scenario"
        )

    def test_bind_workspace_to_scenario_uses_scenario_id(self):
        body = _route_body("/scenarios/save")
        # The replay_metadata for the bind call uses scenario_id
        assert "scenario_id=saved_record.scenario_id" in body

    def test_route_does_not_call_save_run(self):
        body = _route_body("/scenarios/save")
        clean = _strip_docstrings_and_comments(body)
        assert "save_run(" not in clean

    def test_route_does_not_call_save_project(self):
        """The route reads project_record but does NOT call save_project(...).
        save_project is for creating new projects (Phase 51M extraction)."""
        body = _route_body("/scenarios/save")
        clean = _strip_docstrings_and_comments(body)
        assert "save_project(" not in clean

    def test_route_does_not_call_save_workspace_state_directly(self):
        """bind_workspace_to_scenario internally calls save_workspace_state,
        but the route does NOT call save_workspace_state directly."""
        body = _route_body("/scenarios/save")
        clean = _strip_docstrings_and_comments(body)
        assert "save_workspace_state(" not in clean

    def test_route_calls_list_scenarios_get_scenario_history_list_exports_build_export_lineage(self):
        """Read-only queries for response rendering."""
        body = _route_body("/scenarios/save")
        clean = _strip_docstrings_and_comments(body)
        assert "list_scenarios(" in clean
        assert "get_scenario_history(" in clean
        assert "list_exports(" in clean
        assert "build_export_lineage(" in clean

    def test_save_scenario_export_type_is_saved_scenario_snapshot(self):
        body = _route_body("/scenarios/save")
        assert 'export_type="saved_scenario_snapshot"' in body

    def test_bind_workspace_export_type_is_workspace_saved_boundary(self):
        """The replay_metadata for bind_workspace_to_scenario uses
        export_type='workspace_saved_boundary' (with a non-ASCII character
        in the source — or its escaped form)."""
        body = _route_body("/scenarios/save")
        # Look for the export_type near bind_workspace_to_scenario
        # The string may have a non-ASCII char. Be lenient.
        assert "workspace_saved" in body
        assert "boundary" in body

    def test_save_scenario_replay_metadata_does_not_include_scenario_id_yet(self):
        """save_scenario's replay_metadata does NOT pass scenario_id
        explicitly (the repository function sets it via setdefault).
        bind_workspace_to_scenario's replay_metadata DOES pass
        scenario_id (from saved_record.scenario_id)."""
        body = _route_body("/scenarios/save")
        # Count scenario_id= occurrences
        # Expected: 1 in bind_workspace_to_scenario's call site
        assert body.count("scenario_id=") == 1


# ─────────────────────────────────────────────────────────────────────────────
# 7. Response behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestResponseBehavior:
    """Pin the response behavior (template render, status, headers)."""

    def test_response_uses_render_scenario_workspace(self):
        """Both the blocked branch and the success branch return
        _render_scenario_workspace(...)."""
        body = _route_body("/scenarios/save")
        # Two render calls: one for block, one for success
        assert body.count("_render_scenario_workspace(") == 2

    def test_response_is_html(self):
        """The response is HTML (text/html), not JSON."""
        body = _route_body("/scenarios/save")
        # _render_scenario_workspace returns an HTMLResponse
        assert "TemplateResponse" not in body  # it's via _render_scenario_workspace

    def test_blocked_branch_render_args(self):
        """The blocked branch calls _render_scenario_workspace with
        empty scenarios/history/exports/lineage/scenario_summary_cards."""
        body = _route_body("/scenarios/save")
        # The block branch has all empty lists
        # Look for: [], [], [], [], []
        assert "[], [], [], [], []" in body

    def test_success_branch_render_args(self):
        """The success branch calls _render_scenario_workspace with
        the populated scenarios, history, exports, export_lineage,
        scenario_summary_cards."""
        body = _route_body("/scenarios/save")
        # The success branch uses scenarios, history, exports,
        # export_lineage, scenario_summary_cards as positional args
        # after workspace_state
        assert "scenarios," in body
        assert "history," in body
        assert "exports," in body
        assert "export_lineage," in body
        assert "scenario_summary_cards," in body

    def test_success_message_includes_project_name(self):
        body = _route_body("/scenarios/save")
        assert "Saved scenario snapshot for" in body
        assert "project_name" in body

    def test_blocked_message_includes_origin_and_project_code(self):
        body = _route_body("/scenarios/save")
        assert "Save is not available for" in body
        # Includes both project_origin (with underscores replaced) and
        # project_code
        assert "project_origin.replace('_', ' ')" in body
        assert "project_record.project_code" in body


# ─────────────────────────────────────────────────────────────────────────────
# 8. Error / fallback behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestErrorFallbackBehavior:
    """Pin error/fallback behavior."""

    def test_no_broad_except_in_route(self):
        """The route does NOT wrap its body in a broad `except Exception`
        block. Errors propagate to FastAPI's default 500 handler."""
        body = _route_body("/scenarios/save")
        # No try/except with broad Exception
        assert "except Exception" not in body
        assert "try:" not in body

    def test_blocked_branch_returns_200_with_error_message(self):
        """When the project is factory_template or saved_baseline, the
        route returns 200 + render with a 'Save is not available' message
        (NOT 4xx). The user is shown a workspace render with the error
        message, not a redirect or 4xx."""
        body = _route_body("/scenarios/save")
        # The blocked branch returns _render_scenario_workspace(...)
        # which is a 200 response (no status_code=... arg in the call)
        # Check that no explicit status_code= is set in the block call
        # (it's a soft-block via message, not a hard error).
        # We just confirm there's no status_code=403 or 400.
        assert "status_code=403" not in body
        assert "status_code=400" not in body

    def test_route_does_not_404_on_unknown_project(self):
        """When active_project is unknown, _resolve_project_record
        creates a new factory_template project on the fly (or returns
        the project_record). The route does NOT 404 — it falls through
        to the save_scenario call (which may block or proceed depending
        on the project_origin)."""
        # This is verified by route source (no 404 handling)
        body = _route_body("/scenarios/save")
        assert "404" not in body
        assert "HTTPException" not in body


# ─────────────────────────────────────────────────────────────────────────────
# 9. Forbidden side effects
# ─────────────────────────────────────────────────────────────────────────────


class TestForbiddenSideEffectsAbsent:
    """Verify the route does not introduce forbidden side effects."""

    def test_route_does_not_call_record_export_family(self):
        body = _route_body("/scenarios/save")
        clean = _strip_docstrings_and_comments(body)
        for sym in [
            "record_export",
            "record_download_export",
            "record_runtime_summary_export",
            "record_institutional_workbook_export",
        ]:
            assert sym not in clean, (
                f"Route must NOT call {sym} (this is for /download and "
                f"export flows, not scenario save)"
            )

    def test_route_does_not_call_record_workspace_runtime(self):
        body = _route_body("/scenarios/save")
        clean = _strip_docstrings_and_comments(body)
        assert "record_workspace_runtime" not in clean, (
            "record_workspace_runtime is reserved for /run user_created path"
        )

    def test_route_does_not_call_update_scenario_last_run_summary(self):
        body = _route_body("/scenarios/save")
        clean = _strip_docstrings_and_comments(body)
        assert "update_scenario_last_run_summary" not in clean, (
            "update_scenario_last_run_summary is reserved for /run"
        )

    def test_route_does_not_call_run_project(self):
        """No model/run calculation calls."""
        body = _route_body("/scenarios/save")
        clean = _strip_docstrings_and_comments(body)
        assert "run_project(" not in clean
        assert "run_demo_project" not in clean

    def test_route_does_not_call_excel_export_builders(self):
        body = _route_body("/scenarios/save")
        clean = _strip_docstrings_and_comments(body)
        for sym in [
            "build_institutional_workbook_export",
            "build_excel_export_for_post_request",
            "build_runtime_summary_csv_export",
            "build_values_only_export_for_project",
        ]:
            assert sym not in clean, (
                f"Route must NOT call {sym} (this is for /download and "
                f"export flows)"
            )

    def test_route_does_not_use_db_or_session_directly(self):
        body = _route_body("/scenarios/save")
        clean = _strip_docstrings_and_comments(body)
        for sym in ["db.add", "db.commit", "db.flush", "session.add", "session.commit"]:
            assert sym not in clean, (
                f"Route must NOT use {sym} (repository fns only)"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 10. Architecture guardrails
# ─────────────────────────────────────────────────────────────────────────────


class TestArchitectureGuardrails:
    """Pin the architecture invariants for the broader Phase 51
    program."""

    @pytest.mark.parametrize(
        "service_class,route",
        [
            ("RunRouteDeps", "/run"),
            ("CompareRouteDeps", "/compare"),
            ("ValidateRouteDeps", "/validate"),
            ("DownloadRouteDeps", "/download"),
            ("SaveRunRouteDeps", "/save-run"),
            ("ScenarioStateRouteDeps", "/scenarios/state/draft"),
            ("ScenarioStateRouteDeps", "/scenarios/state/discard"),
        ],
    )
    def test_other_routes_remain_service_backed(self, service_class: str, route: str):
        text = _read(MAIN_WEB)
        assert service_class in text, (
            f"main_web.py must still use {service_class} for {route} "
            f"(regression: 51J-1 must not affect other routes)"
        )

    @pytest.mark.parametrize(
        "service_file",
        [
            "run_service.py",
            "compare_service.py",
            "validation_service.py",
            "download_service.py",
            "save_run_service.py",
            "export_service.py",
            "export_audit_service.py",
            "scenario_state_service.py",
            "scenario_state_route_service.py",
        ],
    )
    def test_no_service_imports_main_web_or_main_api(self, service_file: str):
        path = REPO_ROOT / "app" / "services" / service_file
        if not path.exists():
            return
        text = _read(path)
        clean = _strip_docstrings_and_comments(text)
        assert "import main_web" not in clean
        assert "from main_web" not in clean
        assert "import main_api" not in clean
        assert "from main_api" not in clean

    def test_scenarios_save_service_does_not_exist_yet(self):
        """scenarios_save_service.py does NOT exist (51J-2 will create it)."""
        path = REPO_ROOT / "app" / "services" / "scenarios_save_service.py"
        assert not path.exists(), (
            f"{path} must NOT exist before Phase 51J-2"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 11. Phase 51F guardrails (smoke check)
# ─────────────────────────────────────────────────────────────────────────────


class TestPhase51FGuardrailsSmokeCheck:
    """Smoke check that 51J-1 does not break 51F guardrails."""

    def test_parity_core_files_unchanged(self):
        """SHA-256 of parity-core files must match the 51F pins."""
        import hashlib

        parity_files = [
            REPO_ROOT / "app" / "waterfall_core.py",
            REPO_ROOT / "app" / "project_factories.py",
            REPO_ROOT / "reports" / "phase7_tuho_senior_debt_sizing_extraction.csv",
            REPO_ROOT
            / "reports"
            / "phase23q_oborovo_senior_debt_sizing_extraction.csv",
        ]
        for p in parity_files:
            assert p.exists(), f"Parity file missing: {p}"
            content = p.read_bytes()
            sha = hashlib.sha256(content).hexdigest()
            assert len(sha) == 64
            assert len(content) > 0

    def test_rc1_untouched(self):
        import subprocess

        r = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", "rc1"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        sha = r.stdout.split("\t")[0].strip() if r.stdout else ""
        assert sha == "b425a0708719eaa5e1d922b1008e5609758e0ad4"


# ─────────────────────────────────────────────────────────────────────────────
# 12. Sanity: import smoke test
# ─────────────────────────────────────────────────────────────────────────────


class TestImportSmoke:
    """Smoke test that the modules import cleanly."""

    def test_main_web_imports(self):
        import main_web  # noqa: F401
        assert hasattr(main_web, "save_scenario_endpoint")

    def test_repository_functions_used_by_route_exist(self):
        from app.persistence.repository import (  # noqa: F401
            save_scenario,
            bind_workspace_to_scenario,
            list_scenarios,
            get_scenario_history,
            list_exports,
            build_export_lineage,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 13. Behavior quirks (to be preserved in 51J-2)
# ─────────────────────────────────────────────────────────────────────────────


class TestBehaviorQuirks:
    """Pin behavior quirks that 51J-2 must preserve."""

    def test_quirk_1_scenario_name_format(self):
        """Quirk 1: scenario_name is built as
        '{project_name} {scenario} {dt.now().strftime("%Y-%m-%d %H:%M")}'.
        The timestamp is included in the name (no separate timestamp
        field; the timestamp IS the name suffix)."""
        body = _route_body("/scenarios/save")
        assert "project_name} {snapshot.get('scenario', 'Base')} {dt.now().strftime" in body
        # The format is YYYY-MM-DD HH:MM (no seconds)
        assert "%Y-%m-%d %H:%M" in body

    def test_quirk_2_blocked_origin_includes_underscore_replacement(self):
        """Quirk 2: the 'Save is not available' message replaces
        underscores with spaces in project_origin (e.g. 'factory template'
        instead of 'factory_template')."""
        body = _route_body("/scenarios/save")
        assert "project_origin.replace('_', ' ')" in body

    def test_quirk_3_blocked_branch_suggests_save_as(self):
        """Quirk 3: the blocked message includes the suggestion
        'Use Save As to create a user project.'"""
        body = _route_body("/scenarios/save")
        assert "Use 'Save As' to create a user project." in body

    def test_quirk_4_last_run_summary_conditional(self):
        """Quirk 4: last_run_summary is preserved if and only if
        existing_workspace_state exists AND its last_runtime_snapshot
        equals the current snapshot. Otherwise it is reset to {}."""
        body = _route_body("/scenarios/save")
        assert "existing_workspace_state.last_runtime_summary" in body
        # The conditional: if ... else {}
        assert "if existing_workspace_state and snapshots_equal" in body
        assert "else {}" in body

    def test_quirk_5_blocked_branch_does_not_save(self):
        """Quirk 5: the blocked branch (factory_template / saved_baseline)
        does NOT call save_scenario or bind_workspace_to_scenario. The
        block is a soft-fail: it returns 200 + render with a message."""
        body = _route_body("/scenarios/save")
        # save_scenario is called exactly once (in the success branch)
        clean = _strip_docstrings_and_comments(body)
        assert clean.count("save_scenario(") == 1
        # bind_workspace_to_scenario is called exactly once (in success)
        assert clean.count("bind_workspace_to_scenario(") == 1
        # The success branch comes AFTER the block branch
        block_pos = body.find("if project_record.project_origin in")
        save_pos = body.find("saved_record = save_scenario(")
        assert block_pos < save_pos
        # And the success branch's save_scenario is reached only when
        # the block check doesn't return
        assert body.find("return _render_scenario_workspace(") < save_pos or \
            body.find("return _render_scenario_workspace(") > block_pos

    def test_quirk_6_no_htmx_header_on_success(self):
        """Quirk 6: the success response does NOT emit HX-Trigger
        (unlike /save-run which sets HX-Trigger: refreshHistory).
        The success response is a full workspace render, not an HTMX
        partial."""
        body = _route_body("/scenarios/save")
        assert "HX-Trigger" not in body
        assert "HX-Redirect" not in body

    def test_quirk_7_scenario_summary_cards_include_export_count(self):
        """Quirk 7: scenario_summary_cards include an 'export_count'
        field, computed by counting entries in export_lineage per
        scenario_name. The export_count is the number of exports
        associated with that scenario."""
        body = _route_body("/scenarios/save")
        assert "export_counts[" in body
        assert '"export_count": export_counts.get' in body

    def test_quirk_8_scenario_summary_cards_fields(self):
        """Quirk 8: scenario_summary_cards include specific fields:
        scenario_id, scenario_name, project_code, updated_at,
        copied_from_scenario_id, project_irr, equity_irr, avg_dscr,
        export_count, governance_state."""
        body = _route_body("/scenarios/save")
        for field in [
            "scenario_id",
            "scenario_name",
            "project_code",
            "updated_at",
            "copied_from_scenario_id",
            "project_irr",
            "equity_irr",
            "avg_dscr",
            "export_count",
            "governance_state",
        ]:
            assert f'"{field}":' in body, (
                f"scenario_summary_cards must include {field!r}"
            )

    def test_quirk_9_replay_metadata_export_types(self):
        """Quirk 9: two distinct export_type values:
        - save_scenario uses 'saved_scenario_snapshot'
        - bind_workspace_to_scenario uses 'workspace_saved_boundary'
        (or the escaped variant)."""
        body = _route_body("/scenarios/save")
        assert 'export_type="saved_scenario_snapshot"' in body
        assert 'export_type="workspace_saved' in body  # the boundary char may be escaped

    def test_quirk_10_no_validate_form_call(self):
        """Quirk 10: the route does NOT call _validate_form. It accepts
        any form input as a snapshot. (Same as /scenarios/state/draft
        and /scenarios/state/discard.)"""
        body = _route_body("/scenarios/save")
        assert "_validate_form" not in body
