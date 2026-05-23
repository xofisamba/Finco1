# Phase 12 - Persistence and Saved Scenarios Foundation

## Summary

This branch adds the first lightweight persistence layer for the pilot product workflow:

- project records
- saved scenario snapshots
- scenario duplication and soft archive
- export history tracking
- governance snapshot preservation
- sidebar workflow hooks for save, load, duplicate, and history review

The design stays intentionally small and local-first. It is built for a single-user pilot workflow, not full SaaS collaboration.

## Architecture

Persistence stays on local SQLite with JSON payloads for snapshots and governance metadata. This keeps the implementation easy to inspect, easy to back up, and easy to evolve later toward a fuller storage model if Phase 12 grows into richer workflow management.

Persisted concepts:

- `projects`
- `scenarios`
- `runs`
- `scenario_exports`

## Workflow Philosophy

The saved-scenario flow is intentionally practical:

1. Start from TUHO or Oborovo.
2. Adjust the current form.
3. Save a scenario snapshot.
4. Reload or duplicate that snapshot later.
5. Keep a lightweight export trail tied back to the active project workspace.

Soft archive is included so users can tidy the working list without losing traceability.

## Governance Snapshot Philosophy

Saved scenarios and export history preserve a governance snapshot alongside runtime-facing metadata:

- G20 status
- R99/R102 posture
- accepted-convention summary
- evidence posture summary

This preserves the runtime-vs-governance distinction instead of letting exported artifacts drift away from their review context.

## Export Traceability

Export history now captures:

- export type
- artifact name
- export timestamp
- project association
- optional scenario association
- governance posture at export time

This is a foundation for reproducibility, not a full audit ledger yet.

## Future Migration Path

This branch deliberately avoids:

- heavy ORM layers
- enterprise RBAC
- multi-user collaboration
- full derived-tree persistence

If later phases need richer lifecycle handling, the repository API can sit behind SQLite now and migrate forward without changing runtime model logic.

## Known Limitations

- scenario rename is route-ready but still lightweight in the interface
- scenario load restores saved form inputs, not a full derived runtime tree
- export history is foundational and intentionally compact
- this is not yet a multi-user collaboration model

## Runtime Safety

No runtime formulas were changed in this branch.

- G20 remains `BLOCKED`
- R99/R102 remains `NOT APPROVED`
- runtime authority remains unchanged
