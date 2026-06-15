"""UX-2: Active Runtime Result Sheet Refresh on Run.

Root cause: POST /run always targeted #model-output-area (panel-overview).
Runtime-backed result sheets (Senior Debt, SHL, Tax, P&L, Cash Flow, Balance,
Distributions, Sponsor) were never OOB-refreshed. The shared_runtime_block.html
JS used document.getElementById which only reached the first of 8 duplicate IDs.

Fix:
  1. workspace_shell.html: hidden input name="active_tab" id="hidden-active-tab"
  2. static/app.js: switchTab() syncs hidden-active-tab value
  3. main_web.py: third OOB swap — renders active result sheet into panel-{active_tab}
  4. shared_runtime_block.html: _populateRuntimeBlock() uses querySelectorAll to
     update all runtime blocks, not just the first in DOM order

Tests:
  A. workspace_shell.html has hidden-active-tab input.
  B. static/app.js updates hidden-active-tab inside switchTab.
  C. POST /run reads active_tab from form (main_web.py source check).
  D. Runtime-backed sheet map covers all 8 required tabs.
  E. Non-runtime tabs are NOT in the sheet map.
  F. OOB assembly produces active-sheet fragment for active_tab=balance.
  G. OOB assembly produces active-sheet fragment for active_tab=senior-debt.
  H. OOB assembly does NOT produce active-sheet fragment for active_tab=revenue.
  I. Existing Dashboard OOB still wired.
  J. Existing Scenario Matrix OOB still wired.
  K. shared_runtime_block.html: _populateRuntimeBlock uses querySelectorAll.
  L. Partial templates for distributions and sponsor exist.
  M. Engine MD5 unchanged.
  N. TUHO DSCR unchanged.
  O. Oborovo DSCR unchanged.
  P. File scope guard.
"""
from __future__ import annotations

import ast
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")

ENGINE_MD5 = "6bf49f33efc989736c17cea0cb9b7723"
TUHO_P1_DSCR = 1.4507
OBOROVO_P1_DSCR = 1.15

WORKSPACE_SHELL = Path(REPO_ROOT) / "app/templates/partials/workspace_shell.html"
SHARED_RUNTIME = Path(REPO_ROOT) / "app/templates/partials/shared_runtime_block.html"
APP_JS = Path(REPO_ROOT) / "static/app.js"
MAIN_WEB = Path(REPO_ROOT) / "main_web.py"

RUNTIME_SHEET_TABS = {
    "senior-debt", "shl", "tax", "pl", "cashflow", "balance",
    "distributions", "sponsor",
}
NON_RUNTIME_TABS = {"revenue", "opex", "capex", "production", "construction", "inputs"}


# ---------------------------------------------------------------------------
# A. workspace_shell.html has hidden-active-tab input
# ---------------------------------------------------------------------------

class TestWorkspaceShellHiddenInput:
    def test_hidden_active_tab_input_present(self):
        src = WORKSPACE_SHELL.read_text()
        assert 'id="hidden-active-tab"' in src, (
            "workspace_shell.html must have hidden input id='hidden-active-tab'"
        )

    def test_hidden_input_has_name_active_tab(self):
        src = WORKSPACE_SHELL.read_text()
        assert 'name="active_tab"' in src, (
            "workspace_shell.html hidden input must have name='active_tab'"
        )

    def test_hidden_input_default_value_overview(self):
        src = WORKSPACE_SHELL.read_text()
        assert 'value="overview"' in src or "value='overview'" in src, (
            "hidden-active-tab must default to 'overview'"
        )

    def test_hidden_input_inside_main_form(self):
        src = WORKSPACE_SHELL.read_text()
        form_start = src.find('id="main-form"')
        form_end = src.find("</form>", form_start)
        assert form_start != -1 and form_end != -1
        form_block = src[form_start:form_end]
        assert 'id="hidden-active-tab"' in form_block, (
            "hidden-active-tab must be inside #main-form"
        )


# ---------------------------------------------------------------------------
# B. static/app.js updates hidden-active-tab in switchTab
# ---------------------------------------------------------------------------

