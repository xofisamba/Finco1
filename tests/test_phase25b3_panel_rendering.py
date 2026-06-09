"""Test Phase25B3 Panel Rendering — Phase 25B-3 tests.

Split from the original test_phase25b3_what_changed_delta_indicator.py to
keep the test file count manageable and the responsibilities clear.

These tests cover the "What changed since previous run?" delta panel added
in Phase 25B-3 to the Generic Solar / Generic Wind exploratory path.
"""
"""Phase 25B-3 — "What Changed" Delta Indicator tests.

Goal: After editing a Generic Solar / Generic Wind scenario and re-running, the
user sees a small panel "What changed since previous run?" with the most
important KPI deltas.

These tests prove:
- Panel renders for a generic project with both previous + current run data.
- "No previous run" state renders cleanly when there is no prior summary.
- Deltas calculate correctly (absolute, percentage, state classification).
- Missing metrics render as n/a (do not crash, do not invent numbers).
- EXPLORATORY banner / descriptive banner show correctly for generic vs
  factory projects.
- Factory projects (TUHO/Oborovo) are SAFE — the panel does not corrupt
  their data, does not change their IRR / DSCR display, and does not appear
  in factory-controlled sections of the UI.
- The display helper does NOT write to the DB.
- use_construction_schedule_engine stays False (no construction promotion).
- rc1 (run-and-compare 1-export) flow is untouched.

These tests are pure unit + integration: they exercise the helper module and
the template via Jinja2 directly (no HTTP / no live session).
"""
import json
import os
import sys

import pytest
from jinja2 import Environment, FileSystemLoader


# ---------------------------------------------------------------------------
#  Fixtures
# ---------------------------------------------------------------------------

# Repo root (parent of tests/)
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
TEMPLATES_DIR = os.path.join(REPO_ROOT, "app", "templates")
PARTIALS_DIR = os.path.join(TEMPLATES_DIR, "partials")


# Ensure repo root is importable so we can import app.ui.what_changed
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


from app.ui.what_changed import (
    WHAT_CHANGED_METRICS,
    compute_metric_delta,
    compute_what_changed,
    has_any_comparable_delta,
    build_scenario_card_deltas,
)


# ---------------------------------------------------------------------------
#  Helper: Jinja2 environment bound to the partials folder.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def jinja_env():
    return Environment(loader=FileSystemLoader(TEMPLATES_DIR))


# ---------------------------------------------------------------------------
#  TestWhatChangedMetricOrdering
# ---------------------------------------------------------------------------

class TestPanelEmptyState:
    """When no previous run is recorded, the panel must show a clear
    "No previous run available" message — not crash, not invent numbers."""

    def test_no_previous_state_attribute(self, jinja_env):
        tmpl = jinja_env.get_template("partials/what_changed_panel.html")
        out = tmpl.render(
            panel_rows=[],
            has_previous_run=False,
            project_origin="user_created",
            template_source="generic_solar",
            scenario_name="Downside",
        )
        assert 'data-state="no-previous"' in out

    def test_no_previous_shows_empty_state(self, jinja_env):
        tmpl = jinja_env.get_template("partials/what_changed_panel.html")
        out = tmpl.render(
            panel_rows=[],
            has_previous_run=False,
            project_origin="user_created",
            template_source="generic_solar",
            scenario_name="Downside",
        )
        assert "what-changed-empty-state" in out
        assert "No previous run" in out

    def test_no_previous_does_not_render_table(self, jinja_env):
        tmpl = jinja_env.get_template("partials/what_changed_panel.html")
        out = tmpl.render(
            panel_rows=[],
            has_previous_run=False,
            project_origin="user_created",
            template_source="generic_solar",
            scenario_name="Downside",
        )
        assert "what-changed-row" not in out


# ---------------------------------------------------------------------------
#  TestPanelWithPreviousRun
# ---------------------------------------------------------------------------

