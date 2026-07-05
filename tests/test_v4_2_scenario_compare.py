"""V4-2: Scenario Compare & Analysis Workspace tests.

Tests cover the four parts of V4-2:
  A. True Scenario Compare — direction-aware delta sign classes
  B. Input Difference Viewer — diff_scenario_inputs returns field diffs
  C. KPI Dashboard — extended metric set in multi-compare
  D. Financial Statements Compare — FS rows built from canonical engine
"""
from __future__ import annotations

import pytest

from app.persistence.exports_repository import (
    MULTI_COMPARE_HIGHER_IS_BETTER,
    MULTI_COMPARE_LOWER_IS_BETTER,
    MULTI_COMPARE_METRIC_ORDER,
    diff_scenario_inputs,
)


# ─── Part A+C: KPI compare metric set ─────────────────────────────────────


class TestKPICompareMetrics:
    """Part A+C: extended metric set and direction awareness."""

    def test_extended_metric_order_includes_cfads(self):
        assert "CFADS" in MULTI_COMPARE_METRIC_ORDER

    def test_extended_metric_order_includes_min_dscr(self):
        assert "Min DSCR" in MULTI_COMPARE_METRIC_ORDER

    def test_extended_metric_order_includes_distributions(self):
        assert "Distributions" in MULTI_COMPARE_METRIC_ORDER

    def test_direction_higher_is_better_set(self):
        """IRR, DSCR, Revenue, Distributions should be higher-is-better."""
        for key in ("Equity IRR", "Project IRR", "Revenue", "EBITDA", "Distributions", "Min DSCR", "Avg DSCR"):
            assert key in MULTI_COMPARE_HIGHER_IS_BETTER, f"{key} missing from higher-is-better"

    def test_direction_lower_is_better_set(self):
        """OPEX, CAPEX should be lower-is-better."""
        for key in ("OPEX", "CAPEX"):
            assert key in MULTI_COMPARE_LOWER_IS_BETTER, f"{key} missing from lower-is-better"

    def test_disjoint_direction_sets(self):
        """No metric in both direction sets."""
        overlap = MULTI_COMPARE_HIGHER_IS_BETTER & MULTI_COMPARE_LOWER_IS_BETTER
        assert not overlap, f"Overlap between direction sets: {overlap}"


# ─── Part B: Input Difference Viewer ─────────────────────────────────────


class TestDiffScenarioInputsUnit:
    """Unit tests for diff_scenario_inputs using stub ScenarioRecord-like objects."""

    def _make_record(self, scenario_id, scenario_name, snapshot):
        """Create a minimal stub for ScenarioRecord."""

        class _Rec:
            pass

        r = _Rec()
        r.scenario_id = scenario_id
        r.scenario_name = scenario_name
        r.snapshot = snapshot
        r.last_run_summary = {}
        r.governance_state = {}
        return r

    def test_diff_no_db(self, monkeypatch):
        """diff_scenario_inputs diffs snapshot fields; mocks DB call."""
        base_snap = {"capacity_mw": "35", "tariff_eur_mwh": "80.0", "total_capex_keur": "50000"}
        other_snap = {"capacity_mw": "40", "tariff_eur_mwh": "80.0", "total_capex_keur": "55000"}
        base_rec = self._make_record("base-1", "Base Case", base_snap)
        other_rec = self._make_record("other-1", "Scenario A", other_snap)

        import app.persistence.exports_repository as er

        def _mock_get(sid, uid):
            if sid == "base-1":
                return base_rec
            if sid == "other-1":
                return other_rec
            return None

        monkeypatch.setattr(er, "_get_scenario_for_diff", _mock_get, raising=False)
        # Patch the import inside diff_scenario_inputs
        import app.persistence.repository as repo
        monkeypatch.setattr(repo, "get_scenario", _mock_get)

        result = diff_scenario_inputs("user-1", "base-1", "other-1")
        assert result is not None
        assert result["changed_count"] >= 2

        changed_fields = {r["field"] for r in result["rows"] if r["changed"]}
        # capacity_mw (35 -> 40) and total_capex_keur (50000 -> 55000) changed
        assert any("Capacity" in f for f in changed_fields)
        assert any("CAPEX" in f for f in changed_fields)

    def test_diff_returns_none_when_scenario_missing(self, monkeypatch):
        import app.persistence.repository as repo
        monkeypatch.setattr(repo, "get_scenario", lambda sid, uid: None)
        result = diff_scenario_inputs("user-1", "missing-1", "missing-2")
        assert result is None

    def test_diff_same_id_is_zero_changes(self, monkeypatch):
        snap = {"capacity_mw": "35", "total_capex_keur": "50000"}
        rec = self._make_record("s1", "Base", snap)
        import app.persistence.repository as repo
        monkeypatch.setattr(repo, "get_scenario", lambda sid, uid: rec)
        result = diff_scenario_inputs("user-1", "s1", "s1")
        # Same scenario — all fields identical
        assert result["changed_count"] == 0


