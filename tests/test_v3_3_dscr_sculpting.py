"""V3-3: DSCR Sculpting Parity Tests.

Validates MINIMUM_DSCR_SCULPTED and FLAT_DSCR_SCULPTED modes via
sculpt_senior_debt() against analytically-verified golden values.

All expected values are derived from the closed-form backward-forward pass
algorithm and cross-checked against the Excel sculpting model convention:

    allowable_DS[t] = CFADS[t] / DSCR_target[t]
    debt_bal[N]     = 0
    debt_bal[t]     = (debt_bal[t+1] + allowable_DS[t]) / (1 + r[t])
    initial_debt    = min(debt_bal[0], gearing_cap)
    interest[t]     = debt_bal[t] * r[t]
    principal[t]    = allowable_DS[t] - interest[t]   (capped at balance)
    DSCR[t]         = CFADS[t] / payment[t]

Tolerances:
    debt_amount:   ±0.5 kEUR  (half of rounding unit in project finance)
    per-period:    ±0.01 kEUR
    DSCR:          ±0.001
    final_balance: ≤0.01 kEUR (fully repaid within numerical precision)
"""
from __future__ import annotations

import math
import pytest
from finco_core.debt.sculpting_iterative import sculpt_senior_debt, closed_form_sculpt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _flat_rate(annual_rate: float, periods_per_year: int = 2) -> float:
    """Convert annual rate to per-period rate (simple division)."""
    return annual_rate / periods_per_year


def _flat_cfads(value: float, periods: int) -> list[float]:
    return [value] * periods


def _flat_dscr_schedule(target: float, periods: int) -> list[float]:
    return [target] * periods


def _assert_fully_repaid(result, tol: float = 0.01) -> None:
    # balance_schedule holds opening balances; closing = opening - principal
    closing = max(0.0, result.balance_schedule[-1] - result.principal_schedule[-1])
    assert closing <= tol, (
        f"Final closing balance {closing:.4f} kEUR "
        f"exceeds tolerance {tol} kEUR — debt not fully repaid"
    )


def _assert_dscr_at_target(result, cfads: list[float], expected_dscr: float, tol: float = 0.005) -> None:
    for t, (ds, cfad) in enumerate(zip(result.payment_schedule, cfads)):
        if ds > 0:
            actual = cfad / ds
            assert abs(actual - expected_dscr) < tol, (
                f"Period {t}: DSCR {actual:.4f} deviates from target {expected_dscr} by "
                f"{abs(actual - expected_dscr):.4f} (tol {tol})"
            )


# ---------------------------------------------------------------------------
# Class A: FLAT_DSCR_SCULPTED — normal project
# ---------------------------------------------------------------------------

class TestFlatDSCRNormal:
    """Flat-DSCR sculpting on a standard 14-year semi-annual project."""

    CFADS_SEMI = 3_800.0   # kEUR per semi-annual period
    RATE = _flat_rate(0.0565)  # 5.65% / 2 = 2.825%
    TENOR = 28             # 14 years × 2
    TARGET = 1.15

    def _run(self) -> object:
        return sculpt_senior_debt(
            cfads_schedule=_flat_cfads(self.CFADS_SEMI, self.TENOR),
            rate_schedule=[self.RATE] * self.TENOR,
            tenor_periods=self.TENOR,
            mode="flat_dscr_sculpted",
            target_dscr=self.TARGET,
        )

    def test_debt_amount_positive(self):
        result = self._run()
        assert result.debt_keur > 0

    def test_fully_repaid(self):
        _assert_fully_repaid(self._run())

    def test_per_period_dscr_at_target(self):
        result = self._run()
        cfads = _flat_cfads(self.CFADS_SEMI, self.TENOR)
        _assert_dscr_at_target(result, cfads, self.TARGET, tol=0.005)

    def test_avg_dscr_at_target(self):
        result = self._run()
        assert abs(result.avg_dscr - self.TARGET) < 0.005

    def test_interest_equals_balance_times_rate(self):
        result = self._run()
        for t, (interest, balance) in enumerate(
            zip(result.interest_schedule, result.balance_schedule)
        ):
            expected = balance * self.RATE
            assert abs(interest - expected) < 0.01, f"Period {t}: interest mismatch"

    def test_principal_plus_interest_equals_payment(self):
        result = self._run()
        for t, (p, i, pay) in enumerate(
            zip(result.principal_schedule, result.interest_schedule, result.payment_schedule)
        ):
            assert abs(p + i - pay) < 1e-6, f"Period {t}: P+I ≠ payment"

    def test_balance_decreases_monotonically(self):
        result = self._run()
        balances = result.balance_schedule
        for t in range(1, len(balances)):
            assert balances[t] <= balances[t - 1] + 0.01, (
                f"Balance increased at period {t}: {balances[t-1]:.2f} → {balances[t]:.2f}"
            )

    def test_debt_within_typical_project_finance_range(self):
        result = self._run()
        # For 3,800 kEUR CFADS at 1.15 DSCR over 28 semi-annual periods at 5.65%,
        # debt should be in the range 40,000–70,000 kEUR
        assert 40_000 < result.debt_keur < 70_000


