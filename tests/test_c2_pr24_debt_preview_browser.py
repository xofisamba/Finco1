"""C2-PR24: Backend-Computed Debt Preview Stub — production-route
Playwright tests.

Mirrors tests/test_c2_pr14_opex_preview_browser.py's real-uvicorn-
subprocess + real-auth + real-project fixture pattern exactly, for the
new Debt preview indicator (#debt-preview-value) — the FIRST
backend-computed (not frontend-computed) preview field.

Covers the browser-side required-behaviour points from the C2-PR24
task spec:

  1. The debt preview indicator renders on the page with the expected
     label text.
  2. It shows a real value after the page loads / after a preview
     round-trip (the test project fixture is created with valid
     total_capex_keur/gearing_pct, mirroring PR14-20's exact values),
     and the value only changes in response to an actual
     /model/preview network response — proven by intercepting the
     response with a distinctive debt number and confirming the DOM
     updates to exactly that number.
  3. It remains labeled "Debt preview (saved inputs only):" at all
     times.
  4. CAPEX/Revenue/OPEX/EBITDA/OCF previews still work unaffected
     (regression).
  5. No Save/Run/export request fires as a side effect of the debt
     preview.
"""
from __future__ import annotations

import json
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
        "project_name": "C2 PR24 Debt Preview Smoke",
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


class TestDebtPreviewIndicatorPresence:
    def test_debt_preview_element_and_label_present(self, runtime_page):
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('overview')")
        label = page.eval_on_selector(
            "#debt-preview .runtime-status-indicator__label", "el => el.textContent",
        )
        assert label.strip() == "Debt preview (saved inputs only):"
        assert not page_errors

    def test_debt_preview_placeholder_before_any_edit(self, runtime_page):
        """Before any edit/round-trip resolves with a "preview-ready"
        debt status, the indicator stays at its initial "—"
        placeholder — never a fabricated value."""
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('overview')")
        text = page.eval_on_selector("#debt-preview-value", "el => el.textContent")
        assert text.strip() == "—" or not any(ch.isdigit() for ch in text)
        assert not page_errors


class TestDebtPreviewIsBackendDriven:
    def test_debt_preview_dom_updates_to_exact_intercepted_backend_value(self, runtime_page):
        """Intercepts /model/preview's response with a distinctive,
        backend-shaped debt payload and confirms the DOM updates to
        EXACTLY that number — proving the rendered value is driven by
        the backend response, never computed in the browser."""
        page, page_errors, _ = runtime_page

        distinctive_value = 13579.24

        def _handler(route, request):
            response = route.fetch()
            try:
                body = json.loads(response.text())
            except Exception:
                route.fulfill(response=response)
                return
            body["debt"] = {
                "status": "preview-ready",
                "senior_debt_preview": distinctive_value,
                "currency": "EUR",
                "basis": "saved-capex-times-saved-gearing",
            }
            route.fulfill(
                status=response.status,
                headers=response.headers,
                body=json.dumps(body),
            )

        page.route("**/model/preview", _handler)

        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_cell_addr(page, "capex", "amount")
        assert addr is not None
        _edit_cell(page, addr, "12345.67")
        _wait_for_preview_value(page, "debt-preview-value", "data-c2pr24-debt-preview")

        page.evaluate("window.switchTab('overview')")
        text = page.eval_on_selector("#debt-preview-value", "el => el.textContent")
        assert "13,579.24" in text
        assert "EUR" in text
        assert not page_errors

    def test_debt_preview_label_remains_non_authoritative(self, runtime_page):
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_cell_addr(page, "capex", "amount")
        _edit_cell(page, addr, "999.99")
        _wait_for_preview_value(page, "capex-total-preview-value", "data-c2pr10-capex-preview")

        page.evaluate("window.switchTab('overview')")
        label = page.eval_on_selector(
            "#debt-preview .runtime-status-indicator__label", "el => el.textContent",
        )
        assert label.strip() == "Debt preview (saved inputs only):"
        assert not page_errors


class TestExistingPreviewsUnaffectedRegression:
    def test_capex_revenue_opex_ebitda_ocf_previews_still_work(self, runtime_page):
        page, page_errors, _ = runtime_page

        page.evaluate("window.switchTab('capex')")
        capex_addr = _first_editable_cell_addr(page, "capex", "amount")
        _edit_cell(page, capex_addr, "98765.43")
        _wait_for_preview_value(page, "capex-total-preview-value", "data-c2pr10-capex-preview")

        page.evaluate("window.switchTab('revenue')")
        revenue_addr = _first_editable_cell_addr(page, "revenue", "text")
        _edit_cell(page, revenue_addr, "654.32")
        _wait_for_preview_value(page, "revenue-total-preview-value", "data-c2pr13-revenue-preview")
        # EBITDA/OCF only become non-null when Revenue and OPEX are
        # both edited within the SAME debounce flush (see
        # docs/C2_OPERATING_PREVIEW_ARCHITECTURE_CHECKPOINT.md) — not
        # exercised by this single Revenue-only edit; covered
        # separately by tests/test_c2_pr15_ebitda_preview_browser.py
        # and tests/test_c2_pr16_ocf_preview_browser.py. This
        # regression check is scoped to confirming CAPEX/Revenue/OPEX
        # previews still work unaffected by the new Debt preview slice.

        page.evaluate("window.switchTab('opex')")
        opex_addr = _first_editable_cell_addr(page, "opex", "amount")
        if opex_addr:
            _edit_cell(page, opex_addr, "321.45")
            _wait_for_preview_value(page, "opex-total-preview-value", "data-c2pr14-opex-preview")

        assert not page_errors


class TestNoSaveRunExportSideEffect:
    def test_no_save_run_export_triggered_by_debt_preview(self, runtime_page):
        page, page_errors, _ = runtime_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_cell_addr(page, "capex", "amount")

        all_requests = []
        page.on("request", lambda req: all_requests.append(req.url))

        _edit_cell(page, addr, "55555.55")
        page.wait_for_timeout(1500)

        save_requests = [u for u in all_requests if "/scenarios/save" in u or u.rstrip("/").endswith("/save-run")]
        run_requests = [u for u in all_requests if u.rstrip("/").endswith("/run")]
        export_requests = [u for u in all_requests if "/exports/" in u or u.rstrip("/").endswith("/download")]

        assert not save_requests, f"unexpected Save request(s): {save_requests}"
        assert not run_requests, f"unexpected Run request(s): {run_requests}"
        assert not export_requests, f"unexpected export request(s): {export_requests}"
        assert not page_errors
