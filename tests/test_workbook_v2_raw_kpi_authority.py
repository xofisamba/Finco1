"""
UI-4A Correction B — Raw KPI Authority Tests.

Proves:
1. RuntimeResult.raw_kpis returns numeric-only subset (excludes revenue_derivation)
2. Overview uses raw_kpis → OutputMetricProjection correctly
3. Catalog consolidation: scenario_kpi_projection imports KPI_CATALOG from output_metric_projection
4. No format→parse→format patterns in presentation modules
5. Zero / None / unavailable integration
6. Compare raw delta arithmetic (never string parsing)
7. RuntimeResult construction paths

Required tokens:
  RAW_KPI_AUTHORITY, NO_FORMAT_PARSE_FORMAT, OVERVIEW_USES_CANONICAL_METRICS,
  COMPARE_USES_CANONICAL_METRICS, NO_SILENT_ZERO
"""
from __future__ import annotations

import inspect
import re
from types import MappingProxyType
from typing import Any

import pytest

from app.v2.output_metric_projection import (
    KPI_CATALOG,
    OutputMetricProjection,
    MetricAvailability,
    build_output_metric_projection,
    build_overview_metric_projections,
)
from app.v2.scenario_kpi_projection import (
    build_scenario_projection,
    build_compare_rows,
    ScenarioProjection,
)


# ─────────────────────────────────────────────────────────────────────────── #
# 1. RuntimeResult.raw_kpis property                                          #
# ─────────────────────────────────────────────────────────────────────────── #

class TestRuntimeResultRawKpis:
    """raw_kpis returns numeric subset, excluding revenue_derivation."""

    def _make_rr(self, runtime_summary: dict):
        """Build a minimal RuntimeResult from a runtime_summary dict."""
        from app.workbook.runtime_result import RuntimeResult
        return RuntimeResult(
            snapshot_id="20260908T120000Z",
            ran_at="2026-09-08T12:00:00Z",
            origin="test",
            runtime_summary=runtime_summary,
            financial_statements=None,
            debt_schedule=None,
            tax_schedule=None,
            distribution_schedule=None,
            sponsor_schedule=None,
        )

    def test_raw_kpis_returns_numeric_values(self):
        rr = self._make_rr({
            "project_irr": 0.085,
            "equity_irr": 0.123,
            "min_dscr": 1.32,
        })
        kpis = rr.raw_kpis
        assert kpis["project_irr"] == 0.085
        assert kpis["equity_irr"] == 0.123
        assert kpis["min_dscr"] == 1.32

    def test_raw_kpis_excludes_revenue_derivation(self):
        rr = self._make_rr({
            "project_irr": 0.085,
            "revenue_derivation": {"display_value_keur": "27,000 kEUR"},
        })
        kpis = rr.raw_kpis
        assert "revenue_derivation" not in kpis
        assert "project_irr" in kpis

    def test_raw_kpis_empty_when_no_runtime_summary(self):
        from app.workbook.runtime_result import RuntimeResult
        rr = RuntimeResult(
            snapshot_id="test",
            ran_at="",
            origin="test",
            runtime_summary={},
            financial_statements=None,
            debt_schedule=None,
            tax_schedule=None,
            distribution_schedule=None,
            sponsor_schedule=None,
        )
        assert rr.raw_kpis == {}

    def test_raw_kpis_survives_mappingproxy(self):
        """MappingProxyType (frozen dicts) must be handled transparently."""
        rr = self._make_rr({
            "project_irr": 0.085,
            "min_dscr": 1.32,
        })
        # RuntimeResult __post_init__ freezes to MappingProxyType
        assert isinstance(rr.runtime_summary, MappingProxyType)
        kpis = rr.raw_kpis
        assert isinstance(kpis, dict)
        assert kpis["project_irr"] == 0.085

    def test_raw_kpis_reconstruction_path(self):
        """Simulate from_workspace_state: raw floats survive workspace persist."""
        from app.workbook.runtime_result import RuntimeResult

        # Simulate what v2_atomic_run_commit persists: raw kpis + revenue_derivation
        persisted = {
            "project_irr": 0.07593168077589,
            "equity_irr": 0.1234,
            "min_dscr": 1.32,
            "avg_dscr": 1.45,
            "total_capex_keur": 45000.0,
            "revenue_derivation": {"display_value_keur": "80000"},
        }
        rr = RuntimeResult(
            snapshot_id="20260908T143200Z",
            ran_at="2026-09-08T14:32:00Z",
            origin="v2_run",
            runtime_summary=persisted,
            financial_statements=None,
            debt_schedule=None,
            tax_schedule=None,
            distribution_schedule=None,
            sponsor_schedule=None,
        )
        kpis = rr.raw_kpis
        # Solar real-engine proof value: raw IRR preserved exactly
        assert kpis["project_irr"] == pytest.approx(0.07593168077589)
        assert "revenue_derivation" not in kpis

        # build_output_metric_projection must produce correct display
        proj = build_output_metric_projection("project_irr", kpis["project_irr"], freshness="current")
        assert proj.raw_value == pytest.approx(0.07593168077589)
        assert proj.display_value == "7.59%"


