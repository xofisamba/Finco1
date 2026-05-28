"""
Phase 21F: CAPEX Line Item Treatment Options Design — tests.
Design: user-selectable treatment enums + C.16 unresolved example.
"""

import pytest
import sys
sys.path.insert(0, '/opt/finco1')

from app.domain.capex.source_model import (
    AccountingTreatment,
    DepreciationTreatment,
    DepreciationLifeYears,
    TaxTreatment,
    FundingTreatment,
    ConstructionTimingTreatment,
    ScheduleType,
    CapexLineTreatment,
    C16_TREATMENT_EXAMPLE,
    C16_CHILD_TREATMENTS,
)


class TestAccountingTreatmentEnum:
    def test_enum_exists(self):
        assert hasattr(AccountingTreatment, 'DEPRECIABLE_CAPEX')
        assert hasattr(AccountingTreatment, 'INTANGIBLE_ASSET')
        assert hasattr(AccountingTreatment, 'DEVELOPMENT_COST')
        assert hasattr(AccountingTreatment, 'ACQUISITION_PREMIUM')
        assert hasattr(AccountingTreatment, 'LAND_OR_NON_DEPRECIABLE')
        assert hasattr(AccountingTreatment, 'FINANCING_COST')
        assert hasattr(AccountingTreatment, 'RESERVE_ACCOUNT')
        assert hasattr(AccountingTreatment, 'EXCLUDED_FROM_CAPEX')
        assert hasattr(AccountingTreatment, 'CUSTOM')

    def test_is_string_enum(self):
        assert isinstance(AccountingTreatment.DEPRECIABLE_CAPEX, str)


class TestDepreciationTreatmentEnum:
    def test_enum_exists(self):
        assert hasattr(DepreciationTreatment, 'DEPRECIABLE')
        assert hasattr(DepreciationTreatment, 'AMORTIZABLE')
        assert hasattr(DepreciationTreatment, 'NON_DEPRECIABLE')
        assert hasattr(DepreciationTreatment, 'EXPENSED')
        assert hasattr(DepreciationTreatment, 'EXCLUDED')
        assert hasattr(DepreciationTreatment, 'CUSTOM')


class TestTaxTreatmentEnum:
    def test_enum_exists(self):
        assert hasattr(TaxTreatment, 'TAX_DEPRECIABLE')
        assert hasattr(TaxTreatment, 'TAX_AMORTIZABLE')
        assert hasattr(TaxTreatment, 'NON_DEDUCTIBLE')
        assert hasattr(TaxTreatment, 'IMMEDIATELY_DEDUCTIBLE')
        assert hasattr(TaxTreatment, 'EXCLUDED_FROM_TAX_BASIS')
        assert hasattr(TaxTreatment, 'JURISDICTION_SPECIFIC')
        assert hasattr(TaxTreatment, 'CUSTOM')


class TestFundingTreatmentEnum:
    def test_enum_exists(self):
        assert hasattr(FundingTreatment, 'SENIOR_DEBT_ELIGIBLE')
        assert hasattr(FundingTreatment, 'EQUITY_ONLY')
        assert hasattr(FundingTreatment, 'SHL_ELIGIBLE')
        assert hasattr(FundingTreatment, 'INCLUDED_IN_TOTAL_FUNDING')
        assert hasattr(FundingTreatment, 'EXCLUDED_FROM_FUNDING')
        assert hasattr(FundingTreatment, 'CUSTOM')


class TestConstructionTimingTreatmentEnum:
    def test_enum_exists(self):
        assert hasattr(ConstructionTimingTreatment, 'INCLUDED_IN_CONSTRUCTION_DRAW')
        assert hasattr(ConstructionTimingTreatment, 'EXCLUDED_FROM_IDC')
        assert hasattr(ConstructionTimingTreatment, 'PAID_AT_FINANCIAL_CLOSE')
        assert hasattr(ConstructionTimingTreatment, 'PAID_AT_COD')
        assert hasattr(ConstructionTimingTreatment, 'PAID_ON_CUSTOM_SCHEDULE')
        assert hasattr(ConstructionTimingTreatment, 'TIMING_ONLY')


