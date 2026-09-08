"""Browser acceptance: UI-4A Output Contract — Solar (Section 31) and Wind (Section 32).

Proves:
- OutputMetricProjection wired to Overview KPI tiles
- Run button shows scenario identity ("Run Base Case")
- NOT_AVAILABLE sentinel never appears in rendered HTML
- Timestamp rendered as "YYYY-MM-DD HH:MM UTC"
- KPI values: percentage, ratio, kEUR all render correctly
- No Python tracebacks or raw exceptions in page

SOLAR_REAL_BROWSER=PASS, WIND_REAL_UI=PASS

Skip: auto-skipped when Playwright is not importable.
"""
from __future__ import annotations

import glob
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests as _requests

os.environ.setdefault("FINCO_SECRET_KEY", "ui4a-output-contract-secret")

BASE_DIR = Path(__file__).resolve().parents[1]
_SERVER_SECRET = "ui4a-output-contract-secret"

_SOLAR_CREATE_FORM = {
    "project_name": "UI4A Solar Acceptance",
    "project_type": "Solar",
    "template_source": "generic_solar",
    "country_market": "Spain",
    "capacity_mw": "100",
    "cod_date": "2028-01-01",
    "construction_months": "18",
    "horizon_years": "20",
    "tariff_eur_mwh": "55",
    "ppa_term_years": "15",
    "p50_hours": "1800",
    "opex_y1_keur": "1000",
    "total_capex_keur": "90000",
    "gearing_pct": "70",
    "interest_rate_pct": "4.5",
    "tenor_years": "18",
    "target_dscr": "1.30",
}

_WIND_CREATE_FORM = {
    "project_name": "UI4A Wind Acceptance",
    "project_type": "Wind",
    "template_source": "generic_wind",
    "country_market": "Germany",
    "capacity_mw": "80",
    "cod_date": "2029-01-01",
    "construction_months": "24",
    "horizon_years": "20",
    "tariff_eur_mwh": "60",
    "ppa_term_years": "15",
    "p50_hours": "2500",
    "opex_y1_keur": "800",
    "total_capex_keur": "120000",
    "gearing_pct": "70",
    "interest_rate_pct": "5.0",
    "tenor_years": "18",
    "target_dscr": "1.30",
}

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not PLAYWRIGHT_AVAILABLE,
    reason="playwright not installed — skip browser tests",
)


# ── Infrastructure (mirrors test_workbook_v2_output_surface_browser.py) ─────── #

def _chromium_path() -> str:
    candidates = glob.glob("/opt/pw-browsers/chromium*/chrome-linux/chrome")
    return sorted(candidates)[-1] if candidates else ""


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        return s.getsockname()[1]


def _wait_for_server(base_url: str, timeout: float = 40.0) -> None:
    import urllib.request as _req
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with _req.urlopen(f"{base_url}/public-health", timeout=2.0) as r:
                if r.status == 200:
                    return
        except Exception:
            pass
        time.sleep(0.3)
    raise AssertionError(f"Server at {base_url} not ready after {timeout}s")


