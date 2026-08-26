"""Stage C3B3C2 — Typed tax policy, SHL deductibility, corrected arithmetic tests.

Arithmetic: deductible-only method (C3B3C2 fix — no double-count).
  taxable_income = EBITDA - dep - (senior + SHL_deductible) + ATAD_disallowed + reintegration
  shl_non_deductible_keur = audit field ONLY, NOT added to taxable income.

Controlled identity (atad_applies=False, ebitda=5000, dep=1000, senior=500, SHL=300):
  FULLY_DEDUCTIBLE:     5000-1000-(500+300) = 3200
  FULLY_NON_DEDUCTIBLE: 5000-1000-500       = 3500  (NOT 3800)
  CUSTOM 50%:           5000-1000-(500+150)  = 3350  (NOT 3500)
"""
from __future__ import annotations

import importlib

import pytest

from finco_core.inputs._models import (
    ShlInterestDeductibilityMode,
    TaxLossUtilisationGate,
    TaxPeriodisationMode,
    ShlAccountingTreatment,
    ShlPaymentMethod,
    TaxParams,
)
from finco_core.waterfall.tax_engine import compute_period_tax
from finco_core.inputs.serialization import project_inputs_to_dict, project_inputs_from_dict
from app.project_factories import (
    create_default_oborovo,
    create_default_oborovo_legacy_calibration,
    create_default_tuho_wind1,
)


