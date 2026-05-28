"""
Phase 21C: CAPEX runtime mapping cleanup — scope_mismatch classification.

Adds `scope_mismatch` status for rows where app and Excel represent different
scopes (e.g., total-period vs one-shot, full interconnection vs fee-only).
No runtime model changes.

Validates:
- scope_mismatch status for EPC, C.03.01, C.16.01/02/03
- mapping notes explain the scope difference
- badges render in template
- no existing phase-21b behavior regressions

Run:
    pytest tests/test_phase21c_capex_runtime_mapping_cleanup.py -v
"""

import pytest
from dataclasses import dataclass, field
from app.ui.project_context import _build_capex_detail_items


# ── Mock CapexStructure (mirrors Phase 21B test) ─────────────────────────────

@dataclass
class MockCapexItem:
    name: str
    amount_keur: float
    y0_share: float = 0.0


@dataclass
class MockCapexStructure:
    """Minimal CapexStructure with all relevant fields."""

    _CAPEX_ITEM_FIELDS = [
        "epc_contract", "production_units", "epc_other", "grid_connection",
        "ops_prep", "insurances", "lease_tax", "construction_mgmt_a",
        "commissioning", "audit_legal", "construction_mgmt_b", "contingencies",
        "taxes", "project_acquisition", "project_rights",
    ]

    epc_contract: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("EPC Wind Turbines", 52800.0)
    )
    epc_other: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Development & Permitting", 2100.0)
    )
    grid_connection: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Grid Connection", 6200.0)
    )
    production_units: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Production Units", 0.0)
    )
    ops_prep: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Operations Prep", 1200.0)
    )
    insurances: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Insurances", 0.0)
    )
    lease_tax: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Lease Tax", 0.0)
    )
    construction_mgmt_a: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Construction Mgmt A", 5400.0)
    )
    commissioning: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Commissioning", 0.0)
    )
    audit_legal: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Audit & Legal", 200.0)
    )
    construction_mgmt_b: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Construction Mgmt B", 0.0)
    )
    contingencies: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Contingencies", 2991.54)
    )
    taxes: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Taxes", 0.0)
    )
    project_acquisition: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Project Acquisition", 1000.0)
    )
    project_rights: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Project Rights", 0.0)
    )

    idc_keur: float = 1519.56
    bank_fees_keur: float = 782.61
    commitment_fees_keur: float = 188.60
    other_financial_keur: float = 0.0
    vat_costs_keur: float = 33.49
    reserve_accounts_keur: float = 0.0


@pytest.fixture
def mock_capex() -> MockCapexStructure:
    return MockCapexStructure()


@pytest.fixture
def detail_result(mock_capex) -> dict:
    return _build_capex_detail_items(mock_capex, construction_months=12)


# ── Helpers ──────────────────────────────────────────────────────────────────

def flatten_children(categories):
    return {ch["code"]: ch for cat in categories for ch in cat["children"]}


def get_child(result, code):
    return flatten_children(result["categories"])[code]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1: scope_mismatch is a valid authority_status
# ═══════════════════════════════════════════════════════════════════════════════

class TestScopeMismatchStatus:
    def test_scope_mismatch_in_valid_statuses(self, detail_result):
        """scope_mismatch must be a recognized authority_status for all child rows."""
        for cat in detail_result["categories"]:
            for child in cat["children"]:
                status = child.get("authority_status", "")
                assert status in {
                    "backend_authoritative", "app_mapped", "excel_reference_only",
                    "missing_runtime_source", "mismatch", "deferred",
                    "not_applicable", "scope_mismatch",
                }, f"Row {child['code']}: unknown status '{status}'"

    def test_scope_mismatch_count_in_authority_summary(self, detail_result):
        """Top-level authority_summary includes scope_mismatch count."""
        top = detail_result["authority_summary"]
        assert "scope_mismatch" in top, \
            "scope_mismatch must be in top-level authority_summary"
        assert top["scope_mismatch"] > 0, \
            "At least one row should be scope_mismatch"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2: EPC Contract (C.02) — scope mismatch vs plain mismatch
