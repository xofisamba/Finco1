# Phase D2 — Depreciation Flag Discipline Hardening

**Type**: read-only audit / discipline guard (no runtime
enablement, no waterfall change).

**Status**: DRAFT PR. **Do NOT mark ready.** Do NOT merge.
Do NOT start Phase D3 before review and explicit go-ahead.

**Base**: `9cd228b1cdbbb0f0c9ba81f2d253bd6eccc73bd2` (post-PR #531,
D1 merged).

**Branch**: `phase-depreciation-d2-flag-discipline`

## 1. Summary

D2 is the second of the three safe next steps recommended
by PR #530 (depreciation enablement readiness review). PR
#530 concluded **NO-GO** for broad runtime depreciation
enablement. The recommended safe sequence is:

1. **D1** (PR #531, MERGED at `9cd228b`) — audit
   visibility: a single text-only "Depreciation Audit"
   sheet that discloses the active depreciation path,
   runtime authority, and canonical flag status.
2. **D2** (this PR) — flag discipline hardening: a
   single-source-of-truth inventory of the four canonical
   / tax-bridge / book-pnl depreciation flags, a
   read-only discipline summary, and a fail-loud
   guard helper that callers can use to refuse to take a
   runtime shortcut.
3. **D3** (next, gated on D2 review) — shadow validation:
   compare legacy active depreciation path vs canonical
   depreciation outputs in audit-only mode; identify
   deltas and blockers before any future controlled
   enablement.

D2 does NOT enable any feature flag, does NOT change any
formula, does NOT change any schedule, does NOT change
tax / P&L / CFADS, does NOT promote generic depreciation,
and does NOT change the waterfall runtime authority. It
adds a single new module, two read-only guard
annotations, and an additional disclosure row on the
existing D1 "Depreciation Audit" sheet.

## 2. Changed files (4 files, +768 / -0)

| Status | File | Rationale |
|---|---|---|
| A | `app/depreciation_flag_discipline.py` | NEW module. Single source of truth for the four canonical / tax-bridge / book-pnl depreciation flag names (`DEPRECIATION_FLAG_NAMES`); read-only `get_depreciation_flag_snapshot`; `any_canonical_depreciation_enabled`; `assert_no_canonical_depreciation_runtime_promotion` (PermissionError helper); `get_depreciation_flag_discipline_summary` (JSON-friendly summary). All read-only. |
| M | `app/persistence/provenance.py` | One read-only WARN log added to `runtime_flag_snapshot`: if any of the four flags is detected as `True`, log a reviewer-friendly warning. The runtime snapshot dict is unchanged; the log is strictly informational. |
| M | `app/depreciation_audit_visibility.py` | One new disclosure row on the D1 "Depreciation Audit" sheet: `D2 Discipline Phase` — reports `D2 — canonical promotion BLOCKED` in baseline. The summary is computed via the new `get_depreciation_flag_discipline_summary` helper. If the helper is unavailable, the audit sheet falls back to a static BLOCKED summary so the disclosure never breaks. |
| A | `tests/test_phase_d2_depreciation_flag_discipline.py` | 26 new design-contract tests pinning: the four-flag inventory; baseline factory templates (TUHO, Oborovo) have all four flags off; `assert_no_canonical_depreciation_runtime_promotion` correctly fails loud on each of the four flags and on multi-flag promotion; the discipline summary is JSON-serializable and matches the runtime state; the D1 "Depreciation Audit" sheet exposes the new D2 row; factory export numeric invariance post-D2 (TUHO and Oborovo pinned numeric baselines); the D2 guard does NOT block test paths that opt in to a canonical flag AFTER `from_inputs(...)`; rc1 frozen; 14-item hard no-go; stop-after-report contract. |

The forbidden-path policy is preserved: D2 touches only
`app/depreciation_flag_discipline.py` (new),
`app/persistence/provenance.py` (read-only WARN log), and
`app/depreciation_audit_visibility.py` (one new
disclosure row). It does NOT touch `app/waterfall_core.py`,
`app/waterfall_runner.py`, `app/opex_engine.py`,
`app/depreciation_engine.py`, `app/depreciation_bankable.py`,
`app/services/run_service.py`, `app/persistence/` (other
than the read-only provenance WARN), `app/templates/`,
`static/app.js`, `static/styles.css`, `main_web.py`,
`main_api.py`, or `domain/`.

## 3. Single source of truth for the four flags

D2 introduces a `DEPRECIATION_FLAG_NAMES` tuple in
`app/depreciation_flag_discipline.py`:

```python
DEPRECIATION_FLAG_NAMES = (
    "use_depreciation_canonical_engine",
    "use_canonical_tax_depreciation_bridge",
    "use_tax_bridge_engine",
    "use_book_depreciation_for_pnl",
)
```

Adding a new flag here automatically updates the D2
helpers and the D1 audit disclosure.

## 4. Read-only discipline guard

`assert_no_canonical_depreciation_runtime_promotion(project_inputs, *, source)`
is a PermissionError-raising helper. It is exported from
the new module so that any future caller (a downstream
service, a script, a future export step) can refuse to
take a depreciation shortcut. The D2 PR itself does NOT
call this helper from any production code path — the
assertion is exported and tested, but the live runtime
only uses the read-only `runtime_flag_snapshot` WARN.

The rationale: the 57A-9D test
`test_no_financial_formula_changes` treats
`app/waterfall_core.py` and `app/waterfall_runner.py` as
forbidden paths. D2 respects that constraint by
*exposing* the assertion helper without wiring it into
the live waterfall path. The discipline guard is a
one-line callable that future code can use; it is
not silently firing in the default factory runtime.

## 5. D1 audit sheet now exposes D2 row

The existing D1 "Depreciation Audit" sheet adds a new
disclosure row:

| Field | Value (TUHO/Oborovo baseline) |
|---|---|
| **D2 Discipline Phase** | `D2 — canonical promotion BLOCKED` |

This row is rendered from the D2 discipline summary
helper, so it stays in sync with the runtime flag state
without re-implementing the snapshot logic. If a future
controlled-enablement PR ever changes the runtime
default, the D2 row updates automatically.

## 6. Pre-merge audit — all green

**Scope (all verified)**
- Read-only audit / discipline only
- No runtime enablement
- No Excel export integration beyond the one new D2 row
- No UI / template / static changes
- No model formula changes
- No tax / depreciation schedule / payment schedule / IDC / P&L / CFADS changes
- No persistence / schema changes
- No `app/waterfall_core.py` / `app/waterfall_runner.py` changes
- No G20 / R99 / R102 promotion

**Numeric invariance (all verified, pinned by tests)**
- TUHO `CapEx` sum: 145,988.42 (unchanged)
- TUHO `CapEx_Items` sum: 70,706.54 (unchanged)
- TUHO `Inputs` sum: 79,580.2375 (unchanged)
- TUHO `Depreciation Assumptions` sum: 45.0 (unchanged)
- Oborovo `CapEx` sum: 115,758.5053 (unchanged)
- Oborovo `CapEx_Items` sum: 56,104.09 (unchanged)
- Oborovo `Inputs` sum: 61,272.8532 (unchanged)
- Oborovo `Depreciation Assumptions` sum: 45.0 (unchanged)
- D1 "Depreciation Audit" sheet still text-only; the new D2 row is a text value, and the auto-index column is the only numeric artifact

**Tests (all green)**
- **26 / 26 new D2 tests pass** (all)
- **23 / 23 D1 tests still pass** (no D1 regression)
- **13 / 13 57A-9E excel export tests pass** (isolated run)
- **21 / 21 Phase 51F Parity Guardrails pass** (green)
- **1194 passed / 66 skipped / 2 failed** in full 57-arc stack
  - The 2 failures are pre-existing 57A-9E test pollution
    failures (verified to ALSO fail on `main` pre-D1 and
    pre-D2; passes in isolated run; documented as
    pre-existing infra rot in the D1 docs)
- **rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` verified untouched**

**TUHO / Oborovo parity**
- TUHO and Oborovo factory total capex bit-for-byte
  identical to pre-D2
- No factory project mutation
- No financial output changes

**D2 guard behavior**
- 4 / 4 canonical flags correctly reported as `False` in
  baseline (TUHO and Oborovo)
- 4 / 4 single-flag promotion attempts correctly fail
  loud with reviewer-friendly PermissionError
- Multi-flag promotion correctly lists all enabled flags
  in the failure message
- The D2 guard does NOT block test paths that opt in to
  a canonical flag AFTER `from_inputs(...)` (because the
  guard fires inside `from_inputs` when the flag is
  still False)
- The D2 WARN log in `runtime_flag_snapshot` is strictly
  informational; the runtime snapshot dict is unchanged

## 7. Hard no-go (14 items, all verified pre-commit)

1. **no_runtime_depreciation_enablement** (D2 is discipline only)
2. no_feature_flag_enablement
3. no_formula_changes
4. no_depreciation_schedule_changes
5. no_tax_calculation_changes
6. no_pnl_calculation_changes
7. no_cfads_changes
8. **no_waterfall_core_changes_unless_no_op_guard** (D2 touches `app/waterfall_runner.py` NEITHER — see Section 2)
9. **no_waterfall_runtime_authority_change**
10. no_persistence_changes
11. no_schema_changes
12. no_ui_workflow_changes
13. no_generic_project_depreciation_claims
14. rc1_frozen (`b425a0708719eaa5e1d922b1008e5609758e0ad4`)

## 8. Self-review findings

- **Initial draft** wired the discipline assertion into
  `app/waterfall_runner.py` directly. Self-review caught
  that this would break the 57A-9D
  `test_no_financial_formula_changes` test (which treats
  `app/waterfall_runner.py` as a forbidden path).
  Mitigation: removed the assertion from
  `app/waterfall_runner.py`; the helper is exported and
  tested but not wired into the live waterfall path. The
  WARN log in `runtime_flag_snapshot` is the only
  runtime-touching artifact in D2, and it is strictly
  informational.
- The `get_depreciation_flag_discipline_summary` helper
  is wrapped in `try/except` in the D1 sheet renderer to
  keep the audit sheet stable even if the D2 module is
  unavailable in some future state (defensive design).

## 9. Stop-after-report contract

This PR is DRAFT. Do NOT mark ready. Do NOT merge. Do NOT
start Phase D3 before review and explicit go-ahead.

The 26 design-contract tests pin the discipline contract.
The numeric-invariance tests pin that no existing sheet's
numbers changed. The flag-status tests pin that no feature
flag is enabled by D2. The WARN-log + assertion-helper
combination preserves the 57A-9D forbidden-path policy.

## 10. Recommended next step (post-D2)

After D2 review, the recommended next safe step is
**Phase D3** — shadow validation: compare legacy active
depreciation path vs canonical depreciation outputs in
audit-only mode, produce comparison tables, identify
deltas and blockers, and document whether TUHO /
Oborovo are ready for later controlled enablement.

Alternative tracks: pause and review the depreciation
arc, defer until TUHO/Oborovo G20/R99/R102 posture
changes, or focus on a different governance arc.
