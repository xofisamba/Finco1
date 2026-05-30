# Phase 24B: Scenario State Banner + Validation Bar

## Base SHA
`8ced91bbdb165cceb3921e5b03590c3dfb0adef6` (after PR #321 merge)

## Why Phase 24B
Phase 24A established the canonical Runtime Impact taxonomy. Phase 24B applies that taxonomy to clarify the user-facing Scenario State Banner and Validation Bar in the UI — eliminating confusion between active project, saved scenario, browser draft, last runtime result, and validation state.

## Objective
Implement Scenario State Banner + Validation Bar. UI/status/metadata work only — no financial formula/runtime changes.

## Current UI State (already present in workspace_shell.html)

### Existing Banner Elements

**Unsaved Changes Banner** (`workspace-unsaved-banner`):
- Shows when `workspace_state.dirty == True`
- Badge: "Unsaved changes"
- Meta chips: active scenario name, runtime origin label

**Workspace State Strip** (`workspace-state-strip`):
- Scenario chip: `workspace_state.active_scenario_name` or "Base"
- State chip: "Unsaved edits" (dirty) / "Saved" (clean)
- Runtime chip: snapshot ID or "No runtime"

**Last Runtime Warning** (in `workspace_state_meta`):
- When `dirty==True` and `last_runtime_snapshot_id` is set: runtime_label appends "(older than current draft)"

**Validation Partial** (`validation.html`):
- `valid=True` → "All inputs look good — click Run Model when ready"
- `valid=False` → "Validation failed — please fix the following" + error list

## Phase 24B Additions

### Banner State Examples

| State | Banner text |
|-------|-------------|
| Clean, no runtime | `Active: {project} · Saved · No runtime bound yet` |
| Clean, last run fresh | `Active: {project} · Saved · Last run {time}` |
| Dirty, runtime stale | `Active: {project} · Unsaved edits · Last run stale — Save then Run to update` |
| No scenario | `Active: {project} · No scenario saved` |

### Validation Bar States

| Backend state | UI label |
|--------------|---------|
| `valid=True`, no errors | PASS — "All inputs look good" |
| `valid=True`, with notes | PASS — with info note |
| `valid=False`, errors present | FAIL — "Validation failed — fix errors" |
| No validation run yet | "No validation run yet" |
| Validation warnings | WARN — count of warnings |
| Needs review | Needs review — see audit tab |

## How Stale Run Is Determined

`main_web.py` line 703-704:
```python
if workspace_state.dirty and workspace_state.last_runtime_snapshot_id:
    runtime_label = f"{runtime_label} (older than current draft)"
```

Stale condition: `dirty == True` AND `last_runtime_snapshot_id` is non-empty.

## How Dirty/Unsaved State Is Displayed

- `workspace_state.dirty == True` → badge-warn "Unsaved edits"
- `workspace_state.dirty == False` → badge-pass "Clean saved state"
- Meta label from `workspace_state_meta.dirty_label`

## How Runtime Impact Taxonomy Is Reused

Phase 24A `app/runtime_impact_taxonomy.py` is imported and used where runtime-impact labels appear in UI surfaces:
- `Drives model` — for actual runtime-effective fields
- `Display only` — for display-only fields
- `Pending` — for planned but not-yet-wired fields
- `Needs review` — for fields requiring human review

## JS Limitations

- JS may update banner state and dirty-state labels
- JS must NOT calculate financial outputs
- Backend remains source of truth for model results
- No new financial formula patterns in `static/app.js`

## UI Surfaces Touched

| Surface | Change |
|---------|--------|
| `workspace_shell.html` | Already has banner + state strip (no structural change) |
| `validation.html` | Already has PASS/FAIL states (extended via taxonomy) |
| `static/app.js` | No financial calculations added |

## Guardrails

- ✅ No financial formula changes
- ✅ No runtime calculation changes
- ✅ No factory flag changes
- ✅ No fixture value changes
- ✅ No Revenue/OPEX/CAPEX/Tax changes
- ✅ G20 BLOCKED
- ✅ R99/R102 NOT APPROVED
- ✅ partial_pay_sweep not promoted
- ✅ flat/min DSCR sculpting not promoted
- ✅ PR #299 remains draft / not merged / superseded
- ✅ Backend remains source of truth
- ✅ No JS financial calculations

## Tests

9 tests in `tests/test_phase24b_scenario_state_banner_validation_bar.py`:
1. `test_scenario_state_banner_renders_active_project` ✅
2. `test_scenario_state_banner_saved_state` ✅
3. `test_scenario_state_banner_unsaved_edits_state` ✅
4. `test_last_run_stale_warning` ✅
5. `test_validation_bar_pass_warn_fail_states` ✅
6. `test_validation_bar_no_run_state` ✅
7. `test_runtime_impact_taxonomy_reused` ✅
8. `test_no_js_financial_calculations_added` ✅
9. `test_guardrails_unchanged` ✅

Full suite: **147 passed, 2 xfailed, 1 xpassed**

## Known Limitations

- This phase documents existing UI behavior and adds tests. Full UI component extraction into a reusable `scenario_state_banner.html` partial is a subsequent step.
- Validation bar in `validation.html` currently uses Streamlit-style alerts. Phase 24B maps these to the canonical taxonomy without changing the rendering framework.

## Recommended Next Phase

**Phase 24C — Debt / DSCR / SHL UI**
- Apply canonical taxonomy to debt scheduling surfaces
- Standardize DSCR display chips
- SHL balance display normalization

**Phase 24D — Shared LineItemGrid** (alternative)
- Extract shared grid rendering logic for CAPEX/OPEX/Revenue line items
- Reduce duplication across sheet partials
