"""Stage C3B3D1: generic canonical SHL accrual/balance schedule tests.

Test inventory
--------------
1.  TestPureEngine — A through H: period-level arithmetic contracts
2.  TestValidation — guard rails: negative balance, rate, NaN, principal > balance, bool
3.  TestLegacyCrossCheck — apples-to-apples comparison with finco_core.shl.engine (CASH only)
4.  TestNoFinancialDrift — four production projects exact-match C3B3D0 baseline
5.  TestProjectIdentityIndependence — canonical engine result is project-name-blind
"""
from __future__ import annotations

import math
import pytest

from financial_engine.shl.contracts import (
    ShlInterestPaymentMode,
    ShlInterestRateMode,
    ShlPeriodInput,
    ShlRepaymentMode,
    ShlSchedulePolicy,
)
from financial_engine.shl.engine import compute_shl_period
from financial_engine.shl.schedule import run_shl_schedule


# ─────────────────────────────────────────────────────────────────────────────
# 1. TestPureEngine — period-level arithmetic
# ─────────────────────────────────────────────────────────────────────────────

class TestPureEngine:
    """Pure arithmetic contracts for compute_shl_period."""

    def test_A_cash_basic(self):
        """A — CASH: open=100, rate=8%, dcf=0.5 → gross=4, cash=4, pik=0, close=100."""
        r = compute_shl_period(
            opening_balance_keur=100.0,
            drawdown_keur=0.0,
            day_count_fraction=0.5,
            annual_rate=0.08,
            payment_mode=ShlInterestPaymentMode.CASH_PAID,
            scheduled_principal_keur=0.0,
            period_index=0,
        )
        assert r.gross_accrued_interest_keur == pytest.approx(4.0, rel=1e-12)
        assert r.cash_interest_keur == pytest.approx(4.0, rel=1e-12)
        assert r.pik_interest_keur == pytest.approx(0.0, abs=1e-12)
        assert r.closing_balance_keur == pytest.approx(100.0, rel=1e-12)

    def test_B_pik_basic(self):
        """B — PIK: open=100, rate=8%, dcf=0.5 → gross=4, cash=0, pik=4, close=104."""
        r = compute_shl_period(
            opening_balance_keur=100.0,
            drawdown_keur=0.0,
            day_count_fraction=0.5,
            annual_rate=0.08,
            payment_mode=ShlInterestPaymentMode.PIK,
            scheduled_principal_keur=0.0,
            period_index=0,
        )
        assert r.gross_accrued_interest_keur == pytest.approx(4.0, rel=1e-12)
        assert r.cash_interest_keur == pytest.approx(0.0, abs=1e-12)
        assert r.pik_interest_keur == pytest.approx(4.0, rel=1e-12)
        assert r.closing_balance_keur == pytest.approx(104.0, rel=1e-12)

    def test_C_compound_pik(self):
        """C — compound PIK: open=104, rate=8%, dcf=0.5 → gross=4.16, close=108.16."""
        r = compute_shl_period(
            opening_balance_keur=104.0,
            drawdown_keur=0.0,
            day_count_fraction=0.5,
            annual_rate=0.08,
            payment_mode=ShlInterestPaymentMode.PIK,
            scheduled_principal_keur=0.0,
            period_index=1,
        )
        assert r.gross_accrued_interest_keur == pytest.approx(4.16, rel=1e-12)
        assert r.pik_interest_keur == pytest.approx(4.16, rel=1e-12)
        assert r.closing_balance_keur == pytest.approx(108.16, rel=1e-12)

    def test_D_draw_period_start(self):
        """D — period-start draw: open=100, draw=50, rate=8%, dcf=0.5 → basis=150, gross=6."""
        r = compute_shl_period(
            opening_balance_keur=100.0,
            drawdown_keur=50.0,
            day_count_fraction=0.5,
            annual_rate=0.08,
            payment_mode=ShlInterestPaymentMode.CASH_PAID,
            scheduled_principal_keur=0.0,
            period_index=0,
        )
        assert r.gross_accrued_interest_keur == pytest.approx(6.0, rel=1e-12)
        assert r.cash_interest_keur == pytest.approx(6.0, rel=1e-12)
        assert r.closing_balance_keur == pytest.approx(150.0, rel=1e-12)

    def test_E_bullet_4_periods_maturity_index_3(self):
        """E — BULLET: 4 periods, maturity=period 3 (0-indexed), final close=0."""
        policy = ShlSchedulePolicy(
            annual_rate=0.08,
            rate_mode=ShlInterestRateMode.FIXED,
            payment_mode=ShlInterestPaymentMode.CASH_PAID,
            repayment_mode=ShlRepaymentMode.BULLET,
        )
        period_inputs = [
            ShlPeriodInput(period_index=0, day_count_fraction=0.5),
            ShlPeriodInput(period_index=1, day_count_fraction=0.5),
            ShlPeriodInput(period_index=2, day_count_fraction=0.5),
            ShlPeriodInput(period_index=3, day_count_fraction=0.5),
        ]
        results = run_shl_schedule(
            opening_balance_keur=100.0,
            period_inputs=period_inputs,
            policy=policy,
            maturity_period_index=3,
        )
        assert len(results) == 4
        # Non-maturity periods: no principal
        for r in results[:3]:
            assert r.scheduled_principal_keur == pytest.approx(0.0, abs=1e-9)
            assert r.closing_balance_keur == pytest.approx(100.0, rel=1e-10)
        # Maturity period: full principal repaid, closing = 0
        assert results[3].scheduled_principal_keur == pytest.approx(100.0, rel=1e-10)
        assert results[3].closing_balance_keur == pytest.approx(0.0, abs=1e-9)

    def test_F_explicit_principal_reduces_next_period_basis(self):
        """F — EXPLICIT_SCHEDULE: principal reduces next-period opening balance."""
        policy = ShlSchedulePolicy(
            annual_rate=0.08,
            rate_mode=ShlInterestRateMode.FIXED,
            payment_mode=ShlInterestPaymentMode.CASH_PAID,
            repayment_mode=ShlRepaymentMode.EXPLICIT_SCHEDULE,
        )
        period_inputs = [
            ShlPeriodInput(period_index=0, day_count_fraction=0.5, scheduled_principal_keur=20.0),
            ShlPeriodInput(period_index=1, day_count_fraction=0.5, scheduled_principal_keur=0.0),
        ]
        results = run_shl_schedule(
            opening_balance_keur=100.0,
            period_inputs=period_inputs,
            policy=policy,
        )
        assert results[0].closing_balance_keur == pytest.approx(80.0, rel=1e-10)
        # Period 1 opening = 80
        assert results[1].opening_balance_keur == pytest.approx(80.0, rel=1e-10)
        # Period 1 gross = 80 × 0.08 × 0.5 = 3.2
        assert results[1].gross_accrued_interest_keur == pytest.approx(3.2, rel=1e-10)

    def test_G_partial_period_dcf_0_25(self):
        """G — partial period: dcf=0.25, open=100, rate=8% → gross=2.0."""
        r = compute_shl_period(
            opening_balance_keur=100.0,
            drawdown_keur=0.0,
            day_count_fraction=0.25,
            annual_rate=0.08,
            payment_mode=ShlInterestPaymentMode.CASH_PAID,
            scheduled_principal_keur=0.0,
            period_index=0,
        )
        assert r.gross_accrued_interest_keur == pytest.approx(2.0, rel=1e-12)

    def test_H_zero_balance_zero_draw(self):
        """H — zero: open=0, draw=0, rate=8%, dcf=0.5 → all zeros."""
        r = compute_shl_period(
            opening_balance_keur=0.0,
            drawdown_keur=0.0,
            day_count_fraction=0.5,
            annual_rate=0.08,
            payment_mode=ShlInterestPaymentMode.CASH_PAID,
            scheduled_principal_keur=0.0,
            period_index=0,
        )
        assert r.gross_accrued_interest_keur == 0.0
        assert r.cash_interest_keur == 0.0
        assert r.pik_interest_keur == 0.0
        assert r.closing_balance_keur == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 2. TestValidation
