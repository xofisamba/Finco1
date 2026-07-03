"""Stack X: Engine Invariants.

Invariant tests for the financial model engine.  No production code changes.

These tests verify structural correctness of the engine outputs across both
TUHO and Oborovo demo projects.
"""
from __future__ import annotations

import math
import os
import sys

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ui_runner import run_demo_project


# ---------------------------------------------------------------------------
# Module-scoped fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def tuho():
    return run_demo_project("TUHO").result


@pytest.fixture(scope="module")
def oborovo():
    return run_demo_project("Oborovo").result


@pytest.fixture(scope="module", params=["TUHO", "Oborovo"])
def any_result(request):
    return run_demo_project(request.param).result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _operating(periods):
    return [p for p in periods if p.is_operation]


def _numeric_fields(period):
    """Return all numeric (float/int) attribute values of a period."""
    skip = {"period", "date", "year_index", "period_in_year", "is_operation",
            "distribution_source"}
    out = {}
    for attr in dir(period):
        if attr.startswith("_") or attr in skip:
            continue
        val = getattr(period, attr)
        if isinstance(val, (int, float)):
            out[attr] = val
    return out


# ===========================================================================
# 1. Senior Debt
# ===========================================================================

class TestSeniorDebtInvariants:
    """Senior balance conservation and non-negativity."""

    def test_senior_balance_never_negative(self, any_result):
        for p in any_result.periods:
            assert p.senior_balance_keur >= -0.01, (
                f"period {p.period}: senior_balance_keur={p.senior_balance_keur}"
            )

    def test_senior_balance_conservation(self, tuho):
        """closing = prior_closing - principal_repaid."""
        periods = tuho.periods
        for i in range(1, len(periods)):
            opening = periods[i - 1].senior_balance_keur
            principal = periods[i].senior_principal_keur
            closing = periods[i].senior_balance_keur
            expected = opening - principal
            assert abs(expected - closing) < 0.1, (
                f"period {periods[i].period}: opening={opening:.2f} - "
                f"principal={principal:.2f} != closing={closing:.2f}"
            )

    def test_senior_balance_conservation_oborovo(self, oborovo):
        periods = oborovo.periods
        for i in range(1, len(periods)):
            opening = periods[i - 1].senior_balance_keur
            principal = periods[i].senior_principal_keur
            closing = periods[i].senior_balance_keur
            expected = opening - principal
            assert abs(expected - closing) < 0.1, (
                f"period {periods[i].period}: opening={opening:.2f} - "
                f"principal={principal:.2f} != closing={closing:.2f}"
            )

    def test_senior_principal_never_exceeds_opening_balance(self, any_result):
        periods = any_result.periods
        for i in range(1, len(periods)):
            opening = periods[i - 1].senior_balance_keur
            principal = periods[i].senior_principal_keur
            assert principal <= opening + 0.01, (
                f"period {periods[i].period}: principal={principal:.2f} > "
                f"opening={opening:.2f}"
            )

    def test_senior_interest_never_exceeds_theoretical_max(self, any_result):
        """Interest <= opening_balance * some reasonable max rate per period.

        We use 10% per period as a very loose upper bound.
        """
        MAX_RATE_PER_PERIOD = 0.10
        periods = any_result.periods
        for i in range(1, len(periods)):
            opening = periods[i - 1].senior_balance_keur
            interest = periods[i].senior_interest_keur
            max_interest = opening * MAX_RATE_PER_PERIOD + 0.01
            assert interest <= max_interest, (
                f"period {periods[i].period}: interest={interest:.2f} > "
                f"max={max_interest:.2f} (opening={opening:.2f})"
            )


# ===========================================================================
# 2. SHL
# ===========================================================================