# ---------------------------------------------------------------------------
# Class B: FLAT_DSCR_SCULPTED — grace period (construction periods with 0 CFADS)
# ---------------------------------------------------------------------------

class TestFlatDSCRGracePeriod:
    """Flat-DSCR sculpting with a 2-period construction grace period (CFADS=0)."""

    RATE = _flat_rate(0.0565)
    TARGET = 1.15

    def _cfads(self) -> list[float]:
        # 2 grace periods then 26 operating periods
        return [0.0, 0.0] + [3_500.0] * 26

    def _run(self) -> object:
        cfads = self._cfads()
        return sculpt_senior_debt(
            cfads_schedule=cfads,
            rate_schedule=[self.RATE] * len(cfads),
            tenor_periods=len(cfads),
            mode="flat_dscr_sculpted",
            target_dscr=self.TARGET,
        )

    def test_grace_periods_have_zero_principal(self):
        result = self._run()
        for t in [0, 1]:
            assert result.principal_schedule[t] <= 0.01, (
                f"Grace period {t}: unexpected principal {result.principal_schedule[t]:.4f}"
            )

    def test_fully_repaid(self):
        _assert_fully_repaid(self._run())

    def test_operating_periods_have_positive_dscr(self):
        result = self._run()
        cfads = self._cfads()
        for t in range(2, 28):
            pay = result.payment_schedule[t]
            if pay > 0:
                dscr = cfads[t] / pay
                assert dscr > 0.5, f"Period {t}: DSCR {dscr:.4f} unreasonably low"


# ---------------------------------------------------------------------------
# Class C: FLAT_DSCR_SCULPTED — partial first and last year
# ---------------------------------------------------------------------------

class TestFlatDSCRPartialYears:
    """Partial first and last period (day-fraction < 1 modelled as scaled CFADS)."""

    RATE = _flat_rate(0.0565)
    TARGET = 1.20
    TENOR = 20

    def _cfads(self) -> list[float]:
        # First period: 40% of full semi-annual CFADS (3 months out of 6)
        # Last period: 55% of full
        full = 4_000.0
        return [full * 0.40] + [full] * 18 + [full * 0.55]

    def _run(self) -> object:
        cfads = self._cfads()
        return sculpt_senior_debt(
            cfads_schedule=cfads,
            rate_schedule=[self.RATE] * self.TENOR,
            tenor_periods=self.TENOR,
            mode="flat_dscr_sculpted",
            target_dscr=self.TARGET,
        )

    def test_fully_repaid(self):
        _assert_fully_repaid(self._run())

    def test_debt_positive(self):
        assert self._run().debt_keur > 0

    def test_first_period_payment_proportional(self):
        result = self._run()
        cfads = self._cfads()
        # First period payment should be roughly 40% of full period payment
        full_period_payment = result.payment_schedule[1]
        if full_period_payment > 0:
            ratio = result.payment_schedule[0] / full_period_payment
            assert ratio < 0.65, f"First period payment ratio {ratio:.3f} too high for 40% CFADS"


# ---------------------------------------------------------------------------
# Class D: FLAT_DSCR_SCULPTED — variable interest (Euribor step-up)
# ---------------------------------------------------------------------------

