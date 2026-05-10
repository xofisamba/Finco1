"""Phase 6A / 6B.1 / 6B.2 / 6B.3 — Tax template architecture.

Schema, registry, resolver, pure calculation primitives, and tax schedules.

Phase 6A:
- Declarative templates (CITTier, TaxDepreciationRule, TaxTemplate)
- Registry (HR_SIMPLE_2026, ME_INFRA_2026)
- Resolver (resolve_tax_template)
- No active tax calculations, no tax cashflows

Phase 6B.1:
- Pure calculation primitives (calculate_progressive_cit, get_tax_depreciation_rate,
  calculate_tax_depreciation_keur, calculate_taxable_income_keur)
- No waterfall wiring, no model output changes

Phase 6B.2:
- TaxDepreciationPeriod, TaxDepreciationSchedule
- build_tax_depreciation_schedule()
- Book vs tax depreciation separation, ME 2.5% cap support

Phase 6B.3:
- TaxLossPeriod, TaxLossCarryforwardSchedule
- build_tax_loss_carryforward_schedule()
- Loss generation and utilisation tracking (vintage expiry deferred)
"""
from domain.tax.templates.registry import get_builtin_tax_templates
from domain.tax.templates.resolver import resolve_tax_template
from domain.tax.templates.calculations import (
    calculate_progressive_cit,
    get_tax_depreciation_rate,
    calculate_tax_depreciation_keur,
    calculate_taxable_income_keur,
)
from domain.tax.templates.schedules import (
    TaxDepreciationPeriod,
    TaxDepreciationSchedule,
    build_tax_depreciation_schedule,
    TaxLossPeriod,
    TaxLossCarryforwardSchedule,
    build_tax_loss_carryforward_schedule,
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
    # Phase 6B.2
    "TaxDepreciationPeriod",
    "TaxDepreciationSchedule",
    "build_tax_depreciation_schedule",
    # Phase 6B.3
    "TaxLossPeriod",
    "TaxLossCarryforwardSchedule",
    "build_tax_loss_carryforward_schedule",
]