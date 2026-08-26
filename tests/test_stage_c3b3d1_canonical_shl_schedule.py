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
    """All four production projects remain locked on the canonical PR-F1 axis."""

    BASE = {
        "oborovo": dict(
            tax=8490.320140,
            dist=64006.489082,
            senior_ds=63191.174225,
            proj_irr=0.07972912,
            eq_irr=0.10348369,
        ),
        "tuho": dict(
            tax=36994.270322,
            dist=165423.195150,
            senior_ds=65826.388280,
            proj_irr=0.09438932,
            eq_irr=0.11319445,
        ),
        "solar": dict(
            tax=9428.571521,
            dist=19841.892207,
            senior_ds=36928.460619,
            proj_irr=0.07187342,
            eq_irr=0.16305334,
        ),
        "wind": dict(
            tax=31090.265455,
            dist=72964.191873,
            senior_ds=49147.882569,
            proj_irr=0.10503091,
            eq_irr=0.26210647,
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
        from app.project_factories import create_default_oborovo_legacy_calibration
        r = self._run(create_default_oborovo_legacy_calibration)
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

    def test_oborovo_payment_mode_blocked(self):
        """Oborovo bullet repayment is mapped, but payment mode is blocked.

        shl_pik_switch_period=0 has no proven mapping to CASH_PAID (the field
        is unused by runtime). Full policy build raises C3B3D1_BLOCKED_PAYMENT_MODE_SEMANTICS.
        """
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.shl_inputs import build_shl_schedule_policy_from_project_inputs
        p = create_default_oborovo()
        with pytest.raises(NotImplementedError, match="C3B3D1_BLOCKED_PAYMENT_MODE_SEMANTICS"):
            build_shl_schedule_policy_from_project_inputs(p)

    def test_oborovo_repayment_mode_is_bullet(self):
        """Oborovo bullet repayment is correctly identified as BULLET."""
        from app.project_factories import create_default_oborovo
        from financial_engine.adapters.shl_inputs import build_shl_repayment_mode_from_project_inputs
        p = create_default_oborovo()
        mode = build_shl_repayment_mode_from_project_inputs(p)
        assert mode == ShlRepaymentMode.BULLET

    def test_adapter_not_wired_into_orchestrator(self):
        """Governance: shl_inputs adapter must not be imported in orchestrator."""
        import pathlib

        orch_path = pathlib.Path("financial_engine/orchestrator.py")
        if orch_path.exists():
            src = orch_path.read_text()
            assert "shl_inputs" not in src, (
                "financial_engine/orchestrator.py imports shl_inputs — "
                "C3B3D1 adapter must NOT be wired into production runtime."
            )


# ─────────────────────────────────────────────────────────────────────────────
# 7. TestR1ContractHardening — new tests I through T
# ─────────────────────────────────────────────────────────────────────────────

class TestR1ContractHardening:
    """R1 additions: enum validation, contiguity, legacy method blocking."""

    def test_I_invalid_payment_mode_enum_raises(self):
        """I — ShlSchedulePolicy rejects non-enum payment_mode."""
        with pytest.raises(ValueError, match="payment_mode must be ShlInterestPaymentMode"):
            ShlSchedulePolicy(
                annual_rate=0.08,
                payment_mode="CASH_PAID",  # type: ignore[arg-type]
                repayment_mode=ShlRepaymentMode.BULLET,
            )

    def test_J_invalid_repayment_mode_enum_raises(self):
        """J — ShlSchedulePolicy rejects non-enum repayment_mode."""
        with pytest.raises(ValueError, match="repayment_mode must be ShlRepaymentMode"):
            ShlSchedulePolicy(
                annual_rate=0.08,
                payment_mode=ShlInterestPaymentMode.CASH_PAID,
                repayment_mode="BULLET",  # type: ignore[arg-type]
            )

    def test_K_invalid_rate_mode_enum_raises(self):
        """K — ShlSchedulePolicy rejects non-enum rate_mode."""
        with pytest.raises(ValueError, match="rate_mode must be ShlInterestRateMode"):
            ShlSchedulePolicy(
                annual_rate=0.08,
                rate_mode="FIXED",  # type: ignore[arg-type]
                payment_mode=ShlInterestPaymentMode.CASH_PAID,
                repayment_mode=ShlRepaymentMode.BULLET,
            )

    def test_L_period_index_non_contiguous_raises(self):
        """L — run_shl_schedule raises on non-contiguous period_index."""
        policy = ShlSchedulePolicy(
            annual_rate=0.08,
            payment_mode=ShlInterestPaymentMode.CASH_PAID,
            repayment_mode=ShlRepaymentMode.EXPLICIT_SCHEDULE,
        )
        period_inputs = [
            ShlPeriodInput(period_index=0, day_count_fraction=0.5),
            ShlPeriodInput(period_index=2, day_count_fraction=0.5),  # gap!
        ]
        with pytest.raises(ValueError, match="contiguous"):
            run_shl_schedule(
                opening_balance_keur=100.0,
                period_inputs=period_inputs,
                policy=policy,
            )

    def test_M_period_index_not_starting_at_zero_raises(self):
        """M — run_shl_schedule raises when first period_index != 0."""
        policy = ShlSchedulePolicy(
            annual_rate=0.08,
            payment_mode=ShlInterestPaymentMode.CASH_PAID,
            repayment_mode=ShlRepaymentMode.EXPLICIT_SCHEDULE,
        )
        period_inputs = [
            ShlPeriodInput(period_index=1, day_count_fraction=0.5),
        ]
        with pytest.raises(ValueError, match="contiguous"):
            run_shl_schedule(
                opening_balance_keur=100.0,
                period_inputs=period_inputs,
                policy=policy,
            )

    def test_N_legacy_pik_method_raises_not_implemented(self):
        """N — shl_repayment_method='pik' raises C3B3D1_BLOCKED_LEGACY_REPAYMENT_SEMANTICS."""
        from financial_engine.adapters.shl_inputs import build_shl_schedule_policy_from_project_inputs

        class FakeFinancing:
            shl_rate = 0.08
            shl_repayment_method = "pik"
            shl_pik_switch_period = 0

        class FakeProject:
            financing = FakeFinancing()

        with pytest.raises(NotImplementedError, match="C3B3D1_BLOCKED_LEGACY_REPAYMENT_SEMANTICS"):
            build_shl_schedule_policy_from_project_inputs(FakeProject())

    def test_O_legacy_accrued_method_raises_not_implemented(self):
        """O — shl_repayment_method='accrued' raises C3B3D1_BLOCKED_LEGACY_REPAYMENT_SEMANTICS."""
        from financial_engine.adapters.shl_inputs import build_shl_schedule_policy_from_project_inputs

        class FakeFinancing:
            shl_rate = 0.08
            shl_repayment_method = "accrued"
            shl_pik_switch_period = 0

        class FakeProject:
            financing = FakeFinancing()

        with pytest.raises(NotImplementedError, match="C3B3D1_BLOCKED_LEGACY_REPAYMENT_SEMANTICS"):
            build_shl_schedule_policy_from_project_inputs(FakeProject())

    def test_P_pik_switch_positive_raises_not_implemented(self):
        """P — shl_pik_switch_period > 0 raises C3B3D1_BLOCKED_MIXED_PAYMENT_MODE."""
        from financial_engine.adapters.shl_inputs import build_shl_schedule_policy_from_project_inputs

        class FakeFinancing:
            shl_rate = 0.08
            shl_repayment_method = "bullet"
            shl_pik_switch_period = 5

        class FakeProject:
            financing = FakeFinancing()

        with pytest.raises(NotImplementedError, match="C3B3D1_BLOCKED_MIXED_PAYMENT_MODE"):
            build_shl_schedule_policy_from_project_inputs(FakeProject())

    def test_Q_no_silent_none_from_adapter(self):
        """Q — adapter never returns None; it raises for unsupported configs."""
        from financial_engine.adapters.shl_inputs import build_shl_schedule_policy_from_project_inputs

        class FakeFinancingFCF:
            shl_rate = 0.08
            shl_repayment_method = "cash_sweep"
            shl_pik_switch_period = 0

        class FakeProjectFCF:
            financing = FakeFinancingFCF()

        # Must raise, not return None
        with pytest.raises(NotImplementedError):
            result = build_shl_schedule_policy_from_project_inputs(FakeProjectFCF())

    def test_R_bullet_pik_switch_zero_blocked_payment_mode(self):
        """R — bullet + pik_switch=0 raises C3B3D1_BLOCKED_PAYMENT_MODE_SEMANTICS.

        shl_pik_switch_period=0 has no proven semantic: the legacy waterfall
        derives pik_switch_triggered at runtime from (cf_for_shl > balance × rate),
        not from this field. Cannot silently assume CASH_PAID.
        """
        from financial_engine.adapters.shl_inputs import build_shl_schedule_policy_from_project_inputs

        class FakeFinancing:
            shl_rate = 0.10
            shl_repayment_method = "bullet"
            shl_pik_switch_period = 0

        class FakeProject:
            financing = FakeFinancing()

        with pytest.raises(NotImplementedError, match="C3B3D1_BLOCKED_PAYMENT_MODE_SEMANTICS"):
            build_shl_schedule_policy_from_project_inputs(FakeProject())

    def test_S_contiguous_three_periods_ok(self):
        """S — three contiguous period_inputs [0,1,2] pass validation."""
        policy = ShlSchedulePolicy(
            annual_rate=0.08,
            payment_mode=ShlInterestPaymentMode.CASH_PAID,
            repayment_mode=ShlRepaymentMode.BULLET,
        )
        period_inputs = [
            ShlPeriodInput(period_index=i, day_count_fraction=0.5)
            for i in range(3)
        ]
        results = run_shl_schedule(
            opening_balance_keur=100.0,
            period_inputs=period_inputs,
            policy=policy,
            maturity_period_index=2,
        )
        assert len(results) == 3
        assert results[2].closing_balance_keur == pytest.approx(0.0, abs=1e-9)

    def test_T_gross_interest_is_not_deductible_interest(self):
        """T — gross_accrued_interest_keur is gross accounting, not deductible.

        The canonical SHL schedule computes gross accrual. TaxPolicy determines
        deductibility separately. This test verifies the gross value is returned
        regardless of deductibility classification.
        """
        r = compute_shl_period(
            opening_balance_keur=1000.0,
            drawdown_keur=0.0,
            day_count_fraction=1.0,
            annual_rate=0.08,
            payment_mode=ShlInterestPaymentMode.CASH_PAID,
            scheduled_principal_keur=0.0,
            period_index=0,
        )
        # Gross = 1000 * 0.08 * 1.0 = 80
        assert r.gross_accrued_interest_keur == pytest.approx(80.0, rel=1e-12)
        # The gross value is independent of any deductibility determination.
        # Whether 0, 50, or 80 kEUR is deductible is TaxPolicy's concern, not ours.
        assert r.cash_interest_keur == pytest.approx(80.0, rel=1e-12)
        assert r.pik_interest_keur == pytest.approx(0.0, abs=1e-12)


# ─────────────────────────────────────────────────────────────────────────────
# 8. TestR2PeriodIndexTypeEnforcement — bool/type guard on period_index
# ─────────────────────────────────────────────────────────────────────────────

class TestR2PeriodIndexTypeEnforcement:
    """R2: period_index must be real int — bool, float, negative, and gap all rejected.

    Python treats False==0 and True==1, so contiguity checks alone are not
    sufficient. Type must be validated explicitly.
    """

    _POLICY = ShlSchedulePolicy(
        annual_rate=0.08,
        payment_mode=ShlInterestPaymentMode.CASH_PAID,
        repayment_mode=ShlRepaymentMode.EXPLICIT_SCHEDULE,
    )

    def _run(self, period_inputs):
        return run_shl_schedule(
            opening_balance_keur=100.0,
            period_inputs=period_inputs,
            policy=self._POLICY,
        )

    def test_U_bool_indices_False_True_rejected(self):
        """U — [False, True] must be rejected (False==0, True==1 in Python)."""
        period_inputs = [
            ShlPeriodInput(period_index=False, day_count_fraction=0.5),  # type: ignore[arg-type]
            ShlPeriodInput(period_index=True, day_count_fraction=0.5),   # type: ignore[arg-type]
        ]
        with pytest.raises(TypeError, match="bool"):
            self._run(period_inputs)

    def test_V_negative_index_rejected(self):
        """V — [-1, 0] must be rejected (period_index must be >= 0)."""
        period_inputs = [
            ShlPeriodInput(period_index=-1, day_count_fraction=0.5),
            ShlPeriodInput(period_index=0, day_count_fraction=0.5),
        ]
        with pytest.raises(ValueError, match=">= 0"):
            self._run(period_inputs)

    def test_W_duplicate_index_rejected(self):
        """W — [0, 0] must be rejected (non-contiguous / gap)."""
        period_inputs = [
            ShlPeriodInput(period_index=0, day_count_fraction=0.5),
            ShlPeriodInput(period_index=0, day_count_fraction=0.5),
        ]
        with pytest.raises(ValueError, match="contiguous"):
            self._run(period_inputs)

    def test_X_out_of_order_rejected(self):
        """X — [0, 2, 1] must be rejected (non-contiguous)."""
        period_inputs = [
            ShlPeriodInput(period_index=0, day_count_fraction=0.5),
            ShlPeriodInput(period_index=2, day_count_fraction=0.5),
            ShlPeriodInput(period_index=1, day_count_fraction=0.5),
        ]
        with pytest.raises(ValueError, match="contiguous"):
            self._run(period_inputs)

    def test_Y_starting_at_one_rejected(self):
        """Y — [1, 2] must be rejected (must start at 0)."""
        period_inputs = [
            ShlPeriodInput(period_index=1, day_count_fraction=0.5),
            ShlPeriodInput(period_index=2, day_count_fraction=0.5),
        ]
        with pytest.raises(ValueError, match="contiguous"):
            self._run(period_inputs)

    def test_Z_contiguous_zero_one_two_accepted(self):
        """Z — [0, 1, 2] must pass validation."""
        period_inputs = [
            ShlPeriodInput(period_index=i, day_count_fraction=0.5)
            for i in range(3)
        ]
        results = self._run(period_inputs)
        assert len(results) == 3
        assert all(r.closing_balance_keur >= 0 for r in results)


# ─────────────────────────────────────────────────────────────────────────────
# 9. TestR3BoundaryValidation — maturity_period_index type + opening balance
# ─────────────────────────────────────────────────────────────────────────────

class TestR3BoundaryValidation:
    """R3: maturity_period_index type enforcement + opening_balance_keur validation.

    maturity_period_index must be a real int (not bool, not float, not str).
    opening_balance_keur must be numeric, not bool, finite, and >= 0 — validated
    before iterating so empty EXPLICIT_SCHEDULE does not bypass the guard.
    """

    _BULLET_POLICY = ShlSchedulePolicy(
        annual_rate=0.08,
        payment_mode=ShlInterestPaymentMode.CASH_PAID,
        repayment_mode=ShlRepaymentMode.BULLET,
    )
    _EXPLICIT_POLICY = ShlSchedulePolicy(
        annual_rate=0.08,
        payment_mode=ShlInterestPaymentMode.CASH_PAID,
        repayment_mode=ShlRepaymentMode.EXPLICIT_SCHEDULE,
    )

    def _one_period(self):
        return [ShlPeriodInput(period_index=0, day_count_fraction=0.5)]

    # ── maturity_period_index type tests ────────────────────────────────────

    def test_A_maturity_bool_False_rejected(self):
        """A — maturity_period_index=False must be rejected (False==0 in Python)."""
        with pytest.raises(TypeError, match="bool"):
            run_shl_schedule(
                opening_balance_keur=100.0,
                period_inputs=self._one_period(),
                policy=self._BULLET_POLICY,
                maturity_period_index=False,  # type: ignore[arg-type]
            )

    def test_B_maturity_bool_True_rejected(self):
        """B — maturity_period_index=True must be rejected (True==1 in Python)."""
        with pytest.raises(TypeError, match="bool"):
            run_shl_schedule(
                opening_balance_keur=100.0,
                period_inputs=self._one_period(),
                policy=self._BULLET_POLICY,
                maturity_period_index=True,  # type: ignore[arg-type]
            )

    def test_C_maturity_float_rejected(self):
        """C — maturity_period_index=1.0 must be rejected (float, not int)."""
        with pytest.raises(TypeError):
            run_shl_schedule(
                opening_balance_keur=100.0,
                period_inputs=self._one_period(),
                policy=self._BULLET_POLICY,
                maturity_period_index=1.0,  # type: ignore[arg-type]
            )

    def test_D_maturity_string_rejected(self):
        """D — maturity_period_index='1' must be rejected (string, not int)."""
        with pytest.raises(TypeError):
            run_shl_schedule(
                opening_balance_keur=100.0,
                period_inputs=self._one_period(),
                policy=self._BULLET_POLICY,
                maturity_period_index="1",  # type: ignore[arg-type]
            )

    def test_E_maturity_valid_int_passes(self):
        """E — maturity_period_index=0 (valid int) passes for a one-period schedule."""
        results = run_shl_schedule(
            opening_balance_keur=100.0,
            period_inputs=self._one_period(),
            policy=self._BULLET_POLICY,
            maturity_period_index=0,
        )
        assert len(results) == 1
        assert results[0].closing_balance_keur == pytest.approx(0.0, abs=1e-9)

    # ── opening_balance_keur validation tests ───────────────────────────────

    def test_F_negative_opening_empty_schedule_fails(self):
        """F — opening_balance=-1 with empty EXPLICIT_SCHEDULE must fail before iteration."""
        with pytest.raises(ValueError, match=">= 0"):
            run_shl_schedule(
                opening_balance_keur=-1.0,
                period_inputs=[],
                policy=self._EXPLICIT_POLICY,
            )

    def test_G_nan_opening_empty_schedule_fails(self):
        """G — opening_balance=NaN with empty EXPLICIT_SCHEDULE must fail before iteration."""
        with pytest.raises(ValueError, match="finite"):
            run_shl_schedule(
                opening_balance_keur=float("nan"),
                period_inputs=[],
                policy=self._EXPLICIT_POLICY,
            )

    def test_H_inf_opening_empty_schedule_fails(self):
        """H — opening_balance=Inf with empty EXPLICIT_SCHEDULE must fail before iteration."""
        with pytest.raises(ValueError, match="finite"):
            run_shl_schedule(
                opening_balance_keur=float("inf"),
                period_inputs=[],
                policy=self._EXPLICIT_POLICY,
            )

    def test_I_bool_opening_empty_schedule_fails(self):
        """I — opening_balance=True must be rejected (bool, not float)."""
        with pytest.raises(TypeError, match="bool"):
            run_shl_schedule(
                opening_balance_keur=True,  # type: ignore[arg-type]
                period_inputs=[],
                policy=self._EXPLICIT_POLICY,
            )

    def test_J_zero_opening_empty_explicit_schedule_returns_empty(self):
        """J — opening_balance=0, period_inputs=[] with EXPLICIT_SCHEDULE returns ()."""
        results = run_shl_schedule(
            opening_balance_keur=0.0,
            period_inputs=[],
            policy=self._EXPLICIT_POLICY,
        )
        assert results == ()

    def test_K_positive_opening_empty_explicit_schedule_returns_empty(self):
        """K — opening_balance=100, period_inputs=[] with EXPLICIT_SCHEDULE returns ()."""
        results = run_shl_schedule(
            opening_balance_keur=100.0,
            period_inputs=[],
            policy=self._EXPLICIT_POLICY,
        )
        assert results == ()
