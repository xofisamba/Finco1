"""
Tests for Scenarios Excel Matrix cleanup — PR #856.

Verifies structural and visual treatment of scenario_tab.html and
_scenario_unified_entry.html after the Excel-style cleanup:
  - Section banners (Scenario Assumptions / Scenario Outputs)
  - Column sub-labels (Live project values / Downside / Upside / Custom)
  - Protected project read-only rendering
  - Override badge present on overridden cells
  - KPI summary table structural correctness
  - Fallback empty states

Does NOT start a server — renders templates directly via Jinja2.
"""

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.ui.project_context import get_project_context
from app.ui.scenario_matrix import build_matrix_context, INPUT_ROWS, KPI_ROWS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def jinja_env():
    return Environment(
        loader=FileSystemLoader("app/templates"),
        autoescape=select_autoescape(["html"]),
    )


@pytest.fixture(scope="module")
def scenario_tab_template(jinja_env):
    return jinja_env.get_template("partials/scenario_tab.html")


@pytest.fixture(scope="module")
def unified_entry_template(jinja_env):
    return jinja_env.get_template("partials/_scenario_unified_entry.html")


@pytest.fixture(scope="module")
def tuho_ctx():
    return get_project_context("tuho")


# Minimal stubs for scenario context variables
class _FakeWorkspaceState:
    active_scenario_id = "base-id"


class _FakeProjectRecord:
    project_code = "TUHO"


class _FakeScenarioRecord:
    scenario_id = "base-id"
    scenario_name = "Base Case"
    is_base_case = True
    overrides = {}
    snapshot = {}
    base_input_set = {
        "tariff_eur_mwh": "60",
        "p50_hours": "4164",
    }
    last_run_summary = None
    updated_at = None


class _FakeNonBaseScenario:
    scenario_id = "downside-id"
    scenario_name = "Downside"
    is_base_case = False
    overrides = {"ppa_tariff_eur_mwh": "55"}
    snapshot = {"tariff_eur_mwh": "55"}
    base_input_set = {}
    last_run_summary = None
    updated_at = None


SCENARIO_EDITABLE_FIELDS = [
    ("Revenue / PPA", [
        ("tariff_eur_mwh", "PPA Tariff"),
        ("p50_hours", "P50 Operating Hours"),
    ]),
    ("CAPEX", [
        ("total_capex_keur", "Total CAPEX"),
    ]),
]


def _render_tab(template, is_user_project=False, non_base=None):
    return template.render(
        project_record=_FakeProjectRecord(),
        base_case_record=_FakeScenarioRecord(),
        non_base_scenarios=non_base or [],
        scenario_editable_fields=SCENARIO_EDITABLE_FIELDS,
        workspace_state=_FakeWorkspaceState(),
        is_user_project=is_user_project,
    )


def _render_unified(template, matrix_rows=None):
    rows = matrix_rows or []
    return template.render(matrix_rows=rows)


# ---------------------------------------------------------------------------
# scenario_tab.html — Section banner
# ---------------------------------------------------------------------------

class TestSectionBanner:
    def test_assumptions_banner_present(self):
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        env = Environment(loader=FileSystemLoader("app/templates"),
                          autoescape=select_autoescape(["html"]))
        t = env.get_template("partials/scenario_tab.html")
        html = _render_tab(t, is_user_project=False)
        assert "Scenario Assumptions" in html

    def test_banner_has_protected_notice_for_readonly(self, scenario_tab_template):
        html = _render_tab(scenario_tab_template, is_user_project=False)
        assert "Protected original" in html

    def test_banner_no_protected_notice_for_user_project(self, scenario_tab_template):
        html = _render_tab(scenario_tab_template, is_user_project=True)
        assert "Protected original" not in html

    def test_user_banner_mentions_double_click(self, scenario_tab_template):
        html = _render_tab(scenario_tab_template, is_user_project=True)
        assert "Double-click" in html or "double-click" in html or "double click" in html.lower()


# ---------------------------------------------------------------------------
# scenario_tab.html — Column headers
# ---------------------------------------------------------------------------

class TestColumnHeaders:
    def test_base_column_has_live_project_sublabel(self, scenario_tab_template):
        html = _render_tab(scenario_tab_template, is_user_project=False)
        assert "Live project values" in html

    def test_assumption_column_label_present(self, scenario_tab_template):
        html = _render_tab(scenario_tab_template, is_user_project=False)
        assert "Assumption" in html

    def test_base_badge_present(self, scenario_tab_template):
        html = _render_tab(scenario_tab_template, is_user_project=False)
        assert "Base" in html

    def test_nonbase_col_downside_sublabel(self, scenario_tab_template):
        html = _render_tab(scenario_tab_template, non_base=[_FakeNonBaseScenario()])
        assert "Downside" in html

    def test_nonbase_col_upside_sublabel(self, scenario_tab_template):
        class _Upside(_FakeNonBaseScenario):
            scenario_id = "upside-id"
            scenario_name = "Upside"

        class _Down(_FakeNonBaseScenario):
            pass

        html = _render_tab(scenario_tab_template, non_base=[_Down(), _Upside()])
        assert "Upside" in html

    def test_not_run_badge_present_for_unrun_scenario(self, scenario_tab_template):
        html = _render_tab(scenario_tab_template, non_base=[_FakeNonBaseScenario()])
        assert "Not run" in html


