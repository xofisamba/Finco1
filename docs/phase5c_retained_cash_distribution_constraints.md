# Phase 5C: Retained Cash & Distribution Constraint Architecture

**Type:** Design / Architecture documentation only
**Status:** Phase 5C — NOT IMPLEMENTED

---

## 1. Current State

The model currently handles cash distribution as follows:

| Concept | Status |
|---|---|
| `distribution_keur` | Equity distributable after senior debt, SHL, reserves — **unchanged** |
| `adjusted_period_distributions_keur` | Already reflects DSRF cash costs reducing distributable |
| SHL principal | **Metadata / cash ledger movement only** — tracked but does NOT reduce `distribution_keur` |
| SPV cash ledger | Audit-only (`build_cash_ledger_from_results()`) — does not control waterfall |
| HoldCo cash | Audit-only — distributions still flow through waterfall as before |
| Retained earnings blocking | **Does not exist** |
| HoldCo closing cash constraint | **Does not exist** |
| Cash-vs-P&L separation | **Not explicit** |

### What the cash ledger currently captures

The Phase 5A/5B cash ledger maps existing waterfall outputs to an accounting representation:
- SPV equity distributions (DSRF-adjusted preference)
- SHL interest and principal from waterfall periods
- HoldCo dividends, opex, tax, sponsor distributions
- No distribution blocking or constraint enforcement

### What it does NOT yet do

- The waterfall still produces `distribution_keur` without knowing about SHL principal or retention policies
- `adjusted_period_distributions_keur` reduces distributions for DSRF costs, but SHL principal is not yet a deduction
- Sponsor/HoldCo distributions cannot yet be constrained by actual cash availability

---

## 2. Problem Statement

### Why retained cash is needed

**SHL principal consumes SPV cash** — currently `shl_principal_keur` is recorded as a metadata annotation on waterfall periods but does not reduce distributable cash. In a real project finance structure, SHL principal repayments are real cash outflows that compete with equity distributions.

**HoldCo cash should roll forward explicitly** — HoldCo receives dividends and SHL interest/principal from SPVs and pays opex, tax, and sponsor distributions. The current HoldCo result computes a distribution_to_sponsor without an explicit cash roll-forward.

**Sponsor distributions need cash backing** — Phase 3B HoldCo computes `distribution_to_sponsor_keur` as a residual after opex and tax, but it does not verify that HoldCo has sufficient closing cash to actually pay it.

**Tax and sponsor waterfall require cash-vs-P&L separation** — SHL interest deductibility, withholding tax, and eventual sponsor waterfall tiers all depend on knowing actual cash positions, not just P&L residuals.

**The current model cannot enforce distribution capacity** — if SPV cash is tight, the waterfall still outputs a distribution. There is no mechanism to hold back distributions for reserves or SHL repayment sequencing.

---

## 3. Target Future Concepts (NOT IMPLEMENTED)

These are design concepts for future phases — no implementation in Phase 5C.

```python
# 3.1 Cash Available for Distribution
@dataclass(frozen=True)
class CashAvailableForDistribution:
    """Result of cash waterfall sequencing at SPV level."""
    period: int
    spv_code: str
    opening_cash_keur: float
    gross_cash_inflow_keur: float        # operating CF / CFADS
    senior_debt_service_keur: float       # outflow
    dsrf_total_outflow_keur: float        # draws + interest + repayments + fees
    tax_paid_keur: float                  # outflow
    retained_cash_required_keur: float   # minimum cash hold
    shl_interest_keur: float             # outflow
    shl_principal_keur: float            # outflow
    cash_available_for_distribution_keur: float  # residual
    equity_distribution_keur: float       # min(cash_available, waterfall distribution)
    closing_cash_keur: float


# 3.2 Retained Cash Balance
@dataclass(frozen=True)
class RetainedCashBalance:
    """Per-period retained cash position for an entity."""
    period: int
    entity_code: str
    opening_retained_keur: float
    retained_this_period_keur: float
    released_this_period_keur: float
    closing_retained_keur: float


# 3.3 Distribution Constraint
@dataclass(frozen=True)
class DistributionConstraint:
    """A single constraint that may block or reduce a distribution."""
    period: int
    entity_code: str
    reason: "DistributionBlockReason"
    blocked_amount_keur: float
    message: str


# 3.4 Distribution Block Reason
enum DistributionBlockReason:
    RESERVE_REQUIRED       # DSRA/MRA reserve not fully funded
    LIQUIDITY_COVANT        # DSCR or other covenant breach triggers lockup
    RETAINED_EARNINGS_HOLD # cash held for future capital needs
    SHL_PRINCIPAL_HOLDBACK # SHL principal repayment pending
    SPONSOR_WATERFALL_TIER  # cash does not reach this tier
    NEGATIVE_CASH           # closing cash would go negative
    MANUAL_HOLD            # user-configured distribution pause


# 3.5 Required Minimum Cash Balance
@dataclass(frozen=True)
class RequiredMinimumCashBalance:
    """Per-entity minimum cash requirement."""
    entity_code: str
    amount_keur: float                       # fixed minimum
    # OR
    percent_of_next_period_opex: float        # dynamic: % of next period costs


# 3.6 Cash Sweep Policy
@dataclass(frozen=True)
class CashSweepPolicy:
    """Defines how excess cash above minimum is allocated."""
    minimum_cash_keur: float
    sweep_to_senior_debt: bool = False        # optional senior prepayment
    sweep_to_shl_principal: bool = False      # accelerate SHL repayment
    sweep_to_retained_earnings: bool = True   # hold in retained cash
    max_sweep_per_period_keur: float = 0.0   # 0 = unlimited


# 3.7 SHL Principal Payment Policy
@dataclass(frozen=True)
class SHLPrincipalPaymentPolicy:
    """Defines when and how SHL principal is repaid."""
    sequencing: str  # "before_equity" | "after_equity" | "proportional"
    holdback_percent: float = 0.0   # retain X% of SHL principal
    min_cash_before_payment_keur: float = 0.0


# 3.8 HoldCo Distribution Policy
@dataclass(frozen=True)
class HoldCoDistributionPolicy:
    """Defines sponsor distribution constraints at HoldCo level."""
    min_closing_cash_keur: float = 0.0           # minimum HoldCo closing cash
    distribution_limited_to_available: bool = True  # hard cap on sponsor dist
    retained_cash_pct: float = 0.0             # retain X% of excess cash
```

