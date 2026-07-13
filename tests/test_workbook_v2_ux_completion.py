"""
Tests for Workbook V2 UX completion (PR 6/6).

Coverage:
1. Toolbar renders project identity fields (name, type, scenario)
2. Tab navigation: all 8 sheet tabs present; first panel visible, rest hidden
3. Status banner: NOT_RUN, dirty, clean wording
4. Runtime state language: consistent across debt/tax/fs bars
5. No migration copy in rendered HTML (no "migration", "engine-bound",
   "not yet connected", "PARTIAL", "Run Required" in user-facing copy)
6. Run controls OOB div present for HTMX swap
7. Input Coverage Gap: future-input tags render for placeholder rows
"""
from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("FINCO_WORKBOOK_V2", "1")
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-for-v2-ux-tests")

from fastapi.testclient import TestClient  # noqa: E402

import main_web  # noqa: E402
from app.auth import COOKIE_NAME, SessionData, create_session_token  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _authed_client() -> TestClient:
    tc = TestClient(main_web.app, follow_redirects=False)
    tc.cookies.set(COOKIE_NAME, create_session_token())
    return tc


def _create_project(client: TestClient, suffix: str = "ux") -> str:
    import urllib.parse
    resp = client.post(
        "/projects/create",
        data={
            "project_name": f"UX Test {suffix}",
            "project_type": "Solar",
            "template_source": "generic_solar",
            "country_market": "Poland",
            "capacity_mw": "50",
            "cod_date": "2028-01-01",
            "construction_months": "18",
            "horizon_years": "25",
            "tariff_eur_mwh": "55",
            "ppa_term_years": "15",
            "p50_hours": "1800",
            "opex_y1_keur": "700",
            "total_capex_keur": "45000",
            "gearing_pct": "70",
            "interest_rate_pct": "4.5",
            "tenor_years": "18",
            "target_dscr": "1.30",
        },
        follow_redirects=False,
    )
    redirect = resp.headers.get("hx-redirect") or resp.headers.get("location", "")
    assert redirect, f"expected redirect from /projects/create, got {resp.status_code}"
    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query)
    codes = parsed.get("project", [])
    assert codes, f"no project= in redirect URL: {redirect}"
    return codes[0]


def _get_workbook(client: TestClient, project_code: str) -> str:
    resp = client.get(f"/v2/workbook?project={project_code}")
    assert resp.status_code == 200, f"GET /v2/workbook failed: {resp.status_code}"
    return resp.text


# ---------------------------------------------------------------------------
# 1. Toolbar
# ---------------------------------------------------------------------------

class TestToolbar(unittest.TestCase):
    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "toolbar")

    def test_toolbar_present(self):
        body = _get_workbook(self.client, self.project_code)
        self.assertIn('class="v2-toolbar"', body, "v2-toolbar div missing")

    def test_project_name_in_toolbar(self):
        body = _get_workbook(self.client, self.project_code)
        self.assertIn("v2-toolbar-name", body)
        self.assertIn("UX Test toolbar", body)

    def test_run_controls_div_present(self):
        body = _get_workbook(self.client, self.project_code)
        self.assertIn('id="v2-run-controls"', body,
                      "#v2-run-controls must be present for OOB HTMX swap")


# ---------------------------------------------------------------------------
# 2. Tab navigation
# ---------------------------------------------------------------------------

class TestTabNavigation(unittest.TestCase):
    EXPECTED_TABS = [
        "Project Setup", "Inputs", "Revenue", "CAPEX", "OPEX",
        "Senior Debt", "Tax", "Financial Statements",
    ]

    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "tabs")

    def test_all_eight_tabs_present(self):
        body = _get_workbook(self.client, self.project_code)
        for tab_label in self.EXPECTED_TABS:
            self.assertIn(tab_label, body,
                          f"Tab '{tab_label}' missing from workbook")

    def test_tablist_role_present(self):
        body = _get_workbook(self.client, self.project_code)
        self.assertIn('role="tablist"', body)

    def test_first_tab_selected(self):
        body = _get_workbook(self.client, self.project_code)
        # First tab must have aria-selected="true"
        import re
        first_selected = re.search(
            r'<button[^>]+role="tab"[^>]+aria-selected="true"', body
        )
        self.assertIsNotNone(first_selected, "No tab has aria-selected=true")

    def test_sheet_panels_present(self):
        body = _get_workbook(self.client, self.project_code)
        self.assertGreaterEqual(
            body.count('class="v2-sheet-panel"'), 8,
            "Expected 8 sheet panels"
        )

    def test_hidden_attribute_on_non_active_panels(self):
        body = _get_workbook(self.client, self.project_code)
        # At least 7 panels must have hidden attribute
        hidden_count = body.count('v2-sheet-panel" role="tabpanel" id="panel-') + \
                       body.count('v2-sheet-panel" role="tabpanel"')
        # simpler: count `hidden` within sheet panels
        import re
        panels_hidden = re.findall(
            r'<div class="v2-sheet-panel"[^>]*hidden', body
        )
        self.assertGreaterEqual(len(panels_hidden), 7,
                                "Expected at least 7 hidden sheet panels")


