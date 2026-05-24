# Phase 14 Scenario Compare Honesty

## Goal

Make scenario compare reviewer-safe and explicit about what is being compared, when the compared snapshots were captured, and how pending or unavailable metrics should be interpreted.

## What Changed

- Added a compare source-clarity banner in the compare panel.
- Added saved snapshot and runtime metadata cards for the left and right scenarios.
- Added compare-generated timestamp text.
- Standardized missing compare values to `pending / unavailable` and missing deltas to `not_applicable`.
- Added explicit dirty-draft guidance so reviewers can see that unsaved browser edits are excluded from compare output.

## Compare Semantics

- Scenario compare is descriptive only.
- Compare reads saved scenario snapshots and saved runtime summaries only.
- Unsaved browser draft edits are not part of the comparison unless they are saved first.
- Compare does not auto-save and does not auto-run.
- Pending, unavailable, and `not_applicable` markers are intentional and must not be read as zero.

## Metadata Shown

- saved scenario timestamp
- runtime timestamp where available
- runtime snapshot ID where available
- runtime origin where available
- compare generated timestamp
- governance posture summary

## Guardrails

- No runtime/model formulas were changed.
- No workbook calculations were changed.
- No export calculation logic was changed.
- No persistence authority promotion occurred.
- No replay engine behavior was added.
- No new editable surfaces were added.
- No JavaScript financial calculations were added.
- `audit_economic_mode` remains audit/reconciliation-only.
- `runtime_economic_mode` remains the only explicit runtime staging path.
- `G20` remains `BLOCKED`.
- `R99/R102` remain `NOT APPROVED`.

