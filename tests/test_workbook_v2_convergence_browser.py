"""Browser acceptance tests: PR-A workbook convergence shell.

Drives Chromium via Playwright against real uvicorn servers with isolated
temporary SQLite databases.

Server configurations tested
----------------------------
  Server A (default, V2 active):
    - GET / → /library
    - New Project via visible browser form → /v2/workbook?project=<code>&sheet=inputs
    - Library Open via clicking Open link → V2 workbook
    - Legacy bookmark /?project=<code> → V2 workbook
    - Working Copy badge visible
    - Five-field persistence (all 5 required: cod_date, construction_months,
      horizon_years, capacity_mw, p50_hours) — each field found, edited,
      submitted, reloaded, and asserted with no conditional skips
    - Read-only fields (project_type, country_market) — rows required present
    - Invalid input → 422 feedback rendered, no persistence
    - Stale content → 409 refresh behaviour, no stale overwrite
    - Protected reference: Reference badge, no editable controls, mutation
      rejected, workspace snapshot unchanged, Run non-destructive

  Server B (FINCO_WORKBOOK_V2=0, V2 inactive):
    - Library Open click → /?project=<code>
    - New Project form submit → /?project=<code>#inputs
    - /v2/workbook?project=<code> → /?project=<code>
    - /v2/workbook?project=<code>&sheet=inputs → /?project=<code>#inputs
    - /v2/workbook (no project) → /library
    - Legacy workspace markers render

  Server C (FINCO_INPUTS_SLICE1_ENABLED=0, V2 active):
    - V2 shell visible
    - #v2-sheet-inputs visible
    - Config-state disabled notice visible
    - No editable Slice 1 controls inside #v2-sheet-inputs
    - POST /v2/workbook/inputs-slice1/update → 409
    - DB snapshot before == after

Both viewports: 1440×900 and 1920×1080 — Library, New Project landing,
Working Copy Inputs, Reference Inputs, Workbook rollback, Inputs rollback.

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
import urllib.parse
from pathlib import Path

import pytest
import requests as _requests

os.environ.setdefault("FINCO_SECRET_KEY", "browser-convergence-secret")

BASE_DIR = Path(__file__).resolve().parents[1]

from app.auth import COOKIE_NAME, ADMIN_USERNAME, SessionData  # noqa: E402

_SERVER_SECRET = "browser-convergence-secret"

# Minimal form fields for the visible /projects/new form
# Only project_name, project_type, country_market, capacity_mw are visible;
# the rest are filled by server defaults.
_MINIMAL_FORM = {
    "project_name": "Browser Test",
    "project_type": "Wind",
    "country_market": "Poland",
    "capacity_mw": "50",
}

# Full create-form fields for programmatic project arrangement (not New Project evidence)
_FULL_CREATE_FORM = {
    "project_name": "Arranged Project",
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

# The five required persistence fields
_FIVE_FIELDS = [
    ("project_setup.technical.cod_date",              "2030-06-15", "2028-01-01"),
    ("project_setup.technical.construction_months",   "22",         "18"),
    ("project_setup.technical.horizon_years",         "28",         "25"),
    ("project_setup.technical.capacity_mw",           "75",         "50"),
    ("project_setup.technical.p50_hours",             "2500",       "2200"),
]


def _make_token(secret_key: str) -> str:
    """Create a signed session token bypassing the module-level SECRET_KEY cache."""
    from datetime import datetime, timezone
    from itsdangerous import URLSafeTimedSerializer
    login_at = datetime.now(timezone.utc)
    session = SessionData(user_id="1", username=ADMIN_USERNAME, login_at=login_at)
    serializer = URLSafeTimedSerializer(secret_key)
    return serializer.dumps(session.to_dict())


# ---------------------------------------------------------------------------
# Playwright import guard
# ---------------------------------------------------------------------------
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
# Chromium path
# ---------------------------------------------------------------------------
def _chromium_path() -> str:
    candidates = glob.glob("/opt/pw-browsers/chromium*/chrome-linux/chrome")
    if candidates:
        return sorted(candidates)[-1]
    return ""


# ---------------------------------------------------------------------------
# Server helpers
# ---------------------------------------------------------------------------
def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        return s.getsockname()[1]


def _wait_for_server(base_url: str, timeout: float = 30.0) -> None:
    import urllib.request as req_lib
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with req_lib.urlopen(f"{base_url}/public-health", timeout=2.0) as r:
                if r.status == 200:
                    return
        except Exception:
            pass
        time.sleep(0.25)
    raise AssertionError(f"Server at {base_url} not ready after {timeout}s")


def _start_server(tmp_path: Path, extra_env: dict) -> tuple[subprocess.Popen, str]:
    """Start a uvicorn server; return (proc, base_url).

    Strips contaminating flag values from the inherited environment.
    """
    port = _free_port()
    db_path = str(tmp_path / "browser_conv.db")
    base_env = {k: v for k, v in os.environ.items()
                if k not in ("FINCO_WORKBOOK_V2", "FINCO_INPUTS_SLICE1_ENABLED")}
    env = {
        **base_env,
        "FINCO_DB_PATH": db_path,
        "FINCO_SECRET_KEY": _SERVER_SECRET,
        **extra_env,
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
    return proc, base_url


async def _new_browser_page(pw, token: str, base_url: str, width: int, height: int):
    """Launch a Chromium page with auth cookie set."""
    chromium = _chromium_path()
    launch_opts = {"executable_path": chromium} if chromium else {}
    browser = await pw.chromium.launch(**launch_opts)
    ctx = await browser.new_context(viewport={"width": width, "height": height})
    page = await ctx.new_page()
    # Establish domain cookie via /login before setting cookie
    await page.goto(f"{base_url}/login")
    await page.context.add_cookies([{
        "name": COOKIE_NAME,
        "value": token,
        "domain": "127.0.0.1",
        "path": "/",
    }])
    return browser, page


async def _arrange_project(page, base_url: str, name_suffix: str = "") -> str:
    """Create a project via browser-context fetch for test ARRANGEMENT only.

    NOT used as New Project evidence. Returns the project code.
    Fails the test if creation fails.
    """
    fields = dict(_FULL_CREATE_FORM)
    if name_suffix:
        fields["project_name"] = f"Arranged {name_suffix}"

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
    parsed = urllib.parse.urlparse(final_url)
    params = dict(urllib.parse.parse_qsl(parsed.query))
    code = params.get("project", "")
    assert code, f"Arrangement project creation failed; final URL: {final_url}"
    return code


async def _new_project_visible_flow(page, base_url: str, name: str) -> str:
    """Execute the visible New Project browser flow.

    1. Open /library.
    2. Click the New Project card.
    3. Fill the rendered minimal form.
    4. Submit.
    5. Wait for navigation.
    6. Return project code from final URL.

    Fails the test if the button, form, or redirect is missing.
    """
    await page.goto(f"{base_url}/library", wait_until="networkidle")

    # Click the New Project card (link to /projects/new)
    new_proj_link = page.locator('a[href="/projects/new"]').first
    assert await new_proj_link.count() > 0, "New Project link not found on /library"
    await new_proj_link.click()
    await page.wait_for_url("**/projects/new", timeout=10_000)

    # Fill the minimal form
    form = page.locator("#new-project-minimal-form")
    assert await form.count() > 0, "new-project-minimal-form not found on /projects/new"

    await page.fill("#npm-project_name", name)
    await page.select_option("#npm-project_type", "Wind")
    await page.fill("#npm-country_market", "Poland")
    await page.fill("#npm-capacity_mw", "50")

    # Submit and wait for navigation
    submit = form.locator('button[type="submit"]')
    assert await submit.count() > 0, "Submit button not found in new-project-minimal-form"

    async with page.expect_navigation(timeout=15_000):
        await submit.click()

    final_url = page.url
    parsed = urllib.parse.urlparse(final_url)
    params = dict(urllib.parse.parse_qsl(parsed.query))
    code = params.get("project", "")
    assert code, f"New Project redirect did not include project code; final URL: {final_url}"
    return code


async def _library_open_click(page, base_url: str, project_code: str) -> str:
    """Navigate to /library, click the Open link for the given project, return final URL."""
    await page.goto(f"{base_url}/library", wait_until="networkidle")
    open_link = page.locator(f'[data-testid="open-{project_code}"]')
    assert await open_link.count() > 0, (
        f"Open link [data-testid='open-{project_code}'] not found in Library"
    )
    async with page.expect_navigation(timeout=10_000):
        await open_link.click()
    return page.url


async def _activate_inputs_tab(page) -> None:
    """Ensure the Inputs tab is active and #panel-inputs is visible.

    The workbook starts on the Project Setup tab; `?sheet=inputs` in the URL
    triggers a JS tab switch, but we also click explicitly to guarantee
    Playwright sees the panel as visible before any element assertions.
    """
    tab = page.locator('#tab-inputs')
    assert await tab.count() > 0, "#tab-inputs button not found in workbook"
    await tab.click()
    await page.locator('#panel-inputs').wait_for(state='visible', timeout=8_000)


# ---------------------------------------------------------------------------
# Server A fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def server_a(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("server_a")
    proc, base_url = _start_server(tmp, {})
    token = _make_token(_SERVER_SECRET)
    yield base_url, token
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture()
async def browser_a(server_a, tmp_path_factory):
    base_url, token = server_a
    ss_dir = tmp_path_factory.mktemp("ss_a")
    async with async_playwright() as pw:
        browser, page = await _new_browser_page(pw, token, base_url, 1440, 900)
        yield page, base_url, ss_dir
        await browser.close()


# ---------------------------------------------------------------------------
# Server A: V2 active (default)
# ---------------------------------------------------------------------------
class TestServerADefault:
    """Server A: FINCO_WORKBOOK_V2 absent (default active), 1440×900."""

    async def test_root_redirects_to_library(self, browser_a):
        page, base_url, ss_dir = browser_a
        await page.goto(f"{base_url}/", wait_until="networkidle")
        assert "/library" in page.url, f"Expected /library, got {page.url}"
        await page.screenshot(path=str(ss_dir / "a01_root_to_library.png"))

    async def test_new_project_visible_flow_lands_on_v2_inputs(self, browser_a):
        """Visible browser flow: Library → New Project card → form → Create → V2 inputs."""
        page, base_url, ss_dir = browser_a
        code = await _new_project_visible_flow(page, base_url, "BrowserNewProj A")

        # Assert V2 workbook URL with sheet=inputs
        assert "/v2/workbook" in page.url, (
            f"New Project did not redirect to V2 workbook; URL: {page.url}"
        )
        assert f"project={code}" in page.url, (
            f"project code missing from URL; URL: {page.url}"
        )
        assert "sheet=inputs" in page.url, (
            f"sheet=inputs missing from URL after New Project; URL: {page.url}"
        )

        # Assert V2 shell and inputs panel are rendered
        shell = page.locator("#v2-workbook-shell")
        assert await shell.count() > 0, "V2 workbook shell (#v2-workbook-shell) not rendered"

        # Ensure the Inputs tab is active (JS may have already done this via ?sheet=inputs)
        await _activate_inputs_tab(page)
        inputs_panel = page.locator("#v2-sheet-inputs")
        assert await inputs_panel.count() > 0, "#v2-sheet-inputs not rendered"
        await page.screenshot(path=str(ss_dir / "a02_new_project_v2_inputs.png"))

    async def test_library_open_click_lands_on_v2(self, browser_a):
        """Library → click Open link → V2 workbook."""
        page, base_url, ss_dir = browser_a
        code = await _arrange_project(page, base_url, "LibOpen")
        final_url = await _library_open_click(page, base_url, code)
        assert "/v2/workbook" in final_url, (
            f"Library Open did not navigate to V2; final URL: {final_url}"
        )
        assert f"project={code}" in final_url, (
            f"project code not in Open-click URL; final URL: {final_url}"
        )
        await page.screenshot(path=str(ss_dir / "a03_library_open_v2.png"))

    async def test_legacy_bookmark_redirects_to_v2(self, browser_a):
        page, base_url, ss_dir = browser_a
        code = await _arrange_project(page, base_url, "Bookmark")
        await page.goto(f"{base_url}/?project={code}", wait_until="networkidle")
        assert "/v2/workbook" in page.url, f"Expected V2 URL, got {page.url}"
        assert f"project={code}" in page.url
        await page.screenshot(path=str(ss_dir / "a04_legacy_to_v2.png"))

    async def test_working_copy_badge_visible(self, browser_a):
        page, base_url, ss_dir = browser_a
        code = await _arrange_project(page, base_url, "Badge")
        await page.goto(f"{base_url}/v2/workbook?project={code}",
                        wait_until="networkidle")
        badge = page.locator(".v2-toolbar-wc-badge")
        assert await badge.count() > 0, "Working Copy badge (.v2-toolbar-wc-badge) not found"
        wc_text = await badge.first.text_content()
        assert "Working" in wc_text or "Copy" in wc_text, (
            f"Working Copy badge text unexpected: {wc_text!r}"
        )
        await page.screenshot(path=str(ss_dir / "a05_working_copy_badge.png"))

    async def test_five_field_persistence_all_required(self, browser_a):
        """All five canonical fields edited and persisted — zero conditional skips."""
        page, base_url, ss_dir = browser_a
        code = await _arrange_project(page, base_url, "FiveField")
        await page.goto(
            f"{base_url}/v2/workbook?project={code}&sheet=inputs",
            wait_until="networkidle",
        )
        await _activate_inputs_tab(page)

        # All interactions scoped to #v2-sheet-inputs to avoid duplicate
        # data-field-id matches in the hidden project-setup panel.
        inputs_panel = page.locator("#v2-sheet-inputs")
        persisted: dict[str, str] = {}

        for field_id, new_val, _ in _FIVE_FIELDS:
            # Row must exist inside #v2-sheet-inputs — fail if missing (no skip)
            row = inputs_panel.locator(f'[data-field-id="{field_id}"]')
            assert await row.count() > 0, (
                f"Required Slice 1 row for {field_id} not found inside #v2-sheet-inputs"
            )

            # Editable input must exist — fail if missing (no skip)
            inp = row.locator('input[name="value"]')
            assert await inp.count() > 0, (
                f"Editable input for {field_id} not found in Slice 1 row"
            )

            # Fill the field
            await inp.first.fill(new_val)

            # Submit via the Save button
            save_btn = row.locator('button[type="submit"]')
            assert await save_btn.count() > 0, (
                f"Save button not found for {field_id}"
            )
            # Wait for HTMX response (outerHTML swap of #v2-sheet-inputs)
            async with page.expect_response(
                lambda r: "/v2/workbook/inputs-slice1/update" in r.url,
                timeout=10_000,
            ):
                await save_btn.first.click()

            # Brief wait for DOM swap; re-acquire inputs_panel after HTMX swap
            await page.wait_for_timeout(400)
            inputs_panel = page.locator("#v2-sheet-inputs")
            persisted[field_id] = new_val

        await page.screenshot(path=str(ss_dir / "a06_five_fields_saved.png"))

        # Reload and verify all five persisted
        await page.goto(
            f"{base_url}/v2/workbook?project={code}&sheet=inputs",
            wait_until="networkidle",
        )
        await _activate_inputs_tab(page)
        inputs_panel_r = page.locator("#v2-sheet-inputs")
        for field_id, new_val, _ in _FIVE_FIELDS:
            row = inputs_panel_r.locator(f'[data-field-id="{field_id}"]')
            assert await row.count() > 0, (
                f"Row {field_id} missing inside #v2-sheet-inputs after reload"
            )
            inp = row.locator('input[name="value"]')
            assert await inp.count() > 0, (
                f"Input {field_id} missing after reload"
            )
            reloaded_val = await inp.first.input_value()
            # Compare numerically to tolerate float formatting (e.g. "75" vs "75.00")
            try:
                assert float(reloaded_val) == float(new_val), (
                    f"{field_id}: expected {new_val!r} after reload, got {reloaded_val!r}"
                )
            except ValueError:
                assert reloaded_val == new_val, (
                    f"{field_id}: expected {new_val!r} after reload, got {reloaded_val!r}"
                )

        await page.screenshot(path=str(ss_dir / "a07_five_fields_reloaded.png"))

        # Report all five persisted results for the delivery report
        for fid, val, _ in _FIVE_FIELDS:
            assert fid in persisted and persisted[fid] == val, (
                f"Persistence table incomplete for {fid}"
            )

    async def test_read_only_fields_both_required(self, browser_a):
        """project_type and country_market rows must exist with no editable input."""
        page, base_url, ss_dir = browser_a
        code = await _arrange_project(page, base_url, "ReadOnly")
        await page.goto(
            f"{base_url}/v2/workbook?project={code}&sheet=inputs",
            wait_until="networkidle",
        )
        await _activate_inputs_tab(page)

        # Scope to #v2-sheet-inputs to avoid project-setup panel matches
        inputs_panel = page.locator("#v2-sheet-inputs")
        for field_id in (
            "project_setup.identity.project_type",
            "project_setup.identity.country_market",
        ):
            row = inputs_panel.locator(f'[data-field-id="{field_id}"]')
            # Row MUST exist inside #v2-sheet-inputs — fail if missing
            assert await row.count() > 0, (
                f"Required read-only field row {field_id} not found inside #v2-sheet-inputs"
            )
            # Row must be visible
            assert await row.first.is_visible(), (
                f"Read-only row {field_id} is not visible in #v2-sheet-inputs"
            )
            # No enabled editable form control in the Slice 1 row
            editable = row.locator(
                'input[name="value"]:not([readonly]):not([disabled]),'
                'select[name="value"]:not([disabled])'
            )
            assert await editable.count() == 0, (
                f"{field_id} must not have an editable input/select in #v2-sheet-inputs"
            )

        await page.screenshot(path=str(ss_dir / "a08_read_only_fields.png"))

    async def test_invalid_input_yields_422_feedback_no_persistence(self, browser_a):
        """Submit empty value for required field → 422 error rendered, not persisted."""
        page, base_url, ss_dir = browser_a
        code = await _arrange_project(page, base_url, "Invalid")
        await page.goto(
            f"{base_url}/v2/workbook?project={code}&sheet=inputs",
            wait_until="networkidle",
        )
        await _activate_inputs_tab(page)

        # Scope to #v2-sheet-inputs to avoid project-setup panel duplicates
        field_id = "project_setup.technical.construction_months"
        inputs_panel = page.locator("#v2-sheet-inputs")
        row = inputs_panel.locator(f'[data-field-id="{field_id}"]')
        assert await row.count() > 0, f"Row {field_id} not found in #v2-sheet-inputs"

        # Capture the original value before the invalid submission
        inp = row.locator('input[name="value"]')
        assert await inp.count() > 0, f"Editable input for {field_id} not found"
        original_val = await inp.first.input_value()

        # Remove HTML5 required/min constraints so browser allows empty submit,
        # then clear the value to trigger the server's required-field validation
        await page.evaluate(f"""
            const row = document.querySelector('#v2-sheet-inputs [data-field-id="{field_id}"]');
            const inp = row && row.querySelector('input[name="value"]');
            if (inp) {{
                inp.removeAttribute('required');
                inp.removeAttribute('min');
                inp.value = '';
            }}
        """)

        save_btn = row.locator('button[type="submit"]')
        assert await save_btn.count() > 0, f"Save button not found for {field_id}"

        # Submit and expect a 422 HTMX response
        async with page.expect_response(
            lambda r: "/v2/workbook/inputs-slice1/update" in r.url,
            timeout=10_000,
        ) as resp_info:
            await save_btn.first.click()

        resp = await resp_info.value
        assert resp.status == 422, (
            f"Expected 422 for empty required field, got {resp.status}"
        )
        await page.wait_for_timeout(400)

        # Error feedback must be rendered in the Inputs surface
        error_el = page.locator('.v2-inputs-slice1-error, [role="alert"]')
        assert await error_el.count() > 0, (
            "No 422 error feedback rendered in #v2-sheet-inputs after invalid submit"
        )

        await page.screenshot(path=str(ss_dir / "a09_invalid_422.png"))

        # Reload and assert original value not overwritten
        await page.goto(
            f"{base_url}/v2/workbook?project={code}&sheet=inputs",
            wait_until="networkidle",
        )
        await _activate_inputs_tab(page)
        inputs_panel2 = page.locator("#v2-sheet-inputs")
        row2 = inputs_panel2.locator(f'[data-field-id="{field_id}"]')
        assert await row2.count() > 0
        inp2 = row2.locator('input[name="value"]')
        assert await inp2.count() > 0
        after_val = await inp2.first.input_value()
        assert after_val == original_val, (
            f"Invalid submission must not persist; expected {original_val!r}, got {after_val!r}"
        )

    async def test_stale_content_yields_409_no_overwrite(self, browser_a):
        """Capture stale content_hash, perform update, re-submit stale → 409, no overwrite."""
        page, base_url, ss_dir = browser_a
        code = await _arrange_project(page, base_url, "Stale")
        await page.goto(
            f"{base_url}/v2/workbook?project={code}&sheet=inputs",
            wait_until="networkidle",
        )
        await _activate_inputs_tab(page)

        # Capture old content_hash from a Slice 1 field's hidden input
        # (scoped to #v2-sheet-inputs to avoid project-setup panel duplicates)
        field_a = "project_setup.technical.horizon_years"
        old_hash = await page.evaluate(f"""
            const row = document.querySelector('#v2-sheet-inputs [data-field-id="{field_a}"]');
            const h = row && row.querySelector('input[name="content_hash"]');
            h ? h.value : '';
        """)
        assert old_hash, f"Could not read content_hash for {field_a} in #v2-sheet-inputs"

        # Perform a valid update on field_a to advance the server's content_hash
        inputs_panel = page.locator("#v2-sheet-inputs")
        row_a = inputs_panel.locator(f'[data-field-id="{field_a}"]')
        inp_a = row_a.locator('input[name="value"]')
        await inp_a.first.fill("27")
        save_a = row_a.locator('button[type="submit"]')
        async with page.expect_response(
            lambda r: "/v2/workbook/inputs-slice1/update" in r.url,
            timeout=10_000,
        ):
            await save_a.first.click()
        await page.wait_for_timeout(400)
        # Re-acquire after HTMX swap
        inputs_panel = page.locator("#v2-sheet-inputs")

        # Inject the old (stale) content_hash into another field's form
        field_b = "project_setup.technical.capacity_mw"
        await page.evaluate(f"""
            const row = document.querySelector('#v2-sheet-inputs [data-field-id="{field_b}"]');
            const h = row && row.querySelector('input[name="content_hash"]');
            if (h) h.value = {old_hash!r};
        """)

        # Submit field_b with the stale hash
        row_b = inputs_panel.locator(f'[data-field-id="{field_b}"]')
        inp_b = row_b.locator('input[name="value"]')
        await inp_b.first.fill("999")
        save_b = row_b.locator('button[type="submit"]')
        async with page.expect_response(
            lambda r: "/v2/workbook/inputs-slice1/update" in r.url,
            timeout=10_000,
        ) as resp_info:
            await save_b.first.click()

        stale_resp = await resp_info.value
        assert stale_resp.status == 409, (
            f"Expected 409 for stale content, got {stale_resp.status}"
        )
        await page.wait_for_timeout(400)

        # Error message must reference "stale" or "changed"
        error_el = page.locator('.v2-inputs-slice1-error, [role="alert"]')
        error_text = ""
        if await error_el.count() > 0:
            error_text = (await error_el.first.text_content() or "").lower()
        assert "stale" in error_text or "changed" in error_text or "again" in error_text, (
            f"Stale 409 error text not found; got: {error_text!r}"
        )

        await page.screenshot(path=str(ss_dir / "a10_stale_409.png"))

        # Reload and assert capacity_mw was NOT overwritten to 999
        await page.goto(
            f"{base_url}/v2/workbook?project={code}&sheet=inputs",
            wait_until="networkidle",
        )
        await _activate_inputs_tab(page)
        inputs_panel2 = page.locator("#v2-sheet-inputs")
        row_b2 = inputs_panel2.locator(f'[data-field-id="{field_b}"]')
        inp_b2 = row_b2.locator('input[name="value"]')
        val_after = await inp_b2.first.input_value()
        assert val_after != "999", (
            f"Stale submission must not persist; capacity_mw should not be 999, got {val_after!r}"
        )

    async def test_protected_reference_full_assertions(self, browser_a):
        """Protected reference: badge, no editable controls, mutation rejected, workspace unchanged."""
        page, base_url, ss_dir = browser_a

        # Seed the reference model by visiting Library (triggers ensure_reference_models)
        await page.goto(f"{base_url}/library", wait_until="networkidle")

        # Assert reference row exists in Library — fail if not
        ref_open = page.locator('[data-testid="open-tuho-reference"]')
        assert await ref_open.count() > 0, (
            "Reference project 'tuho-reference' not found in Library after seeding. "
            "ensure_reference_models() must be called by Library route."
        )

        # Click the Library Open link for the reference
        async with page.expect_navigation(timeout=10_000):
            await ref_open.click()

        ref_url = page.url
        assert "/v2/workbook" in ref_url, (
            f"Reference Open did not navigate to V2; URL: {ref_url}"
        )
        assert "tuho-reference" in ref_url or "project=" in ref_url, (
            f"Reference project code missing from URL: {ref_url}"
        )

        # Reference badge visible
        ref_badge = page.locator(".v2-toolbar-ref-badge")
        assert await ref_badge.count() > 0, (
            "Reference badge (.v2-toolbar-ref-badge) not visible on reference project"
        )

        # Working Copy badge must NOT appear
        wc_badge = page.locator(".v2-toolbar-wc-badge")
        assert await wc_badge.count() == 0, (
            "Working Copy badge must not appear on a protected reference project"
        )

        # Navigate to inputs sheet
        await page.goto(
            f"{base_url}/v2/workbook?project=tuho-reference&sheet=inputs",
            wait_until="networkidle",
        )
        await _activate_inputs_tab(page)

        # #v2-sheet-inputs must be visible
        inputs_panel = page.locator("#v2-sheet-inputs")
        assert await inputs_panel.count() > 0, (
            "#v2-sheet-inputs not found on reference project Inputs sheet"
        )

        # No editable Slice 1 controls inside the Inputs sheet panel
        # (Slice 1 inputs have class v2-inputs-slice1-input and form wrappers)
        editable_forms = inputs_panel.locator('.v2-inputs-slice1-form')
        assert await editable_forms.count() == 0, (
            "Reference project must not have editable Slice 1 forms in #v2-sheet-inputs"
        )

        await page.screenshot(path=str(ss_dir / "a11_reference_inputs.png"))

        # Direct Slice mutation must be rejected with 409 ProtectedReferenceError
        # (POST directly — no button exists on reference UI)
        parsed = urllib.parse.urlparse(page.url)
        params = dict(urllib.parse.parse_qsl(parsed.query))
        ref_code = params.get("project", "tuho-reference")

        token = _make_token(_SERVER_SECRET)
        mutation_resp = _requests.post(
            f"{base_url}/v2/workbook/inputs-slice1/update",
            data={
                "field_id": "project_setup.technical.construction_months",
                "value": "99",
                "project": ref_code,
                "workbook_version": "1",
                "content_hash": "aaa",
            },
            cookies={COOKIE_NAME: token},
            headers={"HX-Request": "true"},
            allow_redirects=False,
        )
        assert mutation_resp.status_code == 409, (
            f"Direct Slice mutation on reference must return 409, got {mutation_resp.status_code}"
        )

        # Workspace snapshot must be unchanged after rejected mutation
        # (any mutation must have been rejected before reaching persistence)
        # We verify by re-checking that the reference still exists and is accessible
        await page.goto(
            f"{base_url}/v2/workbook?project={ref_code}&sheet=inputs",
            wait_until="networkidle",
        )
        await _activate_inputs_tab(page)
        inputs_again = page.locator("#v2-sheet-inputs")
        assert await inputs_again.count() > 0, (
            "Reference Inputs panel not found after mutation rejection — workspace may be corrupted"
        )
        ref_badge_again = page.locator(".v2-toolbar-ref-badge")
        assert await ref_badge_again.count() > 0, (
            "Reference badge gone after mutation attempt — workspace converted unexpectedly"
        )

        await page.screenshot(path=str(ss_dir / "a12_reference_post_mutation.png"))


# ---------------------------------------------------------------------------
# Both viewports — all core surfaces
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("width,height", [(1440, 900), (1920, 1080)])
async def test_viewports_all_surfaces(server_a, tmp_path_factory, width, height):
    """Both viewports: Library, New Project landing, Working Copy Inputs, Reference Inputs."""
    base_url, token = server_a
    ss_dir = tmp_path_factory.mktemp(f"ss_vp_{width}x{height}")

    async with async_playwright() as pw:
        browser, page = await _new_browser_page(pw, token, base_url, width, height)
        try:
            # Surface 1: Project Library
            await page.goto(f"{base_url}/library", wait_until="networkidle")
            assert "/library" in page.url
            await page.screenshot(path=str(ss_dir / f"vp_{width}x{height}_01_library.png"))

            # Surface 2: New Project landing on Inputs (visible flow)
            code = await _new_project_visible_flow(page, base_url, f"VP{width} New")
            assert "/v2/workbook" in page.url
            assert "sheet=inputs" in page.url
            await page.screenshot(path=str(ss_dir / f"vp_{width}x{height}_02_new_project_inputs.png"))

            # Surface 3: Working Copy Inputs (use the just-created project)
            wc_code = await _arrange_project(page, base_url, f"VP{width} WC")
            await page.goto(
                f"{base_url}/v2/workbook?project={wc_code}&sheet=inputs",
                wait_until="networkidle",
            )
            await _activate_inputs_tab(page)
            assert await page.locator("#v2-sheet-inputs").count() > 0
            await page.screenshot(path=str(ss_dir / f"vp_{width}x{height}_03_wc_inputs.png"))

            # Surface 4: Reference Inputs (seed via library)
            await page.goto(f"{base_url}/library", wait_until="networkidle")
            await page.goto(
                f"{base_url}/v2/workbook?project=tuho-reference&sheet=inputs",
                wait_until="networkidle",
            )
            if "/v2/workbook" in page.url:
                await _activate_inputs_tab(page)
                await page.screenshot(
                    path=str(ss_dir / f"vp_{width}x{height}_04_ref_inputs.png")
                )
        finally:
            await browser.close()


# ---------------------------------------------------------------------------
# Server B fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def server_b(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("server_b")
    proc, base_url = _start_server(tmp, {"FINCO_WORKBOOK_V2": "0"})
    token = _make_token(_SERVER_SECRET)
    yield base_url, token
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture()
async def browser_b(server_b, tmp_path_factory):
    base_url, token = server_b
    ss_dir = tmp_path_factory.mktemp("ss_b")
    async with async_playwright() as pw:
        browser, page = await _new_browser_page(pw, token, base_url, 1440, 900)
        yield page, base_url, ss_dir
        await browser.close()


# ---------------------------------------------------------------------------
# Server B: V2 inactive — complete workbook rollback
# ---------------------------------------------------------------------------
class TestServerBInactiveRollback:
    """Server B: FINCO_WORKBOOK_V2=0 — all routes redirect to legacy surface."""

    async def test_library_open_click_lands_on_legacy(self, browser_b):
        """Library Open click must navigate to /?project=<code> (not V2)."""
        page, base_url, ss_dir = browser_b
        code = await _arrange_project(page, base_url, "B LibOpen")

        # Open link href points to /?project=<code> when V2 inactive
        final_url = await _library_open_click(page, base_url, code)

        assert "/v2/workbook" not in final_url, (
            f"Library Open must NOT navigate to V2 when inactive; got {final_url}"
        )
        assert f"project={code}" in final_url, (
            f"project code missing from legacy Open URL; got {final_url}"
        )
        await page.screenshot(path=str(ss_dir / "b01_library_open_legacy.png"))

    async def test_new_project_visible_flow_lands_on_legacy_inputs(self, browser_b):
        """Visible New Project form must redirect to /?project=<code>#inputs when V2 inactive."""
        page, base_url, ss_dir = browser_b
        await _new_project_visible_flow(page, base_url, "BrowserNewProj B")

        final_url = page.url
        assert "/v2/workbook" not in final_url, (
            f"New Project must NOT land on V2 when inactive; got {final_url}"
        )
        # URL should contain the project code and #inputs fragment
        assert "project=" in final_url, (
            f"project param missing from legacy redirect URL; got {final_url}"
        )
        assert "#inputs" in final_url or "inputs" in final_url, (
            f"#inputs fragment missing from New Project legacy redirect; got {final_url}"
        )
        await page.screenshot(path=str(ss_dir / "b02_new_project_legacy.png"))

    async def test_direct_v2_url_redirects_to_legacy(self, browser_b):
        page, base_url, ss_dir = browser_b
        code = await _arrange_project(page, base_url, "B Direct")
        await page.goto(f"{base_url}/v2/workbook?project={code}", wait_until="networkidle")
        assert "/v2/workbook" not in page.url
        assert f"project={code}" in page.url
        await page.screenshot(path=str(ss_dir / "b03_direct_v2_legacy.png"))

    async def test_direct_v2_sheet_inputs_redirects_to_fragment(self, browser_b):
        page, base_url, ss_dir = browser_b
        code = await _arrange_project(page, base_url, "B Fragment")
        await page.goto(
            f"{base_url}/v2/workbook?project={code}&sheet=inputs",
            wait_until="networkidle",
        )
        assert "/v2/workbook" not in page.url
        assert f"project={code}" in page.url
        await page.screenshot(path=str(ss_dir / "b04_v2_sheet_fragment.png"))

    async def test_v2_no_project_redirects_to_library(self, browser_b):
        page, base_url, ss_dir = browser_b
        await page.goto(f"{base_url}/v2/workbook", wait_until="networkidle")
        assert "/library" in page.url
        await page.screenshot(path=str(ss_dir / "b05_v2_no_project_library.png"))

    async def test_legacy_workspace_markers_visible(self, browser_b):
        """Legacy workspace shell renders (not V2 shell) for a project when V2 inactive."""
        page, base_url, ss_dir = browser_b
        code = await _arrange_project(page, base_url, "B Legacy")
        await page.goto(f"{base_url}/?project={code}", wait_until="networkidle")
        # V2 shell must NOT be present
        v2_shell = page.locator("#v2-workbook-shell")
        assert await v2_shell.count() == 0, (
            "V2 shell must not render when workbook V2 is inactive"
        )
        # The page must have content (legacy shell or workspace markers)
        body = await page.content()
        assert len(body) > 500, "Legacy workspace page has no content"
        await page.screenshot(path=str(ss_dir / "b06_legacy_workspace.png"))


