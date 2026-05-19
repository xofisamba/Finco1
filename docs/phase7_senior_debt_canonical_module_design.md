# Phase 7 — Senior Debt Canonical Module Design

> **Status:** DESIGN ONLY — no runtime implementation  
> **Branch:** `phase7-senior-debt-canonical-module-design`  
> **Merged PRs:** #97 (senior debt source map), #98 (SHL cash sweep source map), #99 (SHL canonical design)  
> **Next recommended:** `phase7-depreciation-canonical-module-design`  

---

## 1. Executive Summary

The senior debt source map (PR #97) identified a critical architectural pattern in TUHO Excel:

- **Actual CFADS** = `CF!R69` = `Macro!R49` (linked formula, actual bank cash flow)
- **Sizing CFADS** = hardcoded `Macro!R50` (explicit sizing assumptions frozen in Excel, not formulas)
- **DSCR switch:** PPA regime = 1.20×, Merchant regime = 1.40–1.41×
- **Debt service capacity** = sizing CFADS / target DSCR
- **Post-senior cash** = actual CFADS − senior debt service → passed to `ShlEngine`

This design document proposes a canonical `domain/senior_debt/` module that:

1. **Owns** actual CFADS, sizing CFADS, DSCR target policy, debt service capacity, interest, principal sculpting, opening/closing balance, and post-senior cash handoff
2. **Does not** compute SHL, tax, distribution account, or sponsor IRR — only exposes outputs consumed by those modules
3. **Preserves** the `Macro!R50` pattern as an explicit `sizing_cfads_keur_by_period` input (not derived from actual CFADS)
4. **Supports** dual-DSCR regimes (PPA / merchant) via per-period `target_dscr_by_period`
5. **Maintains** R99/R102 as BLOCKED
6. **Does not** implement multi-lender tranches — that is a future extension

---

## 2. Inputs and Source Ownership

### 2.1 Who provides what

| Input | Source | Owned by |
|-------|--------|----------|
| `actual_cfads_keur_by_period` | `CF!R69` / `Macro!R49` | SeniorDebtEngine (read-only) |
| `sizing_cfads_keur_by_period` | `Macro!R50` — explicit hardcoded values, not formulas | Caller provides (sizing policy) |
| `target_dscr_by_period` | `DS!R19` — blended DSCR (1.20 PPA / 1.40–1.41 merchant) | SeniorDebtEngine (read-only) |
| `opening_balance_keur` | `DS!$D$57` or prior period closing | SeniorDebtEngine (read-only) |
| `interest_rate_by_period` | `DS!$D$54` or rate schedule | SeniorDebtEngine (read-only) |
| `day_count_fraction_by_period` | `DS!$B$57` etc. (semiannual = 0.5 for TUHO) | SeniorDebtEngine (read-only) |
| `repayment_start_period` | Excel construction end / first operating period | Caller provides |
| `maturity_period` | Excel final maturity column | Caller provides |
| `principal_cap_by_period` | Optional per-period cap (future) | Caller provides |
| `allow_full_cash_sweep` | Policy flag — default `True` | Caller sets |

### 2.2 Critical policy: sizing CFADS is explicit input

**Macro!R50 is NOT a formula.** It contains raw numeric values frozen in Excel (e.g., `2627.9015605277727`). Python cannot and should not reverse-engineer these. They are canonical sizing assumptions.

```
Incorrect approach:  derive sizing_cfads from actual_cfads
Correct approach:    sizing_cfads is an explicit input (e.g., from Excel extraction or config)
```

The `SeniorDebtSizingPolicy` dataclass holds `sizing_cfads_keur_by_period` as an explicit tuple of values, separate from `actual_cfads_keur_by_period`.

---

## 3. Actual CFADS vs Sizing CFADS

### 3.1 Why two CFADS inputs?

| | Actual CFADS | Sizing CFADS |
|---|---|---|
| **Source** | `CF!R69` = `Macro!R49` (formula linking to actual bank FCF) | `Macro!R50` (hardcoded numerics) |
| **Purpose** | Economic cash flow for actual DSCR, post-senior cash | Sizing assumption for debt capacity |
| **Used in** | `actual_dscr = actual_cfads / actual_debt_service` | `sizing_capacity = sizing_cfads / target_dscr` |
| **典型值 (TUHO)** | 300,927 kEUR (total) | 204,669 kEUR (total) |
| **Delta** | +96,258 kEUR (+32%) vs sizing CFADS | — |

The delta represents periods where actual CFADS > sizing CFADS (merchant tail periods, upside scenarios). The sizing CFADS is the **binding constraint** for debt sizing.

### 3.2 TUHO sizing CFADS by period (extracted from Macro!R50)

From PR #97 `reports/phase7_tuho_senior_debt_sizing_extraction.csv`:

| Period | Operating idx | Sizing CFADS (kEUR) | Target DSCR | Debt capacity (kEUR) |
|--------|-------------|--------------------:|------------:|---------------------:|
| P1 | 0 | ~2,628 | 1.20 | ~2,190 |
| P2–P25 | 0–12 | ~2,628 (PPA periods) | 1.20 | ~2,190 |
| P26+ | 13+ | declining (merchant) | 1.41 | declining |
| **Total** | | **204,669** | | |

### 3.3 Canonical representation

```python
@dataclass(frozen=True)
class SeniorDebtSizingPolicy:
    """Explicit sizing CFADS per period — from Macro!R50 or equivalent config."""
    project_name: str
    sizing_cfads_keur_by_period: Tuple[float, ...]   # NOT derived from actual CFADS
    source_cell: str = "Macro!R50"                   # provenance marker
    notes: str = ""
```

---

## 4. Target DSCR Policy

### 4.1 TUHO DSCR switch

| Regime | Periods | Target DSCR | Source |
|--------|--------|------------:|--------|
| PPA | P1–P25 (op_idx 0–12) | **1.20** | `DS!B19 = Scenarios!E186` |
| Merchant | P26–P61 (op_idx 13–30) | **1.40–1.41** | `DS!C19 = Scenarios!E187`, blended via DS!R13 |

### 4.2 DSCR blend formula

`DS!R19 = H13 × $C$19 + (1 − H13) × $B$19`

- `H13` = merchant flag (0 for PPA, ~1.062–1.053 for merchant)
- `$B$19` = 1.20 (PPA DSCR)
- `$C$19` = 1.40 (merchant DSCR)

Result: blended DSCR ≈ 1.20× in PPA periods, ≈ 1.4124× in merchant periods.

### 4.3 Canonical representation

```python
@dataclass(frozen=True)
class SeniorDebtDSCRPolicy:
    """Per-period DSCR target supporting PPA/merchant dual regime."""
    target_dscr_by_period: Tuple[float, ...]
    ppa_dscr: float = 1.20          # TUHO PPA
    merchant_dscr: float = 1.41     # TUHO merchant
    switch_period: int = 26         # period index where switch occurs (1-based)
    source_cells: str = "DS!R19"    # provenance
```

---

## 5. Canonical Calculation Order

For each period `t`:

```
1.  actual_cfads[t]    = actual_cfads_keur_by_period[t]      # from CF!R69
2.  sizing_cfads[t]    = sizing_policy.sizing_cfads_keur_by_period[t]  # from Macro!R50
3.  target_dscr[t]     = dscr_policy.target_dscr_by_period[t]  # from DS!R19
4.  opening_balance[t] = period_results[t-1].closing_balance
                         OR initial_opening_balance for t=1    # from DS!D57

5.  # Interest
    interest[t] = opening_balance[t] × rate[t] × day_frac[t]

6.  # Debt service capacity (sizing basis)
    debt_service_capacity[t] = sizing_cfads[t] / target_dscr[t]

7.  # Principal capacity
    scheduled_principal[t] = debt_service_capacity[t] - interest[t]

8.  # Cap by opening balance (can't repay more than outstanding)
    principal_capped[t] = min(scheduled_principal[t], opening_balance[t])

9.  # Cap by maturity / final repayment
    if t == maturity_period:
        principal_capped[t] = opening_balance[t]  # balloon to zero
    elif t > maturity_period:
        principal_capped[t] = 0.0                  # no principal after maturity

10. # Cap by optional per-period constraint
    if principal_cap_by_period[t] is not None:
        principal_capped[t] = min(principal_capped[t], principal_cap_by_period[t])

11. # Total senior debt service
    senior_debt_service[t] = interest[t] + principal_capped[t]

12. # Closing balance
    closing_balance[t] = opening_balance[t] - principal_capped[t]

13. # Actual DSCR (using actual CFADS, not sizing CFADS)
    actual_dscr[t] = actual_cfads[t] / senior_debt_service[t]
    # Note: actual_dscr may differ from target_dscr — this is an output, not a constraint

14. # Sizing DSCR (using sizing CFADS)
    sizing_dscr[t] = sizing_cfads[t] / debt_service_capacity[t]
    # Should equal target_dscr by construction

15. # Post-senior cash (actual CFADS minus actual senior service)
    post_senior_cash[t] = actual_cfads[t] - senior_debt_service[t]

16. # SHL handoff
    post_senior_cash_available_keur[t] = post_senior_cash[t]
    # → passed to ShlEngine, NOT to distribution directly
```

### 5.1 TUHO-specific constants

| Parameter | Value |
|-----------|-------|
| `initial_opening_balance` | 43,359 kEUR |
| `interest_rate` | 8% (semiannual effective) |
| `day_count_fraction` | 0.5 (semiannual) |
| `repayment_start_period` | P1 (construction ends at P1, first operating = P2) |
| `maturity_period` | P30 (col AJ, op_idx 15) — debt fully repaid by year 7.5 |
| `allow_full_cash_sweep` | `True` (no cash sweep restriction beyond DSCR) |

---

## 6. Proposed `domain/senior_debt/` Module Layout

```
domain/senior_debt/
├── __init__.py          # Exports: SeniorDebtEngine, inputs, results, policies
├── inputs.py            # SeniorDebtPeriodInput, SeniorDebtEngineInputs
├── sizing_policy.py     # SeniorDebtSizingPolicy, SeniorDebtDSCRPolicy
├── result.py            # SeniorDebtPeriodResult, SeniorDebtEngineResult, SeniorDebtAuditRow
├── engine.py            # SeniorDebtEngine.compute(inputs) -> result
├── rate_schedule.py    # RateSchedule (simple wrapper, compatible with existing)
├── audit.py             # to_audit_dataframe(), to_csv(), to_model_summary()
└── validation.py        # validate_against_excel() (optional)
```

### 6.1 Why `sizing_policy.py` separately?

The sizing policy (`SeniorDebtSizingPolicy`) and DSCR policy (`SeniorDebtDSCRPolicy`) are distinct concerns:

- `SeniorDebtSizingPolicy`: what CFADS to use for sizing (from `Macro!R50`)
- `SeniorDebtDSCRPolicy`: what DSCR to target per period (from `DS!R19`)

Keeping them separate allows independent revision. The engine consumes both.

### 6.2 Relationship to existing `domain/senior_sculpting.py`

`SeniorDebtEngine` wraps and extends `SeniorDebtSizingSolver` (from `senior_sculpting.py`). The existing single-facility solver is preserved and called internally. The new engine adds:

- Explicit `sizing_cfads_keur_by_period` input (vs. derived in current code)
- Per-period `target_dscr_by_period` (vs. single global DSCR)
- `post_senior_cash_available_keur` output (new)
- `actual_dscr` and `sizing_dscr` separate outputs (new)
- Full audit row per period

---

## 7. Proposed Dataclasses and Field Definitions

### 7.1 `sizing_policy.py`

```python
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class SeniorDebtSizingPolicy:
    """Explicit sizing CFADS per period — from Macro!R50 or equivalent config.

    This is NOT derived from actual_cfads. It is a separate explicit input
    that represents the canonical sizing assumption frozen in the Excel model.
    """
    project_name: str
    sizing_cfads_keur_by_period: Tuple[float, ...]
    source_cell: str = "Macro!R50"    # provenance
    notes: str = ""


@dataclass(frozen=True)
class SeniorDebtDSCRPolicy:
    """Per-period DSCR target — supports PPA/merchant dual regime."""
    target_dscr_by_period: Tuple[float, ...]
    ppa_dscr: float = 1.20
    merchant_dscr: float = 1.41
    switch_period: int = 26          # 1-based period index
    source_cell: str = "DS!R19"
    notes: str = ""
```

### 7.2 `inputs.py`

```python
from dataclasses import dataclass
from typing import Tuple, Optional

@dataclass(frozen=True)
class SeniorDebtPeriodInput:
    """Canonical input for one semiannual period."""
    period_index: int
    actual_cfads_keur: float                     # from CF!R69
    opening_balance_keur: float                  # from DS!D57 or prior closing
    interest_rate: float                         # annual rate (e.g., 0.08)
    day_count_fraction: float                    # e.g., 0.5 for semiannual
    repayment_start_period: int = 1              # first period principal can be repaid
    maturity_period: Optional[int] = None       # period where balance → 0
    principal_cap_keur: Optional[float] = None  # optional per-period cap
    allow_full_cash_sweep: bool = True


@dataclass(frozen=True)
class SeniorDebtEngineInputs:
    """Full model inputs for the Senior Debt engine."""
    project_name: str
    period_count: int
    period_inputs: Tuple[SeniorDebtPeriodInput, ...]
    sizing_policy: SeniorDebtSizingPolicy
    dscr_policy: SeniorDebtDSCRPolicy
    initial_opening_balance_keur: float          # from DS!D57
    # Tranche config (single-facility for now; multi-lender is future)
    tranche_count: int = 1
```

### 7.3 `result.py`

```python
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class SeniorDebtPeriodResult:
    """Canonical output for one semiannual period."""
    period_index: int
    excel_col: str                               # e.g., "H", "AF"
    operating_period_index: int                  # semiannual op_idx (0–30)
    # Balance
    opening_balance_keur: float
    closing_balance_keur: float
    # Interest
    interest_keur: float
    # Principal
    scheduled_principal_keur: float              # before caps
    principal_repaid_keur: float                 # after caps
    # Debt service
    senior_debt_service_keur: float              # interest + principal
    # CFADS comparison
    sizing_cfads_keur: float                    # from sizing policy
    actual_cfads_keur: float                    # from period input
    # DSCR
    target_dscr: float
    sizing_dscr: float                           # sizing_cfads / debt_service_capacity
    actual_dscr: float                           # actual_cfads / senior_debt_service
    # Post-senior cash (SHL handoff)
    post_senior_cash_available_keur: float
    # Flags
    maturity_balloon: bool                       # True if this period had balloon repayment
    dscr_constraint_active: bool                # True if actual_dscr < target_dscr


@dataclass(frozen=True)
class SeniorDebtEngineResult:
    """Full Senior Debt engine result across all periods."""
    project_name: str
    period_count: int
    period_results: Tuple[SeniorDebtPeriodResult, ...]
    # Totals / audit
    total_interest_keur: float
    total_principal_repaid_keur: float
    total_senior_debt_service_keur: float
    total_sizing_cfads_keur: float
    total_actual_cfads_keur: float
    final_closing_balance_keur: float            # should be ~0 at maturity
    post_senior_cash_total_keur: float           # sum of post_senior_cash
    dscr_violation_count: int                    # periods where actual_dscr < target_dscr
    audit_table: Tuple["SeniorDebtAuditRow", ...]


@dataclass(frozen=True)
class SeniorDebtAuditRow:
    """One row of the Senior Debt audit export."""
    period_index: int
    excel_col: str
    operating_period_index: int
    actual_cfads_keur: float
    sizing_cfads_keur: float
    target_dscr: float
    debt_service_capacity_keur: float
    interest_keur: float
    scheduled_principal_keur: float
    principal_repaid_keur: float
    senior_debt_service_keur: float
    opening_balance_keur: float
    closing_balance_keur: float
    actual_dscr: float
    sizing_dscr: float
    post_senior_cash_keur: float
    maturity_balloon: bool
    dscr_constraint_active: bool
    warnings: Tuple[str, ...]
```

---

## 8. Interest / Day-Count Policy

### 8.1 TUHO interest parameters

| Parameter | Value | Source |
|-----------|-------|--------|
| Annual rate | 8% | `DS!D54` |
| Day count fraction | 0.5 (semiannual) | `DS!$B$57` |
| Interest calculation | `opening_balance × rate × day_frac` | compound |
| Rate schedule | Fixed rate, no step-ups in TUHO | — |

### 8.2 Day-count convention

The `day_count_fraction` is a simple scalar (0.5 for semiannual). For TUHO:
- Semiannual periods: `day_frac = 0.5`
- Rate is expressed as annual effective rate
- Interest = `opening × rate × day_frac`

This is simpler than actual day-count conventions (ACT/ACT, 30/360, etc.). The design does not mandate a specific convention — the `day_count_fraction` is an input that can be configured per project.

### 8.3 Future rate schedule extension

`domain/senior_debt/rate_schedule.py` will hold rate step-ups, bullet margins, and margin-ratchets as a separate policy:

```python
@dataclass(frozen=True)
class SeniorDebtRateSchedule:
    """Future: step-up rates, margin ratchets, bullet margins."""
    base_rate: float = 0.08
    step_ups: Tuple[Tuple[int, float], ...] = ()  # (period_index, new_rate)
    margin_ratchet: Optional[MarginRatchet] = None
```

For TUHO, `rate_schedule = SeniorDebtRateSchedule()` (single fixed rate, no step-ups).

---

## 9. Principal Sculpting and Repayment Constraints

### 9.1 Sculpting method

The principal is **sculpted** to achieve the target DSCR, not amortized on a fixed schedule:

```
debt_service_capacity = sizing_cfads / target_dscr
scheduled_principal = debt_service_capacity - interest
```

This means principal repayment **floats** with sizing CFADS and target DSCR. In PPA periods with low sizing CFADS, principal is low; in merchant periods with higher sizing CFADS, principal is higher.

### 9.2 Repayment constraints (applied in order)

1. **Opening balance cap:** `principal_repaid[t] ≤ opening_balance[t]`
2. **Maturity balloon:** if `t == maturity_period`, `principal_repaid[t] = opening_balance[t]` (balloon to zero)
3. **Post-maturity zero:** if `t > maturity_period`, `principal_repaid[t] = 0`
4. **Optional per-period cap:** `principal_repaid[t] ≤ principal_cap_keur[t]` (future hook)
5. **Non-negative:** `principal_repaid[t] ≥ 0`

### 9.3 TUHO maturity behavior

- Debt fully repaid at col AJ (P30, op_idx 15) — year 7.5
- `closing_balance` at P30 ≈ 0
- No residual balance after maturity

---

## 10. DSCR Outputs and Audit Rows

### 10.1 DSCR outputs per period

| Output | Formula | Purpose |
|--------|---------|---------|
| `target_dscr[t]` | from `dscr_policy.target_dscr_by_period[t]` | Policy input |
| `sizing_dscr[t]` | `sizing_cfads[t] / debt_service_capacity[t]` | Should equal target by construction |
| `actual_dscr[t]` | `actual_cfads[t] / senior_debt_service[t]` | Economic DSCR |
| `dscr_constraint_active[t]` | `actual_dscr[t] < target_dscr[t]` | Warning flag |

`actual_dscr` may fall below `target_dscr` in stressed periods — this is a warning flag, not a hard constraint. The debt is already sized and committed; DSCR is a monitoring metric, not a gate.

### 10.2 TUHO DSCR profile

| Metric | Value |
|--------|-------|
| Target DSCR (PPA) | 1.20 |
| Target DSCR (Merchant) | 1.41 |
| Average actual DSCR | ~1.45 (TUHO) |
| Minimum actual DSCR | ~1.20 (at switch) |
| DSCR violation count | 0 (TUHO) |

### 10.3 Audit export

```python
def to_audit_dataframe(result: SeniorDebtEngineResult) -> pd.DataFrame:
    """Convert audit_table to a pandas DataFrame."""
    ...

def to_csv(result: SeniorDebtEngineResult, path: Path) -> None:
    """Write period-by-period audit CSV matching extraction CSV format."""
    ...

def to_model_summary(result: SeniorDebtEngineResult) -> str:
    return (
        f"Senior Debt Engine Result ({result.project_name}):\n"
        f"  Periods: {result.period_count}\n"
        f"  Initial balance: {initial_opening_balance:,.1f} kEUR\n"
        f"  Total interest: {result.total_interest_keur:,.1f} kEUR\n"
        f"  Total principal: {result.total_principal_repaid_keur:,.1f} kEUR\n"
        f"  Total senior DS: {result.total_senior_debt_service_keur:,.1f} kEUR\n"
        f"  Final closing: {result.final_closing_balance_keur:,.1f} kEUR\n"
        f"  DSCR violations: {result.dscr_violation_count}\n"
        f"  Post-senior cash: {result.post_senior_cash_total_keur:,.1f} kEUR"
    )
```

---

## 11. SHL Handoff Interface

### 11.1 The handoff: post_senior_cash_available_keur

After computing senior debt service, the engine computes:

```
post_senior_cash_available_keur[t] = actual_cfads[t] - senior_debt_service[t]
```

This is the **only** output passed to `ShlEngine`. The senior debt module does not know or care what SHL does with it.

### 11.2 Integration boundary

```
SeniorDebtEngine
├── inputs.actual_cfads_keur_by_period   ← from CF!R69
├── inputs.sizing_policy.sizing_cfads   ← from Macro!R50 (explicit)
├── inputs.dscr_policy.target_dscr       ← from DS!R19
│
├── outputs.period_results[].senior_debt_service_keur
├── outputs.period_results[].actual_dscr
├── outputs.period_results[].post_senior_cash_available_keur   → ShlEngine
└── outputs.audit_table
```

**SeniorDebtEngine does NOT call ShlEngine.** The calling context wires the output to the next stage.

### 11.3 Why post_senior_cash is based on actual CFADS, not sizing CFADS

`post_senior_cash = actual_cfads - senior_debt_service`

- `actual_cfads` is the real economic cash flow
- `senior_debt_service` is the actual committed payment (based on sizing)
- The delta is the real cash left after senior debt — this is what SHL receives

If we used sizing CFADS for `post_senior_cash`, we'd be modeling a hypothetical world, not the actual world.

---

## 12. Tax / Distribution / Sponsor Boundaries

### 12.1 What Senior Debt provides to TaxEngine

```
TaxEngine inputs from SeniorDebtEngine:
├── interest_expense_keur[t] = period_results[t].interest_keur
└── principal_repaid_keur[t]  = period_results[t].principal_repaid_keur
```

### 12.2 What Senior Debt provides to DistributionAccount

**None directly.** The `post_senior_cash` goes to `ShlEngine`, not `DistributionAccount`. The distribution account receives cash from `ShlEngine` (after SHL is served).

Note: R99/R102 is BLOCKED — distribution account logic is not yet promoted.

### 12.3 What Senior Debt provides to SponsorEngine

```
SponsorEngine inputs from SeniorDebtEngine:
├── closing_balance_keur[t]           # senior debt balance over time
├── senior_debt_service_keur[t]       # total debt service (for leverage ratio)
└── post_senior_cash_keur[t]          # cash available after senior (for coverage)
```

### 12.4 Clear boundaries

```
SeniorDebtEngine → post_senior_cash → ShlEngine → cash_after_shl → DistributionAccount
                              ↓
                        SponsorEngine
```

No module computes another module's outputs. Each module only exposes its own outputs.

---

## 13. Migration Plan from Current Senior Debt Modules

### 13.1 Current baseline

The current senior debt logic is split across:
- `domain/senior_sculpting.py` — sizing solver (single facility)
- `domain/senior_rate_schedule.py` — rate schedule
- Fixtures in `tests/` — TUHO and Oborovo fixtures

These are working and fixture-bound. The canonical module wraps them without breaking existing behavior.

### 13.2 Migration steps

```
Current:                          Canonical:
─────────────────────────────────────────────────────────────
senior_sculpting.py               → domain/senior_debt/engine.py
  SeniorDebtSizingSolver            SeniorDebtEngine.compute()
  sizing_derived_from_cfads      → sizing_policy.sizing_cfads (explicit)
  global DSCR                    → dscr_policy.target_dscr_by_period (per-period)
  no post_senior_cash output     → post_senior_cash_available_keur (new)
  ad-hoc audit                   → audit.py with to_csv(), to_dataframe()

senior_rate_schedule.py           → domain/senior_debt/rate_schedule.py
  (preserved as-is)               SeniorDebtRateSchedule (compatible wrapper)
```

### 13.3 Validation

```python
def validate_against_excel(sd_result: SeniorDebtEngineResult,
                           excel_csv_path: str) -> None:
    """Regress SeniorDebtEngineResult against extracted Excel CSV."""
    excel_rows = load_csv(excel_csv_path)
    for sd_row, excel_row in zip(sd_result.audit_table, excel_rows):
        assert_close(sd_row.interest_keur, excel_row["ds_r49_interest_keur"])
        assert_close(sd_row.principal_repaid_keur, excel_row["ds_r50_principal_keur"])
        assert_close(sd_row.opening_balance_keur, excel_row["ds_r47_opening_balance_keur"])
        assert_close(sd_row.actual_dscr, excel_row["ds_r128_actual_dscr"])
```

---

## 14. Future Multi-Lender / Tranche Extension

### 14.1 Current scope: single facility

TUHO senior debt is **single-facility** — one senior debt tranche with one interest rate, one schedule, one maturity. The canonical module is designed for this.

### 14.2 Future: multi-lender extension

A future extension would add:

```python
@dataclass(frozen=True)
class SeniorDebtTranche:
    """Future: multi-lender tranche."""
    tranche_name: str               # e.g., "Senior A", "Senior B"
    opening_balance_keur: float
    interest_rate: float
    day_count_fraction: float
    maturity_period: int
    repayment_schedule: Tuple[float, ...]  # or use sculpting

# SeniorDebtEngineInputs would change:
tranches: Tuple[SeniorDebtTranche, ...]   # instead of single-facility
```

### 14.3 Why not this implementation?

- Multi-lender adds significant complexity (pro-rata repayment, different rates, different maturities)
- TUHO is single-facility — no current requirement
- The canonical single-facility module is a pre-requisite for the multi-lender extension
- PHASE 7 should deliver the single-facility canonical module, not a speculative multi-lender design

---

## 15. Runtime Integration Plan (Default-OFF Flag)

### 15.1 Future `senior_debt_enabled` flag

When `senior_debt_enabled=True`, the canonical `SeniorDebtEngine` is used. When `False`, the legacy `senior_sculpting.py` behavior is preserved.

```python
@dataclass
class WaterfallConfig:
    senior_debt_enabled: bool = False   # default OFF — migration safety
    senior_sizing_policy: SeniorDebtSizingPolicy  # from Macro!R50 extraction
    senior_dscr_policy: SeniorDebtDSCRPolicy       # from DS!R19 extraction
    senior_allow_full_cash_sweep: bool = True
```

### 15.2 Migration path

1. **Phase 7 (design):** This document. No runtime changes.
2. **Phase 8 (canonical module):** Implement `domain/senior_debt/` with `SeniorDebtEngine`, validate against TUHO fixture.
3. **Phase 9 (integration):** Wire `SeniorDebtEngine` into `waterfall_core` behind `senior_debt_enabled=True` flag.
4. **Phase 10 (promotion):** Set `senior_debt_enabled=True` as default, remove legacy code after regression.

---

## 16. Forbidden Scope / Non-Goals

- **No runtime implementation** of `SeniorDebtEngine` in this branch
- **No creation** of active `domain/senior_debt/*.py` runtime files (only illustrative pseudocode in this doc)
- **No changes** to `domain/senior_sculpting.py`
- **No changes** to `domain/senior_rate_schedule.py`
- **No changes** to SHL modules
- **No changes** to tax modules
- **No changes** to distribution account runtime
- **No R99/R102 promotion** — R99/R102 remains BLOCKED
- **No multi-lender implementation** — documented as future extension only
- **No flags** added to project factory
- **No changes** to `app/*` or `app/waterfall_core.py`
- **No scalar plugs**
- **No silent runtime behavior changes**

---

## 17. Acceptance Criteria

- [x] Branch is docs/design/test-only
- [x] No production/runtime files changed
- [x] Design clearly separates actual CFADS from sizing CFADS
- [x] Design includes canonical senior debt inputs, outputs, period result, audit row, and engine result
- [x] Design preserves TUHO `Macro!R50` as explicit `sizing_cfads_keur_by_period` input concept
- [x] Design includes SHL handoff through `post_senior_cash_available_keur`
- [x] Dual-DSCR regime (PPA/merchant) documented via `SeniorDebtDSCRPolicy.target_dscr_by_period`
- [x] Multi-lender/tranche documented as future extension only
- [x] Interest/day-count policy, principal sculpting, and maturity constraints documented
- [x] Migration plan from `senior_sculpting.py` described
- [x] R99/R102 remains BLOCKED
- [x] All tests pass

---

## 18. Recommended Next Branch

**`phase7-depreciation-canonical-module-design`**

Depreciation is a significant model component (EBITDA → EBT bridge) that currently may have fixture-bound or ambiguous source ownership. A canonical `DepreciationEngine` design following the same pattern as `ShlEngine` and `SeniorDebtEngine` would complete the core engine suite for Phase 7.

---

*Document version: 1.0 — 2026-05-19*  
*Authors: Phase 7 design branch — cofix + OpenClaw agent*