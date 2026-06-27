"""Export/Audit C1 Migration: production-route Playwright smoke test.

Mirrors tests/test_senior_debt_c1_migration_browser.py: launches the
app as a real `uvicorn` subprocess, authenticates via
`app.auth.create_session_token()`, creates a real user project via
`/projects/create`, and drives the real `/?project=...` route,
switching to the Downloads tab (`window.switchTab('downloads')`,
panel id `panel-downloads`, grid `data-fc-grid="export"`) and the
Audit tab (`window.switchTab('audit')`, panel id `panel-audit`, grid
`data-fc-grid="audit"`).

Both surfaces are entirely read-only -- no `<input>` exists on
either. Critically, this test also verifies that the real download
links inside `panel-downloads` (`<a class="download-item" href=...>`)
keep their original `href` attribute and remain natively clickable
after gaining `data-fc-*` attributes -- i.e. the C1 markup contract
was added directly onto the existing `<a>` elements, never via an
intercepting wrapper placed in front of them.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")

from app.auth import create_session_token  # noqa: E402  (after env setup)

COOKIE_NAME = "finco_session"


def _pick_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def _wait_for_health(base_url, timeout=20.0):
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/public-health", timeout=2.0) as response:
                if response.status == 200:
                    return
        except Exception as exc:
            last_error = exc
        time.sleep(0.25)
    raise AssertionError(f"app did not become healthy at {base_url!r}: {last_error!r}")


def _create_user_project(base_url, token):
    form = urllib.parse.urlencode({
        "project_name": "Export Audit C1 Migration Smoke",
        "project_type": "Solar",
        "template_source": "oborovo",
        "country_market": "Croatia",
        "capacity_mw": "50",
        "cod_date": "2027-01-01",
        "construction_months": "12",
        "horizon_years": "25",
        "tariff_eur_mwh": "60",
        "ppa_term_years": "15",
        "p50_hours": "1400",
        "opex_y1_keur": "1000",
        "total_capex_keur": "50000",
        "gearing_pct": "70",
        "interest_rate_pct": "5",
        "tenor_years": "15",
        "target_dscr": "1.30",
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/projects/create",
        data=form,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": f"{COOKIE_NAME}={token}",
        },
    )
    with urllib.request.urlopen(req, timeout=10.0) as response:
        redirect = response.headers.get("HX-Redirect")
        assert redirect, "expected HX-Redirect header from /projects/create"
    project_code = urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query).get("project", [None])[0]
    assert project_code, f"could not parse project code from redirect {redirect!r}"
    return project_code


@pytest.fixture(scope="module")
def live_server():
    playwright = pytest.importorskip(
        "playwright.sync_api",
        reason="OPTIONAL_BROWSER_DEPENDENCY_MISSING: install playwright and chromium to run this test",
    )
    port = _pick_free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
    env.setdefault("FINCO_COOKIE_SECURE", "false")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main_web:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(BASE_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_health(base_url)
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.fixture(scope="module")
def export_audit_page(live_server):
    playwright = pytest.importorskip("playwright.sync_api")
    sync_playwright = playwright.sync_playwright

    token = create_session_token()
    project_code = _create_user_project(live_server, token)

    ctx = sync_playwright().start()
    try:
        browser = ctx.chromium.launch()
    except Exception:
        try:
            browser = ctx.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        except Exception as exc:
            ctx.stop()
            pytest.skip(f"OPTIONAL_BROWSER_DEPENDENCY_MISSING_BROWSER_BINARIES: {exc}")

    browser_context = browser.new_context()
    browser_context.add_cookies([{
        "name": COOKIE_NAME,
        "value": token,
        "url": live_server,
    }])
    page = browser_context.new_page()
    page_errors = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))
    page.goto(f"{live_server}/?project={project_code}", wait_until="networkidle")

    try:
        yield page, page_errors, live_server
    finally:
        browser.close()
        ctx.stop()


def _first_addr(page, grid_id):
    return page.evaluate(
        "(g) => { var c = document.querySelector('[data-fc-grid=\"' + g + '\"] [data-fc-cell=\"true\"]');"
        " return c ? c.getAttribute('data-fc-addr') : null; }",
        grid_id,
    )


class TestExportProductionRouteMigration:
    def test_export_grid_root_present(self, export_audit_page):
        page, page_errors, _ = export_audit_page
        page.evaluate("window.switchTab('downloads')")
        assert page.evaluate("!!document.querySelector('[data-fc-grid=\"export\"]')")
        assert not page_errors

    def test_export_cells_have_unique_addresses(self, export_audit_page):
        page, _, _ = export_audit_page
        page.evaluate("window.switchTab('downloads')")
        addrs = page.evaluate(
            "() => Array.from(document.querySelectorAll('[data-fc-grid=\"export\"] [data-fc-addr]'))"
            ".map(el => el.getAttribute('data-fc-addr'))"
        )
        assert len(addrs) > 0
        assert len(addrs) == len(set(addrs))

    def test_all_export_cells_are_non_editable(self, export_audit_page):
        page, _, _ = export_audit_page
        page.evaluate("window.switchTab('downloads')")
        result = page.evaluate(
            "() => Array.from(document.querySelectorAll('[data-fc-grid=\"export\"] [data-fc-cell=\"true\"]'))"
            ".map(el => el.getAttribute('data-fc-editable'))"
        )
        assert len(result) > 0
        for editable in result:
            assert editable == "false"

    def test_clicking_cell_sets_active_cell(self, export_audit_page):
        page, page_errors, _ = export_audit_page
        page.evaluate("window.switchTab('downloads')")
        addr = _first_addr(page, "export")
        assert addr

        page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"]')"
            ".dispatchEvent(new MouseEvent('click', { bubbles: true }))",
            addr,
        )
        active = page.evaluate("window.FcActiveCellManager.getActiveCell()")
        assert active is not None
        assert active["gridId"] == "export"

    def test_keyboard_navigation_and_selection(self, export_audit_page):
        page, _, _ = export_audit_page
        page.evaluate("window.switchTab('downloads')")
        addr = _first_addr(page, "export")
        page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"]').focus()",
            addr,
        )
        page.keyboard.down("Shift")
        page.keyboard.press("ArrowDown")
        page.keyboard.up("Shift")
        selection = page.evaluate("window.FcSelectionManager.getSelection()")
        assert selection is not None
        assert selection["gridId"] == "export"

    def test_copy_reads_raw_value(self, export_audit_page):
        page, _, _ = export_audit_page
        page.evaluate("window.switchTab('downloads')")
        addr = _first_addr(page, "export")
        page.evaluate(
            """
            (addr) => {
              document.querySelector('[data-fc-addr="' + addr + '"]').focus();
              window.FcSelectionManager.selectSingle('export',
                window.FcGridRegistry.getAddr('export', addr));
            }
            """,
            addr,
        )
        copied = page.evaluate("window.FcClipboardController.copySelection()")
        assert copied is not None

    def test_download_link_href_unchanged_after_markup_addition(self, export_audit_page):
        """The values-only export <a> must keep its real, original
        href -- the data-fc-* attributes must not have replaced or
        intercepted it."""
        page, _, _ = export_audit_page
        page.evaluate("window.switchTab('downloads')")
        href = page.evaluate(
            "() => { var a = document.querySelector('[data-fc-addr=\"export!workbook_download.values_only\"]');"
            " return a ? a.getAttribute('href') : null; }"
        )
        assert href == "/download"

    def test_download_link_is_not_wrapped_by_intercepting_element(self, export_audit_page):
        """Confirms the data-fc-cell attribute lives directly on the
        <a> tag itself, not on some wrapper placed in front of it,
        which would otherwise swallow clicks before they reach the
        anchor."""
        page, _, _ = export_audit_page
        page.evaluate("window.switchTab('downloads')")
        is_anchor = page.evaluate(
            "() => { var el = document.querySelector('[data-fc-addr=\"export!workbook_download.values_only\"]');"
            " return el ? el.tagName.toLowerCase() : null; }"
        )
        assert is_anchor == "a"

    def test_download_link_click_navigates(self, export_audit_page):
        """Verifies the download link is still fully functional after
        the C1 markup addition: clicking it triggers real browser
        navigation/download behaviour, not an intercepted no-op."""
        page, _, base_url = export_audit_page
        page.evaluate("window.switchTab('downloads')")
        with page.expect_event("download", timeout=5000) as download_info:
            page.click('[data-fc-addr="export!workbook_download.values_only"]')
        download = download_info.value
        assert download is not None


class TestAuditProductionRouteMigration:
    """The production route (`main_web.py`) hardcodes `audit_mode:
    False` on every workspace render path (confirmed by grep -- every
    occurrence sets the literal `False`, never a query-param toggle).
    `_audit_governance_relocated.html`, and therefore the `audit`
    grid, is only included inside workspace_shell.html's `{% if
    audit_mode %}` block (panel-audit, line ~580). Consequently the
    live `/?project=...` route never renders the `audit` grid in this
    environment -- there is no audit_mode=True toggle reachable from
    the browser to exercise here.

    This is confirmed directly (not assumed) below, and the static
    markup-contract coverage of the `audit` grid (which DOES render
    it, via a hand-built `audit_mode=True` standalone render) lives in
    tests/test_export_audit_c1_markup_contract.py::TestAuditMarkupContract.
    """

    def test_audit_panel_confirmed_not_reachable_via_production_route(self, export_audit_page):
        """Documents (rather than silently skips) the audit_mode gate:
        confirms panel-audit exists but its governance-relocated
        content -- and therefore the `audit` data-fc-grid -- is absent
        on the real production route in this environment, exactly as
        expected from main_web.py's hardcoded `audit_mode: False`."""
        page, page_errors, _ = export_audit_page
        page.evaluate("window.switchTab('audit')")
        panel_exists = page.evaluate("!!document.getElementById('panel-audit')")
        assert panel_exists
        audit_grid_present = page.evaluate("!!document.querySelector('[data-fc-grid=\"audit\"]')")
        assert audit_grid_present is False
        assert not page_errors
