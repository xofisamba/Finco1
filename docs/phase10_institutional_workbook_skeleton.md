# Phase 10 Institutional Workbook Skeleton

## Executive summary

This branch adds the first standardized institutional workbook skeleton for Phase 10. It creates a structured workbook order for lender review, audit workflows, parity review, governance review, and investment committee packages while staying inside the existing export architecture.

This is a workbook foundation, not a final bankability pack and not a parity workbook rewrite.

No runtime formulas, waterfall logic, SHL mechanics, TaxBridge behavior, DistributionAccount authority, project factories, or runtime outputs changed.

G20 remains `BLOCKED`.

R99/R102 remains `NOT APPROVED`.

## Workbook architecture

The institutional workbook skeleton is generated from `app/export/institutional_workbook.py`.

Standard sheet order:

1. Cover
2. Governance
3. Runtime Summary
4. Inputs
5. Construction
6. OPEX
7. CAPEX
8. Revenue
9. Senior Debt
10. SHL
11. Tax
12. P&L
13. Cash Flow
14. Balance Sheet
15. Audit
16. Gap Register

The workbook already has institutional structure even where detailed sheet bindings are still pending.

## Sheet order rationale

- `Cover` and `Governance` front-load provenance and review status.
- `Runtime Summary` provides an immediately usable snapshot from existing runtime outputs.
- Core operating and financing sections follow a lender-review sequence.
- `Audit` and `Gap Register` keep downstream review and follow-up sheets at the end of the pack.

## Provenance strategy

Every workbook carries:

- project
- generated timestamp
- export type
- runtime versus preview marker
- source branch if available
- governance labels

This metadata appears on the `Cover` sheet and is repeated in the sheet header blocks so the workbook remains reviewable even when sheets are separated or printed.

## Governance strategy

The `Governance` sheet explicitly records:

- governance status
- G20 status
- R99/R102 status
- export type
- source branch
- generated timestamp

The workbook is governance-sensitive but does not imply approval. It preserves the current platform position:

- G20 is still blocked pending governance/stakeholder acceptance.
- R99/R102 runtime promotion remains not approved.

## Runtime integration strategy

The `Runtime Summary` sheet uses the existing Phase 10 runtime summary foundation. It exports existing runtime values only:

- active project
- project IRR
- equity IRR
- total revenue
- total EBITDA
- total OPEX
- average DSCR
- minimum DSCR
- total distributions
- total SHL service
- G20 status
- R99/R102 status

No workbook formulas recalculate the model. The workbook consumes the existing runtime summary builder and formats the result for institutional review.

## Placeholder strategy

Sheets that are not yet fully bound use a structured placeholder:

`Phase 10 placeholder - runtime binding pending`

This keeps the workbook honest and reviewer-friendly without fabricating values.

## Formatting conventions

The skeleton applies consistent workbook conventions:

- fixed sheet order
- freeze panes
- section headers
- provenance banner rows
- consistent widths and wrapped notes
- institutional review-friendly labeling

The goal is to feel like an infrastructure project finance review pack rather than a raw CSV dump.

## Downloads and registry integration

The workbook skeleton is now a first-class Phase 10 export artifact:

- route: `/exports/institutional-workbook.xlsx?project=tuho|oborovo`
- export registry entry added
- Downloads / Audit panel card added
- workbook sheet map report added

## Known limitations

- Only `Cover`, `Governance`, and `Runtime Summary` are currently bound with live content.
- Detailed `Inputs`, `Construction`, `OPEX`, `CAPEX`, `Revenue`, `Debt`, `SHL`, `Tax`, `P&L`, `Cash Flow`, `Balance Sheet`, `Audit`, and `Gap Register` sheets are still placeholders.
- This branch does not change Excel export engine architecture beyond adding the skeleton path.
- This branch does not implement persistence, audit history, parity closeout automation, or runtime promotion logic.

## Future workbook roadmap

Recommended follow-on work:

1. Bind existing exportable sections into the placeholder sheets in institutional order.
2. Add provenance manifests per workbook artifact.
3. Add parity/gap worksheets where evidence already exists.
4. Add lender-review navigation aids once sheet bindings deepen.
5. Keep runtime authority separate from workbook presentation unless explicitly approved in a later branch.

## No runtime changes statement

This branch is export, workbook, docs, report, and UI presentation work only.

It does not change:

- runtime formulas
- waterfall logic
- SHL mechanics
- TaxBridge logic
- DistributionAccount authority
- R99/R102 behavior
- G20 status
- project factory defaults
