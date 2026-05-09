# Phase 3 — HoldCo Skeleton Architecture

## Goal
Add minimal HoldCo entity to the financial model — purely structural, no SHL engine, no tax template, no retained earnings constraints.

## Principle
**Keep the architecture additive.** The existing IndependentPortfolio engine must not be rewritten. HoldCo sits above SPVs as a passthrough/aggregation layer.

---

## 1. Architecture Overview

```
Sponsor (equity investor)
    │
    └── HoldCo (intermediate holding entity)
            │
            ├── SPV A (owns % of project A via equity)
            ├── SPV B (owns % of project B via equity)
            └── SPV C (owns % of project C via equity)

Cash flow direction (normalized):
  SPV → HoldCo → Sponsor
  (distributions flow upward; ownership % determines share)
```

### Entities

| Entity | Role | Output |
|--------|------|--------|
| `HoldCoResult` | Aggregates SPV-level distributions, applies ownership %, deducts HoldCo OpEx, passes remainder to Sponsor | Sponsor-level IRR, HoldCo cash flow schedule |
| `HoldCoInputs` | SPV list, ownership percentages, HoldCo OpEx | Feeds runner |
| `HoldCoConfig` | HoldCo entity metadata (name, currency, tax regime) | Configuration |

### HoldCo vs Independent Portfolio

- **Independent Portfolio**: SPVs are independent (no cross-guarantee), each SPV runs its own waterfall
- **HoldCo**: aggregation layer above SPVs; each SPV still runs independently; HoldCo collects distributions and re-distributes based on ownership

---

## 2. Proposed Dataclasses

```python
@dataclass
class HoldCoOwnership:
    spv_code: str
    ownership_pct: float  # 0.0–1.0

@dataclass
class HoldCoInputs:
    name: str
    spv_codes: list[str]           # references to existing SPV projects
    ownerships: list[HoldCoOwnership]
    opex_keur: float               # annual HoldCo-level OpEx (legal, admin)
    tax_rate_pa: float             # corporate tax on HoldCo-level profit

@dataclass
class HoldCoPeriodResult:
    period: int
    spv_code: str
    gross_distribution_keur: float
    ownership_pct: float
    net_to_holdco_keur: float
    holdco_opex_keur: float
    tax_keur: float
    distribution_to_sponsor_keur: float

@dataclass
class HoldCoResult:
    name: str
    periods: list[HoldCoPeriodResult]
    total_spv_distributions_keur: float
    total_sponsor_distributions_keur: float
    holdco_irr: float              # placeholder — IRR recalculation deferred
```

---

## 3. Cash Flow Direction

```
Per period, per SPV:

  SPV Net Distribution
         │
         ▼
  HoldCo receives: dist * ownership_pct (per SPV)
         │
         ▼
  HoldCo aggregates all SPV shares
         │
         ▼
  HoldCo deducts: opex (fixed annual amount in kEUR)
         │
         ▼
  Tax on (aggregate income - opex) if positive
         │
         ▼
  Net to Sponsor = max(0, aggregate - opex - tax)
```

### Ownership Passthrough Logic
- Each SPV distribution flows to HoldCo according to ownership %
- If HoldCo owns 100% of SPV → full distribution to HoldCo
- If HoldCo owns 80% of SPV → 80% of SPV distribution to HoldCo, 20% to minority (not modeled in Phase 3)
- **Phase 3 assumes 100% ownership of all SPVs** (no minority modeling)

---

## 4. HoldCo Aggregation Logic

```
For each period P:
  1. For each SPV in HoldCo portfolio:
       - Get SPV net distribution from IndependentPortfolioResult
       - Multiply by ownership_pct for that SPV
       - Sum all SPV shares → HoldCo gross income

  2. Deduct HoldCo opex (fixed kEUR amount)

  3. Compute taxable income = max(0, gross - opex)

  4. Compute tax = taxable_income * tax_rate_pa

  5. Compute net = gross - opex - tax

  6. Distribute net to Sponsor (equity investor at HoldCo level)

  7. Compute HoldCo IRR from sponsor cash flows (deferred in Phase 3)
```

---

## 5. Ownership Mapping

Phase 3 assumption: **single HoldCo entity owns 100% of all SPVs**.

```python
ownerships = [
    HoldCoOwnership(spv_code="OBOROVO", ownership_pct=1.0),
    HoldCoOwnership(spv_code="TUHO", ownership_pct=1.0),
]
```

Future Phase 4: configurable per-SPV ownership (e.g., HoldCo owns 80%, minority owns 20%).

---

## 6. Future SHL Integration Points

SHL (Shareholder Loan) will be a **subsequent phase** (Phase 4 or later), not Phase 3.

Phase 3 design must not preclude SHL. Key integration points to preserve:

```
HoldCo
  │ (issues SHL to SPV)
  ▼
SPV receives SHL proceeds → SPV cash balance increases → impacts DSCR
SPV pays SHL interest → reduces SPV distributions to HoldCo
SPV repays SHL principal → reduces SPV distributions to HoldCo
```

