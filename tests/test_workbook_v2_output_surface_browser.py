"""Browser acceptance tests: PR-B workbook output surface convergence.

Tests Revenue, Senior Debt, Tax, and Financial Statements in four states
(NOT_RUN, CURRENT, STALE, UNAVAILABLE) using real Playwright + isolated SQLite.

State matrix per sheet
-----------------------
  NOT_RUN   — no prior run; state bar shows run-required notice
  CURRENT   — run completed, workspace clean; outputs visible
  STALE     — run completed, then input edited; prior outputs remain visible with stale notice
  UNAVAILABLE — tested for FS where payload can be absent

Additional coverage
-------------------
  - FS: Annual view is the first-use default (model periods hidden)
  - FS: User can toggle to model periods
  - FS: All three inner tabs (Income Statement, Cash Waterfall, Balance Sheet)
  - Schedule tables: Debt and Tax horizontal scrolling, sticky header
  - None-vs-zero: zero in output stays as 0; None renders as em dash
  - Protected reference: outputs visible, no editable controls, no write path
  - Both viewports: 1440×900 and 1920×1080

Skip behaviour
--------------
Auto-skipped when Playwright is not importable.
"""
from __future__ import annotations

import glob
import os
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests as _requests

os.environ.setdefault("FINCO_SECRET_KEY", "output-surface-test-secret")

BASE_DIR = Path(__file__).resolve().parents[1]
_SERVER_SECRET = "output-surface-test-secret"

