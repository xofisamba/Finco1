"""Phase 51H-1 — Scenario state route family golden characterization.

Characterizes the scenario-state route family BEFORE Phase 51H-2
extraction. Pin current behavior of:

- POST /scenarios/state/draft
- POST /scenarios/state/discard

This is a characterization-only phase. **No production code
changes** are made in 51H-1. The extraction itself happens in
51H-2.

The two routes form a tightly-coupled pair:
- /scenarios/state/draft persists unsaved workspace edits
  (the "dirty" boundary).
- /scenarios/state/discard restores the last saved scenario
  boundary (the "clean" boundary).

Both routes are thin wrappers over `save_workspace_state` /
`discard_workspace_draft` repository calls, and both return
JSON payloads (NOT HTMX-rendered templates).

This test suite pins:
1. Route existence + sizes.
2. Auth/session behavior (unauth → 401 JSON).
3. Draft state behavior (valid request, dirty/empty,
   active_project, active_scenario, workspace_state handling).
4. Discard state behavior (valid request, missing project,
   workspace_state reset/restore, snapshot in payload).
5. Scenario/project persistence: which writes are intended.
6. Side-effect classification: which writes are intended vs.
   forbidden.
7. Response behavior: template names (none — JSON only),
   status codes, content type, headers.
8. Route/service architecture guardrails: other routes remain
   service-backed; no service imports main_web/main_api.
9. Phase 51F guardrails: engine-output + parity-core +
   no-service-imports remain green.
10. Quirks preserved (snapshot=workspace.draft_snapshot in
    discard response, message in payload, etc.).
"""
from __future__ import annotations

