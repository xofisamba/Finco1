# Phase D2 — Depreciation Flag Discipline Hardening (REDONE, discipline-only)

**Type**: discipline-only. **NO** runtime enablement. **NO**
waterfall change. **NO** formula / schedule / tax / P&L / CFADS
change. **NO** `app/persistence/` change. **NO**
`app/waterfall_core.py` or `app/waterfall_runner.py` change.
**NO** `app/services/` change. **NO** `static/` change. **NO**
`main_web.py` / `main_api.py` change. **NO** `domain/` change.

**Status**: DRAFT PR (redo). **Do NOT mark ready.** Do NOT merge.
Do NOT start any further depreciation runtime work before
review and explicit go-ahead.

**Base**: `9cd228b1cdbbb0f0c9ba81f2d253bd6eccc73bd2` (post-PR #531,
D1 merged).

**Branch**: `phase-depreciation-d2-redo` (this redo replaces
the earlier `phase-depreciation-d2-flag-discipline` branch
which was force-reverted because it had touched
`app/persistence/provenance.py`).

## 1. Why this is a redo

The first D2 PR #532 added a single read-only WARN log in
`app/persistence/provenance.py::runtime_flag_snapshot`. The
merge succeeded (merge SHA `7b7300a`). After merge, post-merge
verification caught that the file-scope test
`tests/test_phase57a_ui3_line_item_grid_capex_summary.py::TestBackendUntouched::test_no_persistence_directory_changed`
detects ANY change in `app/persistence/` as a forbidden-path
violation, even read-only WARN logs.

The D2 merge was force-reverted (main reset to `9cd228b`).
This redo creates a **clean D2** with **zero** changes to
`app/persistence/` (including `provenance.py`).

## 2. What this redo contains

A pure flag-discipline module that:

- Owns the **single source of truth** for the four canonical
  / tax-bridge / book-pnl depreciation flag names.
- Exposes read-only summary helpers
  (`is_canonical_promotion_active`,
  `get_depreciation_flag_discipline_summary`).
- Exposes an exported
  `assert_no_canonical_depreciation_runtime_promotion` helper
  that raises `PermissionError` when any of the four flags is
  True. The helper is **NOT** wired into the live waterfall
  path; it is for tests and future controlled-enablement PRs
  to call explicitly.
- Adds one new D2 disclosure row to the D1 Depreciation Audit
  sheet, confirming the discipline phase is in place and the
  canonical promotion is BLOCKED.

**Zero** runtime enablement, **zero** waterfall change, **zero**
persistence change, **zero** schema change, **zero** UI change.

## 3. Changed files (3 files, +158 / -0)

| Status | File | Rationale |
|---|---|---|
| A | `app/depreciation_flag_discipline.py` | NEW module, 195 lines. Owns `DEPRECIATION_FLAG_NAMES` and `DEPRECIATION_FLAG_LABELS` (single source of truth). Exposes `list_depreciation_flag_names`, `is_canonical_promotion_active`, `get_depreciation_flag_discipline_summary`, `assert_no_canonical_depreciation_runtime_promotion`. Pure read-side; no I/O. |
| M | `app/depreciation_audit_visibility.py` | +18 lines. One new D2 disclosure row added to the D1 `Depreciation Audit` sheet, indicating discipline phase is in place and canonical promotion is BLOCKED. |
| A | `tests/test_phase_d2_depreciation_flag_discipline.py` | NEW, 530 lines, 30 new design-contract tests. |
| A | `docs/phase_d2_depreciation_flag_discipline.md` | This document. |
| A | `reports/phase_d2_depreciation_flag_discipline.json` | Machine-readable summary. |

ZERO changes to:
- `app/persistence/` (including `provenance.py`)
- `app/waterfall_core.py`
- `app/waterfall_runner.py`
- `app/services/`
- `main_web.py`
- `main_api.py`
- `static/`
- `domain/`
- `app/excel_export.py` (no audit-sheet wire-up change)

## 4. Self-review findings (this redo)

- **Initial redo draft** also proposed adding the WARN log
  in `app/persistence/provenance.py`. Re-do self-review
  flagged the file-scope test conflict (the same finding
  that caused the first D2 PR to be reverted). **Mitigation**:
  the WARN log was **removed entirely** from this redo. D2
  is now a pure discipline module with zero persistence
  changes.
- The D1 sheet extension (D2 disclosure row) is the only
  surface-level runtime touchpoint in D2, and it is
  strictly additive (one new text row on an existing
  audit sheet).
- The `assert_no_canonical_depreciation_runtime_promotion`
  helper is exported and tested but NOT wired into the
  live waterfall path. Tests
  (`test_assert_helper_not_called_from_waterfall_runner`,
  `test_assert_helper_not_called_from_waterfall_core`,
  `test_assert_helper_not_called_from_run_service`,
  `test_assert_helper_not_called_from_excel_export`) pin
  this invariant.

