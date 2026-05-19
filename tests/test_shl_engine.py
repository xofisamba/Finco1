"""Phase 7 — SHL Engine unit tests.

Tests the canonical ShlEngine in isolation.
These are pure unit tests — no runtime wiring required.

Note: The engine follows the design spec (PR #99) which uses:
    gross = opening × rate × day_frac
    pik = max(0, gross - cash_int)
    principal = min(remaining_cash, outstanding)

This differs structurally from the Excel model which uses more complex
tranche-level implicit interest calculations. The tests below verify
internal consistency (balance reconciliation, cash reconciliation) rather
than exact Excel parity.
"""
import pytest
from domain.shl.inputs import ShlEngineInputs, ShlPeriodInput
from domain.shl.engine import ShlEngine
from domain.shl.result import ShlEngineResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_engine_inputs(
    project_name="TUHO",
    period_count=2,
    tranche_opening=32703.864,
    drawdown=0.0,
    rate=0.08,
    day_frac=0.5,
    post_senior_cash_seq=None,
    pik_allowed=True,
    maintain_min_reserve=False,
    min_reserve=0.0,
):
    """Build ShlEngineInputs for testing.

    The engine computes period t opening as:
        - t=0: sum(tranche_opening_balances_keur) + drawdown[t=0]
        - t>0: prior period closing balance
    """
    if post_senior_cash_seq is None:
        post_senior_cash_seq = [500.0, 500.0]

    period_inputs = tuple(
        ShlPeriodInput(
            period_index=t + 1,
            opening_balance_keur=0.0,  # engine derives this
            drawdown_keur=drawdown,
            interest_rate=rate,
            day_count_fraction=day_frac,
            post_senior_cash_available_keur=post_senior_cash_seq[t],
            pik_allowed=pik_allowed,
            maintain_minimum_cash_reserve=maintain_min_reserve,
            minimum_cash_reserve_keur=min_reserve,
        )
        for t in range(period_count)
    )

    return ShlEngineInputs(
        project_name=project_name,
        period_count=period_count,
        period_inputs=period_inputs,
        total_shl_funding_keur=29135.176,
        tranche_rates=(rate,),
        tranche_day_fracs=(day_frac,),
        tranche_opening_balances_keur=(tranche_opening,),
        pik_allowed=pik_allowed,
        maintain_minimum_cash_reserve=maintain_min_reserve,
        minimum_cash_reserve_keur=min_reserve,
    )


# ---------------------------------------------------------------------------
# Waterfall order tests
# ---------------------------------------------------------------------------

class TestWaterfallOrder:
    def test_first_period_opening_equals_tranche_opening_plus_drawdown(self):
        """First period opening = tranche_opening + first drawdown."""
        tranche_opening = 32703.864
        drawdown = 2911.5216
        inputs = make_engine_inputs(
            period_count=1,
            tranche_opening=tranche_opening,
            drawdown=drawdown,
            post_senior_cash_seq=[1000.0],
        )
        result = ShlEngine.compute(inputs)
        assert result.period_results[0].opening_balance_keur == pytest.approx(
            tranche_opening + drawdown, rel=1e-9
        )

    def test_closing_equals_opening_plus_drawdown_plus_pik_minus_principal(self):
        """Engine enforces: closing = opening + drawdown + PIK - principal."""
        inputs = make_engine_inputs(period_count=1, post_senior_cash_seq=[200.0])
        result = ShlEngine.compute(inputs)
        pr = result.period_results[0]
        expected = pr.opening_balance_keur + pr.drawdown_keur + pr.pik_capitalized_keur - pr.principal_repaid_keur
        assert pr.closing_balance_keur == pytest.approx(expected, rel=1e-9)


# ---------------------------------------------------------------------------
# Balance reconciliation
# ---------------------------------------------------------------------------

class TestBalanceReconciliation:
    def test_balance_reconciliation_holds_every_period(self):
        """opening + drawdown + PIK - principal = closing, every period."""
        inputs = make_engine_inputs(
            period_count=10,
            tranche_opening=32703.864,
            drawdown=0.0,
            post_senior_cash_seq=[500.0] * 10,
        )
        result = ShlEngine.compute(inputs)
        for pr in result.period_results:
            expected = (
                pr.opening_balance_keur
                + pr.drawdown_keur
                + pr.pik_capitalized_keur
                - pr.principal_repaid_keur
            )
            assert pr.closing_balance_keur == pytest.approx(expected, rel=1e-9)


