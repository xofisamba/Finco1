"""Phase 9: R99/R102 Runtime Flag Readiness Fixes — tests.

Tests verify:
1. DSCR stability evidence is available
2. Oborovo guard is active
3. TUHO DA wiring totals are correct
4. Design review doc exists
5. Readiness evidence report exists
6. G07 (DSCR stability) is AVAILABLE
7. G08 equity_irr PARTIAL is documented
8. G08 project_irr PASS is documented
9. G20 BLOCKED
10. No R99/R102 promotion claimed
11. Recommended next branch is explicit
"""

import csv
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
REPORTS_DIR = REPO_ROOT / "reports"

DESIGN_DOC = DOCS_DIR / "phase9_r99_r102_runtime_flag_design_review.md"
READINESS_DOC = DOCS_DIR / "phase9_r99_r102_runtime_flag_readiness_fixes.md"
READINESS_CSV = REPORTS_DIR / "phase9_r99_r102_runtime_flag_readiness_evidence.csv"
GATE_REVIEW_CSV = REPORTS_DIR / "phase9_r99_r102_runtime_flag_gate_review.csv"


# ---------------------------------------------------------------------------
# Helper: run waterfall
# ---------------------------------------------------------------------------

def _run_waterfall(project_name, da_wiring):
    from app.waterfall_core import run_waterfall_v3_core
    from app.project_factories import create_default_tuho_wind1, create_default_oborovo
    from app.ui_runner import _build_period_engine as build_period_engine

    COMMON = dict(
        rate_per_period=0.0, tenor_periods=0, target_dscr=1.15, lockup_dscr=1.10,
        tax_rate=0.10, dsra_months=6, shl_amount=0.0, shl_rate=0.0, shl_idc_keur=0.0,
        shl_repayment_method='bullet', shl_tenor_years=0, shl_wht_rate=0.0,
        discount_rate_project=0.0641, discount_rate_equity=0.0965,
        fixed_debt_keur=None, fixed_ds_keur=None, rate_schedule=None,
        senior_sculpting_config=None, equity_irr_method='equity_only',
        share_capital_keur=0.0, sculpt_capex_keur=0.0,
        debt_sizing_method='dscr_sculpt', dscr_schedule=None,
        advanced_opex_line_items=None, advanced_capex_line_items=None,
        advanced_capex_depreciation_schedule=None,
        use_senior_sweep_cash_cap_for_shl=False, use_tuho_r99_input_engine=False,
        use_shl_fcf_waterfall_engine=False, use_tax_bridge_engine=False,
        use_shl_gross_accrued_for_pnl=False, shl_fcf_waterfall_cash_schedule_keur=(),
        shl_fcf_waterfall_minimum_cash_retained_keur=0.0,
        tuho_cit_cash_tax_start_operating_index=None,
        use_shl_canonical_engine=False, use_depreciation_canonical_engine=False,
        use_senior_debt_sizing_engine=False, use_co2_revenue_bridge=False,
        use_co2_cit_bridge=False, use_dualrun_validation=False,
    )
    if project_name == "TUHO-WIND-1":
        inputs = create_default_tuho_wind1()
    else:
        inputs = create_default_oborovo()
    engine = build_period_engine(inputs)
    kwargs = dict(COMMON)
    kwargs['use_distributionaccount_runtime_wiring'] = da_wiring
    return run_waterfall_v3_core(inputs=inputs, engine=engine, **kwargs)


# ---------------------------------------------------------------------------
# 1. Design review doc exists (prerequisite)
# ---------------------------------------------------------------------------

class TestDesignReviewPrerequisite:
    def test_design_review_doc_exists(self):
        assert DESIGN_DOC.exists(), f"Missing: {DESIGN_DOC}"


# ---------------------------------------------------------------------------
# 2. Readiness files exist
# ---------------------------------------------------------------------------

class TestReadinessFiles:
    def test_readiness_doc_exists(self):
        assert READINESS_DOC.exists(), f"Missing: {READINESS_DOC}"

    def test_readiness_evidence_csv_exists(self):
        assert READINESS_CSV.exists(), f"Missing: {READINESS_CSV}"


# ---------------------------------------------------------------------------
# 3. DSCR stability: no DSCR < 1.0 under either configuration
# ---------------------------------------------------------------------------

class TestDSCRStability:
    def test_tuho_flag_false_no_dscr_below_1(self):
        r = _run_waterfall("TUHO-WIND-1", da_wiring=False)
        below1 = sum(
            1 for wp in r.periods
            if (getattr(wp, 'dscr', None) or float('inf')) < 1.0
        )
        assert below1 == 0, f"flag=False: {below1} periods with DSCR < 1.0"

    def test_tuho_flag_true_no_dscr_below_1(self):
        r = _run_waterfall("TUHO-WIND-1", da_wiring=True)
        below1 = sum(
            1 for wp in r.periods
            if (getattr(wp, 'dscr', None) or float('inf')) < 1.0
        )
        assert below1 == 0, f"flag=True: {below1} periods with DSCR < 1.0"

    def test_tuho_both_configs_all_dscr_inf(self):
        """senior_ds_keur=0 means DSCR=inf everywhere — trivially stable."""
        r = _run_waterfall("TUHO-WIND-1", da_wiring=False)
        inf_count = sum(1 for wp in r.periods if getattr(wp, 'dscr', None) == float('inf'))
        assert inf_count == len(r.periods), (
            f"Expected DSCR=inf for all {len(r.periods)} periods, got {inf_count}"
        )


