# Phase 9: CO2 → CIT Bridge Design

**Branch:** `phase9-co2-cit-bridge-design`
**Date:** 2026-05-20
**Status:** Design Draft

---

## 1. Overview

This document describes the design for bridging CO2 certificate revenue into the Corporate Income Tax (CIT) computation chain within the Finco1 financial model. The goal is to ensure CO2 revenue is treated consistently across the waterfall, tax engine, and distribution gates.

---

## 2. Current CO2 Runtime Flow

CO2 certificate revenue is generated per period by `revenue_decomposition_schedule()` (domain/revenue/generation.py) but the flow stops at the audit/visibility layer:

- **Stored as `co2_revenue_keur`** in `FinancialStatements` (domain/reporting/financial_statements.py line 32) — audit/visibility only
- **NOT included in waterfall `period.revenue_keur`** → CO2 bypasses EBITDA
- **NOT included in TaxEngine** → taxable income excludes CO2
- **NOT included in `r99_fcf_for_distribution_keur`** → R99 gate ignores CO2
- **NOT included in DistributionAccount** → distribution logic ignores CO2
- **NOT included in cash tax** → actual cash tax may be overstated

For TUHO at co2_price=4.191 EUR/MWh, Y1 CO2 revenue = 304.6 + 306.2 = **610.8 kEUR** — currently invisible to the tax and distribution chain.

---

## 3. Why CO2 Revenue Matters for CIT

CO2 certificate revenue is a genuine, recurring cash inflow tied to the operational output of the project. It reduces the effective tax burden when included in the CIT base, lowering the net CIT paid and increasing post-tax cash available for distribution.

The CIT computation (domain/tax/engine.py) follows:

```
taxable_profit = EBITDA - Depreciation - Interest + Fiscal Reintegration + ATAD - Loss CF
CIT = taxable_profit × tax_rate
```

CO2 revenue should increase `EBITDA` (through `period.revenue_keur`), which increases `taxable_profit` before tax, but since tax is applied to that larger base, the net effect is:

```
Net cash impact = CO2_revenue - (CO2_revenue × tax_rate) = CO2_revenue × (1 - tax_rate)
```

For a 25% CIT rate, ~75% of CO2 revenue flows through to post-tax cash.

---

## 4. Gap Analysis — What Works vs. What Doesn't

| Component | CO2 Input? | CO2 Affects Output? | Notes |
|---|---|---|---|
| `revenue_decomposition_schedule()` | ✅ Generated | N/A | Source of truth for CO2 revenue |
| `FinancialStatements.co2_revenue_keur` | ✅ Stored | Audit only | Not wired to waterfall |
| `period.revenue_keur` (waterfall) | ❌ Missing | ❌ | CO2 excluded |
| `period.ebitda_keur` (waterfall) | ❌ Missing | ❌ | Depends on revenue_keur |
| `TaxEngine.ebitda_keur` | ❌ Missing | ❌ | CIT base excludes CO2 |
| `r99_fcf_for_distribution_keur` | ❌ Missing | ❌ | R99 gate ignores CO2 |
| `DistributionAccount` | ❌ Missing | ❌ | No CO2 path |

**Root cause:** CO2 revenue is generated but never promoted to the `period.revenue_keur` field that drives the waterfall, tax, and distribution chain.

---

## 5. Affected Subsystems

| Subsystem | File | Field | Current CO2 Handling |
|---|---|---|---|
| Revenue decomposition | domain/revenue/generation.py | `co2_certificate_revenue_keur` | ✅ Generated |
| Financial statements | domain/reporting/financial_statements.py | `co2_revenue_keur` | ✅ Stored, audit only |
| Waterfall | app/waterfall_core.py | `period.revenue_keur` | ❌ Missing |
| Tax engine | domain/tax/engine.py | `TaxResult.ebitda_keur` | ❌ Missing |
| Tax bridge | domain/depreciation/tax_bridge.py | Depreciation validation | Audit only |
| Depreciation canonical | domain/depreciation/canonical_wiring.py | Tax depreciation audit | Audit only |
| R99 computation | app/waterfall_core.py | `r99_fcf_for_distribution_keur` | ❌ Missing |
| Distribution account | domain/distribution_account/engine.py | Gates evaluation | Audit only |
| Sponsor handoff | domain/sponsor/sponsor_cashflow_runner.py | `distribution_account_received_by_period` | Explicit tuple |

---

## 6. CO2→CIT Dependency Analysis

### Current State (Gap)

CO2 revenue IS generated correctly (~611 kEUR Y1 for TUHO). CO2 revenue IS NOT in `period.revenue_keur` → not in EBITDA.