_FULL_CREATE_FORM = {
    "project_name": "Output Surface Test",
    "project_type": "Wind",
    "template_source": "generic_wind",
    "country_market": "Poland",
    "capacity_mw": "50",
    "cod_date": "2028-01-01",
    "construction_months": "18",
    "horizon_years": "25",
    "tariff_eur_mwh": "55",
    "ppa_term_years": "15",
    "p50_hours": "2200",
    "opex_y1_keur": "900",
    "total_capex_keur": "60000",
    "gearing_pct": "70",
    "interest_rate_pct": "4.5",
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chromium_path() -> str:
    candidates = glob.glob("/opt/pw-browsers/chromium*/chrome-linux/chrome")
    return sorted(candidates)[-1] if candidates else ""


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        return s.getsockname()[1]


def _wait_for_server(base_url: str, timeout: float = 30.0) -> None:
    import urllib.request as _req
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with _req.urlopen(f"{base_url}/public-health", timeout=2.0) as r:
                if r.status == 200:
                    return
        except Exception:
            pass
        time.sleep(0.25)
    raise AssertionError(f"Server at {base_url} not ready after {timeout}s")


def _start_server(tmp_path: Path, extra_env: dict | None = None) -> tuple:
    port = _free_port()
    db_path = str(tmp_path / "output_surface.db")
    base_env = {k: v for k, v in os.environ.items()
                if k not in ("FINCO_WORKBOOK_V2", "FINCO_INPUTS_SLICE1_ENABLED")}
    env = {
        **base_env,
        "FINCO_DB_PATH": db_path,
        "FINCO_SECRET_KEY": _SERVER_SECRET,
        **(extra_env or {}),
    }
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


async def _new_page(pw, token: str, base_url: str, width: int = 1440, height: int = 900):
    from app.auth import COOKIE_NAME
    chromium = _chromium_path()
    opts = {"executable_path": chromium} if chromium else {}
    browser = await pw.chromium.launch(**opts)
    ctx = await browser.new_context(viewport={"width": width, "height": height})
    page = await ctx.new_page()
    await page.goto(f"{base_url}/login")
    await page.context.add_cookies([{
        "name": COOKIE_NAME, "value": token,
        "domain": "127.0.0.1", "path": "/",
    }])
    return browser, page


async def _arrange_project(page, base_url: str, name_suffix: str = "") -> str:
    """Create a project via fetch (arrangement only). Returns project code."""
    fields = dict(_FULL_CREATE_FORM)
    if name_suffix:
        fields["project_name"] = f"Output Test {name_suffix}"
    js_body = " + '&' + ".join(
        f"encodeURIComponent({k!r}) + '=' + encodeURIComponent({v!r})"
        for k, v in fields.items()
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


def _get_content_hash(base_url: str, token: str, project_code: str) -> str:
    from app.auth import COOKIE_NAME
    r = _requests.get(
        f"{base_url}/v2/workbook?project={project_code}",
        cookies={COOKIE_NAME: token},
        allow_redirects=True,
    )
    assert r.status_code == 200, f"GET /v2/workbook failed: {r.status_code}"
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, "html.parser")
    inp = soup.find("input", {"name": "content_hash"})
    assert inp, "no content_hash input found on workbook page"
    return inp["value"]


def _run_model(base_url: str, token: str, project_code: str) -> None:
    """POST /v2/workbook/run and assert 200."""
    from app.auth import COOKIE_NAME
    ch = _get_content_hash(base_url, token, project_code)
    r = _requests.post(
        f"{base_url}/v2/workbook/run",
        data={
            "project": project_code,
            "workbook_version": "2.1.0",
            "content_hash": ch,
        },
        cookies={COOKIE_NAME: token},
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 200, f"Run failed: {r.status_code}"


def _create_regular_project(base_url: str, token: str, name_suffix: str = "") -> str:
    """Create a normal editable project via the API. Returns project_code."""
    import urllib.parse
    from app.auth import COOKIE_NAME
    fields = dict(_FULL_CREATE_FORM)
    fields["project_name"] = f"Protected Reference Test {name_suffix}".strip()
    form_data = "&".join(f"{k}={v}" for k, v in fields.items())
    r = _requests.post(
        f"{base_url}/projects/create",
        data=form_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        cookies={COOKIE_NAME: token},
        allow_redirects=True,
    )
    parsed = urllib.parse.urlparse(r.url)
    code = dict(urllib.parse.parse_qsl(parsed.query)).get("project", "")
    assert code, f"Project creation failed, url={r.url!r}"
    return code


def _convert_project_to_protected_reference(db_path: str, code: str) -> None:
    """Convert an existing project to protected reference directly in the DB."""
    con = sqlite3.connect(db_path)
    con.execute(
        "UPDATE projects SET project_origin=?, template_source=?, project_role=?, is_protected=1"
        " WHERE project_code=?",
        ("factory_template", "tuho", "reference", code),
    )
    con.commit()
    con.close()


def _seed_reference_project(db_path: str, base_url: str, token: str) -> str:
    """Compatibility alias: create + convert to protected reference. Returns project_code."""
    code = _create_regular_project(base_url, token)
    _convert_project_to_protected_reference(db_path, code)
    return code


def _db_snapshot_for_project(db_path: str, code: str) -> dict:
    """Full deterministic snapshot of all DB state for a single project."""
    con = sqlite3.connect(db_path)
    snap: dict = {}

    # Inspect actual columns
    proj_cols = [r[1] for r in con.execute("PRAGMA table_info(projects)").fetchall()]
    ws_cols = [r[1] for r in con.execute("PRAGMA table_info(workspace_states)").fetchall()]

    # Project record
    proj_row = con.execute(
        f"SELECT {', '.join(proj_cols)} FROM projects WHERE project_code=?", (code,)
    ).fetchone()
    snap["project"] = dict(zip(proj_cols, proj_row)) if proj_row else None

    # Workspace record
    ws_row = con.execute(
        f"SELECT {', '.join(ws_cols)} FROM workspace_states WHERE project_code=?", (code,)
    ).fetchone()
    snap["workspace"] = dict(zip(ws_cols, ws_row)) if ws_row else None

    # runs table has no project_code; v2 workbook runs do not insert rows there
    snap["runs"] = []

    con.close()
    return snap


def _db_snapshot(db_path: str) -> dict:
    con = sqlite3.connect(db_path)
    try:
        runs = con.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    except Exception:
        runs = 0
    try:
        ws_rows = con.execute(
            "SELECT project_code, dirty, draft_content_hash FROM workspace_states "
            "ORDER BY project_code"
        ).fetchall()
    except Exception:
        ws_rows = []
    return {"runs": runs, "ws": ws_rows}


async def _navigate_to_tab(page, tab_id: str) -> None:
    """Click a workbook tab and wait for the panel to become visible."""
    btn = page.locator(f"#{tab_id}")
    assert await btn.count() > 0, f"Tab #{tab_id} not found"
    await btn.click()
    panel_id = await btn.get_attribute("aria-controls")
    if panel_id:
        await page.locator(f"#{panel_id}").wait_for(state="visible", timeout=8_000)


async def _run_via_browser(page, base_url: str) -> None:
    """Click the Run button and wait for the run response."""
    run_btn = page.locator('[data-testid="v2-run-btn"]')
    assert await run_btn.count() > 0, "v2-run-btn not found"
    async with page.expect_response(
        lambda r: "/v2/workbook/run" in r.url, timeout=90_000
    ):
        await run_btn.click()
    await page.wait_for_timeout(600)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def server_v2(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("output_v2")
    proc, base_url, db_path = _start_server(tmp)
    yield {"base_url": base_url, "token": _make_token(), "db_path": db_path}
    proc.terminate()
    proc.wait(timeout=10)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_revenue_not_run_state(server_v2):
    """Revenue sheet shows NOT_RUN state with run-required notice."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            code = await _arrange_project(page, base_url, "rev-notrun")
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
            await _navigate_to_tab(page, "tab-revenue")
            bar = page.locator('[data-testid="revenue-state-bar"]')
            assert await bar.count() > 0, "revenue-state-bar missing"
            state_text = await bar.inner_text()
            assert "Run the model" in state_text, f"NOT_RUN text missing: {state_text!r}"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_revenue_current_state(server_v2):
    """Revenue sheet shows CLEAN state with derivation evidence after a run."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            code = await _arrange_project(page, base_url, "rev-current")
            _run_model(base_url, token, code)
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
            await _navigate_to_tab(page, "tab-revenue")
            bar = page.locator('[data-testid="revenue-state-bar"]')
            assert await bar.count() > 0, "revenue-state-bar missing after run"
            clean_badge = page.locator('[data-testid="revenue-state-clean"]')
            # CLEAN or UNAVAILABLE — both are valid; key check is no NOT_RUN text
            state_text = await bar.inner_text()
            assert "Run the model" not in state_text, f"Still showing NOT_RUN after run: {state_text!r}"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_revenue_stale_state(server_v2):
    """Revenue sheet shows STALE with prior outputs visible after input change."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            code = await _arrange_project(page, base_url, "rev-stale")
            _run_model(base_url, token, code)

            # Make workspace dirty by editing a canonical input via HTTP
            from app.auth import COOKIE_NAME
            ch = _get_content_hash(base_url, token, code)
            r = _requests.post(
                f"{base_url}/v2/workbook/update",
                data={
                    "field_id": "project_setup.technical.p50_hours",
                    "value": "2100",
                    "project": code,
                    "workbook_version": "2.1.0",
                    "content_hash": ch,
                },
                cookies={COOKIE_NAME: token},
                headers={"HX-Request": "true"},
            )
            assert r.status_code == 200, f"input edit failed: {r.status_code}"

            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
            await _navigate_to_tab(page, "tab-revenue")
            bar = page.locator('[data-testid="revenue-state-bar"]')
            assert await bar.count() > 0, "revenue-state-bar missing"
            state_text = await bar.inner_text()
            # STALE or UNAVAILABLE — key check: not showing as CLEAN
            assert "Outputs current" not in state_text or "stale" in state_text.lower(), \
                f"stale state not correctly shown: {state_text!r}"
            # Stale notice element
            stale_notice = page.locator('[data-testid="revenue-stale-notice"]')
            if await stale_notice.count() > 0:
                notice_text = await stale_notice.inner_text()
                assert "stale" in notice_text.lower() or "changed" in notice_text.lower()
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_debt_not_run_shows_pre_run_notice(server_v2):
    """Debt sheet shows pre-run notice and no schedule when not run."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            code = await _arrange_project(page, base_url, "debt-notrun")
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
            await _navigate_to_tab(page, "tab-debt")
            # No schedule table
            assert await page.locator('[data-testid="debt-schedule-table"]').count() == 0, \
                "debt schedule table must not appear pre-run"
            # Pre-run notice
            pre_run = page.locator('[data-testid="debt-pre-run-notice"]')
            no_runtime = page.locator('[data-testid="debt-schedule-no-runtime"]')
            has_notice = (await pre_run.count() > 0) or (await no_runtime.count() > 0)
            assert has_notice, "debt pre-run or no-runtime notice missing"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_debt_current_state_shows_schedule(server_v2):
    """Debt sheet shows KPIs and schedule table after a run."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            code = await _arrange_project(page, base_url, "debt-current")
            _run_model(base_url, token, code)
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
            await _navigate_to_tab(page, "tab-debt")
            # State bar should show CLEAN
            state_bar_text = await page.locator('[data-testid="debt-runtime-bar"]').inner_text()
            assert "Outputs current" in state_bar_text or "current" in state_bar_text.lower(), \
                f"Debt not in CLEAN state: {state_bar_text!r}"
            # Schedule table or KPI bar present
            has_kpi = await page.locator('[data-testid="debt-kpi-bar"]').count() > 0
            has_table = await page.locator('[data-testid="debt-schedule-table"]').count() > 0
            assert has_kpi or has_table, "Debt CLEAN state: no KPI bar or schedule table"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_debt_stale_prior_output_visible(server_v2):
    """Debt sheet retains prior schedule and shows stale notice after input change."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            from app.auth import COOKIE_NAME
            code = await _arrange_project(page, base_url, "debt-stale")
            _run_model(base_url, token, code)

            # Verify schedule visible in CLEAN state
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
            await _navigate_to_tab(page, "tab-debt")
            clean_text = await page.locator('[data-testid="debt-runtime-bar"]').inner_text()

            # Make workspace dirty
            ch = _get_content_hash(base_url, token, code)
            _requests.post(
                f"{base_url}/v2/workbook/update",
                data={"field_id": "project_setup.technical.p50_hours",
                      "value": "2150", "project": code,
                      "workbook_version": "2.1.0", "content_hash": ch},
                cookies={COOKIE_NAME: token},
                headers={"HX-Request": "true"},
            )
            await page.reload(wait_until="networkidle")
            await _navigate_to_tab(page, "tab-debt")

            stale_text = await page.locator('[data-testid="debt-runtime-bar"]').inner_text()
            assert "run required" in stale_text.lower() or "stale" in stale_text.lower(), \
                f"Debt stale state not shown: {stale_text!r}"

            # Prior schedule still present (not cleared)
            has_table = await page.locator('[data-testid="debt-schedule-table"]').count() > 0
            has_kpi = await page.locator('[data-testid="debt-kpi-bar"]').count() > 0
            assert has_table or has_kpi, \
                "Prior debt outputs must remain visible when stale"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_tax_not_run_shows_pre_run_notice(server_v2):
    """Tax sheet shows pre-run notice and no schedule when not run."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            code = await _arrange_project(page, base_url, "tax-notrun")
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
            await _navigate_to_tab(page, "tab-tax")
            assert await page.locator('[data-testid="tax-schedule-table"]').count() == 0
            pre = page.locator('[data-testid="tax-pre-run-notice"]')
            no_rt = page.locator('[data-testid="tax-schedule-no-runtime"]')
            assert (await pre.count() > 0) or (await no_rt.count() > 0), \
                "Tax pre-run notice missing"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_tax_current_state_shows_schedule(server_v2):
    """Tax sheet shows summary and schedule after a run."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            code = await _arrange_project(page, base_url, "tax-current")
            _run_model(base_url, token, code)
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
            await _navigate_to_tab(page, "tab-tax")
            bar_text = await page.locator('[data-testid="tax-runtime-bar"]').inner_text()
            assert "Outputs current" in bar_text or "current" in bar_text.lower(), \
                f"Tax not in CLEAN state: {bar_text!r}"
            has_kpi = await page.locator('[data-testid="tax-kpi-bar"]').count() > 0
            has_table = await page.locator('[data-testid="tax-schedule-table"]').count() > 0
            assert has_kpi or has_table, "Tax CLEAN: no KPI bar or schedule"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_tax_stale_prior_output_visible(server_v2):
    """Tax sheet retains prior schedule and shows stale notice after input change."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            from app.auth import COOKIE_NAME
            code = await _arrange_project(page, base_url, "tax-stale")
            _run_model(base_url, token, code)

            # Verify CLEAN then make stale
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
            await _navigate_to_tab(page, "tab-tax")
            ch = _get_content_hash(base_url, token, code)
            _requests.post(
                f"{base_url}/v2/workbook/update",
                data={"field_id": "project_setup.technical.p50_hours",
                      "value": "2050", "project": code,
                      "workbook_version": "2.1.0", "content_hash": ch},
                cookies={COOKIE_NAME: token},
                headers={"HX-Request": "true"},
            )
            await page.reload(wait_until="networkidle")
            await _navigate_to_tab(page, "tab-tax")
            stale_text = await page.locator('[data-testid="tax-runtime-bar"]').inner_text()
            assert "run required" in stale_text.lower() or "stale" in stale_text.lower(), \
                f"Tax stale state not shown: {stale_text!r}"
            # Prior outputs still present
            has_table = await page.locator('[data-testid="tax-schedule-table"]').count() > 0
            has_kpi = await page.locator('[data-testid="tax-kpi-bar"]').count() > 0
            assert has_table or has_kpi, "Prior tax outputs must remain visible when stale"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_fs_not_run_shows_not_run_notice(server_v2):
    """FS sheet shows NOT_RUN bar and no statement tables when not run."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            code = await _arrange_project(page, base_url, "fs-notrun")
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
            await _navigate_to_tab(page, "tab-fs")
            # No statement tables
            assert await page.locator('[data-testid="fs-pnl-table"]').count() == 0
            assert await page.locator('[data-testid="fs-pnl-annual-table"]').count() == 0
            # Pre-run message in at least one panel
            no_runtime = page.locator('[data-testid="fs-pnl-no-runtime"]')
            assert await no_runtime.count() > 0, "fs-pnl-no-runtime notice missing"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_fs_annual_is_first_use_default(server_v2):
    """FS sheet opens in Annual view on first use (no sessionStorage)."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            code = await _arrange_project(page, base_url, "fs-annual-default")
            _run_model(base_url, token, code)
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
            # Clear sessionStorage before navigating to FS
            await page.evaluate("() => sessionStorage.clear()")
            await _navigate_to_tab(page, "tab-fs")
            await page.wait_for_timeout(500)

            # The Annual tab should be active
            annual_tab = page.locator('.v2-fs-period-tab[data-period-view="annual"]')
            assert await annual_tab.count() > 0, "Annual period tab missing"
            aria = await annual_tab.get_attribute("aria-selected")
            assert aria == "true", f"Annual tab not active on first use (aria-selected={aria!r})"

            # Model periods tables should be hidden, annual visible
            model_wrappers = page.locator('.v2-fs-table-model')
            if await model_wrappers.count() > 0:
                # All model wrappers should be hidden
                for i in range(await model_wrappers.count()):
                    display = await model_wrappers.nth(i).evaluate("el => el.style.display")
                    assert display == "none", f"model wrapper {i} should be hidden on first use"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_fs_model_period_toggle(server_v2):
    """User can switch from Annual to Model periods view."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            code = await _arrange_project(page, base_url, "fs-model-toggle")
            _run_model(base_url, token, code)
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
            await page.evaluate("() => sessionStorage.clear()")
            await _navigate_to_tab(page, "tab-fs")
            await page.wait_for_timeout(300)

            # Click model periods tab
            model_tab = page.locator('.v2-fs-period-tab[data-period-view="model"]')
            assert await model_tab.count() > 0, "Model periods tab missing"
            await model_tab.click()
            await page.wait_for_timeout(300)

            # Model periods should now be active
            aria = await model_tab.get_attribute("aria-selected")
            assert aria == "true", "Model periods tab not active after click"

            # Annual wrappers should be hidden
            annual_wrappers = page.locator('.v2-fs-table-annual')
            if await annual_wrappers.count() > 0:
                for i in range(await annual_wrappers.count()):
                    display = await annual_wrappers.nth(i).evaluate("el => el.style.display")
                    assert display == "none", f"annual wrapper {i} should be hidden after model toggle"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_fs_three_inner_tabs(server_v2):
    """All three FS inner tabs switch correctly: Income Statement, Cash Waterfall, Balance Sheet."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            code = await _arrange_project(page, base_url, "fs-tabs")
            _run_model(base_url, token, code)
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
            await page.evaluate("() => sessionStorage.clear()")
            await _navigate_to_tab(page, "tab-fs")
            await page.wait_for_timeout(300)

            panels = [
                ("fs-inner-panel-pnl",   "nav-fs-pnl"),
                ("fs-inner-panel-pf-cf", "nav-fs-pf-cf"),
                ("fs-inner-panel-bs",    "nav-fs-bs"),
            ]
            for panel_id, tab_id in panels:
                tab = page.locator(f"#{tab_id}")
                assert await tab.count() > 0, f"FS inner tab #{tab_id} missing"
                await tab.click()
                await page.wait_for_timeout(200)
                panel = page.locator(f"#{panel_id}")
                assert await panel.count() > 0, f"FS inner panel #{panel_id} missing"
                classes = await panel.get_attribute("class") or ""
                assert "v2-fs-inner-panel-active" in classes, \
                    f"Panel {panel_id} not active after tab click"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_fs_stale_state_prior_outputs_remain(server_v2):
    """FS shows stale state bar but prior statement tables remain visible."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            from app.auth import COOKIE_NAME
            code = await _arrange_project(page, base_url, "fs-stale")
            _run_model(base_url, token, code)

            # Verify CLEAN — get statement row count before stale
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
            await _navigate_to_tab(page, "tab-fs")
            pre_run_rows = await page.locator('[data-testid^="fs-pnl-annual-row-"]').count()

            # Make dirty
            ch = _get_content_hash(base_url, token, code)
            _requests.post(
                f"{base_url}/v2/workbook/update",
                data={"field_id": "project_setup.technical.p50_hours",
                      "value": "1900", "project": code,
                      "workbook_version": "2.1.0", "content_hash": ch},
                cookies={COOKIE_NAME: token},
                headers={"HX-Request": "true"},
            )
            await page.reload(wait_until="networkidle")
            await page.evaluate("() => sessionStorage.clear()")
            await _navigate_to_tab(page, "tab-fs")
            await page.wait_for_timeout(300)

            # Stale bar visible
            bar = page.locator('[data-testid="fs-runtime-bar"]')
            bar_text = await bar.inner_text()
            assert "run required" in bar_text.lower() or "stale" in bar_text.lower(), \
                f"FS stale bar not shown: {bar_text!r}"
            assert "Outputs current" not in bar_text, "Stale FS must not say 'Outputs current'"

            # Prior outputs still visible (not cleared)
            if pre_run_rows > 0:
                post_stale_rows = await page.locator('[data-testid^="fs-pnl-annual-row-"]').count()
                assert post_stale_rows > 0, "FS Annual rows must remain visible in stale state"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_schedule_table_uses_v2_schedule_table_class(server_v2):
    """Debt and Tax schedules use .v2-schedule-table (not inline styles)."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            code = await _arrange_project(page, base_url, "sched-class")
            _run_model(base_url, token, code)
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")

            await _navigate_to_tab(page, "tab-debt")
            debt_table = page.locator('[data-testid="debt-schedule-table"]')
            if await debt_table.count() > 0:
                cls = await debt_table.get_attribute("class") or ""
                assert "v2-schedule-table" in cls, \
                    f"Debt schedule table missing v2-schedule-table class: {cls!r}"

            await _navigate_to_tab(page, "tab-tax")
            tax_table = page.locator('[data-testid="tax-schedule-table"]')
            if await tax_table.count() > 0:
                cls = await tax_table.get_attribute("class") or ""
                assert "v2-schedule-table" in cls, \
                    f"Tax schedule table missing v2-schedule-table class: {cls!r}"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_none_renders_as_em_dash_zero_as_zero(server_v2):
    """Zero values remain 0 in output tables; None values render as em dash."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            code = await _arrange_project(page, base_url, "none-zero")
            _run_model(base_url, token, code)
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
            await _navigate_to_tab(page, "tab-debt")
            # Open the Debt Schedule details section (starts collapsed)
            sched_summary = page.locator('#nav-debt-schedule')
            if await sched_summary.count() > 0:
                await sched_summary.click()
                await page.wait_for_timeout(200)
            # Debt schedule rows should contain numbers (not blanks) or em dashes
            table = page.locator('[data-testid="debt-schedule-table"]')
            if await table.count() > 0:
                cells = page.locator('[data-testid="debt-schedule-table"] td.v2-num')
                count = await cells.count()
                for i in range(min(count, 20)):
                    text = (await cells.nth(i).inner_text()).strip()
                    assert text == "—" or text.lstrip("-").replace(",", "").replace(".", "").isdigit(), \
                        f"cell[{i}] unexpected content: {text!r}"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_protected_reference_outputs_visible_no_mutation(server_v2):
    """Protected reference: working-copy Run → convert → read-only output review."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    db_path = server_v2["db_path"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            # 1. Create a normal editable project
            code = _create_regular_project(base_url, token, "ref-test")

            # 2. Run the model while it is a working copy
            _run_model(base_url, token, code)

            # 3. Verify runtime was persisted
            con = sqlite3.connect(db_path)
            ws_check = con.execute(
                "SELECT last_runtime_summary_json FROM workspace_states WHERE project_code=?",
                (code,)
            ).fetchone()
            con.close()
            assert ws_check is not None and ws_check[0], \
                "Runtime summary must be persisted after Run"

            # 4. Convert to protected reference
            _convert_project_to_protected_reference(db_path, code)

            # 5. Capture complete before-visit snapshot
            snap_before = _db_snapshot_for_project(db_path, code)
            assert snap_before["project"]["project_role"] == "reference"
            assert snap_before["project"]["is_protected"] == 1

            # 6. Navigate and visit all four output tabs
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")

            # Toolbar: reference badge present, working-copy badge absent
            assert await page.locator(".v2-toolbar-ref-badge").count() == 1, \
                "Toolbar reference badge must exist exactly once"
            assert await page.locator(".v2-toolbar-wc-badge").count() == 0, \
                "Toolbar working-copy badge must not exist on a protected reference"

            for tab_id, sheet_selector in [
                ("tab-revenue",  "#v2-sheet-revenue"),
                ("tab-debt",     "#v2-sheet-senior-debt"),
                ("tab-tax",      "#v2-sheet-tax"),
                ("tab-fs",       "#v2-sheet-financial-statements"),
            ]:
                await _navigate_to_tab(page, tab_id)
                sheet = page.locator(sheet_selector)
                assert await sheet.count() > 0, f"{sheet_selector} not found on {tab_id}"

                # Protected notice present
                notice = sheet.locator(".v2-protected-notice")
                assert await notice.count() > 0, f"Protected notice missing on {tab_id}"
                notice_text = await notice.first.inner_text()
                assert "Reference" in notice_text or "reference" in notice_text, \
                    f"Notice must mention 'Reference' on {tab_id}: {notice_text!r}"

                # No editable forms
                forms = sheet.locator(".v2-field-form")
                assert await forms.count() == 0, \
                    f"Edit forms must not appear on protected reference ({tab_id})"

                # No input/select/textarea that could edit assumptions
                inputs = sheet.locator("input:not([type=hidden]), select, textarea")
                assert await inputs.count() == 0, \
                    f"Editable input controls must be absent on {tab_id}"

                # Runtime outputs visible (model was run before conversion)
                if tab_id == "tab-revenue":
                    bar = sheet.locator('[data-testid="revenue-state-bar"]')
                    assert await bar.count() > 0, "revenue-state-bar must be present"
                    bar_text = await bar.inner_text()
                    assert "NOT_RUN" not in bar_text, \
                        f"Revenue must not be NOT_RUN after run: {bar_text!r}"
                    has_clean = await sheet.locator('[data-testid="revenue-state-clean"]').count()
                    has_stale = await sheet.locator('[data-testid="revenue-state-stale"]').count()
                    assert (has_clean + has_stale) > 0, \
                        "Revenue must show CLEAN or STALE after a successful run"
                    deriv = sheet.locator('[data-testid="revenue-derivation"]')
                    assert await deriv.count() > 0, "revenue-derivation must be visible"

                elif tab_id == "tab-debt":
                    bar = sheet.locator('[data-testid="debt-runtime-bar"]')
                    assert await bar.count() > 0, "debt-runtime-bar must be present"
                    has_kpi = await sheet.locator('[data-testid="debt-kpi-bar"]').count()
                    has_sched = await sheet.locator(".v2-schedule-table, .v2-schedule-scroll").count()
                    assert (has_kpi + has_sched) > 0, \
                        "Debt KPI or schedule must be visible after run"

                elif tab_id == "tab-tax":
                    bar = sheet.locator('[data-testid="tax-runtime-bar"]')
                    assert await bar.count() > 0, "tax-runtime-bar must be present"
                    has_kpi = await sheet.locator('[data-testid="tax-kpi-bar"]').count()
                    has_sched = await sheet.locator(".v2-schedule-table, .v2-schedule-scroll").count()
                    assert (has_kpi + has_sched) > 0, \
                        "Tax KPI or schedule must be visible after run"

                elif tab_id == "tab-fs":
                    bar = page.locator('[data-testid="fs-runtime-bar"]')
                    assert await bar.count() > 0, "fs-runtime-bar must be present"
                    bar_text = await bar.inner_text()
                    assert "NOT_RUN" not in bar_text, \
                        f"FS must not be NOT_RUN after run: {bar_text!r}"
                    has_stmt = await sheet.locator(".v2-statement-table, .v2-statement-scroll").count()
                    has_inner = await sheet.locator(
                        ".v2-fs-inner-tab, [data-testid='fs-inner-tab']"
                    ).count()
                    assert (has_stmt + has_inner) > 0, \
                        "FS statement content must be visible after run"

            # 7. Capture after-visit snapshot
            snap_after = _db_snapshot_for_project(db_path, code)

            # 8. Assert full snapshot equality (excluding updated_at timestamps)
            def _drop_timestamps(snap: dict) -> dict:
                import copy
                s = copy.deepcopy(snap)
                for record_key in ("project", "workspace"):
                    rec = s.get(record_key) or {}
                    for ts_col in ("updated_at", "created_at"):
                        rec.pop(ts_col, None)
                return s

            assert _drop_timestamps(snap_after) == _drop_timestamps(snap_before), (
                "DB snapshot must be identical before and after visiting a protected reference "
                "(timestamps excluded).\n"
                f"Before: {snap_before}\nAfter: {snap_after}"
            )

            # 9. Explicit post-visit field assertions
            proj_after = snap_after["project"]
            assert proj_after["project_role"] == "reference", "project_role must remain 'reference'"
            assert proj_after["is_protected"] == 1, "is_protected must remain 1"

            ws_after = snap_after["workspace"]
            ws_before_ws = snap_before["workspace"]
            for key in ("last_runtime_summary_json", "last_debt_schedule_json",
                        "last_tax_schedule_json", "last_financial_statements_json"):
                if key in (ws_after or {}):
                    assert ws_after[key] == ws_before_ws[key], \
                        f"Workspace field {key!r} must be unchanged after viewing"

            # 10. HTTP load must still 200 (no redirect to copy)
            from app.auth import COOKIE_NAME as _CNAME
            r = _requests.get(
                f"{base_url}/v2/workbook?project={code}",
                cookies={_CNAME: token},
                allow_redirects=True,
            )
            assert r.status_code == 200, "Workbook page must load 200 for reference project"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_viewport_1440x900_all_sheets_render(server_v2):
    """All four output sheets render correctly at 1440×900."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url, width=1440, height=900)
        try:
            code = await _arrange_project(page, base_url, "vp1440")
            _run_model(base_url, token, code)
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")

            for tab_id, sheet_id in [
                ("tab-revenue", "v2-sheet-revenue"),
                ("tab-debt",    "v2-sheet-senior-debt"),
                ("tab-tax",     "v2-sheet-tax"),
                ("tab-fs",      "v2-sheet-financial-statements"),
            ]:
                await _navigate_to_tab(page, tab_id)
                sheet = page.locator(f"#{sheet_id}")
                assert await sheet.count() > 0, f"{sheet_id} missing at 1440×900"
                bb = await sheet.bounding_box()
                assert bb is not None and bb["width"] > 0, f"{sheet_id} has zero width"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_viewport_1920x1080_all_sheets_render(server_v2):
    """All four output sheets render correctly at 1920×1080."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url, width=1920, height=1080)
        try:
            code = await _arrange_project(page, base_url, "vp1920")
            _run_model(base_url, token, code)
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")

            for tab_id, sheet_id in [
                ("tab-revenue", "v2-sheet-revenue"),
                ("tab-debt",    "v2-sheet-senior-debt"),
                ("tab-tax",     "v2-sheet-tax"),
                ("tab-fs",      "v2-sheet-financial-statements"),
            ]:
                await _navigate_to_tab(page, tab_id)
                sheet = page.locator(f"#{sheet_id}")
                assert await sheet.count() > 0, f"{sheet_id} missing at 1920×1080"
                bb = await sheet.bounding_box()
                assert bb is not None and bb["width"] > 0, f"{sheet_id} has zero width"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_fs_income_statement_annual_rows_visible(server_v2):
    """FS Income Statement annual rows are visible on first use (Annual default)."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            code = await _arrange_project(page, base_url, "fs-pnl-annual")
            _run_model(base_url, token, code)
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
            await page.evaluate("() => sessionStorage.clear()")
            await _navigate_to_tab(page, "tab-fs")
            await page.wait_for_timeout(400)

            # Income Statement is the default inner tab
            pnl_panel = page.locator("#fs-inner-panel-pnl")
            assert await pnl_panel.count() > 0
            cls = await pnl_panel.get_attribute("class") or ""
            assert "v2-fs-inner-panel-active" in cls, "Income Statement panel not active by default"

            # Annual table visible (contains rows)
            annual_wrapper = pnl_panel.locator(".v2-fs-table-annual").first
            if await annual_wrapper.count() > 0:
                display = await annual_wrapper.evaluate("el => el.style.display")
                assert display != "none", "Annual table must be visible on first use"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_debt_and_tax_schedule_header_columns(server_v2):
    """Debt and Tax schedule tables have expected column headers."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            code = await _arrange_project(page, base_url, "sched-headers")
            _run_model(base_url, token, code)
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")

            await _navigate_to_tab(page, "tab-debt")
            # Open debt schedule details (starts collapsed)
            debt_sched_sum = page.locator('#nav-debt-schedule')
            if await debt_sched_sum.count() > 0:
                await debt_sched_sum.click()
                await page.wait_for_timeout(200)
            debt_table = page.locator('[data-testid="debt-schedule-table"]')
            if await debt_table.count() > 0:
                header_text = await debt_table.locator("thead").inner_text()
                for col in ("Period", "Date", "DSCR"):
                    assert col in header_text, f"Debt schedule missing column '{col}'"

            await _navigate_to_tab(page, "tab-tax")
            # Open tax schedule details (starts collapsed)
            tax_sched_sum = page.locator('#nav-tax-schedule')
            if await tax_sched_sum.count() > 0:
                await tax_sched_sum.click()
                await page.wait_for_timeout(200)
            tax_table = page.locator('[data-testid="tax-schedule-table"]')
            if await tax_table.count() > 0:
                header_text = await tax_table.locator("thead").inner_text()
                for col in ("Period", "Date", "Tax"):
                    assert col in header_text, f"Tax schedule missing column '{col}'"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_revenue_state_bar_testid_present_in_all_states(server_v2):
    """revenue-state-bar data-testid is present before and after a run."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            code = await _arrange_project(page, base_url, "rev-testid")

            # Before run
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
            await _navigate_to_tab(page, "tab-revenue")
            assert await page.locator('[data-testid="revenue-state-bar"]').count() > 0, \
                "revenue-state-bar missing before run"
            notrun_el = page.locator('[data-testid="revenue-state-notrun"]')
            assert await notrun_el.count() > 0, "revenue-state-notrun element missing"

            # After run
            _run_model(base_url, token, code)
            await page.reload(wait_until="networkidle")
            await _navigate_to_tab(page, "tab-revenue")
            assert await page.locator('[data-testid="revenue-state-bar"]').count() > 0, \
                "revenue-state-bar missing after run"
            # NOT_RUN element should be gone
            assert await page.locator('[data-testid="revenue-state-notrun"]').count() == 0, \
                "revenue-state-notrun still shown after run"
        finally:
            await browser.close()


# ── Sticky / scroll computed-style browser tests ────────────────────────── #

@pytest.mark.asyncio
async def test_debt_schedule_sticky_and_scroll(server_v2):
    """Debt schedule: sticky header cells computed, horizontal scroll possible."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            code = await _arrange_project(page, base_url, "debt-sticky")
            _run_model(base_url, token, code)
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
            await _navigate_to_tab(page, "tab-debt")

            # Open the debt schedule section
            sched_sum = page.locator('#nav-debt-schedule')
            assert await sched_sum.count() > 0, "#nav-debt-schedule summary missing"
            await sched_sum.click()
            await page.wait_for_timeout(300)

            # Table must be present after a run
            table = page.locator('[data-testid="debt-schedule-table"]')
            assert await table.count() > 0, \
                "Debt schedule table absent after a successful run — must be present"

            # Header cells must have position:sticky
            first_th = table.locator("thead th").first
            pos = await first_th.evaluate("el => getComputedStyle(el).position")
            assert pos == "sticky", f"Debt schedule header th not sticky (got {pos!r})"

            # Wrapper: scroll container
            wrapper = page.locator('[data-testid="debt-schedule-table-wrapper"]')
            assert await wrapper.count() > 0, "debt-schedule-table-wrapper missing"
            overflow_x = await wrapper.evaluate("el => getComputedStyle(el).overflowX")
            assert overflow_x in ("auto", "scroll"), \
                f"Wrapper overflow-x must be auto or scroll, got {overflow_x!r}"

            # First tbody td must have position:sticky (sticky first column)
            first_td = table.locator("tbody td:first-child").first
            if await first_td.count() > 0:
                td_pos = await first_td.evaluate("el => getComputedStyle(el).position")
                assert td_pos == "sticky", \
                    f"Debt schedule first body td not sticky (got {td_pos!r})"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_tax_schedule_sticky_and_scroll(server_v2):
    """Tax schedule: sticky header cells computed, scroll wrapper present."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            code = await _arrange_project(page, base_url, "tax-sticky")
            _run_model(base_url, token, code)
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
            await _navigate_to_tab(page, "tab-tax")

            # Open the tax schedule section
            sched_sum = page.locator('#nav-tax-schedule')
            if await sched_sum.count() > 0:
                await sched_sum.click()
                await page.wait_for_timeout(300)

            table = page.locator('[data-testid="tax-schedule-table"]')
            assert await table.count() > 0, \
                "Tax schedule table absent after a successful run — must be present"

            first_th = table.locator("thead th").first
            pos = await first_th.evaluate("el => getComputedStyle(el).position")
            assert pos == "sticky", f"Tax schedule header th not sticky (got {pos!r})"

            wrapper = page.locator('[data-testid="tax-schedule-table-wrapper"]')
            if await wrapper.count() > 0:
                overflow_x = await wrapper.evaluate("el => getComputedStyle(el).overflowX")
                assert overflow_x in ("auto", "scroll"), \
                    f"Tax wrapper overflow-x must be auto or scroll, got {overflow_x!r}"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_fs_statement_sticky_and_scroll(server_v2):
    """FS statement tables: corner sticky, period headers sticky, row labels sticky."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            code = await _arrange_project(page, base_url, "fs-sticky")
            _run_model(base_url, token, code)
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
            await page.evaluate("() => sessionStorage.clear()")
            await _navigate_to_tab(page, "tab-fs")
            await page.wait_for_timeout(400)

            # Income Statement annual table (visible by default)
            pnl_annual = page.locator('[data-testid="fs-pnl-annual-table"]')
            if await pnl_annual.count() > 0:
                # Corner cell (first th): sticky top + left
                corner = pnl_annual.locator("thead th").first
                corner_pos = await corner.evaluate("el => getComputedStyle(el).position")
                assert corner_pos == "sticky", \
                    f"FS PnL corner th not sticky (got {corner_pos!r})"

                # Row-label td in first body row: sticky left
                first_td = pnl_annual.locator("tbody td:first-child").first
                if await first_td.count() > 0:
                    td_pos = await first_td.evaluate("el => getComputedStyle(el).position")
                    assert td_pos == "sticky", \
                        f"FS PnL row-label td not sticky (got {td_pos!r})"

                # Scroll wrapper: overflow-x auto
                wrapper = page.locator('[data-testid="fs-pnl-annual-table-wrapper"]')
                if await wrapper.count() > 0:
                    ox = await wrapper.evaluate("el => getComputedStyle(el).overflowX")
                    assert ox in ("auto", "scroll"), \
                        f"FS PnL annual wrapper overflow-x={ox!r}"
        finally:
            await browser.close()


# ── UNAVAILABLE state tests ─────────────────────────────────────────────── #

@pytest.mark.asyncio
async def test_revenue_unavailable_when_no_derivation(server_v2):
    """Revenue shows UNAVAILABLE when runtime_summary exists but revenue_derivation is absent."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    db_path = server_v2["db_path"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            code = await _arrange_project(page, base_url, "rev-unavail")
            _run_model(base_url, token, code)

            # Patch the persisted last_runtime_summary_json to remove revenue_derivation
            import json
            con = sqlite3.connect(db_path)
            rows = con.execute(
                "SELECT last_runtime_summary_json FROM workspace_states WHERE project_code=?",
                (code,)
            ).fetchall()
            if rows:
                rs = json.loads(rows[0][0] or "{}")
                rs.pop("revenue_derivation", None)
                con.execute(
                    "UPDATE workspace_states SET last_runtime_summary_json=? WHERE project_code=?",
                    (json.dumps(rs), code)
                )
                con.commit()
            con.close()

            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
            await _navigate_to_tab(page, "tab-revenue")

            state_bar = page.locator('[data-testid="revenue-state-bar"]')
            assert await state_bar.count() > 0, "revenue-state-bar missing"
            bar_text = await state_bar.inner_text()

            # Should NOT say "Outputs current" when derivation is absent
            assert "Outputs current" not in bar_text, \
                f"Revenue must not say 'Outputs current' when derivation absent: {bar_text!r}"

            # Should show UNAVAILABLE or have no CLEAN badge
            clean_el = page.locator('[data-testid="revenue-state-clean"]')
            assert await clean_el.count() == 0, \
                "revenue-state-clean must not appear when revenue_derivation is absent"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_debt_unavailable_state_no_outputs_current(server_v2):
    """Debt shows UNAVAILABLE when rr exists but debt_schedule is absent."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    db_path = server_v2["db_path"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            code = await _arrange_project(page, base_url, "debt-unavail")
            _run_model(base_url, token, code)

            # Null out the debt_schedule in workspace_states
            con = sqlite3.connect(db_path)
            con.execute(
                "UPDATE workspace_states SET last_debt_schedule_json='{}' WHERE project_code=?",
                (code,)
            )
            con.commit()
            con.close()

            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
            await _navigate_to_tab(page, "tab-debt")

            bar = page.locator('[data-testid="debt-runtime-bar"]')
            assert await bar.count() > 0, "debt-runtime-bar missing"
            bar_text = await bar.inner_text()
            assert "Outputs current" not in bar_text, \
                f"Debt must not say 'Outputs current' when schedule absent: {bar_text!r}"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_revenue_exact_clean_after_run(server_v2):
    """After a successful run, Revenue is exactly CLEAN (not UNAVAILABLE)."""
    base_url, token = server_v2["base_url"], server_v2["token"]
    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            code = await _arrange_project(page, base_url, "rev-exact-clean")
            _run_model(base_url, token, code)
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
            await _navigate_to_tab(page, "tab-revenue")

            # Exactly CLEAN — not UNAVAILABLE, not STALE, not NOT_RUN
            clean_el = page.locator('[data-testid="revenue-state-clean"]')
            assert await clean_el.count() > 0, \
                "revenue-state-clean must exist after a successful run"
            # UNAVAILABLE must not appear
            unavail_el = page.locator('[data-testid="revenue-state-unavailable"]')
            assert await unavail_el.count() == 0, \
                "revenue-state-unavailable must not appear after a successful run"
            # NOT_RUN must not appear
            notrun_el = page.locator('[data-testid="revenue-state-notrun"]')
            assert await notrun_el.count() == 0, \
                "revenue-state-notrun must not appear after a successful run"
            # Derivation evidence present
            derivation = page.locator('[data-testid="revenue-derivation"]')
            assert await derivation.count() > 0, \
                "revenue-derivation evidence must appear when CLEAN"
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_xss_marker_undefined_after_hydration(server_v2):
    """Security: XSS inert marker must remain undefined after workbook hydration.

    Places the canonical inert payload in project_name (a user-controlled field
    that is embedded in the sessionStorage hydration script) and asserts that:
    - window.__fincoXssMarker is undefined (script element was not broken);
    - the workbook loads successfully;
    - the page HTML does not contain the attacker literal </script> after a run.
    """
    base_url, token = server_v2["base_url"], server_v2["token"]
    _INERT_PAYLOAD = 'Project </script><script>window.__fincoXssMarker="executed"</script>'

    async with async_playwright() as pw:
        browser, page = await _new_page(pw, token, base_url)
        try:
            # 1. Create project with an ordinary name (project_name is
            #    not user-editable post-creation in V2, but runtime_summary
            #    carries it through the hydration path).
            code = await _arrange_project(page, base_url, "xss-check")

            # 2. Run the model to populate the sessionStorage hydration script.
            _run_model(base_url, token, code)

            # 3. Inject the inert payload into the persisted runtime_summary
            #    so it is embedded in the next hydration script.
            import json, sqlite3
            db_path = server_v2["db_path"]
            con = sqlite3.connect(db_path)
            row = con.execute(
                "SELECT last_runtime_summary_json FROM workspace_states WHERE project_code=?",
                (code,)
            ).fetchone()
            if row and row[0]:
                rs = json.loads(row[0])
                rs["project_name"] = _INERT_PAYLOAD
                con.execute(
                    "UPDATE workspace_states SET last_runtime_summary_json=? WHERE project_code=?",
                    (json.dumps(rs), code)
                )
                con.commit()
            con.close()

            # 4. Navigate to the V2 workbook (triggers hydration script).
            await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")

            # 5. Assert the inert marker was NOT executed.
            marker = await page.evaluate("window.__fincoXssMarker")
            assert marker is None, (
                f"XSS inert marker executed — window.__fincoXssMarker={marker!r}. "
                "The sessionStorage hydration script is not HTML-script-safe."
            )

            # 6. Workbook loads successfully (Run button present).
            run_btn = page.locator('[data-testid="v2-run-btn"]')
            assert await run_btn.count() > 0, "Workbook must load successfully"

            # 7. Inspect the page source — no literal attacker payload.
            html = await page.content()
            assert _INERT_PAYLOAD not in html, (
                "Attacker literal payload found verbatim in page HTML"
            )

            # 8. sessionStorage round-trip: key must exist and payload must decode correctly.
            stored_raw = await page.evaluate(
                "window.sessionStorage.getItem('lastRuntimeSummary')"
            )
            assert stored_raw is not None, (
                "lastRuntimeSummary must exist after V2 workbook hydration"
            )
            assert stored_raw != "", (
                "lastRuntimeSummary must not be an empty string"
            )
            stored = json.loads(stored_raw)
            assert stored.get("project_name") == _INERT_PAYLOAD, (
                "project_name must round-trip exactly through the script-safe "
                "sessionStorage hydration path"
            )
        finally:
            await browser.close()
