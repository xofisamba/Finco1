# Model Evidence Taxonomy

This file defines every evidence category used in
`reports/validation/validation_evidence_matrix.json` and explains the
order in which categories are stacked. It is the project's internal
*vocabulary* for talking about how much we know about a given model
area.

The taxonomy is **conservative by intent**. An area is filed under
the *strongest* category that honestly applies, never stronger. If
the reviewer is not sure, the area is moved to the *weaker* category.

---

## 1. Categories, weakest to strongest

### 1.1 `not implemented`

* The code is not present in the repository at the base SHA.
* **No claim of any kind is supported.** Even "the feature does not
  exist" is the only valid statement.
* Examples: a feature on a future roadmap; an export format that has
  not been written yet.

### 1.2 `implemented but unvalidated`

* The code is present, but no test touches it (or no test touches
  the part of it that matters for the area).
* **No claim of any kind is supported.**
* This is the default category for any code that exists but is not
  exercised. Many "obvious" code paths fall here.
* Promotion to a stronger category requires writing and running a
  test that exercises the area and observing it pass.

### 1.3 `exploratory`

* The code is present and *some* test touches it, but the testing is
  research-grade: small samples, ad-hoc inputs, no pinned outputs.
* **No external claim is supported. No pilot claim is supported.**
* This is the appropriate category for generic solar / wind logic
  before generic parity is achieved.
* Promotion to a stronger category requires either (a) golden-parity
  pinning (see §1.5) or (b) pilot-user testing (see §1.7).

### 1.4 `internally tested`

* At least one test exercises the area, with observed pass/fail
  recorded. The reviewer is expected to re-run and confirm.
* **No external claim is supported.** "Internally tested" means the
  project has looked at it; it does not mean anyone outside the
  project has.
* This is the typical category for `domain/**`,
  `app/project_factories.py`, and the broader web / service layer.
* Promotion requires: more tests, or golden-parity pinning, or
  external review, or pilot-user testing — depending on the
  destination category.

### 1.5 `golden-parity tested`

* Outputs of the area are pinned against a known reference. Any
  silent change fails the test.
* **Pinned outputs are not externally validated.** They are pinned
  against regression, not against any external benchmark.
* This is the category for TUHO and Oborovo outputs in the Phase 51F
  engine-output golden guardrail. It is also the appropriate category
  for any future golden output added with the same protocol.
* Promotion requires: external review, or pilot-user testing, or
  promotion to `approved for narrow scope` (still not external).

### 1.6 `pinned / regression-protected`

* The area is covered by a project-internal guardrail that prevents
  silent regression. Phase 51F parity-core lock and
  no-service-imports-main_web/main_api are the canonical examples.
* **Pin / regression protection is not external validation.** It is
  engineering hygiene; it does not authorize any external claim.
* The reviewer should note that the *act* of pinning does not prove
  the pinned value is correct in an absolute sense; it only proves
  the value has not drifted since the pin was set.
* Promotion requires: external review, pilot-user testing, or
  `approved for narrow scope`.

### 1.7 `pilot-user tested`

* A real human has used the feature in a controlled setting, with
  observed pass/fail and qualitative feedback recorded.
* **Pilot-user testing is not external validation.** It is internal
  validation with a real user in the loop.
* This is the appropriate category for areas ready to graduate from
  exploratory or internally-tested to a stronger internal claim, but
  not yet ready for any external claim.
* Promotion requires: external review, or `approved for narrow
  scope`, or a second pilot with broader scope.

### 1.8 `externally reviewed`

* A third party has read the code (or a defined scope of it) and
  produced a written opinion. The B1 external review package
  (PR #390) is the project-internal scaffolding for this; the actual
  review has not yet been performed at the time of writing.
* **External review is not external validation in the lender / bank /
  audit / certification / regulatory / SaaS sense.** It is a
  third-party opinion, which is a precondition for, but not a
  substitute for, any of those.
* The B1 package's no-go claim list (see
  `docs/external_review/no_go_claims.md`) applies to any reviewer
  output: the reviewer is required to acknowledge and not reproduce
  the no-go claims.
* Promotion requires: alignment between the reviewer's findings and
  the project's documented posture, plus any specific actions the
  reviewer requires.

### 1.9 `approved for narrow scope`

* The area is approved for one or more explicitly named narrow use
  cases (e.g. "TUHO Wind 1 only", "Oborovo Solar PV only").