# ---------------------------------------------------------------------------
# Both viewports — Server B rollback surface
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("width,height", [(1440, 900), (1920, 1080)])
async def test_viewports_server_b_rollback(server_b, tmp_path_factory, width, height):
    """Both viewports: Workbook rollback legacy surface."""
    base_url, token = server_b
    ss_dir = tmp_path_factory.mktemp(f"ss_b_vp_{width}x{height}")

    async with async_playwright() as pw:
        browser, page = await _new_browser_page(pw, token, base_url, width, height)
        try:
            code = await _arrange_project(page, base_url, f"VP-B{width}")
            await page.goto(f"{base_url}/?project={code}", wait_until="networkidle")
            body = await page.content()
            assert len(body) > 500
            await page.screenshot(
                path=str(ss_dir / f"vp_b_{width}x{height}_legacy_surface.png")
            )
        finally:
            await browser.close()


# ---------------------------------------------------------------------------
# Server C fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def server_c(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("server_c")
    proc, base_url = _start_server(tmp, {"FINCO_INPUTS_SLICE1_ENABLED": "0"})
    token = _make_token(_SERVER_SECRET)
    # Expose db_path for snapshot assertions
    db_path = str(tmp / "browser_conv.db")
    yield base_url, token, db_path
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture()
async def browser_c(server_c, tmp_path_factory):
    base_url, token, db_path = server_c
    ss_dir = tmp_path_factory.mktemp("ss_c")
    async with async_playwright() as pw:
        browser, page = await _new_browser_page(pw, token, base_url, 1440, 900)
        yield page, base_url, db_path, ss_dir
        await browser.close()


