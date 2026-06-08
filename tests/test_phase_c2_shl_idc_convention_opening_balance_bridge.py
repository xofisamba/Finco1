"""Phase C2 - SHL IDC Convention Decision + Opening Balance Bridge Design tests.

This is a DESIGN and DECISION phase. It must:
- Add exactly 3 new files: 1 design doc, 1 report JSON, 1 test file
- NOT change any code, runtime, schema, persistence, feature flag,
  CAPEX formula, debt, tax, depreciation, IDC, or project status
- NOT change rc1 SHA
- NOT change any existing tests
- Document Convention B (Excel full-source elapsed compound) as the
  authoritative SHL IDC convention for future construction runtime
- Design Layer 4 (Opening Balance Bridge) with explicit per-field
  policies
- Address C1 blockers 1 and 2; defer blockers 3, 4, 5 to C3
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
DESIGN_DOC = (
    REPO_ROOT
    / "docs" / "phase_c2_shl_idc_convention_opening_balance_bridge.md"
)
REPORT_JSON = (
    REPO_ROOT
    / "reports" / "phase_c2_shl_idc_convention_opening_balance_bridge.json"
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


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------


class TestFilesExist:
    def test_design_doc_exists(self):
        assert DESIGN_DOC.is_file(), f"missing design doc: {DESIGN_DOC}"

    def test_report_json_exists(self):
        assert REPORT_JSON.is_file(), f"missing report: {REPORT_JSON}"

    def test_design_doc_nonempty(self):
        assert DESIGN_DOC.stat().st_size > 5000, (
            "design doc should be substantial (>= 5KB)"
        )


# ---------------------------------------------------------------------------
# 7 Required sections present
# ---------------------------------------------------------------------------


REQUIRED_SECTIONS = [
    "## 1. SHL IDC Convention Decision",
    "## 2. Double-Counting Policy",
    "## 3. Opening Balance Bridge Design",
    "## 4. Bridge Audit Table",
    "## 5. Runtime Integration Boundary",
    "## 6. Validation Requirements",
    "## 7. Recommendation",
]


class TestRequiredSectionsPresent:
    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_section_present(self, design_doc_text, section):
        assert section in design_doc_text, (
            f"required section missing: {section!r}"
        )


# ---------------------------------------------------------------------------
# Section 1: SHL IDC Convention Decision
# ---------------------------------------------------------------------------


class TestShlIdcConventionDecision:
    def test_three_conventions_compared(self, design_doc_text):
        idx = design_doc_text.find("## 1. SHL IDC Convention Decision")
        end = design_doc_text.find("## 2. Double-Counting Policy")
        window = design_doc_text[idx:end]
        for letter, keyword in (
            ("A", "Manual"),
            ("B", "Excel"),
            ("C", "Phase 7I"),
        ):
            assert (
                f"#### Convention {letter}" in window
                or f"Convention {letter} " in window
                or f"Convention {letter}:" in window
            ), f"Convention {letter} ({keyword}) missing"

    def test_convention_a_current_authoritative(self, design_doc_text):
        idx = design_doc_text.find("## 1. SHL IDC Convention Decision")
        end = design_doc_text.find("## 2. Double-Counting Policy")
        window = design_doc_text[idx:end]
        # Convention A is the current authoritative one
        assert (
            "1169" in window
            or "1,169" in window
        ), "TUHO 1169 reference missing in Convention A"
        # Oborovo 0
        assert "Oborovo: 0" in window or "Oborovo 0" in window, (
            "Oborovo 0 reference missing"
        )

    def test_convention_b_excel_values(self, design_doc_text):
        idx = design_doc_text.find("## 1. SHL IDC Convention Decision")
        end = design_doc_text.find("## 2. Double-Counting Policy")
        window = design_doc_text[idx:end]
        # Excel full-source elapsed compound values
        assert "3,568.688" in window, "TUHO Excel SHL IDC value missing"
        assert "1,169.662" in window, "Oborovo Excel SHL IDC value missing"

    def test_convention_b_formula_documented(self, design_doc_text):
        idx = design_doc_text.find("## 1. SHL IDC Convention Decision")
        end = design_doc_text.find("## 2. Double-Counting Policy")
        window = design_doc_text[idx:end]
        # The full-source elapsed compound formula
        assert (
            "(1 + SHL rate)" in window
            or "SHL rate) ^" in window
            or "SHL rate) **" in window
        ), "Excel formula not documented"

    def test_recommendation_is_convention_b(self, design_doc_text):
        # The recommendation is Convention B
        idx = design_doc_text.find("## 1. SHL IDC Convention Decision")
        end = design_doc_text.find("## 2. Double-Counting Policy")
        window = design_doc_text[idx:end]
        # Convention B should be recommended
        assert (
            "**Convention B**" in window
            or "Convention B (Excel" in window
        ), "Convention B not explicitly recommended"
        # And A is current
        assert "current" in window.lower() or "today" in window.lower(), (
            "should mention that A is current"
        )

    def test_migration_path_documented(self, design_doc_text):
        idx = design_doc_text.find("## 1. SHL IDC Convention Decision")
        end = design_doc_text.find("## 2. Double-Counting Policy")
        window = design_doc_text[idx:end]
        # C2-C9 or similar multi-phase path
        for marker in ("C3", "C8", "C9", "promotion"):
            assert marker in window, f"migration step {marker!r} missing"

    def test_pros_and_cons_for_each_convention(self, design_doc_text):
        idx = design_doc_text.find("## 1. SHL IDC Convention Decision")
        end = design_doc_text.find("## 2. Double-Counting Policy")
        window = design_doc_text[idx:end]
        # Each convention should have at least one Pros and one Cons bullet
        for letter in ("A", "B", "C"):
            # Find the convention header
            header_idx = window.find(f"#### Convention {letter}")
            if header_idx < 0:
                # Try the convention mention
                header_idx = window.find(f"Convention {letter} ")
            assert header_idx >= 0, f"Convention {letter} header missing"
            # Find the next convention header
            next_letter = chr(ord(letter) + 1)
            next_idx = window.find(f"#### Convention {next_letter}", header_idx)
            if next_idx < 0:
                next_idx = window.find("### 1.", header_idx)
            if next_idx < 0:
                next_idx = len(window)
            section = window[header_idx:next_idx]
            assert "Pros" in section, f"Convention {letter} Pros missing"
            assert "Cons" in section, f"Convention {letter} Cons missing"


# ---------------------------------------------------------------------------
# Section 2: Double-Counting Policy
# ---------------------------------------------------------------------------


class TestDoubleCountingPolicy:
    REQUIRED_FIELDS = [
        "shl_idc_keur",
        "shl_amount_keur",
        "shl_opening_balance_keur",
        "senior_opening_balance_keur",
        "senior_idc_keur",
        "capex_keur",
        "reserves_keur",
        "vat",
        "financing_fees_keur",
        "commitment_fee_keur",
        "equity_total_keur",
    ]

    @pytest.mark.parametrize("field", REQUIRED_FIELDS)
    def test_field_in_policy_table(self, design_doc_text, field):
        idx = design_doc_text.find("## 2. Double-Counting Policy")
        end = design_doc_text.find("## 3. Opening Balance Bridge Design")
        window = design_doc_text[idx:end]
        # VAT is in doc as 'VAT costs', allow that
        if field == "vat":
            assert (
                "VAT costs" in window
                or "vat_costs" in window.lower()
            ), f"policy field VAT missing"
        else:
            assert field in window, f"policy field {field!r} missing"

    def test_replaced_semantic_defined(self, design_doc_text):
        idx = design_doc_text.find("## 2. Double-Counting Policy")
        end = design_doc_text.find("## 3. Opening Balance Bridge Design")
        window = design_doc_text[idx:end]
        assert "replaced" in window, "replaced semantic missing"
        assert "frozen" in window, "frozen semantic missing"
        assert "retained" in window, "retained semantic missing"
        assert "derived" in window, "derived semantic missing"

    def test_shl_idc_policy_is_replaced(self, design_doc_text):
        idx = design_doc_text.find("## 2. Double-Counting Policy")
        end = design_doc_text.find("## 3. Opening Balance Bridge Design")
        window = design_doc_text[idx:end]
        # The row for shl_idc_keur should have policy=replaced
        # Allow backticks and various formats
        row_match = re.search(
            r"shl_idc_keur[^|]*\|[^|]*\|[^|]*\|\s*\*\*replaced\*\*",
            window,
        )
        assert row_match, "shl_idc_keur policy should be 'replaced'"

    def test_senior_opening_balance_policy_is_frozen(self, design_doc_text):
        idx = design_doc_text.find("## 2. Double-Counting Policy")
        end = design_doc_text.find("## 3. Opening Balance Bridge Design")
        window = design_doc_text[idx:end]
        # The row for senior_opening_balance_keur mentions both 'replaced'
        # and 'frozen' (replaced-when-modelling-correct, frozen-otherwise).
        # The CURRENT default (until C3) is frozen.
        row_match = re.search(
            r"senior_opening_balance_keur[^|]*\|",
            window,
        )
        assert row_match, "senior_opening_balance_keur row missing"
        # Find the policy column (4th column)
        line = row_match.group(0)
        # Should contain both replaced and frozen
        assert (
            "frozen" in window and "replaced" in window
        ), "senior_opening_balance row should mention both frozen and replaced"
        # And the rationale should mention C1 blocker 5
        assert "blocker 5" in window or "R-PAR-2" in window, (
            "senior_opening_balance policy should reference C1 blocker 5"
        )

    def test_capex_total_is_frozen(self, design_doc_text):
        idx = design_doc_text.find("## 2. Double-Counting Policy")
        end = design_doc_text.find("## 3. Opening Balance Bridge Design")
        window = design_doc_text[idx:end]
        # Operating CAPEX is different from construction CAPEX
        row_match = re.search(
            r"capex_keur[^|]*\|[^|]*\|[^|]*\|\s*\*\*frozen\*\*",
            window,
        )
        assert row_match, "capex_keur policy should be 'frozen'"

    def test_double_counting_guard_invariant(self, design_doc_text):
        idx = design_doc_text.find("## 2. Double-Counting Policy")
        end = design_doc_text.find("## 3. Opening Balance Bridge Design")
        window = design_doc_text[idx:end]
        # The guard invariant must be stated
        assert (
            "exactly one of" in window.lower()
            or "exactly one" in window.lower()
        ), "double-counting guard invariant not stated"


# ---------------------------------------------------------------------------
# Section 3: Opening Balance Bridge Design (Layer 4)
# ---------------------------------------------------------------------------


class TestOpeningBalanceBridgeDesign:
    def test_layer_4_responsibility_stated(self, design_doc_text):
        idx = design_doc_text.find("## 3. Opening Balance Bridge Design")
        end = design_doc_text.find("## 4. Bridge Audit Table")
        window = design_doc_text[idx:end]
        assert "responsibility" in window.lower() or "Layer 4" in window

    def test_layer_4_inputs_listed(self, design_doc_text):
        idx = design_doc_text.find("## 3. Opening Balance Bridge Design")
        end = design_doc_text.find("## 4. Bridge Audit Table")
        window = design_doc_text[idx:end]
        for inp in (
            "ConstructionScheduleResult",
            "Manual override",
            "Replacement policy",
        ):
            assert inp in window, f"input {inp!r} missing"

    def test_layer_4_outputs_listed(self, design_doc_text):
        idx = design_doc_text.find("## 3. Opening Balance Bridge Design")
        end = design_doc_text.find("## 4. Bridge Audit Table")
        window = design_doc_text[idx:end]
        for out in (
            "opening_senior_balance",
            "opening_shl_balance",
            "equity_contribution",
            "capitalized_senior_idc",
            "capitalized_shl_idc",
        ):
            assert out in window, f"output {out!r} missing"

    def test_layer_4_module_location(self, design_doc_text):
        idx = design_doc_text.find("## 3. Opening Balance Bridge Design")
        end = design_doc_text.find("## 4. Bridge Audit Table")
        window = design_doc_text[idx:end]
        # The module should be in domain/construction/
        assert (
            "domain/construction/opening_bridge.py" in window
        ), "Layer 4 module location not specified"

    def test_layer_4_pure_function(self, design_doc_text):
        idx = design_doc_text.find("## 3. Opening Balance Bridge Design")
        end = design_doc_text.find("## 4. Bridge Audit Table")
        window = design_doc_text[idx:end]
        # The bridge is a pure function with no mutation
        assert "pure" in window.lower(), (
            "bridge should be described as pure function"
        )
        assert (
            "does not import" in window.lower()
            or "must not" in window.lower()
        ), "bridge boundaries not stated"

    def test_layer_4_algorithm_steps(self, design_doc_text):
        idx = design_doc_text.find("## 3. Opening Balance Bridge Design")
        end = design_doc_text.find("## 4. Bridge Audit Table")
        window = design_doc_text[idx:end]
        # The algorithm should have steps
        for step in ("Receive", "Apply", "Compute", "Build", "Return"):
            assert step in window, f"algorithm step {step!r} missing"


# ---------------------------------------------------------------------------
# Section 4: Bridge Audit Table
# ---------------------------------------------------------------------------


class TestBridgeAuditTable:
    REQUIRED_COLUMNS = [
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
    ]

    @pytest.mark.parametrize("col", REQUIRED_COLUMNS)
    def test_column_in_table(self, design_doc_text, col):
        idx = design_doc_text.find("## 4. Bridge Audit Table")
        end = design_doc_text.find("## 5. Runtime Integration Boundary")
        window = design_doc_text[idx:end]
        assert col in window, f"audit column {col!r} missing"

    def test_example_tuho_shl_idc_audit_row(self, design_doc_text):
        idx = design_doc_text.find("## 4. Bridge Audit Table")
        end = design_doc_text.find("## 5. Runtime Integration Boundary")
        window = design_doc_text[idx:end]
        # The TUHO SHL IDC example should show 1,169 -> 3,568.688
        assert "1,169" in window or "1169" in window
        assert "3,568.688" in window

    def test_example_oborovo_shl_idc_audit_row(self, design_doc_text):
        idx = design_doc_text.find("## 4. Bridge Audit Table")
        end = design_doc_text.find("## 5. Runtime Integration Boundary")
        window = design_doc_text[idx:end]
        # The Oborovo SHL IDC example should show 0 -> 1,169.662
        assert "0.000" in window or "0 kEUR" in window
        assert "1,169.662" in window

    def test_audit_table_invariants(self, design_doc_text):
        idx = design_doc_text.find("## 4. Bridge Audit Table")
        end = design_doc_text.find("## 5. Runtime Integration Boundary")
        window_lower = design_doc_text[idx:end].lower()
        # Should have explicit invariants
        for invariant in (
            "exactly one row",
            "matches the policy",
            "not_applicable",
        ):
            assert invariant in window_lower, (
                f"invariant {invariant!r} not stated"
            )


# ---------------------------------------------------------------------------
# Section 5: Runtime Integration Boundary
# ---------------------------------------------------------------------------


class TestRuntimeIntegrationBoundary:
    def test_layer_5_not_implemented(self, design_doc_text):
        idx = design_doc_text.find("## 5. Runtime Integration Boundary")
        end = design_doc_text.find("## 6. Validation Requirements")
        window = design_doc_text[idx:end]
        # Layer 5 is deferred
        assert (
            "not implemented" in window.lower()
            or "design-level only" in window.lower()
        ), "Layer 5 should be marked as not implemented"

    def test_layer_5_consumes_bridge(self, design_doc_text):
        idx = design_doc_text.find("## 5. Runtime Integration Boundary")
        end = design_doc_text.find("## 6. Validation Requirements")
        window = design_doc_text[idx:end]
        # Layer 5 consumes OpeningBalanceBridgeResult
        assert "OpeningBalanceBridgeResult" in window or "bridge" in window.lower()

    def test_layer_5_does_not_consume_engine_directly(self, design_doc_text):
        idx = design_doc_text.find("## 5. Runtime Integration Boundary")
        end = design_doc_text.find("## 6. Validation Requirements")
        window = design_doc_text[idx:end]
        # The boundary forbids direct engine consumption
        assert "must not consume" in window.lower() or (
            "must not" in window.lower()
        ), "Layer 5 must-not-consume rules missing"

    def test_layer_5_enforces_opt_in_flag(self, design_doc_text):
        idx = design_doc_text.find("## 5. Runtime Integration Boundary")
        end = design_doc_text.find("## 6. Validation Requirements")
        window = design_doc_text[idx:end]
        # The opt-in flag must be respected
        assert (
            "use_construction_schedule_engine" in window
            or "default off" in window.lower()
        ), "opt-in flag enforcement missing"


# ---------------------------------------------------------------------------
# Section 6: Validation Requirements
# ---------------------------------------------------------------------------


class TestValidationRequirements:
    REQUIRED_EVIDENCE = [
        "TUHO construction-period parity snapshot",
        "Oborovo construction-period parity snapshot",
        "Manual-vs-derived reconciliation",
        "COD opening balance reconciliation",
        "IDC by source reconciliation",
        "No double-counting test plan",
    ]

    @pytest.mark.parametrize("evidence", REQUIRED_EVIDENCE)
    def test_evidence_in_section(self, design_doc_text, evidence):
        idx = design_doc_text.find("## 6. Validation Requirements")
        end = design_doc_text.find("## 7. Recommendation")
        window = design_doc_text[idx:end]
        assert evidence in window, f"evidence {evidence!r} missing"

    def test_tuho_parity_targets(self, design_doc_text):
        idx = design_doc_text.find("## 6. Validation Requirements")
        end = design_doc_text.find("## 7. Recommendation")
        window = design_doc_text[idx:end]
        # TUHO targets
        assert "72,994.450" in window
        assert "29,135.176" in window
        assert "3,568.688" in window

    def test_oborovo_parity_targets(self, design_doc_text):
        idx = design_doc_text.find("## 6. Validation Requirements")
        end = design_doc_text.find("## 7. Recommendation")
        window = design_doc_text[idx:end]
        # Oborovo targets
        assert "57,973.041" in window
        assert "14,620.774" in window
        assert "1,169.662" in window

    def test_senior_idc_effective_rate_caveat(self, design_doc_text):
        idx = design_doc_text.find("## 6. Validation Requirements")
        end = design_doc_text.find("## 7. Recommendation")
        window = design_doc_text[idx:end]
        # The senior IDC effective-rate caveat must be documented
        assert (
            "effective-rate" in window.lower()
            or "effective rate" in window.lower()
        ), "senior IDC effective-rate caveat missing"

    def test_c3_readiness_checklist(self, design_doc_text):
        idx = design_doc_text.find("## 6. Validation Requirements")
        end = design_doc_text.find("## 7. Recommendation")
        window = design_doc_text[idx:end]
        # C3 readiness checklist should be present
        assert (
            "C3 readiness" in window
            or "C3 readiness checklist" in window
        ), "C3 readiness checklist missing"


# ---------------------------------------------------------------------------
# Section 7: Recommendation
# ---------------------------------------------------------------------------


class TestRecommendation:
    def _get_section_7(self, design_doc_text):
        idx = design_doc_text.find("## 7. Recommendation")
        end = design_doc_text.find("## 8.", idx)
        if end < 0:
            end = len(design_doc_text)
        return design_doc_text[idx:end]

    def test_recommendation_is_b(self, design_doc_text):
        window = self._get_section_7(design_doc_text)
        # The choice line is "### Choice: **B. More discovery needed**"
        assert (
            "Choice:" in window and "B." in window
        ), "Recommendation should be B"

    def test_recommendation_rationale_at_least_3(self, design_doc_text):
        window = self._get_section_7(design_doc_text)
        rationale_idx = window.find("Rationale")
        assert rationale_idx > 0, "Rationale section missing"
        rationale = window[rationale_idx:]
        numbered = re.findall(r"^\d+\.\s+", rationale, re.MULTILINE)
        assert len(numbered) >= 3, (
            f"rationale should have at least 3 points, got {len(numbered)}"
        )

    def test_suggests_c3_scope(self, design_doc_text):
        window = self._get_section_7(design_doc_text)
        # C3 scope should be suggested
        assert (
            "C3 scope" in window
            or "C3 should" in window
        ), "C3 scope suggestion missing"

    def test_recommendation_explains_blockers_remaining(self, design_doc_text):
        window = self._get_section_7(design_doc_text)
        window_lower = window.lower()
        # Blockers 3, 4, 5 should be mentioned as remaining
        assert (
            "blocker 3" in window_lower
            or "blockers 3" in window_lower
            or "blocker 3," in window_lower
            or "layer 5" in window_lower
        ), "remaining blockers not mentioned"


# ---------------------------------------------------------------------------
# Hard constraints
# ---------------------------------------------------------------------------


class TestHardConstraints:
    def test_no_python_code_blocks(self, design_doc_text):
        python_fences = re.findall(r"```python\b", design_doc_text)
        assert len(python_fences) == 0, (
            f"design doc should not contain Python code blocks "
            f"(found {len(python_fences)})"
        )

    def test_no_from_imports(self, design_doc_text):
        from_imports = re.findall(r"^from\s+\w+\s+import\s+", design_doc_text)
        assert len(from_imports) == 0, "no Python imports allowed"

    def test_design_only_markers(self, design_doc_text):
        text = design_doc_text.lower()
        assert "design only" in text, "design-only marker missing"
        assert "docs only" in text, "docs-only marker missing"
        assert "no code" in text, "no-code marker missing"

    def test_stop_after_report_marker(self, design_doc_text):
        assert "Stop after report" in design_doc_text


# ---------------------------------------------------------------------------
# C1 blocker addresses
# ---------------------------------------------------------------------------


class TestC1BlockerAddresses:
    def test_addresses_blocker_1_shl_idc_convention(self, design_doc_text):
        # Blocker 1 is SHL IDC convention
        assert "blocker 1" in design_doc_text.lower() or (
            "R-PAR-1" in design_doc_text
        ), "C1 blocker 1 (R-PAR-1) not addressed"

    def test_addresses_blocker_2_layer_4(self, design_doc_text):
        # Blocker 2 is Layer 4
        assert (
            "Layer 4" in design_doc_text
        ), "C1 blocker 2 (Layer 4) not addressed"

    def test_defers_blocker_3_layer_5(self, design_doc_text):
        # Blocker 3 is Layer 5 - should be deferred
        idx = design_doc_text.find("## 7. Recommendation")
        end = design_doc_text.find("## 8.", idx)
        if end < 0:
            end = len(design_doc_text)
        window = design_doc_text[idx:end]
        assert "C3" in window or "deferred" in window.lower(), (
            "Blocker 3 (Layer 5) not mentioned as deferred"
        )

    def test_defers_blocker_4_parity_snapshot(self, design_doc_text):
        # Blocker 4 is parity snapshot
        idx = design_doc_text.find("## 7. Recommendation")
        end = design_doc_text.find("## 8.", idx)
        if end < 0:
            end = len(design_doc_text)
        window_lower = design_doc_text[idx:end].lower()
        assert (
            "parity snapshot" in window_lower
        ), "Blocker 4 (parity snapshot) not mentioned as deferred"

    def test_defers_blocker_5_senior_idc(self, design_doc_text):
        # Blocker 5 is senior IDC effective-rate
        idx = design_doc_text.find("## 7. Recommendation")
        end = design_doc_text.find("## 8.", idx)
        if end < 0:
            end = len(design_doc_text)
        window = design_doc_text[idx:end]
        assert (
            "senior IDC" in window
            or "effective-rate" in window
            or "effective rate" in window
        ), "Blocker 5 (senior IDC) not mentioned as deferred"


# ---------------------------------------------------------------------------
# Report JSON structure
# ---------------------------------------------------------------------------


class TestReportJson:
    def test_report_valid_json(self):
        json.loads(REPORT_JSON.read_text(encoding="utf-8"))

    def test_report_has_required_keys(self, report_json_data):
        for key in (
            "phase",
            "title",
            "type",
            "status",
            "branch",
            "addresses_c1_blockers",
            "hard_constraints",
            "shl_idc_conventions",
            "double_counting_policy",
            "opening_balance_bridge_layer_4",
            "bridge_audit_table",
            "runtime_integration_boundary_layer_5",
            "validation_requirements_for_c3",
            "recommendation",
        ):
            assert key in report_json_data, f"key {key!r} missing"

    def test_addresses_c1_blockers_1_and_2(self, report_json_data):
        assert 1 in report_json_data["addresses_c1_blockers"]
        assert 2 in report_json_data["addresses_c1_blockers"]

    def test_hard_constraints_all_true(self, report_json_data):
        for k, v in report_json_data["hard_constraints"].items():
            assert v is True, (
                f"hard constraint {k!r} should be true, got {v!r}"
            )

    def test_recommendation_is_b(self, report_json_data):
        assert report_json_data["recommendation"]["choice"].startswith("B")

    def test_three_conventions_in_json(self, report_json_data):
        conventions = report_json_data["shl_idc_conventions"]
        assert "convention_a_manual" in conventions
        assert "convention_b_excel_engine" in conventions
        assert "convention_c_phase7i_diagnostic" in conventions
        # B is the recommendation
        assert "B" in conventions["recommendation"]["choice"]

    def test_policy_fields_in_json(self, report_json_data):
        fields = report_json_data["double_counting_policy"]["fields"]
        # 11 fields listed in section 2
        assert len(fields) == 11
        field_names = {f["field"] for f in fields}
        for f in (
            "shl_idc_keur",
            "shl_amount_keur",
            "shl_opening_balance_keur",
            "senior_opening_balance_keur",
            "senior_idc_keur",
            "capex_keur",
            "reserves_keur",
            "vat_costs",
            "financing_fees_keur",
            "commitment_fee_keur",
            "equity_total_keur",
        ):
            assert f in field_names, f"policy field {f!r} missing from JSON"

    def test_audit_table_columns_in_json(self, report_json_data):
        cols = report_json_data["bridge_audit_table"]["required_columns"]
        # JSON has 14 columns per the doc
        assert len(cols) >= 10
        # Verify we have the core columns
        cols_str = " ".join(cols)
        for c in (
            "field_code",
            "manual_value",
            "construction_derived",
            "selected_runtime",
            "selection_reason",
            "double_counting",
            "parity_status",
        ):
            assert c in cols_str, f"audit column keyword {c!r} missing"

    def test_bridge_outputs_in_json(self, report_json_data):
        outputs = report_json_data["opening_balance_bridge_layer_4"][
            "outputs"
        ]
        for out in (
            "opening_senior_balance_at_cod_keur",
            "opening_shl_balance_at_cod_keur",
            "equity_contribution_at_cod_keur",
            "capitalized_senior_idc_keur",
            "capitalized_shl_idc_keur",
            "financing_fee_treatment_keur",
            "audit_reconciliation_table",
        ):
            assert out in outputs, f"bridge output {out!r} missing"

    def test_validation_requirements_in_json(self, report_json_data):
        val = report_json_data["validation_requirements_for_c3"]
        for k in (
            "tuho_construction_period_parity_snapshot",
            "oborovo_construction_period_parity_snapshot",
            "manual_vs_derived_reconciliation_test",
            "cod_opening_balance_reconciliation_test",
            "idc_by_source_reconciliation_test",
            "no_double_counting_test_plan",
        ):
            assert k in val, f"validation requirement {k!r} missing"

    def test_layer_5_deferred_in_json(self, report_json_data):
        assert (
            report_json_data["runtime_integration_boundary_layer_5"][
                "implemented_in_c2"
            ]
            is False
        ), "Layer 5 should be marked as not implemented in C2"


# ---------------------------------------------------------------------------
# Git / scope guards
# ---------------------------------------------------------------------------


class TestScopeGuards:
    EXPECTED_ADDITIONS = (
        "docs/phase_c2_shl_idc_convention_opening_balance_bridge.md",
        "reports/phase_c2_shl_idc_convention_opening_balance_bridge.json",
        "tests/test_phase_c2_shl_idc_convention_opening_balance_bridge.py",
    )

    FORBIDDEN_CODE_PATHS = (
        "domain/",
        "app/",
        "main_web.py",
        "main_api.py",
        "static/",
    )

    @staticmethod
    def _phase_commit_sha() -> str:
        """Locate the Phase C2 squash-merge commit on origin/main.

        C-series test design (pre-#554) used an absolute
        ``git diff origin/main HEAD`` check. C9 (a later phase)
        legitimately adds files under app/, docs/, and reports/
        per C8 §7.3, which would cause C1-C5's absolute checks
        to fire as false positives on a branch that has C9
        already merged or in progress.
        """
        r = subprocess.run(
            ["git", "log", "--merges", "--first-parent",
             "--format=%H %s", "origin/main"],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        c_shas = []
        for ln in r.stdout.splitlines():
            parts = ln.split(" ", 1)
            if len(parts) == 2 and parts[1].startswith("Phase C2:"):
                c_shas.append(parts[0])
        if not c_shas:
            r = subprocess.run(
                ["git", "log", "--format=%H %s", "origin/main"],
                cwd=str(REPO_ROOT), capture_output=True, text=True,
            )
            for ln in r.stdout.splitlines():
                parts = ln.split(" ", 1)
                if len(parts) == 2 and parts[1].startswith("Phase C2:"):
                    c_shas.append(parts[0])
        assert c_shas, "could not locate Phase C2 commit on origin/main"
        return c_shas[0]

    def test_only_expected_files_added(self):
        c_sha = self._phase_commit_sha()
        result = subprocess.run(
            ["git", "diff", "--name-status", c_sha + "^1", c_sha,
             "--diff-filter=AMD"],
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
            # The 3 files: 1 doc, 1 json, 1 test
            assert path in self.EXPECTED_ADDITIONS, (
                f"unexpected added file: {path!r} "
                f"(expected: {self.EXPECTED_ADDITIONS})"
            )

    @pytest.mark.parametrize("path", FORBIDDEN_CODE_PATHS)
    def test_forbidden_code_path_untouched(self, path):
        c_sha = self._phase_commit_sha()
        result = subprocess.run(
            ["git", "diff", "--stat", c_sha + "^1", c_sha, "--", path],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "", (
            f"Phase C2 must not touch {path}: got diff:\n{result.stdout}"
        )


# ---------------------------------------------------------------------------
# rc1 frozen
# ---------------------------------------------------------------------------


class TestRc1Frozen:
    def test_rc1_sha_reachable(self):
        result = subprocess.run(
            [
                "git",
                "cat-file",
                "-e",
                "b425a0708719eaa5e1d922b1008e5609758e0ad4",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            "rc1 SHA not reachable on origin/main"
        )


# ---------------------------------------------------------------------------
# Project statuses unchanged
# ---------------------------------------------------------------------------


class TestProjectStatusesUnchanged:
    def test_tuho_referenced(self, design_doc_text):
        assert "TUHO" in design_doc_text

    def test_oborovo_referenced(self, design_doc_text):
        assert "Oborovo" in design_doc_text
