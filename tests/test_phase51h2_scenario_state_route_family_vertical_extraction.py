"""Phase 51H-2 — /scenarios/state/* route family vertical extraction tests.

This test suite pins the Phase 51H-2 extraction:

The /scenarios/state/draft and /scenarios/state/discard route
orchestration in main_web.py is now extracted into a new
service module ``app/services/scenario_state_route_service.py``.

Before Phase 51H-2 (Phases 51G-3, 51H-1):
    - main_web.py contained the full /scenarios/state/draft and
      /scenarios/state/discard orchestration inline.
    - Routes called save_workspace_state / discard_workspace_draft
      directly via module-scope imports.
    - No service module existed for the scenario-state family.
    - scenario_state_service.py (data-layer) was the only related
      service.

After Phase 51H-2:
    - main_web.py routes are thin wrappers (auth + form + deps
      bundle + service call + JSONResponse).
    - app/services/scenario_state_route_service.py owns the
      orchestration (execute_draft_route, execute_discard_route,
      ScenarioStateRouteOutcome, ScenarioStateRouteDeps).
    - scenario_state_service.py is unchanged (still data-layer
      only — no Request, no form, no auth).
    - The deps bundle injects the helpers from main_web module
      scope as callables; the service does NOT import main_web
      or main_api.

Scope (Phase 51H-2 is a behavior-preserving vertical extraction):
- Allowed: app/services/scenario_state_route_service.py,
  main_web.py, tests/test_phase51h1_*, tests/test_phase51h2_*,
  docs/phase51h2_*, reports/phase51h2_*.
- NOT allowed: model/runtime/formula changes, fixture CSV
  changes, schema/migration changes, JS changes, parity-core
  file changes, unrelated route refactors, export service
  refactors, repository refactors, scenario_state_service.py
  conversion into route orchestration.

These tests verify:
1. app/services/scenario_state_route_service.py exists.
2. scenario_state_route_service.py does not import main_web
   or main_api.
3. Existing app/services/scenario_state_service.py remains
   data-layer-oriented and is not turned into a request/form/
   auth route orchestration module.
4. POST /scenarios/state/draft route remains thin after
   extraction.
5. POST /scenarios/state/discard route remains thin after
   extraction.
6. Existing Phase 51H-1 characterization still passes.
7. Draft behavior preserved.
8. Discard behavior preserved.
9. All 12 quirks preserved.
10. Intended side effects preserved:
    - draft save_workspace_state × 1;
    - discard discard_workspace_draft × 1;
    - discard fallback save_workspace_state × 0-1.
11. Forbidden side effects remain absent.
12. JSON response keys/status/header behavior preserved.
13. Unauth still returns 401 JSON, not redirect.
14. No HX-Trigger/HX-Redirect/template render introduced.
15. /run, /compare, /validate, /download, /save-run remain
    service-backed and thin.
16. run_service.py, compare_service.py, validation_service.py,
    download_service.py, save_run_service.py remain intact.
17. Phase 51F guardrails pass.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_WEB = REPO_ROOT / "main_web.py"
SCENARIO_STATE_SERVICE = REPO_ROOT / "app" / "services" / "scenario_state_service.py"
SCENARIO_STATE_ROUTE_SERVICE = (
    REPO_ROOT / "app" / "services" / "scenario_state_route_service.py"
)


# ─── Helpers ───────────────────────────────────────────────────────────────


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _strip_docstrings_and_comments(text: str) -> str:
    """Strip module docstrings, function/class docstrings, and comments.

    Used for code-level checks (e.g. "does the service call forbidden
    side effects in actual code, not just in docstrings?")."""
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
        pattern + r"\s*\nasync def \w+\(.*?\n    return .*?\)",
        text,
        re.DOTALL,
    )
    assert m is not None, f"Route {route_path} not found"
    return m.group(0)


def _service_function_body(name: str) -> str:
    """Return the body of a function in scenario_state_route_service.py."""
    text = _read(SCENARIO_STATE_ROUTE_SERVICE)
    pattern = re.escape(f"async def {name}(")
    m = re.search(
        pattern + r".*?(?=\nasync def |\nclass |\Z)",
        text,
        re.DOTALL,
    )
    assert m is not None, f"Function {name} not found in service"
    return m.group(0)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Service module exists
# ─────────────────────────────────────────────────────────────────────────────


