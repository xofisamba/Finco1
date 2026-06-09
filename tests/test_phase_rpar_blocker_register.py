"""Shape-only characterization tests for the R-PAR blocker register.

Asserts existence and shape of the register (count, status
distribution, severity distribution, required IDs).
"""

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "docs" / "phase_rpar_blocker_register.md"
REPORT_PATH = REPO_ROOT / "reports" / "phase_rpar_blocker_register.json"


# --- Existence ------------------------------------------------------------

def test_doc_exists():
    assert DOC_PATH.exists()


def test_report_exists():
    assert REPORT_PATH.exists()


# --- Document shape -------------------------------------------------------

def test_doc_has_required_sections():
    text = DOC_PATH.read_text()
    required = [
        "# R-PAR / R-Series Blocker Register",
        "## 1. Sources",
        "## 2. Status legend",
        "## 3. Severity legend",
        "## 4. The register",
        "## 5. Counts by status",
        "## 6. Counts by severity",
        "## 7. What this document does NOT do",
        "## 8. Test footprint",
    ]
    for s in required:
        assert s in text, f"missing section: {s}"


def test_doc_lists_all_rpar_ids():
    """All R-PAR-1..5 must be present in the doc."""
    text = DOC_PATH.read_text()
    for n in range(1, 6):
        assert f"R-PAR-{n}" in text, f"missing R-PAR-{n}"


def test_doc_lists_other_blocker_ids():
    text = DOC_PATH.read_text()
    required = [
        "R67",
        "R84",
        "R98",
        "R99",
        "R102",
        "DEBT-SCULPT",
        "DEP-SHADOW",
        "OB-SHL-OB",
        "OB-DIST-LOCKUP",
        "OB-SNAP",
        "OPEX-VIS",
        "CAPEX-2.0",
        "CONST-IDC",
        "REPLAY",
        "MULTI-USER",
        "SIGNOFF",
        "CERT",
        "COMMERCIAL",
        "F3",
    ]
    for rid in required:
        assert rid in text, f"missing blocker ID: {rid}"


# --- Report shape ---------------------------------------------------------

def test_report_is_valid_json():
    data = json.loads(REPORT_PATH.read_text())
    assert isinstance(data, dict)


def test_report_required_keys():
    data = json.loads(REPORT_PATH.read_text())
    for k in [
        "phase", "date", "type", "base_sha", "status",
        "register", "counts_by_status", "counts_by_severity",
        "total_blockers", "hard_rules_respected",
        "no_production_code_change", "no_promotion",
        "no_runtime_change", "rc1_untouched",
    ]:
        assert k in data, f"missing key: {k}"


def test_report_status_draft():
    data = json.loads(REPORT_PATH.read_text())
    assert data["status"] == "DRAFT"
    assert data["type"] == "report-only"


def test_report_register_size():
    data = json.loads(REPORT_PATH.read_text())
    # the register must have at least 20 entries
    assert data["total_blockers"] >= 20, f"expected >=20 blockers, got {data['total_blockers']}"


def test_report_register_ids_unique():
    data = json.loads(REPORT_PATH.read_text())
    ids = [e["id"] for e in data["register"]]
    assert len(ids) == len(set(ids)), "duplicate IDs in register"


def test_report_register_each_has_required_fields():
    data = json.loads(REPORT_PATH.read_text())
    for entry in data["register"]:
        for k in ["id", "status", "severity", "owner", "blocks", "allowed", "forbidden", "resolution"]:
            assert k in entry, f"entry {entry.get('id')} missing field: {k}"


def test_report_hard_rules():
    data = json.loads(REPORT_PATH.read_text())
    assert data["hard_rules_respected"] is True
    assert data["no_production_code_change"] is True
    assert data["no_promotion"] is True
    assert data["no_runtime_change"] is True
    assert data["rc1_untouched"] is True


def test_report_counts_match_register():
    data = json.loads(REPORT_PATH.read_text())
    actual = {}
    for e in data["register"]:
        actual[e["status"]] = actual.get(e["status"], 0) + 1
    for status, count in data["counts_by_status"].items():
        assert actual.get(status, 0) == count, f"{status} count mismatch: {actual.get(status,0)} vs {count}"