# ─────────────────────────────────────────────────────────────────────────── #
# 2. Catalog consolidation proof                                               #
# ─────────────────────────────────────────────────────────────────────────── #

class TestCatalogConsolidation:
    """One canonical KPI_CATALOG from output_metric_projection only."""

    def test_scenario_kpi_projection_imports_catalog(self):
        """scenario_kpi_projection must NOT define its own KPI list."""
        import app.v2.scenario_kpi_projection as skp
        import app.v2.output_metric_projection as omp
        # The catalog used in scenario_kpi_projection must be the same object
        # or a subset of output_metric_projection.KPI_CATALOG
        skp_src = inspect.getsource(skp)
        # Must import from output_metric_projection
        assert "from app.v2.output_metric_projection import" in skp_src
        assert "KPI_CATALOG" in skp_src
        # Must NOT define a new standalone list named KPI_CATALOG
        # (local import re-uses omp's catalog)
        assert skp_src.count("KPI_CATALOG = [") == 0

    def test_all_scenario_projection_keys_from_canonical_catalog(self):
        """ScenarioProjection KPIs come from KPI_CATALOG entries."""
        rs = {
            "project_irr": 0.085,
            "equity_irr": 0.10,
            "min_dscr": 1.32,
            "avg_dscr": 1.45,
            "min_llcr": 1.28,
            "target_dscr": 1.20,
        }
        proj = build_scenario_projection("Test", rs, "2026-09-08T12:00:00Z", False)
        catalog_keys = {entry[0] for entry in KPI_CATALOG}
        for key in proj.kpis:
            assert key in catalog_keys, f"Key {key!r} not in canonical catalog"

    def test_compare_rows_keys_match_catalog(self):
        rs = {"project_irr": 0.085, "min_dscr": 1.32}
        p1 = build_scenario_projection("Base", rs, None, False)
        p2 = build_scenario_projection("Downside", {"project_irr": 0.070, "min_dscr": 1.15}, None, False)
        rows = build_compare_rows([p1, p2])
        row_keys = {r.key for r in rows}
        catalog_keys = {entry[0] for entry in KPI_CATALOG}
        assert row_keys == catalog_keys


# ─────────────────────────────────────────────────────────────────────────── #
# 3. Overview uses raw_kpis via OutputMetricProjection                         #
# ─────────────────────────────────────────────────────────────────────────── #

