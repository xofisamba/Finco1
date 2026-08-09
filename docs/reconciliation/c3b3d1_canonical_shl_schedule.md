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

Tax-authority line: `gross_accrued_interest_keur` is the deductible interest
expense that flows into `PeriodInterestInput.shl_interest_keur` (C3B3D2 wiring scope).

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
deferred to C3B3D2 via `shl_pik_switch_period > 0` detection in the adapter.

---

## 5. Supported repayment modes

| Mode | Mechanism |
|---|---|
| `BULLET` | Full outstanding balance repaid at `maturity_period_index`. All other periods: `scheduled_principal = 0`. |
| `EXPLICIT_SCHEDULE` | Per-period `scheduled_principal_keur` from `ShlPeriodInput`. |

---

## 6. Unsupported modes — fail-closed

The following repayment modes raise `NotImplementedError` in C3B3D1:

- `FCF_WATERFALL` — requires D2 cash-waterfall integration
- `CASH_SWEEP` — requires D2 cash-waterfall integration
- `PIK_THEN_SWEEP` — requires D2 period-level mode switching
- `PARTIAL_PAY_SWEEP` — requires D2 cash integration

Error label: `C3B3D1_DEFERRED: FCF-waterfall repayment requires D2 cash integration`

These are detected in `build_shl_schedule_policy_from_project_inputs` via
`_FCF_WATERFALL_METHODS` and raise `NotImplementedError` with label
`C3B3D1_BLOCKED_FCF_REPAYMENT`. They are never silently treated as BULLET.

---

## 7. Construction → operating opening-balance seam (C3B3D2)

The canonical opening balance at operating period 1 is:

```
SHL_commitment + construction_PIK = operating_opening_balance
```

For Oborovo: `13,547.2 kEUR + 1,169.0 kEUR IDC = ~14,716.2 kEUR` (approximate;
exact construction PIK computation is NOT source-proven from committed evidence).

This seam is labelled `C3B3D2_CONSTRUCTION_SEAM` and is deferred to C3B3D2.
The C3B3D1 adapter does NOT use `shl_amount_keur` as an opening balance — it
is referenced only for validation.

---

## 8. Tax boundary

The canonical schedule exposes `gross_accrued_interest_keur` per period. This
feeds `PeriodInterestInput.shl_interest_keur` in the clean tax engine (D2 wiring).

For projects where `atad_enabled=False` and `shl_interest_deductibility=FULLY_NON_DEDUCTIBLE`
(Oborovo): the gross SHL interest cancels entirely with fiscal reintegration —
the net effect on taxable income is zero. The canonical schedule still computes
the correct gross for audit purposes.

---

## 9. Accounting boundary

The canonical SHL schedule models **financial accounting** (balance sheet + P&L):
- PIK is capitalised into the SHL liability balance
- Cash interest is an income-statement expense

No asset/liability netting, no deferred tax, no withholding tax modelling in C3B3D1.
WHT modelling is deferred to C3B3D2 via `ShlTaxInterface` in `finco_core.shl.inputs`.

---

## 10. Oborovo SHL balance lineage status

**Status: `OBOROVO_SHL_BALANCE_LINEAGE_UNRESOLVED`**

The construction → operating opening balance transition for Oborovo cannot be
proven from committed source evidence alone:

- SHL commitment: `13,547.2 kEUR` (project_factories.py, sourced from oborovo_baseline.json)
- IDC: `1,169.0 kEUR` (project_factories.py comment: "IDC from construction")
- Construction PIK: not independently computed from committed source evidence
- Excel BS row for operating opening balance: not extracted in C3B1/C3B2 fixtures

The C3B3D1 adapter does NOT promote Oborovo to the canonical SHL schedule runtime.
This is acceptable — Oborovo continues to run via the legacy waterfall path unchanged.

---

## 11. TUHO lineage/runtime status

**Status: `TUHO_SHL_BALANCE_LINEAGE_UNRESOLVED` + `C3B3D1_BLOCKED_FCF_REPAYMENT`**

TUHO uses `shl_repayment_method = "pik_then_sweep"`, which is in the FCF-waterfall
set. The adapter raises `NotImplementedError` with label `C3B3D1_BLOCKED_FCF_REPAYMENT`.

TUHO continues to run via the legacy waterfall path unchanged.

---

## 12. Deferred work for C3B3D2

| Item | Label |
|---|---|
| Wire canonical SHL schedule into orchestrator.py | C3B3D2_ORCHESTRATOR_WIRING |
| Construction → operating balance seam | C3B3D2_CONSTRUCTION_SEAM |
| Feed gross_accrued_interest into PeriodInterestInput | C3B3D2_TAX_WIRING |
| PIK-then-cash mixed mode (shl_pik_switch_period > 0) | C3B3D2_MIXED_MODE |
| WHT modelling | C3B3D2_WHT |
| Oborovo opening balance proof | C3B3D2_OBOROVO_BALANCE_PROOF |
| TUHO pik_then_sweep classification | C3B3D2_TUHO_SWEEP |
| FCF waterfall cash-waterfall integration | C3B3D2_FCF_WATERFALL |