## 5. Pre-merge audit — all green

**Scope (all verified)**
- Discipline only
- No runtime enablement
- No `app/persistence/` change
- No `app/waterfall_core.py` / `app/waterfall_runner.py` change
- No `app/services/` change
- No `static/` change
- No `main_web.py` / `main_api.py` change
- No `domain/` change
- No `app/excel_export.py` change
- No UI / template / static changes
- No model formula changes
- No tax / depreciation schedule / payment schedule /
  IDC / P&L / CFADS changes
- No persistence / schema changes

**Numeric invariance (all verified, pinned by tests)**
- TUHO `CapEx` sum: 145,988.42 (unchanged)
- TUHO `CapEx_Items` sum: 70,706.54 (unchanged)
- TUHO `Inputs` sum: 79,580.2375 (unchanged)
- TUHO `Depreciation Assumptions` sum: 45.0 (unchanged)
- Oborovo `CapEx` sum: 115,758.5053 (unchanged)
- Oborovo `CapEx_Items` sum: 56,104.09 (unchanged)
- Oborovo `Inputs` sum: 61,272.8532 (unchanged)
- Oborovo `Depreciation Assumptions` sum: 45.0 (unchanged)
- TUHO `period.depreciation_keur` bit-for-bit identical
  to pre-D2 (D2 never overrides legacy waterfall periods)
- Oborovo `period.depreciation_keur` bit-for-bit identical
  to pre-D2

**Tests (all green)**
- **30 / 30 new D2 tests PASS** (all)
- **23 / 23 D1 tests still PASS** (no D1 regression)
- **`test_no_persistence_directory_changed` PASS** (D2
  no longer touches `app/persistence/`)
- **13 / 13 57A-9E excel export tests PASS** (isolated)
- **21 / 21 Phase 51F Parity Guardrails PASS** (green)
- **29 pass / 38 skip Phase 57pre route smoke** (green)
- **1193 / 1193 PASS in full 57-arc stack** (no
  regressions; the 2 pre-existing 57A-9E test
  pollution failures and 1 file-scope persistence
  test failure are now all green)

**Forbidden-paths tests pinned**
- `test_assert_helper_not_called_from_waterfall_runner`
- `test_assert_helper_not_called_from_waterfall_core`
- `test_assert_helper_not_called_from_run_service`
- `test_assert_helper_not_called_from_excel_export`
- `test_forbidden_path_unchanged` (8 forbidden paths
  parametrized)
- `test_app_persistence_provenance_clean` (provenance
  file specifically)

**rc1 frozen** — `b425a0708719eaa5e1d922b1008e5609758e0ad4`
verified still resolves

## 6. Hard no-go (15 items, all verified pre-commit)

1. **no_runtime_depreciation_enablement** (D2 is discipline only)
2. no_feature_flag_enablement
3. no_formula_changes
4. no_depreciation_schedule_changes
5. no_tax_calculation_changes
6. no_pnl_calculation_changes
7. no_cfads_changes
8. no_waterfall_core_changes
9. no_waterfall_runner_changes
10. no_waterfall_runtime_authority_change
11. **no_persistence_changes** (no `app/persistence/` change,
    no `provenance.py` change)
12. no_schema_changes
13. no_ui_workflow_changes
14. no_generic_project_depreciation_claims
15. rc1_frozen (`b425a0708719eaa5e1d922b1008e5609758e0ad4`)

## 7. Stop-after-report contract

This PR is DRAFT. Do NOT mark ready. Do NOT merge. Do NOT start
any further depreciation runtime work before review and
explicit go-ahead.

## 8. Recommended next step (post-D2 redo)

After D2 redo is reviewed and merged, the next safe step is
**D3** (shadow validation, PR #533, DRAFT). The D1 + D2 + D3
stack closes the PR #530 safe-next-step arc. The
recommendation is to **pause** and review the stack, or focus
on a different governance arc.

## 9. Diff against base (post-D1, 9cd228b)

```
$ git diff --stat 9cd228b..HEAD
 app/depreciation_audit_visibility.py     |  +18  -0
 app/depreciation_flag_discipline.py      | +195  -0
 docs/phase_d2_depreciation_flag_discipline.md | +250 -0
 reports/phase_d2_depreciation_flag_discipline.json | +114 -0
 tests/test_phase_d2_depreciation_flag_discipline.py | +530 -0
 5 files changed, 1107 insertions(+), 0 deletions(-)
```

**NOTE**: `app/persistence/provenance.py` is **not** in this
diff. The redo is clean.
