# Phase 55F — Wire validation_summary into index/audit context

## Status

DRAFT, awaiting user review. NO auto-merge.

## Summary

Activates the UI-2.3 `_validation_summary_bar.html` partial by adding
`validation_summary` to the `index.html` render context. Counts are
derived from the existing `_governance_snapshot` (G20 status and
R99/R102 status). No fake counts. No financial model changes.

## What changed

### `main_web.py`

- New helper `_validation_summary_for_context(project_code)` that
  returns:
  - `None` if no project_code is supplied
  - A dict with `pass_count`, `warn_count`, `fail_count`, `last_validated_at=""` derived from real governance state
- Mapping (real, not invented):
  - G20 BLOCKED → `fail_count += 1`
  - R99/R102 NOT APPROVED → `fail_count += 1`
  - Other governance state → `warn_count += 1`
  - No state set → `pass_count += 1`
- Added `"validation_summary": _validation_summary_for_context(project_record.project_code)` to index.html render context.
- The helper is read-only.

### Tests

- `tests/test_phase55f_validation_summary_context.py` (26 tests)
- Tests: helper exists, returns None for missing project_code, counts
  derived from real governance state, partial renders pass/warn/fail/info,
  no fake counts, no financial changes, no CSS/JS changes.

## Hard gates verified

- ✓ Only `main_web.py` (helper + context key) and tests added
- ✓ No templates changed
- ✓ No static CSS/JS changes
- ✓ No frontend dependency changes
- ✓ No model/parity-core/schema/formula/fixture changes
- ✓ No new persistence writes (helper is read-only)
- ✓ No financial output changes
- ✓ `/run` route behavior unchanged
- ✓ No no-go UI claims introduced
- ✓ rc1 SHA `b425a07` untouched
- ✓ 865 relevant tests pass

## Context keys added

| Key | Used by | Source |
|---|---|---|
| `validation_summary` | `_validation_summary_bar.html` | `_governance_snapshot(project_code)` — G20 status + R99/R102 status |

## Important note

The validation bar currently lives in `audit_reconciliation_tab.html`
which is a tab-spec file. The `index.html` context now also includes
`validation_summary` so the bar can be included in any future
top-level page that needs the validation summary. **No template
changes are made in this PR** — the partial is already wired in
`audit_reconciliation_tab.html` and will pick up the new context
automatically when that tab is rendered with the right context.

## Recommendation

Review this PR (#474) for visual confirmation. With the wiring, the
validation bar will show real pass/warn/fail counts derived from
existing governance state. No new claims; no external validation.
