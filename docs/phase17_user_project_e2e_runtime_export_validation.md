# Phase 17D User Project E2E Runtime, Save/Load, and Export Binding Validation

Phase 17D validates the complete user-created project workflow after the Phase 17C snapshot-built runtime path.

The validated workflow is: create a user project, enter required assumptions, confirm the project appears in the selector, reload it, save a scenario, run from a clean saved state, confirm runtime output changes with saved assumptions, check export/download binding, check compare binding, and confirm reload preserves assumptions.

Runtime comes from saved assumptions for user-created projects. Dirty draft browser state is not runtime authority. Run is allowed only when the current form matches the clean workspace base or a clean saved scenario snapshot. Save does not auto-run. Run does not auto-save.

TUHO and Oborovo remain factory templates and keep their established factory runtime path.

## Export Binding Status

The download route is user-project-aware after Phase 17C. For user-created projects it calls the same clean-state guard and builds export inputs with `build_projectinputs_from_snapshot`. It does not intentionally fall back to TUHO or Oborovo for user-created project exports.

In this environment, workbook byte generation cannot be executed because `openpyxl` is unavailable. The Phase 17D package therefore includes route-source assertions and marks full workbook artifact inspection as a remaining export hardening gap.

## Compare Binding Status

The compare route is user-project-aware after Phase 17C. It uses the clean saved snapshot for user-created projects and blocks dirty drafts through `runtime_guard_for_snapshot`. It does not silently compare TUHO when a user-created project is selected.

## Remaining Gaps

Full browser E2E coverage requires FastAPI/TestClient or browser dependencies in the execution environment. Full workbook artifact inspection requires `openpyxl`. Debt-output reporting still exposes gearing effects through DSCR rather than a dedicated senior-debt KPI in the route-level card set.

G20 remains BLOCKED. R99/R102 remain NOT APPROVED.
