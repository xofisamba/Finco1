"""C2-PR7: Backend Preview Endpoint Contract Stub — production-route
Playwright tests.

Covers the 2 required browser-safety points from the C2-PR7 task spec:

  10. Normal edit/flush still does NOT call the new backend preview
      endpoint (network monitoring confirms zero requests to
      /model/preview during a real edit+flush+preview-build sequence).
  11. Client CAN build request metadata via
      FcRecalcPreview.buildPreviewRequest() without it ever being
      sent (direct call returns the expected shape; network
      monitoring confirms zero requests result from calling it).

Mirrors tests/test_c2_pr6_recalc_preview_browser.py's production-route
pattern: real uvicorn subprocess, real auth, real project creation.
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
        "project_name": "C2 PR7 Backend Preview Smoke",
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
def preview_page(live_server):
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


def _first_editable_amount_addr(page, grid_id, kind="amount"):
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


class TestBackendPreviewEndpointBrowserSafety:
    def test_edit_and_flush_never_calls_backend_preview_endpoint(self, preview_page):
        """Point 10: a real edit + flush + preview-payload-build
        sequence must fire zero requests to /model/preview (or any
        other path containing "preview")."""
        page, _, _ = preview_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        all_requests = []
        page.on("request", lambda req: all_requests.append(req.url))

        _edit_cell(page, addr, "4242.42")
        page.evaluate(
            """
            () => {
              window.FcLiveModel.flushScheduledRecalc();
              var snapshot = window.FcLiveModel.getPendingRecalcSnapshot();
              snapshot.affectedGroups = window.FcDependencyGraph.resolveSnapshot(snapshot);
              var execution = window.FcRecalcExecutor.execute(snapshot, { reason: 'manual-test' });
              window.FcRecalcPreview.buildPreviewPayload(snapshot, execution, { reason: 'manual-test' });
            }
            """
        )
        page.wait_for_timeout(500)

        preview_endpoint_requests = [
            url for url in all_requests
            if "/model/preview" in url or "preview" in url.lower()
        ]
        assert preview_endpoint_requests == []

    def test_build_preview_request_returns_shape_without_sending(self, preview_page):
        """Point 11: FcRecalcPreview.buildPreviewRequest() returns the
        expected request-shaped object, and calling it produces zero
        network requests."""
        page, page_errors, _ = preview_page

        all_requests = []
        page.on("request", lambda req: all_requests.append(req.url))

        result = page.evaluate(
            """
            () => {
              var snapshot = {
                grids: [{ gridId: 'capex', addrs: ['capex!a.amount'] }],
                projectDirty: true,
                affectedGroups: ['overview-kpis', 'capex']
              };
              var execution = window.FcRecalcExecutor.execute(snapshot, { reason: 'manual-test' });
              var payload = window.FcRecalcPreview.buildPreviewPayload(snapshot, execution, { reason: 'manual-test' });
              var request = window.FcRecalcPreview.buildPreviewRequest(payload);
              return {
                request: request,
                endpointMetadata: window.FcRecalcPreview.previewEndpoint,
                payload: payload
              };
            }
            """
        )
        page.wait_for_timeout(300)

        request = result["request"]
        assert request["url"] == "/model/preview"
        assert request["method"] == "POST"
        assert request["body"] == result["payload"]
        assert result["endpointMetadata"] == "/model/preview"

        preview_endpoint_requests = [
            url for url in all_requests
            if "/model/preview" in url or "preview" in url.lower()
        ]
        assert preview_endpoint_requests == []
        assert not page_errors
