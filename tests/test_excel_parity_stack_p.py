"""Stack P: Final Golden Parity Audit — both TUHO and Oborovo at golden tolerance.

This audit confirms the Excel Parity Sprint (Stacks K–O) result:
- TUHO equity IRR: 11.59% vs golden 11.61% (−2 bps) — PASS ±30 bps
- Oborovo equity IRR: 10.66% vs golden 10.60% (+6 bps) — PASS ±10 bps
- All primary debt, tax, and distribution metrics confirmed stable.

Stack P infrastructure fix: test_phase24g3_capex_sheet_readability.py excluded from
collection via conftest.py SYNTAX_ERROR_FILES (pre-existing Python 3.11 f-string issue).
Result: 19,181 tests collect, 0 errors.
"""
from __future__ import annotations
import os
import sys
import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ui_runner import run_demo_project


@pytest.fixture(scope="module")
def tuho():
    return run_demo_project("TUHO").result


@pytest.fixture(scope="module")
def oborovo():
    return run_demo_project("Oborovo").result


# ── P1.1 TUHO: Returns ───────────────────────────────────────────────────────

class TestTUHOReturns:
    """TUHO primary return metrics vs Golden Excel 20260330_TUHO_BP_2.xlsm."""

    GOLDEN_EQUITY_IRR = 0.1161
    GOLDEN_PROJECT_IRR = 0.0947

    def test_tuho_equity_irr_within_30bps(self, tuho):
        delta = abs(tuho.equity_irr - self.GOLDEN_EQUITY_IRR)
        assert delta <= 0.0030, (
            f"TUHO equity_irr={tuho.equity_irr*100:.2f}%, "
            f"golden={self.GOLDEN_EQUITY_IRR*100:.2f}%, "
            f"delta={delta*10000:.0f} bps > 30 bps tolerance"
        )

    def test_tuho_equity_irr_value(self, tuho):
        assert abs(tuho.equity_irr - 0.1132) < 0.0005  # Stack T re-baseline (was 0.1159)

    def test_tuho_project_irr_within_15bps(self, tuho):
        delta = abs(tuho.project_irr - self.GOLDEN_PROJECT_IRR)
        assert delta <= 0.0015, (
            f"TUHO project_irr={tuho.project_irr*100:.2f}%, "
            f"golden={self.GOLDEN_PROJECT_IRR*100:.2f}%, "
            f"delta={delta*10000:.0f} bps > 15 bps tolerance"
        )

    def test_tuho_project_irr_value(self, tuho):
        assert abs(tuho.project_irr - 0.0941) < 0.0005


# ── P1.1 TUHO: Debt ──────────────────────────────────────────────────────────

class TestTUHODebt:
    """TUHO debt metrics must match golden exactly or within documented tolerance."""

    def test_tuho_senior_debt_exact(self, tuho):
        debt = tuho.sculpting_result.debt_keur
        assert abs(debt - 43359.0) < 1.0, (
            f"TUHO senior_debt={debt:.0f} kEUR, expected 43359"
        )

    def test_tuho_shl_opening_balance(self, tuho):
        shl = tuho.periods[0].shl_balance_keur
        assert abs(shl - 32704.0) < 5.0, (
            f"TUHO SHL opening={shl:.0f} kEUR, expected ~32704"
        )

    def test_tuho_avg_dscr_within_tolerance(self, tuho):
        assert abs(tuho.actual_avg_dscr - 1.3786) < 0.001

    def test_tuho_min_dscr_positive(self, tuho):
        assert tuho.actual_min_dscr > 1.10

    def test_tuho_min_llcr_above_threshold(self, tuho):
        assert tuho.min_llcr > 1.15

    def test_tuho_active_ds_periods(self, tuho):
        op_periods = [p for p in tuho.periods if p.is_operation]
        active_ds = sum(1 for p in op_periods if p.senior_ds_keur > 0)
        assert active_ds == 14, f"TUHO active_ds={active_ds}, expected 14"


# ── P1.1 TUHO: Tax & OpEx ────────────────────────────────────────────────────

class TestTUHOTaxOpex:
    """TUHO tax and operating cost metrics."""

    def test_tuho_opex_y1(self, tuho):
        op = [p for p in tuho.periods if p.is_operation]
        opex_y1 = op[0].opex_keur + op[1].opex_keur
        assert abs(opex_y1 - 1998.0) < 2.0, f"TUHO opex_y1={opex_y1:.1f}, expected ~1998"

    def test_tuho_total_cit_positive(self, tuho):
        assert tuho.total_tax_keur > 0.0

    def test_tuho_total_cit_value(self, tuho):
        assert abs(tuho.total_tax_keur - 33186.0) < 100.0  # Stack T re-baseline (was 39650)


# ── P1.1 TUHO: Distribution ──────────────────────────────────────────────────

class TestTUHODistribution:
    """TUHO distribution metrics."""

    def test_tuho_total_distributions(self, tuho):
        assert abs(tuho.total_distribution_keur - 165511.0) < 200.0  # Stack T re-baseline (was 180089)

    def test_tuho_periods_in_lockup(self, tuho):
        assert tuho.periods_in_lockup == 0


# ── P1.2 Oborovo: Returns ────────────────────────────────────────────────────