class TestOverviewUsesCanonicalMetrics:
    """Overview receives OutputMetricProjection objects with correct raw values."""

    def _make_rr_full(self, kpis: dict, debt_summary: dict = None):
        from app.workbook.runtime_result import RuntimeResult
        debt_payload = None
        if debt_summary:
            debt_payload = {"summary": debt_summary, "periods": []}
        return RuntimeResult(
            snapshot_id="snap001",
            ran_at="2026-09-08T14:32:00Z",
            origin="v2_run",
            runtime_summary=kpis,
            financial_statements=None,
            debt_schedule=debt_payload,
            tax_schedule=None,
            distribution_schedule=None,
            sponsor_schedule=None,
        )

    def _make_pis(self):
        class _FakePis:
            template_source = "generic_solar"
            def to_projectinputs(self):
                raise Exception("no real PIS")
        return _FakePis()

    def test_overview_output_metrics_populated(self):
        from app.v2.overview_projection import build_overview_projection
        rr = self._make_rr_full({
            "project_irr": 0.085,
            "equity_irr": 0.12,
            "min_dscr": 1.32,
            "avg_dscr": 1.45,
        })
        ov = build_overview_projection(rr, False, self._make_pis())
        assert "project_irr" in ov.output_metrics
        assert "equity_irr" in ov.output_metrics

    def test_overview_project_irr_display_from_raw(self):
        """0.085 → raw_value=0.085 → display_value='8.50%'."""
        from app.v2.overview_projection import build_overview_projection
        rr = self._make_rr_full({"project_irr": 0.085})
        ov = build_overview_projection(rr, False, self._make_pis())
        m = ov.output_metrics["project_irr"]
        assert m.raw_value == pytest.approx(0.085)
        assert m.display_value == "8.50%"
        assert m.availability == MetricAvailability.AVAILABLE

    def test_overview_none_irr_gives_dash(self):
        """None raw value → display_value='—' (NOT 'NOT_AVAILABLE')."""
        from app.v2.overview_projection import build_overview_projection
        rr = self._make_rr_full({"project_irr": None})
        ov = build_overview_projection(rr, False, self._make_pis())
        m = ov.output_metrics["project_irr"]
        assert m.raw_value is None
        assert m.display_value == "—"
        assert "NOT_AVAILABLE" not in m.display_value

    def test_overview_zero_irr_is_available(self):
        """Zero raw value → AVAILABLE, display '0.00%', not '—' (NO_SILENT_ZERO)."""
        from app.v2.overview_projection import build_overview_projection
        rr = self._make_rr_full({"project_irr": 0.0})
        ov = build_overview_projection(rr, False, self._make_pis())
        m = ov.output_metrics["project_irr"]
        assert m.raw_value == 0.0
        assert m.display_value == "0.00%"
        assert m.availability == MetricAvailability.AVAILABLE

    def test_overview_zero_dscr_is_available(self):
        """Zero DSCR → '0.00x', not '—'."""
        from app.v2.overview_projection import build_overview_projection
        rr = self._make_rr_full({"min_dscr": 0.0})
        ov = build_overview_projection(rr, False, self._make_pis())
        m = ov.output_metrics["min_dscr"]
        assert m.display_value == "0.00x"
        assert m.availability == MetricAvailability.AVAILABLE

    def test_overview_zero_keur_is_available(self):
        """Zero kEUR → '0 kEUR', not '—'."""
        from app.v2.overview_projection import build_overview_projection
        rr = self._make_rr_full({"total_capex_keur": 0.0})
        ov = build_overview_projection(rr, False, self._make_pis())
        m = ov.output_metrics["total_capex_keur"]
        assert m.display_value == "0 kEUR"
        assert m.availability == MetricAvailability.AVAILABLE

    def test_overview_run_timestamp_display_normalized(self):
        """run_timestamp_display is normalized in Python (no Jinja slicing)."""
        from app.v2.overview_projection import build_overview_projection
        rr = self._make_rr_full({"project_irr": 0.085})
        ov = build_overview_projection(rr, False, self._make_pis())
        assert ov.run_timestamp_display == "2026-09-08 14:32 UTC"

    def test_overview_no_run_timestamp_display_empty(self):
        from app.v2.overview_projection import build_overview_projection
        ov = build_overview_projection(None, False, self._make_pis())
        assert ov.run_timestamp_display == ""


# ─────────────────────────────────────────────────────────────────────────── #
# 4. Compare canonical projection and raw delta                                #
# ─────────────────────────────────────────────────────────────────────────── #