# ─── Part D: FS Compare — unit test the row builders ─────────────────────


class TestFSCompareRowBuilders:
    """Part D: verify canonical FS rows are produced from factory inputs."""

    def test_pnl_rows_from_factory(self):
        """Run factory TUHO through engine and verify PnL rows exist."""
        from app.project_factories import create_default_tuho_wind1
        from app.ui_runner import _build_period_engine
        from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
        from domain.financial_statements import assemble_financial_statements

        proj = create_default_tuho_wind1()
        eng = _build_period_engine(proj)
        result = WaterfallRunner(proj, eng).run(WaterfallRunConfig.from_inputs(proj, eng))
        fs = assemble_financial_statements(result)

        assert len(fs.pnl.periods) > 0
        total_revenue = sum(p.revenues_keur for p in fs.pnl.periods)
        assert total_revenue > 0

    def test_balance_sheet_rows_from_factory(self):
        """Final balance sheet period is non-zero."""
        from app.project_factories import create_default_tuho_wind1
        from app.ui_runner import _build_period_engine
        from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
        from domain.financial_statements import assemble_financial_statements

        proj = create_default_tuho_wind1()
        eng = _build_period_engine(proj)
        result = WaterfallRunner(proj, eng).run(WaterfallRunConfig.from_inputs(proj, eng))
        fs = assemble_financial_statements(result)

        bs_final = fs.balance_sheet.periods[-1]
        assert bs_final.total_assets_keur != 0

    def test_pf_cash_waterfall_rows_from_factory(self):
        """PF Cash Waterfall has net_dividends in at least one period."""
        from app.project_factories import create_default_tuho_wind1
        from app.ui_runner import _build_period_engine
        from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
        from domain.financial_statements import assemble_financial_statements

        proj = create_default_tuho_wind1()
        eng = _build_period_engine(proj)
        result = WaterfallRunner(proj, eng).run(WaterfallRunConfig.from_inputs(proj, eng))
        fs = assemble_financial_statements(result)

        total_dividends = sum(p.net_dividends_keur for p in fs.pf_cash_waterfall.periods)
        assert total_dividends > 0

    def test_two_factory_scenarios_have_identical_fs(self):
        """Two runs from the same factory produce identical FS totals."""
        from app.project_factories import create_default_tuho_wind1
        from app.ui_runner import _build_period_engine
        from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
        from domain.financial_statements import assemble_financial_statements

        def _run_fs():
            proj = create_default_tuho_wind1()
            eng = _build_period_engine(proj)
            result = WaterfallRunner(proj, eng).run(WaterfallRunConfig.from_inputs(proj, eng))
            return assemble_financial_statements(result)

        fs1 = _run_fs()
        fs2 = _run_fs()
        t1 = sum(p.revenues_keur for p in fs1.pnl.periods)
        t2 = sum(p.revenues_keur for p in fs2.pnl.periods)
        assert abs(t1 - t2) < 0.01
