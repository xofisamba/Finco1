from __future__ import annotations

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "docs" / "phase57a10d_capex_vat_wht_depreciation_basis_design.md"
REPORT_PATH = REPO_ROOT / "reports" / "phase57a10d_capex_vat_wht_depreciation_basis_design.json"


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


class TestVatBasis:
    def test_vat_basis_documented(self, report, doc_text):
        vat = report["vat_basis"]
        assert vat["recoverability_required"] is True
        assert vat["recoverable_vat_not_automatically_economic_capex"] is True
        assert vat["nonrecoverable_vat_may_become_economic_capex"] is True
        assert set(vat["supported_basis_modes"]) == {"base_only", "base_plus_contingency"}
        lowered = doc_text.lower()
        assert "recoverable" in lowered
        assert "non-recoverable" in lowered or "nonrecoverable" in lowered


class TestWhtBasis:
    def test_wht_basis_documented(self, report, doc_text):
        wht = report["wht_basis"]
        assert wht["line_level_metadata"] is True
        assert wht["supplier_or_jurisdiction_dependent"] is True
        assert wht["primary_nature"] == "tax_or_cash_timing_treatment"
        assert set(wht["supported_gross_up_modes"]) == {
            "withheld_from_payment",
            "grossed_up_by_payer",
        }
        lowered = doc_text.lower()
        assert "gross-up" in lowered or "grossed up" in lowered
        assert "withholding" in lowered


class TestDepreciationBasis:
    def test_depreciation_basis_documented(self, report, doc_text):
        dep = report["depreciation_basis"]
        assert "depreciable_flag" in dep["required_fields"]
        assert "depreciation_category" in dep["required_fields"]
        assert "useful_life_years" in dep["required_fields"]
        assert "depreciation_basis_mode" in dep["required_fields"]
        assert dep["separate_from_current_runtime_tax_book_engine"] is True
        lowered = doc_text.lower()
        assert "useful life" in lowered
        assert "tax / book" in lowered or "tax/book" in lowered


class TestScenarioSemantics:
    def test_scenario_semantics_documented(self, report, doc_text):
        sem = report["scenario_semantics"]
        assert sem["override_keying"] == "sub_line_id"
        assert sem["override_rule"] == "replace_not_delta"
        assert sem["duplicated_scenarios_preserve_overrides"] is True
        assert sem["derived_tax_or_depreciation_amounts_direct_overrideable"] is False
        lowered = doc_text.lower()
        assert "replace baseline values" in lowered
        assert "duplicated scenarios" in lowered


class TestUserAddedRows:
    def test_user_added_line_behavior_documented(self, report, doc_text):
        rows = report["user_added_sub_lines"]
        assert rows["supported"] is True
        assert rows["ownership"] == "project_owned_baseline_plus_scenario_override_by_sub_line_id"
        assert rows["exports_basis_metadata"] is True
        assert "C.02.U001" in doc_text
        assert "C.08.U001" in doc_text


class TestExportStrategy:
    def test_export_audit_strategy_documented(self, report, doc_text):
        strategy = report["export_strategy"]
        assert "CapEx" in strategy
        assert "CapEx_Items" in strategy
        assert "CapEx_SubLines_Audit" in strategy
        assert "tax_depreciation_audit_sheets" in strategy
        assert "reconciliation_sheets" in strategy
        lowered = doc_text.lower()
        assert "capex_sublines_audit" in lowered or "capex sublines audit" in lowered
        assert "tax / depreciation audit sheets" in lowered or "tax/depreciation audit sheets" in lowered


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


class TestImplementationOptions:
    def test_implementation_options_compared(self, report, doc_text):
        options = report["implementation_options"]
        assert set(options.keys()) == {
            "A_widen_capex_sub_lines",
            "B_capex_sub_line_tax_details_table",
            "C_json_metadata_on_sub_line",
            "D_hybrid_scalar_columns_plus_detail_tables",
        }
        assert report["preferred_architecture"] == "D_hybrid_scalar_columns_plus_detail_tables"
        lowered = doc_text.lower()
        assert "option a" in lowered
        assert "option b" in lowered
        assert "option c" in lowered
        assert "option d" in lowered


class TestBoundaries:
    def test_design_only_boundaries_preserved(self, report):
        boundaries = set(report["design_only_boundaries"])
        assert boundaries == {
            "no_runtime_implementation",
            "no_schema_changes",
            "no_export_changes",
            "no_run_changes",
            "no_financial_formula_changes",
            "no_tax_engine_wiring",
            "no_depreciation_engine_wiring",
            "no_idc_wiring",
        }

    def test_rc1_pinned(self, report):
        assert report["rc1_frozen_sha"] == "b425a0708719eaa5e1d922b1008e5609758e0ad4"
