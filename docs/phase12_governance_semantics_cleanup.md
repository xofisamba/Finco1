# Phase 12 Governance Semantics Cleanup

## Executive summary

This branch hardens the governance and reconciliation vocabulary used across the institutional review pack. The main goal is to remove label drift before editable grids, richer reviewer workflows, and future signoff logic add more statefulness on top of the current workbook ecosystem.

No runtime formulas change in this branch. No reconciliation math changes. No workbook numeric values are softened or normalized. `G20` remains `BLOCKED`. `R99/R102` remain `NOT APPROVED`.

## Governance semantics philosophy

The review pack needs labels that tell reviewers exactly what kind of issue they are looking at:

- a real runtime-risk question
- a governance blocker
- an evidence-quality limitation
- a reporting-layer scalar gap
- a documented convention

Phase 10 and early Phase 12 materials used `MISSING_EVIDENCE` too broadly. That made it harder for non-engineering readers to tell whether the missing item was:

- Excel-side only
- runtime-binding related
- a missing reviewer scalar
- a true missing source
- or simply a governance follow-up

This cleanup makes those meanings explicit.

## Label hierarchy

The authoritative hierarchy is now:

1. `PASS`
2. `ACCEPTED_CONVENTION`
3. `WARN`
4. `EVIDENCE_LIMITATION` / `GROUPED_SOURCE_ONLY`
5. `MISSING_EXCEL_EVIDENCE` / `MISSING_REVIEW_SCALAR` / `SOURCE_NOT_AVAILABLE` / `RUNTIME_BINDING_PENDING`
6. `GOVERNANCE_REVIEW`
7. `STAKEHOLDER_DECISION`
8. `GOVERNANCE_BLOCKER`
9. `FAIL`
10. workflow states such as `BLOCKED` and `NOT_APPROVED`

The hierarchy is meant for reviewer interpretation, not runtime authority.

## Missing-evidence split rationale

The old umbrella label `MISSING_EVIDENCE` is retained only as a legacy/historical reference. New outputs should use one of these more precise labels instead:

- `MISSING_EXCEL_EVIDENCE`
  - runtime-side value exists
  - committed Excel-side row is absent or unusable at the needed level

- `MISSING_REVIEW_SCALAR`
  - the pack lacks a dedicated reviewer-facing scalar or bridge
  - example: reconciliation IRR reporting scalar

- `SOURCE_NOT_AVAILABLE`
  - neither side provides a defensible standalone source
  - example: separate CO2 or balancing sub-lines

- `RUNTIME_BINDING_PENDING`
  - underlying runtime logic exists
  - the reporting breakout is not yet first-class

This split is intentionally narrow. It avoids label sprawl while still answering the reviewer’s first question: what exactly is missing?

## Reviewer guidance strategy

The workbook now explains semantics in the navigation and governance layers so reviewers can distinguish:

- runtime-authoritative output
- review-only output
- governance-blocked output
- evidence-quality limitations
- accepted conventions that do not change runtime authority

The intended interpretation is:

- `ACCEPTED_CONVENTION` is not approval
- `MISSING_EXCEL_EVIDENCE` is not zero
- `SOURCE_NOT_AVAILABLE` does not justify synthetic splits
- `RUNTIME_BINDING_PENDING` is not a formula defect
- `GOVERNANCE_BLOCKER` remains a blocker

## Runtime vs governance distinction

This branch preserves the existing separation:

- runtime remains the only source of runtime-calculated values
- workbook/report labels remain explanatory only
- governance classifications do not override runtime outputs
- persisted or exported views remain non-authoritative snapshots

## Accepted convention clarification

`ACCEPTED_CONVENTION` means the difference is understood as a presentation, timing, or definition convention. It does **not** mean:

- approved by governance
- safe to ignore in signoff discussions
- promoted into runtime authority

This distinction matters for future approval flows and editable-grid UX, where a reviewer may otherwise confuse “documented convention” with “approved output.”

## Workbook and report consistency strategy

The cleanup is applied first to the active institutional review pack surfaces:

- Navigation
- Governance
- Executive Summary
- Executive Dashboard
- Gap Register
- Reviewer Notes
- generated CSV reports

Historical phase artifacts may still contain legacy wording, but the active Phase 10/11/12 review pack surfaces now use the clarified semantics model.

## Migration-status table for remaining `MISSING_EVIDENCE` usage

Not every historical artifact is being mass-rewritten in this cleanup. The boundary is:

- new or regenerated active reviewer-facing outputs should use the precise labels
- frozen historical artifacts may retain `MISSING_EVIDENCE`
- legacy references should be documented rather than silently rewritten

| Surface | Status | Why |
| --- | --- | --- |
| Active calibration workbook surfaces (`Navigation`, `Executive Dashboard`, `Reviewer Notes`, active reconciliation rows) | `REPLACED_BY_PRECISE_LABEL` | These are current reviewer-facing surfaces and now use `SOURCE_NOT_AVAILABLE`, `MISSING_EXCEL_EVIDENCE`, and `MISSING_REVIEW_SCALAR` where appropriate. |
| Newly generated Phase 12 governance semantics reports | `REPLACED_BY_PRECISE_LABEL` | The semantics cleanup branch treats these as authoritative for future reviewer interpretation. |
| Older Phase 10 CSV artifacts that are kept as historical evidence snapshots | `LEGACY_FROZEN_REFERENCE` | They record prior review state and are not automatically re-authored unless a later branch intentionally regenerates them. |
| Any remaining active output that still needs a narrower label split but is not blocking tests today | `ACTIVE_TO_MIGRATE_LATER` | These should be migrated only where the surface is still actively consumed and the meaning can be split safely. |
| Legacy references explaining the old umbrella term itself | `INTENTIONALLY_RETAINED` | The old label remains documented as a historical umbrella so reviewers can interpret prior artifacts. |

Going forward:

- use `MISSING_EXCEL_EVIDENCE` when runtime-side data exists but committed Excel-side support is missing
- use `MISSING_REVIEW_SCALAR` when the reporting layer lacks a reviewer scalar or bridge
- use `SOURCE_NOT_AVAILABLE` when neither side provides a defensible standalone source
- keep `RUNTIME_BINDING_PENDING` for reporting breakout gaps rather than evidence gaps

## Known limitations

- legacy historical documents may still contain `MISSING_EVIDENCE`
- older evidence artifacts are not retroactively re-authored
- workflow statuses such as `BLOCKED` and `NOT_APPROVED` remain separate from row-level reconciliation labels
- this branch does not implement approval roles, reviewer permissions, or editable-grid state

## No runtime changes statement

No runtime/model formulas are changed in this branch. No reconciliation math is changed. No workbook numeric calculations are changed. No persistence model semantics are redesigned. No approval workflow is implemented. `G20` remains `BLOCKED`. `R99/R102` remain `NOT APPROVED`.
