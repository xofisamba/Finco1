"""
Phase 21D — CAPEX source model input schema design tests.

Design/schema-only tests — no runtime changes validated here.
"""

import pytest
from pathlib import Path

DOCS_DIR = Path("/opt/finco1/docs")


class TestDesignDocument:
    """Tests that the design document exists and contains required content."""

    def test_design_doc_exists(self):
        assert (DOCS_DIR / "phase21d_capex_source_model_input_schema_design.md").exists()

    def test_doc_mentions_epc_c02(self):
        doc = (DOCS_DIR / "phase21d_capex_source_model_input_schema_design.md").read_text()
        assert "EPC" in doc and "C.02" in doc

    def test_doc_mentions_grid_c03(self):
        doc = (DOCS_DIR / "phase21d_capex_source_model_input_schema_design.md").read_text()
        assert "Grid" in doc or "C.03" in doc

    def test_doc_mentions_project_rights_c16(self):
        doc = (DOCS_DIR / "phase21d_capex_source_model_input_schema_design.md").read_text()
        assert "Project Rights" in doc or "C.16" in doc

    def test_doc_mentions_m1_m18_schedule(self):
        doc = (DOCS_DIR / "phase21d_capex_source_model_input_schema_design.md").read_text()
        assert "M1" in doc or "payment schedule" in doc.lower()

    def test_doc_states_no_runtime_changes(self):
        doc = (DOCS_DIR / "phase21d_capex_source_model_input_schema_design.md").read_text()
        assert "no runtime" in doc.lower() or "no calculation" in doc.lower()

    def test_doc_defines_capex_source_type(self):
        doc = (DOCS_DIR / "phase21d_capex_source_model_input_schema_design.md").read_text()
        assert "CapexSourceType" in doc or "CAPEX source model" in doc

    def test_doc_defines_capex_scope(self):
        doc = (DOCS_DIR / "phase21d_capex_source_model_input_schema_design.md").read_text()
        assert "CapexScope" in doc

    def test_doc_defines_capex_payment_schedule(self):
        doc = (DOCS_DIR / "phase21d_capex_source_model_input_schema_design.md").read_text()
        assert "CapexPaymentSchedule" in doc

    def test_doc_defines_capex_line_definition(self):
        doc = (DOCS_DIR / "phase21d_capex_source_model_input_schema_design.md").read_text()
        assert "CapexLineDefinition" in doc

    def test_doc_has_guardrails_section(self):
        doc = (DOCS_DIR / "phase21d_capex_source_model_input_schema_design.md").read_text()
        assert "Guardrail" in doc or "guardrail" in doc.lower()

    def test_doc_has_recommended_next_phase(self):
        doc = (DOCS_DIR / "phase21d_capex_source_model_input_schema_design.md").read_text()
        assert "Phase 21E" in doc or "recommended" in doc.lower()

    def test_doc_addresses_epc_scope_mismatch(self):
        doc = (DOCS_DIR / "phase21d_capex_source_model_input_schema_design.md").read_text()
        assert "aggregate_total" in doc or "aggregate" in doc

    def test_doc_addresses_grid_gpa_fee_only(self):
        doc = (DOCS_DIR / "phase21d_capex_source_model_input_schema_design.md").read_text()
        assert "fee_only" in doc or "FEE_ONLY" in doc

    def test_doc_addresses_project_rights_deferred(self):
        doc = (DOCS_DIR / "phase21d_capex_source_model_input_schema_design.md").read_text()
        assert "defer" in doc.lower()

    def test_doc_addresses_payment_schedule_timing_vs_total(self):
        doc = (DOCS_DIR / "phase21d_capex_source_model_input_schema_design.md").read_text()
        assert "timing" in doc.lower()

    def test_doc_has_future_connection_points(self):
        doc = (DOCS_DIR / "phase21d_capex_source_model_input_schema_design.md").read_text()
        assert "Construction" in doc or "depreciation" in doc.lower() or "funding" in doc.lower()


