# Canonical Inputs Slice 1 Report

## Field Inventory

| Field | Registry ID | Section | Unit | Runtime binding | Decision |
|---|---|---|---|---|---|
| Project Type | `project_setup.identity.project_type` | Project | - | `TEMPLATE_LOCKED` | Include read-only |
| Country / Market | `project_setup.identity.country_market` | Project | - | `RUNTIME_PARTIALLY_BOUND` | Include unavailable/read-only evidence |
| Commercial Operation Date | `project_setup.technical.cod_date` | Schedule | - | `RUNTIME_FULLY_BOUND` | Include editable |
| Construction Duration | `project_setup.technical.construction_months` | Schedule | months | `RUNTIME_FULLY_BOUND` | Include editable |
| Project Horizon | `project_setup.technical.horizon_years` | Schedule | years | `RUNTIME_FULLY_BOUND` | Include editable |
| Installed Capacity | `project_setup.technical.capacity_mw` | Technical | MW | `RUNTIME_FULLY_BOUND` | Include editable |
| P50 Operating Hours | `project_setup.technical.p50_hours` | Production | h/yr | `RUNTIME_FULLY_BOUND` | Include editable under current product meaning |

## Fields Considered But Excluded

- Project Name: deferred to a dedicated project metadata rename contract.
- Capacity Factor: deferred until it can be projected from an authoritative runtime-derived source with stale-state semantics.
- Degradation: no current registry-backed field.
- Currency: no direct `ProjectInputs` path.
- Scenario label: Scenarios editing is out of scope.
- P90/P99 production values: not registry-backed for this slice.
- Revenue, CAPEX, OPEX, Debt and Tax inputs: out of scope for Slice 1.

## Runtime Data Path

Slice 1 editable fields use:

`Registry -> ProjectInputSet -> WorkbookUpdateService -> V2 atomic draft update -> WorkbookService -> ProjectInputs -> explicit Run`

No field uses Jinja, JavaScript, or route-local financial calculations.

## UI Evidence

Feature flag off:

- Existing Inputs Control Tower remains rendered.
- No `Canonical Slice 1` marker is present.

Feature flag on:

- `Project`, `Schedule`, `Technical`, and `Production` sections render.
- The table columns are `Input`, `Value`, `Unit`, and `Status`.
- Read-only rows show status badges and do not render hidden mutation forms.
- Protected references render read-only controls and direct POST attempts are rejected.
- Every Slice 1 save response re-renders the complete `#v2-sheet-inputs` container so all forms receive the new composite content hash.
- Controlled Slice 1 `409` and `422` HTMX responses are browser-swapped by an endpoint-scoped `htmx:beforeSwap` handler. Other workbook routes and unrelated 4xx/5xx responses are not globally swapped.
- Workbook version mismatch returns `409` with `HX-Refresh: true` for HTMX requests so the browser explicitly reloads the current registry version.

## Stale-State Evidence

After a successful edit, the workspace is marked dirty, prior runtime data remains
available, and the UI returns `Run required`. The model does not rerun until the
user explicitly presses Run.

Sequential cross-section edits are supported without a browser reload because
the first edit response refreshes every Slice 1 form hash.

Stale-hash responses also return a full Slice 1 container with current persisted
values and current form hashes, allowing retry without a full browser reload.

## P50 Boundary

P50 is exposed only as the current Finco1 operating-hours field
(`technical.operating_hours_p50`, unit `h/yr`). Excel P50/yield semantics remain
unresolved and are not claimed as parity in this PR.

## Scope Confirmation

- No model equation changes.
- No parity target changes.
- No golden fixture changes.
- No schema changes.
- No Scenarios editing.
- No CAPEX/OPEX/Revenue/Debt/Tax redesign.
