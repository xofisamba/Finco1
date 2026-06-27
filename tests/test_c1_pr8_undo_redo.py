"""C1-PR8: Spreadsheet Interaction Layer — Undo/Redo Foundation.

Static wiring checks (always run, no optional dependency):
  - undo-manager.js is served
  - base.html wires it in after clipboard-controller.js and before app.js
  - clipboard-controller.js / selection-manager.js / active-cell.js /
    focus-manager.js / keyboard-router.js / swap-lifecycle.js are
    unchanged and still served
  - clipboard-controller.js now integrates with FcUndoManager
  - existing pages still render unchanged
  - no fill/formula/recalculation code exists

The JS-execution behaviour (transaction recording, undo/redo,
keyboard guards, HTMX-swap interplay) is covered separately in
tests/test_c1_pr8_undo_redo_browser.py, which intentionally never
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
    def test_undo_manager_js_is_served(self, client):
        r = client.get("/static/interaction/undo-manager.js")
        assert r.status_code == 200
        assert "FcUndoManager" in r.text

    def test_clipboard_controller_js_unchanged_and_still_served(self, client):
        r = client.get("/static/interaction/clipboard-controller.js")
        assert r.status_code == 200
        assert "FcClipboardController" in r.text

    def test_clipboard_controller_integrates_with_undo_manager(self, client):
        r = client.get("/static/interaction/clipboard-controller.js")
        assert r.status_code == 200
        assert "FcUndoManager" in r.text
        assert "recordTransaction" in r.text

    def test_selection_manager_js_unchanged_and_still_served(self, client):
        r = client.get("/static/interaction/selection-manager.js")
        assert r.status_code == 200
        assert "FcSelectionManager" in r.text
        assert "selectSingle" in r.text
        assert "extendTo" in r.text

    def test_keyboard_router_js_unchanged_and_still_served(self, client):
        r = client.get("/static/interaction/keyboard-router.js")
        assert r.status_code == 200
        assert "FcKeyboardRouter" in r.text

    def test_active_cell_js_unchanged_and_still_served(self, client):
        r = client.get("/static/interaction/active-cell.js")
        assert r.status_code == 200
        assert "FcActiveCellManager" in r.text

    def test_focus_manager_js_unchanged_and_still_served(self, client):
        r = client.get("/static/interaction/focus-manager.js")
        assert r.status_code == 200
        assert "syncFocus" in r.text

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

    def test_no_fill_formula_or_recalculation_code_in_undo_manager(self, client):
        r = client.get("/static/interaction/undo-manager.js")
        assert r.status_code == 200
        lowered = r.text.lower()
        for forbidden in (
            "filldown(", "fillright(", "dragfill(",
            "parseformula(", "recalculate(", "recalculation(",
        ):
            assert forbidden not in lowered, forbidden

    def test_base_html_loads_undo_manager_after_clipboard_controller_before_app_js(self, client):
        r = client.get("/?project=tuho")
        assert r.status_code == 200
        body = r.text
        assert "/static/interaction/clipboard-controller.js" in body
        assert "/static/interaction/undo-manager.js" in body
        assert "/static/app.js" in body

        clipboard_controller_pos = body.index("/static/interaction/clipboard-controller.js")
        undo_manager_pos = body.index("/static/interaction/undo-manager.js")
        app_js_pos = body.index('/static/app.js"')
        assert clipboard_controller_pos < undo_manager_pos < app_js_pos

    def test_existing_workspace_page_still_renders(self, client):
        r = client.get("/?project=tuho")
        assert r.status_code == 200
        body = r.text
        assert "workspace-content" in body
        assert 'id="main-form"' in body
