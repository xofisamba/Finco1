"""Senior Debt C1 Migration: production-route Playwright smoke test.

Mirrors tests/test_revenue_c1_migration_browser.py /
tests/test_inputs_c1_migration_browser.py: launches the app as a real
`uvicorn` subprocess, authenticates via
`app.auth.create_session_token()`, creates a real user project via
`/projects/create`, and drives the real `/?project=...` route,
switching to the Senior Debt tab (`window.switchTab('senior-debt')`,
panel id `panel-senior-debt`).

Senior Debt's production markup is a mix of a real `<table
class="editable-grid-table">` (4 always-editable draft-workspace
inputs: gearing_pct, target_dscr, interest_rate_pct, tenor_years) and a
non-table `<div class="assumption-grid">` (5 read-only summary
`<span>` fields) sharing one `data-fc-grid="seniordebt"` root. This
test confirms both DOM shapes register correctly under the same grid,
plus the standard Active Cell / Keyboard / Selection / Copy / Paste /
Undo coverage, an htmx re-scan, and that the read-only summary cells'
raw values match the real project_ctx values rendered server-side.
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
    """POST /projects/create with a valid session cookie, returning the
    new project's code (parsed from the HX-Redirect response header)."""
    form = urllib.parse.urlencode({
        "project_name": "Senior Debt C1 Migration Smoke",
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
def senior_debt_page(live_server):
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

    # The Senior Debt sheet renders inside a tab panel that is hidden
    # (display:none) until its tab is activated, panel id
    # "panel-senior-debt", tab id "senior-debt".
    page.evaluate("window.switchTab('senior-debt')")

    try:
        yield page, page_errors
    finally:
        browser.close()
        ctx.stop()


def _first_table_addr(page):
    return page.evaluate(
        """
        () => {
          var cell = document.querySelector(
            '[data-fc-grid="seniordebt"] .editable-grid-table [data-fc-cell="true"]'
          );
          return cell ? cell.getAttribute('data-fc-addr') : null;
        }
        """
    )


def _first_summary_addr(page):
    return page.evaluate(
        """
        () => {
          var cell = document.querySelector(
            '[data-fc-grid="seniordebt"] .assumption-grid [data-fc-cell="true"]'
          );
          return cell ? cell.getAttribute('data-fc-addr') : null;
        }
        """
    )


class TestSeniorDebtProductionRouteMigration:
    def test_senior_debt_grid_root_present(self, senior_debt_page):
        page, page_errors = senior_debt_page
        assert page.evaluate("!!document.querySelector('[data-fc-grid=\"seniordebt\"]')")
        assert not page_errors

    def test_senior_debt_cells_have_unique_addresses(self, senior_debt_page):
        page, _ = senior_debt_page
        addrs = page.evaluate(
            """
            () => Array.from(document.querySelectorAll('[data-fc-grid="seniordebt"] [data-fc-addr]'))
              .map(el => el.getAttribute('data-fc-addr'))
            """
        )
        assert len(addrs) > 0
        assert len(addrs) == len(set(addrs))

    def test_table_rows_and_div_rows_both_register_under_same_grid(self, senior_debt_page):
        """Confirms FcGridRegistry indexes both the <table> rows
        (editable-grid-table) and the non-table <div> rows
        (assumption-grid) under the single seniordebt grid root."""
        page, _ = senior_debt_page
        table_addr = _first_table_addr(page)
        summary_addr = _first_summary_addr(page)
        assert table_addr
        assert summary_addr

        table_grid_id = page.evaluate(
            """
            (addr) => {
              var cell = window.FcGridRegistry.getAddr('seniordebt', addr);
              return cell ? 'seniordebt' : null;
            }
            """,
            table_addr,
        )
        summary_grid_id = page.evaluate(
            """
            (addr) => {
              var cell = window.FcGridRegistry.getAddr('seniordebt', addr);
              return cell ? 'seniordebt' : null;
            }
            """,
            summary_addr,
        )
        assert table_grid_id == "seniordebt"
        assert summary_grid_id == "seniordebt"

    def test_draft_inputs_are_editable_with_real_input(self, senior_debt_page):
        page, _ = senior_debt_page
        result = page.evaluate(
            """
            () => Array.from(document.querySelectorAll(
              '[data-fc-grid="seniordebt"] .editable-grid-table [data-fc-cell="true"]'
            )).map(el => ({
              editable: el.getAttribute('data-fc-editable'),
              hasInput: !!el.querySelector('input'),
            }))
            """
        )
        assert len(result) == 4
        for entry in result:
            assert entry["editable"] == "true"
            assert entry["hasInput"] is True

    def test_summary_cells_are_non_editable_with_no_input(self, senior_debt_page):
        page, _ = senior_debt_page
        result = page.evaluate(
            """
            () => Array.from(document.querySelectorAll(
              '[data-fc-grid="seniordebt"] .assumption-grid [data-fc-cell="true"]'
            )).map(el => ({
              editable: el.getAttribute('data-fc-editable'),
              hasInput: !!el.querySelector('input'),
              raw: el.getAttribute('data-fc-raw'),
            }))
            """
        )
        assert len(result) >= 4
        for entry in result:
            assert entry["editable"] == "false"
            assert entry["hasInput"] is False
            assert entry["raw"] is not None

    def test_clicking_editable_cell_sets_active_cell(self, senior_debt_page):
        page, page_errors = senior_debt_page
        addr = _first_table_addr(page)
        assert addr

        page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"] input')"
            ".dispatchEvent(new MouseEvent('click', { bubbles: true }))",
            addr,
        )

        active = page.evaluate("window.FcActiveCellManager.getActiveCell()")
        assert active is not None
        assert active["gridId"] == "seniordebt"
        assert active["cell"]["addr"] == addr
        assert not page_errors

    def test_keyboard_navigation_moves_active_cell(self, senior_debt_page):
        page, _ = senior_debt_page
        addr = _first_table_addr(page)
        page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"] input').focus()",
            addr,
        )
        before = page.evaluate("window.FcActiveCellManager.getActiveCell().cell.addr")
        page.keyboard.press("ArrowDown")
        after = page.evaluate("window.FcActiveCellManager.getActiveCell().cell.addr")
        assert after != before

    def test_shift_arrow_extends_selection(self, senior_debt_page):
        page, _ = senior_debt_page
        addr = _first_table_addr(page)
        page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"] input').focus()",
            addr,
        )
        page.keyboard.down("Shift")
        page.keyboard.press("ArrowDown")
        page.keyboard.up("Shift")
        selection = page.evaluate("window.FcSelectionManager.getSelection()")
        assert selection is not None
        assert selection["gridId"] == "seniordebt"

    def test_copy_reads_raw_value(self, senior_debt_page):
        page, _ = senior_debt_page
        addr = _first_table_addr(page)
        raw = page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"]').getAttribute('data-fc-raw')",
            addr,
        )

        page.evaluate(
            """
            (addr) => {
              document.querySelector('[data-fc-addr="' + addr + '"] input').focus();
              window.FcSelectionManager.selectSingle('seniordebt',
                window.FcGridRegistry.getAddr('seniordebt', addr));
            }
            """,
            addr,
        )
        copied = page.evaluate("window.FcClipboardController.copySelection()")
        assert copied is not None
        assert raw in str(copied)

    def test_paste_writes_to_editable_draft_input(self, senior_debt_page):
        page, _ = senior_debt_page
        addr = _first_table_addr(page)

        page.evaluate(
            """
            (addr) => {
              document.querySelector('[data-fc-addr="' + addr + '"] input').focus();
              window.FcActiveCellManager.setActiveCell('seniordebt',
                window.FcGridRegistry.getAddr('seniordebt', addr));
            }
            """,
            addr,
        )
        page.evaluate("(text) => window.FcClipboardController.pasteText(text)", "42.5")

        new_value = page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"] input').value",
            addr,
        )
        assert new_value == "42.5"

    def test_paste_onto_readonly_summary_cell_is_a_noop(self, senior_debt_page):
        page, _ = senior_debt_page
        addr = _first_summary_addr(page)

        before = page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"]').getAttribute('data-fc-raw')",
            addr,
        )
        page.evaluate(
            """
            (addr) => {
              document.querySelector('[data-fc-addr="' + addr + '"]').focus();
              window.FcActiveCellManager.setActiveCell('seniordebt',
                window.FcGridRegistry.getAddr('seniordebt', addr));
            }
            """,
            addr,
        )
        page.evaluate("(text) => window.FcClipboardController.pasteText(text)", "999.99")

        after = page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"]').getAttribute('data-fc-raw')",
            addr,
        )
        assert after == before

    def test_edit_marks_dirty_and_undo_works(self, senior_debt_page):
        page, _ = senior_debt_page
        addr = _first_table_addr(page)
        before_value = page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"] input').value",
            addr,
        )

        page.evaluate(
            """
            (addr) => {
              var input = document.querySelector('[data-fc-addr="' + addr + '"] input');
              input.dispatchEvent(new MouseEvent('click', { bubbles: true }));
              input.focus();
              input.value = '99';
              input.dispatchEvent(new Event('input', { bubbles: true }));
              input.dispatchEvent(new Event('change', { bubbles: true }));
            }
            """,
            addr,
        )

        assert page.evaluate("window.FcUndoManager.canUndo()") is True

        page.keyboard.press("Control+z")
        after_value = page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"] input').value",
            addr,
        )
        assert after_value == before_value

    def test_raw_numeric_values_on_readonly_summary_cells_match_project_ctx(self, senior_debt_page):
        """Confirms data-fc-raw on the assumption-grid summary cells
        reflects the real server-rendered project_ctx values, not a
        placeholder."""
        page, _ = senior_debt_page
        facility_raw = page.evaluate(
            "() => { var c = document.querySelector('[data-fc-addr=\"seniordebt!facility_amount\"]'); "
            "return c ? c.getAttribute('data-fc-raw') : null; }"
        )
        tenor_raw = page.evaluate(
            "() => { var c = document.querySelector('[data-fc-addr=\"seniordebt!tenor_summary\"]'); "
            "return c ? c.getAttribute('data-fc-raw') : null; }"
        )
        assert facility_raw is not None
        assert tenor_raw is not None
        # Tenor was seeded as 15 years via /projects/create.
        assert tenor_raw == "15"

    def test_htmx_swap_preserves_grid_registration(self, senior_debt_page):
        page, page_errors = senior_debt_page
        before = page.evaluate(
            "Array.from(document.querySelectorAll('[data-fc-grid=\"seniordebt\"] [data-fc-addr]')).length"
        )
        assert before > 0
        page.evaluate("window.FcGridRegistry.scan(document)")
        after = page.evaluate(
            "Array.from(document.querySelectorAll('[data-fc-grid=\"seniordebt\"] [data-fc-addr]')).length"
        )
        assert after == before
        assert page.evaluate("!!window.FcGridRegistry.getGrid('seniordebt')")
        assert not page_errors
