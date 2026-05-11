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
    CITTier,
    TaxDepreciationRule,
    TaxTemplate,
    TaxTemplateOverride,
    ResolvedTaxConfig,
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
]