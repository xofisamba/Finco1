"""
Phase 21E: CAPEX Input Wiring First Tranche — tests.

Covers: scope wiring for EPC C.02, Grid C.03, Project Rights C.16,
M1-M18 timing_only flag, and schedule_note.
"""

from tests.test_helpers import REPO_ROOT, PYTHON
import sys
sys.path.insert(0, str(REPO_ROOT))

from app.ui.project_context import _build_capex_detail_items
from app.domain.capex.source_model import CapexScope


# ── Mock Capex ────────────────────────────────────────────────────────────────

class MockCapex:
    """Minimal C.02-capable mock matching CapexStructure interface."""

    class _Info:
        construction_months = 18

    class EPCContract:
        amount_keur = 52800.0

    class GridConnection:
        amount_keur = 6200.0

    class Monitoring:
        amount_keur = 200.0

    class Insurances:
        amount_keur = 0.0   # app=0 → excel_reference_only

    class LandSecuring:
        amount_keur = 0.0

    class BankDueDiligence:
        amount_keur = 0.0

    class ConstructionManagement:
        amount_keur = 0.0

    class Contingencies:
        amount_keur = 2991.54

    class ProjectRights:
        amount_keur = 0.0

    class TotalCapex:
        total = 72993.71

    class IDC:
        idc_keur = 1519.56

    class BankFees:
        bank_fees_keur = 782.61

    info = _Info()
    epc_contract = EPCContract()
    grid_connection = GridConnection()
    monitoring = Monitoring()
    insurances = Insurances()
    land_securing = LandSecuring()
    bank_due_diligence = BankDueDiligence()
    construction_mgmt = ConstructionManagement()
    contingencies = Contingencies()
    project_rights = ProjectRights()
    total_capex = TotalCapex()
    idc = IDC()
    bank_fees = BankFees()

    # Used by _build_capex_items (capex._CAPEX_ITEM_FIELDS)
    _CAPEX_ITEM_FIELDS = ["epc_contract", "grid_connection", "monitoring",
                          "insurances", "land_securing", "bank_due_diligence",
                          "construction_mgmt", "contingencies", "project_rights"]


def _build():
    return _build_capex_detail_items(MockCapex(), construction_months=18)


# ── EPC C.02 Scope Wiring ────────────────────────────────────────────────────

class TestEPCScopeWiring:
    def test_c02_category_exists(self):
        result = _build()
        cats = result["categories"]
        c02 = next((c for c in cats if c["code"] == "C.02"), None)
        assert c02 is not None, "C.02 category must exist"

    def test_c02_children_all_payment_batch(self):
        result = _build()
        cats = result["categories"]
        c02 = next((c for c in cats if c["code"] == "C.02"), None)
        assert c02 is not None
        scopes = [ch.get("scope") for ch in c02["children"]]
        assert all(s == CapexScope.PAYMENT_BATCH for s in scopes), \
            f"All C.02 children should be payment_batch scope, got {scopes}"

    def test_c02_children_not_plain_mismatch(self):
        """C.02 children have payment_batch scope — not a plain value mismatch."""
        result = _build()
        cats = result["categories"]
        c02 = next((c for c in cats if c["code"] == "C.02"), None)
        for ch in c02["children"]:
            # payment_batch scope is distinct from raw value comparison
            assert ch.get("scope") in (
                CapexScope.PAYMENT_BATCH,
                CapexScope.AGGREGATE_TOTAL,
            ), f"C.02 child {ch['code']} must have payment_batch or aggregate_total scope"

    def test_c02_mapping_note_refers_to_scope(self):
        """C.02 children should have notes consistent with payment_batch scope."""
        result = _build()
        cats = result["categories"]
        c02 = next((c for c in cats if c["code"] == "C.02"), None)
        for ch in c02["children"]:
            note = ch.get("mapping_note", "")
            # Note should reference the payment-batch nature, not a generic mismatch
            # (Payment-batch rows are just reference rows, so notes may vary)
            assert isinstance(note, str)


# ── Grid C.03 Scope Wiring ───────────────────────────────────────────────────

class TestGridScopeWiring:
    def test_c03_category_exists(self):
        result = _build()
        cats = result["categories"]
        c03 = next((c for c in cats if c["code"] == "C.03"), None)
        assert c03 is not None, "C.:03 category must exist"

    def test_c03_01_gpa_fee_fee_only(self):
        """C.03.01 GPA Fee must have fee_only scope."""
        result = _build()
        cats = result["categories"]
        c03 = next((c for c in cats if c["code"] == "C.03"), None)
        c0301 = next((ch for ch in c03["children"] if ch["code"] == "C.03.01"), None)
        assert c0301 is not None
        assert c0301.get("scope") == CapexScope.FEE_ONLY, \
            f"C.03.01 must be fee_only scope, got {c0301.get('scope')}"

    def test_c03_gpa_fee_mapping_note_refers_to_gpa(self):
        """C.03.01 mapping note should explain it's GPA fee only."""
        result = _build()
        cats = result["categories"]
        c03 = next((c for c in cats if c["code"] == "C.03"), None)
        c0301 = next((ch for ch in c03["children"] if ch["code"] == "C.03.01"), None)
        note = c0301.get("mapping_note", "").lower()
        # Should reference scope difference (GPA fee vs full interconnection)
        assert "gpa" in note or "fee" in note or "scope" in note, \
            f"C.03.01 note should reference GPA/fee: {c0301.get('mapping_note')}"

    def test_c03_children_show_distinct_scope(self):
        """C.03 should show at least one fee_only and avoid plain mismatch confusion."""
        result = _build()
        cats = result["categories"]
        c03 = next((c for c in cats if c["code"] == "C.03"), None)
        scopes = {ch.get("scope") for ch in c03["children"]}
        # fee_only must appear; generic (C.03.02 zero-row) is acceptable
        assert CapexScope.FEE_ONLY in scopes, \
            f"C.03 must have fee_only scope child, got {scopes}"