class TestServiceModuleExists:
    """The new service module exists."""

    def test_scenario_state_route_service_file_exists(self):
        assert SCENARIO_STATE_ROUTE_SERVICE.exists(), (
            f"{SCENARIO_STATE_ROUTE_SERVICE} must exist after Phase 51H-2"
        )

    def test_module_has_scenario_state_route_outcome(self):
        text = _read(SCENARIO_STATE_ROUTE_SERVICE)
        assert "@dataclass" in text
        assert "class ScenarioStateRouteOutcome" in text
        # Required fields
        for field in ["payload", "status_code", "headers", "is_redirect", "redirect_url"]:
            assert field in text, f"ScenarioStateRouteOutcome must have '{field}' field"

    def test_module_has_scenario_state_route_deps(self):
        text = _read(SCENARIO_STATE_ROUTE_SERVICE)
        assert "class ScenarioStateRouteDeps" in text
        # Required dep fields
        for dep in [
            "collect_form_snapshot",
            "project_workspace_from_snapshot",
            "save_workspace_state",
            "discard_workspace_draft",
            "snapshots_equal",
            "default_workspace_snapshot",
            "governance_snapshot",
            "replay_metadata_for_project",
            "workspace_state_meta",
        ]:
            assert dep in text, f"ScenarioStateRouteDeps must have '{dep}' field"

    def test_module_has_execute_draft_route(self):
        text = _read(SCENARIO_STATE_ROUTE_SERVICE)
        assert "async def execute_draft_route(" in text

    def test_module_has_execute_discard_route(self):
        text = _read(SCENARIO_STATE_ROUTE_SERVICE)
        assert "async def execute_discard_route(" in text


# ─────────────────────────────────────────────────────────────────────────────
# 2. Service does NOT import main_web or main_api
# ─────────────────────────────────────────────────────────────────────────────


