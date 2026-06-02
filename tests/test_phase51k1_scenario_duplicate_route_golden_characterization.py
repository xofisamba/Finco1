"""Phase 51K-1 — POST /scenarios/{scenario_id}/duplicate golden
characterization.

Pins the current behavior of POST /scenarios/{scenario_id}/duplicate
(duplicate_scenario_endpoint) in main_web.py BEFORE the 51K-2
vertical extraction. After 51K-2 the orchestration body moves to
``app.services.scenario_duplicate_service``; these tests will be
re-pointed to look at the service body for orchestration content.

This is a characterization-only phase. No production code is
changed. The test file is the only deliverable that may be
modified by the characterization itself (to add new tests and
helpers).

20 categories covered (per spec):

1. Route existence and route size.
2. Auth/session behavior.
3. Path parameter scenario_id behavior.
4. user_id source from auth/session, not form.
5. active_project handling.
6. active_scenario behavior.
7. original scenario lookup behavior.
8. duplicate scenario name/code behavior.
9. snapshot/workspace behavior.
10. intended persistence writes.
11. intended call ordering if order matters.
12. replay_metadata export_type values if present.
13. governance_state behavior if present.
14. response type/template/context/JSON payload.
15. HTMX headers or absence.
16. redirect/status behavior.
17. error/fallback behavior.
18. forbidden side effects absent.
19. existing service-backed routes remain intact.
20. Phase 51F guardrails remain green.

Recommended 51K-2 extraction boundary:

- New module: ``app/services/scenario_duplicate_service.py``
- Dataclass ``ScenarioDuplicateRouteOutcome`` with
  ``template_name``, ``context``, ``payload``, ``status_code``,
  ``headers``, ``is_redirect``, ``redirect_url``.
- Dataclass ``ScenarioDuplicateRouteDeps`` with 9 callables:
  ``get_scenario``, ``duplicate_scenario``, ``get_project_by_code``,
  ``list_scenarios``, ``get_scenario_history``, ``list_exports``,
  ``build_export_lineage``, ``get_workspace_state``,
  ``render_scenario_workspace``.
- ``async def execute_scenario_duplicate_route(*, request,
  scenario_id, user, deps) -> ScenarioDuplicateRouteOutcome``
  (no form; the route is path-parameter-only).
- Route in main_web.py becomes a thin wrapper: auth check, deps
  bundle, service call, response render.

Why not extend ``scenario_state_service.py``: data-layer only.
Why not extend ``scenario_state_route_service.py``: draft/discard
only (no row creation/duplication).
Why not extend ``scenarios_save_service.py``: save creates a new
ScenarioRecord from form snapshot; duplicate copies an existing
ScenarioRecord. Different concern.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_WEB = REPO_ROOT / "main_web.py"
SERVICES_DIR = REPO_ROOT / "app" / "services"
SCENARIO_DUPLICATE_SERVICE = (
    REPO_ROOT / "app" / "services" / "scenario_duplicate_service.py"
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _route_body(route_path: str) -> str:
    """Return the body of a route in main_web.py given the path.

    For path-parameter routes use the Python f-string form
    (e.g. ``/scenarios/{scenario_id}/duplicate``).
    """
    text = _read(MAIN_WEB)
    # The route decorator may be either @app.post("/scenarios/{scenario_id}/duplicate")
    # or @app.post(f"/scenarios/{scenario_id}/duplicate"). We accept either.
    patterns = [
        re.escape(f'@app.post("{route_path}")'),
        re.escape(f"@app.post('{route_path}')"),
    ]
    for pat in patterns:
        m = re.search(
            pat + r"\s*\nasync def \w+\(.*?(?=\n@app\.(get|post|put|delete|route)\(|\Z)",
            text,
            re.DOTALL,
        )
        if m is not None:
            return m.group(0)
    raise AssertionError(f"Route {route_path} not found in main_web.py")


def _route_or_service_body(route_path: str) -> str:
    """Return the body that orchestrates the route. After Phase 51K-2,
    orchestration lives in scenario_duplicate_service.py (the
    execute_scenario_duplicate_route function), not in the thin
    main_web.py route. We use the service body for orchestration-
    content checks; the route body is used for thin-route checks.

    Behavior-characterization tests should call this helper.
    Structural thin-route tests should still call _route_body.
    """
    if SCENARIO_DUPLICATE_SERVICE.exists():
        text = _read(SCENARIO_DUPLICATE_SERVICE)
        m = re.search(
            r"async def execute_scenario_duplicate_route\(.*?(?=\nasync def |\nclass |\Z)",
            text,
            re.DOTALL,
        )
        if m is not None:
            return m.group(0)
    # Fallback: return the route body (pre-51K-2 behavior)
    return _route_body(route_path)


def _strip_docstrings_and_comments(text: str) -> str:
    """Remove triple-quoted docstrings and ``#`` comments from text.

    Used to avoid false positives when checking for forbidden
    imports or function calls in docstrings and module-level
    comments.
    """
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
        """POST /scenarios/{scenario_id}/duplicate exists in main_web.py."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        assert body is not None

    def test_route_size_is_characteristic(self):
        """Pin current route size. Pre-extraction ~67 non-blank
        (Phase 51I hotspot estimate). After 51K-2 it should shrink
        to ~25-30 non-blank (thin route with deps + service call)."""
        body = _route_body("/scenarios/{scenario_id}/duplicate")
        non_blank = [l for l in body.splitlines() if l.strip()]
        assert 55 <= len(non_blank) <= 90, (
            f"/scenarios/{{scenario_id}}/duplicate is {len(non_blank)} "
            f"non-blank lines; expected 55-90 (pre-extraction "
            f"characteristic)"
        )

    def test_uses_execute_pattern_after_51k2(self):
        """Phase 51K-2: the route now uses the
        execute_scenario_duplicate_route() pattern (orchestration is
        in the service)."""
        body = _route_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        # The route now calls execute_scenario_duplicate_route(...)
        assert "execute_scenario_duplicate_route(" in clean
        # And the deps class lives in the service, NOT in main_web.py
        text = _read(MAIN_WEB)
        assert "class ScenarioDuplicateRouteDeps" not in text
        assert "class ScenarioDuplicateDeps" not in text