**Waterfall formula:**
```python
ebitda = max(0, rev - opex)  # rev = period.revenue_keur, CO2 not present
```

**TaxEngine input:**
```python
ebitda_keur = period.ebitda_keur  # sourced from waterfall, excludes CO2
```

### Future Required State

CO2 revenue must be added to revenue before EBITDA calculation:

```
period.revenue_keur (with CO2) = gross_revenue + co2_revenue_keur
period.ebitda_keur (corrected) = max(0, period.revenue_keur - period.opex_keur)
TaxEngine.ebitda_keur (corrected) = period.ebitda_keur
```

The downstream chain (CIT → post-tax cash → R99 → DistributionAccount → Sponsor) then benefits automatically.

### TaxEngine CO2 Field Recommendation

TaxEngine should accept an optional `co2_revenue_keur` parameter, added to `ebitda_keur` before the taxable income computation:

```python
def compute(..., co2_revenue_keur: float = 0.0) -> TaxResult:
    ebitda_incl_co2 = ebitda_keur + co2_revenue_keur
    taxable_income = ebitda_incl_co2 - depreciation - interest + ...
```

---

## 7. TaxEngine — CO2 Input Field Design

### Option A: Add CO2 as Separate Parameter

TaxEngine `compute()` signature gains a new optional field:

```python
def compute(
    self,
    ebitda_keur: float,
    depreciation_keur: float,
    interest_keur: float,
    fiscal_reintegration_keur: float = 0.0,
    atad_keur: float = 0.0,
    loss_cf_keur: float = 0.0,
    co2_revenue_keur: float = 0.0,  # NEW
    tax_rate: float = 0.25,
    period: int = 0,
) -> TaxResult:
```

**Pros:** Clean, explicit, auditable
**Cons:** All callers must be updated

### Option B: Adjust EBITDA Before TaxEngine Call

Pre-process `ebitda_keur` at the waterfall level before passing to TaxEngine:

```python
ebitda_incl_co2 = period.ebitda_keur + period.co2_revenue_keur
```

**Pros:** No change to TaxEngine interface
**Cons:** Implicit, less auditable; CO2混入EBITDA without clear lineage

### Recommendation

**Option A** — Add `co2_revenue_keur` as an explicit field to TaxEngine. This maintains auditability and explicit lineage. The waterfall caller is modified to pass `co2_revenue_keur=period.co2_revenue_keur or 0.0` at the TaxEngine call site.

---

## 8. Waterfall Revenue Field — CO2 Inclusion Design

### Current Revenue Computation (app/waterfall_core.py line ~161)

```python
rev = period.revenue_keur  # CO2 NOT included
ebitda = max(0, rev - opex)
```

### Proposed Revenue Computation

```python
rev = period.revenue_keur + getattr(period, 'co2_revenue_keur', 0.0)
ebitda = max(0, rev - opex)
```

This requires:
1. `period` object (likely a `PeriodData` namedtuple or dataclass) has a `co2_revenue_keur` attribute
2. `revenue_decomposition_schedule()` populates `period.co2_revenue_keur` alongside `period.revenue_keur`

### PeriodData Attribute Recommendation

Add `co2_revenue_keur: float = 0.0` to the period data structure used across the waterfall chain.

---

## 9. Waterfall → TaxEngine Call Site Modification

The waterfall computes tax via TaxEngine. The call site in `waterfall_core.py` must be updated:

**Before:**
```python
tax_result = tax_engine.compute(
    ebitda_keur=period.ebitda_keur,
    depreciation_keur=period.depreciation_keur,
    interest_keur=period.interest_keur,
    ...
)
```

**After:**
```python
tax_result = tax_engine.compute(
    ebitda_keur=period.ebitda_keur,
    depreciation_keur=period.depreciation_keur,
    interest_keur=period.interest_keur,
    co2_revenue_keur=getattr(period, 'co2_revenue_keur', 0.0),  # NEW
    ...
)
```

---

## 10. Depreciation → TaxEngine — Ordering Requirement

Before CO2 can be wired into CIT, the TaxEngine must have a reliable depreciation input. The current state:

| Component | Status | Notes |
|---|---|---|
| TaxBridge | NOT promoted to TaxEngine | Audit only |
| Depreciation canonical | NOT wired to TaxEngine | Audit only |
| TaxBridge validation | Audit only | Not authoritative |

**The depreciation canonical wiring must be promoted before the CO2→CIT bridge is complete.** The TaxBridge must become the authoritative depreciation source for TaxEngine. See Section 13 for promotion order.

---

## 11. actual_cfads vs. sizing_cfads Implications

