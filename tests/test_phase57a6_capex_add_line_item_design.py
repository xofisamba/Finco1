"""Phase 57A-6: CAPEX add-line-item design tests.

These tests pin the design contract from
``docs/phase57a6_capex_add_line_item_design.md``.
They do NOT make any runtime / template / persistence
changes.

The contract is:

1. The user can add a line under C.01..C.16.
2. The next available code is assigned.
3. The numeric impact is limited to category
   subtotal, Hard CAPEX Total, Total CAPEX.
4. P&L, Balance Sheet, Cash Flow, IDC, funding
   drawdown, tax engine, depreciation, C.17 / C.18
   are NOT affected.
5. The persistence approach is defined (Option C
   hybrid recommended).
6. Schema / migration is explicitly out of scope
   for 57A-6.
7. No runtime implementation in 57A-6.
8. G20 / R99 / R102 governance guards do not
   block CAPEX editing.
9. rc1 (``b425a0708719eaa5e1d922b1008e5609758e0ad4``)
   is frozen.

Type: docs / report / test-only. Auto-merge eligible.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = (
    REPO_ROOT
    / "docs"
    / "phase57a6_capex_add_line_item_design.md"
)
REPORT_PATH = (
    REPO_ROOT
    / "reports"
    / "phase57a6_capex_add_line_item_design.json"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def doc_text() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def report() -> dict:
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Files exist
# ---------------------------------------------------------------------------


class TestFilesExist:
    def test_design_doc_exists(self):
        assert DOC_PATH.is_file()

    def test_report_json_exists(self):
        assert REPORT_PATH.is_file()


# ---------------------------------------------------------------------------
# 1. Add-line UX flow
# ---------------------------------------------------------------------------


class TestAddLineUXFlow:
    def test_discovery_in_design(self, doc_text):
        # The design must describe the discovery of the
        # "+ Add line" button.
        assert "+ Add line" in doc_text

    def test_click_flow_in_design(self, doc_text):
        # The design must describe what happens when
        # the user clicks the button (read parent code,
        # find next available sub-line code, insert
        # row).
        for keyword in [
            "data-capex-add-line",
            "next available",
            "C.01.04",
        ]:
            assert keyword in doc_text, (
                f"Design must mention {keyword!r}."
            )

    def test_edit_and_save_in_design(self, doc_text):
        # The design must describe the edit and save
        # steps.
        for keyword in [
            "edit",
            "save",
            "input_field_template",
        ]:
            assert keyword.lower() in doc_text.lower(), (
                f"Design must mention {keyword!r}."
            )


# ---------------------------------------------------------------------------
# 2. Numeric impact
# ---------------------------------------------------------------------------


class TestNumericImpact:
    @pytest.mark.parametrize(
        "impacted",
        [
            "category's sub-line",
            "category subtotal",
            "hard capex total",
            "total capex",
        ],
    )
    def test_impacted_items_documented(self, doc_text, impacted):
        assert impacted in doc_text.lower(), (
            f"Impacted item {impacted!r} must be "
            f"documented in the design."
        )

    @pytest.mark.parametrize(
        "not_impacted",
        [
            "p&l",
            "balance sheet",
            "cash flow",
            "idc",
            "funding drawdown",
            "tax engine",
            "depreciation",
        ],
    )
    def test_not_impacted_items_documented(
        self, doc_text, report, not_impacted,
    ):
        # The design must list each non-impacted
        # mechanism.
        assert not_impacted in doc_text.lower(), (
            f"Non-impacted mechanism {not_impacted!r} "
            f"must be documented in the design."
        )

    def test_report_numeric_impact_matrix(self, report):
        # The report must have a numeric_impact dict
        # where each value starts with "yes" or "no".
        ni = report["numeric_impact"]
        for key, val in ni.items():
            assert (
                isinstance(val, str)
                and (
                    val.lower().startswith("yes")
                    or val.lower().startswith("no")
                )
            ), (
                f"numeric_impact.{key} must start with "
                f"yes or no, got {val!r}."
            )
        # Spot-check key items. The keys in the
        # report use snake_case with category codes.
        for key in [
            "category_subtotal",
            "hard_capex_total_c01_c16",
            "total_capex_c01_c18",
        ]:
            assert ni.get(key, "").lower().startswith("yes"), (
                f"numeric_impact.{key} must be 'yes', "
                f"got {ni.get(key)!r}."
            )
        for key in [
            "p_and_l",
            "idc",
            "c17_c18_rows",
        ]:
            assert ni.get(key, "").lower().startswith("no"), (
                f"numeric_impact.{key} must be 'no', "
                f"got {ni.get(key)!r}."
            )


# ---------------------------------------------------------------------------
# 3. Persistence approach
# ---------------------------------------------------------------------------


class TestPersistenceApproach:
    def test_persistence_section_in_design(self, doc_text):
        assert "persistence" in doc_text.lower()

    def test_option_c_recommended(self, doc_text, report):
        # Option C (hybrid) is recommended.
        pattern = re.compile(
            r"option[\s_-]*c.*(recommended|hybrid)",
            re.IGNORECASE | re.DOTALL,
        )
        assert pattern.search(doc_text), (
            "Design must recommend Option C "
            "(hybrid) for persistence."
        )
        assert report["persistence_approach"]["recommended"] == (
            "option_c_hybrid"
        )

    def test_capex_sub_lines_table_documented(
        self, doc_text, report,
    ):
        assert "capex_sub_lines" in doc_text
        assert "capex_sub_lines" in (
            report["persistence_approach"]["table_schema"]["name"]
        )

    def test_no_change_to_capex_structure(self, doc_text):
        # The design must state that CapexStructure
        # shape is not changed.
        pattern = re.compile(
            r"does not change.*CapexStructure",
            re.IGNORECASE | re.DOTALL,
        )
        assert pattern.search(doc_text), (
            "Design must state that CapexStructure "
            "shape is not changed by Option C."
        )


# ---------------------------------------------------------------------------
# 4. Stop-and-document
# ---------------------------------------------------------------------------


class TestStopAndDocument:
    def test_out_of_scope_section(self, doc_text):
        assert "out of scope" in doc_text.lower()

    def test_migration_out_of_scope(self, doc_text):
        # The design must state that the migration
        # and persistence-layer changes are out of
        # scope for 57A-6.
        pattern = re.compile(
            r"out of scope.*57a-?6|57a-?6.*out of scope",
            re.IGNORECASE | re.DOTALL,
        )
        assert pattern.search(doc_text), (
            "Design must state that migration is out "
            "of scope for 57A-6."
        )

    def test_no_runtime_implementation_in_57a6(
        self, doc_text, report,
    ):
        # The design must say 57A-6 is design only
        # and that no runtime change happens in 57A-6.
        # The doc uses phrases like "57A-6 PR is
        # design only" and "no runtime change".
        pattern = re.compile(
            r"design[\s_-]*only|no[\s_-]*runtime",
            re.IGNORECASE,
        )
        assert pattern.search(doc_text), (
            "Design must say 57A-6 is design only / "
            "no runtime change."
        )
        assert "no_runtime_implementation" in (
            report["out_of_scope"]
        )


# ---------------------------------------------------------------------------
# 5. G20 / R99 / R102 governance guards
# ---------------------------------------------------------------------------


class TestGovernanceGuards:
    def test_g20_r99_r102_in_design(self, doc_text):
        for guard in ["G20", "R99", "R102"]:
            assert guard in doc_text


# ---------------------------------------------------------------------------
# 6. Hard no-go
# ---------------------------------------------------------------------------


class TestHardNoGo:
    @pytest.mark.parametrize(
        "no_go_keyword",
        [
            "idc calculation",
            "construction funding",
            "g20",
            "tailwind",
            "portfolio",
            "schema",
            "backend keys visible",
        ],
    )
    def test_no_go_in_doc(self, doc_text, no_go_keyword):
        assert no_go_keyword in doc_text.lower(), (
            f"Hard no-go {no_go_keyword!r} must be in "
            f"the design."
        )

    def test_no_go_in_report(self, report):
        joined = " ".join(report["hard_no_go"])
        for canonical in [
            "no_financial_formula",
            "no_idc_calculation",
            "no_construction_funding",
            "no_g20_r99_r102",
            "no_tailwind_alpine",
            "no_portfolio",
            "no_schema",
            "no_backend_keys_visible",
            "rc1_frozen",
        ]:
            assert canonical in joined, (
                f"Canonical no-go {canonical!r} must be "
                f"in report's hard_no_go list."
            )


# ---------------------------------------------------------------------------
# 7. rc1 frozen
# ---------------------------------------------------------------------------


class TestRc1Frozen:
    def test_rc1_sha_pinned_in_doc(self, doc_text):
        assert (
            "b425a0708719eaa5e1d922b1008e5609758e0ad4"
            in doc_text
        )

    def test_rc1_sha_pinned_in_report(self, report):
        assert (
            report["rc1_frozen_sha"]
            == "b425a0708719eaa5e1d922b1008e5609758e0ad4"
        )


# ---------------------------------------------------------------------------
# 8. No-go copy
# ---------------------------------------------------------------------------


class TestNoGoCopy:
    @pytest.mark.parametrize(
        "forbidden",
        [
            "validated",
            "guaranteed",
            "100% accurate",
            "production-ready",
            "saas-ready",
        ],
    )
    def test_no_forbidden_claims(self, doc_text, forbidden):
        pattern = re.compile(
            r"\b" + re.escape(forbidden) + r"\b",
            re.IGNORECASE,
        )
        matches = pattern.findall(doc_text)
        assert not matches, (
            f"Forbidden term {forbidden!r} must not "
            f"appear in the design doc. Found "
            f"{len(matches)}."
        )
