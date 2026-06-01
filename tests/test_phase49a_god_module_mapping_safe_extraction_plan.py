"""Phase 49A — God Module Mapping / Safe Extraction Plan.

Docs/reports/tests-only phase. These tests assert the planning artifacts exist
and carry the required content and guardrails. No production behavior is exercised.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORTS = ROOT / "reports"

MAIN_DOC = DOCS / "phase49a_god_module_mapping_safe_extraction_plan.md"
MATRIX_DOC = DOCS / "phase49a_extraction_dependency_matrix.md"
FIRST_DOC = DOCS / "phase49a_first_extraction_candidate_export_service.md"
JSON_SUMMARY = REPORTS / "phase49a_god_module_mapping_summary.json"


def test_main_doc_exists():
    assert MAIN_DOC.exists()


def test_extraction_dependency_matrix_exists():
    assert MATRIX_DOC.exists()


def test_first_extraction_candidate_doc_exists():
    assert FIRST_DOC.exists()


def test_json_summary_parses_and_has_required_keys():
    if not JSON_SUMMARY.exists():
        return  # optional
    data = json.loads(JSON_SUMMARY.read_text())
    assert data.get("recommended_first_extraction") == "export_service"
    assert data.get("no_behavior_changes") is True


def test_docs_mention_main_web_as_hotspot():
    text = MAIN_DOC.read_text().lower()
    assert "main_web.py" in text
    assert "route" in text and ("orchestration" in text or "hotspot" in text)


def test_matrix_includes_required_candidate_rows():
    text = MATRIX_DOC.read_text().lower()
    required = [
        "export", "scenario state", "run orchestration",
        "template context", "validation", "audit",
        "auth", "session", "backup", "readyz",
        "snapshot collector", "ui component",
    ]
    for token in required:
        assert token in text, f"missing candidate row token: {token}"


def test_docs_recommend_export_service_first():
    text = (MAIN_DOC.read_text() + FIRST_DOC.read_text()).lower()
    assert "export_service" in text or "export/download service" in text


def test_docs_state_no_behavior_changes():
    text = MAIN_DOC.read_text().lower()
    assert "no behavior" in text or "no-behavior-change" in text or "without changing runtime behavior" in text


def test_docs_state_no_formula_or_runtime_or_model_output_changes():
    text = MAIN_DOC.read_text().lower()
    assert "no financial formula" in text
    assert "runtime calculation" in text or "runtime behavior" in text
    assert "model output" in text


def test_docs_include_guardrails():
    text = MAIN_DOC.read_text()
    assert "G20 remains BLOCKED" in text
    assert "R99/R102 remain NOT APPROVED" in text
    assert "partial_pay_sweep" in text
    assert "DSCR sculpting" in text
    assert "Backend remains source of truth" in text


def test_phase47_48_export_metadata_index_preserved_reference():
    """Phase 49A must reference that Phase 47/48 export metadata/index is preserved."""
    text = FIRST_DOC.read_text()
    assert "Export_Metadata" in text and "Workbook_Index" in text
    # the anchoring tests/docs still exist
    assert (DOCS / "phase47_export_hygiene_runtime_metadata.md").exists()
    assert (DOCS / "phase48_export_index_readme_sheet_polish.md").exists()


def test_no_js_financial_calculations_added():
    """Phase 49A touches no JS; confirm no new .js files with financial calc keywords under app/."""
    app_dir = ROOT / "app"
    suspicious = []
    for js in app_dir.rglob("*.js"):
        body = js.read_text(errors="ignore").lower()
        if any(k in body for k in ("dscr", "irr =", "npv", "waterfall", "cashflow =")):
            suspicious.append(str(js))
    assert not suspicious, f"unexpected JS financial calc: {suspicious}"
