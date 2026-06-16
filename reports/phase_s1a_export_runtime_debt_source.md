# Phase S1-A Report — Export Runtime Debt Source

**Status**: DRAFT, awaiting review
**Date**: 2026-06-17
**Branch**: `phase/s1a-export-runtime-debt-source`
**Base**: `main` @ `3a570bc` (post HOTFIX-PILOT-BLOCKER-1)
**Risk level**: LOW (presentation-only)

## Summary

Phase S1-A fixes a presentation-only trust gap in the
institutional Excel export: Generic projects displayed
`senior debt = 0` even though the runtime produces a real
sculpted debt amount. TUHO and Oborovo are bit-identical
unchanged.

## Files

| File | Lines | Purpose |
| --- | --- | --- |
| `app/export/institutional_workbook.py` | +45 / -3 | Add `_resolve_export_senior_debt_keur` helper, patch 3 read sites |
| `tests/test_phase_s1a_export_runtime_senior_debt.py` | NEW, 318 lines | 20 tests: helper unit + workbook integration + parity + invariants |
| `docs/phase_s1a_export_runtime_debt_source.md` | NEW | Phase brief, problem, fix, constraints |
| `reports/phase_s1a_export_runtime_debt_source.md` | NEW | This report |

## Test results

### S1-A test suite (20 tests)
- TestResolveExportSeniorDebtKeurHelper: 4/4 PASS
- TestInstitutionalWorkbookSeniorDebt: 9/9 PASS
- TestParityBitIdentity: 3/3 PASS
- TestNoRuntimeChange: 4/4 PASS

### Phase 51F Parity Guardrails (21 tests)
- 21/21 PASS (engine MD5, factories MD5, frozen schedule
  hashes, runtime mode wiring all preserved)

### Phase 23s combined frozen-schedule parity
- 9/9 PASS (TUHO + Oborovo frozen senior-debt schedule parity
  bit-identical)

## Empirical evidence

### Pre-fix vs post-fix

| Project | Pre-fix `senior debt anchor` | Post-fix `senior debt anchor` | Delta |
| --- | --- | --- | --- |
| `generic_solar` | 0 | **22,650** | +22,650 (FIX) |
| `tuho` | 43,359 | 43,359 | 0 (parity) |
| `oborovo` | 42,852 | 42,852 | 0 (parity) |

### Runtime source-of-truth

| Project | `input.fixed_debt_keur` | `runtime.sculpting_result.debt_keur` | Match |
| --- | --- | --- | --- |
| `generic_solar` | 0 | **22,650** | NO (helper falls back) |
| `tuho` | 43,359 | 43,359 | YES (helper returns input) |
| `oborovo` | 42,852 | 42,852 | YES (helper returns input) |

## Engine and factory invariants

| File | MD5 | Status |
| --- | --- | --- |
| `app/waterfall_core.py` | `6bf49f33efc989736c17cea0cb9b7723` | UNCHANGED |
| `app/project_factories.py` | `3350c93a7689bb3f5e717a064adcd106` | UNCHANGED |

## Constraints preserved (all pinned by tests)

- ✅ rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` untouched
- ✅ No financial formula / debt / DSCR sculpt / tax / IDC changes
- ✅ No engine / factory / model changes
- ✅ No persistence schema migration
- ✅ No R99 / R102 / G20 / construction / sponsor changes
- ✅ TUHO / Oborovo parity bit-identical

## Stop-after-report contract

DRAFT only. Do NOT mark ready. Do NOT merge. Awaiting user
review and explicit go-ahead.

Next step options after approval:
- S1-B: gearing cap per-method flag (medium risk, 4h)
- S1-C: factory-direct ≡ resolver (low-medium risk, 1-2h)
- S1-D: documentation update (no risk, 1h)
- Or pause and review the arc.
