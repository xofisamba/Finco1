"""Product Gap PR10 -- Scenarios / Compare Reality Check tests.

Scope (see docs/PRODUCT_GAP_PR10_SCENARIOS_COMPARE_REALITY_CHECK.md):
- Scenarios tab/screen still renders.
- Compare tab/screen still renders.
- Live / Base / Active labels remain clear.
- Real saved scenario assumptions (snapshot/overrides/base_input_set
  via effectiveValue()) remain visible.
- No fabricated/static/mock scenario or compare output exists -- this
  investigation found the Scenarios/Compare screens already source
  every visible value from a real saved ScenarioRecord or a real
  run_project() result, so there is nothing to hide/replace (unlike
  PR6-PR9, which found and removed real placeholder content).
- Honest empty/unavailable-state copy is present where no scenario/
  compare selection has been made yet.
- No banned internal jargon appears in user-facing (non-audit_mode)
  Scenarios/Compare copy.
- G20/R99/R102 governance content remains audit_mode-gated wherever it
  appears (this PR did not need to remove it -- PR7/PR9 already
  established that audit_mode-gated governance content is acceptable
  since audit_mode is hardcoded False for normal users).
- No Save/Run/persistence/export behaviour is changed.
- No Preview Architecture or Runtime Pipeline files are touched.
- CAPEX/OPEX/Revenue/Financial Statements/Distribution/Sponsor/Senior
  Debt/Tax Product Gap behaviour is unaffected.
"""
from __future__ import annotations

import os
import re
import subprocess

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BANNED_JARGON = [
    "C1", "C2", "Preview Architecture", "Runtime Pipeline", "stub",
    "placeholder architecture", "R99", "R102", "G20",
]