class TestSHLInvariants:
    """SHL balance conservation and non-negativity."""

    def test_shl_balance_never_negative(self, any_result):
        for p in any_result.periods:
            assert p.shl_balance_keur >= -0.01, (
                f"period {p.period}: shl_balance_keur={p.shl_balance_keur}"
            )

    def test_shl_balance_conservation(self, tuho):
        """closing = prior_closing + PIK - principal_repaid."""
        periods = tuho.periods
        for i in range(1, len(periods)):
            opening = periods[i - 1].shl_balance_keur
            pik = periods[i].shl_pik_keur
            principal = periods[i].shl_principal_keur
            closing = periods[i].shl_balance_keur
            expected = opening + pik - principal
            assert abs(expected - closing) < 0.1, (
                f"period {periods[i].period}: opening={opening:.2f} + pik={pik:.2f} "
                f"- principal={principal:.2f} != closing={closing:.2f}"
            )

    def test_shl_balance_conservation_oborovo(self, oborovo):
        periods = oborovo.periods
        for i in range(1, len(periods)):
            opening = periods[i - 1].shl_balance_keur
            pik = periods[i].shl_pik_keur
            principal = periods[i].shl_principal_keur
            closing = periods[i].shl_balance_keur
            expected = opening + pik - principal
            assert abs(expected - closing) < 0.1, (
                f"period {periods[i].period}: opening={opening:.2f} + pik={pik:.2f} "
                f"- principal={principal:.2f} != closing={closing:.2f}"
            )

    def test_shl_principal_never_exceeds_opening_balance(self, any_result):
        periods = any_result.periods
        for i in range(1, len(periods)):
            opening = periods[i - 1].shl_balance_keur
            principal = periods[i].shl_principal_keur
            assert principal <= opening + 0.01, (
                f"period {periods[i].period}: shl_principal={principal:.2f} > "
                f"opening={opening:.2f}"
            )

    def test_shl_interest_reasonable(self, any_result):
        """SHL cash interest <= opening_balance * 20% per period (loose bound)."""
        MAX_RATE = 0.20
        periods = any_result.periods
        for i in range(1, len(periods)):
            opening = periods[i - 1].shl_balance_keur
            interest = periods[i].shl_interest_keur
            assert interest <= opening * MAX_RATE + 0.01, (
                f"period {periods[i].period}: shl_interest={interest:.2f} > "
                f"max={opening * MAX_RATE:.2f}"
            )


# ===========================================================================
# 3. Tax
# ===========================================================================

class TestTaxInvariants:
    """Tax fields are non-negative and loss carryforward is monotone."""

    def test_tax_accrual_never_negative(self, any_result):
        for p in any_result.periods:
            assert p.tax_keur >= -0.01, (
                f"period {p.period}: tax_keur={p.tax_keur}"
            )

    def test_corporate_tax_cash_never_negative(self, any_result):
        for p in any_result.periods:
            assert p.corporate_tax_cash_keur >= -0.01, (
                f"period {p.period}: corporate_tax_cash_keur={p.corporate_tax_cash_keur}"
            )

    def test_tax_loss_closing_never_negative(self, any_result):
        for p in any_result.periods:
            assert p.tax_loss_closing_audit_keur >= -0.01, (
                f"period {p.period}: tax_loss_closing_audit_keur="
                f"{p.tax_loss_closing_audit_keur}"
            )

    def test_tax_loss_carryforward_monotone_decrease(self, any_result):
        """Once losses reach zero, they do not reappear."""
        losses_exhausted = False
        for p in any_result.periods:
            closing = p.tax_loss_closing_audit_keur
            if not losses_exhausted and closing < 0.01:
                losses_exhausted = True
            if losses_exhausted:
                assert closing < 0.01, (
                    f"period {p.period}: losses reappeared: "
                    f"tax_loss_closing={closing:.2f}"
                )

    def test_total_tax_non_negative(self, any_result):
        total = sum(p.tax_keur for p in any_result.periods)
        assert total >= -0.1, f"total_tax_keur={total:.2f} is negative"

    def test_total_cit_cash_non_negative(self, any_result):
        total = sum(p.corporate_tax_cash_keur for p in any_result.periods)
        assert total >= -0.1, f"total_corporate_tax_cash_keur={total:.2f} is negative"


# ===========================================================================
# 4. DSCR
# ===========================================================================

class TestDSCRInvariants:
    """DSCR is finite and positive in operating periods with debt service."""

    def test_dscr_no_nan(self, any_result):
        for p in any_result.periods:
            if p.dscr is not None:
                assert not math.isnan(p.dscr), (
                    f"period {p.period}: DSCR is NaN"
                )

    def test_dscr_positive_when_ebitda_positive_and_ds_positive(self, any_result):
        """When EBITDA > 0 and senior DS > 0, DSCR should be positive."""
        for p in any_result.periods:
            if p.dscr is None:
                continue
            if math.isinf(p.dscr):
                # inf allowed when DS = 0
                continue
            if p.ebitda_keur > 0 and p.senior_ds_keur > 0:
                assert p.dscr > 0, (
                    f"period {p.period}: DSCR={p.dscr} not positive despite "
                    f"ebitda={p.ebitda_keur:.2f} and ds={p.senior_ds_keur:.2f}"
                )

    def test_dscr_finite_in_operating_periods_with_ds(self, any_result):
        """DSCR should not be +/-inf when there is actual debt service."""
        for p in any_result.periods:
            if not p.is_operation:
                continue
            if p.senior_ds_keur > 0 and p.dscr is not None:
                assert math.isfinite(p.dscr), (
                    f"period {p.period}: DSCR={p.dscr} is not finite "
                    f"(ds={p.senior_ds_keur:.2f})"
                )


