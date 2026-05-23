# Phase 11 Institutional Export Product Polish

## Export polish philosophy

Phase 11 begins after the calibration and governance-hardening layers are already in place. The goal of this branch is to make the workbook ecosystem feel more institutional, more usable in review meetings, and more consistent as a product surface.

This is a presentation and reviewer-experience branch. It does not change runtime authority, formulas, or governance outcomes.

## Reviewer UX strategy

The workbook now treats the review journey as intentional:

- Cover for orientation and key metrics,
- Navigation for sheet access and legend,
- Executive Dashboard as the primary entry point for non-engineering reviewers,
- Review Signoff / Governance Timeline / Readiness Matrix for workflow,
- discipline sheets for detailed review,
- and Reviewer Notes for interpretation support.

That structure is meant to work for IC reviewers, lenders, auditors, and engineers without forcing them into the same reading order.

## Institutional formatting strategy

This branch standardizes:

- title hierarchy,
- metadata placement,
- reviewer callouts,
- governance banners,
- freeze panes,
- print-title rows,
- page-fit settings,
- footer/header provenance,
- and sheet-level readability.

The target is a board-ready and PDF-friendly workbook rather than a technical export dump.

## Print / PDF strategy

Major sheets now carry explicit print settings so the workbook remains readable when exported to PDF or used in meeting packets:

- repeated title rows,
- fit-to-page behavior,
- consistent orientation,
- and sheet headers/footers with provenance context.

## Navigation strategy

Navigation is now layered:

- the Cover sheet introduces the pack,
- the Navigation sheet acts as an index and legend,
- each major sheet retains a return path,
- and reviewer-specific paths are documented in the Phase 11 navigation report.

## Governance presentation strategy

Governance framing remains explicit and unchanged:

- `G20` remains `BLOCKED`
- `R99/R102` remain `NOT APPROVED`

The polish layer makes those states easier to understand. It does not weaken or bypass them.

## Workbook consistency strategy

The branch also standardizes workbook metadata and export descriptions so the workbook ecosystem reads as one coordinated product surface instead of a set of disconnected artifacts.

## Known limitations

- This branch does not resolve evidence gaps.
- This branch does not create parity plugs.
- This branch does not change IRR logic, waterfall logic, SHL logic, tax logic, or runtime authority.
- Some review items remain governance or evidence questions by design.

## No runtime changes statement

No runtime/model formulas are changed in this branch. This is export polish, workbook UX, formatting, metadata, and reviewer-flow work only.
