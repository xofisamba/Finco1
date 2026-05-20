# Phase 7F: Oborovo OpEx Fix

**Branch:** `phase7f-oborovo-opex-fix`  
**Base:** `216651498e8ddede577b97a5ac8e05739970aed3` (PR #129)  
**Date:** 2026-05-20

## Executive Summary

**Status: NO FIX NEEDED** — Oborovo OpEx is already correctly calibrated.

Investigation confirmed that `create_default_oborovo()` in `app/project_factories.py` already produces the correct Y1 OpEx total of **1,338 kEUR** (matching Excel target exactly). The earlier reported gap of ~1,998 kEUR was based on stale data in the PR #129 calibration review CSV.

The factory correctly uses:
- `Technical Management = 198 kEUR` (parent only, no sub-items)
- `Infrastructure Maintenance = 244 kEUR` (parent only, no sub-items)
- `Environmental&Social = 32 kEUR` (parent only, no sub-items)
- **Total Y1 OpEx = 1,338 kEUR** ✅

## Investigation Findings

### What was reported (PR #129 calibration review)
| Metric | Reported "Excel" | Reported "Model" | Delta |
|--------|-----------------|------------------|-------|
| Oborovo OpEx Y1 | 1,338 kEUR | 1,998 kEUR | +660 ❌ |

The PR #129 calibration review CSV contained **incorrect model values** for Oborovo OpEx. The reported model value of 1,998 kEUR did not match the actual output of the current codebase.

### What the actual model produces
| Metric | Excel Target | Actual Model | Delta | Status |
|--------|-------------|--------------|-------|--------|
| Oborovo OpEx Y1 | 1,338 kEUR | **1,338 kEUR** | 0 | ✅ CORRECT |
| Oborovo Avg DSCR | 1.147 | **1.229** | +0.082 | ⚠️ WARN |
| Oborovo Equity IRR | 10.60% | **9.17%** | -1.43pp | ⚠️ WARN |
| Oborovo Project IRR | 7.96% | **7.98%** | +0.02pp | ✅ OK |
| Oborovo Debt | 42,852 kEUR | **42,852 kEUR** | 0 | ✅ OK |
| Oborovo Distributions | 104,918 kEUR | **104,699 kEUR** | -219 | ✅ OK |
| TUHO OpEx Y1 | 1,998 kEUR | **1,998 kEUR** | 0 | ✅ CORRECT |
| TUHO Avg DSCR | 1.451 | **1.554** | +0.103 | ⚠️ WARN |
| TUHO Equity IRR | 11.61% | **11.15%** | -0.46pp | ⚠️ WARN |

### Root cause of earlier misreport
The PR #129 calibration review CSV (written by a sub-agent) contained incorrectly sourced model values. Specifically:
- Oborovo OpEx Y1 was listed as "1,998 kEUR" for model but actual is 1,338 kEUR
- Oborovo Distributions were listed as "120,096 kEUR" for model but actual is 104,699 kEUR
- Oborovo Avg DSCR was listed as "0.848" but actual is 1.229

This appears to have been a data sourcing error in the sub-agent's CSV generation.

### Current Oborovo factory OpEx items (correct)
| Item | Y1 Amount (kEUR) |
|------|-----------------|
| Technical Management | 198.0 |
| Infrastructure Maintenance | 244.0 |
| Maintain Site | 45.0 |
| Clean Material | 40.0 |
| Security | 30.0 |
| Insurance | 255.0 |
| Lease & Property Tax | 208.1 |
| Power Expenses | 177.0 |
| Fees | 14.0 |
| Audit&Accounting&Legal | 24.0 |
| Bank Fees | 20.0 |
| Environmental&Social | 32.0 |
| Contingencies | 51.0 |
| Taxes | 0.0 |
| Salary&Payroll | 0.0 |
| **TOTAL** | **1,338.1** |

## What was investigated

1. **Oborovo OpEx factory (`app/project_factories.py:create_default_oborovo`)** — confirmed correct (1,338 kEUR total, no duplication)
2. **Oborovo DSCR calibration test (`tests/test_oborovo_dscr_calibration.py`)** — all 9 tests pass, confirming correct OpEx
3. **Oborovo OpEx tests (`tests/test_opex_runtime_flag.py`)** — passing, confirms flag semantics
4. **TUHO OpEx (`app/project_factories.py:create_default_tuho_wind1`)** — correctly uses 1,998 kEUR
5. **No Oborovo-specific OpEx template** — Oborovo uses the same `OpexItem` path as TUHO

## Actual calibration status

### Oborovo — mostly calibrated
| Metric | Excel | Model | Status |
|--------|-------|-------|--------|
| Debt | 42,852 | 42,852 | ✅ OK |
| Project IRR | 7.96% | 7.98% | ✅ OK |
| OpEx Y1 | 1,338 | 1,338 | ✅ OK |
| Distributions | 104,918 | 104,699 | ✅ OK (-0.2%) |
| Avg DSCR | 1.147 | 1.229 | ⚠️ WARN (+0.082, outside ±0.05) |
| Equity IRR | 10.60% | 9.17% | ⚠️ WARN (-1.43pp, outside ±1.0pp) |

### TUHO — mostly calibrated  
| Metric | Excel | Model | Status |
|--------|-------|-------|--------|
| Debt | 43,359 | 43,359 | ✅ OK |
| OpEx Y1 | 1,998 | 1,998 | ✅ OK |
| Project IRR | 9.47% | 9.41% | ✅ OK (-0.06pp) |
| CO2 Y1 | 611 | 611 | ✅ OK |
| Avg DSCR | 1.451 | 1.554 | ⚠️ WARN (+0.103) |
| Equity IRR | 11.61% | 11.15% | ⚠️ WARN (-0.46pp) |

## Remaining calibration gaps (not OpEx)

These are **NOT** OpEx issues and cannot be fixed by adjusting OpEx:

1. **Oborovo Equity IRR** (-1.43pp vs Excel) — driven by different merchant curve assumptions (model uses AFRY curve vs Excel's older curve). Not a simple fix.
2. **Oborovo Avg DSCR** (+0.082 vs Excel) — may be driven by Revenue timing differences, not OpEx.
3. **TUHO Avg DSCR** (+0.103 vs Excel) — may be CFADS sensitivity issue.
4. **TUHO Equity IRR** (-0.46pp vs Excel) — may be CO2 assumptions or revenue timing.

## Recommended next branches

1. **`phase9-tuho-calibration-deep-dive`** — address TUHO DSCR/IRR deltas
2. **`phase9-oborovo-merchant-curve-review`** — investigate Oborovo equity IRR gap (-1.43pp)
3. **`phase9-shl-r102-runtime-wiring`** — implement SHL R102 input contract

## What this branch does

**No code changes** — this branch documents that no fix is needed for Oborovo OpEx.

The calibration review CSV has been corrected to reflect actual model outputs.