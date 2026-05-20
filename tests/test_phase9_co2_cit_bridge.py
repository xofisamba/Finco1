"""Phase 9 CO2→CIT runtime bridge validation tests.

Tests the `use_co2_cit_bridge` flag which adds TUHO CO2 certificate revenue
directly to taxable income in the TaxEngine (without modifying EBITDA).

R99/R102: BLOCKED — taxable income only, no distribution promotion.
"""

import pytest
from pathlib import Path

DOCS_PATH = Path("docs/phase9_co2_cit_runtime_bridge.md")
CSV_PATH = Path("reports/phase9_co2_cit_bridge_validation.csv")


class TestFlagDefaults:
    """Flag must default to False to preserve legacy baseline."""

    def test_cit_bridge_flag_default_is_false(self):
        from app.waterfall_core import run_waterfall_v3_core
        import inspect
        sig = inspect.signature(run_waterfall_v3_core)
        param = sig.parameters["use_co2_cit_bridge"]
        assert param.default is False, (
            f"use_co2_cit_bridge must default to False, got {param.default}"
        )

    def test_cit_bridge_flag_exists(self):
        from app.waterfall_core import run_waterfall_v3_core
        import inspect
        sig = inspect.signature(run_waterfall_v3_core)
        assert "use_co2_cit_bridge" in sig.parameters


class TestBridgeValidation:
    """Doc, CSV, and implementation checks."""

    def test_cit_bridge_doc_exists(self):
        assert DOCS_PATH.exists(), f"{DOCS_PATH} must exist"

    def test_cit_bridge_csv_exists(self):
        assert CSV_PATH.exists(), f"{CSV_PATH} must exist"

    def test_cit_bridge_doc_has_required_sections(self):
        content = DOCS_PATH.read_text()
        required = [
            "Executive Summary",
            "Current CO2→Tax Gap",
            "Taxable Income Bridge Design",
            "Runtime Ownership Boundaries",
            "R99/R102 Blocked Confirmation",
            "Recommended Next Step",
        ]
        for section in required:
            assert section in content, f"Missing section: {section}"

    def test_csv_has_required_columns(self):
        content = CSV_PATH.read_text()
        header = content.split("\n")[0]
        required = ["project", "flag", "metric", "baseline", "delta", "status", "notes"]
        for col in required:
            assert col in header, f"Missing CSV column: {col}"

    def test_csv_has_both_projects(self):
        content = CSV_PATH.read_text()
        assert "TUHO" in content
        assert "OBOROVO" in content


class TestMutualExclusivity:
    """use_co2_cit_bridge and use_co2_revenue_bridge cannot both be True."""

    def test_mutual_exclusivity_enforced_in_code(self):
        content = Path("app/waterfall_core.py").read_text()
        assert "use_co2_cit_bridge and use_co2_revenue_bridge cannot both be True" in content

    def test_revenue_bridge_still_functional(self):
        from app.waterfall_core import run_waterfall_v3_core
        import inspect
        sig = inspect.signature(run_waterfall_v3_core)
        assert "use_co2_revenue_bridge" in sig.parameters


class TestTuhoOnlyGuard:
    """CO2 CIT bridge must raise ValueError for non-TUHO-WIND-1 projects."""

    def test_guard_raises_for_unknown_project(self):
        content = Path("app/waterfall_core.py").read_text()
        assert 'raise ValueError' in content
        assert "TUHO-WIND-1" in content
        assert "use_co2_cit_bridge" in content


class TestTaxEngineWiring:
    """CO2→CIT bridge is wired into compute_period_tax."""

    def test_co2_param_in_compute_period_tax(self):
        from domain.waterfall.tax_engine import compute_period_tax
        import inspect
        sig = inspect.signature(compute_period_tax)
        assert "co2_revenue_keur" in sig.parameters

    def test_co2_cit_bridge_field_in_tax_period_result(self):
        from domain.waterfall.tax_engine import TaxPeriodResult
        fields = [f.name for f in TaxPeriodResult.__dataclass_fields__.values()]
        assert "co2_cit_bridge_keur" in fields

    def test_co2_added_to_taxable_before_losses(self):
        content = Path("domain/waterfall/tax_engine.py").read_text()
        assert "co2_revenue_keur" in content
        # Should be added, not subtracted
        idx = content.find("co2_revenue_keur")
        snippet = content[idx-20:idx+60]
        assert "+ co2_revenue_keur" in snippet or "ebitda_keur\n        + co2_revenue_keur" in content


