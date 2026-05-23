# Phase 10 Evidence Coverage and Runtime Binding Expansion

## Runtime Binding Expansion Strategy

This branch expands the review pack by binding additional values that already exist in runtime outputs, assembled financial statements, or existing export helpers. The goal is to reduce avoidable reporting gaps without changing model behavior.

The branch stays within reporting and workbook scope:

- no runtime formula changes
- no waterfall logic changes
- no SHL logic changes
- no tax logic changes
- no OPEX engine changes
- no DistributionAccount promotion
- no R99/R102 promotion
- no G20 approval

## Evidence Coverage Methodology

The review pack now distinguishes more clearly between:

- Excel-side evidence gaps
- runtime-side values already available and now bound
- reporting-layer binding gaps
- governance blockers

Rows remain `MISSING_EVIDENCE` when the Excel side is still unavailable, even if the runtime side is now properly surfaced. This is deliberate. The workbook should become more complete without pretending that missing Excel evidence has been solved.

## Runtime Coverage Methodology

Runtime coverage is measured by whether a row now has a real runtime-backed model-side value surfaced in the workbook or companion reports.

This branch especially expands runtime-side visibility for:

- SHL cash interest, PIK, and total service
- tax loss balances
- taxable profit after losses
- CIT accrual
- current-period tax cash
- existing CFADS and distribution audit fields

## Unresolved Gap Methodology

The new runtime binding gap register explains for each unresolved row:

- why it is still unresolved
- whether engineering work exists
- whether evidence is missing
- whether governance decision is required
- the expected roadmap phase

This reduces ambiguous `WARN` handling and makes follow-up work easier to sequence.

## Source Consistency Policy

If a source is already runtime-available, the workbook should now either:

- bind it directly
- or state exactly why it still is not surfaced

No runtime-available field should remain silently blank. No missing evidence row should be zero-filled to make the pack look cleaner than it really is.

## Known Limitations

This branch does not create new Excel evidence. It only improves how existing runtime-side and committed evidence are surfaced.

Examples of still-limited areas:

- separate CO2 and balancing revenue evidence
- contingency breakout as a standalone runtime row
- reconciliation IRR
- MOIC
- some full-horizon Excel-side tax rows

## Governance Limitations

This branch does not change governance posture.

G20 remains `BLOCKED`.
R99/R102 remain `NOT APPROVED`.

Audit-only and governance-sensitive rows remain labeled as such.

## No Runtime Changes Statement

This is an evidence coverage and runtime binding branch only.

- no runtime formula changes
- no waterfall changes
- no SHL mechanics changes
- no TaxBridge changes
- no DistributionAccount authority changes
- no fake parity values
- no silent zero-fill