### actual_cfads (CF!R69)
Currently excludes CO2 → **understates cash available for distribution**. This affects:
- DSCR computation (denominator)
- Distribution eligibility
- Sponsor cashflow visibility

### sizing_cfads (Macro!R50)
May or may not include CO2 — **requires verification** in the Macro workbook. If sizing_cfads includes CO2 but actual_cfads does not, debt sizing is optimistic relative to actuals.

### Canonical Separation Requirement
`sizing_cfads` and `actual_cfads` must be kept semantically distinct:
- `sizing_cfads` = CFADS used for debt capacity computation (Macro input)
- `actual_cfads` = actual CFADS after all adjustments (runtime computation)

Both should include CO2 revenue once bridged, but the distinction must be preserved for audit.

---

## 12. Dependency Graph

```
CO2 generation (revenue_decomposition_schedule)
    ↓
co2_revenue_keur [FinancialStatements — audit only]
    ↓ GAP: not in period.revenue_keur
period.revenue_keur → ebitda_keur (waterfall)
    ↓
EBITDA → TaxEngine (ebitda_keur input) → CIT
    ↓
post-tax cash → cf_after_tax → r99_fcf_for_distribution → DistributionAccount → Sponsor
```

**Key bottleneck:** The "period object" must carry `co2_revenue_keur` from revenue decomposition through to waterfall revenue and TaxEngine call.

---

## 13. Recommended Promotion Order

| # | Capability | Classification | Precondition | Status |
|---|---|---|---|---|
| 1 | R102 runtime | SAFE AFTER PRECONDITION | DistributionAccount audit→runtime + SHL wiring complete | BLOCKED |
| 2 | Depreciation→TaxEngine | BLOCKED | TaxBridge promotion + canonical depreciation CIT-source flag | BLOCKED |
| 3 | TaxBridge promotion | BLOCKED | Depreciation canonical wiring promoted | BLOCKED |
| 4 | SeniorDebtSizing runtime | SAFE AFTER PRECONDITION | Macro!R50 live sizing CFADS wiring | PARTIAL |
| 5 | DistributionAccount runtime | BLOCKED | R99/R102 gate ownership + CO2→CIT bridge complete | BLOCKED |
| 6 | CO2→revenue bridge | READY | None (standalone) | **READY** |
| 7 | R99 runtime | BLOCKED | All above + CO2→CIT→DistributionAccount chain complete | BLOCKED |

**CO2→revenue bridge (item 6)** is the first ready capability — it requires only adding `co2_revenue_keur` to the period data structure and including it in `period.revenue_keur`. This is a small, targeted change.

---

## 14. Explicit Blockers

1. **CO2 revenue not in `period.revenue_keur`** — `period` object lacks CO2 field; waterfall does not aggregate CO2 into revenue
2. **TaxEngine has no CO2 input field** — `TaxResult` and `compute()` lack `co2_revenue_keur` parameter
3. **Depreciation canonical not TaxEngine-authoritative** — TaxBridge not promoted; TaxEngine uses runtime depreciation, not canonical
4. **DistributionAccount audit-only** — no runtime distribution routing; gates always return 0
5. **R99 gate not connected to post-tax cashflow chain** — `r99_fcf_for_distribution_keur` excludes CO2; gate evaluation not wired to actual cash

---

## 15. Final Recommendation

**SAFE TO PROMOTE:** None (full R99 chain is blocked)

**NEXT SAFE STEP:** Wire CO2 revenue into waterfall `period.revenue_keur` — the smallest, most targeted change that enables the rest of the chain.

### Immediate Action Items

| # | Action | File(s) | Complexity |
|---|---|---|---|
| A | Add `co2_revenue_keur: float = 0.0` to period data structure | waterfall_core.py / period dataclass | Low |
| B | Populate `period.co2_revenue_keur` in revenue decomposition | generation.py | Low |
| C | Include CO2 in waterfall `rev` computation | waterfall_core.py | Low |
| D | Add `co2_revenue_keur` parameter to TaxEngine `compute()` | engine.py | Medium |
| E | Update waterfall TaxEngine call site to pass CO2 | waterfall_core.py | Low |
| F | Promote TaxBridge to TaxEngine-authoritative | tax_bridge.py, canonical_wiring.py | High |
| G | Enable DistributionAccount runtime | engine.py | High |

Steps A–E constitute the CO2→CIT bridge and can be implemented independently of steps F–G. Step F is a prerequisite for full CIT correctness but can be parallelized with CO2 bridging once TaxBridge audit is complete.

---

*End of Phase 9 CO2→CIT Bridge Design Document*