def _read(*parts: str) -> str:
    with open(os.path.join(PROJECT_ROOT, *parts), "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def scenario_tab():
    return _read("app", "templates", "partials", "scenario_tab.html")


@pytest.fixture
def scenario_matrix():
    return _read("app", "templates", "partials", "scenario_matrix.html")


@pytest.fixture
def scenario_unified_entry():
    return _read("app", "templates", "partials", "_scenario_unified_entry.html")


@pytest.fixture
def scenario_compare():
    return _read("app", "templates", "partials", "scenario_compare.html")


@pytest.fixture
def scenario_compare_multi():
    return _read("app", "templates", "partials", "scenario_compare_multi.html")


@pytest.fixture
def scenario_multi_compare_picker():
    return _read("app", "templates", "partials", "scenario_multi_compare_picker.html")


@pytest.fixture
def scenario_version_history():
    return _read("app", "templates", "partials", "scenario_version_history.html")


@pytest.fixture
def workspace_shell():
    return _read("app", "templates", "partials", "workspace_shell.html")


@pytest.fixture
def main_web_source():
    return _read("main_web.py")


# ─── 1 & 2: Scenarios / Compare tabs still render ──────────────────────────

class TestTabsStillRender:
    def test_scenario_panel_present_in_shell(self, workspace_shell):
        assert 'id="panel-scenario"' in workspace_shell

    def test_compare_panel_present_in_shell(self, workspace_shell):
        assert 'id="panel-compare"' in workspace_shell

    def test_scenario_tab_included_in_shell(self, workspace_shell):
        assert "scenario_tab.html" in workspace_shell

    def test_scenario_compare_included_in_shell(self, workspace_shell):
        assert "scenario_compare.html" in workspace_shell

    def test_scenario_matrix_included_in_shell(self, workspace_shell):
        assert "scenario_matrix.html" in workspace_shell

    def test_scenario_routes_present(self, main_web_source):
        assert '"/scenarios/add"' in main_web_source or "/scenarios/add" in main_web_source
        assert "/scenarios/compare" in main_web_source
        assert "/scenarios/compare-panel" in main_web_source
        assert "/scenarios/compare-multi" in main_web_source


# ─── 3: Live vs Scenario / Base vs Active labels remain clear ─────────────

class TestLiveVsScenarioLabelsClear:
    def test_base_case_label_present(self, scenario_tab):
        assert "Base Case" in scenario_tab or "badge-info" in scenario_tab

    def test_active_badge_present(self, scenario_tab):
        assert "badge-pass" in scenario_tab and "Active" in scenario_tab

    def test_matrix_base_column_labelled_live(self, scenario_matrix):
        assert ">Base<" in scenario_matrix
        assert "Live" in scenario_matrix

    def test_matrix_legend_explains_columns(self, scenario_matrix):
        assert "scenario-matrix-legend" in scenario_matrix

    def test_compare_base_active_labels_present(self, scenario_compare):
        assert "badge-runtime" in scenario_compare
        assert "Base" in scenario_compare


# ─── 4: Real saved scenario assumptions remain visible ─────────────────────

class TestRealSavedScenarioAssumptionsVisible:
    def test_effective_value_macro_sources_real_fields(self, scenario_tab):
        # effectiveValue() reads overrides / snapshot / base_input_set --
        # all real fields on a persisted ScenarioRecord, never invented.
        assert "scenarioRecord.overrides" in scenario_tab
        assert "scenarioRecord.snapshot" in scenario_tab
        assert "scenarioRecord.base_input_set" in scenario_tab

    def test_matrix_reads_real_scenario_records(self, scenario_matrix):
        assert "col_downside" in scenario_matrix
        assert "col_upside" in scenario_matrix
        assert "last_run_summary" in scenario_matrix

    def test_real_persistence_paths_unchanged(self, main_web_source):
        assert "update_scenario_overrides" in main_web_source
        assert "save_scenario" in main_web_source
        assert "add_scenario" in main_web_source


# ─── 5 & 6: No placeholder/static/mock output shown as authoritative ──────

class TestNoFabricatedOutputFound:
    """This investigation found no static/hardcoded scenario or compare
    output anywhere in these templates (unlike PR6-PR9's findings for
    other sheets) -- every number traces back to a real ScenarioRecord
    field or a real run_project() result. These assertions document
    and lock in that absence."""

    def test_no_static_preview_notice_in_scenario_tab(self, scenario_tab):
        assert "preview-notice" not in scenario_tab

    def test_no_static_preview_notice_in_compare(self, scenario_compare):
        assert "preview-notice" not in scenario_compare

    def test_compare_metrics_sourced_from_compare_result(self, scenario_compare):
        # Every metric cell in scenario_compare.html reads from
        # compare_result.metrics / row.* -- never a hardcoded literal.
        assert "compare_result.metrics" in scenario_compare
        assert "row.base_value" in scenario_compare or "row.left_value" in scenario_compare

    def test_multi_compare_sourced_from_multi_compare_result(self, scenario_compare_multi):
        assert "multi_compare_result" in scenario_compare_multi
        assert "row['values']" in scenario_compare_multi

    def test_no_fabricated_delta_computation_in_template(self, scenario_compare):
        # Deltas must come pre-computed from the backend (row.delta),
        # never computed inline in the template via Jinja arithmetic.
        assert "row.delta" in scenario_compare
        # No "- {{" style inline subtraction patterns for delta cells.
        assert re.search(r"\{\{\s*row\.\w+\s*-\s*row\.\w+\s*\}\}", scenario_compare) is None


# ─── 7: Honest unavailable/empty-state copy where real output is absent ───

class TestHonestEmptyStatesPresent:
    def test_compare_empty_state_present(self, scenario_compare):
        assert 'data-testid="compare-empty-state"' in scenario_compare
        assert "Run at least one scenario to enable comparison." in scenario_compare

    def test_compare_partial_base_no_active_state(self, scenario_compare):
        assert "No Active Scenario" in scenario_compare
        assert "Select a saved scenario to compare against Base Case." in scenario_compare

    def test_multi_compare_empty_state_present(self, scenario_compare_multi):
        assert 'data-testid="multi-compare-empty-state"' in scenario_compare_multi
        assert "Select 2-4 saved scenarios to start a multi-compare." in scenario_compare_multi

    def test_multi_compare_picker_empty_states_present(self, scenario_multi_compare_picker):
        assert "No saved scenarios" in scenario_multi_compare_picker
        assert "Save at least 2 scenarios to enable multi-compare." in scenario_multi_compare_picker

    def test_matrix_inheritance_note_present_when_not_live(self, scenario_matrix):
        assert "scenario-matrix-inheritance-note" in scenario_matrix
        assert "No scenarios yet." in scenario_matrix


# ─── 8: No banned internal jargon in normal-user-facing copy ──────────────

class TestNoInternalJargonInNormalUserCopy:
    """Governance jargon (G20/R99/R102) is permitted only inside
    audit_mode-gated blocks, consistent with the PR7/PR9 precedent
    that audit_mode is hardcoded False for normal users. This class
    strips both Jinja comments and the audit_mode-gated blocks before
    checking for banned terms."""

    def _strip_comments_and_audit_blocks(self, src: str) -> str:
        visible = re.sub(r"\{#.*?#\}", "", src, flags=re.DOTALL)
        visible = re.sub(r"<!--.*?-->", "", visible, flags=re.DOTALL)
        # Remove the {% if audit_mode %} ... {% endif %} blocks (non-nested,
        # sufficient for these templates which do not nest audit_mode ifs).
        visible = re.sub(
            r"\{%-?\s*if\s+audit_mode[^%]*%\}.*?\{%-?\s*endif\s*-?%\}",
            "",
            visible,
            flags=re.DOTALL,
        )
        return visible

    @pytest.mark.parametrize(
        "fixture_name",
        [
            "scenario_tab",
            "scenario_matrix",
            "scenario_unified_entry",
            "scenario_compare",
            "scenario_compare_multi",
            "scenario_multi_compare_picker",
        ],
    )
    def test_no_banned_jargon_outside_audit_mode(self, fixture_name, request):
        src = request.getfixturevalue(fixture_name)
        visible = self._strip_comments_and_audit_blocks(src)
        for term in BANNED_JARGON:
            assert term not in visible, (
                f"banned jargon {term!r} found outside audit_mode gate in {fixture_name}"
            )

    def test_governance_content_is_audit_mode_gated_in_compare(self, scenario_compare):
        # scenario_compare.html itself does not contain the literal "G20"
        # string -- the governance label text lives server-side in
        # compare_scenarios() (app/persistence/exports_repository.py).
        # The template only renders compare_result.governance_rows /
        # governance_summary, and that rendering must be audit_mode-gated.
        visible = re.sub(r"\{#.*?#\}", "", scenario_compare, flags=re.DOTALL)
        idx = visible.find("governance_rows")
        assert idx >= 0, "expected governance_rows to exist (audit-only) in scenario_compare.html"
        preceding = visible[:idx]
        assert preceding.rfind("if audit_mode") > preceding.rfind("endif")

    def test_governance_content_is_audit_mode_gated_in_multi_compare(self, scenario_compare_multi):
        visible = re.sub(r"\{#.*?#\}", "", scenario_compare_multi, flags=re.DOTALL)
        idx = visible.find("governance_rows")
        assert idx >= 0
        preceding = visible[:idx]
        assert preceding.rfind("if audit_mode") > preceding.rfind("endif")

    def test_governance_content_is_audit_mode_gated_in_version_history(self, scenario_version_history):
        # version_history uses HTML comments (<!-- -->), not Jinja
        # comments, for its explanatory note -- skip those too.
        visible = re.sub(r"\{#.*?#\}", "", scenario_version_history, flags=re.DOTALL)
        visible = re.sub(r"<!--.*?-->", "", visible, flags=re.DOTALL)
        idx = visible.find("G20")
        assert idx >= 0
        preceding = visible[:idx]
        assert preceding.rfind("if audit_mode") > preceding.rfind("endif")

    def test_audit_mode_hardcoded_false_for_normal_users(self, main_web_source):
        assert '"audit_mode": False' in main_web_source


# ─── 9: No Save/Run/persistence/export behaviour changed ──────────────────

class TestNoBehaviourRegressed:
    def test_no_backend_or_persistence_file_changes(self):
        result = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=PROJECT_ROOT, capture_output=True, text=True,
        )
        if result.returncode != 0:
            pytest.skip("git diff against main not available in this sandbox")
        changed = result.stdout.splitlines()
        for forbidden in (
            "main_web.py",
            "app/persistence/repository.py",
            "app/persistence/exports_repository.py",
            "app/persistence/_helpers.py",
            "app/ui/scenario_matrix.py",
            "app/services/compare_service.py",
        ):
            assert forbidden not in changed, (
                f"{forbidden} should not need changes for a Scenarios/Compare UI-honesty pass"
            )