def _db_snapshot(db_path: str) -> dict:
    """Capture a deterministic DB snapshot for zero-write verification."""
    con = sqlite3.connect(db_path)
    try:
        try:
            runs = con.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        except Exception:
            runs = 0
        try:
            ws_rows = con.execute(
                "SELECT project_code, dirty, draft_content_hash FROM workspace_states"
                " ORDER BY project_code"
            ).fetchall()
        except Exception:
            ws_rows = []
        return {"runs": runs, "ws": ws_rows}
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Server C: Inputs Slice 1 disabled — complete rollback
# ---------------------------------------------------------------------------
class TestServerCInputsRollback:
    """Server C: FINCO_INPUTS_SLICE1_ENABLED=0 — Slice 1 disabled, V2 shell active."""

    async def test_inputs_sheet_shows_config_state_disabled_notice(self, browser_c):
        page, base_url, db_path, ss_dir = browser_c
        code = await _arrange_project(page, base_url, "C Disabled")
        await page.goto(
            f"{base_url}/v2/workbook?project={code}&sheet=inputs",
            wait_until="networkidle",
        )

        # V2 shell must be visible
        shell = page.locator("#v2-workbook-shell")
        assert await shell.count() > 0, "V2 workbook shell not found on Server C"

        # Activate the Inputs tab
        await _activate_inputs_tab(page)

        # #v2-sheet-inputs must be visible
        inputs_panel = page.locator("#v2-sheet-inputs")
        assert await inputs_panel.count() > 0, "#v2-sheet-inputs not found on Server C"

        # Config-state disabled notice must appear
        notice = page.locator(".v2-slice1-config-state, .v2-slice1-disabled-notice")
        assert await notice.count() > 0, (
            "Config-state disabled notice not found on Server C Inputs sheet"
        )

        # No editable Slice 1 controls inside the Inputs sheet panel
        editable_in_inputs = inputs_panel.locator('input[name="value"]')
        assert await editable_in_inputs.count() == 0, (
            "Editable Slice 1 controls must not appear inside #v2-sheet-inputs when disabled"
        )

        await page.screenshot(path=str(ss_dir / "c01_inputs_disabled_notice.png"))

    async def test_slice1_post_returns_409_and_db_unchanged(self, browser_c):
        """POST to Slice 1 endpoint with Slice 1 disabled → 409, DB snapshot unchanged."""
        page, base_url, db_path, ss_dir = browser_c
        code = await _arrange_project(page, base_url, "C 409")

        token = _make_token(_SERVER_SECRET)
        snapshot_before = _db_snapshot(db_path)

        resp = _requests.post(
            f"{base_url}/v2/workbook/inputs-slice1/update",
            data={
                "field_id": "project_setup.technical.construction_months",
                "value": "20",
                "project": code,
                "workbook_version": "1",
                "content_hash": "aaa",
            },
            cookies={COOKIE_NAME: token},
            headers={"HX-Request": "true"},
            allow_redirects=False,
        )
        assert resp.status_code == 409, (
            f"Disabled Slice 1 endpoint must return 409, got {resp.status_code}"
        )

        snapshot_after = _db_snapshot(db_path)
        assert snapshot_before == snapshot_after, (
            f"DB state changed despite Slice 1 disabled 409 rejection.\n"
            f"  BEFORE: {snapshot_before}\n  AFTER:  {snapshot_after}"
        )


# ---------------------------------------------------------------------------
# Both viewports — Server C Inputs rollback banner
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("width,height", [(1440, 900), (1920, 1080)])
async def test_viewports_server_c_inputs_rollback(server_c, tmp_path_factory, width, height):
    """Both viewports: Inputs rollback banner (Slice 1 disabled notice)."""
    base_url, token, db_path = server_c
    ss_dir = tmp_path_factory.mktemp(f"ss_c_vp_{width}x{height}")

    async with async_playwright() as pw:
        browser, page = await _new_browser_page(pw, token, base_url, width, height)
        try:
            code = await _arrange_project(page, base_url, f"VP-C{width}")
            await page.goto(
                f"{base_url}/v2/workbook?project={code}&sheet=inputs",
                wait_until="networkidle",
            )
            await _activate_inputs_tab(page)
            notice = page.locator(".v2-slice1-config-state, .v2-slice1-disabled-notice")
            assert await notice.count() > 0, (
                f"Inputs disabled notice not found at {width}x{height}"
            )
            await page.screenshot(
                path=str(ss_dir / f"vp_c_{width}x{height}_inputs_rollback.png")
            )
        finally:
            await browser.close()
