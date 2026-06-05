"""Phase 57A-2: CAPEX 2.0 design characterization tests.

These tests pin the design contract from
``docs/phase57a2_capex_2_design_characterization.md``.
They do NOT make any runtime / template changes.

The contract is:

1. The active CAPEX template is ``sheet_capex.html``
   (post-57A-3 single-sheet).
2. ``sheet_capex_detail.html`` is a deprecated alias
   that is not linked from ``workspace_shell.html``.
3. Backend keys (snake_case) are NEVER visible to the
   user. They are preserved in ``data-capex-code``
   attributes.
4. Visible codes follow the Excel CAPEX model
   (C.01..C.18 with sub-lines).
5. Editable rows: C.01..C.16 sub-line amount (in user
   project mode). Read-only: C.17, C.18, all subtotals,
   all totals.
6. Add-line-item UX is designed but persistence is out
   of scope.
7. Future model inputs (cost/MW, contingency, VAT, WHT,
   depreciation, payment schedule, utilisation) are
   documented in the design but not wired.
8. G20 / R99 / R102 governance guards do not block
   CAPEX editing.
9. rc1 (``b425a0708719eaa5e1d922b1008e5609758e0ad4``)
   is frozen.
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
    / "phase57a2_capex_2_design_characterization.md"
)
REPORT_PATH = (
    REPO_ROOT
    / "reports"
    / "phase57a2_capex_2_design_characterization.json"
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
        assert DOC_PATH.is_file(), (
            "Design doc must exist at "
            f"{DOC_PATH.relative_to(REPO_ROOT)}"
        )

    def test_report_json_exists(self):
        assert REPORT_PATH.is_file(), (
            "Report JSON must exist at "
            f"{REPORT_PATH.relative_to(REPO_ROOT)}"
        )


# ---------------------------------------------------------------------------
# 1. Single active CAPEX template
# ---------------------------------------------------------------------------


class TestSingleActiveCapexTemplate:
    def test_active_template_is_sheet_capex(self, doc_text):
        assert "app/templates/partials/sheet_capex.html" in doc_text

    def test_no_workspace_shell_link_to_detail_alias(
        self, doc_text, report,
    ):
        # The design must state that the deprecated alias
        # is NOT linked from workspace_shell.html.
        assert (
            "sheet_capex_detail.html"
            in doc_text
        )
        # Verify the design states the alias is not
        # linked. The doc uses 'not linked from the
        # workspace shell' (with optional article).
        pattern = re.compile(
            r"not\s+linked\s+from\s+the\s+workspace\s+shell",
            re.IGNORECASE,
        )
        assert pattern.search(doc_text), (
            "Design must state that the deprecated alias "
            "is not linked from the workspace shell."
        )

    def test_report_documents_active_and_deprecated(
        self, report,
    ):
        assert (
            report["current_active_template"]
            == "app/templates/partials/sheet_capex.html"
        )
        assert (
            report["current_deprecated_template"]
            == "app/templates/partials/sheet_capex_detail.html"
        )


# ---------------------------------------------------------------------------
# 2. Backend keys are hidden
# ---------------------------------------------------------------------------


class TestBackendKeysHidden:
    @pytest.mark.parametrize(
        "backend_key",
        [
            "lease_tax",
            "epc_contract",
            "project_rights",
            "production_units",
            "epc_other",
            "project_acquisition",
            "ops_prep",
            "construction_mgmt_a",
            "construction_mgmt_b",
            "commissioning",
            "audit_legal",
            "insurances",
            "contingencies",
            "taxes",
        ],
    )
    def test_backend_key_in_mapping_table(
        self, report, backend_key,
    ):
        # Each backend key must have a visible Excel-style
        # code mapping in the report.
        assert backend_key in report["visible_business_codes"], (
            f"Backend key {backend_key!r} must be mapped to "
            f"an Excel-style code in the report."
        )
        code = report["visible_business_codes"][backend_key]
        assert re.match(r"^C\.\d{2}\.\d{2}$", code), (
            f"Visible code for {backend_key!r} must follow "
            f"the C.NN.NN pattern. Got: {code!r}."
        )

    def test_design_states_backend_keys_never_visible(
        self, doc_text,
    ):
        assert "NEVER visible" in doc_text
        assert "data-capex-code" in doc_text


# ---------------------------------------------------------------------------
# 3. Editable vs read-only
# ---------------------------------------------------------------------------


class TestEditableVsReadOnly:
    def test_c01_to_c16_editable_in_user_project_mode(
        self, doc_text,
    ):
        # The design must say C.01..C.16 sub-line amount
        # is editable in user project mode.
        pattern = re.compile(
            r"C\.01\.\.C\.16.*editable",
            re.IGNORECASE | re.DOTALL,
        )
        assert pattern.search(doc_text), (
            "Design must state that C.01..C.16 sub-line "
            "amount is editable in user project mode."
        )

    def test_c17_c18_readonly(self, doc_text):
        assert "C.17" in doc_text
        assert "C.18" in doc_text
        assert "data_financing" in doc_text
        # Both C.17 and C.18 are read-only.
        assert re.search(
            r"C\.17.*read-only",
            doc_text,
            re.IGNORECASE,
        )
        assert re.search(
            r"C\.18.*read-only",
            doc_text,
            re.IGNORECASE,
        )

    def test_subtotals_and_totals_derived_readonly(
        self, doc_text,
    ):
        assert "subtotal" in doc_text.lower()
        assert "derived" in doc_text.lower()
        assert "Hard CAPEX Total" in doc_text
        assert "Total CAPEX" in doc_text


# ---------------------------------------------------------------------------
# 4. Add-line-item behavior
# ---------------------------------------------------------------------------


class TestAddLineItem:
    def test_design_documents_add_line_item(self, doc_text):
        assert "Add line" in doc_text or "add-line-item" in doc_text

    def test_design_states_persistence_out_of_scope(
        self, doc_text,
    ):
        # The design must state that persistence is out
        # of scope for the first 57A-x arc.
        pattern = re.compile(
            r"persistence.*out of scope",
            re.IGNORECASE,
        )
        assert pattern.search(doc_text), (
            "Design must state that add-line-item "
            "persistence is out of scope for the first "
            "57A-x arc."
        )

    def test_design_states_only_subtotal_total_impact(
        self, doc_text, report,
    ):
        # The new line affects only the category
        # subtotal and the total CAPEX, not any other
        # model mechanism.
        assert "category's subtotal" in doc_text or (
            "category subtotal" in doc_text
        )
        assert "Total CAPEX" in doc_text
        # The doc lists the non-impacted mechanisms as
        # "(P&L, Balance Sheet, Cash Flow, IDC, funding
        # drawdown, tax engine, depreciation)" — the
        # first three must be present.
        for keyword in [
            "P&L",
            "Balance Sheet",
            "Cash Flow",
        ]:
            assert keyword in doc_text, (
                f"Doc must mention {keyword!r} as a "
                f"non-impacted mechanism."
            )
        # In the report, the no_impact list must include
        # the key downstream effects.
        report_text = json.dumps(report)
        for keyword in [
            "P&L",
            "Balance Sheet",
            "Cash Flow",
            "IDC",
            "funding drawdown",
            "tax",
            "depreciation",
        ]:
            assert keyword in report_text, (
                f"Report must mention {keyword!r} as a "
                f"non-impacted mechanism."
            )


# ---------------------------------------------------------------------------
# 5. Future model inputs
# ---------------------------------------------------------------------------


class TestFutureModelInputs:
    @pytest.mark.parametrize(
        "future_input",
        [
            "Cost / MW",
            "Contingency",
            "VAT",
            "WHT",
            "Depreciation",
            "Payment schedule",
            "Utilisation",
        ],
    )
    def test_future_input_documented(
        self, doc_text, report, future_input,
    ):
        assert future_input in doc_text, (
            f"Future model input {future_input!r} must be "
            f"documented in the design."
        )
        # The future_model_inputs list in the report may
        # use shortened labels (e.g. "Cost / MW" or
        # "Payment schedule M1..M18"); check that the
        # keyword appears in the report as a substring of
        # at least one entry.
        assert any(
            future_input in entry
            for entry in report["future_model_inputs"]
        ), (
            f"Future model input {future_input!r} must "
            f"be listed in the report."
        )

    def test_future_inputs_not_wired(self, doc_text):
        # The design must say these columns are not wired
        # to the model in any 57A-x phase.
        assert "not wired" in doc_text or "NOT wired" in doc_text
        assert "future model input" in doc_text.lower()


# ---------------------------------------------------------------------------
# 6. G20 / R99 / R102 governance guards
# ---------------------------------------------------------------------------


class TestGovernanceGuardsDoNotBlock:
    def test_g20_r99_r102_documented(self, doc_text):
        for guard in ["G20", "R99", "R102"]:
            assert guard in doc_text, (
                f"Governance guard {guard!r} must be "
                f"mentioned in the design."
            )

    def test_g20_r99_r102_do_not_block_capex_editing(
        self, doc_text,
    ):
        # The design must say these guards do not block
        # CAPEX editing.
        pattern = re.compile(
            r"(G20|R99|R102).*do not block CAPEX editing",
            re.IGNORECASE | re.DOTALL,
        )
        assert pattern.search(doc_text), (
            "Design must state that G20 / R99 / R102 "
            "do not block CAPEX editing."
        )


# ---------------------------------------------------------------------------
# 7. Runtime sequence
# ---------------------------------------------------------------------------


class TestRuntimeSequence:
    def test_runtime_sequence_documented(self, report):
        seq = report["runtime_sequence"]
        assert len(seq) == 6, (
            f"Runtime sequence must have 6 phases. "
            f"Got {len(seq)}."
        )
        for entry in seq:
            assert "order" in entry
            assert "phase" in entry
            assert "type" in entry
            assert "auto_merge" in entry

    def test_runtime_sequence_order(self, report):
        seq = report["runtime_sequence"]
        orders = [e["order"] for e in seq]
        assert orders == sorted(orders), (
            "Runtime sequence orders must be sorted."
        )
        phases = [e["phase"] for e in seq]
        assert phases == [
            "57A-2",
            "57A-3",
            "57A-4",
            "57A-5",
            "57A-6",
            "57A-7",
        ], f"Runtime sequence must be 57A-2..57A-7. Got {phases}."

    def test_design_phases_drafted_only(self, report):
        # 57A-3, 57A-4, 57A-5 are draft-only (not auto-merge).
        draft_phases = {
            e["phase"]
            for e in report["runtime_sequence"]
            if e.get("draft") is True
        }
        assert draft_phases == {
            "57A-3",
            "57A-4",
            "57A-5",
        }

    def test_design_phases_auto_merge(self, report):
        # 57A-2, 57A-6, 57A-7 are docs/report/test-only
        # and auto-merge eligible.
        auto_phases = {
            e["phase"]
            for e in report["runtime_sequence"]
            if e["auto_merge"] is True
        }
        assert auto_phases == {
            "57A-2",
            "57A-6",
            "57A-7",
        }


# ---------------------------------------------------------------------------
# 8. Hard no-go
# ---------------------------------------------------------------------------


class TestHardNoGo:
    @pytest.mark.parametrize(
        "no_go_keyword",
        [
            "financial formula changes",
            "IDC calculation",
            "construction funding",
            "G20",
            "Tailwind",
            "Portfolio",
            "schema",
            "backend keys visible",
        ],
    )
    def test_no_go_in_doc(self, doc_text, no_go_keyword):
        assert no_go_keyword in doc_text, (
            f"Hard no-go rule {no_go_keyword!r} must be "
            f"in the design doc."
        )

    def test_no_go_in_report(self, report):
        for ng in report["hard_no_go"]:
            assert ng
        joined = " ".join(report["hard_no_go"])
        # Spot-check a few canonical no-go rules by
        # substring match (the report uses underscored
        # identifiers that may include qualifiers like
        # '_unless_explicitly_scoped').
        for canonical in [
            "no_financial_formula_changes",
            "no_idc_calculation_changes",
            "no_construction_funding_changes",
            "no_g20_r99_r102_promotion",
            "no_tailwind_alpine",
            "no_backend_keys_visible_in_ui",
            "rc1_frozen",
            "no_schema_migration",
            "no_portfolio",
        ]:
            assert canonical in joined, (
                f"Canonical no-go {canonical!r} must be "
                f"in report's hard_no_go list."
            )
        # The report's hard_no_go list must contain at
        # least the no-schema and no-portfolio rules.
        joined = " ".join(report["hard_no_go"])
        assert "no_schema" in joined
        assert "no_portfolio" in joined


# ---------------------------------------------------------------------------
# 9. rc1 frozen
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
# 10. No-go copy
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
        # The design doc must not contain the forbidden
        # positive claims.
        pattern = re.compile(
            r"\b" + re.escape(forbidden) + r"\b",
            re.IGNORECASE,
        )
        matches = pattern.findall(doc_text)
        assert not matches, (
            f"Forbidden term {forbidden!r} must not appear "
            f"in the design doc. Found {len(matches)}."
        )
