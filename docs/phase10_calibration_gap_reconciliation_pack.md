# Phase 10 Calibration Gap Reconciliation Pack

## Purpose

This branch creates a reviewer-grade reconciliation pack for the remaining Excel versus Model calibration gaps without changing runtime logic. The pack is evidence-first:

- what matches is shown explicitly
- what differs is classified explicitly
- what is missing stays marked as `MISSING_EVIDENCE`
- what is governance-only stays separate from runtime authority

Primary artifact:

- `reports/phase10_calibration_reconciliation_pack.xlsx`

Supporting reports:

- `reports/phase10_calibration_gap_register.csv`
- `reports/phase10_calibration_source_inventory.csv`
- `reports/phase10_calibration_reconciliation_summary.csv`

## Methodology

The workbook combines live TUHO runtime outputs with already committed Phase 9 and Phase 10 evidence artifacts. It does not fabricate Excel rows and it does not introduce parity plugs.

Evidence sources used:

- `reports/phase9_tuho_full_line_item_period_bridge.csv`
- `reports/phase9_tuho_shl_period_bridge.csv`
- `reports/phase9_final_tuho_accepted_conventions.csv`
- `reports/phase9_tuho_calibration_gap_register.csv`
- `reports/phase10_runtime_workbook_binding_status.csv`
- live runtime output from the existing TUHO project path

Runtime versus preview discipline:

- runtime-derived values are labeled from runtime sources
- review-only / governance-only lines are labeled as such
- missing Excel evidence remains text-marked, never silently converted to zero
- accepted conventions are documented separately from runtime parity claims

## Classification Policy

Allowed classifications:

- `PASS`
- `WARN`
- `FAIL`
- `ACCEPTED_CONVENTION`
- `MISSING_EVIDENCE`
- `RUNTIME_BINDING_PENDING`
- `GOVERNANCE_BLOCKER`

Every non-`PASS` line includes:

- root cause
- explanation
- recommended action
- governance impact

## Workbook Structure

Workbook tabs:

1. `Executive Summary`
2. `Governance`
3. `Runtime Summary`
4. `Revenue Reconciliation`
5. `OPEX Reconciliation`
6. `Senior Debt Reconciliation`
7. `SHL Reconciliation`
8. `Tax R35-R67-R69`
9. `CFADS Waterfall`
10. `Distributions Sponsor`
11. `Returns Reconciliation`
12. `Gap Register`
13. `Source Inventory`
14. `Accepted Conventions`
15. `Reviewer Notes`

Excel-safe tab names are used where `/` would be invalid in an `.xlsx` sheet title. The full reviewer-facing names are still written inside the sheets.

Horizontal structure:

- periods run across columns as `P1 ... P61`
- each metric is shown as `Excel`, `Model`, and `Delta`
- trailing columns show `Total`, `Status`, `Classification`, `Root Cause`, `Recommended Action`, `Governance Impact`, and `Notes`

## Accepted Conventions Policy

Accepted conventions remain documentation, not runtime fixes. Examples carried into this pack:

- XIRR date convention
- SHL IDC investment-base treatment
- distribution versus dividend definition
- SHL gross accrued versus cash interest versus PIK presentation
- grouped OPEX local-tax / minor rows
- governed R35 residual

These are visible so reviewers can separate convention drift from runtime defects.

## Governance Limits

This branch does not approve any downstream gate.

- G20 remains `BLOCKED`
- R99/R102 remain `NOT APPROVED`
- the reconciliation pack is audit and review evidence only
- stakeholder sign-offs remain pending

The pack can narrow and classify gaps, but it does not redesign:

- waterfall logic
- SHL mechanics
- TaxBridge behavior
- DistributionAccount runtime authority
- OPEX engine behavior

## Future Roadmap

Natural next steps after this pack depend on reviewer feedback:

1. reporting-only reconciliation IRR view if stakeholders require it
2. targeted CO2 or balancing source-map hardening if sub-line parity becomes material
3. deeper tax row extraction if R35/R67/R69 needs a stronger Excel evidence trail
4. governance review once stakeholders accept or reject the documented conventions

## No Runtime Changes

This branch is reporting/export only.

- no runtime formula changes
- no waterfall logic changes
- no SHL logic changes
- no tax logic changes
- no OPEX engine changes
- no DistributionAccount promotion
- no R99/R102 promotion
- no G20 approval
