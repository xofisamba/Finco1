# Phase 24A: UI/Runtime Impact Taxonomy

## Base SHA
`78f785366482c93efc0ea0e6f058ec4a7833a3be` (after PR #320 merge)

## Why Phase 24A
Phase 23U confirmed backend parity is fully characterized for the current frozen senior DS path. With TUHO and Oborovo debt/DSCR/SHL/distribution backend behavior now stable, the UI taxonomy can be safely normalized without changing model behavior.

## Objective
Standardize UI/runtime impact taxonomy across FincoGPT input and output surfaces. This phase is UI/metadata/documentation focused — no formula/runtime changes.

##4-State Canonical Taxonomy

### Primary States

| State | Definition |
|-------|-----------|
| **Drives model** | Input is runtime-effective and directly affects calculation outputs. User should understand changes alter model results. |
| **Display only** | Field is visible/reference/displayed but does not currently affect runtime calculations. User should not expect formula impact. |
| **Pending** | Field/section is planned or captured but not yet wired. Could become runtime-effective in a later phase. |
| **Needs review** | Field/section has ambiguous mapping, unresolved source issue, validation concern, or requires human/model review before being trusted. |

### Sub-reasons (tooltip/helper text only)

| Key | Text |
|-----|------|
| `timing_only` | Timing only — used for construction draw/timing only, not IDC runtime |
| `reference_only` | Reference only — shown for reference, not runtime-effective |
| `pending_treatment` | Pending treatment — captured but not yet wired to runtime |
| `pending_runtime_source` | Pending runtime source — runtime source not yet connected |
| `not_comparable` | Not comparable — scope mismatch prevents direct comparison |
| `deferred` | Deferred — intentionally deferred to a later phase |
| `not_applicable` | Not applicable — does not apply to this project/scenario |
| `fixture_backed` | Fixture-backed — value from fixture CSV, not runtime solver |
| `frozen_schedule` | Frozen schedule — frozen per-period value, not computed |
| `source_locked` | Source locked — from Excel calibration, locked |
| `validation_warning` | Validation warning — field has a validation concern |
| `excel_parity_known_gap` | Excel parity known gap — known difference from Excel, documented |

## Legacy Label Mapping

| Legacy label | Canonical state |
|-------------|----------------|
| `Drives model` | Drives model |
| `backend_authoritative` | Drives model |
| `Timing only` | Display only |
| `Reference only` | Display only |
| `Display only` | Display only |
| `Not applicable` | Display only |
| `Pending treatment` | Pending |
| `Pending runtime source` | Pending |
| `Deferred` | Pending |
| `Not comparable` | Needs review |
| `Needs review` | Needs review |
| `mismatch` | Needs review |
| `scope_mismatch` | Needs review |
| `Unknown` | Needs review |

## Section-by-Section Classification

### Revenue
- **Primary status**: Drives model
- PPA price, production, CO2 certificates, balancing — all runtime-effective
- Sub-reason: none needed

### OPEX
- **Primary status**: Drives model
- All OPEX lines are runtime-effective (affect CFADS/EBITDA)
- Sub-reason: none needed

### CAPEX
- **Primary status**: Display only / Pending (Phase 21 is display/schema only)
- C.16 Project Rights: **Pending** (not runtime-effective)
- M1-M18 schedule: **Display only** (timing-only, not IDC runtime)
- EPC/Grid totals (aggregate_total scope): **Drives model** (real CAPEX total)

### Debt / Senior DS
- **Primary status**: Drives model
- TUHO: Fixture-backed frozen schedule — sub-reason: "Fixture-backed frozen schedule"
- Oborovo: Fixture-backed frozen schedule — sub-reason: "Fixture-backed frozen schedule"
- **No solver/sculpting claim** — frozen path is backward-computed, not sculpted

### SHL / Distribution
- **Primary status**: Drives model
- SHL PIK/sweep and distribution lock-up are runtime-effective
- Sub-reason: none needed

### Tax
- **Primary status**: Drives model (if runtime-effective)
- Pending/future tax treatment: **Pending** or **Needs review**
- Tax fields only marked Drives model if actually wired

### Scenario / Validation / Audit
- Calibration reconciliation fields: **Needs review** or **Display only**
- Audit-only fields: **Display only**

## Frozen Senior DS Treatment

TUHO and Oborovo senior debt schedule surfaces:

| Property | Value |
|----------|-------|
| Primary state | Drives model |
| Sub-reason | "Fixture-backed frozen schedule" |
| Sculpting active | **false** |
| Note | "Fixture-backed frozen schedule — DSCR is backward-computed from frozen service" |

**Do NOT claim solver/sculpting is active** — the frozen path uses backward-computed DSCR from a fixture-backed schedule, not a forward sculpting solver.

## Guardrails

- ✅ No financial formula changes
- ✅ No runtime calculation changes
- ✅ No factory flag changes
- ✅ No fixture value changes
- ✅ No senior debt sizing logic changes
- ✅ No SHL/distribution logic changes
- ✅ No Revenue/OPEX/CAPEX/Tax changes
- ✅ G20 BLOCKED
- ✅ R99/R102 NOT APPROVED
- ✅ partial_pay_sweep not promoted
- ✅ flat/min DSCR sculpting not promoted
- ✅ PR #299 remains draft / not merged / superseded
- ✅ Backend remains source of truth
- ✅ No JS financial calculations

## Tests

7 tests in `tests/test_phase24a_ui_runtime_impact_taxonomy.py`:
1. `test_runtime_impact_primary_states_are_canonical` ✅
2. `test_legacy_runtime_impact_labels_map_to_canonical_states` ✅
3. `test_frozen_senior_ds_surface_drives_model_with_fixture_subreason` ✅
4. `test_capex_runtime_impact_not_promoted` ✅
5. `test_no_financial_runtime_changes` ✅
6. `test_no_unknown_primary_runtime_impact_labels_in_templates` ✅
7. `test_guardrails_unchanged` ✅

Full suite: **138 passed, 2 xfailed, 1 xpassed**

## New Module

`app/runtime_impact_taxonomy.py` — canonical taxonomy source of truth:
- `RuntimeImpactStatus` enum (4 canonical states)
- `CANONICAL_STATES` tuple
- `SUB_REASONS` dict
- `LEGACY_TO_CANONICAL` mapping
- `map_legacy_to_canonical()` function
- `get_sub_reason()` function
- `get_frozen_senior_ds_taxonomy()` helper
- `get_capex_taxonomy()` helper

## Known Limitations

- This phase establishes the taxonomy and documents current state. Full UI label standardization across all surfaces is a subsequent effort.
- `_derive_runtime_impact_label` in `project_context.py` uses legacy labels internally — mapping to canonical states is done at the taxonomy module level.
- JS display-only label updates are out of scope for this phase.

## Recommended Next Phase

**Phase 24B — Scenario State Banner + Validation Bar**
- Add a consistent runtime impact indicator to scenario/project selection surfaces
- Standardize validation status bar across pages
- Distinguish Drives model vs Display only vs Pending vs Needs review at point of display

**Phase 24C — Debt / DSCR / SHL UI** (alternative)
- Apply taxonomy to debt scheduling surfaces
- Standardize DSCR display chips
- SHL balance display normalization
