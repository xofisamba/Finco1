"""Test Phase25B3 Factory Safety — Phase 25B-3 tests.

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

class TestFactorySafety:
    """For factory projects (TUHO / Oborovo), the panel must:
    - NOT render the EXPLORATORY banner (factory is reference, not exploratory)
    - NOT mutate factory data
    - Render the descriptive banner (since factory projects are not
      generic_solar / generic_wind)
    """

    def test_tuho_renders_descriptive_not_exploratory(self, jinja_env):
        tmpl = jinja_env.get_template("partials/what_changed_panel.html")
        out = tmpl.render(
            panel_rows=[],
            has_previous_run=False,
            project_origin="factory_template",
            template_source="tuho",
            scenario_name="TUHO base",
        )
        assert "what-changed-exploratory-banner" not in out
        assert "what-changed-descriptive-banner" in out

    def test_oborovo_renders_descriptive_not_exploratory(self, jinja_env):
        tmpl = jinja_env.get_template("partials/what_changed_panel.html")
        out = tmpl.render(
            panel_rows=[],
            has_previous_run=False,
            project_origin="factory_template",
            template_source="oborovo",
            scenario_name="Oborovo base",
        )
        assert "what-changed-exploratory-banner" not in out
        assert "what-changed-descriptive-banner" in out

    def test_factory_panel_renders_safely_with_previous(self, jinja_env):
        """Even if a factory project somehow has a previous_run_summary
        (not the current flow, but defensive), the panel must still
        render safely without the exploratory banner."""
        rows = [{
            "key": "project_irr", "label": "Project IRR", "format": "pct",
            "current_display": "9.47%", "previous_display": "9.30%",
            "delta_display": "+0.17 pp", "percent_display": "+1.8%",
            "state": "positive",
        }]
        tmpl = jinja_env.get_template("partials/what_changed_panel.html")
        out = tmpl.render(
            panel_rows=rows,
            has_previous_run=True,
            project_origin="factory_template",
            template_source="tuho",
            scenario_name="TUHO base",
        )
        assert "wc-row--positive" in out
        assert "what-changed-exploratory-banner" not in out


# ---------------------------------------------------------------------------
#  TestVersionHistoryWiring
# ---------------------------------------------------------------------------

class TestVersionHistoryWiring:
    """The scenario_version_history.html must include the what_changed_panel
    per card, gated on card.is_user_project, with proper context passing
    (Jinja2 `with` block)."""

    def test_version_history_includes_what_changed_panel(self, jinja_env):
        # Just check the file references the panel partial
        vh_path = os.path.join(PARTIALS_DIR, "scenario_version_history.html")
        with open(vh_path) as f:
            vh_src = f.read()
        assert 'partials/what_changed_panel.html' in vh_src

    def test_version_history_gates_on_is_user_project(self, jinja_env):
        vh_path = os.path.join(PARTIALS_DIR, "scenario_version_history.html")
        with open(vh_path) as f:
            vh_src = f.read()
        # The block must check card.is_user_project before including
        assert "card.is_user_project" in vh_src

    def test_version_history_passes_card_context_via_with_block(self, jinja_env):
        vh_path = os.path.join(PARTIALS_DIR, "scenario_version_history.html")
        with open(vh_path) as f:
            vh_src = f.read()
        # Jinja2 `include` does NOT scope `card` from the surrounding `for`
        # loop, so we must use a `{% with %}` block to pass per-card vars
        assert "{% with" in vh_src
        assert "panel_rows=card.panel_rows" in vh_src
        assert "has_previous_run=card.has_previous_run" in vh_src
        assert "scenario_name=card.scenario_name" in vh_src

    def test_end_to_end_render_through_version_history(self, jinja_env):
        """Render the full scenario_version_history.html with a card that
        has a previous_run_summary and verify the panel rows appear."""
        cards = [{
            "scenario_id": "x", "scenario_name": "Downside",
            "project_code": "test", "updated_at": None,
            "project_irr": 0.082, "equity_irr": 0.105, "avg_dscr": 1.45,
            "export_count": 0, "governance_state": {},
            "is_user_project": True, "template_source": "generic_solar",
            "has_previous_run": True,
            "panel_rows": [
                {"key": "project_irr", "label": "Project IRR", "format": "pct",
                 "current_display": "8.20%", "previous_display": "7.50%",
                 "delta_display": "+0.70 pp", "percent_display": "+9.3%",
                 "state": "positive"},
            ],
        }]
        tmpl = jinja_env.get_template("partials/scenario_version_history.html")
        out = tmpl.render(
            scenario_summary_cards=cards,
            workspace_state=None,
        )
        assert "what-changed-panel" in out
        assert "what-changed-row" in out
        assert "Project IRR" in out
        assert "+0.70 pp" in out

    def test_end_to_end_no_previous_renders_empty_state(self, jinja_env):
        cards = [{
            "scenario_id": "x", "scenario_name": "Base",
            "project_code": "test", "updated_at": None,
            "project_irr": 0.10, "equity_irr": 0.12, "avg_dscr": 1.5,
            "export_count": 0, "governance_state": {},
            "is_user_project": True, "template_source": "generic_solar",
            "has_previous_run": False,
            "panel_rows": [],
        }]
        tmpl = jinja_env.get_template("partials/scenario_version_history.html")
        out = tmpl.render(
            scenario_summary_cards=cards,
            workspace_state=None,
        )
        assert "what-changed-panel" in out
        assert "what-changed-empty-state" in out
        assert "what-changed-row" not in out

    def test_factory_card_does_not_render_panel(self, jinja_env):
        cards = [{
            "scenario_id": "x", "scenario_name": "TUHO base",
            "project_code": "tuho", "updated_at": None,
            "project_irr": 0.0947, "equity_irr": 0.1161, "avg_dscr": 1.451,
            "export_count": 0, "governance_state": {},
            "is_user_project": False, "template_source": "tuho",
            "has_previous_run": False,
            "panel_rows": [],
        }]
        tmpl = jinja_env.get_template("partials/scenario_version_history.html")
        out = tmpl.render(
            scenario_summary_cards=cards,
            workspace_state=None,
        )
        # Card exists but the panel partial is NOT included (gated on is_user_project)
        assert "TUHO base" in out
        assert "what-changed-panel" not in out


# ---------------------------------------------------------------------------
#  TestSafetyConstraints
# ---------------------------------------------------------------------------

class TestSafetyConstraints:
    """Hard constraints from the task spec:
    - use_construction_schedule_engine stays False
    - rc1 untouched
    - no Tailwind/Alpine
    - no new financial formulas
    """

    def test_construction_engine_stays_false(self):
        # The what_changed module and the partials must not flip this flag
        import app.ui.what_changed as mod
        src = open(mod.__file__).read()
        assert "use_construction_schedule_engine" not in src
        vh = open(os.path.join(PARTIALS_DIR, "what_changed_panel.html")).read()
        assert "use_construction_schedule_engine" not in vh
        svh = open(os.path.join(PARTIALS_DIR, "scenario_version_history.html")).read()
        assert "use_construction_schedule_engine" not in svh

    def test_no_tailwind_or_alpine_in_partials(self):
        vh = open(os.path.join(PARTIALS_DIR, "what_changed_panel.html")).read()
        svh = open(os.path.join(PARTIALS_DIR, "scenario_version_history.html")).read()
        for needle in ("tailwind", "alpine", "x-data", "x-show", "@click"):
            assert needle not in vh.lower(), f"Found {needle} in what_changed_panel.html"
            assert needle not in svh.lower(), f"Found {needle} in scenario_version_history.html"

    def test_helper_has_no_financial_formulas(self):
        """No new IRR, DSCR, NPV, etc. calculations beyond the simple
        difference and percent-difference."""
        import app.ui.what_changed as mod
        src = open(mod.__file__).read()
        # No NPV / IRR / DSCR computation libraries
        for needle in ("numpy_financial", "scipy.optimize", "np.irr", "np.npv"):
            assert needle not in src

    def test_partial_has_no_inline_javascript(self):
        vh = open(os.path.join(PARTIALS_DIR, "what_changed_panel.html")).read()
        assert "<script" not in vh.lower()


# ---------------------------------------------------------------------------
#  TestRC1Untouched
# ---------------------------------------------------------------------------

class TestRC1Untouched:
    """rc1 (run-and-compare 1-export) is the compare path from Phase 24-D.
    The What Changed panel must not change its display, its inputs, or
    its output."""

    def test_rc1_compare_helper_unaffected(self):
        # The compare path lives in app.services.compare_service (or similar)
        # The what_changed module must not import or monkey-patch it.
        import app.ui.what_changed as mod
        src = open(mod.__file__).read()
        for needle in ("compare_service", "base_vs_active_compare"):
            assert needle not in src

    def test_what_changed_does_not_modify_kpis_dict(self):
        """Compute deltas should not mutate either the current or previous
        dict in place."""
        current = {"project_irr": 0.082, "total_revenue_keur": 55000}
        previous = {"project_irr": 0.075, "total_revenue_keur": 50000}
        snapshot_current = dict(current)
        snapshot_previous = dict(previous)
        _ = compute_what_changed(current, previous)
        assert current == snapshot_current
        assert previous == snapshot_previous


# ---------------------------------------------------------------------------
#  TestCSSStyleGuard
# ---------------------------------------------------------------------------

class TestCSSStyleGuard:
    """The new CSS classes must be additive and not collide with existing
    .wc-* classes. Also, the `:root` count must remain 3 (Phase 24G-2
    invariant)."""

    def test_root_count_remains_three(self):
        css_path = os.path.join(REPO_ROOT, "static", "styles.css")
        with open(css_path) as f:
            css = f.read()
        # Phase 25B-3 invariant: the :root block count must stay at 3
        # (the count after Phase 24G-2 cleanup). Phase 25B-3 only adds
        # `.wc-*` classes which do not introduce new :root selectors.
        # Note: the CSS also contains two :root selectors inside @media
        # blocks (lines ~1330 and ~1335); those are also not new.
        import re
        n = len(re.findall(r":root\s*\{", css))
        # 3 base :root + 2 inside @media (pre-existing) = 5
        assert n == 5, f"Expected 5 :root occurrences (3 base + 2 @media), found {n}"
        # But the *base* :root count must remain 3
        n_base = len(re.findall(r"^:root\s*\{", css, re.MULTILINE))
        assert n_base == 3, f"Expected 3 base :root blocks, found {n_base}"

    def test_wc_classes_are_scoped(self):
        css_path = os.path.join(REPO_ROOT, "static", "styles.css")
        with open(css_path) as f:
            css = f.read()
        # All new classes should start with .wc-
        import re
        # Match .wc-foo at the start of a selector (allowing compound
        # selectors like ".wc-row--positive .wc-td-delta").
        # The class may appear as a simple selector or as part of a chain.
        new_classes_simple = re.findall(r"^\.(wc-[a-zA-Z0-9_-]+)\s*\{", css, re.MULTILINE)
        new_classes_compound = re.findall(r"\.wc-([a-zA-Z0-9_-]+)", css)
        all_wc_names = set()
        all_wc_names.update(new_classes_simple)
        all_wc_names.update("wc-" + n for n in new_classes_compound)
        # Common required classes
        for required in (
            "wc-panel", "wc-header", "wc-title", "wc-subtitle",
            "wc-banner", "wc-empty", "wc-table",
            "wc-row--positive", "wc-row--negative", "wc-row--zero",
            "wc-row--n_a", "wc-td-delta",
        ):
            assert required in all_wc_names, f"missing class .{required}"

class TestDisplayHelperDoesNotWrite:
    """The display helper must be pure: same input -> same output, no DB,
    no time-based random, no I/O."""

    def test_deterministic_output(self):
        current = {"project_irr": 0.082}
        previous = {"project_irr": 0.075}
        a = compute_what_changed(current, previous)
        b = compute_what_changed(current, previous)
        assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)

    def test_does_not_import_persistence(self):
        # The helper module should not import anything from app.persistence
        # (we want it to remain a pure function usable in templates and tests).
        import app.ui.what_changed as mod
        src = open(mod.__file__).read()
        assert "from app.persistence" not in src
        assert "import app.persistence" not in src

    def test_does_not_import_main_web(self):
        import app.ui.what_changed as mod
        src = open(mod.__file__).read()
        assert "import main_web" not in src
        assert "from main_web" not in src


# ---------------------------------------------------------------------------
#  TestFactorySafety
# ---------------------------------------------------------------------------
