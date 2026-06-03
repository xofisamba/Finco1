"""Phase 54D — Shared LineItemGrid specification guardrails.

Verifies:
- doc and JSON exist
- Required columns defined (always + audit + compare)
- 6 cell states
- 8 variants
- Implementation plan
- Migration order
- Context key contract candidates
- Test strategy
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "phase54d_shared_line_item_grid_spec.md"
JSON_RPT = REPO_ROOT / "reports" / "phase54d_shared_line_item_grid_spec.json"


class TestDeliverablesExist:
    def test_doc_exists(self):
        assert DOC.exists()

    def test_json_report_exists(self):
        assert JSON_RPT.exists()

    def test_phase_field_is_54d(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["phase"] == "54D"

    def test_recommended_next_step_is_54e(self):
        data = json.loads(JSON_RPT.read_text())
        assert "54E" in data["recommended_next_step"]


class TestGridSpec:
    def test_orientation_documented(self):
        data = json.loads(JSON_RPT.read_text())
        assert "orientation" in data["line_item_grid_spec"]

    def test_frozen_left_documented(self):
        data = json.loads(JSON_RPT.read_text())
        assert "frozen_left" in data["line_item_grid_spec"]
        assert len(data["line_item_grid_spec"]["frozen_left"]) >= 2

    def test_modes_documented(self):
        data = json.loads(JSON_RPT.read_text())
        modes = data["line_item_grid_spec"]["modes"]
        for m in ["default", "audit", "compare", "compact"]:
            assert m in modes


class TestRequiredColumns:
    def test_always_columns(self):
        data = json.loads(JSON_RPT.read_text())
        always = data["required_columns"]["always"]
        names = [c["name"] for c in always]
        for col in ["code", "line_item", "runtime_impact", "total"]:
            assert col in names

    def test_audit_mode_columns(self):
        data = json.loads(JSON_RPT.read_text())
        audit = data["required_columns"]["audit_mode_only"]
        names = [c["name"] for c in audit]
        for col in ["source", "last_modified", "modified_by", "run_id"]:
            assert col in names

    def test_compare_mode_columns(self):
        data = json.loads(JSON_RPT.read_text())
        compare = data["required_columns"]["compare_mode_only"]
        names = [c["name"] for c in compare]
        for col in ["base_value", "delta", "delta_pct", "source_scenario"]:
            assert col in names


class TestCellStates:
    EXPECTED_STATES = ["input", "calculated", "display-only", "pending",
                       "needs-review", "validation-issue"]

    @pytest.mark.parametrize("state", EXPECTED_STATES)
    def test_state_documented(self, state):
        data = json.loads(JSON_RPT.read_text())
        states = [s["state"] for s in data["cell_state_spec"]]
        assert state in states

    def test_6_cell_states(self):
        data = json.loads(JSON_RPT.read_text())
        n = len(data["cell_state_spec"])
        assert n == 6


class TestVariants:
    EXPECTED_VARIANTS = ["CAPEX", "OPEX", "Revenue", "Debt/DSCR",
                         "SHL/Distribution", "CFADS/Cash Flow",
                         "Scenario Compare", "Audit/Reconciliation"]

    @pytest.mark.parametrize("variant", EXPECTED_VARIANTS)
    def test_variant_documented(self, variant):
        data = json.loads(JSON_RPT.read_text())
        variants = [v["variant"] for v in data["variant_spec"]]
        assert variant in variants

    def test_8_variants(self):
        data = json.loads(JSON_RPT.read_text())
        n = len(data["variant_spec"])
        assert n == 8


class TestImplementationPlan:
    def test_stack_decision_present(self):
        data = json.loads(JSON_RPT.read_text())
        assert "stack_decision" in data["implementation_plan"]

    def test_no_client_side_calculations(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["implementation_plan"]["client_side_calculations"] is False

    def test_htmx_for_mode_swaps(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["implementation_plan"]["htmx_for_mode_swaps"] is True


class TestMigrationOrder:
    def test_migration_order_has_steps(self):
        data = json.loads(JSON_RPT.read_text())
        order = data["migration_order"]
        assert len(order) >= 8

    def test_macro_first_step(self):
        data = json.loads(JSON_RPT.read_text())
        order = data["migration_order"]
        assert "macro" in order[0].lower() or "Create macro" in order[0]


class TestContextKeyContract:
    def test_candidate_1_present(self):
        data = json.loads(JSON_RPT.read_text())
        assert "candidate_1_list_of_dicts" in data["context_key_contract_candidates"]

    def test_candidate_2_present(self):
        data = json.loads(JSON_RPT.read_text())
        assert "candidate_2_structured_response" in data["context_key_contract_candidates"]


class TestTestStrategy:
    def test_strategy_has_unit_tests(self):
        data = json.loads(JSON_RPT.read_text())
        assert "ui3_unit_tests" in data["test_strategy"]

    def test_strategy_has_accessibility(self):
        data = json.loads(JSON_RPT.read_text())
        assert "ui3_accessibility" in data["test_strategy"]

    def test_strategy_has_data_contract(self):
        data = json.loads(JSON_RPT.read_text())
        assert "ui3_data_contract" in data["test_strategy"]