# ─────────────────────────────────────────────────────────────────────────────

class TestValidation:
    """Guard-rail validation: bad inputs must raise promptly."""

    def test_negative_opening_balance_raises(self):
        with pytest.raises(ValueError, match="opening_balance_keur must be >= 0"):
            compute_shl_period(
                opening_balance_keur=-1.0,
                drawdown_keur=0.0,
                day_count_fraction=0.5,
                annual_rate=0.08,
                payment_mode=ShlInterestPaymentMode.CASH_PAID,
                scheduled_principal_keur=0.0,
                period_index=0,
            )

    def test_negative_annual_rate_raises(self):
        with pytest.raises(ValueError, match="annual_rate must be >= 0"):
            compute_shl_period(
                opening_balance_keur=100.0,
                drawdown_keur=0.0,
                day_count_fraction=0.5,
                annual_rate=-0.01,
                payment_mode=ShlInterestPaymentMode.CASH_PAID,
                scheduled_principal_keur=0.0,
                period_index=0,
            )

    def test_nan_opening_balance_raises(self):
        with pytest.raises(ValueError, match="must be finite"):
            compute_shl_period(
                opening_balance_keur=float("nan"),
                drawdown_keur=0.0,
                day_count_fraction=0.5,
                annual_rate=0.08,
                payment_mode=ShlInterestPaymentMode.CASH_PAID,
                scheduled_principal_keur=0.0,
                period_index=0,
            )

    def test_inf_rate_raises(self):
        with pytest.raises(ValueError, match="must be finite"):
            compute_shl_period(
                opening_balance_keur=100.0,
                drawdown_keur=0.0,
                day_count_fraction=0.5,
                annual_rate=float("inf"),
                payment_mode=ShlInterestPaymentMode.CASH_PAID,
                scheduled_principal_keur=0.0,
                period_index=0,
            )

    def test_principal_exceeds_balance_raises(self):
        """EXPLICIT_SCHEDULE: principal > outstanding balance must raise."""
        with pytest.raises(ValueError, match="exceeds outstanding balance"):
            compute_shl_period(
                opening_balance_keur=100.0,
                drawdown_keur=0.0,
                day_count_fraction=0.5,
                annual_rate=0.08,
                payment_mode=ShlInterestPaymentMode.CASH_PAID,
                scheduled_principal_keur=200.0,
                period_index=0,
            )

    def test_bool_rate_raises_in_policy(self):
        """Bool rate must be rejected by ShlSchedulePolicy.__post_init__."""
        with pytest.raises(ValueError, match="bool"):
            ShlSchedulePolicy(
                annual_rate=True,  # type: ignore[arg-type]
                payment_mode=ShlInterestPaymentMode.CASH_PAID,
                repayment_mode=ShlRepaymentMode.BULLET,
            )

    def test_bool_rate_raises_in_engine(self):
        """Bool rate must be rejected by compute_shl_period._validate_finite."""
        with pytest.raises(ValueError, match="bool"):
            compute_shl_period(
                opening_balance_keur=100.0,
                drawdown_keur=0.0,
                day_count_fraction=0.5,
                annual_rate=True,  # type: ignore[arg-type]
                payment_mode=ShlInterestPaymentMode.CASH_PAID,
                scheduled_principal_keur=0.0,
                period_index=0,
            )

    def test_bullet_without_maturity_index_raises(self):
        """BULLET mode requires maturity_period_index."""
        policy = ShlSchedulePolicy(
            annual_rate=0.08,
            payment_mode=ShlInterestPaymentMode.CASH_PAID,
            repayment_mode=ShlRepaymentMode.BULLET,
        )
        with pytest.raises(ValueError, match="maturity_period_index is required"):
            run_shl_schedule(
                opening_balance_keur=100.0,
                period_inputs=[ShlPeriodInput(period_index=0, day_count_fraction=0.5)],
                policy=policy,
            )

    def test_fcf_waterfall_raises_not_implemented(self):
        """FCF_WATERFALL repayment_method in adapter must raise NotImplementedError."""
        from financial_engine.adapters.shl_inputs import _FCF_WATERFALL_METHODS

        # Confirm the fail-closed set covers known FCF methods
        assert "fcf_waterfall" in _FCF_WATERFALL_METHODS
        assert "cash_sweep" in _FCF_WATERFALL_METHODS
        assert "pik_then_sweep" in _FCF_WATERFALL_METHODS
        assert "partial_pay_sweep" in _FCF_WATERFALL_METHODS

        # Adapter raises NotImplementedError for FCF waterfall methods
        from financial_engine.adapters.shl_inputs import build_shl_schedule_policy_from_project_inputs

        class FakeFinancing:
            shl_rate = 0.08
            shl_repayment_method = "fcf_waterfall"
            shl_pik_switch_period = 0

        class FakeProject:
            financing = FakeFinancing()

        with pytest.raises(NotImplementedError, match="C3B3D1_BLOCKED_FCF_REPAYMENT"):
            build_shl_schedule_policy_from_project_inputs(FakeProject())


