# Demo Q&A Guardrail

This file is the **safe Q&A guardrail for demos**. It is a
companion to the B11 commercial messaging guardrail and the
B19 demo script guardrail. It governs the answers that may be
given to audience questions during a demo (live or recorded).

> **This guardrail is internal governance. It is not a
> marketing playbook. It is not a sales enablement tool. It
> is not a customer reference. It is not external validation.
> It is not a marketing launch approval.**
>
> **Claude review is separate.** The Phase 51N checkpoint
> includes a Claude review preparation pack on the Agent A
> side; Claude review itself is handled outside this branch.
> The Q&A guardrail does not represent Claude review as
> completed.

---

## 1. Why this guardrail exists

Live demos invite audience questions. The audience may ask
about bankability, audit, certification, regulatory approval,
production readiness, or investment advice. A wrong answer
can create an external claim that the project is not in a
position to support.

The B11 commercial messaging guardrail defines the language
rules. The B19 demo script guardrail defines the demo flow
and the prohibited demo claims. This file (B22) adds the
**Q&A layer** — the answers to specific questions that the
demo presenter may face.

The answers are **conservative**. They are designed to:

* Avoid creating any external claim.
* Acknowledge the no-go list (B1) without restating it in
  every answer.
* Refer the audience to the appropriate B-track document
  when the question is out of scope.
* Avoid investment advice, guaranteed returns, bankability,
  audit / certification / regulatory / SaaS claims.

## 2. Color-coding of answers

Each Q&A item is color-coded:

* **Green** — safe to use in any channel without further
  review. Project-internal statement that does not authorize
  any external claim.
* **Yellow** — consistent with the no-go list but missing
  required context. May be used only with the documented
  context.
* **Red** — prohibited in any channel. Listed in the
  prohibited claims register.

The full per-question matrix is in
`reports/commercial/qa_claims_matrix.json` (B22, machine-
readable). It maps each question to a green / yellow / red
answer, the required context, the no-go claim risk, the
escalation trigger, and the source-of-truth pointer.

## 3. Approved answer snippets (green)

The following answer snippets are green. They may be used
without further review.

### 3.1 What is Finco1?

> "Finco1 is an internal project-finance screening tool that
> runs the project through a full waterfall schedule —
> revenue, opex, CFADS, debt service, distributions, returns."

* **Color:** green
* **No-go claim risk:** none
* **Source of truth:** B1 no-go list, B11 §1, B19 §1.

### 3.2 What reference projects exist?

> "TUHO Wind 1 and Oborovo Solar PV are reference projects
> with outputs pinned for regression protection."

* **Color:** green
* **No-go claim risk:** none
* **Source of truth:** B11 §1, B19 §1, Phase 51F pins.

### 3.3 What is the state of the pilot?

> "We are running a controlled pilot with real human users
> under the B7 runbook. The pilot is internal validation
> with documented no-go enforcement. The pilot has not yet
> produced a public result."

* **Color:** green
* **No-go claim risk:** none
* **Source of truth:** B11 §1, B19 §1, B7 runbook, B18 launch
  checklist.

### 3.4 Is the model externally validated?

> "No. Finco1 has not been externally validated. External
> validation is a future workstream that is tracked in B16
> (External Review Closeout Tracker) and is not represented
> as completed in this branch."

* **Color:** green
* **No-go claim risk:** none
* **Source of truth:** B1 no-go list, B11 §1, B16 closeout
  tracker.

### 3.5 Is the model in production?

> "No. Finco1 is not in production. The model is in
> internal-validation state. The B8 enterprise SaaS
> readiness tracker explicitly does not represent any
> production claim."

* **Color:** green
* **No-go claim risk:** none
* **Source of truth:** B1 no-go list, B8 tracker, B11 §1.

### 3.6 What is the difference between a generic solar / wind
        project and TUHO / Oborovo?