class TestTaxParamsValidation:
    def test_custom_pct_required(self):
        with pytest.raises(ValueError, match="shl_interest_deductible_pct is required"):
            TaxParams(
                shl_interest_deductibility=ShlInterestDeductibilityMode.CUSTOM_DEDUCTIBLE_PERCENTAGE,
                shl_interest_deductible_pct=None,
            )

    def test_custom_pct_out_of_range_high(self):
        with pytest.raises(ValueError, match=r"\[0, 1\]"):
            TaxParams(
                shl_interest_deductibility=ShlInterestDeductibilityMode.CUSTOM_DEDUCTIBLE_PERCENTAGE,
                shl_interest_deductible_pct=1.5,
            )

    def test_custom_pct_out_of_range_negative(self):
        with pytest.raises(ValueError, match=r"\[0, 1\]"):
            TaxParams(
                shl_interest_deductibility=ShlInterestDeductibilityMode.CUSTOM_DEDUCTIBLE_PERCENTAGE,
                shl_interest_deductible_pct=-0.1,
            )

    def test_pct_bool_true_rejected(self):
        with pytest.raises(ValueError, match="bool"):
            TaxParams(
                shl_interest_deductibility=ShlInterestDeductibilityMode.CUSTOM_DEDUCTIBLE_PERCENTAGE,
                shl_interest_deductible_pct=True,
            )

    def test_pct_bool_false_rejected(self):
        with pytest.raises(ValueError, match="bool"):
            TaxParams(
                shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE,
                shl_interest_deductible_pct=False,
            )

    def test_pct_nan_rejected(self):
        with pytest.raises(ValueError, match="finite"):
            TaxParams(
                shl_interest_deductibility=ShlInterestDeductibilityMode.CUSTOM_DEDUCTIBLE_PERCENTAGE,
                shl_interest_deductible_pct=float("nan"),
            )

    def test_pct_inf_rejected(self):
        with pytest.raises(ValueError, match="finite"):
            TaxParams(
                shl_interest_deductibility=ShlInterestDeductibilityMode.CUSTOM_DEDUCTIBLE_PERCENTAGE,
                shl_interest_deductible_pct=float("inf"),
            )

    def test_pct_neg_inf_rejected(self):
        with pytest.raises(ValueError, match="finite"):
            TaxParams(
                shl_interest_deductibility=ShlInterestDeductibilityMode.CUSTOM_DEDUCTIBLE_PERCENTAGE,
                shl_interest_deductible_pct=float("-inf"),
            )

    def test_fully_deductible_with_wrong_pct(self):
        with pytest.raises(ValueError, match="FULLY_DEDUCTIBLE"):
            TaxParams(
                shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE,
                shl_interest_deductible_pct=0.5,
            )

    def test_fully_non_deductible_with_wrong_pct(self):
        with pytest.raises(ValueError, match="FULLY_NON_DEDUCTIBLE"):
            TaxParams(
                shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE,
                shl_interest_deductible_pct=0.5,
            )

    def test_workbook_periodisation_blocked_unconditionally(self):
        with pytest.raises(ValueError, match="WORKBOOK_MODEL_YEAR_PAIRING"):
            TaxParams(tax_periodisation_mode=TaxPeriodisationMode.WORKBOOK_MODEL_YEAR_PAIRING)

    def test_workbook_periodisation_blocked_without_cash_tax_flag(self):
        with pytest.raises(ValueError, match="WORKBOOK_MODEL_YEAR_PAIRING"):
            TaxParams(
                tax_periodisation_mode=TaxPeriodisationMode.WORKBOOK_MODEL_YEAR_PAIRING,
                clean_cash_tax_timing_enabled=False,
            )

    def test_subject_to_limitations_without_thin_cap_blocked(self):
        with pytest.raises(ValueError, match="limitation mechanism"):
            TaxParams(
                shl_interest_deductibility=ShlInterestDeductibilityMode.SUBJECT_TO_LIMITATIONS,
                thin_cap_enabled=False,
            )

    def test_subject_to_limitations_with_thin_cap_allowed(self):
        tp = TaxParams(
            shl_interest_deductibility=ShlInterestDeductibilityMode.SUBJECT_TO_LIMITATIONS,
            thin_cap_enabled=True,
        )
        assert tp.shl_interest_deductibility == ShlInterestDeductibilityMode.SUBJECT_TO_LIMITATIONS

    def test_foreign_shl_cap_requires_fully_non_deductible(self):
        with pytest.raises(ValueError, match="foreign_shl_interest_cap_enabled"):
            TaxParams(
                foreign_shl_interest_cap_enabled=True,
                shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE,
            )

    def test_foreign_shl_cap_with_custom_mode_blocked(self):
        with pytest.raises(ValueError, match="foreign_shl_interest_cap_enabled"):
            TaxParams(
                foreign_shl_interest_cap_enabled=True,
                shl_interest_deductibility=ShlInterestDeductibilityMode.CUSTOM_DEDUCTIBLE_PERCENTAGE,
                shl_interest_deductible_pct=0.5,
            )

    def test_foreign_shl_cap_with_fully_non_deductible_allowed(self):
        tp = TaxParams(
            foreign_shl_interest_cap_enabled=True,
            shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE,
        )
        assert tp.foreign_shl_interest_cap_enabled is True

    def test_defaults_are_backward_compat(self):
        tp = TaxParams()
        assert tp.shl_interest_deductibility == ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE
        assert tp.shl_interest_deductible_pct is None
        assert tp.foreign_shl_interest_cap_enabled is False
        assert tp.tax_loss_utilisation_gate == TaxLossUtilisationGate.TAXABLE_INCOME_POSITIVE
        assert tp.tax_periodisation_mode == TaxPeriodisationMode.CALENDAR_TAX_YEAR
        assert tp.shl_construction_accounting == ShlAccountingTreatment.EXPENSE_TO_PNL
        assert tp.shl_construction_payment == ShlPaymentMethod.PIK_TO_SHL_BALANCE

    def test_boundary_pct_zero_accepted(self):
        tp = TaxParams(
            shl_interest_deductibility=ShlInterestDeductibilityMode.CUSTOM_DEDUCTIBLE_PERCENTAGE,
            shl_interest_deductible_pct=0.0,
        )
        assert tp.shl_interest_deductible_pct == 0.0

    def test_boundary_pct_one_accepted(self):
        tp = TaxParams(
            shl_interest_deductibility=ShlInterestDeductibilityMode.CUSTOM_DEDUCTIBLE_PERCENTAGE,
            shl_interest_deductible_pct=1.0,
        )
        assert tp.shl_interest_deductible_pct == 1.0


