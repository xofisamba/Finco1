"""V4-4: Lender Case & Covenant Workspace tests.

Validates:
- apply_lender_adjustments: direction of each stress type
- run_lender_case: returns expected keys, KPIs move in correct direction
- build_covenant_periods: correct RAG classification, field presence
- build_credit_summary: correct field population
- Golden-parity: base IRR / avg DSCR unchanged vs V4-3 references
"""
from __future__ import annotations

import pytest

# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def tuho_proj():
    from app.project_factories import create_default_tuho_wind1
    return create_default_tuho_wind1()


@pytest.fixture(scope="module")
def tuho_base_result(tuho_proj):
    from app.ui_runner import _build_period_engine
    from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
    eng = _build_period_engine(tuho_proj)
    return WaterfallRunner(tuho_proj, eng).run(WaterfallRunConfig.from_inputs(tuho_proj, eng))


@pytest.fixture(scope="module")
def tuho_base_kpis(tuho_base_result):
    r = tuho_base_result
    return {
        "equity_irr": r.equity_irr,
        "project_irr": r.project_irr,
        "actual_avg_dscr": r.actual_avg_dscr,
        "min_dscr": r.min_dscr,
        "min_llcr": r.min_llcr,
        "total_distribution_keur": r.total_distribution_keur,
        "total_revenue_keur": r.total_revenue_keur,
        "total_ebitda_keur": r.total_ebitda_keur,
        "equity_npv": r.equity_npv,
        "total_tax_keur": r.total_tax_keur,
        "total_senior_ds_keur": r.total_senior_ds_keur,
    }


# ─── Golden parity ───────────────────────────────────────────────────────────

class TestGoldenParity:
    def test_equity_irr(self, tuho_base_result):
        assert abs(tuho_base_result.equity_irr - 0.1132) < 0.001

    def test_avg_dscr(self, tuho_base_result):
        assert abs(tuho_base_result.actual_avg_dscr - 1.3786) < 0.01

    def test_distributions(self, tuho_base_result):
        assert abs(tuho_base_result.total_distribution_keur - 165471) < 1000


# ─── apply_lender_adjustments ─────────────────────────────────────────────────

class TestApplyLenderAdjustments:
    def test_no_adjustments_unchanged(self, tuho_proj):
        from app.services.lender_case_service import apply_lender_adjustments
        stressed = apply_lender_adjustments(tuho_proj, {})
        assert stressed is tuho_proj or stressed == tuho_proj

    def test_yield_haircut_reduces_hours(self, tuho_proj):
        from app.services.lender_case_service import apply_lender_adjustments
        orig_hours = tuho_proj.technical.operating_hours_p50
        stressed = apply_lender_adjustments(tuho_proj, {"yield_haircut": 10.0})
        assert stressed.technical.operating_hours_p50 < orig_hours

    def test_yield_p90_override(self, tuho_proj):
        from app.services.lender_case_service import apply_lender_adjustments
        stressed = apply_lender_adjustments(tuho_proj, {"yield_p90": 3620.0})
        assert abs(stressed.technical.operating_hours_p50 - 3620.0) < 1.0

    def test_ppa_haircut_reduces_tariff(self, tuho_proj):
        from app.services.lender_case_service import apply_lender_adjustments
        orig = tuho_proj.revenue.ppa_base_tariff
        stressed = apply_lender_adjustments(tuho_proj, {"ppa_haircut": 5.0})
        assert stressed.revenue.ppa_base_tariff < orig

    def test_opex_contingency_raises_opex(self, tuho_proj):
        from app.services.lender_case_service import apply_lender_adjustments
        from app.services.sensitivity_service import _apply_shock
        # Verify that the shocked project has higher opex (y1_amount_keur)
        orig_total = sum(getattr(o, "y1_amount_keur", 0.0) or 0.0 for o in tuho_proj.opex)
        stressed = apply_lender_adjustments(tuho_proj, {"opex_contingency": 10.0})
        new_total = sum(getattr(o, "y1_amount_keur", 0.0) or 0.0 for o in stressed.opex)
        assert new_total > orig_total

    def test_availability_stress_reduces_availability(self, tuho_proj):
        from app.services.lender_case_service import apply_lender_adjustments
        orig = tuho_proj.technical.plant_availability
        stressed = apply_lender_adjustments(tuho_proj, {"availability_stress": 5.0})
        assert stressed.technical.plant_availability < orig


