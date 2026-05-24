# Phase 14 Export Lineage UI

## Goal

Make export lineage visible in the reviewer workflow before download without changing runtime authority, workbook calculations, persistence authority, or governance gates.

## What Changed

- Added an export lineage summary panel in the workspace shell.
- Added clearer export action descriptions in the downloads area.
- Added reviewer-visible context for:
  - active project
  - saved scenario boundary
  - scenario revision
  - last runtime snapshot
  - runtime origin
  - runtime timestamp
  - governance posture
- Added recent export record details so reviewers can see which scenario, runtime boundary, branch, template provenance, and flag count produced tracked artifacts.
- Added dirty/stale draft guidance near export actions.

## Updated UI Surfaces

- `app/templates/partials/workspace_shell.html`
  - export lineage summary
  - download semantics
  - recent export history details
- `app/templates/partials/scenario_workspace.html`
  - richer export lineage history for saved-scenario workflow context
- `app/templates/index.html`
  - export-lineage helper text beside existing reviewer guidance
- `static/app.js`
  - refreshes export lineage guidance when draft state changes
- `static/styles.css`
  - export-lineage panel styling
- `main_web.py`
  - passes descriptive export-lineage context to templates

## Authority Rules Preserved

- Export lineage UI is descriptive only.
- Runtime/backend output remains the source of financial truth.
- Workbook/export artifacts do not become the calculation authority.
- Dirty drafts do not silently become runtime truth.
- Export actions do not auto-run the model.
- No replay engine behavior is introduced.
- `audit_economic_mode` remains audit/reconciliation-only.
- `runtime_economic_mode` remains the only explicit runtime staging path.

## Reviewer Interpretation Notes

- Values-only Excel export reflects submitted workbook values plus descriptive provenance.
- Runtime summary CSV reflects backend runtime metrics and provenance for the active project.
- Institutional workbook reflects reviewer-facing runtime/export context and cover notes.
- If the workspace is dirty, runtime-backed exports still describe the last clean backend snapshot, not the current unsaved draft.
- `unavailable` and `not_applicable` markers are intentional and must not be read as zero.

## Governance Posture

- `G20` remains `BLOCKED`.
- `R99/R102` remain `NOT APPROVED`.
- Accepted conventions remain explanatory only and do not imply approval.

## Guardrails

- No runtime/model formulas were changed.
- No workbook calculations were changed.
- No export calculation logic was changed.
- No persistence authority promotion occurred.
- No new editable surfaces were added.
- No JavaScript financial calculations were added.

