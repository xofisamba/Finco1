"""
finco_core.tax — Tax engine.

Extraction target (V2-3): TaxEngine, LossCarryforward (5-year rolling,
Croatian CIT §16, expire_before_use=True), holdco tax calculations,
tax bridge (reconciliation-only per Phase 0 Z2).

Source: domain/tax/

Critical invariant: LCF methodology is NOT calibrated to the Excel Golden
Model where Excel is wrong. Finco intentionally keeps the correct Croatian
§16 treatment.

V2-3: Forward shims to domain tax modules.
"""
from domain.tax import (
    taxable_profit,
    tax_liability,
    apply_loss_carryforward,
    atad_limit,
    fiscal_reintegration,
    get_builtin_tax_templates,
    resolve_tax_template,
    CITTier,
    TaxDepreciationRule,
    TaxTemplate,
    TaxTemplateOverride,
    ResolvedTaxConfig,
    calculate_progressive_cit,
    get_tax_depreciation_rate,
    calculate_tax_depreciation_keur,
    calculate_taxable_income_keur,
    TaxDepreciationPeriod,
    TaxDepreciationSchedule,
    build_tax_depreciation_schedule,
    TaxLossPeriod,
    TaxLossCarryforwardSchedule,
    build_tax_loss_carryforward_schedule,
    SPVTaxEngineInputs,
    SPVTaxPeriodResult,
    SPVTaxResult,
    run_spv_tax_engine,
    HoldCoTaxInputs,
    WithholdingTaxConfig,
    InterestDeductibilityConfig,
    IntercompanyTaxFlow,
    HoldCoTaxPeriodResult,
    HoldCoTaxResult,
    calculate_withholding_tax_keur,
    calculate_holdco_taxable_income_before_limitations,
    exclude_shl_principal_from_taxable_income,
    calculate_interest_limitation_keur,
    calculate_deductible_interest_after_limitation_keur,
)
from domain.tax.engine import atad_adjustment

__all__ = [
    "taxable_profit",
    "tax_liability",
    "apply_loss_carryforward",
    "atad_limit",
    "atad_adjustment",
    "fiscal_reintegration",
    "get_builtin_tax_templates",
    "resolve_tax_template",
    "CITTier",
    "TaxDepreciationRule",
    "TaxTemplate",
    "TaxTemplateOverride",
    "ResolvedTaxConfig",
    "calculate_progressive_cit",
    "get_tax_depreciation_rate",
    "calculate_tax_depreciation_keur",
    "calculate_taxable_income_keur",
    "TaxDepreciationPeriod",
    "TaxDepreciationSchedule",
    "build_tax_depreciation_schedule",
    "TaxLossPeriod",
    "TaxLossCarryforwardSchedule",
    "build_tax_loss_carryforward_schedule",
    "SPVTaxEngineInputs",
    "SPVTaxPeriodResult",
    "SPVTaxResult",
    "run_spv_tax_engine",
    "HoldCoTaxInputs",
    "WithholdingTaxConfig",
    "InterestDeductibilityConfig",
    "IntercompanyTaxFlow",
    "HoldCoTaxPeriodResult",
    "HoldCoTaxResult",
    "calculate_withholding_tax_keur",
    "calculate_holdco_taxable_income_before_limitations",
    "exclude_shl_principal_from_taxable_income",
    "calculate_interest_limitation_keur",
    "calculate_deductible_interest_after_limitation_keur",
]
