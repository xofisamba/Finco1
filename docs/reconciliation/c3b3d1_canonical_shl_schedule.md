# C3B3D1 — Canonical SHL Accrual/Balance Schedule

**Stage:** C3B3D1
**Branch:** `stage-c3b3d1-canonical-shl-schedule`
**Blocker removed:** `NO_GENERIC_CANONICAL_PERIOD_SHL_INTEREST_SOURCE`

---

## 1. Why the legacy SHL engine is not the canonical tax-interest authority

The legacy `finco_core.shl.engine.ShlEngine` is waterfall-coupled: it
accepts `post_senior_cash_available_keur` per period and uses cash availability
to decide whether interest is paid in cash or PIK. Its interest accrual is
therefore a function of the waterfall state at runtime.

The canonical tax engine (`financial_engine/tax/`) requires interest as an
exogenous input (`PeriodInterestInput.shl_interest_keur`). Feeding the legacy
engine's output back into the tax engine creates a circular dependency:

    tax(shl_interest) → CFADS → SHL cash available → SHL interest → tax(shl_interest)

The canonical `financial_engine/shl/` package breaks this loop by computing
SHL accrual deterministically from opening balance + drawdown + rate + DCF,
without reference to post-senior cash availability.

---

## 2. Non-circular canonical schedule boundary

The canonical schedule is:
- **BALANCE-DRIVEN**: interest = f(balance, rate, day_count_fraction)
- **CASH-WATERFALL-INDEPENDENT**: no post_senior_cash input
- **DETERMINISTIC**: given fixed opening balance and policy, output is fully determined

D2 wiring: `ShlPeriodResult.gross_accrued_interest_keur` flows into
`PeriodInterestInput.shl_interest_keur`. Deductibility is then determined by
`ShlInterestDeductibilityMode` / ATAD / thin-cap / other TaxPolicy mechanics —
NOT by this schedule. Gross SHL interest is not deductible interest; TaxPolicy
decides how much is deductible.

---

## 3. Balance roll-forward identity

```
balance_for_interest  = opening_balance + drawdown
gross_interest        = balance_for_interest × annual_rate × day_count_fraction
cash_interest         = gross_interest   if CASH_PAID  else 0
pik_interest          = gross_interest   if PIK        else 0
closing_balance       = opening_balance + drawdown + pik_interest - scheduled_principal
```

Invariant: `closing_balance >= 0` (absorbed for floating-point dust with `max(·, 0)`).

---

## 4. Gross vs cash vs PIK interest

| Field | CASH_PAID | PIK |
|---|---|---|
| `gross_accrued_interest_keur` | rate × balance × dcf | rate × balance × dcf |
| `cash_interest_keur` | = gross | 0 |
| `pik_interest_keur` | 0 | = gross |
| Effect on closing balance | none (cash out) | +gross (capitalised) |

The canonical schedule does not model mixed (PIK-then-cash) modes — these are
deferred to a later stage via `shl_pik_switch_period > 0` detection in the
adapter (fail-closed: `C3B3D1_BLOCKED_MIXED_PAYMENT_MODE`).

---

## 5. Supported repayment modes

| Mode | Mechanism |
|---|---|
| `BULLET` | Full outstanding balance repaid at `maturity_period_index`. All other periods: `scheduled_principal = 0`. |
| `EXPLICIT_SCHEDULE` | Per-period `scheduled_principal_keur` from `ShlPeriodInput`. |

---

## 6. Unsupported modes — fail-closed

The following repayment modes raise `NotImplementedError` in C3B3D1:

- `FCF_WATERFALL` — requires later-stage cash-waterfall integration
- `CASH_SWEEP` — requires later-stage cash-waterfall integration
- `PIK_THEN_SWEEP` — requires later-stage period-level mode switching
- `PARTIAL_PAY_SWEEP` — requires later-stage cash integration
- `pik` / `accrued` method strings — no source evidence maps these to
  EXPLICIT_SCHEDULE period-principal semantics (`C3B3D1_BLOCKED_LEGACY_REPAYMENT_SEMANTICS`)

The fail-closed set is `_FCF_WATERFALL_METHODS` in the adapter. These are never
silently treated as BULLET.

---

## 7. Interest settlement vs accounting classification

CASH_PAID and PIK are **settlement mechanics** — how interest is settled
each period (cash out vs capitalised into principal). They are NOT accounting
classification policy (income-statement expense vs. asset capitalisation).

The SHL schedule does not determine accounting classification. Whether accrued
SHL interest is expensed to P&L or capitalised to an asset is an accounting
policy question outside C3B3D1 scope.

