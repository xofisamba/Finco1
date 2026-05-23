# Phase 10 Runtime-to-Workbook Binding

## Executive summary

This branch moves the institutional workbook from a pure skeleton to a runtime-bound review export. It keeps the existing workbook order and provenance strategy, then replaces placeholder-only sheets with structured content sourced from existing project context, existing runtime outputs, existing output-table builders, and the existing offline financial-statements assembly.

This is workbook binding and presentation work only.

It does not change:

- runtime formulas
- waterfall logic
- SHL mechanics
- TaxBridge logic
- DistributionAccount authority
- project factories
- OPEX engine behavior
- SeniorDebtSizing behavior
- R99/R102 behavior
- G20 status

G20 remains `BLOCKED`.

R99/R102 remains `NOT APPROVED`.

## Runtime-bound sheets

The workbook now binds the following sheets with structured content:

- `Inputs`
- `Construction`
- `OPEX`
- `CAPEX`
- `Revenue`
- `Senior Debt`
- `SHL`
- `Tax`
- `P&L`
- `Cash Flow`
- `Balance Sheet`
- `Audit`
- `Gap Register`

`Cover`, `Governance`, and `Runtime Summary` remain in place from the skeleton foundation.

## Source strategy

The workbook uses three existing source layers:

1. `ProjectContext`
   Used for read-only project metadata and factory/template assumptions.

2. Runtime waterfall result
   Used for runtime totals, runtime period fields, debt/SHL balances, distributions, DSCR, and other live outputs.

3. Offline financial-statements assembly
   Used for workbook-friendly `P&L`, `Tax`, `Cash Flow`, and `Balance Sheet` sections without introducing new formulas into the workbook export layer.

This keeps the authority chain explicit and avoids duplicating model logic in the export code.

## Runtime versus template assumptions

Every populated sheet distinguishes between:

- runtime-derived values
- template or factory assumptions
- review-only notes

The intent is to make it obvious which numbers are authoritative runtime outputs and which values are assumption anchors or workbook context.

## Sheet coverage

### Inputs

Now includes:

- project metadata
- technology
- country
- capacity
- COD / financial close
- construction duration
- governance labels
- existing input-summary table

### Construction

Now includes:

- construction timing anchors
- total CAPEX
- IDC
- bank fees
- debt / SHL / sponsor funding anchors

This sheet remains a summary binding, not a full construction spend-curve export.

### OPEX

Now includes:

- runtime total OPEX
- factory Y1 OPEX
- contingency method
- contingency percentage
- OPEX line items

### CAPEX

Now includes:

- total CAPEX
- debt and SHL funding anchors
- share capital / share premium anchors
- implied funding remainder for transparency
- existing CAPEX summary helper output
- CAPEX item table

### Revenue

Now includes:

- P50 hours
- availability assumptions
- PPA tariff / term / index
- CO2 enablement flag
- runtime total revenue
- runtime period revenue table

### Senior Debt

Now includes:

- senior debt amount
- tenor
- rate assumption
- target DSCR
- runtime average / minimum DSCR
- runtime total debt service
- runtime period debt table

### SHL

Now includes:

- opening SHL anchor including IDC
- SHL rate
- SHL repayment method
- runtime totals for cash interest, PIK, and principal
- runtime period SHL schedule

### Tax

Now includes:

- CIT assumptions
- loss carryforward years
- ATAD inputs where already available
- runtime total cash tax
- runtime total CIT accrual
- runtime tax-bridge period table
- governance notes for R99/R102

### P&L

Now includes a runtime-bound period table using existing assembled statement rows:

- revenue
- OPEX
- depreciation
- EBIT
- senior interest
- SHL interest
- EBT
- fiscal reintegration
- taxable income
- net income
- net dividends

### Cash Flow

Now includes a runtime-bound PF cash waterfall table using existing assembled rows:

- revenue cash
- OPEX cash
- EBITDA cash
- cash tax
- FCF for banks
- senior debt service
- FCF for SHL
- SHL cash interest
- SHL principal
- net dividends

### Balance Sheet

Now includes a runtime-bound period table using existing assembled rows:

- gross fixed assets
- accumulated depreciation
- net fixed assets
- cash
- senior balance
- SHL balance
- retained earnings
- total assets
- total liabilities and equity
- balance check

### Audit

Now includes:

- runtime source notes
- provenance notes
- sheet-level source coverage
- explicit workbook boundary statements

### Gap Register

Now includes existing known workbook/export gaps and conventions, including:

- missing detailed construction spend curve
- missing full OPEX escalator roll-forward
- CAPEX spend-curve detail pending
- R99/R102 governance blocker
- G20 governance blocker
- accepted convention coverage notes

## Institutional formatting strategy

The branch keeps the workbook moving toward lender-review readability by using:

- consistent sheet order
- provenance banner rows
- section headers
- source-labeled sections
- numeric formats
- freeze panes
- wrapped notes
- explicit governance highlighting

The output should read as a structured review workbook, not as a raw CSV dump.

## Remaining limitations

- `Construction` and `CAPEX` remain summary-bound rather than fully schedule-bound.
- `OPEX` does not yet export a full period escalator roll-forward.
- `Revenue` does not yet split every possible sub-line into separate reviewer tabs.
- `Senior Debt` does not yet include expanded covenant analytics.
- `SHL` does not yet include a separate accrued-versus-cash reviewer view.
- `Balance Sheet` does not yet include a full capital-accounts breakout.
- The workbook still depends on existing runtime and assembly layers; it does not replace them.

## Export registry and status reporting

This branch also updates:

- export registry metadata to reflect runtime binding in progress
- workbook sheet map implemented levels
- runtime workbook binding status report

These artifacts document exactly which sheets are bound and which details are still intentionally partial.

## Future roadmap

Natural next steps after this branch:

1. Expand construction and CAPEX schedule binding where an existing exportable source already exists.
2. Add deeper OPEX and revenue sub-line binding without creating workbook-only calculations.
3. Add reviewer navigation and sheet cross-linking once section depth stabilizes.
4. Continue keeping runtime authority separate from workbook presentation unless explicitly approved in a later branch.

## No runtime changes statement

This branch is export binding, workbook presentation, docs, reports, and tests only.

No runtime or model formulas were changed in order to populate the workbook.