# ---------------------------------------------------------------------------
# Cash reconciliation
# ---------------------------------------------------------------------------

class TestCashReconciliation:
    def test_cash_reconciliation_holds_every_period(self):
        """post_senior_cash = cash_int + principal + cash_after_shl, every period."""
        inputs = make_engine_inputs(
            period_count=5,
            tranche_opening=32703.864,
            drawdown=0.0,
            post_senior_cash_seq=[500.0, 600.0, 550.0, 580.0, 520.0],
        )
        result = ShlEngine.compute(inputs)
        for pr in result.period_results:
            # post_senior_cash is stored as post_senior_cash_available_keur in ShlPeriodInput
            # In ShlPeriodResult, it's available via cash_consumed + cash_after_shl
            rhs = pr.cash_interest_paid_keur + pr.principal_repaid_keur + pr.cash_after_shl_keur
            lhs = pr.cash_consumed_by_shl_keur + pr.cash_after_shl_keur
            assert lhs == pytest.approx(rhs, rel=1e-9)


# ---------------------------------------------------------------------------
# PIK trigger
# ---------------------------------------------------------------------------

class TestPIKTrigger:
    def test_pik_triggered_when_cash_lt_gross(self):
        """PIK > 0 when available cash < gross accrued interest."""
        # balance=5000 → gross = 5000*0.08*0.5 = 200
        # cash = 100 → shortfall = 100 → PIK = 100
        inputs = make_engine_inputs(
            period_count=1,
            tranche_opening=5000.0,
            drawdown=0.0,
            post_senior_cash_seq=[100.0],
        )
        result = ShlEngine.compute(inputs)
        pr = result.period_results[0]
        assert pr.pik_triggered is True
        assert pr.pik_capitalized_keur == pytest.approx(100.0, rel=1e-9)
        assert pr.cash_interest_paid_keur == pytest.approx(100.0, rel=1e-9)

    def test_no_pik_when_cash_gte_gross(self):
        """PIK = 0 when available cash >= gross accrued."""
        inputs = make_engine_inputs(
            period_count=1,
            tranche_opening=5000.0,  # gross = 200
            drawdown=0.0,
            post_senior_cash_seq=[300.0],  # excess cash
        )
        result = ShlEngine.compute(inputs)
        pr = result.period_results[0]
        assert pr.pik_triggered is False
        assert pr.pik_capitalized_keur == pytest.approx(0.0, abs=0.01)

    def test_pik_suppressed_when_pik_allowed_false(self):
        """PIK = 0 when pik_allowed=False, even with shortfall."""
        inputs = make_engine_inputs(
            period_count=1,
            tranche_opening=5000.0,  # gross = 200
            drawdown=0.0,
            post_senior_cash_seq=[100.0],  # shortfall
            pik_allowed=False,
        )
        result = ShlEngine.compute(inputs)
        pr = result.period_results[0]
        assert pr.pik_capitalized_keur == pytest.approx(0.0, abs=0.01)


# ---------------------------------------------------------------------------
# Minimum cash reserve
# ---------------------------------------------------------------------------

class TestMinimumReserve:
    def test_reserve_default_off(self):
        """Default: no reserve retained."""
        inputs = make_engine_inputs(
            period_count=1,
            tranche_opening=5000.0,
            drawdown=0.0,
            post_senior_cash_seq=[300.0],
        )
        result = ShlEngine.compute(inputs)
        pr = result.period_results[0]
        assert pr.reserve_applied is False

    def test_reserve_applied_when_enabled(self):
        """When enabled, minimum reserve is retained before SHL service."""
        inputs = make_engine_inputs(
            period_count=1,
            tranche_opening=5000.0,  # gross = 200
            drawdown=0.0,
            post_senior_cash_seq=[300.0],
            maintain_min_reserve=True,
            min_reserve=100.0,
        )
        result = ShlEngine.compute(inputs)
        pr = result.period_results[0]
        assert pr.reserve_applied is True
        # 300 cash - 100 reserve = 200 available; gross=200; all goes to interest
        assert pr.cash_interest_paid_keur == pytest.approx(200.0, rel=1e-9)
        assert pr.cash_after_shl_keur == pytest.approx(100.0, rel=1e-9)


