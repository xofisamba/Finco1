"""Test Phase25B3 Panel Helpers — Phase 25B-3 tests.

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

class TestWhatChangedMetricOrdering:
    """The metric ordering is part of the contract: finance users scan
    the panel top-to-bottom and the order must match the priority they
    have in mind (project returns > DSCR > revenue/OPEX > financing)."""

    def test_metrics_count_is_ten(self):
        assert len(WHAT_CHANGED_METRICS) == 10

    def test_first_metric_is_project_irr(self):
        key = WHAT_CHANGED_METRICS[0][0]
        assert key == "project_irr"

    def test_second_metric_is_equity_irr(self):
        key = WHAT_CHANGED_METRICS[1][0]
        assert key == "equity_irr"

    def test_third_and_fourth_metrics_are_dscr(self):
        key3 = WHAT_CHANGED_METRICS[2][0]
        key4 = WHAT_CHANGED_METRICS[3][0]
        assert key3 == "avg_dscr"
        assert key4 == "min_dscr"

    def test_all_metrics_have_three_positional_fields(self):
        for m in WHAT_CHANGED_METRICS:
            assert len(m) == 3
            assert isinstance(m[0], str)  # key
            assert isinstance(m[1], str)  # label
            assert isinstance(m[2], str)  # format

    def test_pct_metrics_have_pct_format(self):
        pct_keys = {"project_irr", "equity_irr"}
        for m in WHAT_CHANGED_METRICS:
            key, _label, fmt = m
            if key in pct_keys:
                assert fmt == "pct"

    def test_x_metrics_have_x_format(self):
        x_keys = {"avg_dscr", "min_dscr"}
        for m in WHAT_CHANGED_METRICS:
            key, _label, fmt = m
            if key in x_keys:
                assert fmt == "x"


# ---------------------------------------------------------------------------
#  TestComputeMetricDelta
# ---------------------------------------------------------------------------

class TestComputeMetricDelta:
    """The core delta math. State classification:
    - positive: current > previous (and the metric is "higher-is-better")
    - negative: current < previous (and the metric is "higher-is-better")
    - zero:     no change
    - n_a:      either current or previous is missing
    """

    def test_increase_for_pct_metric_is_positive(self):
        row = compute_metric_delta(
            "project_irr", "Project IRR", "pct",
            current={"project_irr": 0.082},
            previous={"project_irr": 0.075},
        )
        assert row["state"] == "positive"
        assert row["current_display"] == "8.20%"
        assert row["previous_display"] == "7.50%"
        assert row["delta_display"] == "+0.70 pp"

    def test_decrease_for_pct_metric_is_negative(self):
        row = compute_metric_delta(
            "equity_irr", "Equity IRR", "pct",
            current={"equity_irr": 0.105},
            previous={"equity_irr": 0.115},
        )
        assert row["state"] == "negative"
        assert row["delta_display"].startswith("-")

    def test_zero_delta(self):
        row = compute_metric_delta(
            "total_capex_keur", "CAPEX", "keur",
            current={"total_capex_keur": 80000},
            previous={"total_capex_keur": 80000},
        )
        assert row["state"] == "zero"
        # The display must start with 0 (zero delta); suffix may include units
        assert row["delta_display"].lstrip("+").lstrip("-").startswith("0")

    def test_missing_current_is_n_a(self):
        row = compute_metric_delta(
            "total_revenue_keur", "Revenue", "keur",
            current={"other": 1},
            previous={"total_revenue_keur": 50000},
        )
        assert row["state"] == "n_a"

    def test_missing_previous_is_n_a(self):
        row = compute_metric_delta(
            "total_revenue_keur", "Revenue", "keur",
            current={"total_revenue_keur": 55000},
            previous={},
        )
        assert row["state"] == "n_a"

    def test_both_missing_is_n_a(self):
        row = compute_metric_delta(
            "total_revenue_keur", "Revenue", "keur",
            current={}, previous={},
        )
        assert row["state"] == "n_a"

    def test_keur_format_uses_thousands_separator(self):
        row = compute_metric_delta(
            "total_revenue_keur", "Revenue", "keur",
            current={"total_revenue_keur": 55000},
            previous={"total_revenue_keur": 50000},
        )
        # keur display uses comma-thousands separator
        assert "55,000" in row["current_display"]
        assert "50,000" in row["previous_display"]

    def test_dscr_format_uses_x_suffix(self):
        row = compute_metric_delta(
            "avg_dscr", "Avg DSCR", "x",
            current={"avg_dscr": 1.45},
            previous={"avg_dscr": 1.30},
        )
        assert "x" in row["current_display"]
        assert row["delta_display"].endswith("x")

    def test_percent_display_present_when_previous_nonzero(self):
        row = compute_metric_delta(
            "total_revenue_keur", "Revenue", "keur",
            current={"total_revenue_keur": 55000},
            previous={"total_revenue_keur": 50000},
        )
        # 10% increase
        assert row["percent_display"] is not None
        assert "+10.0%" in row["percent_display"]

    def test_percent_display_none_when_previous_zero(self):
        row = compute_metric_delta(
            "total_revenue_keur", "Revenue", "keur",
            current={"total_revenue_keur": 100},
            previous={"total_revenue_keur": 0},
        )
        # Avoid divide-by-zero / infinite percent
        assert row["percent_display"] is None


# ---------------------------------------------------------------------------
#  TestComputeWhatChanged
# ---------------------------------------------------------------------------

class TestComputeWhatChanged:
    """End-to-end compute across all metrics, given current + previous dicts.

    compute_what_changed signature: (previous, current)."""

    def _current(self):
        return {
            "project_irr": 0.082,
            "equity_irr": 0.105,
            "avg_dscr": 1.45,
            "min_dscr": 1.20,
            "total_revenue_keur": 55000,
            "total_opex_keur": 12500,
            "total_ebitda_keur": 42500,
            "total_capex_keur": 80000,
            "total_distributions_keur": 18000,
            "senior_debt_keur": 38000,
        }

    def _previous(self):
        return {
            "project_irr": 0.075,
            "equity_irr": 0.090,
            "avg_dscr": 1.30,
            "min_dscr": 1.10,
            "total_revenue_keur": 50000,
            "total_opex_keur": 12000,
            "total_ebitda_keur": 38000,
            "total_capex_keur": 80000,
            "total_distributions_keur": 15000,
            "senior_debt_keur": 40000,
        }

    def test_returns_one_row_per_metric(self):
        rows = compute_what_changed(self._previous(), self._current())
        assert len(rows) == 10

    def test_capex_delta_is_zero(self):
        rows = compute_what_changed(self._previous(), self._current())
        capex = [r for r in rows if r["key"] == "total_capex_keur"][0]
        assert capex["state"] == "zero"

    def test_revenue_delta_is_positive(self):
        rows = compute_what_changed(self._previous(), self._current())
        rev = [r for r in rows if r["key"] == "total_revenue_keur"][0]
        assert rev["state"] == "positive"

    def test_senior_debt_delta_is_negative(self):
        rows = compute_what_changed(self._previous(), self._current())
        d = [r for r in rows if r["key"] == "senior_debt_keur"][0]
        # senior_debt went from 40000 (previous) to 38000 (current) — deleveraging
        assert d["state"] == "negative"

    def test_no_previous_returns_all_n_a(self):
        rows = compute_what_changed({}, self._current())
        assert all(r["state"] == "n_a" for r in rows)

    def test_partial_previous_keeps_known_rows_comparable(self):
        prev = {"project_irr": 0.075}  # only project_irr
        rows = compute_what_changed(prev, self._current())
        known = [r for r in rows if r["key"] == "project_irr"][0]
        assert known["state"] == "positive"
        unknown = [r for r in rows if r["key"] == "equity_irr"][0]
        assert unknown["state"] == "n_a"


class TestHasAnyComparableDelta:
    def test_with_only_n_a_rows_returns_false(self):
        rows = [
            {"key": "x", "state": "n_a", "delta_display": "—", "current_display": "—",
             "previous_display": "—", "percent_display": None, "label": "X", "format": "pct"}
            for _ in range(10)
        ]
        assert has_any_comparable_delta(rows) is False

    def test_with_at_least_one_positive_returns_true(self):
        rows = [{"key": "x", "state": "positive", "delta_display": "+1",
                 "current_display": "1", "previous_display": "0",
                 "percent_display": None, "label": "X", "format": "pct"}]
        assert has_any_comparable_delta(rows) is True

    def test_with_only_zero_returns_true(self):
        # zero IS a comparable delta (the user can see "nothing changed here")
        rows = [{"key": "x", "state": "zero", "delta_display": "0",
                 "current_display": "1", "previous_display": "1",
                 "percent_display": None, "label": "X", "format": "pct"}]
        assert has_any_comparable_delta(rows) is True


# ---------------------------------------------------------------------------
#  TestBuildScenarioCardDeltas
# ---------------------------------------------------------------------------

class TestBuildScenarioCardDeltas:
    """Helper that augments a card dict with panel-ready data."""

    def test_factory_card_is_user_project_false(self):
        card = build_scenario_card_deltas({
            "scenario_name": "TUHO base",
            "is_user_project": False,
            "template_source": "tuho",
        })
        assert card["is_user_project"] is False
        assert card["has_previous_run"] is False  # no previous supplied

    def test_user_card_with_no_previous_has_empty_state(self):
        card = build_scenario_card_deltas({
            "scenario_name": "Generic base",
            "is_user_project": True,
            "template_source": "generic_solar",
        })
        assert card["is_user_project"] is True
        assert card["has_previous_run"] is False
        # panel_rows is always 10 (one per metric) but all n_a
        assert len(card["panel_rows"]) == 10
        assert all(r["state"] == "n_a" for r in card["panel_rows"])

    def test_user_card_with_previous_populates_panel_rows(self):
        card = build_scenario_card_deltas({
            "scenario_name": "Generic base",
            "is_user_project": True,
            "template_source": "generic_solar",
            "project_irr": 0.082,
            "equity_irr": 0.105,
            "avg_dscr": 1.45,
            "previous_run_summary": {
                "project_irr": 0.075,
                "equity_irr": 0.090,
                "avg_dscr": 1.30,
            },
        })
        assert card["has_previous_run"] is True
        assert len(card["panel_rows"]) == 10
        # At least the 3 known metrics should be comparable
        known = [r for r in card["panel_rows"] if r["state"] != "n_a"]
        assert len(known) == 3

    def test_card_preserves_template_source(self):
        card = build_scenario_card_deltas({
            "scenario_name": "Generic base",
            "is_user_project": True,
            "template_source": "generic_wind",
        })
        assert card["template_source"] == "generic_wind"


# ---------------------------------------------------------------------------
#  TestExploratoryBanner
# ---------------------------------------------------------------------------
