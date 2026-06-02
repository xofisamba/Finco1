# Approved Demo Language

This file is a **curated set of approved language snippets** for
Finco1 demos, sales conversations, pitches, and other commercial
channels. It is illustrative; the **authoritative source** is the
commercial claims review matrix
(`reports/commercial/commercial_claims_review_matrix.json`)
and the prohibited claims register
(`docs/commercial/prohibited_claims_register.md`).

> **Demo language is internal. It is not external validation, not
> a customer reference, and not a production-readiness statement.**
> The snippets below are project-internal statements; they do
> not authorize any external claim. See
> `docs/commercial/no_go_claims_commercial_guardrail.md` for the
> full guardrail.

---

## 1. The three safe-harbor statements

Every demo, sales conversation, and pitch should anchor on the
three safe-harbor statements below. They are the green statements
that do not require further review.

### 1.1 "Internal screening tool"

> "Finco1 is an internal project-finance screening tool."

* **Status:** green
* **Channel scope:** all channels (sales, demo, pitch, website,
  investor, reviewer)
* **Required context:** none
* **Why it is safe:** it is a project-internal statement of what
  the project is. It does not authorize any external claim.

### 1.2 "Controlled pilot"

> "We are running a controlled pilot with real human users under
> the B7 runbook."

* **Status:** green
* **Channel scope:** all channels
* **Required context:** the B7 runbook reference, on request
* **Why it is safe:** the pilot is internal validation with a
  real human in the loop. The pilot user is bound by an
  acknowledgement that forbids external-claim language. The
  pilot is not a customer reference.

### 1.3 "TUHO and Oborovo reference projects"

> "TUHO Wind 1 and Oborovo Solar PV are reference projects with
> outputs pinned for regression protection."

* **Status:** green
* **Channel scope:** all channels
* **Required context:** the Phase 51F pin scope, on request
* **Why it is safe:** the pin covers five specific metrics per
  project. The pin is regression protection, not external
  validation.

## 2. Additional green statements

The following statements are also green. They are short and
specific; they do not require further review.

### 2.1 What the model is

* "Finco1 is a Python-based project-finance model."
* "Finco1 produces a full waterfall schedule (revenue, opex,
  CFADS, debt service, distributions, returns)."
* "Finco1 includes TUHO Wind 1 and Oborovo Solar PV as pinned
  reference projects."
* "Finco1 has a docs/report governance pack covering model
  scope, validation evidence, pilot runbook, and a roadmap
  tracker."
* "Finco1 has Phase 51F guardrails — engine-output golden,
  parity-core lock, and no-service-imports — that prevent
  silent regression."

### 2.2 What the model is not

* "Finco1 is not a lender / bank / audit / certification /
  regulatory / SaaS-grade product."
* "Finco1 has not been externally validated."
* "Generic solar and wind are exploratory and unvalidated for
  external claim."
* "G20, R99, R102, partial_pay_sweep, and flat/min DSCR
  sculpting are not approved."

### 2.3 What the project has

* "The project has a docs/report governance pack with a
  validation evidence matrix, a controlled pilot runbook, and
  an enterprise SaaS readiness tracker."
* "The project has a no-go claim list that prevents
  external-claim language."
* "The project has Phase 51F guardrails that pin TUHO and
  Oborovo outputs and prevent silent regression during refactor."

### 2.4 What the project is doing

* "The project is working towards enterprise readiness. The
  current state is internal; the readiness tracker is
  intentionally conservative."
* "The project is acquiring generic solar and wind reference
  models for future generic validation. Generic claims are not
  supported yet."
* "The project is preparing for an external review of the
  model. The review scaffolding is in place; the review has
  not yet been performed."

### 2.5 What the project is not yet

* "The project is not yet in production."
* "The project has no customers yet."
* "The project has not been externally validated."
* "The project has not been approved for any lender / bank /
  audit / certification / regulatory / SaaS-grade use."

