# Phase 10 Excel Parity Export Foundation

## Executive summary

This branch creates the first Phase 10 export/parity foundation layer. It prepares the project for institutional review workflows by centralizing export metadata, adding a standardized runtime summary CSV export, documenting workbook conventions, and improving the Downloads / Audit tab.

This is not final bankability, persistence, SaaS productization, multi-user infrastructure, or R99/R102 promotion.

No runtime formulas, waterfall logic, SHL mechanics, TaxBridge behavior, DistributionAccount runtime authority, project factories, or runtime flags changed.

G20 remains `BLOCKED`.

R99/R102 remains `NOT APPROVED`.

## Export architecture overview

New foundation package:

- `app/export/__init__.py`
- `app/export/registry.py`
- `app/export/runtime_summary.py`

The package has two responsibilities:

1. Maintain a lightweight artifact registry for review and governance exports.
2. Produce standardized runtime summary CSVs from existing runtime outputs.

It deliberately does not recalculate model outputs or mutate runtime results.

## Artifact registry

The registry defines:

- artifact name
- category
- project scope
- format
- runtime versus preview/review/audit label
- governance sensitivity
- current status
- path and notes

Categories:

- `parity`
- `runtime`
- `governance`
- `audit`
- `validation`
- `workbook`
- `source_map`

Registry report:

- `reports/phase10_export_registry.csv`

Current included artifacts:

- TUHO full line-item horizontal review workbook
- TUHO final parity closeout status
- Phase 10 runtime summary export
- Phase 10 export registry
- TUHO horizontal source map
- TUHO horizontal gap analysis
- Financial statements audit workbook

## Runtime summary export conventions

The runtime summary CSV exports:

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

Every row includes provenance metadata:

- project
- timestamp
- runtime/preview distinction
- governance status
- G20 status
- R99/R102 status
- export type
- source branch if available
- notes

Endpoint:

- `/exports/runtime-summary.csv?project=tuho`
- `/exports/runtime-summary.csv?project=oborovo`

The export is labeled `runtime`, never `preview`.

## Workbook organization conventions

Future institutional workbooks should use a consistent organization:

- Cover
- Governance
- Runtime Summary
- Inputs
- OPEX
- CAPEX
- Revenue
- Debt
- SHL
- Tax
- P&L
- Cash Flow
- Balance Sheet
- Audit
- Gap Register

This branch does not implement the full institutional workbook. It defines the convention and implements the minimal export registry/runtime summary foundation.

## Downloads / Audit UI

The Downloads / Audit tab now includes a Phase 10 export registry panel with artifact descriptions, category badges, governance labels, and runtime summary export links.

This is a UI/export presentation improvement only.

## Validation strategy

Tests cover:

- export registry exists
- registry names are unique
- artifact categories are valid
- runtime summary export generates TUHO and Oborovo CSVs
- TUHO and Oborovo exports differ
- runtime exports include timestamps
- runtime exports include governance labels
- runtime exports distinguish runtime from preview
- Downloads tab renders registry entries
- G20 remains blocked
- R99/R102 remains not approved

## Known limitations

- Existing full Excel export is not rewritten.
- No institutional workbook is created yet.
- No persistence backend or export history is introduced.
- No runtime authority is moved to exports.
- R99/R102 promotion remains outside this branch.
- G20 remains a stakeholder/governance decision, not a technical auto-pass.

## Future Phase 10 roadmap

Recommended next steps:

1. Institutional workbook skeleton using the documented sheet order.
2. Export provenance manifest for each generated workbook.
3. Review-package generation for lender/audit workflows.
4. Reconciliation IRR reporting view if stakeholders require it.
5. R99/R102 final promotion review only after governance approval.
