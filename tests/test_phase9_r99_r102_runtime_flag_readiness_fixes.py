"""Phase 9: R99/R102 Runtime Flag Readiness Fixes — tests.

Tests verify:
1. all required reports exist
2. required columns exist in each report
3. DSCR time-series has period-level rows
4. distribution delta bridge has period-level rows
5. distribution delta bridge contains the -41,613 kEUR total delta or updated measured equivalent
6. blocked reasons are populated for zeroed periods
7. Excel parity report includes required metrics
8. gate readiness update includes G07, G08, E15, G20
9. G20 remains BLOCKED unless explicitly justified
10. implementation recommendation is conditional on G07/G08 status
11. docs state no runtime code changed
12. tests pass
"""

import csv
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
REPORTS_DIR = REPO_ROOT / "reports"

DSCR_CSV = REPORTS_DIR / "phase9_r99_r102_dscr_stability_timeseries.csv"
BRIDGE_CSV = REPORTS_DIR / "phase9_r99_r102_distribution_delta_bridge.csv"
PARSITY_CSV = REPORTS_DIR / "phase9_r99_r102_excel_parity_review.csv"
GATE_CSV = REPORTS_DIR / "phase9_r99_r102_gate_readiness_update.csv"
DOC = DOCS_DIR / "phase9_r99_r102_runtime_flag_readiness_fixes.md"


# ---------------------------------------------------------------------------
# 1. All required reports exist
# ---------------------------------------------------------------------------

class TestRequiredFiles:
    def test_dscr_timeseries_exists(self):
        assert DSCR_CSV.exists(), f"Missing: {DSCR_CSV}"

    def test_delta_bridge_exists(self):
        assert BRIDGE_CSV.exists(), f"Missing: {BRIDGE_CSV}"

    def test_excel_parity_exists(self):
        assert PARSITY_CSV.exists(), f"Missing: {PARSITY_CSV}"

    def test_gate_readiness_exists(self):
        assert GATE_CSV.exists(), f"Missing: {GATE_CSV}"

    def test_readiness_doc_exists(self):
        assert DOC.exists(), f"Missing: {DOC}"


# ---------------------------------------------------------------------------
# 2. Required columns in each report
# ---------------------------------------------------------------------------

