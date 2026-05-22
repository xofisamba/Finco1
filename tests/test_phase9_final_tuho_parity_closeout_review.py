import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "phase9_final_tuho_parity_closeout_review.md"
STATUS = ROOT / "reports" / "phase9_final_tuho_parity_closeout_status.csv"
CONVENTIONS = ROOT / "reports" / "phase9_final_tuho_accepted_conventions.csv"
G20 = ROOT / "reports" / "phase9_final_tuho_g20_gate_checklist.csv"
DECISIONS = ROOT / "reports" / "phase9_final_tuho_stakeholder_decisions.csv"


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_docs_and_reports_exist():
    for path in [DOC, STATUS, CONVENTIONS, G20, DECISIONS]:
        assert path.exists(), path


def test_report_columns_are_present():
    expected = {
        STATUS: {
            "category",
            "metric",
            "status",
            "excel_value",
            "model_value",
            "delta",
            "classification",
            "accepted",
            "required_decision",
            "notes",
        },
        CONVENTIONS: {
            "convention_id",
            "convention",
            "description",
            "affected_metrics",
            "runtime_impact",
            "reporting_impact",
            "bankability_impact",
            "accepted_for_closeout",
            "stakeholder_decision_required",
            "notes",
        },
        G20: {
            "gate_id",
            "gate_name",
            "status",
            "evidence_artifact",
            "blocker_type",
            "stakeholder_decision_required",
            "required_next_action",
            "notes",
        },
        DECISIONS: {
            "decision_id",
            "decision",
            "options",
            "recommended_option",
            "consequence_if_accepted",
            "consequence_if_rejected",
            "required_before_g20",
            "notes",
        },
    }
    for path, columns in expected.items():
        rows = _rows(path)
        assert rows
        assert columns.issubset(rows[0].keys())


def test_closeout_status_includes_required_categories():
    rows = _rows(STATUS)
    pairs = {(row["category"], row["metric"]) for row in rows}
    required = {
        ("Operations", "Production"),
        ("Revenue", "Revenue"),
        ("Costs", "OPEX"),
        ("Costs", "EBITDA"),
        ("Senior Debt", "Senior Debt"),
        ("SHL", "SHL Opening"),
        ("SHL", "SHL Interest / PIK"),
        ("SHL", "SHL Principal"),
        ("Tax", "Taxable Income / R35"),
        ("Tax", "CIT / R67"),
        ("Cash Flow", "CFADS / R69"),
        ("Distributions", "Distributions"),
        ("Returns", "Project IRR"),
        ("Returns", "Equity IRR"),
        ("Returns", "Reconciliation IRR"),
        ("Governance", "G20"),
        ("Governance", "R99/R102"),
    }
    assert required.issubset(pairs)


def test_accepted_conventions_include_required_items():
    conventions = {row["convention"] for row in _rows(CONVENTIONS)}
    assert "XIRR construction-date convention" in conventions
    assert "SHL IDC investment-base treatment" in conventions


def test_g20_checklist_and_stakeholder_decisions_include_required_items():
    gates = {row["gate_id"]: row for row in _rows(G20)}
    assert "G20-09" in gates
    assert gates["G20-09"]["gate_name"] == "Reconciliation IRR decision"

    decisions = {row["decision_id"]: row for row in _rows(DECISIONS)}
    assert "DEC-01" in decisions
    assert "equity IRR residual" in decisions["DEC-01"]["decision"]


def test_docs_state_governance_status_and_no_runtime_changes():
    text = DOC.read_text(encoding="utf-8")
    assert "No runtime changes were made in this branch." in text
    assert "G20 remains `BLOCKED` pending stakeholder acceptance / gate sign-off." in text
    assert "R99/R102 runtime promotion remains `NOT APPROVED`." in text
