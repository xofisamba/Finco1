# Phase 1.5 Portfolio UI + Excel Export

**Branch:** `portfolio-ui-export`  
**PR:** #2  
**Repository:** `xofisamba/Finco1`

---

## Scope

Minimal portfolio UI layer and Excel export for `IndependentPortfolioResult`.

### What is added

- `app/portfolio_ui.py` — table builders for display/UI use
- `app/excel_export.py` — appends three sheets for independent SPV portfolios
- `tests/test_portfolio_ui.py` — 16 tests for UI table builders
- `tests/test_excel_export.py` — 4 portfolio tests (real Excel workbook verification)
- `docs/phase1_5_portfolio_ui_export.md` — this document

### Files changed

| File | Change |
|------|--------|
| `app/portfolio_ui.py` | New — `build_portfolio_summary_table`, `build_portfolio_spv_table`, `render_portfolio_summary` |
| `app/excel_export.py` | Append-only — adds `Portfolio_Summary`, `Portfolio_SPVs`, `Portfolio_Notes` sheets |
| `tests/test_portfolio_ui.py` | New — 16 tests for UI table builders |
| `tests/test_excel_export.py` | Extended — 4 real Excel workbook tests for portfolio sheets |
| `docs/phase1_5_portfolio_ui_export.md` | New — scope doc |

---

## IRR Semantics

Simple Average Project IRR and Simple Average Equity IRR are **unweighted averages** of per-SP IRRs. They are **NOT true portfolio XIRR values**.

- They do NOT account for different SPV sizes, timing, or capital amounts
- They do NOT use date-aligned cash flow aggregation (XIRR)
- True portfolio IRR requires aggregating all SPV cash flows across a common timeline

**IRR labels in UI tables explicitly say:**  
`"Simple Avg Project IRR (NOT Portfolio XIRR)"` and `"Simple Avg Equity IRR (NOT Portfolio XIRR)"`

---

## DSRF Status

DSRF is a **placeholder only** in Phase 1.5:

- `dsrf_enabled=False` by default
- `enabled=True` raises `ValueError` immediately
- No funding/release engine implemented

---

## Tests

| Command | Result |
|---------|--------|
| `pytest tests/test_portfolio_ui.py -q` | 16 passed |
| `pytest tests/test_excel_export.py -q` | 40 passed (4 new portfolio workbook tests) |
| `pytest tests/test_phase1_portfolio.py -q` | 28 passed |
| `pytest tests/test_portfolio_inputs.py tests/test_portfolio_runner.py tests/test_portfolio_waterfall.py -q` | 50 passed |
| `pytest tests/ -q` (full suite) | 1,434 passed, 1 xfailed, 0 regressions |

---

## Explicit Limitations

Phase 1.5 does NOT implement:

- **No HoldCo** entity
- **No SHL** / intercompany flows
- **No Sponsor IRR**
- **No monthly model** frequency
- **No pooled financing**
- **No cross-SP cash pooling**
- **No retained earnings constraint**
- **No DSRF funding/release** engine

These are deferred to Phase 2+.

---

## Excel Export Sheets

| Sheet | Content |
|-------|---------|
| `Portfolio_Summary` | Portfolio KPIs — totals, DSCR, IRR labels |
| `Portfolio_SPVs` | Per-SP V breakdown — code, name, revenue, EBITDA, tax, DS, distributions, DSCR, IRR |
| `Portfolio_Notes` | Limitations disclaimer, IRR disclaimer, DSRF status, warnings |