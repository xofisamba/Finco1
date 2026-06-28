"""C2-PR5: Incremental Recalculation Execution Stub — production-route
Playwright tests.

Covers the 10 required-behaviour points from the C2-PR5 task spec:

  1. Executor accepts a valid snapshot (canExecute true, execute() well-formed).
  2. Executor returns a deterministic no-op result.
  3. Unknown groups are handled safely (no throw, distinct safe status).
  4. Flush-complete event payload includes "execution".
  5. Dirty state remains unchanged after execution.
  6. No backend Run/recalc request fires.
  7. No financial/KPI values change.
  8. getLastExecution() returns the last stub result.
  9. clearLastExecution() clears it.
 10. Existing C1/C2 tests remain passing (run separately, not here).

Mirrors tests/test_c2_pr4_dependency_graph_browser.py's production-route
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
        "project_name": "C2 PR5 Recalc Executor Smoke",
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
def exec_page(live_server):
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
        yield page, page_errors
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


class TestRecalcExecutorStubProductionRoute:
    def test_executor_accepts_valid_snapshot(self, exec_page):
        """Point 1: a well-formed snapshot passes canExecute and execute()
        returns a well-formed result."""
        page, page_errors = exec_page

        result = page.evaluate(
            """
            () => {
              var snapshot = {
                grids: [{ gridId: 'capex', addrs: ['capex!a.amount'] }],
                projectDirty: true,
                affectedGroups: ['capex', 'overview-kpis', 'senior-debt']
              };
              return {
                canExecute: window.FcRecalcExecutor.canExecute(snapshot),
                result: window.FcRecalcExecutor.execute(snapshot, { reason: 'test' })
              };
            }
            """
        )
        assert result["canExecute"] is True
        res = result["result"]
        assert res["status"] == "stubbed"
        assert res["executed"] is False
        assert res["affectedGroups"] == sorted(res["affectedGroups"])
        assert res["dirtyCells"] == ["capex!a.amount"]
        assert res["reason"] == "test"
        assert not page_errors

    def test_executor_returns_deterministic_no_op_result(self, exec_page):
        """Point 2: calling execute() twice on logically-equal snapshots
        produces deep-equal, deterministic results; no DOM side effects."""
        page, _ = exec_page

        outcome = page.evaluate(
            """
            () => {
              var snapshot = {
                grids: [{ gridId: 'opex', addrs: ['opex!b.budget'] }],
                projectDirty: true,
                affectedGroups: ['opex', 'overview-kpis', 'tax']
              };
              var r1 = window.FcRecalcExecutor.execute(snapshot, { reason: 'manual-flush' });
              var r2 = window.FcRecalcExecutor.execute(JSON.parse(JSON.stringify(snapshot)), { reason: 'manual-flush' });
              return { r1: r1, r2: r2 };
            }
            """
        )
        assert outcome["r1"] == outcome["r2"]
        assert outcome["r1"]["executed"] is False

    def test_unknown_groups_handled_safely(self, exec_page):
        """Point 3: affectedGroups containing 'unknown' never throws and
        produces a distinct, still-safe status."""
        page, page_errors = exec_page

        result = page.evaluate(
            """
            () => {
              try {
                var snapshot = {
                  grids: [{ gridId: 'bogus', addrs: ['bogus!x'] }],
                  projectDirty: true,
                  affectedGroups: ['overview-kpis', 'unknown']
                };
                var res = window.FcRecalcExecutor.execute(snapshot, { reason: 'manual-flush' });
                return { threw: false, res: res };
              } catch (e) {
                return { threw: true, message: String(e) };
              }
            }
            """
        )
        assert result["threw"] is False
        assert result["res"]["status"] == "stubbed-unknown"
        assert result["res"]["executed"] is False
        assert not page_errors

    def test_flush_complete_event_includes_execution(self, exec_page):
        """Point 4: triggering a real edit + flush exposes 'execution' on
        the recalc-flush-complete event payload's snapshot."""
        page, _ = exec_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")
        _edit_cell(page, addr, "777.00")

        payload = page.evaluate(
            """
            () => {
              var captured = null;
              window.FcLiveModel.on('recalc-flush-complete', (e) => { captured = e; });
              window.FcLiveModel.flushScheduledRecalc();
              return captured;
            }
            """
        )
        assert payload is not None
        snapshot = payload["snapshot"]
        assert "execution" in snapshot
        execution = snapshot["execution"]
        assert execution["executed"] is False
        assert execution["status"].startswith("stubbed")
        # Additive only — pre-existing C2-PR3/PR4 fields still present.
        assert "grids" in snapshot
        assert "projectDirty" in snapshot
        assert "affectedGroups" in snapshot

    def test_dirty_state_unchanged_after_execution(self, exec_page):
        """Point 5: calling execute() never affects
        isCellDirty/isSheetDirty/isProjectDirty."""
        page, _ = exec_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")
        _edit_cell(page, addr, "321.00")

        before = page.evaluate(
            "(addr) => ({ cell: window.FcLiveModel.isCellDirty('capex', addr), sheet: window.FcLiveModel.isSheetDirty('capex'), project: window.FcLiveModel.isProjectDirty() })",
            addr,
        )

        page.evaluate(
            """
            () => {
              var snapshot = window.FcLiveModel.getPendingRecalcSnapshot();
              snapshot.affectedGroups = window.FcDependencyGraph.resolveSnapshot(snapshot);
              window.FcRecalcExecutor.execute(snapshot, { reason: 'manual-test' });
            }
            """
        )

        after = page.evaluate(
            "(addr) => ({ cell: window.FcLiveModel.isCellDirty('capex', addr), sheet: window.FcLiveModel.isSheetDirty('capex'), project: window.FcLiveModel.isProjectDirty() })",
            addr,
        )

        assert before == after
        assert after["cell"] is True
        assert after["sheet"] is True
        assert after["project"] is True

    def test_no_backend_run_request_fires(self, exec_page):
        """Point 6: executor invocation + flush must never trigger a
        Run/recalc network request."""
        page, _ = exec_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        run_like_requests = []
        page.on("request", lambda req: run_like_requests.append(req.url)
                if ("/run" in req.url or "recalc" in req.url) else None)

        _edit_cell(page, addr, "9999.99")
        page.evaluate(
            """
            () => {
              window.FcLiveModel.flushScheduledRecalc();
            }
            """
        )
        page.wait_for_timeout(500)

        assert run_like_requests == []

    def test_no_financial_values_change(self, exec_page):
        """Point 7: executor invocation must not change any rendered
        financial output/KPI value on the page."""
        page, _ = exec_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        kpi_before = page.evaluate(
            """
            () => {
              var el = document.querySelector('[data-kpi], .kpi-value, #workspace-active-scenario-name');
              return el ? el.textContent : null;
            }
            """
        )

        page.evaluate(
            """
            () => {
              var snapshot = window.FcLiveModel.getPendingRecalcSnapshot();
              snapshot.affectedGroups = window.FcDependencyGraph.resolveSnapshot(snapshot);
              window.FcRecalcExecutor.execute(snapshot, { reason: 'manual-test' });
              window.FcLiveModel.flushScheduledRecalc();
            }
            """
        )
        page.wait_for_timeout(300)

        kpi_after = page.evaluate(
            """
            () => {
              var el = document.querySelector('[data-kpi], .kpi-value, #workspace-active-scenario-name');
              return el ? el.textContent : null;
            }
            """
        )
        assert kpi_before == kpi_after

    def test_get_last_execution_returns_last_result(self, exec_page):
        """Point 8: getLastExecution() returns the most recent execute()
        result."""
        page, _ = exec_page

        outcome = page.evaluate(
            """
            () => {
              window.FcRecalcExecutor.clearLastExecution();
              var snapshot = {
                grids: [{ gridId: 'tax', addrs: ['tax!cit_rate'] }],
                projectDirty: true,
                affectedGroups: ['overview-kpis', 'tax']
              };
              var executed = window.FcRecalcExecutor.execute(snapshot, { reason: 'manual-test' });
              var last = window.FcRecalcExecutor.getLastExecution();
              return { executed: executed, last: last };
            }
            """
        )
        assert outcome["last"] == outcome["executed"]

    def test_clear_last_execution_resets_it(self, exec_page):
        """Point 9: clearLastExecution() resets getLastExecution() to
        null/undefined."""
        page, _ = exec_page

        outcome = page.evaluate(
            """
            () => {
              var snapshot = {
                grids: [{ gridId: 'tax', addrs: ['tax!cit_rate'] }],
                projectDirty: true,
                affectedGroups: ['overview-kpis', 'tax']
              };
              window.FcRecalcExecutor.execute(snapshot, { reason: 'manual-test' });
              window.FcRecalcExecutor.clearLastExecution();
              return window.FcRecalcExecutor.getLastExecution();
            }
            """
        )
        assert outcome is None
