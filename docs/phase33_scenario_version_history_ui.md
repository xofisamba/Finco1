# Phase 33 — Scenario Version History UI

**Branch:** `phase33-scenario-version-history-ui`
**Base SHA:** `5ec5df54079115fe241932ed831045a4f138173a` (after PR #344 Phase 32)
**Date:** 2026-05-31
**Status:** UI wiring — no runtime formula changes

---

## 1. Scope & Objective

Expose existing scenario versioning/history capabilities in a lightweight UI surface in the workspace sidebar.
No new persistence schema. No financial model changes. No formula/runtime changes.

---

## 2. Phase 32 Recap

Phase 32 confirmed existing persistence already supports scenario versioning:

- Stable `scenario_id` (UUID hex, immutable) ✅
- `created_at` / `updated_at` timestamps ✅
- Named scenario snapshots ✅
- `snapshot_json` (full input state) ✅
- Base/override separation ✅
- `list_scenarios()` ordered by `updated_at DESC` ✅
- `get_scenario(scenario_id)` load by ID ✅
- `get_scenario_history()` including archived ✅
- `compare_scenarios()` for governance-aware comparison ✅
- Draft/saved/runtime distinction in `workspace_states` ✅
- Run snapshots in `runs` table ✅

**No new persistence implementation needed.** Phase 33 wires existing capabilities to the UI.

---

## 3. UI Surface Added

### 3.1 New Partial: `scenario_version_history.html`

Added at `app/templates/partials/scenario_version_history.html`.

**Content:**
- Heading: "Saved Versions — preserve input snapshots"
- Version list showing scenario cards (scenario name, active badge, updated timestamp, project code, equity IRR if available, governance badges)
- Draft/Saved/Runtime explainer (3-item bullet list)
- Stale runtime warning (shown when `workspace_state.dirty == 1`)

### 3.2 Wiring

Included in `scenario_workspace.html` (sidebar) — only for user projects (`is_user_project == True`).

No new endpoints. No new schema. No JS financial calculations.

---

## 4. Existing Capabilities Reused

| Capability | Source |
|------------|--------|
| `scenario_summary_cards` | `_current_project_workspace()` → passed to template |
| Active scenario ID | `workspace_state.active_scenario_id` |
| Dirty/draft state | `workspace_state.dirty` |
| Scenario name + updated_at | `card.scenario_name`, `card.updated_at` |
| Project code | `card.project_code` |
| Last run KPIs (IRR) | `card.equity_irr` |
| Governance state | `card.governance_state` (G20/R99/R102) |
| List of saved scenarios | `scenario_summary_cards` (already populated in `_workspace_refresh_payload`) |

---

## 5. Draft / Saved / Runtime Semantics

### Draft
- Unsaved form edits stored in `workspace_states.draft_snapshot_json`
- Not yet part of any saved version
- Does not affect Run output until saved

### Saved
- Each explicit Save creates a **new immutable row** with a new `scenario_id`
- Older versions remain accessible — never overwritten
- Scenario name, timestamp, and input snapshot are preserved

### Runtime
- `workspace_states.last_runtime_snapshot_json` stores last model run result
- Reflects the inputs that were active at time of last Run
- May be stale if draft was edited after last Run
- **Stale warning shown** when `dirty == 1`

---

## 6. Endpoints Used

No new endpoints added. The following existing endpoints power the UI:

| Endpoint | Purpose |
|----------|---------|
| `GET /scenarios` | Loads scenario list + `scenario_summary_cards` |
| `POST /scenarios/save` | Creates new scenario version (INSERT, never overwrite) |
| `GET /scenarios/{id}/load` | Loads specific scenario by ID |
| `POST /scenarios/{id}/select` | Sets active scenario |
| `GET /scenarios/history` | Refreshes history and lineage |
| `GET /scenarios/compare` | Governance-aware scenario comparison |

---

## 7. Out-of-Scope

| Feature | Reason |
|---------|--------|
| New schema migration | Phase 32 confirmed none needed |
| JS financial calculations | Not needed — backend is authoritative |
| Complex version browser | Out of scope — lightweight exposure only |
| Scenario branching UI | Nice-to-have, deferred |
| Multi-user auth | Out of scope — single-user pilot |
| Bank/lender/audit/certification claims | Not applicable |

---

## 8. Limitations

1. **Version list is read-only** — the partial shows saved versions but does not include load/restore buttons (existing `/scenarios/{id}/load` endpoint handles that)
2. **Stale runtime warning is basic** — shown when `dirty==1`, no deeper delta detection
3. **No version diff UI** — use `/scenarios/compare` for that
4. **Generic projects remain exploratory** — no validation status change implied

---

## 9. Guardrails

- ✅ No financial formula changes
- ✅ No runtime calculations
- ✅ No model output changes
- ✅ No project factory changes
- ✅ No fixture CSVs changed
- ✅ No TUHO/Oborovo validation behavior changes
- ✅ No senior debt sizing logic changes
- ✅ No DSCR/sculpting logic changes
- ✅ No SHL/distribution logic changes
- ✅ No Revenue/OPEX/CAPEX/Tax formula changes
- ✅ No JS financial calculations added
- ✅ No new schema migration
- ✅ G20 BLOCKED (unchanged)
- ✅ R99/R102 NOT APPROVED (unchanged)
- ✅ partial_pay_sweep not promoted
- ✅ flat/min DSCR sculpting not promoted
- ✅ Backend remains source of truth
- ✅ No lender/bank/audit/SaaS/certification claims

---

## 10. Recommended Next Phase

**Phase 34** — Generic Project Path Full Validation:
- TUHO frozen path: validated ✅
- Oborovo frozen path: validated ✅
- Generic solar/wind: **unvalidated** — next priority

---

## 11. Phase 33 Finding

**Classification: UI WIRING — EXISTING CAPABILITIES EXPOSED**

The version history UI is purely informational — it surfaces existing scenario versioning data that was already available via the backend. No new persistence, no financial changes, no new endpoints required.

**Phase 33D fix: NOT REQUIRED** — implementation is minimal and uses only existing endpoints.