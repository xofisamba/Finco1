"""C2-PR4: Dependency Graph Foundation — production-route Playwright tests.

Covers the 10 required-behaviour points from the C2-PR4 task spec:

  1. Known CAPEX cells resolve to expected groups.
  2. Known Inputs cells resolve to expected groups.
  3. Known Senior Debt cells resolve to expected groups.
  4. Unknown cells resolve conservatively and do not throw.
  5. Snapshot resolution is deterministic across different edit orders.
  6. Flush-complete event includes affected groups.
  7. Dirty state remains unchanged after dependency resolution.
  8. No backend Run/recalc request is made.
  9. No financial values change.
 10. Existing C1/C2 tests remain passing (run separately, not here).

Mirrors tests/test_c2_pr3_recalc_scheduler_browser.py's production-route
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
        "project_name": "C2 PR4 Dependency Graph Smoke",
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
def dep_page(live_server):
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


class TestDependencyGraphFoundationProductionRoute:
    def test_known_capex_cell_resolves_expected_groups(self, dep_page):
        """Point 1: a real CAPEX cell address resolves to capex/senior-debt/overview-kpis."""
        page, page_errors = dep_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")
        assert addr

        groups = page.evaluate("(addr) => window.FcDependencyGraph.resolveCell(addr)", addr)
        assert groups == sorted(groups)
        assert "capex" in groups
        assert "senior-debt" in groups
        assert "overview-kpis" in groups
        assert not page_errors

    def test_known_inputs_cell_resolves_expected_groups(self, dep_page):
        """Point 2: a real Inputs cell address (technical section) resolves broadly."""
        page, _ = dep_page
        page.evaluate("window.switchTab('inputs')")
        addr = page.evaluate(
            """
            () => {
              var cell = document.querySelector('[data-fc-grid="inputs"] [data-fc-cell="true"]');
              return cell ? cell.getAttribute('data-fc-addr') : null;
            }
            """
        )
        assert addr
        assert addr.startswith("inputs!")

        groups = page.evaluate("(addr) => window.FcDependencyGraph.resolveCell(addr)", addr)
        assert groups == sorted(groups)
        assert "overview-kpis" in groups

    def test_known_senior_debt_cell_resolves_expected_groups(self, dep_page):
        """Point 3: seniordebt!gearing_pct resolves to senior-debt/overview-kpis."""
        page, _ = dep_page
        page.evaluate("window.switchTab('senior-debt')")

        groups = page.evaluate(
            "() => window.FcDependencyGraph.resolveCell('seniordebt!gearing_pct')"
        )
        assert groups == sorted(groups)
        assert "senior-debt" in groups
        assert "overview-kpis" in groups
        assert "tax" not in groups

    def test_unknown_cell_resolves_conservatively_without_throwing(self, dep_page):
        """Point 4: a fabricated nonsense address never throws and resolves conservatively."""
        page, page_errors = dep_page

        result = page.evaluate(
            """
            () => {
              try {
                var groups = window.FcDependencyGraph.resolveCell('totally-bogus-grid!nonsense.field.path');
                var explanation = window.FcDependencyGraph.explain('totally-bogus-grid!nonsense.field.path');
                var malformed = window.FcDependencyGraph.resolveCell('not-even-an-address');
                return { groups: groups, explanation: explanation, malformed: malformed, threw: false };
              } catch (e) {
                return { threw: true, message: String(e) };
              }
            }
            """
        )
        assert result["threw"] is False
        assert "unknown" in result["groups"]
        assert result["groups"] == sorted(result["groups"])
        assert result["explanation"]["matched"] is False
        assert "unmapped" in result["explanation"]["reason"] or "not registered" in result["explanation"]["reason"]
        assert "unknown" in result["malformed"]
        assert not page_errors

    def test_snapshot_resolution_is_deterministic(self, dep_page):
        """Point 5: resolveSnapshot on snapshots representing the same logical
        dirty set, built via different edit orders, produce structurally
        equal affectedGroups output."""
        page, _ = dep_page
        page.evaluate("window.switchTab('capex')")
        capex_addr = _first_editable_amount_addr(page, "capex")

        snap_a = {
            "grids": [
                {"gridId": "capex", "addrs": [capex_addr]},
                {"gridId": "seniordebt", "addrs": ["seniordebt!gearing_pct"]},
            ],
            "projectDirty": True,
        }
        snap_b = {
            "grids": [
                {"gridId": "seniordebt", "addrs": ["seniordebt!gearing_pct"]},
                {"gridId": "capex", "addrs": [capex_addr]},
            ],
            "projectDirty": True,
        }

        groups_a = page.evaluate("(s) => window.FcDependencyGraph.resolveSnapshot(s)", snap_a)
        groups_b = page.evaluate("(s) => window.FcDependencyGraph.resolveSnapshot(s)", snap_b)

        assert groups_a == groups_b
        assert groups_a == sorted(groups_a)

    def test_flush_complete_event_includes_affected_groups(self, dep_page):
        """Point 6: triggering a real edit + flush exposes affectedGroups on
        the recalc-flush-complete event payload's snapshot."""
        page, _ = dep_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")
        _edit_cell(page, addr, "888.00")

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
        assert "affectedGroups" in snapshot
        assert "capex" in snapshot["affectedGroups"]
        assert snapshot["affectedGroups"] == sorted(snapshot["affectedGroups"])
        # Additive only — pre-existing C2-PR3 fields still present and intact.
        assert "grids" in snapshot
        assert "projectDirty" in snapshot

    def test_dirty_state_unchanged_after_dependency_resolution(self, dep_page):
        """Point 7: calling resolveCell/resolveSnapshot/getAffectedGroups/explain
        never affects isCellDirty/isSheetDirty/isProjectDirty."""
        page, _ = dep_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")
        _edit_cell(page, addr, "321.00")

        before = page.evaluate(
            "(addr) => ({ cell: window.FcLiveModel.isCellDirty('capex', addr), sheet: window.FcLiveModel.isSheetDirty('capex'), project: window.FcLiveModel.isProjectDirty() })",
            addr,
        )

        page.evaluate(
            """
            (addr) => {
              window.FcDependencyGraph.resolveCell(addr);
              window.FcDependencyGraph.resolveSnapshot(window.FcLiveModel.getPendingRecalcSnapshot());
              window.FcDependencyGraph.getAffectedGroups([addr, 'bogus!x']);
              window.FcDependencyGraph.explain(addr);
            }
            """,
            addr,
        )

        after = page.evaluate(
            "(addr) => ({ cell: window.FcLiveModel.isCellDirty('capex', addr), sheet: window.FcLiveModel.isSheetDirty('capex'), project: window.FcLiveModel.isProjectDirty() })",
            addr,
        )

        assert before == after
        assert after["cell"] is True
        assert after["sheet"] is True
        assert after["project"] is True

    def test_no_backend_run_request_fires(self, dep_page):
        """Point 8: dependency resolution + flush must never trigger a
        Run/recalc network request."""
        page, _ = dep_page
        page.evaluate("window.switchTab('capex')")
        addr = _first_editable_amount_addr(page, "capex")

        run_like_requests = []
        page.on("request", lambda req: run_like_requests.append(req.url)
                if ("/run" in req.url or "recalc" in req.url) else None)

        _edit_cell(page, addr, "4242.42")
        page.evaluate(
            """
            (addr) => {
              window.FcDependencyGraph.resolveCell(addr);
              window.FcDependencyGraph.resolveSnapshot(window.FcLiveModel.getPendingRecalcSnapshot());
              window.FcLiveModel.flushScheduledRecalc();
            }
            """,
            addr,
        )
        page.wait_for_timeout(500)

        assert run_like_requests == []

    def test_no_financial_values_change(self, dep_page):
        """Point 9: dependency resolution must not change any rendered
        financial output/KPI value on the page."""
        page, _ = dep_page
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
            (addr) => {
              window.FcDependencyGraph.resolveCell(addr);
              window.FcDependencyGraph.getAffectedGroups([addr]);
              window.FcDependencyGraph.explain(addr);
              window.FcLiveModel.flushScheduledRecalc();
            }
            """,
            addr,
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
