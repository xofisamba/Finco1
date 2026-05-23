# Phase 10 CO2 / Balancing Source-Map Hardening

## Purpose

This branch hardens the reviewer-facing source map for CO2 and balancing revenue without changing runtime revenue formulas, without fabricating sub-line values, and without forcing parity where the evidence does not exist.

The goal is to help reviewers understand the difference between:

- revenue that is cleanly evidenced,
- revenue that is only evidenced as a grouped total,
- revenue sub-lines that remain missing on one or both sides,
- and genuine runtime concerns.

## Source-map philosophy

The key rule in this branch is simple:

- if the available evidence is grouped, the workbook says it is grouped;
- if the available evidence is missing, the workbook says it is missing;
- if a separate sub-line is not supported by committed evidence, we do not invent it.

This is especially important for CO2 and balancing because reviewer expectations often assume more sub-line evidence than the committed source set actually provides.

## Grouped vs separate evidence policy

The workbook and companion reports now distinguish:

- `SEPARATE`
- `GROUPED_ONLY`
- `SEPARATE_REQUESTED_BUT_UNAVAILABLE`

That distinction prevents grouped revenue evidence from being misread as a runtime failure. It also prevents us from silently turning a reviewer request for sub-line transparency into a made-up split.

## Evidence-quality methodology

The dedicated source-map reports use the following evidence-quality levels:

- `HIGH`
- `MEDIUM`
- `LOW`
- `MISSING`

These ratings describe the quality of committed evidence, not the quality of the runtime engine itself.

## Runtime vs Excel handling

This branch preserves the following discipline:

- runtime aggregate revenue stays aggregate if that is all the runtime export exposes,
- Excel grouped evidence stays grouped if that is all the committed extraction supports,
- standalone CO2 or balancing values are never synthesized from totals.

That means some rows remain explicitly limited, but the limitation is now explained more clearly for reviewers.

## Governance interpretation

The CO2/balancing layer is mostly an evidence-quality and source-map issue. It is not treated as proof of a runtime revenue defect by default.

This branch explicitly preserves:

- G20 remains `BLOCKED`
- R99/R102 remain `NOT APPROVED`

The new workbook content helps reviewers understand the limitations. It does not approve them.

## Reviewer guidance

Reviewers should read the new `CO2 & Balancing Reconciliation` sheet as a source-quality explainer:

- `PASS` means the row is supported cleanly by current evidence.
- `GROUPED_SOURCE_ONLY` means the current sources support only a grouped revenue view.
- `MISSING_EVIDENCE` means the requested split is not available in the committed evidence set.
- `EVIDENCE_LIMITATION` means the data exists only at a broader level than the desired reviewer split.
- `GOVERNANCE_REVIEW` means interpretation still matters for closeout discussion.

Grouped evidence does not imply a hidden runtime bug. It means the current reporting evidence surface is narrower than the desired review lens.

## Known limitations

- CO2 and balancing remain weakly evidenced as separate rows.
- Some revenue interpretation still depends on grouped totals.
- This branch does not introduce deeper Excel extraction work.
- This branch does not add new runtime revenue fields.

## No runtime changes statement

This document is the branch's no runtime changes statement. No runtime revenue formulas, no revenue engine logic, no waterfall logic, no SHL logic, no tax logic, and no governance gates are changed here.
