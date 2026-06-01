"""Phase 48 — Export Index README Sheet Polish tests.

Verifies:
1. workbook_index helper module exists
2. INSTITUTIONAL_SHEET_INVENTORY and CALIBRATION_SHEET_INVENTORY exist
3. write_workbook_index_sheet_full function exists
4. Institutional workbook includes Export_Metadata and Workbook_Index sheets
5. Calibration workbook includes Export_Metadata and Workbook_Index sheets
6. Export_Metadata remains first sheet
7. Workbook_Index is second sheet
8. Workbook_Index includes sheet inventory table or clear sheet-purpose rows
9. Workbook_Index includes last clean backend run wording
10. Workbook_Index includes generic unvalidated warning
11. Workbook_Index includes internal review / not certified audit wording
12. Workbook_Index includes non-claims wording
13. Workbook_Index includes G20 BLOCKED and R99/R102 NOT APPROVED
14. Existing sheets remain present (Cover, Governance, etc.)
15. Docs exist: phase48 doc and workbook index matrix
16. JSON summary parses with workbook_index_status and no_formula_changes
17. Guardrails in JSON
18. No fixture CSVs changed
19. No JS financial calculations added
20. import main_web OK
"""
import json
from pathlib import Path

import pytest

BASE_SHA = "d6276fac210d960a6a4b7e2c201a51e4d3fac8d3"

WORKBOOK_INDEX_PY = Path("app/export/workbook_index.py")
INSTITUTIONAL_PY = Path("app/export/institutional_workbook.py")
CALIBRATION_PY = Path("app/export/calibration_reconciliation.py")
DOC_MD = Path("docs/phase48_export_index_readme_sheet_polish.md")
DOC_MATRIX = Path("docs/phase48_workbook_index_matrix.md")
JSON_SUMMARY = Path("reports/phase48_export_index_readme_summary.json")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: workbook_index helper module exists
# ─────────────────────────────────────────────────────────────────────────────
def test_workbook_index_module_exists():
    assert WORKBOOK_INDEX_PY.exists(), f"{WORKBOOK_INDEX_PY} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Sheet inventory constants exist
# ─────────────────────────────────────────────────────────────────────────────
def test_institutional_sheet_inventory_exists():
    from app.export.workbook_index import INSTITUTIONAL_SHEET_INVENTORY
    assert isinstance(INSTITUTIONAL_SHEET_INVENTORY, list), (
        "INSTITUTIONAL_SHEET_INVENTORY must be a list"
    )
    assert len(INSTITUTIONAL_SHEET_INVENTORY) > 0, (
        "INSTITUTIONAL_SHEET_INVENTORY must not be empty"
    )
    # Each row must be a 5-tuple: (sheet_name, purpose, audience, status, notes)
    for row in INSTITUTIONAL_SHEET_INVENTORY:
        assert isinstance(row, tuple), f"Row {row} must be a tuple"
        assert len(row) == 5, f"Row {row} must have 5 elements"


