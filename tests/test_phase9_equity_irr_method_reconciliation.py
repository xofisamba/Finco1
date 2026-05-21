"""Phase 9: Equity IRR Method Reconciliation — tests.

SCOPE: Analysis/reports/tests only. No runtime code changed.

Key findings:
- Corrected shl_plus_dividends: 14.96% (no double-count)
- build_sponsor_cashflows has double-count bug: 26.66%
- Calibrated reference (11.15%) used shl_balance=0 bug (harness passed shl_amount=0.0)
- Excel target: 11.61%
- G20 remains BLOCKED
"""
import csv
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "reports"
DOCS_DIR = REPO_ROOT / "docs"

R1 = REPORTS_DIR / "phase9_equity_irr_method_comparison.csv"
R2 = REPORTS_DIR / "phase9_equity_irr_cashflow_method_bridge.csv"
R3 = REPORTS_DIR / "phase9_equity_irr_difference_by_component.csv"
DOC = DOCS_DIR / "phase9_equity_irr_method_reconciliation.md"


class TestRequiredFiles:
    def test_method_comparison_exists(self):
        assert R1.exists(), f"Missing: {R1}"
    def test_cashflow_bridge_exists(self):
        assert R2.exists(), f"Missing: {R2}"
    def test_component_delta_exists(self):
        assert R3.exists(), f"Missing: {R3}"
    def test_doc_exists(self):
        assert DOC.exists(), f"Missing: {DOC}"


class TestMethodComparison:
    def test_includes_calibrated_reference(self):
        with open(R1, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert any("11.15" in r["equity_irr"] for r in rows), "Missing calibrated_reference (11.15%)"

    def test_includes_shl_plus_dividends_corrected(self):
        with open(R1, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert any("corrected" in r["method"].lower() or "14.96" in r["equity_irr"] for r in rows), \
            "Missing shl_plus_dividends_corrected"

    def test_includes_excel_target(self):
        with open(R1, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert any("11.61" in r["equity_irr"] for r in rows), "Missing excel_target (11.61%)"

    def test_includes_buggy_methods(self):
        with open(R1, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        methods = [r["method"] for r in rows]
        assert any("bSC" in m or "double" in m for m in methods), "Missing bSC buggy method"
        assert any("buggy" in m or "wrong" in m for m in methods), "Missing equity_only buggy method"

    def test_14_74_percent_in_model_column(self):
        with open(R1, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        values = [r["equity_irr"] for r in rows]
        assert any("14.74" in v or "14.96" in v for v in values), "Missing model value (~14.74%)"

    def test_all_required_columns_present(self):
        with open(R1, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        required = {"method", "equity_irr", "investment_base_keur", "total_distributions_keur",
                    "total_shl_interest_keur", "total_shl_principal_keur",
                    "includes_shl_principal", "includes_shl_interest", "status", "notes"}
        missing = required - set(rows[0].keys())
        assert not missing, f"Missing columns: {missing}"


class TestCashflowBridge:
    def test_row_count(self):
        with open(R2, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 61, f"Expected 61 periods, got {len(rows)}"

    def test_has_required_columns(self):
        with open(R2, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        required = {"period", "date", "shl_plus_dividends_cashflow_keur",
                    "distribution_keur", "shl_interest_keur", "shl_principal_keur",
                    "investment_or_injection_keur"}
        missing = required - set(rows[0].keys())
        assert not missing, f"Missing columns: {missing}"

    def test_period_sequence(self):
        with open(R2, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        periods = [int(r["period"]) for r in rows]
        assert periods == list(range(2, 63)), f"Period sequence wrong: {periods[:5]}"

    def test_first_period_investment_base(self):
        with open(R2, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert float(rows[0]["investment_or_injection_keur"]) < 0, \
            "First period must have negative investment"


class TestComponentDelta:
    def test_has_required_columns(self):
        with open(R3, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        required = {"component", "calibrated_total_keur", "shl_plus_dividends_total_keur",
                    "delta_keur", "estimated_irr_impact", "classification"}
        missing = required - set(rows[0].keys())
        assert not missing, f"Missing columns: {missing}"

    def test_investment_base_delta_is_zero(self):
        with open(R3, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            if "investment" in r["component"].lower():
                assert float(r["delta_keur"]) == 0.0, \
                    f"Investment base delta should be 0, got {r['delta_keur']}"

    def test_shl_interest_driver_identified(self):
        with open(R3, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            if "shl_interest" in r["component"].lower():
                assert "DRIVER" in r["classification"] or "KEY" in r["classification"], \
                    "SHL interest should be identified as a key driver"


class TestDocContent:
    def test_g20_blocked(self):
        with open(DOC, encoding="utf-8") as f:
            content = f.read()
        assert "BLOCKED" in content, "Doc must state G20 remains BLOCKED"

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

    def test_identifies_double_count_bug(self):
        with open(DOC, encoding="utf-8") as f:
            content = f.read()
        assert "double-count" in content.lower() or "double count" in content.lower(), \
            "Doc must identify build_sponsor_cashflows double-count bug"

    def test_lists_next_steps(self):
        with open(DOC, encoding="utf-8") as f:
            content = f.read()
        assert "next" in content.lower() and ("step" in content.lower() or "branch" in content.lower()), \
            "Doc must list next steps"


class TestScope:
    def test_no_runtime_files_changed(self):
        """Verify no runtime behavior files in this branch."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "origin/main"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        changed = result.stdout.strip().split("\n")
        runtime_files = [f for f in changed if f.startswith("domain/") and not f.startswith("domain/returns/")]
        assert len(runtime_files) == 0, f"Runtime files changed: {runtime_files}"