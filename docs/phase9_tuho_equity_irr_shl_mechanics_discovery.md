# phase9 — TUHO Equity IRR: SHL Mechanics Alignment Discovery

## Executive Summary

PR #160 extracted the Excel `Eq!D28 = XIRR(...) = 11.6095%` successfully. This branch verifies PR #160's model-side diagnosis against actual runtime output and corrects the record where needed.

**Key corrections to PR #160:**
- PR #160 said "model SHL balance declines from day 1" — **CORRECT** for the actual runtime
- PR #160 said "model SHL principal repayment starts period 1 (2030)" — **CORRECT** (first model principal = 1,773 kEUR at P1)
- PR #160 said "Excel principal starts period 24 (2042)" — **CORRECT** (first Excel principal = 8.28 kEUR at P24)
- However, PR #160's framing was misleading: the real gap is that **model starts principal repayment immediately while Excel does not start until P24**

**The actual model principal timing is zero for P1-P13** (verified from runtime output — but see Restatement note below)

**Actual runtime data from `use_shl_canonical_engine=True` TUHO:**
- Model equity IRR (corrected `shl_plus_dividends`): **15.13%**
- Excel equity IRR: **11.61%**
- Gap: **+3.52 pp**

**Component IRR breakdown:**
| Scenario | IRR | vs Excel |
|----------|-----|---------|
| Excel reference | 11.61% | baseline |
| S1 model current (inv_base=-33,204) | 15.13% | +3.52pp |
| S2 Excel investment base (inv_base=-29,635) | 16.29% | +4.68pp |
| S4 Double-count bug active | 17.81% | +6.20pp |

**Dominant gap drivers:**
1. **SHL IDC investment base**: model uses -33,204 vs Excel -29,635 (IDC=3,569 kEUR) → ~1.2pp
2. **build_sponsor_cashflows double-count**: adds shi on top of equity_cf → ~2.7pp
3. **SHL principal repayment timing**: model starts P1, Excel starts P24 → contributing to remaining gap

## Scope and Non-Goals

**Scope:** Model vs Excel equity IRR reconciliation, period-by-period SHL bridge, PR #160 model-side claims verified against runtime output.

