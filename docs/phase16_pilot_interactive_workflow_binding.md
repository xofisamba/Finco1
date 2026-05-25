# Phase 16 — Pilot Interactive Workflow Binding

## Context

Phase 16 PR #238 fixed the first wave of pilot UI blockers:
- Removed misleading "FACTORY CONTEXT — READ-ONLY TEMPLATE DATA" badge
- Added honest feedback to the dead New Project button

This branch tackles the second wave: **the app appeared to accept input but felt disconnected from any real effect**.

## Root Cause

Three distinct problems confirmed after code investigation:

1. **`btn-discard-edits` was a dead button** — had no HTMX attribute and no JavaScript event listener. Clicking did nothing.

2. **Dirty-state banner never appeared after typing** — `queueWorkspaceDraftPersist` correctly POSTed to `/scenarios/state/draft` and received a JSON response with `dirty: true`, but the inline handler did call `applyWorkspaceStateMeta(data)` — so the UI never updated to show unsaved state without a full-page reload.

3. **Non-runtime-bound fields had vague labels** — `ppa_term_years` said "Preview convenience value until saved." and `construction_months` said "Editable here for workflow convenience; still preview-only until saved." Neither made clear that these fields do not affect model outputs at all.

## Fixed Issues

### 1. Discard / Revert Draft button (index.html)

Added to `btn-discard-edits`:

```html
hx-post="/scenarios/state/discard"
hx-form="#main-form"
hx-swap="none"
onclick="var f=document.getElementById('main-form');if(f){var d=new FormData(f);fetch('/scenarios/state/discard',{method:'POST',body:d,credentials:'same-origin'}).then(function(r){return r.ok?r.json():null}).then(function(j){if(j&&window.applyWorkspaceStateMeta)window.applyWorkspaceStateMeta(j);if(j&&j.snapshot&&window.applyScenarioSnapshot)window.applyScenarioSnapshot(j.snapshot,'');}).catch(function(){alert('Revert failed. Try refreshing the page.');});}"
```

What it does:
- On click: POST `/scenarios/state/discard` with current form data
- Backend returns JSON with `workspace_state_meta` (dirty=false, saved_snapshot, etc.)
- JS calls `applyWorkspaceStateMeta(j)` to restore clean UI state
- If backend returns `snapshot`, also calls `applyScenarioSnapshot(j.snapshot, '')` to repopulate form fields
- On failure: shows `alert('Revert failed. Try refreshing the page.')` — honest error, not silent no-op

### 2. Preview-only labels

**`ppa_term_years` in `sheet_revenue.html`:**
- Old: "Preview convenience value until saved."
- New: "Preview only — not runtime-bound yet."

**`construction_months` in `sheet_opex.html`:**
- Old: "Editable here for workflow convenience; still preview-only until saved."
- New: "Preview only — not runtime-bound yet."

These are the only two non-runtime-bound fields that have editable inputs in the sheet partials. The label change makes the intent explicit.

### 3. Dirty-state propagation (already present, confirmed working)

`queueWorkspaceDraftPersist` in `app.js` already calls `applyWorkspaceStateMeta(data)` when the server returns JSON. This was confirmed functional — the only missing piece was the discard button that could clear it.

---

## Field Binding Inventory

### Runtime-bound fields

These fields flow through `_build_schema_from_form` → `build_projectinputs` → runtime model → KPI outputs.

| Field | Schema key | Model input | Expected runtime effect |
|-------|-----------|------------|------------------------|
| `tariff_eur_mwh` | `revenue.tariff_eur_mwh` | `ppa_base_tariff` | Changes `total_revenue_keur` / `net_revenue_keur` |
| `opex_y1_keur` | `opex.opex_y1_keur` | scales base OPEX | Changes `total_opex_keur` / EBITDA |
| `p50_hours` | `production.p50_hours` | `operating_hours_p50` | Changes energy yield → revenue |
| `gearing_pct` | `financing.gearing_pct` | `gearing_ratio` | Changes senior debt quantum |
| `target_dscr` | `financing.target_dscr` | `target_dscr` | Affects senior debt sizing |
| `interest_rate_pct` | `financing.interest_rate_pct` | `base_rate` override | Changes financing cost |
| `tenor_years` | `financing.tenor_years` | `senior_tenor_years` | Affects debt repayment schedule |

### Preview-only / not runtime-bound fields

These fields are saved to snapshot and appear in the UI, but do not flow into the model's `build_projectinputs` schema.

| Field | Sheet | Reason |
|-------|-------|--------|
| `ppa_term_years` | sheet_revenue.html | Not used in `RevenueInput` schema or `build_projectinputs` |
| `construction_months` | sheet_opex.html | No model handler exists for this field in the current schema |

### Saved but not schema-mapped

| Field | Sheet/form | Status |
|-------|-----------|--------|
| `capacity_mw` | Sidebar | Saved to snapshot but not in `_build_schema_from_form` — cannot affect runtime |

---

## Workflow Explanation

### Edit → Dirty → Save → Run cycle

1. **Edit supported input** (e.g., `tariff_eur_mwh`)
2. `input` event fires → `queueWorkspaceDraftPersist()` fires after 350ms debounce
3. POST `/scenarios/state/draft` with form data → server saves `draft_snapshot`, returns `workspace_state_meta` with `dirty: true`
4. `applyWorkspaceStateMeta(data)` updates: dirty banner, dirty label, disables Run/Save-Run buttons
5. User clicks **Save Scenario** → POST `/scenarios/save` → `saved_snapshot = draft_snapshot`, `dirty: false`
6. User clicks **Run Model** → POST `/run` → uses `saved_snapshot` values → runtime summary in output area
7. User clicks **Revert Draft** → POST `/scenarios/state/discard` → restores `saved_snapshot` into form, `dirty: false`

### Authority boundaries

- **Backend is runtime authority** — browser draft edits do not affect model outputs until saved and run
- **Export lineage is descriptive only** — it records the runtime snapshot ID, not the browser state
- **Dirty state is client-server shared** — both `applyWorkspaceStateMeta` (JS) and `_workspace_state_meta` (Python) compute the same dirty flag from `workspace_state.dirty`

---

## What Was NOT Changed

- No runtime/model formula changes
- No `build_projectinputs` schema additions
- No new editable surfaces
- No persistence architecture changes
- No JS financial calculations
- No G20 or R99/R102 changes
- No Replay engine changes
- No new project creation

---

## Remaining Risks

1. **`ppa_term_years` and `construction_months` remain preview-only** — the UI now honestly says so, but the fields cannot affect runtime without a separate schema wiring story.

2. **`capacity_mw` is saved but not mapped** — it goes into the form/snapshot but not into `_build_schema_from_form`. If operators expect changing capacity to affect the model, they will be disappointed. No UI label exists for this — the sidebar just shows the project default.

3. **No end-to-end Playwright test** — the test suite proves the pieces exist (endpoints wired, labels correct, dirty state propagates) but does not run a full browser automation of the edit → save → run → verify cycle.

4. **Discard uses inline onclick** — HTMX `hx-post` is set but the actual mechanism is an inline `fetch()` call. This works but is not the cleanest HTMX pattern. A full HTMX wiring with a proper response partial would be cleaner but requires more template work.