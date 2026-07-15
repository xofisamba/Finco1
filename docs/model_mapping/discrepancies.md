# Mapping Discrepancies

## v5.3 Corrections

The v5.3 pass corrects semantic evidence errors from earlier drafts without introducing implementation behavior.

## v5.3.1 Support-Metadata Boundary

The preliminary mapping package is authoritative for row inventory only. Its storage claims are explicitly superseded by workbook-verified metadata in the committed source JSON files.

Direct workbook inspection reproduced package metadata noise:

- 330 preliminary hardcode claims are formula-backed by workbook storage.
- 14 depreciation candidate-input formula-backed cells are not verified hardcode evidence.
- 478 scenario active-formula claims disagree with workbook storage.

These discrepancies do not alter runtime behavior or curated canonical mappings. They prevent future implementation work from treating preliminary package fields as editability, scenario, or runtime authority.

### VAT and WHT

VAT rate and reimbursement evidence is recorded only as VAT evidence. WHT reimbursement remains absence-confirmed until a distinct WHT reimbursement source is confirmed.

### Equity Ownership

Sponsor and Investor 1 ownership shares are editable hardcode evidence. Investor 2 ownership share is formula-axis evidence and is not user-editable.

### Thin Capitalization

Thin capitalization toggle, ratio, amount, and percentage concepts remain separate. The ratio evidence is formula-axis evidence; amount and percentage concepts keep their own editable hardcode evidence.

### DSRA

DSRA evidence is label/formula evidence only. No editable DSRA balance source is confirmed in this mapping pass.

### Legal Reserve and Loss Carryforward

Oborovo-only legal reserve and loss-carryforward cap fields are recorded as workbook-only evidence. They are not promoted to runtime fields by this PR.

## Unresolved Items

Items marked `ABSENCE_CONFIRMED` or `UNRESOLVED` are not implementation-ready. Future PRs must either expose backend-authoritative fields or explicitly document that the concept remains outside the product scope.

## Confidentiality Boundary

This document intentionally omits source workbook values and formulas. The committed evidence model records coordinates and semantic classifications only.
