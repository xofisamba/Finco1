# Phase 50C Closeout — Scenario State Service Extraction Summary

## Base SHA
`83d4388f8a6272c2a51b8646a59f6f26cb703358` (PR #371, before Phase 50B/50C extraction)

## Head SHA
`4ff6b84d6ef86222fdb9f11dfa92da02ca5285b7` (PR #375, after Phase 50C-3)

## Objective
Close out the Phase 50B/50C scenario state service extraction — summarize what moved into `app/services/scenario_state_service.py`, confirm behavior preservation, and map what remains in `main_web.py` before the next extraction phase.

> **This phase is docs/reports/tests only.** No production code changes.

---

## PR Summary

| PR | Phase | SHA | Summary |
|----|-------|-----|---------|
| #371 | 50A Characterization | `83d4388` | Broad characterization of scenario state resolution across `/run`, `/compare`, `/download`. No extraction. |
| #372 | 50B Helper Extraction | `dd61248` | Extracted `build_workspace_state_metadata()` + `scenario_provenance_for_record()` into `scenario_state_service.py`. Thin backward-compatible wrappers left in `main_web.py`. |
| #373 | 50C-1 Resolver Characterization | `af2729c` | Documented `_resolve_runtime_snapshot_source` — 5 branches, setdefault fields, effective_runtime_origin override logic. 28 tests. |
| #374 | 50C-2 Resolver Extraction | `9925bc2` | Extracted `RuntimeSnapshotResolution` + `resolve_runtime_snapshot()` into `scenario_state_service.py`. Thin wrapper remains in `main_web.py`. |
| #375 | 50C-3 Guard Wrapper | `4ff6b84` | Added `check_runtime_allowed()` wrapper. All 6 `runtime_guard_for_snapshot` call sites in `main_web.py` updated. Direct import removed from `main_web.py`. |

---

## Final `scenario_state_service.py` API Map

```python
# Low-risk helpers (Phase 50B)
def build_workspace_state_metadata(workspace_state) -> dict
def scenario_provenance_for_record(project_record, scenario_record) -> dict | None

# Runtime snapshot resolver (Phase 50C-2)
@dataclass(frozen=True)
class RuntimeSnapshotResolution:
    snapshot: dict
    scenario_record: Any
    warning: str
    effective_runtime_origin: str

def resolve_runtime_snapshot(
    user, project, workspace_state, runtime_origin
) -> RuntimeSnapshotResolution

# Runtime guard wrapper (Phase 50C-3)
def check_runtime_allowed(workspace_state, snapshot) -> tuple[bool, str, str]
    """Thin wrapper around repository.runtime_guard_for_snapshot."""
```

---

## Before / After Responsibility Split

### `app/services/scenario_state_service.py` — now owns:
- Workspace dirty/state metadata building
- Scenario provenance metadata building
- Runtime snapshot resolution (5-branch decision tree)
- Runtime guard (delegate to repository)

### `main_web.py` — still owns:
- Route orchestration (`/run`, `/compare`, `POST /download`)
- Form parsing (`_collect_form_snapshot`)
- Project/workspace request resolution (inline)
- Model run execution (`run_project`, `run_demo_project`)
- KPI formatting
- `record_workspace_runtime` persistence call
- Template/context rendering
- Scenario CRUD endpoints (save/load/discard, etc.)

---

## Behavior Preservation Summary

| Item | Status |
|------|--------|
| `/run` route blocks when `allow_run=False` | ✅ |
| `/compare` route blocks when `allow_run=False` | ✅ |
| `POST /download` blocks when `allow_run=False` | ✅ |
| `effective_runtime_origin` override in A1 branch | ✅ |
| All 5 setdefault fields always applied | ✅ |
| Branch C `dict(None)` TypeError fixed | ✅ |
| Branch B2 `dict(None)` TypeError fixed | ✅ |
| `runtime_origin` values: `saved_state`, `workspace_base`, `factory_base_runtime`, `preview_only` | ✅ |
| `guard_message` returned to UI on block | ✅ |
| `_resolve_runtime_snapshot_source` is thin wrapper | ✅ |
| `main_web.py` has 0 direct `record_export` calls | ✅ |

---

## Runtime Snapshot Branch Preservation

| Branch | Trigger | Repository Call | setdefault Applied |
|--------|---------|-----------------|-------------------|
| A | `saved_state` + `active_scenario_id` | Yes | Yes (5 fields) |
| A1 | Branch A but scenario unavailable | Fallback → workspace | Yes (5 fields) |
| B | `workspace_base` or `factory_base_runtime` or `preview_only` | No | Yes (5 fields) |
| B2 | `workspace_base` + `active_scenario_id` but `saved_snapshot is None` | No | Yes (5 fields) |
| C | `saved_state` without `active_scenario_id` | No | Yes (5 fields) |

---

## Runtime Guard Preservation

- `check_runtime_allowed()` is a zero-modification passthrough to `runtime_guard_for_snapshot`
- All 6 former call sites now use `check_runtime_allowed`
- `runtime_guard_for_snapshot` is no longer imported directly into `main_web.py`
- Dirty/stale workspace detection behavior is unchanged

---

## Test Coverage Summary

| File | Tests | Phase |
|------|-------|-------|
| `tests/test_phase50a_scenario_state_characterization.py` | 28 | 50A |
| `tests/test_phase50b_scenario_state_helper_extraction.py` | 25 | 50B |
| `tests/test_phase50c1_runtime_snapshot_source_characterization.py` | 28 | 50C-1 |
| `tests/test_phase50c2_runtime_snapshot_resolver_extraction.py` | 33 | 50C-2 |
| `tests/test_phase50c3_runtime_guard_wrapper.py` | 21 | 50C-3 |
| **Total** | **135** | |

---

## Known Limitations

1. **`_resolve_runtime_snapshot_source` wrapper remains in `main_web.py`** — it correctly delegates to `resolve_runtime_snapshot()` but is not inlined into routes. This is intentional; full inlining requires separate route-by-route PRs.

2. **Runtime guard is a passthrough, not a true extraction** — `check_runtime_allowed` delegates to `runtime_guard_for_snapshot` in the repository. The actual dirty/stale logic is not yet in the service layer.

3. **`record_workspace_runtime` not yet wrapped** — called directly in `main_web.py` after model runs.

---

## Residual `main_web.py` Responsibilities

| Category | Items |
|----------|-------|
| **Route orchestration** | `/run`, `/compare`, `POST /download` |
| **Request parsing** | `_collect_form_snapshot`, form field extraction |
| **Project/workspace resolution** | `_project_workspace_from_request` (inline, ~50 lines) |
| **Model execution** | `run_project`, `run_demo_project` |
| **Persistence calls** | `record_workspace_runtime`, `save_workspace_state`, `save_scenario`, `add_scenario`, `bind_workspace_to_scenario`, `discard_workspace_draft`, `duplicate_scenario`, `rename_scenario`, `archive_scenario`, `promote_scenario_to_base_case`, `select_scenario`, `update_scenario_last_run_summary` |
| **KPI formatting** | `_format_kpis`, `runtime_summary_to_dict` |
| **Templates** | All `templates.TemplateResponse` calls |
| **Scenario CRUD** | `/scenario/save`, `/scenario/load`, `/scenario/delete`, `/scenario/discard`, `/scenario/duplicate`, `/scenario/rename`, `/scenario/archive`, `/scenario/promote`, `/scenario/select` |

---

## Recommended Next Extraction Candidates

### 1. `_project_workspace_from_request` extraction (Phase 50D)
**Risk: Medium** | **Lines: ~50** | **Call sites: 3**

Inline helper that resolves `project_record` + `workspace_state` from the current request. Used at the top of `/run`, `/compare`, and `POST /download`. Extraction would further thin these routes.

### 2. Form snapshot / project input builder extraction (Phase 50E)
**Risk: Medium** | **Lines: ~80** | **Call sites: 3**

`_collect_form_snapshot` + `build_projectinputs` / `build_projectinputs_from_snapshot` chain. Builds the `ProjectInputs` dict that feeds into `run_project`. Already uses schema validation — extraction would clean up form-handling logic from routes.

### 3. `/run` route characterization + run orchestration service (Phase 50F)
**Risk: High** | **Lines: ~200** | **Call sites: 1**

The largest remaining route. Characterization needed before any extraction. KPI formatting, template rendering, and `record_workspace_runtime` call are the primary candidates for service extraction.

### 4. `/compare` service characterization (Phase 50G)
**Risk: Medium** | **Lines: ~150** | **Call sites: 1**

Multi-scenario execution + comparison table rendering. Less complex than `/run` but still significant orchestration.

---

## Service Layer Status

| Service | Phase Completed | Contents |
|---------|---------------|----------|
| `app/services/export_service.py` | Phase 49 | Export bytes/workbook construction |
| `app/services/export_audit_service.py` | Phase 49D-3B | Export audit recording |
| `app/services/scenario_state_service.py` | Phase 50C-3 | Scenario state + runtime snapshot + runtime guard |

**Total services extracted from `main_web.py` so far: 3**

---

## Guardrails — Confirmed Preserved

- ✅ No financial formula changes
- ✅ No runtime calculation changes
- ✅ No model output changes
- ✅ No route behavior changes
- ✅ No export behavior changes
- ✅ No fixture CSV changes
- ✅ No schema/migrations
- ✅ No JS financial calculations
- ✅ G20 BLOCKED · R99/R102 NOT APPROVED
- ✅ partial_pay_sweep not promoted · flat/min DSCR not promoted
- ✅ Backend remains source of truth