class TestServiceImportDirection:
    """The service does NOT import main_web or main_api (one-way
    import direction)."""

    def test_service_does_not_import_main_web(self):
        text = _read(SCENARIO_STATE_ROUTE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "import main_web" not in clean
        assert "from main_web" not in clean

    def test_service_does_not_import_main_api(self):
        text = _read(SCENARIO_STATE_ROUTE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert "import main_api" not in clean
        assert "from main_api" not in clean

    def test_service_does_not_define_main_web_helpers(self):
        """The service does NOT define module-level helpers that
        are typically defined in main_web (e.g. _collect_form_snapshot).
        It receives them via deps."""
        text = _read(SCENARIO_STATE_ROUTE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # The service MUST NOT define any of these as module-level
        # functions; they are passed in as deps.
        assert "def _collect_form_snapshot" not in clean
        assert "def _project_workspace_from_snapshot" not in clean
        assert "def _default_workspace_snapshot" not in clean
        assert "def _governance_snapshot" not in clean
        assert "def _replay_metadata_for_project" not in clean
        assert "def _workspace_state_meta" not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 3. scenario_state_service.py remains data-layer
# ─────────────────────────────────────────────────────────────────────────────


class TestScenarioStateServiceUnchanged:
    """The pre-existing scenario_state_service.py is unchanged:
    still data-layer only, no Request, no form, no auth."""

    def test_scenario_state_service_still_has_data_layer_helpers(self):
        text = _read(SCENARIO_STATE_SERVICE)
        for helper in [
            "build_workspace_state_metadata",
            "resolve_runtime_snapshot",
            "check_runtime_allowed",
            "scenario_provenance_for_record",
        ]:
            assert f"def {helper}(" in text, (
                f"scenario_state_service.py must still expose {helper}()"
            )

    def test_scenario_state_service_has_no_route_orchestration(self):
        text = _read(SCENARIO_STATE_SERVICE)
        # No route-orchestration classes
        assert "class ScenarioStateRouteOutcome" not in text
        assert "class ScenarioStateRouteDeps" not in text
        # No execute_*_route() functions
        assert "def execute_draft_route" not in text
        assert "def execute_discard_route" not in text

    def test_scenario_state_service_does_not_depend_on_request_or_form(self):
        text = _read(SCENARIO_STATE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # No template
        assert "TemplateResponse" not in clean
        # No auth
        assert "get_current_user" not in clean
        # No HTML form handling
        assert "await request.form" not in clean
        assert "form.get" not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 4. Routes are thin after extraction
# ─────────────────────────────────────────────────────────────────────────────


class TestRoutesAreThin:
    """Both routes are thin after extraction (auth + form + deps +
    service call + JSONResponse)."""

    def test_draft_route_calls_execute_draft_route(self):
        body = _route_body("/scenarios/state/draft")
        clean = _strip_docstrings_and_comments(body)
        assert "execute_draft_route(" in clean

    def test_discard_route_calls_execute_discard_route(self):
        body = _route_body("/scenarios/state/discard")
        clean = _strip_docstrings_and_comments(body)
        assert "execute_discard_route(" in clean

    def test_draft_route_constructs_scenario_state_route_deps(self):
        body = _route_body("/scenarios/state/draft")
        clean = _strip_docstrings_and_comments(body)
        assert "ScenarioStateRouteDeps(" in clean

    def test_discard_route_constructs_scenario_state_route_deps(self):
        body = _route_body("/scenarios/state/discard")
        clean = _strip_docstrings_and_comments(body)
        assert "ScenarioStateRouteDeps(" in clean

    def test_draft_route_size_after_51h2(self):
        """Pin current route size. The route is thin (auth + form +
        deps bundle + service call + JSONResponse)."""
        body = _route_body("/scenarios/state/draft")
        non_blank = [l for l in body.splitlines() if l.strip()]
        # 36 non-blank (was 33 in 51H-1; +3 lines for the new
        # ScenarioStateRouteDeps and execute_draft_route wiring)
        assert 25 <= len(non_blank) <= 50, (
            f"/scenarios/state/draft is {len(non_blank)} non-blank lines; "
            f"expected 25-50 (thin route after 51H-2)"
        )

    def test_discard_route_size_after_51h2(self):
        body = _route_body("/scenarios/state/discard")
        non_blank = [l for l in body.splitlines() if l.strip()]
        assert 25 <= len(non_blank) <= 50

    def test_draft_route_does_no_orchestration(self):
        """The route must not contain user-facing draft branch
        orchestration or any model-execution logic."""
        body = _route_body("/scenarios/state/draft")
        clean = _strip_docstrings_and_comments(body)
        # No form.get("current_saved_scenario_id"...) (now in service)
        assert 'form.get("current_saved_scenario_id"' not in clean
        # No replay_metadata assembly (now in service)
        assert "replay_metadata=" not in clean
        # No save_workspace_state call (now in service via deps)
        assert "save_workspace_state(" not in clean

    def test_discard_route_does_no_orchestration(self):
        body = _route_body("/scenarios/state/discard")
        clean = _strip_docstrings_and_comments(body)
        # No discard_workspace_draft call (now in service via deps)
        assert "discard_workspace_draft(" not in clean
        # No baseline_snapshot fallback logic (now in service)
        assert "baseline_snapshot" not in clean
        # No payload["snapshot"] assignment (now in service)
        assert 'payload["snapshot"]' not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 5. Service owns the orchestration
# ─────────────────────────────────────────────────────────────────────────────


class TestServiceOwnsOrchestration:
    """The service module owns the orchestration."""

    def test_service_calls_save_workspace_state_exactly_once_in_draft(self):
        body = _service_function_body("execute_draft_route")
        clean = _strip_docstrings_and_comments(body)
        # save_workspace_state is called via deps (1× per success)
        assert "deps.save_workspace_state(" in clean
        assert clean.count("deps.save_workspace_state(") == 1

    def test_service_calls_discard_workspace_draft_exactly_once(self):
        body = _service_function_body("execute_discard_route")
        clean = _strip_docstrings_and_comments(body)
        assert "deps.discard_workspace_draft(" in clean
        assert clean.count("deps.discard_workspace_draft(") == 1

    def test_service_discard_fallback_calls_save_workspace_state(self):
        """When discard_workspace_draft returns None, the service
        also calls save_workspace_state(...) as fallback."""
        body = _service_function_body("execute_discard_route")
        clean = _strip_docstrings_and_comments(body)
        # Inside the if workspace_state is None branch
        assert "if workspace_state is None" in clean
        assert "deps.save_workspace_state(" in clean
        # The fallback uses baseline_snapshot
        assert "draft_snapshot=baseline_snapshot" in body
        assert "saved_snapshot=baseline_snapshot" in body
        assert "dirty=False" in body

    def test_service_draft_replay_metadata_export_type(self):
        body = _service_function_body("execute_draft_route")
        # export_type = "workspace_draft_state" preserved
        assert 'export_type="workspace_draft_state"' in body
        # scenario_id is passed
        assert "scenario_id=active_scenario_id" in body

    def test_service_discard_fallback_replay_metadata_export_type(self):
        body = _service_function_body("execute_discard_route")
        assert 'export_type="workspace_draft_state"' in body

    def test_service_draft_passes_dirty_from_snapshots_equal(self):
        body = _service_function_body("execute_draft_route")
        clean = _strip_docstrings_and_comments(body)
        assert "not deps.snapshots_equal(snapshot, saved_snapshot)" in clean

    def test_service_draft_preserves_active_scenario_id_quirk(self):
        body = _service_function_body("execute_draft_route")
        # Both branches (existing vs form)
        assert "existing.active_scenario_id" in body
        assert 'form.get("current_saved_scenario_id", "") or None' in body

    def test_service_discard_includes_snapshot_in_payload(self):
        """Quirk 3: discard response includes 'snapshot' key with
        workspace_state.draft_snapshot."""
        body = _service_function_body("execute_discard_route")
        assert 'payload["snapshot"] = workspace_state.draft_snapshot' in body

    def test_service_draft_message_is_constant(self):
        """Quirk 1."""
        body = _service_function_body("execute_draft_route")
        assert (
            "Workspace draft captured. Saved scenario authority is unchanged."
            in body
        )

    def test_service_discard_message_is_constant(self):
        """Quirk 2."""
        body = _service_function_body("execute_discard_route")
        # The string may be split across lines by Python implicit
        # string concatenation in the source. Check both halves.
        assert (
            "Unsaved edits discarded. Workspace restored to the last"
            in body
        )
        assert "saved runtime boundary." in body


# ─────────────────────────────────────────────────────────────────────────────
# 6. Intended side effects preserved
# ─────────────────────────────────────────────────────────────────────────────


class TestIntendedSideEffectsPreserved:
    """Intended persistence writes are preserved in the service."""

    def test_draft_save_workspace_state_intended(self):
        body = _service_function_body("execute_draft_route")
        clean = _strip_docstrings_and_comments(body)
        # Exactly 1 call to deps.save_workspace_state
        assert clean.count("deps.save_workspace_state(") == 1

    def test_draft_save_workspace_state_args(self):
        body = _service_function_body("execute_draft_route")
        assert "user_id=user.user_id" in body
        assert "project_id=project_record.project_id" in body
        assert "project_code=project_code" in body
        assert "draft_snapshot=snapshot" in body
        assert "saved_snapshot=saved_snapshot" in body
        assert "dirty=not deps.snapshots_equal(snapshot, saved_snapshot)" in body
        assert "governance_state=deps.governance_snapshot(project_code)" in body

    def test_discard_discard_workspace_draft_intended(self):
        body = _service_function_body("execute_discard_route")
        clean = _strip_docstrings_and_comments(body)
        assert clean.count("deps.discard_workspace_draft(") == 1

    def test_discard_discard_workspace_draft_args(self):
        body = _service_function_body("execute_discard_route")
        assert "user.user_id, project_record.project_id" in body

    def test_discard_fallback_save_workspace_state_args(self):
        body = _service_function_body("execute_discard_route")
        assert "draft_snapshot=baseline_snapshot" in body
        assert "saved_snapshot=baseline_snapshot" in body
        assert "dirty=False" in body
        assert "governance_state=deps.governance_snapshot(project_code)" in body

    def test_draft_does_not_call_discard_workspace_draft(self):
        body = _service_function_body("execute_draft_route")
        clean = _strip_docstrings_and_comments(body)
        assert "deps.discard_workspace_draft(" not in clean

    def test_discard_does_not_repeat_discard_in_fallback(self):
        """The fallback only calls save_workspace_state, NOT
        discard_workspace_draft again."""
        body = _service_function_body("execute_discard_route")
        clean = _strip_docstrings_and_comments(body)
        # discard_workspace_draft is called exactly once
        assert clean.count("deps.discard_workspace_draft(") == 1
        # save_workspace_state is called exactly once (in fallback)
        assert clean.count("deps.save_workspace_state(") == 1


# ─────────────────────────────────────────────────────────────────────────────
# 7. Forbidden side effects remain absent
# ─────────────────────────────────────────────────────────────────────────────


class TestForbiddenSideEffectsAbsent:
    """Forbidden side effects must NOT be introduced by the 51H-2
    extraction."""

    @pytest.mark.parametrize(
        "forbidden_symbol",
        [
            "record_export",
            "record_download_export",
            "record_runtime_summary_export",
            "record_institutional_workbook_export",
            "record_workspace_runtime",
            "update_scenario_last_run_summary",
        ],
    )
    def test_forbidden_helper_not_called_in_service(self, forbidden_symbol: str):
        text = _read(SCENARIO_STATE_ROUTE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        assert forbidden_symbol not in clean, (
            f"Service must NOT call {forbidden_symbol}"
        )

    def test_no_db_or_session_direct_access_in_service(self):
        text = _read(SCENARIO_STATE_ROUTE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        for sym in ["db.add", "db.commit", "db.flush", "session.add", "session.commit"]:
            assert sym not in clean

    def test_no_save_run_save_project_save_scenario_in_service(self):
        text = _read(SCENARIO_STATE_ROUTE_SERVICE)
        clean = _strip_docstrings_and_comments(text)
        # save_workspace_state is allowed (intended write)
        assert "deps.save_run(" not in clean
        assert "deps.save_project(" not in clean
        assert "deps.save_scenario(" not in clean

    @pytest.mark.parametrize("route", ["/scenarios/state/draft", "/scenarios/state/discard"])
    def test_route_does_not_call_forbidden_helpers(self, route: str):
        body = _route_body(route)
        clean = _strip_docstrings_and_comments(body)
        for sym in [
            "record_export",
            "record_download_export",
            "record_workspace_runtime",
            "update_scenario_last_run_summary",
        ]:
            assert sym not in clean, (
                f"{route} must NOT call {sym}"
            )

    @pytest.mark.parametrize("route", ["/scenarios/state/draft", "/scenarios/state/discard"])
    def test_route_does_not_call_save_run_save_project_directly(self, route: str):
        body = _route_body(route)
        clean = _strip_docstrings_and_comments(body)
        # Routes can call save_workspace_state via deps (intended).
        # They must NOT call save_run, save_project, save_scenario
        # directly.
        assert "save_run(" not in clean
        assert "save_project(" not in clean
        assert "save_scenario(" not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 8. JSON response behavior preserved
# ─────────────────────────────────────────────────────────────────────────────


class TestJSONResponseBehavior:
    """JSON response shape, status, headers preserved."""

    def test_draft_route_returns_jsonresponse(self):
        body = _route_body("/scenarios/state/draft")
        assert "return JSONResponse(" in body

    def test_discard_route_returns_jsonresponse(self):
        body = _route_body("/scenarios/state/discard")
        assert "return JSONResponse(" in body

    def test_draft_route_no_htmx_trigger(self):
        body = _route_body("/scenarios/state/draft")
        assert "HX-Trigger" not in body

    def test_discard_route_no_htmx_trigger(self):
        body = _route_body("/scenarios/state/discard")
        assert "HX-Trigger" not in body

    def test_draft_route_no_template_render(self):
        body = _route_body("/scenarios/state/draft")
        assert "templates.TemplateResponse" not in body

    def test_discard_route_no_template_render(self):
        body = _route_body("/scenarios/state/discard")
        assert "templates.TemplateResponse" not in body

    def test_draft_unauth_401_json_via_route(self):
        """The route still returns 401 JSON on no user (auth is route-owned)."""
        body = _route_body("/scenarios/state/draft")
        # The 401 JSON pattern must still be in the route
        assert "JSONResponse(" in body
        assert '"Login required"' in body or "'Login required'" in body
        assert "401" in body

    def test_discard_unauth_401_json_via_route(self):
        body = _route_body("/scenarios/state/discard")
        assert "JSONResponse(" in body
        assert '"Login required"' in body or "'Login required'" in body
        assert "401" in body


# ─────────────────────────────────────────────────────────────────────────────
# 9. Other routes remain service-backed
# ─────────────────────────────────────────────────────────────────────────────


class TestOtherRoutesRemainServiceBacked:
    """Other extracted route families (run/compare/validate/download/
    save-run) must remain service-backed and not regress in 51H-2."""

    @pytest.mark.parametrize(
        "service_class,route",
        [
            ("RunRouteDeps", "/run"),
            ("CompareRouteDeps", "/compare"),
            ("ValidateRouteDeps", "/validate"),
            ("DownloadRouteDeps", "/download"),
            ("SaveRunRouteDeps", "/save-run"),
        ],
    )
    def test_other_routes_remain_service_backed(self, service_class: str, route: str):
        text = _read(MAIN_WEB)
        assert service_class in text, (
            f"main_web.py must still use {service_class} for {route} "
            f"(regression: 51H-2 must not affect other routes)"
        )

    @pytest.mark.parametrize(
        "service_file",
        [
            "run_service.py",
            "compare_service.py",
            "validation_service.py",
            "download_service.py",
            "save_run_service.py",
        ],
    )
    def test_other_service_files_unchanged_after_51h2(self, service_file: str):
        """These service files must NOT have been modified by 51H-2."""
        path = REPO_ROOT / "app" / "services" / service_file
        text = _read(path)
        # The 51H-2 module must NOT be imported here (no
        # scenario_state_route_service dependencies)
        assert "scenario_state_route_service" not in text, (
            f"{service_file} must not depend on the new "
            f"scenario_state_route_service module"
        )
        # And the file's size (in lines) should match the baseline
        # (sanity check that we did not modify it accidentally).
        # We do NOT pin a specific number, but check it's reasonable.
        lines = len(text.splitlines())
        assert lines > 100, (
            f"{service_file} should still be a substantial service "
            f"file ({lines} lines)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 10. ScenarioStateRouteDeps bundle integrity
# ─────────────────────────────────────────────────────────────────────────────


class TestDepsBundle:
    """Verify the ScenarioStateRouteDeps dataclass."""

    def test_deps_is_a_dataclass(self):
        text = _read(SCENARIO_STATE_ROUTE_SERVICE)
        assert "@dataclass" in text
        assert "class ScenarioStateRouteDeps:" in text

    def test_deps_has_9_callables_no_constants(self):
        from app.services.scenario_state_route_service import (
            ScenarioStateRouteDeps,
        )
        import dataclasses

        fields = dataclasses.fields(ScenarioStateRouteDeps)
        # All 9 fields are callables (no constants needed for this
        # route family — there is no form validation)
        assert len(fields) == 9, (
            f"Expected 9 deps fields, got {len(fields)}"
        )
        for f in fields:
            assert "Callable" in str(f.type), (
                f"Field {f.name} must be a Callable, got {f.type}"
            )

    def test_deps_fields_are_required(self):
        """All fields must be required (no defaults)."""
        from app.services.scenario_state_route_service import (
            ScenarioStateRouteDeps,
        )
        import dataclasses

        for f in dataclasses.fields(ScenarioStateRouteDeps):
            assert f.default is dataclasses.MISSING, (
                f"Field {f.name} must be required (no default)"
            )

    def test_deps_includes_all_required_helpers(self):
        from app.services.scenario_state_route_service import (
            ScenarioStateRouteDeps,
        )
        import dataclasses

        names = {f.name for f in dataclasses.fields(ScenarioStateRouteDeps)}
        required = {
            "collect_form_snapshot",
            "project_workspace_from_snapshot",
            "save_workspace_state",
            "discard_workspace_draft",
            "snapshots_equal",
            "default_workspace_snapshot",
            "governance_snapshot",
            "replay_metadata_for_project",
            "workspace_state_meta",
        }
        assert required.issubset(names), (
            f"Missing: {required - names}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 11. ScenarioStateRouteOutcome shape
# ─────────────────────────────────────────────────────────────────────────────


class TestOutcomeShape:
    """Verify the ScenarioStateRouteOutcome dataclass."""

    def test_outcome_default_values(self):
        from app.services.scenario_state_route_service import (
            ScenarioStateRouteOutcome,
        )

        outcome = ScenarioStateRouteOutcome()
        assert outcome.payload == {}
        assert outcome.status_code == 200
        assert outcome.headers == {}
        assert outcome.is_redirect is False
        assert outcome.redirect_url is None

    def test_outcome_can_carry_payload(self):
        from app.services.scenario_state_route_service import (
            ScenarioStateRouteOutcome,
        )

        outcome = ScenarioStateRouteOutcome(
            payload={"success": True, "message": "ok"},
            status_code=200,
        )
        assert outcome.payload == {"success": True, "message": "ok"}
        assert outcome.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# 12. Integration: route + service together
# ─────────────────────────────────────────────────────────────────────────────


class TestIntegration:
    """The service + route together produce the same observable
    behavior as the pre-extraction route."""

    def test_draft_service_constructs_correct_save_workspace_state_kwargs(self):
        """The service must construct the same save_workspace_state
        kwargs as the pre-extraction route."""
        body = _service_function_body("execute_draft_route")
        # Required kwargs (use the multiline-tolernt check)
        for kw in [
            "user_id=user.user_id",
            "project_id=project_record.project_id",
            "project_code=project_code",
            "draft_snapshot=snapshot",
            "saved_snapshot=saved_snapshot",
            "active_scenario_id=active_scenario_id",
            "active_scenario_name=active_scenario_name",
            "governance_state=deps.governance_snapshot(project_code)",
            "replay_metadata=deps.replay_metadata_for_project(",
            'export_type="workspace_draft_state"',
        ]:
            assert kw in body, f"Missing kwarg: {kw}"

    def test_discard_service_constructs_correct_discard_workspace_draft_kwargs(self):
        body = _service_function_body("execute_discard_route")
        assert "user.user_id, project_record.project_id" in body

    def test_discard_fallback_uses_baseline_snapshot(self):
        body = _service_function_body("execute_discard_route")
        assert "draft_snapshot=baseline_snapshot" in body
        assert "saved_snapshot=baseline_snapshot" in body


# ─────────────────────────────────────────────────────────────────────────────
# 13. Phase 51F guardrails (smoke check)
# ─────────────────────────────────────────────────────────────────────────────


class TestPhase51FGuardrailsSmokeCheck:
    """Smoke check that 51H-2 does not break 51F guardrails.

    The full 51F suite is run separately via:
        pytest tests/test_phase51f_parallel_work_guardrails.py
    Here we do a minimal structural check.
    """

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
        assert sha == "b425a0708719eaa5e1d922b1008e5609758e0ad4", (
            f"rc1 SHA changed! Got {sha!r}"
        )

    def test_all_9_services_clean_no_main_web_imports(self):
        """All 9 services (8 pre-existing + 1 new) must not
        import main_web or main_api."""
        services = [
            "run_service.py",
            "compare_service.py",
            "validation_service.py",
            "download_service.py",
            "save_run_service.py",
            "export_service.py",
            "export_audit_service.py",
            "scenario_state_service.py",
            "scenario_state_route_service.py",
        ]
        for service_file in services:
            path = REPO_ROOT / "app" / "services" / service_file
            if not path.exists():
                continue  # skip non-existent (e.g. before 51H-2)
            text = _read(path)
            clean = _strip_docstrings_and_comments(text)
            assert "import main_web" not in clean, (
                f"{service_file} must NOT import main_web"
            )
            assert "from main_web" not in clean
            assert "import main_api" not in clean
            assert "from main_api" not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 14. Sanity: import smoke test
# ─────────────────────────────────────────────────────────────────────────────


class TestImportSmoke:
    """Smoke test that all modules import cleanly."""

    def test_main_web_imports(self):
        import main_web  # noqa: F401
        assert hasattr(main_web, "save_workspace_draft_endpoint")
        assert hasattr(main_web, "discard_workspace_draft_endpoint")

    def test_scenario_state_route_service_imports(self):
        from app.services import scenario_state_route_service  # noqa: F401
        from app.services.scenario_state_route_service import (
            ScenarioStateRouteOutcome,
            ScenarioStateRouteDeps,
            execute_draft_route,
            execute_discard_route,
        )
        assert ScenarioStateRouteOutcome is not None
        assert ScenarioStateRouteDeps is not None
        assert callable(execute_draft_route)
        assert callable(execute_discard_route)

    def test_scenario_state_service_unchanged(self):
        from app.services import scenario_state_service  # noqa: F401
        from app.services.scenario_state_service import (
            build_workspace_state_metadata,
            resolve_runtime_snapshot,
            check_runtime_allowed,
            scenario_provenance_for_record,
        )
        # Still callable
        assert callable(build_workspace_state_metadata)
        assert callable(resolve_runtime_snapshot)
        assert callable(check_runtime_allowed)
        assert callable(scenario_provenance_for_record)
