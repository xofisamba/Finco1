# Phase 9: TUHO Equity IRR — Excel Source Map

## Executive Summary

**Key finding:** The Excel workbook with `Eq!D28` formula is **not available in the repo**. The 11.61% equity IRR reference comes from Sprint 21 gap register, not from direct Excel extraction.

The model's corrected `shl_plus_dividends` equity IRR is **14.74%** (model) / **15.49%** (manual XIRR). The gap to Excel 11.61% is **+2.88 to +3.88 pp**.

**Root cause of gap cannot be confirmed** without the Excel workbook.

## Scope and Non-Goals

**In scope:** Source-map analysis, reports, CSV data, tests.  
**Out of scope:** R99/R102 runtime implementation, runtime code changes, Excel export changes.  
**G20:** BLOCKED.

## Current Known Values

| Source | Equity IRR | Notes |
|--------|-----------|-------|
| Model `shl_plus_dividends` (waterfall inline) | **14.74%** | With correct SHL params, DA wiring, canonical SHL |
| Model `shl_plus_dividends` (manual XIRR) | **15.49%** | Same CFs, small timing difference from waterfall's own compute |
| `build_sponsor_cashflows` (buggy) | **26.66%** | Double-counts shi+shp (PR #158) |
| `equity_only` (wrong method) | **56.73%** | Wrong investment base |
| Calibrated reference (Sprint 21) | **11.15%** | Uses `shl_balance=0` bug in harness |
| Excel target | **11.61%** | Source: `Eq!D28`, MISSING_EVIDENCE |

## Excel Source Evidence Status

**MISSING_EVIDENCE:** The Excel workbook containing the `Eq!D28` cell (11.61% equity IRR) has **not been imported or extracted into the repo**. 

Available evidence:
- Sprint 21 gap register: `Eq!D28 = 11.61%`
- `tuho_usporedba_v4.xlsx`: "Model IRR: 8.89% | Excel IRR: 11.61%"
- `tuho_usporedba_sprint24.xlsx`: "Equity IRR (Model): 11.18%" vs target 11.61%
- `TUHO Comparison` sheet has SHL interest row but no equity IRR formula extraction

**Without the Excel workbook, the exact equity IRR cashflow row/range and formula cannot be confirmed.**

## Cashflow Method Comparison

**Model `shl_plus_dividends`** (correct):
- Initial investment: -33,203.69 kEUR (SHL + IDC + share capital)
- Periods 1-13: equity CF = SHL interest only (no distributions, SHL balance > 0)
- Periods 15-61: equity CF = distributions only (SHL balance = 0)
- Total SHL interest: ~10,184 kEUR
- Total distributions: ~284,342 kEUR
- XIRR = 14.74–15.49% (model vs manual)

**Excel 11.61%** (presumed, MISSING_EVIDENCE):
- Exact investment base: UNKNOWN
- Exact CF stream: UNKNOWN
- Whether it includes SHL interest: UNKNOWN
- Whether it uses different lockup distribution timing: UNKNOWN

## SHL Interest Treatment

Model `shl_plus_dividends` includes SHL interest cashflows in equity CF during the PIK phase (periods 1-13 = ~10,184 kEUR total).

**If Excel excludes SHL interest** from its equity IRR, that would explain the gap. Excel's equity IRR would then be based on distributions only, which are delayed (first distribution at period 15 vs period 3 in model). This would produce a lower IRR closer to 11.61%.

**If Excel includes SHL interest** (same as model), the gap is unexplained and may be in the lockup distribution timing or investment base.

## SHL Principal Treatment

Model excludes SHL principal from equity CF (shp goes to debt service, not equity CF stream). This is consistent with `shl_plus_dividends` method where equity CF = shi when balance > 0.

**Excel treatment: UNKNOWN.**

## WHT Treatment

TUHO has `shl_wht_rate = 0%`. No WHT applicable. Not a gap driver.

## Dividend/Distribution Treatment

Model: distributions start at period 15 (SHL fully repaid at period 14).  
**Excel lockup timing: UNKNOWN** — Sprint 21 doc says Excel also experiences DSRA/lockup delay.

## Investment Base Treatment

Model: -33,203.69 kEUR (SHL 29,135 + IDC 3,568.69 + share capital 500)  
**Excel investment base: UNKNOWN** — may differ if Excel uses different SHL IDC treatment.

## Timing/Date Convention

Model: semi-annual period end dates (2030-06-30, 2030-12-31, ...)  
**Excel XIRR date convention: UNKNOWN** — may use mid-period dates or different convention.

## Root Cause of 14.74% vs 11.61%

**Cannot be determined without Excel workbook.** Potential causes (ranked by likelihood):

1. **Excel excludes SHL interest from equity CF stream** — most likely. If Excel equity IRR uses only distributions (no SHL interest during PIK phase), the CF stream would be smaller in early periods → lower IRR → closer to 11.61%.
2. **Lockup distribution timing differs** — model has zero distributions until period 15; Excel may have some earlier distributions due to different lockup threshold.
3. **Investment base differs** — if Excel uses a different equity base (e.g., excluding SHL IDC or using different share capital), the initial investment would differ.
4. **XIRR date convention** — mid-period vs end-period dates affect IRR.

## Authoritative Method Recommendation

**Until Excel workbook is available, the authoritative method cannot be determined.**

If Excel excludes SHL interest from equity CF:
- Model `shl_plus_dividends` does NOT match Excel
- A new method (e.g., `distributions_only`) would be needed for TUHO
- **Recommended next branch:** `phase9-tuho-equity-irr-excel-extraction`

If Excel includes SHL interest:
- Model `shl_plus_dividends` conceptually matches Excel
- Gap may be in lockup timing or investment base
- **Recommended next branch:** `phase9-equity-irr-cashflow-parity-fix`

## `build_sponsor_cashflows` Double-Count Bug

PR #158 identified that `build_sponsor_cashflows` double-counts SHL cashflows for `shl_plus_dividends`, producing 26.66% vs correct 14.96%. This is a **reporting bug only** (affects sponsor reporting, not runtime).

**Must be fixed before G20** since sponsor IRR reporting would be wrong.

**Recommended fix branch:** `phase9-sponsor-cashflows-double-count-fix`

## G20 Readiness Impact

- **G20 remains BLOCKED**
- Cannot unblock without resolving the 14.74% vs 11.61% gap
- The gap may be in model methodology (wrong method for TUHO) or in the harness configuration
- Excel workbook extraction is a prerequisite for any resolution

## Recommended Next Branch

**Option A (if Excel extraction is priority):** `phase9-tuho-equity-irr-excel-extraction`  
Extract the `Eq` sheet from the TUHO Excel workbook, map `Eq!D28` equity IRR formula, and extract the equity cashflow row/range.

**Option B (if reporting bug fix is priority):** `phase9-sponsor-cashflows-double-count-fix`  
Fix the `build_sponsor_cashflows` double-count bug in `domain/returns/sponsor_cashflows.py`.

## Explicit Statements

- **R99/R102 NOT approved** — this PR does not implement or approve either flag
- **G20 remains BLOCKED** — equity IRR gap (14.74% vs 11.61%) is unresolved
- **No runtime code changed** — all deliverables are analysis/reports/tests only
- **Excel source evidence is MISSING** — `Eq!D28` cell not extracted from Excel workbook

## Deliverables

| File | Description |
|------|-------------|
| `reports/phase9_tuho_equity_irr_excel_source_map.csv` | Excel source map (12 items, 10 MISSING_EVIDENCE) |
| `reports/phase9_tuho_equity_irr_cashflow_source_bridge.csv` | 61 period-level cashflow bridge |
| `reports/phase9_tuho_equity_irr_definition_matrix.csv` | 5 methods with IRR values |
| `reports/phase9_tuho_equity_irr_gap_register.csv` | 6 gaps (G-EIRR-*) |
| `docs/phase9_tuho_equity_irr_excel_source_map.md` | This doc |
| `tests/test_phase9_tuho_equity_irr_excel_source_map.py` | Tests |