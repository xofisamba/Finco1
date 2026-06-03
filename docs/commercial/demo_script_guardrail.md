# Demo Script Guardrail

This file is the **demo script guardrail** for Finco1. It
governs the language used in demo scripts, sales conversations,
pitches, website copy, investor materials, and reviewer-facing
materials. It builds on the B11 commercial messaging guardrail
and the B1 no-go claim list.

> **This guardrail is internal. It is not external validation,
> not a customer reference, not a marketing launch approval,
> and not a production-readiness statement.** The guardrail
> exists to prevent external claims that the project is not in
> a position to support. It is a refresh / supplement of the
> B11 commercial messaging guardrail with demo-specific rules.
>
> **Claude review is separate.** The Phase 51N checkpoint
> includes a Claude review preparation pack on the Agent A
> side; Claude review itself is handled outside this branch.
> B19 does not depend on Claude review.

---

## 1. Why this guardrail exists

The B11 commercial messaging guardrail
(`docs/commercial/no_go_claims_commercial_guardrail.md`) is the
project-wide rule for commercial messaging. B19 (this file)
adds **demo-specific** rules:

* an **allowed demo flow** (the order in which demo segments
  may be presented);
* **prohibited demo claims** (phrases that may not appear in
  any demo script or live demo, regardless of channel);
* a **per-slide / per-demo-section claim checklist** (a
  per-segment review grid);
* an **explicit "no investment advice / no guaranteed returns
  / no bankability / no SaaS-ready claims"** rule that applies
  to every demo, every time.

The guardrail is a refresh / supplement to B11. It does not
loosen any B11 rule. It does not introduce any new green
language. It tightens the B11 rules for demo-specific contexts.

## 2. Source of truth

The guardrail is built on:

* `docs/commercial/no_go_claims_commercial_guardrail.md` (B11)
* `docs/commercial/prohibited_claims_register.md` (B11)
* `docs/commercial/approved_demo_language.md` (B11)
* `reports/commercial/commercial_claims_review_matrix.json`
  (B11)
* `reports/commercial/demo_claims_checklist.json` (B19,
  machine-readable)
* `docs/external_review/no_go_claims.md` (B1)
* `docs/validation/internal_vs_external_validation_boundaries.md`
  (B3)
* `docs/validation/validation_evidence_matrix.md` (B3 narrative)
* `docs/validation/model_confidence_heatmap.md` (B12)

A claim that is inconsistent with any of these is a violation
of the guardrail. A claim that is consistent with these but is
missing required context is a yellow violation; see §4.

## 3. Allowed demo flow

The allowed demo flow is the order in which demo segments may
be presented. The flow is conservative; it does not introduce
any new green language beyond the B11 approved demo language.

1. **Introduction.** "Finco1 is an internal project-finance
   screening tool." (B11 safe harbor; green.)
2. **Scope statement.** "Finco1 has been used for internal
   testing on specific reference projects (TUHO Wind 1, Oborovo
   Solar PV)." (B11 safe harbor; green.)
3. **Pilot statement.** "We are running a controlled pilot
   with real human users under the B7 runbook." (B11 safe
   harbor; green, with the B7 runbook reference on request.)
4. **Reference projects statement.** "TUHO Wind 1 and Oborovo
   Solar PV are reference projects with outputs pinned for
   regression protection." (B11 safe harbor; green, with the
   Phase 51F pin scope on request.)
5. **Bounded scope statement.** "Generic solar and wind are
   exploratory and unvalidated for external claim." (B11
   safe harbor; green, mandatory before any discussion of
   generic technology.)
6. **No external validation statement.** "Finco1 has not been
   externally validated." (B11 safe harbor; green, mandatory
   before any discussion of validation status.)
7. **Demo run.** A live or recorded demo of the model on a
   documented input set (TUHO inputs, Oborovo inputs, or pilot
   user inputs).
8. **No-go boundary statement.** "Finco1 is not a lender /
   bank / audit / certification / regulatory / SaaS-grade
   product." (B11 safe harbor; green, mandatory before any
   discussion of claims or use cases.)
9. **Q&A.** Answer questions only with the B11 safe harbor
   statements; refer specific claim questions to the no-go
   list.

The flow is a guideline. Segments may be reordered if the
reordering is consistent with the B11 rules. Segments may not
be removed if their content is required (e.g. the generic
solar / wind statement is mandatory before any discussion of
generic technology).

## 4. Prohibited demo claims

The following claims are prohibited in any demo, regardless of
channel:

* **No investment advice.** "Investment advice" / "buy
  recommendation" / "any statement that the user should rely
  on the model's output for a real decision" — prohibited.
* **No guaranteed returns.** "Guaranteed returns" / "guaranteed
  IRR" / "guaranteed NPV" — prohibited.
