# Phase 49D-1 — POST /download Route Characterization

**Branch:** `phase49d1-characterize-post-download-before-extraction`
**Base SHA:** `f6e53d5633858f0bd0aace8df77e34d28620f61d`
**Route:** `POST /download` (main_web.py:2054)
**Phase:** 49D-1 (pre-extraction characterization — no refactoring)

---

## 1. Route Location and Responsibilities

**File:** `main_web.py`
**Line:** 2054
**Function:** `async def download_post(request: Request)`
**Route:** `POST /download`

**Responsibilities:**
1. Parse 12 form fields from request body
2. Resolve project record + workspace state from snapshot
3. Determine runtime origin path (factory vs user_created vs saved_state vs saved_baseline)
4. Run model with appropriate inputs override
5. Build provenance metadata with scenario/runtime details
6. Generate Excel bytes with provenance
7. Record export event in database
8. Return StreamingResponse with XLSX bytes

---

## 2. Form Fields Parsed

| Field | Type | Notes |
|-------|------|-------|
| `project_type` | str | e.g. "Solar", "Wind" |
| `scenario` | str | e.g. "Base", "Downside", "Upside" |
| `capacity_mw` | str | |
| `tariff_eur_mwh` | str | |
| `p50_hours` | str | |
| `total_capex_keur` | str | |
| `opex_y1_keur` | str | |
| `gearing_pct` | str | |
| `target_dscr` | str | |
| `interest_rate_pct` | str | |
| `tenor_years` | str | |

---

## 3. Scenario/Project Source Paths

### Path A: `user_created` project_origin
**Condition:** `project_record.project_origin == "user_created"`

Steps:
1. Call `runtime_guard_for_snapshot(workspace_state, snapshot)` → `(allow_run, runtime_origin, guard_message)`
2. If `not allow_run` → return 400 HTML error with `guard_message`
3. Call `_resolve_runtime_snapshot_source(user, project_record, workspace_state, runtime_origin)`
   → returns `(runtime_snapshot, active_scenario_record, runtime_warning, effective_runtime_origin)`
4. Set `override = build_projectinputs_from_snapshot(runtime_snapshot)`
5. Set `runtime_project_key = "Solar" if _canonical_project_type(effective_project_type) == "Solar" else "Wind"`

**Helpers used:** `runtime_guard_for_snapshot`, `_resolve_runtime_snapshot_source`, `build_projectinputs_from_snapshot`, `_canonical_project_type`

---

### Path B: `saved_state` runtime_origin
**Condition:** `project_record.project_origin != "user_created"` AND `runtime_guard_for_snapshot(workspace_state, snapshot)[1] == "saved_state"` AND `workspace_state.active_scenario_id` is truthy

Steps:
1. Set `runtime_origin = "saved_state"`
2. Call `_resolve_runtime_snapshot_source(...)` → `(runtime_snapshot, active_scenario_record, runtime_warning, effective_runtime_origin)`
3. Set `override = build_projectinputs_from_snapshot(runtime_snapshot)`
4. `runtime_seed = _normalize_template_source(project_record.template_source or project_record.source_project_template, effective_project_type)`
5. `runtime_project_key` from `runtime_seed` ("TUHO", "Oborovo", or "Solar"/"Wind")

---

### Path C: `saved_baseline` project_origin
**Condition:** `project_record.project_origin == "saved_baseline"` (after Excel bytes are built)

Effect:
- Sets `replay_metadata["baseline_source"] = True` after `build_excel_export()`
- Does NOT change `runtime_origin` (stays "factory_base_runtime" or whatever was set)

---

### Path D: `factory_base_runtime` (default fallback)
**Condition:** None of the above paths match

Steps:
1. Set `runtime_origin = "factory_base_runtime"`
2. `override = build_projectinputs(schema)` — from form fields (not snapshot)
3. `runtime_seed = _normalize_template_source(...)` → determines `runtime_project_key`

---

## 4. Runtime Snapshot Source Paths

| Path | Snapshot Source | Override Source | `runtime_origin` |
|------|----------------|-----------------|-----------------|
| `user_created` | `_resolve_runtime_snapshot_source()` | `build_projectinputs_from_snapshot(runtime_snapshot)` | `"factory_base_runtime"` (passed in, may be overridden) |
| `saved_state` | `_resolve_runtime_snapshot_source()` | `build_projectinputs_from_snapshot(runtime_snapshot)` | `"saved_state"` |
| `saved_baseline` | N/A | Form schema (via Path D) | `"factory_base_runtime"` (from Path D) |
| `factory_base_runtime` | N/A | Form schema via `build_projectinputs(schema)` | `"factory_base_runtime"` |

---

## 5. Provenance Metadata Paths

`replay_metadata = _replay_metadata_for_project(...)` is called with these key arguments:

| Field | Source | Notes |
|-------|--------|-------|
| `project_code` | `project_record.project_code` | |
| `export_type` | `"excel_model_export"` | |
| `workbook_type` | `"values_only_excel_export"` | |
| `export_timestamp` | `utc_now_iso()` | Current time |
| `runtime_timestamp` | `utc_now_iso()` | Current time (same as export) |
| `project_id` | `project_record.project_id` | |
| `scenario_id` | `workspace_state.active_scenario_id` if `runtime_origin == "saved_state"` else `None` | |
| `scenario_name` | `active_scenario_record.scenario_name` if `active_scenario_record` else `scenario` | |
| `runtime_origin` | Path-dependent string | |
| `artifact_name` | `filename` | |
| `project_inputs_override` | `demo.project_inputs` | Result inputs |
| `template_origin_override` | `"saved_project_assumptions"` if `user_created` else `None` | |
| `active_scenario_id` | `workspace_state.active_scenario_id` if `runtime_origin == "saved_state"` else `None` | |
| `active_scenario_name` | `workspace_state.active_scenario_name` if `runtime_origin == "saved_state"` else `None` | |
| `scenario_provenance` | `_scenario_provenance_for_record(project_record, active_scenario_record)` | |
| `warning_note` | `runtime_warning` | From `_resolve_runtime_snapshot_source` |

---

## 6. Error Paths

| Error | Cause | Response | Status |
|-------|-------|----------|--------|
| Form validation | `build_projectinputs(schema)` raises `ValueError` | HTML error page | 400 |
| Runtime guard blocked | `runtime_guard_for_snapshot` returns `allow_run=False` | HTML error with `guard_message` | 400 |
| Unknown exception | Any `Exception` in try block | HTML error page | 500 |

---

## 7. Export Recording Behavior

After Excel bytes are built, `record_export()` is called:

```python
record_export(
    user_id=user.user_id,
    project_code=project_code,
    export_type="excel_model_export",
    artifact_name=filename,
    artifact_path=f"/download?project_type={project_type}&scenario={scenario}",
    project_id=project_record.project_id if project_record else None,
    scenario_id=active_scenario_record.scenario_id if active_scenario_record else None,
    governance_state=_governance_snapshot(project_code),
    replay_metadata=replay_metadata,
)
```

`record_export` is **always called** on success, regardless of path.

---

## 8. Response Behavior

On success:
- `StreamingResponse(iter([excel_bytes]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")`
- Headers: `Content-Disposition: attachment; filename="fincogpt_{project_type.lower()}_{scenario.lower()}.xlsx"`, `Content-Length: <len>`

On form validation error: `HTMLResponse` status 400
On runtime guard blocked: `HTMLResponse` status 400
On unknown exception: `HTMLResponse` status 500

---

## 9. Extraction Risks for Phase 49D-2

| Risk | Severity | Mitigation |
|------|----------|------------|
| `build_projectinputs` vs `build_projectinputs_from_snapshot` conditional | High | Both paths must be preserved exactly |
| `runtime_origin` path-dependent metadata fields | High | All conditional fields in `replay_metadata` must be captured per path |
| `_resolve_runtime_snapshot_source` side effects | Medium | Function has observable side effects on `runtime_warning` and `active_scenario_record` |
| `record_export` after Excel generation | Medium | Must stay in route or be called with exact same fields |
| `baseline_source` flag only set on `saved_baseline` path | Low | Clear conditional behavior |
| Auth check at top of route | Low | Simple redirect, easy to preserve |

---

## 10. Required 49D-2 Extraction Contract

Before extraction, the service function must accept:

```python
def build_excel_export_for_post_request(
    result,
    project_inputs,
    project_type: str,
    scenario: str,
    project_record,
    runtime_origin: str,
    replay_metadata: dict,
    *,
    baseline_source: bool = False,
) -> ExportResponse
```

The route must:
1. Compute `replay_metadata` **before** calling the service
2. Call the service with `(demo.result, demo.project_inputs, project_type, scenario, project_record, runtime_origin, replay_metadata, baseline_source=...)`
3. Call `record_export` **after** the service returns (with the same `replay_metadata`)
4. Return the `StreamingResponse` from the route (not from the service)

---

## 11. Guardrails

| Gate | Status |
|------|--------|
| No financial formula changes | ✅ |
| No runtime calculation changes | ✅ |
| No model output changes | ✅ |
| G20 | BLOCKED |
| R99 | NOT APPROVED |
| R102 | NOT APPROVED |
| partial_pay_sweep | Not promoted |
| flat/min DSCR sculpting | Not promoted |
| Backend source of truth | ✅ |

---

## 12. Recommended Next Phase

**Phase 49D-2 — Extract POST /download into export_service**

After characterization tests are merged, implement the extraction contract above.
Add full path coverage tests (6 paths minimum) before calling extraction done.