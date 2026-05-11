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

---

## Phase 6B.1 — Tax Calculation Primitives

**Status:** Pure functions using TaxTemplate schema. **No waterfall wiring. No model output changes.**
**Added:** `domain/tax/templates/calculations.py`

### Overview

Phase 6B.1 adds four pure calculation primitives built on the Phase 6A TaxTemplate schema.
These functions accept TaxTemplate types (CITTier, TaxDepreciationRule) and return plain floats.
No mutation, no side effects, no waterfall integration.

### Functions

#### `calculate_progressive_cit(taxable_profit_keur, cit_tiers) → float`

Applies progressive CIT brackets to a taxable profit.

```python
from domain.tax.templates import calculate_progressive_cit, CITTier

# Flat 10%
tiers = (CITTier(0.0, None, 0.10),)
calculate_progressive_cit(1000.0, tiers)  # → 100.0

# Progressive (ME-style: 9% ≤ 100k, 15% > 100k)
tiers = (
    CITTier(0.0, 100_000.0, 0.09),
    CITTier(100_000.0, None, 0.15),
)
calculate_progressive_cit(150_000.0, tiers)  # → 16,500.0
# 100,000 × 9% = 9,000; 50,000 × 15% = 7,500 → total = 16,500
```

Rules:
- `taxable_profit ≤ 0` → returns `0.0`
- Each tier applies to its slice of profit
- Tiers must be contiguous (enforced by TaxTemplate validation)

#### `get_tax_depreciation_rate(rule: TaxDepreciationRule) → float`

Returns the effective annual tax depreciation rate for an asset category.

```python
from domain.tax.templates import get_tax_depreciation_rate, ME_INFRA_2026

infra = next(r for r in ME_INFRA_2026.depreciation_rules if r.asset_category == "infrastructure")
rate = get_tax_depreciation_rate(infra)  # → 0.025 (2.5% cap is binding)
```

Rules (applied in order):
1. `deductible=False` → `0.0`
2. `max_deductible_rate` set → `min(base_rate, cap)`
3. `annual_rate` set → use directly
4. `useful_life_years > 0` → `1 / useful_life_years`
5. Otherwise → `0.0`

#### `calculate_tax_depreciation_keur(asset_cost_keur, rule) → float`

Annual tax depreciation deduction for an asset.

```python
from domain.tax.templates import calculate_tax_depreciation_keur, ME_INFRA_2026

infra = next(r for r in ME_INFRA_2026.depreciation_rules if r.asset_category == "infrastructure")
# 10M EUR wind turbine (10,000 kEUR cost, ME 2.5% cap)
calculate_tax_depreciation_keur(10_000.0, infra)  # → 250.0 kEUR
```

Rules:
- `asset_cost < 0` → raises `ValueError`
- `deductible=False` → `0.0`
- `amount = asset_cost × effective_rate`

Note: `bonus_depreciation_pct` not applied in this primitive (future extension point).

#### `calculate_taxable_income_keur(ebitda, deductible_interest, tax_depreciation, non_deductible_addbacks=0.0) → float`

Computes taxable income from EBITDA.

```
taxable_income = ebitda − deductible_interest − tax_depreciation + non_deductible_addbacks
```

```python
from domain.tax.templates import calculate_taxable_income_keur

taxable = calculate_taxable_income_keur(
    ebitda_keur=3_000.0,         # 3M EUR EBITDA
    deductible_interest_keur=500.0,
    tax_depreciation_keur=250.0,  # ME 2.5% cap on 10M asset
)
# → 2,250.0 kEUR
```

### Explicit Non-Scope (Phase 6B.1)

| Item | Status |
|---|---|
| ATAD EBITDA interest limitation | ❌ Not applied — apply separately in tax engine |
| Thin-cap adjustment | ❌ Not applied |
| Loss carryforward | ❌ Not applied |
| Withholding tax engine | ❌ Not applied |
| Deferred tax accounting | ❌ Not applied |
| Tax cashflow injection into waterfall | ❌ Not wired |
| HoldCo / SHL tax treatment | ❌ Not implemented |