# ---------------------------------------------------------------------------
# scenario_tab.html — Override badge
# ---------------------------------------------------------------------------

class TestOverrideBadge:
    def test_override_badge_present_for_overridden_cell(self, scenario_tab_template):
        # _FakeNonBaseScenario has ppa_tariff_eur_mwh override
        html = _render_tab(scenario_tab_template, non_base=[_FakeNonBaseScenario()])
        assert "sc-override-badge" in html

    def test_no_override_badge_on_base_column(self, scenario_tab_template):
        html = _render_tab(scenario_tab_template, is_user_project=False)
        # No non-base scenarios → no override badges
        assert "sc-override-badge" not in html


# ---------------------------------------------------------------------------
# scenario_tab.html — Editability
# ---------------------------------------------------------------------------

class TestEditability:
    def test_user_project_cells_have_ondblclick(self, scenario_tab_template):
        html = _render_tab(scenario_tab_template, is_user_project=True,
                           non_base=[_FakeNonBaseScenario()])
        assert "ondblclick" in html

    def test_protected_project_no_ondblclick(self, scenario_tab_template):
        html = _render_tab(scenario_tab_template, is_user_project=False,
                           non_base=[_FakeNonBaseScenario()])
        assert "ondblclick" not in html

    def test_add_scenario_form_present_for_user(self, scenario_tab_template):
        html = _render_tab(scenario_tab_template, is_user_project=True)
        assert "sc-add-form" in html

    def test_no_add_scenario_form_for_protected(self, scenario_tab_template):
        html = _render_tab(scenario_tab_template, is_user_project=False)
        assert "sc-add-form" not in html


# ---------------------------------------------------------------------------
# scenario_tab.html — Section groups
# ---------------------------------------------------------------------------

class TestSectionGroups:
    def test_revenue_ppa_section_label(self, scenario_tab_template):
        html = _render_tab(scenario_tab_template)
        assert "Revenue" in html

    def test_capex_section_label(self, scenario_tab_template):
        html = _render_tab(scenario_tab_template)
        assert "CAPEX" in html

    def test_field_label_ppa_tariff(self, scenario_tab_template):
        html = _render_tab(scenario_tab_template)
        assert "PPA Tariff" in html


# ---------------------------------------------------------------------------
# _scenario_unified_entry.html — Outputs section
# ---------------------------------------------------------------------------

class TestUnifiedEntryOutputs:
    def test_scenario_outputs_banner_present(self, unified_entry_template):
        html = _render_unified(unified_entry_template)
        assert "Scenario Outputs" in html

    def test_empty_state_shown_when_no_matrix(self, unified_entry_template):
        html = unified_entry_template.render(matrix_rows=None)
        assert "Run the model" in html

    def _html_with_row(self, template):
        rows = [_FakeMatrixRow("Project IRR", "project_irr")]
        return _render_unified(template, matrix_rows=rows)

    def test_base_case_column_header_present(self, unified_entry_template):
        assert "Base Case" in self._html_with_row(unified_entry_template)

    def test_base_case_sublabel_live_project(self, unified_entry_template):
        assert "Live project values" in self._html_with_row(unified_entry_template)

    def test_downside_column_header_present(self, unified_entry_template):
        assert "Downside" in self._html_with_row(unified_entry_template)

    def test_upside_column_header_present(self, unified_entry_template):
        assert "Upside" in self._html_with_row(unified_entry_template)

    def test_custom_column_header_present(self, unified_entry_template):
        assert "Custom" in self._html_with_row(unified_entry_template)

    def test_compare_link_present(self, unified_entry_template):
        html = _render_unified(unified_entry_template)
        assert "comparison" in html.lower() or "compare" in html.lower()


# ---------------------------------------------------------------------------
# _scenario_unified_entry.html — KPI rows
# ---------------------------------------------------------------------------

class _FakeMatrixRow:
    def __init__(self, label, attr, is_kpi=True, unit=""):
        self.row = type("R", (), {"label": label, "attr": attr, "unit": unit})()
        self.is_kpi = is_kpi
        self.base = "10.5%"
        self.downside = "8.2%"
        self.upside = ""
        self.custom = ""


class TestKPIRows:
    def test_kpi_row_renders(self, unified_entry_template):
        rows = [_FakeMatrixRow("Project IRR", "project_irr")]
        html = _render_unified(unified_entry_template, matrix_rows=rows)
        assert "Project IRR" in html

    def test_empty_kpi_cell_shows_dash(self, unified_entry_template):
        rows = [_FakeMatrixRow("Equity IRR", "equity_irr")]
        html = _render_unified(unified_entry_template, matrix_rows=rows)
        assert "—" in html

    def test_non_kpi_rows_excluded(self, unified_entry_template):
        rows = [
            _FakeMatrixRow("PPA Tariff", "tariff_eur_mwh", is_kpi=False),
            _FakeMatrixRow("Project IRR", "project_irr", is_kpi=True),
        ]
        html = _render_unified(unified_entry_template, matrix_rows=rows)
        assert "Project IRR" in html
        assert "PPA Tariff" not in html