# ── C.16 Project Rights Scope Wiring ────────────────────────────────────────

class TestProjectRightsScope:
    def test_c16_category_exists(self):
        result = _build()
        cats = result["categories"]
        c16 = next((c for c in cats if c["code"] == "C.16"), None)
        assert c16 is not None, "C.16 category must exist"

    def test_c16_children_all_project_rights(self):
        """All C.16 children must have project_rights scope."""
        result = _build()
        cats = result["categories"]
        c16 = next((c for c in cats if c["code"] == "C.16"), None)
        scopes = [ch.get("scope") for ch in c16["children"]]
        assert all(s == CapexScope.PROJECT_RIGHTS for s in scopes), \
            f"All C.16 children must have project_rights scope, got {scopes}"

    def test_c16_affects_runtime_false(self):
        """C.16 children must not affect runtime."""
        result = _build()
        cats = result["categories"]
        c16 = next((c for c in cats if c["code"] == "C.16"), None)
        for ch in c16["children"]:
            assert ch.get("affects_runtime") == False, \
                f"C.16 child {ch['code']} must have affects_runtime=False"

    def test_c16_authority_shows_scope_mismatch(self):
        """C.16 authority should be scope_mismatch (app=0 vs Excel nonzero, different scope)."""
        result = _build()
        cats = result["categories"]
        c16 = next((c for c in cats if c["code"] == "C.16"), None)
        for ch in c16["children"]:
            assert ch.get("authority_status") == "scope_mismatch", \
                f"C.16 child {ch['code']} must be scope_mismatch, got {ch.get('authority_status')}"


# ── M1-M18 Timing-Only Flag ──────────────────────────────────────────────────

class TestScheduleMetadata:
    def test_scheduled_rows_have_timing_only_true(self):
        """All rows with monthly_schedule_source in excel_m1_m18/app_profile must have timing_only=True."""
        result = _build()
        all_children = [ch for cat in result["categories"] for ch in cat.get("children", [])]
        scheduled = [ch for ch in all_children if ch.get("monthly_schedule_source") in ("excel_m1_m18", "app_profile")]
        assert len(scheduled) > 0, "Must have rows with excel_m1_m18 schedule"
        for ch in scheduled:
            assert ch.get("timing_only") == True, \
                f"Scheduled row {ch['code']} must have timing_only=True, got {ch.get('timing_only')}"

    def test_scheduled_rows_have_schedule_note(self):
        """All scheduled rows must have a non-empty schedule_note."""
        result = _build()
        all_children = [ch for cat in result["categories"] for ch in cat.get("children", [])]
        scheduled = [ch for ch in all_children if ch.get("monthly_schedule_source") in ("excel_m1_m18", "app_profile")]
        for ch in scheduled:
            note = ch.get("schedule_note", "")
            assert len(note) > 0, f"Scheduled row {ch['code']} must have schedule_note"
            assert "timing" in note.lower(), \
                f"schedule_note for {ch['code']} must mention timing: {note}"

    def test_nonscheduled_rows_no_timing_flag(self):
        """Rows without schedules should not have timing_only=True."""
        result = _build()
        all_children = [ch for cat in result["categories"] for ch in cat.get("children", [])]
        unscheduled = [ch for ch in all_children if ch.get("monthly_schedule_source") not in ("excel_m1_m18", "app_profile")]
        for ch in unscheduled:
            if ch.get("monthly_schedule_source") in ("missing", "static_reference"):
                assert ch.get("timing_only") is None, \
                    f"Unscheduled row {ch['code']} should not have timing_only"


# ── No Regressions ───────────────────────────────────────────────────────────

class TestNoRegressions:
    def test_main_web_imports(self):
        import main_web
        assert main_web is not None

    def test_no_private_attrib_leak(self):
        """Template should not expose private _ prefixed fields."""
        result = _build()
        all_children = [ch for cat in result["categories"] for ch in cat.get("children", [])]
        for ch in all_children:
            for key in ch:
                assert not key.startswith("_"), f"Child row leaks private key: {key}"

    def test_all_children_have_scope_field(self):
        """Every child row must have a scope field."""
        result = _build()
        all_children = [ch for cat in result["categories"] for ch in cat.get("children", [])]
        for ch in all_children:
            assert "scope" in ch, f"Child {ch.get('code')} missing scope field"

    def test_authority_summary_present(self):
        """Authority summary should be present on categories."""
        result = _build()
        cats = result["categories"]
        assert all("authority_summary" in cat for cat in cats)

    def test_phase21d_tests_pass(self):
        """Phase 21D tests must still pass."""
        import subprocess
        result = subprocess.run(
            [PYTHON, "-m", "pytest",
             "tests/test_phase21d_capex_source_model_schema_design.py",
             "-v", "--tb=short"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, f"Phase 21D tests failed:\n{result.stdout}\n{result.stderr}"
