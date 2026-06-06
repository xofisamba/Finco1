"""Phase 57A-10 advanced columns foundation design contract tests.

This phase is intentionally docs/report/test-only.
It must not introduce runtime, schema, UI, export, or
formula behavior changes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = (
    REPO_ROOT / "docs" / "phase57a10_capex_advanced_columns_foundation_design.md"
)
REPORT_PATH = (
    REPO_ROOT
    / "reports"
    / "phase57a10_capex_advanced_columns_foundation_design.json"
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


class TestRequiredColumnsAddressed:
    @pytest.mark.parametrize(
        "column_name",
        [
            "label",
            "amount_keur",
            "cost_per_mw",
            "contingency_pct",
            "vat_applicability",
            "vat_rate_pct",
            "wht_rate_pct",
            "depreciation_category",
            "depreciation_life_years",
            "comments",
            "payment_schedule",
            "utilisation",
        ],
    )
    def test_column_exists_in_report(self, report, column_name):
        names = [entry["name"] for entry in report["required_columns"]]
        assert column_name in names

    @pytest.mark.parametrize(
        "phrase",
        [
            "ownership model",
            "scenario override semantics",
            "calculation authority matrix",
            "excel compatibility analysis",
            "payment schedule and utilisation design",
            "vat / wht design assumptions",
            "depreciation design assumptions",
        ],
    )
    def test_foundation_topics_exist_in_doc(self, doc_text, phrase):
        assert phrase in doc_text.lower()


class TestOwnershipAndOverrideSemantics:
    def test_project_level_uuid_ownership_defined(self, report):
        ownership = report["ownership_model"]
        assert ownership["sub_line_id_identity"] == "project_level_uuid"
        assert ownership["scenario_role"] == "override_state_only"

    def test_core_override_rule_is_replace_not_delta(self, report, doc_text):
        assert (
            report["scenario_override_semantics"]["core_rule"]
            == "override_replaces_baseline_not_delta"
        )
        assert "replaces the baseline field value" in doc_text.lower()

    def test_unknown_override_rule_preserved(self, report):
        assert (
            report["scenario_override_semantics"]["unknown_override_keys"]
            == "phase20b_silent_drop_preserved"
        )


class TestDesignOnlyBoundaries:
    def test_design_only_boundaries_include_runtime_export_schema_formula(self, report):
        boundaries = set(report["design_only_boundaries"])
        assert "no_runtime_changes" in boundaries
        assert "no_schema_changes" in boundaries
        assert "no_ui_changes" in boundaries
        assert "no_formula_changes" in boundaries
        assert "no_excel_export_changes" in boundaries
        assert "no_idc_runtime_wiring" in boundaries

    def test_vat_wht_depreciation_schedule_are_design_only(self, doc_text):
        lowered = doc_text.lower()
        assert "design-only" in lowered
        assert "no idc runtime wiring" in lowered
        assert "not wired to current run" in lowered

    def test_phase_plan_exists(self, report):
        assert len(report["phase_plan"]) >= 5
        assert report["phase_plan"][0] == "57A-10A_metadata_safe_columns"


class TestUntouchedFilesPinned:
    @pytest.mark.parametrize(
        "path_name",
        [
            "app/waterfall_core.py",
            "app/services/run_service.py",
            "app/services/capex_sub_lines_integration.py",
            "app/persistence/capex_sub_lines.py",
            "app/excel_export.py",
            "app/project_factories.py",
        ],
    )
    def test_runtime_files_list_unchanged(self, report, path_name):
        assert path_name in report["files_not_changed"]

    def test_schema_files_unchanged(self, report):
        assert "schema" in report["schema_files_not_changed"]
        assert "migrations" in report["schema_files_not_changed"]

    def test_ui_static_files_unchanged(self, report):
        ui_files = set(report["ui_files_not_changed"])
        assert "static/app.js" in ui_files
        assert "static/styles.css" in ui_files

    def test_formula_files_unchanged(self, report):
        assert "app/waterfall_core.py" in report["formula_files_not_changed"]


class TestRecommendationAndRc1:
    def test_recommendation_is_pass(self, report):
        assert report["recommendation"] == "PASS"

    def test_rc1_sha_pinned(self, report):
        assert (
            report["rc1_frozen_sha"]
            == "b425a0708719eaa5e1d922b1008e5609758e0ad4"
        )