## 3. Yellow statements (use with care and context)

The following statements are yellow: they are consistent with the
B1 no-go list but require context. The required context is
specified.

### 3.1 "The model is approved for our internal use."

* **Status:** yellow
* **Required context:** the pilot protocol (B7) and the B3
  matrix.
* **Why it is yellow:** "approved" can be read as external
  approval. The project has internally approved the model for
  internal use, not externally approved it for any other use.
* **Yellow without context:** the claim implies external
  approval. This is a guardrail violation.

### 3.2 "The model produces specific outputs for specific inputs."

* **Status:** yellow
* **Required context:** the TUHO and Oborovo pin scope, not
  generic.
* **Why it is yellow:** "specific outputs" can be read as
  "any outputs". The pin covers five specific metrics per
  project, not generic outputs.
* **Yellow without context:** the claim implies generic
  correctness. This is a guardrail violation.

### 3.3 "We are running a controlled pilot."

* **Status:** yellow
* **Required context:** the B7 runbook, not a customer
  reference.
* **Why it is yellow:** "running a pilot" can be read as
  "selling". The pilot is internal validation, not a sales
  process.
* **Yellow without context:** the claim implies a customer
  relationship. This is a guardrail violation.

### 3.4 "We are working towards enterprise readiness."

* **Status:** yellow
* **Required context:** the B8 tracker, 10% current, multi-year
  effort.
* **Why it is yellow:** "working towards" can be read as
  "near". The B8 tracker is intentionally conservative.
* **Yellow without context:** the claim implies near-readiness.
  This is a guardrail violation.

## 4. Red statements (prohibited)

The following statements are red: they are prohibited in any
commercial channel. Each is in the prohibited claims register
with a rationale and a category.

### 4.1 Lender / bank

* "bankable"
* "lender-approved" / "lender-grade"
* "ready for credit committee"
* "ICG-ready" / "credit-policy-aligned"
* "acceptable to any specific lender or bank"

### 4.2 Audit / certification / regulatory

* "audited"
* "certified" / "accredited"
* "IFRS-aligned" / "US-GAAP-aligned" (as a representation of
  compliance)
* "regulatory-approved" / "regulatory-ready" / "filing-ready"
* "compliant with any regulatory regime"

### 4.3 SaaS / production / commercial

* "enterprise SaaS-ready"
* "production-ready"
* "SLA-backed" / "warranty-covered"
* "ready for any specific customer"
* "scalable" (in the sense of "ready for enterprise scale")
* "multi-tenant-ready"

### 4.4 Generic validation

* "generic solar validated"
* "generic wind validated"
* "solar / wind parity"
* "any solar project" / "any wind project" (in the sense of
  "the model is correct for any solar / wind project")
* "validation" (used as a noun implying external validation)

### 4.5 Approval of not-approved areas

* "G20 approved" / "G20 ready"
* "R99 approved" / "R102 approved"
* "partial-pay sweep supported" / "flat DSCR sculpting
  supported"
* "any not-approved feature supported"

### 4.6 Advice / guarantees

* "investment advice" / "buy recommendation"
* "guaranteed returns" / "guaranteed IRR"
* "any statement that the user should rely on the model's
  output for a real decision"

## 5. What this list is not

* It is not a marketing playbook. The project does not currently
  do marketing.
* It is not a sales enablement tool. The project does not
  currently have customers.
* It is not a customer reference. The project does not currently
  have customers.
* It is not external validation. It is internal governance.

## 6. Cross-references

* `docs/commercial/no_go_claims_commercial_guardrail.md` (B11)
* `docs/commercial/prohibited_claims_register.md` (B11)
* `reports/commercial/commercial_claims_review_matrix.json` (B11)
* `docs/external_review/no_go_claims.md` (B1)
* `docs/validation/internal_vs_external_validation_boundaries.md` (B3)

---

*End of approved demo language.*