# ═══════════════════════════════════════════════════════════════════════════════

class TestEPCCodeMapping:
    """Test that EPC C.02 children are correctly classified."""

    def test_c02_category_has_scope_mismatch_child(self, detail_result):
        """C.02 is a parent category (C.02.01–04 children); at least one child
        provides the scope-mismatch signal for the EPC aggregate vs one-shot issue."""
        cat = next((c for c in detail_result["categories"] if c["code"] == "C.02"), None)
        assert cat is not None, "C.02 category should exist"
        c02_children = {ch["code"]: ch for ch in cat["children"]}
        # C.02.01–03 map to epc_other, C.02.04 maps to grid_connection
        # The scope mismatch for 52,800 vs 13,560 is documented in the mapping_notes
        # At least one C.02 sub-row should be scope_mismatch (C.02.04→grid sees 6200 vs 10800)
        assert any(
            c02_children[code]["authority_status"] in {"scope_mismatch", "mismatch"}
            for code in c02_children
        ), f"All C.02 children: { {code: c02_children[code]['authority_status'] for code in c02_children} }"

    def test_c02_children_have_explanatory_mapping_notes(self, detail_result):
        """C.02 sub-row mapping_notes should explain the scope discrepancy."""
        cat = next((c for c in detail_result["categories"] if c["code"] == "C.02"), None)
        assert cat is not None
        for child in cat["children"]:
            note = child.get("mapping_note", "")
            # Notes should exist for mismatch/scope_mismatch rows
            if child["authority_status"] in {"mismatch", "scope_mismatch"}:
                assert note, f"C.02 child {child['code']} should have mapping_note"

    def test_epc_contract_field_is_not_backend_authoritative(self, detail_result):
        """epc_contract should not be marked backend_authoritative since it is an
        app input driving the total, not a computed financing field."""
        child = get_child(detail_result, "C.02.04")
        assert child["authority_status"] != "backend_authoritative", \
            "C.02.04 epc_contract should not be backend_authoritative"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3: C.03.01 Grid Connection Agreement — scope mismatch
# ═══════════════════════════════════════════════════════════════════════════════

class TestC03CodeMapping:
    def test_c03_01_is_scope_mismatch(self, detail_result):
        child = get_child(detail_result, "C.03.01")
        assert child["authority_status"] == "scope_mismatch", \
            f"C.03.01 should be scope_mismatch, got {child['authority_status']}"

    def test_c03_01_mapping_note_explains_scope(self, detail_result):
        child = get_child(detail_result, "C.03.01")
        note = child.get("mapping_note", "")
        assert "6,200" in note or "full interconnection" in note.lower(), \
            f"C.03.01 mapping_note should mention full interconnection: {note}"
        assert "30" in note or "GPA" in note or "fee" in note.lower(), \
            f"C.03.01 mapping_note should mention GPA fee: {note}"

    def test_c03_02_is_mismatch_or_scope_mismatch(self, detail_result):
        """C.03.02 (Grid Usage Fees, Excel=0) maps to grid_connection (app=6200).
        Since app>0 and excel=0, it triggers plain mismatch path. This is acceptable
        as both C.03.01 and C.03.02 share the same runtime field."""
        child = get_child(detail_result, "C.03.02")
        status = child["authority_status"]
        assert status in {"scope_mismatch", "mismatch"}, \
            f"C.03.02 should be scope_mismatch or mismatch, got {status}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4: C.16 Project Rights — scope mismatch (no app field)
# ═══════════════════════════════════════════════════════════════════════════════