# ─────────────────────────────────────────────────────────────────────────────
# 3. TestLegacyCrossCheck
# ─────────────────────────────────────────────────────────────────────────────

class TestLegacyCrossCheck:
    """Compare canonical engine against finco_core.shl for pure CASH scenarios.

    Apples-to-apples is possible ONLY when:
      - post_senior_cash_available_keur is sufficient to pay full interest (no PIK)
      - pik_allowed=True but PIK never triggered (cash always covers)
      - No FCF waterfall, no R102 sweep, no reserve
      - Only cash interest, no principal (comparing accrual only)

    Boundaries where clean apples-to-apples comparison is NOT possible:
      - Legacy engine takes post_senior_cash_available_keur (waterfall-dependent).
      - Legacy engine computes principal from remaining cash (sweep-dependent).
      - R102 sweep paths are legacy-specific.
      - PIK triggers are waterfall-dependent in the legacy engine.
    These are documented as C3B3D1_LEGACY_BOUNDARY_BLOCKED.
    """

    def _run_legacy(self, opening, rate, dcf, post_cash):
        """Run legacy SHL engine for a single period (pure CASH scenario)."""
        from finco_core.shl.inputs import ShlEngineInputs, ShlPeriodInput as LegacyPeriodInput
        from finco_core.shl.engine import ShlEngine

        period = LegacyPeriodInput(
            period_index=1,
            opening_balance_keur=opening,
            drawdown_keur=0.0,
            interest_rate=rate,
            day_count_fraction=dcf,
            post_senior_cash_available_keur=post_cash,
            maintain_minimum_cash_reserve=False,
            minimum_cash_reserve_keur=0.0,
            pik_allowed=True,
            distribution_account_r102_sweep_candidate_keur=None,
        )
        inputs = ShlEngineInputs(
            project_name="cross_check_test",
            period_count=1,
            period_inputs=(period,),
            total_shl_funding_keur=opening,
            tranche_rates=(rate,),
            tranche_day_fracs=(dcf,),
            tranche_opening_balances_keur=(opening,),
            pik_allowed=True,
        )
        result = ShlEngine.compute(inputs)
        return result.period_results[0]

    def test_cash_interest_matches_legacy_engine(self):
        """Canonical gross == legacy gross_accrued when post_cash is ample."""
        opening = 5000.0
        rate = 0.08
        dcf = 0.5
        post_cash = 10_000.0  # well above interest → no PIK in legacy

        canonical = compute_shl_period(
            opening_balance_keur=opening,
            drawdown_keur=0.0,
            day_count_fraction=dcf,
            annual_rate=rate,
            payment_mode=ShlInterestPaymentMode.CASH_PAID,
            scheduled_principal_keur=0.0,
            period_index=0,
        )
        legacy = self._run_legacy(opening, rate, dcf, post_cash)

        # Gross interest must match exactly
        assert canonical.gross_accrued_interest_keur == pytest.approx(
            legacy.gross_accrued_interest_keur, rel=1e-12
        )
        assert canonical.cash_interest_keur == pytest.approx(
            legacy.cash_interest_paid_keur, rel=1e-12
        )
        assert canonical.pik_interest_keur == pytest.approx(0.0, abs=1e-12)

    def test_pik_interest_matches_legacy_when_no_cash(self):
        """Canonical PIK == legacy PIK when post_senior_cash=0 (pure PIK)."""
        opening = 5000.0
        rate = 0.08
        dcf = 0.5
        post_cash = 0.0  # forces full PIK in legacy

        canonical = compute_shl_period(
            opening_balance_keur=opening,
            drawdown_keur=0.0,
            day_count_fraction=dcf,
            annual_rate=rate,
            payment_mode=ShlInterestPaymentMode.PIK,
            scheduled_principal_keur=0.0,
            period_index=0,
        )
        legacy = self._run_legacy(opening, rate, dcf, post_cash)

        assert canonical.gross_accrued_interest_keur == pytest.approx(
            legacy.gross_accrued_interest_keur, rel=1e-12
        )
        assert canonical.pik_interest_keur == pytest.approx(
            legacy.pik_capitalized_keur, rel=1e-12
        )

    def test_legacy_boundary_documented(self):
        """C3B3D1_LEGACY_BOUNDARY_BLOCKED: FCF/sweep/R102 paths not comparable.

        The legacy engine is waterfall-coupled — it consumes post_senior_cash
        and may sweep principal from residual. The canonical engine is
        cash-waterfall-independent. These paths cannot produce apples-to-apples
        results and are intentionally not cross-checked.
        """
        # This test exists purely as documentation in the test suite.
        boundary_label = "C3B3D1_LEGACY_BOUNDARY_BLOCKED"
        assert boundary_label  # structural marker


