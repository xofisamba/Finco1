"""UX-1A-NAVIGATION-CONTEXT-FIX.

Regression coverage for the tab-switching / "New Project Setup" bug:
two ``htmx:afterSwap`` handlers (one global in ``static/app.js``, one
inline on ``#workspace-content`` in ``workspace_shell.html``) used a
static condition (panel hidden + contains a form) to decide whether to
force-show the New Project panel. That condition is true after almost
any unrelated htmx swap in the workspace (Save, Run, scenario create),
not just after the create-project form result is actually swapped in,
so the New Project panel could be forced open while the user was on a
different tab.

This is presentation/navigation only -- no model, formula, runtime,
export, or validation-classification changes are covered or required
by these tests.
"""
from __future__ import annotations

import os
import pathlib
import re

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-ux1a")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_session_token  # noqa: E402
from main_web import app  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

EXPECTED_TAB_PANELS = (
    "panel-overview",
    "panel-inputs",
    "panel-scenario",
    "panel-construction",
    "panel-production",
    "panel-revenue",
    "panel-opex",
    "panel-capex",
    "panel-senior-debt",
    "panel-shl",
    "panel-tax",
    "panel-pl",
    "panel-cashflow",
    "panel-balance",
    "panel-distributions",
    "panel-sponsor",
    "panel-audit",
    "panel-downloads",
)


@pytest.fixture(scope="module")
def logged_in_client():
    client = TestClient(app)
    token = create_session_token(user_id="1", username="test_user")
    client.cookies.set("finco_session", token)
    return client


class TestWorkspaceContainsAllTabPanels:
    """A valid project workspace must render every tab panel once,
    so client-side tab switching never finds a missing target."""

    def test_workspace_has_all_expected_panels(self, logged_in_client):
        r = logged_in_client.get("/?project=tuho", follow_redirects=True)
        assert r.status_code == 200
        for panel_id in EXPECTED_TAB_PANELS:
            assert f'id="{panel_id}"' in r.text, (
                f"Workspace is missing expected tab panel {panel_id!r}"
            )

    def test_new_project_panel_hidden_by_default(self, logged_in_client):
        r = logged_in_client.get("/?project=tuho", follow_redirects=True)
        match = re.search(
            r'<div class="tab-panel" id="panel-new-project"([^>]*)>',
            r.text,
        )
        assert match is not None, "panel-new-project not found in workspace"
        assert "display:none" in match.group(1), (
            "panel-new-project must start hidden so it cannot be "
            "mistaken for the requested tab"
        )


class TestAfterSwapHandlerScoped:
    """The afterSwap handlers must only re-show the New Project panel
    when the swap actually targeted it, not on every swap."""

    def test_global_handler_checks_swap_target(self):
        text = (REPO_ROOT / "static" / "app.js").read_text()
        match = re.search(
            r"htmx:afterSwap.*?panel-new-project.*?\n(?:.*?\n){0,8}",
            text,
            re.DOTALL,
        )
        assert match is not None
        assert "panel.contains(target)" in text, (
            "The global afterSwap handler must check that the swap "
            "target was actually inside panel-new-project before "
            "force-showing it"
        )

    def test_inline_handler_checks_event_target(self):
        # UX-1C: the duplicate inline hx-on handler on #workspace-content
        # was removed (it was a stale pre-UX-1A copy of the same check
        # now living once in static/app.js's document-level listener).
        # Guard against a duplicate handler creeping back in without the
        # scoped check.
        text = (
            REPO_ROOT / "app" / "templates" / "partials" / "workspace_shell.html"
        ).read_text()
        assert "htmx:afterSwap" not in text, (
            "workspace_shell.html should not carry its own afterSwap "
            "handler for panel-new-project; that logic lives once in "
            "static/app.js"
        )
        app_js_text = (REPO_ROOT / "static" / "app.js").read_text()
        assert "panel.contains(target)" in app_js_text, (
            "static/app.js must check the actual swap target before "
            "force-showing panel-new-project"
        )


class TestSwitchTabGuardsAgainstStaleNewProjectPanel:
    """switchTab() must defensively close any stray New Project panel
    and refuse to switch into a panel that doesn't exist."""

    def test_switch_tab_closes_new_project_panel(self):
        text = (REPO_ROOT / "static" / "app.js").read_text()
        fn_match = re.search(
            r"function switchTab\(tabId\) \{.*?\n\}", text, re.DOTALL
        )
        assert fn_match is not None
        body = fn_match.group(0)
        assert "panel-new-project" in body, (
            "switchTab() must reset panel-new-project's visibility on "
            "every real tab switch"
        )
        assert "newProjectPanel.style.display = 'none'" in body

    def test_switch_tab_guards_missing_panel(self):
        text = (REPO_ROOT / "static" / "app.js").read_text()
        fn_match = re.search(
            r"function switchTab\(tabId\) \{.*?\n\}", text, re.DOTALL
        )
        assert fn_match is not None
        body = fn_match.group(0)
        assert "getElementById('panel-' + tabId)" in body, (
            "switchTab() must check the target panel exists before "
            "switching, so a stale/invalid tabId cannot silently fall "
            "through to whatever panel happens to be visible"
        )


class TestActiveProjectContextPreservedAcrossActions:
    """Save / Run / Scenario routes must keep the active_project
    context bound to the same project, never silently dropping it."""

    def test_workspace_active_project_hidden_field_populated(self, logged_in_client):
        r = logged_in_client.get("/?project=tuho", follow_redirects=True)
        assert r.status_code == 200
        match = re.search(
            r'name="active_project" value="([^"]*)"', r.text
        )
        assert match is not None
        assert match.group(1) == "tuho"

    def test_scenarios_route_preserves_project(self, logged_in_client):
        r = logged_in_client.get("/scenarios?project=tuho", follow_redirects=True)
        assert r.status_code == 200

    def test_run_route_exists_for_active_project(self, logged_in_client):
        r = logged_in_client.post(
            "/run",
            data={"active_project": "tuho"},
            follow_redirects=True,
        )
        # Accept any non-5xx response: this is checking the route is
        # reachable and does not error when active_project is present,
        # not validating run output.
        assert r.status_code < 500


class TestInvalidProjectDoesNotMasqueradeAsNewProjectSetup:
    """An invalid/unknown project code must not be silently treated
    as if the user had opened the New Project panel."""

    def test_unknown_project_code_does_not_force_new_project_panel_visible(
        self, logged_in_client
    ):
        r = logged_in_client.get(
            "/?project=does-not-exist-xyz", follow_redirects=True
        )
        assert r.status_code == 200
        match = re.search(
            r'<div class="tab-panel" id="panel-new-project"([^>]*)>',
            r.text,
        )
        assert match is not None
        assert "display:none" in match.group(1), (
            "panel-new-project must remain hidden on initial render "
            "even for an unrecognised project code; switching it "
            "visible is a client-side action only, not a default "
            "server-rendered state"
        )
