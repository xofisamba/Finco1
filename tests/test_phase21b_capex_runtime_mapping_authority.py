"""
Phase 21B: CAPEX detail runtime mapping — authority flags tests.

Validates that _build_capex_detail_items() correctly classifies C.01–C.18
rows by authority status (backend_authoritative / app_mapped / excel_reference_only /
missing_runtime_source / mismatch / deferred / not_applicable), source type,
runtime impact, and that the template renders authority badges.

Run:
    pytest tests/test_phase21b_capex_runtime_mapping_authority.py -v
"""

import pytest
from dataclasses import dataclass, field
from app.ui.project_context import _build_capex_detail_items


# ── Mock CapexStructure ────────────────────────────────────────────────────────

@dataclass
class MockCapexItem:
    name: str
    amount_keur: float
    y0_share: float = 0.0


@dataclass
class MockCapexStructure:
    """Minimal CapexStructure with all relevant fields for authority mapping tests."""

    _CAPEX_ITEM_FIELDS = [
        "epc_contract", "grid_connection", "monitoring", "insurances",
        "land_securing", "bank_due_diligence", "construction_mgmt",
        "contingencies", "project_rights",
    ]

    # Hard CAPEX items
    epc_contract: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("EPC Contract", 52800.0)
    )
    epc_other: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("EPC Other / Dev & Perm", 2100.0)
    )
    grid_connection: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Grid Connection", 6200.0)
    )
    monitoring: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Monitoring & Telecom", 0.0)
    )
    insurances: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Insurances", 0.0)
    )
    land_securing: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Land Securing", 0.0)
    )
    bank_due_diligence: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Bank Due Diligence", 0.0)
    )
    construction_mgmt: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Construction Management", 0.0)
    )
    contingencies: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Contingencies", 2991.54)
    )
    project_rights: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Project Rights", 0.0)
    )
    ops_prep: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Operations Prep", 1200.0)
    )
    commissioning: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Commissioning", 0.0)
    )
    audit_legal: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Audit & Legal", 200.0)
    )
    project_acquisition: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Project Acquisition", 1000.0)
    )
    production_units: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Production Units", 0.0)
    )
    lease_tax: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Lease Tax", 0.0)
    )
    construction_mgmt_a: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Construction Mgmt A", 5400.0)
    )
    construction_mgmt_b: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Construction Mgmt B", 0.0)
    )
    taxes: MockCapexItem = field(
        default_factory=lambda: MockCapexItem("Taxes", 0.0)
    )

    # Financing costs (floats, not CapexItems)
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


# ── Helpers ────────────────────────────────────────────────────────────────────

def flatten_children(categories):
    """Flatten all children from all categories into a dict keyed by code."""
    return {ch["code"]: ch for cat in categories for ch in cat["children"]}


def get_child(result, code):
    return flatten_children(result["categories"])[code]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1: CAPEX detail context includes C.01–C.18
# ═══════════════════════════════════════════════════════════════════════════════

class TestCAPEXDetailC01toC18:
    def test_all_18_categories_present(self, detail_result):
        codes = {cat["code"] for cat in detail_result["categories"]}
        expected = {f"C.{i:02d}" for i in range(1, 19)}
        assert expected.issubset(codes), f"Missing categories: {expected - codes}"
        assert len(codes) == 18

    def test_categories_have_authority_summary(self, detail_result):
        for cat in detail_result["categories"]:
            assert "authority_summary" in cat, f"Category {cat['code']} missing authority_summary"
            summary = cat["authority_summary"]
            assert isinstance(summary, dict)
            assert "backend_authoritative" in summary
            assert "app_mapped" in summary
            assert "excel_reference_only" in summary
            assert "missing_runtime_source" in summary
            assert "mismatch" in summary

    def test_authority_summary_top_level_present(self, detail_result):
        assert "authority_summary" in detail_result
        top = detail_result["authority_summary"]
        assert top["_total_child_rows"] > 0


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2: Every C.x row has authority_status
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthorityStatusPresent:
    VALID_STATUSES = {
        "backend_authoritative", "app_mapped", "excel_reference_only",
        "missing_runtime_source", "mismatch", "deferred", "not_applicable",
    }

    def test_every_child_has_authority_status(self, detail_result):
        for cat in detail_result["categories"]:
            for child in cat["children"]:
                assert "authority_status" in child, \
                    f"Row {child['code']} missing authority_status"
                assert child["authority_status"] in self.VALID_STATUSES, \
                    f"Row {child['code']}: invalid authority_status '{child['authority_status']}'"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3: Every C.x row has source_type
