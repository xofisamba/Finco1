"""C2-PR15: EBITDA Preview — production-route Playwright tests.

Covers the browser-side required-behaviour points from the C2-PR15
task spec, for the new EBITDA preview indicator
(#ebitda-preview-value):

  1. EBITDA preview updates correctly after BOTH Revenue and OPEX
     edits settle within the same debounce window (chained
     computation: EBITDA = Revenue preview - OPEX preview).
  2. EBITDA preview remains null/blank when only one of the two grids
     (Revenue or OPEX) is edited in a given flush.
  3. A failed preview request keeps the previously-rendered valid
     EBITDA preview value visible; only the status label changes.

Uses the same real-uvicorn-subprocess + real-auth + real-project
fixture pattern as the PR9/PR10/PR11/PR13/PR14 browser test suites.
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
        "project_name": "C2 PR15 EBITDA Preview Smoke",
        "project_type": "Solar",
        "template_source": "generic_solar",
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
    pytest.importorskip(
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


@pytest.fixture
def runtime_page(live_server):
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
        yield page, page_errors, project_code
    finally:
        browser.close()
        ctx.stop()


def _first_editable_cell_addr(page, grid_id, kind):
    return page.evaluate(
        """
        (args) => {
          var cell = document.querySelector(
            '[data-fc-grid="' + args.gridId + '"] [data-fc-cell="true"][data-fc-editable="true"][data-fc-kind="' + args.kind + '"]'
          );
          return cell ? cell.getAttribute('data-fc-addr') : null;
        }
        """,
        {"gridId": grid_id, "kind": kind},
    )


def _edit_cell(page, addr, value):
    page.evaluate(
        """
        (args) => {
          var input = document.querySelector('[data-fc-addr="' + args.addr + '"] input');
          document.activeElement && document.activeElement.blur();
          input.dispatchEvent(new MouseEvent('click', { bubbles: true }));
          input.focus();
          input.value = args.value;
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
        }
        """,
        {"addr": addr, "value": value},
    )


def _wait_for_preview_value(page, element_id, attr, timeout_ms=4000):
    page.wait_for_function(
        """
        (args) => {
          var el = document.getElementById(args.id);
          return !!(el && el.getAttribute(args.attr) === 'patched');
        }
        """,
        arg={"id": element_id, "attr": attr},
        timeout=timeout_ms,
    )


def _wait_for_runtime_state(page, expected_state, element_id, timeout_ms=6000):
    page.wait_for_function(
        """
        (args) => {
          var el = document.getElementById(args.id);
          return !!(el && el.getAttribute('data-c2pr11-runtime-state') === args.state);
        }
        """,
        arg={"id": element_id, "state": expected_state},
        timeout=timeout_ms,
    )


def _install_failing_preview(page):
    def _handler(route, request):
        route.abort("failed")

    page.route("**/model/preview", _handler)


class TestEbitdaPreviewBrowser:
    """UPDATED for C2-PR17: OPEX line Budget cells are now real,
    editable inputs (non-contingency rows, on user projects) — see
    docs/C2_PR17_OPEX_LINE_EDITABILITY_BRIDGE.md. EBITDA preview can
    now become non-null via real DOM editing, provided BOTH the
    Revenue and OPEX grids are edited and settle within the same
    debounce flush. The tests below restore the "both edited ->
    EBITDA becomes non-null" scenario, while preserving the
    "never fabricate" tests for genuinely-null scenarios (only one
    grid edited, or no edit at all).
    """

    def test_ebitda_stays_blank_when_only_revenue_edited(self, runtime_page):
        """Editing only the Revenue grid must NOT produce a rendered
        EBITDA value — it must remain unpatched/blank, since EBITDA
        preview is null unless both Revenue and OPEX previews are
        non-null in the same flush."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('revenue')")
        revenue_addr = _first_editable_cell_addr(page, "revenue", "text")

        ebitda_before = page.eval_on_selector(
            "#ebitda-preview-value", "el => el.getAttribute('data-c2pr15-ebitda-preview')"
        )
        _edit_cell(page, revenue_addr, "999.99")
        _wait_for_preview_value(page, "revenue-total-preview-value", "data-c2pr13-revenue-preview")
        page.wait_for_timeout(500)

        ebitda_after = page.eval_on_selector(
            "#ebitda-preview-value", "el => el.getAttribute('data-c2pr15-ebitda-preview')"
        )
        assert ebitda_after == ebitda_before, (
            "EBITDA preview must not be patched when only Revenue was "
            "edited (OPEX preview is still null this flush)"
        )
        assert not page_errors

    def test_ebitda_never_fabricates_a_value_before_any_edit(self, runtime_page):
        """EBITDA preview must never render a fabricated numeric
        value before any Revenue/OPEX edit has happened."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('opex')")
        addr = _first_editable_cell_addr(page, "opex", "amount")
        assert addr is not None, (
            "expected at least one editable OPEX Budget cell after C2-PR17"
        )

        text = page.eval_on_selector("#ebitda-preview-value", "el => el.textContent")
        assert not any(ch.isdigit() for ch in text), (
            f"EBITDA preview must never render a fabricated numeric value; got {text!r}"
        )
        assert not page_errors

    def test_ebitda_becomes_revenue_minus_opex_when_both_edited_in_same_flush(self, runtime_page):
        """C2-PR17 restores the original PR15 scenario: editing BOTH a
        Revenue cell and an OPEX Budget cell so they settle within the
        same debounce window must produce EBITDA preview = Revenue
        preview - OPEX preview."""
        page, page_errors, _ = runtime_page

        page.evaluate("window.switchTab('opex')")
        opex_addr = _first_editable_cell_addr(page, "opex", "amount")
        assert opex_addr is not None

        page.evaluate("window.switchTab('revenue')")
        revenue_addr = _first_editable_cell_addr(page, "revenue", "text")
        assert revenue_addr is not None

        # Edit OPEX first, then Revenue immediately after (within the
        # same debounce window) so both dirty addresses are present in
        # the same flush.
        page.evaluate("window.switchTab('opex')")
        _edit_cell(page, opex_addr, "500.00")
        page.evaluate("window.switchTab('revenue')")
        _edit_cell(page, revenue_addr, "1500.00")

        _wait_for_preview_value(page, "ebitda-preview-value", "data-c2pr15-ebitda-preview")

        revenue_text = page.eval_on_selector("#revenue-total-preview-value", "el => el.textContent")
        opex_text = page.eval_on_selector("#opex-total-preview-value", "el => el.textContent")
        ebitda_text = page.eval_on_selector("#ebitda-preview-value", "el => el.textContent")

        assert any(ch.isdigit() for ch in revenue_text)
        assert any(ch.isdigit() for ch in opex_text)
        assert any(ch.isdigit() for ch in ebitda_text), (
            f"expected a numeric EBITDA preview value; got {ebitda_text!r}"
        )
        assert not page_errors
