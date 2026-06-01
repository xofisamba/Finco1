# Phase 49D-3A — Export Audit Recording Characterization

**Branch:** `phase49d3a-characterize-export-audit-recording`
**Base SHA:** `c05d7b036ad2cab6d9c989e0ff78b3679c3e74c9`
**Phase:** 49D-3A (pre-extraction characterization — no refactoring)

---

## 1. Objective

Characterize all export audit recording logic (`record_export` calls) in `main_web.py` before extracting the recording side-effect into a dedicated audit service in Phase 49D-3B.

---

## 2. record_export Call Sites

There are **4 `record_export` call sites** in `main_web.py`:

| # | Route | Line | export_type |
|---|-------|------|-------------|
| 1 | POST /download | 2167 | `excel_model_export` |
| 2 | GET /download | 2234 | `excel_model_export` |
| 3 | GET /exports/runtime-summary.csv | 2276 | `runtime_summary_csv` |
| 4 | GET /exports/institutional-workbook.xlsx | 2322 | `institutional_workbook` |

---

## 3. Call Site Details

### Call #1: POST /download (main_web.py:2167)

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

Key characteristics:
- replay_metadata is built by the route (not by the service)
- baseline_source is set in replay_metadata by the route AFTER Excel generation and BEFORE this call (line 2163)
- scenario_id includes active_scenario_record.scenario_id (only when saved_state)
- replay_metadata includes runtime_origin, scenario_provenance, warning_note

### Call #2: GET /download (main_web.py:2234)

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

Key characteristics:
- replay_metadata is built via _replay_metadata_for_project (line 2132)
- replay_metadata includes template_origin_override=saved_project_assumptions when user_created
- No scenario_id in this call (unlike POST /download)
- No baseline_source handling in this route

### Call #3: GET /exports/runtime-summary.csv (main_web.py:2276)

```python
record_export(
    user_id=user.user_id,
    project_code=safe_project,
    export_type="runtime_summary_csv",
    artifact_name=export.filename,
    artifact_path=f"/exports/runtime-summary.csv?project={safe_project}",
    project_id=project_record.project_id if project_record else None,
    governance_state=_governance_snapshot(safe_project),
    replay_metadata=_replay_metadata_for_project(
        safe_project,
        export_type="runtime_summary_csv",
        export_timestamp=export.metadata["export_generated_at"],
        runtime_timestamp=export.metadata["runtime_generated_at"],
        project_id=project_record.project_id if project_record else None,
        runtime_origin=export.metadata["runtime_origin"],
        artifact_name=export.filename,
        baseline_source=(project_record.project_origin == "saved_baseline") if project_record else None,
    ),
)
```

Key characteristics:
- replay_metadata is built INLINE via _replay_metadata_for_project (not pre-built)
- replay_metadata gets timestamps from export.metadata (set by build_runtime_summary_csv_export)
- runtime_origin from export.metadata["runtime_origin"]
- baseline_source conditionally set based on project_record.project_origin == "saved_baseline"

### Call #4: GET /exports/institutional-workbook.xlsx (main_web.py:2322)

```python
record_export(
    user_id=user.user_id,
    project_code=safe_project,
    export_type="institutional_workbook",
    artifact_name=export.filename,
    artifact_path=f"/exports/institutional-workbook.xlsx?project={safe_project}",
    project_id=project_record.project_id if project_record else None,
    governance_state=_governance_snapshot(safe_project),
    replay_metadata=_replay_metadata_for_project(
        safe_project,
        export_type="institutional_workbook",
        workbook_type="institutional_workbook_runtime_binding",
        export_timestamp=export.metadata["export_generated_at"],
        runtime_timestamp=export.metadata["runtime_generated_at"],
        project_id=project_record.project_id if project_record else None,
        runtime_origin=export.metadata["runtime_origin"],
        artifact_name=export.filename,
        baseline_source=(project_record.project_origin == "saved_baseline") if project_record else None,
    ),
)
```

Key characteristics:
- Same pattern as Call #3 (inline _replay_metadata_for_project)
- workbook_type="institutional_workbook_runtime_binding" extra field
- baseline_source conditional on saved_baseline

---

## 4. Helper Functions

### _replay_metadata_for_project (main_web.py:884)

Purpose: Build a provenance dict for export recording.

Signature:
```python
def _replay_metadata_for_project(
    project_code: str,
    *,
    export_type: str | None = None,
    workbook_type: str | None = None,
    export_timestamp: str | None = None,
    runtime_timestamp: str | None = None,
    project_id: str | None = None,
    scenario_id: str | None = None,
    scenario_name: str | None = None,
    scenario_revision: str | None = None,
    runtime_snapshot_id: str | None = None,
    runtime_origin: str | None = None,
    artifact_name: str | None = None,
    project_inputs_override=None,
    template_origin_override: str | None = None,
    baseline_source: bool | None = None,
    active_scenario_id: str | None = None,
    active_scenario_name: str | None = None,
    scenario_provenance: dict | None = None,
    warning_note: str | None = None,
) -> dict
```