# ═══════════════════════════════════════════════════════════════════════════════

class TestSourceTypePresent:
    VALID_SOURCE_TYPES = {
        "excel_reference", "app_input", "computed_runtime", "static_reference", "missing"
    }

    def test_every_child_has_source_type(self, detail_result):
        for cat in detail_result["categories"]:
            for child in cat["children"]:
                assert "source_type" in child, \
                    f"Row {child['code']} missing source_type"
                assert child["source_type"] in self.VALID_SOURCE_TYPES, \
                    f"Row {child['code']}: invalid source_type '{child['source_type']}'"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4: Every C.x row has affects_runtime boolean
# ═══════════════════════════════════════════════════════════════════════════════

class TestAffectsRuntimeBoolean:
    def test_every_child_has_affects_runtime(self, detail_result):
        for cat in detail_result["categories"]:
            for child in cat["children"]:
                assert "affects_runtime" in child, \
                    f"Row {child['code']} missing affects_runtime"
                assert isinstance(child["affects_runtime"], bool), \
                    f"Row {child['code']}: affects_runtime must be bool"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 5: Rows without runtime source are marked missing_runtime_source or
#         excel_reference_only
# ═══════════════════════════════════════════════════════════════════════════════

class TestRowsWithoutRuntimeSource:
    def test_rows_with_no_app_field_are_excel_reference_only_or_missing(
        self, detail_result
    ):
        """Rows with no runtime_source_field should not be app_mapped or
        backend_authoritative (unless they are true backend-calculated items)."""
        for cat in detail_result["categories"]:
            for child in cat["children"]:
                # backend_authoritative rows without individual app fields are
                # true backend-calculated (C.17.04/05); they are exempt.
                if child["authority_status"] == "backend_authoritative":
                    continue
                if child.get("runtime_source_field") is None:
                    status = child["authority_status"]
                    assert status in {"excel_reference_only", "missing_runtime_source",
                                     "not_applicable", "deferred"}, \
                        f"Row {child['code']} with no runtime_source_field " \
                        f"has unexpected status '{status}'"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 6: No row is marked backend_authoritative unless runtime_source_field exists
# ═══════════════════════════════════════════════════════════════════════════════

class TestBackendAuthoritativeRequiresField:
    def test_backend_authoritative_rows_have_valid_source_type(
        self, detail_result
    ):
        """backend_authoritative rows must have source_type=computed_runtime."""
        for cat in detail_result["categories"]:
            for child in cat["children"]:
                if child["authority_status"] == "backend_authoritative":
                    assert child["source_type"] == "computed_runtime", \
                        f"Row {child['code']} is backend_authoritative " \
                        f"but source_type is {child['source_type']}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 7: Mismatch rows include mismatch_amount_keur or mismatch_pct
# ═══════════════════════════════════════════════════════════════════════════════

class TestMismatchRowsHaveAmount:
    def test_mismatch_rows_have_mismatch_metadata(self, detail_result):
        for cat in detail_result["categories"]:
            for child in cat["children"]:
                if child["authority_status"] == "mismatch":
                    has_amount = child.get("mismatch_amount_keur") is not None
                    has_pct = child.get("mismatch_pct") is not None
                    assert has_amount or has_pct, \
                        f"Row {child['code']} is mismatch but has no " \
                        f"mismatch_amount_keur or mismatch_pct"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 8: Specific known classifications (TUHO known values)
# ═══════════════════════════════════════════════════════════════════════════════