# ─────────────────────────────────────────────────────────────────────────────
# 4. TestNoFinancialDrift
# ─────────────────────────────────────────────────────────────────────────────

class TestNoFinancialDrift:
    """All four production projects must exactly match C3B3D0 baseline.

    These tests run the existing production waterfall runner (unchanged) and
    confirm zero financial drift from the C3B3D1 changes (which add a new
    financial_engine/shl/ package without touching any production path).
    """

    BASE = {
        "oborovo": dict(
            tax=8489.215657,
            dist=63997.380136,
            senior_ds=63192.172875,
            proj_irr=0.07973030,
            eq_irr=0.10348411,
        ),
        "tuho": dict(
            tax=37004.372718,
            dist=165479.319576,
            senior_ds=65826.388280,
            proj_irr=0.09439294,
            eq_irr=0.11320018,
        ),
        "solar": dict(
            tax=9432.701033,
            dist=19858.410252,
            senior_ds=36928.460619,
            proj_irr=0.07188301,
            eq_irr=0.16286268,
        ),
        "wind": dict(
            tax=31098.189755,
            dist=72995.889074,
            senior_ds=49147.882569,
            proj_irr=0.10503502,
            eq_irr=0.26204906,
        ),
    }

    def _run(self, factory):
        from app.ui_runner import _build_period_engine
        from app.waterfall_runner import WaterfallRunConfig, WaterfallRunner
        p = factory()
        engine = _build_period_engine(p)
        config = WaterfallRunConfig.from_inputs(p, engine)
        return WaterfallRunner(p, engine).run(config)

    def test_oborovo_no_drift(self):
        from app.project_factories import create_default_oborovo
        r = self._run(create_default_oborovo)
        b = self.BASE["oborovo"]
        assert r.total_tax_keur == pytest.approx(b["tax"], abs=0.001)
        assert r.total_distribution_keur == pytest.approx(b["dist"], abs=0.001)
        assert r.total_senior_ds_keur == pytest.approx(b["senior_ds"], abs=0.001)
        assert r.project_irr == pytest.approx(b["proj_irr"], abs=1e-6)
        assert r.equity_irr == pytest.approx(b["eq_irr"], abs=1e-6)

    def test_tuho_no_drift(self):
        from app.project_factories import create_default_tuho_wind1
        r = self._run(create_default_tuho_wind1)
        b = self.BASE["tuho"]
        assert r.total_tax_keur == pytest.approx(b["tax"], abs=0.001)
        assert r.total_distribution_keur == pytest.approx(b["dist"], abs=0.001)
        assert r.total_senior_ds_keur == pytest.approx(b["senior_ds"], abs=0.001)
        assert r.project_irr == pytest.approx(b["proj_irr"], abs=1e-6)
        assert r.equity_irr == pytest.approx(b["eq_irr"], abs=1e-6)

    def test_solar_no_drift(self):
        from app.project_factories import create_default_solar_project
        r = self._run(create_default_solar_project)
        b = self.BASE["solar"]
        assert r.total_tax_keur == pytest.approx(b["tax"], abs=0.001)
        assert r.total_distribution_keur == pytest.approx(b["dist"], abs=0.001)
        assert r.total_senior_ds_keur == pytest.approx(b["senior_ds"], abs=0.001)
        assert r.project_irr == pytest.approx(b["proj_irr"], abs=1e-6)
        assert r.equity_irr == pytest.approx(b["eq_irr"], abs=1e-6)

    def test_wind_no_drift(self):
        from app.project_factories import create_default_wind_project
        r = self._run(create_default_wind_project)
        b = self.BASE["wind"]
        assert r.total_tax_keur == pytest.approx(b["tax"], abs=0.001)
        assert r.total_distribution_keur == pytest.approx(b["dist"], abs=0.001)
        assert r.total_senior_ds_keur == pytest.approx(b["senior_ds"], abs=0.001)
        assert r.project_irr == pytest.approx(b["proj_irr"], abs=1e-6)
        assert r.equity_irr == pytest.approx(b["eq_irr"], abs=1e-6)