# ---------------------------------------------------------------------------
# 3. Status banner wording
# ---------------------------------------------------------------------------

class TestStatusBannerWording(unittest.TestCase):
    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "banner")

    def test_not_run_banner_shown_on_fresh_project(self):
        body = _get_workbook(self.client, self.project_code)
        self.assertIn("Model has not been run", body,
                      "Fresh project should show NOT_RUN banner")

    def test_no_stale_developer_banner_text(self):
        body = _get_workbook(self.client, self.project_code)
        self.assertNotIn("Draft changed — Run required", body,
                         "Old banner wording must be replaced")


# ---------------------------------------------------------------------------
# 4. Runtime state language consistency
# ---------------------------------------------------------------------------

class TestRuntimeStateLanguage(unittest.TestCase):
    """Runtime bar templates use consistent vocabulary across debt/tax/fs."""

    def _render_debt_bar(self, debt_state: str) -> str:
        from jinja2 import Environment, FileSystemLoader
        import os
        tpl_dir = os.path.join(
            os.path.dirname(__file__), "..", "app", "templates", "v2"
        )
        env = Environment(loader=FileSystemLoader(tpl_dir))
        tpl = env.get_template("partials/_debt_runtime_bar.html")
        return tpl.render(debt_state=debt_state)

    def _render_tax_bar(self, tax_state: str) -> str:
        from jinja2 import Environment, FileSystemLoader
        import os
        tpl_dir = os.path.join(
            os.path.dirname(__file__), "..", "app", "templates", "v2"
        )
        env = Environment(loader=FileSystemLoader(tpl_dir))
        tpl = env.get_template("partials/_tax_runtime_bar.html")
        return tpl.render(tax_state=tax_state)

    def _render_fs_bar(self, fs_state: str) -> str:
        from jinja2 import Environment, FileSystemLoader
        import os
        tpl_dir = os.path.join(
            os.path.dirname(__file__), "..", "app", "templates", "v2"
        )
        env = Environment(loader=FileSystemLoader(tpl_dir))
        tpl = env.get_template("partials/_fs_runtime_bar.html")
        return tpl.render(fs_state=fs_state)

    def test_debt_not_run_says_not_run(self):
        html = self._render_debt_bar("NOT_RUN")
        self.assertIn("Not run", html)
        self.assertNotIn("Run Required", html)
        self.assertNotIn("Available after Run", html)

    def test_debt_clean_says_outputs_current(self):
        html = self._render_debt_bar("CLEAN")
        self.assertIn("Outputs current", html)

    def test_debt_stale_says_run_required(self):
        html = self._render_debt_bar("STALE")
        self.assertIn("Run required", html)
        self.assertNotIn("stale for current draft", html)

    def test_debt_unavailable_says_output_unavailable(self):
        html = self._render_debt_bar("UNAVAILABLE")
        self.assertIn("Output unavailable", html)
        self.assertNotIn("persisted", html)

    def test_tax_not_run_says_not_run(self):
        html = self._render_tax_bar("NOT_RUN")
        self.assertIn("Not run", html)
        self.assertNotIn("Run Required", html)

    def test_tax_stale_says_run_required(self):
        html = self._render_tax_bar("STALE")
        self.assertIn("Run required", html)

    def test_fs_not_run_says_not_run(self):
        html = self._render_fs_bar("NOT_RUN")
        self.assertIn("Not run", html)
        self.assertNotIn("Not yet run", html)

    def test_fs_stale_says_run_required(self):
        html = self._render_fs_bar("STALE")
        self.assertIn("Run required", html)

    def test_fs_unavailable_says_output_unavailable(self):
        html = self._render_fs_bar("FS_UNAVAILABLE")
        self.assertIn("Output unavailable", html)

    def test_debt_tax_fs_not_run_vocabulary_identical(self):
        debt_html = self._render_debt_bar("NOT_RUN")
        tax_html = self._render_tax_bar("NOT_RUN")
        fs_html = self._render_fs_bar("NOT_RUN")
        for html, name in [(debt_html, "debt"), (tax_html, "tax"), (fs_html, "fs")]:
            self.assertIn("Not run", html,
                          f"{name} NOT_RUN must say 'Not run'")


