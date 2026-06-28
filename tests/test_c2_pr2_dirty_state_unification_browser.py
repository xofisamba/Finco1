"""C2-PR2: Dirty-State Unification — production-route Playwright tests.

Covers the 11 required-behaviour points from the C2-PR2 task spec:

  1. Editable C1 cell edit marks FcLiveModel dirty.
  2. Existing dirty banner still updates (now driven by FcLiveModel via
     the new app.js _syncDirtyFromLiveModel overlay).
  3. Run gating still behaves exactly as before (disabled while dirty).
  4. Save clears dirty state (both the legacy banner/meta and
     FcLiveModel, via the new applyWorkspaceStateMeta -> clearAllDirty
     hook).
  5. Non-editable paste no-ops do not mark dirty.
  6. Undo updates dirty state per the documented conservative decision
     (re-editing through FcCellIO.writeValue re-fires `change`, so
     FcLiveModel still reports the cell dirty after an undo — dirty
     state is not auto-cleared on revert-to-baseline; see
     docs/C2_PR2_DIRTY_STATE_UNIFICATION_NOTE.md).
  7. Multiple sheets can be dirty independently (FcLiveModel
     isSheetDirty stays scoped per-grid, pre-existing C2-PR1 behaviour,
     re-verified here against the real production route).
  8. clearAllDirty() clears project dirty state.
  9. No recalculation occurs (editing a cell must not fire any
     /run-shaped network request).

Like tests/test_capex_c1_migration_browser.py, this exercises the REAL
production route via a real `uvicorn` subprocess (not `file://`), to
avoid the asyncio/Playwright-sync-API conflict of importing main_web
directly in this process.
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
        "project_name": "C2 PR2 Dirty State Smoke",
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
def dirty_page(live_server):
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


class TestDirtyStateUnificationProductionRoute:
    def test_editable_cell_edit_marks_live_model_dirty(self, dirty_page):
        """Point 1: editable C1 cell edit marks FcLiveModel dirty."""
        page, page_errors = dirty_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")
        assert addr

        assert page.evaluate("(addr) => window.FcLiveModel.isCellDirty('capex', addr)", addr) is False
        _edit_cell(page, addr, "777.50")
        assert page.evaluate("(addr) => window.FcLiveModel.isCellDirty('capex', addr)", addr) is True
        assert page.evaluate("window.FcLiveModel.isSheetDirty('capex')") is True
        assert page.evaluate("window.FcLiveModel.isProjectDirty()") is True
        assert not page_errors

    def test_dirty_banner_updates_from_live_model(self, dirty_page):
        """Point 2: the existing dirty banner reflects a C1 grid edit,
        even though that cell lives outside #main-form and is therefore
        invisible to the legacy server-snapshot-diff dirty mechanism on
        its own — proof the unification overlay (app.js
        _syncDirtyFromLiveModel) is wired correctly."""
        page, _ = dirty_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        banner_hidden_before = page.evaluate(
            "!!document.getElementById('workspace-unsaved-banner').classList.contains('is-hidden')"
        )
        assert banner_hidden_before is True

        _edit_cell(page, addr, "888.25")

        banner_hidden_after = page.evaluate(
            "!!document.getElementById('workspace-unsaved-banner').classList.contains('is-hidden')"
        )
        assert banner_hidden_after is False

    def test_run_gating_disabled_while_dirty(self, dirty_page):
        """Point 3: Run gating still behaves exactly as before — the
        Run button is disabled while the workspace is dirty."""
        page, _ = dirty_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        run_disabled_before = page.evaluate(
            "document.getElementById('btn-run-model-sidebar').disabled"
        )
        assert run_disabled_before is False

        _edit_cell(page, addr, "999.00")

        run_disabled_after = page.evaluate(
            "document.getElementById('btn-run-model-sidebar').disabled"
        )
        assert run_disabled_after is True

    def test_save_clears_dirty_state(self, dirty_page):
        """Point 4: Save clears dirty state. /scenarios/save's htmx
        response only ever swaps #saved-scenario-panel (the saved-
        scenario summary cards) — it does not call
        applyWorkspaceStateMeta and never touches the banner element
        directly, exactly as before this change. What C2-PR2 adds is a
        successful-Save hook that clears FcLiveModel's canonical dirty
        state (see static/app.js's btn-save 'htmx:afterRequest'
        listener), which in turn re-syncs the banner/Run-gating via the
        existing 'project-clean' pub/sub event."""
        page, _ = dirty_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")
        _edit_cell(page, addr, "123.45")
        assert page.evaluate("window.FcLiveModel.isProjectDirty()") is True
        assert page.evaluate(
            "document.getElementById('btn-run-model-sidebar').disabled"
        ) is True

        with page.expect_response(lambda r: "/scenarios/save" in r.url):
            page.click("#btn-save")
        page.wait_for_timeout(250)

        assert page.evaluate("window.FcLiveModel.isProjectDirty()") is False
        assert page.evaluate(
            "document.getElementById('btn-run-model-sidebar').disabled"
        ) is False

    def test_non_editable_cell_no_op_does_not_mark_dirty(self, dirty_page):
        """Point 5: a write attempt against a non-editable cell must
        never create dirty state. FcCellIO.writeValue itself no-ops for
        !cell.editable, so this directly exercises that guarantee via
        the real Senior Debt sheet's read-only facility_amount cell."""
        page, page_errors = dirty_page
        page.evaluate("window.switchTab('senior-debt')")

        before = page.evaluate(
            "document.querySelector('[data-fc-addr=\"seniordebt!facility_amount\"]').getAttribute('data-fc-raw')"
        )

        page.evaluate(
            """
            () => {
              var cell = window.FcGridRegistry.getAddr('seniordebt', 'seniordebt!facility_amount');
              window.FcCellIO.writeValue(cell, '999999');
            }
            """
        )

        after = page.evaluate(
            "document.querySelector('[data-fc-addr=\"seniordebt!facility_amount\"]').getAttribute('data-fc-raw')"
        )
        assert after == before, "writeValue must no-op against a non-editable cell"
        assert page.evaluate(
            "window.FcLiveModel.isCellDirty('seniordebt', 'seniordebt!facility_amount')"
        ) is False
        assert page.evaluate("window.FcLiveModel.isSheetDirty('seniordebt')") is False
        assert not page_errors

    def test_undo_keeps_cell_dirty_per_conservative_decision(self, dirty_page):
        """Point 6: undo reverts the value, but per the documented
        conservative baseline-clearing decision (no load-time-baseline
        plumbing exists today to detect "back to last-saved"), the cell
        remains reported dirty after an undo — because undo's revert
        write also flows through FcCellIO.writeValue -> `change` ->
        FcLiveModel.markCellDirty, exactly like any other edit."""
        page, _ = dirty_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")
        before_value = page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"] input').value", addr
        )

        _edit_cell(page, addr, "55555.55")
        assert page.evaluate("(addr) => window.FcLiveModel.isCellDirty('capex', addr)", addr) is True

        page.evaluate(
            """
            (addr) => {
              var input = document.querySelector('[data-fc-addr="' + addr + '"] input');
              input.dispatchEvent(new MouseEvent('click', { bubbles: true }));
              input.focus();
            }
            """,
            addr,
        )
        page.keyboard.press("Control+z")

        after_value = page.evaluate(
            "(addr) => document.querySelector('[data-fc-addr=\"' + addr + '\"] input').value", addr
        )
        assert after_value == before_value
        # Conservative decision: still dirty even though the value is
        # back at its pre-edit baseline.
        assert page.evaluate("(addr) => window.FcLiveModel.isCellDirty('capex', addr)", addr) is True

    def test_multiple_sheets_dirty_independently(self, dirty_page):
        """Point 7: multiple sheets can be dirty independently."""
        page, _ = dirty_page
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

        assert page.evaluate("window.FcLiveModel.isSheetDirty('capex')") is True
        assert page.evaluate("window.FcLiveModel.isSheetDirty('seniordebt')") is True
        assert page.evaluate("window.FcLiveModel.getDirtySheets().length") == 2

    def test_clear_all_dirty_clears_project_dirty(self, dirty_page):
        """Point 8: clearAllDirty() clears project dirty state (and the
        banner with it, via the project-clean pub/sub event)."""
        page, _ = dirty_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")
        _edit_cell(page, addr, "2222.22")
        assert page.evaluate("window.FcLiveModel.isProjectDirty()") is True

        page.evaluate("window.FcLiveModel.clearAllDirty()")

        assert page.evaluate("window.FcLiveModel.isProjectDirty()") is False
        assert page.evaluate("window.FcLiveModel.getDirtySheets().length") == 0

    def test_no_recalculation_request_fires_on_dirty_edit(self, dirty_page):
        """Point 9: editing a cell must not trigger any model-run
        network request — dirty-state tracking is purely client-side
        bookkeeping, never an implicit recalculation/Run."""
        page, _ = dirty_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        run_like_requests = []
        page.on("request", lambda req: run_like_requests.append(req.url)
                if ("/run" in req.url or "recalc" in req.url) else None)

        _edit_cell(page, addr, "3333.33")
        page.wait_for_timeout(500)

        assert run_like_requests == []