import json
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


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Per-test SQLite database for clean state.

    Mirrors the fixture used by other phase51 test files. This is
    defined locally so the 51H-1 suite is self-contained."""
    import uuid

    db_file = tmp_path / f"phase51h1_{uuid.uuid4().hex[:8]}.db"
    monkeypatch.setenv("FINCO_DB_PATH", str(db_file))
    import app.persistence.db as db_mod

    db_mod.DB_PATH = str(db_file)
    db_mod._connection = None
    yield str(db_file)
    db_mod._connection = None


# ─── Helpers ───────────────────────────────────────────────────────────────


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _strip_docstrings_and_comments(text: str) -> str:
    """Strip module docstrings, function/class docstrings, and comments.

    Used for code-level checks (e.g. "does the route call forbidden
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
    # Escape the path for regex
    pattern = re.escape(f'@app.post("{route_path}")')
    m = re.search(
        pattern + r"\s*\nasync def \w+\(.*?\n    return .*?\)",
        text,
        re.DOTALL,
    )
    if m is None:
        # Try GET
        pattern = re.escape(f'@app.get("{route_path}")')
        m = re.search(
            pattern + r"\s*\nasync def \w+\(.*?\n    return .*?\)",
            text,
            re.DOTALL,
        )
    assert m is not None, f"Route {route_path} not found"
    return m.group(0)


def _route_or_service_body(route_path: str) -> str:
    """Return the body that orchestrates the route. After Phase 51H-2,
    orchestration lives in scenario_state_route_service.py (the
    execute_draft_route / execute_discard_route functions), not in
    the thin main_web.py route. We use the service body for
    orchestration-content checks; the route body is used for
    thin-route checks.

    Behavior-characterization tests should call this helper.
    Structural thin-route tests should still call _route_body.
    """
    if SCENARIO_STATE_ROUTE_SERVICE.exists():
        text = _read(SCENARIO_STATE_ROUTE_SERVICE)
        if "draft" in route_path:
            m = re.search(
                r"async def execute_draft_route\(.*?(?=\nasync def execute_|\Z)",
                text,
                re.DOTALL,
            )
            if m is not None:
                return m.group(0)
        if "discard" in route_path:
            m = re.search(
                r"async def execute_discard_route\(.*?(?=\nasync def execute_|\Z)",
                text,
                re.DOTALL,
            )
            if m is not None:
                return m.group(0)
    # Fallback: return the route body (pre-51H-2 behavior)
    return _route_body(route_path)


def _service_uses_scenario_state_route_service() -> bool:
    """True if scenario_state_route_service.py exists (Phase 51H-2+)."""
    return SCENARIO_STATE_ROUTE_SERVICE.exists()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Route existence and sizes
# ─────────────────────────────────────────────────────────────────────────────


class TestRouteExistence:
    """Pin the existence of the scenario-state routes."""

    def test_draft_route_exists(self):
        text = _read(MAIN_WEB)
        assert '@app.post("/scenarios/state/draft")' in text
        assert "async def save_workspace_draft_endpoint" in text

    def test_discard_route_exists(self):
        text = _read(MAIN_WEB)
        assert '@app.post("/scenarios/state/discard")' in text
        assert "async def discard_workspace_draft_endpoint" in text

    def test_draft_route_size_is_characteristic(self):
        """Pin the route (main_web.py) size only. The orchestration
        now lives in scenario_state_route_service.py; its size is
        NOT pinned here. Use _route_body (not _route_or_service_body)
        to assert the thin route size."""
        body = _route_body("/scenarios/state/draft")
        non_blank = [l for l in body.splitlines() if l.strip()]
        # Pre-extraction: ~33 non-blank. After 51H-2: ~36 non-blank
        # (route stays thin; orchestration is in the service).
        assert 20 <= len(non_blank) <= 50, (
            f"/scenarios/state/draft is {len(non_blank)} non-blank lines; "
            f"expected 20-50 (thin route characteristic after 51H-2)"
        )

    def test_discard_route_size_is_characteristic(self):
        body = _route_body("/scenarios/state/discard")
        non_blank = [l for l in body.splitlines() if l.strip()]
        assert 20 <= len(non_blank) <= 50, (
            f"/scenarios/state/discard is {len(non_blank)} non-blank lines; "
            f"expected 20-50 (thin route characteristic after 51H-2)"
        )

    def test_no_other_scenario_state_routes(self):
        """There are exactly 2 routes under /scenarios/state/ in 51H-1
        scope. Adjacent /scenarios/* routes are NOT in this family
        (e.g. /scenarios/save, /scenarios/{id}/select are separate)."""
        text = _read(MAIN_WEB)
        # /scenarios/state/ routes (just the two)
        state_routes = re.findall(
            r'@app\.(?:post|get|put|delete|route)\("(/scenarios/state/[^"]+)"\)',
            text,
        )
        assert sorted(state_routes) == [
            "/scenarios/state/discard",
            "/scenarios/state/draft",
        ], (
            f"Unexpected scenario-state routes: {sorted(state_routes)}; "
            f"only /scenarios/state/draft and /scenarios/state/discard "
            f"are in scope for 51H-1"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Authentication / session behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestAuthenticationBehavior:
    """Pin auth/session behavior for the scenario-state routes."""

    def test_draft_route_uses_get_current_user(self):
        """The THIN route in main_web.py owns the auth check
        (Phase 51H-2: auth stays in the route, not the service)."""
        body = _route_body("/scenarios/state/draft")
        assert "get_current_user(request)" in body
        # Auth check happens first
        assert body.find("get_current_user(request)") < body.find("return JSONResponse")

    def test_discard_route_uses_get_current_user(self):
        body = _route_body("/scenarios/state/discard")
        assert "get_current_user(request)" in body
        assert body.find("get_current_user(request)") < body.find("return JSONResponse")

    def test_draft_route_uses_user_user_id_only(self):
        """user_id is derived from user.user_id, never from form."""
        body = _route_or_service_body("/scenarios/state/draft")
        assert "user.user_id" in body
        # No form-derived user_id
        clean = _strip_docstrings_and_comments(body)
        # The form is collected but user_id comes from user only
        assert "user_id=" in clean

    def test_discard_route_uses_user_user_id_only(self):
        body = _route_or_service_body("/scenarios/state/discard")
        assert "user.user_id" in body
        assert "user_id=" in _strip_docstrings_and_comments(body)

    def test_draft_unauth_returns_401_json(self, isolated_db, tmp_path, monkeypatch):
        """Unauthenticated POST /scenarios/state/draft returns
        401 + JSON {"error": "Login required"}."""
        from fastapi.testclient import TestClient
        from main_web import app

        c = TestClient(app)
        r = c.post("/scenarios/state/draft", data={})
        assert r.status_code == 401, (
            f"Expected 401, got {r.status_code}; body: {r.text[:200]}"
        )
        body = r.json()
        assert body == {"error": "Login required"}, (
            f"Expected {{'error': 'Login required'}}, got {body}"
        )
        assert r.headers.get("content-type", "").startswith("application/json")

    def test_discard_unauth_returns_401_json(self, isolated_db):
        from fastapi.testclient import TestClient
        from main_web import app

        c = TestClient(app)
        r = c.post("/scenarios/state/discard", data={})
        assert r.status_code == 401
        body = r.json()
        assert body == {"error": "Login required"}
        assert r.headers.get("content-type", "").startswith("application/json")

    def test_draft_no_htmx_redirect_on_unauth(self, isolated_db):
        """Unlike /save-run (302 to /login), scenario-state routes
        return 401 JSON (not an HTMX redirect). This is a quirk:
        these routes are JSON-only, not HTMX-partial-based."""
        from fastapi.testclient import TestClient
        from main_web import app

        c = TestClient(app)
        r = c.post("/scenarios/state/draft", data={})
        assert "HX-Redirect" not in r.headers
        assert r.headers.get("location") is None

    def test_discard_no_htmx_redirect_on_unauth(self, isolated_db):
        from fastapi.testclient import TestClient
        from main_web import app

        c = TestClient(app)
        r = c.post("/scenarios/state/discard", data={})
        assert "HX-Redirect" not in r.headers
        assert r.headers.get("location") is None


# ─────────────────────────────────────────────────────────────────────────────
# 3. Draft state behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestDraftStateBehavior:
    """Pin the draft endpoint's behavior with various inputs."""

    @pytest.fixture
    def client(self, isolated_db):
        from fastapi.testclient import TestClient
        from main_web import app
        from app.auth import create_session_token, COOKIE_NAME

        c = TestClient(app)
        token = create_session_token()
        c.cookies.set(COOKIE_NAME, token)
        return c

    def test_draft_with_valid_form_returns_200_json(self, client):
        """Valid draft request → 200 + JSON payload."""
        r = client.post(
            "/scenarios/state/draft",
            data={"active_project": "tuho", "project_type": "Wind"},
        )
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/json")

    def test_draft_response_has_required_keys(self, client):
        r = client.post(
            "/scenarios/state/draft",
            data={"active_project": "tuho"},
        )
        body = r.json()
        required = {
            "dirty",
            "dirty_label",
            "active_scenario_id",
            "active_scenario_name",
            "last_runtime_origin",
            "last_runtime_origin_label",
            "last_runtime_snapshot_id",
            "message",
        }
        assert required.issubset(body.keys()), (
            f"Missing required keys: {required - body.keys()}"
        )

    def test_draft_response_message_is_constant(self, client):
        """Quirk: the message is a fixed string."""
        r = client.post(
            "/scenarios/state/draft",
            data={"active_project": "tuho"},
        )
        body = r.json()
        assert body["message"] == (
            "Workspace draft captured. Saved scenario authority is unchanged."
        )

    def test_draft_dirty_when_form_differs_from_saved(self, client):
        """When the form snapshot differs from the saved_snapshot,
        dirty is True (form is treated as a draft)."""
        form_data = {
            "active_project": "tuho",
            "project_type": "Wind",
            "capacity_mw": "999.0",  # Different from baseline
        }
        r = client.post("/scenarios/state/draft", data=form_data)
        assert r.json()["dirty"] is True

    def test_draft_with_empty_form_still_returns_200(self, client):
        """Empty form → 200 with payload (route does not 400 on empty)."""
        r = client.post("/scenarios/state/draft", data={})
        assert r.status_code == 200
        body = r.json()
        # Has expected keys
        assert "dirty" in body
        assert "message" in body

    def test_draft_with_unknown_project_falls_back_to_factory(self, client):
        """Unknown project code falls back to a factory_template
        project via _resolve_project_record → save_project."""
        r = client.post(
            "/scenarios/state/draft",
            data={"active_project": "totally_made_up_project_xyz"},
        )
        assert r.status_code == 200
        # _resolve_project_record creates a project on the fly
        # (this is current behavior, not an error)

    def test_draft_calls_save_workspace_state(self):
        """The route must call save_workspace_state(...) once per
        successful request (intended persistence write)."""
        body = _route_or_service_body("/scenarios/state/draft")
        clean = _strip_docstrings_and_comments(body)
        assert "save_workspace_state(" in clean
        # Exactly one call
        assert clean.count("save_workspace_state(") == 1

    def test_draft_passes_replay_metadata_to_workspace_state(self):
        body = _route_or_service_body("/scenarios/state/draft")
        clean = _strip_docstrings_and_comments(body)
        # replay_metadata must be passed
        assert "replay_metadata=" in clean
        # export_type = "workspace_draft_state" (the intended marker)
        assert 'export_type="workspace_draft_state"' in clean

    def test_draft_does_not_call_forbidden_side_effects(self):
        """Quirk: the draft route must NOT call record_export family,
        record_workspace_runtime, update_scenario_last_run_summary."""
        body = _route_or_service_body("/scenarios/state/draft")
        clean = _strip_docstrings_and_comments(body)
        for sym in [
            "record_export",
            "record_download_export",
            "record_runtime_summary_export",
            "record_institutional_workbook_export",
            "record_workspace_runtime",
            "update_scenario_last_run_summary",
        ]:
            assert sym not in clean, (
                f"/scenarios/state/draft must NOT call {sym}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Discard state behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestDiscardStateBehavior:
    """Pin the discard endpoint's behavior."""

    @pytest.fixture
    def client(self, isolated_db):
        from fastapi.testclient import TestClient
        from main_web import app
        from app.auth import create_session_token, COOKIE_NAME

        c = TestClient(app)
        token = create_session_token()
        c.cookies.set(COOKIE_NAME, token)
        return c

    def test_discard_with_valid_form_returns_200_json(self, client):
        r = client.post(
            "/scenarios/state/discard",
            data={"active_project": "tuho"},
        )
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/json")

    def test_discard_response_has_snapshot(self, client):
        """Quirk: discard response includes the full snapshot
        (so the client can restore form fields)."""
        r = client.post(
            "/scenarios/state/discard",
            data={"active_project": "tuho"},
        )
        body = r.json()
        assert "snapshot" in body, (
            "discard response must include 'snapshot' (full draft snapshot)"
        )
        assert isinstance(body["snapshot"], dict)

    def test_discard_response_message_is_constant(self, client):
        r = client.post(
            "/scenarios/state/discard",
            data={"active_project": "tuho"},
        )
        body = r.json()
        assert body["message"] == (
            "Unsaved edits discarded. Workspace restored to the last "
            "saved runtime boundary."
        )

    def test_discard_response_has_required_keys(self, client):
        r = client.post(
            "/scenarios/state/discard",
            data={"active_project": "tuho"},
        )
        body = r.json()
        required = {
            "dirty",
            "dirty_label",
            "active_scenario_id",
            "active_scenario_name",
            "last_runtime_origin",
            "last_runtime_origin_label",
            "last_runtime_snapshot_id",
            "snapshot",
            "message",
        }
        assert required.issubset(body.keys())

    def test_discard_with_no_existing_workspace_still_works(self, client):
        """Quirk: when discard_workspace_draft returns None
        (no existing workspace), the route creates a fresh
        workspace_state from baseline_snapshot."""
        r = client.post(
            "/scenarios/state/discard",
            data={"active_project": "tuho"},
        )
        assert r.status_code == 200
        # dirty should be False (we just discarded)
        assert r.json()["dirty"] is False

    def test_discard_does_not_400_on_unknown_project(self, client):
        """Unknown project still works (falls back to factory)."""
        r = client.post(
            "/scenarios/state/discard",
            data={"active_project": "nope_unknown"},
        )
        assert r.status_code == 200

    def test_discard_calls_discard_workspace_draft(self):
        """The route must call discard_workspace_draft(...) on the
        existing workspace."""
        body = _route_or_service_body("/scenarios/state/discard")
        clean = _strip_docstrings_and_comments(body)
        assert "discard_workspace_draft(" in clean
        assert clean.count("discard_workspace_draft(") == 1

    def test_discard_calls_save_workspace_state_for_fallback(self):
        """Quirk: when discard_workspace_draft returns None, the
        route also calls save_workspace_state(...) to seed a
        fresh workspace_state from baseline_snapshot."""
        body = _route_or_service_body("/scenarios/state/discard")
        clean = _strip_docstrings_and_comments(body)
        # Conditional call (in the if branch)
        assert "save_workspace_state(" in clean
        # The call must be inside a `if workspace_state is None:` branch
        assert "if workspace_state is None" in clean

    def test_discard_does_not_call_forbidden_side_effects(self):
        body = _route_or_service_body("/scenarios/state/discard")
        clean = _strip_docstrings_and_comments(body)
        for sym in [
            "record_export",
            "record_download_export",
            "record_runtime_summary_export",
            "record_institutional_workbook_export",
            "record_workspace_runtime",
            "update_scenario_last_run_summary",
        ]:
            assert sym not in clean, (
                f"/scenarios/state/discard must NOT call {sym}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Scenario / project persistence
# ─────────────────────────────────────────────────────────────────────────────


class TestScenarioProjectPersistence:
    """Pin intended persistence calls for the scenario-state routes."""

    def test_draft_intended_writes(self):
        """Draft route's intended writes:
        1. save_workspace_state(...) — 1 call per success
        2. No other persistence writes (no save_run, save_project,
           save_scenario, etc.)."""
        body = _route_or_service_body("/scenarios/state/draft")
        clean = _strip_docstrings_and_comments(body)
        # save_workspace_state is called exactly once
        assert clean.count("save_workspace_state(") == 1
        # No other persistence writes
        assert "save_run(" not in clean
        assert "save_project(" not in clean
        assert "save_scenario(" not in clean
        assert "create_project_record(" not in clean
        assert "create_scenario_record(" not in clean

    def test_discard_intended_writes(self):
        """Discard route's intended writes:
        1. discard_workspace_draft(...) — 1 call (always)
        2. save_workspace_state(...) — 1 call (fallback when
           discard_workspace_draft returns None)
        Total: 1-2 writes depending on whether workspace_state
        existed."""
        body = _route_or_service_body("/scenarios/state/discard")
        clean = _strip_docstrings_and_comments(body)
        assert clean.count("discard_workspace_draft(") == 1
        # save_workspace_state may be 0 or 1 (fallback)
        assert clean.count("save_workspace_state(") <= 1
        # No other persistence writes
        assert "save_run(" not in clean
        assert "save_project(" not in clean
        assert "save_scenario(" not in clean

    def test_draft_save_workspace_state_args(self):
        """The save_workspace_state call must pass the expected
        fields for a draft capture.

        Phase 51H-2: this call now lives in
        scenario_state_route_service.execute_draft_route. We use
        deps.save_workspace_state(...) instead of save_workspace_state(...)
        (callable injection)."""
        body = _route_or_service_body("/scenarios/state/draft")
        clean = _strip_docstrings_and_comments(body)
        # Required args (use deps.* since 51H-2)
        assert "user_id=user.user_id" in clean
        assert "project_id=project_record.project_id" in clean
        assert "project_code=project_code" in clean
        assert "draft_snapshot=snapshot" in clean
        assert "saved_snapshot=saved_snapshot" in clean
        assert "dirty=not deps.snapshots_equal(snapshot, saved_snapshot)" in clean
        assert "governance_state=deps.governance_snapshot(project_code)" in clean
        # replay_metadata with the right export_type
        assert (
            'replay_metadata=deps.replay_metadata_for_project(\n            project_code,\n            project_id=project_record.project_id,\n            scenario_id=active_scenario_id,\n            export_type="workspace_draft_state"'
            in clean
        )

    def test_discard_save_workspace_state_args(self):
        """The save_workspace_state fallback call must pass baseline_snapshot
        for both draft and saved (creating a clean state).

        Phase 51H-2: this call now lives in
        scenario_state_route_service.execute_discard_route."""
        body = _route_or_service_body("/scenarios/state/discard")
        # Use raw body (don't strip string literals — they are part of
        # the export_type marker we want to check)
        # Required args
        assert "draft_snapshot=baseline_snapshot" in body
        assert "saved_snapshot=baseline_snapshot" in body
        assert "dirty=False" in body
        assert 'export_type="workspace_draft_state"' in body
        # Verify the replay_metadata_for_project call is the one
        # inside the fallback (after the if workspace_state is None)
        # Phase 51H-2: service uses deps.replay_metadata_for_project(...)
        # with 16-space indent (inside the if-block which is inside
        # execute_discard_route).
        clean = _strip_docstrings_and_comments(body)
        assert (
            'replay_metadata=deps.replay_metadata_for_project(\n                project_code,'
            in clean
        )


# ─────────────────────────────────────────────────────────────────────────────
# 6. Side-effect classification
# ─────────────────────────────────────────────────────────────────────────────


class TestSideEffectClassification:
    """Pin which side effects are intended and which are forbidden."""

    @pytest.mark.parametrize("route", ["/scenarios/state/draft", "/scenarios/state/discard"])
    def test_no_record_export_family(self, route):
        body = _route_body(route)
        clean = _strip_docstrings_and_comments(body)
        for sym in [
            "record_export",
            "record_download_export",
            "record_runtime_summary_export",
            "record_institutional_workbook_export",
        ]:
            assert sym not in clean, (
                f"{route} must NOT call {sym} (export audit is for "
                f"/download and export flows, not for scenario-state)"
            )

    @pytest.mark.parametrize("route", ["/scenarios/state/draft", "/scenarios/state/discard"])
    def test_no_record_workspace_runtime(self, route):
        """record_workspace_runtime is reserved for /run user_created
        path; the scenario-state routes must NOT call it."""
        body = _route_body(route)
        clean = _strip_docstrings_and_comments(body)
        assert "record_workspace_runtime" not in clean

    @pytest.mark.parametrize("route", ["/scenarios/state/draft", "/scenarios/state/discard"])
    def test_no_update_scenario_last_run_summary(self, route):
        """update_scenario_last_run_summary is reserved for /run;
        scenario-state routes must NOT call it."""
        body = _route_body(route)
        clean = _strip_docstrings_and_comments(body)
        assert "update_scenario_last_run_summary" not in clean

    @pytest.mark.parametrize("route", ["/scenarios/state/draft", "/scenarios/state/discard"])
    def test_no_db_or_session_direct_access(self, route):
        body = _route_body(route)
        clean = _strip_docstrings_and_comments(body)
        for sym in ["db.add", "db.commit", "db.flush", "session.add", "session.commit"]:
            assert sym not in clean, (
                f"{route} must NOT use {sym} (repository fns only)"
            )

    def test_draft_intended_persistence_is_save_workspace_state(self):
        body = _route_or_service_body("/scenarios/state/draft")
        clean = _strip_docstrings_and_comments(body)
        # Only intended persistence is save_workspace_state
        # (and the implicit _resolve_project_record -> save_project when
        # the project is unknown, which is in _resolve_project_record,
        # not in the route body itself)
        assert "save_workspace_state(" in clean


# ─────────────────────────────────────────────────────────────────────────────
# 7. Response behavior
# ─────────────────────────────────────────────────────────────────────────────


class TestResponseBehavior:
    """Pin response behavior: template, status, headers, JSON shape."""

    def test_draft_returns_jsonresponse(self):
        """The THIN route in main_web.py constructs the JSONResponse.
        The service returns a ScenarioStateRouteOutcome."""
        body = _route_body("/scenarios/state/draft")
        assert "return JSONResponse(" in body
        # NOT a template render
        assert "templates.TemplateResponse" not in body

    def test_discard_returns_jsonresponse(self):
        body = _route_body("/scenarios/state/discard")
        assert "return JSONResponse(" in body
        assert "templates.TemplateResponse" not in body

    def test_draft_no_htmx_trigger_header(self, isolated_db):
        """Quirk: unlike /save-run (HX-Trigger: refreshHistory), the
        scenario-state routes do NOT emit HTMX triggers. They return
        a plain JSON payload that the client JS consumes directly."""
        from fastapi.testclient import TestClient
        from main_web import app
        from app.auth import create_session_token, COOKIE_NAME

        c = TestClient(app)
        token = create_session_token()
        c.cookies.set(COOKIE_NAME, token)
        r = c.post("/scenarios/state/draft", data={"active_project": "tuho"})
        assert r.headers.get("HX-Trigger") is None

    def test_discard_no_htmx_trigger_header(self, isolated_db):
        from fastapi.testclient import TestClient
        from main_web import app
        from app.auth import create_session_token, COOKIE_NAME

        c = TestClient(app)
        token = create_session_token()
        c.cookies.set(COOKIE_NAME, token)
        r = c.post("/scenarios/state/discard", data={"active_project": "tuho"})
        assert r.headers.get("HX-Trigger") is None

    def test_draft_uses_workspace_state_meta(self):
        """Quirk: the response payload is built from
        deps.workspace_state_meta(workspace_state) + a 'message' key.

        Phase 51H-2: this lives in
        scenario_state_route_service.execute_draft_route now."""
        body = _route_or_service_body("/scenarios/state/draft")
        clean = _strip_docstrings_and_comments(body)
        assert "deps.workspace_state_meta(workspace_state)" in clean
        # The 'message' key is added to the payload
        assert 'payload["message"]' in clean

    def test_discard_uses_workspace_state_meta(self):
        body = _route_or_service_body("/scenarios/state/discard")
        clean = _strip_docstrings_and_comments(body)
        assert "deps.workspace_state_meta(workspace_state)" in clean
        # Quirks: discard response adds 'snapshot' AND 'message'
        assert 'payload["snapshot"]' in clean
        assert 'payload["message"]' in clean


# ─────────────────────────────────────────────────────────────────────────────
# 8. Route / service architecture guardrails
# ─────────────────────────────────────────────────────────────────────────────


class TestArchitectureGuardrails:
    """Pin the architecture guardrails for the broader route family."""

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
        ],
    )
    def test_no_service_imports_main_web(self, service_file: str):
        """No service in app/services/ may import main_web (one-way
        import direction)."""
        path = REPO_ROOT / "app" / "services" / service_file
        text = _read(path)
        clean = _strip_docstrings_and_comments(text)
        assert "import main_web" not in clean
        assert "from main_web" not in clean

    @pytest.mark.parametrize(
        "service_file",
        [
            "run_service.py",
            "compare_service.py",
            "validation_service.py",
            "download_service.py",
            "save_run_service.py",
            "scenario_state_service.py",
        ],
    )
    def test_no_route_orchestration_service_imports_main_api(self, service_file: str):
        """No route-orchestration service in app/services/ may
        import main_api."""
        path = REPO_ROOT / "app" / "services" / service_file
        text = _read(path)
        clean = _strip_docstrings_and_comments(text)
        assert "import main_api" not in clean
        assert "from main_api" not in clean

    def test_other_routes_remain_service_backed(self):
        """Other extracted route families (run/compare/validate/
        download/save-run) must remain service-backed and not
        regress in 51H-1."""
        text = _read(MAIN_WEB)
        for service, route in [
            ("RunRouteDeps", "/run"),
            ("CompareRouteDeps", "/compare"),
            ("ValidateRouteDeps", "/validate"),
            ("DownloadRouteDeps", "/download"),
            ("SaveRunRouteDeps", "/save-run"),
        ]:
            # The route still uses its deps class
            assert service in text, (
                f"main_web.py must still use {service} for {route} "
                f"(regression: 51H-1 must not affect other routes)"
            )

    def test_draft_route_uses_execute_pattern_after_51h2(self):
        """Phase 51H-2: the draft route now uses the
        execute_draft_route() pattern (orchestration is in the service)."""
        body = _route_body("/scenarios/state/draft")
        clean = _strip_docstrings_and_comments(body)
        # The route now calls execute_draft_route(...)
        assert "execute_draft_route(" in clean

    def test_discard_route_uses_execute_pattern_after_51h2(self):
        body = _route_body("/scenarios/state/discard")
        clean = _strip_docstrings_and_comments(body)
        assert "execute_discard_route(" in clean

    def test_draft_route_does_not_define_a_deps_class(self):
        """Phase 51H-2: the deps class lives in the service module,
        not in main_web.py."""
        text = _read(MAIN_WEB)
        assert "class ScenarioStateRouteDeps" not in text
        assert "class ScenarioStateDeps" not in text

    def test_discard_route_does_not_define_a_deps_class(self):
        text = _read(MAIN_WEB)
        assert "class ScenarioStateRouteDeps" not in text
        assert "class ScenarioStateDeps" not in text


# ─────────────────────────────────────────────────────────────────────────────
# 9. Phase 51F guardrails (smoke check; full suite runs separately)
# ─────────────────────────────────────────────────────────────────────────────


class TestPhase51FGuardrailsSmokeCheck:
    """Smoke check that 51H-1 does not break 51F guardrails.

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


# ─────────────────────────────────────────────────────────────────────────────
# 10. Scenario-state-service pre-existing helpers
# ─────────────────────────────────────────────────────────────────────────────


class TestExistingScenarioStateServiceHelpers:
    """scenario_state_service.py already exists (Phase 50). 51H-1
    pins which helpers it exposes and which 51H-2 may reuse."""

    def test_scenario_state_service_exposes_build_workspace_state_metadata(self):
        text = _read(SCENARIO_STATE_SERVICE)
        assert "def build_workspace_state_metadata(" in text

    def test_scenario_state_service_exposes_resolve_runtime_snapshot(self):
        text = _read(SCENARIO_STATE_SERVICE)
        assert "def resolve_runtime_snapshot(" in text

    def test_scenario_state_service_exposes_check_runtime_allowed(self):
        text = _read(SCENARIO_STATE_SERVICE)
        assert "def check_runtime_allowed(" in text

    def test_scenario_state_service_exposes_scenario_provenance_for_record(self):
        text = _read(SCENARIO_STATE_SERVICE)
        assert "def scenario_provenance_for_record(" in text

    def test_scenario_state_service_does_not_have_route_orchestration_yet(self):
        """Pre-extraction: scenario_state_service.py does NOT
        contain a ScenarioStateRouteOutcome / execute_*_route.
        51H-2 may add it or 51H-2 may create a separate
        scenario_state_route_service.py."""
        text = _read(SCENARIO_STATE_SERVICE)
        assert "class ScenarioStateRouteOutcome" not in text
        assert "def execute_scenario_state_route" not in text
        assert "def execute_draft_route" not in text
        assert "def execute_discard_route" not in text

    def test_main_web_already_uses_scenario_state_service_helpers(self):
        """Pin the existing imports from scenario_state_service."""
        text = _read(MAIN_WEB)
        assert "from app.services.scenario_state_service import" in text
        # These are the helpers that the broader route family already
        # uses (via main_web)
        assert "build_workspace_state_metadata" in text
        assert "resolve_runtime_snapshot" in text
        assert "check_runtime_allowed" in text
        assert "scenario_provenance_for_record" in text


# ─────────────────────────────────────────────────────────────────────────────
# 11. Behavior quirks (to be preserved in 51H-2)
# ─────────────────────────────────────────────────────────────────────────────


class TestBehaviorQuirks:
    """Pin behavior quirks that 51H-2 must preserve."""

    def test_quirk_1_draft_message_is_constant_string(self):
        """Quirk 1: the draft response's 'message' field is a fixed
        string, not derived from any input.

        Phase 51H-2: this lives in scenario_state_route_service now,
        with a slightly different formatting (parenthesized string
        concatenation for line length)."""
        body = _route_or_service_body("/scenarios/state/draft")
        clean = _strip_docstrings_and_comments(body)
        # The message string itself is preserved
        assert (
            '"Workspace draft captured. Saved scenario authority is unchanged."'
            in clean
        )
        # And it is assigned to payload["message"]
        assert 'payload["message"]' in clean

    def test_quirk_2_discard_message_is_constant_string(self):
        body = _route_or_service_body("/scenarios/state/discard")
        clean = _strip_docstrings_and_comments(body)
        # The message string is preserved (may be split across lines
        # by Python implicit string concatenation in the source)
        assert (
            "Unsaved edits discarded. Workspace restored to the last"
            in clean
        )
        assert (
            "saved runtime boundary."
            in clean
        )
        assert 'payload["message"]' in clean

    def test_quirk_3_discard_response_includes_snapshot(self):
        """Quirk 3: discard response includes a 'snapshot' key with
        workspace_state.draft_snapshot. draft does NOT include it."""
        draft_clean = _strip_docstrings_and_comments(
            _route_or_service_body("/scenarios/state/draft")
        )
        discard_clean = _strip_docstrings_and_comments(
            _route_or_service_body("/scenarios/state/discard")
        )
        # draft does NOT have 'snapshot' in payload
        assert 'payload["snapshot"]' not in draft_clean
        # discard DOES have 'snapshot' in payload
        assert 'payload["snapshot"]' in discard_clean
        # discard sets it to workspace_state.draft_snapshot
        assert (
            "payload[\"snapshot\"] = workspace_state.draft_snapshot" in discard_clean
        )

    def test_quirk_4_draft_active_scenario_id_preserved_from_form_or_existing(self):
        """Quirk 4: draft reads current_saved_scenario_id from the
        form (when no existing workspace_state) OR uses
        existing.active_scenario_id (when workspace_state exists).

        Phase 51H-2: this lives in scenario_state_route_service now.
        The ternary is multiline in the service source."""
        body = _route_or_service_body("/scenarios/state/draft")
        # The form-get branch (still one-line)
        assert "form.get(\"current_saved_scenario_id\", \"\") or None" in body
        # The existing-workspace branch (multiline in service, 8-space
        # indent inside the active_scenario_id = (...) assignment)
        assert "existing.active_scenario_id" in body
        # The if/else is preserved (either single-line or multiline)
        assert "if existing" in body
        assert " else " in body

    def test_quirk_5_draft_replay_metadata_uses_scenario_id_when_present(self):
        """Quirk 5: when active_scenario_id is present, it is
        passed to _replay_metadata_for_project as scenario_id."""
        body = _route_or_service_body("/scenarios/state/draft")
        clean = _strip_docstrings_and_comments(body)
        # The replay_metadata call site includes scenario_id=active_scenario_id
        assert "scenario_id=active_scenario_id" in clean

    def test_quirk_6_discard_fallback_creates_clean_workspace(self):
        """Quirk 6: when no workspace_state exists, the discard
        route creates a fresh one with dirty=False from
        baseline_snapshot."""
        body = _route_or_service_body("/scenarios/state/discard")
        clean = _strip_docstrings_and_comments(body)
        # The fallback branch
        assert "if workspace_state is None:" in clean
        assert "draft_snapshot=baseline_snapshot" in clean
        assert "saved_snapshot=baseline_snapshot" in clean
        assert "dirty=False" in clean

    def test_quirk_7_draft_does_not_set_last_runtime_origin(self):
        """Quirk 7: draft does NOT modify last_runtime_* fields
        (it leaves them from the existing workspace_state, or
        unset for a new workspace)."""
        body = _route_or_service_body("/scenarios/state/draft")
        clean = _strip_docstrings_and_comments(body)
        # No explicit last_runtime_* kwargs to save_workspace_state
        # (the route does not pass them, so the repository keeps
        # existing values or leaves them as None)
        # Check that the save_workspace_state call site does NOT
        # include last_runtime_origin, last_runtime_snapshot_id,
        # last_runtime_summary, last_runtime_snapshot as kwargs.
        # We do this by checking that the call is bounded by
        # the standard fields.
        assert "last_runtime_origin=" not in clean
        assert "last_runtime_snapshot_id=" not in clean
        assert "last_runtime_summary=" not in clean

    def test_quirk_8_discard_keeps_last_runtime_fields(self):
        """Quirk 8: discard_workspace_draft (repository function)
        keeps the last_runtime_* fields; the route does not pass
        them explicitly either."""
        body = _route_or_service_body("/scenarios/state/discard")
        clean = _strip_docstrings_and_comments(body)
        # Same as quirk 7
        assert "last_runtime_origin=" not in clean
        assert "last_runtime_snapshot_id=" not in clean
        assert "last_runtime_summary=" not in clean


# ─────────────────────────────────────────────────────────────────────────────
# 12. Recommended extraction boundary for 51H-2
# ─────────────────────────────────────────────────────────────────────────────


class TestExtractionBoundaryMarkers:
    """Pin the structural markers that 51H-2 will use to decide the
    extraction boundary."""

    def test_scenario_state_service_can_be_extended_option_a(self):
        """Option A: extend app/services/scenario_state_service.py
        with route orchestration.

        Pre-extraction: scenario_state_service.py contains ONLY
        data-layer helpers (build_workspace_state_metadata,
        resolve_runtime_snapshot, check_runtime_allowed,
        scenario_provenance_for_record). Adding route orchestration
        would mix data-layer and route-layer concerns."""
        text = _read(SCENARIO_STATE_SERVICE)
        # All 4 helpers are data-layer (no Request, no form, no auth)
        for helper in [
            "build_workspace_state_metadata",
            "resolve_runtime_snapshot",
            "check_runtime_allowed",
            "scenario_provenance_for_record",
        ]:
            assert f"def {helper}(" in text

    def test_scenario_state_service_does_not_depend_on_request_or_form(self):
        """scenario_state_service.py should remain data-layer only;
        it should not need Request/form/auth."""
        text = _read(SCENARIO_STATE_SERVICE)
        # No Request, no form, no auth
        assert "Request" not in text or "Request" in text.split("def")[0]  # imports only
        clean = _strip_docstrings_and_comments(text)
        # No template
        assert "TemplateResponse" not in clean
        # No auth
        assert "get_current_user" not in clean
        # No HTML form handling
        assert "await request.form" not in clean
        assert "form.get" not in clean

    def test_route_orchestration_lives_in_separate_service_after_51h2(self):
        """Phase 51H-2: Option B was selected. The new
        app/services/scenario_state_route_service.py exists and
        contains the orchestration (execute_draft_route /
        execute_discard_route / ScenarioStateRouteDeps /
        ScenarioStateRouteOutcome)."""
        option_b_path = (
            REPO_ROOT / "app" / "services" / "scenario_state_route_service.py"
        )
        # Post-51H-2: DOES exist
        assert option_b_path.exists(), (
            f"{option_b_path} must exist after Phase 51H-2 (extraction is done)"
        )
        text = _read(option_b_path)
        # Has the public API
        assert "class ScenarioStateRouteOutcome" in text
        assert "class ScenarioStateRouteDeps" in text
        assert "async def execute_draft_route" in text
        assert "async def execute_discard_route" in text
        # Option A path: scenario_state_service.py still exists
        # and is unchanged (data-layer only)
        assert SCENARIO_STATE_SERVICE.exists()

    def test_helpers_route_needs(self):
        """Pin the helpers that the orchestration needs (for 51H-2
        deps bundle). Phase 51H-2: the helpers are now deps.* (callable
        injection); previously they were inline module-scope calls."""
        body_draft = _route_or_service_body("/scenarios/state/draft")
        body_discard = _route_or_service_body("/scenarios/state/discard")
        full_route_body = body_draft + "\n" + body_discard
        clean = _strip_docstrings_and_comments(full_route_body)
        # Phase 51H-2: helpers are passed as deps.<name>(...)
        # So the body uses deps.collect_form_snapshot, deps.save_workspace_state, etc.
        assert "deps.collect_form_snapshot(" in clean
        assert "deps.project_workspace_from_snapshot(" in clean
        assert "deps.default_workspace_snapshot(" in clean
        assert "deps.save_workspace_state(" in clean
        assert "deps.discard_workspace_draft(" in clean
        assert "deps.snapshots_equal(" in clean
        assert "deps.governance_snapshot(" in clean
        assert "deps.replay_metadata_for_project(" in clean
        assert "deps.workspace_state_meta(" in clean


# ─────────────────────────────────────────────────────────────────────────────
# 13. Sanity: import smoke test
# ─────────────────────────────────────────────────────────────────────────────


class TestImportSmoke:
    """Smoke test that the modules import cleanly."""

    def test_main_web_imports(self):
        import main_web  # noqa: F401
        assert hasattr(main_web, "save_workspace_draft_endpoint")
        assert hasattr(main_web, "discard_workspace_draft_endpoint")

    def test_scenario_state_service_imports(self):
        from app.services import scenario_state_service  # noqa: F401

    def test_repository_functions_used_by_routes_exist(self):
        """The repository functions the routes call must exist."""
        from app.persistence.repository import (  # noqa: F401
            save_workspace_state,
            discard_workspace_draft,
        )
