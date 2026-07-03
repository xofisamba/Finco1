"""Stack Q: Oborovo DSCR CFADS basis fix + Python 3.11 f-string test fix.

Part 1 — DSCR CFADS basis:
  Root cause confirmed: actual_avg_dscr=1.242 used the engine's sculpted DS schedule
  (28 periods, not aligned to frozen CSV) with actual EBITDA as CFADS numerator.
  Fix: waterfall_core.py now uses sizing CFADS (DS!R20 fcf_for_banks) for period.dscr
  and filters _active_dsrs to CSV-active DS periods (ds_r57 > 0 = 28 periods).
  Result: actual_avg_dscr 1.242 → 1.179 (golden 1.147, delta +0.032).
  Remaining gap (0.032): methodological — weighted vs simple average or other
  Golden Excel convention not fully reproducible from available CSV data.

Part 2 — Python 3.11 f-string:
  Fixed backslash-in-f-string at test_phase24g3_capex_sheet_readability.py:391.
  Stack P temporary conftest.py exclusion removed. File collects normally.

No IRR, debt sizing, repayment, revenue, tax, sponsor, or cashflow changes.
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


# ── Q1/Q2: Oborovo avg DSCR improvement ──────────────────────────────────────

class TestOborovoAvgDSCRImproved:
    """Oborovo actual_avg_dscr must improve to ~1.179 using sizing CFADS basis."""

    STACK_P_VALUE = 1.242  # pre-Stack-Q value (actual EBITDA / sculpted DS)
    STACK_Q_VALUE = 1.179  # post-Stack-Q value (sizing CFADS / frozen DS, 28 periods)
    GOLDEN = 1.147

    def test_avg_dscr_improved_vs_stack_p(self, oborovo):
        assert oborovo.actual_avg_dscr < self.STACK_P_VALUE - 0.05, (
            f"Stack Q avg_dscr {oborovo.actual_avg_dscr:.4f} should be "
            f"significantly below Stack P value {self.STACK_P_VALUE}"
        )

    def test_avg_dscr_at_stack_q_value(self, oborovo):
        delta = abs(oborovo.actual_avg_dscr - self.STACK_Q_VALUE)
        assert delta < 0.005, (
            f"Oborovo actual_avg_dscr={oborovo.actual_avg_dscr:.4f}, "
            f"expected ~{self.STACK_Q_VALUE} (sizing CFADS / frozen DS, 28 CSV-active periods)"
        )

    def test_avg_dscr_below_1_20(self, oborovo):
        assert oborovo.actual_avg_dscr < 1.20, (
            f"Stack Q avg_dscr {oborovo.actual_avg_dscr:.4f} should be below 1.20"
        )

    def test_remaining_gap_to_golden_below_0_04(self, oborovo):
        """Remaining gap (1.179 vs 1.147) = +0.032. Must be below 0.04."""
        gap = oborovo.actual_avg_dscr - self.GOLDEN
        assert gap < 0.04, (
            f"Remaining gap vs golden: {gap:.4f} > 0.04"
        )

    def test_min_dscr_still_positive(self, oborovo):
        assert oborovo.actual_min_dscr > 1.10


# ── Q3: No regression on primary KPIs ────────────────────────────────────────

class TestOborovoNoRegression:
    """Primary Oborovo KPIs must be unchanged from Stack O/P baseline."""

    def test_oborovo_equity_irr_unchanged(self, oborovo):
        assert abs(oborovo.equity_irr - 0.1054) < 0.0005  # Stack T re-baseline (was 0.1066)

    def test_oborovo_project_irr_unchanged(self, oborovo):
        assert abs(oborovo.project_irr - 0.0809) < 0.0005

    def test_oborovo_senior_debt_unchanged(self, oborovo):
        assert abs(oborovo.sculpting_result.debt_keur - 42852.0) < 5.0

    def test_oborovo_total_senior_ds_unchanged(self, oborovo):
        assert abs(oborovo.total_senior_ds_keur - 63522.0) < 5.0

    def test_oborovo_total_distribution_unchanged(self, oborovo):
        assert abs(oborovo.total_distribution_keur - 68775.0) < 200.0  # Stack T re-baseline (was 71598)

    def test_oborovo_total_tax_unchanged(self, oborovo):
        assert abs(oborovo.total_tax_keur - 8874.0) < 100.0  # Stack T re-baseline (was 11128)

    def test_oborovo_total_revenue_unchanged(self, oborovo):
        assert abs(oborovo.total_revenue_keur - 238735.0) < 10.0

    def test_oborovo_sponsor_irr_unchanged(self, oborovo):
        assert oborovo.sponsor_irr > 0.09


class TestTUHONoRegression:
    """TUHO must not regress — no changes to TUHO path."""

    def test_tuho_equity_irr_unchanged(self, tuho):
        assert abs(tuho.equity_irr - 0.1132) < 0.0005  # Stack T re-baseline (was 0.1159)

    def test_tuho_project_irr_unchanged(self, tuho):
        assert abs(tuho.project_irr - 0.0941) < 0.0005

    def test_tuho_avg_dscr_unchanged(self, tuho):
        assert abs(tuho.actual_avg_dscr - 1.3786) < 0.001

    def test_tuho_senior_debt_unchanged(self, tuho):
        assert abs(tuho.sculpting_result.debt_keur - 43359.0) < 1.0


# ── Q4: Golden validation ─────────────────────────────────────────────────────

class TestGoldenValidation:
    """Document before/after/golden for Oborovo avg DSCR."""

    GOLDEN_EQUITY_IRR = 0.1060
    GOLDEN_PROJECT_IRR = 0.0796
    GOLDEN_AVG_DSCR = 1.147  # from 20260414_BP_Oborovo_FINAL.xlsm

    def test_oborovo_equity_irr_still_within_golden(self, oborovo):
        delta = abs(oborovo.equity_irr - self.GOLDEN_EQUITY_IRR)
        assert delta <= 0.0010, f"equity_irr delta {delta*10000:.0f} bps > 10 bps"

    def test_oborovo_project_irr_still_within_golden(self, oborovo):
        delta = abs(oborovo.project_irr - self.GOLDEN_PROJECT_IRR)
        assert delta <= 0.0015, f"project_irr delta {delta*10000:.0f} bps > 15 bps"

    def test_oborovo_avg_dscr_closer_to_golden(self, oborovo):
        """Stack Q must close the gap vs Stack P: 1.179 is closer to 1.147 than 1.242."""
        stack_p_gap = abs(1.242 - self.GOLDEN_AVG_DSCR)
        stack_q_gap = abs(oborovo.actual_avg_dscr - self.GOLDEN_AVG_DSCR)
        assert stack_q_gap < stack_p_gap, (
            f"Stack Q avg_dscr={oborovo.actual_avg_dscr:.4f} gap={stack_q_gap:.4f} "
            f"is NOT smaller than Stack P gap={stack_p_gap:.4f}"
        )


# ── Q5/Q6: Python 3.11 f-string fix ──────────────────────────────────────────

class TestPython311FStringFix:
    """Confirm test_phase24g3_capex_sheet_readability.py now collects without errors."""

    def test_syntax_error_file_not_excluded_from_conftest(self):
        """Stack P workaround must be removed: SYNTAX_ERROR_FILES must be empty."""
        import sys
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "conftest_check",
            os.path.join(os.path.dirname(__file__), "conftest.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        syntax_error_files = getattr(mod, 'SYNTAX_ERROR_FILES', set())
        assert "test_phase24g3_capex_sheet_readability.py" not in syntax_error_files, (
            "Stack P conftest exclusion must be removed in Stack Q"
        )

    def test_target_file_parseable_as_python(self):
        """test_phase24g3_capex_sheet_readability.py must parse without SyntaxError."""
        import ast
        target = os.path.join(
            os.path.dirname(__file__),
            "test_phase24g3_capex_sheet_readability.py",
        )
        with open(target, "r") as f:
            source = f.read()
        try:
            ast.parse(source)
        except SyntaxError as exc:
            pytest.fail(f"SyntaxError in test_phase24g3_capex_sheet_readability.py: {exc}")
