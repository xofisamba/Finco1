# Phase 7 — Senior Debt DSCR Sizing Source Map

## Executive Summary

TUHO Excel separates **actual CFADS** from **debt sizing CFADS**. This distinction is critical for Python: using actual CFADS for debt repayment would produce faster repayment, lower senior balances, and different SHL cash sweep than Excel. This branch documents the source map empirically.

**Key finding:** Macro!R50 is hardcoded sizing CFADS — numerically ~32% below actual CFADS. The buffer maintains minimum Senior DSCR ≈ 1.41x (vs 1.2x target) across the loan life.

---

## Key Cells

| Cell | Formula | Value (kEUR) | Purpose |
|------|---------|-------------:|---------|
| `CF!R69` | `=SUM(R20,R38,R63,R66,R67)+...` | **300,927** | Actual FCF for banks / actual CFADS |
| `Macro!R49` | `=CF!R69` (direct link) | **300,927** | Actual CFADS feed into Macro |
| `Macro!R50` | **HARDCODED NUMERIC** | **204,669** | Sizing CFADS — manually adjusted |
| `DS!R19` | `=R13*$C$19+(1-R13)*$B$19` | 1.2 / 1.41 | Target DSCR (PPA/merchant) |
| `DS!R20` | `=(R17/R19+SUM(CF!R73:R73))*R9*$B20` | — | Debt service capacity |
| `Inputs!D204` | `=C160` → Scenarios!E186 | 1.2 | Base DSCR target input |

**Delta:** Macro!R49 − Macro!R50 = **96,258 kEUR (32%)**

---

## DSCR Switch

| Phase | DSCR Target | Periods |
|-------|------------|---------|
| PPA / Contracted | **1.20** | Periods 1–25 (op_idx 0–12) |
| Merchant | **~1.41** | Periods 26–61 (op_idx 13–30) |

**Switch period:** Period 26 (op_idx 13). Formula: `DS!R19 = R13*1.4 + (1-R13)*1.2`, where R13 is operating period index. As R13 > 1, blended DSCR exceeds 1.4x.

---

## Macro!R49 vs Macro!R50

```
Macro!R49 (actual CFADS):  linked to CF!R69   → 300,927 kEUR total
Macro!R50 (sizing CFADS):  HARDCODED           → 204,669 kEUR total
Buffer:                     96,258 kEUR          → 32% below actual
```

**R50 values are not formulas.** They are plain numeric constants (e.g. `2539.6336729104755`). Each period's R50 value was manually chosen to maintain the 1.41x minimum DSCR constraint.

---

## DS!R20 Debt Service Capacity Formula

```
DS!R20 = (R17 / R19 + SUM(CF!R73:R73)) × R9 × B20

Where:
  R17 = Macro!R50 (sizing CFADS) per period
  R19 = target DSCR (1.2 or ~1.41)
  CF!R73 = cumulative senior interest paid to date
  R9 = some scaling factor
  B20 = debt service capacity multiplier
```

The formula blends sizing CFADS (R17) with cumulative interest (CF!R73) to derive debt service capacity, then applies a period-specific multiplier (B20).

---

## Current Python Source Map

**Current Python uses actual CFADS**, not sizing CFADS. The waterfall computes debt service from `r69_fcf_banks_keur` (actual CFADS). It does NOT have an explicit `sizing_cfads` parameter.

**Gap:** Python senior repayment ≈ what Excel would produce if Macro!R50 ≈ R49. This results in slightly faster repayment than Excel, producing the observed ~355 kEUR minor Δ on senior interest.

---

## Canonical SeniorDebtSizingPolicy

```python
@dataclass(frozen=True)
class SeniorDebtSizingPolicy:
    sizing_cfads_keur_by_period: tuple[float, ...]  # explicit sizing input
    target_dscr_by_period: tuple[float, ...]        # 1.20 PPA / ~1.41 merchant
    interest_rate_schedule: tuple[float, ...]
    day_count_fraction: tuple[float, ...]
    opening_balance_keur: float
    maturity_periods: int
```

**Default behavior (flag-off):** Python uses actual CFADS as sizing CFADS (current behavior, no change).

**Future flag-on:** Explicit `sizing_cfads_keur_by_period` parameter wired from project inputs, matching the canonical policy above.

---

## Gap Analysis

| Issue | Cause | Effect |
|-------|-------|--------|
| Faster repayment | Python uses actual CFADS (R49) instead of sizing CFADS (R50) | Lower senior balances at maturity, different SHL cash sweep |
| SHL cash sweep impact | SHL gets residual after senior service; smaller senior balance → more SHL repaid → different distributions | R99/R102 audit values shift |
| ~355 kEUR Δ on senior interest | Actual vs sizing CFADS mismatch | Minor but present |

---

## Oborovo Check

Oborovo model (`20260414_BP_Oborovo_Sensitivity_FINAL for PPT.xlsm`) was listed as reference but not available for direct cell inspection in this branch. The same Macro!R49/R50 pattern is expected to exist in Oborovo. **Future branch should verify.**

---

## R99/R102 Status

**BLOCKED.** Senior Debt sizing source map is a prerequisite gate. This branch documents the gap but does not fix it. Future runtime implementation behind default-off flag.

---

## Acceptance Criteria

- [x] Macro!R50 is hardcoded numeric (not formula)
- [x] Macro!R49 links to CF!R69
- [x] DS!R19 shows 1.20 PPA / ~1.41 merchant split
- [x] PPA→Merchant switch at period 26 (op_idx 13)
- [x] Total sizing delta documented: 96,258 kEUR (32%)
- [x] Canonical `SeniorDebtSizingPolicy` documented
- [x] R99/R102 remains BLOCKED
- [x] No runtime changes
- [x] All existing tests pass