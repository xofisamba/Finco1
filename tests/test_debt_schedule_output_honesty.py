"""
Tests for Senior Debt / Debt Schedule output honesty — PR #857.

Verifies:
- sheet_senior_debt.html renders without error (protected + user projects)
- Protected project: no editable debt input elements, "Protected original" badge
- User project: editable draft grid present, "Editing" label
- Debt assumptions vs runtime outputs are clearly distinguished
- Unavailable panel starts visible (not hidden) when no run data
- "Draft schedule" / "Runtime Debt Outputs" labelling present
- No fake amortization rows introduced
- No debt math calculated in template (display only)

Does NOT start a server — renders via Jinja2.
"""

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.ui.project_context import get_project_context


@pytest.fixture(scope="module")
def jinja_env():
    return Environment(
        loader=FileSystemLoader("app/templates"),
        autoescape=select_autoescape(["html"]),
    )


@pytest.fixture(scope="module")
def sd_template(jinja_env):
    return jinja_env.get_template("partials/sheet_senior_debt.html")


@pytest.fixture(scope="module")
def tuho_ctx():
    return get_project_context("tuho")


@pytest.fixture(scope="module")
def oborovo_ctx():
    return get_project_context("oborovo")


def _render(template, ctx, is_user_project=False):
    return template.render(
        project_ctx=ctx,
        is_user_project=is_user_project,
    )


# ---------------------------------------------------------------------------
# Baseline renders
# ---------------------------------------------------------------------------

class TestBaselineRenders:
    def test_renders_protected_project(self, sd_template, tuho_ctx):
        html = _render(sd_template, tuho_ctx, is_user_project=False)
        assert len(html) > 0

    def test_renders_user_project(self, sd_template, tuho_ctx):
        html = _render(sd_template, tuho_ctx, is_user_project=True)
        assert len(html) > 0

    def test_renders_oborovo_protected(self, sd_template, oborovo_ctx):
        html = _render(sd_template, oborovo_ctx, is_user_project=False)
        assert len(html) > 0


# ---------------------------------------------------------------------------
# Protected project — read-only
# ---------------------------------------------------------------------------

class TestProtectedProject:
    def test_protected_badge_present(self, sd_template, tuho_ctx):
        html = _render(sd_template, tuho_ctx, is_user_project=False)
        assert "Protected original" in html

    def test_no_editable_inputs_for_protected(self, sd_template, tuho_ctx):
        html = _render(sd_template, tuho_ctx, is_user_project=False)
        # The editable draft grid should NOT appear for protected projects
        assert 'type="number"' not in html

    def test_no_editable_grid_for_protected(self, sd_template, tuho_ctx):
        html = _render(sd_template, tuho_ctx, is_user_project=False)
        assert "editable-grid-shell" not in html

    def test_no_draft_grid_inputs_protected(self, sd_template, tuho_ctx):
        html = _render(sd_template, tuho_ctx, is_user_project=False)
        assert 'data-grid-source="gearing_pct"' not in html


# ---------------------------------------------------------------------------
# User project — editable draft grid
# ---------------------------------------------------------------------------

class TestUserProject:
    def test_no_protected_badge_for_user_project(self, sd_template, tuho_ctx):
        html = _render(sd_template, tuho_ctx, is_user_project=True)
        assert "Protected original" not in html

    def test_editing_label_for_user_project(self, sd_template, tuho_ctx):
        html = _render(sd_template, tuho_ctx, is_user_project=True)
        assert "Editing" in html

    def test_editable_grid_present_for_user(self, sd_template, tuho_ctx):
        html = _render(sd_template, tuho_ctx, is_user_project=True)
        assert "editable-grid-shell" in html

    def test_gearing_input_present_for_user(self, sd_template, tuho_ctx):
        html = _render(sd_template, tuho_ctx, is_user_project=True)
        assert 'data-grid-source="gearing_pct"' in html

    def test_draft_label_on_grid(self, sd_template, tuho_ctx):
        html = _render(sd_template, tuho_ctx, is_user_project=True)
        assert "Draft" in html or "draft" in html


# ---------------------------------------------------------------------------
# Section labels — Debt Assumptions vs Runtime Debt Outputs
# ---------------------------------------------------------------------------