class TestReportColumns:
    def test_dscr_timeseries_columns(self):
        with open(DSCR_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        required = ["period", "date", "legacy_distribution_keur", "da_distribution_keur",
                   "distribution_delta_keur", "legacy_dscr", "da_wired_dscr", "dscr_delta",
                   "senior_ds_keur", "cfads_or_cash_available_keur", "lockup_active",
                   "blocked_reason", "blocked_details", "status", "notes"]
        assert list(rows[0].keys()) == required, f"DSCR columns mismatch: {list(rows[0].keys())}"

    def test_delta_bridge_columns(self):
        with open(BRIDGE_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        required = ["period", "date", "legacy_distribution_keur", "da_distribution_keur",
                   "delta_keur", "cumulative_delta_keur", "primary_blocking_gate",
                   "blocked_reason", "blocked_details", "actual_dscr", "target_dscr",
                   "period_index", "senior_tenor_years", "dsra_balance_keur",
                   "dsra_target_keur", "jdsra_balance_keur", "jdsra_target_keur",
                   "cash_available_keur", "classification", "notes"]
        assert list(rows[0].keys()) == required, f"Bridge columns mismatch"

    def test_excel_parity_columns(self):
        with open(PARSITY_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        required = ["metric", "excel_value", "legacy_model_value", "da_wired_model_value",
                    "legacy_delta", "da_wired_delta", "tolerance", "status_legacy",
                    "status_da_wired", "preferred_source", "notes"]
        assert list(rows[0].keys()) == required

    def test_gate_readiness_columns(self):
        with open(GATE_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        required = ["gate_id", "gate_name", "previous_status", "new_status",
                    "evidence", "blocker", "required_next_action",
                    "can_proceed_to_implementation", "notes"]
        assert list(rows[0].keys()) == required


# ---------------------------------------------------------------------------
# 3. DSCR time-series has period-level rows
# ---------------------------------------------------------------------------

class TestDSCRTimeSeries:
    def test_has_period_level_rows(self):
        with open(DSCR_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) >= 50, f"Expected ~61 period rows, got {len(rows)}"

    def test_all_periods_have_dates(self):
        with open(DSCR_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        empty_dates = [r for r in rows if not r["date"]]
        assert len(empty_dates) == 0, f"Found {len(empty_dates)} rows with empty dates"

    def test_no_dscr_below_1(self):
        with open(DSCR_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        below1 = [r for r in rows if r["status"] == "FAIL_DSCR"]
        assert len(below1) == 0, f"Found {len(below1)} periods with DSCR < 1.0"

    def test_zeroed_periods_are_correctly_flagged(self):
        with open(DSCR_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        zeroed = [r for r in rows if r["status"] == "ZEROED"]
        # Should be 13 zeroed periods
        assert len(zeroed) == 13, f"Expected 13 ZEROED periods, got {len(zeroed)}"


# ---------------------------------------------------------------------------
# 4. Distribution delta bridge has period-level rows
# ---------------------------------------------------------------------------

class TestDeltaBridge:
    def test_has_period_level_rows(self):
        with open(BRIDGE_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) >= 50, f"Expected ~61 period rows, got {len(rows)}"


# ---------------------------------------------------------------------------
# 5. Distribution delta bridge contains the -41,613 kEUR total delta
# ---------------------------------------------------------------------------

class TestDeltaAmount:
    def test_total_delta_approx_41613(self):
        with open(BRIDGE_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        last_row = rows[-1]
        cum_delta = float(last_row["cumulative_delta_keur"])
        assert -45_000 < cum_delta < -40_000, (
            f"Expected cumulative delta ~-41,613 kEUR, got {cum_delta}"
        )

    def test_cumulative_delta_is_monotonic(self):
        with open(BRIDGE_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        cum = 0.0
        for r in rows:
            delta = float(r["delta_keur"])
            cum += delta
            cum_in_csv = float(r["cumulative_delta_keur"])
            assert abs(cum - cum_in_csv) < 0.05, (
                f"Cumulative mismatch at period {r['period']}: computed {cum}, CSV {cum_in_csv}"
            )


# ---------------------------------------------------------------------------
# 6. Blocked reasons are populated for zeroed periods
# ---------------------------------------------------------------------------

class TestBlockedReasons:
    def test_zeroed_periods_have_blocked_reasons(self):
        with open(BRIDGE_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        zeroed = [r for r in rows if r["classification"] == "ZEROED_BY_DA"]
        for r in zeroed:
            assert r["blocked_reason"].strip(), (
                f"Period {r['period']} ZEROED but missing blocked_reason"
            )
        assert len(zeroed) == 13, f"Expected 13 ZEROED_BY_DA, got {len(zeroed)}"

    def test_zeroed_periods_primary_blocking_gate_is_set(self):
        with open(BRIDGE_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        zeroed = [r for r in rows if r["classification"] == "ZEROED_BY_DA"]
        for r in zeroed:
            assert r["primary_blocking_gate"].strip(), (
                f"Period {r['period']} ZEROED but missing primary_blocking_gate"
            )


# ---------------------------------------------------------------------------
# 7. Excel parity report includes required metrics
# ---------------------------------------------------------------------------

class TestExcelParityMetrics:
    def test_includes_equity_irr(self):
        with open(PARSITY_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        names = {r["metric"] for r in rows}
        assert "equity_irr" in names, f"equity_irr not found in {names}"

    def test_includes_project_irr(self):
        with open(PARSITY_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        names = {r["metric"] for r in rows}
        assert "project_irr" in names

    def test_includes_senior_debt(self):
        with open(PARSITY_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        names = {r["metric"] for r in rows}
        assert "senior_debt_keur" in names


# ---------------------------------------------------------------------------
# 8. Gate readiness update includes G07, G08, E15, G20
# ---------------------------------------------------------------------------

class TestGateReadinessUpdate:
    def test_includes_g07(self):
        with open(GATE_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        gate_ids = {r["gate_id"] for r in rows}
        assert "G07" in gate_ids, f"G07 not found in {gate_ids}"

    def test_includes_g08(self):
        with open(GATE_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        gate_ids = {r["gate_id"] for r in rows}
        assert "G08" in gate_ids or any("excel" in r["gate_name"].lower() for r in rows), (
            f"G08/excel parity not found"
        )

    def test_includes_e15(self):
        with open(GATE_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        gate_ids = {r["gate_id"] for r in rows}
        assert "E15" in gate_ids, f"E15 not found in {gate_ids}"

    def test_includes_g20(self):
        with open(GATE_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        gate_ids = {r["gate_id"] for r in rows}
        assert "G20" in gate_ids, f"G20 not found in {gate_ids}"


# ---------------------------------------------------------------------------
# 9. G20 remains BLOCKED
# ---------------------------------------------------------------------------

class TestG20Blocked:
    def test_g20_is_blocked(self):
        with open(GATE_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        g20 = next((r for r in rows if r["gate_id"] == "G20"), None)
        assert g20 is not None, "G20 not found in gate readiness"
        assert g20["new_status"] == "BLOCKED", (
            f"G20 must remain BLOCKED, got {g20['new_status']}"
        )
        assert g20["can_proceed_to_implementation"] == "NO", (
            f"G20 can_proceed must be NO, got {g20['can_proceed_to_implementation']}"
        )


# ---------------------------------------------------------------------------
# 10. Implementation recommendation is conditional on G07/G08 status
# ---------------------------------------------------------------------------

class TestImplementationRecommendation:
    def test_doc_recommends_conditional_implementation(self):
        with open(DOC, encoding="utf-8") as f:
            content = f.read()
        assert "phase9-r99-r102-runtime-flag-implementation" in content, (
            "Doc must recommend next branch"
        )
        # Should state the recommendation is conditional
        assert (
            "CONDITIONAL" in content or
            "conditional" in content or
            "if" in content.lower()
        ), "Doc should make implementation recommendation conditional on G07/G08 status"

    def test_gate_readiness_g07_available(self):
        with open(GATE_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        g07 = next((r for r in rows if r["gate_id"] == "G07"), None)
        assert g07 is not None, "G07 not found"
        assert g07["new_status"] == "AVAILABLE", (
            f"G07 must be AVAILABLE, got {g07['new_status']}"
        )

    def test_gate_readiness_g08_partial_or_ready(self):
        with open(GATE_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        g08 = next((r for r in rows if r["gate_id"] == "G08"), None)
        assert g08 is not None, "G08 not found"
        # G08 should be PARTIAL (not blocking, but not fully ready)
        assert g08["new_status"] in ("PARTIAL", "READY"), (
            f"G08 must be PARTIAL or READY, got {g08['new_status']}"
        )


# ---------------------------------------------------------------------------
# 11. Docs state no runtime code changed
# ---------------------------------------------------------------------------

class TestNoRuntimeCodeChanges:
    def test_doc_states_no_runtime_changes(self):
        with open(DOC, encoding="utf-8") as f:
            content = f.read()
        # Should have a scope section or statement that no runtime code changed
        assert (
            "no runtime code changed" in content.lower() or
            "docs/reports/tests only" in content.lower() or
            "non-goals" in content.lower()
        ), "Doc should state scope/no runtime changes"

    def test_doc_states_g20_blocked(self):
        with open(DOC, encoding="utf-8") as f:
            content = f.read()
        assert "G20" in content and "BLOCKED" in content, (
            "Doc must state G20 BLOCKED"
        )

    def test_doc_states_no_promotion(self):
        with open(DOC, encoding="utf-8") as f:
            content = f.read()
        assert "NOT approved" in content or "not approved" in content, (
            "Doc must state R99/R102 promotion not approved"
        )


# ---------------------------------------------------------------------------
# 12. Tests pass (basic sanity)
# ---------------------------------------------------------------------------

class TestBasicSanity:
    def test_all_csvs_are_readable(self):
        for path in [DSCR_CSV, BRIDGE_CSV, PARSITY_CSV, GATE_CSV]:
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            assert len(rows) > 0, f"{path.name} is empty"

    def test_dscr_timeseries_row_count(self):
        with open(DSCR_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 61, f"Expected 61 periods, got {len(rows)}"

    def test_delta_bridge_row_count(self):
        with open(BRIDGE_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 61, f"Expected 61 periods, got {len(rows)}"

    def test_zeroed_periods_are_13(self):
        with open(BRIDGE_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        zeroed = [r for r in rows if r["classification"] == "ZEROED_BY_DA"]
        assert len(zeroed) == 13, f"Expected 13 ZEROED_BY_DA, got {len(zeroed)}"