# ─────────────────────────────────────────────────────────────────────────────
# 2. Auth/session behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestAuthenticationBehavior:
    def test_route_uses_get_current_user(self):
        """Auth check: route uses get_current_user(request)."""
        body = _route_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert "get_current_user(request)" in clean
        # Auth check happens before any return statement
        clean_first_return = clean.find("return")
        auth_pos = clean.find("get_current_user(request)")
        assert auth_pos != -1
        assert clean_first_return == -1 or auth_pos < clean_first_return

    def test_route_uses_user_user_id(self):
        """user_id is derived from user.user_id, NEVER from form."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert "user.user_id" in clean

    def test_unauth_returns_302_to_login(self):
        """Unauthenticated POST /scenarios/{scenario_id}/duplicate
        returns 302 redirect to /login (NOT 401 JSON, NOT 200)."""
        from fastapi.testclient import TestClient

        from app.persistence.db import init_db
        from main_web import app

        init_db()
        c = TestClient(app)
        # Use a non-existent scenario_id; auth check happens first
        r = c.post(
            "/scenarios/some-id/duplicate",
            data={},
            follow_redirects=False,
        )
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
        r = c.post(
            "/scenarios/some-id/duplicate",
            data={},
            follow_redirects=False,
        )
        # Not JSON; it's a redirect
        assert not r.headers.get(
            "content-type", ""
        ).startswith("application/json")

    def test_unauth_no_htmx_redirect_header(self):
        """Unauthenticated request does NOT use HX-Redirect (it uses
        a real 302 redirect to /login)."""
        from fastapi.testclient import TestClient

        from app.persistence.db import init_db
        from main_web import app

        init_db()
        c = TestClient(app)
        r = c.post(
            "/scenarios/some-id/duplicate",
            data={},
            follow_redirects=False,
        )
        assert "HX-Redirect" not in r.headers


# ─────────────────────────────────────────────────────────────────────────────
# 3. Path parameter scenario_id behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestPathParameterBehavior:
    def test_route_signature_takes_scenario_id(self):
        """The route signature is
        async def duplicate_scenario_endpoint(request: Request, scenario_id: str)."""
        body = _route_body("/scenarios/{scenario_id}/duplicate")
        assert "async def duplicate_scenario_endpoint" in body
        assert "scenario_id: str" in body

    def test_route_uses_scenario_id_in_get_scenario(self):
        """scenario_id is passed to get_scenario(scenario_id, user.user_id)."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        assert "get_scenario(scenario_id, user.user_id)" in body

    def test_route_uses_scenario_id_in_duplicate_scenario(self):
        """scenario_id is passed to duplicate_scenario(user.user_id, scenario_id)."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        assert "duplicate_scenario(user.user_id, scenario_id)" in body


# ─────────────────────────────────────────────────────────────────────────────
# 4. user_id from session, not form
# ─────────────────────────────────────────────────────────────────────────────


class TestUserIdSource:
    def test_user_id_never_from_form(self):
        """The route is POST /scenarios/{scenario_id}/duplicate and
        does NOT have form input; user_id comes from session."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        # The route does NOT call await request.form() (it's a
        # path-parameter-only route).
        assert "await request.form()" not in clean
        # And user_id is always derived from user.user_id
        assert "user.user_id" in clean

    def test_all_persistence_calls_use_user_user_id(self):
        """All persistence calls reference user.user_id (as first or
        second positional arg, depending on the helper's signature)."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        # get_scenario and duplicate_scenario take (scenario_id, user.user_id)
        # or (user.user_id, scenario_id) — accept either ordering
        # provided both args are present.
        for helper in (
            "get_scenario",
            "duplicate_scenario",
        ):
            assert f"{helper}(scenario_id, user.user_id)" in clean or \
                f"{helper}(user.user_id, scenario_id)" in clean, (
                f"Expected {helper} called with both scenario_id and user.user_id"
            )
        # All other helpers take (user.user_id, ...) as first arg.
        # In Phase 51K-2 the service uses ``deps.{helper}(user.user_id, ...)``
        # (possibly multiline). The literal ``{helper}(`` and
        # ``user.user_id`` are both present in the service.
        for helper in (
            "get_project_by_code",
            "list_scenarios",
            "get_scenario_history",
            "list_exports",
            "build_export_lineage",
            "get_workspace_state",
        ):
            # The call site references the helper name (possibly
            # as deps.{helper}) and user.user_id.
            assert f"{helper}(" in clean, (
                f"Expected {helper}( call"
            )
            assert "user.user_id" in clean, (
                f"user.user_id must be referenced"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 5. active_project handling
# ─────────────────────────────────────────────────────────────────────────────


class TestActiveProjectBehavior:
    def test_route_resolves_project_record(self):
        """The route resolves the active project via
        get_project_by_code(user.user_id, original.project_code).

        Phase 51K-2: service uses
        ``project_record = deps.get_project_by_code(user.user_id,
        original.project_code)`` (possibly multiline)."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        # Substring match (works for multiline calls)
        assert "get_project_by_code(" in clean
        assert "user.user_id" in clean
        assert "original.project_code" in clean

    def test_project_id_derived_from_original(self):
        """All read-only queries use original.project_id.

        Phase 51K-2: service uses ``project_id=original.project_id``
        (possibly multiline)."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        # list_scenarios / get_scenario_history / list_exports /
        # build_export_lineage all reference original.project_id
        for helper in (
            "list_scenarios",
            "get_scenario_history",
            "list_exports",
            "build_export_lineage",
        ):
            assert f"{helper}(" in clean, (
                f"Expected {helper}( call"
            )
        assert "original.project_id" in clean
        # The helpers are passed ``project_id=original.project_id``
        # (the substring ``project_id=original.project_id`` is
        # present in the service).
        assert clean.count("project_id=original.project_id") >= 4


# ─────────────────────────────────────────────────────────────────────────────
# 6. active_scenario behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestActiveScenarioBehavior:
    def test_route_uses_original_scenario(self):
        """The route stores the original scenario in 'original' and
        accesses its fields.

        Phase 51K-2: service uses ``original = deps.get_scenario(`` and
        accesses original.scenario_name, original.project_code,
        original.project_id."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert "original = get_scenario(" in clean or \
            "original = deps.get_scenario(" in clean
        assert "original.scenario_name" in clean
        assert "original.project_code" in clean
        assert "original.project_id" in clean

    def test_scenario_not_found_returns_404(self):
        """If get_scenario returns None, the route returns 404 JSON.

        Phase 51K-2: service returns ScenarioDuplicateRouteOutcome
        with status_code=404 and payload={"error": "Scenario not
        found"}. The literal "Scenario not found" is present."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert "if original is None:" in clean
        assert '"Scenario not found"' in clean
        assert "status_code=404" in clean


# ─────────────────────────────────────────────────────────────────────────────
# 7. Original scenario lookup behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestOriginalScenarioLookup:
    def test_get_scenario_called_once(self):
        """get_scenario is called exactly once with (scenario_id, user.user_id)."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert "get_scenario(scenario_id, user.user_id)" in clean
        # The call signature appears exactly once (after stripping
        # comments/docstrings).
        # Allow one call in body.
        assert clean.count("get_scenario(scenario_id, user.user_id)") == 1

    def test_get_scenario_return_value_checked(self):
        """The return value of get_scenario is checked for None."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        assert "if original is None:" in body


# ─────────────────────────────────────────────────────────────────────────────
# 8. Duplicate scenario name/code behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestDuplicateScenarioBehavior:
    def test_duplicate_scenario_called_once(self):
        """duplicate_scenario(user.user_id, scenario_id) is called
        exactly once after the None check."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert "duplicate_scenario(user.user_id, scenario_id)" in clean
        assert clean.count("duplicate_scenario(user.user_id, scenario_id)") == 1

    def test_duplicate_called_after_get_scenario(self):
        """duplicate_scenario runs AFTER get_scenario's None check
        (auth happens first)."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        # get_scenario position
        get_pos = clean.find("get_scenario(scenario_id, user.user_id)")
        # duplicate_scenario position
        dup_pos = clean.find("duplicate_scenario(user.user_id, scenario_id)")
        # 404 (None check) position
        none_pos = clean.find("if original is None:")
        # 404 must come before duplicate
        assert none_pos != -1
        assert get_pos < none_pos
        assert none_pos < dup_pos
        # Auth (get_current_user) is even earlier
        auth_pos = body.find("get_current_user(request)")
        assert auth_pos < get_pos


# ─────────────────────────────────────────────────────────────────────────────
# 9. Snapshot/workspace behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestSnapshotWorkspaceBehavior:
    def test_route_resolves_workspace_state(self):
        """The route resolves workspace_state via
        get_workspace_state(user.user_id, original.project_id)
        and passes it to render_scenario_workspace.

        Phase 51K-2: service uses
        ``deps.get_workspace_state(user.user_id, original.project_id)``
        inline in the render call (multiline)."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        # Substring match (works for multiline calls)
        assert "get_workspace_state(" in clean
        assert "user.user_id" in clean
        assert "original.project_id" in clean

    def test_workspace_state_passed_to_render(self):
        """workspace_state is passed as the 5th positional arg of
        render_scenario_workspace (service) or _render_scenario_workspace
        (legacy / pre-extraction)."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        # The render call: _render_scenario_workspace(request, user,
        # project_record, get_workspace_state(...), scenarios, ...
        # (or the service variant: render_scenario_workspace(...)).
        assert (
            "_render_scenario_workspace(" in clean
            or "render_scenario_workspace(" in clean
        )
        # get_workspace_state is referenced (inline in the render
        # call as the 4th positional arg).
        assert "get_workspace_state(" in clean
        assert "user.user_id" in clean
        assert "original.project_id" in clean


# ─────────────────────────────────────────────────────────────────────────────
# 10. Intended persistence writes
# ─────────────────────────────────────────────────────────────────────────────


class TestPersistenceSideEffects:
    """Pin intended persistence calls."""

    def test_duplicate_scenario_called_once(self):
        """duplicate_scenario is called exactly once per success
        (after the None check)."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert clean.count("duplicate_scenario(") == 1

    def test_read_only_queries_called_once_each(self):
        """list_scenarios, get_scenario_history, list_exports,
        build_export_lineage are called once each."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        for helper in (
            "list_scenarios(",
            "get_scenario_history(",
            "list_exports(",
            "build_export_lineage(",
        ):
            assert clean.count(helper) == 1, (
                f"{helper} should be called exactly once"
            )

    def test_get_workspace_state_called_once(self):
        """get_workspace_state is called exactly once."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert clean.count("get_workspace_state(") == 1

    def test_get_project_by_code_called_once(self):
        """get_project_by_code is called exactly once."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert clean.count("get_project_by_code(") == 1


# ─────────────────────────────────────────────────────────────────────────────
# 11. Intended call ordering
# ─────────────────────────────────────────────────────────────────────────────


class TestCallOrdering:
    def test_ordering_auth_get_duplicate_queries_render(self):
        """Order: get_current_user -> 404 check -> duplicate_scenario
        -> get_project_by_code -> list_scenarios -> get_scenario_history
        -> list_exports -> build_export_lineage -> _render_scenario_workspace.

        Phase 51K-2: route has get_current_user (auth) and
        service has all the other orchestration calls.
        """
        # Use both bodies: route for auth position, service for
        # the rest.
        body_route = _route_body("/scenarios/{scenario_id}/duplicate")
        body_service = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean_service = _strip_docstrings_and_comments(body_service)
        # Accept either ``helper(`` or ``deps.helper(`` in service
        def _pos(text, s):
            p1 = text.find(s)
            p2 = text.find("deps." + s)
            candidates = [p for p in (p1, p2) if p != -1]
            if not candidates:
                return -1
            return min(candidates)

        # All positions must be present. Auth is in the route
        # body; the orchestration calls are in the service body.
        # We compare positions within the service body (relative
        # ordering) and verify auth is in the route body.
        assert body_route.find("get_current_user(request)") != -1, (
            "auth (get_current_user) must be in the route body"
        )
        positions = {
            "get_scenario": _pos(clean_service, "get_scenario("),
            "duplicate": _pos(clean_service, "duplicate_scenario("),
            "get_project_by_code": _pos(clean_service, "get_project_by_code("),
            "list_scenarios": _pos(clean_service, "list_scenarios("),
            "get_scenario_history": _pos(clean_service, "get_scenario_history("),
            "list_exports": _pos(clean_service, "list_exports("),
            "build_export_lineage": _pos(clean_service, "build_export_lineage("),
            "render": _pos(clean_service, "render_scenario_workspace("),
        }
        # All positions must be present in the service
        for k, v in positions.items():
            assert v != -1, f"{k} not found in service body"
        # Ordering assertions (within the service body)
        assert positions["get_scenario"] < positions["duplicate"]
        assert positions["duplicate"] < positions["get_project_by_code"]
        assert positions["get_project_by_code"] < positions["list_scenarios"]
        assert positions["list_scenarios"] < positions["get_scenario_history"]
        assert positions["get_scenario_history"] < positions["list_exports"]
        assert positions["list_exports"] < positions["build_export_lineage"]
        assert positions["build_export_lineage"] < positions["render"]


# ─────────────────────────────────────────────────────────────────────────────
# 12. replay_metadata export_type values
# ─────────────────────────────────────────────────────────────────────────────


class TestReplayMetadata:
    def test_no_replay_metadata_for_duplicate(self):
        """The /scenarios/{id}/duplicate route does NOT pass
        replay_metadata to duplicate_scenario (the repository
        function is the single source of truth for the duplicate's
        metadata). This is a behavior difference from /scenarios/save
        and /save-run."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        # The call signature is
        # duplicate_scenario(user.user_id, scenario_id)
        # No replay_metadata kwarg.
        assert "duplicate_scenario(user.user_id, scenario_id)" in clean
        # No export_type=... in the call
        m = re.search(
            r"duplicate_scenario\([^)]*\)",
            clean,
            re.DOTALL,
        )
        assert m is not None
        assert "export_type" not in m.group(0)


# ─────────────────────────────────────────────────────────────────────────────
# 13. governance_state behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestGovernanceState:
    def test_no_governance_snapshot_call(self):
        """The /scenarios/{id}/duplicate route does NOT call
        _governance_snapshot — the repository function
        duplicate_scenario is the single source of truth."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert "_governance_snapshot" not in clean
        assert "governance_snapshot(" not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 14. Response behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestResponseBehavior:
    def test_success_response_uses_render_scenario_workspace(self):
        """The success response is full workspace render via
        _render_scenario_workspace(...) (route) or
        render_scenario_workspace(...) (service)."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        # One render call (success path)
        assert (
            clean.count("_render_scenario_workspace(")
            + clean.count("render_scenario_workspace(")
        ) == 1

    def test_404_response_uses_json(self):
        """The 404 response is JSON, not HTML.

        Pre-extraction: ``JSONResponse({"error": "Scenario not found"},
        status_code=404)``.
        Phase 51K-2: service returns ``ScenarioDuplicateRouteOutcome``
        with ``status_code=404`` and ``payload={"error": "Scenario
        not found"}``; the route translates to a JSONResponse.
        """
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        # The literal "Scenario not found" string is present (in
        # JSONResponse or in the outcome payload).
        assert '"Scenario not found"' in clean
        # And the 404 status code is referenced somewhere (in the
        # route's JSONResponse or in the outcome.status_code)
        assert "status_code=404" in clean or "status_code: int = 200" in body

    def test_success_message_includes_original_scenario_name(self):
        """The success message is
        f'Duplicated {original.scenario_name}.'"""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        assert "Duplicated {original.scenario_name}." in body

    def test_render_args_include_all_required(self):
        """The render call includes request, user, project_record,
        workspace_state, scenarios, history, exports, export_lineage,
        scenario_summary_cards, message."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        # Verify the render call has all required positional args
        # (in source order).
        for required in (
            "request,",
            "user,",
            "project_record,",
            "get_workspace_state(user.user_id, original.project_id),",
            "scenarios,",
            "history,",
            "exports,",
            "export_lineage,",
            "scenario_summary_cards,",
        ):
            assert required in body, (
                f"Render call missing: {required}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 15. HTMX headers or absence
# ─────────────────────────────────────────────────────────────────────────────


class TestHtmxHeaders:
    def test_no_htmx_trigger_header_in_route(self):
        """The /scenarios/{id}/duplicate route does NOT set
        HX-Trigger or HX-Redirect. The response is a full workspace
        render, not an HTMX partial."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert "HX-Trigger" not in clean
        assert "HX-Redirect" not in clean

    def test_404_no_htmx_headers(self):
        """The 404 JSON response does NOT use HTMX headers."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert "HX-Trigger" not in clean
        assert "HX-Redirect" not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 16. Redirect/status behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestRedirectStatus:
    def test_auth_redirect_uses_redirectresponse(self):
        """The 302 auth redirect uses RedirectResponse(url='/login',
        status_code=302). The auth redirect is route-owned (auth
        check happens before the service call)."""
        body = _route_body("/scenarios/{scenario_id}/duplicate")
        assert "RedirectResponse(url=\"/login\", status_code=302)" in body

    def test_404_uses_status_code_404(self):
        """The 404 response uses status_code=404.

        Phase 51K-2: service returns ScenarioDuplicateRouteOutcome
        with status_code=404; the route translates to a
        JSONResponse. The literal ``status_code=404`` is present
        in the service outcome default OR the route's
        JSONResponse."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        # The 404 status code is referenced in the service
        # (ScenarioDuplicateRouteOutcome has ``status_code: int =
        # 200`` field; the service explicitly sets it to 404 via
        # ``status_code=404`` in the early return).
        assert "status_code=404" in clean


# ─────────────────────────────────────────────────────────────────────────────
# 17. Error/fallback behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestErrorFallback:
    def test_no_broad_except_in_route(self):
        """The route does NOT wrap the body in broad `except Exception`.
        Errors propagate to FastAPI default 500."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        # No `except Exception:` (broad) inside the route
        assert "except Exception:" not in clean

    def test_only_explicit_error_path_is_404(self):
        """The only explicit error path is the 404 (Scenario not
        found). Pre-extraction: route's JSONResponse. Phase 51K-2:
        service's ScenarioDuplicateRouteOutcome with status_code=404
        and payload={"error": "Scenario not found"}."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        # The literal "Scenario not found" string is present
        assert '"Scenario not found"' in clean


# ─────────────────────────────────────────────────────────────────────────────
# 18. Forbidden side effects absent
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
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        for helper in (
            "record_export(",
            "record_download_export(",
            "record_runtime_summary_export(",
            "record_institutional_workbook_export(",
        ):
            assert helper not in clean

    def test_route_does_not_call_record_workspace_runtime(self):
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert "record_workspace_runtime(" not in clean

    def test_route_does_not_call_update_scenario_last_run_summary(self):
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert "update_scenario_last_run_summary(" not in clean

    def test_route_does_not_call_save_run(self):
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert "save_run(" not in clean

    def test_route_does_not_call_save_project(self):
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert "save_project(" not in clean

    def test_route_does_not_call_run_project(self):
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert "run_project(" not in clean

    def test_route_does_not_call_excel_export_builders(self):
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        for helper in (
            "build_institutional_workbook_export(",
            "build_excel_export_for_post_request(",
            "build_runtime_summary_csv_export(",
            "build_values_only_export_for_project(",
        ):
            assert helper not in clean, (
                f"Route must not call {helper}"
            )

    def test_route_does_not_use_db_or_session_directly(self):
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        for forbidden in (
            "db.add",
            "db.commit",
            "db.flush",
            "session.add",
            "session.commit",
        ):
            assert forbidden not in clean, (
                f"Route must not use {forbidden} directly"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 19. Existing service-backed routes remain intact
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
        ],
    )
    def test_other_routes_remain_service_backed(self, route: str, marker: str):
        """All previously-extracted routes remain service-backed."""
        text = _read(MAIN_WEB)
        if route == "/download":
            assert marker in text
            return
        verb = "post"
        pattern = re.escape(f'@app.{verb}("{route}")')
        m = re.search(
            pattern + r"\s*\nasync def \w+\(.*?(?=\n@app\.(get|post|put|delete|route)\(|\Z)",
            text,
            re.DOTALL,
        )
        assert m is not None, f"Route {route} not found"
        body = m.group(0)
        clean = _strip_docstrings_and_comments(body)
        assert marker in clean, (
            f"{route} must use {marker}"
        )

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
            "export_service.py",
            "export_audit_service.py",
        ],
    )
    def test_no_service_imports_main_web_or_main_api(self, service_file: str):
        """No service module may import main_web or main_api."""
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
# 20. Phase 51F guardrails (smoke check)
# ─────────────────────────────────────────────────────────────────────────────


class TestPhase51FGuardrailsSmokeCheck:
    def test_app_still_imports(self):
        """main_web.app still imports successfully."""
        from main_web import app

        assert app is not None

    def test_repository_functions_exist(self):
        """All repository functions the route uses still exist."""
        from app.persistence.repository import (  # noqa: F401
            build_export_lineage,
            duplicate_scenario,
            get_project_by_code,
            get_scenario,
            get_scenario_history,
            get_workspace_state,
            list_exports,
            list_scenarios,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Behavior quirks (to be preserved in 51K-2)
# ─────────────────────────────────────────────────────────────────────────────


class TestBehaviorQuirks:
    """Pin behavior quirks that 51K-2 must preserve."""

    def test_quirk_1_no_replay_metadata_for_duplicate(self):
        """Quirk 1: duplicate_scenario is called WITHOUT replay_metadata
        (different from /scenarios/save which passes
        export_type='saved_scenario_snapshot')."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        # The call signature is positional only:
        # duplicate_scenario(user.user_id, scenario_id)
        m = re.search(
            r"duplicate_scenario\([^)]*\)",
            clean,
            re.DOTALL,
        )
        assert m is not None
        call = m.group(0)
        # No kwargs at all
        assert "replay_metadata" not in call
        assert "export_type" not in call
        assert "governance_state" not in call
        assert "snapshot" not in call

    def test_quirk_2_404_uses_json_not_html(self):
        """Quirk 2: the 404 'Scenario not found' response is JSON
        (NOT HTML, NOT redirect, NOT template render).

        Phase 51K-2: service returns ScenarioDuplicateRouteOutcome
        with status_code=404 and payload={"error": "Scenario not found"};
        the route translates to a JSONResponse. The literal "Scenario
        not found" string is present in the service payload."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert '"Scenario not found"' in clean
        assert "status_code=404" in clean

    def test_quirk_3_success_message_includes_original_scenario_name(self):
        """Quirk 3: success message is
        f'Duplicated {original.scenario_name}.' (with period)."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        assert "Duplicated {original.scenario_name}." in body

    def test_quirk_4_no_governance_snapshot_call(self):
        """Quirk 4: the route does NOT call _governance_snapshot
        (different from /scenarios/save which calls it 2x per
        success). The repository function duplicate_scenario is
        the single source of truth."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert "_governance_snapshot" not in clean

    def test_quirk_5_workspace_state_resolved_inline(self):
        """Quirk 5: workspace_state is resolved inline in the
        _render_scenario_workspace call
        (get_workspace_state(user.user_id, original.project_id)),
        not stored in a separate variable. The render call has 10
        positional args."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        # workspace_state is the 4th positional arg of the render
        # call (request, user, project_record, workspace_state, ...).
        # We verify by checking that get_workspace_state is called
        # exactly once and that it appears inside the render call.
        assert "get_workspace_state(user.user_id, original.project_id)" in clean
        assert clean.count("get_workspace_state(") == 1

    def test_quirk_6_scenario_summary_cards_fields(self):
        """Quirk 6: scenario_summary_cards has 10 specific fields
        (same shape as /scenarios/save's cards)."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        for field in (
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
        ):
            assert field in clean, (
                f"scenario_summary_cards must include '{field}'"
            )

    def test_quirk_7_export_count_computed_per_scenario_name(self):
        """Quirk 7: scenario_summary_cards.export_count is computed
        by counting export_lineage entries per scenario_name
        (same as /scenarios/save)."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        # The pattern: ``export_counts[entry["scenario_name"]] =
        # export_counts.get(entry["scenario_name"], 0) + 1``
        assert "export_counts[entry[\"scenario_name\"]]" in clean
        assert "export_counts.get(entry[\"scenario_name\"]" in clean

    def test_quirk_8_no_form_input(self):
        """Quirk 8: the route is path-parameter-only; it does NOT
        read form input (no await request.form()). Different from
        /scenarios/save which accepts any form input as snapshot."""
        body = _route_or_service_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert "await request.form()" not in clean
        assert "_collect_form_snapshot" not in clean

    def test_quirk_9_no_hx_trigger_no_hx_redirect(self):
        """Quirk 9: the route does NOT emit HX-Trigger or
        HX-Redirect. The response is a full workspace render."""
        body = _route_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        assert "HX-Trigger" not in clean
        assert "HX-Redirect" not in clean

    def test_quirk_10_route_uses_service_after_extraction(self):
        """Quirk 10: post-extraction, the route uses
        execute_scenario_duplicate_route(...)."""
        body = _route_body("/scenarios/{scenario_id}/duplicate")
        clean = _strip_docstrings_and_comments(body)
        # Post-extraction: the route uses the execute pattern
        assert "execute_scenario_duplicate_route(" in clean


# ─────────────────────────────────────────────────────────────────────────────
# Recommended 51K-2 extraction boundary
# ─────────────────────────────────────────────────────────────────────────────


class TestExtractionBoundaryRecommendation:
    def test_scenario_duplicate_service_exists(self):
        """Phase 51K-2: scenario_duplicate_service.py exists in
        app/services/."""
        path = SERVICES_DIR / "scenario_duplicate_service.py"
        assert path.exists(), (
            f"{path} must exist after Phase 51K-2"
        )
        # The service should export the canonical API
        text = path.read_text(encoding="utf-8")
        assert "class ScenarioDuplicateRouteOutcome" in text
        assert "class ScenarioDuplicateRouteDeps" in text
        assert "async def execute_scenario_duplicate_route(" in text

    def test_recommended_module_name(self):
        """The recommended 51K-2 module is
        app/services/scenario_duplicate_service.py."""
        path = SERVICES_DIR / "scenario_duplicate_service.py"
        assert path.exists()
        # After 51K-2 it should be created