> "Generic solar and wind are exploratory and unvalidated for
> any external claim. TUHO and Oborovo are specific projects
> with outputs pinned by Phase 51F. The pinned values are
> regression protection, not external validation."

* **Color:** green
* **No-go claim risk:** none
* **Source of truth:** B1 no-go list, B11 §1, B12 heatmap
  HC-003 / HC-004, B19 §1.

## 4. Required-context answers (yellow)

The following answers are yellow. They may be used only with
the documented context.

### 4.1 What is validated?

> "The Phase 51F pins are the only validated outputs at this
> time. They cover five specific metrics for TUHO and five
> specific metrics for Oborovo. The pins are regression
> protection, not external validation."

* **Color:** yellow
* **Required context:** "regression protection, not external
  validation" (mandatory).
* **No-go claim risk:** low; the answer can be misread as
  broader validation. The context is required.
* **Source of truth:** B3 matrix AREA-001 / AREA-002 / AREA-014,
  B11 §1.

### 4.2 What is internally tested?

> "TUHO, Oborovo, senior debt (TUHO / Oborovo scope),
> sponsor economics, distributions (TUHO / Oborovo scope,
> partial pin), Excel export, persistence / scenarios, and
> UI warnings are internally tested. The B3 matrix and the
> B12 heatmap are the source of truth for what is internally
> tested vs what is exploratory or pinned."

* **Color:** yellow
* **Required context:** "the B3 matrix and the B12 heatmap
  are the source of truth" (mandatory).
* **No-go claim risk:** low; the answer is correct but a
  listener may infer broader internal testing. The context
  is required.
* **Source of truth:** B3 matrix, B12 heatmap, B11 §1.

### 4.3 What is exploratory?

> "Generic solar and generic wind are exploratory. The
> B2 reference acquisition framework is in place; zero
> references have been acquired. The B2 framework is a
> preparation, not a validation."

* **Color:** yellow
* **Required context:** "B2 framework is a preparation, not
  a validation" (mandatory).
* **No-go claim risk:** low; the answer is correct. The
  context is required.
* **Source of truth:** B3 matrix AREA-003 / AREA-004, B2
  framework, B11 §1.

### 4.4 What is blocked?

> "G20 is BLOCKED. R99 and R102 are NOT APPROVED.
> partial_pay_sweep and flat / min DSCR sculpting are not
> promoted. These are explicit project decisions governed by
> the B1 no-go list."

* **Color:** yellow
* **Required context:** "explicit project decisions governed
  by the B1 no-go list" (mandatory).
* **No-go claim risk:** low; the answer is correct. The
  context is required.
* **Source of truth:** B1 no-go list, B11 §1.

### 4.5 What is the state of the Phase 51N checkpoint?

> "Phase 51N is a post-M2 route extraction checkpoint + Agent
> B docs integration + Claude review preparation pack. It is
> documentation and evidence preparation, not external
> validation. Claude review itself is separate and is not
> represented as completed."

* **Color:** yellow
* **Required context:** "documentation and evidence
  preparation, not external validation" + "Claude review
  itself is separate and is not represented as completed"
  (both mandatory).
* **No-go claim risk:** low; the answer is correct. The
  context is required.
* **Source of truth:** B3 matrix AREA-020, B12 heatmap
  HC-019, B14 refresh tracker, B16 closeout tracker.

## 5. Prohibited answers (red)

The following answers are red. They are prohibited in any
channel. The full prohibited claims register is in
`docs/commercial/prohibited_claims_register.md` (B11).

### 5.1 Is Finco1 bankable?

> **Prohibited.** Any answer that uses the word "bankable" or
> implies lender / bank / credit-policy alignment is
> prohibited. The correct red response is: "Finco1 is not a
> lender / bank / audit / certification / regulatory / SaaS
> -grade product. Bankability is not in scope for this
> project at this time."

* **Color:** red
* **No-go claim risk:** high. Any affirmative answer creates
  a lender / bank claim.
* **Escalation trigger:** if the audience presses for a
  bankability claim, the demo presenter refers the question
  to the project lead and ends the discussion.