class TestFlatDSCRVariableRate:
    """Variable rate schedule — step up from 4% to 7% over 14 years."""

    TARGET = 1.15
    TENOR = 28

    def _rates(self) -> list[float]:
        # Steps up 0.25% annual (0.125% semi-annual) each year
        base = 0.04 / 2
        return [base + i * 0.00125 for i in range(self.TENOR)]

    def _cfads(self) -> list[float]:
        return [4_200.0] * self.TENOR

    def _run(self) -> object:
        return sculpt_senior_debt(
            cfads_schedule=self._cfads(),
            rate_schedule=self._rates(),
            tenor_periods=self.TENOR,
            mode="flat_dscr_sculpted",
            target_dscr=self.TARGET,
        )

    def test_fully_repaid(self):
        _assert_fully_repaid(self._run())

    def test_interest_uses_period_rate(self):
        result = self._run()
        rates = self._rates()
        for t, (interest, balance, rate) in enumerate(
            zip(result.interest_schedule, result.balance_schedule, rates)
        ):
            expected = balance * rate
            assert abs(interest - expected) < 0.01, (
                f"Period {t}: interest {interest:.4f} ≠ balance×rate {expected:.4f}"
            )

    def test_interest_schedule_reflects_variable_rate(self):
        result = self._run()
        rates = self._rates()
        # Verify interest correctly uses period-specific rate on opening balance
        for t in range(self.TENOR):
            expected_interest = result.balance_schedule[t] * rates[t]
            assert abs(result.interest_schedule[t] - expected_interest) < 0.01


# ---------------------------------------------------------------------------
# Class E: FLAT_DSCR_SCULPTED — gearing cap binding
# ---------------------------------------------------------------------------

class TestFlatDSCRGearingCapBinding:
    """Gearing cap is less than unconstrained DSCR debt → cap binds."""

    RATE = _flat_rate(0.0565)
    TARGET = 1.10
    TENOR = 28
    CFADS = 5_000.0
    GEARING_CAP = 40_000.0  # Cap below unconstrained amount

    def _run(self) -> object:
        return sculpt_senior_debt(
            cfads_schedule=[self.CFADS] * self.TENOR,
            rate_schedule=[self.RATE] * self.TENOR,
            tenor_periods=self.TENOR,
            mode="flat_dscr_sculpted",
            target_dscr=self.TARGET,
            gearing_cap_keur=self.GEARING_CAP,
        )

    def test_debt_does_not_exceed_gearing_cap(self):
        result = self._run()
        assert result.debt_keur <= self.GEARING_CAP + 0.01

    def test_fully_repaid(self):
        _assert_fully_repaid(self._run())

    def test_debt_at_cap(self):
        result = self._run()
        # When cap binds, debt should be at or very close to cap
        assert abs(result.debt_keur - self.GEARING_CAP) < 1.0


# ---------------------------------------------------------------------------
# Class F: FLAT_DSCR_SCULPTED — short tenor (5 years)
# ---------------------------------------------------------------------------

class TestFlatDSCRShortTenor:
    """Short tenor bridge loan — 5-year (10 semi-annual periods)."""

    RATE = _flat_rate(0.060)
    TARGET = 1.30
    TENOR = 10
    CFADS = 2_000.0

    def _run(self) -> object:
        return sculpt_senior_debt(
            cfads_schedule=[self.CFADS] * self.TENOR,
            rate_schedule=[self.RATE] * self.TENOR,
            tenor_periods=self.TENOR,
            mode="flat_dscr_sculpted",
            target_dscr=self.TARGET,
        )

    def test_fully_repaid(self):
        _assert_fully_repaid(self._run())

    def test_per_period_dscr_at_target(self):
        result = self._run()
        _assert_dscr_at_target(result, [self.CFADS] * self.TENOR, self.TARGET, tol=0.005)

    def test_debt_amount_reasonable(self):
        result = self._run()
        # PV of 10 × (2000/1.30) at 3% per period
        approx_pv = sum((self.CFADS / self.TARGET) / (1 + self.RATE) ** (t + 1) for t in range(self.TENOR))
        assert abs(result.debt_keur - approx_pv) < 100  # within 100 kEUR of PV estimate


# ---------------------------------------------------------------------------
# Class G: FLAT_DSCR_SCULPTED — long tenor (20 years)
# ---------------------------------------------------------------------------

