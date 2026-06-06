from __future__ import annotations

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "docs" / "phase57a10c_capex_contingency_design.md"
REPORT_PATH = REPO_ROOT / "reports" / "phase57a10c_capex_contingency_design.json"


@pytest.fixture(scope="module")
def doc_text() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def report() -> dict:
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


class TestFilesExist:
    def test_design_doc_exists(self):
        assert DOC_PATH.is_file()

    def test_report_exists(self):
        assert REPORT_PATH.is_file()


class TestOwnershipModel:
    def test_preferred_ownership_option_is_line_item(self, report, doc_text):
        assert report["preferred_ownership_option"] == "B"
        assert "line-item-level" in doc_text.lower()

    def test_rejected_ownership_models_documented(self, doc_text):
        lowered = doc_text.lower()
        assert "option a rejected" in lowered
        assert "option c rejected" in lowered


class TestSourceOfTruth:
    def test_base_amount_remains_authoritative(self, report, doc_text):
        source = report["source_of_truth"]
        assert source["authoritative_field"] == "base_amount_keur"
        assert source["derived_contingency_cost"] is True
        assert source["derived_effective_total"] is True
        lowered = doc_text.lower()
        assert "base amount remains authoritative" in lowered


class TestScenarioSemantics:
    def test_scenario_replace_semantics_documented(self, report, doc_text):
        semantics = report["scenario_semantics"]
        assert semantics["base_amount_override_rule"] == "replace_not_delta"
        assert semantics["contingency_pct_override_rule"] == "replace_not_delta"
        assert semantics["derived_contingency_cost_behavior"] == "recompute_from_effective_values"
        assert semantics["effective_total_behavior"] == "recompute_from_base_plus_contingency"
        assert semantics["direct_contingency_cost_override"] == "not_allowed_by_default"
        assert "replace baseline values" in doc_text.lower()


class TestUserAddedLines:
    def test_user_added_line_behavior_documented(self, report, doc_text):
        rows = report["user_added_sub_lines"]
        assert rows["supported"] is True
        assert "C.02.U001" in doc_text
        assert "C.08.U001" in doc_text
        for column in [
            "base_amount_keur",
            "contingency_pct",
            "derived_contingency_cost_keur",
            "effective_total_keur",
        ]:
            assert column in rows["display"]


class TestFundingBoundary:
    def test_funding_and_idc_boundary_documented(self, report, doc_text):
        boundary = report["funding_idc_boundary"]
        assert boundary["sources_and_uses"] == "future_phase_only"
        assert boundary["construction_funding"] == "future_phase_only"
        assert boundary["idc"] == "future_phase_only"
        assert boundary["debt_sizing"] == "future_phase_only"
        assert boundary["no_implicit_funding_assumption"] is True
        lowered = doc_text.lower()
        assert "sources & uses" in lowered
        assert "idc" in lowered
        assert "debt sizing" in lowered


class TestExportStrategy:
    def test_export_strategy_documented(self, report, doc_text):
        strategy = report["export_strategy"]
        assert "CapEx" in strategy
        assert "CapEx_Items" in strategy
        assert "CapEx_SubLines_Audit" in strategy
        assert "reconciliation_sheets" in strategy
        lowered = doc_text.lower()
        assert "capex_sublines_audit" in lowered or "capex sublines audit" in lowered


class TestGenericCompatibility:
    def test_generic_compatibility_documented(self, report, doc_text):
        compat = report["generic_compatibility"]
        assert compat["supported_paths"] == ["TUHO", "Oborovo", "Generic Solar", "Generic Wind"]
        assert compat["no_template_specific_assumptions"] is True
        lowered = doc_text.lower()
        assert "generic solar" in lowered
        assert "generic wind" in lowered
        assert "exploratory" in lowered
        assert "unvalidated" in lowered


class TestRecommendationSection:
    def test_recommendation_and_future_sequence_documented(self, report, doc_text):
        rec = report["recommendation_section"]
        assert rec["preferred_option"] == "B"
        assert len(report["estimated_future_implementation_sequence"]) >= 3
        lowered = doc_text.lower()
        assert "implementation complexity" in lowered
        assert "migration impact" in lowered
        assert "rollback strategy" in lowered

    def test_design_only_boundaries_preserved(self, report):
        boundaries = set(report["design_only_boundaries"])
        assert boundaries == {
            "no_runtime_implementation",
            "no_schema_changes",
            "no_export_changes",
            "no_run_changes",
            "no_financial_formula_changes",
        }

    def test_rc1_pinned(self, report):
        assert report["rc1_frozen_sha"] == "b425a0708719eaa5e1d922b1008e5609758e0ad4"