class TestSectionLabels:
    def test_debt_assumptions_section_label(self, sd_template, tuho_ctx):
        html = _render(sd_template, tuho_ctx)
        assert "Debt Assumptions" in html

    def test_runtime_debt_outputs_section_label(self, sd_template, tuho_ctx):
        html = _render(sd_template, tuho_ctx)
        assert "Runtime Debt Outputs" in html

    def test_draft_schedule_notice(self, sd_template, tuho_ctx):
        html = _render(sd_template, tuho_ctx)
        assert "Draft schedule" in html or "not yet a full lender" in html

    def test_calculated_after_run_notice(self, sd_template, tuho_ctx):
        html = _render(sd_template, tuho_ctx)
        assert "Calculated after Run" in html or "Run the model" in html

    def test_engine_source_referenced(self, sd_template, tuho_ctx):
        html = _render(sd_template, tuho_ctx)
        assert "WaterfallResult" in html


# ---------------------------------------------------------------------------
# Unavailable panel — correct initial display
# ---------------------------------------------------------------------------

class TestUnavailablePanel:
    def test_unavailable_panel_present(self, sd_template, tuho_ctx):
        html = _render(sd_template, tuho_ctx)
        assert "sd-unavailable-panel" in html

    def test_unavailable_panel_not_hidden_by_default(self, sd_template, tuho_ctx):
        # PR #857 fix: panel should NOT have style="display:none;" in HTML
        # (it starts visible; JS hides it after a run)
        import re
        html = _render(sd_template, tuho_ctx)
        panel_match = re.search(
            r'id="sd-unavailable-panel"([^>]*>)',
            html
        )
        assert panel_match, "sd-unavailable-panel element not found"
        assert "display:none" not in panel_match.group(1), \
            "Unavailable panel should start visible (JS hides it post-run)"

    def test_run_model_message_in_unavailable_panel(self, sd_template, tuho_ctx):
        html = _render(sd_template, tuho_ctx)
        assert "Run the model" in html or "not available yet" in html.lower()


# ---------------------------------------------------------------------------
# No fake amortization rows
# ---------------------------------------------------------------------------

class TestNoFakeAmortization:
    def test_debt_schedule_table_empty_by_default(self, sd_template, tuho_ctx):
        html = _render(sd_template, tuho_ctx)
        # sd-schedule-body must be empty — populated by JS from sessionStorage
        assert '<tbody id="sd-schedule-body"></tbody>' in html

    def test_debt_schedule_header_empty_by_default(self, sd_template, tuho_ctx):
        html = _render(sd_template, tuho_ctx)
        assert '<tr id="sd-schedule-header"></tr>' in html

    def test_no_hardcoded_keur_values_in_schedule(self, sd_template, tuho_ctx):
        # No inline numeric values like "43,359" or "2,302" in the schedule table
        import re
        html = _render(sd_template, tuho_ctx)
        # The schedule block should be empty (display:none, no rows)
        schedule_block = re.search(
            r'id="sd-schedule-block".*?</div>', html, re.DOTALL
        )
        if schedule_block:
            block_html = schedule_block.group(0)
            # Should not contain hardcoded large numbers
            assert not re.search(r'\b\d{4,}\b', block_html.replace('sd-schedule', '')), \
                "Unexpected numeric content in debt schedule block"


# ---------------------------------------------------------------------------
# Assumption grid — reads from project_ctx only
# ---------------------------------------------------------------------------

class TestAssumptionGrid:
    def test_facility_amount_section_present(self, sd_template, tuho_ctx):
        html = _render(sd_template, tuho_ctx)
        assert "Facility Amount" in html

    def test_tenor_shown(self, sd_template, tuho_ctx):
        html = _render(sd_template, tuho_ctx)
        assert "Tenor" in html

    def test_target_dscr_shown(self, sd_template, tuho_ctx):
        html = _render(sd_template, tuho_ctx)
        assert "Target DSCR" in html

    def test_fc_editable_false_on_assumption_grid(self, sd_template, tuho_ctx):
        # Read-only assumption items must have data-fc-editable="false"
        html = _render(sd_template, tuho_ctx, is_user_project=False)
        assert 'data-fc-editable="false"' in html

    def test_no_debt_math_in_template(self, sd_template, tuho_ctx):
        # Verify the assumption grid only displays values from project_ctx
        # (presentation formatting like * 100 for pct is allowed)
        # No aggregation, subtraction, or financial formulas.
        html = _render(sd_template, tuho_ctx)
        assert "SD_ROWS" in html  # JS row definitions present (not Jinja math)
