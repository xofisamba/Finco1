# Phase 9 TUHO Full Line-Item Horizontal Review Workbook

## Executive summary

This branch replaces the PR #168 reviewer pack with a horizontal, human-readable workbook that uses corrected reporting feeds for SHL, distributions, and Tax/CFADS. It is reporting-only: no runtime formulas, waterfall routing, SHL mechanics, R99/R102 logic, factories, or runtime flags changed.

Primary artifact:

- `reports/phase9_tuho_full_line_item_horizontal_review_workbook.xlsx`

Backup CSVs:

- `reports/phase9_tuho_full_line_item_horizontal_summary.csv`
- `reports/phase9_tuho_full_line_item_horizontal_gap_analysis.csv`
- `reports/phase9_tuho_full_line_item_horizontal_source_map.csv`

## What was wrong in PR #168

The independent review found three pack defects:

1. SHL model columns were zero in every period.
2. Distribution model columns were zero or inconsistent and mixed flag states.
3. Tax/CFADS was entirely marked as `MISSING_EVIDENCE`.

Those were reporting/data-feed defects, not runtime waterfall findings.

## What was fixed

### SHL feed fix

The horizontal workbook now sources SHL model rows from runtime period fields and derived opening balances:

- opening balance: `shl_amount_keur + shl_idc_keur` for P1, then prior-period `period.shl_balance_keur`
- gross accrued interest: `period.shl_gross_accrued_interest_keur`
- cash interest paid: `period.shl_interest_keur`
- PIK capitalized: `period.shl_pik_keur`
- principal repaid: `period.shl_principal_keur`
- closing balance: `period.shl_balance_keur`

The model SHL opening balance in P1 is approximately `32,704 kEUR`, so the all-zero defect is closed.

### Distribution feed fix

The workbook uses one authoritative model distribution row:

- `period.distribution_keur` under the `default runtime / legacy path` flag state

The DA-wired / R99 staging view is shown separately as:

- `DA-wired / pre-G20 staging`

That row is explicitly audit-only and must not be treated as runtime source acceptance.

### Tax/CFADS feed fix

Tax/CFADS is no longer entirely missing. The workbook wires available mapped fields:

- taxable income: `period.taxable_income_before_losses_audit_keur`
- CIT cash: `period.corporate_tax_cash_keur`
- CFADS / FCF banks: `period.r69_fcf_banks_keur`

Where sub-lines are still unavailable, the source map uses precise `MISSING_EVIDENCE` reasons rather than generic missing labels.

## Workbook layout

The main sheet is `Horizontal Review`, with periods across columns and metric rows grouped into:

- Operations
- Revenue
- Costs / EBITDA
- Senior Debt
- SHL
- Tax / CFADS
- Distributions
- Returns

Additional sheets:

- `Summary`
- `Gap Analysis`
- `Accepted Conventions`
- `Flag-State Legend`
- `Source Map`

## Status counts

Current reviewer status counts:

- `PASS`: 6
- `WARN`: 4
- `FAIL`: 0
- `ACCEPTED_CONVENTION`: 2
- `MISSING_EVIDENCE`: 3
- `BLOCKER`: 2

The two blockers are governance items, not newly introduced model drift:

- `G20` remains `BLOCKED`
- `R99/R102` runtime promotion remains `NOT APPROVED`

## Accepted conventions

The workbook keeps these as explicit review conventions:

- SHL IDC investment-base treatment
- XIRR construction date convention
- distribution versus dividend definition
- SHL cash interest versus gross accrued / PIK presentation
- DSCR / senior debt service presentation

## Unresolved gaps

Remaining review gaps are intentionally visible:

- Excel CO2 and balancing sub-lines are not separately mapped in the committed extraction.
- Reconciliation IRR is not implemented in this workbook.
- R35/tax basis row ownership still carries known residual review items.
- Default SHL repayment timing and the P25 alignment path remain separated by flag state.

## Governance impact

This workbook fixes the reviewer-facing reporting pack defects but does not approve G20. G20 remains `BLOCKED` pending final parity/gate review.

R99/R102 runtime promotion remains `NOT APPROVED`. The DA-wired row is an annotation only and is not a runtime source.

## Changed-file scope

Only docs, reports, tests, and the workbook generation script are changed. No runtime files were changed.

Recommended next branch if accepted:

- `phase9-final-tuho-parity-closeout-review`
