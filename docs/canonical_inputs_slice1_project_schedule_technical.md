# Canonical Inputs Slice 1 - Project, Schedule, Technical, Production

## Scope

This slice introduces a feature-flagged Inputs workspace for a tightly scoped
set of registry-backed fields. It uses the existing canonical path:

`Registry -> ProjectInputSet -> WorkbookService -> ProjectInputs -> engine -> RuntimeResult -> server projection -> HTMX/Jinja`

The feature flag is `FINCO_INPUTS_SLICE1_ENABLED`. **Default: active** (absent or empty → on). Set to `"0"`, `"false"`, `"no"`, or `"off"` to disable. Canonical parser: `app.utils.workbook_flag.inputs_slice1_active()`.

## Included Fields

| Canonical field | Display section | Label | ProjectInputs path | State | Validation |
|---|---|---|---|---|---|
| `project_setup.identity.project_type` | Project | Project Type | template-owned | `READ_ONLY_TEMPLATE_LOCKED` | read-only |
| `project_setup.identity.country_market` | Project | Country / Market | `info.country_iso` partial mapping | `UNAVAILABLE_UNRESOLVED` | read-only in Slice 1 |
| `project_setup.technical.cod_date` | Schedule | Commercial Operation Date | `info.cod_date` | `EDITABLE_BOUND` | required ISO date |
| `project_setup.technical.construction_months` | Schedule | Construction Duration | `info.construction_months` | `EDITABLE_BOUND` | required integer, 1-120 months |
| `project_setup.technical.horizon_years` | Schedule | Project Horizon | `info.horizon_years` | `EDITABLE_BOUND` | required integer, 1-50 years |
| `project_setup.technical.capacity_mw` | Technical | Installed Capacity | `technical.capacity_mw` | `EDITABLE_BOUND` | required number, minimum 0.1 MW |
| `project_setup.technical.p50_hours` | Production | P50 Operating Hours | `technical.operating_hours_p50` | `EDITABLE_BOUND` | required number, minimum 1 h/yr |

## Excluded Fields

| Concept | Reason |
|---|---|
| Project Name | Requires a dedicated project metadata rename workflow so `ProjectRecord.project_name` and workspace draft state cannot diverge. |
| Capacity Factor | Stored display value can become stale after capacity/P50 edits; deferred until an authoritative runtime-derived projection exists. |
| Degradation | Adapter helper exists, but no current workbook registry field exists for Slice 1. |
| Currency | No direct `ProjectInputs` path; display currency is not a runtime input. |
| Scenario label | Scenario editing is out of scope. |
| P90/P99 production values | Not registry-backed in the current Slice 1 field set. |
| Revenue, CAPEX, OPEX, Debt, Tax | Explicitly deferred to later slices or existing dedicated sheets. |

## Editable and Read-Only States

Only `EDITABLE_BOUND` fields render editable controls. Protected reference
projects force all rows to `READ_ONLY_REFERENCE_PROJECT` and the Slice 1 update
endpoint rejects direct POST attempts through the existing protected-reference
guard.

Read-only states are not cosmetic only:

- `READ_ONLY_TEMPLATE_LOCKED`: project type is owned by project creation/template.
- `UNAVAILABLE_UNRESOLVED`: country is visible as evidence but not editable
  until its free-text label to `country_iso` binding is fully registered.

Project Name is not visible or editable in Slice 1. A safe rename requires a
separate atomic project metadata contract and is intentionally deferred.

Capacity Factor is not visible in Slice 1. It remains a registry display field,
but this PR does not show it because the stored snapshot value can become stale
after Capacity or P50 edits.

## P50 Boundary

`project_setup.technical.p50_hours` remains editable only under the current
Finco1 product meaning: operating hours in `h/yr`. This slice does not claim
Excel P50/yield parity, does not derive MWh, and does not add any conversion.

## Save and Stale-State Behavior

Successful edits delegate to `WorkbookUpdateService.apply_draft_update`, which:

1. validates the semantic registry field;
2. applies the typed value to `ProjectInputSet`;
3. persists the draft snapshot through the existing V2 atomic draft update;
4. marks the workspace dirty;
5. preserves any prior runtime result until the user explicitly runs again.

Failed validation renders the submitted value and inline error without
persistence, stale-state changes, or a model run.

Successful and failed Slice 1 HTMX responses re-render the full Slice 1
container so every editable form receives the current composite content hash.
The browser transport explicitly allows controlled Slice 1 `409` and `422`
responses from `/v2/workbook/inputs-slice1/update` to swap into the DOM. This
is endpoint-scoped and does not enable global 4xx/5xx swapping. Workbook
version mismatches remain `409` responses and instruct HTMX to refresh the page
with `HX-Refresh: true`.

## Next Recommended Slice

The next recommended implementation slice is Scenarios Slice 1 for the same
canonical field set. Scenario editing is not implemented here.
