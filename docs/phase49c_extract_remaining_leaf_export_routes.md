# Phase 49C — Extract Remaining Leaf Export Routes from main_web.py

**Branch:** `phase49c-extract-remaining-leaf-export-routes`
**Base SHA:** `811a71d3b8fef7a78a705b759c2882d7f0439cd6`
**Head SHA:** `d2f5c8646c6bc05e1a60325f93386c8e9956bba9`
**Phase:** 49C

---

## 1. Objective

After Phase 49B extracted 3 export routes from `main_web.py`, conduct a thorough inspection of remaining routes to find any additional simple leaf-like export routes suitable for extraction.

---

## 2. Route Inspection Results

**Total routes in main_web.py: 34**

All 34 routes were inspected and classified:

| Route | Type | Status |
|-------|------|--------|
| `GET /` | HTML template | Not an export |
| `GET /login` | HTML form | Not an export |
| `POST /login` | Auth | Not an export |
| `POST /logout` | Auth | Not an export |
| `GET /public-health` | Health check | Not an export |
| `GET /readyz` | Health check | Not an export |
| `GET /health` | Health check | Not an export |
| `POST /validate` | Validation | Not an export |
| `POST /run` | Model execution | Not an export |
| `POST /compare` | Comparison | Not an export (returns HTML template) |
| `POST /download` | Excel export | **Deferred to 49D** — complex form/session/provenance |
| `GET /download` | Excel export | **Already extracted in 49B ✅** |
| `GET /exports/runtime-summary.csv` | CSV export | **Already extracted in 49B ✅** |
| `GET /exports/institutional-workbook.xlsx` | Workbook export | **Already extracted in 49B ✅** |
| `GET /projects/new` | HTML form | Not an export |
| `GET /projects/browse` | HTML | Not an export |
| `POST /projects/create` | Project creation | Not an export |
| `GET /scenarios` | HTML | Not an export |
| `POST /scenarios/state/draft` | State change | Not an export |
| `POST /scenarios/state/discard` | State change | Not an export |
| `GET /scenarios/history` | HTML | Not an export |
| `GET /scenarios/compare` | HTML | Not an export |
| `POST /scenarios/save` | Save | Not an export |
| `GET /scenarios/{scenario_id}/load` | HTML | Not an export |
| `POST /scenarios/{scenario_id}/duplicate` | Duplicate | Not an export |
| `POST /scenarios/add` | Add scenario | Not an export |
| `POST /scenarios/{scenario_id}/select` | Select | Not an export |
| `POST /scenarios/{scenario_id}/update-overrides` | Override | Not an export |
| `POST /projects/{project_code}/save-as` | Save-as | Not an export |
| `POST /scenarios/{scenario_id}/rename` | Rename | Not an export |
| `POST /scenarios/{scenario_id}/archive` | Archive | Not an export |
| `GET /runs` | HTML | Not an export |
| `POST /save-run` | Save | Not an export |
| `GET /run/{run_id}` | HTML | Not an export |

### Export Routes Summary

| Route | Phase | Status |
|-------|-------|--------|
| `GET /download` | 49B | Already extracted ✅ |
| `GET /exports/runtime-summary.csv` | 49B | Already extracted ✅ |
| `GET /exports/institutional-workbook.xlsx` | 49B | Already extracted ✅ |
| `POST /download` | 49D | Deferred — complex form/session/provenance handling |

**Phase 49C finding: No additional export routes found that are suitable for extraction.**

---

## 3. POST /download — Deferred to Phase 49D

### Why Deferred

`POST /download` (line 2054) has complex behavior:

1. **Form parsing** — parses 12+ form fields (capacity_mw, tariff_eur_mwh, p50_hours, total_capex_keur, etc.)
2. **Project/session resolution** — `_project_workspace_from_snapshot()`, `runtime_guard_for_snapshot()`, `_resolve_runtime_snapshot_source()`
3. **Provenance complexity** — uses `active_scenario_record`, `workspace_state`, `runtime_origin` variants: `factory_base_runtime`, `saved_state`, `user_created`
4. **Conditional overrides** — `build_projectinputs()` vs `build_projectinputs_from_snapshot()` based on `project_origin`
5. **Multiple record_export fields** — `scenario_id`, `scenario_name`, `active_scenario_id`, `scenario_provenance`, `warning_note`

Extracting this safely requires careful wrapping of all conditional paths.

### Phase 49D Approach

1. Keep `run_demo_project()` call in route (not extractable without breaking provenance)
2. Create `build_values_only_export_for_post_request(result, project_inputs, project_type, scenario, replay_metadata)` in export_service
3. Wrap all conditional provenance paths in service
4. Add comprehensive test coverage for each POST path variant

### Required Tests for Phase 49D

- `user_created` project origin path
- `saved_baseline` project origin path
- `saved_state` runtime origin path
- `factory_base_runtime` path
- Form validation error path
- Runtime guard blocked path

---

## 4. Service API

Phase 49C makes **no changes** to `app/services/export_service.py` — no additional leaf exports were found to extract.

Existing functions (from 49B) remain unchanged:

```python
@dataclass ExportResponse:
    bytes_data: bytes | None
    filename: str | None
    media_type: str | None
    status_code: int
    error_content: str | None
    metadata: dict[str, Any]

def build_values_only_export_for_project(
    result, project_inputs, project_type, scenario, *, replay_metadata=None
) -> ExportResponse

def build_runtime_summary_csv_export(
    runtime_project_code, *, safe_project=None
) -> ExportResponse  # metadata from runtime_rows[0]

def build_institutional_workbook_export(
    runtime_project_code, *, safe_project=None
) -> ExportResponse  # metadata from runtime_rows[0]
```

---

## 5. main_web.py Status

| Metric | Value |
|--------|-------|
| Lines | 3362 (unchanged from 49B) |
| Routes wrapped | 3 of 4 export routes (49B) |
| New exports found | 0 |

---

## 6. Tests

- **15 tests** in `test_phase49c_remaining_leaf_export_routes.py`
- **57 tests** — Phase 49B + Phase 47/48 regression suite

---

## 7. Guardrails

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
| No JS financial calculations | ✅ |
| No fixture CSVs changed | ✅ |
| No schema migrations | ✅ |

---

## 8. Recommended Next Phase

**Phase 49D — Extract POST /download from main_web.py**

With 15 tests covering the complex form handling paths, extract the remaining export route with complex conditional provenance. Alternatively, Phase 49E could target the next god module candidate identified in the Phase 49A mapping (`app/persistence/repository.py`).

---

## 9. Changed Files

| File | Change |
|------|--------|
| `tests/test_phase49c_remaining_leaf_export_routes.py` | 15 tests — route inspection + regression |
| `docs/phase49c_extract_remaining_leaf_export_routes.md` | Phase doc |
| `docs/phase49c_leaf_export_extraction_matrix.md` | Extraction matrix |
| `reports/phase49c_leaf_export_extraction_summary.json` | JSON summary |