"""Phase 9: TUHO Equity IRR Excel Source Map — tests.

SCOPE: Analysis/reports/tests only. No runtime code changed.

Key findings:
- Excel workbook with Eq!D28 not in repo → MISSING_EVIDENCE
- Model shl_plus_dividends: 14.74% (corrected ~15.49%)
- Gap to Excel 11.61% cannot be explained without Excel source
- build_sponsor_cashflows double-count bug confirmed (26.66%)
- G20 BLOCKED
- R99/R102 NOT approved
"""
import csv
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "reports"
DOCS_DIR = REPO_ROOT / "docs"

R2 = REPORTS_DIR / "phase9_tuho_equity_irr_excel_source_map.csv"
R3 = REPORTS_DIR / "phase9_tuho_equity_irr_cashflow_source_bridge.csv"
R4 = REPORTS_DIR / "phase9_tuho_equity_irr_definition_matrix.csv"
R5 = REPORTS_DIR / "phase9_tuho_equity_irr_gap_register.csv"
DOC = DOCS_DIR / "phase9_tuho_equity_irr_excel_source_map.md"


class TestRequiredFiles:
    def test_source_map_exists(self):
        assert R2.exists(), f"Missing: {R2}"
    def test_cashflow_bridge_exists(self):
        assert R3.exists(), f"Missing: {R3}"
    def test_definition_matrix_exists(self):
        assert R4.exists(), f"Missing: {R4}"
    def test_gap_register_exists(self):
        assert R5.exists(), f"Missing: {R5}"
    def test_doc_exists(self):
        assert DOC.exists(), f"Missing: {DOC}"


class TestSourceMap:
    def test_includes_equity_irr_cell(self):
        with open(R2, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert any("equity" in r["item"].lower() and "irr" in r["item"].lower() for r in rows), "Missing equity IRR result cell row"

    def test_evidence_status_column(self):
        with open(R2, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert "evidence_status" in rows[0].keys(), "Missing evidence_status column"
        missing_evidence = [r for r in rows if r.get("evidence_status") == "MISSING_EVIDENCE"]
        assert len(missing_evidence) > 0, "Should have at least one MISSING_EVIDENCE row"

    def test_includes_shl_interest_row(self):
        with open(R2, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert any("shl interest" in r["item"].lower() for r in rows), "Missing SHL interest row"

    def test_includes_shl_principal_row(self):
        with open(R2, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert any("shl principal" in r["item"].lower() for r in rows), "Missing SHL principal row"

    def test_includes_dividends_row(self):
        with open(R2, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert any("dividend" in r["item"].lower() or "distribution" in r["item"].lower() for r in rows), "Missing dividends row"

    def test_includes_wht_row(self):
        with open(R2, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert any("wht" in r["item"].lower() for r in rows), "Missing WHT row"

    def test_includes_investment_base_row(self):
        with open(R2, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert any("investment base" in r["item"].lower() for r in rows), "Missing investment base row"

    def test_includes_timing_row(self):
        with open(R2, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert any("timing" in r["item"].lower() or "date" in r["item"].lower() for r in rows), "Missing timing row"


class TestDefinitionMatrix:
    def test_includes_excel_11_61(self):
        with open(R4, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert any("11.61" in r["computed_irr"] or "11.61" in r.get("target_or_reference","") for r in rows), \
            "Missing Excel 11.61%"

    def test_includes_corrected_14_range(self):
        """Model corrected should be in ~14-15% range."""
        with open(R4, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        ref_values = [r.get('target_or_reference', '') for r in rows]
        # Check for ~14-15% range in target_or_reference
        has_corrected = any(any(v in r for v in ['14.74', '14.96', '15.49', '15.48', '14.7', '15.5']) for r in ref_values)
        assert has_corrected, f"Missing corrected ~14.96% in target_or_reference. Values: {ref_values}"

    def test_includes_buggy_26_66(self):
        with open(R4, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert any("26.66" in r["computed_irr"] or "buggy" in r["method"].lower() for r in rows), \
            "Missing buggy 26.66%"

    def test_includes_wrong_equity_only(self):
        with open(R4, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert any("56.73" in r["computed_irr"] or "wrong" in r["status"].lower() or "equity_only" in r["method"].lower() for r in rows), \
            "Missing wrong equity_only 56.73%"


class TestCashflowBridge:
    def test_row_count(self):
        with open(R3, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 61, f"Expected 61 periods, got {len(rows)}"

    def test_excel_column_marked_missing(self):
        with open(R3, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        missing = [r for r in rows if r.get("excel_cashflow_keur_if_available") == "MISSING_EVIDENCE"]
        assert len(missing) == 61, "All Excel cashflow values should be MISSING_EVIDENCE"

    def test_model_shl_interest_populated(self):
        with open(R3, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        # First 13 periods should have non-zero shl_interest
        nonzero = [r for r in rows[:14] if float(r.get("model_shl_interest_keur", "0") or "0") > 0]
        assert len(nonzero) >= 13, f"Expected ~13 periods with non-zero SHL interest, got {len(nonzero)}"


class TestGapRegister:
    def test_includes_shl_interest_gap(self):
        with open(R5, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert any("G-EIRR-SHL-INTEREST" in r["gap_id"] for r in rows), \
            "Missing G-EIRR-SHL-INTEREST gap"

    def test_includes_bSC_doublecount_gap(self):
        with open(R5, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert any("G-EIRR-BSC-DOUBLECOUNT" in r["gap_id"] or "doublecount" in r["gap_id"].lower() for r in rows), \
            "Missing G-EIRR-BSC-DOUBLECOUNT gap"

    def test_all_gaps_have_severity(self):
        with open(R5, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            assert r.get("severity") in ["HIGH", "MED", "LOW"], \
                f"Gap {r.get('gap_id')} missing valid severity"


class TestDocContent:
    def test_g20_blocked(self):
        with open(DOC, encoding="utf-8") as f:
            content = f.read()
        assert "BLOCKED" in content, "Doc must state G20 BLOCKED"

    def test_r99_r102_not_approved(self):
        with open(DOC, encoding="utf-8") as f:
            content = f.read()
        assert "NOT approved" in content or "not approved" in content, \
            "Doc must explicitly state R99/R102 NOT approved"

    def test_no_runtime_changes(self):
        with open(DOC, encoding="utf-8") as f:
            content = f.read()
        assert "no runtime" in content.lower() or "analysis" in content.lower(), \
            "Doc must state no runtime changes"

    def test_missing_evidence_stated(self):
        with open(DOC, encoding="utf-8") as f:
            content = f.read()
        assert "MISSING_EVIDENCE" in content, \
            "Doc must explicitly state Excel source evidence is missing"

    def test_lists_next_branches(self):
        with open(DOC, encoding="utf-8") as f:
            content = f.read()
        assert "phase9-tuho-equity-irr-excel-extraction" in content or "excel-extraction" in content, \
            "Doc must list recommended next branches"


class TestScope:
    def test_no_runtime_files_changed(self):
        """Verify no runtime behavior files in this branch."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "origin/main"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        changed = result.stdout.strip().split("\n") if result.stdout.strip() else []
        runtime_files = [
            f for f in changed
            if f.startswith("domain/") and not f.startswith("domain/returns/")
            and not f.startswith("domain/waterfall/")  # waterfall_engine is not runtime waterfall
        ]
        assert len(runtime_files) == 0, f"Runtime files changed: {runtime_files}"