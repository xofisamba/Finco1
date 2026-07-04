"""Phase 6A — Tax template registry.

Provides builtin demo templates for architecture validation.
All templates are clearly marked as illustrative and not legally binding.
"""
from __future__ import annotations

from finco_core.tax.templates.inputs import (
    CITTier,
    TaxDepreciationRule,
    TaxTemplate,
)


# ── HR Simple 2026 — flat CIT example ────────────────────────────────────────

HR_SIMPLE_2026 = TaxTemplate(
    country_code="HR",
    template_name="HR Simple 2026 (Illustrative)",
    tax_year=2026,
    # Flat 10% CIT (single tier)
    cit_tiers=(
        CITTier(min_profit_keur=0.0, max_profit_keur=None, tax_rate=0.10),
    ),
    # Basic straight-line depreciation for common asset categories
    depreciation_rules=(
        TaxDepreciationRule(
            asset_category="buildings",
            method="straight_line",
            annual_rate=None,
            useful_life_years=20.0,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="20-year straight-line for commercial buildings",
        ),
        TaxDepreciationRule(
            asset_category="equipment",
            method="straight_line",
            annual_rate=None,
            useful_life_years=5.0,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="5-year straight-line for equipment and machinery",
        ),
        TaxDepreciationRule(
            asset_category="vehicles",
            method="straight_line",
            annual_rate=None,
            useful_life_years=5.0,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="5-year straight-line for motor vehicles",
        ),
        TaxDepreciationRule(
            asset_category="intangibles",
            method="straight_line",
            annual_rate=None,
            useful_life_years=5.0,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="5-year straight-line for software and licenses",
        ),
        # Non-deductible: land
        TaxDepreciationRule(
            asset_category="land",
            method="straight_line",
            annual_rate=0.0,
            useful_life_years=None,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=False,
            notes="Land is not tax-deductible in HR",
        ),
    ),
    withholding_tax_dividends=0.0,
    withholding_tax_interest=0.0,
    loss_carryforward_years=5,
    thin_cap_ratio=None,
    interest_limitation_pct_ebitda=0.30,  # ATAD-compliant EBITDA cap
    metadata=(
        ("note", "illustrative only — not legal tax advice"),
        ("legal_ref", "ZK 2024, ZZ 2024"),
        ("source", " publicly available ZK guidance"),
    ),
)


# ── ME Infra 2026 — progressive CIT + infrastructure cap ─────────────────────

ME_INFRA_2026 = TaxTemplate(
    country_code="ME",
    template_name="ME Infrastructure 2026 (Illustrative)",
    tax_year=2026,
    # Progressive CIT: 9% up to 100M profit, 15% above
    # (real Montenegro CIT has a 15% rate with specific exemptions;
    # this is a progressive proxy for illustrative purposes)
    cit_tiers=(
        CITTier(min_profit_keur=0.0, max_profit_keur=100_000.0, tax_rate=0.09),
        CITTier(min_profit_keur=100_000.0, max_profit_keur=None, tax_rate=0.15),
    ),
    # Infrastructure depreciation: 20-year useful life BUT capped at 2.5%/year
    # This is the key Montenegro tax feature for renewable energy projects.
    # Even though the asset has a 20-year useful life for accounting,
    # tax law limits annual deduction to 2.5% of cost per year.
    depreciation_rules=(
        TaxDepreciationRule(
            asset_category="infrastructure",
            method="straight_line",
            annual_rate=None,
            useful_life_years=20.0,
            max_deductible_rate=0.025,  # 2.5% per year = key ME tax constraint
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="20-year asset life, but ME tax law caps deductible at 2.5%/year. "
                  "Annual deduction = min(calculated, 0.025 * cost)",
        ),
        TaxDepreciationRule(
            asset_category="equipment",
            method="declining_balance",
            annual_rate=0.25,  # 25% declining balance
            useful_life_years=10.0,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="25% declining balance for equipment (standard ME practice)",
        ),
        TaxDepreciationRule(
            asset_category="vehicles",
            method="straight_line",
            annual_rate=None,
            useful_life_years=5.0,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="5-year straight-line for motor vehicles",
        ),
        TaxDepreciationRule(
            asset_category="intangibles",
            method="straight_line",
            annual_rate=None,
            useful_life_years=5.0,
            max_deductible_rate=None,
            bonus_depreciation_pct=0.0,
            deductible=True,
            notes="5-year straight-line for software and licenses",
        ),
    ),
    withholding_tax_dividends=0.0,
    withholding_tax_interest=0.0,
    loss_carryforward_years=5,
    thin_cap_ratio=4.0,   # Debt / equity <= 4.0
    interest_limitation_pct_ebitda=0.30,
    metadata=(
        ("note", "illustrative only — not legal tax advice"),
        ("legal_ref", "ME Tax Law, Law on Corporate Income Tax"),
        ("infrastructure_cap", "2.5% per year for ME renewable projects"),
    ),
)


# ── Public Registry ────────────────────────────────────────────────────────────

_BUILTIN_TEMPLATES: tuple[TaxTemplate, ...] = (
    HR_SIMPLE_2026,
    ME_INFRA_2026,
)


def get_builtin_tax_templates() -> tuple[TaxTemplate, ...]:
    """Return all builtin tax templates.

    Phase 6A includes two illustrative templates:
    - HR_SIMPLE_2026: flat 10% CIT, straight-line depreciation
    - ME_INFRA_2026: progressive CIT (9%/15%), infrastructure cap at 2.5%/year

    All builtin templates are marked as illustrative in their metadata.
    Do NOT use these for actual tax compliance.
    """
    return _BUILTIN_TEMPLATES
