"""Phase 7 — Senior Debt Canonical Module Design doc validation tests.

Tests that the design document exists and covers required sections.
No runtime/behavior tests — this is a docs-only branch.
"""
import os
import pytest

DOC = os.path.join(
    os.path.dirname(__file__),
    "..",
    "docs",
    "phase7_senior_debt_canonical_module_design.md",
)


class TestDocExists:
    def test_design_doc_exists(self):
        assert os.path.exists(DOC), f"{DOC} not found"

    def test_design_doc_not_empty(self):
        with open(DOC) as f:
            content = f.read()
        assert len(content) > 1000, "Design doc is suspiciously short"


REQUIRED_SECTIONS = [
    "Executive Summary",
    "Inputs and Source Ownership",
    "Actual CFADS vs Sizing CFADS",
    "Target DSCR",
    "Canonical Calculation Order",
    "Module Layout",
    "dataclasses",
    "Interest",
    "Principal",
    "DSCR",
    "SHL Handoff",
    "Tax",
    "Migration",
    "Multi-lender",
    "Runtime Integration",
    "Forbidden Scope",
    "Recommended Next Branch",
]


class TestSections:
    def test_all_sections_present(self):
        with open(DOC) as f:
            content = f.read()
        for section in REQUIRED_SECTIONS:
            assert section in content, f"Missing section: {section}"


REQUIRED_DATACLASSES = [
    "SeniorDebtSizingPolicy",
    "SeniorDebtDSCRPolicy",
    "SeniorDebtPeriodInput",
    "SeniorDebtEngineInputs",
    "SeniorDebtPeriodResult",
    "SeniorDebtEngineResult",
    "SeniorDebtAuditRow",
]


class TestDataclassCoverage:
    def test_all_dataclasses_documented(self):
        with open(DOC) as f:
            content = f.read()
        for dc in REQUIRED_DATACLASSES:
            assert dc in content, f"Missing dataclass: {dc}"


REQUIRED_INPUT_FIELDS = [
    "actual_cfads_keur",
    "sizing_cfads_keur",
    "target_dscr",
    "opening_balance_keur",
    "interest_rate",
    "day_count_fraction",
    "repayment_start_period",
    "maturity_period",
    "principal_cap",
    "allow_full_cash_sweep",
]

REQUIRED_OUTPUT_FIELDS = [
    "debt_service_capacity_keur",
    "interest_keur",
    "scheduled_principal_keur",
    "principal_repaid_keur",
    "closing_balance_keur",
    "senior_debt_service_keur",
    "post_senior_cash_available_keur",
    "actual_dscr",
    "sizing_dscr",
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


POLICY_DECISIONS = [
    "sizing_cfads_keur_by_period",
    "explicit input",
    "Macro!R50",
    "actual CFADS",
    "post-senior cash",
    "SHL handoff",
    "PPA",
    "merchant",
    "1.20",
    "1.41",
]


class TestPolicyDecisions:
    def test_key_policies_documented(self):
        with open(DOC) as f:
            content = f.read()
        lc = content.lower()
        for item in POLICY_DECISIONS:
            assert item.lower() in lc, f"Missing policy: {item}"


REQUIRED_MODULE_FILES = [
    "domain/senior_debt",
    "inputs.py",
    "result.py",
    "engine.py",
    "sizing_policy.py",
    "rate_schedule.py",
    "audit.py",
]


class TestModuleLayout:
    def test_proposed_module_files_documented(self):
        with open(DOC) as f:
            content = f.read()
        for fpath in REQUIRED_MODULE_FILES:
            assert fpath in content, f"Missing module file: {fpath}"


CALCULATION_STEPS = [
    "actual CFADS",
    "sizing CFADS",
    "target DSCR",
    "debt service capacity",
    "interest",
    "principal capacity",
    "closing balance",
    "post-senior cash",
    "SHL handoff",
]


class TestCalculationOrder:
    def test_calculation_steps_documented(self):
        with open(DOC) as f:
            content = f.read()
        lc = content.lower()
        for step in CALCULATION_STEPS:
            assert step.lower() in lc, f"Missing calc step: {step}"


class TestR99Blocked:
    def test_r99_blocked_mentioned(self):
        with open(DOC) as f:
            content = f.read()
        assert "BLOCKED" in content or "blocked" in content.lower(), \
            "R99/R102 BLOCKED status not documented"


class TestMigrationPlan:
    def test_migration_plan_mentions_senior_sculpting(self):
        with open(DOC) as f:
            content = f.read()
        assert "senior_sculpting" in content, \
            "Migration from senior_sculpting not mentioned"


class TestMultiLenderFuture:
    def test_multi_lender_documented_as_future(self):
        with open(DOC) as f:
            content = f.read()
        assert "future" in content.lower(), \
            "Multi-lender future extension not mentioned"


class TestNoRuntimeChanges:
    def test_domain_senior_debt_not_imported(self):
        import sys
        mod_names = list(sys.modules.keys())
        sd_mods = [m for m in mod_names if m.startswith("domain.senior_debt")]
        assert not sd_mods, f"Unexpected domain.senior_debt modules imported: {sd_mods}"

    def test_no_production_runtime_files_created(self):
        import os
        sd_dir = os.path.join(os.path.dirname(__file__), "..", "domain", "senior_debt")
        if os.path.exists(sd_dir):
            files = os.listdir(sd_dir)
            assert not files, f"Unexpected domain/senior_debt/ files found: {files} — design-only"


class TestSHLHandoff:
    def test_shl_handoff_documented(self):
        with open(DOC) as f:
            content = f.read()
        assert "post_senior_cash_available" in content, \
            "SHL handoff not documented"


class TestMacroR50:
    def test_macro_r50_documented_as_explicit_sizing_input(self):
        with open(DOC) as f:
            content = f.read()
        assert "Macro!R50" in content, "Macro!R50 not mentioned"
        assert "explicit input" in content.lower() or "explicit sizing" in content.lower(), \
            "Macro!R50 as explicit input not documented"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])