**Phase 3 does NOT implement SHL.** HoldCo → SPV cash flow is pure equity distribution only.

---

## 7. Future Tax-Template Integration Points

Phase 3 assumes a flat corporate tax rate applied to HoldCo-level income.

Future tax-template integration will replace the flat rate with a proper tax computation:
- Deductible interest (SHL interest when Phase 4 adds SHL)
- Tax loss carryforwards
- Thin capitalization rules

**Phase 3 does NOT implement tax templates.** Placeholder: `tax_rate_pa = 0.20` (20% default).

---

## 8. Risks and Convergence Considerations

### Risk 1: Sponsor IRR not computed in Phase 3
HoldCo IRR is deferred. Sponsor will not see return metrics until Phase 4+ when SHL and tax are implemented.

### Risk 2: Multi-level waterfall complexity
When SHL is added (Phase 4), SPV-level waterfall must correctly handle intercompany flows. If HoldCo issues SHL to SPV, SPV's waterfall must reflect additional liability and interest burden.

### Risk 3: Ownership % modeling
Phase 3 assumes 100% ownership. Phase 4+ must support minority interests without breaking the passthrough logic.

### Convergence
The HoldCo aggregation is a **simple passthrough** — no iterative convergence needed at this stage (unlike sculpting or DSRA funding calculations).

---

## 9. Excel Export Implications

When HoldCo is added, new export sheets required:

| Sheet | Content |
|-------|---------|
| `HoldCo_Summary` | Per-period: gross income, opex, tax, net to sponsor |
| `HoldCo_SPVs` | Per-SPV ownership % and contribution to HoldCo |
| `HoldCo_Notes` | Limitations disclaimer (placeholder IRR, no SHL, no tax template) |

Existing sheets unchanged:
- `Portfolio_Summary` (IndependentPortfolio)
- `Portfolio_SPVs` (IndependentPortfolio)
- `DSRF` (if enabled)

---

## 10. Suggested Implementation Phases

### Phase 3A — Core HoldCo Skeleton
- `domain/holdco/holdco_inputs.py` — HoldCoInputs, HoldCoOwnership
- `domain/holdco/holdco_result.py` — HoldCoResult, HoldCoPeriodResult
- `domain/holdco/holdco_aggregation.py` — pure passthrough aggregation (no SHL)
- `domain/holdco/run.py` — run_holdco(holdco_inputs, portfolio_results)
- `domain/holdco/__init__.py` — exports
- `tests/test_holdco.py` — basic tests (100% ownership, opex deduction, tax computation)
- `tests/test_holdco_integration.py` — integration with existing portfolio results

**Phase 3A scope:**
- Only equity distributions flow through HoldCo (no SHL)
- 100% ownership assumption
- Flat corporate tax rate
- No retained earnings
- No convergence needed (passthrough only)
- IRR recalculation deferred

### Phase 3B — HoldCo + Excel Export
- `app/excel_export.py` — append HoldCo_Summary, HoldCo_SPVs, HoldCo_Notes sheets
- `app/holdco_ui.py` — build HoldCo summary table (optional UI for validation)
- `tests/test_holdco_excel_export.py` — workbook tests for HoldCo sheets

**Phase 3B scope:**
- All Phase 3A complete
- Excel export working
- Notes sheet disclaims deferred IRR

### Phase 4 (later) — SHL + Sponsor IRR
- SHL engine at HoldCo level (intercompany loan)
- SPV waterfall integration (SHL flows into SPV cash)
- Sponsor IRR computation (replaces deferred placeholder)
- Tax template integration (deductible interest via SHL)
- Minority ownership support

### Phase 5+ (future) — Refinancing / Mezzanine / Monthly Model
- Out of scope for now

---

## Explicit Non-Scope (Phase 3)

| Feature | Status |
|---------|--------|
| SHL engine | ❌ Not in Phase 3 |
| Intercompany interest | ❌ Not in Phase 3 |
| Tax template engine | ❌ Not in Phase 3 |
| Retained earnings constraint | ❌ Not in Phase 3 |
| Pooled financing | ❌ Not in Phase 3 |
| Refinancing | ❌ Not in Phase 3 |
| Mezzanine | ❌ Not in Phase 3 |
| Monthly model | ❌ Not in Phase 3 |
| Minority ownership | ❌ Not in Phase 3 |
| Sponsor IRR recalculation | ❌ Deferred beyond Phase 3 |

---

## Constraints

- Do NOT modify `domain/portfolio/independent/` — the independent portfolio engine is complete and frozen
- Do NOT modify `domain/waterfall/` core waterfall engine
- Do NOT modify `domain/dsra_engine.py` or reserves
- HoldCo is **additive only** — it reads from IndependentPortfolioResult and produces HoldCoResult
- All existing tests must continue to pass