---

## 4. Proposed Future Sequencing

### SPV Cash Waterfall Sequencing (Future)

```
SPV opening cash
  + operating cashflow / CFADS
  - senior debt service (interest + principal)
  +/- DSRF draws / repayments / commitment fee / drawn interest
  - tax paid
  - required reserves / retained cash
  - SHL interest
  - SHL principal
  = cash available for equity distribution
  - equity distribution (capped at cash available)
  = SPV closing cash
```

**Key rule:** Equity distribution = `min(cash_available, waterfall_distribution_keur)`

### HoldCo Cash Waterfall Sequencing (Future)

```
HoldCo opening cash
  + dividends received from SPVs
  + SHL interest received from SPVs
  + SHL principal received from SPVs
  - HoldCo opex
  - HoldCo tax
  - required retained cash
  = cash available for sponsor distribution
  - sponsor distribution (capped at cash available)
  = HoldCo closing cash
```

---

## 5. Explicit Decisions Needed Before Implementation

The following questions must be resolved before coding Phase 5D:

1. **SHL principal sequencing** — should SHL principal repayment be deducted from cash BEFORE equity distributions are computed, or AFTER distributions are computed (i.e., equity gets residual)?

2. **SHL interest ranking** — should SHL interest always rank before equity distributions, or is it optional (based on policy)?

3. **Retained cash formulation** — should it be:
   - Fixed minimum balance (manual input)?
   - Percentage of next period senior debt + opex?
   - Percentage of CFADS?
   - Combination?

4. **Scope of constraint enforcement** — should distribution constraints apply at:
   - SPV level only?
   - HoldCo level only?
   - Both (SPV constraint limits upstream dividends, HoldCo constraint limits sponsor distribution)?

5. **Negative cash response** — if closing cash would go negative:
   - Warning only?
   - Hard block (distribution = 0)?
   - Partial distribution (cash-limited)?

6. **HoldCo closing cash constraint** — should sponsor distributions be hard-limited by HoldCo closing cash balance, or is warning-only acceptable?

7. **Tax timing** — how do tax payments align with cash ledger periods? Corporate tax is computed annually but paid quarterly/monthly — should cash ledger track timing nuance?

8. **DSRF interaction** — DSRF already reduces `adjusted_period_distributions_keur`. Does SHL principal add an additional deduction, or does it replace DSRF-adjusted distributions?

---

## 6. Recommended Phase 5D Implementation Sequence

### Phase 5D.1 — Data Models Only
- Define `DistributionBlockReason` enum
- Define `DistributionConstraint` dataclass
- Define `CashAvailableForDistribution` dataclass
- Define `RetainedCashBalance` dataclass
- No business logic — pure type definitions

### Phase 5D.2 — Calculation Helper
- `compute_cash_available_for_distribution(spv_output, policy)` — pure function
- Takes SPV output + policy objects
- Returns `CashAvailableForDistribution`
- No mutation, no side effects
- `compute_holdco_cash_available(holdco_result, policy)` — similarly

### Phase 5D.3 — SPV Retained Cash Overlay (Audit-Only)
- Wire D.2 helper into portfolio orchestrator
- `build_cash_ledger_from_results()` gains optional `spv_policy` parameter
- Emit retained cash movements in ledger
- **No enforcement** — still emits all movements, adds audit annotation

### Phase 5D.4 — HoldCo Retained Cash Overlay (Audit-Only)
- Same pattern for HoldCo
- Add `holdco_policy` parameter
- Audit annotation on HoldCo ledger

### Phase 5D.5 — Optional Enforcement Mode
- `enforcement_mode=True/False` flag
- When disabled (default): audit-only, no distribution changes
- When enabled: apply distribution constraints, emit warnings
- Waterfall outputs still unchanged — constraint is a wrapper/overlay

---

## 7. Non-Scope

The following are explicitly NOT implemented in Phase 5C or any immediate follow-up:

- Tax engine (withholding tax, ATAD, transfer pricing)
- HoldCo IRR
- Sponsor IRR
- Sponsor waterfall (equity cascade tiers)
- Legal dividend tests (solvency, retained earnings tests under local law)
- Monthly model
- Actual distribution blocking (hard enforcement)
- Waterfall redesign
- Pooled financing redesign
- Refinancing logic

---

*Phase 5C is design documentation only. No code changes were made in this phase.*