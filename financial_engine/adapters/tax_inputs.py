"""financial_engine.adapters.tax_inputs — Generic ProjectInputs → TaxCalculationInput adapter.

Maps canonical ProjectInputs to a TaxCalculationInput for the clean Phase 2B / 2C engine.
No project-name dispatch, no snapshot loading, no factory invocations.

Tax policy is derived exclusively from project input fields:
  - corporate_rate        → TaxPolicy.corporate_rate
  - thin_cap_enabled      → TaxPolicy.atad_enabled (workbook gates ATAD on thin_cap flag)
  - atad_ebitda_limit     → TaxPolicy.atad_ebitda_limit
  - atad_min_interest_keur→ TaxPolicy.atad_de_minimis_threshold_keur_annual
  - loss_carryforward_years → TaxPolicy.loss_carryforward_years
  - period_frequency      → TaxPolicy.periods_per_tax_year

C3B1 source evidence (Oborovo):
  - ATAD gated by BS!G45 = thin_cap_enabled = False → atad_enabled=False for Oborovo
  - FR = full SHL reintegration (thin_cap_enabled=False → C59=1.0, D59=True)
  - For ATAD=False + thin_cap=False: TI = EBITDA - tax_dep - senior_interest (SHL cancels)
  - cash_tax_timing = TAX_YEAR_LAST_PERIOD, lag=0

Opening loss vintages: derived from project inputs.tax.initial_tax_loss_keur.
For Oborovo: initial_tax_loss_keur = 0.0 → empty tuple.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from finco_core.inputs import ProjectInputs

from finco_core.inputs._models import PeriodFrequency


_POLICY_ID = "clean-project-tax-v1"
_POLICY_VERSION = "1.0.0"


def build_tax_contract_from_project_inputs(
    project_inputs: "ProjectInputs",
) -> object:
    """Map canonical ProjectInputs to a TaxCalculationInput.

    Parameters
    ----------
    project_inputs:
        Canonical project inputs (finco_core.inputs.ProjectInputs).

    Returns
    -------
    TaxCalculationInput — ready for calculate_tax() or run_senior_debt_model().

    Notes
    -----
    * period_interest is returned EMPTY — senior interest is supplied by the
      fixed-point solver in run_senior_debt_model(); SHL interest is excluded
      because for ATAD=False projects it cancels with fiscal reintegration.
    * period_adjustments is returned EMPTY for the same reason.
    * Callers that need SHL in the tax input must merge it after this call.
    """
    from financial_engine.inputs import TaxCalculationInput, OpeningTaxLossVintageInput
    from financial_engine.policies.tax import TaxPolicy, CashTaxTiming

    tax = project_inputs.tax
    info = project_inputs.info

    # Periods per tax year from period frequency
    freq = info.period_frequency
    if freq == PeriodFrequency.SEMESTRIAL:
        periods_per_tax_year = 2
    else:
        raise ValueError(
            f"build_tax_contract_from_project_inputs: unsupported period_frequency "
            f"{freq!r}. Only SEMESTRIAL (2 periods/year) is supported."
        )

    # ATAD gated on thin_cap_enabled (workbook: ATAD rows guarded by thin_cap flag).
    # C3B1 evidence: G56=BS!G45=thin_cap_enabled; Oborovo thin_cap=False → ATAD=False.
    atad_enabled: bool = tax.thin_cap_enabled

    policy = TaxPolicy(
        policy_id=_POLICY_ID,
        policy_version=_POLICY_VERSION,
        corporate_rate=tax.corporate_rate,
        periods_per_tax_year=periods_per_tax_year,
        loss_carryforward_years=tax.loss_carryforward_years,
        atad_enabled=atad_enabled,
        atad_ebitda_limit=tax.atad_ebitda_limit,
        atad_de_minimis_threshold_keur_annual=tax.atad_min_interest_keur,
        cash_tax_timing=CashTaxTiming.TAX_YEAR_LAST_PERIOD,
        cash_tax_payment_lag_periods=0,
    )

    # Opening loss vintages from project inputs.
    # For projects with initial_tax_loss_keur = 0, this is an empty tuple.
    if tax.initial_tax_loss_keur > 0:
        raise NotImplementedError(
            "build_tax_contract_from_project_inputs: non-zero initial_tax_loss_keur "
            f"({tax.initial_tax_loss_keur} kEUR) requires a vintage origin_tax_year "
            "that cannot be generically determined from ProjectInputs alone. "
            "Provide opening_loss_vintages explicitly."
        )
    opening_loss_vintages: tuple[OpeningTaxLossVintageInput, ...] = ()

    return TaxCalculationInput(
        policy=policy,
        opening_loss_vintages=opening_loss_vintages,
        period_interest=(),
        period_adjustments=(),
    )