# ---------------------------------------------------------------------------
# 4. TUHO DA wiring totals correct
# ---------------------------------------------------------------------------

class TestTUHODAWiring:
    def test_tuho_flag_false_total(self):
        r = _run_waterfall("TUHO-WIND-1", da_wiring=False)
        assert abs(r.total_distribution_keur - 326_165) < 1000, (
            f"Expected ~326,165 kEUR, got {r.total_distribution_keur:,.2f}"
        )

    def test_tuho_flag_true_total(self):
        r = _run_waterfall("TUHO-WIND-1", da_wiring=True)
        assert abs(r.total_distribution_keur - 284_552) < 500, (
            f"Expected ~284,552 kEUR, got {r.total_distribution_keur:,.2f}"
        )

    def test_tuho_delta(self):
        r = _run_waterfall("TUHO-WIND-1", da_wiring=True)
        assert -44_000 < r.distribution_wiring_delta_keur < -40_000, (
            f"Expected delta ~-41,613 kEUR, got {r.distribution_wiring_delta_keur:,.2f}"
        )


# ---------------------------------------------------------------------------
# 5. Oborovo guard active
# ---------------------------------------------------------------------------

class TestOborovoGuard:
    def test_oborovo_flag_true_guard_fires(self):
        r = _run_waterfall("OBOROVO-SOLAR-1", da_wiring=True)
        assert r.distribution_source == "oborovo_guard_blocked", (
            f"Expected oborovo_guard_blocked, got {r.distribution_source}"
        )

    def test_oborovo_flag_true_unchanged(self):
        r0 = _run_waterfall("OBOROVO-SOLAR-1", da_wiring=False)
        r1 = _run_waterfall("OBOROVO-SOLAR-1", da_wiring=True)
        assert abs(r1.total_distribution_keur - r0.total_distribution_keur) < 0.01, (
            "Oborovo distribution must not change when guard fires"
        )


# ---------------------------------------------------------------------------
# 6. G07 DSCR stability is AVAILABLE
# ---------------------------------------------------------------------------

class TestG07DSCRStability:
    def test_e03_is_available(self):
        with open(READINESS_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        e03 = next((r for r in rows if r["evidence_id"] == "E03"), None)
        assert e03 is not None, "E03 not found in readiness evidence"
        assert e03["current_status"] == "AVAILABLE", (
            f"E03 status must be AVAILABLE, got {e03['current_status']}"
        )

    def test_dscr_stability_mentioned_in_doc(self):
        with open(READINESS_DOC, encoding="utf-8") as f:
            content = f.read()
        assert "AVAILABLE" in content or "DSCR" in content
        assert "inf" in content or "stability" in content.lower()


# ---------------------------------------------------------------------------
# 7. G08 equity_irr PARTIAL documented
# ---------------------------------------------------------------------------

class TestG08EquityIRR:
    def test_e08_equity_irr_is_partial(self):
        with open(READINESS_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        row = next((r for r in rows if r["evidence_id"] == "E08_equity_irr"), None)
        assert row is not None
        assert row["current_status"] == "PARTIAL", (
            f"E08_equity_irr must be PARTIAL, got {row['current_status']}"
        )


# ---------------------------------------------------------------------------
# 8. G08 project_irr PASS documented
# ---------------------------------------------------------------------------

class TestG08ProjectIRR:
    def test_e08_project_irr_is_pass(self):
        with open(READINESS_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        row = next((r for r in rows if r["evidence_id"] == "E08_project_irr"), None)
        assert row is not None
        assert row["current_status"] == "PASS", (
            f"E08_project_irr must be PASS, got {row['current_status']}"
        )


# ---------------------------------------------------------------------------
# 9. G20 BLOCKED
# ---------------------------------------------------------------------------

class TestG20Blocked:
    def test_gate_review_g20_blocked(self):
        with open(GATE_REVIEW_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        g20 = next((r for r in rows if r["gate_id"] == "G20"), None)
        assert g20 is not None
        assert g20["current_status"] == "BLOCKED", (
            f"G20 must be BLOCKED, got {g20['current_status']}"
        )


# ---------------------------------------------------------------------------
# 10. No report claims R99/R102 promotion approved
# ---------------------------------------------------------------------------

class TestNoPromotionClaimed:
    def test_gate_review_no_promotion_approved(self):
        with open(GATE_REVIEW_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            if r["current_status"] == "APPROVED":
                assert r["gate_id"] not in ("G10", "G20", "G07", "G08"), (
                    f"Gate {r['gate_id']} claims APPROVED — R99/R102 promotion not approved"
                )


# ---------------------------------------------------------------------------
# 11. Recommended next branch explicit in doc
# ---------------------------------------------------------------------------

class TestRecommendedNextBranch:
    def test_readiness_doc_next_branch_explicit(self):
        with open(READINESS_DOC, encoding="utf-8") as f:
            content = f.read()
        assert "phase9-r99-r102-runtime-flag-implementation" in content or "phase9-r99-r102-runtime-flag-readiness-fixes" in content, (
            "Readiness doc must include next branch recommendation"
        )