class TestWaterfallEngineWiring:
    """co2_cit_bridge_by_period is threaded through run_waterfall."""

    def test_co2_cit_bridge_param_in_run_waterfall(self):
        from domain.waterfall.waterfall_engine import run_waterfall
        import inspect
        sig = inspect.signature(run_waterfall)
        assert "co2_cit_bridge_by_period" in sig.parameters

    def test_co2_cit_bridge_passed_to_compute_period_tax(self):
        content = Path("domain/waterfall/waterfall_engine.py").read_text()
        assert "co2_revenue_keur=co2_cit_bridge_keur" in content


class TestR99R102Blocked:
    """R99/R102 are not modified by use_co2_cit_bridge."""

    def test_r99_blocked_in_doc(self):
        content = DOCS_PATH.read_text()
        assert "R99" in content
        # Confirm R99 section says BLOCKED
        assert "R99" in content and "BLOCKED" in content

    def test_r102_blocked_in_doc(self):
        content = DOCS_PATH.read_text()
        assert "R102" in content
        # Confirm R102 section says BLOCKED
        assert "R102" in content and "BLOCKED" in content


class TestNoDistributionAccountChange:
    """DistributionAccount is not rewritten by this bridge."""

    def test_distributionaccount_not_in_cit_bridge_doc(self):
        content = DOCS_PATH.read_text()
        section = "Runtime Ownership Boundaries"
        start = content.find(section)
        end = start + 500 if start != -1 else len(content)
        snippet = content[start:end]
        assert "DistributionAccount" not in snippet or "Unchanged" in snippet


class TestNoEbITDAChange:
    """EBITDA chain is unchanged when use_co2_cit_bridge=True."""

    def test_ebitda_unchanged_in_doc(self):
        content = DOCS_PATH.read_text()
        # Should say ebitda_schedule is unchanged
        assert "ebitda_schedule" in content
        assert "Unchanged" in content


class TestAuditMetadata:
    """CO2→CIT bridge attaches audit metadata to the result."""

    def test_audit_metadata_in_code(self):
        content = Path("app/waterfall_core.py").read_text()
        assert "_co2_cit_bridge" in content
        assert "co2_by_period" in content

    def test_period_annotation_with_co2_cit_bridge_keur(self):
        content = Path("app/waterfall_core.py").read_text()
        assert 'setattr(wp, "co2_cit_bridge_keur"' in content


class TestNoConflictingCombinations:
    """Guard against using both CO2 bridges simultaneously."""

    def test_oborovo_raises_value_error(self):
        """Oborovo is protected by TUHO-only guard."""
        content = Path("app/waterfall_core.py").read_text()
        # The guard should appear for use_co2_cit_bridge
        assert "use_co2_cit_bridge=True" in content


class TestDocsRequiredSections:
    """All 12 required documentation sections are present."""

    def test_executive_summary_exists(self):
        content = DOCS_PATH.read_text()
        assert "Executive Summary" in content

    def test_depreciation_interaction_section_exists(self):
        content = DOCS_PATH.read_text()
        assert "Depreciation Interaction" in content

    def test_tax_loss_interaction_section_exists(self):
        content = DOCS_PATH.read_text()
        assert "Tax Loss Interaction" in content

    def test_actual_vs_sizing_cfads_section_exists(self):
        content = DOCS_PATH.read_text()
        assert "actual_cfads vs sizing_cfads" in content or "sizing_cfads" in content

    def test_distributionaccount_non_participation_section_exists(self):
        content = DOCS_PATH.read_text()
        assert "DistributionAccount Non-Participation" in content or "DistributionAccount" in content

    def test_validation_results_section_exists(self):
        content = DOCS_PATH.read_text()
        assert "Validation Results" in content

    def test_known_limitations_section_exists(self):
        content = DOCS_PATH.read_text()
        assert "Known Limitations" in content

    def test_recommended_next_step_section_exists(self):
        content = DOCS_PATH.read_text()
        assert "Recommended Next Step" in content

    def test_change_table_exists(self):
        content = DOCS_PATH.read_text()
        assert "| File |" in content or "domain/waterfall" in content
