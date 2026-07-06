"""V4-7: BESS Complete Workflow tests.

Validates:
- BessParams extended fields present
- create_default_bess_project has bess attached
- bess_service builds revenue breakdown and asset dashboard
- BESS shocks are in SHOCK_REGISTRY and apply cleanly
- Template files exist
- Golden parity unchanged (TUHO Wind 1)
"""
from __future__ import annotations

import os
import pytest


# ─── BessParams extended fields ──────────────────────────────────────────────

class TestBessParamsExtended:
    def test_frequency_regulation_field_exists(self):
        from finco_core.inputs.bess import BessParams
        p = BessParams(power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0)
        assert hasattr(p, "frequency_regulation_eur_mw_year")
        assert p.frequency_regulation_eur_mw_year == 0.0

    def test_reserve_market_field_exists(self):
        from finco_core.inputs.bess import BessParams
        p = BessParams(power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0)
        assert p.reserve_market_eur_mw_year == 0.0

    def test_fixed_contracted_field_exists(self):
        from finco_core.inputs.bess import BessParams
        p = BessParams(power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0)
        assert p.fixed_contracted_eur_mw_year == 0.0

    def test_depth_of_discharge_field(self):
        from finco_core.inputs.bess import BessParams
        p = BessParams(power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0)
        assert p.depth_of_discharge == 0.85

    def test_cycle_life_field(self):
        from finco_core.inputs.bess import BessParams
        p = BessParams(power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0)
        assert p.cycle_life == 4000

    def test_replacement_year_field(self):
        from finco_core.inputs.bess import BessParams
        p = BessParams(power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0)
        assert p.replacement_year == 0

    def test_domain_bess_params_has_same_fields(self):
        from domain.revenue.bess import BessParams
        p = BessParams(power_mw=10.0, energy_mwh=20.0, cycles_per_year=365.0)
        assert hasattr(p, "frequency_regulation_eur_mw_year")
        assert hasattr(p, "depth_of_discharge")
        assert hasattr(p, "cycle_life")


# ─── Factory fix ─────────────────────────────────────────────────────────────

class TestBessProjectFactory:
    def test_bess_project_has_bess_params(self):
        from app.project_factories import create_default_bess_project
        proj = create_default_bess_project()
        assert proj.technical.bess is not None

    def test_bess_project_bess_enabled(self):
        from app.project_factories import create_default_bess_project
        proj = create_default_bess_project()
        assert proj.technical.bess_enabled is True

    def test_solar_bess_project_has_bess_params(self):
        from app.project_factories import create_default_solar_bess_project
        proj = create_default_solar_bess_project()
        assert proj.technical.bess is not None

    def test_wind_bess_project_has_bess_params(self):
        from app.project_factories import create_default_wind_bess_project
        proj = create_default_wind_bess_project()
        assert proj.technical.bess is not None


# ─── BESS service ─────────────────────────────────────────────────────────────

class TestBessService:
    @pytest.fixture(scope="class")
    def bess_proj_result(self):
        from app.project_factories import create_default_solar_bess_project
        from app.ui_runner import _build_period_engine
        from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
        proj = create_default_solar_bess_project()
        eng = _build_period_engine(proj)
        result = WaterfallRunner(proj, eng).run(WaterfallRunConfig.from_inputs(proj, eng))
        return proj, result

    def test_build_bess_revenue_breakdown_returns_dict(self, bess_proj_result):
        from app.services.bess_service import build_bess_revenue_breakdown
        proj, result = bess_proj_result
        br = build_bess_revenue_breakdown(proj, result)
        assert br is not None
        assert "params" in br
        assert "annual" in br
        assert "lifetime" in br

    def test_revenue_breakdown_has_periods(self, bess_proj_result):
        from app.services.bess_service import build_bess_revenue_breakdown
        proj, result = bess_proj_result
        br = build_bess_revenue_breakdown(proj, result)
        assert len(br["periods"]) > 0

    def test_lifetime_net_revenue_positive(self, bess_proj_result):
        from app.services.bess_service import build_bess_revenue_breakdown
        proj, result = bess_proj_result
        br = build_bess_revenue_breakdown(proj, result)
        assert br["lifetime"]["net_revenue_keur"] > 0

    def test_build_bess_asset_dashboard_returns_dict(self, bess_proj_result):
        from app.services.bess_service import build_bess_asset_dashboard
        proj, result = bess_proj_result
        ba = build_bess_asset_dashboard(proj, result)
        assert ba is not None
        assert "soh_curve" in ba
        assert "capacity_curve" in ba
        assert "end_of_life" in ba

    def test_soh_curve_length(self, bess_proj_result):
        from app.services.bess_service import build_bess_asset_dashboard
        proj, result = bess_proj_result
        ba = build_bess_asset_dashboard(proj, result)
        assert len(ba["soh_curve"]) == proj.info.horizon_years

    def test_non_bess_project_returns_none(self):
        from app.services.bess_service import build_bess_revenue_breakdown, build_bess_asset_dashboard
        from app.project_factories import create_default_tuho_wind1
        from app.ui_runner import _build_period_engine
        from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
        proj = create_default_tuho_wind1()
        eng = _build_period_engine(proj)
        result = WaterfallRunner(proj, eng).run(WaterfallRunConfig.from_inputs(proj, eng))
        assert build_bess_revenue_breakdown(proj, result) is None
        assert build_bess_asset_dashboard(proj, result) is None


