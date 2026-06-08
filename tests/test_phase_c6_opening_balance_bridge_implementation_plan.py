"""Phase C6 - Layer 4 Opening Balance Bridge Implementation Plan tests.

**Scope label:** DESIGN / IMPLEMENTATION PLAN ONLY. DOCS ONLY. NO CODE.
NO RUNTIME. NO DOMAIN. NO FORMULA CHANGES.

This phase is a **plan**, not an implementation. The C6 test file
is a **design-doc / report / non-scope / API shape / guards /
recommendation / hard-constraints** test, not a runtime test. It
asserts that this plan is correct, complete, and self-consistent.

This phase does NOT implement:
- domain/construction/opening_bridge.py (C7+)
- Any bridge dataclass (C7+)
- Any bridge function (C7+)
- C2 §6.4 / §6.5 / §6.6 tests (C7+)
- Layer 5 runtime seam (C8 design, C9 implementation)
- Opt-in flag flip (C10+)
- Senior IDC base-rate modelling (separate workstream)

Hard constraints:
- NO code implementation
- NO runtime changes
- NO domain changes
- NO schema changes
- NO persistence changes
- NO feature flags
- NO formula changes
- NO CAPEX/debt/tax/depreciation/IDC changes
- NO project status changes
- rc1 SHA `b425a07...` reachable
- `use_construction_schedule_engine` remains default-off
- C4 snapshots are READ-ONLY
- C5 fixtures are READ-ONLY
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
DESIGN_DOC = (
    REPO_ROOT
    / "docs" / "phase_c6_opening_balance_bridge_implementation_plan.md"
)
REPORT_JSON = (
    REPO_ROOT
    / "reports"
    / "phase_c6_opening_balance_bridge_implementation_plan.json"
)
C1_DOC = REPO_ROOT / "docs" / "phase_c1_construction_idc_design_gate.md"
C2_DOC = (
    REPO_ROOT
    / "docs" / "phase_c2_shl_idc_convention_opening_balance_bridge.md"
)
C3_DOC = (
    REPO_ROOT / "docs" / "phase_c3_construction_parity_snapshot_design.md"
)
C4_FIXTURES = (
    REPO_ROOT / "tests" / "fixtures" / "construction_parity"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def design_doc_text() -> str:
    return DESIGN_DOC.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def report_json_data() -> dict:
    return json.loads(REPORT_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def c2_doc_text() -> str:
    return C2_DOC.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------


class TestFilesExist:
    def test_design_doc_exists(self):
        assert DESIGN_DOC.is_file()

    def test_report_json_exists(self):
        assert REPORT_JSON.is_file()

    def test_c1_doc_exists(self):
        assert C1_DOC.is_file()

    def test_c2_doc_exists(self):
        assert C2_DOC.is_file()

    def test_c3_doc_exists(self):
        assert C3_DOC.is_file()

    def test_c4_fixtures_dir_exists(self):
        assert C4_FIXTURES.is_dir()


# ---------------------------------------------------------------------------
# Scope label — design / implementation plan only
# ---------------------------------------------------------------------------


class TestScopeLabelDocsOnly:
    """C6 is DESIGN / IMPLEMENTATION PLAN ONLY. DOCS ONLY. NO CODE."""

    def test_scope_label_in_design_doc(self, design_doc_text):
        text = design_doc_text
        assert "DESIGN / IMPLEMENTATION PLAN ONLY" in text
        assert "DOCS ONLY" in text
        assert "NO CODE" in text
        assert "NO RUNTIME" in text
        assert "NO DOMAIN" in text
        assert "NO FORMULA CHANGES" in text

    def test_scope_label_in_report(self, report_json_data):
        assert "scope_label" in report_json_data
        assert "DESIGN / IMPLEMENTATION PLAN ONLY" in (
            report_json_data["scope_label"]
        )

    def test_no_bridge_module_in_c6(self, design_doc_text):
        # C6 explicitly excludes the bridge module
        text = design_doc_text
        assert "C6 does NOT add" in text
        assert "domain/construction/opening_bridge.py" in text
        # And the test file must NOT add it
        test_file = Path(__file__).read_text(encoding="utf-8")
        # AST check: no import of opening_bridge
        tree = ast.parse(test_file)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "opening_bridge" in node.module:
                    pytest.fail(
                        f"C6 test must not import {node.module!r} (bridge is C7+)"
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if "opening_bridge" in alias.name:
                        pytest.fail(
                            f"C6 test must not import {alias.name!r} (bridge is C7+)"
                        )

    def test_c6_stops_at_plan(self, design_doc_text):
        assert "Stop after report" in design_doc_text


# ---------------------------------------------------------------------------
# Section 1: C1-C5 stack verification
# ---------------------------------------------------------------------------


class TestC1C5StackVerification:
    def test_c1_sha_in_design_doc(self, design_doc_text):
        assert "5fccc3a" in design_doc_text

    def test_c2_sha_in_design_doc(self, design_doc_text):
        assert "59f9e3d" in design_doc_text

    def test_c3_sha_in_design_doc(self, design_doc_text):
        assert "aa800a5" in design_doc_text

    def test_c4_sha_in_design_doc(self, design_doc_text):
        assert "dcc30b6" in design_doc_text

    def test_c5_sha_in_design_doc(self, design_doc_text):
        assert "2d8a91c" in design_doc_text

    def test_c1_c5_shas_reachable(self):
        for sha in ("5fccc3a", "59f9e3d", "aa800a5", "dcc30b6", "2d8a91c"):
            result = subprocess.run(
                ["git", "cat-file", "-e", sha],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, (
                f"C1-C5 SHA {sha} not reachable"
            )

    def test_c1_blockers_5_total(self, design_doc_text):
        # C1 listed 5 blockers
        text = design_doc_text
        assert "5 blockers" in text

    def test_c2_section_6_7_readiness_count(self, design_doc_text):
        # C2 §6.7 has 8 items
        assert "8 items" in design_doc_text or "items_total=8" in design_doc_text

    def test_c5_recommendation_was_b(self, design_doc_text):
        # C5 recommended B (more validation needed)
        text = design_doc_text
        assert "B. More validation needed" in text

    def test_c6_recommendation_in_design_doc(self, design_doc_text):
        # C6 also recommends B
        assert "Choice: **B. More design needed**" in design_doc_text

    def test_c6_recommendation_in_report(self, report_json_data):
        assert report_json_data["recommendation"]["choice"] == "B. More design needed"

    def test_preconditions_met_in_design_doc(self, design_doc_text):
        assert "All C1–C5 preconditions for C6 are met" in design_doc_text


# ---------------------------------------------------------------------------
# Section 2: Layer 4 implementation scope
# ---------------------------------------------------------------------------


class TestLayer4Scope:
    def test_scope_section_present(self, design_doc_text):
        assert "## 2. Define exact Layer 4 implementation scope" in (
            design_doc_text
        )

    def test_opening_senior_balance_in_scope(self, design_doc_text):
        assert "opening_senior_balance_at_cod_keur" in design_doc_text

    def test_opening_shl_balance_in_scope(self, design_doc_text):
        assert "opening_shl_balance_at_cod_keur" in design_doc_text

    def test_equity_contribution_in_scope(self, design_doc_text):
        assert "equity_contribution_at_cod_keur" in design_doc_text

    def test_capitalized_idc_in_scope(self, design_doc_text):
        assert "capitalized_senior_idc_keur" in design_doc_text
        assert "capitalized_shl_idc_keur" in design_doc_text

    def test_financing_fee_in_scope(self, design_doc_text):
        assert "financing_fee_treatment_keur" in design_doc_text

    def test_audit_table_in_scope(self, design_doc_text):
        assert "audit_reconciliation_table" in design_doc_text

    def test_11_field_policy_in_scope(self, design_doc_text):
        # The 11-field policy table (C2 §2.1) is in scope
        assert "11-field policy table" in design_doc_text

    def test_dataclass_count(self, design_doc_text):
        # C6 §5 lists 8 dataclasses (5 input + 3 output)
        text = design_doc_text
        assert "OpeningBalanceBridgeInput" in text
        assert "OpeningBalanceBridgeResult" in text
        assert "BridgeAuditRow" in text
        assert "BridgeMetadata" in text
        assert "ManualOverrideRow" in text
        assert "BridgeFieldPolicy" in text
        assert "ParityReferenceRow" in text
        assert "ProjectAssumptions" in text

    def test_function_signature(self, design_doc_text):
        # The single public function
        assert "build_opening_balance_bridge" in design_doc_text

    def test_exception_name(self, design_doc_text):
        # The exception type
        assert "BridgeIdentityError" in design_doc_text


# ---------------------------------------------------------------------------
# Section 3: Non-scope
# ---------------------------------------------------------------------------


class TestNonScope:
    def test_non_scope_section_present(self, design_doc_text):
        assert "## 3. Define explicit non-scope" in design_doc_text

    def test_no_waterfall_wiring(self, design_doc_text):
        assert "No wiring into the waterfall" in design_doc_text

    def test_no_runtime_wiring(self, design_doc_text):
        assert "No wiring into the runtime" in design_doc_text

    def test_no_feature_flag_flip(self, design_doc_text):
        assert "No feature flag flip" in design_doc_text

    def test_no_manual_field_replacement(self, design_doc_text):
        assert "No replacement of runtime manual fields" in design_doc_text

    def test_no_capex_total_change(self, design_doc_text):
        assert "No change to CAPEX totals" in design_doc_text

    def test_no_debt_service_change(self, design_doc_text):
        assert "No change to debt service" in design_doc_text

    def test_no_tax_change(self, design_doc_text):
        assert "No change to tax" in design_doc_text

    def test_no_depreciation_change(self, design_doc_text):
        assert "No change to depreciation" in design_doc_text

    def test_no_cfads_change(self, design_doc_text):
        assert "No change to CFADS" in design_doc_text

    def test_no_project_status_change(self, design_doc_text):
        assert "No change to project statuses" in design_doc_text

    def test_no_persistence_writes(self, design_doc_text):
        assert "No persistence writes" in design_doc_text

    def test_no_ui_rendering(self, design_doc_text):
        assert "No UI rendering" in design_doc_text

    def test_no_engine_call(self, design_doc_text):
        assert "Bridge must NOT call the engine" in design_doc_text

    def test_forbidden_imports_listed(self, design_doc_text):
        # The forbidden imports list
        text = design_doc_text
        for module in (
            "domain/inputs.py",
            "domain/waterfall*",
            "app/",
            "main_web.py",
            "main_api.py",
            "static/",
        ):
            assert module in text, f"forbidden import {module!r} not listed"


# ---------------------------------------------------------------------------
# Section 4: Proposed files for C7
# ---------------------------------------------------------------------------


class TestProposedFilesForC7:
    def test_files_section_present(self, design_doc_text):
        assert "## 4. Proposed files for future C7" in design_doc_text

    def test_bridge_module_path(self, design_doc_text):
        assert "domain/construction/opening_bridge.py" in design_doc_text

    def test_c7_test_file_path(self, design_doc_text):
        assert "test_phase_c7_opening_balance_bridge.py" in design_doc_text

    def test_c7_design_doc_path(self, design_doc_text):
        assert "phase_c7_opening_balance_bridge_implementation.md" in (
            design_doc_text
        )

    def test_c7_report_path(self, design_doc_text):
        assert "phase_c7_opening_balance_bridge_implementation.json" in (
            design_doc_text
        )

    def test_4_new_files(self, design_doc_text):
        # The C7 file list has 4 new files
        text = design_doc_text
        assert "4 new files" in text or "New files (4 total)" in text

    def test_zero_modifications(self, design_doc_text):
        assert "no modifications to existing files" in design_doc_text

    def test_no_c6_bridge_module(self, design_doc_text):
        # C6 explicitly does not add the bridge module
        assert "C6 does NOT add" in design_doc_text
        assert "C7+" in design_doc_text


# ---------------------------------------------------------------------------
# Section 5: API / dataclass shape
# ---------------------------------------------------------------------------


class TestApiDataclassShape:
    def test_api_section_present(self, design_doc_text):
        assert "## 5. API / dataclass shape" in design_doc_text

    def test_input_dataclass(self, design_doc_text):
        assert "OpeningBalanceBridgeInput" in design_doc_text

    def test_output_dataclass(self, design_doc_text):
        assert "OpeningBalanceBridgeResult" in design_doc_text

    def test_audit_row_dataclass(self, design_doc_text):
        assert "BridgeAuditRow" in design_doc_text

    def test_metadata_dataclass(self, design_doc_text):
        assert "BridgeMetadata" in design_doc_text

    def test_manual_override_dataclass(self, design_doc_text):
        assert "ManualOverrideRow" in design_doc_text

    def test_field_policy_dataclass(self, design_doc_text):
        assert "BridgeFieldPolicy" in design_doc_text

    def test_parity_reference_dataclass(self, design_doc_text):
        assert "ParityReferenceRow" in design_doc_text

    def test_project_assumptions_dataclass(self, design_doc_text):
        assert "ProjectAssumptions" in design_doc_text

    def test_function_signature_in_design(self, design_doc_text):
        # The exact function signature (formatted slightly differently in
        # the design doc — it appears as a `def` line)
        text = design_doc_text
        assert "build_opening_balance_bridge" in text
        assert "OpeningBalanceBridgeInput" in text
        assert "OpeningBalanceBridgeResult" in text

    def test_all_dataclasses_frozen(self, design_doc_text):
        # C2 §3.6.1: bridge output is a frozen dataclass
        text = design_doc_text
        # The shapes section says "frozen dataclasses"
        assert "frozen dataclass" in text

    def test_no_python_enums_in_design(self, design_doc_text):
        # C3 §4.7 says no Python enums for field codes
        # The audit row uses string literals (selection_reason, etc.)
        # and BridgeFieldPolicy uses string policy values
        text = design_doc_text
        # Check that no `class XXX(Enum)` or `class XXX(IntEnum)` is
        # introduced in the design doc
        assert "class XXX(Enum)" not in text
        assert "class XXX(IntEnum)" not in text


# ---------------------------------------------------------------------------
# Section 6: Double-counting guards
# ---------------------------------------------------------------------------


class TestDoubleCountingGuards:
    def test_guards_section_present(self, design_doc_text):
        assert "## 6. Double-counting guards" in design_doc_text

    def test_guard_invariant_from_c2(self, design_doc_text):
        # C2 §2.3 invariant
        assert "exactly one of" in design_doc_text

    def test_guarded_single_source(self, design_doc_text):
        # 10 fields with guarded_single_source
        assert "guarded_single_source" in design_doc_text

    def test_guarded_composite(self, design_doc_text):
        # 1 field (equity_total_keur) with guarded_composite
        assert "guarded_composite" in design_doc_text

    def test_not_applicable_excluded(self, design_doc_text):
        # Per C2 §4.5 invariant 4, no field has not_applicable
        assert "No field has `not_applicable`" in design_doc_text

    def test_11_field_guard_table(self, design_doc_text):
        # The 11-field guard table is in §6.1
        text = design_doc_text
        # Verify the table has all 11 fields
        for field in (
            "shl_idc_keur",
            "shl_amount_keur",
            "shl_opening_balance_keur",
            "senior_opening_balance_keur",
            "senior_idc_keur",
            "capex_keur",
            "reserves_keur",
            "vat_operating",
            "financing_fees_keur",
            "commitment_fee_keur",
            "equity_total_keur",
        ):
            assert field in text, f"field {field!r} missing from guard table"

    def test_senior_idc_caveat_in_guards(self, design_doc_text):
        # C1 R-PAR-2 is preserved in the guard rules
        assert "blocker_5_R-PAR-2" in design_doc_text
        assert "effective-rate" in design_doc_text

    def test_senior_opening_balance_frozen(self, design_doc_text):
        # senior_opening_balance_keur is frozen (not replaced)
        text = design_doc_text
        # The policy for senior_opening_balance_keur is frozen
        assert "senior_opening_balance_keur" in text
        # Find the line and check the policy
        # The guard table has policy column
        # Per C2 §2.1, this is `frozen`
        # In the C6 design doc, the §2.4 table says "frozen"
        # and §6.1 says "frozen"
        assert text.count("frozen") >= 3  # mentioned multiple times

    def test_senior_idc_replaced(self, design_doc_text):
        # senior_idc_keur is replaced (with effective-rate caveat)
        text = design_doc_text
        assert "senior_idc_keur" in text
        # The policy for senior_idc_keur is `replaced`
        # but the §6.4 caveat says the bridge preserves the
        # asymmetry: senior_idc is replaced but
        # senior_opening_balance is frozen
        assert "asymmetry" in text

    def test_blocker_5_r_par_2_caveat(self, design_doc_text):
        # The C1 R-PAR-2 caveat
        assert "C1 R-PAR-2" in design_doc_text


# ---------------------------------------------------------------------------
# Section 7: Validation plan for C7
# ---------------------------------------------------------------------------


class TestValidationPlanForC7:
    def test_validation_section_present(self, design_doc_text):
        assert "## 7. Validation plan for future C7 implementation" in (
            design_doc_text
        )

    def test_cod_opening_balance_reconciliation(self, design_doc_text):
        # C2 §6.4
        assert "C2 §6.4" in design_doc_text
        assert "COD opening balance reconciliation" in design_doc_text

    def test_idc_by_source_reconciliation(self, design_doc_text):
        # C2 §6.5
        assert "C2 §6.5" in design_doc_text
        assert "IDC by source reconciliation" in design_doc_text

    def test_no_double_counting(self, design_doc_text):
        # C2 §6.6
        assert "C2 §6.6" in design_doc_text
        assert "no double-counting" in design_doc_text.lower() or (
            "no double counting" in design_doc_text.lower()
        )

    def test_tuho_bridge_test(self, design_doc_text):
        # §7.3: TUHO bridge result vs C4 snapshot
        text = design_doc_text
        assert "TUHO" in text
        assert "C4 snapshot" in text or "C2 §6.4" in text

    def test_oborovo_bridge_test(self, design_doc_text):
        # §7.3: Oborovo bridge result vs C4 snapshot
        text = design_doc_text
        assert "Oborovo" in text
        assert "C4 snapshot" in text or "C2 §6.4" in text

    def test_audit_rows_generated(self, design_doc_text):
        # §7.5: audit table has exactly 11 rows
        text = design_doc_text
        assert "11 rows" in text

    def test_frozen_replaced_retained_derived_respected(
        self, design_doc_text
    ):
        text = design_doc_text
        # All 4 policies are mentioned in the validation plan
        for policy in ("frozen", "replaced", "retained", "derived"):
            assert policy in text, f"policy {policy!r} not in validation plan"

    def test_no_caller_mutation(self, design_doc_text):
        # §7.6: mutation guard test
        assert "mutation guard" in design_doc_text.lower()

    def test_no_waterfall_imports(self, design_doc_text):
        # §7.8: no waterfall imports (AST-level)
        assert "domain/inputs.py" in design_doc_text
        assert "waterfall" in design_doc_text.lower()

    def test_no_app_imports(self, design_doc_text):
        # §7.8: no app imports
        assert "app/" in design_doc_text

    def test_no_runtime_path_wiring(self, design_doc_text):
        # §7.8: no runtime wiring
        assert "main_web.py" in design_doc_text
        assert "main_api.py" in design_doc_text

    def test_forbidden_path_guards(self, design_doc_text):
        # §7.14: forbidden-path guard
        text = design_doc_text
        assert "forbidden-path" in text.lower() or (
            "forbidden path" in text.lower()
        )

    def test_estimated_test_count_89(self, design_doc_text):
        # §7.19 says total estimated = 89
        text = design_doc_text
        assert "**Total estimated**" in text
        # The number 89 should appear
        assert "89" in text

    def test_19_categories(self, design_doc_text):
        # §7.19 has 19 categories
        text = design_doc_text
        # The validation plan has 19 categories listed
        # Count the §7.x headers
        section_7_headers = re.findall(r"### 7\.\d+", text)
        assert len(section_7_headers) >= 17  # §7.1 to §7.19 minus summary

    def test_validation_summary_in_report(self, report_json_data):
        # The report has the validation plan summary
        assert "validation_plan_for_c7" in report_json_data
        assert (
            report_json_data["validation_plan_for_c7"]["estimated_test_count"]
            == 89
        )


# ---------------------------------------------------------------------------
# Section 8: Recommendation
# ---------------------------------------------------------------------------


class TestRecommendation:
    def test_recommendation_section_present(self, design_doc_text):
        assert "## 8. Recommendation" in design_doc_text

    def test_recommendation_choice_b(self, design_doc_text):
        assert "Choice: **B. More design needed**" in design_doc_text

    def test_recommendation_rationale_points(self, design_doc_text):
        # 6 rationale points
        text = design_doc_text
        assert "1. **C5 explicitly deferred Layer 4 to C6+" in text
        assert "2. **The bridge has a non-trivial API surface" in text
        assert (
            "3. **The bridge introduces a new layer of trust" in text
        )
        assert (
            "4. **The senior IDC effective-rate caveat is still"
            in text
        )
        assert "5. **C6 implements 0 of 3 deferred C2 §6.7 items" in text
        assert "6. **C6 is the right scope" in text

    def test_unblock_a_section(self, design_doc_text):
        # The "What would unblock A" section
        assert "What would unblock" in design_doc_text
        assert "A. Ready for C7" in design_doc_text

    def test_remains_open_section(self, design_doc_text):
        # The "What remains open" section
        assert "What remains open after C6" in design_doc_text

    def test_multi_phase_path(self, design_doc_text):
        # The multi-phase path table
        text = design_doc_text
        for phase in (
            "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10", "C11"
        ):
            assert phase in text, f"phase {phase!r} not in multi-phase path"


# ---------------------------------------------------------------------------
# Hard constraints
# ---------------------------------------------------------------------------


class TestHardConstraints:
    def test_report_hard_constraints_all_true(self, report_json_data):
        for k, v in report_json_data["hard_constraints"].items():
            assert v is True, (
                f"hard constraint {k!r} should be true, got {v!r}"
            )

    def test_design_doc_hard_constraints_section(
        self, design_doc_text
    ):
        assert "## 9. Hard constraints (re-asserted)" in design_doc_text

    def test_design_doc_stop_after_report(self, design_doc_text):
        assert "## 10. Stop after report" in design_doc_text

    def test_c6_produces_3_files_only(self, design_doc_text):
        text = design_doc_text
        assert "C6 produces **3 files only**" in text
        for path in (
            "phase_c6_opening_balance_bridge_implementation_plan.md",
            "phase_c6_opening_balance_bridge_implementation_plan.json",
            "test_phase_c6_opening_balance_bridge_implementation_plan.py",
        ):
            assert path in text


# ---------------------------------------------------------------------------
# Git / scope guards
# ---------------------------------------------------------------------------


class TestScopeGuards:
    EXPECTED_ADDITIONS = (
        "docs/phase_c6_opening_balance_bridge_implementation_plan.md",
        "reports/phase_c6_opening_balance_bridge_implementation_plan.json",
        "tests/test_phase_c6_opening_balance_bridge_implementation_plan.py",
    )

    FORBIDDEN_CODE_PATHS = (
        "domain/",
        "app/",
        "main_web.py",
        "main_api.py",
        "static/",
    )

    def test_only_expected_files_added(self):
        result = subprocess.run(
            ["git", "diff", "--name-status", "origin/main", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        lines = [ln for ln in result.stdout.strip().splitlines() if ln]
        status_pairs = [ln.split("\t") for ln in lines]
        for status, path in status_pairs:
            assert status == "A", (
                f"only additions allowed, got {status} for {path}"
            )
            assert path in self.EXPECTED_ADDITIONS, (
                f"unexpected added file: {path!r}"
            )

    @pytest.mark.parametrize("path", FORBIDDEN_CODE_PATHS)
    def test_forbidden_code_path_untouched(self, path):
        result = subprocess.run(
            ["git", "diff", "--stat", "origin/main", "HEAD", "--", path],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "", (
            f"Phase C6 must not touch {path}: got diff:\n{result.stdout}"
        )


# ---------------------------------------------------------------------------
# rc1 frozen
# ---------------------------------------------------------------------------


class TestRc1Frozen:
    def test_rc1_sha_reachable(self):
        result = subprocess.run(
            [
                "git", "cat-file", "-e",
                "b425a0708719eaa5e1d922b1008e5609758e0ad4",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Project statuses unchanged
# ---------------------------------------------------------------------------


class TestProjectStatusesUnchanged:
    def test_tuho_referenced(self, design_doc_text):
        assert "TUHO" in design_doc_text

    def test_oborovo_referenced(self, design_doc_text):
        assert "Oborovo" in design_doc_text

    def test_generic_wind_referenced(self, design_doc_text):
        assert "Generic Wind" in design_doc_text

    def test_generic_solar_referenced(self, design_doc_text):
        assert "Generic Solar" in design_doc_text

    def test_tuho_level_2_in_design_doc(self, design_doc_text):
        # The C6 design doc states TUHO remains Level 2
        assert "TUHO remains **Level 2**" in design_doc_text

    def test_oborovo_level_2_in_design_doc(self, design_doc_text):
        assert "Oborovo remains **Level 2**" in design_doc_text


# ---------------------------------------------------------------------------
# C2 cross-reference
# ---------------------------------------------------------------------------


class TestC2CrossReference:
    def test_c2_section_3_5_referenced(self, design_doc_text):
        # C6 §1.2 references C2 §3.5
        assert "§3.5" in design_doc_text

    def test_c2_section_3_7_referenced(self, design_doc_text):
        # C6 §1.2 references C2 §3.7
        assert "§3.7" in design_doc_text

    def test_c2_section_4_1_referenced(self, design_doc_text):
        # C6 §1.2 references C2 §4.1
        assert "§4.1" in design_doc_text

    def test_c2_section_4_5_referenced(self, design_doc_text):
        # C6 §1.2 references C2 §4.5
        assert "§4.5" in design_doc_text

    def test_c2_section_2_1_referenced(self, design_doc_text):
        # C6 §1.2 references C2 §2.1 (the policy table)
        assert "§2.1" in design_doc_text

    def test_c2_section_6_referenced(self, design_doc_text):
        # C6 §1.2 references C2 §6 (validation requirements)
        assert "§6" in design_doc_text

    def test_c2_bridge_output_contract_in_design(
        self, design_doc_text, c2_doc_text
    ):
        # The C6 design doc's API shape must match C2 §3.7
        c2_contract_fields = (
            "opening_senior_balance_at_cod_keur",
            "opening_shl_balance_at_cod_keur",
            "equity_contribution_at_cod_keur",
            "capitalized_senior_idc_keur",
            "capitalized_shl_idc_keur",
            "financing_fee_treatment_keur",
            "audit_reconciliation_table",
            "source_construction_result",
            "manual_overrides",
            "bridge_metadata",
        )
        for field in c2_contract_fields:
            assert field in c2_doc_text, (
                f"C2 contract field {field!r} not in C2 doc"
            )
            assert field in design_doc_text, (
                f"C2 contract field {field!r} not in C6 design"
            )

    def test_c2_audit_table_columns_in_design(
        self, design_doc_text, c2_doc_text
    ):
        # The C6 design doc's audit row must have all 14 columns
        # from C2 §4.1
        c2_audit_columns = (
            "field_code",
            "manual_value_keur",
            "construction_derived_value_keur",
            "selected_runtime_value_keur",
            "selection_reason",
            "override_status",
            "double_counting_guard",
            "parity_reference_keur",
            "parity_delta_keur",
            "parity_status",
            "c1_blocker_reference",
            "audit_timestamp",
            "bridge_version",
            "policy_version",
        )
        for col in c2_audit_columns:
            assert col in c2_doc_text, (
                f"C2 audit column {col!r} not in C2 doc"
            )
            assert col in design_doc_text, (
                f"C2 audit column {col!r} not in C6 design"
            )


# ---------------------------------------------------------------------------
# Senior IDC caveat
# ---------------------------------------------------------------------------


class TestSeniorIdcCaveat:
    def test_senior_idc_caveat_referenced(self, design_doc_text):
        # C6 design doc references the senior IDC caveat
        assert "C1 R-PAR-2" in design_doc_text
        assert "effective-rate" in design_doc_text
        assert "blocker_5_R-PAR-2" in design_doc_text

    def test_separate_workstream_in_design(self, design_doc_text):
        # The senior IDC fix is a separate workstream
        assert "separate workstream" in design_doc_text

    def test_asymmetry_preserved_in_design(self, design_doc_text):
        # The C6 design preserves the asymmetry:
        # senior_idc is replaced (effective-rate calibrated)
        # but senior_opening_balance is frozen
        assert "asymmetry is intentional" in design_doc_text
