"""C1-PR9: Spreadsheet Interaction Layer — Fill Down / Fill Right
Foundation.

Static wiring checks (always run, no optional dependency):
  - fill-controller.js is served
  - base.html wires it in after undo-manager.js and before app.js
  - clipboard-controller.js / undo-manager.js / selection-manager.js /
    active-cell.js / focus-manager.js are unchanged and still served
  - fill-controller.js integrates with FcUndoManager/applyCellValue
  - existing pages still render unchanged
  - no drag-fill/autofill/formula/recalculation code exists

The JS-execution behaviour (fill down/right, clipping, undo/redo
integration, keyboard guards, HTMX-swap interplay) is covered
separately in tests/test_c1_pr9_fill_controller_browser.py, which
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
    def test_fill_controller_js_is_served(self, client):
        r = client.get("/static/interaction/fill-controller.js")
        assert r.status_code == 200
        assert "FcFillController" in r.text

    def test_fill_controller_integrates_with_undo_manager_and_clipboard_controller(self, client):
        r = client.get("/static/interaction/fill-controller.js")
        assert r.status_code == 200
        assert "FcUndoManager" in r.text
        assert "recordTransaction" in r.text
        assert "FcClipboardController" in r.text
        assert "applyCellValue" in r.text

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
        assert "selectSingle" in r.text
        assert "extendTo" in r.text

    def test_active_cell_js_unchanged_and_still_served(self, client):
        r = client.get("/static/interaction/active-cell.js")
        assert r.status_code == 200
        assert "FcActiveCellManager" in r.text

    def test_focus_manager_js_unchanged_and_still_served(self, client):
        r = client.get("/static/interaction/focus-manager.js")
        assert r.status_code == 200
        assert "syncFocus" in r.text

    def test_app_js_unchanged_and_still_served(self, client):
        r = client.get("/static/app.js")
        assert r.status_code == 200
        assert "function queueWorkspaceDraftPersist" in r.text
        assert "htmx:afterSwap" in r.text
        assert "bindEditableGridInputs" in r.text

    def test_no_dragfill_autofill_formula_or_recalculation_code_in_fill_controller(self, client):
        r = client.get("/static/interaction/fill-controller.js")
        assert r.status_code == 200
        lowered = r.text.lower()
        for forbidden in (
            "dragfill(", "autofillseries(", "parseformula(",
            "recalculate(", "recalculation(",
        ):
            assert forbidden not in lowered, forbidden

    def test_base_html_loads_fill_controller_after_undo_manager_before_app_js(self, client):
        r = client.get("/?project=tuho")
        assert r.status_code == 200
        body = r.text
        assert "/static/interaction/undo-manager.js" in body
        assert "/static/interaction/fill-controller.js" in body
        assert "/static/app.js" in body

        undo_manager_pos = body.index("/static/interaction/undo-manager.js")
        fill_controller_pos = body.index("/static/interaction/fill-controller.js")
        app_js_pos = body.index('/static/app.js"')
        assert undo_manager_pos < fill_controller_pos < app_js_pos

    def test_existing_workspace_page_still_renders(self, client):
        r = client.get("/?project=tuho")
        assert r.status_code == 200
        body = r.text
        assert "workspace-content" in body
        assert 'id="main-form"' in body
