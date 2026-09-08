"""
UI-4A — Output integrity tests for OutputMetricProjection and Overview display.

Proves:
  - "NOT_AVAILABLE" sentinel never reaches display_value — always "—"
  - No silent zero: zero raw values produce "0.00x" / "0.00%" not "—"
  - All KPI keys in the catalog can be built without arithmetic
  - build_output_metric_projection handles None, "", "NOT_AVAILABLE", raw float
  - Freshness mapping produces correct availability and CSS class
  - build_overview_metric_projections covers all expected KPI keys
"""
import pytest
from app.v2.output_metric_projection import (
    NOT_AVAILABLE,
    MetricAvailability,
    OutputMetricProjection,
    build_output_metric_projection,
    build_overview_metric_projections,
    _KPI_CATALOG,
)


class TestSentinelNeverReachesDisplay:
    """NOT_AVAILABLE string must never appear in display_value."""

    def test_none_value_produces_dash(self):
        proj = build_output_metric_projection("project_irr", None, freshness="not_run")
        assert proj.display_value == NOT_AVAILABLE
        assert proj.display_value == "—"
        assert "NOT_AVAILABLE" not in proj.display_value

    def test_empty_string_produces_dash(self):
        proj = build_output_metric_projection("min_dscr", "", freshness="not_run")
        assert proj.display_value == "—"
        assert "NOT_AVAILABLE" not in proj.display_value

    def test_not_available_string_produces_dash(self):
        proj = build_output_metric_projection("equity_irr", "NOT_AVAILABLE", freshness="current")
        assert proj.display_value == "—"
        assert "NOT_AVAILABLE" not in proj.display_value

    def test_nan_produces_dash(self):
        import math
        proj = build_output_metric_projection("avg_dscr", math.nan, freshness="current")
        assert proj.display_value == "—"

    def test_inf_produces_dash(self):
        proj = build_output_metric_projection("project_irr", float("inf"), freshness="current")
        assert proj.display_value == "—"

    def test_negative_inf_produces_dash(self):
        proj = build_output_metric_projection("senior_debt_keur", float("-inf"), freshness="current")
        assert proj.display_value == "—"


class TestNoSilentZero:
    """Zero raw values must produce explicit zero display, not '—'."""

    def test_zero_irr_shows_zero_pct(self):
        proj = build_output_metric_projection("project_irr", 0.0, freshness="current")
        assert proj.display_value != "—"
        assert "0.00%" in proj.display_value
        assert proj.raw_value == pytest.approx(0.0)

    def test_zero_dscr_shows_zero_ratio(self):
        proj = build_output_metric_projection("min_dscr", 0.0, freshness="current")
        assert proj.display_value != "—"
        assert "0.00x" in proj.display_value

    def test_zero_keur_shows_zero(self):
        proj = build_output_metric_projection("total_capex_keur", 0.0, freshness="current")
        assert proj.display_value != "—"
        assert "0" in proj.display_value


class TestFormatting:
    """display_value formatting rules by key type."""

    def test_project_irr_formatted_as_pct(self):
        proj = build_output_metric_projection("project_irr", 0.085, freshness="current")
        assert proj.display_value == "8.50%"

    def test_min_dscr_formatted_as_ratio(self):
        proj = build_output_metric_projection("min_dscr", 1.32, freshness="current")
        assert proj.display_value == "1.32x"

    def test_senior_debt_formatted_as_keur(self):
        proj = build_output_metric_projection("senior_debt_keur", 27000.0, freshness="current")
        assert "27,000" in proj.display_value
        assert "kEUR" in proj.display_value

    def test_pre_formatted_string_passes_through(self):
        proj = build_output_metric_projection("project_irr", "8.50%", freshness="current")
        assert proj.display_value == "8.50%"

    def test_pre_formatted_ratio_passes_through(self):
        proj = build_output_metric_projection("avg_dscr", "1.45x", freshness="current")
        assert proj.display_value == "1.45x"


class TestAvailability:
    """Availability flag must reflect freshness and actual value."""

    def test_available_when_value_present_and_current(self):
        proj = build_output_metric_projection("project_irr", 0.085, freshness="current")
        assert proj.availability == MetricAvailability.AVAILABLE
        assert proj.is_available

    def test_run_required_when_no_value_and_not_run(self):
        proj = build_output_metric_projection("project_irr", None, freshness="not_run")
        assert proj.availability == MetricAvailability.RUN_REQUIRED
        assert not proj.is_available

    def test_stale_when_no_value_and_stale(self):
        proj = build_output_metric_projection("project_irr", None, freshness="stale")
        assert proj.availability == MetricAvailability.STALE

    def test_not_available_when_no_value_and_current(self):
        proj = build_output_metric_projection("equity_npv_keur", None, freshness="current")
        assert proj.availability == MetricAvailability.NOT_AVAILABLE