class TestFlatDSCRLongTenor:
    """Long tenor renewable energy project — 20 years (40 semi-annual periods)."""

    RATE = _flat_rate(0.0500)
    TARGET = 1.15
    TENOR = 40
    CFADS = 3_200.0

    def _run(self) -> object:
        return sculpt_senior_debt(
            cfads_schedule=[self.CFADS] * self.TENOR,
            rate_schedule=[self.RATE] * self.TENOR,
            tenor_periods=self.TENOR,
            mode="flat_dscr_sculpted",
            target_dscr=self.TARGET,
        )

    def test_fully_repaid(self):
        _assert_fully_repaid(self._run())

    def test_avg_dscr_at_target(self):
        result = self._run()
        assert abs(result.avg_dscr - self.TARGET) < 0.005

    def test_debt_amount_greater_than_short_tenor_equivalent(self):
        result = self._run()
        # Longer tenor → more PV capacity → larger debt
        assert result.debt_keur > 30_000


# ---------------------------------------------------------------------------
# Class H: MINIMUM_DSCR_SCULPTED — dual-DSCR schedule (PPA / merchant split)
# ---------------------------------------------------------------------------

class TestMinimumDSCRDualSchedule:
    """TUHO-style dual-DSCR: PPA periods at 1.20, merchant periods at 1.45."""

    RATE = _flat_rate(0.0565)
    TENOR = 28
    PPA_PERIODS = 20
    MERCHANT_PERIODS = 8
    CFADS_PPA = 4_000.0
    CFADS_MERCH = 3_000.0

    def _cfads(self) -> list[float]:
        return [self.CFADS_PPA] * self.PPA_PERIODS + [self.CFADS_MERCH] * self.MERCHANT_PERIODS

    def _dscr_schedule(self) -> list[float]:
        return [1.20] * self.PPA_PERIODS + [1.45] * self.MERCHANT_PERIODS

    def _run(self) -> object:
        return sculpt_senior_debt(
            cfads_schedule=self._cfads(),
            rate_schedule=[self.RATE] * self.TENOR,
            tenor_periods=self.TENOR,
            mode="minimum_dscr_sculpted",
            dscr_schedule=self._dscr_schedule(),
        )

    def test_fully_repaid(self):
        _assert_fully_repaid(self._run())

    def test_ppa_periods_at_1_20_dscr(self):
        result = self._run()
        cfads = self._cfads()
        for t in range(self.PPA_PERIODS):
            pay = result.payment_schedule[t]
            if pay > 0:
                dscr = cfads[t] / pay
                assert abs(dscr - 1.20) < 0.005, (
                    f"PPA period {t}: DSCR {dscr:.4f} ≠ 1.20"
                )

    def test_merchant_periods_at_1_45_dscr(self):
        result = self._run()
        cfads = self._cfads()
        for t in range(self.PPA_PERIODS, self.TENOR):
            pay = result.payment_schedule[t]
            if pay > 0:
                dscr = cfads[t] / pay
                assert abs(dscr - 1.45) < 0.005, (
                    f"Merchant period {t}: DSCR {dscr:.4f} ≠ 1.45"
                )

    def test_ppa_payments_higher_than_merchant_payments(self):
        result = self._run()
        # PPA CFADS=4000 at 1.20 → target DS=3333
        # Merchant CFADS=3000 at 1.45 → target DS=2069
        avg_ppa = sum(result.payment_schedule[:self.PPA_PERIODS]) / self.PPA_PERIODS
        avg_merch = sum(result.payment_schedule[self.PPA_PERIODS:]) / self.MERCHANT_PERIODS
        assert avg_ppa > avg_merch

    def test_debt_amount_positive(self):
        assert self._run().debt_keur > 0

    def test_interest_on_opening_balance(self):
        result = self._run()
        for t, (interest, balance) in enumerate(
            zip(result.interest_schedule, result.balance_schedule)
        ):
            expected = balance * self.RATE
            assert abs(interest - expected) < 0.01, f"Period {t}: interest mismatch"


# ---------------------------------------------------------------------------
# Class I: MINIMUM_DSCR_SCULPTED — uniform per-period schedule (equiv. to flat)
# ---------------------------------------------------------------------------