* **Approval is project-internal.** It is not a lender, bank, audit,
  certification, regulatory, or SaaS-grade approval.
* This is the appropriate destination for TUHO and Oborovo after
  golden-parity testing and any required pilot work.
* Promotion requires: an explicit internal approval record, plus
  pilot-user testing or external review in the target scope.

### 1.10 `approved for generic scope`

* The area is approved for general use.
* **No area in this matrix currently claims this level.** Generic
  solar / wind is explicitly exploratory (§1.3).
* Promotion requires, at minimum: (a) successful golden-parity
  testing in the generic case, (b) pilot-user testing in the generic
  case, (c) external review of the generic case, (d) explicit
  internal approval record. All four are required; none alone is
  sufficient.

### 1.11 `blocked`

* The area is intentionally not advancing. G20 is the canonical
  example.
* **A blocked area must not be claimed at any external level.**
* Unblocking requires a dedicated, explicitly approved change. It is
  not a routine operation.

### 1.12 `not approved`

* The area exists in some form (or is referenced in discussions) but
  has not been approved for any scope. R99, R102, `partial_pay_sweep`,
  and flat / min DSCR sculpting are canonical examples.
* **A not-approved area must not be claimed at any external level.**
* Promotion requires, at minimum: (a) a feature-design document, (b)
  internal tests, (c) golden-parity pinning if outputs are involved,
  (d) explicit internal approval record. The standard is the same as
  for any new feature.

## 2. Category order and stacking

The categories are stacked from weakest to strongest (§1.1 to
§1.12). When two categories might both apply, the stronger one wins.
For example, an area that is "internally tested" *and* "pinned" is
filed under `pinned / regression-protected`, because the pin is the
stronger claim.

A special case: `approved for narrow scope` and `approved for generic
scope` are **scope-bound**. An area approved for TUHO is filed under
`approved for narrow scope` for the TUHO scope, and under the
appropriate weaker category for the generic scope. The matrix JSON
uses one row per area; the scope is recorded in `notes`.

## 3. What "external claim" means

The matrix and this taxonomy talk about `external_claim_allowed` and
`pilot_claim_allowed`. These are the only two claim levels the
project uses internally.

* **`external_claim_allowed: true`** — the project is willing to
  state, in writing, to a party outside the project, that the area
  behaves as documented. This is *not* a lender, bank, audit,
  certification, regulatory, or SaaS-grade claim; it is a project
  statement of confidence.
* **`pilot_claim_allowed: true`** — the project is willing to put the
  area in front of a real human in a controlled pilot. This is *not*
  a production claim; it is a controlled-pilot claim.
* Both flags are *false* by default and must be set to *true*
  explicitly with documented evidence.

## 4. What is *not* in this taxonomy

The taxonomy does not include any of the following, because they are
*outside* the project's internal validation vocabulary and would
imply a level of assurance the project does not provide:

* "lender-grade", "bank-grade", "bankable", "ICG-ready", "credit-committee-ready"
* "audited", "certified", "accredited", "IFRS-aligned", "US-GAAP-aligned", "compliant"
* "SaaS-ready", "production-ready", "SLA-backed", "warranty-covered"
* "regulatory-ready", "filing-ready", "assurance-opinion"

These terms appear in the no-go list
(`docs/external_review/no_go_claims.md`) and are not part of the
matrix's vocabulary.

## 5. How a row gets promoted

Promotion to a stronger category is a normal B-track operation, not
a code change. The procedure is:

1. Identify the row to be promoted.
2. Produce the evidence required by the destination category
   (§1.3–§1.10).
3. Update the JSON row, recording:
   * the new `evidence_category`,
   * the new `evidence_files` and `tests_or_reports_to_check`,
   * the new `external_claim_allowed` / `pilot_claim_allowed` values,
   * a short note in `notes` explaining what changed and when.
4. If the promotion crosses an `external_claim_allowed: false →
   true` boundary, also update
   `docs/validation/internal_vs_external_validation_boundaries.md` and
   request a review of the no-go claim list.

## 6. How a row gets demoted

Demotion (to a weaker category) is also a normal B-track operation.
The procedure is:

1. Identify the row to be demoted.
2. Record the demotion reason in `notes`.
3. Update the JSON row.

No external review is required for a demotion. Demotions are
encouraged when evidence is found insufficient; a matrix that
*never* demotes is a matrix that has stopped being honest.

---

*End of model evidence taxonomy.*