* **No bankability.** "Bankable" / "lender-grade" /
  "lender-approved" / "ready for credit committee" / "ICG-
  ready" / "credit-policy-aligned" — prohibited.
* **No audit / certification / regulatory claims.**
  "Audited" / "certified" / "accredited" / "regulatory-
  approved" / "regulatory-ready" / "filing-ready" / "compliant
  with any regulatory regime" — prohibited.
* **No SaaS-ready claims.** "Enterprise SaaS-ready" /
  "production-ready" / "SLA-backed" / "warranty-covered" /
  "multi-tenant-ready" / "scalable" (in the sense of "ready
  for enterprise scale") — prohibited.
* **No generic solar / wind claims.** "Generic solar
  validated" / "generic wind validated" / "solar / wind
  parity" / "any solar project" / "any wind project" (in the
  sense of "correct for any solar / wind project") —
  prohibited.
* **No G20 / R99 / R102 claims.** "G20 approved" / "G20
  ready" (G20 is BLOCKED) / "R99 approved" / "R102 approved"
  (R99/R102 are NOT APPROVED) — prohibited.
* **No partial-pay sweep / flat DSCR sculpting claims.**
  "Partial-pay sweep supported" / "flat DSCR sculpting
  supported" (these features are not promoted) — prohibited.
* **No customer reference claims.** "We have customers" /
  "ready for any specific customer" / "production reference"
  — prohibited.
* **No external validation claims.** "Externally validated" /
  "third-party approved" / any claim that the model has been
  approved by a third party — prohibited.
* **No production-readiness claims.** "Production-ready" /
  "ready for any production use" / "ready for any specific
  customer" — prohibited.

A demo that violates the prohibited claims list triggers a
guardrail violation. The remedy is to revert the violation
(scrub the script, edit the recording, or cancel the demo),
identify how it happened, and update the process to prevent
recurrence.

## 5. Per-slide / per-demo-section claim checklist

Each demo slide or demo section must be reviewed against the
following checklist. The checklist is recorded per slide / per
section in the JSON
(`reports/commercial/demo_claims_checklist.json`).

For each slide / section:

* **Slide / section ID** — unique identifier.
* **Slide / section title** — short text.
* **Claim made** — short text.
* **Claim category** — the B11 claim category (CAT-001
  through CAT-017, or a new category if not covered).
* **Color** — green / yellow / red.
* **Required context (if yellow)** — short text.
* **Reviewer** — anonymized identifier of the reviewer.
* **Reviewed at** — ISO-8601 timestamp.
* **Verdict** — `pass` / `fail` / `conditional` / `not_
  applicable`.
* **Notes** — short text.

A slide / section with verdict `fail` is not approved for the
demo. A slide / section with verdict `conditional` is approved
only if the required context is added. A slide / section with
verdict `pass` is approved.

## 6. Explicit "no investment advice / no guaranteed returns /
   no bankability / no SaaS-ready claims" rule

The following four claims categories are **explicitly
prohibited in any demo, any time, regardless of context**:

* **No investment advice.** A demo is not a recommendation to
  invest, lend, or act. A demo is a demonstration of internal
  validation work.
* **No guaranteed returns.** A demo does not guarantee any
  return. The model is a screening tool, not a guarantee
  instrument.
* **No bankability.** A demo does not establish bankability.
  The model is a screening tool, not a bank-grade product.
* **No SaaS-ready claims.** A demo does not establish SaaS
  readiness. The model is internal, not multi-tenant, not
  SLA-backed.

These four rules are absolute. They are not relaxed by the
B11 safe harbor statements. They are not relaxed by the B19
demo flow. They are not relaxed by the B12 heatmap labels.
They are not relaxed by the B3 matrix evidence categories.

A demo that violates any of these four rules triggers a
guardrail violation.

## 7. What this guardrail is not

* It is not a marketing playbook.
* It is not a sales enablement tool.
* It is not a customer reference.
* It is not external validation.
* It is not a substitute for the B11 commercial messaging
  guardrail.
* It is not a relaxation of the B1 no-go claim list.
* It is not a marketing launch approval.

## 8. Cross-references

* `reports/commercial/demo_claims_checklist.json` (B19,
  machine-readable)
* `docs/commercial/no_go_claims_commercial_guardrail.md` (B11)
* `docs/commercial/approved_demo_language.md` (B11)
* `docs/commercial/prohibited_claims_register.md` (B11)
* `reports/commercial/commercial_claims_review_matrix.json`
  (B11)
* `docs/external_review/no_go_claims.md` (B1, no-go list)
* `docs/validation/internal_vs_external_validation_boundaries.md`
  (B3)
* `docs/validation/validation_evidence_matrix.md` (B3 narrative)
* `docs/validation/model_confidence_heatmap.md` (B12)
* `docs/pilot/post_pilot_evidence_update_template.md` (B19)

---

*End of demo script guardrail.*
