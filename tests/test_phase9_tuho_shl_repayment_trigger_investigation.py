"""Phase 9 TUHO SHL repayment trigger investigation artifact tests.

These tests intentionally validate docs/reports only. They must not depend on
or modify runtime waterfall behavior.
"""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "phase9_tuho_shl_repayment_trigger_investigation.md"
TRACE_PATH = ROOT / "reports" / "phase9_tuho_shl_repayment_trigger_trace.csv"
EXCEL_COMPARE_PATH = ROOT / "reports" / "phase9_tuho_shl_repayment_vs_excel.csv"
ROOT_CAUSE_PATH = ROOT / "reports" / "phase9_tuho_shl_repayment_root_cause_matrix.csv"


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_investigation_artifacts_exist() -> None:
    assert DOC_PATH.exists()
    assert TRACE_PATH.exists()
    assert EXCEL_COMPARE_PATH.exists()
    assert ROOT_CAUSE_PATH.exists()


def test_trigger_trace_has_required_columns_and_first_repayment() -> None:
    rows = _rows(TRACE_PATH)
    required = {
        "period",
        "date",
        "opening_shl_balance_keur",
        "available_cash_pre_shl_keur",
        "senior_debt_service_keur",
        "dscr",
        "lockup_active",
        "shl_interest_keur",
        "shl_principal_keur",
        "repayment_allowed",
        "repayment_trigger_reason",
        "repayment_blocker",
        "distribution_keur",
        "notes",
    }
    assert required.issubset(rows[0])
    assert len(rows) == 60

    first = next(row for row in rows if float(row["shl_principal_keur"]) > 0.0)
    assert first["period"] == "29"
    assert first["date"] == "2044-06-30"
    assert "sweep phase" in first["repayment_trigger_reason"]
    assert first["repayment_blocker"] == "none in current runtime"


def test_excel_comparison_identifies_repayment_timing_mismatch() -> None:
    rows = _rows(EXCEL_COMPARE_PATH)
    required = {
        "period",
        "excel_shl_principal_keur",
        "model_shl_principal_keur",
        "delta_keur",
        "excel_repayment_active",
        "model_repayment_active",
        "classification",
        "notes",
    }
    assert required.issubset(rows[0])
    assert len(rows) == 60

    excel_first = next(row for row in rows if row["excel_repayment_active"] == "True")
    model_first = next(row for row in rows if row["model_repayment_active"] == "True")
    assert excel_first["period"] == "25"
    assert model_first["period"] == "29"
    assert any(row["classification"] == "Excel active / model blocked" for row in rows)
    assert any(row["classification"] == "Both active" for row in rows)


def test_root_cause_matrix_contains_required_hypotheses() -> None:
    rows = _rows(ROOT_CAUSE_PATH)
    hypotheses = {row["hypothesis"] for row in rows}
    required = {
        "repayment starts due to waterfall ordering",
        "repayment starts due to missing grace period",
        "repayment starts due to missing covenant lock",
        "repayment starts due to DSCR availability",
        "repayment starts due to Excel-specific convention",
        "repayment starts due to reporting mismatch",
        "repayment timing economically valid but Excel-different",
    }
    assert required.issubset(hypotheses)
    assert all(row["recommended_action"] for row in rows)


def test_docs_state_runtime_fix_recommendation_g20_status_and_scope() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    assert "Runtime fix recommendation: yes" in doc
    assert "G20 remains BLOCKED" in doc
    assert "R99/R102 runtime promotion remains NOT approved" in doc
    assert "No runtime files were changed" in doc
    assert "not reproducible on the current main" in doc

    forbidden_runtime_paths = [
        "domain/waterfall/waterfall_engine.py",
        "app/waterfall_core.py",
        "app/project_factories.py",
        "domain/shl/",
    ]
    intended_section = doc.split("## Changed Files Intended By This Branch", 1)[1]
    assert not any(path in intended_section for path in forbidden_runtime_paths)
