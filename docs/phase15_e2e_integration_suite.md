# Phase 15 E2E Integration Suite

## Purpose

This branch adds a focused repository-driven end-to-end integration suite for
the guided internal pilot workflow:

select project → edit supported assumption → save scenario → run model → export
workbook → compare scenarios.

Core pilot workflow: save scenario → run model → export workbook → compare scenarios.

The suite is intentionally test-first. It verifies the working-product workflow
without changing runtime behavior, workbook calculations, persistence
authority, or governance semantics.

## Workflow Covered

The Phase 15 suite proves the following flow on supported project state:

1. Select a supported project, currently TUHO.
2. Establish a saved scenario boundary.
3. Edit an existing supported assumption surface.
4. Confirm the workspace becomes dirty.
5. Confirm runtime-like actions are blocked while dirty.
6. Save an explicit persisted scenario snapshot.
7. Confirm save clears dirty state and does not auto-run runtime.
8. Run model from the clean saved boundary.
9. Confirm a runtime snapshot and runtime summary exist.
10. Export a workbook artifact.
11. Confirm the workbook is readable and tied to backend runtime/export context.
12. Compare against a second saved scenario.
13. Confirm compare remains descriptive, timestamped, and honest about pending
    or unavailable values.

## Authority Boundaries Confirmed

- Runtime remains the only source of financial truth.
- Draft edits are not runtime truth.
- Save creates a persisted scenario boundary but does not run the model.
- Export does not auto-run the model.
- Compare reads saved snapshots and saved runtime summaries only.
- Compare does not auto-save and does not auto-run.
- Workbook/export remains descriptive only.
- Provenance remains descriptive only.
- No replay engine behavior is introduced.
- Persistence remains non-authoritative snapshot/workflow metadata.

## Governance Posture

- `G20` remains `BLOCKED`.
- `R99/R102` remain `NOT APPROVED`.
- `audit_economic_mode` remains audit/reconciliation-only.
- `runtime_economic_mode` remains the only explicit runtime staging path.

## Scope Notes

No production application behavior changes are required for this branch.
No runtime/model formulas changed.
No workbook calculations changed.
No export calculation logic changed.
No persistence behavior changed.
No new editable surfaces were added.
No JavaScript financial calculations were added.

## Remaining Gaps

This suite improves guided internal pilot confidence, but it does not replace:

- browser automation
- external model review
- audit certification
- lender-ready claims
- multi-user workflow validation
- deployment hardening
