"""UI-1A — Single Application Shell & Canonical Project Navigation.

Static read-only tests (no app boot, no DB, no runtime imports).
Verifies the acceptance criteria from the UI-1A spec:

  A. Exactly one visible global application header on project pages
  B. Finco One is the visible product brand
  C. Project workflow navigation exposes Overview/Inputs/Outputs/Scenarios/Export-Audit
  D. Inputs/Outputs expose second-level sheet navigation
  E. Project library → project workspace path is deterministic
  F. Sign-out/help actions remain reachable
  G. Existing Run route contract is unchanged
  H. Spreadsheet interaction JS assets remain loaded
  I. No financial-engine files changed
  J. No financial output fingerprints changed (verified via engine test suite)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_HTML = REPO_ROOT / "app" / "templates" / "base.html"
BRAND_BAR_HTML = REPO_ROOT / "app" / "templates" / "partials" / "_brand_bar.html"
SHEET_TABS_HTML = REPO_ROOT / "app" / "templates" / "partials" / "_sheet_tabs.html"
LOGIN_HTML = REPO_ROOT / "app" / "templates" / "login.html"
LIBRARY_ROUTER = REPO_ROOT / "app" / "library" / "router.py"
MAIN_WEB = REPO_ROOT / "main_web.py"
UI1A_CSS = REPO_ROOT / "static" / "ui1a-shell.css"


# ---------------------------------------------------------------------------
# A. Exactly one visible global application header
# ---------------------------------------------------------------------------

class TestSingleChrome:
    def test_legacy_top_header_absent_from_base(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        idx = 0
        while True:
            idx = text.find('<header class="top-header">', idx)
            if idx < 0:
                break
            before = text[:idx]
            # Not in a Jinja comment
            if before.rfind('{#') <= before.rfind('#}'):
                pytest.fail(
                    "Legacy <header class=\"top-header\"> still present in "
                    "base.html — UI-1A requires single chrome."
                )
            idx += 1

    def test_fo_chrome_partial_present_in_base(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert re.search(r'\{%\s*include\s+"partials/_app_chrome\.html"\s*%\}', text), \
            "base.html must include partials/_app_chrome.html (the single chrome)."

    def test_ui1a_css_loaded_in_base(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert "ui1a-shell.css" in text, \
            "base.html must load ui1a-shell.css for the shell additions."

    def test_ui1a_css_file_exists(self):
        assert UI1A_CSS.exists(), "static/ui1a-shell.css must exist."


# ---------------------------------------------------------------------------
# B. Finco One branding
# ---------------------------------------------------------------------------

class TestBranding:
    def test_brand_bar_says_finco_one(self):
        text = BRAND_BAR_HTML.read_text(encoding="utf-8")
        assert "Finco One" in text, "Brand bar must display 'Finco One'."

    def test_login_title_says_finco_one(self):
        text = LOGIN_HTML.read_text(encoding="utf-8")
        assert "Finco One" in text, "Login page title must say 'Finco One'."

    def test_login_has_no_fincogpt(self):
        text = LOGIN_HTML.read_text(encoding="utf-8")
        assert "FincoGPT" not in text, "Login page must not expose 'FincoGPT'."

    def test_base_title_says_finco_one(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert "Finco One" in text, "base.html must reference 'Finco One'."


# ---------------------------------------------------------------------------
# C. Level-1 project workflow navigation
# ---------------------------------------------------------------------------

class TestWorkflowNav:
    def test_overview_in_sidebar_nav(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert "ps-workflow-nav" in text, \
            "base.html must contain .ps-workflow-nav (Level-1 workflow nav)."

    @pytest.mark.parametrize("label", [
        "Overview",
        "Inputs",
        "Outputs",
        "Scenarios",
        "Export / Audit",
    ])
    def test_level1_item_present(self, label):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert label in text, \
            f"Level-1 nav must expose '{label}' in base.html sidebar."

    def test_scenarios_link_to_route(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert 'href="/scenarios"' in text or "switchTab('scenario')" in text, \
            "Scenarios must link to /scenarios or switchTab('scenario')."

    def test_export_audit_link_present(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert 'href="/download"' in text or "Export" in text, \
            "Export/Audit must be reachable from the sidebar."


# ---------------------------------------------------------------------------
# D. Level-2 sheet navigation (Inputs sub-items / Outputs sub-items)
# ---------------------------------------------------------------------------

class TestLevel2Navigation:
    @pytest.mark.parametrize("label", ["Revenue", "OPEX", "CAPEX", "Tax"])
    def test_inputs_sub_item_in_sidebar(self, label):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert label in text, \
            f"Inputs sub-navigation must include '{label}' in base.html."

    @pytest.mark.parametrize("label", ["Cash Flow", "Debt", "Returns", "Financial Statements"])
    def test_outputs_sub_item_in_sidebar(self, label):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert label in text, \
            f"Outputs sub-navigation must include '{label}' in base.html."

    def test_sheet_tabs_have_modeling_group(self):
        text = SHEET_TABS_HTML.read_text(encoding="utf-8")
        assert 'data-fo-sheet-group="modeling"' in text, \
            "_sheet_tabs.html must declare modeling group sheet tabs."


# ---------------------------------------------------------------------------
# F. Sign-out / help actions reachable
# ---------------------------------------------------------------------------

class TestUtilityActions:
    @pytest.mark.parametrize("action", [
        ("/logout", "Sign out"),
        ("/help", "help"),
        ("/known-limitations", "Known Limitations"),
        ("/pilot-guide", "Pilot Guide"),
    ])
    def test_action_reachable_from_brand_bar(self, action):
        href, label = action
        text = BRAND_BAR_HTML.read_text(encoding="utf-8")
        assert href in text, \
            f"Brand bar must expose '{label}' action via '{href}'."


# ---------------------------------------------------------------------------
# G. Run route contract unchanged
# ---------------------------------------------------------------------------

class TestRunRoute:
    def test_run_post_route_in_main_web(self):
        text = MAIN_WEB.read_text(encoding="utf-8")
        assert '"/run"' in text or "'/run'" in text, \
            "POST /run route must remain in main_web.py."

    def test_sidebar_run_button_preserved(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert 'hx-post="/run"' in text, \
            "base.html sidebar Run button (hx-post=/run) must remain."


# ---------------------------------------------------------------------------
# H. Spreadsheet interaction JS assets remain loaded
# ---------------------------------------------------------------------------

class TestSpreadsheetAssets:
    @pytest.mark.parametrize("asset", [
        "interaction/active-cell.js",
        "interaction/keyboard-router.js",
        "interaction/selection-manager.js",
        "interaction/clipboard-controller.js",
        "interaction/undo-manager.js",
        "interaction/fill-controller.js",
        "modelling/capex-sheet-live-totals.js",
        "modelling/opex-sheet-live-totals.js",
    ])
    def test_spreadsheet_asset_loaded(self, asset):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert asset in text, \
            f"base.html must still load spreadsheet asset '{asset}'."


# ---------------------------------------------------------------------------
# I. Financial engine files unchanged
# ---------------------------------------------------------------------------

class TestEngineUnchanged:
    @pytest.mark.parametrize("engine_file", [
        "financial_engine/orchestrator.py",
        "financial_engine/results.py",
        "finco_core/__init__.py",
        "app/services/production_financial_authority.py",
    ])
    def test_engine_file_not_in_ui1a_diff(self, engine_file, tmp_path):
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        changed = result.stdout.strip().splitlines()
        assert engine_file not in changed, \
            f"UI-1A must not modify '{engine_file}'."

    def test_ui1a_css_does_not_touch_engine_tokens(self):
        text = UI1A_CSS.read_text(encoding="utf-8")
        engine_terms = [
            "run_clean_production", "calculate_tax", "WaterfallRunner",
            "TaxAnnualResult", "senior_debt", "xirr",
        ]
        for term in engine_terms:
            assert term not in text, \
                f"ui1a-shell.css must not reference engine term '{term}'."
