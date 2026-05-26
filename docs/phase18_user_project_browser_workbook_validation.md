# Phase 18A User Project Browser and Workbook Artifact Validation

Phase 18A validates the user-created project workflow at the workbook artifact and export-route layer. The goal is to prove that a user-created project built from saved assumptions can be exported and, when workbook dependencies are available, inspected as a real workbook artifact.

User-created project runtime remains bound to saved assumptions through `build_projectinputs_from_snapshot()`. Dirty browser draft state is not runtime authority. Save does not auto-run. Run does not auto-save. TUHO and Oborovo remain factory templates.

## Workbook Artifact Status

Workbook validation is designed to:

- build a user-created project snapshot
- build `ProjectInputs` from saved assumptions
- run the model
- export workbook bytes
- open the workbook with `openpyxl`
- inspect Notes and Inputs sheets for provenance and key assumptions

In this environment, `openpyxl` is not installed, so workbook artifact inspection is prepared and tested as an honest skip. The workbook validation test still verifies the expected workbook provenance labels and export-route source binding through source assertions.

## Export Route Binding Status

The `/download` POST route is user-project-aware. For user-created projects it:

- checks `runtime_guard_for_snapshot`
- uses the clean saved scenario snapshot when available
- falls back to `baseline_snapshot` when there is no saved scenario snapshot
- builds runtime inputs with `build_projectinputs_from_snapshot`
- does not silently route user-created export through TUHO or Oborovo

Phase 18A also hardens export provenance so workbook Notes metadata for user-created projects identifies `saved_project_assumptions` instead of falling back to default factory-style metadata.

## Browser E2E Status

Browser E2E remains optional. No fake browser pass is recorded. If Playwright and app-auth/test harness support become available later, the remaining browser gap is ready to be closed in a future pass.

## Guardrails

No core model formula changes were made. No workbook calculations or export formulas were redesigned. No JavaScript financial calculations were added. No lender-ready or audit-certified claim is introduced.

G20 remains BLOCKED. R99/R102 remain NOT APPROVED.
