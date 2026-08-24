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
    # PR-11: explicit activation toggle and cap for SUBJECT_TO_LIMITATIONS.
    # These fields are independent of each other and of shl_interest_tax_treatment_enabled.
    # shl_limitation_enabled=False is a hard lock — no truthiness coercion allowed.
    shl_limitation_enabled: bool = False
    shl_interest_cap_keur_annual: float | None = None

    def shl_tax_deductible_fraction(self) -> float:
        """Return the fraction of gross SHL interest eligible for tax deduction.

        SUBJECT_TO_LIMITATIONS is not handled by this method because the deductible
        fraction depends on the annual gross SHL interest relative to the cap —
        a per-year computation that cannot be expressed as a static fraction.
        Use shl_annual_deductible_keur() for SUBJECT_TO_LIMITATIONS.

        Raises NotImplementedError for SUBJECT_TO_LIMITATIONS (caller must use
        the per-year cap computation path instead).
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
        # SUBJECT_TO_LIMITATIONS: per-year cap computation required.
        # Callers must use the two-pass approach in build_tax_year_bases.
        raise NotImplementedError(
            "TUHO_SHL_TAX_POLICY_BLOCKED_BY_UNSUPPORTED_LIMITATION: "
            "SUBJECT_TO_LIMITATIONS cannot be expressed as a static deductible fraction — "
            "the deductible amount depends on the annual gross SHL total vs the cap. "
            "Use shl_annual_deductible_keur(annual_gross_shl_keur) via the two-pass "
            "approach in build_tax_year_bases (PR-11 G2C_SHL_TAX_FEEDBACK path)."
        )

    def is_subject_to_limitations_active(self) -> bool:
        """Return True if and only if SUBJECT_TO_LIMITATIONS is fully active.

        Active requires ALL of:
        - shl_interest_tax_treatment_enabled is True (financing interest injected)
        - shl_interest_deductibility is SUBJECT_TO_LIMITATIONS
        - shl_limitation_enabled is True (explicit activation — not via truthiness)
        - shl_interest_cap_keur_annual is not None

        None semantics: shl_interest_cap_keur_annual=None means "not parameterised" which
        is distinct from zero cap. Zero cap is a valid policy (all SHL disallowed).
        False literal for shl_limitation_enabled does NOT activate through truthiness.
        NaN/Inf are rejected at computation time (not at this check).
        """
        # Explicit boolean check — not via truthiness coercion
        if not self.shl_interest_tax_treatment_enabled:
            return False
        if self.shl_interest_deductibility is not ShlInterestDeductibilityMode.SUBJECT_TO_LIMITATIONS:
            return False
        if self.shl_limitation_enabled is not True:
            return False
        if self.shl_interest_cap_keur_annual is None:
            return False
        return True

    def shl_annual_deductible_keur(self, annual_gross_shl_keur: float) -> tuple[float, float]:
        """Compute (deductible, disallowed) SHL interest for one calendar year.

        Only valid when is_subject_to_limitations_active() is True.
        All other modes must use shl_tax_deductible_fraction().

        Parameters
        ----------
        annual_gross_shl_keur : gross annual SHL interest for this calendar year.
            Must be finite and >= 0. NaN/Inf are rejected fail-closed.

        Returns
        -------
        (deductible_keur, disallowed_keur) where:
            deductible_keur = min(annual_gross_shl_keur, cap_keur_annual)
            disallowed_keur = annual_gross_shl_keur - deductible_keur
        Both are non-negative and sum exactly to annual_gross_shl_keur.

        Fail-closed conditions:
        - is_subject_to_limitations_active() is False → raises ValueError
        - annual_gross_shl_keur is NaN or Inf → raises ValueError
        - annual_gross_shl_keur < 0 → raises ValueError
        - shl_interest_cap_keur_annual is NaN or Inf → raises ValueError
        """
        if not self.is_subject_to_limitations_active():
            raise ValueError(
                "G2C_SHL_ANNUAL_DEDUCTIBLE_REQUIRES_ACTIVE_LIMITATION: "
                "shl_annual_deductible_keur() called when is_subject_to_limitations_active() "
                "is False. Use shl_tax_deductible_fraction() for other modes."
            )
        # Fail closed: NaN/Inf in annual_gross_shl_keur
        if not math.isfinite(annual_gross_shl_keur):
            raise ValueError(
                "G2C_SHL_TAX_FEEDBACK_INVALID_GROSS_SHL: "
                f"annual_gross_shl_keur must be finite, got {annual_gross_shl_keur!r}. "
                "NaN/Inf cannot behave like None or zero in SHL tax computation."
            )
        if annual_gross_shl_keur < 0.0:
            raise ValueError(
                "G2C_SHL_TAX_FEEDBACK_NEGATIVE_GROSS_SHL: "
                f"annual_gross_shl_keur must be >= 0, got {annual_gross_shl_keur!r}."
            )
        cap = self.shl_interest_cap_keur_annual
        # Already checked cap is not None (is_subject_to_limitations_active)
        assert cap is not None
        if not math.isfinite(cap):
            raise ValueError(
                "G2C_SHL_TAX_FEEDBACK_INVALID_CAP: "
                f"shl_interest_cap_keur_annual must be finite, got {cap!r}. "
                "NaN/Inf cannot behave like None or zero."
            )
        # Zero cap is valid: all SHL interest is disallowed
        effective_cap = max(0.0, cap)
        deductible = min(annual_gross_shl_keur, effective_cap)
        disallowed = annual_gross_shl_keur - deductible
        return deductible, disallowed
