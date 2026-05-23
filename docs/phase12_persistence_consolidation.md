# Phase 12 Persistence Consolidation

## Executive summary

Phase 12 persistence consolidation establishes `app/persistence/` as the single authoritative application persistence namespace.

The cleanup removes two orphaned alternatives:

- top-level `persistence/`
- `domain/persistence/`

This is an ownership cleanup only. Persistence semantics stay lightweight. Runtime authority does not move. Scenario and export workflows remain intact.

## Authority decision

`app/persistence/` is the only live application persistence package.

It owns:

- project persistence
- scenario persistence
- run metadata
- export metadata
- governance snapshot storage
- scenario lineage
- export lineage

No other package should be treated as an alternative repository layer.

## File responsibilities inside `app/persistence/`

### `db.py`

`db.py` owns the lightweight database bootstrap and connection/cursor helpers used by the current pilot workflow.

Responsibility:

- database path handling
- schema initialization
- connection and cursor access for repository operations

It is infrastructure only. It is not runtime authority.

### `repository.py`

`repository.py` owns the workflow-facing persistence operations.

Responsibility:

- save/load project records
- save/load scenario records
- duplicate and archive scenarios
- record export history
- preserve scenario and export lineage
- persist governance snapshot metadata
- persist last-run summaries as non-authoritative workflow metadata

It stores snapshots and workflow records only. It does not calculate financial outputs.

### `provenance.py`

`provenance.py` owns audit/replay metadata assembly.

Responsibility:

- commit SHA provenance
- branch provenance
- template/factory provenance
- runtime timestamp vs export timestamp
- runtime flag snapshot metadata
- replay limitation notices

It improves traceability only. It is not a replay engine and it does not override runtime execution.

## Removed orphaned packages

### Removed top-level `persistence/`

The top-level `persistence/` package was legacy code and no longer part of the active product path.

It created namespace ambiguity because it looked like a viable backend alongside `app/persistence/`, while the web app did not actually use it.

### Removed `domain/persistence/`

`domain/persistence/` was no longer imported by live app code.

The only remaining imports were from an orphaned legacy test module. That means the package had become dead architectural weight rather than a real boundary.

This branch removed `domain/persistence/` orphan package content so future contributors have only one live persistence namespace to follow.

Removing it reduces the risk of future editable-grid work accidentally growing a second persistence authority.

## Persistence is not runtime authority

This branch preserves the core boundary:

- persistence stores snapshots and workflow metadata
- runtime execution remains the only source of calculated financial truth

Persisted summaries are useful for UX and traceability, but they are **not** authoritative truth.

That means:

- no persisted KPI overrides runtime outputs
- no stored workbook summary becomes model authority
- no saved snapshot replaces a fresh runtime execution

## Scenario workflow semantics preserved

The current scenario workflow remains unchanged:

- save
- load
- duplicate
- archive

Scenario lineage also remains preserved:

- copied-from scenario relationships
- originating template/project lineage
- governance snapshot lineage

## Export lineage semantics preserved

Export traceability also remains preserved:

- scenario to run to export linkage
- governance posture at export time
- provenance metadata for audit replay context

Again, this is traceability only. It does not promote exports into runtime authority.

## Editable-grid prerequisites still outstanding

This cleanup is preparation for future stateful workflows, not the implementation of them.

Still outstanding before editable grids:

- dirty-state tracking
- input transaction model
- unsaved changes handling
- run guard
- immutable snapshot boundaries
- stale-state prevention

Those concerns should build on `app/persistence/` only.

## Governance posture

- `G20` remains `BLOCKED`
- `R99/R102` remain `NOT APPROVED`

This cleanup does not change any governance approval state.

## No runtime changes statement

No runtime/model formulas are changed in this branch. No workbook calculations are changed. No persistence semantics are redesigned. No editable-grid behavior is implemented. Persistence remains workflow metadata and snapshot storage only, not runtime authority.
