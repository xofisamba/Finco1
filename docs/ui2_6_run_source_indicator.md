# UI-2.6 — Run-source indicator

## Status

DRAFT, awaiting user visual review.

## Summary

Adds a new reusable partial `app/templates/partials/_last_run_indicator.html`
that displays a conservative last-run / run-source indicator when the
`runtime_summary` context is available, and renders nothing when it's missing.

## What changed

### `app/templates/partials/_last_run_indicator.html` (NEW)

- Conditional rendering: outputs nothing if `runtime_summary` is missing
  or has no `run_id` and no `last_run_at` (prevents showing fake IDs)
- Truncates long run IDs to first 12 chars + ellipsis
- Conservative copy: "Last run" / "Runtime source" / "Run reference" / "When"
- Always shows "Review model evidence before export." note
- Uses `<aside role="status" aria-label="Last run source">` for accessibility

### `app/templates/index.html`

- Adds `{% include "partials/_last_run_indicator.html" %}` after
  `workspace_shell.html` (additive, no removals)

### `static/styles.css`

- Adds `.last-run-indicator` and 5 sub-classes (additive, no removals)
- Uses existing CSS variables (--text-1, --text-2, --border-2, --accent-1, --bg-1, --bg-2)
  with safe fallbacks (no `:root` changes)
- 36 lines of additive CSS

### `tests/test_ui2_6_run_source_indicator.py`

- 48 new tests covering: partial existence, missing context safe,
  missing run_id safe, available fields render, no fake ID generation,
  forbidden no-go term scan, CSS additive only, no backend changes,
  accessibility, integration with index.html

## Hard gates verified

- Only allowed files modified (1 new partial, 1 CSS section, 1 index include)
- No backend/service/persistence/model changes
- No `static/app.js` changes
- No `app/runtime_impact_taxonomy.py` changes
- No frontend dependency changes
- No `:root` CSS variable changes
- No new forbidden UI claims
- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` untouched
- All 804 relevant tests pass (UI-2.1..UI-2.6, Phase 51F, 52F, 53I, 54)

## Context limitation (per Phase 54F-J)

The `runtime_summary` context key is currently NOT in the index.html render
context (verified in `main_web.py:1438`). Therefore the partial renders
nothing in the current state. The partial is wired in for future use —
when `runtime_summary` is added to the index context, the indicator will
activate automatically without further changes.

This is the conservative path: present code that is safe today (no
visible side effects because context is missing) and ready for tomorrow
(activates when context is supplied).

## Copy

Safe terms used:

- "Last run"
- "Runtime source"
- "Run reference"
- "When"
- "Review model evidence before export."

No no-go terms used. No "validated", "certified", "audit-ready",
"bankable", "lender-ready", etc.

## Recommendation

Review this PR (#468) for visual confirmation. UI-2.5 (#467) and
UI-2.6 (#468) form the final two items in the UI-2 runtime stack.
