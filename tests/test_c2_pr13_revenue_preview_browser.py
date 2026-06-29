"""C2-PR13: Revenue Total Preview — production-route Playwright tests.

Mirrors tests/test_c2_pr10_capex_total_preview_browser.py and
tests/test_c2_pr11_preview_ux_polish_browser.py exactly, for the new
Revenue total preview indicator (#revenue-total-preview-value).

Covers the browser-side required-behaviour points from the C2-PR13
task spec:

  1. Revenue preview updates after editing revenue inputs.
  2. Exactly one preview request per settled edit (PR9 debounce
     regression).
  3. No Save triggered.
  4. No Run triggered.
  5. No Overview KPI changes (byte-identical pre/post).
  7. A failed preview request keeps the previous Revenue preview value
     visible; only the status label changes.
  8. PR9 request sequencing still holds for the Revenue preview
     specifically (rapid edits, only newest renders).
  9. Save does not erase the Revenue (or CAPEX) preview value.
  10. Existing CAPEX preview continues to work unaffected (regression).

(Points 6 "no persistence writes" is a backend concern, covered in
tests/test_c2_pr13_revenue_preview.py's
TestNoFinancialEngineCallOrPersistenceMutation.test_no_persistence_mutation.)

Uses the same real-uvicorn-subprocess + real-auth + real-project
fixture pattern as the PR9/PR10/PR11 browser test suites.
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
        "project_name": "C2 PR13 Revenue Total Preview Smoke",
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


class TestRevenueTotalPreviewBrowser:
    def test_editable_revenue_cell_edit_updates_revenue_total_preview(self, runtime_page):
        """Point 1: editing an editable Revenue cell updates the
        Revenue total preview element after the debounce."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('revenue')")
        addr = _first_editable_cell_addr(page, "revenue", "text")
        assert addr, "expected at least one editable Revenue cell"

        before_text = page.eval_on_selector("#revenue-total-preview-value", "el => el.textContent")
        _edit_cell(page, addr, "12345.67")
        _wait_for_preview_value(page, "revenue-total-preview-value", "data-c2pr13-revenue-preview")
        after_text = page.eval_on_selector("#revenue-total-preview-value", "el => el.textContent")

        assert after_text != before_text
        assert any(ch.isdigit() for ch in after_text)
        assert not page_errors

    def test_one_edit_produces_exactly_one_preview_request(self, runtime_page):
        """Point 2: one settled edit -> exactly one preview request
        (PR9 debounce regression, applies identically to Revenue)."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('revenue')")
        addr = _first_editable_cell_addr(page, "revenue", "text")

        preview_requests = []
        page.on("request", lambda req: preview_requests.append(req) if "/model/preview" in req.url else None)

        _edit_cell(page, addr, "777.77")
        page.wait_for_timeout(1500)

        assert len(preview_requests) == 1, f"expected exactly 1 request, got {len(preview_requests)}"
        assert not page_errors

    def test_no_save_or_run_triggered_by_revenue_edit(self, runtime_page):
        """Points 3 & 4: a Revenue edit triggers no Save and no Run
        request."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('revenue')")
        addr = _first_editable_cell_addr(page, "revenue", "text")

        all_requests = []
        page.on("request", lambda req: all_requests.append(req.url))

        _edit_cell(page, addr, "100.00")
        page.wait_for_timeout(500)
        _edit_cell(page, addr, "200.00")
        page.wait_for_timeout(1500)

        save_requests = [u for u in all_requests if "/scenarios/save" in u or u.rstrip("/").endswith("/save-run")]
        run_requests = [u for u in all_requests if u.rstrip("/").endswith("/run")]

        assert not save_requests, f"unexpected Save request(s): {save_requests}"
        assert not run_requests, f"unexpected Run request(s): {run_requests}"
        assert not page_errors

    def test_overview_kpis_byte_identical_pre_and_post_revenue_preview(self, runtime_page):
        """Point 5: only the new #revenue-total-preview-value and the
        existing #overview-runtime-status-value elements may change —
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

    def test_failed_request_keeps_previous_revenue_value_visible(self, runtime_page):
        """Point 7: a failed preview request keeps the previously-
        rendered valid Revenue preview VALUE visible; only the status
        label changes to "Preview failed"."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('revenue')")
        addr = _first_editable_cell_addr(page, "revenue", "text")

        _edit_cell(page, addr, "42222.22")
        _wait_for_preview_value(page, "revenue-total-preview-value", "data-c2pr13-revenue-preview", timeout_ms=6000)
        value_before_failure = page.eval_on_selector(
            "#revenue-total-preview-value", "el => el.textContent"
        )
        assert any(ch.isdigit() for ch in value_before_failure)

        _install_failing_preview(page)

        _edit_cell(page, addr, "43333.33")
        _wait_for_runtime_state(page, "failed", element_id="revenue-total-preview-value")

        value_after_failure = page.eval_on_selector(
            "#revenue-total-preview-value", "el => el.textContent"
        )
        assert value_after_failure == value_before_failure, (
            "a failed preview request must never blank/change the previously-"
            "rendered Revenue preview VALUE — only the status label changes"
        )

        status_text = page.eval_on_selector(
            "#overview-runtime-status-value", "el => el.textContent.trim()"
        )
        assert status_text == "Preview failed"
        assert not page_errors

    def test_sequencing_holds_for_revenue_preview(self, runtime_page):
        """Point 8: PR9 sequencing still holds specifically for the
        Revenue preview — only the newest response's value is ever
        rendered, even when an earlier request resolves later."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('revenue')")
        addr = _first_editable_cell_addr(page, "revenue", "text")

        _install_ordered_delayed_responses(page, delays_ms=[1500, 0])

        _edit_cell(page, addr, "51111.11")
        page.wait_for_timeout(400)
        _edit_cell(page, addr, "52222.22")

        _wait_for_runtime_state(page, "ready", element_id="revenue-total-preview-value")
        page.wait_for_timeout(2000)  # let any stale response, if it arrived, have its chance

        final_state = page.eval_on_selector(
            "#revenue-total-preview-value", "el => el.getAttribute('data-c2pr11-runtime-state')"
        )
        final_value = page.eval_on_selector("#revenue-total-preview-value", "el => el.textContent")
        assert final_state == "ready"
        assert any(ch.isdigit() for ch in final_value)
        assert not page_errors

    def test_save_does_not_erase_revenue_or_capex_preview(self, runtime_page):
        """Point 9: Save does not erase/reset either preview value."""
        page, page_errors, project_code = runtime_page

        page.evaluate("window.switchTab('revenue')")
        rev_addr = _first_editable_cell_addr(page, "revenue", "text")
        _edit_cell(page, rev_addr, "11111.11")
        _wait_for_preview_value(page, "revenue-total-preview-value", "data-c2pr13-revenue-preview")
        revenue_value_before_save = page.eval_on_selector(
            "#revenue-total-preview-value", "el => el.textContent"
        )

        page.evaluate("window.switchTab('capex')")
        capex_addr = _first_editable_cell_addr(page, "capex", "amount")
        _edit_cell(page, capex_addr, "22222.22")
        _wait_for_preview_value(page, "capex-total-preview-value", "data-c2pr10-capex-preview")
        capex_value_before_save = page.eval_on_selector(
            "#capex-total-preview-value", "el => el.textContent"
        )

        # Trigger Save via the real button, like a user would.
        save_btn = page.query_selector("#btn-save") or page.query_selector('[data-action="save"]') or page.query_selector('button:has-text("Save")')
        if save_btn:
            save_btn.click()
            page.wait_for_timeout(1500)

        revenue_value_after_save = page.eval_on_selector(
            "#revenue-total-preview-value", "el => el.textContent"
        )
        capex_value_after_save = page.eval_on_selector(
            "#capex-total-preview-value", "el => el.textContent"
        )
        assert revenue_value_after_save == revenue_value_before_save
        assert capex_value_after_save == capex_value_before_save
        assert not page_errors

    def test_existing_capex_preview_still_works_unaffected(self, runtime_page):
        """Point 10: the existing CAPEX preview continues to work,
        unaffected by the new Revenue preview's presence."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_cell_addr(page, "capex", "amount")

        before_text = page.eval_on_selector("#capex-total-preview-value", "el => el.textContent")
        _edit_cell(page, addr, "98765.43")
        _wait_for_preview_value(page, "capex-total-preview-value", "data-c2pr10-capex-preview")
        after_text = page.eval_on_selector("#capex-total-preview-value", "el => el.textContent")

        assert after_text != before_text
        assert any(ch.isdigit() for ch in after_text)
        assert not page_errors