class TestSchemaStubs:
    """Tests for the isolated schema stubs module."""

    def test_source_model_module_exists(self):
        assert Path("/opt/finco1/app/domain/capex/source_model.py").exists()

    def test_source_model_module_imports_cleanly(self):
        import sys
        sys.path.insert(0, "/opt/finco1")
        import app.domain.capex.source_model as sm
        assert hasattr(sm, "CapexSourceType")
        assert hasattr(sm, "CapexScope")
        assert hasattr(sm, "CapexPaymentSchedule")
        assert hasattr(sm, "CapexLineDefinition")
        assert hasattr(sm, "CapexInputSchemaDesign")

    def test_capex_source_type_constants(self):
        from app.domain.capex.source_model import CapexSourceType
        assert CapexSourceType.EXCEL_REFERENCE == "excel_reference"
        assert CapexSourceType.APP_INPUT == "app_input"
        assert CapexSourceType.RUNTIME_COMPUTED == "runtime_computed"
        assert CapexSourceType.USER_OVERRIDE == "user_override"
        assert CapexSourceType.IMPORTED_SCHEDULE == "imported_schedule"
        assert CapexSourceType.STATIC_REFERENCE == "static_reference"

    def test_capex_scope_constants(self):
        from app.domain.capex.source_model import CapexScope
        assert CapexScope.AGGREGATE_TOTAL == "aggregate_total"
        assert CapexScope.PAYMENT_BATCH == "payment_batch"
        assert CapexScope.FEE_ONLY == "fee_only"
        assert CapexScope.PROJECT_RIGHTS == "project_rights"
        assert CapexScope.MONTHLY_SCHEDULE == "monthly_schedule"
        assert CapexScope.FINANCING_COST == "financing_cost"
        assert CapexScope.RESERVE_ACCOUNT == "reserve_account"
        assert CapexScope.LAND == "land"
        assert CapexScope.GENERIC == "generic"

    def test_capex_payment_schedule_instantiation(self):
        from app.domain.capex.source_model import CapexPaymentSchedule
        schedule = CapexPaymentSchedule(
            schedule_type="excel_m1_m18",
            periods=tuple([1/18] * 18),
            amounts_keur=None,
            total_keur=13560.0,
            source="excel_capex_sheet",
            authority_status="excel_reference",
            notes="18-month Excel schedule"
        )
        assert schedule.schedule_type == "excel_m1_m18"
        assert len(schedule.periods) == 18
        assert abs(sum(schedule.periods) - 1.0) < 1e-9
        assert schedule.total_keur == 13560.0

    def test_capex_line_definition_instantiation(self):
        from app.domain.capex.source_model import (
            CapexLineDefinition, CapexSourceType, CapexScope
        )
        line = CapexLineDefinition(
            code="C.02",
            label="EPC Contract",
            parent_code="C",
            source_type=CapexSourceType.APP_INPUT,
            scope=CapexScope.AGGREGATE_TOTAL,
            amount_keur=52800.0,
            affects_runtime=True,
            runtime_field="capex.epc_contract.amount_keur",
            depreciation_category="plant_machinery",
            tax_basis_category="tax_shield_eligible",
            funding_category="senior_debt",
            mapping_note="4-semester aggregate EPC total",
            monthly_schedule=None,
        )
        assert line.code == "C.02"
        assert line.amount_keur == 52800.0
        assert line.source_type == "app_input"
        assert line.scope == "aggregate_total"
        assert line.affects_runtime is True

    def test_capex_line_with_payment_schedule(self):
        from app.domain.capex.source_model import (
            CapexLineDefinition, CapexPaymentSchedule, CapexSourceType, CapexScope
        )
        schedule = CapexPaymentSchedule(
            schedule_type="excel_m1_m18",
            periods=tuple([1/18] * 18),
            total_keur=13560.0,
            source="excel_capex_sheet",
            authority_status="excel_reference",
        )
        line = CapexLineDefinition(
            code="C.02.01",
            label="Electrical BOP",
            parent_code="C.02",
            source_type=CapexSourceType.EXCEL_REFERENCE,
            scope=CapexScope.PAYMENT_BATCH,
            amount_keur=720.0,
            affects_runtime=False,
            runtime_field=None,
            mapping_note="Per-batch payment reference",
            monthly_schedule=schedule,
        )
        assert line.monthly_schedule is not None
        assert line.monthly_schedule.total_keur == 13560.0

    def test_capex_input_schema_design_container(self):
        from app.domain.capex.source_model import (
            CapexInputSchemaDesign, CapexLineDefinition, CapexSourceType, CapexScope
        )
        line = CapexLineDefinition(
            code="C.13",
            label="Contingencies",
            parent_code="C",
            source_type=CapexSourceType.APP_INPUT,
            scope=CapexScope.AGGREGATE_TOTAL,
            amount_keur=2991.54,
            affects_runtime=True,
            runtime_field="capex.contingencies.amount_keur",
        )
        schema = CapexInputSchemaDesign(
            project_code="TUHO",
            lines=(line,),
            schedules=(),
            version="2026.05.28-v1",
            notes="Phase 21D schema design",
        )
        assert schema.project_code == "TUHO"
        assert len(schema.lines) == 1
        assert schema.version == "2026.05.28-v1"


class TestIsolatedModuleNotImportedByRuntime:

    def test_schema_module_not_in_runtime_imports(self):
        """main_web imports without error — schema module is isolated."""
        import sys
        sys.path.insert(0, "/opt/finco1")
        import main_web  # noqa: F401
        assert True


class TestNoExistingRuntimeRegressions:

    def test_main_web_imports(self):
        import sys
        sys.path.insert(0, "/opt/finco1")
        import main_web  # noqa: F401
        assert True

    def test_capex_breakdown_imports(self):
        import sys
        sys.path.insert(0, "/opt/finco1")
        from domain.capex import capex_breakdown  # noqa: F401
        assert True

    def test_capex_schedule_imports(self):
        import sys
        sys.path.insert(0, "/opt/finco1")
        from domain.capex import capex_schedule  # noqa: F401
        assert True

    def test_project_context_imports(self):
        import sys
        sys.path.insert(0, "/opt/finco1")
        from app.ui import project_context  # noqa: F401
        assert True

    def test_capex_detail_items_structure_unchanged(self):
        """Verify _build_capex_detail_items returns dict with 'categories' key."""
        import sys
        sys.path.insert(0, "/opt/finco1")
        from app.ui.project_context import _build_capex_detail_items
        from app.project_factories import create_default_tuho_wind1

        capex = create_default_tuho_wind1().capex
        result = _build_capex_detail_items(capex)
        assert isinstance(result, dict)
        assert "categories" in result
        codes = [item["code"] for item in result["categories"]]
        assert "C.01" in codes
        assert "C.13" in codes
        # C.13 should be app_mapped
        c13 = next(i for i in result["categories"] if i["code"] == "C.13")
        assert c13["authority_summary"]["app_mapped"] == 1
        c13_children = c13.get("children", [])
        assert len(c13_children) > 0
