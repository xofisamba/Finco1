# Stack U — Pilot Trust Polish

**Branch:** `stack-u-pilot-trust-polish`
**Base:** `main` at Stack S squash-merge `d7b5767`
**Date:** 2026-07-02

---

## Executive Summary

Stack U closes three low-risk pilot trust issues identified by the independent DD
before Stack T (Tax Engine Accuracy) begins.  All fixes are in the export,
template, and test layers.  No engine, domain, or financial formula changes.

No parity numbers move.

---

## U1 — Export IRR Scaling Fix

### Root Cause

`_write_dashboard_sheet()` in `app/excel_export.py` (line 524) divided IRR values
by 100 before writing them to Excel cells:

```python
rows.append((label, float(v) / 100))  # BUG: v is already a decimal fraction
```

`build_dashboard_kpis()` returns raw decimal fractions from the engine
(e.g. `equity_irr = 0.1159`).  The subsequent `number_format = "0.0%"` applied at
line 569 multiplies the stored value by 100 on display, so:

| Path | Stored value | Excel displays |
|------|-------------|----------------|
| Buggy | 0.1159 / 100 = 0.001159 | 0.1% |
| Fixed | 0.1159 | 11.6% |

### Fix

Removed the `/ 100`.  The raw decimal is stored; Excel's `"0.0%"` format handles
the display multiplication.

```python
# After fix:
rows.append((label, float(v)))  # decimal fraction; Excel "0.0%" × 100 on display
```

### File Changed

`app/excel_export.py` — line 524

---

## U2 — OPEX Template 500 Guard

### Root Cause

`sheet_opex_detail.html` crashed with a `TypeError` when OPEX values were `None`.
Three sites:

| Line | Expression | Failure mode |
|------|-----------|--------------|
| 47 | `"%.1f"\|format(project_ctx.opex_y1_total_keur\|default(0))` | Jinja2 `\|default` only fires for undefined, not `None` |
| 259 | `{% if child.inflation_pct == 0 %}` | `None == 0` is `False`; falls through to `"%.1f"\|format(None)` → crash |
| 427 | `"%.1f"\|format(item.escalation_pct)` | `None` passed directly |

### Fix

Three defensive changes:

1. Line 47: `opex_y1_total_keur|default(0)` → `opex_y1_total_keur or 0`
2. Line 259: `if child.inflation_pct == 0` → `if not child.inflation_pct` (catches `None` and `0.0`)
3. Line 427: `format(item.escalation_pct)` → `format(item.escalation_pct or 0)`

No OPEX calculation logic was changed.  No data stored differently.

### File Changed

`app/templates/partials/sheet_opex_detail.html` — lines 47, 259, 427

---

## U3 — Report Artefact Hygiene

### Problem

Recent PRs accidentally included generated report artefacts in diffs:
- `reports/phase10_calibration_reconciliation_pack.xlsx`
- `reports/phase12_governance_label_usage_matrix.csv`

### Fix

Added SHA-256 pins for both artefacts in `tests/test_stack_u_pilot_trust_polish.py`
(`_REPORT_ARTEFACT_SHA_PINS`).  These tests fail if either file is modified without
an intentional update to the hash.

The pins are lightweight (two extra parametrized test cases); no new infrastructure,
no regeneration of reports.

### File Changed

`tests/test_stack_u_pilot_trust_polish.py` — `_REPORT_ARTEFACT_SHA_PINS` dict
and `TestU3ReportArtefactHygiene` class

---

## Files Changed

| File | Change |
|------|--------|
| `app/excel_export.py` | Remove erroneous `/ 100` from IRR value written to dashboard |
| `app/templates/partials/sheet_opex_detail.html` | Three `None`-safe guards on formatting expressions |
| `tests/test_stack_u_pilot_trust_polish.py` | 18 new tests: U1 IRR scaling, U2 template safety, U3 report SHA pins |
| `docs/STACK_U_PILOT_TRUST_POLISH.md` | This document |

---

## Regression Strategy

- No engine, waterfall, domain, tax, SHL, or debt sizing code touched.
- `result.equity_irr` / `result.project_irr` values unchanged — only the export
  cell formatting path corrected.
- OPEX data and calculations unchanged — template guard is display-only.
- Report SHA pins lock artefacts at their current state; any unintended
  modification is detected by the test suite.
- `build_projectinputs`, `build_projectinputs_seeded`, `run_waterfall`, and all
  Golden Parity values are unaffected.

---

## Confirmation

### No engine changes
- ✅ No changes to `domain/`
- ✅ No changes to `app/waterfall_core.py`
- ✅ No changes to `domain/waterfall/waterfall_engine.py`
- ✅ No changes to `app/project_factories.py`

### No financial calculation changes
- ✅ No tax engine changes
- ✅ No debt sizing changes
- ✅ No SHL mechanic changes
- ✅ No IRR calculation changes
- ✅ No financial formula changes

### No parity movement
- ✅ TUHO equity IRR: 11.59% (unchanged)
- ✅ TUHO project IRR: 9.41% (unchanged)
- ✅ TUHO avg DSCR: 1.3786 (unchanged)
- ✅ Oborovo equity IRR: 10.66% (unchanged)
- ✅ Oborovo project IRR: 8.09% (unchanged)
- ✅ Oborovo avg DSCR: 1.179 (unchanged)
- ✅ SHA locks in `test_phase51f_parallel_work_guardrails.py` unchanged

### Stack T tax out of scope
- ✅ SHL deduction correction: NOT in this PR
- ✅ H1 CIT cash settlement: NOT in this PR

---

## Test Summary

| Class | Tests | Covers |
|-------|-------|--------|
| `TestU1IRRScaling` | 8 | Dashboard IRR cells numeric, correct decimal, percentage format, TUHO + Oborovo |
| `TestU2OpexTemplate500Guard` | 8 | Template renders with None/zero/normal inflation and escalation values |
| `TestU3ReportArtefactHygiene` | 2 | SHA-256 pins for phase10 xlsx and phase12 csv |

All 18 Stack U tests pass.
All 268 Stack K–S parity + guardrail tests pass.