---

## 8. Payment mode status: C3B3D1_BLOCKED_PAYMENT_MODE_SEMANTICS

`shl_pik_switch_period` is defined in `FinancingParams` (default 0) but is
**not consumed by any runtime code** outside serialization.

The legacy waterfall engine computes `pik_switch_triggered` at runtime from:

    pik_switch_triggered = (cf_for_shl > shl_balance × shl_rate)

It does NOT read `shl_pik_switch_period`. Therefore `shl_pik_switch_period=0`
has no proven semantic mapping to `CASH_PAID` for every operating period.

C3B3D1 adapter status: **BLOCKED**. Payment mode cannot be derived safely
from `FinancingParams` without committed source evidence. The adapter raises
`C3B3D1_BLOCKED_PAYMENT_MODE_SEMANTICS` for all projects including those with
`shl_pik_switch_period=0`.

The pure canonical engine (`financial_engine/shl/engine.py`) is complete and
accepts any `ShlInterestPaymentMode` — the block is at the
`FinancingParams → policy` adapter layer only.

---

## 9. Construction → operating opening-balance seam

The construction → operating opening balance transition is labelled
`C3B3D2_CONSTRUCTION_SEAM` and is deferred to the next stage.
The C3B3D1 adapter does NOT use `shl_amount_keur` as an opening balance — it
is referenced only for validation.

---

## 10. Tax boundary

The canonical schedule exposes `gross_accrued_interest_keur` per period. This
feeds `PeriodInterestInput.shl_interest_keur` in the clean tax engine (D2 wiring).

`gross_accrued_interest_keur` answers: "what gross SHL interest accrued this period?"
It does NOT answer: "how much SHL interest is deductible?" Deductibility is
governed by `ShlInterestDeductibilityMode` / ATAD / thin-cap / reintegration
mechanics in TaxPolicy — a separate concern from accrual computation.

---

## 11. Oborovo SHL balance lineage status

**Status: `OBOROVO_SHL_BALANCE_LINEAGE_UNRESOLVED`**

Existing repository values represent different SHL states across construction
and operating phases. The exact construction-closing → operating-opening
liability lineage has not yet been proven from committed source evidence.
C3B3D1 therefore does not select an opening balance for Oborovo.

The C3B3D1 adapter does NOT promote Oborovo to the canonical SHL schedule
runtime. Oborovo continues to run via the legacy waterfall path unchanged.

---

## 12. TUHO lineage/runtime status

**Status: `TUHO_SHL_BALANCE_LINEAGE_UNRESOLVED` + `C3B3D1_BLOCKED_FCF_REPAYMENT`**

TUHO uses `shl_repayment_method = "pik_then_sweep"`, which is in the FCF-waterfall
set. The adapter raises `NotImplementedError` with label `C3B3D1_BLOCKED_FCF_REPAYMENT`.

TUHO continues to run via the legacy waterfall path unchanged.

---

## 13. Deferred work: C3B3D2 immediate scope

| Item | Label |
|---|---|
| Authoritative SHL opening balance seam (where proven) | C3B3D2_CONSTRUCTION_SEAM |
| Run canonical SHL accrual schedule in orchestrator | C3B3D2_ORCHESTRATOR_WIRING |
| Map gross_accrued_interest → PeriodInterestInput.shl_interest_keur | C3B3D2_TAX_WIRING |
| Clean Tax runtime integration | C3B3D2_TAX_INTEGRATION |
| Controlled Tax/CFADS/debt diagnostics | C3B3D2_DIAGNOSTICS |
| Payment mode source evidence (pik_switch_period semantics) | C3B3D2_PAYMENT_MODE_SEMANTICS |
| pik/accrued repayment method source evidence | C3B3D2_LEGACY_METHOD_SEMANTICS |
| Oborovo opening balance proof | C3B3D2_OBOROVO_BALANCE_PROOF |

---

## 14. Deferred work: later SHL/waterfall scope

| Item | Notes |
|---|---|
| FCF repayment | Requires cash-waterfall integration |
| Cash sweep | Requires cash-waterfall integration |
| R99 | TUHO-specific waterfall mechanics |
| R102 / distribution account | Waterfall-specific |
| TUHO sweep mechanics | C3B3D1_BLOCKED_FCF_REPAYMENT |
| PIK-then-cash mixed mode | Period-level mode switching |

---

## 15. Deferred work: later tax scope

| Item | Notes |
|---|---|
| WHT modelling | Separate from SHL accrual mechanics |