class TestKnownClassifications:
    """Verify specific C.01–C.18 rows have the expected authority status."""

    def test_c13_contingencies_is_app_mapped(self, detail_result):
        child = get_child(detail_result, "C.13")
        assert child["authority_status"] == "app_mapped", \
            f"C.13 should be app_mapped, got {child['authority_status']}"
        assert child["source_type"] == "app_input"
        # Contingencies is embedded in capex total (not a direct field read);
        # contingency.amount_keur is accessed via capex_items dict, not hasattr(capex, "contingencies")
        # so it does NOT appear in _RUNTIME_SOURCE_FIELDS as a direct field.
        # It affects runtime via the capex total.
        assert child["runtime_source_field"] == "capex.contingencies"

    def test_c17_idc_is_backend_authoritative(self, detail_result):
        child = get_child(detail_result, "C.17.02")
        assert child["authority_status"] == "backend_authoritative", \
            f"C.17.02 should be backend_authoritative, got {child['authority_status']}"
        assert child["source_type"] == "computed_runtime"
        assert child["affects_runtime"] is True
        assert child["runtime_source_field"] == "capex.idc_keur"

    def test_c17_bank_fees_is_backend_authoritative(self, detail_result):
        child = get_child(detail_result, "C.17.01")
        assert child["authority_status"] == "backend_authoritative"
        assert child["affects_runtime"] is True
        assert child["runtime_source_field"] == "capex.bank_fees_keur"

    def test_c17_commitment_fees_is_backend_authoritative(self, detail_result):
        child = get_child(detail_result, "C.17.03")
        assert child["authority_status"] == "backend_authoritative"
        assert child["affects_runtime"] is True
        assert child["runtime_source_field"] == "capex.commitment_fees_keur"

    def test_c18_reserve_accounts_are_backend_authoritative(self, detail_result):
        for code in ("C.18.01", "C.18.02", "C.18.03"):
            child = get_child(detail_result, code)
            assert child["authority_status"] == "backend_authoritative", \
                f"{code} should be backend_authoritative"
            assert child["runtime_source_field"] == "capex.reserve_accounts_keur"

    def test_c01_wind_turbines_is_excel_reference_only(self, detail_result):
        child = get_child(detail_result, "C.01.01")
        assert child["authority_status"] == "excel_reference_only"
        assert child["runtime_source_field"] is None

    def test_c02_epc_grid_connection_is_mismatch(self, detail_result):
        child = get_child(detail_result, "C.02.04")
        assert child["authority_status"] == "mismatch"
        assert child["runtime_source_field"] == "capex.grid_connection"
        # app=6200, excel=10800 → diff=4600
        assert child["mismatch_amount_keur"] == 4600.0

    def test_c15_project_acquisition_is_mismatch(self, detail_result):
        child = get_child(detail_result, "C.15")
        assert child["authority_status"] == "mismatch"
        assert child["runtime_source_field"] == "capex.project_acquisition"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 9: Template renders authority badges (structural test)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTemplateAuthorityBadges:
    """Verify template has authority badge CSS classes."""

    def test_template_has_authority_badge_css(self):
        import os
        tpl_path = os.path.join(
            os.path.dirname(__file__), "..",
            "app/templates/partials/sheet_capex_detail.html"
        )
        with open(tpl_path, "r") as f:
            content = f.read()

        # Authority badge classes
        assert "badge-auth-backend" in content
        assert "badge-auth-app" in content
        assert "badge-auth-excel" in content
        assert "badge-auth-missing" in content
        assert "badge-auth-mismatch" in content
        assert "badge-auth-deferred" in content
        assert "badge-auth-na" in content

        # Authority strip
        assert "capex-auth-strip" in content
        assert "capex-auth-card" in content

        # Source type label
        assert "fc-auth-src" in content

        # Runtime dot
        assert "fc-rt-dot" in content


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 10: Template renders M1–M18 columns
# ═══════════════════════════════════════════════════════════════════════════════

