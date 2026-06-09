"""Shape-only characterization tests for the R-PAR-2 Option A
technical design (hypothetical)."""

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "docs" / "phase_rpar2_option_a_technical_design.md"
REPORT_PATH = REPO_ROOT / "reports" / "phase_rpar2_option_a_technical_design.json"


# --- Existence ------------------------------------------------------------

def test_doc_exists():
    assert DOC_PATH.exists()


def test_report_exists():
    assert REPORT_PATH.exists()


# --- Document shape -------------------------------------------------------

def test_doc_has_required_sections():
    text = DOC_PATH.read_text()
    required = [
        "# R-PAR-2 Option A",
        "## 0. Purpose",
        "## 1. Scope of the technical change",
        "## 2. Senior IDC base-rate row model",
        "## 3. Required inputs",
        "## 4. Excel parity evidence needed",
        "## 5. Tests required before any promotion PR",
        "## 6. No-go criteria",
        "## 7. Implementation order",
        "## 8. What this document does NOT do",
        "## 9. Test footprint",
    ]
    for s in required:
        assert s in text, f"missing section: {s}"


def test_doc_has_base_rate_formula():
    text = DOC_PATH.read_text()
    # the formula is in §2.1
    assert "base_rate" in text
    assert "time_fraction" in text
    # contractually explicit
    assert "30/360" in text or "actual/365" in text


def test_doc_has_parity_gates():
    text = DOC_PATH.read_text()
    assert "±1%" in text or "+/-1%" in text
    assert "tolerance" in text.lower()


def test_doc_has_no_go_criteria():
    text = DOC_PATH.read_text()
    sec = text.split("## 6. No-go criteria", 1)[1].split("## 7.", 1)[0]
    items = re.findall(r"^\d+\.\s+", sec, re.MULTILINE)
    assert len(items) >= 6, f"expected >=6 no-go criteria, found {len(items)}"


def test_doc_has_implementation_order():
    text = DOC_PATH.read_text()
    sec = text.split("## 7. Implementation order", 1)[1].split("## 8.", 1)[0]
    items = re.findall(r"^\d+\.\s+", sec, re.MULTILINE)
    assert len(items) >= 8, f"expected >=8 implementation steps, found {len(items)}"


def test_doc_declares_no_implementation():
    text = DOC_PATH.read_text()
    # front matter must say "NO IMPLEMENTATION"
    assert "NO IMPLEMENTATION" in text
    assert "design only" in text.lower() or "design-only" in text.lower()


# --- Report shape ---------------------------------------------------------

def test_report_is_valid_json():
    data = json.loads(REPORT_PATH.read_text())
    assert isinstance(data, dict)


def test_report_required_keys():
    data = json.loads(REPORT_PATH.read_text())
    for k in [
        "phase", "date", "type", "base_sha", "status",
        "scope_label", "what_changes", "what_does_not_change",
        "base_rate_formula", "new_inputs_required", "parity_gates",
        "test_classes_required", "test_count_estimate",
        "no_go_criteria", "implementation_order",
        "hard_rules_respected", "no_production_code_change",
        "no_promotion", "no_runtime_change", "no_model_change",
        "no_formula_change", "rc1_untouched",
    ]:
        assert k in data, f"missing key: {k}"


def test_report_type_is_design_only():
    data = json.loads(REPORT_PATH.read_text())
    assert data["type"] == "design-only"
    assert data["status"] == "DRAFT"
    assert "NO IMPLEMENTATION" in data["scope_label"]


def test_report_no_go_criteria_size():
    data = json.loads(REPORT_PATH.read_text())
    assert len(data["no_go_criteria"]) >= 6


def test_report_implementation_order_size():
    data = json.loads(REPORT_PATH.read_text())
    assert len(data["implementation_order"]) >= 8


def test_report_test_count_estimate():
    data = json.loads(REPORT_PATH.read_text())
    assert data["test_count_estimate"] >= 20


def test_report_hard_rules():
    data = json.loads(REPORT_PATH.read_text())
    for k in [
        "hard_rules_respected", "no_production_code_change",
        "no_promotion", "no_runtime_change", "no_model_change",
        "no_formula_change", "rc1_untouched",
    ]:
        assert data[k] is True, f"{k} not True"


def test_report_parity_gates_have_tolerance():
    data = json.loads(REPORT_PATH.read_text())
    for k, v in data["parity_gates"].items():
        if "tolerance" in k:
            assert "1%" in str(v), f"tolerance {k}={v} not 1%"


def test_report_new_inputs_required():
    data = json.loads(REPORT_PATH.read_text())
    assert len(data["new_inputs_required"]) >= 1
    names = [i["name"] for i in data["new_inputs_required"]]
    # at least one capitalization or day-count input
    assert any("capitalize" in n or "day_count" in n for n in names)