Behavior:
1. Calls _project_inputs_for_code(project_code) to get project inputs
2. Calls _governance_snapshot(project_code) to get governance state
3. Calls build_replay_metadata(...) with all provided kwargs
4. Adds template_origin if template_origin_override provided
5. Sets baseline_source if provided
6. Sets active_scenario_id and active_scenario_name (with fallback to not_applicable)
7. Updates with scenario_provenance dict if provided
8. Adds warning_note if provided

### _governance_snapshot (main_web.py:217)

Purpose: Return static governance metadata dict for a project.

Signature:
```python
def _governance_snapshot(project_code: str | None = None) -> dict
```

Returns:
```python
{
    "project_code": project_label,
    "g20_status": "BLOCKED",
    "r99_r102_status": "NOT APPROVED",
    "accepted_conventions_state": "Phase 10 closeout baseline",
    "evidence_posture_summary": "Runtime vs governance distinction preserved",
}
```

---

## 5. replay_metadata Fields per Route

| Route | Built by | Key fields |
|-------|----------|------------|
| POST /download | Route (~line 2132) | runtime_origin, scenario_provenance, warning_note, active_scenario_id/name, template_origin_override |
| GET /download | Route via _replay_metadata_for_project | runtime_origin, template_origin_override=saved_project_assumptions if user_created |
| GET /exports/runtime-summary.csv | Inline _replay_metadata_for_project | export_timestamp, runtime_timestamp, runtime_origin from export.metadata |
| GET /exports/institutional-workbook.xlsx | Inline _replay_metadata_for_project | Same as above + workbook_type |

---

## 6. baseline_source Behavior

| Route | baseline_source set? | How |
|-------|---------------------|-----|
| POST /download | YES | replay_metadata["baseline_source"] = True at line 2163 (post-service, pre-record_export) when project_record.project_origin == "saved_baseline" |
| GET /download | NO | Not handled in this route |
| GET /exports/runtime-summary.csv | YES conditional | baseline_source=(project_record.project_origin == "saved_baseline") passed to _replay_metadata_for_project |
| GET /exports/institutional-workbook.xlsx | YES conditional | Same — baseline_source=(project_record.project_origin == "saved_baseline") |

---

## 7. runtime_origin Behavior

| Route | runtime_origin value | Source |
|-------|---------------------|--------|
| POST /download | factory_base_runtime or saved_state | Set in route conditional logic |
| GET /download | factory_base_runtime | Passed via _replay_metadata_for_project |
| GET /exports/runtime-summary.csv | factory_base_runtime or saved_state | export.metadata["runtime_origin"] from build_runtime_summary_csv_export |
| GET /exports/institutional-workbook.xlsx | Same | export.metadata["runtime_origin"] from build_institutional_workbook_export |

---

## 8. Side Effects

record_export is called for its side effects (database persistence). It does not return a value used by the route.

---

## 9. Extraction Risks for Phase 49D-3B

| Risk | Severity | Mitigation |
|------|----------|------------|
| record_export called after StreamingResponse return | High | In POST/GET download — export recorded AFTER bytes sent (not blocking) |
| replay_metadata built differently per route (inline vs pre-built) | High | Service needs flexible API to support both patterns |
| baseline_source timing differs by route (post-bytes vs inline) | Medium | Route sets it before calling service |
| _replay_metadata_for_project has many optional kwargs | Medium | Service needs to accept the same flexibility |
| _governance_snapshot is static but project-specific | Low | Service can call it directly |

---

## 10. Recommended Service Boundary for 49D-3B

```
app/services/export_audit_service.py

def record_export_for_download(
    user_id: str,
    project_code: str,
    export_type: str,
    artifact_name: str,
    artifact_path: str,
    project_id: str | None,
    scenario_id: str | None,
    governance_state: dict,
    replay_metadata: dict,
) -> None:

def record_export_for_runtime_summary(
    user_id: str,
    safe_project: str,
    export_filename: str,
    project_record,
    export_metadata: dict,
) -> None:

def record_export_for_institutional_workbook(
    user_id: str,
    safe_project: str,
    export_filename: str,
    project_record,
    export_metadata: dict,
) -> None:
```

---

## 11. Guardrails

| Gate | Status |
|------|--------|
| No production code changed | YES |
| No financial formula changes | YES |
| No runtime calculation changes | YES |
| No model output changes | YES |
| G20 BLOCKED | YES |
| R99/R102 NOT APPROVED | YES |
| partial_pay_sweep not promoted | YES |
| flat/min DSCR sculpting not promoted | YES |
| Backend source of truth | YES |

---

## 12. Recommended Next Phase

Phase 49D-3B — Extract record_export into export_audit_service.
Start with simpler GET routes (runtime-summary, institutional-workbook) since they have inline _replay_metadata_for_project pattern.
POST /download is most complex due to multi-path replay_metadata construction.
