# Phase 5D.1: Distribution Constraint Evaluation Foundation

**Type:** Data-model-only foundation
**Status:** Phase 5D.1 — NOT wired into waterfall engine

---

## Overview

Phase 5D.1 establishes the **domain-model foundation** for distribution constraint evaluation. It provides pure data types and a pure evaluation helper — no waterfall economics are changed, no distributions are blocked, no enforcement is active.

This phase exists solely to define the data vocabulary and constraint evaluation logic that Phase 5D.3–5D.5 will wire into the portfolio orchestrator and optionally into the HoldCo runner.

---

## What Is Implemented

### Domain Package: `domain/portfolio/distribution_constraints/`

| File | Contents |
|---|---|
| `inputs.py` | `DistributionBlockReason` enum (9 values), `DistributionConstraintConfig` dataclass |
| `result.py` | `DistributionConstraintPeriod`, `DistributionConstraintResult` frozen dataclasses |
| `runner.py` | `evaluate_distribution_constraints()` pure helper |

### DistributionBlockReason Enum

```python
enum DistributionBlockReason:
    NONE                     # no constraint applied
    NEGATIVE_CASH            # cash available is negative
    MINIMUM_CASH_RESERVE     # would breach minimum cash reserve
    DSRF_REPAYMENT           # DSRF repayment claim
    SHL_PRINCIPAL_REPAYMENT # SHL principal repayment claim
    HOLDCO_RESTRICTION      # HoldCo-level restriction
    TAX_RESTRICTION         # tax-related restriction
    MANUAL_LOCKUP           # user-configured distribution pause
    OTHER                   # catch-all
```

### DistributionConstraintConfig

```python
@dataclass(frozen=True)
class DistributionConstraintConfig:
    enabled: bool = False                         # opt-in; default OFF
    minimum_cash_reserve_keur: float = 0.0       # must be >= 0
    allow_negative_cash: bool = False            # suppress NEGATIVE_CASH warning
    manual_lockup_periods: tuple[int, ...] = ()   # locked period indices
```

**Key design decision:** `enabled=False` by default. The default configuration is a full pass-through, ensuring no existing code is affected unless it explicitly opts in.

### evaluate_distribution_constraints()

```python
evaluate_distribution_constraints(
    entity_code: str,
    cash_available_by_period: tuple[float, ...],
    requested_distributions_by_period: tuple[float, ...],
    config: DistributionConstraintConfig | None = None,
) -> DistributionConstraintResult
```

**Pure function — no mutation of inputs.** Returns a new `DistributionConstraintResult`. The waterfall engine is not called, not modified, and not aware of this function.

**Constraint application order per period:**
1. Manual lockup → `allowed = 0`, `reason = MANUAL_LOCKUP`
2. Minimum cash reserve → `allowed = min(requested, max(0, cash - reserve))`
3. Negative cash → `reason = NEGATIVE_CASH` (warning only in Phase 5D.1; hard block in Phase 5D.5)

---

## What Is NOT Implemented

| Item | Status |
|---|---|
| Wiring into `build_cash_ledger_from_results()` | ❌ Not wired |
| Wiring into HoldCo runner | ❌ Not wired |
| Wiring into waterfall | ❌ Not wired |
| Hard distribution blocks | ❌ Phase 5D.5 |
| Actual cash deduction from cash ledger | ❌ Phase 5D.3 |
| HoldCo closing cash constraint | ❌ Phase 5D.4 |
| Retained earnings policy | ❌ Future phase |

---

## Relationship to Cash Ledger (Phase 5A/5B)

The cash ledger (`domain/portfolio/cash_ledger/`) provides the **cash position by period** for each entity. `evaluate_distribution_constraints()` consumes that information:

```python
# Future Phase 5D.3 integration (NOT in this phase):
ledger = build_cash_ledger_from_results(portfolio_result=portfolio_result)
cash_by_period = tuple(p.closing_cash_keur for p in ledger.entities[0].periods)
requested = portfolio_result.spv_outputs[0].adjusted_period_distributions_keur

result = evaluate_distribution_constraints(
    entity_code="SOLAR-1",
    cash_available_by_period=cash_by_period,
    requested_distributions_by_period=requested,
    config=DistributionConstraintConfig(enabled=True, minimum_cash_reserve_keur=100.0),
)
```

The cash ledger is the **source of truth** for `cash_available_by_period`. This phase defines how to evaluate constraints against that data — it does not compute cash positions.

---

## Relationship to SHL Principal Repayment

SHL principal repayments are a **cash outflow** that reduces the cash available for equity distribution. In the Phase 5D.3 audit-only overlay, SHL principal will be added to the SPV cash ledger as a negative movement (using `movements_from_spv_output` which already maps `shl_principal_keur`).

The Phase 5D constraint evaluation reads the resulting closing cash position, so SHL principal is implicitly accounted for through the cash ledger roll-forward.

---

## Relationship to Future Retained Earnings Enforcement

Phase 5D.5 (`enforcement_mode=True`) will wire `DistributionConstraintResult.allowed_distribution_keur` into the HoldCo runner as a **read** from the constrained field — similar to how `adjusted_period_distributions_keur` is read over `distribution_keur` today.

The data model supports this without change:
- `allowed_distribution_keur <= requested_distribution_keur` is enforced at construction
- `block_reasons` provides auditable traceability for every constraint applied

---

## Phase Sequencing

| Phase | Focus | Status |
|---|---|---|
| Phase 5A | Cash ledger foundation | ✅ Merged |
| Phase 5B | Cash ledger integration | ✅ Merged |
| Phase 5C | Retained cash design | ✅ Merged |
| **Phase 5D.1** | **Constraint data models** | **Current |
| Phase 5D.2 | `compute_cash_available_for_distribution()` helper | Planned |
| Phase 5D.3 | SPV retained cash overlay (audit-only) | Planned |
| Phase 5D.4 | HoldCo retained cash overlay (audit-only) | Planned |
| Phase 5D.5 | Optional enforcement mode | Planned |

