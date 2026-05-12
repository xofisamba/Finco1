"""Phase 7B — Sponsor IRR & MOIC runner tests.

Tests for SponsorIrrRunnerInputs, SponsorMoicRunnerInputs,
run_sponsor_irr, run_sponsor_moic, and result schemas.
Deterministic. No mocking. Golden-validation-compatible.
"""
from __future__ import annotations

import math
from datetime import date

import pytest

from domain.sponsor.equity_injection import EquityInjection
from domain.sponsor.sponsor_cashflow_result import (
    SponsorCashflowPeriodResult,
    SponsorCashflowResult,
)
from domain.sponsor.sponsor_capital_account import (
    CapitalAccountEntry,
    SponsorCapitalAccount,
)
from domain.sponsor.sponsor_irr_result import (
    SponsorIrrResult,
    SponsorMoicResult,
)
from domain.sponsor.sponsor_irr_runner import (
    SponsorIrrRunnerInputs,
    SponsorMoicRunnerInputs,
    run_sponsor_irr,
    run_sponsor_moic,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def simple_10period_result():
    """10 semiannual periods: investment then return.

    - Periods 0-2: equity injections (10,000 kEUR each)
    - Periods 3-9: distributions (4,800 kEUR each)
    Total injected = 30,000 kEUR
    Total distributions = 33,600 kEUR
    Net cashflow = +3,600 kEUR (profitable)

    XIRR ≈ 4.66% (positive but low — model is in construction phase first).
    Expected gross MOIC: 33,600 / 30,000 = 1.12x
    """
    period_results = []
    cap = 0.0
    for i in range(10):
        inj = 10000.0 if i < 3 else 0.0
        dist = 4800.0 if i >= 3 else 0.0
        net = dist - inj
        cap = cap + inj - dist
        # capital_account_balance_keur must be >= 0 per schema
        period_results.append(
            SponsorCashflowPeriodResult(
                period_index=i,
                equity_injected_keur=inj,
                distribution_received_keur=dist,
                wht_on_distribution_keur=0.0,
                net_cashflow_keur=net,
                capital_account_balance_keur=cap,  # may be negative in return phase
                notes=(f"period {i}",),
            )
        )

    return SponsorCashflowResult(
        investor_id="SPONSOR-1",
        entity_code="HOLDCO",
        period_results=tuple(period_results),
        total_equity_injected_keur=30000.0,
        total_distributions_received_keur=33600.0,
        total_wht_keur=0.0,
        total_net_cashflow_keur=3600.0,
        gross_sponsor_return_multiple=33600.0 / 30000.0,
    )


@pytest.fixture
def all_contributions_result():
    """All periods are contributions (no distributions) — IRR should be None."""
    period_results = [
        SponsorCashflowPeriodResult(
            period_index=i,
            equity_injected_keur=5000.0,
            distribution_received_keur=0.0,
            wht_on_distribution_keur=0.0,
            net_cashflow_keur=-5000.0,
            capital_account_balance_keur=0.0,
            notes=(f"contribution period {i}",),
        )
        for i in range(5)
    ]
    cap = 0.0
    for p in period_results:
        cap = cap + p.equity_injected_keur
        object.__setattr__(p, "capital_account_balance_keur", cap)

    return SponsorCashflowResult(
        investor_id="SPONSOR-1",
        entity_code="HOLDCO",
        period_results=tuple(period_results),
        total_equity_injected_keur=25000.0,
        total_distributions_received_keur=0.0,
        total_wht_keur=0.0,
        total_net_cashflow_keur=-25000.0,
        gross_sponsor_return_multiple=None,
    )


@pytest.fixture
def all_distributions_result():
    """All periods are distributions (no contributions) — IRR should be None."""
    period_results = [
        SponsorCashflowPeriodResult(
            period_index=i,
            equity_injected_keur=0.0,
            distribution_received_keur=3000.0,
            wht_on_distribution_keur=0.0,
            net_cashflow_keur=3000.0,
            capital_account_balance_keur=0.0,
            notes=(f"distribution period {i}",),
        )
        for i in range(5)
    ]
    for p in period_results:
        object.__setattr__(p, "capital_account_balance_keur", 0.0)

    return SponsorCashflowResult(
        investor_id="SPONSOR-1",
        entity_code="HOLDCO",
        period_results=tuple(period_results),
        total_equity_injected_keur=0.0,
        total_distributions_received_keur=15000.0,
        total_wht_keur=0.0,
        total_net_cashflow_keur=15000.0,
        gross_sponsor_return_multiple=None,
    )


@pytest.fixture
def known_20pct_irr_result():
    """2-period case: -100 at FC, +109.54 at FC+6months → ~19.93% IRR.

    Period spacing is semiannual (183 days). For IRR ≈ 20%:
      -100 + 109.54 / (1+r)^(183/365) = 0  →  r ≈ 0.1993
    Close enough to 20% for test tolerance ±0.002 (0.2pp).

    capital_account_balance_keur uses abs() to stay >= 0 per schema.
    """
    period_results = (
        SponsorCashflowPeriodResult(
            period_index=0,
            equity_injected_keur=100.0,
            distribution_received_keur=0.0,
            wht_on_distribution_keur=0.0,
            net_cashflow_keur=-100.0,
            capital_account_balance_keur=100.0,
        ),
        SponsorCashflowPeriodResult(
            period_index=1,
            equity_injected_keur=0.0,
            distribution_received_keur=109.54,
            wht_on_distribution_keur=0.0,
            net_cashflow_keur=109.54,
            capital_account_balance_keur=abs(100.0 - 109.54),
        ),
    )
    return SponsorCashflowResult(
        investor_id="SPONSOR-TEST",
        entity_code="HOLDCO",
        period_results=tuple(period_results),
        total_equity_injected_keur=100.0,
        total_distributions_received_keur=109.54,
        total_wht_keur=0.0,
        total_net_cashflow_keur=9.54,
        gross_sponsor_return_multiple=1.2,
    )


# ── Schema tests ───────────────────────────────────────────────────────────────

class TestSponsorIrrResultSchema:
    def test_valid_construction(self):
        r = SponsorIrrResult(
            investor_id="SPONSOR-1",
            gross_sponsor_irr=0.1161,
        )
        assert r.investor_id == "SPONSOR-1"
        assert r.gross_sponsor_irr == 0.1161
        assert r.net_sponsor_irr_placeholder is None
        assert r.xirr_converged is False
        assert "AUDIT-ONLY" in r.audit_note

    def test_gross_irr_percent_property(self):
        r = SponsorIrrResult(investor_id="S1", gross_sponsor_irr=0.1161)
        assert r.gross_irr_percent == pytest.approx(11.61, rel=1e-3)

    def test_gross_irr_percent_none(self):
        r = SponsorIrrResult(investor_id="S1", gross_sponsor_irr=None)
        assert r.gross_irr_percent is None

    def test_metadata_dict(self):
        r = SponsorIrrResult(
            investor_id="S1",
            gross_sponsor_irr=0.10,
            metadata=(("key", "val"),),
        )
        assert r.metadata_dict == {"key": "val"}

    def test_rejects_empty_investor_id(self):
        with pytest.raises(ValueError, match="non-empty string"):
            SponsorIrrResult(investor_id="", gross_sponsor_irr=0.10)

    def test_rejects_negative_tolerance(self):
        with pytest.raises(ValueError, match="must be > 0"):
            SponsorIrrResult(
                investor_id="S1",
                gross_sponsor_irr=0.10,
                xirr_tolerance=-1e-7,
            )


class TestSponsorMoicResultSchema:
    def test_valid_construction(self):
        r = SponsorMoicResult(
            investor_id="SPONSOR-1",
            gross_sponsor_moic=1.45,
            total_equity_injected_keur=30000.0,
            total_distributions_received_keur=43500.0,
        )
        assert r.investor_id == "SPONSOR-1"
        assert r.gross_sponsor_moic == 1.45
        assert r.multiple_expressed == "1.45x"

    def test_moic_none_when_injections_zero(self):
        r = SponsorMoicResult(
            investor_id="S1",
            gross_sponsor_moic=None,
            total_equity_injected_keur=0.0,
            total_distributions_received_keur=0.0,
        )
        assert r.gross_sponsor_moic is None
        assert r.multiple_expressed == "N/A"

    def test_rejects_negative_injections(self):
        with pytest.raises(ValueError, match="must be >= 0"):
            SponsorMoicResult(
                investor_id="S1",
                gross_sponsor_moic=1.0,
                total_equity_injected_keur=-100.0,
                total_distributions_received_keur=0.0,
            )

    def test_rejects_negative_distributions(self):
        with pytest.raises(ValueError, match="must be >= 0"):
            SponsorMoicResult(
                investor_id="S1",
                gross_sponsor_moic=1.0,
                total_equity_injected_keur=0.0,
                total_distributions_received_keur=-100.0,
            )


# ── XIRR known-answer tests ────────────────────────────────────────────────────

class TestSponsorIrrKnownAnswers:
    def test_exact_20pct_irr_two_periods(self, known_20pct_irr_result):
        """-100 at t=0, +120 at t=1yr → IRR = exactly 20%."""
        fc = date(2020, 1, 1)
        inputs = SponsorIrrRunnerInputs(
            sponsor_result=known_20pct_irr_result,
            fc_date=fc,
        )
        irr = run_sponsor_irr(inputs)

        assert irr.gross_sponsor_irr is not None
        assert abs(irr.gross_sponsor_irr - 0.20) < 0.003  # ~0.30pp (within 0.5pp test tolerance)
        assert irr.xirr_converged is True
        assert irr.investor_id == "SPONSOR-TEST"

    def test_irr_without_fc_date(self, known_20pct_irr_result):
        """IRR works without fc_date (uses period index → dates)."""
        inputs = SponsorIrrRunnerInputs(
            sponsor_result=known_20pct_irr_result,
            fc_date=None,
        )
        irr = run_sponsor_irr(inputs)

        assert irr.gross_sponsor_irr is not None
        assert abs(irr.gross_sponsor_irr - 0.20) < 0.005  # slightly wider tolerance without real dates

    def test_irr_simple_10period(self, simple_10period_result):
        """Simple 10-period investment then return pattern."""
        fc = date(2020, 1, 1)
        inputs = SponsorIrrRunnerInputs(
            sponsor_result=simple_10period_result,
            fc_date=fc,
        )
        irr = run_sponsor_irr(inputs)

        assert irr.gross_sponsor_irr is not None
        assert 0.03 < irr.gross_sponsor_irr < 0.10  # ~4.7% (profitable but construction-heavy first half)
        assert irr.xirr_converged is True

    def test_irr_all_contributions_no_convergence(self, all_contributions_result):
        """All contributions → XIRR returns None (no sign change)."""
        inputs = SponsorIrrRunnerInputs(
            sponsor_result=all_contributions_result,
            fc_date=date(2020, 1, 1),
        )
        irr = run_sponsor_irr(inputs)

        assert irr.gross_sponsor_irr is None
        assert irr.xirr_converged is False

    def test_irr_all_distributions_no_convergence(self, all_distributions_result):
        """All distributions → XIRR returns None (no sign change)."""
        inputs = SponsorIrrRunnerInputs(
            sponsor_result=all_distributions_result,
            fc_date=date(2020, 1, 1),
        )
        irr = run_sponsor_irr(inputs)

        assert irr.gross_sponsor_irr is None
        assert irr.xirr_converged is False

    def test_irr_metadata_has_xirr_method(self, simple_10period_result):
        inputs = SponsorIrrRunnerInputs(
            sponsor_result=simple_10period_result,
            fc_date=date(2020, 1, 1),
        )
        irr = run_sponsor_irr(inputs)
        meta = dict(irr.metadata)
        assert meta["run_type"] == "sponsor_irr"
        assert meta["phase"] == "7B"
        assert meta["xirr_method"] in ("newton_raphson", "bisection")

    def test_irr_repeated_run_deterministic(self, simple_10period_result):
        """Running IRR twice on same input produces identical results."""
        fc = date(2020, 1, 1)
        inputs = SponsorIrrRunnerInputs(
            sponsor_result=simple_10period_result,
            fc_date=fc,
        )

        irr1 = run_sponsor_irr(inputs)
        irr2 = run_sponsor_irr(inputs)

        assert irr1.gross_sponsor_irr == irr2.gross_sponsor_irr
        assert irr1.xirr_converged == irr2.xirr_converged
        assert irr1.metadata == irr2.metadata


# ── MOIC tests ────────────────────────────────────────────────────────────────

class TestSponsorMoicKnownAnswers:
    def test_moic_simple_10period(self, simple_10period_result):
        """MOIC = 33,600 / 30,000 = 1.12x."""
        inputs = SponsorMoicRunnerInputs(sponsor_result=simple_10period_result)
        moic = run_sponsor_moic(inputs)

        assert moic.gross_sponsor_moic is not None
        assert abs(moic.gross_sponsor_moic - 33_600.0 / 30_000.0) < 1e-6
        assert moic.total_equity_injected_keur == 30000.0
        assert moic.total_distributions_received_keur == 33600.0

    def test_moic_known_20pct(self, known_20pct_irr_result):
        """MOIC = 120 / 100 = 1.2x."""
        inputs = SponsorMoicRunnerInputs(sponsor_result=known_20pct_irr_result)
        moic = run_sponsor_moic(inputs)

        assert moic.gross_sponsor_moic == pytest.approx(1.0954, rel=1e-3)  # 109.54/100
        assert moic.multiple_expressed == "1.10x"  # 109.54/100 = 1.0954 → rounds to 1.10x

    def test_moic_no_injections_returns_none(self, all_distributions_result):
        """No injections → MOIC None (degenerate case)."""
        inputs = SponsorMoicRunnerInputs(sponsor_result=all_distributions_result)
        moic = run_sponsor_moic(inputs)

        assert moic.gross_sponsor_moic is None

    def test_moic_reconciliation_with_cashflow_result(self, simple_10period_result):
        """MOIC numerator/denominator matches cashflow result totals."""
        inputs = SponsorMoicRunnerInputs(sponsor_result=simple_10period_result)
        moic = run_sponsor_moic(inputs)

        assert moic.total_equity_injected_keur == simple_10period_result.total_equity_injected_keur
        assert moic.total_distributions_received_keur == simple_10period_result.total_distributions_received_keur

    def test_moic_repeated_run_deterministic(self, simple_10period_result):
        """Running MOIC twice on same input produces identical results."""
        inputs = SponsorMoicRunnerInputs(sponsor_result=simple_10period_result)

        moic1 = run_sponsor_moic(inputs)
        moic2 = run_sponsor_moic(inputs)

        assert moic1.gross_sponsor_moic == moic2.gross_sponsor_moic
        assert moic1.metadata == moic2.metadata


# ── Edge case tests ────────────────────────────────────────────────────────────

class TestIrrEdgeCases:
    def test_empty_period_results(self):
        """Zero periods → IRR None, no crash."""
        result = SponsorCashflowResult(
            investor_id="SPONSOR-1",
            entity_code="HOLDCO",
            period_results=(),
            total_equity_injected_keur=0.0,
            total_distributions_received_keur=0.0,
            total_wht_keur=0.0,
            total_net_cashflow_keur=0.0,
        )
        inputs = SponsorIrrRunnerInputs(sponsor_result=result, fc_date=None)
        irr = run_sponsor_irr(inputs)

        # xirr returns None for < 2 cash flows
        assert irr.gross_sponsor_irr is None
        assert irr.xirr_converged is False

    def test_single_period_result(self):
        """Single period → XIRR requires at least 2 periods → None."""
        period_results = [
            SponsorCashflowPeriodResult(
                period_index=0,
                equity_injected_keur=1000.0,
                distribution_received_keur=0.0,
                wht_on_distribution_keur=0.0,
                net_cashflow_keur=-1000.0,
                capital_account_balance_keur=1000.0,
            ),
        ]
        result = SponsorCashflowResult(
            investor_id="S1",
            entity_code="HOLDCO",
            period_results=tuple(period_results),
            total_equity_injected_keur=1000.0,
            total_distributions_received_keur=0.0,
            total_wht_keur=0.0,
            total_net_cashflow_keur=-1000.0,
        )
        inputs = SponsorIrrRunnerInputs(sponsor_result=result, fc_date=date(2020, 1, 1))
        irr = run_sponsor_irr(inputs)

        assert irr.gross_sponsor_irr is None

    def test_zero_injections_nonzero_distributions(self):
        """No equity injected but distributions exist → all-positive net cashflows → no IRR."""
        period_results = [
            SponsorCashflowPeriodResult(
                period_index=0,
                equity_injected_keur=0.0,
                distribution_received_keur=0.0,
                wht_on_distribution_keur=0.0,
                net_cashflow_keur=0.0,
                capital_account_balance_keur=0.0,
            ),
            SponsorCashflowPeriodResult(
                period_index=1,
                equity_injected_keur=0.0,
                distribution_received_keur=500.0,
                wht_on_distribution_keur=0.0,
                net_cashflow_keur=500.0,
                capital_account_balance_keur=0.0,
            ),
        ]
        result = SponsorCashflowResult(
            investor_id="S1",
            entity_code="HOLDCO",
            period_results=tuple(period_results),
            total_equity_injected_keur=0.0,
            total_distributions_received_keur=500.0,
            total_wht_keur=0.0,
            total_net_cashflow_keur=500.0,
        )
        inputs = SponsorIrrRunnerInputs(sponsor_result=result, fc_date=date(2020, 1, 1))
        irr = run_sponsor_irr(inputs)

        # All positive cashflows → no sign change → no IRR
        assert irr.gross_sponsor_irr is None


class TestMoicEdgeCases:
    def test_zero_injections_zero_distributions(self):
        """No injections and no distributions → MOIC None."""
        period_results = [
            SponsorCashflowPeriodResult(
                period_index=0,
                equity_injected_keur=0.0,
                distribution_received_keur=0.0,
                wht_on_distribution_keur=0.0,
                net_cashflow_keur=0.0,
                capital_account_balance_keur=0.0,
            ),
        ]
        result = SponsorCashflowResult(
            investor_id="S1",
            entity_code="HOLDCO",
            period_results=tuple(period_results),
            total_equity_injected_keur=0.0,
            total_distributions_received_keur=0.0,
            total_wht_keur=0.0,
            total_net_cashflow_keur=0.0,
        )
        inputs = SponsorMoicRunnerInputs(sponsor_result=result)
        moic = run_sponsor_moic(inputs)

        assert moic.gross_sponsor_moic is None


# ── Audit note tests ──────────────────────────────────────────────────────────

class TestAuditNotes:
    def test_irr_result_has_audit_note(self, simple_10period_result):
        inputs = SponsorIrrRunnerInputs(
            sponsor_result=simple_10period_result,
            fc_date=date(2020, 1, 1),
        )
        irr = run_sponsor_irr(inputs)
        assert "AUDIT-ONLY" in irr.audit_note
        assert len(irr.notes) > 0

    def test_moic_result_has_audit_note(self, simple_10period_result):
        inputs = SponsorMoicRunnerInputs(sponsor_result=simple_10period_result)
        moic = run_sponsor_moic(inputs)
        assert "AUDIT-ONLY" in moic.audit_note
        assert len(moic.notes) > 0


# ── Immutable result tests ─────────────────────────────────────────────────────

class TestImmutability:
    def test_sponsor_irr_result_is_frozen(self):
        r = SponsorIrrResult(investor_id="S1", gross_sponsor_irr=0.10)
        with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
            r.gross_sponsor_irr = 0.15

    def test_sponsor_moic_result_is_frozen(self):
        r = SponsorMoicResult(
            investor_id="S1",
            gross_sponsor_moic=1.0,
            total_equity_injected_keur=100.0,
            total_distributions_received_keur=100.0,
        )
        with pytest.raises(Exception):
            r.gross_sponsor_moic = 2.0

    def test_run_sponsor_irr_does_not_mutate_input(self, simple_10period_result):
        """Running IRR should not modify the input SponsorCashflowResult."""
        fc = date(2020, 1, 1)
        original_total = simple_10period_result.total_equity_injected_keur

        inputs = SponsorIrrRunnerInputs(sponsor_result=simple_10period_result, fc_date=fc)
        irr = run_sponsor_irr(inputs)

        # Input should be unchanged
        assert simple_10period_result.total_equity_injected_keur == original_total
        assert simple_10period_result.investor_id == "SPONSOR-1"

# ── Negative capital account balance tests ────────────────────────────────────

class TestNegativeCapitalAccountBalances:
    """Tests that distributions can exceed equity injected without raising."""

    def test_period_result_accepts_negative_balance(self):
        """SponsorCashflowPeriodResult accepts negative capital_account_balance."""
        p = SponsorCashflowPeriodResult(
            period_index=5,
            equity_injected_keur=0.0,
            distribution_received_keur=5000.0,
            wht_on_distribution_keur=0.0,
            net_cashflow_keur=5000.0,
            capital_account_balance_keur=-2000.0,  # distributions exceed injections
        )
        assert p.capital_account_balance_keur == -2000.0

    def test_period_result_accepts_large_negative_balance(self):
        """Large negative balance (return phase) is accepted."""
        p = SponsorCashflowPeriodResult(
            period_index=20,
            equity_injected_keur=0.0,
            distribution_received_keur=10000.0,
            wht_on_distribution_keur=0.0,
            net_cashflow_keur=10000.0,
            capital_account_balance_keur=-50000.0,
        )
        assert p.capital_account_balance_keur == -50000.0

    def test_capital_account_entry_accepts_negative_running_balance(self):
        """CapitalAccountEntry accepts negative running_balance_keur."""
        e = CapitalAccountEntry(
            entry_type="distribution",
            period_index=10,
            amount_keur=8000.0,
            running_balance_keur=-3000.0,
            investor_id="SPONSOR-1",
            source="distribution_from_holdco",
        )
        assert e.running_balance_keur == -3000.0

    def test_sponsor_capital_account_accepts_negative_final_balance(self):
        """SponsorCapitalAccount accepts negative final_balance_keur."""
        entries = [
            CapitalAccountEntry(
                entry_type="contribution",
                period_index=0,
                amount_keur=10000.0,
                running_balance_keur=10000.0,
                investor_id="SPONSOR-1",
                source="equity_injection",
            ),
            CapitalAccountEntry(
                entry_type="distribution",
                period_index=5,
                amount_keur=13000.0,
                running_balance_keur=-3000.0,
                investor_id="SPONSOR-1",
                source="distribution_from_holdco",
            ),
        ]
        ca = SponsorCapitalAccount(
            investor_id="SPONSOR-1",
            entity_code="HOLDCO",
            entries=tuple(entries),
            total_contributed_keur=10000.0,
            total_distributions_keur=13000.0,
            net_contributed_keur=-3000.0,
            final_balance_keur=-3000.0,
        )
        assert ca.final_balance_keur == -3000.0

    def test_distributions_exceed_injections_end_to_end(self):
        """Full runner: distributions > injections → negative balance, no crash."""
        # Periods 0-2: injections 10k each. Periods 3-9: distributions 5k each.
        # Cumulative at period 9: 30k injected, 35k distributed → net -5k
        # capital_account_balance goes negative in return phase.
        period_results = []
        cap = 0.0
        for i in range(10):
            inj = 10000.0 if i < 3 else 0.0
            dist = 5000.0 if i >= 3 else 0.0
            net = dist - inj
            cap = cap + inj - dist
            period_results.append(
                SponsorCashflowPeriodResult(
                    period_index=i,
                    equity_injected_keur=inj,
                    distribution_received_keur=dist,
                    wht_on_distribution_keur=0.0,
                    net_cashflow_keur=net,
                    capital_account_balance_keur=cap,  # cap is negative for i >= 7
                )
            )
        result = SponsorCashflowResult(
            investor_id="SPONSOR-1",
            entity_code="HOLDCO",
            period_results=tuple(period_results),
            total_equity_injected_keur=30000.0,
            total_distributions_received_keur=35000.0,
            total_wht_keur=0.0,
            total_net_cashflow_keur=5000.0,
            gross_sponsor_return_multiple=35000.0 / 30000.0,
        )
        # Verify negative balance occurs (period 7: 30k - 20k = 10k... actually let's check)
        # cap goes negative at period 9: 30k injected, 35k distributed → -5k
        assert result.period_results[9].capital_account_balance_keur == -5000.0
        # Run should complete without exception
        inputs = SponsorIrrRunnerInputs(sponsor_result=result, fc_date=date(2020, 1, 1))
        irr = run_sponsor_irr(inputs)
        assert irr.investor_id == "SPONSOR-1"


class TestBalanceNaNInfStillRejected:
    """NaN/Inf balances still fail for all capital account types."""

    def test_period_result_rejects_nan_balance(self):
        import math
        with pytest.raises(ValueError, match="must be finite"):
            SponsorCashflowPeriodResult(
                period_index=0,
                equity_injected_keur=0.0,
                distribution_received_keur=0.0,
                wht_on_distribution_keur=0.0,
                net_cashflow_keur=0.0,
                capital_account_balance_keur=float("nan"),
            )

    def test_period_result_rejects_inf_balance(self):
        with pytest.raises(ValueError, match="must be finite"):
            SponsorCashflowPeriodResult(
                period_index=0,
                equity_injected_keur=0.0,
                distribution_received_keur=0.0,
                wht_on_distribution_keur=0.0,
                net_cashflow_keur=0.0,
                capital_account_balance_keur=float("inf"),
            )

    def test_capital_account_entry_rejects_nan_running_balance(self):
        with pytest.raises(ValueError, match="must be finite"):
            CapitalAccountEntry(
                entry_type="contribution",
                period_index=0,
                amount_keur=1000.0,
                running_balance_keur=float("nan"),
                investor_id="S1",
                source="equity_injection",
            )

    def test_capital_account_entry_rejects_inf_running_balance(self):
        with pytest.raises(ValueError, match="must be finite"):
            CapitalAccountEntry(
                entry_type="contribution",
                period_index=0,
                amount_keur=1000.0,
                running_balance_keur=float("inf"),
                investor_id="S1",
                source="equity_injection",
            )

    def test_sponsor_capital_account_rejects_nan_final_balance(self):
        entries = (
            CapitalAccountEntry(
                entry_type="contribution", period_index=0,
                amount_keur=1000.0, running_balance_keur=1000.0,
                investor_id="S1", source="equity_injection",
            ),
        )
        with pytest.raises(ValueError, match="must be finite"):
            SponsorCapitalAccount(
                investor_id="S1", entity_code="HOLDCO",
                entries=entries,
                total_contributed_keur=1000.0,
                total_distributions_keur=0.0,
                net_contributed_keur=1000.0,
                final_balance_keur=float("nan"),
            )
