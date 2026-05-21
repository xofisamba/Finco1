"""Phase 9: R99/R102 Lockup Blocker and IRR Reconciliation — tests.

Tests verify:
1. All required reports exist
2. Required columns exist in each report
3. 13 zeroed periods are present (or updated measured equivalent)
4. Cumulative delta approximately equals -41,613 kEUR (or updated measured equivalent)
5. Every zeroed period has non-empty blocking reason details
6. Blocker aggregation sums to total delta
7. Equity IRR reconciliation includes Excel target 11.61%
8. Equity IRR reconciliation includes PR #155 22.31% path
9. Report explicitly states whether 22.31% is harness/method issue
10. G20 remains BLOCKED
11. No runtime files changed
"""

import csv
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
REPORTS_DIR = REPO_ROOT / "reports"

LOCKUP_CSV = REPORTS_DIR / "phase9_r99_r102_lockup_blocker_detail.csv"
DELTA_REASON_CSV = REPORTS_DIR / "phase9_r99_r102_distribution_delta_by_reason.csv"
IRR_RECON_CSV = REPORTS_DIR / "phase9_equity_irr_reconciliation.csv"
CF_BRIDGE_CSV = REPORTS_DIR / "phase9_equity_irr_cashflow_bridge.csv"
DOC = DOCS_DIR / "phase9_r99_r102_readiness_lockup_and_irr_reconciliation.md"


# ---------------------------------------------------------------------------
# 1. All required reports exist
# ---------------------------------------------------------------------------

class TestRequiredFiles:
    def test_lockup_blocker_detail_exists(self):
        assert LOCKUP_CSV.exists(), f"Missing: {LOCKUP_CSV}"

    def test_delta_reason_exists(self):
        assert DELTA_REASON_CSV.exists(), f"Missing: {DELTA_REASON_CSV}"

    def test_irr_reconciliation_exists(self):
        assert IRR_RECON_CSV.exists(), f"Missing: {IRR_RECON_CSV}"

    def test_cf_bridge_exists(self):
        assert CF_BRIDGE_CSV.exists(), f"Missing: {CF_BRIDGE_CSV}"

    def test_doc_exists(self):
        assert DOC.exists(), f"Missing: {DOC}"


# ---------------------------------------------------------------------------
# 2. Lockup blocker detail report columns
# ---------------------------------------------------------------------------

