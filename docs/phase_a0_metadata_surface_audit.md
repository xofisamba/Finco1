# Phase A0 - Metadata Surface Audit

> Type: analysis-only, docs / report / optional documentation validation test  
> Branch: `phase-a0-metadata-surface-audit`  
> Requested base: post-Phase A1 main (`f54dbd7d12ffc2c03980c59c5e73677e6e0fbbaa`)  
> rc1: `b425a0708719eaa5e1d922b1008e5609758e0ad4` - untouched  
> Status: backend-authoritative metadata audit only. No runtime, UI, model, persistence, export, schema, or formula changes in this phase.

## 1. Purpose

Phase A1 proved that read-only derivation popovers can improve trust when
they are tied directly to backend-authoritative values.

Before building any A2 derivation chains for Revenue, CAPEX, Debt, Tax,
OPEX, Distributions, or Sponsor returns, we need an honest inventory of
what the backend already exposes today.

This audit answers:

- which displayed metrics already have trustworthy backend components
- which metrics are only partially surfaced
- which metrics would become misleading if we tried to explain them too far
- where future derivation popovers should source their evidence from

This phase does **not**:

- modify runtime behavior
- modify UI behavior
- modify model calculations
- modify persistence behavior
- modify export behavior
- modify schema or migrations
- modify formulas
- calculate anything in the frontend

## 2. Reviewed surfaces

The audit is grounded in the current backend and evidence surfaces:

- `domain/waterfall/waterfall_engine.py`
- `app/api/project_runner.py`
- `app/ui/runtime_summary.py`
- `app/output_tables.py`
- `app/export/runtime_summary.py`
- `app/excel_export.py`
- `domain/reporting/financial_statements.py`
- `app/persistence/exports_repository.py`

Supporting evidence was also taken from the existing workbook / audit
reporting layer:

- runtime summary CSV export
- values-only Excel export sheets
- institutional workbook skeleton
- calibration reconciliation pack and source inventories

## 3. Current surface model

### 3.1 Source hierarchy for future derivations

Future derivation popovers should use this source order:

1. **Runtime result / period fields**
   - `WaterfallResult`
   - `WaterfallPeriod`
2. **Read-only output table builders**
   - `build_waterfall_table(result)`
   - `build_revenue_table(result)`
   - `build_debt_table(result)`
   - `build_tax_depreciation_table(result)`
   - `build_returns_table(result)`
3. **Audit metadata / export evidence**
   - runtime summary CSV export
   - Excel workbook sheets
   - institutional workbook / calibration packs
4. **Persistence / inputs only where the metric is not runtime-derived**
   - example: CAPEX baseline totals from `project_inputs.capex`

### 3.2 Explicit rejection

Future derivations must **not**:

- calculate financial values in JavaScript
- reconstruct missing backend values in templates
- parse rendered export files to fabricate runtime truth
- infer unavailable sub-components from totals

## 4. Derivation readiness matrix