# ─── 10: No Preview Architecture / Runtime Pipeline files touched ─────────

class TestGuardrailFilesUntouched:
    RESTRICTED_PATHS = [
        "domain/",
        "app/waterfall_core.py",
        "app/input_adapter.py",
        "app/project_factories.py",
        "static/modelling/runtime-renderer.js",
        "app/services/model_preview.py",
        "app/services/preview_context.py",
        "app/services/previews/",
    ]

    def test_restricted_paths_not_in_diff_against_main(self):
        result = subprocess.run(
            ["git", "diff", "main", "--name-only"],
            cwd=PROJECT_ROOT, capture_output=True, text=True,
        )
        if result.returncode != 0:
            pytest.skip("git diff against main not available in this sandbox")
        changed_files = result.stdout.splitlines()
        # V2-4 authorized: domain/ shims and finco_core/ engine modules
        _v24 = ("domain/waterfall/", "domain/tax/", "domain/financing/",
                "domain/depreciation/", "domain/shl/", "domain/sponsor/",
                "domain/returns/", "domain/distribution_account/",
                "finco_core/", "docs/V2_", "tests/test_v2_")
        changed_files = [c for c in changed_files
                         if not c.startswith(_v24)
                         and c not in {"domain/shl_fcf_waterfall.py",
                                       "domain/period_engine.py",
                                       "domain/validation.py"}]
        for changed in changed_files:
            for restricted in self.RESTRICTED_PATHS:
                assert not changed.startswith(restricted), (
                    f"Restricted path touched: {changed!r} matches {restricted!r}"
                )


