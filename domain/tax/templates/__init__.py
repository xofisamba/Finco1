"""Phase 6A / 6B.1 — Tax template architecture.

Schema, registry, resolver, and pure calculation primitives.

Phase 6A:
- Declarative templates (CITTier, TaxDepreciationRule, TaxTemplate)
- Registry (HR_SIMPLE_2026, ME_INFRA_2026)
- Resolver (resolve_tax_template)
- No active tax calculations, no tax cashflows

Phase 6B.1:
- Pure calculation primitives (calculate_progressive_cit, get_tax_depreciation_rate,
  calculate_tax_depreciation_keur, calculate_taxable_income_keur)
- No waterfall wiring, no model output changes
"""
from domain.tax.templates.registry import get_builtin_tax_templates
from domain.tax.templates.resolver import resolve_tax_template
from domain.tax.templates.calculations import (
    calculate_progressive_cit,
    get_tax_depreciation_rate,
    calculate_tax_depreciation_keur,
    calculate_taxable_income_keur,
)

__all__ = [
    # Phase 6A
    "get_builtin_tax_templates",
    "resolve_tax_template",
    # Phase 6B.1
    "calculate_progressive_cit",
    "get_tax_depreciation_rate",
    "calculate_tax_depreciation_keur",
    "calculate_taxable_income_keur",
]