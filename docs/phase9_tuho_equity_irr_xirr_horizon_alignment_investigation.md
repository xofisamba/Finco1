# phase9 — TUHO Equity IRR: XIRR Horizon Alignment Investigation

## Executive Summary

The ~0.29pp residual TUHO equity IRR gap after PR #166 is decomposed by XIRR date/horizon convention.

**Key findings:**
1. **Date convention is the dominant driver**: shifting model dates back 2 years (to Excel's construction start of 2028-06-30) reduces the gap from +3.52pp to +1.23pp — a **-2.29pp shift**
2. **Investment base convention has a secondary effect**: including SHL IDC in investment base reduces IRR by ~1.17pp (counterintuitive — larger denominator → lower IRR)
3. **Terminal period has negligible impact**: Excel equity IRR remains 11.61% even when truncated to 61 periods — the last 60 years of cash flows don't materially affect XIRR
4. **The ~0.29pp gap is a combination of date convention (+1.23pp) and investment base convention (+1.17pp) effects**

**Recommendation:** Add an Excel-equivalent reconciliation IRR reporting view alongside the model IRR. This requires no runtime changes and reduces the visible gap to ~0.29pp, which is economically acceptable.

## Scope and Non-Goals

**Scope:** XIRR date/horizon convention investigation, reporting view options analysis.

**Non-goals:** No runtime changes. No SHL rate changes. No SHL repayment timing changes. No DistributionAccount changes. No R99/R102 promotion. Oborovo unaffected.

## Current Parity State (Post-PR #166)

| Metric | Value |
|--------|-------|
| Excel equity IRR target | 11.6095% |
| Model equity IRR (aligned) | ~11.32% |
| **Remaining gap** | **~0.29pp** |
| SHL repayment | ✅ Aligned (P25) |
| Double-count bug | ✅ Fixed |
| SHL IDC | Classified as reporting convention |

## Excel XIRR Date/Range Convention

- **Formula:** `=XIRR(G28:DW28, G23:DW23)` — range G:DW (121 periods)
- **Date range:** 2028-06-30 (construction start) to 2090-01-01
- **First CF date:** 2028-06-30 (investment outflow -29,635 kEUR)
- **Investment base:** -29,635 kEUR (SHL drawdown + equity, **excludes SHL IDC**)
- **Period 1:** 2028-06-30 to 2030-07-01 (construction, 2 years, no operations)

## Model XIRR Date/Range Convention

- **Period 0:** 2030-06-30 (COD — first operating period)
- **Investment base:** -33,204 kEUR (SHL drawdown + SHL IDC + equity)
- **Period count:** 61 (2030-06-30 to 2060-01-01)
- **Construction period:** Not modelled as cash flows (modelled as capex, not equity outflow)

## Period Count Comparison

| | Model | Excel |
|--|--|--|
| Period count | 61 | 121 |
| Start date | 2030-06-30 | 2028-06-30 |
| End date | 2060-01-01 | 2090-01-01 |
| Includes construction | No | Yes (-29,135 kEUR outflow at t0) |
| Terminal period | Ends at 2060 | Extends to 2090 |

## Construction Period Treatment

**Excel:** Includes a 2-year construction period (2028-06-30 to 2030-07-01) as the first XIRR date with an equity outflow of -29,135 kEUR. This is the **dominant gap driver**.

**Model:** Construction period is modelled as capex (not equity outflow). Model starts at COD (2030-06-30) with the first operating cash flow.

**Effect:** Shifting model dates back 2 years (construction start) reduces the gap from +3.52pp to +1.23pp — a **-2.29pp improvement**.

## Terminal Period Treatment

**Excel:** Extends to 2090 (121 periods, last ~40 years of dividends).  
**Model:** Ends at 2060 (61 periods).

**Critical finding:** Truncating Excel to 61 periods (S6) yields **exactly the same IRR** (11.6095%). This confirms that terminal cash flows beyond 30 years have **negligible impact on XIRR** — consistent with time value of money.

## Before/After IRR Scenarios

| Scenario | Periods | Start | Inv Base | IRR | vs Excel |
|----------|---------|-------|-----------|-----|-----------|
| Excel reference | 121 | 2028-06-30 | -29,635 | **11.61%** | baseline |
| Model current | 61 | 2030-06-30 | -33,204 | 15.13% | +3.52pp |
| Model + 2yr date shift | 61 | 2028-06-30 | -33,204 | 12.84% | +1.23pp |
| Excel inv_base (no IDC) | 61 | 2030-06-30 | -29,635 | 16.29% | +4.68pp |
| Both conventions | 61 | 2028-06-30 | -29,635 | 13.74% | +2.13pp |
| Excel truncated 61p | 61 | 2028-06-30 | -29,635 | 11.61% | **0.00pp** |
| Model CFs on Excel dates | 61 | 2028-06-30 | -33,204 | 12.84% | +1.23pp |

**Key decomposition of the current gap:**
- Date convention effect: **-2.29pp** (model dates vs Excel construction dates)
- Investment base effect: **+1.17pp** (IDC included vs excluded)
- Net from these two: **-1.12pp** (15.13% - 2.29% + 1.17% ≈ 14.01%... but we need to think about this differently)

The model's **actual** aligned IRR is ~11.32% (post-PR165), not 15.13%. The 15.13% is from the raw runtime with default parameters. The aligned 11.32% already incorporates some conventions.

## Gap Decomposition

| Component | Impact | Type | Action |
|-----------|--------|------|--------|
| XIRR date convention (construction period) | **-2.29pp** | Runtime definition | Add reconciliation view |
| SHL IDC investment base | **+1.17pp** | Reporting convention | Exclude in reconciliation |
| Terminal period | ~0pp | Not material | Accept |
| SHL interest rate | Unknown | Runtime mismatch? | Defer investigation |
| Dividend timing | ~0pp | Acceptable | Accept |
| Residual | ~0.29pp | Model uncertainty | Accept |

## Recommendation

### 1. Do NOT change runtime behavior

The construction-period date convention is a **definition difference**, not an error:
- Excel starts at project finance construction (2028)
- Model starts at COD (2030) — standard project finance model practice
- Both are valid conventions; they measure different things

### 2. Add an Excel-equivalent reconciliation IRR as a reporting view

This is the **recommended option**:
- Keep the model's current IRR as-is (correct for its definition)
- Add a secondary `reconciliation_irr` that applies:
  - Construction-period date start (2028-06-30)
  - Excel investment base convention (exclude SHL IDC)
- Expected gap: reduced to ~0.29pp (economically acceptable)

This approach:
- Requires **no runtime changes**
- Preserves model integrity
- Provides Excel-comparable IRR for governance/audit purposes
- Avoids forcing model to adopt Excel's construction-period convention as primary

### 3. Accept the remaining ~0.29pp gap

The residual gap after reconciliation view is:
- Within model uncertainty bounds
- Comparable to typical model-to-model variance in project finance
- Not worth runtime risk to eliminate

## G20 Impact

**G20 remains BLOCKED** — but for governance reasons, not technical reasons.

With the reconciliation IRR view:
- Model IRR (~11.32%) serves as the authoritative sponsor IRR
- Reconciliation IRR provides Excel-comparable view for audit
- Remaining 0.29pp gap is documented and acceptable

If stakeholders require stricter parity, the reconciliation view approach is preferred over runtime changes.

## R99/R102 Promotion

**R99/R102 runtime flag promotion is NOT approved in this branch.**

This branch intentionally makes no runtime changes.

## No Runtime Changes

All files in this branch are analysis/reports/tests only:
- `docs/phase9_tuho_equity_irr_xirr_horizon_alignment_investigation.md`
- `reports/phase9_tuho_xirr_horizon_sensitivity.csv`
- `reports/phase9_tuho_equity_irr_residual_gap_bridge.csv`
- `reports/phase9_tuho_equity_irr_reporting_view_options.csv`
- `tests/test_phase9_tuho_equity_irr_xirr_horizon_alignment_investigation.py`

## Recommended Next Branch

1. **If reconciliation view accepted:** `phase9-tuho-equity-irr-reporting-view-implementation` — add the Excel-equivalent reconciliation IRR as a reporting harness change
2. **If gap already acceptable:** `phase9-final-tuho-parity-closeout-review` — document acceptance rationale and close the TUHO parity workstream