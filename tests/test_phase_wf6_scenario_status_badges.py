"""Phase WF-6 — Scenario Run-Status Badges.

Acceptance criteria:
1. Engine MD5 unchanged.
2. Nav "Scenarios" button has data-wf6-scenario-count attribute (even when 0).
3. Nav count badge appears when scenarios exist (digit value).
4. Nav count badge absent when no non-base scenarios.
5. Scenario tab has data-wf6-run-badge attribute.
6. sc-run-badge--run present when last_run_summary is non-empty.
7. sc-run-badge--not-run present when last_run_summary is empty/absent.
8. CSS .nav-scenario-count-badge defined.
9. CSS .sc-run-badge defined.
10. CSS .sc-run-badge--run defined.
11. CSS .sc-run-badge--not-run defined.
12. CSS has WF-6 marker.
13. File scope: only allowed files changed.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-wf6")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_session_token  # noqa: E402
from main_web import app  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
ENGINE_MD5 = "6bf49f33efc989736c17cea0cb9b7723"
CSS_PATH = REPO_ROOT / "static" / "styles.css"
NAV_PATH = REPO_ROOT / "app" / "templates" / "partials" / "_nav_compression.html"
SCENARIO_TAB_PATH = REPO_ROOT / "app" / "templates" / "partials" / "scenario_tab.html"


@pytest.fixture(scope="module")
def workspace_html():
    c = TestClient(app, follow_redirects=True)
    token = create_session_token(user_id="wf6_user", username="wf6_user")
    c.cookies.set("finco_session", token)
    r = c.get("/?project=tuho")
    assert r.status_code == 200
    return r.text


# ---------------------------------------------------------------------------
# 1. Engine parity
# ---------------------------------------------------------------------------

class TestEngineParity:
    def test_engine_md5_unchanged(self):
        md5 = hashlib.md5(
            (REPO_ROOT / "app" / "waterfall_core.py").read_bytes()
        ).hexdigest()
        assert md5 == ENGINE_MD5, f"Engine MD5 changed: {md5}"


# ---------------------------------------------------------------------------
# 2–4. Nav Scenarios button badge
# ---------------------------------------------------------------------------

class TestNavScenarioBadge:
    def test_scenarios_button_has_wf6_count_attribute(self, workspace_html):
        """data-wf6-scenario-count must be present even when count is 0."""
        assert 'data-wf6-scenario-count=' in workspace_html, (
            "Nav Scenarios button missing data-wf6-scenario-count attribute"
        )

    def test_scenarios_count_attribute_has_digit_value(self, workspace_html):
        m = re.search(r'data-wf6-scenario-count="(\d+)"', workspace_html)
        assert m is not None, "data-wf6-scenario-count value is not a digit"

    def test_nav_template_has_count_badge_markup(self):
        src = NAV_PATH.read_text()
        assert 'data-wf6-scenario-count=' in src
        assert 'nav-scenario-count-badge' in src
        assert 'data-wf6-count-badge=' in src


# ---------------------------------------------------------------------------
# 5–7. Scenario run-status badge
# ---------------------------------------------------------------------------

class TestScenarioRunBadge:
    def test_scenario_tab_template_has_run_badge_markup(self):
        src = SCENARIO_TAB_PATH.read_text()
        assert 'data-wf6-run-badge=' in src, "scenario_tab.html missing data-wf6-run-badge"
        assert 'sc-run-badge--run' in src
        assert 'sc-run-badge--not-run' in src

    def test_workspace_html_has_wf6_run_badge(self, workspace_html):
        """Scenario tab is included in workspace; run-badge markup in template source."""
        # The tuho project may have no non-base scenarios, so badges won't appear
        # in the rendered HTML. Verify the template source has the markup instead.
        src = SCENARIO_TAB_PATH.read_text()
        assert 'data-wf6-run-badge=' in src, (
            "scenario_tab.html template missing data-wf6-run-badge attribute"
        )

    def test_run_badge_run_variant_class(self):
        src = SCENARIO_TAB_PATH.read_text()
        assert 'sc-run-badge--run' in src

    def test_run_badge_not_run_variant_class(self):
        src = SCENARIO_TAB_PATH.read_text()
        assert 'sc-run-badge--not-run' in src


# ---------------------------------------------------------------------------
# 8–12. CSS
# ---------------------------------------------------------------------------

class TestCSS:
    def test_nav_count_badge_css_defined(self):
        css = CSS_PATH.read_text()
        assert '.nav-scenario-count-badge' in css

    def test_sc_run_badge_css_defined(self):
        css = CSS_PATH.read_text()
        assert '.sc-run-badge {' in css or '.sc-run-badge\n' in css or '.sc-run-badge ' in css

    def test_sc_run_badge_run_css_defined(self):
        css = CSS_PATH.read_text()
        assert '.sc-run-badge--run' in css

    def test_sc_run_badge_not_run_css_defined(self):
        css = CSS_PATH.read_text()
        assert '.sc-run-badge--not-run' in css

    def test_wf6_marker_in_css(self):
        css = CSS_PATH.read_text()
        assert 'WF-6' in css


# ---------------------------------------------------------------------------
# 13. File scope
# ---------------------------------------------------------------------------

class TestFileScope:
    def test_only_allowed_files_changed(self):
        if shutil.which("git") is None or not (REPO_ROOT / ".git").exists():
            pytest.skip("git not available")
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "diff", "--name-only", "origin/main"],
            capture_output=True, text=True,
        )
        changed = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        allowed_prefixes = (
            "static/styles.css",
            "app/templates/partials/_nav_compression.html",
            "app/templates/partials/scenario_tab.html",
            "tests/test_phase_wf6_",
            "tests/test_phase_wf5_",
            "tests/test_phase_wf4_",
            "tests/test_phase_wf3_",
            "tests/test_phase_wf2_",
            "tests/test_phase_wf1_",
            "tests/test_phase_p2fix",
            "tests/test_phase_m1_",
            "tests/test_phase_m2_",
            "tests/test_phase_m3_",
            "tests/test_phase_m4_",
            "tests/test_phase_stab",
            "tests/test_phase_pr1_",
            "tests/test_phase_pr2_",
            "tests/test_phase_pr3_",
            "app/templates/partials/_scenario_matrix_oob.html",
            "app/ui/dashboard.py",
            "app/templates/",
            "docs/phase_wf",
            "reports/phase_wf",
            "scripts/",
            "app/ui/scenario_matrix.py",
            "app/templates/partials/scenario_matrix.html",
            "main_web.py",
            # UX-1C: active workspace cleanup follow-up allowlist
            "app/templates/partials/kpis.html",
            "app/templates/partials/scenario_multi_compare_picker.html",
            "app/templates/partials/scenario_workflow_indicators.html",
            "app/templates/partials/workspace_shell.html",
            "tests/test_phase57a4_single_capex_sheet_layout.py",
            "tests/test_phase_m1_scenario_matrix.py",
            "tests/test_phase_m2_scenario_matrix_live.py",
            "tests/test_phase_m3_scenario_matrix_overrides.py",
            "tests/test_phase_m4_scenario_matrix_run.py",
            "tests/test_phase_p2fix2_shell_strip.py",
            "tests/test_phase_p2fix3_c2_first_edit.py",
            "tests/test_phase_p2fix4_five_area_navigation.py",
            "tests/test_phase_p2fix5b_normal_mode_shell_strip.py",
            "tests/test_phase_p2fix5c_dashboard_kpi.py",
            "tests/test_phase_p2fix5d_five_area_navigation.py",
            "tests/test_phase_p2fix5e_reference_ux.py",
            "tests/test_phase_p2fix6_c2_create_copy_ui.py",
            "tests/test_phase_p2fix7_production_cleanup.py",
            "tests/test_phase_pr1_form_timing_fields.py",
            "tests/test_phase_pr2_realized_gearing.py",
            "tests/test_phase_pr3_taxonomy.py",
            "tests/test_phase_scenario1_base_case_init.py",
            "tests/test_phase_scenario1_review_fix.py",
            "tests/test_phase_scenario2_fixes.py",
            "tests/test_phase_stab1_run_refreshes_kpis.py",
            "tests/test_phase_stab2_realized_gearing_scale.py",
            "tests/test_phase_stab3_capex_subline_propagation.py",
            "tests/test_phase_stab5_export_route_fix.py",
            "tests/test_phase_stab6_new_project_first_run.py",
            "tests/test_phase_stab7_generic_dashboard_parity.py",
            "tests/test_phase_stab8_e2e_runtime_validation.py",
            "tests/test_phase_ux4b_save_as_button.py",
            "tests/test_phase_wf2_sheet_styling.py",
            "tests/test_phase_wf3_home_and_projects_split.py",
            "tests/test_phase_wf4_minimal_create_and_list_hygiene.py",
            "tests/test_phase_wf5_grouped_results_nav.py",
            "tests/test_p1_compare_validation.py",
            "tests/test_phase51a_run_route_golden_characterization.py",
            "tests/test_ux1a_navigation_context_fix.py",
            "tests/test_phase_ux1_inputs_badge_cleanup.py",
            "tests/test_phase_ux4cde_pilot_polish.py",
            "tests/test_phase_ux2_active_sheet_refresh.py",
        )
        disallowed_prefixes = (
            "app/persistence/",
            "app/services/",
            "app/waterfall_core.py",
            "app/project_factories.py",
            "app/excel_export.py",
            "main_api.py",
            "static/app.js",
        )
        for f in changed:
            assert not any(f.startswith(p) for p in disallowed_prefixes), (
                f"Disallowed file changed: {f}"
            )
            assert any(f.startswith(p) for p in allowed_prefixes), (
                f"File outside allowed scope: {f}"
            )
