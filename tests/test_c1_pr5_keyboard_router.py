"""C1-PR5: Spreadsheet Interaction Layer — Keyboard Navigation Foundation.

Static wiring checks (always run, no optional dependency):
  - keyboard-router.js is served
  - base.html wires it in after focus-manager.js and before app.js
  - existing pages still render unchanged

The JS-execution behaviour (arrow/Enter/Tab/Home/End/Ctrl+Arrow
movement, scoping to focused grid cells only, no clipboard/selection)
is covered separately in tests/test_c1_pr5_keyboard_router_browser.py,
which intentionally never imports main_web — Playwright's sync API
cannot run inside an already-active asyncio/anyio event loop, and
merely importing main_web in this process is enough to leave one
running.
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
    def test_keyboard_router_js_is_served(self, client):
        r = client.get("/static/interaction/keyboard-router.js")
        assert r.status_code == 200
        assert "FcKeyboardRouter" in r.text

    def test_focus_manager_js_still_serves_sync_focus(self, client):
        r = client.get("/static/interaction/focus-manager.js")
        assert r.status_code == 200
        assert "syncFocus" in r.text

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

    def test_no_clipboard_or_selection_code_in_keyboard_router(self, client):
        r = client.get("/static/interaction/keyboard-router.js")
        assert r.status_code == 200
        lowered = r.text.lower()
        for forbidden in (
            "clipboarddata", "execcommand", "navigator.clipboard",
            "rangeselect", "shiftkey && (window.fcselection",
        ):
            assert forbidden not in lowered

    def test_base_html_loads_keyboard_router_after_focus_manager_before_app_js(self, client):
        r = client.get("/?project=tuho")
        assert r.status_code == 200
        body = r.text
        assert "/static/interaction/focus-manager.js" in body
        assert "/static/interaction/keyboard-router.js" in body
        assert "/static/app.js" in body

        focus_manager_pos = body.index("/static/interaction/focus-manager.js")
        keyboard_router_pos = body.index("/static/interaction/keyboard-router.js")
        app_js_pos = body.index('/static/app.js"')
        assert focus_manager_pos < keyboard_router_pos < app_js_pos

    def test_existing_workspace_page_still_renders(self, client):
        r = client.get("/?project=tuho")
        assert r.status_code == 200
        body = r.text
        assert "workspace-content" in body
        assert 'id="main-form"' in body