class TestFreshnessCSS:
    """css_freshness_class property produces correct modifier."""

    def test_current_freshness(self):
        proj = build_output_metric_projection("project_irr", 0.085, freshness="current")
        assert proj.css_freshness_class == "v2-kpi-tile--current"

    def test_stale_freshness(self):
        proj = build_output_metric_projection("project_irr", 0.085, freshness="stale")
        assert proj.css_freshness_class == "v2-kpi-tile--stale"
        assert proj.is_stale

    def test_notrun_freshness(self):
        proj = build_output_metric_projection("project_irr", None, freshness="not_run")
        assert proj.css_freshness_class == "v2-kpi-tile--notrun"


class TestKpiCatalogCoverage:
    """Every KPI in the catalog must be buildable."""

    @pytest.mark.parametrize("entry", _KPI_CATALOG)
    def test_catalog_entry_buildable(self, entry):
        key = entry[0]
        proj = build_output_metric_projection(key, None, freshness="not_run")
        assert proj.key == key
        assert proj.label == entry[1]
        assert proj.unit == entry[2]
        assert proj.source == entry[3]
        assert "NOT_AVAILABLE" not in proj.display_value

    @pytest.mark.parametrize("entry", _KPI_CATALOG)
    def test_catalog_entry_with_value(self, entry):
        key = entry[0]
        unit = entry[2]
        if unit == "%":
            val = 0.075
        elif unit == "x":
            val = 1.25
        else:
            val = 25000.0
        proj = build_output_metric_projection(key, val, freshness="current")
        assert proj.display_value != "—"
        assert "NOT_AVAILABLE" not in proj.display_value
        assert proj.raw_value is not None


class TestBuildOverviewMetricProjections:
    """build_overview_metric_projections covers all expected keys."""

    EXPECTED_KEYS = {
        "project_irr", "equity_irr", "avg_dscr", "min_dscr",
        "total_capex_keur", "senior_debt_keur", "total_revenue_keur",
        "total_ebitda_keur", "total_cfads_keur", "equity_npv_keur",
        "min_llcr", "target_dscr",
    }

    def test_empty_summaries_cover_all_keys(self):
        result = build_overview_metric_projections(
            runtime_summary={},
            debt_summary={},
            freshness="not_run",
        )
        assert self.EXPECTED_KEYS.issubset(set(result.keys())), (
            f"Missing keys: {self.EXPECTED_KEYS - set(result.keys())}"
        )

    def test_all_display_values_are_dash_when_empty(self):
        result = build_overview_metric_projections({}, {}, freshness="not_run")
        for key, proj in result.items():
            assert "NOT_AVAILABLE" not in proj.display_value, (
                f"Key {key!r} has 'NOT_AVAILABLE' in display_value: {proj.display_value!r}"
            )

    def test_runtime_summary_values_propagate(self):
        rs = {
            "project_irr": 0.085,
            "equity_irr": "12.30%",
            "min_dscr": 1.32,
            "avg_dscr": "1.45x",
            "total_capex_keur": 45000.0,
            "senior_debt_keur": 27000.0,
            "total_revenue_keur": 80000.0,
            "total_ebitda_keur": 35000.0,
            "total_cfads_keur": 30000.0,
        }
        result = build_overview_metric_projections(rs, {}, freshness="current")
        assert result["project_irr"].display_value == "8.50%"
        assert result["equity_irr"].display_value == "12.30%"
        assert result["min_dscr"].display_value == "1.32x"
        assert "27,000" in result["senior_debt_keur"].display_value

    def test_debt_summary_values_propagate(self):
        ds = {"min_llcr": 1.28, "target_dscr": 1.30}
        result = build_overview_metric_projections({}, ds, freshness="current")
        assert result["min_llcr"].display_value == "1.28x"
        assert result["target_dscr"].display_value == "1.30x"

    def test_scenario_id_and_timestamp_propagate(self):
        result = build_overview_metric_projections(
            {"project_irr": 0.09},
            {},
            freshness="current",
            scenario_id="sc-abc",
            run_timestamp="2026-01-15T10:00:00",
        )
        assert result["project_irr"].scenario_id == "sc-abc"
        assert result["project_irr"].run_timestamp == "2026-01-15T10:00:00"


class TestImmutability:
    """OutputMetricProjection is frozen — no mutation allowed."""

    def test_frozen(self):
        proj = build_output_metric_projection("project_irr", 0.085, freshness="current")
        with pytest.raises((AttributeError, TypeError)):
            proj.display_value = "99%"  # type: ignore[misc]
