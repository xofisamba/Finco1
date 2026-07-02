"""Stack O: Oborovo equity IRR method calibration tests.

Root cause: equity_irr_method="combined" (investment=capex-debt, CF=distributions only)
gave 6.24% vs Golden Excel 10.60%. The Golden Excel computes equity IRR from the
SHL+share_capital investor perspective: SHL interest while SHL outstanding, then
dividends after SHL repaid — matching "shl_plus_dividends".

Fix: equity_irr_method changed to "shl_plus_dividends" in create_default_oborovo().
Result: 10.66% vs golden 10.60% — delta +6 bps, PASS.
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


# ── Oborovo equity IRR parity ─────────────────────────────────────────────────

class TestOborovoEquityIRR:
    """Oborovo equity IRR must match Golden Excel 10.60% within ±10 bps."""

    GOLDEN = 0.1060
    STACK_N_VALUE = 0.0624  # pre-Stack-O value (combined method)
    TOLERANCE = 0.0010  # ±10 bps

    def test_oborovo_equity_irr_improved_vs_stack_n(self, oborovo_result):
        assert oborovo_result.equity_irr > self.STACK_N_VALUE + 0.03, (
            f"Stack O equity IRR {oborovo_result.equity_irr:.4f} should be "
            f"significantly above Stack N combined-method value {self.STACK_N_VALUE}"
        )

    def test_oborovo_equity_irr_within_golden_tolerance(self, oborovo_result):
        delta = abs(oborovo_result.equity_irr - self.GOLDEN)
        assert delta <= self.TOLERANCE, (
            f"Oborovo equity_irr={oborovo_result.equity_irr*100:.2f}%, "
            f"golden={self.GOLDEN*100:.2f}%, delta={delta*10000:.0f} bps > "
            f"tolerance {self.TOLERANCE*10000:.0f} bps"
        )

    def test_oborovo_equity_irr_above_threshold(self, oborovo_result):
        assert oborovo_result.equity_irr > 0.1050, (
            f"Oborovo equity_irr {oborovo_result.equity_irr:.4f} must be above 10.50%"
        )


# ── Merchant curve unchanged ──────────────────────────────────────────────────

class TestMerchantCurveUnchanged:
    """Project IRR and total revenue must be unchanged (merchant curve was already calibrated)."""

    GOLDEN_PROJECT_IRR = 0.0796
    STACK_N_TOTAL_REVENUE = 238734.9

    def test_oborovo_project_irr_unchanged(self, oborovo_result):
        """Project IRR must remain calibrated — merchant curve not changed."""
        delta = abs(oborovo_result.project_irr - self.GOLDEN_PROJECT_IRR)
        assert delta < 0.0015, (
            f"project_irr changed: {oborovo_result.project_irr:.4f} vs "
            f"golden {self.GOLDEN_PROJECT_IRR:.4f}"
        )

    def test_oborovo_total_revenue_unchanged(self, oborovo_result):
        """Total revenue must be unchanged — only equity IRR method changed."""
        delta = abs(oborovo_result.total_revenue_keur - self.STACK_N_TOTAL_REVENUE)
        assert delta < 10.0, (
            f"total_revenue_keur changed: {oborovo_result.total_revenue_keur:.1f} "
            f"vs expected {self.STACK_N_TOTAL_REVENUE}"
        )

    def test_oborovo_total_senior_ds_unchanged(self, oborovo_result):
        assert abs(oborovo_result.total_senior_ds_keur - 63522.4) < 5.0

    def test_oborovo_avg_dscr_unchanged(self, oborovo_result):
        # Stack Q improved Oborovo avg DSCR to 1.179 (sizing CFADS basis).
        assert abs(oborovo_result.actual_avg_dscr - 1.179) < 0.005

    def test_oborovo_min_dscr_positive(self, oborovo_result):
        assert oborovo_result.actual_min_dscr > 1.0


# ── TUHO not regressed ────────────────────────────────────────────────────────

class TestTUHONotRegressed:
    """TUHO must not change — it already uses shl_plus_dividends."""

    TUHO_EQUITY_IRR = 0.1159
    TUHO_PROJECT_IRR = 0.0941
    TUHO_AVG_DSCR = 1.3786

    def test_tuho_equity_irr_unchanged(self, tuho_result):
        delta = abs(tuho_result.equity_irr - self.TUHO_EQUITY_IRR)
        assert delta < 0.001, (
            f"TUHO equity_irr changed: {tuho_result.equity_irr:.4f}"
        )

    def test_tuho_project_irr_unchanged(self, tuho_result):
        delta = abs(tuho_result.project_irr - self.TUHO_PROJECT_IRR)
        assert delta < 0.0005

    def test_tuho_avg_dscr_unchanged(self, tuho_result):
        delta = abs(tuho_result.actual_avg_dscr - self.TUHO_AVG_DSCR)
        assert delta < 0.001
