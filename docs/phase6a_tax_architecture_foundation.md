# Phase 6A — Tax Architecture Foundation

**Purpose:** Declarative schema, registry, and resolver for jurisdiction-specific tax configurations.
**Status:** Architecture only. **No active tax engine.** No tax calculations. No tax cashflows.
**Last updated:** 2026-05-10

---

## Architecture Goals

1. **Declarative templates** — tax configurations stored as data, not code. No hardcoded jurisdiction logic.
2. **Separation of accounting vs tax depreciation** — `TaxDepreciationRule` supports both accounting depreciation (for financial statements) and tax deductible amounts separately.
3. **Progressive CIT support** — `CITTier` models bracket-based corporate income tax (e.g., 9% up to 100M, 15% above).
4. **Non-deductible depreciation** — `deductible=False` marks categories (e.g., land) that never produce tax deductions.
5. **Override strategy** — `TaxTemplateOverride` enables user modifications without mutating builtin templates.
6. **Future SPV / HoldCo separation** — templates are entity-agnostic; a future tax engine can apply SPV-level or HoldCo-level rules.
7. **Future SHL tax treatment** — SHL interest/principal treated separately from dividend income in `HoldCoRunner`.

---

## Domain Models

### `CITTier`
Defines a single CIT bracket.

```python
CITTier(min_profit_keur=0.0, max_profit_keur=100_000.0, tax_rate=0.09)
```

- `min >= 0`, `max > min` if bounded, `tax_rate ∈ [0, 1]`
- No overlapping tiers within one template

### `TaxDepreciationRule`
Defines depreciation for one asset category under a tax regime.

```python
TaxDepreciationRule(
    asset_category="infrastructure",
    method="straight_line",
    useful_life_years=20.0,
    max_deductible_rate=0.025,   # key: 2.5% cap for ME renewable projects
    deductible=True,
    notes="ME tax law caps at 2.5%/year regardless of useful life",
)
```

Supports: straight-line, declining balance, units-of-production, capped depreciation, non-deductible.

### `TaxTemplate`
Complete tax configuration for one country + year.

```python
TaxTemplate(
    country_code="ME",
    template_name="ME Infrastructure 2026",
    tax_year=2026,
    cit_tiers=(...),
    depreciation_rules=(...),
    withholding_tax_dividends=0.0,
    withholding_tax_interest=0.0,
    loss_carryforward_years=5,
    thin_cap_ratio=4.0,
    interest_limitation_pct_ebitda=0.30,
    metadata=(("note", "illustrative only"),),
)
```

Validates: uppercase country_code, no duplicate asset categories, no overlapping CIT tiers, rates ∈ [0,1].

### `TaxTemplateOverride`
Immutable patch for a template field.

```python
TaxTemplateOverride(
    override_name="custom_wht",
    field_path="withholding_tax_interest",
    override_value=0.05,
    reason="Treaty rate HR-ME",
)
```

Phase 6A: simple top-level field only. Nested paths (`cit_tiers.0.tax_rate`) not supported yet.

### `ResolvedTaxConfig`
Output of `resolve_tax_template()`: base template + overrides + merged metadata.

---

## Declarative Registry Strategy

Templates are registered in `domain/tax/templates/registry.py` via `get_builtin_tax_templates()`.

Current Phase 6A builtins:

| Template | Country | CIT | Depreciation |
|---|---|---|---|
| `HR_SIMPLE_2026` | HR (Croatia) | Flat 10% | Straight-line, 20y buildings, 5y equipment, non-deductible land |
| `ME_INFRA_2026` | ME (Montenegro) | Progressive 9%/15% | Infrastructure: 20y life, **capped at 2.5%/year** |

All builtin templates are marked as **illustrative only** in their metadata. Do not use for actual tax compliance.

---

## Progressive CIT Support

Example: Montenegro 9%/15% progressive:

```python
cit_tiers=(
    CITTier(min_profit_keur=0.0, max_profit_keur=100_000.0, tax_rate=0.09),
    CITTier(min_profit_keur=100_000.0, max_profit_keur=None, tax_rate=0.15),
)
```

Tax engine downstream must implement the bracket calculation (apply lower rate to lower bracket, higher rate to excess).

---

## Deductible vs Non-Deductible Depreciation

`deductible=False` marks categories that never produce tax deductions:

```python
TaxDepreciationRule(
    asset_category="land",
    method="straight_line",
    annual_rate=0.0,
    useful_life_years=None,
    max_deductible_rate=None,
    bonus_depreciation_pct=0.0,
    deductible=False,
    notes="Land is not tax-deductible in HR",
)
```

