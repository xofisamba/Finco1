"""C1-PR6: Spreadsheet Interaction Layer — Selection Model Foundation.

Static wiring checks (always run, no optional dependency):
  - selection-manager.js is served
  - base.html wires it in after keyboard-router.js and before app.js
  - keyboard-router.js still serves the PR5 API plus the PR6 addendum
  - existing pages still render unchanged

The JS-execution behaviour (click selection, range extension via
Shift+Arrow, collapse-on-move, swap reconciliation) is covered
separately in tests/test_c1_pr6_selection_manager_browser.py, which
intentionally never imports main_web — Playwright's sync API cannot
run inside an already-active asyncio/anyio event loop, and merely
importing main_web in this process is enough to leave one running.
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
    def test_selection_manager_js_is_served(self, client):
        r = client.get("/static/interaction/selection-manager.js")
        assert r.status_code == 200
        assert "FcSelectionManager" in r.text

    def test_keyboard_router_js_still_serves_and_has_pr6_addendum(self, client):
        r = client.get("/static/interaction/keyboard-router.js")
        assert r.status_code == 200
        assert "FcKeyboardRouter" in r.text
        assert "FcSelectionManager" in r.text
        assert "extendTo" in r.text
        assert "collapseToActive" in r.text

    def test_focus_manager_js_still_serves_sync_focus(self, client):
        r = client.get("/static/interaction/focus-manager.js")
        assert r.status_code == 200
        assert "syncFocus" in r.text

    def test_active_cell_js_unchanged_and_still_served(self, client):
        r = client.get("/static/interaction/active-cell.js")
        assert r.status_code == 200
        assert "FcActiveCellManager" in r.text

    def test_swap_lifecycle_js_unchanged_and_still_served(self, client):
        r = client.get("/static/interaction/swap-lifecycle.js")
        assert r.status_code == 200
        assert "FcSwapLifecycle" in r.text

    def test_app_js_unchanged_and_still_served(self, client):
        r = client.get("/static/app.js")
        assert r.status_code == 200
        assert "function queueWorkspaceDraftPersist" in r.text
        assert "htmx:afterSwap" in r.text
        assert "bindEditableGridInputs" in r.text

    def test_no_clipboard_or_fill_or_undo_code_in_selection_manager(self, client):
        r = client.get("/static/interaction/selection-manager.js")
        assert r.status_code == 200
        lowered = r.text.lower()
        for forbidden in (
            "clipboarddata", "execcommand", "navigator.clipboard",
            "document.oncopy", "document.onpaste", "document.oncut",
            "ctrl+z", "ctrl+y",
            "addeventlistener('copy'", "addeventlistener(\"copy\"",
            "addeventlistener('paste'", "addeventlistener(\"paste\"",
            "addeventlistener('cut'", "addeventlistener(\"cut\"",
        ):
            assert forbidden not in lowered, forbidden

    def test_base_html_loads_selection_manager_after_keyboard_router_before_app_js(self, client):
        r = client.get("/?project=tuho")
        assert r.status_code == 200
        body = r.text
        assert "/static/interaction/keyboard-router.js" in body
        assert "/static/interaction/selection-manager.js" in body
        assert "/static/app.js" in body

        keyboard_router_pos = body.index("/static/interaction/keyboard-router.js")
        selection_manager_pos = body.index("/static/interaction/selection-manager.js")
        app_js_pos = body.index('/static/app.js"')
        assert keyboard_router_pos < selection_manager_pos < app_js_pos

    def test_existing_workspace_page_still_renders(self, client):
        r = client.get("/?project=tuho")
        assert r.status_code == 200
        body = r.text
        assert "workspace-content" in body
        assert 'id="main-form"' in body