| Metric | Current Runtime Source | Available Components | Missing Components | Derivation Ready? | Risk Level | Recommended Action |
|---|---|---|---|---|---|---|
| Revenue | `WaterfallResult.total_revenue_keur`; `WaterfallPeriod.revenue_keur`; `build_revenue_table()` | total revenue, period revenue, generation MWh, optional BESS / hybrid revenue rows | tariff / price decomposition, PPA vs merchant split, CO2 / balancing split | `PARTIAL` | Medium | Build a conservative total-revenue popover only after read-only evidence mapping; do not promise a full revenue formula chain yet |
| EBITDA | `WaterfallResult.total_ebitda_keur`; `WaterfallPeriod.ebitda_keur`; `build_waterfall_table()`; `build_tax_depreciation_table()` | revenue, opex, EBITDA at period level; total EBITDA | no explicit standalone derivation payload in runtime summary today | `READY` | Low | Implement early; expose one sample period and total values from backend |
| OPEX | `WaterfallResult.total_opex_keur`; `WaterfallPeriod.opex_keur`; `build_waterfall_table()` | total OPEX, period OPEX | no runtime line-item OPEX breakdown in the summary surface | `PARTIAL` | Medium | Safe total-only popover is possible; line-item OPEX derivation should wait |
| CAPEX Total | `project_inputs.capex.total_capex[_keur]`; `build_capex_summary_table()`; `build_capex_items_table()`; Excel `CapEx` / `CapEx_Items` | total CAPEX, sculpt CAPEX, 15-item CAPEX table, CAPEX sub-line audit | no runtime `WaterfallResult` CAPEX derivation payload; no canonical runtime “why this total” surface | `PARTIAL` | Medium | Treat as input/evidence derivation, not a runtime cash-flow derivation; add read-only context explicitly |
| Senior Debt | `WaterfallResult.total_senior_ds_keur`; `WaterfallPeriod.senior_interest_keur`, `senior_principal_keur`, `senior_ds_keur`, `senior_balance_keur`; `build_debt_table()` | debt service, interest, principal, balance, DSCR / LLCR / PLCR rows | authoritative opening-debt derivation in runtime summary is weak; current card uses context/project anchor rather than a result-bound scalar | `PARTIAL` | Medium | Add read-only exposure for debt opening / schedule anchors before a popover |
| DSCR | `WaterfallResult.actual_avg_dscr`, `actual_min_dscr`; `WaterfallPeriod.dscr`, `cf_after_tax_keur`, `senior_ds_keur`; A1 derivation evidence | displayed avg DSCR, period DSCR, example period components, supporting totals | nothing essential for the current conservative A1 scope | `READY` | Low | Already implemented in A1; keep wording conservative |
| CFADS | `WaterfallPeriod.cf_after_tax_keur`; A1 derivation evidence; `build_waterfall_table()` | period CFADS, total CFADS, supporting EBITDA and tax fields | a fully explicit engine-level CFADS decomposition contract beyond `cf_after_tax_keur` | `READY` | Low | Already implemented in A1 using backend field identity, not invented formula math |
| Tax | `WaterfallResult.total_tax_keur`; `WaterfallPeriod.tax_keur`, `taxable_profit_keur`, `depreciation_keur`, `interest_*`; `build_tax_depreciation_table()` | total tax, period cash tax, taxable profit, depreciation, senior interest, SHL interest | explicit bridge between tax accrual, cash timing, losses, and audit-only fields in one runtime-safe payload | `PARTIAL` | High | Do not ship a “full tax formula” popover yet; requires curated read-only exposure |
| Distributions | `WaterfallResult.total_distribution_keur`; `WaterfallPeriod.distribution_keur`; `build_waterfall_table()` | total distributions, period distributions, some audit-only distribution-account fields exist in period objects | a safe, compact explanation of lockup, reserves, R99 / R102, SHL competition, and distribution-account source routing | `NOT READY` | High | Avoid for now; high risk of oversimplifying gating behavior |
| Sponsor Returns | `WaterfallResult.sponsor_irr`; `build_returns_table()`; sponsor waterfall audit exports exist separately | sponsor IRR scalar; sponsor waterfall export modules and audit sheets exist outside runtime summary | backend-authoritative runtime sponsor cash-flow chain is not surfaced in the current runtime summary context | `NOT READY` | High | Defer until a runtime-safe sponsor evidence payload exists |

## 5. Metric-by-metric findings

### 5.1 Revenue

**What exists now**

- runtime total revenue scalar
- period revenue rows
- generation MWh rows
- optional BESS / hybrid revenue rows when relevant

**What is missing**

- explicit tariff / price components
- PPA-versus-merchant split in the runtime summary surface
- durable CO2 / balancing separation

**Conclusion**

Revenue is a good A2 candidate only if the first version is framed as:

- displayed metric: total revenue
- evidence: period revenue rows plus generation support
- no claim that we currently expose the complete price-stack derivation

### 5.2 EBITDA

**What exists now**

- runtime total EBITDA
- period revenue
- period OPEX
- period EBITDA

**Conclusion**

EBITDA is the strongest low-risk next step after A1. The evidence chain is
compact, backend-authoritative, and already present in runtime and export
surfaces.

### 5.3 OPEX

**What exists now**

- runtime total OPEX
- period OPEX rows

**What is missing**

- runtime line-item OPEX decomposition

**Conclusion**

OPEX is safe for a total-only explanation, but not yet safe for a
line-item derivation story.

### 5.4 CAPEX Total

**What exists now**

- input-owned CAPEX totals
- CAPEX summary and 15-item itemization
- CAPEX sub-line audit sheet for user-created projects

**What is missing**

- runtime-result-owned CAPEX derivation payload
- explicit “total CAPEX comes from inputs, not from a waterfall period
  calculation” messaging

**Conclusion**

CAPEX can be surfaced, but only as a **baseline/input evidence** derivation,
not as if it were a runtime-calculated waterfall metric.

### 5.5 Senior Debt

**What exists now**

- period interest, principal, service, balance
- total senior debt service scalar
- DSCR / LLCR / PLCR rows

**What is missing**

- authoritative runtime summary origin for the displayed senior debt card
- concise debt-opening story suitable for user-facing UI

**Conclusion**

Useful medium-risk target after EBITDA / Revenue / CAPEX, but it needs a
small read-only exposure pass first.

### 5.6 Tax

**What exists now**

- total tax scalar
- period cash tax
- taxable profit
- depreciation
- senior and SHL interest rows

**What is missing**

- unified read-only tax bridge payload for “why tax is this number”
- explicit loss / accrual / timing explanation surface

**Conclusion**

Tax is **not** ready for a confident end-user derivation story without
additional backend exposure.

### 5.7 Distributions

**What exists now**

- total distribution scalar
- period distribution rows
- some audit-only R99 / R102 / distribution-account bridge fields in
  `WaterfallPeriod`

**What is missing**

- a compact, honest explanation surface for all gating conditions

**Conclusion**

High risk. Too easy to imply a simplistic formula where the actual story is
gated, stateful, and governance-sensitive.