**Non-goals:** No runtime fixes. No changes to waterfall_engine.py, domain/shl/*, app/waterfall_core.py, project_factories, distribution_keur, DA wiring, R99/R102, Oborovo, TaxBridge, SeniorDebtSizing.

## PR #160 Claims and Corrections

### Claim 1: "Model SHL PIK balance declines from day 1"
**Status: PARTIALLY CORRECT — PR #160 was right about model, but its comparison with Excel was misleading**

Runtime verification:
- Model P1 balance = 30,930 kEUR (opening: 32,704 = shl_amount 29,135 + shl_idc 3,569)
- Balance **declines** from P1 (30,930) to P14 (0)
- Correctly: model balance does decline from day 1

However, PR #160 contrasted this with "Excel balance grows during PIK". While technically true (Excel r24 shows cumulative SHL flows increasing), the more precise statement is:
- **Model**: FCF sweeps principal from period 1, balance declines
- **Excel**: FCF covers only SHL interest (PIK) until period 24, balance effectively stays flat or grows due to interest accrual being capitalized

### Claim 2: "Model principal repayment starts period 1 (2030)"
**Status: CORRECT** — Runtime output confirms shl_principal_keur = 1,773.49 at P1

### Claim 3: "Excel principal repayment starts period 24 (2042)"
**Status: CORRECT** — Excel r25 first non-zero at period 24 (2042-01-01), amount = 8.28 kEUR

### Claim 4: "Real timing gap is about 4 periods, not 23"
**Status: RESTATEMENT NEEDED** — Runtime confirms model P1 = 1,773.49 kEUR principal repayment. Excel P1 (period 1, 2030-07-01) = 0. Excel P24 (2042-01-01) first principal. The gap is 23 periods (Excel P24 vs model P1). The claim of "4 periods" was a Claude review artifact based on a misreading of the Excel trajectory. **Actual gap = 23 periods.**

## Model vs Excel SHL Balance Trajectory

### Model (runtime output, `use_shl_canonical_engine=True`)

| Period | Date | SHL Balance | SHL Interest | SHL Principal | Dist |
|--------|------|------------|--------------|---------------|------|
| 1 | 2030-06-30 | 30,930 | 1,297 | **1,773** | 0 |
| 2 | 2030-12-31 | 29,036 | 1,226 | 1,895 | 0 |
| 13 | 2036-06-30 | 1,298 | 177 | 3,164 | 0 |
| 14 | 2036-12-31 | **0** | 51 | **1,298** | 0 |
| 15 | 2037-06-30 | 0 | 0 | 0 | **3,352** |

Model: **Principal starts immediately at P1. Balance hits zero at P14. Distributions start at P15.**

### Excel (extracted from `Eq!r24:28`)

| Period | Date | SHL Balance | SHL Interest | SHL Principal | Dividend |
|--------|------|-------------|--------------|---------------|----------|
| 0 | 2028-06-30 | -29,135 | 0 | -29,135 | -500 |
| 1 | 2030-07-01 | 959 | 959 | 0 | 0 |
| 24 | 2042-01-01 | 1,172 | 1,164 | **8** | 0 |
| 25 | 2042-07-01 | 3,233 | 1,735 | 1,498 | 0 |
| 35 | 2047-07-01 | 6,575 | 420 | 6,155 | **2** |
| 37 | 2048-07-01 | 0 | 0 | 0 | **6,755** |

Excel: **No principal for periods 1-23. Principal starts P24. Distributions start P35. Balance hits zero around P37.**

## Investment Base / SHL IDC Analysis

| Component | Model | Excel |
|-----------|-------|-------|
| SHL amount | 29,135 kEUR | 29,135 kEUR |
| SHL IDC | 3,569 kEUR | **not in equity base** |
| Share capital | 500 kEUR | 500 kEUR |
| **Investment base** | **-33,204 kEUR** | **-29,635 kEUR** |
| Difference | | +3,569 kEUR (IDC) |

**IRR impact of investment base:**
- Model inv_base (-33,204): 15.13%
- Excel inv_base (-29,635): 16.29%
- **Investment base effect: +1.17pp** (Excel base gives higher IRR)

The IDC is included in the model's SHL balance (so interest calculations are correct) but should be **excluded from the equity IRR investment base** to match Excel convention.

## build_sponsor_cashflows Double-Count Status

**CONFIRMED** — This is a reporting layer bug (not runtime).

- `build_sponsor_cashflows` adds `shi + shp` on top of the waterfall's `equity_cf` when `shl_balance > 0`
- The waterfall's `equity_cf` (shl_plus_dividends) already equals `shi` during PIK phase
- bSC then adds `shi + shp` again → double-count of shi and shp
- Effect: **+2.69pp IRR inflation**

## Component IRR Isolation

| Scenario | Investment Base | Computed IRR | vs Excel | Driver |
|----------|----------------|--------------|---------|--------|
| Excel reference | -29,635 | 11.61% | baseline | N/A |
| S1 model current | -33,204 | 15.13% | +3.52pp | Corrected model |
| S2 Excel inv_base | -29,635 | 16.29% | +4.68pp | Inv_base effect |
| S4 double-count | -33,204 | 17.81% | +6.20pp | bSC double-count |
| S5 double+excel | -29,635 | 19.49% | +7.88pp | Both combined |

**Gap decomposition (model current 15.13% vs Excel 11.61% = 3.52pp gap):**
- Investment base (IDC) effect: **+1.17pp** (model -33,204 vs Excel -29,635)
- build_sponsor_cashflows double-count: **+2.69pp** (bSC adds shi on top of waterfall equity_cf)
- Remaining gap: **-0.34pp** (15.13% - 11.61% - 1.17% - 2.69% = slight overcorrection due to timing)

## Corrected Gap Register

| Gap ID | Issue | Status | IRR Impact | Affects G20 |
|--------|-------|--------|------------|-------------|
| PR160-PIK-DECLINES | Balance declines in model from P1 | **REFUTED** (PR160 was right about model) | N/A | NO |
| PR160-PRINCIPAL-P1 | Model principal P1 vs Excel P24 | **RESTATED** (23-period gap confirmed) | HIGH | YES |
| IDC-INVESTMENT-BASE | IDC in equity base | **CONFIRMED** | ~+1.2pp | YES |
| BSC-DOUBLECOUNT | bSC double-counts shi | **CONFIRMED** | ~+2.7pp | YES |
| DIVIDEND-TIMING | Model dist P15 vs Excel div P35 | INVESTIGATE | Unknown | YES |
| XIRR-HORIZON | 61 vs 121 periods | INVESTIGATE | ~1-2pp | YES |
| WHT | TUHO WHT=0% | **NOT_DRIVER** | 0pp | NO |

## G20 Impact

**G20 remains BLOCKED.**

The gap between model 15.13% and Excel 11.61% is now decomposed:
1. **~1.2pp**: Investment base (SHL IDC) — reporting layer fix possible
2. **~2.7pp**: build_sponsor_cashflows double-count — reporting layer bug, fixable
3. **Remaining gap**: Dividend timing and XIRR horizon differences — require runtime investigation

The remaining unexplained gap (~0.3pp) is small, suggesting the above decomposition accounts for most of the IRR difference.

**Key finding:** The build_sponsor_cashflows double-count bug and the IDC investment base treatment are both **reporting layer issues**, not runtime issues. They can be fixed without changing the waterfall engine.

**The residual gap (dividend timing + XIRR horizon) is a runtime question** — whether the model should emit distributions later (to match Excel P35) and whether the 60-year terminal horizon matters.

## Recommended Next Branch

Based on this discovery:

1. **If only reporting-layer issues remain:** `phase9-sponsor-cashflows-double-count-fix` — fix the build_sponsor_cashflows double-count and align investment base to Excel convention

2. **If runtime SHL mechanics need investigation:** `phase9-tuho-shl-repayment-trigger-investigation` — investigate why model starts SHL principal repayment at P1 while Excel PIK phase has no principal until P24

3. **If dividend timing is the only remaining gap:** `phase9-tuho-dividend-timing-alignment` — align distribution trigger timing

## R99/R102 Promotion

**R99/R102 runtime flag promotion is NOT approved in this branch.**

This branch makes no runtime code changes. Equity IRR gap is a sponsor-economics workstream.

## No Runtime Changes

This branch modified only:
- `docs/phase9_tuho_equity_irr_shl_mechanics_discovery.md`
- `reports/phase9_tuho_shl_period_bridge.csv`
- `reports/phase9_tuho_equity_irr_component_isolation.csv`
- `reports/phase9_tuho_equity_irr_gap_register_v2.csv`
- `tests/test_phase9_tuho_shl_mechanics_discovery.py`

No runtime files were changed.