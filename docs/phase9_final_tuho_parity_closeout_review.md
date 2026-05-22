# Phase 9 Final TUHO Parity Closeout Review

## Executive summary

This branch creates the final TUHO parity closeout governance pack using the corrected horizontal reviewer workbook from PR #169 and the independent review result.

Final parity verdict: `ACCEPT WITH MINOR FOLLOW-UP`.

The corrected workbook is suitable as the evidence base for final TUHO parity closeout review. No remaining technical runtime blocker was identified by the post-PR #169 review. G20 is technically unblocked, but it remains governance/stakeholder-acceptance blocked until the explicit stakeholder decisions in this pack are accepted.

No runtime changes were made in this branch.

R99/R102 runtime promotion remains `NOT APPROVED`.

## Scope and non-goals

Scope:

- Summarize final TUHO parity evidence.
- Capture accepted conventions.
- Capture missing evidence and stakeholder decisions.
- Produce G20 gate checklist reports.
- Keep the corrected horizontal workbook as the primary reviewer artifact.

Non-goals:

- No waterfall runtime logic changes.
- No SHL mechanics, repayment timing, interest, PIK, or WHT changes.
- No SeniorDebtSizing changes.
- No TaxBridge runtime changes.
- No DistributionAccount runtime changes.
- No R99/R102 source promotion.
- No Oborovo changes.
- No project factory, runtime flag, UI, or Excel export runtime changes.

## Source artifacts reviewed

- `reports/phase9_tuho_full_line_item_horizontal_review_workbook.xlsx`
- `reports/phase9_tuho_full_line_item_horizontal_summary.csv`
- `reports/phase9_tuho_full_line_item_horizontal_gap_analysis.csv`
- `reports/phase9_tuho_full_line_item_horizontal_source_map.csv`
- `docs/phase9_tuho_full_line_item_horizontal_review_workbook.md`
- Independent review after PR #169

## PR #169 corrected workbook summary

PR #169 fixed the three PR #168 reporting/data-feed defects:

- SHL model rows now use runtime period fields, and P1 opening SHL balance is approximately `32,704 kEUR`.
- Distributions use a single default runtime / legacy source via `distribution_keur`.
- DA-wired/R99 staging is shown separately as audit-only and is not treated as runtime source acceptance.
- Tax/CFADS now wires R35/R67/R69-visible fields where available.

PR #169 status counts:

- `PASS`: 6
- `WARN`: 4
- `FAIL`: 0
- `ACCEPTED_CONVENTION`: 2
- `MISSING_EVIDENCE`: 3
- `BLOCKER`: 2

The two blockers are governance blockers:

- `G20` stakeholder acceptance / gate sign-off
- `R99/R102` runtime promotion not approved

## Independent review result

Independent review verdict: `ACCEPT WITH MINOR FOLLOW-UP`.

Interpretation:

- The corrected workbook is fit for final TUHO parity closeout review.
- No remaining technical runtime blocker was identified.
- G20 can proceed to stakeholder gate review, but it is not approved by this branch.
- R99/R102 runtime promotion remains a separate, unapproved decision.

## Key PASS metrics

- Production: exact horizon match in the corrected pack.
- Revenue: exact horizon match within rounding.
- Senior debt service: runtime field feed corrected and reviewer-visible.
- SHL opening balance: P1 non-zero runtime feed corrected.
- CIT cash / R67: available field wired into Tax/CFADS section.
- CFADS / R69: available field wired into Tax/CFADS section.
- Project IRR: model project IRR is stable in the corrected pack.

## Key WARN metrics

- Equity IRR residual is approximately `-0.29pp` versus the Excel target, based on the post-review governance interpretation. This can be accepted within tolerance if stakeholders approve, or it can trigger a reconciliation IRR reporting-view branch.
- Taxable Income / R35 carries a known governed residual from Phase 6.
- SHL principal timing and distribution interpretation require the flag-state legend and reviewer cover note.
- OPEX/local-tax/minor-row grouping remains a known review convention.

## Accepted conventions

- XIRR construction-date convention.
- SHL IDC investment-base treatment.
- Distribution versus dividend definition.
- SHL cash interest versus gross accrued / PIK presentation.
- OPEX local-tax/minor grouping.
- Taxable Income / R35 governed residual.
- CO2 / balancing sub-line mapping treated as non-blocking follow-up unless stakeholders require separate sub-line proof.

## Missing evidence items

- Reconciliation IRR reporting view is not implemented in the corrected workbook.
- Excel CO2 and balancing sub-lines are not separately mapped.
- Some taxable income row ownership residuals remain documented from Phase 6 and are governed as accepted convention or follow-up.

## Stakeholder decisions required

Stakeholders must decide whether to:

- Accept the equity IRR residual of about `-0.29pp`, or require a reconciliation IRR reporting view.
- Waive reconciliation IRR evidence for G20, or require implementation before gate sign-off.
- Accept distribution/dividend presentation convention.
- Accept SHL IDC investment-base convention.
- Accept the Taxable Income / R35 governed residual.
- Accept CO2/balancing sub-line mapping as non-blocking follow-up.

## G20 status

G20 remains `BLOCKED` pending stakeholder acceptance / gate sign-off.

This branch does not approve G20. It prepares the evidence pack and decision register needed for a G20 governance review.

## R99/R102 status

R99/R102 runtime promotion remains `NOT APPROVED`.

The DA-wired / pre-G20 staging row in the corrected workbook remains audit-only. It is not a runtime source and does not authorize R99/R102 promotion.

## Recommended next phase

If stakeholders accept the decisions in this pack:

- proceed to G20 gate review / R99-R102 final promotion review.

If stakeholders require reconciliation IRR:

- create `phase9-tuho-equity-irr-reporting-view-implementation`.

If stakeholders require separate sub-line evidence:

- create a targeted CO2/balancing or R35/taxable-income reporting branch rather than changing runtime behavior.
