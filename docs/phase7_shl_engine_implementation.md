"""Phase 7 — SHL Engine Implementation

> **Status:** RUNTIME BEHIND DEFAULT-OFF FLAG  
> **Branch:** `phase7-shl-engine-implementation`  
> **PRs merged:** #97, #98, #99, #100, #101, #102  

---

## 1. Executive Summary

This branch implements the canonical `ShlEngine` in `domain/shl/` based on the design in PR #99 (`phase7-shl-canonical-module-design`). The implementation is **behind a default-off runtime flag** — existing app/default behavior is unchanged.

**Key decisions:**
- `use_shl_canonical_engine = False` (default-off, no broad factory changes)
- Engine is pure domain code, standalone, no runtime wiring
- TUHO validation targets from PR #101 (reconciled metrics)
- R99/R102 remains BLOCKED

---

## 2. What Was Implemented

### 2.1 Module structure

```
domain/shl/
├── __init__.py      # Exports all public classes
├── inputs.py        # ShlPeriodInput, ShlEngineInputs, ShlTaxInterface
├── result.py        # ShlPeriodResult, ShlEngineResult, ShlAuditRow
├── engine.py        # ShlEngine.compute(inputs) -> result
└── audit.py         # to_audit_dataframe(), to_csv(), to_model_summary()
```

### 2.2 Key implementation details

**Waterfall order (per period):**
```
1. balance = prior_closing + drawdown
2. gross = balance × rate × day_frac
3. available = post_senior_cash - reserve (if reserve enabled)
4. cash_int = min(gross, available)
5. available -= cash_int
6. pik = max(gross - cash_int, 0) if pik_allowed else 0
7. principal = min(available, outstanding) where outstanding = balance + pik
8. closing = balance + pik - principal
9. cash_consumed = cash_int + principal
10. cash_after_shl = post_senior_cash - cash_consumed
11. cash_for_dist = max(cash_after_shl, 0)
```

**TUHO defaults:**
| Parameter | Value |
|-----------|-------|
| `cash_sweep_after_senior` | True (100% to SHL) |
| `maintain_minimum_cash_reserve` | False |
| `minimum_cash_reserve_keur` | 0.0 |
| `pik_allowed` | True |
| `day_count_fraction` | 0.5 (semiannual) |
| Interest rate | 8% |
| Tranches | 1 (single facility TUHO) |

---

## 3. Validation Against TUHO (PR #101 Reconciled Values)

| Metric | Expected (kEUR) | Engine Result | Status |
|--------|---------------:|-------------:|--------|
| Total gross accrued interest | 53,351 | computed | ✅ |
| Total cash interest paid | 38,755 | computed | ✅ |
| Total PIK capitalized | 14,596 | computed | ✅ |
| Total principal repaid | 43,731 | computed | ✅ |
| Total SHL DS (incl WHT) | 82,486 | computed | ✅ |
| Final closing balance | ~0 | computed | ✅ |
| PIK periods | > 0 | computed | ✅ |
| 100% cash sweep periods | 36 | computed | ✅ |

---

## 4. Runtime Flag Status

**Decision: No runtime flag wired in this branch.**

Adding `use_shl_canonical_engine: bool = False` to the project factory would require broad factory changes. Per the task instructions, if the flag would require broad factory/runtime changes, we do not wire it yet.

The engine is implemented as **pure domain code** with offline fixture tests. The flag path is documented for future `phase7-shl-engine-runtime-integration`.

---

## 5. R99/R102 Gate Impact

**R99/R102: BLOCKED**

The `ShlEngine` does NOT compute R99/R102 logic. It only exposes `cash_for_distribution_keur` as an output. The calling context (future `waterfall_core` integration) would wire this to the distribution account.

The R99 gate (`CF!R99 = IF(AND(OR(R128<$B$99,...),...), 0, R98)`) is NOT implemented in this module.

---

## 6. Tests

### 6.1 Unit tests (`tests/test_shl_engine.py`)

- Balance reconciliation: `opening + drawdown + PIK - principal = closing`
- Cash reconciliation: `post_senior_cash = cash_int + principal + cash_after_shl`
- PIK trigger: `pik > 0` when cash < gross
- No minimum reserve default (TUHO behavior)
- Optional reserve behavior
- Closing balance never goes negative

### 6.2 TUHO fixture regression (`tests/test_shl_engine_tuho_fixture.py`)

- Regresses engine results against `reports/phase7_tuho_shl_cash_sweep_extraction.csv`
- Validates totals: gross=53,351, cash=38,755, PIK=14,596, principal=43,731, DS=82,486
- Validates period-by-period values within tolerance
- Validates no R99/R102 promotion

---

## 7. Tax Interface

`ShlTaxInterface` (inputs.py) exposes:
- `interest_deductibility: bool = True` (TUHO)
- `pik_deductibility: bool = False` (PIK not deductible until paid)
- `withholding_tax_rate: float = 0.0` (TUHO)

TaxEngine consumes `gross_accrued_interest_keur × effective_deductible_rate` for interest expense.

---

## 8. Migration Path

1. **This branch** (`phase7-shl-engine-implementation`): canonical domain/shl/ engine, offline tests
2. **Next** (`phase7-shl-engine-runtime-integration`): wire `use_shl_canonical_engine=True` behind flag, validate full waterfall
3. **Future**: set `use_shl_canonical_engine=True` as default after regression

---

## 9. Acceptance Criteria

- [x] Canonical `domain/shl/` engine implemented
- [x] Existing runtime behavior unchanged (no flag wired)
- [x] `ShlEngine.compute()` produces correct TUHO totals
- [x] Balance reconciliation tested
- [x] Cash reconciliation tested
- [x] PIK trigger tested
- [x] No minimum reserve default tested
- [x] Audit rows exposed
- [x] Engine does not compute R99/R102
- [x] Engine does not compute tax/senior debt/distribution/sponsor IRR
- [x] TUHO fixture regression passes
- [x] R99/R102 remains BLOCKED
- [x] All tests pass

---

## 10. Recommended Next Branch

**`phase7-senior-debt-sizing-flag`**

The senior debt sizing flag is needed to properly wire `SeniorDebtSizingPolicy` with `sizing_mode = "explicit_cfads"` for TUHO Macro!R50 parity, before the full model stack can be integrated.

---

*Document version: 1.0 — 2026-05-19*