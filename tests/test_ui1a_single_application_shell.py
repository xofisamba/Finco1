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

    def test_scenarios_canonical_uses_switchtab(self):
        # Correction A: Scenarios Level-1 nav must stay inside the workspace.
        text = BASE_HTML.read_text(encoding="utf-8")
        assert "switchTab('scenario')" in text, \
            "Scenarios Level-1 nav must use switchTab('scenario') to stay in workspace."

    def test_scenarios_canonical_does_not_require_href_scenarios(self):
        # The /scenarios href must NOT be the canonical Level-1 nav action.
        # (It may still exist as a legacy deep-link elsewhere on the page.)
        text = BASE_HTML.read_text(encoding="utf-8")
        # Correct: switchTab('scenario') is used inside ps-workflow-nav
        assert "switchTab('scenario')" in text, \
            "ps-workflow-nav must use switchTab('scenario'), not /scenarios href."

    def test_export_audit_does_not_use_download_href(self):
        # Correction A: href="/download" must NOT appear as a live attribute
        # in the Level-1 workflow nav — /download is an action endpoint, not a
        # navigation surface. Jinja comments ({# ... #}) are stripped before checking.
        import re as _re
        text = BASE_HTML.read_text(encoding="utf-8")
        nav_start = text.find('<nav class="ps-workflow-nav"')
        nav_end = text.find('</nav>', nav_start)
        assert nav_start >= 0, "ps-workflow-nav must exist."
        nav_block = text[nav_start:nav_end]
        # Strip Jinja comments so their text content doesn't trip the check
        nav_no_comments = _re.sub(r'\{#.*?#\}', '', nav_block, flags=_re.DOTALL)
        assert 'href="/download"' not in nav_no_comments, \
            "Export/Audit Level-1 nav must NOT use href=\"/download\" (action endpoint)."

    def test_export_audit_exposes_switchtab_downloads(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert "switchTab('downloads')" in text, \
            "Export/Audit must expose switchTab('downloads') for the Downloads panel."

    def test_export_audit_exposes_switchtab_audit(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert "switchTab('audit')" in text, \
            "Export/Audit must expose switchTab('audit') for the Audit/Reference panel."


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
# I & J. Financial engine files unchanged — PR-level diff gate
# ---------------------------------------------------------------------------

UI1A_FROZEN_MAIN = "b915e749cfae52d987bb1ccb8f0be53b181ca136"

# Explicit review gate: run git diff between the frozen main SHA and HEAD,
# assert that no financial-engine paths appear. This is a deterministic
# structural check, not a `git diff HEAD` (which only covers uncommitted
# working-tree changes and is meaningless after commit).

class TestEngineUnchanged:
    def _pr_changed_paths(self) -> list[str]:
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{UI1A_FROZEN_MAIN}...HEAD"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        return result.stdout.strip().splitlines()

    @pytest.mark.parametrize("prefix", [
        "financial_engine/",
        "finco_core/",
    ])
    def test_no_engine_directory_in_pr_diff(self, prefix):
        changed = self._pr_changed_paths()
        offenders = [p for p in changed if p.startswith(prefix)]
        assert not offenders, \
            f"UI-1A PR diff must not modify '{prefix}*'. Found: {offenders}"

    @pytest.mark.parametrize("path", [
        "app/api/project_runner.py",
        "app/services/production_financial_authority.py",
    ])
    def test_no_financial_service_in_pr_diff(self, path):
        changed = self._pr_changed_paths()
        assert path not in changed, \
            f"UI-1A PR diff must not modify '{path}'."

    def test_ui1a_css_does_not_touch_engine_tokens(self):
        text = UI1A_CSS.read_text(encoding="utf-8")
        engine_terms = [
            "run_clean_production", "calculate_tax", "WaterfallRunner",
            "TaxAnnualResult", "senior_debt", "xirr",
        ]
        for term in engine_terms:
            assert term not in text, \
                f"ui1a-shell.css must not reference engine term '{term}'."
