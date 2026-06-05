"""Phase 57A-7: CAPEX advanced columns design tests.

These tests pin the design contract from
``docs/phase57a7_capex_advanced_columns_design.md``.
They do NOT make any runtime / template / persistence
changes.

The contract is:

1. Each advanced column is designed (Cost / MW,
   Contingency, VAT, WHT, Depreciation, Comments,
   Payment schedule, Utilisation).
2. Each column's:
   - Type (derived / future model input / free-form).
   - Editable flag.
   - Backend wiring required.
   - Feeds (P&L, Balance Sheet, etc.).
   - Phase to wire.
3. The columns are NOT wired in 57A-7.
4. Staged backend integration plan exists (5 stages).
5. Comments is the safest first column (no model
   effect).
6. Hard no-go preserved.
7. rc1 (``b425a0708719eaa5e1d922b1008e5609758e0ad4``)
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
    / "phase57a7_capex_advanced_columns_design.md"
)
REPORT_PATH = (
    REPO_ROOT
    / "reports"
    / "phase57a7_capex_advanced_columns_design.json"
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
# 1. Each advanced column is designed
# ---------------------------------------------------------------------------


class TestAdvancedColumnsDesigned:
    @pytest.mark.parametrize(
        "column_keyword",
        [
            "cost",
            "contingency",
            "vat",
            "wht",
            "depreciation",
            "comments",
            "payment schedule",
            "utilisation",
        ],
    )
    def test_column_documented(self, doc_text, column_keyword):
        # The column must be mentioned in the design.
        assert column_keyword in doc_text.lower(), (
            f"Column {column_keyword!r} must be "
            f"documented in the design."
        )

    @pytest.mark.parametrize(
        "column",
        [
            "cost_per_mw",
            "contingency",
            "vat",
            "wht",
            "depreciation",
            "comments",
            "payment_schedule_m1_m18",
            "utilisation",
        ],
    )
    def test_column_in_report(self, report, column):
        names = [c["name"] for c in report["columns"]]
        assert column in names, (
            f"Column {column!r} must be in report's "
            f"columns list. Found: {names}"
        )


# ---------------------------------------------------------------------------
# 2. Each column's attributes
# ---------------------------------------------------------------------------


class TestColumnAttributes:
    @pytest.mark.parametrize(
        "column_name,expected_type",
        [
            ("cost_per_mw", "derived"),
            ("contingency", "future_model_input"),
            ("vat", "future_model_input"),
            ("wht", "future_model_input"),
            ("depreciation", "future_model_input"),
            ("comments", "free_form_text"),
            ("payment_schedule_m1_m18", "future_model_input"),
            ("utilisation", "future_model_input"),
        ],
    )
    def test_column_type(
        self, report, column_name, expected_type,
    ):
        col = next(
            c for c in report["columns"] if c["name"] == column_name
        )
        assert col["type"] == expected_type, (
            f"Column {column_name!r} type must be "
            f"{expected_type!r}, got {col['type']!r}."
        )

    def test_comments_column_has_no_model_effect(
        self, doc_text, report,
    ):
        # Comments has no model effect.
        col = next(
            c for c in report["columns"] if c["name"] == "comments"
        )
        assert "no model effect" in (
            col["feeds"][0].lower()
        ) or "display only" in (
            col["feeds"][0].lower()
        )

    def test_payment_schedule_total_must_equal_one(
        self, doc_text,
    ):
        # The payment schedule fractions must sum to 1.0.
        pattern = re.compile(
            r"total of the fractions.*1\.?0",
            re.IGNORECASE | re.DOTALL,
        )
        assert pattern.search(doc_text), (
            "Design must state that the payment "
            "schedule fractions must sum to 1.0."
        )


# ---------------------------------------------------------------------------
# 3. Columns NOT wired in 57A-7
# ---------------------------------------------------------------------------


class TestColumnsNotWiredIn57a7:
    def test_what_is_not_in_57a7_section(self, doc_text):
        assert "what is not in 57a-7" in doc_text.lower() or (
            "what is not in 57a7" in doc_text.lower()
        )

    def test_no_new_columns_in_57a7(self, doc_text, report):
        # 57A-7 must not add new columns to the CAPEX
        # sheet.
        assert "no new columns" in doc_text.lower()
        assert "no_new_columns_in_capex_sheet" in (
            report["what_is_not_in_57a7"]
        )

    def test_no_new_fields_in_57a7(self, doc_text, report):
        # 57A-7 must not add new fields to
        # CapexItem.
        assert "no new fields" in doc_text.lower() or (
            "new field" in doc_text.lower()
        )
        assert "no_new_fields_on_capex_item" in (
            report["what_is_not_in_57a7"]
        )

    def test_no_tax_engine_in_57a7(self, report):
        assert "no_tax_engine" in report["what_is_not_in_57a7"]

    def test_no_idc_in_57a7(self, report):
        assert "no_idc_calculation_change" in (
            report["what_is_not_in_57a7"]
        )


# ---------------------------------------------------------------------------
# 4. Staged backend integration
# ---------------------------------------------------------------------------


class TestStagedBackendIntegration:
    def test_stages_exist(self, report):
        stages = report["staged_backend_integration"]
        assert len(stages) == 5, (
            f"Expected 5 stages. Got {len(stages)}."
        )

    def test_stage_1_is_comments(self, report):
        stage_1 = report["staged_backend_integration"][0]
        assert "comments" in stage_1["columns"]

    def test_stage_5_is_payment_schedule(self, report):
        stage_5 = report["staged_backend_integration"][4]
        # Stage 5 should include payment_schedule_m1_m18
        # and utilisation.
        joined = " ".join(stage_5["columns"]).lower()
        assert "payment_schedule" in joined
        assert "utilisation" in joined


# ---------------------------------------------------------------------------
# 5. G20 / R99 / R102
# ---------------------------------------------------------------------------


class TestGovernanceGuards:
    def test_g20_r99_r102_in_design(self, doc_text):
        for guard in ["G20", "R99", "R102"]:
            assert guard in doc_text, (
                f"Governance guard {guard!r} must be "
                f"mentioned in the design."
            )


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
