"""financial_engine.policies.tax — TaxPolicy immutable contract.

Phase 2B full contract. No calculation performed here.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CashTaxTiming(str, Enum):
    """When does the CIT cash payment crystallise relative to accrual?"""
    SAME_PERIOD = "same_period"
    TAX_YEAR_LAST_PERIOD = "tax_year_last_period"


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

    def shl_tax_deductible_fraction(self) -> float:
        """Return the fraction of gross SHL interest eligible for tax deduction.

        SUBJECT_TO_LIMITATIONS remains fail-closed until the relevant thin-cap
        limitation engine is source-proven and implemented.
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
        raise NotImplementedError(
            "TUHO_SHL_TAX_POLICY_BLOCKED_BY_UNSUPPORTED_LIMITATION: "
            "SUBJECT_TO_LIMITATIONS requires a source-proven thin-cap/limitation "
            "calculation before clean tax fixed-point execution."
        )