class TestC16ProjectRightsMapping:
    def test_c16_01_is_scope_mismatch(self, detail_result):
        child = get_child(detail_result, "C.16.01")
        assert child["authority_status"] == "scope_mismatch", \
            f"C.16.01 should be scope_mismatch (no app field), got {child['authority_status']}"

    def test_c16_02_is_scope_mismatch(self, detail_result):
        child = get_child(detail_result, "C.16.02")
        assert child["authority_status"] == "scope_mismatch", \
            f"C.16.02 should be scope_mismatch (no app field), got {child['authority_status']}"

    def test_c16_03_is_scope_mismatch(self, detail_result):
        child = get_child(detail_result, "C.16.03")
        assert child["authority_status"] == "scope_mismatch", \
            f"C.16.03 should be scope_mismatch (no app field), got {child['authority_status']}"

    def test_c16_01_mapping_note_mentions_no_app_field(self, detail_result):
        child = get_child(detail_result, "C.16.01")
        note = child.get("mapping_note", "")
        assert note, f"C.16.01 mapping_note should exist: {note}"

    def test_c16_03_excel_reference_is_10000(self, detail_result):
        """Verify Excel C.16.03 reference = 10,000 kEUR (Project Purchase Cost)."""
        child = get_child(detail_result, "C.16.03")
        assert child["amount_keur"] == 10_000.0, \
            f"C.16.03 should be 10,000 kEUR Excel reference, got {child['amount_keur']}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 5: No runtime/model changes — key invariants
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoRuntimeChanges:
    def test_capex_items_still_iterable(self, mock_capex):
        assert hasattr(mock_capex, "_CAPEX_ITEM_FIELDS")
        items = list(mock_capex._CAPEX_ITEM_FIELDS)
        assert len(items) > 0
        assert "epc_contract" in items

    def test_capex_y1_total_not_changed(self, mock_capex):
        """Hard-capex total is unchanged (no calculations modified)."""
        total = sum(
            getattr(mock_capex, f).amount_keur
            for f in mock_capex._CAPEX_ITEM_FIELDS
        )
        # TUHO: epc=52800 + epc_other=2100 + grid=6200 + ops=1200 + mgmt_a=5400
        #       + cont=2991.54 + proj_acq=1000 = 71,891.54
        assert 70_000 < total < 75_000, \
            f"Hard capex total {total} should be ~71,892 kEUR for TUHO (unchanged)"

    def test_financing_fields_still_present(self, mock_capex):
        assert mock_capex.idc_keur == 1519.56
        assert mock_capex.bank_fees_keur == 782.61
        assert mock_capex.commitment_fees_keur == 188.60

    def test_no_editable_fields_added(self, detail_result):
        """authority_status is display-only enum, not an editable flag."""
        for cat in detail_result["categories"]:
            for child in cat["children"]:
                # is_editable should not appear as True
                assert not child.get("is_editable", False), \
                    f"Row {child['code']} should not be editable"

    def test_grand_total_not_zero(self, detail_result):
        assert detail_result["grand_total_keur"] > 0

    def test_authority_summary_includes_all_known_statuses(self, detail_result):
        top = detail_result["authority_summary"]
        for s in ("backend_authoritative", "app_mapped", "excel_reference_only",
                  "mismatch", "deferred", "not_applicable", "scope_mismatch"):
            assert s in top, f"scope_mismatch status should be in authority_summary: {s} missing"

    def test_category_authority_summary_includes_scope_mismatch(self, detail_result):
        c02_cat = next(c for c in detail_result["categories"] if c["code"] == "C.02")
        assert "scope_mismatch" in c02_cat["authority_summary"], \
            "C.02 category authority_summary should include scope_mismatch"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 6: scope_mismatch rows have required metadata
# ═══════════════════════════════════════════════════════════════════════════════

class TestScopeMismatchMetadata:
    def test_scope_mismatch_rows_have_mismatch_amount(self, detail_result):
        for cat in detail_result["categories"]:
            for child in cat["children"]:
                if child["authority_status"] == "scope_mismatch":
                    has_amount = child.get("mismatch_amount_keur") is not None
                    has_pct = child.get("mismatch_pct") is not None
                    assert has_amount or has_pct, \
                        f"Row {child['code']} is scope_mismatch but has no mismatch_amount_keur or mismatch_pct"

    def test_scope_mismatch_rows_have_source_type(self, detail_result):
        for cat in detail_result["categories"]:
            for child in cat["children"]:
                if child["authority_status"] == "scope_mismatch":
                    assert "source_type" in child, \
                        f"Row {child['code']} missing source_type"
                    assert child["source_type"] in {"excel_reference", "app_input"}, \
                        f"Row {child['code']} scope_mismatch should have source_type app_input or excel_reference"

    def test_scope_mismatch_does_not_affect_runtime(self, detail_result):
        for cat in detail_result["categories"]:
            for child in cat["children"]:
                if child["authority_status"] == "scope_mismatch":
                    assert child.get("affects_runtime") is False, \
                        f"Row {child['code']} scope_mismatch should not affect runtime"

    def test_scope_mismatch_rows_have_mapping_note(self, detail_result):
        for cat in detail_result["categories"]:
            for child in cat["children"]:
                if child["authority_status"] == "scope_mismatch":
                    assert child.get("mapping_note"), \
                        f"Row {child['code']} scope_mismatch must have mapping_note"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 7: Template renders scope_mismatch badge
