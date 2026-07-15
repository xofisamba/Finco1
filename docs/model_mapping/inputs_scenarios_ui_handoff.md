# Inputs and Scenarios UI Handoff

## Status

The mapping artifacts are ready for future UI planning, but this PR does not implement any UI.

## What the UI May Trust

The UI may trust registry-backed canonical fields that are marked runtime-bound in the crosswalk.

For workbook-only evidence, the UI may display audit metadata only after a product decision confirms the concept should be surfaced.

The preliminary mapping package is authoritative for row inventory only. Its `hardcode_cells`, `formula_cells`, `active_formula_kind`, candidate-input and scenario metadata are not implementation contracts unless revalidated against actual workbook storage or represented in the curated v5.3 evidence axes.

## What the UI Must Not Infer

The UI must not infer:

- source workbook formulas
- source workbook values
- P&L, tax, debt, or scenario behavior from coordinates alone
- editable status from column letter alone
- WHT reimbursement from VAT reimbursement evidence
- implementation eligibility from preliminary package claims
- scenario override eligibility from active-cell storage alone

## Required Future Gates

Before implementation, each field needs:

1. canonical field id
2. runtime ownership
3. save/load behavior
4. scenario override behavior
5. validation rules
6. export/audit behavior
7. test coverage

Rows marked `ABSENCE_CONFIRMED` are not candidates for UI implementation until distinct backend-authoritative evidence exists.

Blank scenario override cells remain inherit semantics, not explicit zero.
