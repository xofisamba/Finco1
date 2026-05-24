# Phase 14A Reviewer Productivity Polish

## Purpose

Phase 14A improves reviewer clarity and accessibility around the existing editable-grid workflow without changing any runtime authority, workbook calculations, persistence authority, or governance posture.

This branch is intentionally limited to reviewer-facing polish:

- clearer draft vs saved vs runtime explanations
- clearer disabled-action explanations
- accessibility and keyboard-focus improvements
- clearer existing editable-grid help text

It does **not**:

- change financial formulas
- change runtime/model economics
- change workbook calculations
- add new editable assumption surfaces
- add JavaScript financial calculations
- alter `audit_economic_mode` / `runtime_economic_mode` contracts

## Reviewer Workflow Guidance

1. Edit assumptions in the current workspace draft.
2. If the draft changes, the workspace becomes dirty and runtime-like actions are blocked.
3. Save to create a new persisted scenario snapshot.
4. Run only after the workspace returns to a clean state.
5. Treat runtime cards as the last clean backend run, not as live browser calculations.
6. Treat workbook export as a backend-authored artifact tied to backend runtime/export behavior.

Workbook export remains backend-authored and does not use browser-side draft calculations.

## Boundary Rules

### Draft workspace

- editable
- unsaved
- preview-only
- never runtime-authoritative

### Saved scenario

- explicit persisted boundary
- created only by explicit save
- does not auto-run the model

### Runtime snapshot

- last clean backend run
- remains authoritative until the next clean run
- can become stale relative to later draft edits

## Disabled Action Semantics

When unsaved edits exist:

- Run Model is disabled because the backend must bind to a clean saved boundary.
- Compare is disabled for the same reason.
- Save Run is disabled for the same reason.

These explanations are now visible in reviewer-facing helper text and reflected in control metadata.

## Accessibility Polish

Phase 14A adds or strengthens:

- accessible names on key reviewer actions
- `aria-describedby` links from controls to reviewer guidance
- `aria-disabled` preservation on blocked actions
- visible focus treatment for keyboard users
- programmatically identifiable reviewer state banners and notes

## Existing Editable Surfaces Only

No new editable surfaces were added. This branch remains limited to the current Phase 13B editable assumption tables:

- Revenue assumptions
- OPEX assumptions
- Selected senior debt assumptions

Excluded surfaces remain excluded:

- tax waterfall grids
- SHL waterfall grids
- DistributionAccount internals
- complex runtime-generated schedules
- R99/R102 promotion surfaces

## Governance Posture

- `G20` remains `BLOCKED`
- `R99/R102` remain `NOT APPROVED`
- accepted conventions remain explanatory only and do not imply approval

## Known Limitations

- reviewer polish does not add spreadsheet-style keyboard editing
- export guidance is clearer, but export availability rules are still governed by backend flows
- stale runtime remains a reviewer interpretation state, not a browser-side recalculation state