---



## Phase 5D.2 — Cash Ledger Integration

**Status:** Implemented

`evaluate_constraints_from_portfolio_ledger()` bridges the Phase 5A/5B cash ledger with the Phase 5D.1 constraint evaluator as an optional audit-only step.

### What is wired together

```
cash ledger (EntityCashLedger)
  → cash_available_by_period_from_entity_ledger()
     = opening_cash + all movements EXCEPT EQUITY_DISTRIBUTION + SPONSOR_DISTRIBUTION
  → evaluate_distribution_constraints(cash_available, requested_distribution)

cash ledger movements
  → requested_distributions_from_entity_ledger()
     = sum of |EQUITY_DISTRIBUTION| + |SPONSOR_DISTRIBUTION| per period
  → evaluate_distribution_constraints(requested=...)
```

### Four integration helpers

| Function | Purpose |
|---|---|
| `cash_available_by_period_from_entity_ledger()` | Derives cash before distributions from ledger |
| `requested_distributions_from_entity_ledger()` | Extracts distribution amounts from ledger |
| `evaluate_constraints_from_entity_ledger()` | Single-entity constraint evaluation |
| `evaluate_constraints_from_portfolio_ledger()` | Multi-entity evaluation with per-entity config |

### Key properties

- **No mutation** — all functions are pure reads from the cash ledger
- **No waterfall changes** — constraint evaluation is a separate result object
- **No distribution blocking** — result is informational; enforcement requires Phase 5D.5 opt-in
- **Config per entity** — `config_by_entity` dict maps entity codes to individual configs
- **Default config fallback** — unconfigured entities use `default_config` (or pass-through)

### Future use

This integration is the foundation for Phase 5D.3 (SPV retained cash overlay) and Phase 5D.4 (HoldCo retained cash overlay). When those phases are implemented, they will populate `DistributionConstraintConfig` with the entity's specific policy and call these same functions.

---




## Phase 5D.3 — SPV Retained Cash Overlay

**Status:** Implemented

`SPVRetainedCashOverlay` and `SPVRetainedCashPeriod` are audit-only result objects that show what distributions WOULD be constrained to, and what cash WOULD be retained, without changing any SPVOutput or waterfall field.

### What this phase adds

```python
from domain.portfolio.distribution_constraints import (
    SPVRetainedCashPeriod,
    SPVRetainedCashOverlay,
    build_spv_retained_cash_overlay,
    build_spv_retained_cash_overlays_from_portfolio_ledger,
)
```

Three key functions:
- `build_spv_retained_cash_overlay(constraint_result)` — maps DistributionConstraintResult → SPVRetainedCashOverlay
- `build_spv_retained_cash_overlays_from_portfolio_ledger(portfolio_ledger, config_by_entity, default_config)` — evaluates and maps all entities
- `evaluate_constraints_from_portfolio_ledger()` (from D.2) — computes constraint results from cash ledger

### Overlay properties

| Property | Value |
|---|---|
| No SPVOutput mutation | ✅ |
| No distribution_keur change | ✅ |
| No enforcement | ✅ — audit-only |
| Uses cash ledger (D.2) | ✅ |
| Uses constraint evaluator (D.1) | ✅ |
| No filtering by entity type | All entities included |

### Future enforcement path

When Phase 5D.5 implements `enforcement_mode=True`, the `SPVRetainedCashOverlay.allowed_distribution_keur` will be wired into the HoldCo runner as a read (over `adjusted_period_distributions_keur`). The overlay is the "audit trail" that shows what the enforcement WOULD produce.

---




## Phase 5D.4 — HoldCo Retained Cash Overlay

**Status:** Implemented

`HoldCoRetainedCashOverlay` is an audit-only HoldCo-level retained cash result that shows what sponsor distributions WOULD be available after retained cash deduction, without changing any HoldCo result field.

### What this phase adds

```python
from domain.portfolio.distribution_constraints import (
    HoldCoRetainedCashOverlay,
    build_holdco_retained_cash_overlay,
    holdco_requested_distribution_by_period,
    holdco_available_distribution_by_period,
)
```

Three functions:
- `holdco_requested_distribution_by_period(holdco_result)` — reads `distribution_to_sponsor_keur` per period, falls back to 0.0
- `holdco_available_distribution_by_period(holdco_result, retained_cash_by_period)` — computes `max(0, requested - retained)` with zero-padding
- `build_holdco_retained_cash_overlay(holdco_result, retained_cash_by_period)` — returns full `HoldCoRetainedCashOverlay`

### Key properties

| Property | Value |
|---|---|
| No HoldCo result mutation | ✅ |
| No waterfall changes | ✅ |
| No actual distribution blocking | ✅ |
| Uses `_safe_float` for all numeric reads | ✅ |
| Length mismatch emits warning | ✅ |
| available_distribution >= 0 always | ✅ |

### Future path

This overlay is the foundation for Phase 5D.5 optional enforcement mode, where `available_distribution_by_period` would be compared against actual sponsor distribution to detect or enforce constraints.

---


## Non-Scope

Explicitly out of scope for Phase 5D.1 and all near-term follow-ups:

- Tax engine / withholding tax / ATAD / transfer pricing
- HoldCo IRR computation
- Sponsor IRR computation
- Sponsor waterfall (equity cascade)
- Legal dividend tests (solvency, distributable profits)
- Monthly model
- Pooled financing redesign
- Refinancing logic

*Phase 5D.1 is a data-model-only foundation. No waterfall economics are modified.*