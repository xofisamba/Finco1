"""Phase 57A-10E tax metadata persistence design contract tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = (
    REPO_ROOT / "docs" / "phase57a10e_capex_tax_metadata_persistence_design.md"
)
REPORT_PATH = (
    REPO_ROOT
    / "reports"
    / "phase57a10e_capex_tax_metadata_persistence_design.json"
)


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


class TestArchitectureDocumented:
    def test_preferred_architecture_is_hybrid(self, report, doc_text):
        architecture = report["preferred_persistence_architecture"]
        assert architecture["option"] == "C"
        assert architecture["name"] == "hybrid"
        assert "hybrid ownership" in doc_text.lower()

    @pytest.mark.parametrize(
        "phrase",
        [
            "persistence ownership recommendation",
            "future field shortlist",
            "scenario semantics",
            "uuid ownership and binding",
            "validation rules",
            "export authority",
            "generic solar / wind compatibility",
            "migration plan",
        ],
    )
    def test_required_topics_exist_in_doc(self, doc_text, phrase):
        assert phrase in doc_text.lower()


class TestFieldShortlist:
    def test_vat_fields_documented(self, report):
        vat = report["field_shortlist"]["vat"]
        assert "vat_recoverable_flag" in vat["required"]
        assert "vat_rate_pct" in vat["required"]
        assert "vat_basis_mode" in vat["required"]

    def test_wht_fields_documented(self, report):
        wht = report["field_shortlist"]["wht"]
        assert "wht_rate_pct" in wht["required"]
        assert "wht_treatment_mode" in wht["required"]
        assert "wht_gross_up_flag" in wht["required"]

    def test_depreciation_fields_documented(self, report):
        depreciation = report["field_shortlist"]["depreciation"]
        assert "depreciation_asset_class" in depreciation["required"]
        assert "depreciation_useful_life_years" in depreciation["required"]
        assert "depreciable_flag" in depreciation["required"]
        assert "depreciation_basis_mode" in depreciation["required"]


class TestScenarioSemantics:
    def test_override_rule_is_replace_not_delta(self, report, doc_text):
        semantics = report["scenario_semantics"]
        assert semantics["binding_key"] == "sub_line_id"
        assert semantics["override_rule"] == "replace_not_delta"
        assert "replace-not-delta" in doc_text.lower()

    def test_duplicate_and_readd_behavior_documented(self, report):
        semantics = report["scenario_semantics"]
        assert "preserve_same_project_level_sub_line_id_references" in (
            semantics["duplicate_scenario_behavior"]
        )
        assert "new_line_gets_new_sub_line_id" in (
            semantics["deleted_readded_behavior"]
        )


class TestValidationAndExportAuthority:
    def test_validation_ranges_and_combinations_documented(self, report):
        rules = report["validation_rules"]
        assert rules["allowed_ranges"]["vat_rate_pct"] == "0_to_100"
        assert rules["allowed_ranges"]["wht_rate_pct"] == "0_to_100"
        assert (
            "vat_recoverable_flag_requires_vat_rate_pct_and_vat_basis_mode"
            in rules["required_combinations"]
        )

    def test_export_authority_documented(self, report):
        authority = report["export_authority"]
        assert authority["CapEx_SubLines_Audit"] == "canonical_per_line_evidence_surface"
        assert authority["Tax_Audit_Sheets"] == "future_vat_wht_deep_audit_surface"
        assert (
            authority["Depreciation_Audit_Sheets"]
            == "future_depreciation_deep_audit_surface"
        )


class TestGenericCompatibilityAndMigration:
    def test_generic_compatibility_documented(self, report, doc_text):
        supported = report["generic_compatibility"]["supported_project_families"]
        assert "Generic Solar" in supported
        assert "Generic Wind" in supported
        assert "exploratory/unvalidated" in doc_text.lower()

    def test_migration_plan_documented(self, report):
        plan = report["migration_plan"]
        assert plan[0] == "57A-10F_scalar_baseline_persistence_and_validation_only"
        assert plan[1] == "57A-10G_export_audit_evidence_and_allowlisted_metadata_overrides"
        assert plan[2] == "57A-10H_tax_depreciation_runtime_wiring_if_separately_approved"


class TestSafetyAndRc1:
    def test_design_only_boundaries_preserved(self, report):
        boundaries = set(report["design_only_boundaries"])
        assert "no_runtime_changes" in boundaries
        assert "no_schema_changes" in boundaries
        assert "no_export_changes" in boundaries
        assert "no_run_changes" in boundaries
        assert "no_formula_changes" in boundaries
        assert "no_tax_engine_wiring" in boundaries
        assert "no_depreciation_engine_wiring" in boundaries
        assert "no_idc_wiring" in boundaries
        assert "no_ui_static_changes" in boundaries

    @pytest.mark.parametrize(
        "path_name",
        [
            "app/waterfall_core.py",
            "app/services/run_service.py",
            "app/services/capex_sub_lines_integration.py",
            "app/excel_export.py",
            "app/persistence/*",
            "app/project_factories.py",
            "app/templates/*",
            "static/app.js",
            "static/styles.css",
        ],
    )
    def test_forbidden_paths_are_pinned_unchanged(self, report, path_name):
        assert path_name in report["files_not_changed"]

    def test_rc1_sha_pinned(self, report):
        assert (
            report["rc1_frozen_sha"]
            == "b425a0708719eaa5e1d922b1008e5609758e0ad4"
        )

    def test_recommendation_is_pass(self, report):
        assert report["recommendation"] == "PASS"
