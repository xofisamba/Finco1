"""Phase 9 TUHO SHL repayment trigger alignment design artifact tests."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "phase9_tuho_shl_repayment_trigger_alignment_design.md"
OPTIONS = ROOT / "reports" / "phase9_tuho_shl_repayment_alignment_options.csv"
IMPACT = ROOT / "reports" / "phase9_tuho_shl_repayment_alignment_impact.csv"
GATES = ROOT / "reports" / "phase9_tuho_shl_repayment_alignment_gate_matrix.csv"


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_design_artifacts_exist() -> None:
    assert DOC.exists()
    assert OPTIONS.exists()
    assert IMPACT.exists()
    assert GATES.exists()


def test_alignment_options_report_has_required_columns_and_options() -> None:
    rows = _rows(OPTIONS)
    required_columns = {
        "option_id",
        "option_name",
        "description",
        "implementation_area",
        "default_behavior_change",
        "tuho_only",
        "flag_required",
        "pros",
        "cons",
        "risk",
        "recommendation",
    }
    assert required_columns.issubset(rows[0])
    option_ids = {row["option_id"] for row in rows}
    assert {
        "no_change_document_excel_convention",
        "tuho_only_repayment_start_period_override",
        "config_driven_shl_principal_eligibility_date",
        "r99_r102_distribution_account_source",
        "senior_debt_zero_only_current_behavior",
    }.issubset(option_ids)
    recommended = next(
        row for row in rows if row["option_id"] == "config_driven_shl_principal_eligibility_date"
    )
    assert "Recommended" in recommended["recommendation"]


def test_alignment_impact_report_marks_unimplemented_irr_as_estimate_required() -> None:
    rows = _rows(IMPACT)
    required_columns = {
        "scenario",
        "first_principal_period",
        "first_principal_date",
        "total_principal_repaid_keur",
        "expected_equity_irr",
        "delta_vs_current_pp",
        "delta_vs_excel_pp",
        "runtime_change_required",
        "notes",
    }
    assert required_columns.issubset(rows[0])
    scenarios = {row["scenario"]: row for row in rows}
    assert scenarios["current_model"]["first_principal_period"] == "29"
    assert scenarios["excel_fixture"]["first_principal_period"] == "25"
    target = scenarios["alignment_target_config_driven"]
    assert target["expected_equity_irr"] == "ESTIMATE_REQUIRED"
    assert target["runtime_change_required"] == "true"


def test_gate_matrix_contains_required_governance_gates() -> None:
    rows = _rows(GATES)
    required_columns = {
        "gate_id",
        "gate_name",
        "current_status",
        "required_before_implementation",
        "evidence_available",
        "missing_evidence",
        "owner_module",
        "notes",
    }
    assert required_columns.issubset(rows[0])
    gate_ids = {row["gate_id"] for row in rows}
    assert {
        "GATE_EXCEL_TIMING",
        "GATE_MODEL_P29",
        "GATE_ZERO_DRIFT",
        "GATE_OBOROVO",
        "GATE_R99_NOT_APPROVED",
        "GATE_G20_BLOCKED",
        "GATE_SPONSOR_IRR",
        "GATE_SHL_SCHEDULE",
    }.issubset(gate_ids)


def test_design_doc_states_recommendation_scope_and_blockers() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "phase9-tuho-shl-repayment-trigger-alignment-implementation" in text
    assert "Config-driven SHL principal eligibility date" in text
    assert "G20 remains BLOCKED" in text
    assert "R99/R102 runtime promotion remains NOT approved" in text
    assert "does not change runtime behavior" in text
    assert "No `domain/waterfall/waterfall_engine.py` change" in text

