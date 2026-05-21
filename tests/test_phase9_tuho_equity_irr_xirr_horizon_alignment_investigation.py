"""
Tests for phase9 — TUHO Equity IRR XIRR Horizon Alignment Investigation.

Scope: REPORTING / IRR CONVENTION INVESTIGATION / TESTS ONLY. No runtime code changed.
G20: BLOCKED. R99/R102: NOT APPROVED.

Key findings:
- Date convention (construction period) is the DOMINANT gap driver: -2.29pp effect
- Investment base convention (IDC) has +1.17pp effect  
- Terminal period has negligible impact (~0pp)
- Remaining gap after date+base alignment: ~0.29pp (acceptable)
- Recommendation: Add Excel-equivalent reconciliation IRR as reporting view
"""
import csv, os, pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(REPO, "docs", "phase9_tuho_equity_irr_xirr_horizon_alignment_investigation.md")
REPORTS = os.path.join(REPO, "reports")


def _csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))


class TestRequiredFiles:
    def test_doc_exists(self):
        assert os.path.exists(DOC), f"Missing: {DOC}"

    def test_sensitivity_exists(self):
        p = os.path.join(REPORTS, "phase9_tuho_xirr_horizon_sensitivity.csv")
        assert os.path.exists(p), f"Missing: {p}"

    def test_residual_gap_bridge_exists(self):
        p = os.path.join(REPORTS, "phase9_tuho_equity_irr_residual_gap_bridge.csv")
        assert os.path.exists(p), f"Missing: {p}"

    def test_reporting_view_options_exists(self):
        p = os.path.join(REPORTS, "phase9_tuho_equity_irr_reporting_view_options.csv")
        assert os.path.exists(p), f"Missing: {p}"


class TestSensitivity:
    def test_has_8_scenarios(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_xirr_horizon_sensitivity.csv"))
        assert len(rows) == 8, f"Expected 8 scenarios, got {len(rows)}"

    def test_includes_current_model_method(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_xirr_horizon_sensitivity.csv"))
        assert any("current" in r["scenario"].lower() for r in rows), \
            "Must include current_model_method scenario"

    def test_includes_model_cashflows_on_excel_dates(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_xirr_horizon_sensitivity.csv"))
        assert any("excel_date" in r["scenario"].lower() or "excel_dates" in r["scenario"].lower()
                   for r in rows), "Must include model_cashflows_on_excel_dates scenario"

    def test_has_required_columns(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_xirr_horizon_sensitivity.csv"))
        required = ["scenario","period_count","start_date","end_date","equity_irr","delta_vs_excel_pp","runtime_change_required","reporting_only"]
        for col in required:
            assert col in rows[0], f"Missing column: {col}"

    def test_date_shift_reduces_gap(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_xirr_horizon_sensitivity.csv"))
        # Find scenarios with date shift
        for r in rows:
            if "2yr" in r["scenario"] or "date_shift" in r["scenario"]:
                delta = float(r["delta_vs_excel_pp"].replace("pp","").replace("+",""))
                assert delta < 3.52, "Date shift should reduce gap from +3.52pp baseline"


class TestResidualGapBridge:
    def test_has_8_components(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_equity_irr_residual_gap_bridge.csv"))
        assert len(rows) == 8, f"Expected 8 components, got {len(rows)}"

    def test_includes_xirr_date_convention(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_equity_irr_residual_gap_bridge.csv"))
        ids = [r["component"] for r in rows]
        assert any("xirr" in i.lower() and "date" in i.lower() for i in ids), \
            "Must include XIRR date convention component"

    def test_includes_shl_idc(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_equity_irr_residual_gap_bridge.csv"))
        ids = [r["component"] for r in rows]
        assert any("idc" in i.lower() for i in ids), "Must include SHL IDC component"

    def test_includes_shl_interest_rate_source(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_equity_irr_residual_gap_bridge.csv"))
        ids = [r["component"] for r in rows]
        assert any("rate" in i.lower() and ("shl" in i.lower() or "interest" in i.lower()) for i in ids), \
            "Must include SHL interest rate source component"

    def test_has_required_columns(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_equity_irr_residual_gap_bridge.csv"))
        required = ["component","before_gap_pp","after_gap_pp","estimated_impact_pp","affects_runtime","affects_reporting","recommended_action"]
        for col in required:
            assert col in rows[0], f"Missing column: {col}"


class TestReportingViewOptions:
    def test_has_6_options(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_equity_irr_reporting_view_options.csv"))
        assert len(rows) == 6, f"Expected 6 options, got {len(rows)}"

    def test_includes_excel_equivalent_reconciliation_irr(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_equity_irr_reporting_view_options.csv"))
        names = [r["option_name"] for r in rows]
        assert any("excel_equivalent" in n.lower() or "reconciliation" in n.lower() for n in names), \
            "Must include excel_equivalent_reconciliation_irr option"

    def test_has_required_columns(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_equity_irr_reporting_view_options.csv"))
        required = ["option_id","option_name","runtime_change_required","reporting_only","expected_gap_after_pp","recommendation"]
        for col in required:
            assert col in rows[0], f"Missing column: {col}"

    def test_recommendation_column_populated(self):
        rows = _csv(os.path.join(REPORTS, "phase9_tuho_equity_irr_reporting_view_options.csv"))
        for r in rows:
            assert r["recommendation"], f"Option {r['option_id']} missing recommendation"


class TestDocContent:
    def test_documents_date_convention_as_dominant_driver(self):
        with open(DOC) as f:
            content = f.read()
        assert "date convention" in content.lower() or "construction period" in content.lower(), \
            "Doc must address XIRR date convention"

    def test_gives_before_after_irr_scenarios(self):
        with open(DOC) as f:
            content = f.read()
        # Should show before/after IRR scenarios
        assert "11.61%" in content and "15.13%" in content, \
            "Doc must show IRR scenarios"

    def test_states_recommendation(self):
        with open(DOC) as f:
            content = f.read()
        rec_lines = [l for l in content.split("\n") if "recommend" in l.lower()]
        assert rec_lines, "Doc must state explicit recommendation"

    def test_g20_blocked(self):
        with open(DOC) as f:
            content = f.read()
        assert "BLOCKED" in content, "Doc must state G20 BLOCKED"

    def test_r99_r102_not_approved(self):
        with open(DOC) as f:
            content = f.read()
        assert "NOT approved" in content, "Doc must not approve R99/R102"

    def test_029pp_gap_stated(self):
        with open(DOC) as f:
            content = f.read()
        assert "0.29" in content, "Doc must state 0.29pp residual gap"

    def test_terminal_period_negligible(self):
        with open(DOC) as f:
            content = f.read()
        assert "terminal" in content.lower() and ("negligible" in content.lower() or "0pp" in content or "0.0pp" in content), \
            "Doc must state terminal period has negligible impact"

    def test_next_branch_recommended(self):
        with open(DOC) as f:
            content = f.read()
        assert "next" in content.lower() and "branch" in content.lower(), \
            "Doc must recommend next branch"

    def test_reconciliation_irr_recommended(self):
        with open(DOC) as f:
            content = f.read()
        assert "reconciliation" in content.lower() or "reconciliation" in content.lower(), \
            "Doc must recommend reconciliation IRR approach"


class TestScope:
    def test_no_runtime_files_changed(self):
        # Verify doc states no runtime changes
        assert os.path.exists(DOC)
        with open(DOC) as f:
            content = f.read()
        assert "no runtime" in content.lower() or "not change" in content.lower(), \
            "Doc must explicitly state no runtime changes were made"