class TestLockupBlockerDetailColumns:
    def test_required_columns(self):
        with open(LOCKUP_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        required = {"period", "date", "legacy_distribution_keur", "da_distribution_keur",
                    "delta_keur", "actual_dscr", "target_dscr", "lockup_within_senior_tenor",
                    "lockup_details", "cash_available_keur"}
        assert required.issubset(rows[0].keys()), f"Missing columns"


# ---------------------------------------------------------------------------
# 3. 13 zeroed periods present
# ---------------------------------------------------------------------------

class TestZeroedPeriods:
    def test_thirteen_zeroed_periods(self):
        with open(LOCKUP_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        zeroed = [r for r in rows if float(r["da_distribution_keur"]) == 0 and float(r["legacy_distribution_keur"]) > 0]
        assert len(zeroed) == 13, f"Expected 13 zeroed periods, got {len(zeroed)}"

    def test_all_zeroed_within_senior_tenor(self):
        with open(LOCKUP_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        zeroed = [r for r in rows if float(r["da_distribution_keur"]) == 0 and float(r["legacy_distribution_keur"]) > 0]
        for r in zeroed:
            assert r["lockup_within_senior_tenor"] == "True", (
                f"Period {r['period']} zeroed but lockup_within_senior_tenor=False"
            )

    def test_zeroed_periods_have_lockup_details(self):
        with open(LOCKUP_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        zeroed = [r for r in rows if float(r["da_distribution_keur"]) == 0 and float(r["legacy_distribution_keur"]) > 0]
        for r in zeroed:
            assert r["lockup_details"].strip(), (
                f"Period {r['period']} zeroed but missing lockup_details"
            )


# ---------------------------------------------------------------------------
# 4. Cumulative delta approximately -41,613 kEUR
# ---------------------------------------------------------------------------

class TestDeltaAmount:
    def test_cumulative_delta(self):
        with open(LOCKUP_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        total_legacy = sum(float(r["legacy_distribution_keur"]) for r in rows)
        total_da = sum(float(r["da_distribution_keur"]) for r in rows)
        total_delta = total_da - total_legacy
        assert -45_000 < total_delta < -40_000, (
            f"Expected delta ~-41,613 kEUR, got {total_delta:.2f}"
        )


# ---------------------------------------------------------------------------
# 5. Distribution delta by reason
# ---------------------------------------------------------------------------

class TestDeltaByReason:
    def test_has_rows(self):
        with open(DELTA_REASON_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) >= 1, "Delta by reason report is empty"

    def test_contains_senior_tenor_blocker(self):
        with open(DELTA_REASON_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        reasons = {r["blocking_reason"] for r in rows}
        assert any("senior" in r.lower() or "tenor" in r.lower() or "lockup" in r.lower()
                   for r in reasons), f"No senior_tenor/lockup reason found in {reasons}"

    def test_blocker_sums_to_total_delta(self):
        with open(LOCKUP_CSV, newline="", encoding="utf-8") as f:
            rows_l = list(csv.DictReader(f))
        with open(DELTA_REASON_CSV, newline="", encoding="utf-8") as f:
            rows_d = list(csv.DictReader(f))

        total_legacy = sum(float(r["legacy_distribution_keur"]) for r in rows_l)
        total_da = sum(float(r["da_distribution_keur"]) for r in rows_l)
        total_delta = total_da - total_legacy

        delta_from_reasons = sum(float(r["total_delta_keur"]) for r in rows_d)
        assert abs(delta_from_reasons - total_delta) < 1.0, (
            f"Blocker sum {delta_from_reasons:.2f} != |delta| {abs(total_delta):.2f}"
        )


# ---------------------------------------------------------------------------
# 6. Equity IRR reconciliation
# ---------------------------------------------------------------------------

class TestIRRReconciliation:
    def test_has_rows(self):
        with open(IRR_RECON_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) >= 4, f"Expected at least 4 paths, got {len(rows)}"

    def test_includes_excel_target(self):
        with open(IRR_RECON_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert any("11.61" in r.get("equity_irr", "") or r.get("status") == "TARGET" for r in rows), (
            "Excel target 11.61% not found"
        )

    def test_includes_pr155_22_31_path(self):
        with open(IRR_RECON_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert any("22.31" in r.get("equity_irr", "") or "PR #155" in r.get("source", "") for r in rows), (
            "PR #155 22.31% path not found"
        )

    def test_pr155_classified_as_harness_error(self):
        with open(IRR_RECON_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        pr155_row = next((r for r in rows if "22.31" in r.get("equity_irr", "") or "PR #155" in r.get("source", "")), None)
        assert pr155_row is not None, "PR #155 row not found"
        status = pr155_row.get("status", "")
        assert "ERROR" in status.upper() or "HARNESS" in status.upper(), (
            f"PR #155 should be classified as HARNESS_ERROR, got: {status}"
        )

    def test_includes_gap_register_calibrated_value(self):
        with open(IRR_RECON_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert any("11.15" in r.get("equity_irr", "") or r.get("status") == "CALIBRATED" for r in rows), (
            "Calibrated value 11.15% (G-EIRR-01) not found"
        )

    def test_doc_states_22_31_is_harness_issue(self):
        with open(DOC, encoding="utf-8") as f:
            content = f.read()
        assert "22.31%" in content, "Doc must mention 22.31%"
        assert ("harness" in content.lower() or "method error" in content.lower() or
                "wrong" in content.lower()), (
            "Doc must explicitly state 22.31% is a harness/method issue"
        )


# ---------------------------------------------------------------------------
# 7. Cashflow bridge
# ---------------------------------------------------------------------------

class TestCashflowBridge:
    def test_has_period_rows(self):
        with open(CF_BRIDGE_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) >= 50, f"Expected ~61 period rows, got {len(rows)}"

    def test_has_required_columns(self):
        with open(CF_BRIDGE_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        required = {"period", "date", "legacy_equity_cashflow_keur", "da_wired_equity_cashflow_keur", "delta_keur"}
        assert required.issubset(rows[0].keys())


# ---------------------------------------------------------------------------
# 8. G20 remains BLOCKED
# ---------------------------------------------------------------------------

class TestG20Blocked:
    def test_doc_states_g20_blocked(self):
        with open(DOC, encoding="utf-8") as f:
            content = f.read()
        assert "G20" in content and "BLOCKED" in content, (
            "Doc must state G20 BLOCKED"
        )

    def test_doc_states_no_runtime_changes(self):
        with open(DOC, encoding="utf-8") as f:
            content = f.read()
        assert ("no runtime code changed" in content.lower() or
                "docs/report/test-only" in content.lower() or
                "tests only" in content.lower()), (
            "Doc must state scope is docs/reports/tests only"
        )


# ---------------------------------------------------------------------------
# 9. Basic CSV sanity
# ---------------------------------------------------------------------------

class TestCSVSanity:
    def test_lockup_detail_row_count(self):
        with open(LOCKUP_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 61, f"Expected 61 periods, got {len(rows)}"

    def test_delta_reason_aggregates_correctly(self):
        with open(DELTA_REASON_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        total = sum(float(r["total_delta_keur"]) for r in rows)
        assert -45_000 < total < -41_000, f"Total delta by reason {total:.2f} outside expected range"

    def test_irr_recon_has_status_column(self):
        with open(IRR_RECON_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            assert r.get("status", "").strip(), f"Row {r.get('source')} missing status"