### ME Infrastructure 2.5% Cap — Full Example

Demonstrates how the primitives work together for a Montenegro wind project:

```python
from domain.tax.templates import (
    calculate_taxable_income_keur,
    calculate_progressive_cit,
    calculate_tax_depreciation_keur,
    get_tax_depreciation_rate,
    ME_INFRA_2026,
)

# Asset: 10M EUR wind turbine
cost_kEUR = 10_000.0  # 10M EUR = 10,000 kEUR

# Tax depreciation (ME 2.5% annual cap)
infra_rule = next(r for r in ME_INFRA_2026.depreciation_rules
                  if r.asset_category == "infrastructure")
tax_dep = calculate_tax_depreciation_keur(cost_kEUR, infra_rule)
# → 250.0 kEUR/year (2.5% × 10,000)

# Taxable income
taxable = calculate_taxable_income_keur(
    ebitda_keur=3_000.0,
    deductible_interest_keur=500.0,
    tax_depreciation_keur=tax_dep,
)
# → 2,250.0 kEUR

# CIT (ME progressive: 9% ≤ 100M, 15% > 100M)
cit = calculate_progressive_cit(taxable, ME_INFRA_2026.cit_tiers)
# → 202.5 kEUR (2,250 × 9%)
```

Accounting depreciation (20-year straight-line) = 500 kEUR/year, but ME tax law caps deductible at 250 kEUR/year.
This 250 kEUR/year timing difference is a deferred tax item — not handled in this phase.

---

## Phase 6B.4 — SPV Tax Engine Foundation

**Purpose:** Pure SPV-level tax engine that computes CIT per period using TaxTemplate primitives, depreciation schedules, and loss carryforward schedules.
**Status:** Pure engine only. **No waterfall integration. No tax cashflow wiring. No deferred tax accounting.**

### What is built

| Component | File | Description |
|---|---|---|
| Engine inputs | `domain/tax/engine_inputs.py` | `SPVTaxEngineInputs` — validated per-entity inputs |
| Engine results | `domain/tax/engine_result.py` | `SPVTaxPeriodResult`, `SPVTaxResult` — per-period and aggregate output |
| Engine runner | `domain/tax/engine_runner.py` | `run_spv_tax_engine()` — pure function, no side effects |
| Tests | `tests/test_tax_engine_runner.py` | 20 test cases covering templates, timing diffs, loss carryforward, validation |

### Engine flow

```
SPVTaxEngineInputs
  → resolve depreciation rule from ResolvedTaxConfig
  → build_tax_depreciation_schedule()  (book vs tax dep, timing diffs, accumulated pool)
  → compute taxable_income_before_losses per period
       EBITDA
     - deductible_interest
     - tax_depreciation
     + non_deductible_addbacks
  → build_tax_loss_carryforward_schedule()
  → calculate_progressive_cit() per period using resolved CIT tiers
  → compute effective_tax_rate = cit / taxable_income_after_losses (0 if ≤ 0)
  → SPVTaxResult (per-period + aggregates)
```

### Explicit Non-Scope (Phase 6B.4)

| Item | Status |
|---|---|
| Waterfall integration | ❌ Not wired — Phase 6B.5+ |
| Tax cashflow injection into model | ❌ Not implemented |
| Deferred tax accounting (DTA/DTL) | ❌ Not implemented |
| HoldCo / intercompany tax logic | ❌ Not implemented |
| SHL tax treatment | ❌ Not implemented |
| Withholding tax engine | ❌ Not implemented |
| ATAD EBITDA interest limitation | ❌ Not applied — apply in future ATAD engine |
| Thin-cap adjustment | ❌ Not applied |
| Tax loss vintage tracking | ❌ Single pool only — future vintage tracking |
| Sponsor waterfall | ❌ Not implemented |

### Exports

```python
from domain.tax import (
    SPVTaxEngineInputs,
    SPVTaxPeriodResult,
    SPVTaxResult,
    run_spv_tax_engine,
)
```

### Validation rules