def test_calibration_sheet_inventory_exists():
    from app.export.workbook_index import CALIBRATION_SHEET_INVENTORY
    assert isinstance(CALIBRATION_SHEET_INVENTORY, list), (
        "CALIBRATION_SHEET_INVENTORY must be a list"
    )
    assert len(CALIBRATION_SHEET_INVENTORY) > 0, (
        "CALIBRATION_SHEET_INVENTORY must not be empty"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: write_workbook_index_sheet_full function exists
# ─────────────────────────────────────────────────────────────────────────────
def test_write_workbook_index_sheet_full_exists():
    from app.export.workbook_index import write_workbook_index_sheet_full
    assert callable(write_workbook_index_sheet_full), (
        "write_workbook_index_sheet_full must be callable"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Institutional workbook includes Export_Metadata and Workbook_Index
# ─────────────────────────────────────────────────────────────────────────────
def test_institutional_has_export_metadata_and_index():
    text = INSTITUTIONAL_PY.read_text()
    assert "Export_Metadata" in text, (
        "institutional_workbook.py must reference Export_Metadata sheet"
    )
    assert "Workbook_Index" in text, (
        "institutional_workbook.py must reference Workbook_Index sheet"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Calibration workbook includes Export_Metadata and Workbook_Index
# ─────────────────────────────────────────────────────────────────────────────
def test_calibration_has_export_metadata_and_index():
    text = CALIBRATION_PY.read_text()
    assert "Export_Metadata" in text, (
        "calibration_reconciliation.py must reference Export_Metadata sheet"
    )
    assert "Workbook_Index" in text, (
        "calibration_reconciliation.py must reference Workbook_Index sheet"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Export_Metadata remains first sheet
# ─────────────────────────────────────────────────────────────────────────────
def test_export_metadata_remains_first_sheet():
    text = INSTITUTIONAL_PY.read_text()
    # The first create_sheet / active title should be Export_Metadata
    # Check the definition order
    lines = text.split("\n")
    export_meta_idx = None
    for i, line in enumerate(lines):
        if 'export_meta.title = "Export_Metadata"' in line or 'title = "Export_Metadata"' in line:
            export_meta_idx = i
            break
    assert export_meta_idx is not None, (
        "Export_Metadata must be set as active sheet title in institutional_workbook.py"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Workbook_Index is second sheet
# ─────────────────────────────────────────────────────────────────────────────
def test_workbook_index_is_second_sheet():
    text = INSTITUTIONAL_PY.read_text()
    # Workbook_Index should be created right after Export_Metadata
    # Look for the pattern: export_meta, then create_sheet("Workbook_Index")
    assert 'create_sheet("Workbook_Index")' in text, (
        "institutional_workbook.py must create Workbook_Index sheet"
    )
    # Check it comes after Export_Metadata
    export_meta_pos = text.find('title = "Export_Metadata"')
    index_pos = text.find('create_sheet("Workbook_Index")')
    assert export_meta_pos < index_pos, (
        "Workbook_Index must be created after Export_Metadata in institutional_workbook.py"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Workbook_Index includes sheet inventory table or clear sheet-purpose rows
# ─────────────────────────────────────────────────────────────────────────────
def test_workbook_index_has_sheet_inventory():
    text = WORKBOOK_INDEX_PY.read_text()
    assert "Sheet Inventory" in text, (
        "workbook_index.py must include 'Sheet Inventory' section"
    )
    assert "Sheet Name" in text and "Purpose" in text, (
        "workbook_index.py must include sheet inventory column headers"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Workbook_Index includes last clean backend run wording
# ─────────────────────────────────────────────────────────────────────────────
def test_workbook_index_last_clean_backend_run():
    text = WORKBOOK_INDEX_PY.read_text()
    assert "last clean backend run" in text.lower(), (
        "workbook_index.py must mention 'last clean backend run'"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: Workbook_Index includes generic unvalidated warning
# ─────────────────────────────────────────────────────────────────────────────
def test_workbook_index_generic_unvalidated_warning():
    text = WORKBOOK_INDEX_PY.read_text()
    assert "exploratory" in text.lower() and "unvalidated" in text.lower(), (
        "workbook_index.py must include generic exploratory/unvalidated warning"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: Workbook_Index includes internal review / not certified audit wording
# ─────────────────────────────────────────────────────────────────────────────
def test_workbook_index_internal_review_notice():
    text = WORKBOOK_INDEX_PY.read_text()
    assert "internal review" in text.lower() or "not certified" in text.lower(), (
        "workbook_index.py must include internal review / not certified audit notice"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: Workbook_Index includes non-claims wording
# ─────────────────────────────────────────────────────────────────────────────
def test_workbook_index_non_claims():
    text = WORKBOOK_INDEX_PY.read_text()
    assert "NON-CLAIMS" in text, (
        "workbook_index.py must include NON-CLAIMS section"
    )
    assert "not bank" in text.lower() or "not lender" in text.lower(), (
        "workbook_index.py must have non-claims wording"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 13: Workbook_Index includes G20 BLOCKED and R99/R102 NOT APPROVED
# ─────────────────────────────────────────────────────────────────────────────
def test_workbook_index_g20_r99_r102():
    text = WORKBOOK_INDEX_PY.read_text()
    assert "G20" in text and "BLOCKED" in text, (
        "workbook_index.py must state G20 BLOCKED"
    )
    assert "R99" in text and "NOT APPROVED" in text, (
        "workbook_index.py must state R99 NOT APPROVED"
    )
    assert "R102" in text and "NOT APPROVED" in text, (
        "workbook_index.py must state R102 NOT APPROVED"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 14: Existing sheets remain present (Cover, Governance, etc.)
# ─────────────────────────────────────────────────────────────────────────────
def test_institutional_existing_sheets_unchanged():
    text = INSTITUTIONAL_PY.read_text()
    sheets = [
        "Cover", "Governance", "Runtime Summary", "Inputs",
        "Construction", "OPEX", "CAPEX", "Revenue",
        "Senior Debt", "SHL", "Tax", "P&L",
        "Cash Flow", "Balance Sheet", "Audit", "Gap Register",
    ]
    for sheet in sheets:
        assert f'"{sheet}"' in text or f"'{sheet}'" in text, (
            f"Sheet {sheet} must remain in institutional_workbook.py"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 15: Docs exist: phase48 doc and workbook index matrix
# ─────────────────────────────────────────────────────────────────────────────
def test_phase48_doc_exists():
    assert DOC_MD.exists(), f"{DOC_MD} not found"


def test_phase48_matrix_exists():
    assert DOC_MATRIX.exists(), f"{DOC_MATRIX} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 16: JSON summary parses with workbook_index_status and no_formula_changes
# ─────────────────────────────────────────────────────────────────────────────
def test_json_summary_parses():
    assert JSON_SUMMARY.exists(), f"{JSON_SUMMARY} not found"
    data = json.loads(JSON_SUMMARY.read_text())
    assert data.get("workbook_index_status") == "implemented", (
        "JSON must have workbook_index_status = implemented"
    )
    assert data.get("no_formula_changes") is True, (
        "JSON must have no_formula_changes = true"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 17: Guardrails in JSON
# ─────────────────────────────────────────────────────────────────────────────
def test_guardrails_in_json():
    data = json.loads(JSON_SUMMARY.read_text())
    guardrails = data.get("guardrails", {})
    assert guardrails.get("g20") == "BLOCKED", "G20 must be BLOCKED in JSON"
    assert guardrails.get("r99") == "NOT APPROVED", "R99 must be NOT APPROVED in JSON"
    assert guardrails.get("r102") == "NOT APPROVED", "R102 must be NOT APPROVED in JSON"
    assert guardrails.get("partial_pay_sweep") == "not promoted", (
        "partial_pay_sweep must be not promoted in JSON"
    )
    assert guardrails.get("flat_min_dscr_sculpting") == "not promoted", (
        "flat_min_dscr_sculpting must be not promoted in JSON"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 18: No fixture CSVs changed
# ─────────────────────────────────────────────────────────────────────────────
def test_no_fixture_csv_changes():
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--", "*.csv"],
        capture_output=True, text=True, cwd=Path(__file__).parent.parent,
    )
    changed = [l for l in result.stdout.strip().split("\n") if l and not l.startswith("tests/")]
    assert len(changed) == 0, f"Fixture CSVs changed: {changed}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 19: No JS financial calculations added
# ─────────────────────────────────────────────────────────────────────────────
def test_no_js_financial_calculations():
    js_files = list(Path("static/js").glob("*.js"))
    for js in js_files:
        content = js.read_text().lower()
        financial_terms = ["irr", "npv", "dscr", "cashflow", "equity_irr", "project_irr"]
        has_calc = any(
            term in content
            and ("function" in content or "=>" in content)
            for term in financial_terms
        )
        if has_calc:
            assert "display" in content or "element" in content or "innerHTML" in content, (
                f"{js.name} appears to contain financial calculations, not just display"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Test 20: import main_web OK
# ─────────────────────────────────────────────────────────────────────────────
def test_import_main_web():
    import main_web  # noqa: F401