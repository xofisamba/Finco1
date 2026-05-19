# Phase 7 — SHL Metric Reconciliation Note

**Date:** 2026-05-19
**Branch:** `phase7-shl-source-map-metric-reconciliation`
**Source PRs:** #98 (`phase7-shl-cash-sweep-source-map`)

---

## Background

A GitHub review identified inconsistent SHL metric naming/totals across the SHL source map deliverables. This note records the correct values and the fixes applied.

---

## The Inconsistency

The original `docs/phase7_shl_cash_sweep_source_map.md` contained:

| Metric | Doc stated (incorrect) | Correct from CSV |
|--------|------------------------|-------------------|
| SHL Gross Accrued Interest | 53,351 kEUR | **53,351 kEUR** ✓ |
| SHL Net Cash Interest Paid | 49,782 kEUR | — |
| SHL PIK Capitalized | 11,027 kEUR | **14,596 kEUR** |
| SHL Cash Interest Paid | — | **38,755 kEUR** |

The doc used old reference values (49,782 / 11,027) that were superseded by correct CSV extraction.

---

## Correct Values (from `reports/phase7_tuho_shl_cash_sweep_extraction.csv`)

All values are totals across 63 periods (including construction col G):

| Metric | Excel Source | Value (kEUR) |
|--------|-------------|-------------:|
| SHL Gross Accrued Interest | `DS!R135` sum | **53,350.87** |
| SHL Cash Interest Paid | `DS!R135 − DS!R138` | **38,755.35** |
| SHL PIK Capitalized | `DS!R138` sum | **14,595.52** |
| SHL Principal Repaid | `DS!R137` sum | **43,730.70** |
| SHL Debt Service incl. WHT | `DS!R127` sum | **82,486.05** |

Note: `DS!R122` (net cash int paid) = `DS!R135` (gross) in the CSV, which represents **tranche 1 (Sponsor) only** in operating periods. The cash interest paid shown above (`gross − PIK = 38,755`) is the correct total across all tranches, consistent with `DS!D135 − DS!D138`.

**PIK = 14,596 kEUR** (not 11,027 kEUR as originally documented) because the CSV totals include the construction period PIK accrual. The operating-only PIK is 11,027 kEUR.

---

## Changes Made

### `docs/phase7_shl_cash_sweep_source_map.md`
- Row: "Net Cash Interest Paid 49,782" → "Cash Interest Paid 38,755"
- Row: "PIK Capitalized 11,027" → "PIK Capitalized 14,596"
- Acceptance criteria bullet updated accordingly

### `tests/test_shl_cash_sweep_source_map.py`
- Already had correct values: gross=53,351, cash=38,755, PIK=14,596 ✅
- No test changes needed — tests were already correct

---

## Metric Definitions

- **Gross Accrued Interest** (`DS!R135`): Opening balance × rate × day_frac for all 3 tranches combined, including construction period IDC.
- **Cash Interest Paid**: `gross_accrued − PIK` = actual cash outflow for interest. In TUHO construction period, no cash interest is paid — all accrues as PIK.
- **PIK Capitalized** (`DS!R138`): Interest accrued but not paid in cash — added to SHL balance. Includes construction-period PIK.
- **Principal Repaid** (`DS!R137`): Cash principal repayment after interest is paid.
- **SHL Debt Service incl. WHT** (`DS!R127`): Total SHL debt service including withholding tax, across all tranches.

---

## R99/R102 Status

BLOCKED — no changes to distribution logic in this fix branch.