# ---------------------------------------------------------------------------
# 5. No migration copy in rendered page
# ---------------------------------------------------------------------------

class TestNoMigrationCopy(unittest.TestCase):
    FORBIDDEN_STRINGS = [
        "engine-bound",
        "not engine-bound",
        "Planned in future migration",
        "Available after Production migration",
        "Available after Revenue migration",
        "Not yet connected",
        "not yet connected",
        "Available after future migration",
    ]

    def setUp(self):
        self.client = _authed_client()
        self.project_code = _create_project(self.client, "copy")

    def test_no_migration_copy_in_workbook(self):
        body = _get_workbook(self.client, self.project_code)
        for forbidden in self.FORBIDDEN_STRINGS:
            self.assertNotIn(
                forbidden, body,
                f"Migration copy '{forbidden}' found in rendered workbook"
            )

    def test_no_raw_partial_badge_text(self):
        body = _get_workbook(self.client, self.project_code)
        # The PARTIAL classification value should not appear as raw user-visible text
        # (it can appear in data-testid attributes which are not user-facing)
        import re
        # Find text content inside span tags - PARTIAL should not appear as a span's text content
        partial_in_text = re.findall(
            r'<span[^>]*>\s*PARTIAL\s*</span>', body
        )
        self.assertEqual(len(partial_in_text), 0,
                         f"Raw 'PARTIAL' text found in span elements: {partial_in_text}")


# ---------------------------------------------------------------------------
# 6. Input Coverage Gap: future-input tags
# ---------------------------------------------------------------------------

class TestFutureInputTags(unittest.TestCase):
    """Placeholder rows render v2-future-tag, not old placeholder-tag."""

    def _render_sheet(self, template_name: str, ctx: dict) -> str:
        from jinja2 import Environment, FileSystemLoader
        import os
        tpl_dir = os.path.join(
            os.path.dirname(__file__), "..", "app", "templates", "v2"
        )
        env = Environment(loader=FileSystemLoader(tpl_dir))
        tpl = env.get_template(template_name)
        return tpl.render(**ctx)

    def _base_ctx(self) -> dict:
        return {
            "project_code": "TEST001",
            "workbook_version": "1",
            "content_hash": "abc123",
            "project_editable": True,
            "ws_dirty": False,
            "has_runtime": False,
            "field_error": None,
            "flash_error": None,
        }

    def test_senior_debt_future_tags_present(self):
        ctx = {**self._base_ctx(), "debt_fields": [], "debt_schedule": None,
               "runtime_summary": None, "debt_operational_periods": None,
               "debt_state": "NOT_RUN"}
        html = self._render_sheet("partials/sheet_senior_debt.html", ctx)
        self.assertIn("v2-future-tag", html,
                      "Senior Debt placeholders must use v2-future-tag")
        self.assertNotIn("v2-placeholder-tag", html)

    def test_revenue_future_tags_present(self):
        ctx = {**self._base_ctx(), "revenue_fields": []}
        html = self._render_sheet("partials/sheet_revenue.html", ctx)
        self.assertIn("v2-future-tag", html,
                      "Revenue placeholders must use v2-future-tag")
        self.assertNotIn("v2-placeholder-tag", html)

    def test_senior_debt_no_migration_copy(self):
        ctx = {**self._base_ctx(), "debt_fields": [], "debt_schedule": None,
               "runtime_summary": None, "debt_operational_periods": None,
               "debt_state": "NOT_RUN"}
        html = self._render_sheet("partials/sheet_senior_debt.html", ctx)
        self.assertNotIn("engine-bound", html)
        self.assertNotIn("this PR", html)
        self.assertNotIn("future registry expansion", html)


if __name__ == "__main__":
    unittest.main()