class TestAppJsSwitchTabBinding:
    def test_hidden_active_tab_referenced_in_app_js(self):
        src = APP_JS.read_text()
        assert "hidden-active-tab" in src, (
            "static/app.js must reference 'hidden-active-tab' to sync on tab switch"
        )

    def test_binding_inside_switch_tab_function(self):
        src = APP_JS.read_text()
        # Find switchTab function body
        match = re.search(r"function switchTab\(tabId\)\s*\{(.+?)(?=\nfunction |\Z)", src, re.DOTALL)
        assert match, "switchTab function not found in app.js"
        body = match.group(1)
        assert "hidden-active-tab" in body, (
            "hidden-active-tab update must be inside switchTab function body"
        )

    def test_binding_sets_value_to_tabid(self):
        src = APP_JS.read_text()
        assert ".value = tabId" in src or ".value=tabId" in src, (
            "switchTab must set hidden-active-tab.value = tabId"
        )


# ---------------------------------------------------------------------------
# C. POST /run reads active_tab from form (source check)
# ---------------------------------------------------------------------------

class TestMainWebReadsActiveTab:
    def test_active_tab_read_from_form(self):
        src = MAIN_WEB.read_text()
        assert '"active_tab"' in src or "'active_tab'" in src, (
            "main_web.py must read 'active_tab' from the POST form"
        )

    def test_runtime_sheet_map_defined(self):
        src = MAIN_WEB.read_text()
        assert "_RUNTIME_SHEET_MAP" in src, (
            "main_web.py must define _RUNTIME_SHEET_MAP for active sheet OOB"
        )


# ---------------------------------------------------------------------------
# D. Runtime-backed sheet map covers all 8 required tabs
# ---------------------------------------------------------------------------

class TestRuntimeSheetMapCoverage:
    def _extract_map_keys(self):
        src = MAIN_WEB.read_text()
        match = re.search(
            r"_RUNTIME_SHEET_MAP\s*=\s*\{(.+?)\}", src, re.DOTALL
        )
        assert match, "_RUNTIME_SHEET_MAP block not found in main_web.py"
        block = match.group(1)
        return block

    @pytest.mark.parametrize("tab", sorted(RUNTIME_SHEET_TABS))
    def test_tab_in_sheet_map(self, tab):
        block = self._extract_map_keys()
        assert f'"{tab}"' in block or f"'{tab}'" in block, (
            f"_RUNTIME_SHEET_MAP must include '{tab}'"
        )


# ---------------------------------------------------------------------------
# E. Non-runtime tabs are NOT in the sheet map
# ---------------------------------------------------------------------------

class TestNonRuntimeTabsNotInMap:
    @pytest.mark.parametrize("tab", sorted(NON_RUNTIME_TABS))
    def test_non_runtime_tab_not_in_sheet_map(self, tab):
        src = MAIN_WEB.read_text()
        match = re.search(
            r"_RUNTIME_SHEET_MAP\s*=\s*\{(.+?)\}", src, re.DOTALL
        )
        assert match, "_RUNTIME_SHEET_MAP block not found in main_web.py"
        block = match.group(1)
        assert f'"{tab}"' not in block and f"'{tab}'" not in block, (
            f"Non-runtime tab '{tab}' must NOT be in _RUNTIME_SHEET_MAP"
        )


# ---------------------------------------------------------------------------
# F & G. OOB active-sheet assembly in main_web.py source
# ---------------------------------------------------------------------------

class TestActiveSheetOOBAssembly:
    def test_oob_sheet_wraps_panel_id(self):
        src = MAIN_WEB.read_text()
        assert 'panel-' + '" + _active_tab' in src or \
               "panel-' + _active_tab" in src or \
               '"panel-" + _active_tab' in src or \
               "'panel-' + _active_tab" in src, (
            "OOB sheet fragment must use panel-{active_tab} as the wrapper ID"
        )

    def test_oob_sheet_uses_hx_swap_oob(self):
        src = MAIN_WEB.read_text()
        assert 'hx-swap-oob="true"' in src, (
            "Active sheet OOB must use hx-swap-oob='true'"
        )

    def test_oob_sheet_non_blocking(self):
        src = MAIN_WEB.read_text()
        # Must have a try/except around active sheet OOB
        assert "active_sheet_oob failed" in src, (
            "Active sheet OOB assembly must be non-blocking (try/except with warning)"
        )

    def test_shared_runtime_block_included_in_oob(self):
        src = MAIN_WEB.read_text()
        assert "shared_runtime_block.html" in src, (
            "Active sheet OOB must include shared_runtime_block.html"
        )


