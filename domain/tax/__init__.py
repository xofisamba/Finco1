"""Tax module — corporate tax, ATAD, loss carryforward, fiscal reintegration.

Phase 6A adds:
- CITTier, TaxDepreciationRule, TaxTemplate, TaxTemplateOverride, ResolvedTaxConfig
- get_builtin_tax_templates(), resolve_tax_template()
"""
from domain.tax.engine import (
    taxable_profit,
    tax_liability,
    apply_loss_carryforward,
    atad_limit,
)
from domain.tax.reintegration import fiscal_reintegration

# Phase 6B.1 — Tax Template Architecture
from domain.tax.templates import (
    get_builtin_tax_templates,
    resolve_tax_template,
    calculate_progressive_cit,
    get_tax_depreciation_rate,
    calculate_tax_depreciation_keur,
    calculate_taxable_income_keur,
)
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

__all__ = [
    # Phase 1-4 existing
    "taxable_profit",
    "tax_liability",
    "apply_loss_carryforward",
    "atad_limit",
    "fiscal_reintegration",
    # Phase 6A — tax template architecture
    "get_builtin_tax_templates",
    "resolve_tax_template",
    "CITTier",
    "TaxDepreciationRule",
    "TaxTemplate",
    "TaxTemplateOverride",
    "ResolvedTaxConfig",
]
