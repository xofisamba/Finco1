# Phase 17C From-Scratch Runtime Path

Phase 17C implements user-created project runtime from saved assumptions. A user-created project now builds `ProjectInputs` from the clean saved project/scenario snapshot instead of using TUHO, Oborovo, or generic factory templates as the primary runtime source.

TUHO and Oborovo remain factory templates and continue to run through their existing factory path. User-created projects are routed through `build_projectinputs_from_snapshot`, which validates required Phase 17B fields, converts numeric/date strings, and creates a runtime object directly from the saved assumptions.

## Runtime Source Precedence

For user-created projects, runtime source precedence is clean saved scenario snapshot, then project baseline_snapshot, then documented system defaults only for secondary fields not yet captured.

Unsaved dirty browser state is never runtime authority. The existing dirty guard still blocks model run, compare, export, and save-run behavior when the current browser draft differs from the clean saved source.

## Builder Coverage

The snapshot builder maps project metadata, country/market, capacity, COD, construction months, horizon, tariff, PPA term, P50 hours, year-one OPEX, total CAPEX, gearing, interest rate, tenor, and target DSCR.

Secondary assumptions not collected in Phase 17B use explicit system defaults: semiannual frequency, simple capex allocation to the provided total CAPEX line, 2% OPEX/revenue indexation, Croatia tax defaults, no CO2 revenue, and default availability/degradation conventions.

## Runtime Delta Proof

Behavioral tests prove that increasing tariff and P50 hours increases total revenue, increasing OPEX reduces EBITDA, and increasing gearing changes debt stress through DSCR. These are input-mapping proofs, not formula changes.

## Guardrails

No model formula changes were made. Workbook calculations, export calculation logic, scenario compare semantics, persistence authority, and save/run boundaries were not redesigned.

Save does not auto-run. Run does not auto-save. Frontend/browser state does not become runtime authority.

G20 remains BLOCKED. R99/R102 remain NOT APPROVED.
