"""Shape-only characterization tests for the next-sprint decision matrix.

Asserts the document exists, lists all 7 candidates A-G, has a
comparison matrix, and produces a primary + parallel recommendation
that are distinct and from the candidate set.
"""

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "docs" / "phase_next_sprint_decision_matrix.md"
REPORT_PATH = REPO_ROOT / "reports" / "phase_next_sprint_decision_matrix.json"


# --- Existence ------------------------------------------------------------

def test_doc_exists():
    assert DOC_PATH.exists()


def test_report_exists():
    assert REPORT_PATH.exists()


# --- Document shape -------------------------------------------------------

def test_doc_has_required_sections():
    text = DOC_PATH.read_text()
    required = [
        "# Next Sprint Decision Matrix",
        "## 1. The seven candidates",
        "## 2. Comparison matrix",
        "## 3. Per-option detail",
        "## 4. Final recommendation",
        "## 5. No-go list",
        "## 6. What this document does NOT do",
        "## 7. Test footprint",
    ]
    for s in required:
        assert s in text, f"missing section: {s}"


def test_doc_lists_all_seven_candidates():
    text = DOC_PATH.read_text()
    for code in ["A", "B", "C", "D", "E", "F", "G"]:
        # must mention each code letter in §1 or §3
        assert f"### {code}." in text or f"**{code}**" in text, f"missing candidate {code}"


def test_doc_has_comparison_matrix():
    text = DOC_PATH.read_text()
    # §2 must have a markdown table with all 7 codes
    section = text.split("## 2. Comparison matrix", 1)[1].split("## 3.", 1)[0]
    for code in ["A", "B", "C", "D", "E", "F", "G"]:
        assert f"| {code} |" in section, f"missing code {code} in comparison matrix"


def test_doc_has_primary_and_parallel_recommendation():
    text = DOC_PATH.read_text()
    # §4.1 primary, §4.2 parallel
    assert "## 4.1 Primary:" in text
    assert "## 4.2 Parallel low-risk:" in text


def test_doc_has_no_go_list():
    text = DOC_PATH.read_text()
    assert "## 5. No-go list" in text
    nogo = text.split("## 5. No-go list", 1)[1].split("## 6.", 1)[0]
    items = re.findall(r"^- ❌", nogo, re.MULTILINE)
    assert len(items) >= 5, f"expected >=5 no-go items, found {len(items)}"


# --- Report shape ---------------------------------------------------------

def test_report_is_valid_json():
    data = json.loads(REPORT_PATH.read_text())
    assert isinstance(data, dict)


def test_report_required_keys():
    data = json.loads(REPORT_PATH.read_text())
    for k in [
        "phase", "date", "type", "base_sha", "status",
        "candidates", "primary_recommendation", "parallel_recommendation",
        "nogo_list", "suggested_sequencing",
        "hard_rules_respected", "no_production_code_change",
        "no_promotion", "no_runtime_change", "rc1_untouched",
    ]:
        assert k in data, f"missing key: {k}"


def test_report_seven_candidates():
    data = json.loads(REPORT_PATH.read_text())
    codes = [c["code"] for c in data["candidates"]]
    assert sorted(codes) == ["A", "B", "C", "D", "E", "F", "G"]


def test_report_recommendations_are_distinct():
    data = json.loads(REPORT_PATH.read_text())
    assert data["primary_recommendation"] != data["parallel_recommendation"]
    # both must be in candidate set
    codes = [c["code"] for c in data["candidates"]]
    assert data["primary_recommendation"] in codes
    assert data["parallel_recommendation"] in codes


def test_report_each_candidate_has_required_fields():
    data = json.loads(REPORT_PATH.read_text())
    for c in data["candidates"]:
        for k in ["code", "name", "product_value", "implementation_risk",
                  "parity_risk", "effort", "dependency_blockers",
                  "recommended_order"]:
            assert k in c, f"candidate {c.get('code')} missing: {k}"


def test_report_no_go_list_size():
    data = json.loads(REPORT_PATH.read_text())
    assert len(data["nogo_list"]) >= 5, f"expected >=5 no-go, got {len(data['nogo_list'])}"


def test_report_sequencing_size():
    data = json.loads(REPORT_PATH.read_text())
    # at least 4 sprints in the suggested sequence
    assert len(data["suggested_sequencing"]) >= 4


def test_report_hard_rules():
    data = json.loads(REPORT_PATH.read_text())
    assert data["hard_rules_respected"] is True
    assert data["no_production_code_change"] is True
    assert data["no_promotion"] is True
    assert data["no_runtime_change"] is True
    assert data["rc1_untouched"] is True


def test_report_status_draft():
    data = json.loads(REPORT_PATH.read_text())
    assert data["status"] == "DRAFT"
    assert data["type"] == "report-only"
