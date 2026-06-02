# No-Go Claims & Commercial Messaging Guardrail

This file is the **commercial messaging guardrail** for Finco1. It
governs the language used in sales conversations, demos, pitches,
website copy, investor materials, and any other external-facing
or third-party-facing communication. It builds on the B1
no-go claim list (`docs/external_review/no_go_claims.md`) and the
internal vs external validation boundaries
(`docs/validation/internal_vs_external_validation_boundaries.md`).

> **The commercial messaging guardrail is internal governance. It
> is not a marketing or sales artifact, not a customer reference,
> and not a regulatory or audit deliverable. The guardrail exists
> to prevent external claims that the project is not in a position
> to support.**

---

## 1. Why this guardrail exists

The B1 no-go claim list is the project's hard line on what claims
are off the table. The B1 list is comprehensive but is framed for
an internal and reviewer audience. Commercial messaging is a
different surface: it is repeated, public, and easy to mis-quote.

The guardrail translates the B1 list into language rules for
commercial use. It defines:

* what can be said safely (green language);
* what can be said with care and context (yellow language);
* what must not be said (red language, with the prohibited
  register);
* a per-language review matrix for sales / demo / pitch /
  website / investor / reviewer channels.

## 2. Source of truth

The guardrail is built on the following source-of-truth documents:

* `docs/external_review/no_go_claims.md` (B1, merged in PR #390)
* `docs/validation/internal_vs_external_validation_boundaries.md` (B3)
* `docs/external_review/external_review_package_index.md` (B1)
* `docs/pilot/controlled_pilot_runbook.md` (B7)
* `docs/validation/validation_evidence_matrix.md` (B3)
* `reports/validation/validation_evidence_matrix.json` (B3)

A claim that is inconsistent with any of these is a violation of
the guardrail. A claim that is consistent with these but is
missing required context is a yellow violation; see §4.

## 3. Channel scope

The guardrail applies to the following channels:

* **Sales conversations.** Direct sales calls, demos, follow-ups.
* **Demo language.** Pre-recorded demos, live demo scripts.
* **Pitch.** Investor pitches, partner pitches, conference talks.
* **Website copy.** Marketing site, blog posts, white papers.
* **Investor materials.** Pitch decks, financial models shown to
  investors, due-diligence responses.
* **Reviewer-facing materials.** Reviewer briefings, B1 package
  walkthroughs, data-room Q&A.

The guardrail does **not** apply to:

* Internal project communication (Slack, internal docs).
* Code comments and docstrings.
* Internal governance documents (the B-track artifacts).
* PR descriptions and commit messages.

## 4. Red / yellow / green language

### 4.1 Green language (safe to use)

Green language can be used in any channel without further review.
It is a project-internal statement that does not authorize any
external claim.

* "Finco1 is an internal project-finance screening tool."
* "Finco1 has been used for internal testing on specific reference
  projects (TUHO Wind 1, Oborovo Solar PV)."
* "Finco1 has a controlled-pilot protocol for internal validation
  with real human users."
* "Finco1 has a docs/report governance pack covering model
  scope, validation evidence, pilot runbook, and a roadmap
  tracker."
* "TUHO Wind 1 and Oborovo Solar PV are reference projects with
  outputs pinned for regression protection."
* "Phase 51F guardrails are project-internal refactor protection
  for the model."
* "Generic solar and wind are exploratory and unvalidated for
  external claim."
* "We have not yet performed external validation of the model."

### 4.2 Yellow language (use with care and context)

Yellow language is consistent with the B1 no-go list but is
missing required context. It can be used in any channel **only**
with the documented context. The context is the difference
between a yellow-light statement and a green-light statement.

* "The model is approved for our internal use." — context: pilot
  protocol and B3 matrix.
* "The model produces specific outputs for specific inputs." —
  context: TUHO and Oborovo pin scope, not generic.
* "The model has been internally tested on multiple scenarios." —
  context: enumerate the scenarios, do not generalize.
* "We are running a controlled pilot." — context: B7 runbook, not
  a customer reference.
* "We have a strong engineering posture." — context: not a
  guarantee of any specific output.
* "We are working towards enterprise readiness." — context: B8
  tracker, 10% current, multi-year effort.

A yellow statement **without** its context is a guardrail
violation, even if the statement alone is on the no-go list's
permitted side.

### 4.3 Red language (prohibited)

Red language is prohibited in any commercial channel. Each entry
is in the prohibited claims register
(`docs/commercial/prohibited_claims_register.md`) with a
rationale and a category (lender / audit / certification /
regulatory / SaaS / production / claim / approval / advice).

See `prohibited_claims_register.md` for the full list with
rationales. A short version:

* "bankable" / "lender-approved" / "lender-grade"
* "audited" / "certified" / "accredited"
* "regulatory-approved" / "regulatory-ready" / "filing-ready"
* "enterprise SaaS-ready" / "production-ready" / "SLA-backed"
* "generic solar validated" / "generic wind validated" /
  "generic solar / wind parity"
* "G20 approved" / "G20 ready"
* "R99 approved" / "R102 approved"
* "investment advice" / "buy recommendation"
* "guaranteed returns" / "guaranteed IRR"

## 5. The "internal screening tool" carve-out

The single most important green statement is:

> "Finco1 is an internal project-finance screening tool."

This carve-out is the safe harbor for most commercial
conversation. It is a project-internal statement of what the
project is. It does not authorize any external claim.

The carve-out does **not** allow:

* "It's good enough for your use case." (yellow without context)
* "It works for any solar / wind project." (red — generic solar /
  wind is not validated)
* "It's lender-grade." (red — no lender-grade claim is supported)

The carve-out does allow:

* "It is a screening tool for project-finance decisions." (green)
* "It is in active internal use and pilot." (green)
* "It has a docs/report governance pack." (green)
* "It is not a substitute for lender / bank / audit / regulatory
  review." (green, with the right framing)

## 6. The "controlled pilot" carve-out

A second safe-harbor statement is:

> "We are running a controlled pilot with real human users under
> the B7 runbook."

This carve-out is also green. It is internal validation with a
real human in the loop. It does not authorize any external claim.

The carve-out does **not** allow:

* "We have customers." (red — no customers)
* "We are in production." (red — no production)
* "Our pilot users endorse the model." (red — the pilot user
  acknowledgement forbids this; see
  `docs/pilot/controlled_pilot_runbook.md` §3)

The carve-out does allow:

* "We are running a controlled pilot." (green)
* "We are not yet in production." (green)
* "Our pilot has documented no-go enforcement." (green)
* "Our pilot user is bound by an acknowledgement that
  forbids external-claim language." (green, with the right
  framing)