class TestShlNonDeductibleFraction:
    def test_fully_deductible(self):
        tp = TaxParams(shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE)
        assert tp.shl_non_deductible_fraction == 0.0

    def test_fully_non_deductible(self):
        tp = TaxParams(shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE)
        assert tp.shl_non_deductible_fraction == 1.0

    def test_custom_50pct(self):
        tp = TaxParams(
            shl_interest_deductibility=ShlInterestDeductibilityMode.CUSTOM_DEDUCTIBLE_PERCENTAGE,
            shl_interest_deductible_pct=0.5,
        )
        assert abs(tp.shl_non_deductible_fraction - 0.5) < 1e-12

    def test_custom_0pct(self):
        tp = TaxParams(
            shl_interest_deductibility=ShlInterestDeductibilityMode.CUSTOM_DEDUCTIBLE_PERCENTAGE,
            shl_interest_deductible_pct=0.0,
        )
        assert tp.shl_non_deductible_fraction == 1.0

    def test_custom_100pct(self):
        tp = TaxParams(
            shl_interest_deductibility=ShlInterestDeductibilityMode.CUSTOM_DEDUCTIBLE_PERCENTAGE,
            shl_interest_deductible_pct=1.0,
        )
        assert tp.shl_non_deductible_fraction == 0.0

    def test_subject_to_limitations_raises(self):
        tp = TaxParams(
            shl_interest_deductibility=ShlInterestDeductibilityMode.SUBJECT_TO_LIMITATIONS,
            thin_cap_enabled=True,
        )
        with pytest.raises(NotImplementedError):
            _ = tp.shl_non_deductible_fraction


class TestComputePeriodTaxArithmetic:
    BASE = dict(
        ebitda_keur=5000.0,
        depreciation_keur=1000.0,
        senior_interest_keur=500.0,
        shl_interest_keur=300.0,
        loss_carryforward_keur=0.0,
        tax_rate=0.10,
        atad_applies=False,
    )

    def test_none_mode_legacy_fully_deductible(self):
        r = compute_period_tax(**self.BASE, shl_interest_deductibility=None)
        assert r.shl_non_deductible_keur == 0.0
        assert abs(r.taxable_income_keur - 3200.0) < 1e-9

    def test_fully_deductible_taxable_income(self):
        r = compute_period_tax(
            **self.BASE,
            shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE,
        )
        assert r.shl_non_deductible_keur == 0.0
        assert abs(r.taxable_income_keur - 3200.0) < 1e-9

    def test_fully_non_deductible_taxable_income(self):
        r = compute_period_tax(
            **self.BASE,
            shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE,
        )
        assert abs(r.shl_non_deductible_keur - 300.0) < 1e-9
        assert abs(r.taxable_income_keur - 3500.0) < 1e-9

    def test_custom_50pct_taxable_income(self):
        r = compute_period_tax(
            **self.BASE,
            shl_interest_deductibility=ShlInterestDeductibilityMode.CUSTOM_DEDUCTIBLE_PERCENTAGE,
            shl_interest_deductible_pct=0.5,
        )
        assert abs(r.shl_non_deductible_keur - 150.0) < 1e-9
        assert abs(r.taxable_income_keur - 3350.0) < 1e-9

    def test_accounting_ebt_reconciles_fully_non_deductible(self):
        ebt = 5000.0 - 1000.0 - 500.0 - 300.0  # 3200
        expected = ebt + 300.0  # 3500
        r = compute_period_tax(
            **self.BASE,
            shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE,
        )
        assert abs(r.taxable_income_keur - expected) < 1e-9

    def test_accounting_ebt_reconciles_custom_50pct(self):
        ebt = 5000.0 - 1000.0 - 500.0 - 300.0  # 3200
        expected = ebt + 150.0  # 3350
        r = compute_period_tax(
            **self.BASE,
            shl_interest_deductibility=ShlInterestDeductibilityMode.CUSTOM_DEDUCTIBLE_PERCENTAGE,
            shl_interest_deductible_pct=0.5,
        )
        assert abs(r.taxable_income_keur - expected) < 1e-9

    def test_subject_to_limitations_raises(self):
        with pytest.raises(NotImplementedError, match="C3B3C_BLOCKED_TUHO_THIN_CAP_FORMULA"):
            compute_period_tax(
                **self.BASE,
                shl_interest_deductibility=ShlInterestDeductibilityMode.SUBJECT_TO_LIMITATIONS,
            )

    def test_no_double_count(self):
        r = compute_period_tax(
            **self.BASE,
            shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE,
        )
        assert abs(r.taxable_income_keur - 3800.0) > 1.0, "Double-count detected"
        assert abs(r.taxable_income_keur - 3500.0) < 1e-9

    def test_tax_correct(self):
        r = compute_period_tax(
            **self.BASE,
            shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE,
        )
        assert abs(r.tax_keur - 350.0) < 1e-9

    def test_zero_shl_modes_equivalent(self):
        base_zero = dict(self.BASE, shl_interest_keur=0.0)
        r_ded = compute_period_tax(**base_zero, shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE)
        r_non = compute_period_tax(**base_zero, shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE)
        assert abs(r_ded.taxable_income_keur - r_non.taxable_income_keur) < 1e-9

    def test_atad_applied_to_deductible_interest_only(self):
        r = compute_period_tax(
            ebitda_keur=1000.0,
            depreciation_keur=0.0,
            senior_interest_keur=200.0,
            shl_interest_keur=200.0,
            loss_carryforward_keur=0.0,
            tax_rate=0.10,
            atad_applies=True,
            atad_min_threshold_keur=3000.0,
            shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE,
        )
        assert abs(r.taxable_income_keur - 800.0) < 1e-9
        assert r.disallowed_interest_keur == 0.0


