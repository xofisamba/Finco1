# MVP G1 Current Financial Authority

## Test authority

| Class | Meaning | Release effect |
|---|---|---|
| `CURRENT_BLOCKING` | Protects the canonical engine or product contract | Required green |
| `HISTORICAL_COMPATIBILITY` | Compares current behavior with a superseded source/baseline | Runnable, non-blocking |
| `DIAGNOSTIC` | Locates and explains a divergence | Runnable, non-blocking |

Historical evidence is retained. It does not become current authority by updating
goldens, hashes, correction ledgers, or tolerances to match today's output.

## Current canonical authority

### Base tax

Canonical Base tax is generic and methodology-driven: calendar tax years,
explicit model/calendar fragmentation, FIFO loss vintages, configurable legal
loss-carryforward life, positive-taxable-income utilization, explicit interest
deductibility and fiscal reintegration, and explicit cash-tax timing. Source
cash-tax vectors are not runtime inputs. No project identity selects a tax formula.

Oborovo workbook conventions such as a five-model-period loss window, EBT-positive
utilization, H2/next-H1 pairing, June/H1 payment, and non-causal row-39 behavior are
`HISTORICAL_COMPATIBILITY`, not generic Base methodology.

### Bank case and Base case

Base Performance is the P50 operating case. Bank sizing is a separate lender case,
using generic P90 production and configured target DSCR (1.20x for Generic Solar
and Wind). Target DSCR controls Bank sizing. Base DSCR is independently calculated
as Base CFADS divided by actual Senior debt service and need not equal 1.20x.

### SHL causality

The only canonical SHL-to-Senior capacity path is:

`SHL gross interest -> deductible interest -> taxable income/cash tax -> Bank CFADS -> DSCR-sized Senior capacity`.

There is no direct SHL-principal addition, top-up, target fitting, or balancing
adjustment.

### Source projects

TUHO and Oborovo remain source-evidence and calibration projects. Calculations may
dispatch on typed project-owned capability, policy, or input. They may not dispatch
on project name, project code, baseline identity, or source workbook identity.

## Historical and diagnostic authorities

- Phase 2A exact `OPERATING_CORE_V1` snapshots are historical compatibility evidence.
- Phase 2B methodology/engine invariants remain current blocking. Its
  `TAX_CFADS_V1` correction-aware four-baseline comparison is marked
  `historical_compatibility` and remains diagnostic.
  Its 488 Oborovo differences are not approved corrections and are not a current
  release authority. The still-current hand-calculated tax invariants remain useful.
- C3B3B and earlier C3B3 tax/SHL stages remain forensic history superseded by B5-B8
  and G0/G0.1 where their assertions conflict.
- Phase 51F's old Oborovo OPEX total and whole-file implementation hashes are retired.
  The OPEX value was already superseded by hierarchical OPEX migration; evolving
  production modules are protected by semantic tests, review scope, and current
  exact-head gates. Immutable source-extraction report hashes remain blocking.

## G2B Simple Sponsor Returns canonical authority

### Pure Legal Equity

Outflows: share-capital contributions + share-premium contributions +
other-committed-equity contributions + additional-equity contributions
(all from G2A construction funding schedule).

Inflows: legal-equity distributions (operating periods only).

### Total Sponsor

Outflows: all Pure Legal Equity outflows + SHL cash principal contributions.

Inflows: legal-equity distributions + ACTUAL SHL cash interest paid +
ACTUAL SHL principal paid from available project cash.

Contractual SHL amounts due but unpaid because of a project cash deficit are
NOT sponsor cash receipts.  They remain visible through `cash_shortfall_keur`.

PIK accrual is not a sponsor cash receipt at accrual time.  When available
project cash actually repays the capitalised SHL balance (which may include
accrued PIK), that actual paid amount enters Total Sponsor receipts.  If the
contractual due amount exceeds available cash, only the portion actually paid
enters receipts; the remainder is a cash shortfall.

Actual SHL cash receipt derivation (per operating period):

```
cash_available_for_shl = max(0, signed_post_senior)
actual_cash_interest   = min(scheduled_cash_interest, cash_available_for_shl)
cash_after_interest    = max(0, cash_available_for_shl - actual_cash_interest)
actual_principal       = min(max(0, scheduled_principal_due), cash_after_interest)
```

Signed project cash deficits (CFADS < Senior debt service, or contractual
SHL service due > available post-Senior cash) are exposed as
`cash_shortfall_keur` and are not automatically funded by sponsor
contributions, top-ups, or balancing items.

`DISTRIBUTE_ALL_POST_SHL_CASH` is a Generic MVP distribution policy.
It is not an institutional waterfall, a lock-up covenant, or an Excel
parity rule.

### Timing

Construction cashflow dates: `financial_close + (period_index − 1) months`.
This is the Generic MVP sponsor-return timing projection over the G2A
monthly funding periods, not an Excel source-truth draw axis.

Operating cashflow dates: `period_end` from the clean engine operating
period grid.

## Current blocking ring

1. MVP G2B Simple Sponsor Returns
2. MVP G2A Financing Stack and Derived SHL
3. MVP G1 Governance & Methodology Lock
4. MVP G0 Generic Clean Engine
5. C3B3D2B5 SHL Fixed-Point Integration
6. C3B3D2B6 Base/Post-Senior Cash
7. C3B3D2B7 Bank/Senior Source Parity
8. C3B3D2B8 Base/Senior/SHL Closure
9. C3B1 source-truth evidence
10. C3B3A clean Senior contract
11. CI product smoke/persistence and current semantic core checks
12. Parity Guardrails semantic outputs, immutable source hashes, and import boundaries

Phase 2A, Phase 2B, C3B3B/C3B3C/C3B3D0/C3B3D1/C3B3D2A/B0-B4,
Phase 2C, and Phase 2D are manual historical or diagnostic workflows unless a later
authority explicitly promotes a surviving assertion. A workflow-authority test
locks those workflows to `workflow_dispatch` while preserving automatic
pull-request execution for every member of the current blocking ring.
