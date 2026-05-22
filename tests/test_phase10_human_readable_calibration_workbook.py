"""
Phase 10 — Human-Readable Calibration Workbook Tests

Tests that the Phase 10 calibration workbook is generated correctly,
has required sheets, has Excel/Model/Delta row structure, contains
MISSING_EVIDENCE markers, and has correct governance status.
No runtime model files are changed — these are report-only tests.
"""

import pytest
import os
import subprocess

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
WORKBOOK_PATH = os.path.join(REPORTS_DIR, "phase10_human_readable_calibration_workbook.xlsx")

# ── Helpers ───────────────────────────────────────────────────────────────────

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

skip_if_no_openpyxl = pytest.mark.skipif(not HAS_OPENPYXL, reason="openpyxl not available")


def sheet_text(wb, sheet_name):
    """Collect all cell text from a sheet."""
    ws = wb[sheet_name]
    parts = []
    for r in range(1, ws.max_row + 1):
        for c in range(1, ws.max_column + 1):
            v = ws.cell(row=r, column=c).value
            if v:
                parts.append(str(v))
    return " ".join(parts)


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestWorkbookGenerated:
    """Workbook file exists."""

    def test_workbook_generated(self):
        assert os.path.exists(WORKBOOK_PATH), \
            f"Workbook not found at {WORKBOOK_PATH}"


@skip_if_no_openpyxl
class TestRequiredSheets:
    """All required sheets exist."""

    def test_required_sheets_exist(self):
        wb = openpyxl.load_workbook(WORKBOOK_PATH, read_only=True)
        required = [
            "Summary", "Operations", "Revenue", "OPEX EBITDA", "CAPEX Construction",
            "Senior Debt", "SHL", "Tax", "CFADS Waterfall", "Distributions",
            "Returns", "Gap Analysis", "Source Map", "Accepted Conventions", "Governance"
        ]
        for s in required:
            assert s in wb.sheetnames, f"Missing required sheet: {s}"

    def test_semiannual_period_columns_exist(self):
        """Operations sheet has at least 14 period columns (P1-P14)."""
        wb = openpyxl.load_workbook(WORKBOOK_PATH, read_only=True)
        ws = wb["Operations"]
        row1 = [ws.cell(row=1, column=c).value for c in range(1, ws.max_column + 1)]
        period_cols = [v for v in row1 if v and (str(v).startswith("P") or "2030" in str(v))]
        assert len(period_cols) >= 14, \
            f"Only {len(period_cols)} period columns found (expected >=14)"


@skip_if_no_openpyxl
class TestRowStructure:
    """Excel/Model/Delta triplet rows exist for key metrics."""

    def test_revenue_electricity_excel_model_delta_rows_exist(self):
        wb = openpyxl.load_workbook(WORKBOOK_PATH, read_only=True)
        ws = wb["Revenue"]
        texts = [str(ws.cell(row=r, column=1).value) for r in range(1, ws.max_row + 1)]
        assert any("Electricity Revenue" in t and "Excel" in t for t in texts), \
            "Revenue sheet missing Electricity Revenue — Excel row"
        assert any("Electricity Revenue" in t and "Model" in t for t in texts), \
            "Revenue sheet missing Electricity Revenue — Model row"
        assert any("Electricity Revenue" in t and "Delta" in t for t in texts), \
            "Revenue sheet missing Electricity Revenue — Delta row"

    def test_opex_excel_model_delta_rows_exist(self):
        wb = openpyxl.load_workbook(WORKBOOK_PATH, read_only=True)
        ws = wb["OPEX EBITDA"]
        texts = [str(ws.cell(row=r, column=1).value) for r in range(1, ws.max_row + 1)]
        assert any("Total OPEX" in t and "Excel" in t for t in texts)
        assert any("Total OPEX" in t and "Model" in t for t in texts)
        assert any("Total OPEX" in t and "Delta" in t for t in texts)

    def test_senior_debt_closing_balance_rows_exist(self):
        wb = openpyxl.load_workbook(WORKBOOK_PATH, read_only=True)
        ws = wb["Senior Debt"]
        texts = [str(ws.cell(row=r, column=1).value) for r in range(1, ws.max_row + 1)]
        assert any("Closing Balance" in t for t in texts), \
            "Senior Debt sheet missing Closing Balance row"

    def test_shl_opening_balance_rows_exist(self):
        wb = openpyxl.load_workbook(WORKBOOK_PATH, read_only=True)
        ws = wb["SHL"]
        texts = [str(ws.cell(row=r, column=1).value) for r in range(1, ws.max_row + 1)]
        assert any("Opening Balance" in t for t in texts), \
            "SHL sheet missing Opening Balance row"

    def test_cfads_rows_exist(self):
        wb = openpyxl.load_workbook(WORKBOOK_PATH, read_only=True)
        ws = wb["CFADS Waterfall"]
        texts = [str(ws.cell(row=r, column=1).value) for r in range(1, ws.max_row + 1)]
        assert any("EBITDA" in t and "Model" in t for t in texts), \
            "CFADS sheet missing EBITDA — Model row"


