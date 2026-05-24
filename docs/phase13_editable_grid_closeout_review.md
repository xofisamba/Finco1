# Phase 13D — Editable Grid Closeout Review

## Purpose

Phase 13D is the closeout review pack for the Phase 13 editable-grid program. It does not add features. It documents and verifies that the Phase 13A, 13B, and 13C work preserves runtime authority, draft/saved/runtime boundaries, governance posture, and stale-state protections.

## Closeout finding

The editable-grid workflow remains controlled and review-safe:

- editable grids are draft-only input surfaces
- saved scenarios remain explicit persisted boundaries
- last runtime results remain bound to the last clean backend snapshot
- runtime-like actions remain blocked while unsaved edits exist
- frontend code does not calculate financial outputs

## Authority boundaries

Phase 13 closes with the following boundaries intact:

1. **Draft workspace state**
   - editable
   - preview-only
   - not runtime-authoritative

2. **Saved scenario**
   - explicit persisted scenario snapshot
   - save clears dirty state
   - save does not auto-run runtime

3. **Last runtime snapshot**
   - authoritative runtime boundary until next clean run
   - later draft edits do not mutate prior runtime meaning

4. **Frontend**
   - never computes IRR, DSCR, debt service, EBITDA, or runtime summaries
   - only mirrors selected fields into canonical form inputs

## State transition review

The validated transition path remains:

- clean saved scenario load
- draft edit creates dirty state
- dirty state disables runtime-like actions
- save clears dirty state and creates a persisted scenario boundary
- revert restores the saved boundary and clears dirty state
- any later draft edit after runtime clearly stales the runtime snapshot

## HTMX review

The closeout review confirms that expected partial refreshes preserve semantics:

- scenario-load refresh reapplies workspace metadata
- mirror inputs resync from canonical fields after swaps
- listeners rebind idempotently after swaps
- dirty and clean labels remain visible after expected swaps

## Editable surface inventory

Current editable surfaces are still limited to the Phase 13B scope:

- Revenue assumptions
  - tariff
  - PPA term
  - P50 hours
- OPEX assumptions
  - Y1 OPEX
  - construction months
- Financing assumptions
  - gearing
  - target DSCR
  - interest rate
  - tenor

No new editable surfaces were added in Phase 13D.

## Excluded surfaces

Still excluded from editable-grid scope:

- tax waterfall grids
- SHL waterfall grids
- DistributionAccount internals
- complex runtime-generated schedules
- R99/R102 surfaces

## Governance posture

The closeout review confirms:

- `G20` remains `BLOCKED`
- `R99/R102` remain `NOT APPROVED`
- accepted conventions remain explanatory, not approval

## Known limitations

- selected editable surfaces only
- no spreadsheet-style formula editing
- no replay engine
- no multi-user coordination layer
- no cell-level transaction history
- no alternate mobile calculation path, by design

## Recommended next roadmap step

The next sensible step is a narrow Phase 14 workflow pass focused on reviewer productivity, not authority expansion:

- richer reviewer messaging
- keyboard and accessibility polish
- optional cell validation ergonomics
- stronger publish/package workflow for dirty local environments

## No runtime changes statement

Phase 13D does not change runtime formulas, workbook calculations, persistence authority, or governance approval semantics. It is a closeout review pack only.
