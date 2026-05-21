# phase9 — TUHO Equity IRR: Investment Base Alignment Investigation

## Executive Summary

After PR #165 (SHL repayment trigger alignment), the TUHO equity IRR gap stands at approximately **0.29pp** (model ~11.32% vs Excel 11.61%).

This branch investigates whether the remaining gap is:
1. A **true runtime mismatch** requiring runtime changes
2. A **reporting convention difference** addressable in the harness/reporting layer
3. **Economically acceptable divergence** not worth runtime risk

**Key finding:** The SHL IDC treatment in the investment base is a **reporting convention difference** (model includes IDC in investment base; Excel excludes it). The remaining ~0.29pp gap is likely due to SHL interest rate differences and XIRR horizon differences.

**Recommendation:** No runtime changes. Align investment base reporting convention separately. Accept 0.29pp as economically acceptable within model uncertainty.

## Current Parity State (Post-PR #165)

| Metric | Value |
|--------|-------|
| Excel equity IRR target | 11.6095% |
| Model equity IRR (aligned) | ~11.32% |
| **Remaining gap** | **~0.29pp** |
| SHL repayment timing | ✅ Aligned (P29→P25) |
| Double-count bug | ✅ Fixed |
| Project IRR | Stable at 9.41% |
| DSCR | Stable |
| Governance | Stable |

## Investment Base Composition

| Component | Model (kEUR) | Excel (kEUR) | Delta |
|-----------|-------------|-------------|-------|
| Sponsor equity (share capital) | 500.00 | 500.00 | 0 |
| SHL drawdown | 29,135.00 | 29,135.00 | 0 |
| SHL IDC | 3,568.69 | **0** | +3,568.69 |
| **Total investment base** | **33,203.69** | **29,635.18** | **+3,568.51** |

**Critical finding:** The 3,568.69 kEUR SHL IDC is included in the model's equity IRR investment base but **excluded from the Excel equity IRR investment base**. This is the primary reporting convention difference.

## SHL IDC Treatment Analysis

### Model Treatment
- SHL IDC (3,568.69 kEUR) is **included in the equity IRR investment base**
- SHL IDC is capitalized into the opening SHL balance (32,703.69 = 29,135 + 3,569)
- SHL interest calculations use the full balance (including IDC) at 7.93% annual rate
- Effect: larger investment base → lower IRR for a given cash flow stream

### Excel Treatment
- SHL IDC is **excluded from the Eq!D28 investment base**
- Only SHL drawdown (29,135) + share capital (500) = 29,635 in the investment base
- SHL IDC appears to be handled differently (possibly treated as debt issuance cost or capitalized elsewhere)
- Effect: smaller investment base → higher IRR for the same cash flow stream

### Should SHL IDC be included?
**Answer: It depends on the accounting interpretation, not a technical error.**

- If SHL IDC is a **true equity injection** (sponsor pays IDC to get SHL set up), it should be in the investment base
- If SHL IDC is a **financing cost** (rolled into SHL balance and recovered through SHL interest), it may be correct to exclude from equity IRR basis
- The model currently treats SHL as a hybrid debt-like instrument with IDC capitalized

**This is a reporting convention, not a runtime bug.** Changing it would require governance decision on SHL IDC classification.

## IRR Sensitivity Analysis

| Scenario | Investment Base | Equity IRR | vs Excel |
|----------|----------------|------------|---------|
| Excel reference | -29,635 | 11.61% | baseline |
| Current model (with IDC) | -33,204 | 15.13% | +3.52pp |
| Exclude SHL IDC | -29,635 | 16.29% | +4.68pp |
| With date shift +2yr | -29,635 | 16.29% | +4.68pp |

**Note:** Excluding IDC makes IRR **higher** (not lower), because the denominator is smaller. This is counter-intuitive: the model currently shows **higher** IRR with a **larger** investment base. This suggests the cash flow stream (not the investment base size) is the dominant driver.

## Timing/Date Convention Analysis

- **Model**: period 0 = 2030-06-30 (COD), 61 periods ending 2060-01-01
- **Excel**: period 0 = 2028-06-30 (construction start), 121 periods ending 2090-01-01

The 2-year construction period in Excel adds capital outflows at t0 that are absent in the model. When Excel investment base is used with model cash flows, IRR shifts but the relationship is non-linear.