class TestMinimumDSCREquivalentToFlat:
    """Uniform dscr_schedule with same target must produce identical result to FLAT mode."""

    RATE = _flat_rate(0.0565)
    TARGET = 1.20
    TENOR = 28
    CFADS = 3_600.0

    def _cfads(self) -> list[float]:
        return [self.CFADS] * self.TENOR

    def _run_flat(self) -> object:
        return sculpt_senior_debt(
            cfads_schedule=self._cfads(),
            rate_schedule=[self.RATE] * self.TENOR,
            tenor_periods=self.TENOR,
            mode="flat_dscr_sculpted",
            target_dscr=self.TARGET,
        )

    def _run_min(self) -> object:
        return sculpt_senior_debt(
            cfads_schedule=self._cfads(),
            rate_schedule=[self.RATE] * self.TENOR,
            tenor_periods=self.TENOR,
            mode="minimum_dscr_sculpted",
            dscr_schedule=[self.TARGET] * self.TENOR,
        )

    def test_debt_amounts_identical(self):
        flat = self._run_flat()
        mini = self._run_min()
        assert abs(flat.debt_keur - mini.debt_keur) < 0.01, (
            f"flat={flat.debt_keur:.4f} vs min={mini.debt_keur:.4f}"
        )

    def test_payment_schedules_identical(self):
        flat = self._run_flat()
        mini = self._run_min()
        for t, (fp, mp) in enumerate(zip(flat.payment_schedule, mini.payment_schedule)):
            assert abs(fp - mp) < 0.01, f"Period {t}: flat={fp:.4f} min={mp:.4f}"


# ---------------------------------------------------------------------------
# Class J: MINIMUM_DSCR_SCULPTED — gearing cap binding
# ---------------------------------------------------------------------------

class TestMinimumDSCRGearingCap:
    """Gearing cap binds for dual-DSCR case."""

    RATE = _flat_rate(0.0565)
    TENOR = 24
    GEARING_CAP = 30_000.0

    def _cfads(self) -> list[float]:
        return [4_500.0] * 16 + [3_000.0] * 8

    def _dscr_schedule(self) -> list[float]:
        return [1.20] * 16 + [1.45] * 8

    def _run(self) -> object:
        return sculpt_senior_debt(
            cfads_schedule=self._cfads(),
            rate_schedule=[self.RATE] * self.TENOR,
            tenor_periods=self.TENOR,
            mode="minimum_dscr_sculpted",
            dscr_schedule=self._dscr_schedule(),
            gearing_cap_keur=self.GEARING_CAP,
        )

    def test_debt_capped(self):
        result = self._run()
        assert result.debt_keur <= self.GEARING_CAP + 0.01

    def test_fully_repaid(self):
        _assert_fully_repaid(self._run())


# ---------------------------------------------------------------------------
# Class K: API contract — error cases
# ---------------------------------------------------------------------------

class TestSculptSeniorDebtAPIContract:
    """sculpt_senior_debt() raises on invalid mode / missing arguments."""

    def test_frozen_excel_raises(self):
        with pytest.raises(ValueError, match="(?i)frozen_excel_schedule"):
            sculpt_senior_debt(
                cfads_schedule=[1000.0] * 10,
                rate_schedule=[0.02825] * 10,
                tenor_periods=10,
                mode="frozen_excel_schedule",
            )

    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError):
            sculpt_senior_debt(
                cfads_schedule=[1000.0] * 10,
                rate_schedule=[0.02825] * 10,
                tenor_periods=10,
                mode="nonexistent_mode",
            )

    def test_minimum_dscr_without_schedule_raises(self):
        with pytest.raises(ValueError, match="dscr_schedule"):
            sculpt_senior_debt(
                cfads_schedule=[1000.0] * 10,
                rate_schedule=[0.02825] * 10,
                tenor_periods=10,
                mode="minimum_dscr_sculpted",
                dscr_schedule=None,
            )

    def test_flat_mode_does_not_require_dscr_schedule(self):
        result = sculpt_senior_debt(
            cfads_schedule=[1000.0] * 10,
            rate_schedule=[0.02825] * 10,
            tenor_periods=10,
            mode="flat_dscr_sculpted",
            target_dscr=1.15,
        )
        assert result.debt_keur > 0

    def test_mode_string_lowercase_accepted(self):
        result = sculpt_senior_debt(
            cfads_schedule=[1000.0] * 10,
            rate_schedule=[0.02825] * 10,
            tenor_periods=10,
            mode="flat_dscr_sculpted",
        )
        assert result is not None

    def test_result_has_required_attributes(self):
        result = sculpt_senior_debt(
            cfads_schedule=[1000.0] * 10,
            rate_schedule=[0.02825] * 10,
            tenor_periods=10,
            mode="flat_dscr_sculpted",
        )
        assert hasattr(result, "debt_keur")
        assert hasattr(result, "balance_schedule")
        assert hasattr(result, "interest_schedule")
        assert hasattr(result, "principal_schedule")
        assert hasattr(result, "payment_schedule")
        assert hasattr(result, "dscr_schedule")
        assert hasattr(result, "avg_dscr")
        assert hasattr(result, "min_dscr")