class TestCompareCanonicalProjection:
    """Compare uses canonical KPI_CATALOG and raw float deltas."""

    def test_compare_delta_from_raw_floats(self):
        """Delta = raw_base - raw_scenario; never parse formatted strings."""
        base_rs = {"project_irr": 0.085}
        down_rs = {"project_irr": 0.070}
        base = build_scenario_projection("Base", base_rs, None, False)
        down = build_scenario_projection("Downside", down_rs, None, False)
        rows = build_compare_rows([base, down])
        irr_row = next(r for r in rows if r.key == "project_irr")
        assert irr_row.deltas[0] == "—"        # base has no delta
        assert irr_row.deltas[1] == "-1.50%"   # -0.015 * 100 = -1.50%

    def test_compare_dscr_delta_ratio(self):
        base = build_scenario_projection("Base", {"min_dscr": 1.32}, None, False)
        upside = build_scenario_projection("Upside", {"min_dscr": 1.45}, None, False)
        rows = build_compare_rows([base, upside])
        dscr_row = next(r for r in rows if r.key == "min_dscr")
        assert dscr_row.deltas[1] == "+0.13x"

    def test_compare_none_base_delta_is_dash(self):
        base = build_scenario_projection("Base", {"min_dscr": None}, None, False)
        other = build_scenario_projection("Other", {"min_dscr": 1.32}, None, False)
        rows = build_compare_rows([base, other])
        dscr_row = next(r for r in rows if r.key == "min_dscr")
        assert dscr_row.deltas[1] == "—"

    def test_compare_raw_values_preserved(self):
        base = build_scenario_projection("Base", {"project_irr": 0.085}, None, False)
        rows = build_compare_rows([base])
        irr_row = next(r for r in rows if r.key == "project_irr")
        assert irr_row.raw_values[0] == pytest.approx(0.085)

    def test_compare_formatted_string_in_rs_yields_dash(self):
        """Pre-formatted strings in runtime_summary must not be parsed back."""
        # If runtime_summary contains a pre-formatted string "8.50%", it should
        # produce raw_value=None and display "—", not parse back to 8.5.
        rs = {"project_irr": "8.50%"}
        proj = build_scenario_projection("Test", rs, None, False)
        assert proj.kpis["project_irr"] == "—"
        assert proj.kpis_raw["project_irr"] is None


# ─────────────────────────────────────────────────────────────────────────── #
# 5. No-format-parse-format structural guard                                   #
# ─────────────────────────────────────────────────────────────────────────── #

class TestNoFormatParseFormat:
    """Scan presentation modules for forbidden raw reconstruction patterns.

    Forbidden: replace("%",...) / replace("x",...) / replace("kEUR",...) or
    strip("%") followed by float() conversion in presentation modules.
    """

    PRESENTATION_MODULES = [
        "app/v2/output_metric_projection.py",
        "app/v2/overview_projection.py",
        "app/v2/scenario_kpi_projection.py",
    ]

    # Pattern: stripping a unit suffix and converting back to float
    _FORBIDDEN_PATTERNS = [
        # .replace("%" ...) followed by float() within same function
        r'\.replace\(["\']%["\']',
        r'\.replace\(["\']x["\']',
        r'\.replace\(["\']kEUR["\']',
        r'strip\(["\']%["\']',
    ]

    def test_no_parse_format_in_output_metric_projection(self):
        self._check_module("app/v2/output_metric_projection.py")

    def test_no_parse_format_in_scenario_kpi_projection(self):
        self._check_module("app/v2/scenario_kpi_projection.py")

    def test_resolve_display_deleted(self):
        """_resolve_display must not exist in output_metric_projection."""
        import app.v2.output_metric_projection as omp
        assert not hasattr(omp, "_resolve_display"), (
            "_resolve_display still exists — must be deleted (Correction A)"
        )

    def _check_module(self, path: str):
        import os
        full = os.path.join("/home/user/Finco1", path)
        with open(full) as f:
            src = f.read()
        for pattern in self._FORBIDDEN_PATTERNS:
            matches = re.findall(pattern, src)
            if matches:
                # Allowed: display-only manipulation unrelated to numeric parsing
                # Check if any match is followed by float() (forbidden reconstruction)
                for m in matches:
                    # Check surrounding context for float() conversion
                    idx = src.find(m[:20])
                    if idx != -1:
                        ctx = src[max(0, idx-20):idx+200]
                        if "float(" in ctx:
                            pytest.fail(
                                f"Forbidden format→parse pattern in {path}:\n{ctx}"
                            )


