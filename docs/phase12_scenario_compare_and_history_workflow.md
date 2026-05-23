# Phase 12 - Scenario Compare and History Workflow

## Summary

This branch turns the persistence foundation into a usable review workflow:

- scenario history and timeline visibility
- side-by-side scenario compare
- copied-from lineage visibility
- export lineage visibility
- governance-aware comparison context
- improved scenario cards for the workspace sidebar

The goal is practical reviewer usability, not a heavy analytics system.

## Compare Philosophy

Scenario comparison is intentionally lightweight and review-friendly.

It compares the saved scenario snapshot plus the latest saved summary metadata across:

- Revenue
- OPEX
- EBITDA
- Senior Debt
- SHL
- DSCR
- Project IRR
- Equity IRR
- CAPEX
- Distributions

Where a metric is not yet present in the saved summary, it remains visibly pending instead of being invented.

## Governance-Aware Comparison

Numeric deltas are not the whole story, so the compare view also shows:

- G20 posture
- R99/R102 posture
- runtime-vs-governance context

This helps reviewers distinguish real numeric drift from review-state differences.

## Scenario History and Lineage

Saved scenarios now surface:

- created and updated timestamps
- copied-from lineage
- archived state
- export count
- latest saved summary metrics where available

This gives the workspace a workable audit trail without introducing a complex enterprise state machine.

## Export Lineage

Export history now reads more like lineage than a flat list. Reviewers can see:

- artifact type
- export timestamp
- linked scenario name when available
- governance posture at export time

That keeps export traceability visible in the same workspace used for saving and comparing scenarios.

## Reviewer Workflow

The intended flow is simple:

1. Save a scenario snapshot.
2. Duplicate it to explore an alternative case.
3. Compare the two scenarios side by side.
4. Review history and export lineage before sharing outputs.

## Known Limitations

- compare uses persisted summary metadata, not a full rerun-on-compare engine
- latest approved / latest reviewed are still governance-oriented conventions, not formal workflow states
- prior-export download recovery is still foundation-level, not a full artifact store
- this remains single-user and pilot-focused by design

## Runtime Safety

No runtime formulas were changed in this branch.

- G20 remains `BLOCKED`
- R99/R102 remains `NOT APPROVED`
- runtime authority remains unchanged
