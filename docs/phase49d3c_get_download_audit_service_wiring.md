# Phase 49D-3C — GET /download Audit Service Wiring

**Branch:** `phase49d3c-wire-get-download-export-audit-service`
**Base SHA:** `bed4b7e554c473225d6c306ad479f07d3e6d3152`
**Phase:** 49D-3C (behavior-preserving production refactor — one route)

---

## 1. Objective

Wire the existing `record_download_export()` service function into the `GET /download` route only, preserving `record_export` payload behavior exactly. **POST /download is not touched.**

---

## 2. What Changed

### `main_web.py` — `GET /download` route

**Before:**
```python
record_export(
    user_id=user.user_id,
    project_code=project_code,
    export_type="excel_model_export",
    artifact_name=filename,
    artifact_path=f"/download?project_type={project_type}&scenario={scenario}",
    project_id=project_record.project_id if project_record else None,
    governance_state=_governance_snapshot(project_code),
    replay_metadata=replay_metadata,
)
```

**After:**
```python
record_download_export(
    user_id=user.user_id,
    project_code=project_code,
    export_type="excel_model_export",
    artifact_name=filename,
    artifact_path=f"/download?project_type={project_type}&scenario={scenario}",
    project_id=project_record.project_id if project_record else None,
    governance_state=_governance_snapshot(project_code),
    replay_metadata=replay_metadata,
    scenario_id=None,
)
```

**Changes:**
- `record_export(...)` → `record_download_export(...)`
- `scenario_id=None` added (GET /download has no scenario_id, per 49D-3A characterization)
- Import line updated to include `record_download_export`

---

## 3. What Did NOT Change

- `POST /download` — still uses direct `record_export(...)` call
- `_replay_metadata_for_project` — stays in main_web.py
- `_governance_snapshot` — stays in main_web.py
- `build_values_only_export_for_project` — unchanged
- `build_excel_export_for_post_request` — unchanged
- Replay metadata construction — unchanged
- Baseline_source timing — unchanged (set post-helper, pre-record)
- Export bytes, filenames, status codes, content-types — unchanged

---

## 4. record_export Payload Preservation

| Field | Original | After 49D-3C | Preserved |
|-------|----------|--------------|-----------|
| `user_id` | `user.user_id` | ✅ Same | YES |
| `project_code` | `project_code` | ✅ Same | YES |
| `export_type` | `"excel_model_export"` | ✅ Same | YES |
| `artifact_name` | `filename` | ✅ Same | YES |
| `artifact_path` | `/download?project_type={project_type}&scenario={scenario}` | ✅ Same | YES |
| `project_id` | `project_record.project_id if project_record else None` | ✅ Same | YES |
| `governance_state` | `_governance_snapshot(project_code)` | ✅ Same | YES |
| `replay_metadata` | pre-built dict | ✅ Same | YES |
| `scenario_id` | not passed | `None` added | YES (GET has no scenario_id) |

---

## 5. baseline_source Timing Preserved

```
1. _replay_metadata_for_project(...)  ← builds base dict
2. if project_origin == "saved_baseline": replay_metadata["baseline_source"] = True  ← timing preserved
3. build_values_only_export_for_project(...)  ← export generation
4. record_download_export(...)  ← service call
5. StreamingResponse(...)  ← response
```

---

## 6. Exception Behavior

`record_download_export` does NOT swallow exceptions. If `record_export` raised, it still raises. This is the same behavior as the original direct call.

---

## 7. Tests

```
tests/test_phase49d3c_get_download_audit_service_wiring.py  20 passed ✅
```

| Test | Status |
|------|--------|
| `test_main_web_imports_cleanly` | ✅ |
| `test_record_download_export_imports_cleanly` | ✅ |
| `test_record_download_export_calls_record_export_with_type` | ✅ |
| `test_record_download_export_preserves_artifact_path` | ✅ |
| `test_record_download_export_forwards_all_fields` | ✅ |
| `test_get_download_route_calls_record_download_export` | ✅ |
| `test_get_download_still_builds_replay_metadata_in_main_web` | ✅ |
| `test_get_download_still_calls_governance_snapshot` | ✅ |
| `test_post_download_still_uses_direct_record_export` | ✅ |
| `test_only_one_direct_record_export_remains` | ✅ |
| `test_phase49d3b_runtime_institutional_tests_pass` | ✅ |
| `test_no_unexpected_production_code_changes` | ✅ |
| `test_no_fixture_csv_changes` | ✅ |
| `test_no_schema_migrations` | ✅ |
| `test_guardrails_stated` | ✅ |
| `test_get_download_requires_auth` | ✅ |
| `test_record_download_export_does_not_swallow_exceptions` | ✅ |
| `test_get_download_replay_metadata_construction_preserved` | ✅ |
| `test_get_download_baseline_source_handling_preserved` | ✅ |
| `test_phase49d3a_regression` | ✅ |

---

## 8. Guardrails

| Gate | Status |
|------|--------|
| No production code changed (except GET /download route) | ✅ |
| No financial formula changes | ✅ |
| No runtime calculation changes | ✅ |
| No model output changes | ✅ |
| No fixture CSV changes | ✅ |
| No schema migrations | ✅ |
| No JS financial calculations | ✅ |
| G20 BLOCKED | ✅ |
| R99/R102 NOT APPROVED | ✅ |
| partial_pay_sweep not promoted | ✅ |
| flat/min DSCR not promoted | ✅ |
| Backend source of truth | ✅ |

---

## 9. Direct `record_export` Calls Remaining in main_web.py

After 49D-3C: **1** — the `POST /download` call.

| Route | Call type | Phase |
|-------|-----------|-------|
| `GET /exports/runtime-summary.csv` | `record_runtime_summary_export()` | 49D-3B ✅ |
| `GET /exports/institutional-workbook.xlsx` | `record_institutional_workbook_export()` | 49D-3B ✅ |
| `GET /download` | `record_download_export()` | 49D-3C ✅ |
| `POST /download` | `record_export()` direct | 49D-3D (next) |

---

## 10. Recommended Next Phase

**Phase 49D-3D** — Wire `record_download_export()` into `POST /download` route. This is the last remaining extraction. After that, all `record_export` calls in `main_web.py` will be delegated to the audit service, and `main_web.py` will be free of the `record_export` import entirely.