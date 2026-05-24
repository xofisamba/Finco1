## Phase 13A - Editable Grid State Controls

### Purpose

Phase 13A introduces the state-management foundation required before a larger editable-grid UX rollout. The goal is to keep scenario editing usable without creating runtime ambiguity or a second source of truth.

### Architecture Summary

- `app/persistence/` remains the single authoritative persistence namespace.
- Saved scenarios remain explicit persisted snapshots.
- Workspace draft state is stored separately from saved scenarios.
- Runtime results bind only to a clean snapshot boundary:
  - saved scenario snapshot
  - clean workspace base snapshot
- Unsaved draft edits remain preview-only until the user either saves or discards them.

### State Model

The state model now distinguishes four layers:

1. Saved scenario:
   Explicitly persisted scenario snapshot with governance metadata and optional last runtime summary.
2. Workspace draft:
   Current editable form state for the active project workspace. This may be dirty.
3. Runtime boundary:
   The snapshot that the last runtime execution actually used.
4. Runtime result:
   KPI/result summary bound to that runtime snapshot only.

This prevents later edits from silently changing the meaning of an already-rendered runtime result.

### Dirty-State Tracking

- Form edits update workspace draft state.
- Dirty state compares the current draft snapshot against the last saved snapshot boundary.
- Dirty state survives workspace navigation because it is stored as workspace metadata rather than only browser-local state.

Dirty state does **not** imply approval, governance advancement, or runtime authority.

### Save / Discard Semantics

- `Save Scenario` creates an explicit saved scenario snapshot.
- `Discard Edits` restores the workspace draft back to the last saved snapshot boundary.
- There is no hidden scenario auto-save.

The workspace may persist draft metadata to avoid accidental loss, but saved scenario authority remains explicit and user-driven.

### Runtime Snapshot Boundary

Runtime execution is guarded by snapshot cleanliness:

- allowed:
  - clean saved scenario state
  - clean workspace base state
- blocked:
  - unsaved edits that diverge from the saved/runtime boundary

If unsaved edits are active, the user must save or discard before runtime execution proceeds. This keeps runtime outputs tied to a deterministic snapshot.

### Stale-State Prevention Strategy

- last runtime snapshot ID is tracked separately
- runtime origin is tracked separately:
  - `saved_state`
  - `workspace_base`
  - `preview_only`
- later draft edits do not mutate prior runtime metadata
- active scenario and last runtime boundary are shown separately

### Runtime vs Preview Separation

- workspace draft = preview/editable state
- saved scenario = persisted scenario boundary
- runtime result = bound execution snapshot

These layers are intentionally not interchangeable.

### Governance Safety

- governance labels remain explanatory only
- `ACCEPTED_CONVENTION` does not imply approval
- `G20` remains `BLOCKED`
- `R99/R102` remains `NOT APPROVED`

In other words: G20 remains `BLOCKED`, and R99/R102 remain `NOT APPROVED`.

### Known Limitations

- this is not the final editable-grid UX
- there is no collaborative or multi-user locking model
- there is no replay engine
- runtime calculations still come only from runtime execution, not persistence
- unsaved draft persistence is workspace-scoped, not approval-scoped

### No Runtime Changes

This branch does not change runtime/model formulas, workbook calculations, or runtime authority. It only adds state-control guardrails around editable scenario workflow.
