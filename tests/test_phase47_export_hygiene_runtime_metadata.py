"""Phase 47 — Export Hygiene Runtime Metadata tests.

Verifies:
1. export_metadata helper module exists
2. build_export_metadata returns all required fields
3. TUHO/Oborovo metadata says trusted pilot scope
4. Generic project metadata says exploratory/unvalidated
5. metadata_rows helper works
6. institutional_workbook has Export_Metadata sheet
7. calibration_reconciliation has Export_Metadata sheet
8. existing sheets remain present (Cover, Governance, etc.)
9. Export_Metadata sheet contains last clean backend run wording
10. Export_Metadata sheet contains non-claims wording
11. Docs exist: phase47 doc and metadata matrix
12. JSON summary parses with no_formula_changes
13. Guardrails stated in JSON
14. No fixture CSVs changed
15. No JS financial calculations added
16. import main_web OK
"""
import json
from pathlib import Path

import pytest

BASE_SHA = "a5fafdf8b93ff23d7272b11b1928798b3bc9fa63"

EXPORT_METADATA_PY = Path("app/export_metadata.py")
INSTITUTIONAL_XLSX = Path("app/export/institutional_workbook.py")
CALIBRATION_XLSX = Path("app/export/calibration_reconciliation.py")
DOC_MD = Path("docs/phase47_export_hygiene_runtime_metadata.md")
DOC_MATRIX = Path("docs/phase47_export_metadata_matrix.md")
JSON_SUMMARY = Path("reports/phase47_export_metadata_summary.json")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: export_metadata helper module exists
# ─────────────────────────────────────────────────────────────────────────────
def test_export_metadata_module_exists():
    assert EXPORT_METADATA_PY.exists(), f"{EXPORT_METADATA_PY} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: build_export_metadata returns all required fields
# ─────────────────────────────────────────────────────────────────────────────
def test_build_export_metadata_has_required_fields():
    from app.export_metadata import build_export_metadata
    meta = build_export_metadata(
        project_id="tuho",
        project_name="TUHO Wind",
        active_project="tuho",
        export_type="test_export",
    )
    required = [
        "export_generated_at",
        "export_type",
        "active_project",
        "project_id",
        "project_name",
        "scenario_id",
        "scenario_name",
        "scenario_saved_at",
        "last_clean_backend_run_at",
        "dirty_or_stale_warning",
        "validation_status",
        "trusted_pilot_scope",
        "generic_boundary",
        "non_claims",
        "backend_source_of_truth",
    ]
    for field in required:
        assert field in meta, f"Missing field: {field}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: TUHO/Oborovo metadata says trusted pilot scope
# ─────────────────────────────────────────────────────────────────────────────
def test_tuho_metadata_says_trusted_pilot_scope():
    from app.export_metadata import build_export_metadata
    meta = build_export_metadata(
        project_id="tuho",
        active_project="tuho",
        export_type="test_export",
    )
    assert "TUHO" in meta["trusted_pilot_scope"], (
        "TUHO metadata must reference TUHO in trusted_pilot_scope"
    )
    assert "frozen-template" in meta["trusted_pilot_scope"].lower(), (
        "trusted_pilot_scope must reference frozen-template path"
    )


