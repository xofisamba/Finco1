# Phase 5A: Retained Earnings Foundation — Architecture & Planning

## Overview

Phase 5A establishes the **planning and data-model foundation** for explicit
retained earnings and cash retention, before sponsor waterfall and advanced tax.

**Implementation status:** Phase 5A **partially implemented** — cash ledger
domain package (`domain/portfolio/cash_ledger/`) is live. No financial outputs
changed. Retained earnings blocking is **not yet implemented**.

### Implemented (Phase 5A)
| Component | Status |
|-----------|--------|
| `CashMovementType` enum | ✅ Implemented |
| `CashMovement` dataclass | ✅ Implemented |
| `CashLedgerPeriod` | ✅ Implemented |
| `EntityCashLedger` | ✅ Implemented |
| `PortfolioCashLedger` | ✅ Implemented |
| `build_entity_cash_ledger` | ✅ Implemented |
| `build_portfolio_cash_ledger` | ✅ Implemented |
| `reconcile_cash_ledger` | ✅ Implemented |
| `movements_from_holdco_result` adapter | ✅ Implemented |
| `movements_from_spv_output` adapter | ✅ Implemented |
| Retained earnings blocking | ❌ Not implemented |
| SPVCashAccount / HoldCoCashAccount | ❌ Not implemented |

### Clear constraints (Phase 5A — audit layer only)
- This is audit/accounting layer only — **no waterfall economics changed**
- **No distribution constraints implemented**
- SHL principal is mapped as cash movement only, **not yet used to constrain distributions**
- **No Sponsor IRR implemented**
- **No HoldCo IRR implemented**
- **No tax engine implemented**

## Current State (as of Phase 4C)

The model currently handles cash distribution as follows:

| Concept | Status |
|---------|--------|
| `distribution_keur` | Equity cash distributable after senior debt, SHL, reserves |
| DSRF | Already reduces `adjusted_period_distributions_keur` |
| SHL enrichment (Phase 4C) | Adds `shl_interest_keur` / `shl_principal_keur` as **metadata** on waterfall periods |
| SHL principal | **Does NOT reduce** `distribution_keur` in Phase 4C |
| SPV cash ledger | **Does not exist** — cash is implicit |
| Retained earnings account | **Does not exist** |
| HoldCo cash account | **Does not exist** |
| Cash vs P&L separation | **Not explicit** — `distribution_keur` conflates cash flows |

## Why Phase 5A is Needed

1. **SHL principal repayments consume SPV cash** — currently not reflected in distributions
2. **HoldCo debt service** — future HoldCo own debt requires a cash account with explicit balances
3. **Sponsor waterfall** — equity cascade requires knowing how much cash is actually available at each tier
4. **Tax engine** — eventual cash-vs-P&L separation needed; tax deductibility of SHL interest requires cash-flow tracking
5. **DSRF consistency** — commitment fees, interest, repayments are real cash movements that should appear in ledger

## Target Future Architecture

```
SPV operations
  → senior debt service
  → DSRF effects
  → taxes
  → retained cash decisions        ← NEW: explicit retention policy
  → SHL servicing                 ← NEW: SHL principal reduces distributable cash
  → equity distributions          ← NEW: residual after all prior claims
  → HoldCo cash account           ← NEW: explicit HoldCo cash balance
  → future sponsor waterfall      ← DEFERRED: equity cascade
```

**Key principle:** Distributions should become **residual cash** after all prior claims (debt, DSRF, tax, SHL, retention).

## Proposed Data Model (Future — NO Implementation in Phase 5A)

### SPVCashAccount
```python
@dataclass(frozen=True)
class SPVCashAccount:
    """SPV-level cash ledger tracking inflows and outflows by type."""
    spv_code: str
    period_index: int
    opening_balance_keur: float        # prior period closing
    senior_debt_service_keur: float   # outflow: senior interest + principal
    dsrf_outflow_keur: float          # outflow: commitment fee + drawn interest + repayment
    tax_paid_keur: float              # outflow: corporate tax
    shl_interest_paid_keur: float    # outflow: SHL interest (not principal)
    shl_principal_paid_keur: float    # outflow: SHL principal repayment
    retained_cash_keur: float        # outflow: cash retained per policy
    distributable_cash_keur: float    # residual: available for distribution
    closing_balance_keur: float       # opening + all movements
```

### HoldCoCashAccount
```python
@dataclass(frozen=True)
class HoldCoCashAccount:
    """HoldCo-level cash account aggregating SPV distributions."""
    period_index: int
    opening_balance_keur: float
    spv_distributions_keur: float      # inflows: dividend + SHL interest
    holdco_opex_keur: float           # outflows: HoldCo operating costs
    holdco_tax_keur: float             # outflows: HoldCo entity tax
    holdco_debt_service_keur: float   # future: HoldCo own debt service
    distributions_to_sponsor_keur: float
    closing_balance_keur: float
```

### RetainedEarningsBalance
```python
@dataclass(frozen=True)
class RetainedEarningsBalance:
    """Per-period retained earnings ledger entry."""
    spv_code: str
    period_index: int
    opening_retained_keur: float
    retained_this_period_keur: float
    released_this_period_keur: float   # future: release to distributable pool
    closing_retained_keur: float
```

