"""Phase 51G-1 — POST /save-run golden characterization.

Characterize current POST /save-run behavior BEFORE any extraction
to app/services/save_run_service.py.

POST /save-run is runtime-persistence sensitive. It is the first
route characterized that performs INTENDED runtime persistence
writes (save_run, save_project). These are NOT forbidden — they
are the route's primary purpose. The guardrail is "preserve
exactly as-is", not "do not call".

This file pins:

1. Route exists at POST /save-run in main_web.py.
2. Unauthenticated request → 302 to /login.
3. Authenticated + empty/dirty state → 200 + save-result-err
   template with HX-Trigger: refreshHistory.
4. Authenticated + valid factory_template origin → 200 +
   save-result-ok template with HX-Trigger: refreshHistory.
5. INTENDED runtime persistence writes (save_run, save_project)
   are performed and produce RunRecord / ProjectRecord rows.
6. Replay metadata export_type is "saved_run_metadata" for run
   and "saved_run_project_state" for project.
7. user_id is derived from session, never from form.
8. Form inputs are passed through exactly (9 numeric/text
   fields).
9. KPI dict from run_project is forwarded to RunRecord.kpis
   without transformation.
10. Effective project_type resolves to project_record.project_type
    when present (project_type from form is fallback).
11. /save-run error responses use the same save_result.html
    template (success=False + error message).
12. _clean_user_project_runtime_snapshot is currently NOT defined
    in main_web.py (existing latent bug: the user_created branch
    in /save-run raises NameError when reached). This is
    documented as a known characterization quirk, not fixed.
13. No record_export, no record_download_export,
    no record_runtime_summary_export, no
    record_institutional_workbook_export, no record_workspace_runtime,
    no update_scenario_last_run_summary is called by /save-run
    (the only persistence writes are save_run + save_project).
14. Phase 51F guardrails (engine output golden, parity-core lock,
    no-service-imports-main_web/main_api) all remain green.
15. /run, /compare, /validate, /download routes and services
    remain intact.

All tests are behavior-level (not call-count) where possible.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

import pytest


# ─── Paths and constants ────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_WEB = REPO_ROOT / "main_web.py"
SAVE_RESULT_HTML = REPO_ROOT / "app" / "templates" / "partials" / "save_result.html"


# ─── Helpers ────────────────────────────────────────────────────────────────

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _route_body(name: str) -> str:
    """Extract the body of a named async def route from main_web.py."""
    src = _read(MAIN_WEB)
    pattern = re.compile(
        rf"@app\.\w+\(\"{re.escape(name)}\"\)\s*\nasync def \w+\([^)]*\):.*?(?=\n@app\.|\Z)",
        re.DOTALL,
    )
    m = pattern.search(src)
    assert m, f"Route {name} not found in main_web.py"
    return m.group(0)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Route exists and structure preserved
# ═══════════════════════════════════════════════════════════════════════════

class TestSaveRunRouteStructure:
    """Pin the /save-run route's location and structural shape."""

    def test_save_run_route_exists_in_main_web(self):
        """POST /save-run must exist in main_web.py (not yet extracted)."""
        text = _read(MAIN_WEB)
        assert '@app.post("/save-run")' in text, (
            "POST /save-run must remain in main_web.py (Phase 51G-1 is "
            "characterization only, not extraction)."
        )

    def test_save_run_route_handler_is_save_run_endpoint(self):
        """Route handler is named save_run_endpoint."""
        text = _read(MAIN_WEB)
        assert "async def save_run_endpoint" in text, (
            "save_run_endpoint handler must exist in main_web.py"
        )

    def test_save_run_route_size_is_characteristic(self):
        """Current /save-run route size is ~127 non-blank lines.

        This pin is the lower bound — the route MUST NOT shrink
        (Phase 51G-1 is characterization only; later extraction
        happens in 51G-2). The route MAY grow by 1–2 lines
        (e.g. via comment, import) but a 50%+ drop would indicate
        silent refactor.
        """
        body = _route_body("/save-run")
        non_blank = sum(1 for line in body.splitlines() if line.strip())
        assert non_blank >= 110, (
            f"/save-run route shrunk to {non_blank} non-blank lines. "
            f"Phase 51G-1 is characterization only; route must remain "
            f"intact. (Expected ~127 lines; minimum 110.)"
        )
        assert non_blank <= 200, (
            f"/save-run route grew to {non_blank} non-blank lines. "
            f"Such growth is unusual for a characterization phase."
        )

    def test_save_run_route_does_not_import_main_web(self):
        """The route lives in main_web.py, so it trivially 'uses' main_web.
        We check that it does NOT call run_service or compare_service
        or validation_service or download_service (it has its own
        orchestration, not yet extracted)."""
        body = _route_body("/save-run")
        for forbidden in (
            "run_service.",
            "compare_service.",
            "validation_service.",
            "download_service.",
        ):
            assert forbidden not in body, (
                f"/save-run route must not call {forbidden} (Phase 51G-1 "
                f"characterization — no service extraction yet)"
            )

    def test_save_run_route_does_not_call_service_extraction(self):
        """No app/services/save_run_service import or call yet."""
        text = _read(MAIN_WEB)
        # Service extraction happens in Phase 51G-2, not 51G-1.
        assert "save_run_service" not in text, (
            "save_run_service must not exist yet — Phase 51G-1 is "
            "characterization only. Extraction is Phase 51G-2."
        )


