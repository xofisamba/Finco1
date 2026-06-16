# Phase S1-A — Export Runtime Debt Source Fix

**Status**: DRAFT, awaiting review
**Branch**: `phase/s1a-export-runtime-debt-source`
**Base**: `main` @ `3a570bc` (post HOTFIX-PILOT-BLOCKER-1)
**Risk level**: LOW (presentation-only, 1 production file + 1 test file)
**rc1**: untouched
**TUHO / Oborovo**: bit-identical parity preserved
**Engine MD5**: unchanged (`6bf49f33efc989736c17cea0cb9b7723`)
**Factories MD5**: unchanged (`3350c93a7689bb3f5e717a064adcd106`)

---

## 1. Problem (from S1 Review)

Phase S1 Review (analysis-only) identified a trust gap in the
institutional Excel export: for Generic projects, the
`Construction`, `CAPEX`, and `Senior Debt` sheets displayed
`senior debt = 0` even though the runtime actually produces a
sculpted debt amount.

### Root cause

`app/export/institutional_workbook.py` reads
`bundle.context.senior_debt_keur` (which is wired to
`financing.fixed_debt_keur` per
`app/ui/project_context.py:2335`) at three locations:

- Line 475: `("Senior debt anchor", bundle.context.senior_debt_keur, ...)`
- Line 512: `senior = bundle.context.senior_debt_keur or 0.0`
- Line 576: `("Senior debt amount", bundle.context.senior_debt_keur, ...)`

For TUHO and Oborovo, `financing.fixed_debt_keur` is set to the
frozen Excel-derived senior debt amount, and the runtime uses this
value as an override (so the runtime result is bit-identical to
the input). For Generic projects, `financing.fixed_debt_keur = 0`
because the Generic factory does not set it; the runtime
computes the actual sculpted debt amount from the DSCR-sculpt
formula.

### Empirical confirmation (pre-fix)

| Project | `input.fixed_debt_keur` | `runtime.sculpting_result.debt_keur` | Excel export reads |
| --- | --- | --- | --- |
| `generic_solar` | 0 | **22,650** | **0** (WRONG) |
| `tuho` | 43,359 | 43,359 | 43,359 (correct) |
| `oborovo` | 42,852 | 42,852 | 42,852 (correct) |

The bundle already has `runtime_result` populated (line 71 of
`institutional_workbook.py`). The Senior Debt sheet already reads
`bundle.runtime_result.actual_avg_dscr`,
`bundle.runtime_result.actual_min_dscr`,
`bundle.runtime_result.total_senior_ds_keur`. The three
`bundle.context.senior_debt_keur` reads were inconsistent with
the other senior-debt-related rows in the same sheet.

---

## 2. Fix

### Helper function

Added `_resolve_export_senior_debt_keur(bundle)` in
`app/export/institutional_workbook.py`. The helper:

- Returns the input value (`bundle.context.senior_debt_keur`)
  when it is non-zero. This is the case for TUHO, Oborovo, and
  any future project with `fixed_debt_keur` set explicitly. For
  these projects the runtime result is bit-identical to the
  input because the runtime uses the input as an override.
- Falls back to `runtime_result.sculpting_result.debt_keur` when
  the input is zero. This is the case for Generic projects.
  The runtime result is the actual sculpted debt amount.

The function never invents a value: it returns either the input
or the runtime result. For TUHO and Oborovo the two are
bit-identical, so the helper preserves the parity contract. For
Generic, the runtime result is the authoritative value.

### Patch sites (3 locations)

- `_write_construction_sheet`: `Senior debt anchor` row
- `_write_capex_sheet`: `Senior debt funding` row
- `_write_senior_debt_sheet`: `Senior debt amount` row

In each case, the value cell now calls
`_resolve_export_senior_debt_keur(bundle)`, and the
`source_classification` and `trust_note` columns are updated
from `template assumption` to `template assumption + runtime`
with a note explaining the dual source.

---

## 3. Post-fix behaviour

| Project | Export `senior debt anchor` | Export `senior debt funding` | Export `senior debt amount` |
| --- | --- | --- | --- |
| `generic_solar` | **22,650** (was 0) | **22,650** (was 0) | **22,650** (was 0) |
| `tuho` | 43,359 (unchanged) | 43,359 (unchanged) | 43,359 (unchanged) |
| `oborovo` | 42,852 (unchanged) | 42,852 (unchanged) | 42,852 (unchanged) |

---

## 4. Constraints preserved (all pinned by tests)

- ✅ rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` untouched
- ✅ No financial formula / debt / DSCR sculpt / tax / IDC changes
- ✅ No engine / factory / model changes (engine MD5 + factory MD5
  both bit-identical)
- ✅ No persistence schema migration
- ✅ No R99 / R102 / G20 / construction / sponsor changes
- ✅ TUHO / Oborovo parity bit-identical (input == runtime result
  for both, helper returns input)
- ✅ Phase 51F parity guardrails 21/21 PASS
- ✅ Phase 23s combined frozen-schedule parity 9/9 PASS
- ✅ New tests: 20 added, all PASS

---

## 5. Test coverage

`tests/test_phase_s1a_export_runtime_senior_debt.py` — 20 tests in 4
classes:

- `TestResolveExportSeniorDebtKeurHelper` (4 tests): the helper
  function returns the right value for TUHO, Oborovo, Generic.
- `TestInstitutionalWorkbookSeniorDebt` (9 tests): end-to-end
  workbook generation: the three senior-debt cells in the three
  sheets show the right value for Generic, TUHO, Oborovo.
- `TestParityBitIdentity` (3 tests): helper output matches the
  runtime result for TUHO and Oborovo (parity guarantee).
- `TestNoRuntimeChange` (4 tests): engine MD5, factories MD5,
  waterfall engine MD5, rc1 ancestor.

---

## 6. Files changed

- `app/export/institutional_workbook.py` (+45 / -3)
- `tests/test_phase_s1a_export_runtime_senior_debt.py` (NEW, 318 lines)
- `docs/phase_s1a_export_runtime_debt_source.md` (this file, NEW)
- `reports/phase_s1a_export_runtime_debt_source.md` (NEW)

No other files modified.

---

## 7. Stop-after-report contract

DRAFT only. Do NOT mark ready. Do NOT merge. Awaiting user
review and explicit go-ahead.

After approval, the next step is S1-B (gearing cap per-method
flag, medium risk, 4h) or S1-C (factory-direct ≡ resolver,
low-medium risk, 1-2h), or pause and review the arc.
