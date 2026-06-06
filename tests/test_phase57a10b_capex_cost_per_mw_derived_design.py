from __future__ import annotations

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "docs" / "phase57a10b_capex_cost_per_mw_derived_design.md"
REPORT_PATH = REPO_ROOT / "reports" / "phase57a10b_capex_cost_per_mw_derived_design.json"


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


class TestPreferredArchitecture:
    def test_preferred_option_is_a(self, report):
        assert report["preferred_option"] == "A"

    def test_amount_is_authoritative_and_cost_per_mw_is_derived(self, report):
        arch = report["preferred_architecture"]
        assert arch["authoritative_field"] == "amount_keur"
        assert arch["derived_field"] == "cost_per_mw"
        assert arch["persist_cost_per_mw"] is False

    def test_rejected_options_documented(self, report, doc_text):
        assert set(report["rejected_options"]) == {"B", "C"}
        lowered = doc_text.lower()
        assert "option b rejected" in lowered
        assert "option c rejected" in lowered


class TestScenarioSemantics:
    def test_scenario_semantics_documented(self, report, doc_text):
        semantics = report["scenario_semantics"]
        assert semantics["amount_override_rule"] == "replace_not_delta"
        assert semantics["cost_per_mw_behavior"] == "auto_updates_from_effective_amount"
        assert semantics["cost_per_mw_override_key"] == "not_allowed"
        assert "auto-update" in doc_text.lower()


class TestCapacitySource:
    def test_capacity_source_is_explicit(self, report, doc_text):
        dep = report["capacity_dependency"]
        assert dep["selected_source"] == "capacity_mw"
        assert dep["blank_when_missing_or_non_positive"] is True
        assert "project technical field" in doc_text.lower()
        assert "capacity_mw" in doc_text


class TestExportStrategy:
    def test_export_strategy_documented(self, report, doc_text):
        strategy = report["export_strategy"]
        assert "CapEx" in strategy
        assert "CapEx_Items" in strategy
        assert "CapEx_SubLines_Audit" in strategy
        assert "reconciliation_sheets" in strategy
        lowered = doc_text.lower()
        assert "capex_sublines_audit" in lowered or "capex_sublines_audit".replace("_", " ") in lowered


class TestGenericCompatibility:
    def test_generic_solar_wind_compatibility_documented(self, report, doc_text):
        compat = report["generic_compatibility"]
        assert compat["supported_paths"] == ["TUHO", "Oborovo", "Generic Solar", "Generic Wind"]
        assert compat["no_template_specific_assumptions"] is True
        lowered = doc_text.lower()
        assert "generic solar" in lowered
        assert "generic wind" in lowered
        assert "exploratory" in lowered
        assert "unvalidated" in lowered


class TestFutureInteractions:
    def test_future_advanced_column_interactions_documented(self, report, doc_text):
        interactions = report["future_interactions"]
        assert set(interactions.keys()) == {
            "contingency",
            "vat_wht",
            "depreciation",
            "payment_schedule",
            "utilisation",
        }
        lowered = doc_text.lower()
        assert "contingency" in lowered
        assert "vat / wht" in lowered
        assert "depreciation" in lowered
        assert "payment schedule" in lowered
        assert "utilisation" in lowered


class TestImplementationPlan:
    def test_future_sequence_documented(self, report, doc_text):
        sequence = report["estimated_future_implementation_sequence"]
        assert len(sequence) >= 3
        lowered = doc_text.lower()
        assert "estimated future implementation sequence" in lowered

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
