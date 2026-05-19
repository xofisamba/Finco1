# Phase 7 — SHL Canonical Module Design

> **Status:** DESIGN ONLY — no runtime implementation  
> **Branch:** `phase7-shl-canonical-module-design`  
> **Merged PRs:** #97 (senior debt source map), #98 (SHL cash sweep source map)  
> **Oborovo extraction:** ⚠️ OPEN ITEM — file not available in workspace  

---

## 1. Executive Summary

Two Phase 7 P1 branches have mapped the Excel source for SHL:

- **Senior debt source map (PR #97):** actual CFADS from `CF!R69` = `Macro!R49`; sizing CFADS hardcoded in `Macro!R50`; DSCR switch documented
- **SHL cash sweep source map (PR #98):** TUHO applies **100% cash sweep** to SHL after senior debt service; no minimum cash reserve mechanism found; PIK trigger `MAX(gross - cash × outstanding_pct, 0)` confirmed

This design document proposes a canonical `domain/shl/` module architecture that:

1. **Owns** SHL opening balance, drawdowns, gross accrued interest, cash interest paid, PIK, principal repayment, closing balance, and residual cash handoff
2. **Does not** compute tax, distribution account, or sponsor IRR — only exposes outputs that consumers can use
3. **Preserves** TUHO's 100% cash sweep and no-minimum-reserve as default behavior
4. **Supports** an optional minimum cash reserve hook that is **default-off** for future use
5. **Maintains** R99/R102 as blocked until gates are formally promoted

---

## 2. Inputs and Source Ownership

### 2.1 Who provides what

| Input | Source | Owned by |
|-------|--------|----------|
| Opening balance | `DS!R120` (beginning balance row) | SHLEngine (read-only) |
| Drawdowns | `Inputs!D238` / `DS!D121` | SHLEngine (read-only) |
| Interest rate | Per-tranche rates from `DS!B131`, `DS!B142`, `DS!B153` | SHLEngine (read-only) |
| Day count fraction | `DS!$B131` etc. (semiannual = 0.5 for TUHO) | SHLEngine (read-only) |
| `post_senior_cash_available_keur_by_period` | `CF!R69 + CF!R70` (CFADS - Senior DS) | Caller provides |
| `cash_sweep_after_senior` | Policy flag — default `True` | Caller sets |
| `maintain_minimum_cash_reserve` | Policy flag — default `False` | Caller sets |
| `minimum_cash_reserve_keur` | Future hook — default 0.0 | Caller sets |
| `pik_allowed` | Per-tranche config — default `True` for TUHO | Caller sets |

### 2.2 Inputs dataclass

```python
@dataclass(frozen=True)
class ShlPeriodInput:
    """Canonical input for one semiannual period."""
    period_index: int                              # 1-based semiannual period
    opening_balance_keur: float                    # DS!R120 at period start
    drawdown_keur: float                           # new funding drawn this period
    interest_rate: float                           # annual rate (e.g., 0.08)
    day_count_fraction: float                      # e.g., 0.5 for semiannual
    post_senior_cash_available_keur: float         # CFADS - Senior DS
    maintain_minimum_cash_reserve: bool = False    # default OFF
    minimum_cash_reserve_keur: float = 0.0         # future hook
    pik_allowed: bool = True                       # TUHO default True


@dataclass(frozen=True)
class ShlEngineInputs:
    """Full model inputs for the SHL engine across all periods."""
    project_name: str                              # e.g., "TUHO", "Oborovo"
    period_count: int                              # e.g., 63 (TUHO)
    period_inputs: tuple[ShlPeriodInput, ...]      # one per period
    total_shl_funding_keur: float                  # DS!D121 reference
    # Tranche-level config (TUHO has 3: Sponsor, Inv1, Inv2)
    tranche_rates: tuple[float, ...]               # annual rates per tranche
    tranche_day_fracs: tuple[float, ...]           # day count fractions
    tranche_opening_balances_keur: tuple[float, ...]  # initial balances
```

### 2.3 Source cell mapping

```
SHL opening balance  ← DS!R120  (combined: DS!H133 + DS!H144 + DS!H155 per period)
SHL drawdown         ← DS!R121  (constant = DS!D121 total funding per period)
Gross accrued int    ← DS!R135  (= opening × rate × day_frac)
Cash interest paid   ← DS!R122  (= net cash int across all 3 tranches)
PIK capitalized     ← DS!R138  (= MAX(gross - cash_available × outstanding_pct, 0))
Principal repaid    ← DS!R137  (= MIN(remaining_cash, outstanding_balance))
SHL ending balance   ← DS!R139  (= opening + PIK - principal)
DS incl WTH          ← DS!R127  (SHL debt service including WHT)
Net SHL DS           ← CF!R104  (= -DS!R128, used in distribution gate)
```

---

## 3. Outputs and Audit Rows

### 3.1 Outputs dataclass

```python
@dataclass(frozen=True)
class ShlPeriodResult:
    """Canonical output for one semiannual period."""
    period_index: int
    opening_balance_keur: float
    drawdown_keur: float
    gross_accrued_interest_keur: float
    cash_interest_paid_keur: float
    pik_capitalized_keur: float
    principal_repaid_keur: float
    closing_balance_keur: float
    cash_consumed_by_shl_keur: float        # cash_interest + principal
    cash_after_shl_keur: float              # post_senior - cash_consumed
    cash_for_distribution_keur: float       # residual after SHL fully served
    # Tranche-level breakdown (TUHO: Sponsor / Inv1 / Inv2)
    tranche_opening_balances_keur: tuple[float, ...]
    tranche_gross_accrued_keur: tuple[float, ...]
    tranche_cash_int_paid_keur: tuple[float, ...]
    tranche_pik_keur: tuple[float, ...]
    tranche_principal_keur: tuple[float, ...]
    tranche_closing_balances_keur: tuple[float, ...]
    # Audit flags
    pik_triggered: bool                    # True if PIK > 0
    cash_sweep_100_pct: bool               # True if post-senior cash == cash_consumed
    reserve_applied: bool                  # True if minimum reserve was active


@dataclass(frozen=True)
class ShlEngineResult:
    """Full SHL engine result across all periods."""
    project_name: str
    period_count: int
    period_results: tuple[ShlPeriodResult, ...]
    # Totals / audit
    total_gross_accrued_interest_keur: float
    total_cash_interest_paid_keur: float
    total_pik_capitalized_keur: float
    total_principal_repaid_keur: float
    total_shl_debt_service_incl_wht_keur: float
    total_cash_consumed_keur: float
    final_closing_balance_keur: float       # should be ~0 at end of model
    pik_period_count: int                  # number of periods with PIK > 0
    cash_sweep_100_pct_period_count: int   # number of periods with 100% sweep
    audit_table: tuple[ShlAuditRow, ...]
```

### 3.2 Audit row dataclass

```python
@dataclass(frozen=True)
class ShlAuditRow:
    """One row of the SHL audit export."""
    period_index: int
    excel_col: str                        # e.g., "H", "AF"
    operating_period_index: int            # semiannual op_idx (0–30)
    # Balance
    shl_opening_keur: float
    drawdown_keur: float
    shl_closing_keur: float
    # Interest breakdown
    gross_accrued_keur: float
    cash_int_paid_keur: float
    pik_capitalized_keur: float
    # Cash flows
    post_senior_cash_keur: float
    cash_consumed_keur: float
    cash_after_shl_keur: float
    cash_for_distribution_keur: float
    # Policy flags
    pik_triggered: bool
    cash_sweep_100_pct: bool
    reserve_applied: bool
    # Classification
    classification: str                   # "SHL_Active" / "SHL_Inactive" / "N/A"
    # Warnings (non-fatal)
    warnings: tuple[str, ...]             # e.g., "PIK > cash_int", "closing > opening"
```

---

## 4. Canonical Waterfall Order

For each period `t`:

```
1.  opening_balance[t] = period_results[t-1].closing_balance
                        OR initial_tranche_openings for t=1

2.  IF drawdown[t] > 0:
        opening_balance[t] += drawdown[t]

3.  gross_accrued[t] = opening_balance[t] × rate × day_frac

4.  post_senior_cash[t] = caller-provided
    # = CFADS[t] - SeniorDebtService[t]

5.  IF maintain_minimum_cash_reserve AND minimum_cash_reserve_keur > 0:
        reserve_cash = minimum_cash_reserve_keur
        available_for_shl = post_senior_cash[t] - reserve_cash
    ELSE:
        available_for_shl = post_senior_cash[t]   # TUHO default

6.  cash_interest_paid[t] = MIN(gross_accrued[t], available_for_shl)

7.  pik_capitalized[t] = MAX(gross_accrued[t] - cash_interest_paid[t], 0)
                         IF pik_allowed ELSE 0

8.  cash_remaining[t] = available_for_shl - cash_interest_paid[t]

9.  principal_repaid[t] = MIN(
        cash_remaining[t],
        opening_balance[t] + pik_capitalized[t]   # balance after PIK accrues
    )

10. closing_balance[t] = opening_balance[t] + pik_capitalized[t] - principal_repaid[t]

11. cash_consumed_by_shl[t] = cash_interest_paid[t] + principal_repaid[t]

12. cash_after_shl[t] = post_senior_cash[t] - cash_consumed_by_shl[t]

13. cash_for_distribution[t] = MAX(cash_after_shl[t], 0.0)
    # Zero if SHL not yet fully served or gate not passed
    # CF!R99 gate controls this in the Excel — do NOT conflate with SHL closing balance
```

### 4.1 TUHO default behavior

| Parameter | TUHO Value | Notes |
|-----------|------------|-------|
| `cash_sweep_after_senior` | `True` | 100% of available cash goes to SHL |
| `maintain_minimum_cash_reserve` | `False` | No reserve floor |
| `pik_allowed` | `True` | PIK capitalized when cash insufficient |
| `day_count_fraction` | `0.5` | Semiannual periods |
| Tranche rates | 8% for all 3 | Sponsor, Inv1, Inv2 |
| Tranche count | 3 | Combined in DS!R120; split in tranche detail rows |

### 4.2 PIK trigger detail

Excel formula: `DS!R138 = MAX(H135 - H116 * H132, 0)`

- `H135` = gross accrued interest
- `H116` = cash available for SHL interest (CF!R116)
- `H132` = outstanding balance fraction (for P2: opening / initial)

When `H116 * H132 < H135` → shortfall is PIKed.

Canonical form: `PIK[t] = MAX(0, gross_accrued[t] - cash_available_for_int[t])`

Where `cash_available_for_int[t] = MIN(post_senior_cash[t], available_for_shl_int)`.

---

## 5. Proposed `domain/shl/` Module Layout

```
domain/shl/
├── __init__.py          # Exports: ShlEngine, ShlEngineInputs, ShlEngineResult, ShlAuditRow
├── inputs.py            # ShlPeriodInput, ShlEngineInputs, ShlTaxInterface (optional)
├── result.py            # ShlPeriodResult, ShlEngineResult, ShlAuditRow
├── engine.py            # ShlEngine.compute(ShlEngineInputs) -> ShlEngineResult
├── audit.py             # to_audit_dataframe(), to_csv(), to_model_summary()
└── validation.py        # validate_against_excel(), validate_balance_reconciliation() (optional)
```

### 5.1 `__init__.py`

```python
"""domain/shl/ — SHL / Junior Debt Engine.

Canonical SHL engine for the Finco1 financial model.
Handles interest accrual, PIK capitalization, principal repayment,
and residual cash handoff to the distribution account.

Default TUHO behavior: cash_sweep_after_senior=True, maintain_minimum_cash_reserve=False.
"""

from domain.shl.inputs import ShlPeriodInput, ShlEngineInputs, ShlTaxInterface
from domain.shl.result import (
    ShlPeriodResult,
    ShlEngineResult,
    ShlAuditRow,
)
from domain.shl.engine import ShlEngine
from domain.shl.audit import to_audit_dataframe, to_csv, to_model_summary

__all__ = [
    "ShlEngine",
    "ShlEngineInputs",
    "ShlPeriodInput",
    "ShlPeriodResult",
    "ShlEngineResult",
    "ShlAuditRow",
    "ShlTaxInterface",
    "to_audit_dataframe",
    "to_csv",
    "to_model_summary",
]
```

### 5.2 `inputs.py`

```python
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class ShlPeriodInput:
    period_index: int
    opening_balance_keur: float
    drawdown_keur: float
    interest_rate: float
    day_count_fraction: float
    post_senior_cash_available_keur: float
    maintain_minimum_cash_reserve: bool = False
    minimum_cash_reserve_keur: float = 0.0
    pik_allowed: bool = True


@dataclass(frozen=True)
class ShlEngineInputs:
    project_name: str
    period_count: int
    period_inputs: Tuple[ShlPeriodInput, ...]
    total_shl_funding_keur: float
    tranche_rates: Tuple[float, ...]
    tranche_day_fracs: Tuple[float, ...]
    tranche_opening_balances_keur: Tuple[float, ...]


# Optional: tax deductibility interface
@dataclass(frozen=True)
class ShlTaxInterface:
    """Config for how SHL interest feeds the tax engine."""
    interest_deductibility: bool = True    # TUHO: True
    pik_deductibility: bool = False      # TUHO: PIK not deductible until paid
    withholding_tax_rate: float = 0.0     # TUHO: 0% WHT on SHL
    effective_deductible_rate: float = 1.0  # interest_deductibility × (1 - WHT)
```

### 5.3 `result.py`

```python
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class ShlPeriodResult:
    period_index: int
    opening_balance_keur: float
    drawdown_keur: float
    gross_accrued_interest_keur: float
    cash_interest_paid_keur: float
    pik_capitalized_keur: float
    principal_repaid_keur: float
    closing_balance_keur: float
    cash_consumed_by_shl_keur: float
    cash_after_shl_keur: float
    cash_for_distribution_keur: float
    tranche_opening_balances_keur: Tuple[float, ...]
    tranche_gross_accrued_keur: Tuple[float, ...]
    tranche_cash_int_paid_keur: Tuple[float, ...]
    tranche_pik_keur: Tuple[float, ...]
    tranche_principal_keur: Tuple[float, ...]
    tranche_closing_balances_keur: Tuple[float, ...]
    pik_triggered: bool
    cash_sweep_100_pct: bool
    reserve_applied: bool


@dataclass(frozen=True)
class ShlEngineResult:
    project_name: str
    period_count: int
    period_results: Tuple[ShlPeriodResult, ...]
    total_gross_accrued_interest_keur: float
    total_cash_interest_paid_keur: float
    total_pik_capitalized_keur: float
    total_principal_repaid_keur: float
    total_shl_debt_service_incl_wht_keur: float
    total_cash_consumed_keur: float
    final_closing_balance_keur: float
    pik_period_count: int
    cash_sweep_100_pct_period_count: int
    audit_table: Tuple["ShlAuditRow", ...]


@dataclass(frozen=True)
class ShlAuditRow:
    period_index: int
    excel_col: str
    operating_period_index: int
    shl_opening_keur: float
    drawdown_keur: float
    shl_closing_keur: float
    gross_accrued_keur: float
    cash_int_paid_keur: float
    pik_capitalized_keur: float
    post_senior_cash_keur: float
    cash_consumed_keur: float
    cash_after_shl_keur: float
    cash_for_distribution_keur: float
    pik_triggered: bool
    cash_sweep_100_pct: bool
    reserve_applied: bool
    classification: str
    warnings: Tuple[str, ...]
```

### 5.4 `engine.py`

```python
class ShlEngine:
    """Canonical SHL engine.

    Computes period-by-period SHL interest, PIK, principal, and closing balance
    given post-senior cash availability. Does NOT compute tax, distribution, or sponsor IRR.

    Usage:
        inputs = ShlEngineInputs(project_name="TUHO", period_count=63, ...)
        result = ShlEngine.compute(inputs)
    """

    @staticmethod
    def compute(inputs: ShlEngineInputs) -> ShlEngineResult:
        period_results = []
        audit_rows = []
        totals = dict(gross=0.0, cash_int=0.0, pik=0.0, principal=0.0,
                      cash_consumed=0.0, shl_ds=0.0)

        for t, p in enumerate(inputs.period_inputs):
            # ---- Balance step ----
            if t == 0:
                opening = sum(inputs.tranche_opening_balances_keur)
            else:
                opening = period_results[t-1].closing_balance_keur

            balance = opening + p.drawdown_keur

            # ---- Interest step ----
            gross = balance * p.interest_rate * p.day_count_fraction

            # ---- Cash availability ----
            if p.maintain_minimum_cash_reserve:
                available = max(0.0, p.post_senior_cash_available_keur - p.minimum_cash_reserve_keur)
            else:
                available = p.post_senior_cash_available_keur

            # ---- Interest payment ----
            cash_int = min(gross, available)
            available -= cash_int

            # ---- PIK ----
            if p.pik_allowed:
                pik = max(0.0, gross - cash_int)
            else:
                pik = 0.0

            # ---- Principal ----
            principal = min(available, balance + pik)
            available -= principal

            # ---- Closing ----
            closing = balance + pik - principal

            # ---- Cash accounting ----
            cash_consumed = cash_int + principal
            cash_after_shl = p.post_senior_cash_available_keur - cash_consumed
            cash_for_dist = max(cash_after_shl, 0.0)

            # ---- Flags ----
            pik_triggered = pik > 0.01
            sweep_100 = abs(p.post_senior_cash_available_keur - cash_consumed) < 0.01 \
                if p.post_senior_cash_available_keur > 0.01 else False
            reserve_applied = p.maintain_minimum_cash_reserve and p.minimum_cash_reserve_keur > 0.0

            # ---- Tranche breakdown (placeholder for multi-tranche) ----
            tranche_openings = (balance,) * len(inputs.tranche_rates)
            tranche_gross = (gross,) * len(inputs.tranche_rates)
            tranche_cash_int = (cash_int,) * len(inputs.tranche_rates)
            tranche_pik = (pik,) * len(inputs.tranche_rates)
            tranche_principal = (principal,) * len(inputs.tranche_rates)
            tranche_closing = (closing,) * len(inputs.tranche_rates)

            period_results.append(ShlPeriodResult(
                period_index=p.period_index,
                opening_balance_keur=opening,
                drawdown_keur=p.drawdown_keur,
                gross_accrued_interest_keur=gross,
                cash_interest_paid_keur=cash_int,
                pik_capitalized_keur=pik,
                principal_repaid_keur=principal,
                closing_balance_keur=closing,
                cash_consumed_by_shl_keur=cash_consumed,
                cash_after_shl_keur=cash_after_shl,
                cash_for_distribution_keur=cash_for_dist,
                tranche_opening_balances_keur=tranche_openings,
                tranche_gross_accrued_keur=tranche_gross,
                tranche_cash_int_paid_keur=tranche_cash_int,
                tranche_pik_keur=tranche_pik,
                tranche_principal_keur=tranche_principal,
                tranche_closing_balances_keur=tranche_closing,
                pik_triggered=pik_triggered,
                cash_sweep_100_pct=sweep_100,
                reserve_applied=reserve_applied,
            ))

        # ... totals and audit rows ...
        return ShlEngineResult(...)
```

### 5.5 `audit.py`

```python
import csv
from pathlib import Path

def to_audit_dataframe(result: ShlEngineResult) -> ...:
    """Convert audit_table to a pandas DataFrame."""
    ...


def to_csv(result: ShlEngineResult, path: Path) -> None:
    """Write audit table to CSV."""
    ...


def to_model_summary(result: ShlEngineResult) -> str:
    """Return human-readable summary of SHL engine result."""
    return (
        f"SHL Engine Result ({result.project_name}):\n"
        f"  Periods: {result.period_count}\n"
        f"  Gross Accrued Interest: {result.total_gross_accrued_interest_keur:,.1f} kEUR\n"
        f"  Cash Interest Paid: {result.total_cash_interest_paid_keur:,.1f} kEUR\n"
        f"  PIK Capitalized: {result.total_pik_capitalized_keur:,.1f} kEUR\n"
        f"  Principal Repaid: {result.total_principal_repaid_keur:,.1f} kEUR\n"
        f"  Total SHL DS (incl WHT): {result.total_shl_debt_service_incl_wht_keur:,.1f} kEUR\n"
        f"  PIK periods: {result.pik_period_count}\n"
        f"  100% cash sweep periods: {result.cash_sweep_100_pct_period_count}\n"
        f"  Final closing balance: {result.final_closing_balance_keur:,.1f} kEUR"
    )
```

---

## 6. Tax Interface

### 6.1 What SHL provides to TaxEngine

The SHL engine must expose per-period gross accrued interest, cash interest paid, and PIK capitalized — these are the inputs to `TaxEngine`.

```
TaxEngine inputs from SHL:
├── interest_expense_keur[t]   = gross_accrued_interest_keur[t]
│                               (deductible when paid or on accrual depending on policy)
├── cash_interest_keur[t]      = cash_interest_paid_keur[t]
│                               (actual cash outflow for tax purposes)
└── pik_keur[t]                = pik_capitalized_keur[t]
                                (not deductible until paid in cash)
```

### 6.2 ShlTaxInterface fields

| Field | TUHO default | Purpose |
|-------|-------------|---------|
| `interest_deductibility` | `True` | Interest is tax-deductible when accrued |
| `pik_deductibility` | `False` | PIK not deductible until paid in cash |
| `withholding_tax_rate` | `0.0` | No WHT on SHL interest in TUHO |
| `effective_deductible_rate` | `1.0` | `= interest_deductibility × (1 - WHT)` |

### 6.3 TaxEngine consumption pattern

```python
# TaxEngine calls ShlEngineResult to get interest expense
shl_result: ShlEngineResult = ShlEngine.compute(shl_inputs)

for period in shl_result.period_results:
    tax_deductible_int = period.gross_accrued_interest_keur * shl_tax.effective_deductible_rate
    # For TUHO: tax_deductible_int = gross_accrued × 1.0
```

---

## 7. Distribution / R99/R102 Interface

### 7.1 R99 gate status: BLOCKED

R99 (`CF!R99 = IF(AND(OR(R128<$B$99,...),...), 0, R98)`) is the DSCR-gated distribution trigger. It remains BLOCKED per the Phase 7 blueprint (6/16 gates done).

### 7.2 What SHL provides to DistributionAccount

SHL engine exposes `cash_for_distribution_keur[t]` — residual cash after SHL is fully served. This is the input to `DistributionAccount`, which applies its own gate logic (R99).

```
DistributionAccount inputs from SHL:
└── cash_after_shl_keur[t] = period.cash_after_shl_keur
                            (= post_senior_cash - cash_consumed_by_shl)
    When SHL is active and cash is tight:
    → cash_after_shl may be small or zero
    → R99 gate may block distribution entirely

    When SHL is fully repaid:
    → cash_consumed_by_shl = 0
    → cash_after_shl = post_senior_cash
    → distribution can proceed
```

### 7.3 Integration boundary

```
SeniorDebtEngine → post_senior_cash → ShlEngine → cash_after_shl
                                                       ↓
                                              DistributionAccount
                                                       ↓
                                                   SponsorEngine
```

**SHL engine does NOT call DistributionAccount.** It only exposes outputs. The calling context (e.g., `waterfall_core`) wires the outputs to the next stage.

---

## 8. Sponsor Interface

### 8.1 What SHL provides to SponsorEngine

SHL engine exposes per-period sponsor-relevant cashflows for IRR computation:

| Output | Use by SponsorEngine |
|--------|---------------------|
| `cash_for_distribution_keur[t]` | Dividend/distribution现金流 |
| `principal_repaid_keur[t]` | Refund of SHL investment |
| `pik_capitalized_keur[t]` | Accrued but unpaid interest (not yet cash) |
| `closing_balance_keur[t]` | SHL outstanding balance over time |

### 8.2 Sponsor cashflow classification

```python
@dataclass(frozen=True)
class ShlSponsorCashflows:
    """Canonical sponsor-view of SHL cashflows."""
    shl_investment_keur: float           # initial funding (negative = outflow)
    shl_refund_keur: tuple[float,...]   # principal refunds per period
    shl_cash_interest_keur: tuple[float,...]  # cash interest income per period
    shl_pik_keur: tuple[float,...]      # PIK (accrued income, not yet cash)
```

SponsorEngine uses `shl_refund` and `shl_cash_interest` forIRR, but excludes `shl_pik` until actually paid.

---

## 9. Validation and Audit Export Plan

### 9.1 Balance reconciliation

```
Opening[t] + Drawdown[t] + PIK[t] - Principal[t] = Closing[t]

Verification:
∀ period: closing_balance_keur == opening_balance_keur + pik_capitalized_keur - principal_repaid_keur
```

### 9.2 Cash flow reconciliation

```
post_senior_cash[t] = cash_interest_paid[t] + principal_repaid[t] + cash_after_shl[t]

Verification:
∀ period: cash_consumed_by_shl[t] + cash_after_shl[t] == post_senior_cash[t]
```

### 9.3 TUHO baseline assertions

| Assertion | Expected |
|-----------|----------|
| Total gross accrued | 53,351 kEUR |
| Total cash interest paid | 38,755 kEUR |
| Total PIK capitalized | 14,596 kEUR |
| Total principal repaid | 43,731 kEUR |
| Total SHL DS incl WHT | 82,486 kEUR |
| PIK periods | > 0 |
| 100% cash sweep periods | 36 (all operating periods) |
| Final closing balance | ~0 (fully repaid by end of model) |

### 9.4 Audit export format

```python
def to_csv(result: ShlEngineResult, path: Path) -> None:
    """Write period-by-period audit CSV."""
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "period_index", "excel_col", "operating_period_index",
            "shl_opening_keur", "drawdown_keur", "shl_closing_keur",
            "gross_accrued_keur", "cash_int_paid_keur", "pik_capitalized_keur",
            "principal_repaid_keur", "post_senior_cash_keur",
            "cash_consumed_keur", "cash_after_shl_keur", "cash_for_distribution_keur",
            "pik_triggered", "cash_sweep_100_pct", "reserve_applied",
            "classification", "warnings",
        ])
        writer.writeheader()
        for row in result.audit_table:
            writer.writerow(asdict(row))
```

---

## 10. Runtime Integration Plan (Default-OFF Flag)

### 10.1 Future `shl_enabled` flag

When `shl_enabled=True`, the canonical `ShlEngine` is used. When `False`, the legacy `shl_fcf_waterfall.py` behavior is preserved.

```python
@dataclass
class WaterfallConfig:
    shl_enabled: bool = False  # default OFF — migration safety
    shl_cash_sweep_after_senior: bool = True
    shl_maintain_minimum_cash_reserve: bool = False
    shl_minimum_cash_reserve_keur: float = 0.0
    shl_pik_allowed: bool = True
```

### 10.2 Migration path

1. **Phase 7 (design):** This document. No runtime changes.
2. **Phase 8 (canonical module):** Implement `domain/shl/` with `ShlEngine`, validate against TUHO fixture.
3. **Phase 9 (integration):** Wire `ShlEngine` into `waterfall_core` behind `shl_enabled=True` flag.
4. **Phase 10 (promotion):** Set `shl_enabled=True` as default, remove legacy code after regression.

---

## 11. Migration from Legacy `domain/shl_fcf_waterfall.py`

### 11.1 Legacy behavior gaps

- Reads from waterfall-aggregated cash directly (not from `post_senior_cash_available_keur` field)
- No explicit `post_senior_cash` input — source ownership ambiguous
- PIK trigger may not match Excel's `MAX(gross - cash × outstanding_pct, 0)`
- 3-tranche structure aggregated in `DS!R120` — tranche detail in rows 133–161 not directly consumed
- No `cash_sweep_pct` parameter — inherits whatever the waterfall produces
- Audit export ad-hoc, not canonical

### 11.2 Migration steps

```
domain/shl_fcf_waterfall.py  →  domain/shl/engine.py
────────────────────────────────────────────────────
waterfall_aggregated_cash    →  post_senior_cash_available_keur_by_period
implicit cash sweep          →  cash_sweep_after_senior = True (explicit)
ad-hoc PIK trigger           →  MAX(gross - cash_available × outstanding_pct, 0) (canonical)
DS!R120 combined             →  DS!R120 + tranche detail rows 133–161 (multi-tranche)
no audit export              →  audit.py with to_csv(), to_dataframe()
```

### 11.3 Validation

```python
def validate_against_excel(shl_result: ShlEngineResult, excel_csv_path: str) -> None:
    """Regress ShlEngineResult against extracted Excel CSV."""
    excel_rows = load_csv(excel_csv_path)
    for shl_row, excel_row in zip(shl_result.audit_table, excel_rows):
        assert_close(shl_row.gross_accrued_keur, excel_row["ds_r135_gross_accrued_int_keur"])
        assert_close(shl_row.cash_int_paid_keur, excel_row["ds_r122_net_int_paid_keur"])
        assert_close(shl_row.pik_capitalized_keur, excel_row["ds_r138_pik_capitalized_keur"])
        assert_close(shl_row.principal_repaid_keur, excel_row["ds_r137_principal_repaid_keur"])
        assert_close(shl_row.shl_closing_keur, excel_row["ds_r139_shl_ending_keur"])
```

---

## 12. Oborovo Readiness

### 12.1 Status: ⚠️ OPEN ITEM

Oborovo Excel workbook (`20260414_BP_Oborovo_Sensitivity_FINAL for PPT.xlsm`) was **not available in the workspace** during SHL cash sweep extraction (PR #98). The Oborovo SHL pattern is therefore **unverified**.

### 12.2 Expected differences (based on Phase 5D context)

- Oborovo is a solar project vs TUHO wind — different construction timing and CFADS profile
- SHL may have different tranche structure or rates
- `maintain_minimum_cash_reserve` may differ
- Oborovo distribution constraints from Phase 5D may affect SHL timing

### 12.3 Required action before Oborovo SHL integration

1. Obtain Oborovo Excel workbook
2. Extract same SHL cell rows (`DS!R120`, `R122`, `R124`, `R125`, `R127`, `R128`, `R135`, `R137`, `R138`, `R139`)
3. Verify `cash_sweep_after_senior = True` for Oborovo
4. Verify `pik_allowed` and tranche rates
5. Update `ShlEngineInputs.tranche_rates` and `tranche_day_fracs` to handle Oborovo config
6. Write `reports/phase7_oborovo_shl_cash_sweep_extraction.csv`

---

## 13. Forbidden Scope / Non-Goals

- **No runtime implementation** of `ShlEngine` in this branch
- **No creation** of active `domain/shl/*.py` runtime files (only illustrative pseudocode in this doc)
- **No changes** to `domain/shl_fcf_waterfall.py`
- **No changes** to senior debt modules
- **No changes** to tax modules
- **No changes** to distribution account runtime
- **No R99/R102 promotion** — R99/R102 remains BLOCKED
- **No flags** added to project factory
- **No changes** to `app/*` or `app/waterfall_core.py`
- **No scalar plugs**
- **No silent runtime behavior changes**

---

## 14. Acceptance Criteria

- [x] Branch is docs/design/test-only
- [x] No production/runtime files changed
- [x] Design separates SHL from senior debt, tax, distribution, and sponsor economics
- [x] Canonical SHL inputs: `opening_balance_keur`, `drawdown_keur_by_period`, `interest_rate_by_period`, `day_count_fraction_by_period`, `post_senior_cash_available_keur_by_period`, `cash_sweep_after_senior`, `maintain_minimum_cash_reserve`, `minimum_cash_reserve_keur`, `pik_allowed`
- [x] Canonical SHL outputs: `gross_accrued_interest_keur`, `cash_interest_paid_keur`, `pik_capitalized_keur`, `principal_repaid_keur`, `closing_balance_keur`, `cash_consumed_by_shl_keur`, `cash_after_shl_keur`, `cash_for_distribution_keur`
- [x] Canonical period result and engine result dataclasses documented
- [x] Audit row dataclass and export plan defined
- [x] TUHO 100% cash sweep preserved as default (`cash_sweep_after_senior = True`)
- [x] Optional minimum reserve hook is default-off (`maintain_minimum_cash_reserve = False`)
- [x] Oborovo missing extraction explicitly documented as open item
- [x] Tax interface documented (`ShlTaxInterface`)
- [x] Distribution/R99/R102 interface documented (BLOCKED status preserved)
- [x] Sponsor interface documented
- [x] Migration plan from `shl_fcf_waterfall.py` described
- [x] Validation and audit export plan defined
- [x] R99/R102 remains BLOCKED
- [x] All tests pass

---

## 15. Recommended Next Branch

**Option A: `phase7-senior-debt-canonical-module-design`** (recommended)
Design the canonical senior debt module following the same pattern as this SHL design. Maps to the senior debt source map from PR #97.

**Option B: `phase7-shl-design-review-fixes`**
If the SHL design exposes unresolved questions (e.g., Oborovo extraction needed, tranche handling clarification needed), address those before senior debt design.

---

*Document version: 1.0 — 2026-05-19*  
*Authors: Phase 7 design branch — cofix + OpenClaw agent*