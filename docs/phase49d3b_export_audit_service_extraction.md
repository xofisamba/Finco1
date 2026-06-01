# Phase 49D-3B — Export Audit Service Extraction

**Branch:** `phase49d3b-extract-runtime-institutional-export-audit-service`
**Base SHA:** `aa92ef6a4fe181da6900cbaae9a2f31b720423c1`
**Phase:** 49D-3B (behavior-preserving extraction — production code changes)

---

## 1. Objective

Extract the `record_export` side-effect for the two simplest export audit routes into a dedicated audit service, while preserving existing behavior exactly.

---

## 2. What Moved

### New File: `app/services/export_audit_service.py`

Three typed wrapper functions around `record_export()`:

| Function | Route | Wraps |
|---------|-------|-------|
| `record_runtime_summary_export(...)` | `GET /exports/runtime-summary.csv` | `record_export(...)` with `export_type="runtime_summary_csv"` |
| `record_institutional_workbook_export(...)` | `GET /exports/institutional-workbook.xlsx` | `record_export(...)` with `export_type="institutional_workbook"` |
| `record_download_export(...)` | (not yet used — for GET/POST /download in 49D-3C) | `record_export(...)` with `export_type="excel_model_export"` |

### `main_web.py` Changes

Two route handlers updated to delegate `record_export` to the audit service:

**`GET /exports/runtime-summary.csv`** (line ~2277):
- Before: `record_export(user_id=..., project_code=safe_project, export_type="runtime_summary_csv", ...)`
- After: `record_runtime_summary_export(user_id=..., project_code=safe_project, artifact_name=export.filename, ...)`

**`GET /exports/institutional-workbook.xlsx`** (line ~2321):
- Before: `record_export(user_id=..., project_code=safe_project, export_type="institutional_workbook", ...)`
- After: `record_institutional_workbook_export(user_id=..., project_code=safe_project, artifact_name=export.filename, ...)`

---

## 3. What Did NOT Move

The following remain entirely in `main_web.py`:

- `_replay_metadata_for_project()` — helper function stays
- `_governance_snapshot()` — helper function stays
- `GET /download` `record_export` call — NOT extracted in this phase
- `POST /download` `record_export` call — NOT extracted in this phase
- Authentication (`get_current_user`)
- Project lookup (`get_project_by_code`)
- `runtime_project_code` normalization
- Export generation via `build_runtime_summary_csv_export` / `build_institutional_workbook_export`
- StreamingResponse construction

---

## 4. Service API

### `record_runtime_summary_export`

```python
def record_runtime_summary_export(
    user_id: str,
    project_code: str,
    artifact_name: str,
    project_id: str | None,
    governance_state: dict[str, Any],
    replay_metadata: dict[str, Any],
) -> None:
```

Internally calls `record_export()` with:
- `export_type="runtime_summary_csv"`
- `artifact_path=f"/exports/runtime-summary.csv?project={project_code}"`

### `record_institutional_workbook_export`

```python
def record_institutional_workbook_export(
    user_id: str,
    project_code: str,
    artifact_name: str,
    project_id: str | None,
    governance_state: dict[str, Any],
    replay_metadata: dict[str, Any],
) -> None:
```

Internally calls `record_export()` with:
- `export_type="institutional_workbook"`
- `artifact_path=f"/exports/institutional-workbook.xlsx?project={project_code}"`

### `record_download_export`

```python
def record_download_export(
    user_id: str,
    project_code: str,
    export_type: str,
    artifact_name: str,
    artifact_path: str,
    project_id: str | None,
    governance_state: dict[str, Any],
    replay_metadata: dict[str, Any],
    scenario_id: str | None = None,
) -> None:
```

Typed wrapper for GET/POST /download `record_export` calls (to be used in 49D-3C).

---

## 5. record_export Payload Preservation

### Runtime Summary CSV

| Field | Value | Preserved |
|-------|-------|-----------|
| `user_id` | `user.user_id` | ✅ Same |
| `project_code` | `safe_project` | ✅ Same |
| `export_type` | `"runtime_summary_csv"` | ✅ Same |
| `artifact_name` | `export.filename` | ✅ Same |
| `artifact_path` | `/exports/runtime-summary.csv?project={safe_project}` | ✅ Same |
| `project_id` | `project_record.project_id if project_record else None` | ✅ Same |
| `governance_state` | `_governance_snapshot(safe_project)` | ✅ Same |
| `replay_metadata` | `_replay_metadata_for_project(...)` | ✅ Same |

### Institutional Workbook

| Field | Value | Preserved |
|-------|-------|-----------|
| `user_id` | `user.user_id` | ✅ Same |
| `project_code` | `safe_project` | ✅ Same |
| `export_type` | `"institutional_workbook"` | ✅ Same |
| `artifact_name` | `export.filename` | ✅ Same |
| `artifact_path` | `/exports/institutional-workbook.xlsx?project={safe_project}` | ✅ Same |
| `project_id` | `project_record.project_id if project_record else None` | ✅ Same |
| `governance_state` | `_governance_snapshot(safe_project)` | ✅ Same |
| `replay_metadata` | `_replay_metadata_for_project(...)` | ✅ Same |

---

## 6. Exception Behavior

Exceptions from `record_export` propagate through the service function unchanged. The service does NOT swallow exceptions. If the database is unavailable, the route will receive an exception.

---

## 7. Tests

```
tests/test_phase49d3b_export_audit_service_extraction.py  28 passed ✅
```

Regression (behavioral):
- 49D-3A: 35/35 ✅
- 49D-2 behavioral: ✅
- 49B behavioral: ✅ (git-diff/line-count tests fail as expected in branch context)

---

## 8. Guardrails

| Gate | Status |
|------|--------|
| No production code changed (except 2 route handlers) | ✅ |
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

## 9. Recommended Next Phase

**Phase 49D-3C** — Extract `record_export` for `GET /download` into the already-written `record_download_export()` function. Then Phase 49D-3D for `POST /download`.

Note: `record_download_export()` is already implemented in `export_audit_service.py` and exported, but NOT yet wired into `main_web.py`. The GET /download extraction is the next logical step since it has the simpler pre-built `replay_metadata` pattern (no `scenario_id`).