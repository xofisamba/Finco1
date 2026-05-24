# Phase 13C — Editable Grid Hardening

## Purpose

Phase 13C is a reliability pass over the Phase 13B editable-grid UX. It does not introduce new runtime features or broaden the editable surface area. The work is limited to hardening state semantics, partial-refresh behavior, reviewer clarity, and regression coverage.

## What this branch hardens

- dirty-state lifecycle determinism
- save and revert predictability
- HTMX partial-refresh rebinding
- stale runtime labeling when a draft diverges from the last clean runtime snapshot
- runtime-action disabling while unsaved edits exist
- reviewer clarity on draft vs saved vs runtime boundaries
- mobile-safe readability for the state strip and unsaved banner

## What this branch does not do

- no new runtime formulas
- no workbook calculation changes
- no JavaScript financial calculations
- no new editable assumption families beyond the Phase 13B surfaces
- no persistence redesign
- no replay engine
- no governance approval changes

## Hardening changes summary

1. **Dirty-state controls**
   - Run, draft compare, and save-run remain disabled while the workspace is dirty.
   - Dirty-state UI now updates button `aria-disabled` state alongside visual disabling.

2. **Stale runtime clarity**
   - When a last runtime snapshot exists and the draft becomes dirty, the runtime-origin label explicitly tells the reviewer that the runtime boundary is older than the current draft.

3. **HTMX rebinding robustness**
   - Draft persistence field listeners and grid mirror listeners are rebound safely after HTMX swaps.
   - Rebinding is idempotent, so repeated partial refreshes do not stack duplicate listeners.

4. **Reviewer messaging**
   - The unsaved banner now explains that runtime cards remain bound to the last clean snapshot.
   - The saved-scenario workspace panel repeats that boundary in plain reviewer language.

## State semantics

There are still three separate layers, and this branch reinforces that separation:

1. **Saved scenario**
   - persisted scenario snapshot
   - explicit save boundary

2. **Draft workspace state**
   - editable but non-authoritative
   - can be reverted deterministically

3. **Last runtime snapshot**
   - last executed clean backend snapshot
   - remains authoritative for runtime summary until the next clean run

## HTMX partial-refresh strategy

Phase 13C assumes partial refreshes are normal and therefore:

- reattaches draft-persistence listeners after swaps
- reattaches grid mirror listeners after swaps
- resyncs mirror inputs from canonical fields after swaps
- keeps button disablement tied to workspace metadata, not one-time page-load assumptions

## Runtime authority protection

This branch keeps runtime authority server-side only.

- grid edits never compute financial values
- JavaScript never computes IRR, DSCR, debt service, or runtime summaries
- runtime execution remains blocked while unsaved edits exist
- save and revert do not trigger runtime automatically

## Reviewer clarity

This branch is meant to reduce misreads during review:

- a dirty draft is visibly different from a saved scenario
- a stale runtime snapshot is visibly different from the current draft
- the last clean runtime result remains interpretable even after later edits

## Governance posture

- `G20` remains `BLOCKED`
- `R99/R102` remain `NOT APPROVED`

Accepted conventions remain explanatory only and do not imply approval.

## Known limitations

- still only selected editable surfaces
- no spreadsheet-like keyboard workflow
- no transaction batching
- no cell-level audit trail beyond draft/save/runtime boundaries
- no mobile-specific alternate calculation path, by design

## No runtime changes statement

Phase 13C does not change runtime formulas, workbook calculations, or persistence authority. It is a hardening pass over the Phase 13B editable-grid UX only.
