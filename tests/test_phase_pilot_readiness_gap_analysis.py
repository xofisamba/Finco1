"""Shape-only characterization tests for the pilot-readiness gap analysis PR.

These tests assert the *shape* of the gap analysis (existence, count,
classification coverage). They do NOT assert content beyond the
document's stated blocker counts. They are an existence and
coverage check, not a quality check.

Type: REPORT-ONLY, DOCS+TESTS ONLY
Status: DRAFT
Date: 2026-06-09
Base: 72f3ab6 (post-#557)
"""

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "docs" / "phase_pilot_readiness_gap_analysis.md"
REPORT_PATH = REPO_ROOT / "reports" / "phase_pilot_readiness_gap_analysis.json"


# ---------------------------------------------------------------------------
# Existence checks
# ---------------------------------------------------------------------------

def test_doc_file_exists():
    assert DOC_PATH.exists(), f"missing: {DOC_PATH}"


def test_report_file_exists():
    assert REPORT_PATH.exists(), f"missing: {REPORT_PATH}"


# ---------------------------------------------------------------------------
# Document content shape
# ---------------------------------------------------------------------------

def test_doc_has_required_sections():
    text = DOC_PATH.read_text()
    required = [
        "# Pilot-Readiness Gap Analysis",
        "## 0. Purpose",
        "## 1. Scope & Method",
        "## 2. Top 20 Pilot-Readiness Blockers",
        "## 3. Top 10 Paid-Product Blockers",
        "## 4. Top 10 Enterprise Blockers",
        "## 5. Cross-cutting risk summary",
        "## 6. Recommended next sprint",
        "## 7. No-go list",
        "## 8. What this document does NOT do",
        "## 9. Test footprint",
    ]
    for section in required:
        assert section in text, f"missing section: {section}"


def test_doc_pilot_blocker_table_has_20_rows():
    """The §2 table must list 20 pilot blockers."""
    text = DOC_PATH.read_text()
    # section 2 is between '## 2. Top 20' and '## 3.'
    m = re.search(r"## 2\. Top 20[^\n]*\n(.*?)\n## 3\.", text, re.DOTALL)
    assert m, "section 2 not found"
    body = m.group(1)
    # count table rows starting with "| N |"
    rows = re.findall(r"^\| \d+ \|", body, re.MULTILINE)
    assert len(rows) == 20, f"expected 20 pilot blockers, found {len(rows)}"


def test_doc_paid_blocker_table_has_10_rows():
    text = DOC_PATH.read_text()
    m = re.search(r"## 3\. Top 10[^\n]*\n(.*?)\n## 4\.", text, re.DOTALL)
    assert m, "section 3 not found"
    body = m.group(1)
    rows = re.findall(r"^\| P\d+ \|", body, re.MULTILINE)
    assert len(rows) == 10, f"expected 10 paid blockers, found {len(rows)}"


def test_doc_enterprise_blocker_table_has_10_rows():
    text = DOC_PATH.read_text()
    m = re.search(r"## 4\. Top 10[^\n]*\n(.*?)\n## 5\.", text, re.DOTALL)
    assert m, "section 4 not found"
    body = m.group(1)
    rows = re.findall(r"^\| E\d+ \|", body, re.MULTILINE)
    assert len(rows) == 10, f"expected 10 enterprise blockers, found {len(rows)}"


def test_doc_classifies_blockers():
    text = DOC_PATH.read_text()
    # the doc must mention the classification taxonomy
    for kind in ["architecture", "parity", "UX", "governance", "testing", "commercial"]:
        assert kind.lower() in text.lower(), f"missing classification kind: {kind}"


def test_doc_has_no_go_list():
    text = DOC_PATH.read_text()
    assert "## 7. No-go list" in text
    nogo_section = text.split("## 7. No-go list", 1)[1].split("## 8.", 1)[0]
    # must list at least 5 no-go items
    items = re.findall(r"^- ", nogo_section, re.MULTILINE)
    assert len(items) >= 5, f"expected at least 5 no-go items, found {len(items)}"


# ---------------------------------------------------------------------------
# Report content shape
# ---------------------------------------------------------------------------

def test_report_is_valid_json():
    data = json.loads(REPORT_PATH.read_text())
    assert isinstance(data, dict)


def test_report_required_keys():
    data = json.loads(REPORT_PATH.read_text())
    required = [
        "phase",
        "date",
        "type",
        "base_sha",
        "status",
        "horizons",
        "pilot_blockers_count",
        "paid_blockers_count",
        "enterprise_blockers_count",
        "parity_baseline",
        "pilot_blockers",
        "paid_blockers",
        "enterprise_blockers",
        "recommended_next_sprint",
        "nogo_list",
        "hard_rules_respected",
        "no_production_code_change",
    ]
    for k in required:
        assert k in data, f"missing key: {k}"


def test_report_counts_consistent():
    data = json.loads(REPORT_PATH.read_text())
    assert data["pilot_blockers_count"] == 20
    assert data["paid_blockers_count"] == 10
    assert data["enterprise_blockers_count"] == 10
    assert len(data["pilot_blockers"]) == 20
    assert len(data["paid_blockers"]) == 10
    assert len(data["enterprise_blockers"]) == 10


def test_report_status_draft():
    data = json.loads(REPORT_PATH.read_text())
    assert data["status"] == "DRAFT"
    assert data["type"] == "report-only"
    assert data["hard_rules_respected"] is True
    assert data["no_production_code_change"] is True


def test_report_no_regressions_marker():
    data = json.loads(REPORT_PATH.read_text())
    assert data["parity_baseline"]["regressions_from_c_series"] == 0