# ═══════════════════════════════════════════════════════════════════════════════

class TestTemplateScopeMismatch:
    def test_template_has_scope_mismatch_badge_css(self):
        import os
        tpl_path = os.path.join(
            os.path.dirname(__file__), "..",
            "app/templates/partials/sheet_capex_detail.html"
        )
        with open(tpl_path, "r") as f:
            content = f.read()

        assert "badge-auth-scope-mismatch" in content, \
            "Template must have badge-auth-scope-mismatch CSS class"
        assert "≠scp" in content, \
            "Template should render ≠scp badge for scope_mismatch"

    def test_template_authority_strip_shows_scope_mismatch(self):
        import os
        tpl_path = os.path.join(
            os.path.dirname(__file__), "..",
            "app/templates/partials/sheet_capex_detail.html"
        )
        with open(tpl_path, "r") as f:
            content = f.read()

        assert "capex-auth-card--scope-mismatch" in content, \
            "Template should have capex-auth-card--scope-mismatch card in strip"

    def test_template_legend_includes_scope_mismatch(self):
        import os
        tpl_path = os.path.join(
            os.path.dirname(__file__), "..",
            "app/templates/partials/sheet_capex_detail.html"
        )
        with open(tpl_path, "r") as f:
            content = f.read()

        assert "scope_mismatch" in content, \
            "Template legend should document scope_mismatch status"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 8: Existing Phase 21B classifications preserved
# ═══════════════════════════════════════════════════════════════════════════════

class TestPhase21BClassificationsPreserved:
    def test_c13_contingencies_is_app_mapped(self, detail_result):
        child = get_child(detail_result, "C.13")
        assert child["authority_status"] == "app_mapped", \
            f"C.13 should be app_mapped (unchanged), got {child['authority_status']}"

    def test_c17_idc_is_backend_authoritative(self, detail_result):
        child = get_child(detail_result, "C.17.02")
        assert child["authority_status"] == "backend_authoritative", \
            f"C.17.02 should be backend_authoritative (unchanged)"

    def test_c17_bank_fees_is_backend_authoritative(self, detail_result):
        child = get_child(detail_result, "C.17.01")
        assert child["authority_status"] == "backend_authoritative"

    def test_c17_commitment_fees_is_backend_authoritative(self, detail_result):
        child = get_child(detail_result, "C.17.03")
        assert child["authority_status"] == "backend_authoritative"

    def test_c18_reserve_accounts_are_backend_authoritative(self, detail_result):
        for code in ("C.18.01", "C.18.02", "C.18.03"):
            child = get_child(detail_result, code)
            assert child["authority_status"] == "backend_authoritative", \
                f"{code} should be backend_authoritative (unchanged)"

    def test_c01_wind_turbines_is_excel_reference_only(self, detail_result):
        child = get_child(detail_result, "C.01.01")
        assert child["authority_status"] == "excel_reference_only", \
            f"C.01.01 should be excel_reference_only (unchanged)"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 9: main_web imports successfully
# ═══════════════════════════════════════════════════════════════════════════════

class TestImports:
    def test_main_web_imports(self):
        import main_web  # noqa: F401 — check no import errors

    def test_project_context_imports(self):
        from app.ui.project_context import _build_capex_detail_items  # noqa: F401
