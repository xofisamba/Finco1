"""
UI-9 — Workbook tab navigation.

Verifies that every DOM-switch Modeling tab (Overview, Inputs, Revenue, OPEX,
CAPEX, Debt, Tax, Financials) responds to click events immediately after a
project is opened (including newly-created projects).  URL tabs (Scenarios,
Compare, Sensitivity, Lender, Reports, BESS) are verified to still work.

Static-only tests always run.  Live-browser Playwright tests skip gracefully
when Playwright or the chromium binaries are not available.
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Static guardrails — always run
# ---------------------------------------------------------------------------

def test_dom_tabs_have_click_handler_in_sheet_tabs():
    src = _read("app/templates/partials/_sheet_tabs.html")
    # The click listener wiring block must be present
    assert 'data-fo-sheet-kind="dom"' in src, \
        "_sheet_tabs.html: DOM tab buttons not found"
    assert "addEventListener('click'" in src, \
        "_sheet_tabs.html: no click event listener added for DOM tabs"
    assert "window.switchTab" in src, \
        "_sheet_tabs.html: click handler does not call window.switchTab"


def test_dom_tab_active_sync_in_sheet_tabs():
    src = _read("app/templates/partials/_sheet_tabs.html")
    assert "_syncFoSheetActive" in src, \
        "_sheet_tabs.html: _syncFoSheetActive helper not found — fo-sheet--active won't update on click"
    assert "fo-sheet--active" in src, \
        "_sheet_tabs.html: fo-sheet--active class toggle not present"


def test_appjs_hash_activation_supports_fo_sheet():
    src = _read("static/app.js")
    # Hash-based tab activation must also query fo-sheet DOM tabs
    assert 'data-fo-sheet-kind="dom"' in src, \
        "app.js: hash-based activation doesn't query .fo-sheet DOM tabs — hash redirect after project creation broken"


def test_all_dom_tab_ids_present():
    src = _read("app/templates/partials/_sheet_tabs.html")
    for tab_id in ("overview", "inputs", "revenue", "opex", "capex", "senior-debt", "tax", "pl"):
        assert f'data-fo-sheet-id="{tab_id}"' in src, \
            f"_sheet_tabs.html: DOM tab {tab_id!r} not found"


def test_all_dom_panels_present():
    src = _read("app/templates/partials/workspace_shell.html")
    for panel_id in ("panel-overview", "panel-inputs", "panel-revenue", "panel-opex",
                     "panel-capex", "panel-senior-debt", "panel-tax", "panel-pl"):
        assert f'id="{panel_id}"' in src, \
            f"workspace_shell.html: #{panel_id} not found — switchTab guard will block navigation"


def test_new_project_form_uses_inputs_hash():
    src = _read("app/templates/partials/new_project_minimal.html")
    assert "#inputs" in src, \
        "new_project_minimal.html: redirect after creation doesn't include #inputs hash"


# ---------------------------------------------------------------------------
# Live-browser Playwright tests — skip if playwright/chromium missing
# ---------------------------------------------------------------------------

DOM_TABS = [
    ("overview", "Overview"),
    ("inputs", "inputs"),        # panel content check — presence of panel only
    ("revenue", "revenue"),
    ("opex", "opex"),
    ("capex", "capex"),
    ("senior-debt", "senior-debt"),
    ("tax", "tax"),
    ("pl", "pl"),
]

URL_TABS = [
    ("scenarios", "/scenarios"),
    ("compare", "/scenarios/compare"),
    ("sensitivity", "/scenarios/sensitivity"),
    ("lender", "/scenarios/lender-case"),
    ("reports", "/scenarios/exec-summary"),
    ("bess", "/scenarios/bess-revenue"),
]


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def _wait_for_health(base_url: str, timeout: float = 25.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/public-health", timeout=2.0) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                if resp.status == 200 and '"status":"ok"' in body.replace(" ", ""):
                    return
        except Exception as exc:
            last_error = exc
            time.sleep(0.3)
            continue
        time.sleep(0.3)
    raise AssertionError(f"App not healthy at {base_url!r}; last_error={last_error!r}")


@pytest.fixture(scope="module")
def live_app():
    playwright = pytest.importorskip(
        "playwright.sync_api",
        reason="OPTIONAL_BROWSER_DEPENDENCY_MISSING",
    )

    port = _pick_free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.setdefault("FINCO_SECRET_KEY", "test-secret-ui9")
    env.setdefault("FINCO_COOKIE_SECURE", "false")

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main_web:app",
         "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(REPO),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_health(base_url)
        sync_playwright = playwright.sync_playwright
        try:
            pw = sync_playwright().start()
            browser = pw.chromium.launch()
        except Exception as exc:
            proc.terminate()
            pytest.skip(f"OPTIONAL_BROWSER_DEPENDENCY_MISSING_BINARIES: {exc}")
        yield {"base_url": base_url, "browser": browser, "pw": pw}
        browser.close()
        pw.stop()
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def _login(page, base_url: str) -> bool:
    username = os.environ.get("FINCO_E2E_USERNAME") or os.environ.get("FINCO_ADMIN_USER")
    password = os.environ.get("FINCO_E2E_PASSWORD") or os.environ.get("FINCO_ADMIN_PASSWORD")
    if not username or not password:
        pytest.skip("E2E credentials not configured: set FINCO_E2E_USERNAME and FINCO_E2E_PASSWORD")
    page.goto(f"{base_url}/login", wait_until="networkidle")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")
    return True


def _open_project(page, base_url: str, project_code: str = "tuho") -> None:
    page.goto(f"{base_url}/?project={project_code}", wait_until="networkidle")
    page.locator("#fo-sheets").wait_for(state="visible", timeout=10_000)


@pytest.mark.parametrize("tab_id,_label", DOM_TABS)
def test_dom_tab_click_shows_panel(live_app, tab_id, _label):
    """Clicking each DOM modeling tab must make its panel active."""
    page = live_app["browser"].new_page(viewport={"width": 1366, "height": 900})
    js_errors: list[str] = []
    page.on("pageerror", lambda e: js_errors.append(str(e)))
    try:
        _login(page, live_app["base_url"])
        _open_project(page, live_app["base_url"])

        btn = page.locator(f'.fo-sheet[data-fo-sheet-kind="dom"][data-fo-sheet-id="{tab_id}"]')
        btn.click()
        page.wait_for_timeout(300)

        # Panel must be active
        panel = page.locator(f"#panel-{tab_id}")
        assert panel.count() >= 1, f"#panel-{tab_id} not found in DOM"
        assert "active" in (panel.get_attribute("class") or ""), \
            f"#panel-{tab_id} not active after clicking {tab_id!r} tab"

        # Tab button must show active state
        assert "fo-sheet--active" in (btn.get_attribute("class") or ""), \
            f".fo-sheet[data-fo-sheet-id={tab_id!r}] not marked active after click"

        assert not js_errors, f"JS errors during {tab_id!r} tab click: {js_errors}"
    finally:
        page.close()


def test_dom_tabs_active_after_hash_redirect(live_app):
    """After project creation redirect to /?project=X#inputs, Inputs panel must be active."""
    page = live_app["browser"].new_page(viewport={"width": 1366, "height": 900})
    js_errors: list[str] = []
    page.on("pageerror", lambda e: js_errors.append(str(e)))
    try:
        _login(page, live_app["base_url"])
        # Simulate post-creation redirect with hash
        page.goto(f"{live_app['base_url']}/?project=tuho#inputs", wait_until="networkidle")
        page.locator("#fo-sheets").wait_for(state="visible", timeout=10_000)
        page.wait_for_timeout(500)

        panel = page.locator("#panel-inputs")
        assert panel.count() >= 1, "#panel-inputs not found"
        assert "active" in (panel.get_attribute("class") or ""), \
            "#panel-inputs not active after loading /?project=tuho#inputs"
        assert not js_errors, f"JS errors on hash redirect: {js_errors}"
    finally:
        page.close()


@pytest.mark.parametrize("tab_id,href", URL_TABS)
def test_url_tab_click_swaps_canvas(live_app, tab_id, href):
    """Clicking each URL tab must swap the main canvas without a full page reload."""
    page = live_app["browser"].new_page(viewport={"width": 1366, "height": 900})
    js_errors: list[str] = []
    page.on("pageerror", lambda e: js_errors.append(str(e)))
    try:
        _login(page, live_app["base_url"])
        _open_project(page, live_app["base_url"])

        tab = page.locator(f'.fo-sheet[data-fo-sheet-kind="url"][data-fo-sheet-id="{tab_id}"]')
        tab.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(300)

        # URL must have updated
        assert href in page.url, \
            f"URL did not update to {href!r} after clicking {tab_id!r} tab; got {page.url!r}"

        # #main-canvas must still exist
        assert page.locator("#main-canvas").count() >= 1, \
            "#main-canvas gone after URL tab click — chrome was clobbered"

        # Tab must be active
        assert "fo-sheet--active" in (tab.get_attribute("class") or ""), \
            f"URL tab {tab_id!r} not marked active after click"

        assert not js_errors, f"JS errors during {tab_id!r} URL tab click: {js_errors}"
    finally:
        page.close()
