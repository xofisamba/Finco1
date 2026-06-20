# External Pilot Documentation Review

Scope: review all pilot-facing documentation for calibration/factory-project/
internal-terminology leakage and propose cleanup recommendations.

## Findings by file

### `docs/external_pilot_guide.md`

| Line | Term | Issue | Recommendation |
|---|---|---|---|
| 100 | "Excel-parity validation/validated" | Internal QA terminology presented to external pilots without explanation | Replace with "validated against reference models" |
| 131 | "Excel-parity" | Same as above | Same replacement |
| 139 | "R99/R102 promoted workflow" | Internal governance gate codes with no external-facing explanation | Remove the R99/R102 codes from pilot-facing prose; if the underlying limitation must be communicated, describe it in plain language (e.g. "certain audit-only fields are not yet used in cash routing decisions") |

### `app/templates/known_limitations_page.html`

| Line | Term | Issue | Recommendation |
|---|---|---|---|
| 113 | `<strong>R99/R102 promoted workflow</strong> — R99/R102 are audit-only fields, presented for traceability only. They are not approved for runtime cash routing, distribution triggers, or SHL service decisions.` | Verified, real, unredacted internal gate-code reference on a user-facing limitations page | Reword without the R99/R102 codes: "Certain audit-only input fields are shown for traceability only and are not yet used in cash routing, distribution triggers, or SHL service decisions." Preserves the substantive disclosure, removes internal code names. |

### `docs/pilot_user_guide.md`

| Line(s) | Term | Issue | Recommendation |
|---|---|---|---|
| 22 | "frozen-template" | Internal QA jargon | Reword as "fixed starting template" or remove from external-facing copy |
| 28 | "parity evidence" | Internal QA jargon | Reword as "model accuracy checks" |
| 36-40 | "Parity Workbook" | Names an internal artifact | Remove or rename if this artifact is ever exposed externally |
| 63 | "factory mode" | Internal dev-tool wording | Reword as "template mode" or remove |
| 79 | "Audit / Parity tab" | Internal QA naming | Rename to a user-facing label if this tab is exposed to pilots, otherwise mark this doc as internal-only |
| 106, 127 | (additional QA-jargon references) | Same family of issues | Same treatment |

**Structural recommendation:** This file reads like an internal QA review
checklist, not an external pilot guide. The content and tone are
appropriate for an internal audience but high-risk if shared externally
under its current name. Recommend splitting it into two documents:

- An external-facing `docs/pilot_user_guide.md` containing only the
  plain-language onboarding content a pilot user actually needs.
- A new internal-only `docs/internal_audit_guide.md` (or similar) that
  retains all QA/parity/audit terminology for internal reviewers.

## Summary

| Doc | Classification | Action needed |
|---|---|---|
| `docs/external_pilot_guide.md` | (B) audit-adjacent prose in an otherwise external doc | Replace 3 terms (lines 100, 131, 139) |
| `app/templates/known_limitations_page.html` | (A) user-facing limitations page | Reword 1 bullet (line 113) to drop R99/R102 codes |
| `docs/pilot_user_guide.md` | (B/C) internal QA checklist mislabeled as a pilot guide | Structural split recommended; not a simple terminology swap |

## Constraints respected

None of the recommendations above touch R99/R102/G20 promotion *state* or
logic — only the textual presentation of references to those codes in
documentation. No engine, persistence, or governance-state changes are
implied or required.
