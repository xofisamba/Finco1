# Phase 10 Final Calibration Residual Closeout Pack

## Residual closeout philosophy

This branch is the final Phase 10 calibration-status framing layer. Its job is not to eliminate every remaining difference. Its job is to classify the remaining differences clearly enough that reviewers can tell the difference between:

- resolved residuals,
- accepted convention drift,
- evidence limitations,
- governance blockers,
- remaining engineering follow-up,
- and stakeholder decision items.

That distinction matters because most remaining Phase 10 items are no longer broad runtime-calibration questions.

## Governance interpretation framework

The new `Calibration Residual Closeout` sheet is the final reference point for the Phase 10 workbook ecosystem. It is designed to stop reviewers from conflating:

- technical review readiness,
- governance signoff,
- evidence quality,
- and future enhancement work.

The workbook remains safe for review, but some items still require governance interpretation or later follow-up.

## Accepted convention methodology

Accepted conventions remain documented rather than hidden. They continue to cover areas such as:

- XIRR timing interpretation,
- SHL IDC investment-base treatment,
- distribution versus dividend framing,
- grouped revenue evidence,
- OPEX grouping conventions,
- and presentation-layer distinctions that do not imply runtime instability.

Accepted conventions are not runtime fixes. They are interpretation and presentation decisions that reviewers should understand explicitly.

## Evidence limitation methodology

Evidence limitations are now separated from engineering defects and governance blockers. A row may remain open because:

- the runtime export only exists in aggregate form,
- the committed Excel evidence only exists as a grouped total,
- or a reviewer-facing scalar has not been implemented as a reporting-only view.

That does not imply a broken model. It means the current evidence surface is narrower than the desired review lens.

## Engineering-followup philosophy

The closeout pack isolates true engineering follow-up so that Phase 11 can focus on optional reporting/product enhancements without reopening Phase 10 runtime-calibration work by default.

Examples include:

- reconciliation-only MOIC or IRR views,
- deeper extraction work,
- optional runtime coverage expansion,
- and export/product polish.

These are future enhancements, not current runtime blockers.

## Stakeholder-decision methodology

Stakeholder decisions remain visible where interpretation, waiver, or presentation choice is still required. That includes:

- equity IRR residual acceptance,
- reconciliation IRR waiver versus later implementation,
- grouped revenue evidence sufficiency,
- and final governance acceptance boundaries.

The pack makes those decisions explicit instead of allowing them to sit inside ambiguous WARN rows.

## Phase 11 transition framing

Phase 11 should begin from a cleaner base:

- runtime formulas remain untouched,
- governance blockers remain explicit,
- evidence limitations are named,
- and future work is separated from current runtime behavior.

The intended transition is from calibration/governance closeout into export/product polish, not back into broad model redesign.

## Governance limits

- G20 remains `BLOCKED`.
- R99/R102 remain `NOT APPROVED`.
- This branch does not approve either of those statuses.

## No runtime changes statement

This document is the branch's no runtime changes statement. No runtime formulas, no parity plugs, no IRR overrides, no waterfall logic, no SHL logic, no tax logic, and no governance gates are changed here.
