# Phase 50C — Residual `/run`, `/compare`, `POST /download` Route Map

## Base SHA
`83d4388f8a6272c2a51b8646a59f6f26cb703358`

## Head SHA
`4ff6b84d6ef86222fdb9f11dfa92da02ca5285b7`

## Purpose
Map what remains in `main_web.py` after Phase 50B/50C scenario state service extraction. This is the pre-characterization map for the next extraction phase. All items listed here are **unmodified by Phase 50B/50C** — they are the residual responsibilities that remain in `main_web.py`.

> This phase is docs only. No production code changed.

---

## `/run` (POST) — Residual Responsibilities

**Line range:** ~1420–1600

```
Request → Form parse → Project/workspace resolution → Runtime guard
         → Model run → KPI formatting → Template render
         → record_workspace_runtime
```

| Step | Function / Inline | Lines | Risk | Notes |
|------|-------------------|-------|------|-------|
| Form parsing | `_collect_form_snapshot` + inline | ~40 | Low | All form fields: project_type, scenario, capacity_mw, tariff, capex, opex, gearing, target_dscr, interest, tenor |
| Project/workspace resolution | Inline in route | ~50 | Medium | `_project_workspace_from_request` — resolves project_record + workspace_state from user + form.active_project |
| Runtime guard | `check_runtime_allowed()` | — | ✅ Done (50C-3) | Wrapped in service |
| Model execution | `run_project()` | — | External | FastAPI dependency, not in main_web.py |
| Demo project fallback | `run_demo_project()` | — | External | Used when no active_project |
| KPI extraction | `result.get("kpis", {})` | — | Low | Dict access + formatting |
| Runtime origin binding | `effective_runtime_origin` from `_resolve_runtime_snapshot_source` | — | ✅ Done (50C-2) | Via thin wrapper |
| Warning propagation | `runtime_warning` | — | ✅ Done (50C-2) | Set in wrapper |
| Template rendering | `templates.TemplateResponse` | — | Low | `kpis.html` partial |
| `record_workspace_runtime` | Repository call inline | — | Medium | Not yet wrapped |
| Session/context update | Inline | ~20 | Low | scenario_name, scenario_provenance updates |

### Inline Helpers Used by `/run`
- `_collect_form_snapshot(form)` — builds dict from form fields
- `_project_workspace_from_request(user, form, project_record, workspace_state)` — inline ~50 lines
- `_resolve_runtime_snapshot_source(user, project, workspace_state, runtime_origin)` — thin wrapper (50C-2)

### Persistence Calls in `/run`
- `record_workspace_runtime(workspace_state, snapshot, scenario_name, scenario_provenance, warning_note)` — after model run, before template render

---

## `/compare` (POST) — Residual Responsibilities

**Line range:** ~1500–1750

```
Request → Form parse → Project/workspace resolution → Runtime guard
         → Multi-scenario run → Comparison table build → Template render
         → record_workspace_runtime
```

| Step | Function / Inline | Lines | Risk | Notes |
|------|-------------------|-------|------|-------|
| Form parsing | Inline | ~20 | Low | scenario_a, scenario_b selection |
| Project/workspace resolution | Inline | ~50 | Medium | Same as `/run` — `_project_workspace_from_request` |
| Runtime guard | `check_runtime_allowed()` | — | ✅ Done (50C-3) | Wrapped in service |
| Multi-scenario run | `compare_scenarios()` | — | External | Repository call |
| Comparison table | Inline template logic | ~100 | Low | Jinja2 rendering of diff table |
| Template rendering | `templates.TemplateResponse` | — | Low | `compare_results.html` |
| `record_workspace_runtime` | Repository call | — | Medium | Same as `/run` |

### Persistence Calls in `/compare`
- `record_workspace_runtime` — called per scenario compared

---

## `POST /download` — Residual Responsibilities

**Line range:** ~2000–2150

```
Request → Form parse → Project/workspace resolution → Runtime guard
         → Export service call → Audit service call → Template render
```