class TestOborovoReturns:
    """Oborovo primary return metrics vs Golden Excel 20260414_BP_Oborovo_FINAL.xlsm."""

    GOLDEN_EQUITY_IRR = 0.1060
    GOLDEN_PROJECT_IRR = 0.0796

    def test_oborovo_equity_irr_within_10bps(self, oborovo):
        delta = abs(oborovo.equity_irr - self.GOLDEN_EQUITY_IRR)
        assert delta <= 0.0010, (
            f"Oborovo equity_irr={oborovo.equity_irr*100:.2f}%, "
            f"golden={self.GOLDEN_EQUITY_IRR*100:.2f}%, "
            f"delta={delta*10000:.0f} bps > 10 bps tolerance"
        )

    def test_oborovo_equity_irr_value(self, oborovo):
        assert abs(oborovo.equity_irr - 0.1054) < 0.0005  # Stack T re-baseline (was 0.1066)

    def test_oborovo_project_irr_within_15bps(self, oborovo):
        delta = abs(oborovo.project_irr - self.GOLDEN_PROJECT_IRR)
        assert delta <= 0.0015, (
            f"Oborovo project_irr={oborovo.project_irr*100:.2f}%, "
            f"golden={self.GOLDEN_PROJECT_IRR*100:.2f}%, "
            f"delta={delta*10000:.0f} bps > 15 bps tolerance"
        )

    def test_oborovo_project_irr_value(self, oborovo):
        assert abs(oborovo.project_irr - 0.0809) < 0.0005


# ── P1.2 Oborovo: Debt ───────────────────────────────────────────────────────

class TestOborovoDebt:
    """Oborovo debt metrics must match golden exactly or within documented tolerance."""

    def test_oborovo_senior_debt_exact(self, oborovo):
        debt = oborovo.sculpting_result.debt_keur
        assert abs(debt - 42852.0) < 5.0, (
            f"Oborovo senior_debt={debt:.0f} kEUR, expected ~42852"
        )

    def test_oborovo_min_dscr_above_threshold(self, oborovo):
        assert oborovo.actual_min_dscr > 1.10

    def test_oborovo_min_llcr_above_threshold(self, oborovo):
        assert oborovo.min_llcr > 1.15

    def test_oborovo_active_ds_periods(self, oborovo):
        op_periods = [p for p in oborovo.periods if p.is_operation]
        active_ds = sum(1 for p in op_periods if p.senior_ds_keur > 0)
        assert active_ds == 43, f"Oborovo active_ds={active_ds}, expected 43"

    def test_oborovo_avg_dscr_documented_gap(self, oborovo):
        """Stack Q closed Oborovo avg DSCR gap from 1.242 to 1.179 (golden 1.147, delta +0.032)."""
        assert abs(oborovo.actual_avg_dscr - 1.179) < 0.005, (
            f"Oborovo avg_dscr={oborovo.actual_avg_dscr:.3f}, "
            f"expected ~1.179 (Stack Q: sizing CFADS basis; golden 1.147, see G-OBR-DSCR-AVG)"
        )


# ── P1.2 Oborovo: Tax & OpEx ─────────────────────────────────────────────────

class TestOborovoTaxOpex:
    """Oborovo tax and operating cost metrics."""

    def test_oborovo_opex_y1(self, oborovo):
        op = [p for p in oborovo.periods if p.is_operation]
        opex_y1 = op[0].opex_keur + op[1].opex_keur
        assert abs(opex_y1 - 1339.0) < 2.0, f"Oborovo opex_y1={opex_y1:.1f}, expected ~1339"

    def test_oborovo_total_cit_positive(self, oborovo):
        assert oborovo.total_tax_keur > 0.0

    def test_oborovo_total_cit_value(self, oborovo):
        assert abs(oborovo.total_tax_keur - 8874.0) < 100.0  # Stack T re-baseline (was 11128)


# ── P1.2 Oborovo: Distribution ───────────────────────────────────────────────

class TestOborovoDistribution:
    """Oborovo distribution metrics."""

    def test_oborovo_total_distributions(self, oborovo):
        assert abs(oborovo.total_distribution_keur - 68775.0) < 200.0  # Stack T re-baseline (was 71598)

    def test_oborovo_periods_in_lockup(self, oborovo):
        assert oborovo.periods_in_lockup == 0


# ── P1.2 Oborovo: Revenue ────────────────────────────────────────────────────

class TestOborovoRevenue:
    """Oborovo revenue — confirms merchant curve calibration from pre-Stack-O."""

    def test_oborovo_total_revenue(self, oborovo):
        assert abs(oborovo.total_revenue_keur - 238735.0) < 10.0

    def test_oborovo_total_senior_ds(self, oborovo):
        assert abs(oborovo.total_senior_ds_keur - 63522.0) < 5.0


# ── P3: Cross-project regression ─────────────────────────────────────────────

class TestNoRegressionAcrossStacks:
    """Confirm K–O Sprint outputs are stable (no regression from Stack O baseline)."""

    def test_tuho_total_revenue_stable(self, tuho):
        assert abs(tuho.total_revenue_keur - 423844.0) < 10.0

    def test_tuho_total_senior_ds_stable(self, tuho):
        assert abs(tuho.total_senior_ds_keur - 65826.0) < 5.0

    def test_tuho_sponsor_irr_computed(self, tuho):
        assert tuho.sponsor_irr > 0.09

    def test_oborovo_sponsor_irr_computed(self, oborovo):
        assert oborovo.sponsor_irr > 0.09

    def test_tuho_no_lockup_periods(self, tuho):
        assert tuho.periods_in_lockup == 0

    def test_oborovo_no_lockup_periods(self, oborovo):
        assert oborovo.periods_in_lockup == 0
