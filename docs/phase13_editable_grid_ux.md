# Phase 13B — Editable Grid UX

## Purpose

Phase 13B adds the first controlled editable-grid experience on top of the Phase 13A state-control foundation. The goal is to make selected assumption surfaces easier to edit without changing runtime authority, persistence authority, or workbook calculation behavior.

This branch is intentionally limited to:

- editable grid interaction for selected assumption inputs
- draft-state visibility
- unsaved-changes handling
- runtime snapshot clarity
- HTMX-safe partial refresh behavior
- mobile-safe fallback behavior

This branch does **not**:

- move calculations into the browser
- run financial logic in JavaScript
- bypass save or revert controls
- auto-run the model from partial edits
- promote persistence into runtime authority
- change G20 or R99/R102 governance posture

## State model

The user now sees three distinct boundaries:

1. **Saved scenario**
   - Explicit persisted snapshot.
   - The only scenario state that runtime execution may bind to after user save.

2. **Draft workspace state**
   - Editable grid changes live here first.
   - Draft changes are intentionally non-authoritative and remain preview-only until saved.

3. **Last runtime snapshot**
   - The last clean snapshot executed by the backend runtime.
   - Its meaning is immutable even if the user keeps editing afterward.

## Runtime snapshot boundary

Editable grid inputs are mirror controls only. They write back into the canonical form fields so the server can persist draft state, but they do not calculate outputs or mutate runtime results directly.

Runtime execution remains guarded by the backend:

- if draft and saved state differ, runtime is blocked
- if the active snapshot is clean, runtime may execute
- runtime summary remains tied to the last clean runtime snapshot

This preserves deterministic interpretation:

- **draft state** is editable
- **saved state** is reviewable and persistable
- **runtime state** is authoritative only after clean execution

## Editable surfaces in this phase

The first editable-grid surfaces are intentionally narrow:

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

Excluded from this phase:

- tax waterfall grids
- SHL waterfall grids
- DistributionAccount internals
- complex runtime-generated schedules
- R99/R102 surfaces

## Save and revert behavior

The UX remains explicit:

- **Save Scenario** creates a persisted scenario boundary
- **Revert Draft** restores the last saved scenario boundary
- draft edits do not silently auto-save into scenario history

Background draft persistence exists only to preserve local workflow state safely across navigation. It is not approval, not runtime execution, and not scenario publication.

## Stale-state prevention

Stale-state prevention relies on both UI signals and backend rules:

- dirty badge
- unsaved changes banner
- active scenario display
- last runtime boundary display
- backend run guard on run / compare / save-run flows

That combination prevents a common failure mode where a reviewer believes a runtime card reflects current draft values when it actually reflects an older saved snapshot.

## HTMX and partial refresh behavior

The editable-grid UX is designed to tolerate partial refreshes:

- workspace metadata is reapplied after scenario load
- draft mirror inputs are resynced from canonical form fields
- run and compare buttons are disabled while dirty
- state labels update without promoting client-side authority

## Mobile fallback behavior

The initial grid layout is optimized for desktop review, but still degrades safely on smaller screens:

- horizontal scroll for draft grids
- stacked workspace state strip on narrow viewports
- no mobile-only alternate calculation path

## Governance posture

Governance labels remain explanatory only.

- `ACCEPTED_CONVENTION` does not imply approval
- `G20` remains `BLOCKED`
- `R99/R102` remain `NOT APPROVED`

Editable draft state must never imply that a scenario is reviewed, approved, or runtime-validated.

## Known limitations

- selected input surfaces only; this is not a full grid editor
- no transaction batching or cell-level validation workflow yet
- no spreadsheet-style formula editing
- no replay engine
- no multi-user workflow

## No runtime changes statement

This branch does not change runtime formulas, workbook calculations, or persistence authority semantics. It adds UI and state-clarity behavior only.
