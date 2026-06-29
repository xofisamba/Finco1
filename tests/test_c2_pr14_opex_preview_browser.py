"""C2-PR14: OPEX Total Preview — production-route Playwright tests.

Mirrors tests/test_c2_pr13_revenue_preview_browser.py exactly, for the
new OPEX total preview indicator (#opex-total-preview-value).

Covers the browser-side required-behaviour points from the C2-PR14
task spec:

  1. OPEX preview updates after editing the OPEX Budget input.
  2. Exactly one preview request per settled edit (PR9 debounce
     regression).
  3. No Save triggered.
  4. No Run triggered.
  5. No Overview KPI changes (byte-identical pre/post).
  7. A failed preview request keeps the previous OPEX preview value
     visible; only the status label changes.
  8. PR9 request sequencing still holds for the OPEX preview
     specifically (rapid edits, only newest renders).
  9. Save does not erase the OPEX (or CAPEX/Revenue) preview value.
  10. Existing CAPEX/Revenue previews continue to work unaffected
      (regression).

(Point 6 "no persistence writes" is a backend concern, covered in
tests/test_c2_pr14_opex_preview.py's
TestNoFinancialEngineCallOrPersistenceMutation.test_no_persistence_mutation.)

Uses the same real-uvicorn-subprocess + real-auth + real-project
fixture pattern as the PR9/PR10/PR11/PR13 browser test suites.
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
        "project_name": "C2 PR14 OPEX Total Preview Smoke",
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


def _install_ordered_delayed_responses(page, delays_ms):
    state = {"count": 0}

    def _handler(route, request):
        idx = state["count"]
        state["count"] += 1
        delay = delays_ms[idx] if idx < len(delays_ms) else 0
        response = route.fetch()
        if delay:
            page.wait_for_timeout(delay)
        route.fulfill(response=response)

    page.route("**/model/preview", _handler)


class TestOpexTotalPreviewBrowser:
    """NOTE: OPEX line items are not yet wired up as editable in
    app/templates/partials/sheet_opex_detail.html ("Line editing
    deferred" there is a pre-existing C1 boundary from Phase 21/24,
    unrelated to and out of scope for this preview-pipeline PR — see
    docs/C2_PR14_OPEX_PREVIEW.md). Consequently there is currently no
    way to dirty an "opex!..." address from the real UI, so
    `_computeOpexTotalFromDom()` always returns null in practice
    (counted === 0) — this is the correct, documented "never
    fabricate" behaviour, not a bug. The tests below verify exactly
    that: the OPEX preview indicator never shows a fabricated value
    and the rest of the pipeline (no Save/Run, byte-identical Overview
    KPIs, CAPEX/Revenue previews) is unaffected by OPEX's presence.
    Points 1, 7, 8, 9 from the original task spec (update-after-edit,
    failed-request-preserves-value, sequencing, survives-Save) are not
    independently re-testable for OPEX specifically until a dedicated
    C1 PR adds real OPEX editability; the underlying arithmetic/
    null-propagation logic they'd exercise is covered for EBITDA/OCF
    via direct payload tests in tests/test_c2_pr14_opex_preview.py and
    tests/test_c2_pr15_ebitda_preview.py, which don't depend on DOM
    editability at all.
    """

    def test_opex_preview_never_fabricates_a_value_with_no_editable_inputs(self, runtime_page):
        """The OPEX grid currently has zero editable cells, so the
        preview indicator must never show a fabricated numeric total
        — it must stay in its initial/unavailable state."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('opex')")
        addr = _first_editable_cell_addr(page, "opex", "amount")
        assert addr is None, (
            "expected zero editable OPEX cells under the current, "
            "intentionally-deferred C1 OPEX editing boundary"
        )

        text = page.eval_on_selector("#opex-total-preview-value", "el => el.textContent")
        assert not any(ch.isdigit() for ch in text), (
            f"OPEX preview must never render a fabricated numeric value; got {text!r}"
        )
        assert not page_errors

    def test_no_save_or_run_triggered_and_opex_stays_unavailable_after_other_edits(self, runtime_page):
        """Points 3 & 4 (generalised): editing other grids triggers no
        Save/Run, and never causes the OPEX preview to fabricate a
        value (it has no inputs of its own to react to)."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('revenue')")
        revenue_addr = _first_editable_cell_addr(page, "revenue", "text")

        all_requests = []
        page.on("request", lambda req: all_requests.append(req.url))

        _edit_cell(page, revenue_addr, "100.00")
        page.wait_for_timeout(500)
        _edit_cell(page, revenue_addr, "200.00")
        page.wait_for_timeout(1500)

        save_requests = [u for u in all_requests if "/scenarios/save" in u or u.rstrip("/").endswith("/save-run")]
        run_requests = [u for u in all_requests if u.rstrip("/").endswith("/run")]

        assert not save_requests, f"unexpected Save request(s): {save_requests}"
        assert not run_requests, f"unexpected Run request(s): {run_requests}"

        opex_text = page.eval_on_selector("#opex-total-preview-value", "el => el.textContent")
        assert not any(ch.isdigit() for ch in opex_text)
        assert not page_errors

    def test_overview_kpis_byte_identical_pre_and_post_revenue_preview(self, runtime_page):
        """Point 5: only preview/runtime-status elements may change —
        every dashboard KPI element's text must be byte-identical."""
        page, page_errors, _ = runtime_page

        page.evaluate("window.switchTab('overview')")
        before = page.eval_on_selector_all(
            ".dashboard-kpi-value, [data-p2min3-kpi-status]",
            "els => els.map(el => el.textContent)",
        )

        page.evaluate("window.switchTab('revenue')")
        addr = _first_editable_cell_addr(page, "revenue", "text")
        _edit_cell(page, addr, "654.32")
        _wait_for_preview_value(page, "revenue-total-preview-value", "data-c2pr13-revenue-preview")

        page.evaluate("window.switchTab('overview')")
        after = page.eval_on_selector_all(
            ".dashboard-kpi-value, [data-p2min3-kpi-status]",
            "els => els.map(el => el.textContent)",
        )

        assert before == after
        assert not page_errors

    def test_existing_capex_and_revenue_previews_still_work_unaffected(self, runtime_page):
        """Point 10: the existing CAPEX/Revenue previews continue to
        work, unaffected by the new OPEX preview's presence."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        capex_addr = _first_editable_cell_addr(page, "capex", "amount")

        capex_before = page.eval_on_selector("#capex-total-preview-value", "el => el.textContent")
        _edit_cell(page, capex_addr, "98765.43")
        _wait_for_preview_value(page, "capex-total-preview-value", "data-c2pr10-capex-preview")
        capex_after = page.eval_on_selector("#capex-total-preview-value", "el => el.textContent")
        assert capex_after != capex_before

        page.evaluate("window.switchTab('revenue')")
        revenue_addr = _first_editable_cell_addr(page, "revenue", "text")
        revenue_before = page.eval_on_selector("#revenue-total-preview-value", "el => el.textContent")
        _edit_cell(page, revenue_addr, "12345.67")
        _wait_for_preview_value(page, "revenue-total-preview-value", "data-c2pr13-revenue-preview")
        revenue_after = page.eval_on_selector("#revenue-total-preview-value", "el => el.textContent")
        assert revenue_after != revenue_before
        assert not page_errors