class TestOborovoTaxPolicy:
    def test_shl_interest_deductibility_is_fully_non_deductible(self):
        assert create_default_oborovo().tax.shl_interest_deductibility == ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE

    def test_foreign_shl_cap_enabled(self):
        assert create_default_oborovo().tax.foreign_shl_interest_cap_enabled is True

    def test_thin_cap_disabled(self):
        assert create_default_oborovo().tax.thin_cap_enabled is False

    def test_loss_gate_ebt_positive(self):
        assert create_default_oborovo().tax.tax_loss_utilisation_gate == TaxLossUtilisationGate.EBT_POSITIVE

    def test_tax_periodisation_calendar(self):
        assert create_default_oborovo().tax.tax_periodisation_mode == TaxPeriodisationMode.CALENDAR_TAX_YEAR

    def test_shl_construction_accounting_expense_to_pnl(self):
        assert create_default_oborovo().tax.shl_construction_accounting == ShlAccountingTreatment.EXPENSE_TO_PNL

    def test_shl_construction_payment_pik_to_shl_balance(self):
        assert create_default_oborovo().tax.shl_construction_payment == ShlPaymentMethod.PIK_TO_SHL_BALANCE

    def test_non_deductible_fraction_is_100pct(self):
        assert create_default_oborovo().tax.shl_non_deductible_fraction == 1.0

    def test_oborovo_shl_idc_factory_contract(self):
        # Clean production derives construction PIK from typed dates and rates;
        # the historical scalar remains isolated in explicit legacy calibration.
        assert create_default_oborovo().financing.shl_idc_keur == 0.0
        legacy_shl_idc = (
            create_default_oborovo_legacy_calibration().financing.shl_idc_keur
        )
        assert abs(legacy_shl_idc - 1169.662) < 1.0

    def test_oborovo_100pct_non_deductible_applied_in_compute(self):
        inputs = create_default_oborovo()
        shl_keur = 500.0
        r = compute_period_tax(
            ebitda_keur=3000.0,
            depreciation_keur=800.0,
            senior_interest_keur=300.0,
            shl_interest_keur=shl_keur,
            loss_carryforward_keur=0.0,
            tax_rate=inputs.tax.corporate_rate,
            atad_applies=True,
            atad_ebitda_limit=inputs.tax.atad_ebitda_limit,
            atad_min_threshold_keur=inputs.tax.atad_min_interest_keur,
            shl_interest_deductibility=inputs.tax.shl_interest_deductibility,
        )
        assert abs(r.shl_non_deductible_keur - shl_keur) < 1e-9
        assert abs(r.deductible_interest_keur - 300.0) < 1e-6


