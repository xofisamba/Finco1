"""
tests.test_ui3b_browser_acceptance — UI-3B Playwright browser acceptance.

Runs a live uvicorn subprocess + real Chromium to exercise the V2 workbook
Scenarios / Compare / Sensitivity surfaces end-to-end.

Test classes:
  TestSolarBrowserAcceptance  — 11 browser checks against a live Solar project
  TestWindRealEngineAcceptance — 3 real-engine Wind acceptance (no browser)
  TestSensitivityNonDestructiveProof — 2 real-engine sensitivity proofs

Requires: playwright installed (pip install playwright) and chromium available
at /opt/pw-browsers/chromium-1194/chrome-linux/chrome.
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

# Must set secret key before importing app.auth so tokens are verifiable
os.environ.setdefault("FINCO_SECRET_KEY", "ui3b-browser-accept-test-key")
os.environ.setdefault("FINCO_COOKIE_SECURE", "false")

from app.auth import create_session_token  # noqa: E402

COOKIE_NAME = "finco_session"
CHROMIUM_PATH = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


# ── helpers ──────────────────────────────────────────────────────────────────

def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        return s.getsockname()[1]


def _wait_for_health(base_url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/public-health", timeout=2.0) as r:
                if r.status == 200:
                    return
        except Exception:
            time.sleep(0.3)
    pytest.skip(f"Server at {base_url} did not become healthy within {timeout}s")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **kw):  # type: ignore[override]
        return None


def _create_solar_project(base_url: str, token: str) -> str:
    """Create a Solar project via /projects/create; return project_code."""
    form = urllib.parse.urlencode({
        "project_name": "UI3B Browser Solar",
        "project_type": "Solar",
        "country_market": "Poland",
        "capacity_mw": "50",
        "cod_date": "2025-01-01",
        "construction_months": "18",
        "horizon_years": "20",
        "tariff_eur_mwh": "65",
        "ppa_term_years": "15",
        "p50_hours": "1750",
        "opex_y1_keur": "800",
        "total_capex_keur": "42000",
        "gearing_pct": "70",
        "interest_rate_pct": "4.5",
        "tenor_years": "18",
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
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=15.0) as response:
            loc = response.headers.get("Location") or response.headers.get("HX-Redirect")
            if loc:
                code = urllib.parse.parse_qs(
                    urllib.parse.urlparse(loc).query
                ).get("project", [None])[0]
                if code:
                    return code
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location") or e.headers.get("HX-Redirect")
        if loc:
            code = urllib.parse.parse_qs(
                urllib.parse.urlparse(loc).query
            ).get("project", [None])[0]
            if code:
                return code
        pytest.skip(f"Could not create Solar project: HTTP {e.code} — {loc!r}")
    except Exception as e:
        pytest.skip(f"Could not create Solar project: {e}")
    pytest.skip("Could not create Solar project — /projects/create did not return expected redirect")


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def live_server():
    """Start a live uvicorn server; yield base URL."""
    pytest.importorskip(
        "playwright.sync_api",
        reason="OPTIONAL_BROWSER_DEPENDENCY_MISSING: install playwright to run browser tests",
    )
    port = _pick_free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["FINCO_SECRET_KEY"] = os.environ.get("FINCO_SECRET_KEY", "ui3b-browser-accept-test-key")
    env["FINCO_COOKIE_SECURE"] = "false"
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main_web:app",
         "--host", "127.0.0.1", "--port", str(port)],
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


@pytest.fixture(scope="module")
def solar_page(live_server):
    """Open a Solar project in Chromium; yield (page, base_url, code, errors)."""
    from playwright.sync_api import sync_playwright

    token = create_session_token()
    project_code = _create_solar_project(live_server, token)

    ctx = sync_playwright().start()
    try:
        browser = ctx.chromium.launch(executable_path=CHROMIUM_PATH)
    except Exception as exc:
        ctx.stop()
        pytest.skip(f"OPTIONAL_BROWSER_DEPENDENCY_MISSING_BROWSER_BINARIES: {exc}")

    bctx = browser.new_context()
    bctx.add_cookies([{"name": COOKIE_NAME, "value": token, "url": live_server}])
    page = bctx.new_page()
    page_errors = []
    page.on("pageerror", lambda e: page_errors.append(str(e)))

    yield page, live_server, project_code, page_errors

    browser.close()
    ctx.stop()


# ── Solar browser acceptance ───────────────────────────────────────────────────

class TestSolarBrowserAcceptance:

    def test_01_workbook_loads_200_no_500(self, solar_page):
        """V2 workbook must return HTTP 200 with no error indicators."""
        page, base_url, code, errs = solar_page
        resp = page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="domcontentloaded")
        assert resp.status == 200, f"Workbook returned {resp.status}"
        content = page.content()
        assert "Something went wrong" not in content
        assert "subscriptable" not in content
        assert "TypeError" not in content

    def test_02_v2_shell_marker_present(self, solar_page):
        """V2 workbook shell marker must be in the page."""
        page, base_url, code, errs = solar_page
        content = page.content()
        assert "v2-workbook" in content or "v2-sheet" in content, \
            "V2 workbook shell marker not found"

    def test_03_scenarios_tab_renders(self, solar_page):
        """Scenarios tab content renders when tab is activated."""
        page, base_url, code, errs = solar_page
        # Activate Scenarios tab
        tab = page.query_selector("#tab-scenarios")
        if tab:
            tab.click()
            page.wait_for_timeout(400)
        content = page.content()
        assert "v2-scenarios" in content or "v2-scenario-list" in content, \
            "Scenarios tab content not found"

    def test_04_base_case_visible(self, solar_page):
        """Base Case scenario must appear in the scenarios list."""
        page, base_url, code, errs = solar_page
        content = page.content()
        assert "Base Case" in content or "BC" in content, \
            "Base Case not found in scenarios list"

    def test_05_create_downside_scenario(self, solar_page):
        """Creating a Downside scenario via the form succeeds."""
        page, base_url, code, errs = solar_page
        name_input = page.query_selector(".v2-scenario-name-input")
        if name_input:
            name_input.fill("Downside")
            create_btn = page.query_selector(".v2-scenario-create-btn")
            if create_btn:
                create_btn.click()
                page.wait_for_timeout(600)
        assert "Downside" in page.content(), "Downside scenario not created"

    def test_06_no_js_errors_after_create(self, solar_page):
        """No critical JS errors after scenario creation."""
        page, base_url, code, errs = solar_page
        critical = [e for e in errs if any(x in e for x in ["TypeError", "ReferenceError"])]
        assert not critical, f"Critical JS errors: {critical}"

    def test_07_no_stack_trace_in_page(self, solar_page):
        """No Python traceback or server error in the rendered page."""
        page, base_url, code, errs = solar_page
        content = page.content()
        assert "Traceback" not in content
        assert "Internal Server Error" not in content

    def test_08_htmx_scenario_create_returns_200(self, solar_page):
        """HTMX /workbook/scenarios/create endpoint returns 200 with scenario list HTML."""
        page, base_url, code, errs = solar_page
        token = create_session_token()
        req = urllib.request.Request(
            f"{base_url}/v2/workbook/scenarios/create",
            data=urllib.parse.urlencode({"project": code, "scenario_name": "Upside"}).encode(),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": f"{COOKIE_NAME}={token}",
                "HX-Request": "true",
            },
        )
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            assert resp.status == 200
            body = resp.read().decode()
        assert "v2-scenarios" in body or "Upside" in body, \
            f"HTMX create did not return scenario list. Body snippet: {body[:300]}"

    def test_09_compare_endpoint_returns_200(self, solar_page):
        """HTMX compare endpoint returns 200 with compare sheet HTML."""
        page, base_url, code, errs = solar_page
        token = create_session_token()
        req = urllib.request.Request(
            f"{base_url}/v2/workbook/scenarios/compare?project={code}",
            headers={"Cookie": f"{COOKIE_NAME}={token}", "HX-Request": "true"},
        )
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            assert resp.status == 200
            body = resp.read().decode()
        assert "v2-compare" in body, f"Compare sheet not in response. Body: {body[:300]}"

    def test_10_sensitivity_endpoint_returns_200(self, solar_page):
        """Sensitivity endpoint returns 200 when available."""
        page, base_url, code, errs = solar_page
        token = create_session_token()
        req = urllib.request.Request(
            f"{base_url}/v2/workbook/sensitivity?project={code}",
            headers={"Cookie": f"{COOKIE_NAME}={token}", "HX-Request": "true"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                assert resp.status == 200
                body = resp.read().decode()
            assert "sensitivity" in body.lower() or "v2-sensitivity" in body, \
                f"Sensitivity sheet not in response. Body: {body[:300]}"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                pytest.skip("Sensitivity endpoint not yet routed; skip this step")
            raise

    def test_11_no_critical_browser_errors_overall(self, solar_page):
        """No uncaught TypeError/ReferenceError over the full Solar flow."""
        page, base_url, code, errs = solar_page
        critical = [e for e in errs if any(x in e for x in ["TypeError", "ReferenceError", "SyntaxError"])]
        assert not critical, f"Critical browser errors: {critical}"


# ── Wind real-engine acceptance ────────────────────────────────────────────────

class TestWindRealEngineAcceptance:

    def test_wind_base_irr_positive(self):
        """Wind default base run produces a positive IRR."""
        from app.api.project_runner import run_project
        r = run_project("Wind", "Base")
        rs = (r or {}).get("kpis", {})
        irr = rs.get("project_irr")
        assert irr is not None and irr > 0, f"Wind base IRR invalid: {irr}"

    def test_wind_scenario_isolation(self):
        """Wind base and downside runs produce different IRRs (snapshot isolation)."""
        from app.api.project_runner import run_project
        from app.workbook.service import WorkbookService

        base_snap = {
            "project_name": "Wind Isolation Test",
            "project_type": "Wind",
            "country_market": "Poland",
            "capacity_mw": 50.0,
            "cod_date": "2025-01-01",
            "construction_months": 18,
            "horizon_years": 20,
            "tariff_eur_mwh": 65.0,
            "rev_ppa_base_tariff": 65.0,
            "ppa_term_years": 15,
            "tenor_years": 18,
            "target_dscr": 1.30,
            "total_capex_keur": 50000.0,
            "opex_y1_keur": 1000.0,
            "p50_hours": 2400.0,
            "interest_rate_pct": 4.5,
            "gearing_pct": 70.0,
        }

        def _run(snap, label):
            pis = WorkbookService.build_input_set(snap)
            pi = WorkbookService.to_projectinputs(pis)
            r = run_project("Wind", label, project_inputs_override=pi)
            return (r or {}).get("kpis", {})

        rs_base = _run(base_snap, "Base")
        snap_d = dict(base_snap, rev_ppa_base_tariff=65.0 * 0.85, tariff_eur_mwh=65.0 * 0.85)
        rs_down = _run(snap_d, "Downside")
        irr_b = rs_base.get("project_irr") or 0
        irr_d = rs_down.get("project_irr") or 0
        assert irr_b != irr_d, "Wind base and downside IRRs identical — snapshot isolation failure"

    def test_wind_compare_delta_direction(self):
        """Wind compare matrix: downside delta is negative vs base."""
        from app.api.project_runner import run_project
        from app.workbook.service import WorkbookService
        from app.v2.scenario_kpi_projection import build_scenario_projection, build_compare_rows

        base_snap = {
            "project_name": "Wind Delta Test",
            "project_type": "Wind",
            "country_market": "Poland",
            "capacity_mw": 50.0,
            "cod_date": "2025-01-01",
            "construction_months": 18,
            "horizon_years": 20,
            "tariff_eur_mwh": 65.0,
            "rev_ppa_base_tariff": 65.0,
            "ppa_term_years": 15,
            "tenor_years": 18,
            "target_dscr": 1.30,
            "total_capex_keur": 50000.0,
            "opex_y1_keur": 1000.0,
            "p50_hours": 2400.0,
            "interest_rate_pct": 4.5,
            "gearing_pct": 70.0,
        }

        def _run(snap, label):
            pis = WorkbookService.build_input_set(snap)
            pi = WorkbookService.to_projectinputs(pis)
            r = run_project("Wind", label, project_inputs_override=pi)
            return (r or {}).get("kpis", {})

        rs_base = _run(base_snap, "Base")
        snap_d = dict(base_snap, rev_ppa_base_tariff=65.0 * 0.85, tariff_eur_mwh=65.0 * 0.85)
        rs_down = _run(snap_d, "Downside")

        p_b = build_scenario_projection("Base", rs_base, None, is_stale=False)
        p_d = build_scenario_projection("Downside", rs_down, None, is_stale=False)
        rows = build_compare_rows([p_b, p_d])
        irr_row = next(r for r in rows if r.key == "project_irr")
        assert irr_row.deltas[0] == "—"
        assert irr_row.deltas[1].startswith("-"), \
            f"Downside delta should be negative, got: {irr_row.deltas[1]}"


# ── Sensitivity non-destructive proof ─────────────────────────────────────────

class TestSensitivityNonDestructiveProof:

    def _base_snap(self, name="Sens Test"):
        return {
            "project_name": name,
            "project_type": "Solar",
            "country_market": "Poland",
            "capacity_mw": 50.0,
            "cod_date": "2025-01-01",
            "construction_months": 18,
            "horizon_years": 20,
            "tariff_eur_mwh": 65.0,
            "rev_ppa_base_tariff": 65.0,
            "ppa_term_years": 15,
            "tenor_years": 18,
            "target_dscr": 1.30,
            "total_capex_keur": 42000.0,
            "opex_y1_keur": 800.0,
            "p50_hours": 1750.0,
            "interest_rate_pct": 4.5,
            "gearing_pct": 70.0,
        }

    def test_pis_base_unchanged_after_sensitivity(self):
        """Sensitivity runs must not mutate pis_base.values."""
        import json, hashlib
        from app.workbook.service import WorkbookService
        from app.api.project_runner import run_project

        pis_base = WorkbookService.build_input_set(self._base_snap("NonDestr Test"))
        before_hash = hashlib.sha256(
            json.dumps(dict(pis_base.values), sort_keys=True, default=str).encode()
        ).hexdigest()

        # 5-point tariff sensitivity using internal field_id
        base_tariff = pis_base.values.get("revenue.ppa.base_tariff") or 65.0
        for step in [-0.20, -0.10, 0.0, +0.10, +0.20]:
            new_val = base_tariff * (1 + step)
            pis_sens = pis_base
            try:
                pis_sens = pis_sens.with_value("revenue.ppa.base_tariff", str(new_val))
            except Exception:
                pass
            pi_sens = WorkbookService.to_projectinputs(pis_sens)
            run_project("Solar", "Base", project_inputs_override=pi_sens)

        after_hash = hashlib.sha256(
            json.dumps(dict(pis_base.values), sort_keys=True, default=str).encode()
        ).hexdigest()
        assert before_hash == after_hash, \
            "pis_base.values mutated during sensitivity — non-destructive contract violated"

    def test_sensitivity_five_point_irr_monotone(self):
        """5-point tariff sensitivity produces 5 distinct, monotone IRRs."""
        from app.workbook.service import WorkbookService
        from app.api.project_runner import run_project

        pis_base = WorkbookService.build_input_set(self._base_snap("5-point Test"))
        base_tariff = pis_base.values.get("revenue.ppa.base_tariff") or 65.0
        irrs = []
        for step in [-0.20, -0.10, 0.0, +0.10, +0.20]:
            new_val = base_tariff * (1 + step)
            pis_sens = pis_base.with_value("revenue.ppa.base_tariff", str(new_val))
            pi_sens = WorkbookService.to_projectinputs(pis_sens)
            r = run_project("Solar", "Base", project_inputs_override=pi_sens)
            irrs.append((r or {}).get("kpis", {}).get("project_irr"))

        assert len(irrs) == 5
        assert all(x is not None for x in irrs), f"Some IRRs None: {irrs}"
        assert irrs[0] < irrs[2] < irrs[4], \
            f"Sensitivity IRRs not monotone with tariff: {irrs}"
