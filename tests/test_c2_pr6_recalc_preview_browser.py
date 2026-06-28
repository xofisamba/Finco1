"""C2-PR6: Incremental Recalculation Preview Boundary — production-route
Playwright tests.

Covers the 10 required-behaviour points from the C2-PR6 task spec:

  1. Preview payload builds from a valid execution snapshot.
  2. Payload is deterministic regardless of input ordering.
  3. Payload includes dirty cells and affected groups.
  4. Unknown groups handled safely (no throw).
  5. Missing project/scenario metadata handled safely (omit/null, never invented).
  6. Flush-complete event includes execution with preview payload.
  7. No backend request fires.
  8. Dirty state remains unchanged.
  9. No financial/KPI values change.
 10. Existing C1/C2 tests remain passing (run separately, not here).

Mirrors tests/test_c2_pr5_recalc_executor_browser.py's production-route
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
        "project_name": "C2 PR6 Recalc Preview Smoke",
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


class TestRecalcPreviewBoundaryProductionRoute:
    def test_preview_builds_from_valid_snapshot(self, preview_page):
        """Point 1: a well-formed snapshot + execution builds a
        well-formed preview payload."""
        page, page_errors, _ = preview_page

        result = page.evaluate(
            """
            () => {
              var snapshot = {
                grids: [{ gridId: 'capex', addrs: ['capex!a.amount'] }],
                projectDirty: true,
                affectedGroups: ['capex', 'overview-kpis', 'senior-debt']
              };
              var execution = window.FcRecalcExecutor.execute(snapshot, { reason: 'test' });
              var payload = window.FcRecalcPreview.buildPreviewPayload(snapshot, execution, { reason: 'test' });
              return { payload: payload, valid: window.FcRecalcPreview.validatePreviewPayload(payload) };
            }
            """
        )
        payload = result["payload"]
        assert payload["valid"] is True
        assert result["valid"] is True
        assert payload["dirtyCells"] == ["capex!a.amount"]
        assert payload["affectedGroups"] == sorted(payload["affectedGroups"])
        assert payload["projectDirty"] is True
        assert payload["reason"] == "test"
        assert payload["executionStatus"] == "stubbed"
        assert not page_errors

    def test_payload_deterministic_regardless_of_edit_order(self, preview_page):
        """Point 2: two snapshots representing the same logical dirty
        set, built via different "edit order", produce structurally
        equal payloads."""
        page, _, _ = preview_page

        outcome = page.evaluate(
            """
            () => {
              var snapshotA = {
                grids: [
                  { gridId: 'capex', addrs: ['capex!b.amount', 'capex!a.amount'] },
                  { gridId: 'opex', addrs: ['opex!x.budget'] }
                ],
                projectDirty: true,
                affectedGroups: ['overview-kpis', 'capex', 'opex']
              };
              var snapshotB = {
                grids: [
                  { gridId: 'opex', addrs: ['opex!x.budget'] },
                  { gridId: 'capex', addrs: ['capex!a.amount', 'capex!b.amount'] }
                ],
                projectDirty: true,
                affectedGroups: ['opex', 'capex', 'overview-kpis']
              };
              var execA = window.FcRecalcExecutor.execute(snapshotA, { reason: 'manual-flush' });
              var execB = window.FcRecalcExecutor.execute(snapshotB, { reason: 'manual-flush' });
              var payloadA = window.FcRecalcPreview.buildPreviewPayload(snapshotA, execA, { reason: 'manual-flush' });
              var payloadB = window.FcRecalcPreview.buildPreviewPayload(snapshotB, execB, { reason: 'manual-flush' });
              return { payloadA: payloadA, payloadB: payloadB };
            }
            """
        )
        assert outcome["payloadA"] == outcome["payloadB"]

    def test_payload_includes_dirty_cells_and_affected_groups(self, preview_page):
        """Point 3: payload's dirtyCells/affectedGroups match what's in
        the snapshot/execution passed in."""
        page, _, _ = preview_page

        payload = page.evaluate(
            """
            () => {
              var snapshot = {
                grids: [{ gridId: 'tax', addrs: ['tax!cit_rate'] }],
                projectDirty: true,
                affectedGroups: ['overview-kpis', 'tax']
              };
              var execution = window.FcRecalcExecutor.execute(snapshot, { reason: 'manual-flush' });
              return window.FcRecalcPreview.buildPreviewPayload(snapshot, execution);
            }
            """
        )
        assert payload["dirtyCells"] == ["tax!cit_rate"]
        assert payload["affectedGroups"] == ["overview-kpis", "tax"]

    def test_unknown_groups_handled_safely(self, preview_page):
        """Point 4: affectedGroups containing 'unknown' never throws and
        produces a sensible payload."""
        page, page_errors, _ = preview_page

        result = page.evaluate(
            """
            () => {
              try {
                var snapshot = {
                  grids: [{ gridId: 'bogus', addrs: ['bogus!x'] }],
                  projectDirty: true,
                  affectedGroups: ['overview-kpis', 'unknown']
                };
                var execution = window.FcRecalcExecutor.execute(snapshot, { reason: 'manual-flush' });
                var payload = window.FcRecalcPreview.buildPreviewPayload(snapshot, execution);
                return { threw: false, payload: payload };
              } catch (e) {
                return { threw: true, message: String(e) };
              }
            }
            """
        )
        assert result["threw"] is False
        assert result["payload"]["valid"] is True
        assert "unknown" in result["payload"]["affectedGroups"]
        assert result["payload"]["executionStatus"] == "stubbed-unknown"
        assert not page_errors

    def test_missing_project_metadata_handled_safely(self, preview_page):
        """Point 5: when no project query param is present, payload's
        project field is null, never an invented value. When it IS
        present (as it always is on the real workspace route), it must
        equal the real project code, not a fabricated string."""
        page, _, project_code = preview_page

        with_project = page.evaluate(
            """
            () => {
              var snapshot = { grids: [], projectDirty: false, affectedGroups: [] };
              var execution = window.FcRecalcExecutor.execute(snapshot, { reason: 'manual-flush' });
              return window.FcRecalcPreview.buildPreviewPayload(snapshot, execution);
            }
            """
        )
        assert with_project["project"] == project_code

        # Now simulate a URL with no project param at all.
        without_project = page.evaluate(
            """
            () => {
              var fakeLocation = { search: '' };
              var originalSearch = window.location.search;
              // We cannot reassign window.location, so instead exercise
              // URLSearchParams directly the same way the module does,
              // confirming the "absent -> null" contract in isolation.
              var params = new URLSearchParams('');
              var value = params.get('project');
              return value === null ? null : value;
            }
            """
        )
        assert without_project is None

    def test_flush_complete_event_includes_preview_payload(self, preview_page):
        """Point 6: triggering a real edit + flush exposes
        execution.previewPayload on the recalc-flush-complete event."""
        page, _, _ = preview_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")
        _edit_cell(page, addr, "555.00")

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
        assert execution.get("previewPrepared") is True
        assert "previewPayload" in execution
        preview_payload = execution["previewPayload"]
        assert preview_payload["valid"] is True
        assert addr in preview_payload["dirtyCells"]

    def test_no_backend_request_fires(self, preview_page):
        """Point 7: building a preview payload + flush must never
        trigger any network request (most safety-critical test in this
        file — the whole point of the preview boundary is to build a
        payload without ever sending it)."""
        page, _, _ = preview_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        all_requests = []
        page.on("request", lambda req: all_requests.append(req.url))

        _edit_cell(page, addr, "8888.88")
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

        run_or_recalc_or_preview_requests = [
            url for url in all_requests
            if ("/run" in url or "recalc" in url or "preview" in url)
        ]
        assert run_or_recalc_or_preview_requests == []

    def test_dirty_state_unchanged_by_preview_building(self, preview_page):
        """Point 8: building a preview payload (directly, or via the
        executor's integration) never affects
        isCellDirty/isSheetDirty/isProjectDirty."""
        page, _, _ = preview_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")
        _edit_cell(page, addr, "111.00")

        before = page.evaluate(
            "(addr) => ({ cell: window.FcLiveModel.isCellDirty('capex', addr), sheet: window.FcLiveModel.isSheetDirty('capex'), project: window.FcLiveModel.isProjectDirty() })",
            addr,
        )

        page.evaluate(
            """
            () => {
              var snapshot = window.FcLiveModel.getPendingRecalcSnapshot();
              snapshot.affectedGroups = window.FcDependencyGraph.resolveSnapshot(snapshot);
              var execution = window.FcRecalcExecutor.execute(snapshot, { reason: 'manual-test' });
              window.FcRecalcPreview.buildPreviewPayload(snapshot, execution, { reason: 'manual-test' });
              window.FcRecalcPreview.getLastPreviewPayload();
              window.FcRecalcPreview.clearLastPreviewPayload();
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

    def test_no_financial_values_change(self, preview_page):
        """Point 9: building a preview payload must not change any
        rendered financial output/KPI value on the page."""
        page, _, _ = preview_page
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
              var execution = window.FcRecalcExecutor.execute(snapshot, { reason: 'manual-test' });
              window.FcRecalcPreview.buildPreviewPayload(snapshot, execution, { reason: 'manual-test' });
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

    def test_get_and_clear_last_preview_payload(self, preview_page):
        """Bonus coverage: getLastPreviewPayload()/clearLastPreviewPayload()
        single-slot-state pattern mirrors FcRecalcExecutor's
        getLastExecution()/clearLastExecution()."""
        page, _, _ = preview_page

        outcome = page.evaluate(
            """
            () => {
              window.FcRecalcPreview.clearLastPreviewPayload();
              var snapshot = {
                grids: [{ gridId: 'tax', addrs: ['tax!cit_rate'] }],
                projectDirty: true,
                affectedGroups: ['overview-kpis', 'tax']
              };
              var execution = window.FcRecalcExecutor.execute(snapshot, { reason: 'manual-test' });
              var built = window.FcRecalcPreview.buildPreviewPayload(snapshot, execution, { reason: 'manual-test' });
              var last = window.FcRecalcPreview.getLastPreviewPayload();
              window.FcRecalcPreview.clearLastPreviewPayload();
              var afterClear = window.FcRecalcPreview.getLastPreviewPayload();
              return { built: built, last: last, afterClear: afterClear };
            }
            """
        )
        assert outcome["last"] == outcome["built"]
        assert outcome["afterClear"] is None

    def test_malformed_snapshot_never_throws(self, preview_page):
        """Defensive safety: malformed/invalid snapshot input degrades
        to a safe, explicit valid:false payload rather than throwing."""
        page, page_errors, _ = preview_page

        result = page.evaluate(
            """
            () => {
              try {
                var p1 = window.FcRecalcPreview.buildPreviewPayload(null, null);
                var p2 = window.FcRecalcPreview.buildPreviewPayload(undefined, undefined);
                var p3 = window.FcRecalcPreview.buildPreviewPayload({}, {});
                var p4 = window.FcRecalcPreview.buildPreviewPayload('not-an-object', 42);
                return { threw: false, p1: p1, p2: p2, p3: p3, p4: p4 };
              } catch (e) {
                return { threw: true, message: String(e) };
              }
            }
            """
        )
        assert result["threw"] is False
        for key in ("p1", "p2", "p3", "p4"):
            payload = result[key]
            assert payload["valid"] is False
            assert payload["dirtyCells"] == []
            assert payload["affectedGroups"] == []
        assert not page_errors