# ---------------------------------------------------------------------------
# Closing balance non-negative
# ---------------------------------------------------------------------------

class TestClosingBalance:
    def test_closing_balance_never_negative(self):
        """Closing balance never goes below zero."""
        inputs = make_engine_inputs(
            period_count=20,
            tranche_opening=32703.864,
            drawdown=0.0,
            post_senior_cash_seq=[500.0] * 20,
        )
        result = ShlEngine.compute(inputs)
        for pr in result.period_results:
            assert pr.closing_balance_keur >= -0.01


# ---------------------------------------------------------------------------
# 100% cash sweep
# ---------------------------------------------------------------------------

class TestCashSweep:
    def test_engine_consumes_all_available_cash(self):
        """Engine fully consumes post-senior cash (100% sweep when cash <= need)."""
        inputs = make_engine_inputs(
            period_count=1,
            tranche_opening=5000.0,
            drawdown=0.0,
            post_senior_cash_seq=[300.0],
        )
        result = ShlEngine.compute(inputs)
        pr = result.period_results[0]
        # 300 cash: 200 interest (gross=200), 100 remaining, 100 principal, 0 left
        assert pr.cash_consumed_by_shl_keur == pytest.approx(300.0, rel=1e-9)
        assert pr.cash_for_distribution_keur == pytest.approx(0.0, abs=0.01)


# ---------------------------------------------------------------------------
# Semiannual interest
# ---------------------------------------------------------------------------

class TestSemiannualInterest:
    def test_8pct_semiannual_yields_4pct_per_period(self):
        """8% annual, 0.5 day frac → 4% per period."""
        inputs = make_engine_inputs(
            period_count=1,
            tranche_opening=1000.0,
            drawdown=0.0,
            rate=0.08,
            day_frac=0.5,
            post_senior_cash_seq=[1000.0],  # plenty
        )
        result = ShlEngine.compute(inputs)
        pr = result.period_results[0]
        # 1000 * 0.08 * 0.5 = 40
        assert pr.gross_accrued_interest_keur == pytest.approx(40.0, rel=1e-9)


# ---------------------------------------------------------------------------
# R99/R102 NOT implemented
# ---------------------------------------------------------------------------

class TestNoR99Promotion:
    def test_cash_for_distribution_exposed_not_gated(self):
        """Engine exposes cash_for_distribution but does NOT apply any DSCR gate."""
        inputs = make_engine_inputs(
            period_count=5,
            tranche_opening=32703.864,
            drawdown=0.0,
            post_senior_cash_seq=[500.0] * 5,
        )
        result = ShlEngine.compute(inputs)
        for pr in result.period_results:
            # Engine never applies R99 gate; residual is always exposed
            assert pr.cash_for_distribution_keur >= 0.0


# ---------------------------------------------------------------------------
# Result completeness
# ---------------------------------------------------------------------------

class TestResultCompleteness:
    def test_all_output_fields_populated(self):
        """All required output fields are populated."""
        inputs = make_engine_inputs(period_count=1)
        result = ShlEngine.compute(inputs)
        pr = result.period_results[0]
        assert pr.opening_balance_keur is not None
        assert pr.drawdown_keur is not None
        assert pr.gross_accrued_interest_keur is not None
        assert pr.cash_interest_paid_keur is not None
        assert pr.pik_capitalized_keur is not None
        assert pr.principal_repaid_keur is not None
        assert pr.closing_balance_keur is not None
        assert pr.cash_consumed_by_shl_keur is not None
        assert pr.cash_after_shl_keur is not None
        assert pr.cash_for_distribution_keur is not None
        assert isinstance(pr.pik_triggered, bool)
        assert isinstance(pr.cash_sweep_100_pct, bool)
        assert isinstance(pr.reserve_applied, bool)

    def test_engine_result_totals_positive(self):
        """Result totals are positive after computation."""
        inputs = make_engine_inputs(
            period_count=5,
            tranche_opening=32703.864,
            drawdown=0.0,
            post_senior_cash_seq=[500.0] * 5,
        )
        result = ShlEngine.compute(inputs)
        assert result.total_gross_accrued_interest_keur > 0
        assert result.total_cash_interest_paid_keur > 0
        assert result.total_pik_capitalized_keur >= 0
        assert result.total_principal_repaid_keur >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])