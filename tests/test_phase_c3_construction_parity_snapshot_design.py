"""Phase C3 - Construction Period Parity Snapshot Design tests.

This is a DESIGN phase. It must:
- Add exactly 3 new files: 1 design doc, 1 report JSON, 1 test file
- NOT change any code, runtime, schema, persistence, feature flag,
  CAPEX formula, debt, tax, depreciation, IDC, or project status
- NOT change rc1 SHA
- NOT change any existing tests
- Define a construction parity framework with 3 layers:
  funding, IDC, opening balance
- Specify TUHO and Oborovo golden datasets
- Document the senior IDC effective-rate caveat in 2 places
- Address C1 blockers 3, 4 (C1 blocker 5 deferred)
- Address 7 of 8 C2 §6.7 readiness items at design level
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
    / "docs" / "phase_c3_construction_parity_snapshot_design.md"
)
REPORT_JSON = (
    REPO_ROOT
    / "reports" / "phase_c3_construction_parity_snapshot_design.json"
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
# 10 required sections
# ---------------------------------------------------------------------------


REQUIRED_SECTIONS = [
    "## 1. What construction parity means",
    "## 2. TUHO construction parity dataset",
    "## 3. Oborovo construction parity dataset",
    "## 4. Required snapshot fields",
    "## 5. Funding parity",
    "## 6. IDC parity",
    "## 7. Opening balance parity",
    "## 8. Golden dataset structure",
    "## 9. CI / governance requirements",
    "## 10. Recommendation",
]


class TestRequiredSectionsPresent:
    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_section_present(self, design_doc_text, section):
        assert section in design_doc_text, (
            f"required section missing: {section!r}"
        )


# ---------------------------------------------------------------------------
# Section 1: What construction parity means
# ---------------------------------------------------------------------------


class TestWhatConstructionParityMeans:
    def test_operating_parity_baseline(self, design_doc_text):
        idx = design_doc_text.find("## 1.")
        end = design_doc_text.find("## 2.")
        window = design_doc_text[idx:end]
        # Should mention the operating parity baseline
        assert (
            "operating period" in window.lower()
        ), "operating period baseline not stated"
        # Reference phase9 or phase23N file paths
        for ref in ("phase9", "phase23n", "phase23p"):
            assert ref in window.lower(), f"reference {ref!r} missing"

    def test_three_layer_concentric(self, design_doc_text):
        idx = design_doc_text.find("## 1.")
        end = design_doc_text.find("## 2.")
        window = design_doc_text[idx:end]
        # The 3 layers
        for layer in ("Funding parity", "IDC parity", "Opening balance parity"):
            assert layer in window, f"layer {layer!r} missing"

    def test_boundary_parity_definition(self, design_doc_text):
        idx = design_doc_text.find("## 1.")
        end = design_doc_text.find("## 2.")
        window = design_doc_text[idx:end].lower()
        # Boundary parity is the key concept
        assert (
            "boundary parity" in window
        ), "boundary parity definition missing"

    def test_excludes_runtime_contract(self, design_doc_text):
        idx = design_doc_text.find("## 1.")
        end = design_doc_text.find("## 2.")
        window_lower = design_doc_text[idx:end].lower()
        # C3 is not a runtime contract (subsection 1.4)
        assert (
            "not a runtime contract" in window_lower
            or (
                "not" in window_lower
                and "runtime contract" in window_lower
            )
        ), "runtime contract exclusion not stated"

    def test_flag_state_documented(self, design_doc_text):
        idx = design_doc_text.find("## 1.")
        end = design_doc_text.find("## 2.")
        window = design_doc_text[idx:end]
        # The flag must remain default-off
        assert (
            "use_construction_schedule_engine" in window
            or "default-off" in window
            or "default off" in window.lower()
        ), "flag state not documented"


# ---------------------------------------------------------------------------
# Section 2: TUHO dataset
# ---------------------------------------------------------------------------


class TestTuhoDataset:
    REQUIRED_TUHO_FIELDS = [
        "72,994.450",
        "500.000",
        "29,135.176",
        "43,359.274",
        "3,568.688",
        "1,519.564",
        "44,878.838",
        "32,703.864",
        "2028-06-30",
        "2029-12-30",
        "18",
    ]

    @pytest.mark.parametrize("field", REQUIRED_TUHO_FIELDS)
    def test_tuho_reference_present(self, design_doc_text, field):
        idx = design_doc_text.find("## 2.")
        end = design_doc_text.find("## 3.")
        window = design_doc_text[idx:end]
        assert field in window, f"TUHO reference {field!r} missing"

    def test_tuho_monthly_uses_listed(self, design_doc_text):
        idx = design_doc_text.find("## 2.")
        end = design_doc_text.find("## 3.")
        window = design_doc_text[idx:end]
        # TUHO_MONTHLY_USES_KEUR reference
        assert (
            "TUHO_MONTHLY_USES_KEUR" in window
        ), "TUHO_MONTHLY_USES_KEUR reference missing in section 2"
        # 18 months and 24,226 referenced
        assert "18 monthly" in window or "18" in window, "18 months not stated"
        # The first monthly value is documented (in section 2.1 reference list)
        # But might be in section 4 — check there too
        idx4 = design_doc_text.find("## 4.")
        end4 = design_doc_text.find("## 5.")
        window4 = design_doc_text[idx4:end4]
        assert "24,226.729" in window4, "TUHO first monthly value not in section 4"

    def test_tuho_18_months(self, design_doc_text):
        idx = design_doc_text.find("## 2.")
        end = design_doc_text.find("## 3.")
        window = design_doc_text[idx:end]
        # 18 months
        assert "18 monthly" in window or "18 cells" in window or "m1..m18" in window

    def test_tuho_field_count_207(self, design_doc_text):
        idx = design_doc_text.find("## 2.")
        end = design_doc_text.find("## 3.")
        window = design_doc_text[idx:end]
        # 207 fields
        assert (
            "207 fields" in window
            or "field count" in window.lower()
            or "18\u00d711" in window
        ), "TUHO field count 207 not stated"

    def test_tuho_calendar_dates(self, design_doc_text):
        idx = design_doc_text.find("## 2.")
        end = design_doc_text.find("## 3.")
        window = design_doc_text[idx:end]
        # Calendar dates
        assert "2028-06-30" in window
        assert "2029-12-30" in window

    def test_tuho_tolerance_policy(self, design_doc_text):
        idx = design_doc_text.find("## 2.")
        end = design_doc_text.find("## 3.")
        window = design_doc_text[idx:end]
        # Tolerance policy
        assert (
            "\u00b10.001" in window
            or "0.001" in window
            or "tolerance" in window.lower()
        ), "tolerance policy not stated"

    def test_tuho_opening_balance_identity(self, design_doc_text):
        idx = design_doc_text.find("## 2.")
        end = design_doc_text.find("## 3.")
        window = design_doc_text[idx:end]
        # Opening senior = senior_draw + senior_idc
        # 43,359.274 + 1,519.564 = 44,878.838
        assert "44,878.838" in window
        # Opening SHL = shl_draw + shl_idc
        # 29,135.176 + 3,568.688 = 32,703.864
        assert "32,703.864" in window


# ---------------------------------------------------------------------------
# Section 3: Oborovo dataset
# ---------------------------------------------------------------------------


class TestOborovoDataset:
    REQUIRED_OBOROVO_FIELDS = [
        "57,973.041",
        "500.000",
        "14,620.774",
        "42,852.267",
        "1,169.662",
        "1,086.032",
        "43,938.299",
        "15,790.436",
        "2029-06-29",
        "2030-06-29",
        "12",
    ]

    @pytest.mark.parametrize("field", REQUIRED_OBOROVO_FIELDS)
    def test_oborovo_reference_present(self, design_doc_text, field):
        idx = design_doc_text.find("## 3.")
        end = design_doc_text.find("## 4.")
        window = design_doc_text[idx:end]
        assert field in window, f"Oborovo reference {field!r} missing"

    def test_oborovo_monthly_uses_listed(self, design_doc_text):
        idx = design_doc_text.find("## 3.")
        end = design_doc_text.find("## 4.")
        window = design_doc_text[idx:end]
        # OBOROVO_MONTHLY_USES_KEUR reference
        assert (
            "OBOROVO_MONTHLY_USES_KEUR" in window
        ), "OBOROVO_MONTHLY_USES_KEUR reference missing in section 3"
        # 12 months
        assert "12 monthly" in window or "12" in window, "12 months not stated"
        # The first monthly value is documented in section 4
        idx4 = design_doc_text.find("## 4.")
        end4 = design_doc_text.find("## 5.")
        window4 = design_doc_text[idx4:end4]
        # Oborovo is referenced in section 4 (the field code table covers both)
        assert (
            "oborovo" in window4.lower()
        ), "Oborovo field codes not in section 4"

    def test_oborovo_12_months(self, design_doc_text):
        idx = design_doc_text.find("## 3.")
        end = design_doc_text.find("## 4.")
        window = design_doc_text[idx:end]
        # 12 months
        assert (
            "12 monthly" in window
            or "12 cells" in window
            or "m1..m12" in window
        )

    def test_oborovo_field_count_142(self, design_doc_text):
        idx = design_doc_text.find("## 3.")
        end = design_doc_text.find("## 4.")
        window = design_doc_text[idx:end]
        # 142 fields
        assert (
            "142 fields" in window
            or "field count" in window.lower()
            or "12\u00d711" in window
        ), "Oborovo field count 142 not stated"

    def test_oborovo_calendar_dates(self, design_doc_text):
        idx = design_doc_text.find("## 3.")
        end = design_doc_text.find("## 4.")
        window = design_doc_text[idx:end]
        # Calendar dates
        assert "2029-06-29" in window
        assert "2030-06-29" in window

    def test_oborovo_tolerance_policy(self, design_doc_text):
        idx = design_doc_text.find("## 3.")
        end = design_doc_text.find("## 4.")
        window = design_doc_text[idx:end]
        # Tolerance policy
        assert (
            "\u00b10.001" in window
            or "0.001" in window
            or "tolerance" in window.lower()
        )

    def test_oborovo_opening_balance_identity(self, design_doc_text):
        idx = design_doc_text.find("## 3.")
        end = design_doc_text.find("## 4.")
        window = design_doc_text[idx:end]
        # Opening senior = senior_draw + senior_idc
        # 42,852.267 + 1,086.032 = 43,938.299
        assert "43,938.299" in window
        # Opening SHL = shl_draw + shl_idc
        # 14,620.774 + 1,169.662 = 15,790.436
        assert "15,790.436" in window

    def test_difference_vs_tuho_table(self, design_doc_text):
        idx = design_doc_text.find("## 3.")
        end = design_doc_text.find("## 4.")
        window = design_doc_text[idx:end]
        # The difference table
        assert (
            "Difference vs TUHO" in window
            or "vs TUHO" in window
            or "TUHO | Oborovo" in window
        ), "TUHO vs Oborovo difference table missing"


# ---------------------------------------------------------------------------
# Section 4: Field code schema
# ---------------------------------------------------------------------------


class TestFieldCodeSchema:
    def test_code_format_documented(self, design_doc_text):
        idx = design_doc_text.find("## 4.")
        end = design_doc_text.find("## 5.")
        window = design_doc_text[idx:end]
        # <project>_<category>_<subcategory>_<field>
        assert "<project>" in window or "project_code" in window

    def test_category_values_documented(self, design_doc_text):
        idx = design_doc_text.find("## 4.")
        end = design_doc_text.find("## 5.")
        window = design_doc_text[idx:end]
        # mflow, cum, tot, cal, ob, meta
        for cat in ("mflow", "cum", "tot", "cal", "ob", "meta"):
            assert cat in window, f"category {cat!r} missing"

    def test_subcategory_values_documented(self, design_doc_text):
        idx = design_doc_text.find("## 4.")
        end = design_doc_text.find("## 5.")
        window = design_doc_text[idx:end]
        # use, eq, shl, sen, idc
        for sub in ("use", "eq", "shl", "sen", "idc"):
            assert sub in window, f"subcategory {sub!r} missing"

    def test_canonical_field_count(self, design_doc_text):
        idx = design_doc_text.find("## 4.")
        end = design_doc_text.find("## 5.")
        window = design_doc_text[idx:end]
        # 349 total (207 + 142)
        assert "349 fields" in window or "349" in window

    def test_not_python_enums(self, design_doc_text):
        idx = design_doc_text.find("## 4.")
        end = design_doc_text.find("## 5.")
        window_lower = design_doc_text[idx:end].lower()
        # C3 does not introduce Python enums
        assert (
            "not" in window_lower and "python enum" in window_lower
        ), "Python enum exclusion not stated"

    def test_schema_version_c3_1_0(self, design_doc_text):
        # Schema version can be in section 4 or section 8 (the dataset structure)
        idx4 = design_doc_text.find("## 4.")
        end4 = design_doc_text.find("## 5.")
        window4 = design_doc_text[idx4:end4]
        idx8 = design_doc_text.find("## 8.")
        end8 = design_doc_text.find("## 9.")
        window8 = design_doc_text[idx8:end8]
        assert (
            "C3-1.0" in window4 or "C3-1.0" in window8
        ), "C3-1.0 not in section 4 or 8"


# ---------------------------------------------------------------------------
# Section 5: Funding parity
# ---------------------------------------------------------------------------


class TestFundingParity:
    def test_funding_identity_documented(self, design_doc_text):
        idx = design_doc_text.find("## 5.")
        end = design_doc_text.find("## 6.")
        window = design_doc_text[idx:end]
        # The identity: sum(monthly_uses) == total_uses
        assert "sum(monthly_uses" in window or "monthly uses" in window.lower()
        assert "total_uses" in window or "total uses" in window.lower()

    def test_funding_test_designed_not_implemented(self, design_doc_text):
        idx = design_doc_text.find("## 5.")
        end = design_doc_text.find("## 6.")
        window = design_doc_text[idx:end]
        # The test is designed but not implemented
        assert (
            "when implemented" in window.lower()
            or "future pytest" in window.lower()
        ), "funding test design status not stated"

    def test_funding_failure_mode_blocked(self, design_doc_text):
        idx = design_doc_text.find("## 5.")
        end = design_doc_text.find("## 6.")
        window = design_doc_text[idx:end]
        # Failure mode is BLOCKED
        assert "BLOCKED" in window, "funding failure mode not stated as BLOCKED"

    def test_funding_per_source_4_sources(self, design_doc_text):
        idx = design_doc_text.find("## 5.")
        end = design_doc_text.find("## 6.")
        window = design_doc_text[idx:end]
        # 4 sources
        for src in ("equity", "shl", "junior", "senior"):
            assert src in window.lower(), f"source {src!r} missing"


# ---------------------------------------------------------------------------
# Section 6: IDC parity
# ---------------------------------------------------------------------------


class TestIdcParity:
    def test_senior_idc_caveat_in_docstring(self, design_doc_text):
        idx = design_doc_text.find("## 6.")
        end = design_doc_text.find("## 7.")
        window = design_doc_text[idx:end]
        # The caveat must be documented
        assert (
            "effective rate" in window.lower()
            or "effective-rate" in window.lower()
        ), "effective rate caveat missing in IDC section"
        # And reference C1 R-PAR-2
        assert "R-PAR-2" in window, "C1 R-PAR-2 reference missing"
        # And the docstring requirement
        assert (
            "docstring" in window.lower()
        ), "docstring requirement missing"

    def test_shl_idc_convention_b(self, design_doc_text):
        idx = design_doc_text.find("## 6.")
        end = design_doc_text.find("## 7.")
        window = design_doc_text[idx:end]
        # SHL uses Convention B from C2
        assert (
            "Convention B" in window
            or "full-source elapsed compound" in window
        ), "SHL IDC Convention B reference missing"
        # C2 reference
        assert "C2" in window, "C2 reference missing"

    def test_senior_idc_target_values(self, design_doc_text):
        idx = design_doc_text.find("## 6.")
        end = design_doc_text.find("## 7.")
        window = design_doc_text[idx:end]
        # Senior IDC targets
        assert "1,519.564" in window
        assert "1,086.032" in window
        # And total SHL IDC
        assert "3,568.688" in window
        assert "1,169.662" in window

    def test_idc_identity_documented(self, design_doc_text):
        idx = design_doc_text.find("## 6.")
        end = design_doc_text.find("## 7.")
        window = design_doc_text[idx:end]
        # Identity
        assert (
            "sum(shl_idc" in window
            or "sum(" in window
        ), "IDC identity not stated"

    def test_idc_failure_mode_blocked(self, design_doc_text):
        idx = design_doc_text.find("## 6.")
        end = design_doc_text.find("## 7.")
        window = design_doc_text[idx:end]
        # Failure mode is BLOCKED
        assert "BLOCKED" in window, "IDC failure mode not BLOCKED"


# ---------------------------------------------------------------------------
# Section 7: Opening balance parity
# ---------------------------------------------------------------------------


class TestOpeningBalanceParity:
    def test_senior_opening_caveat(self, design_doc_text):
        idx = design_doc_text.find("## 7.")
        end = design_doc_text.find("## 8.")
        window = design_doc_text[idx:end]
        # Senior opening balance caveat
        assert (
            "effective rate" in window.lower()
            or "effective-rate" in window.lower()
        ), "senior opening balance caveat missing"
        # C2 §2.1 reference
        assert "C2 \u00a72.1" in window or "C2" in window, "C2 reference missing"

    def test_shl_opening_balance_identity(self, design_doc_text):
        idx = design_doc_text.find("## 7.")
        end = design_doc_text.find("## 8.")
        window = design_doc_text[idx:end]
        # SHL opening = principal + IDC
        assert (
            "principal + IDC" in window
            or "total_shl_draw + total_shl_idc" in window
            or "principal + shl_idc" in window.lower()
        ), "SHL opening balance identity not stated"

    def test_three_opening_fields(self, design_doc_text):
        idx = design_doc_text.find("## 7.")
        end = design_doc_text.find("## 8.")
        window = design_doc_text[idx:end]
        # Three opening balance fields
        for field in (
            "opening_senior_balance_keur",
            "opening_shl_balance_keur",
            "equity_contribution_at_cod_keur",
        ):
            assert field in window, f"opening field {field!r} missing"

    def test_opening_failure_mode_blocked(self, design_doc_text):
        idx = design_doc_text.find("## 7.")
        end = design_doc_text.find("## 8.")
        window = design_doc_text[idx:end]
        # Failure mode
        assert "BLOCKED" in window, "opening failure mode not BLOCKED"


# ---------------------------------------------------------------------------
# Section 8: Golden dataset structure
# ---------------------------------------------------------------------------


class TestGoldenDataset:
    def test_dataset_path_documented(self, design_doc_text):
        idx = design_doc_text.find("## 8.")
        end = design_doc_text.find("## 9.")
        window = design_doc_text[idx:end]
        # Dataset paths
        for path in (
            "phase_c3_tuho_construction_parity_golden.json",
            "phase_c3_oborovo_construction_parity_golden.json",
        ):
            assert path in window, f"dataset path {path!r} missing"

    def test_dataset_schema_version(self, design_doc_text):
        idx = design_doc_text.find("## 8.")
        end = design_doc_text.find("## 9.")
        window = design_doc_text[idx:end]
        # Schema version
        assert "C3-1.0" in window

    def test_dataset_not_test_implementation(self, design_doc_text):
        idx = design_doc_text.find("## 8.")
        end = design_doc_text.find("## 9.")
        window_lower = design_doc_text[idx:end].lower()
        # C3 deliverable is dataset, not test
        assert (
            "c4+" in window_lower or "next phase" in window_lower
        ), "dataset vs test distinction not stated"

    def test_dataset_checked_into_repo(self, design_doc_text):
        # The checked-in status is in section 9.1 (CI governance)
        idx = design_doc_text.find("## 9.")
        end = design_doc_text.find("## 10.")
        window_lower = design_doc_text[idx:end].lower()
        assert (
            "checked" in window_lower
            and "repo" in window_lower
        ), "dataset checked-in status not stated in section 9"

    def test_dataset_json_schema(self, design_doc_text):
        idx = design_doc_text.find("## 8.")
        end = design_doc_text.find("## 9.")
        window = design_doc_text[idx:end]
        # JSON example fields
        for f in (
            "schema_version",
            "field_count",
            "tolerance_policy",
            "totals",
            "opening_balances",
            "monthly_grid",
            "caveats",
        ):
            assert f in window, f"JSON field {f!r} missing"


# ---------------------------------------------------------------------------
# Section 9: CI / governance
# ---------------------------------------------------------------------------


class TestCiGovernance:
    def test_c3_designs_workflow(self, design_doc_text):
        idx = design_doc_text.find("## 9.")
        end = design_doc_text.find("## 10.")
        window = design_doc_text[idx:end]
        # C3 designs, does not implement
        assert (
            "does not include" in window.lower()
            or "not include" in window.lower()
            or "future ci workflow" in window.lower()
        ), "C3 design vs implementation boundary not stated"

    def test_schema_freeze_rule(self, design_doc_text):
        idx = design_doc_text.find("## 9.")
        end = design_doc_text.find("## 10.")
        window_lower = design_doc_text[idx:end].lower()
        # Schema change requires C-phase
        assert (
            "schema freeze" in window_lower
            or "schema change" in window_lower
        ), "schema freeze rule not stated"

    def test_audit_trail(self, design_doc_text):
        idx = design_doc_text.find("## 9.")
        end = design_doc_text.find("## 10.")
        window_lower = design_doc_text[idx:end].lower()
        # Audit trail items
        assert (
            "audit trail" in window_lower
        ), "audit trail not stated"
        # Must include dataset, test, sections or similar
        assert "dataset" in window_lower, "dataset missing"
        assert (
            "design test" in window_lower
            or "test" in window_lower
        ), "test missing"
        # Must include "10 sections" reference
        assert (
            "10 sections" in window_lower
            or "section" in window_lower
        ), "sections reference missing"

    def test_dataset_authority(self, design_doc_text):
        idx = design_doc_text.find("## 9.")
        end = design_doc_text.find("## 10.")
        window = design_doc_text[idx:end]
        # Dataset authority
        assert (
            "authoritative" in window.lower()
        ), "dataset authority not stated"


# ---------------------------------------------------------------------------
# Section 10: Recommendation
# ---------------------------------------------------------------------------


class TestRecommendation:
    def _get_section_10(self, design_doc_text):
        idx = design_doc_text.find("## 10. Recommendation")
        # Find next ## section
        end = design_doc_text.find("## 1", idx + 4)
        if end < 0:
            end = len(design_doc_text)
        return design_doc_text[idx:end]

    def test_recommendation_is_b(self, design_doc_text):
        window = self._get_section_10(design_doc_text)
        # The choice is B
        assert (
            "Choice:" in window and "B." in window
        ), "Recommendation should be B"

    def test_recommendation_rationale_at_least_5(self, design_doc_text):
        window = self._get_section_10(design_doc_text)
        rationale_idx = window.find("Rationale")
        assert rationale_idx > 0, "Rationale section missing"
        rationale = window[rationale_idx:]
        numbered = re.findall(r"^\d+\.\s+", rationale, re.MULTILINE)
        assert len(numbered) >= 5, (
            f"rationale should have at least 5 points, got {len(numbered)}"
        )

    def test_recommendation_explains_blockers_remaining(self, design_doc_text):
        window = self._get_section_10(design_doc_text).lower()
        # Blockers deferred to C4+ must be mentioned
        for blocker in ("blocker 5", "senior idc", "effective rate", "c4+", "c5+"):
            assert blocker in window, f"remaining blocker {blocker!r} not mentioned"

    def test_suggests_c4_scope(self, design_doc_text):
        window = self._get_section_10(design_doc_text)
        # C4 scope
        assert (
            "C4" in window
            and ("parity test" in window.lower() or "scaffolding" in window.lower())
        ), "C4 scope suggestion missing"


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
        assert "no implementation" in text, "no-implementation marker missing"

    def test_stop_after_report_marker(self, design_doc_text):
        assert "Stop after report" in design_doc_text


# ---------------------------------------------------------------------------
# C1 blocker addresses
# ---------------------------------------------------------------------------


class TestC1BlockerAddresses:
    def test_addresses_blocker_3_layer_5(self, design_doc_text):
        # Blocker 3 is Layer 5
        assert (
            "Blocker 3" in design_doc_text
            or "blocker 3" in design_doc_text
        ), "C1 blocker 3 not addressed"

    def test_addresses_blocker_4_parity_snapshot(self, design_doc_text):
        # Blocker 4 is construction-period parity snapshot
        assert (
            "Blocker 4" in design_doc_text
            or "blocker 4" in design_doc_text
        ), "C1 blocker 4 not addressed"

    def test_defers_blocker_5_senior_idc(self, design_doc_text):
        # Blocker 5 is senior IDC — deferred
        assert (
            "Blocker 5" in design_doc_text
            or "blocker 5" in design_doc_text
        ), "C1 blocker 5 not mentioned"


# ---------------------------------------------------------------------------
# C2 readiness checklist addresses
# ---------------------------------------------------------------------------


class TestC2ReadinessChecklist:
    CHECKLIST_ITEMS = [
        "TUHO construction-period parity snapshot",
        "Oborovo construction-period parity snapshot",
        "Manual-vs-derived reconciliation",
        "COD opening balance reconciliation",
        "IDC by source reconciliation",
        "No double-counting",
        "senior IDC effective-rate caveat",
    ]

    @pytest.mark.parametrize("item", CHECKLIST_ITEMS)
    def test_checklist_item_addressed(self, design_doc_text, item):
        idx = design_doc_text.find("C3 readiness checklist status")
        end = design_doc_text.find("## 11", idx) if idx > 0 else len(design_doc_text)
        if end < 0:
            end = len(design_doc_text)
        if idx < 0:
            window = design_doc_text
        else:
            window = design_doc_text[idx:end]
        assert item in window, f"checklist item {item!r} not addressed"


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
            "deferred_c1_blockers",
            "hard_constraints",
            "parity_framework",
            "tuho_dataset",
            "oborovo_dataset",
            "field_code_convention",
            "canonical_field_count",
            "funding_parity",
            "idc_parity",
            "opening_balance_parity",
            "golden_dataset",
            "ci_governance",
            "c3_readiness_checklist_status",
            "multi_phase_path",
            "recommendation",
        ):
            assert key in report_json_data, f"key {key!r} missing"

    def test_addresses_c1_blockers_3_and_4(self, report_json_data):
        assert 3 in report_json_data["addresses_c1_blockers"]
        assert 4 in report_json_data["addresses_c1_blockers"]

    def test_defers_c1_blocker_5(self, report_json_data):
        assert 5 in report_json_data["deferred_c1_blockers"]

    def test_hard_constraints_all_true(self, report_json_data):
        for k, v in report_json_data["hard_constraints"].items():
            assert v is True, (
                f"hard constraint {k!r} should be true, got {v!r}"
            )

    def test_recommendation_is_b(self, report_json_data):
        assert report_json_data["recommendation"]["choice"].startswith("B")

    def test_three_parity_layers(self, report_json_data):
        layers = report_json_data["parity_framework"]["three_layers"]
        assert len(layers) == 3
        layer_names = {l["name"] for l in layers}
        assert "funding_parity" in layer_names
        assert "idc_parity" in layer_names
        assert "opening_balance_parity" in layer_names

    def test_canonical_field_count(self, report_json_data):
        cc = report_json_data["canonical_field_count"]
        assert cc["tuho"] == 207
        assert cc["oborovo"] == 142
        assert cc["total"] == 349

    def test_tuho_dataset_in_json(self, report_json_data):
        tuho = report_json_data["tuho_dataset"]
        assert tuho["field_count"] == 207
        assert tuho["construction_months"] == 18
        assert tuho["totals_keur"]["total_uses"] == 72994.450
        assert tuho["totals_keur"]["total_shl_idc"] == 3568.688
        assert tuho["totals_keur"]["total_senior_idc"] == 1519.564
        assert tuho["opening_balances_keur"]["opening_senior_balance"] == 44878.838
        assert tuho["opening_balances_keur"]["opening_shl_balance"] == 32703.864

    def test_oborovo_dataset_in_json(self, report_json_data):
        obo = report_json_data["oborovo_dataset"]
        assert obo["field_count"] == 142
        assert obo["construction_months"] == 12
        assert obo["totals_keur"]["total_uses"] == 57973.041
        assert obo["totals_keur"]["total_shl_idc"] == 1169.662
        assert obo["totals_keur"]["total_senior_idc"] == 1086.032
        assert obo["opening_balances_keur"]["opening_senior_balance"] == 43938.299
        assert obo["opening_balances_keur"]["opening_shl_balance"] == 15790.436

    def test_senior_idc_caveat_in_json(self, report_json_data):
        # Caveat in both tuho + oborovo
        for ds_name in ("tuho_dataset", "oborovo_dataset"):
            ds = report_json_data[ds_name]
            assert (
                ds["caveats"]["senior_idc_effective_rate_caveat_applies"] is True
            ), f"senior IDC caveat missing in {ds_name}"
        # And in idc_parity
        assert (
            report_json_data["idc_parity"]["senior_idc_convention"]
            == "Effective-rate calibrated (C1 R-PAR-2 caveat)"
        )

    def test_field_code_convention_in_json(self, report_json_data):
        fcc = report_json_data["field_code_convention"]
        assert fcc["schema_version"] == "C3-1.0"
        assert fcc["not_python_enums"] is True
        # Has 4 projects, 6 categories
        assert len(fcc["project_values"]) >= 4
        assert len(fcc["category_values"]) >= 6

    def test_checklist_status_in_json(self, report_json_data):
        chk = report_json_data["c3_readiness_checklist_status"]
        assert chk["items_designed"] == 7
        assert chk["items_implemented"] == 0
        assert chk["items_total"] == 8

    def test_multi_phase_path_in_json(self, report_json_data):
        path = report_json_data["multi_phase_path"]
        # C1 and C2 are merged
        c1 = next(p for p in path if p["phase"] == "C1")
        c2 = next(p for p in path if p["phase"] == "C2")
        c3 = next(p for p in path if p["phase"] == "C3")
        assert c1["status"] == "merged"
        assert c2["status"] == "merged"
        assert c3["status"] == "DRAFT"
        # And the SHA references
        assert c1["sha"] == "5fccc3a"
        assert c2["sha"] == "59f9e3d"


# ---------------------------------------------------------------------------
# Git / scope guards
# ---------------------------------------------------------------------------


class TestScopeGuards:
    EXPECTED_ADDITIONS = (
        "docs/phase_c3_construction_parity_snapshot_design.md",
        "reports/phase_c3_construction_parity_snapshot_design.json",
        "tests/test_phase_c3_construction_parity_snapshot_design.py",
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
        """Locate the Phase C3 squash-merge commit on origin/main.

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
            if len(parts) == 2 and parts[1].startswith("Phase C3:"):
                c_shas.append(parts[0])
        if not c_shas:
            r = subprocess.run(
                ["git", "log", "--format=%H %s", "origin/main"],
                cwd=str(REPO_ROOT), capture_output=True, text=True,
            )
            for ln in r.stdout.splitlines():
                parts = ln.split(" ", 1)
                if len(parts) == 2 and parts[1].startswith("Phase C3:"):
                    c_shas.append(parts[0])
        assert c_shas, "could not locate Phase C3 commit on origin/main"
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
            f"Phase C3 must not touch {path}: got diff:\n{result.stdout}"
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
