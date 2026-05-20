# Phase 9: TUHO + Oborovo Calibration Review

**Branch:** `phase9-tuho-oborovo-calibration-review`  
**Base:** `48877e064bdc8205601a5342e3deeca720960ad9` (PR #128)  
**Date:** 2026-05-20

## 1. Executive Summary

This document reviews TUHO and Oborovo calibration status after Phase 9 changes:
- DistributionAccount audit-first module implemented (PR #124–#126)
- R99/R102 remains BLOCKED (audit-only)
- No runtime cash routing introduced
- Cross-module validation pack confirms no hidden coupling (PR #128)

**Goal:** Document what is calibrated, what remains uncalibrated, and what requires Phase 7F source-map validation before R99/R102 promotion.

## 2. TUHO Calibration Status

### TUHO Model Files
- `TUHO_BP.xlsm` / `Tuho_Wind_model.xlsm` — wind model, 72 MW, FC=2028-06-30, COD=2029-12-30
- Golden calibration fixture: `tests/test_sponsor_golden_calibration.py`
- Phase 7F calibration docs: `docs/phase7f_tuho_calibration_investigation.md`, `docs/phase7f_tuho_shl_calibration_plan.md`

### TUHO Key Metrics (Phase 7F Golden Fixture)

| Metric | Excel | Model | Tolerance | Status |
|--------|-------|-------|-----------|--------|
| Debt | 43,359 kEUR | ~43,359 | ±1% | ✅ Calibrated |
| Equity IRR | 11.61% | ~11.81% | ±1.0pp | ✅ Within tol |
| Project IRR | 9.47% | ~10.46% | ±0.5pp | ⚠️ +0.99pp |
| Avg DSCR | 1.451 | ~1.682 | ±0.05 | ⚠️ +0.231 |
| CO2 Y1 | 611 kEUR | 611 kEUR | exact | ✅ Calibrated |
| Full-horizon LP distributions | 121,367 kEUR | ~121,367 | ±1% | ✅ Calibrated |
| Full-horizon GP distributions | 30,342 kEUR | ~30,342 | ±1% | ✅ Calibrated |

### CO2 Revenue — TUHO (PR #122)
- CO2 enabled: `co2_enabled=True`
- CO2 price: `4.191 EUR/MWh`
- Y1 CO2 revenue: `611 kEUR`
- Equity IRR with CO2: 11.81% vs Excel 11.61% → +0.20pp ✅
- Equity IRR without CO2: 10.58% → -1.03pp (historical problem, now resolved)

### SHL Parameters — TUHO
- SHL amount: 32,704 kEUR
- Rate: 7.93%
- Method: pik_then_sweep

## 3. Oborovo Calibration Status

### Oborovo Model Files
- `Oborovo_model.xlsm` — solar model, 53.63 MW (75.26 MWp), Croatia
- Financial Close: 2029-06-29, COD: 2030-06-29

### Oborovo Key Metrics (Phase 7F Golden Fixture)

| Metric | Excel | Model | Tolerance | Status |
|--------|-------|-------|-----------|--------|
| Debt | 42,852 kEUR | ~42,797 | ±1% | ✅ OK |
| Equity IRR | 10.60% | ~9.88% | ±1.0pp | ⚠️ -0.72pp |
| Project IRR | 7.96% | ~7.42% | ±0.5pp | ⚠️ -0.54pp |
| Avg DSCR | 1.147 | ~0.848 | ±0.05 | ❌ -0.299 |
| Total Distributions | 104,918 kEUR | ~120,096 | ±5% | ❌ +14.5% |
| LP distributions | 83,934 kEUR | ~95,985 | ±5% | ❌ +14.4% |
| GP distributions | 20,984 kEUR | ~24,111 | ±5% | ❌ +14.9% |

### Oborovo OpEx Problem
- Model Y1 OpEx: ~1,998 kEUR
- Expected Y1 OpEx: ~1,338 kEUR
- Delta: ~+660 kEUR

**Root cause:** B.01 and B.02 aggregates include sub-items that are already summed.

**Action required:** Phase 7F source-map fix (separate branch).

## 4. DistributionAccount Audit vs Runtime

### TUHO DistributionAccount Audit
- R99 gate: BLOCKED (audit only)
- R102 gate: BLOCKED (audit only)
- `equity_distribution_paid_keur = 0`
- `cash_swept_to_shl_keur = 0`

### Oborovo DistributionAccount Audit
- Oborovo guard: ACTIVE
- R99/R102: BLOCKED (`OBOROVO_NOT_SUPPORTED`)
- Audit rows still generated but gates blocked

## 5. Phase 9 Safety Invariants

| Invariant | TUHO | Oborovo |
|-----------|------|---------|
| R99/R102 BLOCKED | ✅ | ✅ |
| equity_distribution_paid = 0 | ✅ | ✅ |
| cash_swept_to_shl = 0 | ✅ | ✅ |
| Oborovo guard ACTIVE | N/A | ✅ |
| No app changes | ✅ | ✅ |
| No waterfall_core.py changes | ✅ | ✅ |

## 6. What Remains Before R99/R102 Promotion

### TUHO
1. SHL R102 runtime input design (G06) — done in PR #127
2. SHL R102 runtime input implementation (G07) — PENDING
3. DSCR stability validation (G08/G09) — documented in PR #128
4. Default-off flag implementation (G12) — PENDING
5. TUHO Excel source-map validated for R99/R102 audit values

### Oborovo
1. OpEx fix (Phase 7F source-map) — B.01/B.02 sub-item aggregation
2. Equity IRR reconciliation (driven by OpEx)
3. DSCR stability (driven by OpEx)
4. Oborovo guard already active ✅

## 7. Known Gaps

### TUHO
- **Project IRR (+0.99pp vs Excel)** — may need sizing CFADS recalibration
- **Avg DSCR (+0.231 vs Excel)** — model vs Excel methodology difference

### Oborovo
- **OpEx too high (+660 kEUR)** — sub-item aggregation issue in B.01/B.02
- **Equity IRR (-0.72pp vs Excel)** — likely driven by OpEx overstatement
- **DSCR (-0.299 vs Excel)** — driven by OpEx and revenue mis-match
- **Total Distributions (+14.5%)** — driven by OpEx issue cascading through waterfall

## 8. Recommended Next Actions

### Immediate (before Phase 9 closure)
1. Document TUHO calibration findings in this doc ✅ (done)
2. Document Oborovo calibration findings ✅ (done)
3. Note Oborovo OpEx as known gap requiring Phase 7F fix ✅ (done)

### Future Branches
1. `phase9-tuho-calibration-deep-dive` — address TUHO Project IRR and DSCR deltas
2. `phase7f-oborovo-opex-fix` — fix Oborovo OpEx aggregation (B.01/B.02 sub-items)
3. `phase9-shl-r102-runtime-wiring` — implement SHL R102 input contract
4. `phase9-distribution-account-runtime-wiring` — implement enable flag + wiring

## 9. Summary

| Project | Calibration Status | Key Issue |
|---------|-------------------|-----------|
| TUHO | ⚠️ Mostly calibrated | Project IRR +0.99pp, DSCR +0.231 |
| Oborovo | ❌ Not calibrated | OpEx too high, IRR/DSCR off |
| DistributionAccount | ✅ Audit-only, BLOCKED | No runtime routing |
| Oborovo Guard | ✅ Active | TUHO gates blocked |

**Phase 9 goal (audit-first) is ACHIEVED. Runtime promotion requires separate Phase 9F effort.**