# ─── BESS shocks ─────────────────────────────────────────────────────────────

class TestBessShocks:
    BESS_SHOCKS = [
        "bess_arbitrage_spread",
        "bess_cycles",
        "bess_rte",
        "bess_ancillary_price",
        "bess_capacity_price",
    ]

    def test_bess_shocks_in_registry(self):
        from app.services.sensitivity_service import SHOCK_REGISTRY
        for shock in self.BESS_SHOCKS:
            assert shock in SHOCK_REGISTRY, f"Missing shock: {shock}"

    def test_bess_shock_applies_without_error(self):
        from app.services.sensitivity_service import _apply_shock
        from app.project_factories import create_default_solar_bess_project
        proj = create_default_solar_bess_project()
        for shock in self.BESS_SHOCKS:
            shocked = _apply_shock(proj, shock, 10.0)
            assert shocked is not None

    def test_bess_arbitrage_shock_changes_spread(self):
        from app.services.sensitivity_service import _apply_shock
        from app.project_factories import create_default_solar_bess_project
        proj = create_default_solar_bess_project()
        shocked = _apply_shock(proj, "bess_arbitrage_spread", 10.0)
        orig = proj.technical.bess.arbitrage_spread_eur_mwh
        new = shocked.technical.bess.arbitrage_spread_eur_mwh
        assert new == pytest.approx(orig * 1.10)

    def test_bess_shock_on_non_bess_project_is_noop(self):
        from app.services.sensitivity_service import _apply_shock
        from app.project_factories import create_default_tuho_wind1
        proj = create_default_tuho_wind1()
        shocked = _apply_shock(proj, "bess_arbitrage_spread", 10.0)
        assert shocked is proj  # no BESS params → returns original


# ─── Template files ───────────────────────────────────────────────────────────

class TestBessTemplates:
    def test_bess_revenue_breakdown_template_exists(self):
        assert os.path.exists("app/templates/partials/bess_revenue_breakdown.html")

    def test_bess_asset_dashboard_template_exists(self):
        assert os.path.exists("app/templates/partials/bess_asset_dashboard.html")

    def test_workspace_includes_bess_templates(self):
        import re
        with open("app/templates/partials/scenario_workspace.html") as f:
            content = f.read()
        assert "bess_revenue_breakdown.html" in content
        assert "bess_asset_dashboard.html" in content


# ─── Golden parity (regression guard) ────────────────────────────────────────

class TestGoldenParityUnchanged:
    @pytest.fixture(scope="class")
    def tuho_result(self):
        from app.project_factories import create_default_tuho_wind1
        from app.ui_runner import _build_period_engine
        from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
        proj = create_default_tuho_wind1()
        eng = _build_period_engine(proj)
        return WaterfallRunner(proj, eng).run(WaterfallRunConfig.from_inputs(proj, eng))

    def test_equity_irr(self, tuho_result):
        assert abs(tuho_result.equity_irr - 0.1132) < 0.001

    def test_avg_dscr(self, tuho_result):
        assert abs(tuho_result.actual_avg_dscr - 1.3786) < 0.01

    def test_distributions(self, tuho_result):
        assert abs(tuho_result.total_distribution_keur - 165471) < 1000