class TestTuhoTaxPolicy:
    def test_shl_interest_deductibility_is_subject_to_limitations(self):
        assert create_default_tuho_wind1().tax.shl_interest_deductibility == ShlInterestDeductibilityMode.SUBJECT_TO_LIMITATIONS

    def test_foreign_shl_cap_disabled(self):
        assert create_default_tuho_wind1().tax.foreign_shl_interest_cap_enabled is False

    def test_thin_cap_enabled(self):
        assert create_default_tuho_wind1().tax.thin_cap_enabled is True

    def test_loss_gate_ebt_positive(self):
        assert create_default_tuho_wind1().tax.tax_loss_utilisation_gate == TaxLossUtilisationGate.EBT_POSITIVE

    def test_tuho_shl_idc_factory_contract(self):
        # SOURCE_EVIDENCE_PARTIAL: factory-configuration contract only, not an
        # independent source-vector proof. Genuine source comparison requires the
        # TUHO workbook extraction fixture.
        shl_idc = create_default_tuho_wind1().financing.shl_idc_keur
        assert abs(shl_idc - 3568.688) < 1.0, f"TUHO SHL IDC = {shl_idc:.3f} kEUR, expected ~3568.688"

    def test_subject_to_limitations_fails_closed(self):
        with pytest.raises(NotImplementedError, match="C3B3C_BLOCKED_TUHO_THIN_CAP_FORMULA"):
            compute_period_tax(
                ebitda_keur=5000.0,
                depreciation_keur=500.0,
                senior_interest_keur=400.0,
                shl_interest_keur=200.0,
                loss_carryforward_keur=0.0,
                tax_rate=0.18,
                shl_interest_deductibility=ShlInterestDeductibilityMode.SUBJECT_TO_LIMITATIONS,
            )

    def test_tuho_does_not_inherit_oborovo_non_deductible(self):
        tuho = create_default_tuho_wind1()
        oborovo = create_default_oborovo()
        assert tuho.tax.shl_interest_deductibility != oborovo.tax.shl_interest_deductibility
        assert tuho.tax.foreign_shl_interest_cap_enabled is False
        assert oborovo.tax.foreign_shl_interest_cap_enabled is True


class TestEbtPositiveGateSourceOnly:
    """EBT_POSITIVE is source/workbook metadata — not an active runtime mode.

    Both Oborovo and TUHO carry tax_loss_utilisation_gate=EBT_POSITIVE as
    source-workbook evidence. The legacy runtime does NOT execute EBT_POSITIVE
    logic — it continues with TAXABLE_INCOME_POSITIVE behavior unchanged.

    SOURCE_POLICY_CAPTURED_RUNTIME_NOT_PROMOTED.
    Do not expose EBT_POSITIVE as BOUND until the execution path is proven.
    """

    def test_oborovo_ebt_positive_is_source_metadata(self):
        p = create_default_oborovo()
        assert p.tax.tax_loss_utilisation_gate == TaxLossUtilisationGate.EBT_POSITIVE

    def test_tuho_ebt_positive_is_source_metadata(self):
        p = create_default_tuho_wind1()
        assert p.tax.tax_loss_utilisation_gate == TaxLossUtilisationGate.EBT_POSITIVE

    def test_ebt_positive_not_equal_taxable_income_positive(self):
        assert TaxLossUtilisationGate.EBT_POSITIVE != TaxLossUtilisationGate.TAXABLE_INCOME_POSITIVE


