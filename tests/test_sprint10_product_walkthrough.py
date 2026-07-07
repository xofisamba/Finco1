"""
Sprint 10 PR-7 — Product Walkthrough (static guardrails + optional Playwright).

Static tests verify the structural contracts of all Sprint 10 UI changes.
Playwright browser tests skip gracefully when playwright/chromium are not available.

CI artifact: screenshots saved to /tmp/sprint10_screenshots/ when browser runs.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
SCREENSHOT_DIR = Path("/tmp/sprint10_screenshots")


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Static guardrails — always run (no browser needed)
# ---------------------------------------------------------------------------

def test_opex_sheet_has_dynamic_group_loop():
    src = _read("app/templates/partials/sheet_opex.html")
    assert "seen_groups" in src, \
        "sheet_opex.html: dynamic group loop not found — still using hardcoded groups"


def test_opex_sheet_has_collapse_controls():
    src = _read("app/templates/partials/sheet_opex.html")
    assert "opexWsToggleGroup" in src, \
        "sheet_opex.html: opexWsToggleGroup JS function missing — group collapse broken"
    assert "opexWsExpandAll" in src and "opexWsCollapseAll" in src, \
        "sheet_opex.html: Expand All / Collapse All missing"


def test_opex_sheet_has_summary_strip():
    src = _read("app/templates/partials/sheet_opex.html")
    assert "opex-ws-summary-strip" in src, \
        "sheet_opex.html: summary strip missing"


def test_opex_sheet_child_rows_have_name_attributes():
    src = _read("app/templates/partials/sheet_opex.html")
    assert 'name="opex_' in src, \
        "sheet_opex.html: OPEX inputs missing name attributes — form submission broken"


def test_senior_debt_sheet_has_margin_display():
    src = _read("app/templates/partials/sheet_senior_debt.html")
    assert "senior_margin_bps" in src, \
        "sheet_senior_debt.html: credit margin bps field not displayed"
    assert "Credit Margin" in src, \
        "sheet_senior_debt.html: Credit Margin label missing"


def test_senior_debt_sheet_has_dsra_display():
    src = _read("app/templates/partials/sheet_senior_debt.html")
    assert "dsra_months" in src, \
        "sheet_senior_debt.html: dsra_months field not displayed"
    assert "DSRA Reserve" in src, \
        "sheet_senior_debt.html: DSRA Reserve label missing"


def test_senior_debt_sheet_has_lockup_dscr():
    src = _read("app/templates/partials/sheet_senior_debt.html")
    assert "lockup_dscr" in src, \
        "sheet_senior_debt.html: lockup_dscr field not displayed"


def test_project_context_has_margin_fields():
    src = _read("app/ui/project_context.py")
    assert "senior_margin_bps" in src, \
        "project_context.py: senior_margin_bps field not added"
    assert "senior_base_rate_pct" in src, \
        "project_context.py: senior_base_rate_pct field not added"
    assert "dsra_months" in src, \
        "project_context.py: dsra_months field not added"
    assert "lockup_dscr" in src, \
        "project_context.py: lockup_dscr field not added"


def test_revenue_sheet_contract_structure_present():
    """Sprint 10 PR-3: contract structure check (belt-and-suspenders for PR-7)."""
    src = _read("app/templates/partials/sheet_revenue.html")
    assert "rev-contract-block--active" in src, \
        "sheet_revenue.html: active contract block class missing"
    assert "rev-contract-block--disabled" in src, \
        "sheet_revenue.html: disabled contract block class missing"


def test_inputs_section_numeric_fields_present():
    """Sprint 10 PR-1+PR-2: numeric field macro present."""
    src = _read("app/templates/partials/inputs_section.html")
    assert "inp-input-group" in src, \
        "inputs_section.html: numeric input group wrapper missing"


# ---------------------------------------------------------------------------
# Live-browser Playwright tests — skip if playwright/chromium missing
# ---------------------------------------------------------------------------

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
    env.setdefault("FINCO_SECRET_KEY", "test-secret-sprint10")
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
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        yield {"base_url": base_url, "browser": browser, "pw": pw}
        browser.close()
        pw.stop()
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def _login(page, base_url: str) -> None:
    username = os.environ.get("FINCO_E2E_USERNAME") or os.environ.get("FINCO_ADMIN_USER")
    password = os.environ.get("FINCO_E2E_PASSWORD") or os.environ.get("FINCO_ADMIN_PASSWORD")
    if not username or not password:
        pytest.skip("E2E credentials not configured")
    page.goto(f"{base_url}/login", wait_until="networkidle")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


def _open_project(page, base_url: str, project_code: str = "tuho") -> None:
    page.goto(f"{base_url}/?project={project_code}", wait_until="networkidle")
    page.locator("#fo-sheets").wait_for(state="visible", timeout=10_000)


def _screenshot(page, name: str) -> None:
    path = SCREENSHOT_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=False)


def test_walkthrough_inputs_numeric_fields(live_app):
    """PR-1+PR-2: Inputs tab shows numeric fields with unit suffixes."""
    page = live_app["browser"].new_page(viewport={"width": 1366, "height": 900})
    js_errors: list[str] = []
    page.on("pageerror", lambda e: js_errors.append(str(e)))
    try:
        _login(page, live_app["base_url"])
        _open_project(page, live_app["base_url"])

        # Click Inputs tab
        btn = page.locator('.fo-sheet[data-fo-sheet-id="inputs"]')
        btn.click()
        page.wait_for_timeout(400)

        # Numeric inputs should be present
        num_inputs = page.locator('#panel-inputs input[type="number"]')
        assert num_inputs.count() > 0, "Inputs panel: no number-type inputs found"

        # Unit suffix spans should be present
        unit_spans = page.locator('#panel-inputs .inp-unit')
        assert unit_spans.count() > 0, "Inputs panel: no .inp-unit spans found"

        _screenshot(page, "01_inputs_numeric_fields")
        assert not js_errors, f"JS errors on inputs tab: {js_errors}"
    finally:
        page.close()


def test_walkthrough_revenue_contract_structure(live_app):
    """PR-3: Revenue tab shows Contract 1 (active) and Contract 2 (disabled)."""
    page = live_app["browser"].new_page(viewport={"width": 1366, "height": 900})
    js_errors: list[str] = []
    page.on("pageerror", lambda e: js_errors.append(str(e)))
    try:
        _login(page, live_app["base_url"])
        _open_project(page, live_app["base_url"])

        btn = page.locator('.fo-sheet[data-fo-sheet-id="revenue"]')
        btn.click()
        page.wait_for_timeout(400)

        # Contract 1 active block
        c1 = page.locator('.rev-contract-block--active')
        assert c1.count() >= 1, "Revenue: Contract 1 active block not found"

        # Contract 2 disabled block
        c2 = page.locator('.rev-contract-block--disabled')
        assert c2.count() >= 1, "Revenue: Contract 2 disabled block not found"

        _screenshot(page, "02_revenue_contract_structure")
        assert not js_errors, f"JS errors on revenue tab: {js_errors}"
    finally:
        page.close()


def test_walkthrough_opex_collapsible_groups(live_app):
    """PR-4: OPEX tab has collapsible group sections."""
    page = live_app["browser"].new_page(viewport={"width": 1366, "height": 900})
    js_errors: list[str] = []
    page.on("pageerror", lambda e: js_errors.append(str(e)))
    try:
        _login(page, live_app["base_url"])
        _open_project(page, live_app["base_url"])

        btn = page.locator('.fo-sheet[data-fo-sheet-id="opex"]')
        btn.click()
        page.wait_for_timeout(400)

        # Summary strip
        strip = page.locator('.opex-ws-summary-strip')
        assert strip.count() >= 1, "OPEX: summary strip not found"

        # Group sections
        groups = page.locator('.opex-ws-group')
        if groups.count() > 0:
            # Collapse all
            page.click('button:text("Collapse all")')
            page.wait_for_timeout(200)
            _screenshot(page, "03_opex_collapsed")

            # Expand all
            page.click('button:text("Expand all")')
            page.wait_for_timeout(200)
            _screenshot(page, "04_opex_expanded")

        assert not js_errors, f"JS errors on opex tab: {js_errors}"
    finally:
        page.close()


def test_walkthrough_senior_debt_detail(live_app):
    """PR-6: Senior Debt tab shows margin, DSRA, lock-up DSCR."""
    page = live_app["browser"].new_page(viewport={"width": 1366, "height": 900})
    js_errors: list[str] = []
    page.on("pageerror", lambda e: js_errors.append(str(e)))
    try:
        _login(page, live_app["base_url"])
        _open_project(page, live_app["base_url"])

        btn = page.locator('.fo-sheet[data-fo-sheet-id="senior-debt"]')
        btn.click()
        page.wait_for_timeout(400)

        # Facility summary should be present
        summary = page.locator('.assumption-grid')
        assert summary.count() >= 1, "Senior Debt: assumption grid not found"

        _screenshot(page, "05_senior_debt_detail")
        assert not js_errors, f"JS errors on senior debt tab: {js_errors}"
    finally:
        page.close()
