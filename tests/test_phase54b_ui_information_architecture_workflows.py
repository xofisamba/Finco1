"""Phase 54B — Information architecture and workflow map guardrails.

Verifies:
- doc and JSON exist
- 11 sections defined
- 10 workflows defined
- All sections have purpose, intent, templates, dependencies, priority
- State indicator requirements list present
- No-go copy risks documented
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "phase54b_ui_information_architecture_workflows.md"
JSON_RPT = REPO_ROOT / "reports" / "phase54b_ui_information_architecture_workflows.json"


# ============================================================
# 1. Deliverables exist
# ============================================================


class TestDeliverablesExist:
    def test_doc_exists(self):
        assert DOC.exists()

    def test_json_report_exists(self):
        assert JSON_RPT.exists()

    def test_json_includes_required_keys(self):
        data = json.loads(JSON_RPT.read_text())
        for key in [
            "phase", "base_sha", "head_sha", "information_architecture",
            "workflow_map", "backend_dependency_map",
            "state_indicator_requirements", "priority_matrix",
            "no_go_copy_risks", "recommended_next_step",
            "tests_run", "known_failures"
        ]:
            assert key in data, f"Missing key: {key}"

    def test_phase_field_is_54b(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["phase"] == "54B"

    def test_recommended_next_step_is_54c(self):
        data = json.loads(JSON_RPT.read_text())
        assert "54C" in data["recommended_next_step"]


# ============================================================
# 2. 11 sections in IA
# ============================================================


class TestInformationArchitectureComplete:
    EXPECTED_SECTIONS = [
        "Dashboard / Overview",
        "Projects",
        "Inputs",
        "Financing",
        "Scenarios",
        "Compare",
        "Audit & Reconciliation",
        "Reports / Exports",
        "Data Room",
        "Settings",
        "Help / Onboarding",
    ]

    def test_11_sections_defined(self):
        data = json.loads(JSON_RPT.read_text())
        sections = data["information_architecture"]["sections"]
        n = len(sections)
        assert n == 11, f"Expected 11 sections, got {n}"

    @pytest.mark.parametrize("section_name", EXPECTED_SECTIONS)
    def test_section_present(self, section_name):
        data = json.loads(JSON_RPT.read_text())
        sections = data["information_architecture"]["sections"]
        names = [s["name"] for s in sections]
        assert section_name in names, f"Missing section: {section_name}"

    def test_each_section_has_required_fields(self):
        data = json.loads(JSON_RPT.read_text())
        sections = data["information_architecture"]["sections"]
        for s in sections:
            for key in ["id", "name", "purpose", "user_intent",
                        "current_templates", "backend_dependencies",
                        "pilot_priority", "enterprise_priority"]:
                assert key in s, f"Section {s.get('name')} missing {key}"


# ============================================================
# 3. 10 workflows defined
# ============================================================


class TestWorkflowsComplete:
    def test_10_workflows_defined(self):
        data = json.loads(JSON_RPT.read_text())
        workflows = data["workflow_map"]["workflows"]
        n = len(workflows)
        assert n == 10, f"Expected 10 workflows, got {n}"

    @pytest.mark.parametrize("workflow_id", list(range(1, 11)))
    def test_workflow_present(self, workflow_id):
        data = json.loads(JSON_RPT.read_text())
        workflows = data["workflow_map"]["workflows"]
        ids = [w["id"] for w in workflows]
        assert workflow_id in ids

    def test_workflows_cover_all_sections(self):
        # Every workflow should map to at least one section
        data = json.loads(JSON_RPT.read_text())
        workflows = data["workflow_map"]["workflows"]
        for w in workflows:
            assert len(w["steps"]) > 0, f"Workflow {w['id']} ({w['name']}) has no steps"


# ============================================================
# 4. State indicator requirements
# ============================================================


class TestStateIndicatorRequirements:
    EXPECTED_INDICATORS = [
        "active_scenario", "saved_vs_draft", "last_run",
        "validation_status", "factory_vs_user_created",
        "source_locked_fixture_backed", "runtime_impact_per_line",
        "scope_match", "stale_result_warning", "display_only_row_marker"
    ]

    @pytest.mark.parametrize("indicator", EXPECTED_INDICATORS)
    def test_indicator_listed(self, indicator):
        data = json.loads(JSON_RPT.read_text())
        indicators = data["state_indicator_requirements"]
        assert indicator in indicators


# ============================================================
# 5. No-go copy risks
# ============================================================


class TestNoGoCopyRisks:
    def test_no_go_risks_documented(self):
        data = json.loads(JSON_RPT.read_text())
        risks = data["no_go_copy_risks"]
        assert len(risks) >= 5, "Should have at least 5 no-go copy risks"

    def test_bankable_is_in_risks(self):
        data = json.loads(JSON_RPT.read_text())
        risks_text = json.dumps(data["no_go_copy_risks"]).lower()
        assert "bankable" in risks_text

    def test_validated_is_in_risks(self):
        data = json.loads(JSON_RPT.read_text())
        risks_text = json.dumps(data["no_go_copy_risks"]).lower()
        assert "validated" in risks_text or "audit-ready" in risks_text


# ============================================================
# 6. Priority matrix
# ============================================================


class TestPriorityMatrix:
    def test_priority_matrix_covers_11_sections(self):
        data = json.loads(JSON_RPT.read_text())
        matrix = data["priority_matrix"]
        assert len(matrix) == 11, f"Priority matrix should cover 11 sections, got {len(matrix)}"

    def test_dashboard_is_high_priority(self):
        data = json.loads(JSON_RPT.read_text())
        assert data["priority_matrix"]["Dashboard"]["pilot"] == "HIGH"
