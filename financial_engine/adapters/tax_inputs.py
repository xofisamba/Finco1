"""financial_engine.adapters.tax_inputs — Generic ProjectInputs → TaxCalculationInput adapter.

Maps canonical ProjectInputs to a TaxCalculationInput for the clean Phase 2B / 2C engine.
No project-name dispatch, no snapshot loading, no factory invocations.

Tax policy is derived exclusively from project input fields:
  - corporate_rate        → TaxPolicy.corporate_rate
  - atad_enabled          → TaxPolicy.atad_enabled (C3B3D0: independent of thin_cap_enabled)
  - atad_ebitda_limit     → TaxPolicy.atad_ebitda_limit
  - atad_min_interest_keur→ TaxPolicy.atad_de_minimis_threshold_keur_annual
  - loss_carryforward_years → TaxPolicy.loss_carryforward_years
  - period_frequency      → TaxPolicy.periods_per_tax_year

C3B1 source evidence (Oborovo):
  - ATAD gated by BS!G45 = thin_cap_enabled = False → atad_enabled=False for Oborovo
  - cash_tax_timing = TAX_YEAR_LAST_PERIOD, lag=0

C3B3D0: atad_enabled and thin_cap_enabled are independent. This adapter reads
  tax.atad_enabled directly — it no longer derives ATAD from thin_cap_enabled.

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
    *,
    complete_financing_interest_will_be_injected: bool = False,
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
      fixed-point solver in run_senior_debt_model(); SHL interest is omitted
      because no authoritative canonical per-period SHL interest source existed
      before C3B3D1/D2B. Once D2B supplies gross_accrued_interest_keur, TaxPolicy
      determines deductibility (for Oborovo: FULLY_NON_DEDUCTIBLE → deductible=0).
      This is NOT a "cancellation through fiscal reintegration."
    * period_adjustments is returned EMPTY.
    * Callers that need SHL in the tax input must merge it after this call.

    Fail-closed conditions (raises rather than silently computing wrong results):
    * ATAD enabled with empty period_interest and no explicit complete-interest
      injection contract: raises NotImplementedError.
      ATAD requires complete financing interest; this adapter only supplies the
      empty stub — callers must merge full interest before computing ATAD.
    * Nonzero initial_tax_loss_keur: raises NotImplementedError.
      A vintage origin_tax_year cannot be generically inferred.
    * Unsupported period_frequency: raises ValueError.
      Only SEMESTRIAL (2 periods/year) is supported.
    * Clean cash-tax timing not enabled: raises NotImplementedError.
      The clean engine uses TAX_YEAR_LAST_PERIOD (calendar-year CIT accrual), lag=0.
      The payment lag of 0 is source-proven for Oborovo (C3B1). TAX_YEAR_LAST_PERIOD
      itself differs from workbook H2+H1 pairing (WORKBOOK_PERIODISATION_MISMATCH).
      Projects without clean_cash_tax_timing_enabled=True fail closed.
    """
    from financial_engine.inputs import TaxCalculationInput, OpeningTaxLossVintageInput
    from financial_engine.policies.tax import (
        CashTaxTiming,
        ShlInterestDeductibilityMode,
        TaxLossUtilisationGate,
        TaxPolicy,
    )

    tax = project_inputs.tax
    info = project_inputs.info

    # Periods per tax year from period frequency — fail-closed for unsupported values.
    freq = info.period_frequency
    if freq == PeriodFrequency.SEMESTRIAL:
        periods_per_tax_year = 2
    else:
        raise ValueError(
            f"build_tax_contract_from_project_inputs: unsupported period_frequency "
            f"{freq!r}. Only SEMESTRIAL (2 periods/year) is supported."
        )

    # C3B3D0: Read atad_enabled directly from TaxParams — independent of thin_cap_enabled.
    # Previously this adapter derived atad_enabled from thin_cap_enabled (wrong coupling).
    # Field default is False (generic/multi-jurisdiction safe). Old payloads without
    # atad_enabled fall back to the serialised thin_cap_enabled value via deserialization;
    # after materialisation the two fields are fully independent.
    atad_enabled: bool = tax.atad_enabled

    # FAIL-CLOSED: ATAD with empty period_interest is silently wrong.
    # This adapter always returns period_interest=() — the fixed-point solver
    # fills in senior_interest_by_period during iteration, but SHL and other
    # financing interest are NOT supplied by this adapter.
    # If ATAD is enabled, the computation requires complete interest inputs;
    # the caller must merge full interest into the TaxCalculationInput before
    # running the ATAD calculation.
    if atad_enabled and not complete_financing_interest_will_be_injected:
        raise NotImplementedError(
            "build_tax_contract_from_project_inputs: atad_enabled=True requires complete "
            "financing interest inputs (senior + SHL + other). This adapter only supplies "
            "the empty period_interest stub. Merge full interest explicitly before enabling ATAD."
        )

    # Clean cash-tax timing — fail-closed for projects without explicit opt-in.
    #
    # Two separate facts:
    #   (1) SOURCE-PROVEN: cash-tax payment lag = 0 periods (Oborovo, C3B1 evidence).
    #   (2) CLEAN ENGINE CONVENTION: annual CIT placed in last period of calendar
    #       year (TAX_YEAR_LAST_PERIOD). The workbook uses H2+H1 model-year pairing —
    #       a structurally different periodisation measured by WORKBOOK_PERIODISATION_MISMATCH.
    #       TAX_YEAR_LAST_PERIOD is NOT source-proven for Oborovo; it is the engine convention.
    #
    # clean_cash_tax_timing_enabled=True means: "this project is explicitly permitted to
    # use the currently supported clean tax timing convention". It does NOT claim that
    # TAX_YEAR_LAST_PERIOD matches the workbook periodisation.
    if not tax.clean_cash_tax_timing_enabled:
        raise NotImplementedError(
            "build_tax_contract_from_project_inputs: clean_cash_tax_timing_enabled=False. "
            "Projects must explicitly opt in to the clean engine's cash-tax timing convention "
            "(TAX_YEAR_LAST_PERIOD, lag=0). The payment lag of 0 periods is source-proven "
            "for Oborovo (C3B1); TAX_YEAR_LAST_PERIOD is the engine's periodisation convention "
            "and differs from the workbook H2+H1 model-year pairing. "
            "Set clean_cash_tax_timing_enabled=True in TaxParams after confirming payment lag."
        )

    policy = TaxPolicy(
        policy_id=_POLICY_ID,
        policy_version=_POLICY_VERSION,
        corporate_rate=tax.corporate_rate,
        periods_per_tax_year=periods_per_tax_year,
        loss_carryforward_years=tax.loss_carryforward_years,
        atad_enabled=atad_enabled,
        atad_ebitda_limit=tax.atad_ebitda_limit,
        atad_de_minimis_threshold_keur_annual=tax.atad_min_interest_keur,
        # Clean engine convention: annual CIT in last period of each calendar year.
        # SOURCE-PROVEN (C3B1): payment lag = 0 periods.
        # NOT SOURCE-PROVEN: TAX_YEAR_LAST_PERIOD periodisation (workbook uses H2+H1).
        cash_tax_timing=CashTaxTiming.TAX_YEAR_LAST_PERIOD,
        cash_tax_payment_lag_periods=0,
        shl_interest_tax_treatment_enabled=complete_financing_interest_will_be_injected,
        shl_interest_deductibility=ShlInterestDeductibilityMode(
            tax.shl_interest_deductibility.value
        ),
        shl_interest_deductible_pct=tax.shl_interest_deductible_pct,
        # PR-1 / P0-2: forward the typed gate from TaxParams so the clean engine
        # receives the configured policy rather than the TaxPolicy default.
        loss_utilisation_gate=TaxLossUtilisationGate(
            tax.tax_loss_utilisation_gate.value
        ),
    )

    # Opening loss vintages — fail closed for non-zero amounts.
    # A vintage origin_tax_year cannot be generically derived from ProjectInputs.
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
