"""Phase 7 — SHL Canonical Module Design doc validation tests.

Tests that the design document exists and covers required sections.
No runtime/behavior tests — this is a docs-only branch.
"""
import os
import pytest

DOC = os.path.join(
    os.path.dirname(__file__),
    "..",
    "docs",
    "phase7_shl_canonical_module_design.md",
)


# ---------------------------------------------------------------------------
# Document existence
# ---------------------------------------------------------------------------

class TestDocExists:
    def test_design_doc_exists(self):
        assert os.path.exists(DOC), f"{DOC} not found"

    def test_design_doc_not_empty(self):
        with open(DOC) as f:
            content = f.read()
        assert len(content) > 1000, "Design doc is suspiciously short"


# ---------------------------------------------------------------------------
# Required sections present
# ---------------------------------------------------------------------------

REQUIRED_SECTIONS = [
    "Executive Summary",
    "Inputs and Source Ownership",
    "Outputs and Audit Rows",
    "Canonical Waterfall Order",
    "Module Layout",
    "dataclasses",
    "Tax Interface",
    "Distribution",
    "Sponsor Interface",
    "Validation",
    "Runtime Integration",
    "Migration",
    "Oborovo Readiness",
    "Forbidden Scope",
    "Recommended Next Branch",
]


class TestSections:
    def test_all_sections_present(self):
        with open(DOC) as f:
            content = f.read()
        for section in REQUIRED_SECTIONS:
            assert section in content, f"Missing section: {section}"


# ---------------------------------------------------------------------------
# Required dataclasses documented
# ---------------------------------------------------------------------------

REQUIRED_DATACLASSES = [
    "ShlPeriodInput",
    "ShlEngineInputs",
    "ShlPeriodResult",
    "ShlEngineResult",
    "ShlAuditRow",
    "ShlTaxInterface",
]


class TestDataclassCoverage:
    def test_all_dataclasses_documented(self):
        with open(DOC) as f:
            content = f.read()
        for dc in REQUIRED_DATACLASSES:
            assert dc in content, f"Missing dataclass: {dc}"


# ---------------------------------------------------------------------------
# Canonical fields documented
# ---------------------------------------------------------------------------

REQUIRED_INPUT_FIELDS = [
    "opening_balance_keur",
    "drawdown_keur",
    "interest_rate",
    "day_count_fraction",
    "post_senior_cash_available_keur",
    "cash_sweep_after_senior",
    "maintain_minimum_cash_reserve",
    "minimum_cash_reserve_keur",
    "pik_allowed",
]

REQUIRED_OUTPUT_FIELDS = [
    "gross_accrued_interest_keur",
    "cash_interest_paid_keur",
    "pik_capitalized_keur",
    "principal_repaid_keur",
    "closing_balance_keur",
    "cash_consumed_by_shl_keur",
    "cash_after_shl_keur",
    "cash_for_distribution_keur",
]


class TestFieldCoverage:
    def test_input_fields_documented(self):
        with open(DOC) as f:
            content = f.read()
        for field in REQUIRED_INPUT_FIELDS:
            assert field in content, f"Missing input field: {field}"

    def test_output_fields_documented(self):
        with open(DOC) as f:
            content = f.read()
        for field in REQUIRED_OUTPUT_FIELDS:
            assert field in content, f"Missing output field: {field}"


# ---------------------------------------------------------------------------
# TUHO defaults documented
# ---------------------------------------------------------------------------

TUHO_DEFAULTS = [
    "cash_sweep_after_senior = True",
    "maintain_minimum_cash_reserve = False",
    "pik_allowed",
    "100% cash sweep",
    "no minimum cash reserve",
]


class TestTuhuDefaults:
    def test_tuho_defaults_documented(self):
        with open(DOC) as f:
            content = f.read()
        for item in TUHO_DEFAULTS:
            assert item.lower() in content.lower(), f"Missing TUHO default: {item}"


# ---------------------------------------------------------------------------
# Oborovo open item documented
# ---------------------------------------------------------------------------

class TestOborovoOpenItem:
    def test_oborovo_missing_extraction_documented(self):
        with open(DOC) as f:
            content = f.read()
        assert "OPEN ITEM" in content or "open item" in content.lower(), \
            "Oborovo open item not documented"
        assert "not available" in content.lower() or "was not available" in content.lower(), \
            "Oborovo file unavailability not mentioned"


# ---------------------------------------------------------------------------
# R99/R102 blocked status
# ---------------------------------------------------------------------------

class TestR99Blocked:
    def test_r99_blocked_mentioned(self):
        with open(DOC) as f:
            content = f.read()
        assert "BLOCKED" in content or "blocked" in content.lower(), \
            "R99/R102 BLOCKED status not documented"


# ---------------------------------------------------------------------------
# Domain module layout documented
# ---------------------------------------------------------------------------

REQUIRED_MODULE_FILES = [
    "domain/shl",
    "inputs.py",
    "result.py",
    "engine.py",
    "audit.py",
]


class TestModuleLayout:
    def test_proposed_module_files_documented(self):
        with open(DOC) as f:
            content = f.read()
        for fpath in REQUIRED_MODULE_FILES:
            assert fpath in content, f"Missing module file: {fpath}"


# ---------------------------------------------------------------------------
# Waterfall order steps
# ---------------------------------------------------------------------------

WATERFALL_STEPS = [
    "opening balance",
    "drawdown",
    "gross accrued",
    "cash after",
    "minimum cash reserve",
    "cash interest",
    "pik",
    "principal",
    "closing balance",
    "distribution",
]


class TestWaterfallOrder:
    def test_waterfall_steps_documented(self):
        with open(DOC) as f:
            content = f.read()
        for step in WATERFALL_STEPS:
            assert step.lower() in content.lower(), f"Missing waterfall step: {step}"


# ---------------------------------------------------------------------------
# Migration plan
# ---------------------------------------------------------------------------

class TestMigrationPlan:
    def test_migration_plan_mentions_shl_fcf_waterfall(self):
        with open(DOC) as f:
            content = f.read()
        assert "shl_fcf_waterfall" in content, \
            "Migration from shl_fcf_waterfall not mentioned"


# ---------------------------------------------------------------------------
# No runtime changes (test suite should not import domain modules)
# ---------------------------------------------------------------------------

class TestNoRuntimeChanges:
    def test_domain_shl_not_imported(self):
        """Verify this test file does not import domain.shl (which doesn't exist yet)."""
        import sys
        mod_names = list(sys.modules.keys())
        shl_mods = [m for m in mod_names if m.startswith("domain.shl")]
        assert not shl_mods, f"Unexpected domain.shl modules imported: {shl_mods}"

    def test_no_production_runtime_files_created(self):
        """Confirm no domain/shl/*.py files were created in this branch."""
        import os
        shl_dir = os.path.join(os.path.dirname(__file__), "..", "domain", "shl")
        if os.path.exists(shl_dir):
            files = os.listdir(shl_dir)
            assert not files, f"Unexpected domain/shl/ files found: {files} — design-only branch"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
