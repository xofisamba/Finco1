"""Tax module — corporate tax, ATAD, loss carryforward, fiscal reintegration.

Phase 6A adds:
- CITTier, TaxDepreciationRule, TaxTemplate, TaxTemplateOverride, ResolvedTaxConfig
- get_builtin_tax_templates(), resolve_tax_template()

Phase 6B.1 adds:
- calculate_progressive_cit, get_tax_depreciation_rate
- calculate_tax_depreciation_keur, calculate_taxable_income_keur

Phase 6B.2 adds:
- TaxDepreciationPeriod, TaxDepreciationSchedule, build_tax_depreciation_schedule

Phase 6B.3 adds:
- TaxLossPeriod, TaxLossCarryforwardSchedule, build_tax_loss_carryforward_schedule

Phase 6B.4 adds:
- SPVTaxEngineInputs, SPVTaxPeriodResult, SPVTaxResult, run_spv_tax_engine

Phase 6C.1 adds (schema only — no active calculation):
- HoldCoTaxInputs, WithholdingTaxConfig, InterestDeductibilityConfig, IntercompanyTaxFlow
- HoldCoTaxPeriodResult, HoldCoTaxResult
"""
from domain.tax.engine import (
    taxable_profit,
    tax_liability,
    apply_loss_carryforward,
    atad_limit,
)
from domain.tax.reintegration import fiscal_reintegration

# Phase 6A — tax template schema, registry, resolver
from domain.tax.templates.inputs import (
    CITTier,
    TaxDepreciationRule,
    TaxTemplate,
    TaxTemplateOverride,
    ResolvedTaxConfig,
)
from domain.tax.templates.result import (
    CITTier as _CITTierResult,
    TaxDepreciationRule as _TaxDepreciationRuleResult,
    TaxTemplate as _TaxTemplateResult,
    TaxTemplateOverride as _TaxTemplateOverrideResult,
    ResolvedTaxConfig as _ResolvedTaxConfigResult,
)
from domain.tax.templates import (
    get_builtin_tax_templates,
    resolve_tax_template,
)

# Phase 6B.1 — calculation primitives
from domain.tax.templates import (
    calculate_progressive_cit,
    get_tax_depreciation_rate,
    calculate_tax_depreciation_keur,
    calculate_taxable_income_keur,
)

# Phase 6B.2 — tax depreciation schedules
from domain.tax.templates.schedules import (
    TaxDepreciationPeriod,
    TaxDepreciationSchedule,
    build_tax_depreciation_schedule,
)

# Phase 6B.3 — tax loss carryforward schedules
from domain.tax.templates.schedules import (
    TaxLossPeriod,
    TaxLossCarryforwardSchedule,
    build_tax_loss_carryforward_schedule,
)

# Phase 6B.4 — SPV tax engine
from domain.tax.engine_inputs import SPVTaxEngineInputs
from domain.tax.engine_result import SPVTaxPeriodResult, SPVTaxResult
from domain.tax.engine_runner import run_spv_tax_engine

# Phase 6C.2 — HoldCo tax calculation primitives
from domain.tax.holdco_calculations import (
    calculate_withholding_tax_keur,
    calculate_holdco_taxable_income_before_limitations,
    exclude_shl_principal_from_taxable_income,
    calculate_interest_limitation_keur,
    calculate_deductible_interest_after_limitation_keur,
)

# Phase 6C.1 — HoldCo / intercompany tax schema (no active calculation)
from domain.tax.holdco_inputs import (
    HoldCoTaxInputs,
    WithholdingTaxConfig,
    InterestDeductibilityConfig,
    IntercompanyTaxFlow,
)
from domain.tax.holdco_result import (
    HoldCoTaxPeriodResult,
    HoldCoTaxResult,
)

__all__ = [
    # Phase 1-4 existing
    "taxable_profit",
    "tax_liability",
    "apply_loss_carryforward",
    "atad_limit",
    "fiscal_reintegration",
    # Phase 6A
    "get_builtin_tax_templates",
    "resolve_tax_template",
    "CITTier",
    "TaxDepreciationRule",
    "TaxTemplate",
    "TaxTemplateOverride",
    "ResolvedTaxConfig",
    # Phase 6B.1
    "calculate_progressive_cit",
    "get_tax_depreciation_rate",
    "calculate_tax_depreciation_keur",
    "calculate_taxable_income_keur",
    # Phase 6B.2
    "TaxDepreciationPeriod",
    "TaxDepreciationSchedule",
    "build_tax_depreciation_schedule",
    # Phase 6B.3
    "TaxLossPeriod",
    "TaxLossCarryforwardSchedule",
    "build_tax_loss_carryforward_schedule",
    # Phase 6B.4
    "SPVTaxEngineInputs",
    "SPVTaxPeriodResult",
    "SPVTaxResult",
    "run_spv_tax_engine",
    # Phase 6C.1 — HoldCo schema (no active calculation)
    "HoldCoTaxInputs",
    "WithholdingTaxConfig",
    "InterestDeductibilityConfig",
    "IntercompanyTaxFlow",
    "HoldCoTaxPeriodResult",
    "HoldCoTaxResult",
    # Phase 6C.2 — HoldCo tax calculation primitives
    "calculate_withholding_tax_keur",
    "calculate_holdco_taxable_income_before_limitations",
    "exclude_shl_principal_from_taxable_income",
    "calculate_interest_limitation_keur",
    "calculate_deductible_interest_after_limitation_keur",
    # Phase 6C.2 — Aliases
    "split_shl_tax_treatment",
    "calculate_interest_deductibility_limit_keur",
    "calculate_holdco_taxable_income_before_cit_keur",
    # Phase 6C.3 — HoldCo tax engine runner
    "run_holdco_tax_engine",
]