class TestPanelWithPreviousRun:
    """When both current + previous are present, the table must render
    one row per metric, with absolute + percent deltas and state classes."""

    @pytest.fixture
    def rendered_with_previous(self, jinja_env):
        rows = [
            {
                "key": "project_irr", "label": "Project IRR", "format": "pct",
                "current_display": "8.20%", "previous_display": "7.50%",
                "delta_display": "+0.70 pp", "percent_display": "+9.3%",
                "state": "positive",
            },
            {
                "key": "equity_irr", "label": "Equity IRR", "format": "pct",
                "current_display": "10.50%", "previous_display": "9.00%",
                "delta_display": "+1.50 pp", "percent_display": "+16.7%",
                "state": "positive",
            },
            {
                "key": "avg_dscr", "label": "Avg DSCR", "format": "x",
                "current_display": "1.45x", "previous_display": "1.30x",
                "delta_display": "+0.15x", "percent_display": "+11.5%",
                "state": "positive",
            },
            {
                "key": "min_dscr", "label": "Min DSCR", "format": "x",
                "current_display": "1.20x", "previous_display": "1.10x",
                "delta_display": "+0.10x", "percent_display": "+9.1%",
                "state": "positive",
            },
        ]
        tmpl = jinja_env.get_template("partials/what_changed_panel.html")
        return tmpl.render(
            panel_rows=rows,
            has_previous_run=True,
            project_origin="user_created",
            template_source="generic_solar",
            scenario_name="Downside",
        )

    def test_state_attribute_is_with_previous(self, rendered_with_previous):
        assert 'data-state="with-previous"' in rendered_with_previous

    def test_renders_one_row_per_metric(self, rendered_with_previous):
        assert rendered_with_previous.count('data-testid="what-changed-row"') == 4

    def test_renders_all_metric_labels(self, rendered_with_previous):
        for label in ("Project IRR", "Equity IRR", "Avg DSCR", "Min DSCR"):
            assert label in rendered_with_previous

    def test_renders_absolute_deltas(self, rendered_with_previous):
        assert "+0.70 pp" in rendered_with_previous
        assert "+1.50 pp" in rendered_with_previous
        assert "+0.15x" in rendered_with_previous

    def test_renders_percent_deltas(self, rendered_with_previous):
        assert "+9.3%" in rendered_with_previous
        assert "+16.7%" in rendered_with_previous

    def test_positive_rows_get_positive_class(self, rendered_with_previous):
        # Each positive row gets a wc-row--positive class on the <tr>
        assert "wc-row--positive" in rendered_with_previous

    def test_no_empty_state(self, rendered_with_previous):
        assert "what-changed-empty-state" not in rendered_with_previous


# ---------------------------------------------------------------------------
#  TestPanelNegativeAndZeroStates
# ---------------------------------------------------------------------------

class TestPanelNegativeAndZeroStates:
    """Negative deltas get the wc-row--negative class.
    Zero deltas get the wc-row--zero class."""

    def test_negative_row_class(self, jinja_env):
        rows = [{
            "key": "equity_irr", "label": "Equity IRR", "format": "pct",
            "current_display": "8.00%", "previous_display": "10.00%",
            "delta_display": "-2.00 pp", "percent_display": "-20.0%",
            "state": "negative",
        }]
        tmpl = jinja_env.get_template("partials/what_changed_panel.html")
        out = tmpl.render(
            panel_rows=rows,
            has_previous_run=True,
            project_origin="user_created",
            template_source="generic_solar",
            scenario_name="Downside",
        )
        assert "wc-row--negative" in out

    def test_zero_row_class(self, jinja_env):
        rows = [{
            "key": "total_capex_keur", "label": "CAPEX", "format": "keur",
            "current_display": "80,000", "previous_display": "80,000",
            "delta_display": "0", "percent_display": "0.0%",
            "state": "zero",
        }]
        tmpl = jinja_env.get_template("partials/what_changed_panel.html")
        out = tmpl.render(
            panel_rows=rows,
            has_previous_run=True,
            project_origin="user_created",
            template_source="generic_solar",
            scenario_name="Downside",
        )
        assert "wc-row--zero" in out

    def test_n_a_row_class(self, jinja_env):
        rows = [{
            "key": "shl_opening_keur", "label": "SHL Opening", "format": "keur",
            "current_display": "—", "previous_display": "—",
            "delta_display": "—", "percent_display": None,
            "state": "n_a",
        }]
        tmpl = jinja_env.get_template("partials/what_changed_panel.html")
        out = tmpl.render(
            panel_rows=rows,
            has_previous_run=True,
            project_origin="user_created",
            template_source="generic_solar",
            scenario_name="Downside",
        )
        assert "wc-row--n_a" in out


# ---------------------------------------------------------------------------
#  TestDisplayHelperDoesNotWrite
# ---------------------------------------------------------------------------
