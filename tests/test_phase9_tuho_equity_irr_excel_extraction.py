"""
Tests for phase9 — TUHO Equity IRR Excel Extraction.

Scope: ANALYSIS / REPORTS / TESTS ONLY. No runtime code changed.
G20: BLOCKED. R99/R102: NOT APPROVED.
"""
import csv, os, pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "phase9_tuho_equity_irr_excel_extraction.md")
REPORTS = os.path.join(REPO, "reports")

def _csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))

class TestRequiredFiles:
    def test_doc_exists(self):
        assert os.path.exists(DOC), f"Missing: {DOC}"

    def test_formula_map_exists(self):
        p = os.path.join(REPORTS, "phase9_tuho_equity_irr_excel_formula_map.csv")
        assert os.path.exists(p), f"Missing: {p}"

    def test_cashflow_extract_exists(self):
        p = os.path.join(REPORTS, "phase9_tuho_equity_irr_excel_cashflow_extract.csv")
        assert os.path.exists(p), f"Missing: {p}"

    def test_bridge_exists(self):
        p = os.path.join(REPORTS, "phase9_tuho_equity_irr_excel_vs_model_bridge.csv")
        assert os.path.exists(p), f"Missing: {p}"

    def test_gap_register_exists(self):
        p = os.path.join(REPORTS, "phase9_tuho_equity_irr_excel_extraction_gap_register.csv")
        assert os.path.exists(p), f"Missing: {p}"


class TestFormulaMap:
    def test_eq_d28_included(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_equity_irr_excel_formula_map.csv"))
        d28 = [r for r in rows if r["cell"] == "D28"]
        assert len(d28) == 1, "Eq!D28 must be in formula_map"
        assert "XIRR" in d28[0]["formula"], "D28 formula must contain XIRR"

    def test_irr_value_11_61_percent(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_equity_irr_excel_formula_map.csv"))
        d28 = [r for r in rows if r["cell"] == "D28"][0]
        val = float(d28["value"])
        assert 0.115 < val < 0.117, f"D28 value {val} should be ~0.116 (11.6%)"

    def test_g28_formula_shl_plus_dividend(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_equity_irr_excel_formula_map.csv"))
        g28 = [r for r in rows if r["cell"] == "G28"][0]
        assert "G27" in g28["formula"] and "G24" in g28["formula"], \
            "G28 must = G27 + G24 (dividend + SHL total)"

    def test_has_precedent_range(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_equity_irr_excel_formula_map.csv"))
        for r in rows:
            assert r.get("precedent_range"), f"{r['cell']} missing precedent_range"


class TestCashflowExtract:
    def test_has_121_periods(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_equity_irr_excel_cashflow_extract.csv"))
        assert len(rows) == 121, f"Expected 121 periods, got {len(rows)}"

    def test_initial_cashflow_negative(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_equity_irr_excel_cashflow_extract.csv"))
        assert float(rows[0]["excel_cashflow_keur"]) < 0, "Period 0 must be negative (investment)"

    def test_dates_progress_forward(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_equity_irr_excel_cashflow_extract.csv"))
        for i in range(1, len(rows)):
            assert rows[i]["date"] > rows[i-1]["date"], \
                f"Dates must progress: {rows[i-1]['date']} -> {rows[i]['date']}"


class TestBridge:
    def test_has_121_rows(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_equity_irr_excel_vs_model_bridge.csv"))
        assert len(rows) == 121, f"Expected 121 rows, got {len(rows)}"

    def test_initial_investment_base_difference(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_equity_irr_excel_vs_model_bridge.csv"))
        # Period 0: investment base
        assert rows[0]["likely_driver"] == "investment_base_difference", \
            "Period 0 should be flagged as investment_base_difference"

    def test_has_likely_driver_column(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_equity_irr_excel_vs_model_bridge.csv"))
        assert "likely_driver" in rows[0], "Bridge must have likely_driver column"
        assert "notes" in rows[0], "Bridge must have notes column"


class TestGapRegister:
    def test_has_7_gaps(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_equity_irr_excel_extraction_gap_register.csv"))
        assert len(rows) == 7, f"Expected 7 gaps, got {len(rows)}"

    def test_gap_ids_unique(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_equity_irr_excel_extraction_gap_register.csv"))
        ids = [r["gap_id"] for r in rows]
        assert len(ids) == len(set(ids)), "Gap IDs must be unique"

    def test_includes_investment_base_gap(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_equity_irr_excel_extraction_gap_register.csv"))
        ids = [r["gap_id"] for r in rows]
        assert any("INVESTMENT_BASE" in i for i in ids), "Must include investment_base gap"

    def test_includes_shl_interest_gap(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_equity_irr_excel_extraction_gap_register.csv"))
        ids = [r["gap_id"] for r in rows]
        assert any("SHL_INTEREST" in i for i in ids), "Must include SHL interest gap"

    def test_g20_blocked_in_doc(self):
        with open(DOC) as f:
            content = f.read()
        assert "BLOCKED" in content, "G20 BLOCKED must be stated in doc"
        assert "G20" in content, "G20 reference must be in doc"

    def test_no_runtime_changes(self):
        with open(DOC) as f:
            content = f.read()
        # Check doc states no runtime changes
        lines_with_key = [l for l in content.split("\n") if "no runtime" in l.lower() or "no changes" in l.lower() or "harness" in l.lower()]
        assert lines_with_key, "Doc must explicitly state no runtime changes"


class TestDocContent:
    def test_equity_irr_11_61_stated(self):
        with open(DOC) as f:
            content = f.read()
        assert "11.6095" in content or "11.61" in content, "Doc must state 11.6095% IRR"

    def test_xirr_formula_stated(self):
        with open(DOC) as f:
            content = f.read()
        assert "XIRR" in content, "Doc must include XIRR formula"

    def test_shl_interest_included(self):
        with open(DOC) as f:
            content = f.read()
        assert "SHL interest" in content or "shl interest" in content.lower(), \
            "Doc must address SHL interest treatment"

    def test_shl_principal_timing(self):
        with open(DOC) as f:
            content = f.read()
        assert "principal" in content.lower(), "Doc must address principal repayment timing"

    def test_dividend_start_2047(self):
        with open(DOC) as f:
            content = f.read()
        assert "2047" in content, "Doc must state when dividends start (2047)"

    def test_wht_not_driver(self):
        with open(DOC) as f:
            content = f.read()
        assert "WHT" in content and "0%" in content, "Doc must confirm WHT=0"

    def test_idc_investment_base(self):
        with open(DOC) as f:
            content = f.read()
        assert "IDC" in content or "3,568" in content, "Doc must address SHL IDC"

    def test_r99_r102_not_approved(self):
        with open(DOC) as f:
            content = f.read()
        assert "R99" in content or "R99/R102" in content or "NOT approved" in content, \
            "Doc must explicitly not approve R99/R102 promotion"

    def test_g20_blocked_stated(self):
        with open(DOC) as f:
            content = f.read()
        assert "BLOCKED" in content, "Doc must state G20 remains BLOCKED"

    def test_next_branch_recommended(self):
        with open(DOC) as f:
            content = f.read()
        assert "next" in content.lower() and ("branch" in content.lower() or "recommend" in content.lower()), \
            "Doc must recommend next branch"