### 5.2 Can a lender rely on this?

> **Prohibited.** Any answer that implies lender reliance is
> prohibited. The correct red response is: "Finco1 is an
> internal screening tool. It is not a substitute for lender
> / bank / audit / regulatory review. A lender's reliance
> decision is the lender's, not the project's."

* **Color:** red
* **No-go claim risk:** high.
* **Escalation trigger:** refer to the project lead.

### 5.3 Has Finco1 been audited?

> **Prohibited.** The correct red response is: "Finco1 has
> not been externally audited. An external security review is
> a future workstream and is not in scope at this time."

* **Color:** red
* **No-go claim risk:** high.
* **Escalation trigger:** refer to the project lead.

### 5.4 Is Finco1 certified?

> **Prohibited.** The correct red response is: "Finco1 has
> not been certified. No certification has been issued. The
> project does not currently make any certification claim."

* **Color:** red
* **No-go claim risk:** high.
* **Escalation trigger:** refer to the project lead.

### 5.5 Is Finco1 regulatory-approved?

> **Prohibited.** The correct red response is: "Finco1 has
> not been regulatory-approved. No regulator has reviewed or
> approved the model. The project does not currently make
> any regulatory claim."

* **Color:** red
* **No-go claim risk:** high.
* **Escalation trigger:** refer to the project lead.

### 5.6 Is generic solar validated?

> **Prohibited.** The correct red response is: "Generic
> solar is exploratory. It is not validated for any external
> claim. The B2 reference acquisition framework is in
> place; zero references have been acquired."

* **Color:** red
* **No-go claim risk:** high.
* **Escalation trigger:** refer to the project lead.

### 5.7 Is generic wind validated?

> **Prohibited.** The correct red response is: "Generic
> wind is exploratory. It is not validated for any external
> claim. The B2 reference acquisition framework is in
> place; zero references have been acquired."

* **Color:** red
* **No-go claim risk:** high.
* **Escalation trigger:** refer to the project lead.

### 5.8 Is Finco1 enterprise SaaS-ready?

> **Prohibited.** The correct red response is: "Finco1 is
> not enterprise SaaS-ready. The B8 enterprise SaaS
> readiness tracker explicitly does not represent any SaaS
> claim. Reaching 100% on the B8 dimension is a multi-year
> effort and is not the current goal."

* **Color:** red
* **No-go claim risk:** high.
* **Escalation trigger:** refer to the project lead.

### 5.9 Is Finco1 production-ready?

> **Prohibited.** The correct red response is: "Finco1 is
> not production-ready. The model is in internal-validation
> state. The B8 architecture dimension is at 65% with a
> target of 80%. Reaching production-ready is a separate,
> gated workstream."

* **Color:** red
* **No-go claim risk:** high.
* **Escalation trigger:** refer to the project lead.

### 5.10 Can users rely on it for investment decisions?

> **Prohibited.** The correct red response is: "Finco1 is
> a screening tool, not an investment advisor. Users must
> not rely on the model's output for any real-world
> investment, lending, credit, or financing decision. The
> B21 pilot user acknowledgement explicitly forbids any such
> reliance."

* **Color:** red
* **No-go claim risk:** high.
* **Escalation trigger:** refer to the project lead.

### 5.11 Does Finco1 provide investment advice?

> **Prohibited.** The correct red response is: "Finco1 does
> not provide investment advice. The model is a screening
> tool. Any investment decision is the user's, not the
> project's."

* **Color:** red
* **No-go claim risk:** high.
* **Escalation trigger:** refer to the project lead.

### 5.12 Are returns guaranteed?

> **Prohibited.** The correct red response is: "Returns are
> not guaranteed. The model is a screening tool, not a
> guarantee instrument. The pilot user acknowledgement
> explicitly forbids any guarantee claim."

* **Color:** red
* **No-go claim risk:** high.
* **Escalation trigger:** refer to the project lead.

