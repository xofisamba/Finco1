"""C2-PR16: Operating Cash Flow Preview — production-route Playwright
tests.

NOT AUTHORITATIVE OPERATING CASH FLOW: Operating Cash Flow Preview is
a verbatim passthrough of EBITDA Preview (no debt/tax/depreciation/
working-capital adjustment). Covers the browser-side
required-behaviour points from the C2-PR16 task spec, for the new OCF
preview indicator (#operating-cf-preview-value):

NOTE: OPEX line items are not yet wired up as editable in
app/templates/partials/sheet_opex_detail.html ("Line editing
deferred" is a pre-existing C1 boundary from Phase 21/24, unrelated
to and out of scope for this preview-pipeline PR — see
docs/C2_PR16_OPERATING_CF_PREVIEW.md). Since OPEX preview always
returns null today, EBITDA preview (which needs both Revenue and
OPEX previews non-null) can never become non-null via real DOM
editing either, and therefore neither can OCF preview, which is a
verbatim passthrough of EBITDA preview. That is correct, documented
"never fabricate" behaviour, not a bug. The tests below verify that
OCF preview stays permanently unavailable/unpatched in the real
browser. The chained passthrough arithmetic and null-propagation
logic are covered directly (independent of DOM editability) in
tests/test_c2_pr16_ocf_preview.py.

  1. OCF preview never fabricates a value while OPEX has no editable
     inputs (and therefore EBITDA preview is always null).
  2. OCF preview remains null/blank after editing other grids
     (Revenue) that don't make EBITDA preview non-null on their own.

Uses the same real-uvicorn-subprocess + real-auth + real-project
fixture pattern as the PR9/PR10/PR11/PR13/PR14/PR15 browser test
suites.
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
        "project_name": "C2 PR16 OCF Preview Smoke",
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


class TestOcfPreviewBrowser:
    def test_ocf_never_fabricates_a_value_with_no_editable_opex_inputs(self, runtime_page):
        """OCF preview must never render a fabricated numeric value,
        since both of its transitive inputs (EBITDA preview, which
        itself needs OPEX preview) can never become non-null until a
        future dedicated C1 PR adds real OPEX editability."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('opex')")
        addr = _first_editable_cell_addr(page, "opex", "amount")
        assert addr is None, (
            "expected zero editable OPEX cells under the current, "
            "intentionally-deferred C1 OPEX editing boundary"
        )

        text = page.eval_on_selector("#operating-cf-preview-value", "el => el.textContent")
        assert not any(ch.isdigit() for ch in text), (
            f"OCF preview must never render a fabricated numeric value; got {text!r}"
        )
        assert not page_errors

    def test_ocf_stays_blank_when_ebitda_is_null(self, runtime_page):
        """When EBITDA preview is null (OPEX has no editable inputs
        at all today), OCF preview must also remain
        unpatched/blank — never fabricated."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('revenue')")
        revenue_addr = _first_editable_cell_addr(page, "revenue", "text")

        ocf_before = page.eval_on_selector(
            "#operating-cf-preview-value", "el => el.getAttribute('data-c2pr16-ocf-preview')"
        )
        _edit_cell(page, revenue_addr, "999.99")
        _wait_for_preview_value(page, "revenue-total-preview-value", "data-c2pr13-revenue-preview")
        page.wait_for_timeout(500)

        ocf_after = page.eval_on_selector(
            "#operating-cf-preview-value", "el => el.getAttribute('data-c2pr16-ocf-preview')"
        )
        assert ocf_after == ocf_before, (
            "OCF preview must not be patched when EBITDA preview is "
            "unavailable (no editable OPEX inputs exist today)"
        )
        assert not page_errors
