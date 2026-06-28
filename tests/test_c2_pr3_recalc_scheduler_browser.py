"""C2-PR3: Recalculation Scheduler Foundation — production-route Playwright tests.

Covers the 11 required-behaviour points from the C2-PR3 task spec:

  1. Cell edit schedules recalculation (hasPendingRecalc() / 'recalc-scheduled').
  2. Rapid edits batch into one pending flush (no duplicate flush-start
     events for a debounce-window burst).
  3. Multiple sheets are tracked independently in the pending snapshot.
  4. Pending snapshot is deterministic (timestamp-free, sorted).
  5. Manual flush emits start/complete events in the correct order.
  6. Flush does not clear dirty state.
  7. Save/clean cancels pending recalc ('recalc-cancelled').
  8. Non-editable cell paste no-op does not schedule recalc.
  9. No backend Run request is made.
 10. No financial calculation function is called (no model-output change).
 11. Existing C1/C2 dirty-state tests still pass (run separately, not here).

Like tests/test_c2_pr2_dirty_state_unification_browser.py, this exercises
the REAL production route via a real `uvicorn` subprocess, real auth, and
real project creation.
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
        "project_name": "C2 PR3 Recalc Scheduler Smoke",
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
def sched_page(live_server):
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


class TestRecalcSchedulerFoundationProductionRoute:
    def test_cell_edit_schedules_recalc(self, sched_page):
        """Point 1: editing a cell schedules a recalc."""
        page, page_errors = sched_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")
        assert addr

        assert page.evaluate("window.FcLiveModel.hasPendingRecalc()") is False

        scheduled = page.evaluate(
            """
            () => {
              window.__fcRecalcScheduledEvents = [];
              window.FcLiveModel.on('recalc-scheduled', (e) => window.__fcRecalcScheduledEvents.push(e));
              return true;
            }
            """
        )
        assert scheduled is True

        _edit_cell(page, addr, "777.50")

        assert page.evaluate("window.FcLiveModel.hasPendingRecalc()") is True
        assert page.evaluate("window.__fcRecalcScheduledEvents.length") >= 1
        assert not page_errors

    def test_rapid_edits_batch_into_one_pending_flush(self, sched_page):
        """Point 2: a burst of rapid edits within the debounce window
        produces only one eventual flush-start, not one per edit."""
        page, _ = sched_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        page.evaluate(
            """
            () => {
              window.__fcFlushStarts = [];
              window.FcLiveModel.on('recalc-flush-start', (e) => window.__fcFlushStarts.push(e));
            }
            """
        )

        for value in ["10", "20", "30", "40"]:
            _edit_cell(page, addr, value)

        # Wait past the debounce window for the single auto-flush to fire.
        page.wait_for_timeout(600)

        assert page.evaluate("window.__fcFlushStarts.length") == 1

    def test_multiple_sheets_tracked_independently_in_snapshot(self, sched_page):
        """Point 3: pending snapshot tracks multiple dirty sheets independently."""
        page, _ = sched_page
        page.evaluate("window.switchTab('capex')")
        capex_addr = _first_editable_amount_addr(page, "capex")
        _edit_cell(page, capex_addr, "1111.11")

        page.evaluate("window.switchTab('senior-debt')")
        page.evaluate(
            """
            () => {
              var input = document.querySelector('[data-fc-addr="seniordebt!gearing_pct"] input');
              input.focus();
              input.value = '65';
              input.dispatchEvent(new Event('input', { bubbles: true }));
              input.dispatchEvent(new Event('change', { bubbles: true }));
            }
            """
        )

        snapshot = page.evaluate("window.FcLiveModel.getPendingRecalcSnapshot()")
        grid_ids = [g["gridId"] for g in snapshot["grids"]]
        assert "capex" in grid_ids
        assert "seniordebt" in grid_ids
        assert grid_ids == sorted(grid_ids)

    def test_pending_snapshot_is_deterministic(self, sched_page):
        """Point 4: two snapshots of the same logical dirty state
        (same dirty cells, different edit order) are structurally equal."""
        page, _ = sched_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")
        page.evaluate("window.switchTab('senior-debt')")

        _edit_cell(page, addr, "55.55")
        page.evaluate(
            """
            () => {
              var input = document.querySelector('[data-fc-addr="seniordebt!gearing_pct"] input');
              input.focus();
              input.value = '70';
              input.dispatchEvent(new Event('input', { bubbles: true }));
              input.dispatchEvent(new Event('change', { bubbles: true }));
            }
            """
        )

        snap1 = page.evaluate("window.FcLiveModel.getPendingRecalcSnapshot()")

        page.evaluate("window.FcLiveModel.clearAllDirty()")

        # Re-create same logical dirty state, opposite edit order.
        page.evaluate(
            """
            () => {
              var input = document.querySelector('[data-fc-addr="seniordebt!gearing_pct"] input');
              input.focus();
              input.value = '71';
              input.dispatchEvent(new Event('input', { bubbles: true }));
              input.dispatchEvent(new Event('change', { bubbles: true }));
            }
            """
        )
        _edit_cell(page, addr, "56.56")

        snap2 = page.evaluate("window.FcLiveModel.getPendingRecalcSnapshot()")

        assert snap1["grids"] == snap2["grids"]
        assert snap1["projectDirty"] == snap2["projectDirty"] is True

    def test_manual_flush_emits_start_then_complete(self, sched_page):
        """Point 5: flushScheduledRecalc() emits recalc-flush-start
        then recalc-flush-complete, in that order."""
        page, _ = sched_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")
        _edit_cell(page, addr, "42.00")

        order = page.evaluate(
            """
            () => {
              var order = [];
              window.FcLiveModel.on('recalc-flush-start', () => order.push('start'));
              window.FcLiveModel.on('recalc-flush-complete', () => order.push('complete'));
              var snapshot = window.FcLiveModel.flushScheduledRecalc();
              return { order: order, hasSnapshot: !!snapshot };
            }
            """
        )
        assert order["order"] == ["start", "complete"]
        assert order["hasSnapshot"] is True

    def test_flush_does_not_clear_dirty_state(self, sched_page):
        """Point 6: flushing leaves isCellDirty/isSheetDirty/isProjectDirty unchanged."""
        page, _ = sched_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")
        _edit_cell(page, addr, "99.00")

        assert page.evaluate("window.FcLiveModel.isProjectDirty()") is True
        page.evaluate("window.FcLiveModel.flushScheduledRecalc()")

        assert page.evaluate("(addr) => window.FcLiveModel.isCellDirty('capex', addr)", addr) is True
        assert page.evaluate("window.FcLiveModel.isSheetDirty('capex')") is True
        assert page.evaluate("window.FcLiveModel.isProjectDirty()") is True

    def test_save_cancels_pending_recalc(self, sched_page):
        """Point 7: a clearAllDirty()-driven Save flow cancels any
        scheduled-but-not-yet-flushed recalc."""
        page, _ = sched_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")
        _edit_cell(page, addr, "123.45")
        assert page.evaluate("window.FcLiveModel.hasPendingRecalc()") is True

        cancelled = page.evaluate(
            """
            () => {
              var events = [];
              window.FcLiveModel.on('recalc-cancelled', (e) => events.push(e));
              window.FcLiveModel.clearAllDirty();
              return events.length;
            }
            """
        )
        assert cancelled >= 1
        assert page.evaluate("window.FcLiveModel.hasPendingRecalc()") is False

    def test_non_editable_cell_no_op_does_not_schedule_recalc(self, sched_page):
        """Point 8: a write attempt against a non-editable cell never schedules a recalc."""
        page, page_errors = sched_page
        page.evaluate("window.switchTab('senior-debt')")

        page.evaluate(
            """
            () => {
              var cell = window.FcGridRegistry.getAddr('seniordebt', 'seniordebt!facility_amount');
              window.FcCellIO.writeValue(cell, '999999');
            }
            """
        )

        assert page.evaluate("window.FcLiveModel.hasPendingRecalc()") is False
        assert not page_errors

    def test_no_backend_run_request_fires(self, sched_page):
        """Point 9: editing + flushing must never trigger a Run/recalc network request."""
        page, _ = sched_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        run_like_requests = []
        page.on("request", lambda req: run_like_requests.append(req.url)
                if ("/run" in req.url or "recalc" in req.url) else None)

        _edit_cell(page, addr, "3333.33")
        page.evaluate("window.FcLiveModel.flushScheduledRecalc()")
        page.wait_for_timeout(500)

        assert run_like_requests == []

    def test_no_financial_output_changes_from_schedule_and_flush(self, sched_page):
        """Point 10: scheduling and flushing a recalc must not change any
        rendered financial output value — no calculation occurs."""
        page, _ = sched_page
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

        _edit_cell(page, addr, "456.78")
        page.evaluate("window.FcLiveModel.flushScheduledRecalc()")
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
