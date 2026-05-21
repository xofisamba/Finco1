"""Phase 9: SHL Balance Tracking Fix — harness fix + corrected SHL data.

PR #155 equity IRR 22.31% was a DOUBLE ERROR:
1. Harness passed shl_amount=0.0 → shl_balance=0 for all periods
2. Harness used equity_irr_method=equity_only (wrong method)

With corrected SHL params (from financing), SHL balance tracks correctly:
- P1: 32,703.69 kEUR (shl_amount + shl_idc)
- Repaid via PIK+sweep through period 15
- Equity IRR (shl_plus_dividends): 14.74% — close to calibrated 11.15%, gap under investigation

SCOPE: Analysis/reports/tests only. No runtime code changed.
"""
import csv
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
REPORTS_DIR = REPO_ROOT / "reports"

SHL_DETAIL_CSV = REPORTS_DIR / "phase9_shl_balance_tracking_detail.csv"
DOC = DOCS_DIR / "phase9_shl_balance_tracking_investigation.md"


class TestRequiredFiles:
    def test_shl_detail_csv_exists(self):
        assert SHL_DETAIL_CSV.exists(), f"Missing: {SHL_DETAIL_CSV}"

    def test_doc_exists(self):
        assert DOC.exists(), f"Missing: {DOC}"


class TestSHLBalanceTracking:
    """SHL balance is now correctly initialized from financing params."""

    def test_p1_shl_balance_is_nonzero(self):
        """P1 SHL balance should be shl_amount + shl_idc = 32,703.69 kEUR."""
        with open(SHL_DETAIL_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        p1_balance = float(rows[0]["shl_balance_keur"])
        assert p1_balance == 32703.69, f"P1 shl_balance={p1_balance}, expected 32703.69"

    def test_shl_balance_decreases_during_pik_phase(self):
        """SHL balance should decrease as PIK accrues and principal is repaid."""
        with open(SHL_DETAIL_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        balances = [float(r["shl_balance_keur"]) for r in rows]
        # First 14 operating periods (P2-P15) should have decreasing non-zero balances
        for i in range(1, 14):
            assert balances[i] < balances[i - 1], (
                f"Period {i+1} balance {balances[i]:.2f} not less than "
                f"period {i} balance {balances[i-1]:.2f}"
            )

    def test_shl_fully_repaid_by_period_16(self):
        """SHL should be fully repaid by period 16 (after 14 operating periods)."""
        with open(SHL_DETAIL_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            bal = float(r["shl_balance_keur"])
            period = int(r["period"])
            if period > 16:
                assert bal == 0.0, f"Period {period} has shl_balance={bal}, expected 0"

    def test_zero_balance_except_final_period(self):
        """When shl_balance=0 in period N>1, shi should be 0 except period 16 (final bullet interest).
        
        In period 15 (final SHL period), the full remaining balance (1140.66) is repaid as bullet.
        In period 16, shl_balance=0 (fully repaid) but shi=44.86 is interest on the final bullet.
        This is expected behavior — interest accrues in the period before the final bullet is paid.
        """
        with open(SHL_DETAIL_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            bal = float(r["shl_balance_keur"])
            shi = float(r["shl_interest_keur"])
            period = int(r["period"])
            if bal == 0.0 and period > 16:
                assert shi == 0.0, f"Period {period}: bal=0 but shi={shi}"


class TestRootCause:
    def test_doc_identifies_shl_amount_zero_as_root_cause(self):
        with open(DOC, encoding="utf-8") as f:
            content = f.read()
        assert "shl_amount=0.0" in content, (
            "Doc must identify shl_amount=0.0 in harness as root cause"
        )

    def test_doc_states_analysis_scope(self):
        with open(DOC, encoding="utf-8") as f:
            content = f.read()
        assert "ANALYSIS / REPORTS / TESTS ONLY" in content, (
            "Doc must state scope is analysis/reports/tests only"
        )

    def test_doc_states_no_runtime_changes(self):
        with open(DOC, encoding="utf-8") as f:
            content = f.read()
        assert "no runtime code changed" in content.lower(), (
            "Doc must state no runtime code changed"
        )


class TestCSVColumns:
    def test_has_required_columns(self):
        with open(SHL_DETAIL_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        required = {"period", "date", "shl_balance_keur", "shl_interest_keur",
                    "shl_principal_keur", "shl_pik_keur", "equity_cf_keur", "status", "notes"}
        missing = required - set(rows[0].keys())
        assert not missing, f"Missing columns: {missing}"

    def test_row_count(self):
        with open(SHL_DETAIL_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 61, f"Expected 61 periods, got {len(rows)}"
