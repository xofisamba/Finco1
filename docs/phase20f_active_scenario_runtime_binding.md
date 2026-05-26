# Phase 20F - Active Scenario Runtime Binding

## What changed

Phase 20F binds backend runtime and export provenance to the selected saved active scenario.

When a workspace has an `active_scenario_id` and the workspace is clean:

1. If the active scenario is the Base Case, runtime uses the Base Case full saved input set.
2. If the active scenario is a non-base scenario, runtime resolves:
   `resolve_scenario_snapshot(base_input_set, overrides_json)`
3. Runtime never consumes browser draft state or unsaved DOM state.
4. Dirty draft guard remains in place.

## Why it changed

Phase 20E persisted active scenario selection in workspace state, but runtime still followed the prior
saved/draft boundary chain instead of explicitly resolving the selected saved scenario.

Phase 20F closes that gap so the Active badge has real backend meaning:

- **Run Model uses the selected saved scenario**
- Unsaved edits still do not affect Run until they are saved

## Provenance updates

Run/export replay metadata now records active scenario context when available:

- `active_scenario_id`
- `active_scenario_name`
- `scenario_id`
- `scenario_name`
- `is_base_case`
- `parent_scenario_id`
- `override_field_list`
- `baseline_source`
- `template_origin`

If the selected active scenario is missing or invalid, runtime falls back safely to the last clean saved boundary and records a warning note instead of crashing.

## Guardrails

- No runtime/model formula changes
- No workbook/export calculation changes
- No JavaScript financial calculations
- Backend remains source of truth
- Save does not auto-run
- Run does not auto-save
- Dirty browser draft is never runtime authority
- G20 remains BLOCKED
- R99/R102 remain NOT APPROVED

## Known limitations

- Compare remains descriptive and continues to use clean saved boundaries only.
- This branch does not expand Scenario Compare UI output.
- This branch does not add CAPEX/OPEX detail grids.

## Recommended next step

OpenClaw manual smoke on the deployed app:

1. Open a user-created project
2. Add a non-base scenario
3. Change one override such as `tariff_eur_mwh`
4. Mark it Active
5. Run Model
6. Confirm runtime output changes relative to Base Case
7. Export workbook and verify active scenario provenance is present
