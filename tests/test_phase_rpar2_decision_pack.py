"""Shape-only characterization tests for the R-PAR-2 decision pack."""

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "docs" / "phase_rpar2_decision_pack.md"
REPORT_PATH = REPO_ROOT / "reports" / "phase_rpar2_decision_pack.json"


# --- Existence ------------------------------------------------------------

def test_doc_exists():
    assert DOC_PATH.exists()


def test_report_exists():
    assert REPORT_PATH.exists()


# --- Document shape -------------------------------------------------------

def test_doc_has_required_sections():
    text = DOC_PATH.read_text()
    required = [
        "# R-PAR-2 Decision Pack",
        "## 0. Purpose",
        "## 1. Recap of the R-PAR-2 caveat",
        "## 2. The three options",
        "## 3. Accounting impact",
        "## 4. Lender / audit impact",
        "## 5. Implementation effort",
        "## 6. Parity impact",
        "## 7. Strategic / product impact",
        "## 8. Risk score and effort summary",
        "## 9. Recommendation",
        "## 10. What this document does NOT do",
        "## 11. Test footprint",
    ]
    for s in required:
        assert s in text, f"missing section: {s}"


def test_doc_lists_all_three_options():
    text = DOC_PATH.read_text()
    for code in ["A", "B", "C"]:
        assert f"### 2.{['_','1','2','3'][['A','B','C'].index(code)+1]} " in text or f"### 2.{ord(code)-ord('A')+1} " in text or f"### 2.{code} " in text or f"### 2.{ord(code)-ord('A')+1}" in text, f"missing option {code}"


def test_doc_has_recommendation_in_section_9():
    text = DOC_PATH.read_text()
    sec = text.split("## 9. Recommendation", 1)[1].split("## 10.", 1)[0]
    # must recommend exactly one of A/B/C
    m = re.search(r"Recommended decision:\s*Option\s*([ABC])", sec)
    assert m, "no clear recommendation found"
    assert m.group(1) in ["A", "B", "C"]


def test_doc_recommendation_has_conditions():
    text = DOC_PATH.read_text()
    sec = text.split("## 9. Recommendation", 1)[1].split("## 10.", 1)[0]
    assert "Conditions for the" in sec
    # at least 3 conditions
    cond_section = sec.split("Conditions for the", 1)[1]
    items = re.findall(r"^\d+\.\s+", cond_section, re.MULTILINE)
    assert len(items) >= 3, f"expected >=3 conditions, found {len(items)}"


# --- Report shape ---------------------------------------------------------

def test_report_is_valid_json():
    data = json.loads(REPORT_PATH.read_text())
    assert isinstance(data, dict)


def test_report_required_keys():
    data = json.loads(REPORT_PATH.read_text())
    for k in [
        "phase", "date", "type", "base_sha", "status",
        "options", "recommendation", "recommendation_rationale",
        "fallback", "deferred_A_sprint", "conditions_for_B",
        "nogo_list_immediate",
        "hard_rules_respected", "no_production_code_change",
        "no_promotion", "no_runtime_change", "no_model_change",
        "rc1_untouched",
    ]:
        assert k in data, f"missing key: {k}"


def test_report_three_options():
    data = json.loads(REPORT_PATH.read_text())
    codes = [o["code"] for o in data["options"]]
    assert sorted(codes) == ["A", "B", "C"]


def test_report_each_option_has_required_fields():
    data = json.loads(REPORT_PATH.read_text())
    for o in data["options"]:
        for k in ["code", "name", "goal", "accounting_impact",
                  "lender_audit_impact", "implementation_effort",
                  "parity_impact", "risk"]:
            assert k in o, f"option {o.get('code')} missing: {k}"


def test_report_recommendation_is_one_of_abc():
    data = json.loads(REPORT_PATH.read_text())
    assert data["recommendation"] in ["A", "B", "C"]


def test_report_fallback_mentions_alternative():
    data = json.loads(REPORT_PATH.read_text())
    # if recommendation is B, fallback string must mention A or C
    if data["recommendation"] == "B":
        fb = data["fallback"]
        assert "A" in fb or "C" in fb, f"fallback {fb!r} does not mention A or C"


def test_report_conditions_for_b_size():
    data = json.loads(REPORT_PATH.read_text())
    assert len(data["conditions_for_B"]) >= 3


def test_report_hard_rules():
    data = json.loads(REPORT_PATH.read_text())
    assert data["hard_rules_respected"] is True
    assert data["no_production_code_change"] is True
    assert data["no_promotion"] is True
    assert data["no_runtime_change"] is True
    assert data["no_model_change"] is True
    assert data["rc1_untouched"] is True


def test_report_status_draft():
    data = json.loads(REPORT_PATH.read_text())
    assert data["status"] == "DRAFT"
    assert data["type"] == "report-only"
