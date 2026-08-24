"""financial_engine.policies.tax — TaxPolicy immutable contract.

Phase 2B full contract. No calculation performed here.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class CashTaxTiming(str, Enum):
    """When does the CIT cash payment crystallise relative to accrual?"""
    SAME_PERIOD = "same_period"
    TAX_YEAR_LAST_PERIOD = "tax_year_last_period"
    MODEL_YEAR_PAYMENT_PERIOD = "model_year_payment_period"


class TaxBasisPeriodisation(str, Enum):
    """How semi-annual model periods are grouped into tax calculation years."""
    CALENDAR_YEAR = "calendar_year"
    MODEL_YEAR_PAIRING = "model_year_pairing"


class TaxLossUtilisationGate(str, Enum):
    """Gate for using carried-forward losses against positive taxable income."""
    TAXABLE_INCOME_POSITIVE = "taxable_income_positive"
    EBT_POSITIVE = "ebt_positive"


class ShlInterestDeductibilityMode(str, Enum):
    """Clean-engine SHL interest deductibility policy.

    The value strings mirror finco_core.inputs.ShlInterestDeductibilityMode so
    adapters can map canonical ProjectInputs without importing finco_core into
    the clean tax engine.
    """

    FULLY_DEDUCTIBLE = "fully_deductible"
    FULLY_NON_DEDUCTIBLE = "fully_non_deductible"
    SUBJECT_TO_LIMITATIONS = "subject_to_limitations"
    CUSTOM_DEDUCTIBLE_PERCENTAGE = "custom_deductible_percentage"


@dataclass(frozen=True)
class TaxPolicy:
    """Complete jurisdiction tax policy for Phase 2B.

    Attributes
    ----------
    policy_id : unique identifier (e.g. "HR_CIT_2026")
    policy_version : semantic version of this policy record
    corporate_rate : flat CIT rate (e.g. 0.18)
    periods_per_tax_year : number of model periods per calendar tax year (2 = semi-annual)
    loss_carryforward_years : LCF window in tax years (5 for Croatia)
    atad_enabled : whether ATAD interest limitation applies
    atad_ebitda_limit : fraction of annual tax EBITDA allowed as max deductible interest (0.30)
    atad_de_minimis_threshold_keur_annual : annual safe harbour kEUR (3 000 for Croatia)
    cash_tax_timing : controls when the CIT cash payment crystallises
    cash_tax_payment_lag_periods : additional periods after the last-period trigger before
        cash is paid (0 = paid in the triggering period itself)
    shl_interest_tax_treatment_enabled : enables clean SHL deductibility treatment
        when the caller has supplied a complete financing-interest contract
    shl_interest_deductibility : tax treatment for gross accounting SHL interest
    shl_interest_deductible_pct : deductible fraction when CUSTOM_DEDUCTIBLE_PERCENTAGE
    shl_limitation_enabled : explicit activation toggle for SUBJECT_TO_LIMITATIONS
        computation. False literal means the limitation does NOT activate — zero/None
        values are distinct states and must not be coerced to False via truthiness.
        PR-11: must be True for SUBJECT_TO_LIMITATIONS to be active in the tax engine.
    shl_interest_cap_keur_annual : explicit annual cap (kEUR) applied per calendar year
        to gross SHL interest when shl_limitation_enabled=True and mode is
        SUBJECT_TO_LIMITATIONS. Must be strictly positive finite float when supplied.
        None = not set (limitation not parameterised → fail closed on SUBJECT_TO_LIMITATIONS).
        0.0 = zero cap is a valid financial policy (all SHL interest disallowed) and is
        distinct from None.
    """
    policy_id: str
    policy_version: str
    corporate_rate: float
    periods_per_tax_year: int
    loss_carryforward_years: int
    atad_enabled: bool
    atad_ebitda_limit: float
    atad_de_minimis_threshold_keur_annual: float
    cash_tax_timing: CashTaxTiming
    cash_tax_payment_lag_periods: int = 0
    shl_interest_tax_treatment_enabled: bool = False
    shl_interest_deductibility: ShlInterestDeductibilityMode = (
        ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE
    )
    shl_interest_deductible_pct: float | None = None
    tax_basis_periodisation: TaxBasisPeriodisation = TaxBasisPeriodisation.CALENDAR_YEAR
    loss_utilisation_gate: TaxLossUtilisationGate = (
        TaxLossUtilisationGate.TAXABLE_INCOME_POSITIVE
    )
    # NOTE: shl_limitation_enabled and shl_interest_cap_keur_annual have been REMOVED.
    # SUBJECT_TO_LIMITATIONS is now implemented via the ATAD mechanism (atad_enabled=True).
    # The ATAD EBITDA-based limitation is the approved authority for EU interest limitations.
    # An absolute annual SHL cap separate from ATAD has no approved non-workbook authority.

    def shl_tax_deductible_fraction(self) -> float:
        """Return the fraction of gross SHL interest eligible for tax deduction.

        For SUBJECT_TO_LIMITATIONS, SHL interest is treated as fully deductible
        at the year-builder level (fraction=1.0). The ATAD mechanism (atad_enabled=True)
        then applies the EBITDA-based annual limitation to total interest including SHL.
        Callers must ensure atad_enabled=True when mode is SUBJECT_TO_LIMITATIONS.
        """
        if not self.shl_interest_tax_treatment_enabled:
            return 1.0
        mode = self.shl_interest_deductibility
        if mode == ShlInterestDeductibilityMode.FULLY_DEDUCTIBLE:
            return 1.0
        if mode == ShlInterestDeductibilityMode.FULLY_NON_DEDUCTIBLE:
            return 0.0
        if mode == ShlInterestDeductibilityMode.CUSTOM_DEDUCTIBLE_PERCENTAGE:
            pct = self.shl_interest_deductible_pct
            if pct is None:
                raise ValueError(
                    "shl_interest_deductible_pct is required for CUSTOM_DEDUCTIBLE_PERCENTAGE"
                )
            if not 0.0 <= pct <= 1.0:
                raise ValueError(
                    f"shl_interest_deductible_pct must be in [0, 1], got {pct!r}"
                )
            return pct
        # SUBJECT_TO_LIMITATIONS: SHL is fully included in total interest.
        # The ATAD mechanism (atad_enabled=True) provides the annual limitation.
        # No separate per-SHL two-pass cap is applied — ATAD is the sole limitation authority.
        if mode == ShlInterestDeductibilityMode.SUBJECT_TO_LIMITATIONS:
            return 1.0
        raise NotImplementedError(
            f"TUHO_SHL_TAX_POLICY_UNHANDLED_MODE: unrecognised ShlInterestDeductibilityMode {mode!r}"
        )

    def is_subject_to_limitations_active(self) -> bool:
        """Return True if and only if SUBJECT_TO_LIMITATIONS is fully active.

        Active requires ALL of:
        - shl_interest_tax_treatment_enabled is True (financing interest injected)
        - shl_interest_deductibility is SUBJECT_TO_LIMITATIONS
        - atad_enabled is True (ATAD provides the interest limitation for STL)

        Architecture: the unsourced absolute annual SHL cap (shl_limitation_enabled +
        shl_interest_cap_keur_annual) has been removed. ATAD is now the sole limitation
        mechanism for SUBJECT_TO_LIMITATIONS. ATAD must be enabled for STL to be active.
        """
        if not self.shl_interest_tax_treatment_enabled:
            return False
        if self.shl_interest_deductibility is not ShlInterestDeductibilityMode.SUBJECT_TO_LIMITATIONS:
            return False
        # ATAD must be enabled for STL to have any actual limitation effect
        if not self.atad_enabled:
            return False
        return True