### 5.13 What can be said about Claude review while it is in
        progress?

> **Prohibited to claim Claude review is complete.** The
> correct green response (with no claim of completion) is:
> "Claude review is a separate workstream. The Phase 51N
> checkpoint prepared a Claude review pack on the Agent A
> side; Claude review itself is performed outside the
> B-track branch. The Claude review result, when provided,
> will be reflected in B16 (External Review Closeout
> Tracker) only as a separate workstream, never as a side-
> effect of B15."

* **Color:** green (when the response is given as above) /
  red (if the response claims Claude review is complete or
  makes any positive claim about Claude review's findings).
* **No-go claim risk:** medium. Any affirmative claim of
  Claude review approval is a high-risk external claim.
* **Escalation trigger:** refer to the project lead.

### 5.14 What can be said about external review readiness?

> The correct yellow response (with required context) is:
> "External review readiness is tracked in B16 (External
> Review Closeout Tracker). 16 items are `ready_for_external_
> review`; 6 are `pending_internal`; 3 are `pending_pilot`;
> 2 are `pending_external_review`; 1 is `not_applicable`. The
> closeout tracker does not mean external validation has
> occurred."

* **Color:** yellow
* **Required context:** "The closeout tracker does not mean
  external validation has occurred" (mandatory).
* **No-go claim risk:** medium. The answer is correct. The
  context is required.
* **Source of truth:** B16 closeout tracker.

## 6. Required caveats

When a yellow or red answer is given, the demo presenter
includes the required caveat. The caveat is the difference
between a yellow-light statement and a green-light statement.

A caveat is **not** optional. A yellow answer without its
caveat is a guardrail violation, even if the answer alone is
on the no-go list's permitted side.

A red answer is not softened by a caveat. A red answer is
prohibited in any form.

## 7. Escalation triggers

A demo presenter escalates a question to the project lead
when:

* The question is on a red topic and the audience presses
  for an affirmative answer.
* The question is on a topic not covered by the Q&A
  guardrail.
* The question is about a B-track artifact the presenter
  does not have permission to discuss.
* The question is about a potential no-go violation by a
  third party.
* The audience includes a regulator, a journalist, or an
  external auditor.

The escalation is performed in real time. The presenter
defers the question to the project lead and follows up
offline.

## 8. Per-question no-go claim mapping

Each Q&A item is mapped to a no-go claim category. The full
mapping is in `reports/commercial/qa_claims_matrix.json` (B22,
machine-readable). The mapping is used to:

* Determine the color of the answer.
* Determine the required caveat.
* Determine the escalation trigger.
* Audit the Q&A log (if the Q&A is recorded) for no-go
  violations.

## 9. What this guardrail is not

* It is not a marketing playbook. The project does not
  currently do marketing.
* It is not a sales enablement tool. The project does not
  currently have customers.
* It is not a customer reference. The project does not
  currently have customers.
* It is not external validation. The Q&A guardrail is
  internal governance.
* It is not a substitute for the B11 commercial messaging
  guardrail or the B19 demo script guardrail.
* It is not Claude review. Claude review is separate.

## 10. Cross-references

* `reports/commercial/qa_claims_matrix.json` (B22, machine-
  readable)
* `docs/commercial/investor_partner_qa_guardrail.md` (B22)
* `docs/commercial/no_go_claims_commercial_guardrail.md` (B11)
* `docs/commercial/prohibited_claims_register.md` (B11)
* `docs/commercial/approved_demo_language.md` (B11)
* `docs/commercial/demo_script_guardrail.md` (B19)
* `reports/commercial/commercial_claims_review_matrix.json`
  (B11)
* `reports/commercial/demo_claims_checklist.json` (B19)
* `docs/external_review/no_go_claims.md` (B1, no-go list)
* `docs/external_review/external_review_closeout_tracker.md`
  (B16)
* `docs/pilot/pilot_user_acknowledgement.md` (B21)

---

*End of demo Q&A guardrail.*