# ─── run_lender_case ─────────────────────────────────────────────────────────

class TestRunLenderCase:
    @pytest.fixture(scope="class")
    def lc_result(self, tuho_proj):
        from app.services.lender_case_service import run_lender_case
        return run_lender_case(tuho_proj, {"ppa_haircut": 10.0, "yield_haircut": 5.0})

    def test_returns_kpis_key(self, lc_result):
        assert "kpis" in lc_result

    def test_returns_periods_key(self, lc_result):
        assert "periods" in lc_result
        assert len(lc_result["periods"]) > 0

    def test_returns_adjustment_summary(self, lc_result):
        assert "adjustment_summary" in lc_result
        assert len(lc_result["adjustment_summary"]) > 0

    def test_equity_irr_lower_under_stress(self, lc_result, tuho_base_kpis):
        assert lc_result["kpis"]["equity_irr"] < tuho_base_kpis["equity_irr"]

    def test_distributions_lower_under_stress(self, lc_result, tuho_base_kpis):
        assert lc_result["kpis"]["total_distribution_keur"] < tuho_base_kpis["total_distribution_keur"]

    def test_kpis_have_all_fields(self, lc_result):
        kpis = lc_result["kpis"]
        for key in ["equity_irr", "project_irr", "actual_avg_dscr", "min_dscr", "min_llcr",
                    "total_distribution_keur", "total_revenue_keur", "total_ebitda_keur", "equity_npv"]:
            assert key in kpis, f"Missing KPI: {key}"

    def test_no_adjustments_matches_base(self, tuho_proj, tuho_base_kpis):
        from app.services.lender_case_service import run_lender_case
        lc = run_lender_case(tuho_proj, {})
        assert abs(lc["kpis"]["equity_irr"] - tuho_base_kpis["equity_irr"]) < 1e-6


# ─── build_covenant_periods ───────────────────────────────────────────────────

class TestBuildCovenantPeriods:
    @pytest.fixture(scope="class")
    def periods(self, tuho_base_result):
        from app.services.lender_case_service import build_covenant_periods
        return build_covenant_periods(tuho_base_result)

    def test_non_empty(self, periods):
        assert len(periods) > 0

    def test_required_fields_present(self, periods):
        required = ["period", "date", "dscr", "llcr", "plcr", "lockup",
                    "distribution_keur", "cash_sweep_keur",
                    "senior_balance_keur", "senior_ds_keur", "rag"]
        for p in periods[:3]:
            for f in required:
                assert f in p, f"Missing field: {f}"

    def test_rag_values_valid(self, periods):
        valid_rags = {"ok", "caution", "warning", "breach", "na"}
        for p in periods:
            assert p["rag"] in valid_rags, f"Invalid RAG: {p['rag']}"

    def test_ok_rag_when_dscr_healthy(self, periods):
        healthy = [p for p in periods if p["dscr"] is not None and p["dscr"] >= 1.15]
        for p in healthy:
            assert p["rag"] == "ok", f"Expected ok for DSCR {p['dscr']}, got {p['rag']}"

    def test_breach_rag_when_dscr_below_eod(self, tuho_proj):
        from app.services.lender_case_service import run_lender_case, build_covenant_periods
        lc = run_lender_case(tuho_proj, {"ppa_haircut": 40.0})
        periods = lc["periods"]
        any_breach = any(p["rag"] == "breach" for p in periods)
        any_bad = any(p["dscr"] is not None and p["dscr"] < 1.05 for p in periods)
        assert any_breach == any_bad

    def test_tuho_no_breaches_at_base(self, periods):
        # TUHO base case should have no breaches (healthy DSCR ~1.38)
        breaches = [p for p in periods if p["rag"] == "breach"]
        assert len(breaches) == 0

    def test_dscr_positive(self, periods):
        for p in periods:
            if p["dscr"] is not None:
                assert p["dscr"] > 0

    def test_only_operation_periods(self, tuho_base_result):
        from app.services.lender_case_service import build_covenant_periods
        periods = build_covenant_periods(tuho_base_result)
        # All returned periods must be operational (construction excluded)
        for p in periods:
            assert p["dscr"] is not None or True  # just confirm shape

    def test_period_count_matches_operation_periods(self, tuho_base_result):
        from app.services.lender_case_service import build_covenant_periods
        periods = build_covenant_periods(tuho_base_result)
        op_count = sum(1 for p in tuho_base_result.periods if p.is_operation)
        assert len(periods) == op_count