Even if `annual_rate` or `useful_life_years` are set, no deduction is claimed when `deductible=False`.

---

## Override Strategy

`resolve_tax_template()` applies `TaxTemplateOverride` objects immutably:

```python
from domain.tax.templates import get_builtin_tax_templates, resolve_tax_template

tpl = get_builtin_tax_templates()[0]  # HR_SIMPLE_2026
ov = TaxTemplateOverride(
    override_name="relax_wht",
    field_path="withholding_tax_interest",
    override_value=0.05,
    reason="Treaty rate HR-ME",
)
result = resolve_tax_template(tpl, (ov,))
```

Rules:
- Original template is never mutated
- Duplicate field paths: last override wins
- Invalid field paths raise `ValueError`
- `metadata` override replaces base metadata entirely

---

## Montenegro Infrastructure Depreciation Example

This is the key tax feature for renewable energy projects in Montenegro.

**Accounting depreciation:** 20-year useful life → 5%/year straight-line

**ME Tax law constraint:** Annual deductible amount capped at **2.5% of cost per year**

```python
TaxDepreciationRule(
    asset_category="infrastructure",
    method="straight_line",
    useful_life_years=20.0,
    max_deductible_rate=0.025,  # 2.5% cap = key ME tax constraint
    deductible=True,
    notes="20-year asset life, but ME tax law caps deductible at 2.5%/year. "
          "Annual deduction = min(calculated, 0.025 * cost)",
)
```

For a €10M wind turbine:
- Accounting deduction: €500k/year (5% × €10M)
- **Tax deduction: €250k/year** (capped at 2.5% × €10M)
- Tax timing difference: €250k/year deferred

The `max_deductible_rate` field enables the tax engine to apply this cap without encoding it in business logic.

---

## Future SPV vs HoldCo Tax Separation

Phase 6A templates are entity-agnostic. A future tax engine can:

1. Apply SPV-level templates (e.g., HR_SIMPLE_2026) to compute SPV taxable income
2. Apply HoldCo-level templates to compute HoldCo taxable income
3. Model dividend upstreaming from SPV → HoldCo with `withholding_tax_dividends`
4. Model interest upstreaming with `withholding_tax_interest`

The `HoldCoRunner` already separates SHL interest from dividend income (only interest is taxable at HoldCo level; SHL principal is not taxable income). The template schema supports this via `withholding_tax_dividends` (dividend withholding) and `withholding_tax_interest` (interest withholding).

---

## Future SHL Tax Treatment

`HoldCoRunner` in Phase 4B handles three SHL cash flow components:

1. **Dividend**: equity distribution from SPV waterfall → taxable at HoldCo
2. **SHL interest**: taxable HoldCo income
3. **SHL principal**: cash movement only → **NOT taxable income**

The tax template schema supports this via the dividend vs interest withholding rate fields. Future integration would connect the template's `withholding_tax_dividends` and `withholding_tax_interest` to the HoldCo cash flow model.

---

## Explicit Non-Scope (Phase 6A)

The following are **NOT implemented** and are explicitly out of scope:

| Item | Reason |
|---|---|
| Active tax calculation | Schema only; tax engine deferred |
| Tax cashflow injection into waterfall | Not wired |
| Deferred tax accounting | Requires accounting integration |
| Tax loss engine (`apply_loss_carryforward`) | Existing `domain/tax/engine.py` preserved, not modified |
| Withholding tax engine | Rates stored in templates, not applied |
| Thin-cap enforcement | `thin_cap_ratio` stored, not validated |
| EBITDA interest limitation | `interest_limitation_pct_ebitda` stored, not applied |
| User override UI | Override schema defined, UI deferred |

Existing `domain/tax/engine.py` (Phase 1-4 code) remains unchanged and is not modified by Phase 6A.

---

## File Structure

```
domain/tax/
  __init__.py          # exports from engine + Phase 6A additions
  engine.py            # existing: taxable_profit, tax_liability (unchanged)
  ...
  templates/
    __init__.py       # exports get_builtin_tax_templates, resolve_tax_template
    inputs.py         # CITTier, TaxDepreciationRule, TaxTemplate, TaxTemplateOverride, ResolvedTaxConfig
    result.py         # re-exports from inputs (logical grouping)
    registry.py       # HR_SIMPLE_2026, ME_INFRA_2026, get_builtin_tax_templates()
    resolver.py       # resolve_tax_template()
```

---

*Phase 6A establishes the foundation for future tax engine integration. No active calculations are performed.*