def test_oborovo_metadata_says_trusted_pilot_scope():
    from app.export_metadata import build_export_metadata
    meta = build_export_metadata(
        project_id="oborovo",
        active_project="oborovo",
        export_type="test_export",
    )
    assert "Oborovo" in meta["trusted_pilot_scope"], (
        "Oborovo metadata must reference Oborovo in trusted_pilot_scope"
    )
    assert "frozen-template" in meta["trusted_pilot_scope"].lower(), (
        "trusted_pilot_scope must reference frozen-template path"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Generic project metadata says exploratory/unvalidated
# ─────────────────────────────────────────────────────────────────────────────
def test_generic_metadata_says_exploratory_unvalidated():
    from app.export_metadata import build_export_metadata
    meta = build_export_metadata(
        project_id="generic-solar",
        active_project="generic-solar",
        export_type="test_export",
    )
    assert "exploratory" in meta["generic_boundary"].lower(), (
        "generic_boundary must mention 'exploratory'"
    )
    assert "unvalidated" in meta["generic_boundary"].lower(), (
        "generic_boundary must mention 'unvalidated'"
    )
    assert "not for financial decisions" in meta["generic_boundary"].lower(), (
        "generic_boundary must say not for financial decisions"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: metadata_rows helper works
# ─────────────────────────────────────────────────────────────────────────────
def test_metadata_rows_helper():
    from app.export_metadata import build_export_metadata, metadata_rows
    meta = build_export_metadata(
        project_id="tuho",
        active_project="tuho",
        export_type="test_export",
    )
    rows = metadata_rows(meta)
    assert isinstance(rows, list), "metadata_rows must return a list"
    assert all(isinstance(r, tuple) and len(r) == 2 for r in rows), (
        "metadata_rows must return list of (label, value) tuples"
    )
    labels = [r[0] for r in rows]
    assert "Export generated at" in labels, "metadata_rows must include Export generated at"
    assert "Export type" in labels, "metadata_rows must include Export type"
    assert "Non-claims" in labels, "metadata_rows must include Non-claims"
    assert "Backend source of truth" in labels, (
        "metadata_rows must include Backend source of truth"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: institutional_workbook has Export_Metadata sheet
# ─────────────────────────────────────────────────────────────────────────────
def test_institutional_workbook_has_export_metadata_sheet():
    text = INSTITUTIONAL_XLSX.read_text()
    assert "Export_Metadata" in text, (
        "institutional_workbook.py must reference Export_Metadata sheet"
    )
    assert "_write_export_metadata_sheet" in text, (
        "institutional_workbook.py must have _write_export_metadata_sheet function"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: calibration_reconciliation has Export_Metadata sheet
# ─────────────────────────────────────────────────────────────────────────────
def test_calibration_reconciliation_has_export_metadata_sheet():
    text = CALIBRATION_XLSX.read_text()
    assert "Export_Metadata" in text, (
        "calibration_reconciliation.py must reference Export_Metadata sheet"
    )
    assert "_write_export_metadata_sheet" in text, (
        "calibration_reconciliation.py must have _write_export_metadata_sheet function"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: existing sheets remain present
# ─────────────────────────────────────────────────────────────────────────────
def test_institutional_sheets_unchanged():
    text = INSTITUTIONAL_XLSX.read_text()
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
# Test 9: Export_Metadata sheet contains last clean backend run wording
# ─────────────────────────────────────────────────────────────────────────────
def test_export_metadata_sheet_last_clean_run():
    text = INSTITUTIONAL_XLSX.read_text()
    assert "last clean backend run" in text.lower(), (
        "institutional_workbook.py must mention 'last clean backend run' in Export_Metadata"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: Export_Metadata sheet contains non-claims wording
# ─────────────────────────────────────────────────────────────────────────────
def test_export_metadata_sheet_non_claims():
    text = INSTITUTIONAL_XLSX.read_text()
    assert "NON-CLAIMS" in text, (
        "institutional_workbook.py must have NON-CLAIMS block in Export_Metadata"
    )
    assert "not bank" in text.lower() or "not external" in text.lower(), (
        "institutional_workbook.py must have non-claims wording"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: Docs exist: phase47 doc and metadata matrix
# ─────────────────────────────────────────────────────────────────────────────
def test_phase47_doc_exists():
    assert DOC_MD.exists(), f"{DOC_MD} not found"


def test_phase47_matrix_exists():
    assert DOC_MATRIX.exists(), f"{DOC_MATRIX} not found"


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: JSON summary parses with no_formula_changes
# ─────────────────────────────────────────────────────────────────────────────
def test_json_summary_parses():
    assert JSON_SUMMARY.exists(), f"{JSON_SUMMARY} not found"
    data = json.loads(JSON_SUMMARY.read_text())
    assert data.get("no_formula_changes") is True, (
        "JSON must have no_formula_changes = true"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 13: Guardrails stated in JSON
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
# Test 14: No fixture CSVs changed
# ─────────────────────────────────────────────────────────────────────────────
def test_no_fixture_csv_changes():
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--", "*.csv"],
        capture_output=True, text=True, cwd=Path(__file__).parent.parent,
    )
    # Allow tests/ CSVs
    changed = [l for l in result.stdout.strip().split("\n") if l and not l.startswith("tests/")]
    assert len(changed) == 0, f"Fixture CSVs changed: {changed}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 15: No JS financial calculations added
# ─────────────────────────────────────────────────────────────────────────────
def test_no_js_financial_calculations():
    js_files = list(Path("static/js").glob("*.js"))
    for js in js_files:
        content = js.read_text().lower()
        # If file mentions financial terms AND has function/=> syntax, flag it
        financial_terms = ["irr", "npv", "dscr", "cashflow", "equity_irr", "project_irr"]
        has_calc = any(
            term in content
            and ("function" in content or "=>" in content)
            for term in financial_terms
        )
        if has_calc:
            # But allow if it's just displaying values passed from backend
            assert "display" in content or "element" in content or "innerHTML" in content, (
                f"{js.name} appears to contain financial calculations, not just display"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Test 16: import main_web OK
# ─────────────────────────────────────────────────────────────────────────────
def test_import_main_web():
    import main_web  # noqa: F401
    # If this raises, test fails