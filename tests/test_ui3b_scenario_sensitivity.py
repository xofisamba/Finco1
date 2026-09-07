"""
tests.test_ui3b_scenario_sensitivity — UI-3B surface contracts.

Covers:
  - ScenarioProjection / build_scenario_projection formatting
  - build_compare_rows delta arithmetic (raw float path, not string re-parse)
  - Output integrity: kpis_raw populated correctly
  - Sensitivity DRIVER_SPECS completeness
  - OverviewProjection active_scenario_name field
"""
from __future__ import annotations

import pytest

from app.v2.scenario_kpi_projection import (
    KPI_CATALOG,
    ScenarioKpiRow,
    ScenarioProjection,
    build_compare_rows,
    build_scenario_projection,
)


# ── helpers ──────────────────────────────────────────────────────────────── #

def _make_rs(**kw):
    """Minimal runtime_summary dict with sane defaults."""
    defaults = {
        "project_irr": 0.085,
        "equity_irr": 0.120,
        "min_dscr": 1.32,
        "avg_dscr": 1.45,
        "min_llcr": 1.28,
        "senior_debt_keur": 27_000.0,
        "total_capex_keur": 45_000.0,
        "total_revenue_keur": 120_000.0,
        "total_ebitda_keur": 80_000.0,
        "total_cfads_keur": 60_000.0,
    }
    defaults.update(kw)
    return defaults


# ── build_scenario_projection ─────────────────────────────────────────────── #

class TestBuildScenarioProjection:

    def test_clean_state(self):
        rs = _make_rs()
        sp = build_scenario_projection("Base Case", rs, "2025-01-01T10:00:00", is_stale=False)
        assert sp.state == "CLEAN"
        assert sp.scenario_name == "Base Case"

    def test_stale_state(self):
        rs = _make_rs()
        sp = build_scenario_projection("Base Case", rs, "2025-01-01T10:00:00", is_stale=True)
        assert sp.state == "STALE"

    def test_not_run_state(self):
        sp = build_scenario_projection("Downside", None, None, is_stale=False)
        assert sp.state == "NOT_RUN"
        assert sp.ran_at == ""

    def test_pct_formatting(self):
        rs = _make_rs(project_irr=0.085)
        sp = build_scenario_projection("B", rs, None, is_stale=False)
        assert sp.kpis["project_irr"] == "8.50%"

    def test_ratio_formatting(self):
        rs = _make_rs(avg_dscr=1.45)
        sp = build_scenario_projection("B", rs, None, is_stale=False)
        assert sp.kpis["avg_dscr"] == "1.45x"

    def test_keur_formatting(self):
        rs = _make_rs(total_capex_keur=45_000.0)
        sp = build_scenario_projection("B", rs, None, is_stale=False)
        assert "45,000" in sp.kpis["total_capex_keur"]
        assert "kEUR" in sp.kpis["total_capex_keur"]

    def test_kpis_raw_populated(self):
        rs = _make_rs(project_irr=0.085)
        sp = build_scenario_projection("B", rs, None, is_stale=False)
        assert sp.kpis_raw["project_irr"] == pytest.approx(0.085)

    def test_kpis_raw_none_on_missing(self):
        sp = build_scenario_projection("B", {}, None, is_stale=False)
        for key in [item["key"] for item in KPI_CATALOG]:
            assert sp.kpis_raw[key] is None

    def test_kpis_raw_none_on_nan(self):
        import math
        rs = _make_rs(project_irr=float("nan"))
        sp = build_scenario_projection("B", rs, None, is_stale=False)
        assert sp.kpis_raw["project_irr"] is None
        assert sp.kpis["project_irr"] == "—"

    def test_ran_at_truncation(self):
        rs = _make_rs()
        sp = build_scenario_projection("B", rs, "2025-06-15T14:30:00Z", is_stale=False)
        assert sp.ran_at == "2025-06-15 14:30"
        assert "2025-06-15" in sp.ran_at


# ── build_compare_rows ────────────────────────────────────────────────────── #