| Step | Function / Inline | Lines | Risk | Notes |
|------|-------------------|-------|------|-------|
| Form parsing | Inline | ~10 | Low | scenario, project_type, capacity, tariff, etc. |
| Project/workspace resolution | Inline | ~50 | Medium | Same as `/run` — `_project_workspace_from_request` |
| Runtime guard | `check_runtime_allowed()` (2 call sites) | — | ✅ Done (50C-3) | Guard check + origin check |
| Export service | `build_excel_export_for_post_request()` | — | ✅ Done (Phase 49) | In export_service.py |
| Audit service | `record_download_export()` | — | ✅ Done (Phase 49D-3D) | In export_audit_service.py |
| Template rendering | `templates.TemplateResponse` | — | Low | `download.html` |

### Persistence Calls in `POST /download`
- None directly — audit is handled by `record_download_export()`

---

## Shared / Cross-Cutting Responsibilities

### `_project_workspace_from_request` (Inline — ~50 lines)
Used at the top of `/run`, `/compare`, `POST /download`. Resolves:
- `project_record` — from `get_project_record()` or factory (`create_default_tuho_wind1`, etc.)
- `workspace_state` — from `get_workspace_state()`
- `active_project` — from form field
- `project_type` — normalized from form/project

**Risk for extraction: Medium** — has branching logic for `active_project` and factory selection.

### `_collect_form_snapshot` (Inline — ~40 lines)
Builds a flat dict from all form fields. Returns the "raw" snapshot before setdefault enrichment.

**Risk for extraction: Low** — pure transformation, no branching.

### `record_workspace_runtime`
Called after every model run (`/run`, `/compare`). Persists runtime metadata.

**Risk for extraction: Medium** — needs to remain near the model execution point to capture correct timing.

---

## Persistence Calls Still in `main_web.py`

| Function | Where Used |
|----------|-----------|
| `record_workspace_runtime` | `/run`, `/compare` |
| `get_workspace_state` | Inline in all 3 routes |
| `get_project_record` | Inline in all 3 routes |
| `save_workspace_state` | `/scenario/save`, `/run` |
| `save_scenario` | `/scenario/save` |
| `add_scenario` | `/scenario/save` |
| `bind_workspace_to_scenario` | `/scenario/save` |
| `discard_workspace_draft` | `/scenario/discard` |
| `duplicate_scenario` | `/scenario/duplicate` |
| `rename_scenario` | `/scenario/rename` |
| `archive_scenario` | `/scenario/archive` |
| `promote_scenario_to_base_case` | `/scenario/promote` |
| `select_scenario` | `/scenario/select` |
| `update_scenario_last_run_summary` | `/run` after model run |

---

## Scenario CRUD Endpoints (Still Fully in `main_web.py`)

| Endpoint | Method | Lines | Complexity |
|----------|--------|-------|------------|
| `/scenario/save` | POST | ~60 | Medium |
| `/scenario/load` | GET | ~30 | Low |
| `/scenario/delete` | POST | ~20 | Low |
| `/scenario/discard` | POST | ~15 | Low |
| `/scenario/duplicate` | POST | ~20 | Low |
| `/scenario/rename` | POST | ~20 | Low |
| `/scenario/archive` | POST | ~20 | Low |
| `/scenario/promote` | POST | ~25 | Medium |
| `/scenario/select` | POST | ~15 | Low |

---

## Recommended Extraction Order

| Priority | Candidate | Risk | Rationale |
|----------|-----------|------|-----------|
| 1 | `_project_workspace_from_request` extraction | Medium | Used by all 3 routes, ~50 lines, moderate branching |
| 2 | Form snapshot builder (`_collect_form_snapshot` + `build_projectinputs` chain) | Low | Pure transformation, no branching, used by all 3 routes |
| 3 | `record_workspace_runtime` wrapper in scenario_state_service | Medium | Called after model run, needs correct timing |
| 4 | `/run` KPI formatting extraction | Low | `kpis.html` context building — ~30 lines |
| 5 | `/run` route characterization | High | Full characterization needed before any orchestration extraction |
| 6 | `/compare` service characterization | Medium | Less orchestration than `/run` |

---

## Risk Legend

| Level | Meaning |
|-------|---------|
| **Low** | Pure transformation, no branching, no side effects |
| **Medium** | Has branching or modest side effects |
| **High** | Significant orchestration, many branches, timing-sensitive |