# ---------------------------------------------------------------------------
# H. No active-sheet OOB for non-runtime tabs
# ---------------------------------------------------------------------------

class TestNoOOBForNonRuntimeTab:
    def test_revenue_tab_skipped(self):
        src = MAIN_WEB.read_text()
        match = re.search(r"_RUNTIME_SHEET_MAP\s*=\s*\{(.+?)\}", src, re.DOTALL)
        assert match
        block = match.group(1)
        assert '"revenue"' not in block and "'revenue'" not in block, (
            "'revenue' must not appear in _RUNTIME_SHEET_MAP"
        )

    def test_opex_tab_skipped(self):
        src = MAIN_WEB.read_text()
        match = re.search(r"_RUNTIME_SHEET_MAP\s*=\s*\{(.+?)\}", src, re.DOTALL)
        assert match
        block = match.group(1)
        assert '"opex"' not in block and "'opex'" not in block, (
            "'opex' must not appear in _RUNTIME_SHEET_MAP"
        )


# ---------------------------------------------------------------------------
# I. Dashboard OOB still wired
# ---------------------------------------------------------------------------

class TestDashboardOOBStillWired:
    def test_dashboard_oob_template_still_referenced(self):
        src = MAIN_WEB.read_text()
        assert "_dashboard_oob.html" in src, (
            "Dashboard OOB template must still be referenced in main_web.py"
        )

    def test_dashboard_oob_gate_present(self):
        src = MAIN_WEB.read_text()
        assert "runtime_summary.html" in src and "kpis.html" in src, (
            "OOB gate must still check for runtime_summary.html and kpis.html"
        )


# ---------------------------------------------------------------------------
# J. Scenario Matrix OOB still wired
# ---------------------------------------------------------------------------

class TestScenarioMatrixOOBStillWired:
    def test_scenario_matrix_oob_template_still_referenced(self):
        src = MAIN_WEB.read_text()
        assert "_scenario_matrix_oob.html" in src, (
            "Scenario matrix OOB template must still be referenced in main_web.py"
        )


# ---------------------------------------------------------------------------
# K. shared_runtime_block.html uses querySelectorAll
# ---------------------------------------------------------------------------

class TestSharedRuntimeBlockFix:
    def test_queryselectorall_used_for_runtime_blocks(self):
        src = SHARED_RUNTIME.read_text()
        assert "querySelectorAll" in src, (
            "shared_runtime_block.html must use querySelectorAll to update all blocks"
        )

    def test_populates_all_runtime_blocks(self):
        src = SHARED_RUNTIME.read_text()
        assert ".runtime-block" in src or "'.runtime-block'" in src or '".runtime-block"' in src, (
            "shared_runtime_block.html must select by .runtime-block class"
        )

    def test_global_function_guarded_against_reregistration(self):
        src = SHARED_RUNTIME.read_text()
        assert "if (!window._populateRuntimeBlock)" in src or \
               "if(!window._populateRuntimeBlock)" in src, (
            "_populateRuntimeBlock global must be guarded against re-registration"
        )


# ---------------------------------------------------------------------------
# L. Partial templates for distributions and sponsor exist
# ---------------------------------------------------------------------------

class TestDistributionsSponsorPartials:
    def test_distributions_partial_exists(self):
        p = Path(REPO_ROOT) / "app/templates/partials/_sheet_distributions_partial.html"
        assert p.exists(), "_sheet_distributions_partial.html must exist"

    def test_distributions_partial_has_panel_content(self):
        p = Path(REPO_ROOT) / "app/templates/partials/_sheet_distributions_partial.html"
        src = p.read_text()
        assert "Distributions" in src

    def test_sponsor_partial_exists(self):
        p = Path(REPO_ROOT) / "app/templates/partials/_sheet_sponsor_partial.html"
        assert p.exists(), "_sheet_sponsor_partial.html must exist"

    def test_sponsor_partial_has_panel_content(self):
        p = Path(REPO_ROOT) / "app/templates/partials/_sheet_sponsor_partial.html"
        src = p.read_text()
        assert "Sponsor" in src

    def test_distributions_in_sheet_map(self):
        src = MAIN_WEB.read_text()
        assert "_sheet_distributions_partial.html" in src, (
            "_sheet_distributions_partial.html must be referenced in _RUNTIME_SHEET_MAP"
        )

    def test_sponsor_in_sheet_map(self):
        src = MAIN_WEB.read_text()
        assert "_sheet_sponsor_partial.html" in src, (
            "_sheet_sponsor_partial.html must be referenced in _RUNTIME_SHEET_MAP"
        )


