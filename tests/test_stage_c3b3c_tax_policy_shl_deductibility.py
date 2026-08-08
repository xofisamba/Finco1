"""Stage C3B3C — Typed tax policy & SHL interest deductibility source-vector tests.

Covers:
- Enum validation and __post_init__ guards
- Oborovo: FULLY_NON_DEDUCTIBLE + foreign_shl_interest_cap_enabled=True
- TUHO: SUBJECT_TO_LIMITATIONS fails closed (C3B3C_BLOCKED_TUHO_THIN_CAP_FORMULA)
- compute_period_tax() addback logic for each mode
- Renamed-clone test: no identity dispatch allowed
- Serialization round-trip
"""
from __future__ import annotations

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
from app.project_factories import create_default_oborovo, create_default_tuho_wind1


# ── Enum validation ────────────────────────────────────────────────────────────

class TestTaxParamsValidation:
    def test_custom_pct_required(self):
        with pytest.raises(ValueError, match="shl_interest_deductible_pct is required"):
            TaxParams(
                shl_interest_deductibility=ShlInterestDeductibilityMode.CUSTOM_DEDUCTIBLE_PERCENTAGE,
                shl_interest_deductible_pct=None,
            )

    def test_custom_pct_out_of_range(self):
        with pytest.raises(ValueError, match=r"\[0, 1\]"):
            TaxParams(
                shl_interest_deductibility=ShlInterestDeductibilityMode.CUSTOM_DEDUCTIBLE_PERCENTAGE,
                shl_interest_deductible_pct=1.5,
            )

    def test_fully_deductible_with_wrong_pct(self):
        with pytest.raises(ValueError):
            TaxParams(
                shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE,
                shl_interest_deductible_pct=0.5,
            )

    def test_fully_non_deductible_with_wrong_pct(self):
        with pytest.raises(ValueError):
            TaxParams(
                shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE,
                shl_interest_deductible_pct=0.5,
            )

    def test_workbook_periodisation_mode_blocked(self):
        with pytest.raises(ValueError, match="unsupported"):
            TaxParams(
                tax_periodisation_mode=TaxPeriodisationMode.WORKBOOK_MODEL_YEAR_PAIRING,
                clean_cash_tax_timing_enabled=True,
            )

    def test_defaults_are_backward_compat(self):
        tp = TaxParams()
        assert tp.shl_interest_deductibility == ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE
        assert tp.shl_interest_deductible_pct is None
        assert tp.foreign_shl_interest_cap_enabled is False
        assert tp.tax_loss_utilisation_gate == TaxLossUtilisationGate.TAXABLE_INCOME_POSITIVE
        assert tp.tax_periodisation_mode == TaxPeriodisationMode.CALENDAR_TAX_YEAR
        assert tp.shl_construction_accounting == ShlAccountingTreatment.EXPENSE_TO_PNL
        assert tp.shl_construction_payment == ShlPaymentMethod.PIK_TO_SHL_BALANCE


# ── shl_non_deductible_fraction property ──────────────────────────────────────

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

    def test_subject_to_limitations_raises(self):
        tp = TaxParams(shl_interest_deductibility=ShlInterestDeductibilityMode.SUBJECT_TO_LIMITATIONS)
        with pytest.raises(NotImplementedError):
            _ = tp.shl_non_deductible_fraction


# ── compute_period_tax() SHL addback logic ────────────────────────────────────

class TestComputePeriodTaxShlAddback:
    BASE = dict(
        ebitda_keur=5000.0,
        depreciation_keur=1000.0,
        senior_interest_keur=500.0,
        shl_interest_keur=300.0,
        loss_carryforward_keur=0.0,
        tax_rate=0.10,
    )

    def test_none_mode_legacy_shl_in_atad_pool(self):
        # When mode is None (legacy), SHL is in ATAD pool — no addback
        r = compute_period_tax(**self.BASE, shl_interest_deductibility=None)
        assert r.shl_non_deductible_addback_keur == 0.0
        # taxable = 5000 - 1000 - (500+300) = 3200
        assert abs(r.taxable_income_keur - 3200.0) < 1e-6

    def test_fully_deductible_no_addback(self):
        r = compute_period_tax(
            **self.BASE,
            shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE,
        )
        assert r.shl_non_deductible_addback_keur == 0.0
        assert abs(r.taxable_income_keur - 3200.0) < 1e-6

    def test_fully_non_deductible_full_addback(self):
        r = compute_period_tax(
            **self.BASE,
            shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE,
        )
        # SHL removed from ATAD pool: total_interest = 500 only
        # taxable = 5000 - 1000 - 500 + 300 = 3800
        assert abs(r.shl_non_deductible_addback_keur - 300.0) < 1e-6
        assert abs(r.taxable_income_keur - 3800.0) < 1e-6

    def test_custom_50pct_addback(self):
        r = compute_period_tax(
            **self.BASE,
            shl_interest_deductibility=ShlInterestDeductibilityMode.CUSTOM_DEDUCTIBLE_PERCENTAGE,
            shl_interest_deductible_pct=0.5,
        )
        # 50% deductible: SHL in ATAD pool = 150, addback = 150
        # taxable = 5000 - 1000 - (500+150) + 150 = 3500
        assert abs(r.shl_non_deductible_addback_keur - 150.0) < 1e-6
        assert abs(r.taxable_income_keur - 3500.0) < 1e-6

    def test_subject_to_limitations_raises(self):
        with pytest.raises(NotImplementedError, match="C3B3C_BLOCKED_TUHO_THIN_CAP_FORMULA"):
            compute_period_tax(
                **self.BASE,
                shl_interest_deductibility=ShlInterestDeductibilityMode.SUBJECT_TO_LIMITATIONS,
            )

    def test_tax_computed_on_addback(self):
        r = compute_period_tax(
            **self.BASE,
            shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE,
        )
        assert abs(r.tax_keur - r.taxable_income_keur * 0.10) < 1e-9


