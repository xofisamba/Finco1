"""Shape-only characterization tests for the Pilot UX Safe Track inventory."""

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "docs" / "phase_pilot_ux_safe_track_inventory.md"
REPORT_PATH = REPO_ROOT / "reports" / "phase_pilot_ux_safe_track_inventory.json"


# --- Existence ------------------------------------------------------------

def test_doc_exists():
    assert DOC_PATH.exists()


def test_report_exists():
    assert REPORT_PATH.exists()


# --- Document shape -------------------------------------------------------

def test_doc_has_required_sections():
    text = DOC_PATH.read_text()
    required = [
        "# Pilot UX Safe Track",
        "## 0. Purpose",
        "## 1. The five categories",
        "## 2. Consolidated ranking",
        "## 3. Recommended safe-track sprint plan",
        "## 4. Hard-rule coverage",
        "## 5. What this document does NOT do",
        "## 6. Test footprint",
    ]
    for s in required:
        assert s in text, f"missing section: {s}"


def test_doc_has_all_five_categories():
    text = DOC_PATH.read_text()
    categories = [
        "1.1 Run status clarity",
        "1.2 Validation summary clarity",
        "1.3 CAPEX sheet readability",
        "1.4 Export/download clarity",
        "1.5 Stale run warning",
    ]
    for c in categories:
        assert c in text, f"missing category: {c}"


def test_doc_has_consolidated_ranking_table():
    text = DOC_PATH.read_text()
    sec = text.split("## 2. Consolidated ranking", 1)[1].split("## 3.", 1)[0]
    # must have a markdown table with at least 5 data rows
    rows = re.findall(r"^\| \d+ \|", sec, re.MULTILINE)
    assert len(rows) >= 5, f"expected >=5 ranking rows, found {len(rows)}"


def test_doc_declares_independence():
    text = DOC_PATH.read_text()
    # the independence rule must be prominent
    assert "independence" in text.lower()
    assert "R-PAR-2" in text
    assert "C10" in text


# --- Report shape ---------------------------------------------------------

def test_report_is_valid_json():
    data = json.loads(REPORT_PATH.read_text())
    assert isinstance(data, dict)


def test_report_required_keys():
    data = json.loads(REPORT_PATH.read_text())
    for k in [
        "phase", "date", "type", "base_sha", "status",
        "independence_rule", "items", "sprint_plan",
        "all_parity_risk_zero", "all_independent_of_rpar2_c10",
        "hard_rules_respected", "no_production_code_change",
        "no_promotion", "no_runtime_change", "no_model_change",
        "no_formula_change", "no_persistence_schema_change",
        "rc1_untouched",
    ]:
        assert k in data, f"missing key: {k}"


def test_report_five_items():
    data = json.loads(REPORT_PATH.read_text())
    assert len(data["items"]) == 5


def test_report_all_parity_risk_zero():
    data = json.loads(REPORT_PATH.read_text())
    for item in data["items"]:
        assert item["parity_risk"] == 0, f"item {item['category']} has parity_risk={item['parity_risk']}"


def test_report_all_items_independent():
    data = json.loads(REPORT_PATH.read_text())
    for item in data["items"]:
        assert item["independence"] is True, f"item {item['category']} not independent"


def test_report_items_have_required_fields():
    data = json.loads(REPORT_PATH.read_text())
    for item in data["items"]:
        for k in ["rank", "category", "user_value", "parity_risk",
                  "implementation_risk", "effort", "composite_score",
                  "independence"]:
            assert k in item, f"item missing: {k}"


def test_report_ranks_unique_and_1_to_5():
    data = json.loads(REPORT_PATH.read_text())
    ranks = sorted([item["rank"] for item in data["items"]])
    assert ranks == [1, 2, 3, 4, 5]


def test_report_sprint_plan_size():
    data = json.loads(REPORT_PATH.read_text())
    assert len(data["sprint_plan"]) >= 3


def test_report_sprint_plan_covers_all_items():
    data = json.loads(REPORT_PATH.read_text())
    covered = set()
    for sprint in data["sprint_plan"]:
        for item_str in sprint["items"]:
            # extract category key
            m = re.search(r"(\w[\w_]+)\s*\(", item_str)
            if m:
                covered.add(m.group(1))
    # all 5 categories should be covered
    all_cats = {item["category"] for item in data["items"]}
    # each category key (before _) should appear
    short_cats = {c.split("_")[0] for c in all_cats}
    for short in short_cats:
        assert short in covered or any(short in str(sprint["items"]) for sprint in data["sprint_plan"]), f"category {short} not in any sprint"


def test_report_hard_rules():
    data = json.loads(REPORT_PATH.read_text())
    for k in [
        "hard_rules_respected", "no_production_code_change",
        "no_promotion", "no_runtime_change", "no_model_change",
        "no_formula_change", "no_persistence_schema_change",
        "rc1_untouched",
    ]:
        assert data[k] is True, f"{k} not True"


def test_report_status_draft():
    data = json.loads(REPORT_PATH.read_text())
    assert data["status"] == "DRAFT"
    assert data["type"] == "report-only"
    assert data["all_parity_risk_zero"] is True
    assert data["all_independent_of_rpar2_c10"] is True