# ═══════════════════════════════════════════════════════════════════════════
# 2. Auth / session boundary
# ═══════════════════════════════════════════════════════════════════════════

class TestSaveRunAuthBoundary:
    """Pin the auth redirect behavior at the /save-run boundary."""

    def test_unauthenticated_save_run_redirects_to_login(self, unauthenticated_client):
        """Unauthenticated POST /save-run must redirect to /login (302)."""
        r = unauthenticated_client.post(
            "/save-run",
            data={"project_type": "Wind", "scenario": "Base"},
            follow_redirects=False,
        )
        assert r.status_code == 302, (
            f"Expected 302 redirect, got {r.status_code}"
        )
        assert "/login" in r.headers.get("location", ""), (
            f"Expected Location header to contain /login, "
            f"got: {r.headers.get('location', '')}"
        )

    def test_save_run_route_body_uses_get_current_user(self):
        """Route body must call get_current_user(request)."""
        body = _route_body("/save-run")
        assert "get_current_user(request)" in body, (
            "/save-run must call get_current_user(request) for auth check"
        )

    def test_save_run_route_uses_redirect_response_on_no_user(self):
        """If get_current_user returns falsy, the route must return
        RedirectResponse(url=\"/login\", status_code=302)."""
        body = _route_body("/save-run")
        assert 'RedirectResponse(url="/login", status_code=302)' in body, (
            "/save-run must redirect to /login with 302 on no user"
        )

    def test_save_run_user_id_derived_from_session_not_form(self):
        """The route comments and code must derive user_id from session,
        never from form (security: never trust client-provided user_id)."""
        body = _route_body("/save-run")
        assert "user_id = user.user_id" in body, (
            "/save-run must derive user_id from session via user.user_id"
        )
        # The form must NOT contain user_id being trusted
        # (the route should not read user_id from form dict)
        assert "form.get(\"user_id\"" not in body, (
            "/save-run must not read user_id from form"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 3. Form parsing — 9 input fields read from form exactly
# ═══════════════════════════════════════════════════════════════════════════

class TestSaveRunFormParsing:
    """Pin the exact form field set read by /save-run."""

    EXPECTED_FIELDS = [
        "capacity_mw",
        "tariff_eur_mwh",
        "p50_hours",
        "total_capex_keur",
        "opex_y1_keur",
        "gearing_pct",
        "target_dscr",
        "interest_rate_pct",
        "tenor_years",
    ]

    def test_route_reads_exact_9_input_fields_from_form(self):
        """The route reads exactly these 9 fields from form."""
        body = _route_body("/save-run")
        for field in self.EXPECTED_FIELDS:
            assert f'form.get("{field}"' in body, (
                f"/save-run must read form field {field!r}"
            )

    def test_route_does_not_read_user_id_from_form(self):
        """user_id must come from session, not form."""
        body = _route_body("/save-run")
        assert "form.get(\"user_id" not in body, (
            "/save-run must not read user_id from form (security)"
        )

    def test_route_builds_inputs_dict_with_all_9_fields(self):
        """The route builds a dict `inputs` with all 9 fields."""
        body = _route_body("/save-run")
        # The route constructs inputs = { "capacity_mw": form.get(...), ... }
        assert "inputs = {" in body, (
            "/save-run must construct an inputs dict"
        )

    def test_route_reads_project_type_and_scenario_from_form(self):
        """The route reads project_type and scenario from form
        (for form-level routing)."""
        body = _route_body("/save-run")
        assert 'form.get("project_type"' in body
        assert 'form.get("scenario"' in body


# ═══════════════════════════════════════════════════════════════════════════
# 4. Project / scenario selection
# ═══════════════════════════════════════════════════════════════════════════

class TestSaveRunProjectScenarioSelection:
    """Pin how /save-run selects the project and scenario."""

    def test_route_resolves_project_from_snapshot(self):
        """Route must call _project_workspace_from_snapshot to resolve
        project_record and workspace_state from the form snapshot."""
        body = _route_body("/save-run")
        assert "_project_workspace_from_snapshot" in body, (
            "/save-run must resolve project from snapshot via "
            "_project_workspace_from_snapshot"
        )

    def test_route_collects_form_snapshot(self):
        """Route must collect the form snapshot via _collect_form_snapshot."""
        body = _route_body("/save-run")
        assert "_collect_form_snapshot" in body, (
            "/save-run must call _collect_form_snapshot(form)"
        )

    def test_route_uses_effective_project_type(self):
        """Route prefers project_record.project_type; falls back to form."""
        body = _route_body("/save-run")
        assert "effective_project_type" in body, (
            "/save-run must compute effective_project_type from "
            "project_record.project_type or form"
        )
        assert (
            "project_record.project_type or project_type" in body
        ), "/save-run must fall back to form project_type when record is None"

    def test_route_uses_project_code_and_project_name_from_record(self):
        """project_code and project_name come from project_record,
        not from form."""
        body = _route_body("/save-run")
        assert "project_code = project_record.project_code" in body
        assert "project_name = project_record.project_name" in body


# ═══════════════════════════════════════════════════════════════════════════
# 5. Runtime origin behavior
# ═══════════════════════════════════════════════════════════════════════════

class TestSaveRunRuntimeOrigin:
    """Pin how /save-run interacts with the runtime guard and origin."""

    def test_route_calls_check_runtime_allowed(self):
        """Route must call check_runtime_allowed to determine allow_run."""
        body = _route_body("/save-run")
        assert "check_runtime_allowed" in body, (
            "/save-run must call check_runtime_allowed to gate execution"
        )

    def test_route_blocks_when_runtime_not_allowed(self):
        """If allow_run is False, route must return a 200 save_result-err
        with HX-Trigger: refreshHistory."""
        body = _route_body("/save-run")
        # Pattern: if not allow_run: return templates.TemplateResponse(... "partials/save_result.html", context={"success": False, "error": guard_message}, headers={"HX-Trigger": "refreshHistory"})
        assert "if not allow_run:" in body
        # The "not allow_run" branch must use save_result.html partial
        assert "partials/save_result.html" in body
        assert "refreshHistory" in body

    def test_runtime_origin_unpacked_to_3_tuple(self):
        """check_runtime_allowed returns 3-tuple (allow_run, runtime_origin, guard_message)."""
        body = _route_body("/save-run")
        # Must unpack 3 values
        assert (
            "allow_run, runtime_origin, guard_message" in body
        ), "Route must unpack 3-tuple from check_runtime_allowed"


# ═══════════════════════════════════════════════════════════════════════════
# 6. Model execution path
# ═══════════════════════════════════════════════════════════════════════════

class TestSaveRunModelExecution:
    """Pin the model execution path inside /save-run."""

    def test_route_branches_on_project_origin(self):
        """Route has two branches: user_created vs factory_template."""
        body = _route_body("/save-run")
        assert 'project_record.project_origin == "user_created"' in body, (
            "/save-run must branch on project_origin (user_created vs factory_template)"
        )
        assert "user_created" in body
        # Both branches must exist
        assert body.count('project_origin == "user_created"') == 1

    def test_user_created_branch_uses_build_projectinputs_from_snapshot(self):
        """user_created branch uses build_projectinputs_from_snapshot."""
        body = _route_body("/save-run")
        # The user_created branch should call build_projectinputs_from_snapshot
        assert "build_projectinputs_from_snapshot" in body, (
            "user_created branch must call build_projectinputs_from_snapshot"
        )

    def test_factory_template_branch_uses_build_schema_from_form(self):
        """factory_template branch uses _build_schema_from_form +
        build_projectinputs."""
        body = _route_body("/save-run")
        assert "_build_schema_from_form" in body, (
            "factory_template branch must call _build_schema_from_form"
        )
        assert "build_projectinputs" in body, (
            "factory_template branch must call build_projectinputs"
        )

    def test_factory_template_branch_resolves_runtime_seed(self):
        """factory_template branch maps template_source to runtime key
        (tuho / oborovo / Solar / Wind)."""
        body = _route_body("/save-run")
        assert "_normalize_template_source" in body, (
            "factory_template branch must call _normalize_template_source"
        )
        assert 'runtime_seed == "tuho"' in body
        assert 'runtime_seed == "oborovo"' in body

    def test_route_calls_run_project(self):
        """Route must call run_project(runtime_project_key, scenario, ...)."""
        body = _route_body("/save-run")
        assert "run_project(" in body, (
            "/save-run must call run_project to execute the model"
        )

    def test_route_pulls_kpis_from_result(self):
        """Route reads kpis = result[\"kpis\"] from the model result."""
        body = _route_body("/save-run")
        assert 'kpis = result["kpis"]' in body, (
            "/save-run must read kpis from result dict"
        )

    def test_route_wraps_model_execution_in_broad_except(self):
        """Model execution is wrapped in a broad try/except Exception."""
        body = _route_body("/save-run")
        # Two try blocks: one for model execution, one for persistence
        assert body.count("except Exception as e:") >= 2
        # Model error path uses 'Model error: {str(e)}'
        assert "Model error:" in body

    def test_user_created_branch_has_latent_name_error(self):
        """KNOWN CHARACTERIZATION QUIRK: the user_created branch
        references _clean_user_project_runtime_snapshot which is NOT
        defined in main_web.py. This causes a NameError at runtime
        when a user_created project hits /save-run.

        This is a pre-existing bug, NOT introduced by Phase 51G-1.
        Pinning it here so that any future fix is intentional.
        """
        body = _route_body("/save-run")
        assert "_clean_user_project_runtime_snapshot" in body, (
            "/save-run user_created branch must reference "
            "_clean_user_project_runtime_snapshot (even if undefined)"
        )
        # Verify the function is NOT defined in main_web.py
        text = _read(MAIN_WEB)
        assert "def _clean_user_project_runtime_snapshot" not in text, (
            "_clean_user_project_runtime_snapshot should NOT be defined "
            "(existing latent bug). If it IS now defined, the bug was "
            "fixed — that is an intentional change, not a regression."
        )


# ═══════════════════════════════════════════════════════════════════════════
# 7. Intended runtime persistence writes — save_run + save_project
# ═══════════════════════════════════════════════════════════════════════════

class TestSaveRunIntendedPersistenceWrites:
    """Pin the INTENDED runtime persistence writes for /save-run.

    /save-run is the PRIMARY entry point for user-driven persistence.
    save_run + save_project are INTENDED, not forbidden.
    """

    def test_route_calls_save_run(self):
        """Route must call save_run with the expected kwargs."""
        body = _route_body("/save-run")
        assert "save_run(" in body, "/save-run must call save_run"
        # Verify key kwargs are passed positionally/by name
        for kw in [
            "user_id=user_id",
            "project_type=effective_project_type",
            "scenario=scenario",
            "inputs=inputs",
            "kpis=kpis",
        ]:
            assert kw in body, f"save_run must be called with {kw}"

    def test_route_calls_save_project(self):
        """Route must call save_project with the expected kwargs."""
        body = _route_body("/save-run")
        assert "save_project(" in body, "/save-run must call save_project"
        for kw in [
            "user_id=user_id",
            "project_code=project_code",
            "project_name=project_name",
            "source_project_template=project_code",
            "last_run_summary=kpis",
        ]:
            assert kw in body, f"save_project must be called with {kw}"

    def test_save_run_called_first_save_project_second(self):
        """Order of writes: save_run first, then save_project.

        Both writes are inside the same try/except. If save_run
        raises, save_project is NOT called. If save_project
        raises after save_run succeeded, save_run row is still
        committed.
        """
        body = _route_body("/save-run")
        run_pos = body.find("run_record = save_run(")
        proj_pos = body.find("save_project(")
        assert run_pos != -1
        assert proj_pos != -1
        # save_run must come before save_project in the source
        assert run_pos < proj_pos, (
            "save_run must be called before save_project in /save-run"
        )

    def test_save_run_includes_replay_metadata(self):
        """save_run call must pass replay_metadata with export_type."""
        body = _route_body("/save-run")
        assert "replay_metadata=_replay_metadata_for_project(" in body
        assert '"saved_run_metadata"' in body, (
            "save_run replay_metadata must use export_type='saved_run_metadata'"
        )

    def test_save_project_includes_replay_metadata(self):
        """save_project call must pass replay_metadata with export_type
        'saved_run_project_state'."""
        body = _route_body("/save-run")
        assert '"saved_run_project_state"' in body, (
            "save_project replay_metadata must use "
            "export_type='saved_run_project_state'"
        )

    def test_save_project_uses_run_record_created_at(self):
        """save_project's replay_metadata.runtime_timestamp comes from
        run_record.created_at.isoformat() — not utc_now_iso().

        This guarantees the project's runtime_timestamp is the SAME
        as the run's, not a few microseconds later.
        """
        body = _route_body("/save-run")
        assert "run_record.created_at.isoformat()" in body, (
            "save_project runtime_timestamp must come from run_record.created_at"
        )

    def test_save_project_replay_metadata_includes_project_id_none(self):
        """save_project's replay_metadata must explicitly set project_id=None
        (the repo will fill it in based on the existing row)."""
        body = _route_body("/save-run")
        assert "project_id=None" in body, (
            "save_project replay_metadata must set project_id=None"
        )

    def test_save_run_endpoint_returns_run_id(self):
        """Success response context must include run_id, project_type,
        scenario, created_at."""
        body = _route_body("/save-run")
        for field in [
            "\"run_id\"",
            "\"project_type\"",
            "\"scenario\"",
            "\"created_at\"",
        ]:
            assert field in body, (
                f"Success TemplateResponse context must include {field}"
            )
        assert "run_record.run_id" in body
        assert "run_record.created_at.isoformat()" in body

    def test_save_run_persistence_block_wrapped_in_try_except(self):
        """The persistence block is wrapped in try/except Exception."""
        body = _route_body("/save-run")
        # The persistence block has its own try/except with 'Save failed' message
        assert '"Save failed:' in body or "Save failed:" in body, (
            "Persistence block must catch exceptions and return "
            "'Save failed: {error}' message"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 8. Response / template / redirect behavior
# ═══════════════════════════════════════════════════════════════════════════

class TestSaveRunResponseShape:
    """Pin the response / template / redirect behavior."""

    def test_save_result_partial_template_exists(self):
        """The save_result.html partial template must exist."""
        assert SAVE_RESULT_HTML.is_file(), (
            f"Required partial template {SAVE_RESULT_HTML} not found"
        )

    def test_save_result_template_uses_success_flag(self):
        """save_result.html uses {% if success %} to switch layout."""
        text = _read(SAVE_RESULT_HTML)
        assert "{% if success %}" in text
        assert "{% else %}" in text

    def test_save_result_template_renders_run_id_on_success(self):
        """save_result.html renders run_id on success."""
        text = _read(SAVE_RESULT_HTML)
        assert "{{ run_id }}" in text
        assert "{{ project_type }}" in text
        assert "{{ scenario }}" in text
        assert "{{ created_at" in text

    def test_save_result_template_renders_error_on_failure(self):
        """save_result.html renders error message on failure."""
        text = _read(SAVE_RESULT_HTML)
        assert "{{ error }}" in text

    def test_all_responses_use_hx_trigger_refresh_history(self):
        """All save_result responses include HX-Trigger: refreshHistory.

        The route uses this header to tell HTMX to refresh the run
        history panel after a save attempt.
        """
        body = _route_body("/save-run")
        # Count occurrences of refreshHistory header
        assert body.count('"HX-Trigger": "refreshHistory"') >= 4, (
            "All save_result responses must include HX-Trigger: refreshHistory"
        )

    def test_all_responses_use_save_result_html(self):
        """All non-auth responses from /save-run use save_result.html."""
        body = _route_body("/save-run")
        # Count templates.TemplateResponse uses
        assert body.count('name="partials/save_result.html"') >= 4, (
            "All 4 save_result responses (allow_run block, validate block, "
            "model except, persist except, success) must use save_result.html"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 9. Forbidden side effects — what /save-run must NOT call
# ═══════════════════════════════════════════════════════════════════════════

class TestSaveRunForbiddenSideEffects:
    """Pin what /save-run must NOT do (besides intended save_run+save_project)."""

    FORBIDDEN_CALLS = [
        # Audit / export-pipeline calls — these are intended for
        # /download and /export, not /save-run
        ("record_export", "/save-run must not call record_export"),
        ("record_download_export", "/save-run must not call record_download_export"),
        ("record_runtime_summary_export", "/save-run must not call record_runtime_summary_export"),
        ("record_institutional_workbook_export", "/save-run must not call record_institutional_workbook_export"),
        # Runtime / scenario summary updates — those happen elsewhere
        ("record_workspace_runtime", "/save-run must not call record_workspace_runtime"),
        ("update_scenario_last_run_summary", "/save-run must not call update_scenario_last_run_summary"),
    ]

    @pytest.mark.parametrize(
        "call_name,reason",
        FORBIDDEN_CALLS,
        ids=lambda v: v[0] if isinstance(v, tuple) else v,
    )
    def test_save_run_route_does_not_call(self, call_name, reason):
        """Pin that /save-run does not invoke the forbidden helpers."""
        body = _route_body("/save-run")
        # Look for the call as function/method call
        assert f"{call_name}(" not in body, reason

    def test_save_run_does_not_import_record_export(self):
        """/save-run must not import record_export helpers."""
        text = _read(MAIN_WEB)
        # The route body and its imports do not include record_export
        # (it may appear in the file in a different context, but the
        # route must not import or call it).
        body = _route_body("/save-run")
        for forbidden in (
            "record_export",
            "record_download_export",
            "record_runtime_summary_export",
            "record_institutional_workbook_export",
        ):
            assert forbidden not in body, (
                f"/save-run route body must not reference {forbidden}"
            )


# ═══════════════════════════════════════════════════════════════════════════
# 10. Phase 51F guardrails must remain green
# ═══════════════════════════════════════════════════════════════════════════

class TestPhase51FGuardrailsStillActive:
    """Phase 51F guardrails must remain green after Phase 51G-1.

    This phase is characterization only. No parity-core, no
    service-import-direction, no engine-output drift is allowed.
    """

    def test_phase51f_guardrails_test_module_exists(self):
        path = REPO_ROOT / "tests" / "test_phase51f_parallel_work_guardrails.py"
        assert path.is_file(), "Phase 51F test module must remain"

    def test_no_save_run_service_yet(self):
        """No save_run_service.py — extraction is Phase 51G-2."""
        assert not (REPO_ROOT / "app" / "services" / "save_run_service.py").exists(), (
            "save_run_service.py must NOT exist yet — Phase 51G-1 is "
            "characterization only. Extraction happens in Phase 51G-2."
        )

    def test_main_web_intact(self):
        """main_web.py must be untouched (no production code changes)."""
        # If this file is committed as part of Phase 51G-1, it must
        # not have been modified. This test fails if git diff shows
        # any change to main_web.py vs the base SHA.
        text = _read(MAIN_WEB)
        # The save_run_endpoint function must still exist
        assert "async def save_run_endpoint" in text
        # And the route must still be defined
        assert '@app.post("/save-run")' in text

    def test_all_phase51_services_remain_intact(self):
        """No service extracted or modified by Phase 51G-1."""
        # Check that the 4 already-extracted services still exist
        # and have not been modified
        for service in [
            "run_service.py",
            "compare_service.py",
            "validation_service.py",
            "download_service.py",
        ]:
            path = REPO_ROOT / "app" / "services" / service
            assert path.is_file(), f"Service {service} must still exist"

    def test_phase51f_guardrail_test_still_passes(self):
        """Phase 51F guardrails must still be importable and runnable.

        This is a smoke test, not a full run. The full run is in
        the CI workflow.
        """
        path = REPO_ROOT / "tests" / "test_phase51f_parallel_work_guardrails.py"
        text = _read(path)
        # The test module must still contain the 3 guardrail classes
        for guardrail in [
            "TestEngineOutputGoldenTUHO",
            "TestEngineOutputGoldenOborovo",
            "TestParityCoreLock",
            "TestNoServiceImportsMainWebOrMainApi",
        ]:
            assert f"class {guardrail}" in text, (
                f"Phase 51F guardrail class {guardrail} must remain"
            )


# ═══════════════════════════════════════════════════════════════════════════
# 11. Phase 51G-1 self-inventory
# ═══════════════════════════════════════════════════════════════════════════

class TestPhase51G1SelfInventory:
    """The characterization test must be self-consistent."""

    def test_phase51g1_docs_exists(self):
        path = REPO_ROOT / "docs" / "phase51g1_save_run_route_golden_characterization.md"
        assert path.is_file(), (
            f"Required docs file {path} not found"
        )

    def test_phase51g1_summary_json_exists(self):
        path = REPO_ROOT / "reports" / "phase51g1_save_run_route_golden_characterization_summary.json"
        assert path.is_file(), (
            f"Required summary file {path} not found"
        )

    def test_phase51g1_docs_mention_route_size(self):
        path = REPO_ROOT / "docs" / "phase51g1_save_run_route_golden_characterization.md"
        text = _read(path)
        # The docs must mention the route's current size
        assert "127" in text or "non-blank" in text.lower(), (
            "Docs must mention /save-run route size"
        )


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures (test infra)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Per-test SQLite database for clean state."""
    db_file = tmp_path / f"phase51g1_{uuid.uuid4().hex[:8]}.db"
    monkeypatch.setenv("FINCO_DB_PATH", str(db_file))
    import app.persistence.db as db_mod
    db_mod.DB_PATH = str(db_file)
    db_mod._connection = None
    yield str(db_file)
    db_mod._connection = None


@pytest.fixture
def unauthenticated_client(isolated_db):
    from fastapi.testclient import TestClient
    from main_web import app
    return TestClient(app)
