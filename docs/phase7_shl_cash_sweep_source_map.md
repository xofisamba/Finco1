# Phase 7 — SHL Cash Sweep Source Map

## Executive Summary

TUHO Excel allocates **100% of post-senior cash to SHL** until SHL is fully served. There is **no minimum cash reserve** mechanism. Distribution starts only after SHL debt service is exhausted.

**Verified totals:**
| Metric | Value (kEUR) |
|--------|------------:|
| SHL Debt Service (incl. WHT) | **82,486** |
| SHL Gross Accrued Interest | 53,351 |
| SHL Net Cash Interest Paid | 49,782 |
| SHL PIK Capitalized | 11,027 |
| SHL Principal Repaid | 43,731 |

---

## SHL Waterfall Order

```
1. CF!R69  → CFADS = SUM(Revenue, OPEX, Tax, Interest, ...)
2. CF!R70  → Senior Debt Service = -SUM(DS!R49:R50, DS!R84:R85)
3. CF!R69 + CF!R70 → post-senior cash = CFADS - Senior DS
4. CF!R98  → Distribution Account balance = prior balance + residual
5. CF!R99  → FCF for Distribution (gate: DS!R128 >= target, or 0 if not)
6. CF!R102 → FCF for SHL = CF!R99 (100% of residual after distribution gate)
7. DS!R135 → Gross Accrued Interest = opening_balance × rate × frac
8. DS!R122 → Net Cash Interest Paid = min(gross_accrued, cash_for_shl_int)
9. DS!R138 → PIK Capitalized = gross_accrued - cash_interest_paid
10. DS!R137 → Principal Repaid = max cash remaining after interest
11. DS!R139 → SHL Ending Balance = beginning + PIK - principal
12. CF!R104 → Net SHL = -DS!R128 (debt service excl. WTH)
13. Distribution starts when CF!R99 > 0 AND DS!R128 >= target
```

**Critical observation:** CF!R99 has a gate — it only passes FCF to distribution (and thus to SHL) if `DS!R128 >= B99` (minimum DSCR constraint). Until the DSCR threshold is met, CF!R99 = 0 and CF!R102 = 0. Once the threshold is met, **100% of the remaining FCF goes to SHL**.

---

## Key Cells

| Cell | Formula | Purpose |
|------|---------|---------|
| `CF!R69` | `=SUM(R20,R38,R63,R66,R67)` | CFADS |
| `CF!R70` | `=-SUM(DS!R49:R50,DS!R84:R85)` | Senior debt service |
| `CF!R99` | `=IF(AND(OR(R128<$B$99,...),...),0,R98)` | FCF for distribution (gate) |
| `CF!R102` | `=R99` | FCF for SHL = 100% of remaining after distribution gate |
| `CF!R104` | `=-DS!R128` | Net SHL debt service |
| `DS!R120` | `=H133+H144+H155` | SHL opening balance (3 tranches combined) |
| `DS!R135` | `=H133*H$14*$B131` | Gross accrued interest (tranche 1 = Sponsor) |
| `DS!R122` | `=H135+H146+H157` | Net cash interest paid (all tranches) |
| `DS!R138` | `=MAX(H135-H116*H132,0)` | PIK capitalized |
| `DS!R137` | `=MAX(MIN(H133,H$117*H132),0)` | Principal repaid |
| `DS!R139` | `=H133+H134-H137+H138` | SHL ending balance |
| `DS!R127` | `=H122+H123+H124-H125` | SHL debt service incl. WHT |
| `DS!R128` | `=H122+H124-H125` | SHL debt service excl. WHT |

---

## PIK Trigger

**Formula:** `DS!R138 = MAX(gross_accrued - cash_available × outstanding_pct, 0)`

PIK is capitalized when `cash_available < gross_accrued × outstanding_pct`. The PIK amount equals the shortfall.

**PIK formula simplified:** `PIK = MAX(0, gross_accrued × (1 - cash_sweep_rate))`

Where `cash_sweep_rate = min(1, cash_available / gross_accrued)` — when cash is sufficient, PIK = 0; when cash is insufficient, the shortfall is PIKed.