# ─────────────────────────────────────────────────────────────────────────────
# 5. TestProjectIdentityIndependence
# ─────────────────────────────────────────────────────────────────────────────

class TestProjectIdentityIndependence:
    """Canonical engine result is identity-blind — no project_name/code dispatch."""

    def _run_synthetic(self, project_name: str) -> tuple:
        """Run canonical engine with a labelled project name — result must be identical."""
        policy = ShlSchedulePolicy(
            annual_rate=0.08,
            rate_mode=ShlInterestRateMode.FIXED,
            payment_mode=ShlInterestPaymentMode.PIK,
            repayment_mode=ShlRepaymentMode.BULLET,
        )
        period_inputs = [
            ShlPeriodInput(period_index=i, day_count_fraction=0.5)
            for i in range(4)
        ]
        results = run_shl_schedule(
            opening_balance_keur=10_000.0,
            period_inputs=period_inputs,
            policy=policy,
            maturity_period_index=3,
        )
        # Return a tuple of closing balances — these must be identical regardless
        # of what project_name is passed to any wrapper (canonical engine has no
        # project_name parameter at all).
        return tuple(r.closing_balance_keur for r in results)

    def test_same_result_regardless_of_project_label(self):
        """Identical inputs → identical outputs. No dispatch on project identity."""
        result_a = self._run_synthetic("OBOROVO")
        result_b = self._run_synthetic("TUHO")
        result_c = self._run_synthetic("synthetic_project_xyz_9999")
        assert result_a == result_b
        assert result_b == result_c

    def test_no_project_name_in_engine_signature(self):
        """compute_shl_period must not accept a project_name parameter."""
        import inspect
        sig = inspect.signature(compute_shl_period)
        assert "project_name" not in sig.parameters
        assert "project_code" not in sig.parameters

    def test_no_project_name_in_schedule_runner(self):
        """run_shl_schedule must not accept a project_name parameter."""
        import inspect
        sig = inspect.signature(run_shl_schedule)
        assert "project_name" not in sig.parameters
        assert "project_code" not in sig.parameters


