# Phase 12 - Audit Replay Metadata Hardening

## Purpose

This branch hardens provenance and replay-facing metadata for saved runs, scenarios, exports, and reviewer workbooks.

It does **not** introduce a replay engine, and it does **not** change runtime formulas or workbook calculations.

## What We Added

- commit SHA capture for runtime-facing exports and persisted replay metadata
- branch-name capture when available
- distinct runtime execution and export-generation timestamps
- lightweight template/factory provenance for TUHO and Oborovo
- runtime flag snapshots for the current default-off runtime/governance flags
- stronger scenario -> run -> export lineage metadata
- explicit replay limitation notices in review-facing workbook metadata

## Replay Philosophy

Replay metadata is informational provenance only.

Runtime calculations remain authoritative in runtime execution. Persisted metadata does not override cash flows, tax, SHL behavior, DSCR, or workbook values.

## Commit SHA Policy

Where Git context is available, the current `HEAD` commit SHA is captured and attached to:

- runtime summary exports
- institutional workbook metadata
- persisted run metadata
- persisted export metadata

This gives reviewers a concrete code-version anchor for any generated artifact.

## Factory / Template Provenance

The platform does not yet maintain a separate semantic version for project factories.

Instead, this branch captures lightweight template provenance:

- template key
- template origin
- template code
- template revision = `not separately versioned`

That is intentionally honest: template provenance exists, but separate semantic factory versioning does not yet exist.

## Runtime Flag Provenance

Runtime flag capture is provenance-only.

The branch records the enabled/disabled state of the current runtime/governance-safe flags so that exported artifacts can be traced back to the flag posture that was active when the runtime result was generated.

This does **not** change flag behavior.

## Replay Limitations

Replay is still incomplete today.

Current limitations remain:

- deterministic replay is not fully guaranteed
- full runtime tree persistence is not implemented
- editable-state replay is not implemented
- environment-level assumptions are only partially captured
- persisted summaries remain non-authoritative

The workbook now states these limitations explicitly instead of implying stronger replay guarantees than exist.

## Lineage Strategy

The intended traceability chain is now:

`scenario -> run -> export -> workbook/report`

Each layer now carries more provenance so that reviewers can understand:

- which scenario generated an artifact
- when runtime execution occurred
- when the artifact was exported
- which code revision produced it
- which template/factory baseline it came from
- which runtime flags were on or off

## Governance Posture

- G20 remains `BLOCKED`
- R99/R102 remain `NOT APPROVED`

This branch improves traceability only. It does not approve governance gates and does not add new runtime authority.

## Known Limitations

- no replay engine exists yet
- no editable-grid state model exists yet
- no full environment snapshot exists yet
- template revision is lightweight provenance, not separate versioning

## Runtime Scope

No runtime formulas were changed in this branch.