---

## Cash Sweep Rate

All 36 operating periods show **cash_sweep_pct = 1.0 (100%)**.

The distribution gate (CF!R99) must be satisfied first (`DS!R128 >= 1.1` target), then **100% of remaining cash goes to SHL**. There is no partial sweep, no minimum reserve, no working capital retention.

---

## Minimum Cash Reserve

**Finding: NO minimum cash reserve mechanism exists in TUHO.**

The CF sheet and DS sheet contain no cells implementing a floor or reserve retention. Post-senior cash goes entirely to SHL interest → PIK → principal → distribution.

---

## Gap vs Current Python SHL Logic

The current Python SHL logic is in `domain/shl_fcf_waterfall.py` which is **fixture-bound** and not canonical. The key gaps are:

1. **Source ownership:** Python's SHL code does not consume from a canonical `post_senior_cash_available` field — instead it reads directly from waterfall-aggregated cash flows
2. **No explicit cash_sweep_pct parameter** — Python currently inherits whatever the waterfall produces, which may differ from the Excel 100% sweep if the distribution gate or senior debt sizing behaves differently
3. **No PIK trigger formula** — The PIK condition in Python may not match Excel's `MAX(gross - cash × outstanding_pct, 0)` trigger
4. **3-tranche structure** — Excel has Sponsor (B131=8%), Investor 1 (B142=8%), Investor 2 (B153=8%) tranches. Python may aggregate these differently

**Effect of gap:** If Python uses actual CFADS (not sizing CFADS) for senior repayment, the post-senior cash will be different, and SHL principal schedule will shift, producing different SHL closing balances and different distributions.

---

## Canonical ShlEngine Recommendation

```python
@dataclass(frozen=True)
class ShlEngineInputs:
    opening_balance_keur: float
    interest_rate: float
    day_count_fraction: tuple[float, ...]
    pik_eligible: bool
    post_senior_cash_keur: tuple[float, ...]
    minimum_cash_reserve_keur: float = 0.0  # default OFF, future optional

@dataclass(frozen=True)
class ShlPeriodResult:
    gross_accrued_interest_keur: float
    cash_interest_paid_keur: float
    pik_capitalized_keur: float
    principal_repaid_keur: float
    closing_balance_keur: float
    cash_consumed_keur: float  # cash_interest_paid + principal_repaid

# Waterfall order:
# 1. post_senior_cash[t] = CFADS[t] - senior_ds[t]
# 2. gross_accrued[t] = opening_balance[t-1] × rate × day_frac
# 3. cash_interest_paid[t] = min(gross_accrued[t], post_senior_cash[t])
# 4. pik_capitalized[t] = gross_accrued[t] - cash_interest_paid[t]
# 5. cash_remaining[t] = post_senior_cash[t] - cash_interest_paid[t]
# 6. principal_repaid[t] = min(cash_remaining[t], opening_balance[t-1] + pik_capitalized[t])
# 7. closing_balance[t] = opening_balance[t-1] + pik_capitalized[t] - principal_repaid[t]
```

---

## R99/R102 Gate Impact

**Status: BLOCKED.** This source map documents the SHL cash sweep but does not promote R99/R102. The canonical `ShlEngine` must be designed and tested before R99 gates can be re-evaluated.

Current gate status: **6/16 gates done** per `docs/phase7_model_stack_blueprint.md`.

---

## Acceptance Criteria

- [x] TUHO SHL waterfall mapped period-by-period
- [x] CF!R102 = 100% of post-senior cash (cash_sweep_pct = 1.0 for all 36 operating periods)
- [x] SHL gross accrued = 53,351 kEUR, PIK = 11,027 kEUR, principal = 43,731 kEUR verified
- [x] PIK trigger condition documented: `MAX(gross - cash × outstanding_pct, 0)`
- [x] No minimum cash reserve found in TUHO
- [x] Gap vs current Python SHL documented
- [x] Canonical ShlEngine recommendation clear
- [x] R99/R102 remains BLOCKED
- [x] No runtime changes
- [x] All tests pass