### DistributionBlockReason
```python
enum DistributionBlockReason:
    RESERVE_REQUIRED   # DSRA/MRA reserve not fully funded
    LOCKUP_ACTIVE      # DSCR covenant breach (lockup triggered)
    RETAINED_EARNINGS  # cash held for future capital needs
    SHL_PRINCIPAL_HOLD # SHL principal holdback pending confirmation
    SPONSOR_WATERFALL  # sponsor waterfall tiers not yet resolved
```

### CashMovementType Enum
```python
enum CashMovementType:
    # Inflows
    SPV_DISTRIBUTION
    SHL_INTEREST_RECEIPT
    SHL_PRINCIPAL_RECEIPT
    DSRF_DRAW
    # Outflows
    SENIOR_DEBT_SERVICE
    DSRF_COMMITMENT_FEE
    DSRF_INTEREST
    DSRF_REPAYMENT
    SHL_INTEREST_PAYMENT
    SHL_PRINCIPAL_PAYMENT
    CORPORATE_TAX
    RETAINED_CASH
    HOLDCO_OPEX
    HOLDCO_DEBT_SERVICE
    # Equity
    EQUITY_DISTRIBUTION
    SPONSOR_DISTRIBUTION
```

## Constraints (Phase 5A Planning Scope)

| Constraint | Status |
|---|---|
| No recursive entity graph | Required |
| No circular funding | Required |
| No monthly model | Required |
| No tax optimization | Required |
| No treasury optimization | Required |
| No waterfall redesign | Required |
| No HoldCo IRR | Required |
| No Sponsor IRR | Required |
| No refinancing logic | Required |
| No implementation of above data model | Required for Phase 5A |

## Technical Debt & Risks (Current)

1. **In-place SHL enrichment** — `enrich_portfolio_result_with_shl` mutates waterfall period objects in-place. Future immutable refactor may replace with copy-on-write.
2. **No explicit cash ledger** — current model conflates P&L with cash flow. Distributable cash is implicit, not tracked per category.
3. **SHL principal is metadata only** — in Phase 4C, `shl_principal_keur` does not reduce `distribution_keur`. Future retained earnings phase must handle this.
4. **Future sponsor waterfall dependency** — sponsor equity cascade requires explicit per-tier cash availability.
5. **Future tax engine dependency** — eventual SHL interest deductibility requires cash-flow attribution to entity.
6. **DSRF cash flows are separate from waterfall** — DSRF costs are tracked in `adjusted_period_distributions_keur` but not written back to waterfall period objects in a ledger-consistent way.



## Phase 5B — Optional Cash Ledger Integration

**Status:** ✅ Implemented

`build_cash_ledger_from_results()` wires the Phase 5A ledger foundation to
existing `IndependentPortfolioResult` and `HoldCoResult` objects as an **optional
audit output**. No financial outputs change.

### Implemented
| Component | Status |
|-----------|--------|
| `build_cash_ledger_from_results()` | ✅ Implemented |
| Exports via `domain.portfolio.cash_ledger` | ✅ Exported |
| `movements_from_spv_output()` integration | ✅ Integrated |
| `movements_from_holdco_result()` integration | ✅ Integrated |
| Opening cash per entity support | ✅ Supported |
| No mutation of source results | ✅ Guaranteed |

### Constraints (Phase 5B)
- **Audit layer only** — does not modify waterfall economics
- **No distribution blocking** — retained earnings constraints not yet implemented
- **No HoldCo IRR / Sponsor IRR**
- **No tax engine**
- **No sponsor waterfall**
- **No monthly model**

### API
```python
from domain.portfolio.cash_ledger import build_cash_ledger_from_results

ledger = build_cash_ledger_from_results(
    portfolio_result=portfolio_result,   # IndependentPortfolioResult | None
    holdco_result=holdco_result,         # HoldCoResult | None
    opening_cash_by_entity={"SOLAR-1": 100.0},  # optional
)
# ledger is a PortfolioCashLedger
```

### Future Use
- Excel export: ledger data alongside waterfall KPIs
- UI dashboard: cash position by entity and period
- Distribution audit trail: trace SPV distributions → HoldCo → sponsor

## Phase Sequencing (Tentative)

| Phase | Focus |
|-------|-------|
| Phase 4A | SHL straight-line engine + data model |
| Phase 4B | HoldCo SHL-ready fields |
| Phase 4C | SHL end-to-end integration (enrichment layer) |
| **Phase 5A** | **Planning + data model for retained earnings** |
| **Phase 5B** | **Optional cash ledger integration (orchestrator)** |
| **Phase 5C** | **Retained cash/distribution constraint architecture** |
| Phase 5D | HoldCoCashAccount implementation |
| Phase 5E | Sponsor waterfall |
| Phase 5F | Tax engine foundation |



## Phase Status

| Phase | Status |
|-------|--------|
| Phase 5A | ✅ Merged — cash ledger foundation |
| Phase 5B | ✅ Merged — optional cash ledger integration |
| Phase 5C | 📐 Current — retained cash/distribution constraint architecture (design only) |

## Open Questions

1. Should retained earnings be per-SPV or portfolio-level?
2. Is release policy deterministic (fixed schedule) or policy-driven (triggered by DSCR)?
3. Does SHL principal holdback apply before or after DSRF deduction?
4. Should HoldCo cash account be single-currency or multi-currency?
5. Is there a need for a "distribution holiday" concept when lockup is active?