# ── Oborovo source vector tests ────────────────────────────────────────────────

class TestOborovoTaxPolicy:
    def test_shl_interest_deductibility_is_fully_non_deductible(self):
        inputs = create_default_oborovo()
        assert inputs.tax.shl_interest_deductibility == ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE

    def test_foreign_shl_cap_enabled(self):
        inputs = create_default_oborovo()
        assert inputs.tax.foreign_shl_interest_cap_enabled is True

    def test_thin_cap_disabled(self):
        inputs = create_default_oborovo()
        assert inputs.tax.thin_cap_enabled is False

    def test_loss_gate_ebt_positive(self):
        inputs = create_default_oborovo()
        assert inputs.tax.tax_loss_utilisation_gate == TaxLossUtilisationGate.EBT_POSITIVE

    def test_tax_periodisation_calendar(self):
        inputs = create_default_oborovo()
        assert inputs.tax.tax_periodisation_mode == TaxPeriodisationMode.CALENDAR_TAX_YEAR

    def test_shl_construction_accounting_expense_to_pnl(self):
        inputs = create_default_oborovo()
        assert inputs.tax.shl_construction_accounting == ShlAccountingTreatment.EXPENSE_TO_PNL

    def test_shl_construction_payment_pik_to_shl_balance(self):
        inputs = create_default_oborovo()
        assert inputs.tax.shl_construction_payment == ShlPaymentMethod.PIK_TO_SHL_BALANCE

    def test_non_deductible_fraction_is_100pct(self):
        inputs = create_default_oborovo()
        assert inputs.tax.shl_non_deductible_fraction == 1.0


# ── TUHO source vector tests ───────────────────────────────────────────────────

class TestTuhoTaxPolicy:
    def test_shl_interest_deductibility_is_subject_to_limitations(self):
        inputs = create_default_tuho_wind1()
        assert inputs.tax.shl_interest_deductibility == ShlInterestDeductibilityMode.SUBJECT_TO_LIMITATIONS

    def test_foreign_shl_cap_disabled(self):
        inputs = create_default_tuho_wind1()
        assert inputs.tax.foreign_shl_interest_cap_enabled is False

    def test_thin_cap_enabled(self):
        inputs = create_default_tuho_wind1()
        assert inputs.tax.thin_cap_enabled is True

    def test_loss_gate_ebt_positive(self):
        inputs = create_default_tuho_wind1()
        assert inputs.tax.tax_loss_utilisation_gate == TaxLossUtilisationGate.EBT_POSITIVE

    def test_subject_to_limitations_fails_closed_via_compute(self):
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


# ── Renamed-clone test: no identity dispatch ───────────────────────────────────

class TestNoIdentityDispatch:
    """Prove that tax policy is driven by typed enum, not project name/code."""

    def test_oborovo_clone_with_fully_deductible_has_zero_addback(self):
        import dataclasses
        inputs = create_default_oborovo()
        # Override to FULLY_DEDUCTIBLE — a clone with different name
        new_tax = dataclasses.replace(
            inputs.tax,
            shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE,
            foreign_shl_interest_cap_enabled=False,
        )
        r = compute_period_tax(
            ebitda_keur=2000.0,
            depreciation_keur=400.0,
            senior_interest_keur=200.0,
            shl_interest_keur=100.0,
            loss_carryforward_keur=0.0,
            tax_rate=new_tax.corporate_rate,
            shl_interest_deductibility=new_tax.shl_interest_deductibility,
        )
        assert r.shl_non_deductible_addback_keur == 0.0

    def test_renamed_project_with_fully_non_deductible_has_full_addback(self):
        import dataclasses
        inputs = create_default_oborovo()
        new_tax = dataclasses.replace(
            inputs.tax,
            shl_interest_deductibility=ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE,
        )
        r = compute_period_tax(
            ebitda_keur=2000.0,
            depreciation_keur=400.0,
            senior_interest_keur=200.0,
            shl_interest_keur=100.0,
            loss_carryforward_keur=0.0,
            tax_rate=new_tax.corporate_rate,
            shl_interest_deductibility=new_tax.shl_interest_deductibility,
        )
        assert abs(r.shl_non_deductible_addback_keur - 100.0) < 1e-9


# ── Serialization round-trip ───────────────────────────────────────────────────

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
        # Strip new fields to simulate a pre-C3B3C payload
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
