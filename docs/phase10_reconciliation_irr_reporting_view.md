# Phase 10 Reconciliation IRR Reporting View

## Purpose

This branch adds a reviewer-facing IRR reconciliation layer to the Phase 10 workbook ecosystem. The goal is to explain why runtime IRR values and Excel-facing IRR values can differ, which parts of that drift are convention-driven, and which parts remain governance-sensitive.

This is a reporting and review branch only. It does not change runtime formulas, XIRR logic, distribution logic, or any waterfall mechanics.

## IRR reconciliation philosophy

The workbook now separates three questions that had previously been blended together:

1. What does the runtime model currently produce?
2. What does the committed Excel-side evidence suggest?
3. Is the remaining difference an actual runtime defect, a convention difference, or a governance decision?

That separation matters because a small IRR residual is not automatically evidence of a runtime error. Date anchors, distribution framing, and presentation conventions can all move a reviewer-facing IRR without changing the underlying model economics.

## Runtime vs Excel IRR interpretation

The new `IRR Reconciliation` sheet is meant to be read alongside the `Returns Reconciliation` sheet:

- `Returns Reconciliation` keeps the existing scalar runtime-versus-Excel comparison in the broader parity pack.
- `IRR Reconciliation` explains the interpretation layer behind those scalars.

The runtime values remain the authoritative model outputs for this branch. Excel-side values remain evidence inputs for review, not instructions to override runtime behavior.

## XIRR convention discussion

The largest convention drivers remain:

- XIRR construction-date convention
- SHL IDC investment-base treatment
- distribution versus dividend definition
- semiannual timing / COD framing

These items can move a reviewer-facing equity IRR even when the runtime engine is behaving as intended. The new sheet and CSV reports make that distinction explicit.

## Governance interpretation strategy

The IRR reporting layer uses a narrower review vocabulary than the broader pack:

- `PASS`
- `ACCEPTED_CONVENTION`
- `GOVERNANCE_REVIEW`
- `MATERIAL_DELTA`
- `MISSING_EVIDENCE`

This does not replace the broader workbook classification framework. It gives IRR-specific rows a cleaner explanation surface for IC, lender, audit, and stakeholder review.

## Accepted convention methodology

Where a residual is already explained by committed evidence and prior governance artifacts, the reporting layer preserves that explanation instead of escalating it into a fake engineering defect. Examples include:

- XIRR date-anchor differences
- distribution-definition framing
- SHL IDC investment-base convention

The branch does not fabricate a synthetic reconciliation IRR just to remove a governance discussion from the workbook.

## Unresolved limitations

- A dedicated reconciliation IRR scalar remains `MISSING_EVIDENCE`.
- The branch does not alter runtime IRR formulas.
- The branch does not normalize timing assumptions behind the scenes.
- The branch does not approve any stakeholder convention automatically.

## Governance limits

- G20 remains `BLOCKED`.
- R99/R102 remain `NOT APPROVED`.
- This branch improves interpretation and review clarity only.
- It does not approve parity closeout, runtime promotion, or stakeholder acceptance.

## Reviewer guidance

Reviewers should use the new IRR materials in this order:

1. `Executive Dashboard`
2. `Returns Reconciliation`
3. `IRR Reconciliation`
4. `Gap Register`
5. `Accepted Conventions`

That order helps separate real runtime concerns from convention-driven presentation questions before people escalate engineering work unnecessarily.

## No runtime changes statement

This document is the branch's no runtime changes statement. No runtime formulas, XIRR logic, distribution logic, SHL mechanics, TaxBridge logic, DistributionAccount authority, or governance gates are changed here.