class TestBuildCompareRows:

    def _two_projections(self, base_irr=0.085, alt_irr=0.094):
        rs_base = _make_rs(project_irr=base_irr)
        rs_alt = _make_rs(project_irr=alt_irr)
        p_base = build_scenario_projection("Base Case", rs_base, None, is_stale=False)
        p_alt = build_scenario_projection("Upside", rs_alt, None, is_stale=False)
        return p_base, p_alt

    def test_returns_all_kpi_keys(self):
        p1, p2 = self._two_projections()
        rows = build_compare_rows([p1, p2])
        keys = {r.key for r in rows}
        assert keys == {item["key"] for item in KPI_CATALOG}

    def test_base_delta_is_dash(self):
        p1, p2 = self._two_projections()
        rows = build_compare_rows([p1, p2])
        irr_row = next(r for r in rows if r.key == "project_irr")
        assert irr_row.deltas[0] == "—"

    def test_pct_delta_positive(self):
        p1, p2 = self._two_projections(base_irr=0.085, alt_irr=0.094)
        rows = build_compare_rows([p1, p2])
        irr_row = next(r for r in rows if r.key == "project_irr")
        # delta = (0.094 - 0.085) * 100 = +0.90%
        assert irr_row.deltas[1] == "+0.90%"

    def test_pct_delta_negative(self):
        p1, p2 = self._two_projections(base_irr=0.094, alt_irr=0.085)
        rows = build_compare_rows([p1, p2])
        irr_row = next(r for r in rows if r.key == "project_irr")
        assert irr_row.deltas[1] == "-0.90%"

    def test_ratio_delta_format(self):
        rs_base = _make_rs(avg_dscr=1.45)
        rs_alt = _make_rs(avg_dscr=1.50)
        p1 = build_scenario_projection("Base", rs_base, None, is_stale=False)
        p2 = build_scenario_projection("Alt", rs_alt, None, is_stale=False)
        rows = build_compare_rows([p1, p2])
        row = next(r for r in rows if r.key == "avg_dscr")
        assert row.deltas[1] == "+0.05x"

    def test_keur_delta_format(self):
        rs_base = _make_rs(total_capex_keur=45_000.0)
        rs_alt = _make_rs(total_capex_keur=50_000.0)
        p1 = build_scenario_projection("Base", rs_base, None, is_stale=False)
        p2 = build_scenario_projection("Alt", rs_alt, None, is_stale=False)
        rows = build_compare_rows([p1, p2])
        row = next(r for r in rows if r.key == "total_capex_keur")
        assert "+5,000" in row.deltas[1]
        assert "kEUR" in row.deltas[1]

    def test_delta_na_when_not_run(self):
        p1 = build_scenario_projection("Base", _make_rs(), None, is_stale=False)
        p2 = build_scenario_projection("NotRun", None, None, is_stale=False)
        rows = build_compare_rows([p1, p2])
        irr_row = next(r for r in rows if r.key == "project_irr")
        assert irr_row.deltas[1] == "—"

    def test_three_scenarios(self):
        rs = _make_rs()
        p1 = build_scenario_projection("A", rs, None, is_stale=False)
        p2 = build_scenario_projection("B", _make_rs(project_irr=0.10), None, is_stale=False)
        p3 = build_scenario_projection("C", _make_rs(project_irr=0.07), None, is_stale=False)
        rows = build_compare_rows([p1, p2, p3])
        irr_row = next(r for r in rows if r.key == "project_irr")
        assert len(irr_row.deltas) == 3
        assert irr_row.deltas[0] == "—"

    def test_values_list_length(self):
        p1, p2 = self._two_projections()
        rows = build_compare_rows([p1, p2])
        for row in rows:
            assert len(row.values) == 2
            assert len(row.deltas) == 2
            assert len(row.raw_values) == 2


# ── KPI_CATALOG completeness ──────────────────────────────────────────────── #

class TestKpiCatalog:

    def test_all_fmt_values_valid(self):
        valid_fmts = {"pct", "ratio", "keur"}
        for item in KPI_CATALOG:
            assert item["fmt"] in valid_fmts, f"{item['key']} has unknown fmt {item['fmt']!r}"

    def test_no_duplicate_keys(self):
        keys = [item["key"] for item in KPI_CATALOG]
        assert len(keys) == len(set(keys))

    def test_required_kpis_present(self):
        keys = {item["key"] for item in KPI_CATALOG}
        required = {"project_irr", "equity_irr", "min_dscr", "avg_dscr", "min_llcr"}
        assert required.issubset(keys)


# ── OverviewProjection active_scenario_name ───────────────────────────────── #

class TestOverviewProjectionScenarioName:

    def test_active_scenario_name_field_exists(self):
        from app.v2.overview_projection import OverviewProjection, NOT_AVAILABLE
        # Field must exist and default to ""
        import inspect
        sig = inspect.signature(OverviewProjection)
        assert "active_scenario_name" in sig.parameters

    def test_build_passes_through_name(self):
        from app.v2.overview_projection import build_overview_projection
        import inspect
        sig = inspect.signature(build_overview_projection)
        assert "active_scenario_name" in sig.parameters


# ── router DRIVER_SPECS completeness ─────────────────────────────────────── #

class TestDriverSpecs:

    def _get_driver_specs(self):
        import importlib, ast, re
        src = open("app/v2/router.py").read()
        # Find DRIVER_SPECS dict literal
        m = re.search(r"DRIVER_SPECS\s*=\s*\{(.+?)\}\s*\n[^\s]", src, re.DOTALL)
        assert m, "DRIVER_SPECS not found in router.py"
        return m.group(0)

    def test_driver_specs_exists(self):
        src = open("app/v2/router.py").read()
        assert "DRIVER_SPECS" in src

    def test_required_drivers_present(self):
        src = open("app/v2/router.py").read()
        for driver in ["tariff", "capex_total", "opex_total", "generation", "interest_rate", "gearing"]:
            assert f'"{driver}"' in src or f"'{driver}'" in src, f"driver {driver!r} missing"

    def test_five_steps_per_driver(self):
        import re
        src = open("app/v2/router.py").read()
        # Count step lists — each should have 5 entries
        step_lists = re.findall(r'"steps":\s*\[([^\]]+)\]', src)
        for sl in step_lists:
            count = len([x.strip() for x in sl.split(",") if x.strip()])
            assert count == 5, f"Expected 5 steps, got {count}: {sl}"