### 5.8 Sponsor returns

**What exists now**

- sponsor IRR scalar
- separate sponsor waterfall export modules and audit sheets

**What is missing**

- runtime summary sponsor cash-flow chain
- backend-authoritative lightweight popover payload

**Conclusion**

Do not attempt sponsor-return derivations yet.

## 6. Low / medium / high risk buckets

### 6.1 Low-risk derivations

Can be implemented immediately using existing backend data:

- EBITDA
- Revenue (conservative total-only version)

Already implemented:

- DSCR
- CFADS

### 6.2 Medium-risk derivations

Require small read-only backend exposure or clearer binding:

- OPEX
- CAPEX Total
- Senior Debt

### 6.3 High-risk derivations

Risk of misleading users if implemented now:

- Tax
- Distributions
- Sponsor returns

## 7. Additional read-only context needed for A2

### 7.1 Revenue

Recommended future context keys:

- `revenue_derivation.display_value_keur`
- `revenue_derivation.period_count`
- `revenue_derivation.sample_period_label`
- `revenue_derivation.sample_generation_mwh`
- `revenue_derivation.sample_revenue_keur`
- optional supporting flags for BESS / hybrid rows when present

### 7.2 EBITDA

Recommended future context keys:

- `ebitda_derivation.display_value_keur`
- `ebitda_derivation.sample_period_label`
- `ebitda_derivation.sample_revenue_keur`
- `ebitda_derivation.sample_opex_keur`
- `ebitda_derivation.sample_ebitda_keur`

### 7.3 OPEX

Recommended future context keys:

- `opex_derivation.display_value_keur`
- `opex_derivation.sample_period_label`
- `opex_derivation.sample_opex_keur`

### 7.4 CAPEX

Recommended future context keys:

- `capex_derivation.total_capex_keur`
- `capex_derivation.sculpt_capex_keur`
- `capex_derivation.capex_items_source`
- optional `capex_derivation.sub_line_audit_available`

### 7.5 Senior debt

Recommended future context keys:

- `senior_debt_derivation.opening_debt_keur`
- `senior_debt_derivation.total_debt_service_keur`
- `senior_debt_derivation.sample_interest_keur`
- `senior_debt_derivation.sample_principal_keur`
- `senior_debt_derivation.sample_balance_keur`

### 7.6 Tax

Recommended future context keys:

- `tax_derivation.display_value_keur`
- `tax_derivation.sample_taxable_profit_keur`
- `tax_derivation.sample_depreciation_keur`
- `tax_derivation.sample_senior_interest_keur`
- `tax_derivation.sample_shl_interest_keur`
- `tax_derivation.sample_cash_tax_keur`

## 8. Recommended A2 implementation order

### Preferred sequence

1. **A2-1 EBITDA derivation**
   - effort: low
   - UX win: high
   - risk: low

2. **A2-2 Revenue derivation**
   - effort: low-to-medium
   - UX win: high
   - risk: medium unless kept conservative

3. **A2-3 OPEX derivation**
   - effort: low
   - UX win: medium
   - risk: medium

4. **A2-4 CAPEX total derivation**
   - effort: medium
   - UX win: high for Excel-replacement confidence
   - risk: medium because it is input-owned, not runtime-derived

5. **A2-5 Senior debt derivation**
   - effort: medium
   - UX win: high
   - risk: medium

6. **A2-6 Tax derivation**
   - effort: medium-to-high
   - UX win: medium
   - risk: high without careful read-only exposure

### Metrics to avoid for now

- **A2-7 Distributions derivation**
- **A2-8 Sponsor returns derivation**

Those should wait until a later branch deliberately surfaces richer
backend-authoritative evidence.

## 9. Biggest UX wins

The biggest immediate trust wins after A1 are:

- EBITDA
- Revenue
- CAPEX Total
- Senior Debt

These are the places where users most often ask “where did this number come
from?” and where the backend already carries enough structure to answer
honestly with modest read-only additions.

## 10. Biggest technical risks

1. **Confusing totals with formulas**  
   The A1 DSCR wording review showed how easy it is to imply a stronger
   formula claim than the backend actually guarantees.

2. **Mixing runtime truth with export-only evidence**  
   Export sheets are useful support, but they must not become the primary
   calculation source for popovers.

3. **Using persistence as if it were runtime output**  
   This is especially relevant for CAPEX. Input-owned totals are still valid,
   but they should be framed as baseline evidence, not as waterfall-period
   calculations.

4. **Over-explaining governance-sensitive flows**  
   Distributions and sponsor returns are the most likely places to create a
   misleading simplification.

## 11. Recommendation

**Recommendation: PASS**

Phase A0 gives us a clear boundary:

- proceed next with **EBITDA**
- follow with conservative **Revenue**
- then **OPEX**, **CAPEX Total**, and **Senior Debt**
- defer **Tax**, **Distributions**, and **Sponsor returns** until the
  backend exposes a safer read-only evidence payload

That sequence gives us the best trust-surface improvement without
pretending the runtime exposes more than it really does today.
