"""Stack L: DSCR denominator calibration tests.

Verifies that actual_avg_dscr is averaged only over active debt-service periods
after the frozen DS override in waterfall_core.py, matching Golden Excel methodology.
"""
from __future__ import annotations
import os
import sys
import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ui_runner import run_demo_project


@pytest.fixture(scope="module")
def tuho_result():
    return run_demo_project("TUHO").result


@pytest.fixture(scope="module")
def oborovo_result():
    return run_demo_project("Oborovo").result


# ── Active debt-service periods ───────────────────────────────────────────────

class TestActiveDSPeriods:
    """Post-repayment periods must have senior_ds_keur == 0."""

    def test_tuho_has_28_active_ds_periods(self, tuho_result):
        # Y1: senior_ds_keur = engine value (interest + principal). TUHO 14-year
        # tenor = 28 semi-annual periods all with DS > 0. Pre-Y1 frozen overlay
        # only populated 14 of 28 entries so this test expected 14.
        active = [p for p in tuho_result.periods if p.senior_ds_keur > 0]
        assert len(active) == 28, f"Expected 28 active DS periods, got {len(active)}"

    def test_tuho_post_repayment_periods_have_zero_ds(self, tuho_result):
        zero_ds = [p for p in tuho_result.periods if p.senior_ds_keur == 0]
        assert len(zero_ds) > 0, "Expected some post-repayment zero-DS periods"
        # All post-repayment periods should have DSCR = inf (no debt service)
        inf_dsrs = [p for p in zero_ds if p.dscr == float("inf")]
        assert len(inf_dsrs) == len(zero_ds), (
            f"Expected all zero-DS periods to have inf DSCR, "
            f"got {len(inf_dsrs)} of {len(zero_ds)}"
        )

    def test_oborovo_has_28_active_ds_periods(self, oborovo_result):
        # Y1: senior_ds_keur = engine value (interest + principal). Oborovo 14-year
        # tenor = 28 semi-annual periods all with DS > 0. Pre-Y1 frozen overlay
        # mapped to 43 periods from the fixture CSV.
        active = [p for p in oborovo_result.periods if p.senior_ds_keur > 0]
        assert len(active) == 28, f"Expected 28 active DS periods, got {len(active)}"


# ── TUHO avg DSCR improvement ─────────────────────────────────────────────────

class TestTUHOAvgDSCR:
    """TUHO actual_avg_dscr must match Golden Excel 1.371 within tolerance."""

    GOLDEN = 1.3713
    TOLERANCE = 0.02  # tighter than Stack K ±0.05, wider than ±0.01 for engine rounding

    def test_tuho_avg_dscr_within_golden_tolerance(self, tuho_result):
        actual = tuho_result.actual_avg_dscr
        delta = abs(actual - self.GOLDEN)
        assert delta <= self.TOLERANCE, (
            f"TUHO actual_avg_dscr={actual:.4f}, golden={self.GOLDEN}, "
            f"delta={delta:.4f} > tolerance={self.TOLERANCE}"
        )

    def test_tuho_avg_dscr_improved_vs_stack_k(self, tuho_result):
        """Stack K engine value was 1.554. Stack L must be meaningfully lower."""
        STACK_K_VALUE = 1.554
        actual = tuho_result.actual_avg_dscr
        assert actual < STACK_K_VALUE - 0.10, (
            f"Stack L avg DSCR {actual:.4f} should be significantly lower than "
            f"Stack K value {STACK_K_VALUE}"
        )

    def test_tuho_avg_dscr_is_avg_of_fixture_active_period_dscs(self, tuho_result):
        """actual_avg_dscr must equal the mean of fixture-active DSCRs.

        Y1: frozen overlay no longer sets senior_ds_keur for non-fixture periods.
        actual_avg_dscr is computed over fixture-active periods (frozen_value > 0).
        Non-fixture periods have engine DS > 0 but their DSCR is not included.
        """
        # Fixture-active periods: those with _frozen_senior_ds_capacity_keur > 0
        fixture_active_dsrs = [
            p.dscr for p in tuho_result.periods
            if getattr(p, '_frozen_senior_ds_capacity_keur', 0) > 0
            and p.dscr not in (float("inf"), float("-inf"))
            and p.dscr == p.dscr  # NaN guard
        ]
        expected = sum(fixture_active_dsrs) / len(fixture_active_dsrs)
        actual = tuho_result.actual_avg_dscr
        assert abs(actual - expected) < 1e-6, (
            f"actual_avg_dscr {actual} ≠ fixture-active-period mean {expected}"
        )


# ── TUHO min DSCR unchanged ───────────────────────────────────────────────────

class TestTUHOMinDSCR:
    """Min DSCR should be unchanged — it was always computed from active periods."""

    def test_tuho_min_dscr_positive(self, tuho_result):
        assert tuho_result.actual_min_dscr > 1.0

    def test_tuho_min_dscr_matches_active_period_min(self, tuho_result):
        active_dsrs = [
            p.dscr for p in tuho_result.periods
            if p.senior_ds_keur > 0 and p.dscr != float("inf")
        ]
        expected_min = min(active_dsrs)
        assert abs(tuho_result.actual_min_dscr - expected_min) < 1e-6


# ── Oborovo not regressed ──────────────────────────────────────────────────────

class TestOborovoNotRegressed:
    """Oborovo actual_avg_dscr must not be worsened by the Stack L fix.

    Oborovo's DSCR gap is a merchant-curve numerator issue (Stack N), not
    a denominator issue. The guard in waterfall_core.py must prevent regression.
    """

    STACK_K_VALUE = 1.242  # pre-Stack-L Oborovo actual_avg_dscr
    STACK_Q_VALUE = 1.179  # Stack Q: sizing CFADS basis, 28 CSV-active DS periods

    def test_oborovo_avg_dscr_not_worsened(self, oborovo_result):
        actual = oborovo_result.actual_avg_dscr
        # Stack Q improved Oborovo avg DSCR from 1.242 to 1.179 (sizing CFADS basis).
        # Must be at or below the Stack L baseline (1.242) — no regression allowed.
        assert actual <= self.STACK_K_VALUE + 0.001, (
            f"Oborovo actual_avg_dscr regressed above Stack L value {self.STACK_K_VALUE}: "
            f"got {actual:.4f}"
        )

    def test_oborovo_min_dscr_near_target(self, oborovo_result):
        assert 1.10 < oborovo_result.actual_min_dscr < 1.30


# ── Debt schedule unchanged ───────────────────────────────────────────────────

class TestDebtScheduleUnchanged:
    """Debt amounts, principal, and interest must be unchanged."""

    def test_tuho_total_senior_ds_positive(self, tuho_result):
        assert tuho_result.total_senior_ds_keur > 0

    def test_tuho_has_post_repayment_zero_ds_periods(self, tuho_result):
        """After the last active DS period, all subsequent periods have zero DS."""
        zero_ds = [p for p in tuho_result.periods if p.senior_ds_keur == 0]
        assert len(zero_ds) > 0, "Expected post-repayment zero-DS periods"

    def test_oborovo_total_senior_ds_positive(self, oborovo_result):
        assert oborovo_result.total_senior_ds_keur > 0