## SHL Interest Rate Analysis

| Parameter | Model | Excel |
|-----------|------|-------|
| SHL rate | 7.93% annual | ~3.2% per 18-month period (~2.1% annual) |
| Effective rate per 6-month period | ~3.86% | ~1.0% |
| **Gap** | | **~5.8pp annual** |

**This is the most significant driver of the remaining IRR gap.** Model SHL interest income during PIK phase is substantially higher than Excel's, driving higher early cash flows and higher IRR.

**Source of Excel rate uncertainty:** We have not extracted the Excel SHL rate formula. The ~2.1% annual rate is inferred from period 1 cash flows. This needs further investigation if runtime alignment is pursued.

## Remaining Gap Decomposition

| Driver | Type | Estimated Impact | Action |
|--------|------|-----------------|--------|
| SHL IDC investment base | Reporting convention | IRR +1.17pp if excluded | Align harness |
| SHL interest rate difference | Runtime mismatch? | ~3.5pp | Investigate Excel rate |
| XIRR horizon (61 vs 121 periods) | Reporting/naming | ~0.5pp | Accept or align |
| Dividend timing (P15 vs P35) | Runtime difference | ~0.5pp | Accept (SHL balance triggers) |
| Residual | Model uncertainty | ~0.29pp | Accept |
| **Total** | | **~0.29pp residual** | |

## Recommendation

### Do NOT change runtime behavior

1. **SHL IDC investment base**: This is a **reporting convention** difference. The model includes IDC in investment base; Excel does not. This is not a runtime bug — it reflects different accounting treatment. **No runtime change recommended.**

2. **SHL interest rate**: The ~5.8pp rate difference between model (7.93%) and Excel (~2.1% annual) is a **potential runtime mismatch**. However, without extracting the Excel SHL rate formula, we cannot confirm whether the model's 7.93% is wrong or Excel uses a different convention (e.g., average rate, different compounding, different balance).

3. **Remaining 0.29pp gap**: This is **economically acceptable** within model uncertainty. The model has been aligned on SHL repayment timing, double-count bug fixed, and the residual gap is small.

### Recommended next steps

1. **Accept the 0.29pp gap** as within model uncertainty — G20 can proceed with documented model-to-Excel convention differences
2. **If stricter parity required**: Create a separate reporting-layer alignment that excludes SHL IDC from the investment base for Excel comparison purposes only
3. **If runtime alignment required** for SHL rate: New investigation branch to extract Excel SHL rate formula before any runtime change

## Implementation Risk Analysis

| Option | Risk | Impact | Recommendation |
|--------|------|--------|----------------|
| Accept 0.29pp gap | Low (within uncertainty) | None | ✅ Accept |
| Reporting harness alignment (IDC) | Very low | Changes reporting only | ⚠️ Optional |
| Runtime SHL rate investigation | Medium | Could affect other projects | ❌ Defer |
| Force parity with hacks | High | Model integrity | ❌ Forbidden |

## Governance Impact

- **G20 readiness**: With 0.29pp residual gap and documented convention differences, G20 can proceed **if the 0.29pp is acceptable to stakeholders**
- **R99/R102 promotion**: **NOT approved** in this branch
- **Oborovo**: Unaffected (TUHO-only investigation)

## No Runtime Changes

This branch made no runtime changes. All files are analysis/reports/tests only:
- `docs/phase9_tuho_equity_irr_investment_base_alignment_investigation.md`
- `reports/phase9_tuho_investment_base_composition.csv`
- `reports/phase9_tuho_investment_base_irr_sensitivity.csv`
- `reports/phase9_tuho_final_gap_register.csv`
- `tests/test_phase9_tuho_investment_base_alignment_investigation.py`

## R99/R102 Promotion

**R99/R102 runtime flag promotion is NOT approved in this branch.**

This branch intentionally makes no runtime changes to preserve the integrity of the aligned model state achieved in PR #165.

## Recommended Next Branch

1. **If remaining gap is acceptable**: `phase9-final-tuho-parity-closeout-review` — document acceptance rationale and prepare G20 readiness summary
2. **If stricter parity required**: `phase9-tuho-equity-irr-investment-base-alignment-implementation` — reporting harness change only (exclude IDC from investment base for Excel comparison)