class TestCanonicalCleanEngineBlock:
    VERDICT = "C3B3C_BLOCKED_RUNTIME_WIRING"

    def test_block_verdict(self):
        assert self.VERDICT == "C3B3C_BLOCKED_RUNTIME_WIRING"

    def test_canonical_engine_importable(self):
        mod = importlib.import_module("financial_engine.tax.engine")
        assert hasattr(mod, "calculate_tax")

    def test_period_interest_input_has_shl_field(self):
        from financial_engine.inputs import PeriodInterestInput
        p = PeriodInterestInput(period_index=1, senior_interest_keur=100.0, shl_interest_keur=50.0)
        assert p.shl_interest_keur == 50.0
        assert p.total_interest_keur == 150.0


class TestNoIdentityDispatch:
    def test_oborovo_clone_with_fully_deductible(self):
        import dataclasses
        inputs = create_default_oborovo()
        new_tax = dataclasses.replace(
            inputs.tax,
            shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE,
            foreign_shl_interest_cap_enabled=False,
        )
        r = compute_period_tax(
            ebitda_keur=2000.0, depreciation_keur=400.0,
            senior_interest_keur=200.0, shl_interest_keur=100.0,
            loss_carryforward_keur=0.0, tax_rate=new_tax.corporate_rate,
            atad_applies=False,
            shl_interest_deductibility=new_tax.shl_interest_deductibility,
        )
        assert r.shl_non_deductible_keur == 0.0
        assert abs(r.taxable_income_keur - 1300.0) < 1e-9

    def test_generic_project_with_fully_non_deductible(self):
        import dataclasses
        inputs = create_default_oborovo()
        new_tax = dataclasses.replace(
            inputs.tax,
            shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE,
        )
        r = compute_period_tax(
            ebitda_keur=2000.0, depreciation_keur=400.0,
            senior_interest_keur=200.0, shl_interest_keur=100.0,
            loss_carryforward_keur=0.0, tax_rate=new_tax.corporate_rate,
            atad_applies=False,
            shl_interest_deductibility=new_tax.shl_interest_deductibility,
        )
        assert abs(r.shl_non_deductible_keur - 100.0) < 1e-9
        assert abs(r.taxable_income_keur - 1400.0) < 1e-9


class TestSerializationRoundTrip:
    def test_oborovo_roundtrip_preserves_new_fields(self):
        inputs = create_default_oborovo()
        d = project_inputs_to_dict(inputs)
        tax_d = d["tax"]
        assert tax_d["shl_interest_deductibility"] == "fully_non_deductible"
        assert tax_d["foreign_shl_interest_cap_enabled"] is True
        assert tax_d["tax_loss_utilisation_gate"] == "ebt_positive"
        assert tax_d["tax_periodisation_mode"] == "calendar_tax_year"
        assert tax_d["shl_construction_accounting"] == "expense_to_pnl"
        assert tax_d["shl_construction_payment"] == "pik_to_shl_balance"
        assert tax_d["shl_interest_deductible_pct"] is None

        restored = project_inputs_from_dict(d)
        assert restored.tax.shl_interest_deductibility == ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE
        assert restored.tax.foreign_shl_interest_cap_enabled is True
        assert restored.tax.tax_loss_utilisation_gate == TaxLossUtilisationGate.EBT_POSITIVE

    def test_old_payload_without_new_fields_uses_defaults(self):
        inputs = create_default_oborovo()
        d = project_inputs_to_dict(inputs)
        for key in [
            "shl_interest_deductibility", "shl_interest_deductible_pct",
            "foreign_shl_interest_cap_enabled", "tax_loss_utilisation_gate",
            "tax_periodisation_mode", "shl_construction_accounting", "shl_construction_payment",
        ]:
            d["tax"].pop(key, None)
        restored = project_inputs_from_dict(d)
        assert restored.tax.shl_interest_deductibility == ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE
        assert restored.tax.foreign_shl_interest_cap_enabled is False
        assert restored.tax.tax_loss_utilisation_gate == TaxLossUtilisationGate.TAXABLE_INCOME_POSITIVE
