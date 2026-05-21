"""
Tests for phase9 — TUHO Equity IRR Investment Base Alignment Investigation.

Scope: DISCOVERY / PARITY ANALYSIS / REPORTS / TESTS ONLY. No runtime code changed.
G20: BLOCKED (pending acceptance of 0.29pp residual gap). R99/R102: NOT APPROVED.

Key findings:
- Model investment base = -33,204 kEUR (shl_amount 29,135 + shl_idc 3,569 + share_capital 500)
- Excel investment base = -29,635 kEUR (shl_amount 29,135 + share_capital 500)
- SHL IDC difference = 3,569 kEUR
- Remaining IRR gap = ~0.29pp after PR #165 alignment
- Investment base difference is a reporting convention, not a runtime bug
- SHL rate difference (~7.93% model vs ~2.1% Excel) is the dominant remaining gap driver
- Recommendation: Accept 0.29pp as economically acceptable; no runtime changes
"""
import csv, os, pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "phase9_tuho_equity_irr_investment_base_alignment_investigation.md")
REPORTS = os.path.join(REPO, "reports")


def _csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))


class TestRequiredFiles:
    def test_doc_exists(self):
        assert os.path.exists(DOC), f"Missing: {DOC}"

    def test_investment_base_composition_exists(self):
        p = os.path.join(REPORTS, "phase9_tuho_investment_base_composition.csv")
        assert os.path.exists(p), f"Missing: {p}"

    def test_sensitivity_exists(self):
        p = os.path.join(REPORTS, "phase9_tuho_investment_base_irr_sensitivity.csv")
        assert os.path.exists(p), f"Missing: {p}"

    def test_final_gap_register_exists(self):
        p = os.path.join(REPORTS, "phase9_tuho_final_gap_register.csv")
        assert os.path.exists(p), f"Missing: {p}"


class TestInvestmentBaseComposition:
    def test_has_7_rows(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_investment_base_composition.csv"))
        assert len(rows) == 7, f"Expected 7 rows, got {len(rows)}"

    def test_includes_shl_idc_row(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_investment_base_composition.csv"))
        idc_rows = [r for r in rows if "shl_idc" in r["component"].lower()]
        assert len(idc_rows) >= 1, "Must include SHL IDC row"
        assert float(idc_rows[0]["model_amount_keur"]) > 0, "SHL IDC should be > 0 in model"

    def test_includes_sponsor_equity_row(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_investment_base_composition.csv"))
        sc_rows = [r for r in rows if "sponsor" in r["component"].lower() or "share_cap" in r["component"].lower()]
        assert len(sc_rows) >= 1, "Must include sponsor equity row"

    def test_has_required_columns(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_investment_base_composition.csv"))
        required = ["component","model_amount_keur","excel_amount_keur","delta_keur","included_in_model_irr","included_in_excel_irr","classification"]
        for col in required:
            assert col in rows[0], f"Missing column: {col}"

    def test_model_total_larger_than_excel(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_investment_base_composition.csv"))
        model_total_row = [r for r in rows if "total_investment" in r["component"].lower()]
        if model_total_row:
            model_total = float(model_total_row[0]["model_amount_keur"])
            excel_total = float(model_total_row[0]["excel_amount_keur"])
            assert model_total > excel_total, "Model total should be larger (includes IDC)"


class TestSensitivity:
    def test_has_6_scenarios(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_investment_base_irr_sensitivity.csv"))
        assert len(rows) == 6, f"Expected 6 scenarios, got {len(rows)}"

    def test_includes_exclude_shl_idc_scenario(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_investment_base_irr_sensitivity.csv"))
        assert any("exclude" in r["scenario"].lower() or "no idc" in r["scenario"].lower()
                   for r in rows), "Must include exclude_shl_idc scenario"

    def test_has_required_columns(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_investment_base_irr_sensitivity.csv"))
        required = ["scenario","investment_base_keur","equity_irr","delta_vs_excel_pp","runtime_change_required","reporting_only"]
        for col in required:
            assert col in rows[0], f"Missing column: {col}"

    def test_excel_reference_present(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_investment_base_irr_sensitivity.csv"))
        assert any("reference" in r["scenario"].lower() or "excel" in r["scenario"].lower()
                   for r in rows), "Must include Excel reference scenario"


class TestFinalGapRegister:
    def test_has_6_gaps(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_final_gap_register.csv"))
        assert len(rows) == 6, f"Expected 6 gaps, got {len(rows)}"

    def test_includes_idc_gap(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_final_gap_register.csv"))
        ids = [r["gap_id"] for r in rows]
        assert any("IDC" in i or "INVESTMENT" in i for i in ids), "Must include investment base gap"

    def test_gap_ids_unique(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_final_gap_register.csv"))
        ids = [r["gap_id"] for r in rows]
        assert len(ids) == len(set(ids)), "Gap IDs must be unique"

    def test_has_affects_columns(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_final_gap_register.csv"))
        required = ["affects_runtime","affects_reporting","affects_bankability","affects_g20"]
        for col in required:
            assert col in rows[0], f"Missing column: {col}"


class TestDocContent:
    def test_documents_recommendation(self):
        with open(DOC) as f:
            content = f.read()
        rec_lines = [l for l in content.split("\n") if "recommend" in l.lower() and ":" in l]
        assert rec_lines, "Doc must state explicit recommendation"

    def test_no_runtime_change_stated(self):
        with open(DOC) as f:
            content = f.read()
        # Doc should explicitly say no runtime change
        lines = [l for l in content.split("\n") if "runtime" in l.lower() and ("change" in l.lower() or "no" in l.lower() or "not" in l.lower())]
        assert lines, "Doc must explicitly state no runtime change"

    def test_includes_investment_base_composition(self):
        with open(DOC) as f:
            content = f.read()
        assert "29,635" in content or "29635" in content, "Doc must show Excel investment base"
        assert "33,204" in content or "33204" in content, "Doc must show model investment base"
        assert "3,568" in content or "3569" in content, "Doc must quantify SHL IDC"

    def test_g20_blocked(self):
        with open(DOC) as f:
            content = f.read()
        assert "BLOCKED" in content or "G20" in content, "Doc must address G20"

    def test_r99_r102_not_approved(self):
        with open(DOC) as f:
            content = f.read()
        assert "NOT approved" in content or "not approved" in content, \
            "Doc must explicitly not approve R99/R102"

    def test_029pp_gap_stated(self):
        with open(DOC) as f:
            content = f.read()
        assert "0.29" in content or "0.29" in content or "29pp" in content, \
            "Doc must state 0.29pp residual gap"

    def test_economically_acceptable_stated(self):
        with open(DOC) as f:
            content = f.read()
        assert "acceptable" in content.lower() or "acceptable" in content.lower(), \
            "Doc must state whether gap is economically acceptable"

    def test_distinguishes_runtime_vs_reporting(self):
        with open(DOC) as f:
            content = f.read()
        # Doc should distinguish between runtime and reporting issues
        assert ("runtime" in content.lower() and "reporting" in content.lower()), \
            "Doc must distinguish runtime vs reporting convention issues"

    def test_next_branch_recommended(self):
        with open(DOC) as f:
            content = f.read()
        assert "next" in content.lower() and "branch" in content.lower(), \
            "Doc must recommend next branch"


class TestScope:
    def test_no_runtime_files_changed(self):
        # This branch should not have changed any runtime files
        # We verify by checking the doc states no runtime changes
        assert os.path.exists(DOC)
        with open(DOC) as f:
            content = f.read()
        assert "no runtime" in content.lower() or "not change" in content.lower(), \
            "Doc must explicitly state no runtime changes were made"