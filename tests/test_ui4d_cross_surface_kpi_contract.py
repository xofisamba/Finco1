"""UI-4D — Cross-surface KPI contract proof (Section 5).

Proves that Overview, Compare, and Sensitivity all produce the same
OutputMetricProjection for project_irr raw=0.085:
  raw_value  = 0.085
  display_value = "8.50%"

No formatted-string parsing; no independently maintained dicts.
"""
from __future__ import annotations
import pytest


def test_output_metric_projection_project_irr():
    """Single projection for project_irr raw=0.085 → display 8.50%."""
    from app.v2.output_metric_projection import build_output_metric_projection
    m = build_output_metric_projection("project_irr", 0.085, freshness="current")
    assert m.raw_value == pytest.approx(0.085, abs=1e-9)
    assert m.display_value == "8.50%", (
        f"Expected '8.50%', got {m.display_value!r}"
    )


def test_overview_reads_output_metric_projection():
    """build_scenario_projection returns metrics[project_irr] with same contract."""
    from app.v2.scenario_kpi_projection import build_scenario_projection
    proj = build_scenario_projection(
        scenario_name="Base Case",
        runtime_summary={"project_irr": 0.085},
        ran_at="2025-01-01T00:00:00",
        is_stale=False,
    )
    assert proj.metrics is not None
    m = proj.metrics.get("project_irr")
    assert m is not None, "project_irr missing from ScenarioProjection.metrics"
    assert m.raw_value == pytest.approx(0.085, abs=1e-9)
    assert m.display_value == "8.50%"


def test_compare_reads_output_metric_projection():
    """build_compare_rows reads from p.metrics[key].display_value and raw_value."""
    from app.v2.scenario_kpi_projection import build_scenario_projection, build_compare_rows
    base = build_scenario_projection(
        scenario_name="Base",
        runtime_summary={"project_irr": 0.085},
        ran_at="2025-01-01T00:00:00",
        is_stale=False,
    )
    down = build_scenario_projection(
        scenario_name="Downside",
        runtime_summary={"project_irr": 0.070},
        ran_at="2025-01-01T00:00:00",
        is_stale=False,
    )
    rows = build_compare_rows([base, down])
    irr_row = next((r for r in rows if r.key == "project_irr"), None)
    assert irr_row is not None, "project_irr row missing from compare"
    assert irr_row.values[0] == "8.50%"
    assert irr_row.values[1] == "7.00%"
    # Delta proof: 0.085 vs 0.070 → raw delta -0.015 → display "-1.50%"
    # deltas[0] is "—" (base has no delta); deltas[1] is Downside vs Base.
    assert irr_row.deltas[1] == "-1.50%", (
        f"Delta must be -1.50% for 0.085 vs 0.070, got {irr_row.deltas[1]!r}"
    )


def test_sensitivity_projection_contract():
    """build_output_metric_projection used for sensitivity step matches single contract."""
    from app.v2.output_metric_projection import build_output_metric_projection
    m = build_output_metric_projection("project_irr", 0.070, freshness="current")
    assert m.raw_value == pytest.approx(0.070, abs=1e-9)
    assert m.display_value == "7.00%"


def test_all_three_surfaces_same_contract():
    """All three surfaces (Overview, Compare, Sensitivity) produce identical
    raw_value and display_value for project_irr=0.085."""
    from app.v2.output_metric_projection import build_output_metric_projection
    from app.v2.scenario_kpi_projection import build_scenario_projection, build_compare_rows

    # Overview
    proj = build_scenario_projection(
        scenario_name="Base",
        runtime_summary={"project_irr": 0.085},
        ran_at="2025-01-01T00:00:00",
        is_stale=False,
    )
    overview_m = proj.metrics["project_irr"]

    # Sensitivity step
    sens_m = build_output_metric_projection("project_irr", 0.085, freshness="current")

    # Compare
    rows = build_compare_rows([proj])
    compare_row = next(r for r in rows if r.key == "project_irr")

    assert overview_m.raw_value == pytest.approx(0.085)
    assert overview_m.display_value == "8.50%"
    assert sens_m.raw_value == pytest.approx(0.085)
    assert sens_m.display_value == "8.50%"
    assert compare_row.values[0] == "8.50%"