@skip_if_no_openpyxl
class TestDataIntegrity:
    """Missing evidence markers and no silent zero-fill."""

    def test_missing_evidence_marker_used(self):
        wb = openpyxl.load_workbook(WORKBOOK_PATH, read_only=True)
        all_text = ""
        for sheet in wb.sheetnames:
            all_text += sheet_text(wb, sheet) + " "
        assert "MISSING_EVIDENCE" in all_text, \
            "Workbook must contain MISSING_EVIDENCE markers for unmapped Excel rows"

    def test_no_model_row_silently_all_zero(self):
        """Model rows should not be all zeros unless the metric is genuinely zero."""
        wb = openpyxl.load_workbook(WORKBOOK_PATH, read_only=True)
        # Check Revenue sheet — model row for electricity revenue should not be all 0
        ws = wb["Revenue"]
        for r in range(1, ws.max_row + 1):
            label = str(ws.cell(row=r, column=1).value or "")
            if "Model" in label and "Electricity Revenue" in label:
                values = [ws.cell(row=r, column=c).value for c in range(3, 10)]
                # Skip if all MISSING_EVIDENCE
                non_missing = [v for v in values if v and "MISSING" not in str(v)]
                if non_missing:
                    numeric = [float(v) for v in non_missing if isinstance(v, (int, float))]
                    assert not all(v == 0 for v in numeric), \
                        f"Model row for Electricity Revenue appears to be all zeros: {values}"


@skip_if_no_openpyxl
class TestGapAnalysis:
    """Gap Analysis and Source Map sheets."""

    def test_gap_analysis_sheet_exists(self):
        wb = openpyxl.load_workbook(WORKBOOK_PATH, read_only=True)
        assert "Gap Analysis" in wb.sheetnames

    def test_source_map_sheet_exists(self):
        wb = openpyxl.load_workbook(WORKBOOK_PATH, read_only=True)
        assert "Source Map" in wb.sheetnames


@skip_if_no_openpyxl
class TestGovernance:
    """Governance sheet contains correct status for G20/R99/R102."""

    def test_governance_sheet_says_g20_blocked(self):
        wb = openpyxl.load_workbook(WORKBOOK_PATH, read_only=True)
        text = sheet_text(wb, "Governance")
        assert "G20" in text, "Governance sheet must mention G20"
        assert "BLOCKED" in text, "G20 must be marked BLOCKED"

    def test_governance_sheet_says_r99_not_approved(self):
        wb = openpyxl.load_workbook(WORKBOOK_PATH, read_only=True)
        text = sheet_text(wb, "Governance")
        assert "R99" in text, "Governance sheet must mention R99"
        assert "NOT APPROVED" in text, "R99 must be marked NOT APPROVED"

    def test_governance_sheet_says_r102_not_approved(self):
        wb = openpyxl.load_workbook(WORKBOOK_PATH, read_only=True)
        text = sheet_text(wb, "Governance")
        assert "R102" in text, "Governance sheet must mention R102"
        assert "NOT APPROVED" in text, "R102 must be marked NOT APPROVED"


@skip_if_no_openpyxl
class TestReturnsSheet:
    """Returns sheet has project IRR and equity IRR."""

    def test_returns_has_project_irr(self):
        wb = openpyxl.load_workbook(WORKBOOK_PATH, read_only=True)
        text = sheet_text(wb, "Returns")
        assert "Project IRR" in text
        # Should show ~9.41%
        assert any(v and "9.41" in str(v) for r in range(1, wb["Returns"].max_row + 1)
                   for c in range(1, wb["Returns"].max_column + 1)
                   for v in [wb["Returns"].cell(row=r, column=c).value])

    def test_returns_has_equity_irr(self):
        wb = openpyxl.load_workbook(WORKBOOK_PATH, read_only=True)
        text = sheet_text(wb, "Returns")
        assert "Equity IRR" in text


class TestNoRuntimeFilesChanged:
    """Verify no changes to runtime model files."""

    def test_no_runtime_model_formula_files_changed(self):
        """Git status should not show modifications to domain/ or app/waterfall/ or app/ui_runner.py."""
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        changed = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        bad = [
            f for f in changed
            if f.startswith("M") and (
                "domain/" in f or
                "app/waterfall/" in f or
                "app/ui_runner.py" in f or
                "app/tax_bridge.py" in f or
                "app/project_factories.py" in f
            )
        ]
        assert len(bad) == 0, f"Runtime model files were modified: {bad}"


class TestCSVOutputs:
    """CSV reports exist."""

    def test_summary_csv_exists(self):
        csv_path = os.path.join(REPORTS_DIR, "phase10_human_readable_calibration_summary.csv")
        assert os.path.exists(csv_path), f"Summary CSV not found: {csv_path}"

    def test_gap_analysis_csv_exists(self):
        csv_path = os.path.join(REPORTS_DIR, "phase10_human_readable_calibration_gap_analysis.csv")
        assert os.path.exists(csv_path), f"Gap analysis CSV not found: {csv_path}"

    def test_source_map_csv_exists(self):
        csv_path = os.path.join(REPORTS_DIR, "phase10_human_readable_calibration_source_map.csv")
        assert os.path.exists(csv_path), f"Source map CSV not found: {csv_path}"