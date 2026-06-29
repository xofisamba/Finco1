"""C2-PR20: Operating Preview Acceptance Test — one comprehensive
real-route Playwright acceptance test for the full operating preview
stack (CAPEX/Revenue/OPEX/EBITDA/Operating Cash Flow), end to end.

Uses the same real-uvicorn-subprocess + real-auth + real-project
fixture pattern as tests/test_c2_pr16_ocf_preview_browser.py (copied
verbatim), the "switch tab, edit, switch tab, edit" pattern from
test_ocf_chains_through_revenue_opex_ebitda for getting Revenue+OPEX
edits into the same debounce flush, and the
_install_failing_preview/_wait_for_runtime_state helper pattern from
tests/test_c2_pr15_ebitda_preview_browser.py.
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
        "project_name": "C2 PR20 Operating Preview Acceptance",
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


def _parse_numeric(text):
    cleaned = text.replace(",", "").replace("EUR", "").strip()
    return float(cleaned)


class TestOperatingPreviewAcceptance:
    def test_full_capex_revenue_opex_ebitda_ocf_chain_end_to_end(self, runtime_page):
        page, page_errors, project_code = runtime_page

        all_requests = []
        page.on("request", lambda req: all_requests.append(req.url))

        page.evaluate("window.switchTab('overview')")
        kpis_before = page.eval_on_selector_all(
            ".dashboard-kpi-value, [data-p2min3-kpi-status]",
            "els => els.map(el => el.textContent)",
        )

        # Edit CAPEX.
        page.evaluate("window.switchTab('capex')")
        capex_addr = _first_editable_cell_addr(page, "capex", "amount")
        assert capex_addr is not None
        _edit_cell(page, capex_addr, "42000.00")
        _wait_for_preview_value(page, "capex-total-preview-value", "data-c2pr10-capex-preview")

        # Edit OPEX, then Revenue immediately after — same debounce
        # flush, so EBITDA preview becomes non-null too.
        page.evaluate("window.switchTab('opex')")
        opex_addr = _first_editable_cell_addr(page, "opex", "amount")
        assert opex_addr is not None
        page.evaluate("window.switchTab('revenue')")
        revenue_addr = _first_editable_cell_addr(page, "revenue", "text")
        assert revenue_addr is not None

        page.evaluate("window.switchTab('opex')")
        _edit_cell(page, opex_addr, "750.00")
        page.evaluate("window.switchTab('revenue')")
        _edit_cell(page, revenue_addr, "2250.00")

        _wait_for_preview_value(page, "opex-total-preview-value", "data-c2pr14-opex-preview")
        _wait_for_preview_value(page, "ebitda-preview-value", "data-c2pr15-ebitda-preview")
        _wait_for_preview_value(page, "operating-cf-preview-value", "data-c2pr16-ocf-preview")

        capex_text = page.eval_on_selector("#capex-total-preview-value", "el => el.textContent")
        revenue_text = page.eval_on_selector("#revenue-total-preview-value", "el => el.textContent")
        opex_text = page.eval_on_selector("#opex-total-preview-value", "el => el.textContent")
        ebitda_text = page.eval_on_selector("#ebitda-preview-value", "el => el.textContent")
        ocf_text = page.eval_on_selector("#operating-cf-preview-value", "el => el.textContent")

        assert any(ch.isdigit() for ch in capex_text), f"CAPEX preview not numeric: {capex_text!r}"
        assert any(ch.isdigit() for ch in revenue_text), f"Revenue preview not numeric: {revenue_text!r}"
        assert any(ch.isdigit() for ch in opex_text), f"OPEX preview not numeric: {opex_text!r}"
        assert any(ch.isdigit() for ch in ebitda_text), f"EBITDA preview not numeric: {ebitda_text!r}"
        assert any(ch.isdigit() for ch in ocf_text), f"OCF preview not numeric: {ocf_text!r}"

        revenue_value = _parse_numeric(revenue_text)
        opex_value = _parse_numeric(opex_text)
        ebitda_value = _parse_numeric(ebitda_text)
        assert abs(ebitda_value - (revenue_value - opex_value)) < 0.05, (
            f"expected EBITDA preview ({ebitda_value}) to equal Revenue "
            f"preview ({revenue_value}) minus OPEX preview ({opex_value})"
        )
        assert ocf_text == ebitda_text, (
            f"expected Operating Cash Flow preview to equal EBITDA preview "
            f"verbatim; got ocf={ocf_text!r} ebitda={ebitda_text!r}"
        )

        # No Save or Run request fired.
        save_requests = [u for u in all_requests if "/scenarios/save" in u or u.rstrip("/").endswith("/save-run")]
        run_requests = [u for u in all_requests if u.rstrip("/").endswith("/run")]
        assert not save_requests, f"unexpected Save request(s): {save_requests}"
        assert not run_requests, f"unexpected Run request(s): {run_requests}"

        # Workspace dirty-state indicator still showing dirty.
        strip_text = page.eval_on_selector("#workspace-strip-dirty", "el => el.textContent.trim()")
        assert "unsaved" in strip_text.lower(), (
            f"expected dirty-state strip to still read 'unsaved', got {strip_text!r}"
        )

        # Overview KPIs unchanged from pre-edit baseline (byte-identical).
        page.evaluate("window.switchTab('overview')")
        kpis_after = page.eval_on_selector_all(
            ".dashboard-kpi-value, [data-p2min3-kpi-status]",
            "els => els.map(el => el.textContent)",
        )
        assert kpis_after == kpis_before, (
            "Overview KPI values must be byte-identical pre- and post-preview-edit"
        )

        # All five preview values are labeled "(unsaved)" (or, for OCF,
        # the equivalent more-explicit "non-authoritative" wording).
        label_selectors = [
            "#capex-total-preview .runtime-status-indicator__label",
            "#revenue-total-preview .runtime-status-indicator__label",
            "#opex-total-preview .runtime-status-indicator__label",
            "#ebitda-preview .runtime-status-indicator__label",
            "#operating-cf-preview .runtime-status-indicator__label",
        ]
        for selector in label_selectors:
            label_text = page.eval_on_selector(selector, "el => el.textContent")
            assert "(unsaved)" in label_text, (
                f"expected {selector!r} label to contain '(unsaved)', got {label_text!r}"
            )

        assert not page_errors

    def test_failed_preview_request_preserves_last_valid_values(self, runtime_page):
        page, page_errors, project_code = runtime_page

        # First, establish valid preview values for all five indicators.
        page.evaluate("window.switchTab('capex')")
        capex_addr = _first_editable_cell_addr(page, "capex", "amount")
        _edit_cell(page, capex_addr, "55555.55")
        _wait_for_preview_value(page, "capex-total-preview-value", "data-c2pr10-capex-preview")

        page.evaluate("window.switchTab('opex')")
        opex_addr = _first_editable_cell_addr(page, "opex", "amount")
        page.evaluate("window.switchTab('revenue')")
        revenue_addr = _first_editable_cell_addr(page, "revenue", "text")

        page.evaluate("window.switchTab('opex')")
        _edit_cell(page, opex_addr, "800.00")
        page.evaluate("window.switchTab('revenue')")
        _edit_cell(page, revenue_addr, "2400.00")

        _wait_for_preview_value(page, "ebitda-preview-value", "data-c2pr15-ebitda-preview")
        _wait_for_preview_value(page, "operating-cf-preview-value", "data-c2pr16-ocf-preview")

        capex_before = page.eval_on_selector("#capex-total-preview-value", "el => el.textContent")
        revenue_before = page.eval_on_selector("#revenue-total-preview-value", "el => el.textContent")
        opex_before = page.eval_on_selector("#opex-total-preview-value", "el => el.textContent")
        ebitda_before = page.eval_on_selector("#ebitda-preview-value", "el => el.textContent")
        ocf_before = page.eval_on_selector("#operating-cf-preview-value", "el => el.textContent")

        # Now install a failing preview route and trigger another edit.
        _install_failing_preview(page)
        page.evaluate("window.switchTab('opex')")
        _edit_cell(page, opex_addr, "850.00")

        _wait_for_runtime_state(page, "failed", "opex-total-preview-value")

        capex_after = page.eval_on_selector("#capex-total-preview-value", "el => el.textContent")
        revenue_after = page.eval_on_selector("#revenue-total-preview-value", "el => el.textContent")
        opex_after = page.eval_on_selector("#opex-total-preview-value", "el => el.textContent")
        ebitda_after = page.eval_on_selector("#ebitda-preview-value", "el => el.textContent")
        ocf_after = page.eval_on_selector("#operating-cf-preview-value", "el => el.textContent")

        assert capex_after == capex_before, "CAPEX preview must not be blanked on a failed request"
        assert revenue_after == revenue_before, "Revenue preview must not be blanked on a failed request"
        assert opex_after == opex_before, "OPEX preview must not be blanked on a failed request"
        assert ebitda_after == ebitda_before, "EBITDA preview must not be blanked on a failed request"
        assert ocf_after == ocf_before, "OCF preview must not be blanked on a failed request"

        assert not page_errors