# ===========================================================================
# 5. IRR
# ===========================================================================

class TestIRRInvariants:
    """IRR values are finite and in economically plausible ranges."""

    def test_equity_irr_finite(self, any_result):
        assert math.isfinite(any_result.equity_irr), (
            f"equity_irr is not finite: {any_result.equity_irr}"
        )

    def test_equity_irr_in_range(self, any_result):
        irr = any_result.equity_irr
        assert 0.01 <= irr <= 0.50, (
            f"equity_irr={irr:.4f} outside [1%, 50%]"
        )

    def test_project_irr_finite(self, any_result):
        assert math.isfinite(any_result.project_irr), (
            f"project_irr is not finite: {any_result.project_irr}"
        )

    def test_project_irr_in_range(self, any_result):
        irr = any_result.project_irr
        assert 0.01 <= irr <= 0.50, (
            f"project_irr={irr:.4f} outside [1%, 50%]"
        )


# ===========================================================================
# 6. No NaN / No Inf
# ===========================================================================

class TestNoNaNInf:
    """All numeric period fields must be finite; DSCR inf is allowed."""

    def test_no_nan_in_period_fields(self, any_result):
        failures = []
        for p in any_result.periods:
            for field, val in _numeric_fields(p).items():
                if math.isnan(val):
                    failures.append(f"period {p.period}: {field}=NaN")
        assert not failures, "NaN values found:\n" + "\n".join(failures[:20])

    def test_no_inf_except_dscr(self, any_result):
        failures = []
        for p in any_result.periods:
            for field, val in _numeric_fields(p).items():
                if field == "dscr":
                    continue  # inf DSCR is allowed for zero-DS periods
                if math.isinf(val):
                    failures.append(f"period {p.period}: {field}=inf")
        assert not failures, "Inf values found:\n" + "\n".join(failures[:20])


# ===========================================================================
# 7. Distributions
# ===========================================================================

class TestDistributionInvariants:
    """Distributions never exceed available cash."""

    def test_distribution_never_exceeds_available_cash(self, any_result):
        for p in any_result.periods:
            available = max(0.0, p.cf_after_reserves_keur)
            assert p.distribution_keur <= available + 0.01, (
                f"period {p.period}: distribution={p.distribution_keur:.2f} > "
                f"available={available:.2f}"
            )

    def test_total_distributions_non_negative(self, any_result):
        total = sum(p.distribution_keur for p in any_result.periods)
        assert total >= 0, f"total distributions={total:.2f} is negative"

    def test_result_total_distribution_matches_sum(self, any_result):
        period_sum = sum(p.distribution_keur for p in any_result.periods)
        assert abs(period_sum - any_result.total_distribution_keur) < 1.0, (
            f"sum(distributions)={period_sum:.2f} != "
            f"result.total_distribution_keur={any_result.total_distribution_keur:.2f}"
        )


# ===========================================================================
# 8. Cash Conservation (lifetime)
# ===========================================================================

class TestCashConservation:
    """Lifetime cash aggregates are self-consistent."""

    def test_total_senior_ds_positive(self, any_result):
        assert any_result.total_senior_ds_keur > 0, (
            f"total_senior_ds_keur={any_result.total_senior_ds_keur:.2f} not positive"
        )

    def test_total_ebitda_positive(self, any_result):
        assert any_result.total_ebitda_keur > 0, (
            f"total_ebitda_keur={any_result.total_ebitda_keur:.2f} not positive"
        )


# ===========================================================================
# 9. EBITDA Invariants
# ===========================================================================

class TestEBITDAInvariants:
    """EBITDA is positive in all operating periods."""

    def test_ebitda_positive_in_operating_periods(self, any_result):
        failures = []
        for p in _operating(any_result.periods):
            if p.ebitda_keur <= 0:
                failures.append(
                    f"period {p.period}: ebitda_keur={p.ebitda_keur:.2f}"
                )
        assert not failures, (
            "Non-positive EBITDA in operating periods:\n" + "\n".join(failures[:10])
        )