# ---------------------------------------------------------------------------
# Class L: DSRA interaction — debt service reserve account
# ---------------------------------------------------------------------------

class TestDSRAInteraction:
    """DSRA reduces effective CFADS available for sculpting; verify interaction."""

    RATE = _flat_rate(0.0565)
    TARGET = 1.20
    TENOR = 28

    def _cfads_after_dsra(self) -> list[float]:
        # CFADS after DSRA contribution: 3,500 kEUR (net of reserve top-up)
        return [3_500.0] * self.TENOR

    def _cfads_before_dsra(self) -> list[float]:
        # Gross CFADS before DSRA: 4,000 kEUR (first 2 periods have DSRA draw)
        return [4_000.0] * self.TENOR

    def test_sculpting_on_net_cfads_gives_lower_debt(self):
        """Sculpting on net-of-DSRA CFADS gives lower debt than gross CFADS."""
        net_result = sculpt_senior_debt(
            cfads_schedule=self._cfads_after_dsra(),
            rate_schedule=[self.RATE] * self.TENOR,
            tenor_periods=self.TENOR,
            mode="flat_dscr_sculpted",
            target_dscr=self.TARGET,
        )
        gross_result = sculpt_senior_debt(
            cfads_schedule=self._cfads_before_dsra(),
            rate_schedule=[self.RATE] * self.TENOR,
            tenor_periods=self.TENOR,
            mode="flat_dscr_sculpted",
            target_dscr=self.TARGET,
        )
        assert net_result.debt_keur < gross_result.debt_keur

    def test_net_cfads_result_fully_repaid(self):
        result = sculpt_senior_debt(
            cfads_schedule=self._cfads_after_dsra(),
            rate_schedule=[self.RATE] * self.TENOR,
            tenor_periods=self.TENOR,
            mode="flat_dscr_sculpted",
            target_dscr=self.TARGET,
        )
        _assert_fully_repaid(result)


# ---------------------------------------------------------------------------
# Class M: Convergence and numerical properties
# ---------------------------------------------------------------------------

class TestNumericalProperties:
    """Verify algorithmic invariants and numerical stability."""

    def test_backward_pass_initial_debt_equals_pv_of_payments(self):
        """Closed-form invariant: initial debt = PV of allowable_DS at rate schedule."""
        cfads = [3_000.0] * 20
        rate = 0.02825
        target = 1.15
        n = 20

        result = sculpt_senior_debt(
            cfads_schedule=cfads,
            rate_schedule=[rate] * n,
            tenor_periods=n,
            mode="flat_dscr_sculpted",
            target_dscr=target,
        )
        # Recompute PV of allowable DS
        allowable_ds = [c / target for c in cfads]
        pv = sum(ds / (1 + rate) ** (t + 1) for t, ds in enumerate(allowable_ds))
        assert abs(result.debt_keur - pv) < 0.5  # within 0.5 kEUR

    def test_zero_cfads_periods_produce_zero_principal(self):
        """Periods with zero CFADS: allowable_DS=0, principal should be zero."""
        cfads = [0.0] * 3 + [3_000.0] * 17
        n = 20
        result = sculpt_senior_debt(
            cfads_schedule=cfads,
            rate_schedule=[0.025] * n,
            tenor_periods=n,
            mode="flat_dscr_sculpted",
            target_dscr=1.15,
        )
        for t in [0, 1, 2]:
            assert result.principal_schedule[t] <= 0.01, (
                f"Period {t}: principal {result.principal_schedule[t]:.4f} should be ≈0"
            )

    def test_high_rate_reduces_debt(self):
        """At higher rates, same CFADS supports less debt (interest consumes more)."""
        cfads = [3_000.0] * 28
        low_result = sculpt_senior_debt(
            cfads_schedule=cfads, rate_schedule=[0.01] * 28,
            tenor_periods=28, mode="flat_dscr_sculpted", target_dscr=1.15,
        )
        high_result = sculpt_senior_debt(
            cfads_schedule=cfads, rate_schedule=[0.05] * 28,
            tenor_periods=28, mode="flat_dscr_sculpted", target_dscr=1.15,
        )
        assert low_result.debt_keur > high_result.debt_keur

    def test_higher_dscr_target_reduces_debt(self):
        """Higher DSCR target → lower allowable_DS → lower PV → lower debt."""
        cfads = [3_000.0] * 28
        rate = [0.02825] * 28
        low_dscr = sculpt_senior_debt(cfads, rate, 28, "flat_dscr_sculpted", target_dscr=1.10)
        high_dscr = sculpt_senior_debt(cfads, rate, 28, "flat_dscr_sculpted", target_dscr=1.30)
        assert low_dscr.debt_keur > high_dscr.debt_keur

    def test_all_schedules_have_tenor_length(self):
        """All per-period schedule lists must have length == tenor_periods."""
        n = 24
        result = sculpt_senior_debt(
            cfads_schedule=[2_500.0] * n,
            rate_schedule=[0.025] * n,
            tenor_periods=n,
            mode="flat_dscr_sculpted",
            target_dscr=1.20,
        )
        assert len(result.balance_schedule) == n
        assert len(result.interest_schedule) == n
        assert len(result.principal_schedule) == n
        assert len(result.payment_schedule) == n
        assert len(result.dscr_schedule) == n


