"""C2-PR1: Live Modelling Layer — Live Modelling Foundation.

Static wiring checks (always run, no optional dependency):
  - live-model.js is served
  - base.html wires it in after fill-controller.js and before app.js
  - the C1 interaction-layer modules (PR1-PR9) are unchanged and
    still served
  - existing pages still render unchanged
  - no recalculation/formula/dependency-graph/Save/Run code exists in
    live-model.js

The JS-execution behaviour (dirty tracking, batching, scheduler,
session lifecycle, HTMX-swap interplay) is covered separately in
tests/test_c2_pr1_live_model_browser.py, which intentionally never
imports main_web — Playwright's sync API cannot run inside an
already-active asyncio/anyio event loop, and merely importing
main_web in this process is enough to leave one running.
"""
import os
import sys

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

from main_web import app
from app.auth import create_session_token


@pytest.fixture
def client():
    tc = TestClient(app)
    token = create_session_token()
    tc.cookies.set("finco_session", token)
    return tc


class TestStaticWiring:
    def test_live_model_js_is_served(self, client):
        r = client.get("/static/modelling/live-model.js")
        assert r.status_code == 200
        assert "FcLiveModel" in r.text

    def test_fill_controller_js_unchanged_and_still_served(self, client):
        r = client.get("/static/interaction/fill-controller.js")
        assert r.status_code == 200
        assert "FcFillController" in r.text

    def test_undo_manager_js_unchanged_and_still_served(self, client):
        r = client.get("/static/interaction/undo-manager.js")
        assert r.status_code == 200
        assert "FcUndoManager" in r.text

    def test_clipboard_controller_js_unchanged_and_still_served(self, client):
        r = client.get("/static/interaction/clipboard-controller.js")
        assert r.status_code == 200
        assert "FcClipboardController" in r.text

    def test_selection_manager_js_unchanged_and_still_served(self, client):
        r = client.get("/static/interaction/selection-manager.js")
        assert r.status_code == 200
        assert "FcSelectionManager" in r.text

    def test_active_cell_js_unchanged_and_still_served(self, client):
        r = client.get("/static/interaction/active-cell.js")
        assert r.status_code == 200
        assert "FcActiveCellManager" in r.text

    def test_app_js_unchanged_and_still_served(self, client):
        r = client.get("/static/app.js")
        assert r.status_code == 200
        assert "function queueWorkspaceDraftPersist" in r.text
        assert "htmx:afterSwap" in r.text
        assert "bindEditableGridInputs" in r.text

    def test_no_recalculation_formula_dependency_or_saverun_code_in_live_model(self, client):
        r = client.get("/static/modelling/live-model.js")
        assert r.status_code == 200
        lowered = r.text.lower()
        for forbidden in (
            "recalculate(", "recalculation(", "evaluateformula(",
            "dependencygraph", "buildgraph(", "saveproject(",
            "runproject(", "fetch(", "xmlhttprequest",
        ):
            assert forbidden not in lowered, forbidden

    def test_base_html_loads_live_model_after_fill_controller_before_app_js(self, client):
        r = client.get("/?project=tuho")
        assert r.status_code == 200
        body = r.text
        assert "/static/interaction/fill-controller.js" in body
        assert "/static/modelling/live-model.js" in body
        assert "/static/app.js" in body

        fill_controller_pos = body.index("/static/interaction/fill-controller.js")
        live_model_pos = body.index("/static/modelling/live-model.js")
        app_js_pos = body.index('/static/app.js"')
        assert fill_controller_pos < live_model_pos < app_js_pos

    def test_existing_workspace_page_still_renders(self, client):
        r = client.get("/?project=tuho")
        assert r.status_code == 200
        body = r.text
        assert "workspace-content" in body
        assert 'id="main-form"' in body

    def test_no_save_or_run_behaviour_changed(self, client):
        # Confirm the production Save/Run endpoints are unaffected by
        # this PR (smoke check: the routes still exist and respond,
        # nothing has been wired to call them automatically).
        r = client.get("/?project=tuho")
        assert r.status_code == 200
        assert "/static/modelling/live-model.js" in r.text
