# Phase 14 Reviewer Cover Notes

## Purpose

This branch adds reviewer-facing cover notes to active workbook/export outputs so
an exported artifact is interpretable without chat history or private context.

The notes are explanatory only.

They do not:

- compute financial values
- override runtime outputs
- imply approval
- soften blockers
- turn workbook/export into calculation authority
- promote audit/reconciliation-only outputs into runtime authority

No runtime/model formulas were changed.
No workbook calculations were changed.
No persistence authority promotion occurred.
No replay engine behavior was added.

`audit_economic_mode` remains audit/reconciliation-only.
`runtime_economic_mode` remains the only explicit runtime staging path.
`G20` remains `BLOCKED`.
`R99/R102` remain `NOT APPROVED`.

## Artifacts Updated

Reviewer cover notes were added to:

1. Institutional workbook
   - cover sheet reviewer panel
   - governance sheet interpretation section

2. Generic values-only Excel export
   - Notes sheet reviewer cover-note block

The runtime summary CSV was left structurally unchanged in this branch because
the CSV already exposes descriptive provenance fields and is not the best place
for long-form interpretation guidance.

## Required Interpretation Rules

The cover notes explain:

1. Runtime authority
   - runtime/backend output remains the financial source of truth
   - workbook/export is descriptive and reviewer-facing
   - workbook is not the calculation engine

2. Snapshot versus live draft
   - exported artifacts reflect an exported runtime/saved snapshot context
   - later draft edits do not mutate the artifact already exported
   - stale runtime means the reviewer should ask for a saved rerun if current
     draft edits changed after the last clean run

3. Governance boundaries
   - `G20` remains `BLOCKED`
   - `R99/R102` remain `NOT APPROVED`
   - accepted conventions are explanatory, not approval
   - audit/reconciliation traces are not runtime promotion

4. Provenance interpretation
   - commit SHA, branch, scenario, runtime timestamp, export timestamp, flags,
     and template provenance remain descriptive only
   - `unavailable` and `not_applicable` markers are intentional and must not be
     read as zero values

5. Governed residuals
   - documented residuals, timing conventions, or pending labels are governed
     interpretation notes, not silent parity fabrication
   - pending metrics should be read as pending/not available, not zero

6. No-claims
   - not lender-ready without external model review
   - not audit-certified
   - not multi-user governance-ready
   - no replay engine
   - no R99/R102 promotion
   - no G20 approval

## Guardrails

- no runtime/model formula changes
- no workbook calculation changes
- no workbook/export authority promotion
- no persistence authority promotion
- no replay engine behavior
- no governance behavior changes
- no new editable surfaces
- no JavaScript financial calculations