class TestScheduleTypeEnum:
    def test_enum_exists(self):
        assert hasattr(ScheduleType, 'M1_M18_IMPORTED')
        assert hasattr(ScheduleType, 'LINEAR')
        assert hasattr(ScheduleType, 'S_CURVE')
        assert hasattr(ScheduleType, 'ONE_OFF')
        assert hasattr(ScheduleType, 'CUSTOM')


class TestCapexLineTreatmentDataclass:
    def test_can_instantiate(self):
        t = CapexLineTreatment(
            excel_code="C.02",
            excel_name="EPC Contract",
            accounting=AccountingTreatment.DEPRECIABLE_CAPEX,
            depreciation=DepreciationTreatment.DEPRECIABLE,
            depreciation_life=DepreciationLifeYears.YEARS_20,
            tax=TaxTreatment.TAX_DEPRECIABLE,
            funding=FundingTreatment.SENIOR_DEBT_ELIGIBLE,
            construction_timing=ConstructionTimingTreatment.INCLUDED_IN_CONSTRUCTION_DRAW,
            schedule_type=ScheduleType.M1_M18_IMPORTED,
            user_selectable=True,
            treatment_resolved=True,
            treatment_note="EPC: depreciable, 20-year life, senior debt eligible.",
        )
        assert t.excel_code == "C.02"
        assert t.is_unresolved is False

    def test_is_unresolved_property(self):
        t_unresolved = CapexLineTreatment(
            excel_code="C.16",
            excel_name="Project Rights",
            user_selectable=True,
            treatment_resolved=False,
        )
        assert t_unresolved.is_unresolved is True

        t_resolved = CapexLineTreatment(
            excel_code="C.01",
            excel_name="Wind Turbines",
            accounting=AccountingTreatment.DEPRECIABLE_CAPEX,
            user_selectable=True,
            treatment_resolved=True,
        )
        assert t_resolved.is_unresolved is False

    def test_summarise(self):
        t = CapexLineTreatment(
            excel_code="C.16.03",
            excel_name="Land Purchase",
            accounting=AccountingTreatment.LAND_OR_NON_DEPRECIABLE,
            depreciation=DepreciationTreatment.NON_DEPRECIABLE,
            tax=TaxTreatment.NON_DEDUCTIBLE,
            funding=FundingTreatment.SENIOR_DEBT_ELIGIBLE,
            user_selectable=True,
            treatment_resolved=False,
        )
        s = t.summarise()
        assert "land_or_non_depreciable" in s
        assert "non_depreciable" in s
        assert "non_deductible" in s
        assert "unresolved" in s.lower()


class TestC16UnresolvedExample:
    def test_c16_example_exists(self):
        assert C16_TREATMENT_EXAMPLE is not None
        assert C16_TREATMENT_EXAMPLE.excel_code == "C.16"
        assert C16_TREATMENT_EXAMPLE.treatment_resolved is False
        assert C16_TREATMENT_EXAMPLE.user_selectable is True

    def test_c16_children_exist(self):
        assert "C.16.01" in C16_CHILD_TREATMENTS
        assert "C.16.02" in C16_CHILD_TREATMENTS
        assert "C.16.03" in C16_CHILD_TREATMENTS

    def test_c16_all_unresolved(self):
        for code, treatment in C16_CHILD_TREATMENTS.items():
            assert treatment.treatment_resolved is False, f"{code} should be unresolved"
            assert treatment.user_selectable is True, f"{code} should be user-selectable"

    def test_c16_note_explains_pending(self):
        note = C16_TREATMENT_EXAMPLE.treatment_note
        assert "NOT wired to runtime" in note or "not wired" in note.lower()
        assert "unresolved" in note.lower() or "pending" in note.lower()


class TestSchemaInertness:
    def test_main_web_imports(self):
        import main_web
        assert True