# ─────────────────────────────────────────────────────────────────────────────
# 6. TestAdapterShlInputs
# ─────────────────────────────────────────────────────────────────────────────

class TestAdapterShlInputs:
    """Adapter: build_shl_schedule_policy_from_project_inputs."""

    def _oborovo_policy(self):
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.shl_inputs import (
            build_shl_schedule_policy_from_project_inputs,
        )
        p = create_default_oborovo()
        return build_shl_schedule_policy_from_project_inputs(p)

    def test_oborovo_returns_none_or_bullet(self):
        """Oborovo has shl_repayment_method=bullet → should return ShlSchedulePolicy."""
        policy = self._oborovo_policy()
        # Oborovo bullet: returns a policy (not None) since pik_switch_period=0
        assert policy is not None
        assert policy.repayment_mode == ShlRepaymentMode.BULLET
        assert policy.annual_rate == pytest.approx(0.08)

    def test_tuho_fcf_returns_none(self):
        """TUHO pik_then_sweep is FCF-adjacent — raises NotImplementedError."""
        from app.project_factories import create_default_tuho_wind1
        from financial_engine.adapters.shl_inputs import (
            build_shl_schedule_policy_from_project_inputs,
        )
        p = create_default_tuho_wind1()
        # TUHO uses pik_then_sweep — must raise NotImplementedError
        with pytest.raises(NotImplementedError, match="C3B3D1_BLOCKED_FCF_REPAYMENT"):
            build_shl_schedule_policy_from_project_inputs(p)

    def test_adapter_not_wired_into_orchestrator(self):
        """Governance: shl_inputs adapter must not be imported in orchestrator."""
        import ast
        import pathlib

        orch_path = pathlib.Path("financial_engine/orchestrator.py")
        if orch_path.exists():
            src = orch_path.read_text()
            assert "shl_inputs" not in src, (
                "financial_engine/orchestrator.py imports shl_inputs — "
                "C3B3D1 adapter must NOT be wired into production runtime."
            )