- `SPVTaxEngineInputs`: all tuples same length, entity_code non-empty, asset_cost ≥ 0, rule exists in resolved config
- `SPVTaxPeriodResult`: no NaN/inf, effective_tax_rate ∈ [0,1] when taxable income > 0
- `SPVTaxResult`: totals reconcile (sum of periods = aggregates), ending loss pool = last period closing

### Test coverage

- Flat HR template (10% flat CIT)
- Progressive ME template (9%/15% brackets, 2.5% dep cap)
- Depreciation timing difference accumulation and recovery
- Loss carryforward usage and pool floor at zero
- Zero / negative taxable income → no CIT
- Effective tax rate computation and bounds
- Template / config no-mutation verification
- Totals reconciliation
- Invalid inputs (unknown category, mismatched lengths, empty entity, negative asset cost, NaN, inf)

---

## Phase 6B.5 — Tax Audit / Export Visibility

**Purpose:** UI and Excel export helpers for SPV tax engine results.
**Status:** Audit-only. **Not wired into waterfall outputs or IRR metrics.**

### What is built

| Component | File | Description |
|---|---|---|
| Tax UI helpers | `app/tax_ui.py` | Summary/period DataFrames, audit note |
| Excel export helper | `app/tax_excel_export.py` | Writes Tax Summary + per-SPV sheets |
| Tests | `tests/test_tax_ui.py` | 10 tests |
| Tests | `tests/test_tax_excel_export.py` | 8 tests |

### Explicit non-scope

| Item | Status |
|---|---|
| Waterfall integration | ❌ Not wired — audit/export only |
| Model output changes | ❌ None |
| Tax payable into IRR | ❌ Not wired |
| Existing `excel_export.py` | ❌ Not modified |
| HoldCo / SHL / WHT tax | ❌ Not implemented |
| Deferred tax accounting | ❌ Not implemented |

### Audit note

Every exported sheet starts with:
> "AUDIT-ONLY: SPV tax engine results are not yet wired into waterfall outputs or IRR metrics."

Future Phase 6B.6 may wire tax result into optional reconciliation export.

---

## Phase 6B.6 — Optional Tax Audit Sheet Integration

**Purpose:** Integrate SPV tax audit sheets into the existing `build_excel_export()` as an optional, opt-in feature.

**Status:** Audit-only. **No waterfall impact. No model output changes. No cashflow wiring.**

### What's built

| Component | File | Description |
|---|---|---|
| Excel export hook | `app/excel_export.py` | `tax_results=None` parameter in `build_excel_export()` |
| Tests | `tests/test_excel_export.py` | 6 new integration tests |

### Behavior

```python
# Default: unchanged — no tax sheets
data = build_excel_export(result=result, project_inputs=inputs)

# Optional: add SPV tax audit sheets
data = build_excel_export(
    result=result,
    project_inputs=inputs,
    tax_results=(spv_tax_result1, spv_tax_result2, ...),
)
```

- `tax_results=None` → default behavior exactly as before
- `tax_results=()` → no-op (no tax sheets written)
- `tax_results=(result, ...)` → writes `Tax Summary` + `Tax_{entity_code}` sheets
- No changes to existing sheets, values, or layout
- Tax sheets are **audit-only** — not wired into waterfall economics

### Explicit non-scope (unchanged from 6B.5)

| Item | Status |
|---|---|
| Waterfall integration / model output changes | ❌ Not wired |
| Tax payable → IRR / cashflows | ❌ Not wired |
| HoldCo tax / SHL tax / WHT | ❌ Not implemented |
| Deferred tax | ❌ Not implemented |
| Sponsor IRR / sponsor waterfall | ❌ Not implemented |
| Existing `excel_export.py` layout | ❌ Unchanged (except optional hook) |

### Tests

```
tests/test_excel_export.py:               64 passed ✅
tests/test_tax_excel_export.py:           12 passed ✅
tests/test_tax_ui.py:                    10 passed ✅
tests/test_tax_engine_runner.py:         23 passed, 1 skipped ✅
```