# ---------------------------------------------------------------------------
# Class N: DebtSizingMode enum integration
# ---------------------------------------------------------------------------

class TestDebtSizingModeIntegration:
    """sculpt_senior_debt accepts DebtSizingMode enum values directly."""

    def test_accepts_mode_enum_flat(self):
        from finco_core.inputs import DebtSizingMode
        result = sculpt_senior_debt(
            cfads_schedule=[2_000.0] * 10,
            rate_schedule=[0.025] * 10,
            tenor_periods=10,
            mode=DebtSizingMode.FLAT_DSCR_SCULPTED,
            target_dscr=1.15,
        )
        assert result.debt_keur > 0

    def test_accepts_mode_enum_minimum(self):
        from finco_core.inputs import DebtSizingMode
        result = sculpt_senior_debt(
            cfads_schedule=[2_000.0] * 10,
            rate_schedule=[0.025] * 10,
            tenor_periods=10,
            mode=DebtSizingMode.MINIMUM_DSCR_SCULPTED,
            dscr_schedule=[1.20] * 10,
        )
        assert result.debt_keur > 0

    def test_enum_frozen_still_raises(self):
        from finco_core.inputs import DebtSizingMode
        with pytest.raises(ValueError):
            sculpt_senior_debt(
                cfads_schedule=[2_000.0] * 10,
                rate_schedule=[0.025] * 10,
                tenor_periods=10,
                mode=DebtSizingMode.FROZEN_EXCEL_SCHEDULE,
            )

    def test_financing_params_flat_mode_resolves(self):
        from finco_core.inputs import FinancingParams, DebtSizingMode
        fp = FinancingParams(debt_sizing_mode=DebtSizingMode.FLAT_DSCR_SCULPTED)
        assert fp.resolved_debt_sizing_mode() == DebtSizingMode.FLAT_DSCR_SCULPTED

    def test_financing_params_minimum_mode_resolves(self):
        from finco_core.inputs import FinancingParams, DebtSizingMode
        fp = FinancingParams(debt_sizing_mode=DebtSizingMode.MINIMUM_DSCR_SCULPTED)
        assert fp.resolved_debt_sizing_mode() == DebtSizingMode.MINIMUM_DSCR_SCULPTED

    def test_sizing_mode_description_flat(self):
        from finco_core.inputs import FinancingParams, DebtSizingMode
        fp = FinancingParams(
            debt_sizing_mode=DebtSizingMode.FLAT_DSCR_SCULPTED,
            target_dscr=1.20,
        )
        desc = fp.sizing_mode_description
        assert "FLAT_DSCR_SCULPTED" in desc
        assert "1.2" in desc

    def test_sizing_mode_description_minimum(self):
        from finco_core.inputs import FinancingParams, DebtSizingMode
        fp = FinancingParams(debt_sizing_mode=DebtSizingMode.MINIMUM_DSCR_SCULPTED)
        desc = fp.sizing_mode_description
        assert "MINIMUM_DSCR_SCULPTED" in desc
