"""Test Phase25B3 Exploratory Banner — Phase 25B-3 tests.

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

class TestExploratoryBanner:
    """The exploratory / descriptive banner must show correctly:
    - generic_solar / generic_wind  -> EXPLORATORY banner
    - everything else               -> descriptive banner
    """

    def test_exploratory_for_generic_solar(self, jinja_env):
        tmpl = jinja_env.get_template("partials/what_changed_panel.html")
        out = tmpl.render(
            panel_rows=[],
            has_previous_run=False,
            project_origin="user_created",
            template_source="generic_solar",
            scenario_name="Test",
        )
        assert "what-changed-exploratory-banner" in out
        assert "EXPLORATORY" in out
        assert "what-changed-descriptive-banner" not in out

    def test_exploratory_for_generic_wind(self, jinja_env):
        tmpl = jinja_env.get_template("partials/what_changed_panel.html")
        out = tmpl.render(
            panel_rows=[],
            has_previous_run=False,
            project_origin="user_created",
            template_source="generic_wind",
            scenario_name="Test",
        )
        assert "what-changed-exploratory-banner" in out

    def test_descriptive_for_test_template(self, jinja_env):
        tmpl = jinja_env.get_template("partials/what_changed_panel.html")
        out = tmpl.render(
            panel_rows=[],
            has_previous_run=False,
            project_origin="user_created",
            template_source="test",
            scenario_name="Test",
        )
        assert "what-changed-exploratory-banner" not in out
        assert "what-changed-descriptive-banner" in out


# ---------------------------------------------------------------------------
#  TestPanelEmptyState
# ---------------------------------------------------------------------------