## 7. The "TUHO and Oborovo reference projects" carve-out

A third safe-harbor statement is:

> "TUHO Wind 1 and Oborovo Solar PV are reference projects with
> outputs pinned for regression protection."

This carve-out is also green, with the right framing. The pin
covers five specific metrics per project, all under the Phase
51F guardrails. The pin is regression protection, not external
validation.

The carve-out does **not** allow:

* "Our model produces the correct output for any wind / solar
  project." (red — generic is not validated)
* "The pin is a guarantee of correctness." (yellow without
  context; pin is regression protection only)
* "The pin is bank-grade." (red — no bank-grade claim)

The carve-out does allow:

* "TUHO and Oborovo are reference projects with outputs pinned
  for regression protection." (green)
* "The pin covers five specific metrics per project." (green)
* "The pin is not external validation." (green, with the right
  framing)

## 8. Reviewer-facing language

The guardrail also applies to reviewer-facing materials. The
reviewer is bound by the B1 no-go list (see
`docs/external_review/reviewer_instructions.md`); the guardrail
adds the following:

* The reviewer is asked to acknowledge the no-go list.
* The reviewer's output is a third-party opinion, not external
  validation.
* The reviewer is forbidden from producing any external-claim
  language.
* A reviewer output that violates the no-go list is not accepted.

The project does not represent the reviewer's output as
lender-grade, bank-grade, audit-grade, certification-grade,
regulatory-grade, or SaaS-grade, regardless of the reviewer's
findings.

## 9. The review matrix

The full per-claim / per-channel review matrix is in
`reports/commercial/commercial_claims_review_matrix.json`. It
lists each red / yellow / green claim category with the channel
in which it may or may not be used, the required context, and
the responsible owner placeholder.

## 10. The prohibited claims register

The full prohibited claims register is in
`docs/commercial/prohibited_claims_register.md`. It lists each
prohibited claim with a rationale and a category. The register
is the source of truth for what must not be said; the review
matrix is the source of truth for what may be said under what
context.

## 11. Approved demo language

A short list of approved demo language snippets is in
`docs/commercial/approved_demo_language.md`. The list is
illustrative; the full review matrix is authoritative.

## 12. Operationalization

The guardrail is operationalized by:

* the prohibited claims register (the source of truth for what
  must not be said);
* the approved demo language (a curated set of green statements
  for demos);
* the commercial claims review matrix (the per-channel / per-claim
  authority grid);
* a process whereby every commercial artifact (slide deck, demo
  script, blog post, website copy) is checked against the
  register before publication;
* training and acknowledgment by anyone who might speak about
  the model externally.

A breach of the guardrail is a serious issue. The remedy is to
revert the breach, identify how it happened, and update the
process to prevent recurrence.

## 13. What this guardrail is not

* It is not a marketing playbook.
* It is not a sales enablement tool.
* It is not a customer reference.
* It is not external validation.
* It is not a substitute for the B1 no-go claim list or any
  B-track artifact.

## 14. Cross-references

* `docs/external_review/no_go_claims.md` (B1, source of truth)
* `docs/commercial/prohibited_claims_register.md` (B11)
* `docs/commercial/approved_demo_language.md` (B11)
* `reports/commercial/commercial_claims_review_matrix.json` (B11)
* `docs/validation/internal_vs_external_validation_boundaries.md` (B3)
* `docs/external_review/external_review_package_index.md` (B1)
* `docs/pilot/controlled_pilot_runbook.md` (B7)
* `docs/validation/validation_evidence_matrix.md` (B3)

---

*End of no-go claims & commercial messaging guardrail.*
