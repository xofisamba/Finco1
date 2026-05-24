"""Phase 14C pilot-readiness snapshot closeout tests."""

from __future__ import annotations

import csv
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "phase14c_pilot_readiness_snapshot.md"
SCORECARD = ROOT / "reports" / "phase14c_product_maturity_scorecard.csv"
WORKFLOWS = ROOT / "reports" / "phase14c_pilot_safe_workflow_inventory.csv"
LIMITATIONS = ROOT / "reports" / "phase14c_known_limitations_and_no_claims.csv"
ROADMAP = ROOT / "reports" / "phase14c_next_roadmap_options.csv"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_closeout_artifacts_exist():
    for path in (DOC_PATH, SCORECARD, WORKFLOWS, LIMITATIONS, ROADMAP):
        assert path.exists(), f"Missing closeout artifact: {path}"


def test_doc_contains_guardrail_statements():
    content = _read(DOC_PATH)
    assert "`G20` remains `BLOCKED`" in content
    assert "`R99/R102` remain `NOT APPROVED`" in content
    assert "`audit_economic_mode` remains audit/reconciliation-only." in content
    assert "`runtime_economic_mode` remains the only explicit runtime staging path." in content
    assert "No runtime/model formulas changed." in content
    assert "No workbook calculations changed." in content
    assert "No new editable surfaces were added." in content
    assert "No production behavior changes are introduced by this closeout branch." in content


def test_scorecard_has_expected_dimensions_and_scores():
    rows = {row["dimension"]: row for row in _csv_rows(SCORECARD)}
    assert rows["runtime_authority"]["score_1_to_10"] == "9"
    assert rows["persistence_authority"]["score_1_to_10"] == "8"
    assert rows["pilot_readiness"]["current_posture"] == "Guided pilot-safe"
    assert rows["r99_r102_readiness"]["current_posture"] == "Low"


def test_workflow_inventory_distinguishes_supported_and_excluded_flows():
    rows = {row["workflow"]: row for row in _csv_rows(WORKFLOWS)}
    assert rows["Select project template"]["status"] == "SUPPORTED"
    assert rows["Run model"]["guardrail"] == "Clean saved boundary required"
    assert rows["ZIP publish fallback"]["status"] == "SUPPORTED"
    assert rows["R99/R102 runtime promotion"]["status"] == "NOT_SUPPORTED"
    assert rows["G20 approval workflow"]["status"] == "NOT_SUPPORTED"


def test_limitations_and_roadmap_preserve_current_no_claims():
    limitation_rows = {row["area"]: row for row in _csv_rows(LIMITATIONS)}
    roadmap_rows = {row["option"]: row for row in _csv_rows(ROADMAP)}

    assert limitation_rows["Promotion posture"]["no_claim_or_limitation"] == "R99/R102 are NOT APPROVED"
    assert limitation_rows["Gate posture"]["no_claim_or_limitation"] == "G20 remains BLOCKED"
    assert limitation_rows["Replay capabilities"]["no_claim_or_limitation"] == "No full replay engine"

    assert "RECOMMENDED" == roadmap_rows["Phase 15 pilot operations and reviewer handoff"]["priority"]
    assert "No promotion no gate change" in roadmap_rows["R99/R102 promotion preparation"]["explicitly_not_included"]


def test_no_production_code_change_claim_is_docs_reports_only():
    expected_files = {
        "docs/phase14c_pilot_readiness_snapshot.md",
        "reports/phase14c_product_maturity_scorecard.csv",
        "reports/phase14c_pilot_safe_workflow_inventory.csv",
        "reports/phase14c_known_limitations_and_no_claims.csv",
        "reports/phase14c_next_roadmap_options.csv",
        "tests/test_phase14c_pilot_readiness_snapshot.py",
    }
    present = {str(path.relative_to(ROOT)).replace("\\", "/") for path in (
        DOC_PATH, SCORECARD, WORKFLOWS, LIMITATIONS, ROADMAP, Path(__file__)
    )}
    assert present == expected_files
