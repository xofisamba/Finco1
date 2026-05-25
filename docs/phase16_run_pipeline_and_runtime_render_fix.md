# Phase 16 — Run Pipeline and Runtime Render Fix

## Context

After PRs #238, #239, and CSP fix, the live app still didn't work as interactive scenario model. Operator could edit fields, dirty state appeared, but:
- Run Model did not visibly generate runtime output
- Sheet summaries showed factory values, not runtime output
- `/run` likely crashed with `NameError`

Claude forensic review identified root causes:
1. `/run` endpoint referenced undefined variables (`snapshot`, `project_record`, `project_code`, `workspace_state`, `runtime_origin`) in the `active_project in ("tuho", "oborovo")` branch
2. Duplicate `id="btn-run-model"` — base.html had inert button, index.html had HTMX button
3. Sheet summary cards used static `project_ctx.*` (factory reference), not runtime output
4. `form-data-json` was empty → `applyScenarioSnapshot` received `{}` → form never populated from saved snapshot

## Fixes Applied

### 1. `/run` variable setup (main_web.py)

**Root cause:** The `active_project in ("tuho", "oborovo")` branch referenced `snapshot`, `project_record`, `project_code`, `workspace_state`, `runtime_origin` before they were defined.

**Fix:** Moved variable setup before branching, with dirty guard:

```python
form = await request.form()
# -- Phase 16 fix: establish all required variables before any branching --
snapshot = _collect_form_snapshot(form)
active_project = form.get("active_project", "").strip().lower()
# ... all form fields extracted ...
project_code, project_name = _project_persistence_metadata(None, snapshot)
project_record = save_project(...)
workspace_state = get_workspace_state(...)
allow_run, runtime_origin, guard_message = runtime_guard_for_snapshot(workspace_state, snapshot)

# Dirty guard — block run if dirty, do not auto-save
if not allow_run:
    return templates.TemplateResponse(
        request=request,
        name="partials/errors.html",
        context={"errors": [guard_message]},
    )
```

### 2. Run Model button wiring (base.html)

**Root cause:** Duplicate `id="btn-run-model"` — one inert in base.html sidebar, one HTMX in index.html. `document.getElementById` would bind one of them.

**Fix:** Renamed sidebar button to `id="btn-run-model-sidebar"` and added `disabled` + title. The index.html button (`hx-post="/run"`) remains the active one.

```html
<!-- Before: id="btn-run-model" (duplicate, no hx-post) -->
<!-- After: -->
<button id="btn-run-model-sidebar" type="button" disabled
        title="Run is disabled when workspace has unsaved draft edits. Save or revert first.">
  Run Model
</button>
```

### 3. Static sheet summaries labeled as factory reference (sheet_revenue.html)

**Root cause:** `project_ctx.ppa_tariff_eur_mwh` displayed without indicating it's a static factory reference, not runtime output.

**Fix:** Added `assumption-grid--reference` class and per-item `assumption-item--reference` class, plus `factory reference` badge to indicate these are not live runtime values.

```html
<div class="assumption-grid assumption-grid--reference">
  <div class="assumption-item assumption-item--reference">
    <span class="metric-label">PPA Tariff (Y1) <span class="badge badge-preview" style="font-size:0.6rem;">factory reference</span></span>
    <span class="metric-value">{{ project_ctx.ppa_tariff_eur_mwh }} EUR/MWh</span>
  </div>
  ...
</div>
```

## Known Remaining Issues

1. **Form never populated from saved snapshot** — `applyScenarioSnapshot` receives `{}` because `form-data-json` is empty. This is a separate persistence population bug that blocks the full save→load→run chain.
2. **Standard form-based run** (`active_project` not set) still has the variable setup at the top but uses the same block-level variables.
3. **No runtime delta proof test** — integration test showing tariff 60→100 changes revenue has not yet been run live.

## Files Changed

- `main_web.py` — `/run` variable setup, dirty guard
- `app/templates/base.html` — renamed duplicate btn-run-model
- `app/templates/partials/sheet_revenue.html` — labeled factory reference values

## References

- `reports/phase16_run_pipeline_breakpoint_matrix.csv`
- `reports/phase16_run_button_wiring_matrix.csv`
- `reports/phase16_runtime_render_binding_matrix.csv`
- `reports/phase16_runtime_delta_proof_matrix.csv`
- `reports/phase16_run_pipeline_remaining_gaps.csv`