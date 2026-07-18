"""financial_engine.policies.tax — TaxPolicy immutable contract.

Phase 2B full contract. No calculation performed here — this is the
input specification only.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CashTaxTiming(str, Enum):
    """When does the cash tax payment occur relative to accrual?"""
    SAME_PERIOD = "same_period"
    TAX_YEAR_LAST_PERIOD = "tax_year_last_period"


@dataclass(frozen=True)
class TaxPolicy:
    """Complete jurisdiction tax policy for Phase 2B.

    All calculation parameters are expressed as pure scalars — no project
    identity, no fixture reads.

    Attributes
    ----------
    policy_id : str
        Unique identifier (e.g. "HR_CIT_2026"). Used for audit trail only.
    policy_version : str
        Semantic version of this policy record.
    corporate_rate : float
        Flat CIT rate (e.g. 0.18 for 18%). For progressive rates, use
        `cit_tiers` in a future extension; this field is the fallback flat rate.
    periods_per_tax_year : int
        Number of model periods per calendar tax year (2 for semi-annual).
    loss_carryforward_years : int
        Maximum carryforward window in tax years (5 for Croatia).
    expire_losses_before_use : bool
        If True, losses that expire at the start of a period are expired
        before being applied to that period's income (Excel-compatible mode).
    atad_enabled : bool
        Whether ATAD interest limitation applies.
    atad_ebitda_limit : float
        Fraction of annual tax EBITDA allowed as deductible interest
        (0.30 = 30%).
    atad_de_minimis_threshold_keur_annual : float
        Annual de-minimis safe-harbour in kEUR (3 000 kEUR for Croatia).
        Interest up to this amount is always deductible regardless of
        the EBITDA-limit test.
    cash_tax_timing : CashTaxTiming
        Controls when the CIT cash payment crystallises in the model.
    """
    policy_id: str
    policy_version: str
    corporate_rate: float
    periods_per_tax_year: int
    loss_carryforward_years: int
    expire_losses_before_use: bool
    atad_enabled: bool
    atad_ebitda_limit: float
    atad_de_minimis_threshold_keur_annual: float
    cash_tax_timing: CashTaxTiming