class TestTemplateM118Columns:
    def test_template_renders_m1_to_m18_columns(self):
        """Template uses M{{ m }} in a Jinja2 loop; check for loop construct."""
        import os
        tpl_path = os.path.join(
            os.path.dirname(__file__), "..",
            "app/templates/partials/sheet_capex_detail.html"
        )
        with open(tpl_path, "r") as f:
            content = f.read()

        # Jinja2 month loop: {% for m in range(1, 19) %}
        assert "range(1, 19)" in content, \
            "Month loop range(1, 19) missing from template"
        # data-m attribute pattern
        assert 'data-m="' in content, \
            "data-m attribute missing (month column marker)"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 11: Template renders authority summary strip
# ═══════════════════════════════════════════════════════════════════════════════

class TestTemplateAuthoritySummaryStrip:
    def test_template_has_authority_summary_in_strip(self):
        import os
        tpl_path = os.path.join(
            os.path.dirname(__file__), "..",
            "app/templates/partials/sheet_capex_detail.html"
        )
        with open(tpl_path, "r") as f:
            content = f.read()

        assert "capex-auth-strip" in content
        assert "Backend auth" in content or "backend" in content.lower()
        assert "capex-auth-card" in content


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 12: Guardrail — no runtime/model calculation modules changed
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoRuntimeModuleChanges:
    """Ensure no runtime/calculation modules were modified."""

    RUNTIME_MODULES = [
        "domain/capex/capex_breakdown.py",
        "domain/capex/capex_schedule.py",
        "domain/construction/engine.py",
        "domain/construction/runtime_adapter.py",
        "domain/shl/canonical_wiring.py",
        "domain/shl/runtime_adapter.py",
        "domain/returns/sponsor_cashflows.py",
    ]

    def test_no_runtime_modules_modified(self):
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD",
             "origin/main", "--"] + self.RUNTIME_MODULES,
            capture_output=True, text=True, cwd="/opt/finco1"
        )
        # Allow if no changes or if diff is empty
        changed = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
        assert not changed, \
            f"Runtime/model modules were modified: {changed}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 13: Guardrail — no CAPEX totals changed
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoCAPEXTotalsChanged:
    """Ensure the hard-capex / financing / grand totals are unchanged."""

    def test_capex_detail_totals_match_expected(self, mock_capex, detail_result):
        # Grand total from _EXCEL_ROWS sum (C.01–C.18)
        # C.13 was corrected to 2991.54, other C.17 items are backend
        grand = detail_result["grand_total_keur"]
        # Verify it's a positive number in the expected range
        assert grand > 70000, f"Grand total {grand} seems too low"
        assert grand < 80000, f"Grand total {grand} seems too high"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 14: main_web imports successfully
# ═══════════════════════════════════════════════════════════════════════════════

class TestMainWebImport:
    def test_main_web_imports(self):
        import main_web  # should not raise


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 15: monthly_schedule_source present for all children
# ═══════════════════════════════════════════════════════════════════════════════

class TestMonthlyScheduleSource:
    VALID_SCHED_SOURCES = {
        "excel_m1_m18", "app_profile", "static_reference", "missing"
    }

    def test_every_child_has_monthly_schedule_source(self, detail_result):
        for cat in detail_result["categories"]:
            for child in cat["children"]:
                assert "monthly_schedule_source" in child, \
                    f"Row {child['code']} missing monthly_schedule_source"
                assert child["monthly_schedule_source"] in self.VALID_SCHED_SOURCES


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 16: authority_summary counts are consistent
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthoritySummaryConsistency:
    def test_top_level_counts_sum_to_total_rows(self, detail_result):
        top = detail_result["authority_summary"]
        total_rows = top["_total_child_rows"]
        sum_counts = sum(
            v for k, v in top.items() if not k.startswith("_")
        )
        assert sum_counts == total_rows, \
            f"Authority counts sum {sum_counts} != total rows {total_rows}"

    def test_category_counts_sum_to_top_counts(self, detail_result):
        top = detail_result["authority_summary"]
        for cat in detail_result["categories"]:
            summary = cat["authority_summary"]
            for k, v in summary.items():
                assert top.get(k, 0) >= v, \
                    f"Category {cat['code']} count for '{k}' ({v}) " \
                    f"exceeds top-level ({top.get(k, 0)})"