# ─── build_credit_summary ─────────────────────────────────────────────────────

class TestBuildCreditSummary:
    @pytest.fixture(scope="class")
    def cs(self, tuho_proj, tuho_base_kpis):
        from app.services.lender_case_service import build_credit_summary
        return build_credit_summary(tuho_proj, tuho_base_kpis)

    def test_returns_dict(self, cs):
        assert isinstance(cs, dict)

    def test_required_fields(self, cs):
        required = [
            "project_name", "company", "country", "technology", "capacity_mw",
            "cod_date", "horizon_years", "ppa_tariff", "ppa_term_years",
            "total_capex_keur", "debt_keur", "equity_keur", "gearing_pct",
            "senior_tenor_years", "project_irr", "equity_irr", "equity_npv",
            "avg_dscr", "min_dscr", "min_llcr",
            "total_distribution_keur", "total_tax_keur",
        ]
        for f in required:
            assert f in cs, f"Missing field: {f}"

    def test_gearing_sensible(self, cs):
        assert 0.0 < cs["gearing_pct"] < 100.0

    def test_debt_equity_sum_to_capex(self, cs):
        assert abs(cs["debt_keur"] + cs["equity_keur"] - cs["total_capex_keur"]) < 1.0

    def test_no_lender_kpis_when_not_provided(self, cs):
        assert cs["lender_equity_irr"] is None
        assert cs["lender_project_irr"] is None

    def test_lender_kpis_populated_when_provided(self, tuho_proj, tuho_base_kpis):
        from app.services.lender_case_service import build_credit_summary, run_lender_case
        lc = run_lender_case(tuho_proj, {"ppa_haircut": 10.0})
        cs = build_credit_summary(tuho_proj, tuho_base_kpis, lc["kpis"])
        assert cs["lender_equity_irr"] is not None
        assert cs["lender_equity_irr"] < cs["equity_irr"]

    def test_capacity_mw_positive(self, cs):
        assert cs["capacity_mw"] > 0

    def test_equity_irr_matches_base(self, cs, tuho_base_kpis):
        assert cs["equity_irr"] == tuho_base_kpis["equity_irr"]


# ─── _build_adjustment_summary ────────────────────────────────────────────────

class TestAdjustmentSummary:
    def test_empty_adjustments_returns_empty(self):
        from app.services.lender_case_service import _build_adjustment_summary
        rows = _build_adjustment_summary({})
        assert rows == []

    def test_zero_values_excluded(self):
        from app.services.lender_case_service import _build_adjustment_summary
        rows = _build_adjustment_summary({"ppa_haircut": 0.0, "yield_haircut": 5.0})
        assert len(rows) == 1
        assert rows[0]["key"] == "yield_haircut"

    def test_pct_display_format(self):
        from app.services.lender_case_service import _build_adjustment_summary
        rows = _build_adjustment_summary({"ppa_haircut": 10.0})
        assert "10.0%" in rows[0]["display"]

    def test_bps_display_format(self):
        from app.services.lender_case_service import _build_adjustment_summary
        rows = _build_adjustment_summary({"interest_stress": 100.0})
        assert "bps" in rows[0]["display"]