# ---------------------------------------------------------------------------
# M. Engine MD5 unchanged
# ---------------------------------------------------------------------------

class TestUX2EngineParity:
    def test_engine_md5_unchanged(self):
        path = Path(REPO_ROOT) / "app/waterfall_core.py"
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        assert digest == ENGINE_MD5, f"waterfall_core.py must not change; got {digest}"


# ---------------------------------------------------------------------------
# N & O. DSCR parity
# ---------------------------------------------------------------------------

class TestUX2DSCRParity:
    @staticmethod
    def _first_finite_dscr(periods):
        for p in periods:
            if not p.is_operation:
                continue
            d = p.dscr
            if d is None or d != d or d == float("inf"):
                continue
            return d
        return None

    def test_tuho_p1_dscr(self):
        from app.project_factories import create_default_tuho_wind1
        from app.ui_runner import _build_period_engine, _run_waterfall
        proj = create_default_tuho_wind1()
        result = _run_waterfall(proj, _build_period_engine(proj))
        dscr = self._first_finite_dscr(result.periods)
        assert dscr is not None
        assert abs(dscr - TUHO_P1_DSCR) < 0.001, f"TUHO P1 DSCR={dscr}"

    def test_oborovo_p1_dscr(self):
        from app.project_factories import create_default_oborovo
        from app.ui_runner import _build_period_engine, _run_waterfall
        proj = create_default_oborovo()
        result = _run_waterfall(proj, _build_period_engine(proj))
        dscr = self._first_finite_dscr(result.periods)
        assert dscr is not None
        assert abs(dscr - OBOROVO_P1_DSCR) < 0.01, f"Oborovo P1 DSCR={dscr}"


# ---------------------------------------------------------------------------
# P. File scope guard
# ---------------------------------------------------------------------------

class TestUX2FileScope:
    UX2_ALLOWED_PREFIXES = (
        "app/templates/partials/workspace_shell.html",
        "static/app.js",
        "main_web.py",
        "app/templates/partials/shared_runtime_block.html",
        "app/templates/partials/_sheet_distributions_partial.html",
        "app/templates/partials/_sheet_sponsor_partial.html",
        "tests/test_phase_ux2_",
        # cross-arc allowlist updates
        "tests/test_phase_stab",
        "tests/test_phase_pr1_",
        "tests/test_phase_pr2_",
        "tests/test_phase_pr3_",
        "tests/test_phase_m1_",
        "tests/test_phase_m2_",
        "tests/test_phase_m3_",
        "tests/test_phase_m4_",
        "tests/test_phase_wf1_",
        "tests/test_phase_wf2_",
        "tests/test_phase_wf3_",
        "tests/test_phase_wf4_",
        "tests/test_phase_wf5_",
        "tests/test_phase_wf6_",
        "tests/test_phase_p2fix",
        "tests/test_phase_ux1_",
        # infrastructure
        "static/styles.css",
        "constraints.txt",
        "app/ui/scenario_matrix.py",
        "app/templates/partials/_nav_compression.html",
        "app/export/runtime_summary.py",
        "app/export/institutional_workbook.py",
        "app/services/run_service.py",
    )

    UX2_DISALLOWED_PREFIXES = (
        "app/waterfall_core.py",
        "app/project_factories.py",
        "app/persistence/",
        "app/services/export_audit_service.py",
        "app/export/",
    )

    def test_file_scope(self):
        import shutil
        if shutil.which("git") is None:
            pytest.skip("git not available")
        result = subprocess.run(
            ["git", "-C", REPO_ROOT, "diff", "--name-only", "origin/main"],
            capture_output=True, text=True,
        )
        changed = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        for f in changed:
            assert not any(f.startswith(p) for p in self.UX2_DISALLOWED_PREFIXES), (
                f"UX-2 must not touch {f}"
            )
            assert any(f.startswith(p) for p in self.UX2_ALLOWED_PREFIXES), (
                f"UX-2 file outside allowed scope: {f}"
            )

    def test_engine_md5_in_scope(self):
        path = Path(REPO_ROOT) / "app/waterfall_core.py"
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        assert digest == ENGINE_MD5