# ─── 11: Other Product Gap areas unaffected ────────────────────────────────

class TestOtherProductGapAreasUnaffected:
    def test_financials_unavailable_panel_still_present(self):
        src = _read("app", "templates", "partials", "sheet_financials.html")
        assert "fs-unavailable-panel" in src

    def test_distributions_unavailable_panel_still_present(self):
        src = _read("app", "templates", "partials", "_sheet_distributions_partial.html")
        assert "dist-unavailable-panel" in src

    def test_sponsor_unavailable_panel_still_present(self):
        src = _read("app", "templates", "partials", "_sheet_sponsor_partial.html")
        assert "sponsor-unavailable-panel" in src

    def test_senior_debt_unavailable_panel_still_present(self):
        src = _read("app", "templates", "partials", "sheet_senior_debt.html")
        assert "sd-unavailable-panel" in src

    def test_tax_unavailable_panel_still_present(self):
        src = _read("app", "templates", "partials", "sheet_tax.html")
        assert "tax-unavailable-panel" in src


# ─── 12: Developer comment correction (stale "placeholders" claim) ────────

class TestDeveloperCommentCorrected:
    def test_stale_placeholder_comment_removed(self, workspace_shell):
        assert "The other  #}" not in workspace_shell
        assert "three columns are placeholders. NO scenario persistence" not in workspace_shell

    def test_corrected_comment_present(self, workspace_shell):
        assert "Product Gap PR10: comment corrected" in workspace_shell

    def test_comment_is_jinja_comment_no_render_effect(self, workspace_shell):
        # The corrected text must remain inside a {# ... #} Jinja comment
        # block, never inside rendered markup.
        idx = workspace_shell.find("Product Gap PR10: comment corrected")
        assert idx >= 0
        comment_start = workspace_shell.rfind("{#", 0, idx)
        comment_end = workspace_shell.find("#}", idx)
        assert comment_start != -1 and comment_end != -1
