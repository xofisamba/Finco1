"""finco_core.tax.templates — Tax template registry (Croatia / HR_SIMPLE_2026 etc.).

V2-4: Authoritative implementation. domain.tax.templates.* are compatibility shims.
"""
from finco_core.tax.templates.inputs import (
    CITTier, TaxDepreciationRule, TaxTemplate, TaxTemplateOverride, ResolvedTaxConfig,
)
from finco_core.tax.templates.calculations import (
    calculate_progressive_cit, get_tax_depreciation_rate,
)
from finco_core.tax.templates.schedules import (
    build_tax_depreciation_schedule, build_tax_loss_carryforward_schedule,
)
from finco_core.tax.templates.registry import TAX_TEMPLATE_REGISTRY
from finco_core.tax.templates.resolver import resolve_tax_template
from finco_core.tax.templates.result import TaxTemplateResult

__all__ = [
    "CITTier", "TaxDepreciationRule", "TaxTemplate", "TaxTemplateOverride", "ResolvedTaxConfig",
    "calculate_progressive_cit", "get_tax_depreciation_rate",
    "build_tax_depreciation_schedule", "build_tax_loss_carryforward_schedule",
    "TAX_TEMPLATE_REGISTRY", "resolve_tax_template", "TaxTemplateResult",
]