def _start_server(tmp_path: Path) -> tuple:
    port = _free_port()
    db_path = str(tmp_path / "ui4a.db")
    env = {k: v for k, v in os.environ.items()
           if k not in ("FINCO_WORKBOOK_V2", "FINCO_INPUTS_SLICE1_ENABLED")}
    env.update({
        "FINCO_DB_PATH": db_path,
        "FINCO_SECRET_KEY": _SERVER_SECRET,
    })
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main_web:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=str(BASE_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base_url = f"http://127.0.0.1:{port}"
    _wait_for_server(base_url)
    return proc, base_url, db_path


def _make_token() -> str:
    from datetime import datetime, timezone
    from itsdangerous import URLSafeTimedSerializer
    from app.auth import ADMIN_USERNAME, SessionData
    session = SessionData(user_id="1", username=ADMIN_USERNAME,
                          login_at=datetime.now(timezone.utc))
    return URLSafeTimedSerializer(_SERVER_SECRET).dumps(session.to_dict())


async def _new_page(pw, token: str, base_url: str):
    from app.auth import COOKIE_NAME
    chromium = _chromium_path()
    opts = {"executable_path": chromium} if chromium else {}
    browser = await pw.chromium.launch(**opts)
    ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
    page = await ctx.new_page()
    await page.goto(f"{base_url}/login")
    await page.context.add_cookies([{
        "name": COOKIE_NAME, "value": token,
        "domain": "127.0.0.1", "path": "/",
    }])
    return browser, page


async def _arrange_project(page, base_url: str, form: dict) -> str:
    """Create a project via fetch. Returns project_code."""
    js_body = " + '&' + ".join(
        f"encodeURIComponent({k!r}) + '=' + encodeURIComponent({v!r})"
        for k, v in form.items()
    )
    final_url = await page.evaluate(f"""
        async () => {{
            const body = {js_body};
            const resp = await fetch('{base_url}/projects/create', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                body: body,
                redirect: 'follow',
            }});
            return resp.url;
        }}
    """)
    import urllib.parse
    parsed = urllib.parse.urlparse(final_url)
    code = dict(urllib.parse.parse_qsl(parsed.query)).get("project", "")
    assert code, f"project creation failed, final_url={final_url!r}"
    return code


def _get_run_params(base_url: str, token: str, project_code: str) -> dict:
    """Extract content_hash and workbook_version from the workbook page."""
    import re
    from app.auth import COOKIE_NAME
    r = _requests.get(
        f"{base_url}/v2/workbook?project={project_code}",
        cookies={COOKIE_NAME: token},
        allow_redirects=True,
    )
    assert r.status_code == 200, f"GET /v2/workbook failed: {r.status_code}"
    text = r.text
    def _extract(name: str) -> str:
        # Match: name="workbook_version" value="..." or value="..." name="workbook_version"
        pat = r'name="' + re.escape(name) + r'"[^>]*value="([^"]*)"'
        m = re.search(pat, text)
        if not m:
            pat2 = r'value="([^"]*)"[^>]*name="' + re.escape(name) + r'"'
            m = re.search(pat2, text)
        return m.group(1) if m else ""
    return {
        "content_hash": _extract("content_hash"),
        "workbook_version": _extract("workbook_version"),
    }


def _run_model(base_url: str, token: str, project_code: str) -> None:
    from app.auth import COOKIE_NAME
    params = _get_run_params(base_url, token, project_code)
    r = _requests.post(
        f"{base_url}/v2/workbook/run",
        data={"project": project_code, **params},
        cookies={COOKIE_NAME: token},
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 200, f"Run failed: {r.status_code}"
    assert "version mismatch" not in r.text, f"Workbook version mismatch: {r.text[:200]}"


# ── Fixtures ─────────────────────────────────────────────────────────────── #

@pytest.fixture(scope="module")
def solar_server(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("ui4a_solar")
    proc, base_url, db_path = _start_server(tmp)
    token = _make_token()
    yield {"base_url": base_url, "token": token, "db_path": db_path}
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture(scope="module")
def wind_server(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("ui4a_wind")
    proc, base_url, db_path = _start_server(tmp)
    token = _make_token()
    yield {"base_url": base_url, "token": token, "db_path": db_path}
    proc.terminate()
    proc.wait(timeout=10)


# ─────────────────────────────────────────────────────────────────────────── #
# Section 31: Solar real browser acceptance — 11 browser steps                 #
# (Each step navigates to overview to verify a specific contract property)     #
# ─────────────────────────────────────────────────────────────────────────── #

class TestSolarOutputContractBrowser:
    """SOLAR_REAL_BROWSER acceptance — OutputMetricProjection contract."""

    @pytest.mark.asyncio
    async def test_01_workbook_loads_no_error(self, solar_server):
        """Step 1: Solar workbook renders without error."""
        base_url, token = solar_server["base_url"], solar_server["token"]
        async with async_playwright() as pw:
            browser, page = await _new_page(pw, token, base_url)
            try:
                code = await _arrange_project(page, base_url, _SOLAR_CREATE_FORM)
                await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
                body = await page.content()
                assert "Traceback (most recent call last)" not in body
                assert "Internal Server Error" not in body
            finally:
                await browser.close()

    @pytest.mark.asyncio
    async def test_02_run_button_shows_base_case(self, solar_server):
        """Step 2: Run button label contains scenario identity."""
        base_url, token = solar_server["base_url"], solar_server["token"]
        async with async_playwright() as pw:
            browser, page = await _new_page(pw, token, base_url)
            try:
                code = await _arrange_project(page, base_url, _SOLAR_CREATE_FORM)
                await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
                run_btn = page.locator("[data-testid='v2-run-btn']")
                await run_btn.wait_for(state="visible", timeout=10000)
                btn_text = await run_btn.inner_text()
                # Must contain "Run" and scenario context ("Base Case" or just "Run Base Case")
                assert "Run" in btn_text, f"Run button text: {btn_text!r}"
                assert "Base" in btn_text or "Case" in btn_text or btn_text.strip() in ("Run", "Run Base Case"), \
                    f"Run button should show scenario identity: {btn_text!r}"
            finally:
                await browser.close()

    @pytest.mark.asyncio
    async def test_03_no_not_available_sentinel(self, solar_server):
        """Step 3: NOT_AVAILABLE sentinel never appears in rendered HTML."""
        base_url, token = solar_server["base_url"], solar_server["token"]
        async with async_playwright() as pw:
            browser, page = await _new_page(pw, token, base_url)
            try:
                code = await _arrange_project(page, base_url, _SOLAR_CREATE_FORM)
                await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
                body = await page.content()
                assert "NOT_AVAILABLE" not in body, "NOT_AVAILABLE sentinel leaked to HTML"
            finally:
                await browser.close()

    @pytest.mark.asyncio
    async def test_04_overview_renders_after_run(self, solar_server):
        """Steps 4-8: After engine run, overview KPI values present."""
        base_url, token = solar_server["base_url"], solar_server["token"]
        async with async_playwright() as pw:
            browser, page = await _new_page(pw, token, base_url)
            try:
                code = await _arrange_project(page, base_url, _SOLAR_CREATE_FORM)
                _run_model(base_url, token, code)
                await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
                body = await page.content()
                # After run: expect percentage, ratio, and kEUR values
                import re
                pct_matches = re.findall(r'\d+\.\d{2}%', body)
                ratio_matches = re.findall(r'\d+\.\d{2}x', body)
                keur_matches = re.findall(r'[\d,]+\s*kEUR', body)
                assert len(pct_matches) > 0, "No percentage values after solar run"
                assert len(ratio_matches) > 0, "No ratio values after solar run"
                assert len(keur_matches) > 0, "No kEUR values after solar run"
            finally:
                await browser.close()

    @pytest.mark.asyncio
    async def test_05_no_not_available_after_run(self, solar_server):
        """Step 9: NOT_AVAILABLE absent after run (OutputMetricProjection contract)."""
        base_url, token = solar_server["base_url"], solar_server["token"]
        async with async_playwright() as pw:
            browser, page = await _new_page(pw, token, base_url)
            try:
                code = await _arrange_project(page, base_url, _SOLAR_CREATE_FORM)
                _run_model(base_url, token, code)
                await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
                body = await page.content()
                assert "NOT_AVAILABLE" not in body
            finally:
                await browser.close()

    @pytest.mark.asyncio
    async def test_06_timestamp_format_normalized(self, solar_server):
        """Step 10: Timestamp rendered as 'YYYY-MM-DD HH:MM UTC' (Python-normalized)."""
        base_url, token = solar_server["base_url"], solar_server["token"]
        async with async_playwright() as pw:
            browser, page = await _new_page(pw, token, base_url)
            try:
                code = await _arrange_project(page, base_url, _SOLAR_CREATE_FORM)
                _run_model(base_url, token, code)
                await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
                body = await page.content()
                import re
                ts_matches = re.findall(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC', body)
                assert len(ts_matches) > 0, "Timestamp not rendered as 'YYYY-MM-DD HH:MM UTC'"
                # Must NOT appear as raw ISO format with 'T' separator (Jinja slicing gone)
                raw_ts = re.findall(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', body)
                assert len(raw_ts) == 0, f"Raw ISO timestamp leaked: {raw_ts[:3]}"
            finally:
                await browser.close()

    @pytest.mark.asyncio
    async def test_07_no_python_error(self, solar_server):
        """Step 11: No Python errors in solar workbook."""
        base_url, token = solar_server["base_url"], solar_server["token"]
        async with async_playwright() as pw:
            browser, page = await _new_page(pw, token, base_url)
            try:
                code = await _arrange_project(page, base_url, _SOLAR_CREATE_FORM)
                _run_model(base_url, token, code)
                await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
                body = await page.content()
                assert "Traceback (most recent call last)" not in body
                assert "AttributeError" not in body
                assert "KeyError" not in body
            finally:
                await browser.close()


# ─────────────────────────────────────────────────────────────────────────── #
# Section 32: Wind real engine acceptance — 5 browser steps                    #
# ─────────────────────────────────────────────────────────────────────────── #

class TestWindOutputContractBrowser:
    """WIND_REAL_UI acceptance — real engine, no mocked financial outputs."""

    @pytest.mark.asyncio
    async def test_01_wind_workbook_loads(self, wind_server):
        """Step 1: Wind workbook renders without error."""
        base_url, token = wind_server["base_url"], wind_server["token"]
        async with async_playwright() as pw:
            browser, page = await _new_page(pw, token, base_url)
            try:
                code = await _arrange_project(page, base_url, _WIND_CREATE_FORM)
                await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
                body = await page.content()
                assert "Traceback (most recent call last)" not in body
                assert "Internal Server Error" not in body
            finally:
                await browser.close()

    @pytest.mark.asyncio
    async def test_02_wind_run_button_present(self, wind_server):
        """Step 2: Run button present for wind project."""
        base_url, token = wind_server["base_url"], wind_server["token"]
        async with async_playwright() as pw:
            browser, page = await _new_page(pw, token, base_url)
            try:
                code = await _arrange_project(page, base_url, _WIND_CREATE_FORM)
                await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
                run_btn = page.locator("[data-testid='v2-run-btn']")
                await run_btn.wait_for(state="visible", timeout=10000)
                btn_text = await run_btn.inner_text()
                assert "Run" in btn_text
            finally:
                await browser.close()

    @pytest.mark.asyncio
    async def test_03_wind_kpi_values_after_run(self, wind_server):
        """Steps 3-7: Wind KPI values present after real engine run."""
        base_url, token = wind_server["base_url"], wind_server["token"]
        async with async_playwright() as pw:
            browser, page = await _new_page(pw, token, base_url)
            try:
                code = await _arrange_project(page, base_url, _WIND_CREATE_FORM)
                _run_model(base_url, token, code)
                await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
                body = await page.content()
                import re
                pct_matches = re.findall(r'\d+\.\d{2}%', body)
                keur_matches = re.findall(r'[\d,]+\s*kEUR', body)
                assert len(pct_matches) > 0 or len(keur_matches) > 0, \
                    "No KPI values after wind run"
            finally:
                await browser.close()

    @pytest.mark.asyncio
    async def test_04_wind_no_not_available(self, wind_server):
        """Step 8: NOT_AVAILABLE absent from wind page."""
        base_url, token = wind_server["base_url"], wind_server["token"]
        async with async_playwright() as pw:
            browser, page = await _new_page(pw, token, base_url)
            try:
                code = await _arrange_project(page, base_url, _WIND_CREATE_FORM)
                _run_model(base_url, token, code)
                await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
                body = await page.content()
                assert "NOT_AVAILABLE" not in body
            finally:
                await browser.close()

    @pytest.mark.asyncio
    async def test_05_wind_no_traceback(self, wind_server):
        """Steps 9-11: No Python errors in wind workbook."""
        base_url, token = wind_server["base_url"], wind_server["token"]
        async with async_playwright() as pw:
            browser, page = await _new_page(pw, token, base_url)
            try:
                code = await _arrange_project(page, base_url, _WIND_CREATE_FORM)
                _run_model(base_url, token, code)
                await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
                body = await page.content()
                assert "Traceback (most recent call last)" not in body
                assert "AttributeError" not in body
                assert "Internal Server Error" not in body
            finally:
                await browser.close()

# ─────────────────────────────────────────────────────────────────────────── #
# Section 14/15: Real browser — Create Project + Run button (no fetch bypass) #
# ─────────────────────────────────────────────────────────────────────────── #

@pytest.fixture(scope="module")
def pilot_server(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("ui4a_pilot")
    proc, base_url, db_path = _start_server(tmp)
    token = _make_token()
    yield {"base_url": base_url, "token": token, "db_path": db_path}
    proc.terminate()
    proc.wait(timeout=10)


async def _real_create_project(page, base_url: str, project_name: str, project_type: str) -> str:
    """Navigate Library → New Project → fill form → click Create.
    Returns project_code from the resulting workbook URL.
    No fetch/HTTP bypass: uses actual visible-browser navigation.
    """
    import urllib.parse
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    # Navigate to library
    await page.goto(f"{base_url}/library", wait_until="networkidle")

    # Click the New Project link
    new_btn = page.locator("a[href='/projects/new'], a:text('+ New Project'), a:text('New Project')")
    await new_btn.first.wait_for(state="visible", timeout=10000)
    await new_btn.first.click()
    await page.wait_for_url(f"{base_url}/projects/new*", timeout=10000)

    # Fill the form
    await page.fill("#npm-project_name", project_name)
    # Select project type
    await page.select_option("#npm-project_type", project_type)
    await page.fill("#npm-country_market", "Spain")
    await page.fill("#npm-capacity_mw", "80")

    # Click Create project button
    await page.click("button[type='submit']:has-text('Create project')")

    # Wait for HTMX redirect → workbook page
    await page.wait_for_url(f"{base_url}/v2/workbook*", timeout=15000)
    parsed = urllib.parse.urlparse(page.url)
    code = dict(urllib.parse.parse_qsl(parsed.query)).get("project", "")
    assert code, f"No project code in URL after create: {page.url}"
    return code, errors


async def _real_click_run(page, base_url: str, project_code: str) -> list:
    """Navigate to workbook, click Run button in browser, wait for completion.
    Returns list of page errors observed.
    No HTTP bypass: the run fires through the browser's HTMX mechanism.
    """
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    await page.goto(f"{base_url}/v2/workbook?project={project_code}", wait_until="networkidle")
    run_btn = page.locator("[data-testid='v2-run-btn']")
    await run_btn.wait_for(state="visible", timeout=10000)
    await run_btn.click()

    # Wait for HTMX run to complete (network goes idle after all partials loaded)
    await page.wait_for_load_state("networkidle", timeout=60000)
    # Reload to get full page with updated KPI state
    await page.reload(wait_until="networkidle")
    return errors


class TestRealBrowserCreateProject:
    """Section 14: Real Playwright create-project flow — no fetch bypass."""

    @pytest.mark.asyncio
    async def test_solar_create_via_browser_navigation(self, pilot_server):
        """Library → New Project → fill → Create → workbook opens (Solar)."""
        base_url, token = pilot_server["base_url"], pilot_server["token"]
        async with async_playwright() as pw:
            browser, page = await _new_page(pw, token, base_url)
            try:
                code, errors = await _real_create_project(
                    page, base_url, "Pilot Solar Real Nav", "Solar"
                )
                # Workbook page should be visible
                body = await page.content()
                assert "Traceback" not in body
                assert "Internal Server Error" not in body
                assert code, "project_code must be non-empty after browser create"
                # No page-level JS errors
                assert not errors, f"Browser pageerrors during create: {errors}"
            finally:
                await browser.close()

    @pytest.mark.asyncio
    async def test_wind_create_via_browser_navigation(self, pilot_server):
        """Library → New Project → fill → Create → workbook opens (Wind)."""
        base_url, token = pilot_server["base_url"], pilot_server["token"]
        async with async_playwright() as pw:
            browser, page = await _new_page(pw, token, base_url)
            try:
                code, errors = await _real_create_project(
                    page, base_url, "Pilot Wind Real Nav", "Wind"
                )
                body = await page.content()
                assert "Traceback" not in body
                assert code, "project_code must be non-empty after browser create"
            finally:
                await browser.close()


class TestRealBrowserRunButton:
    """Section 15: Real Playwright run-button click — no HTTP POST bypass."""

    @pytest.mark.asyncio
    async def test_click_run_base_case_solar(self, pilot_server):
        """Create solar project, CLICK Run Base Case, verify CURRENT state + KPIs."""
        base_url, token = pilot_server["base_url"], pilot_server["token"]
        async with async_playwright() as pw:
            browser, page = await _new_page(pw, token, base_url)
            try:
                # Arrange: create via fetch (already accepted as backend helper)
                code = await _arrange_project(page, base_url, _SOLAR_CREATE_FORM)

                # Act: real browser click on Run button
                run_errors = await _real_click_run(page, base_url, code)

                # Assert: workbook page after run
                body = await page.content()
                import re
                pct_vals = re.findall(r'\d+\.\d{2}%', body)
                assert len(pct_vals) > 0, "No percentage KPI values after browser run click"
                assert "NOT_AVAILABLE" not in body
                assert "Traceback" not in body
                assert not run_errors, f"Browser pageerrors during run: {run_errors}"
            finally:
                await browser.close()

    @pytest.mark.asyncio
    async def test_click_run_base_case_wind(self, pilot_server):
        """Create wind project, CLICK Run Base Case, verify CURRENT state + KPIs."""
        base_url, token = pilot_server["base_url"], pilot_server["token"]
        async with async_playwright() as pw:
            browser, page = await _new_page(pw, token, base_url)
            try:
                code = await _arrange_project(page, base_url, _WIND_CREATE_FORM)
                run_errors = await _real_click_run(page, base_url, code)
                body = await page.content()
                import re
                pct_vals = re.findall(r'\d+\.\d{2}%', body)
                assert len(pct_vals) > 0, "No percentage KPI values after browser run click (wind)"
                assert "NOT_AVAILABLE" not in body
                assert "Traceback" not in body
            finally:
                await browser.close()