# ─────────────────────────────────────────────────────────────────────────── #
# 6. Zero / None / unavailable end-to-end                                     #
# ─────────────────────────────────────────────────────────────────────────── #

class TestZeroUnavailableIntegration:
    """Prove zero and None handling through the full projection path."""

    @pytest.mark.parametrize("key,zero_display", [
        ("project_irr", "0.00%"),
        ("equity_irr", "0.00%"),
        ("min_dscr", "0.00x"),
        ("avg_dscr", "0.00x"),
        ("total_capex_keur", "0 kEUR"),
        ("total_revenue_keur", "0 kEUR"),
    ])
    def test_zero_raw_value_renders_explicitly(self, key, zero_display):
        """0.0 → AVAILABLE with explicit numeric display (not '—')."""
        proj = build_output_metric_projection(key, 0.0, freshness="current")
        assert proj.display_value == zero_display, (
            f"Key {key!r}: zero should render as {zero_display!r}, got {proj.display_value!r}"
        )
        assert proj.availability == MetricAvailability.AVAILABLE
        assert proj.raw_value == 0.0

    @pytest.mark.parametrize("key", [
        "project_irr", "min_dscr", "total_capex_keur",
    ])
    def test_none_raw_value_renders_dash(self, key):
        """None → NOT_AVAILABLE, display_value='—' (never 'NOT_AVAILABLE')."""
        proj = build_output_metric_projection(key, None, freshness="current")
        assert proj.display_value == "—"
        assert proj.raw_value is None
        assert "NOT_AVAILABLE" not in proj.display_value

    def test_nan_produces_dash(self):
        """NaN → NOT_AVAILABLE, display_value='—'."""
        import math
        proj = build_output_metric_projection("project_irr", float("nan"), freshness="current")
        assert proj.display_value == "—"
        assert proj.raw_value is None

    def test_inf_produces_dash(self):
        """Infinity → NOT_AVAILABLE, display_value='—'."""
        proj = build_output_metric_projection("project_irr", float("inf"), freshness="current")
        assert proj.display_value == "—"
        assert proj.raw_value is None


# ─────────────────────────────────────────────────────────────────────────── #
# 7. Senior debt / CFADS gap documentation                                     #
# ─────────────────────────────────────────────────────────────────────────── #

class TestRawAuthorityGaps:
    """senior_debt_keur and total_cfads_keur are documented gaps."""

    def test_senior_debt_not_in_result_kpis(self):
        """Absence of senior_debt_keur in runtime_summary → raw_value=None."""
        rs = {"project_irr": 0.085}  # no senior_debt_keur
        metrics = build_overview_metric_projections(rs, {}, freshness="current")
        sd = metrics["senior_debt_keur"]
        assert sd.raw_value is None, "senior_debt_keur not in kpis; must be None"
        assert sd.display_value == "—"

    def test_total_cfads_not_in_result_kpis(self):
        """Absence of total_cfads_keur in runtime_summary → raw_value=None."""
        rs = {"project_irr": 0.085}
        metrics = build_overview_metric_projections(rs, {}, freshness="current")
        cf = metrics["total_cfads_keur"]
        assert cf.raw_value is None
        assert cf.display_value == "—"

    def test_senior_debt_available_when_present(self):
        """If senior_debt_keur is ever added to kpis, it must format correctly."""
        rs = {"senior_debt_keur": 27000.0}
        metrics = build_overview_metric_projections(rs, {}, freshness="current")
        sd = metrics["senior_debt_keur"]
        assert sd.raw_value == 27000.0
        assert "27,000" in sd.display_value
        assert "kEUR" in sd.display_value
