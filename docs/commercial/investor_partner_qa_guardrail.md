# Investor / Partner Q&A Guardrail

This file is the **safe Q&A guardrail for investor
conversations and partner discussions**. It is a companion
to the B11 commercial messaging guardrail, the B19 demo
script guardrail, the B22 demo Q&A guardrail, and the B16
external review closeout tracker.

> **This guardrail is internal governance. It is not a
> marketing playbook. It is not a sales enablement tool. It
> is not a customer reference. It is not external validation.
> It is not a marketing launch approval.**
>
> **The project does not currently make any enterprise SaaS
> claim, lender-grade claim, audit-grade claim, or production
> -ready claim. The project does not currently have
> customers. The project does not currently make any
> external claim at all.**
>
> **Claude review is separate.** The Phase 51N checkpoint
> includes a Claude review preparation pack on the Agent A
> side; Claude review itself is handled outside this branch.
> The Q&A guardrail does not represent Claude review as
> completed.

---

## 1. Why this guardrail exists

Investor conversations and partner discussions are a higher-
risk surface than demos. Investors may press for ROI claims,
timeline commitments, or "is this bankable?" framing.
Partners may press for "is this enterprise-ready?" or "can
we use it for our deals?" framing.

The B11 commercial messaging guardrail and the B22 demo
Q&A guardrail define the language rules. This file (B22
investor / partner) adds the **investor / partner specific
Q&A layer** — the answers to specific questions that
investors and partners may ask.

The answers are **conservative**. They are designed to:

* Avoid creating any external claim.
* Acknowledge the no-go list (B1) without restating it in
  every answer.
* Refer the audience to the appropriate B-track document
  when the question is out of scope.
* Avoid investment advice, guaranteed returns, ROI claims,
  bankability, audit / certification / regulatory / SaaS
  claims.
* Avoid timeline commitments that imply production
  readiness, customer references, or external validation.

## 2. Color-coding of answers

Each Q&A item is color-coded:

* **Green** — safe to use in any channel without further
  review.
* **Yellow** — consistent with the no-go list but missing
  required context.
* **Red** — prohibited in any channel.

The full per-question matrix is in
`reports/commercial/qa_claims_matrix.json` (B22, machine-
readable).

## 3. Approved answer snippets (green)

### 3.1 What is Finco1's product status?

> "Finco1 is an internal project-finance screening tool. It
> is in internal-validation state. The B8 enterprise SaaS
> readiness tracker explicitly does not represent any
> production claim."

* **Color:** green
* **No-go claim risk:** none
* **Source of truth:** B1 no-go list, B8 tracker, B11 §1.

### 3.2 What is the current state of the model?

> "The model has 12 service-backed routes and 13 service
> modules, with 5 inline hotspot routes remaining (tracked
> in B17). The model has 21 B3 matrix areas, with TUHO and
> Oborovo as the two narrow-scope targets for promotion to
> approved_for_narrow_scope after B1 review and a controlled
> pilot."

* **Color:** green
* **No-go claim risk:** low
* **Source of truth:** B3 matrix, B8 tracker, B17 remaining
  hotspots tracker.

### 3.3 What is the B-track governance posture?

> "The project has a docs/report governance pack covering
> model scope, validation evidence matrix, controlled pilot
> runbook, enterprise SaaS readiness tracker, pilot
> execution pack, data room index, commercial messaging
> guardrail, model confidence heatmap, paid pilot gate,
> governance refresh plan, external review closeout
> tracker, remaining hotspots tracker, controlled pilot
> launch checklist, post-pilot evidence update template,
> and demo script guardrail. The B-track governance is in
> place; what is pending is execution, not policy."

* **Color:** green
* **No-go claim risk:** low
* **Source of truth:** B1-B19 governance artifacts (PRs
  #390, #394, #398, #413).

### 3.4 What is the B2 generic validation status?

> "B2 generic reference acquisition is a preparation, not a
> validation. The framework is in place; zero references
> have been acquired. Generic solar and wind are explicitly
> exploratory and unvalidated for any external claim."

* **Color:** green
* **No-go claim risk:** none
* **Source of truth:** B2 framework, B3 matrix AREA-003 /
  AREA-004.

### 3.5 What is the relationship between Finco1 and the
        Agent A track?

> "Agent A owns the route / service extraction work in Phase
> 51+ (51G through 51N). The B-track owns the governance
> documentation. Agent B never modifies Agent A files. The
> two tracks coordinate via the B14 governance refresh plan
> and the B17 remaining hotspots tracker."

* **Color:** green
* **No-go claim risk:** none
* **Source of truth:** B14 refresh plan, B17 remaining
  hotspots tracker.

## 4. Required-context answers (yellow)

### 4.1 What is the timeline to production-ready?

> "The B8 enterprise SaaS readiness tracker documents the
> project-internal self-assessment of the dimensions
> required for production-ready. The current state is
> internal-validation. Reaching production-ready is a multi-
> year effort and is not the current goal. We are not
> committing to a specific timeline to production-ready in
> this conversation."

* **Color:** yellow
* **Required context:** "We are not committing to a
  specific timeline to production-ready in this conversation"
  (mandatory).
* **No-go claim risk:** medium. The answer is correct. The
  context is required.
* **Escalation trigger:** if the investor presses for a
  specific date, the presenter refers the question to the
  project lead.

### 4.2 What is the timeline to enterprise SaaS-ready?

> "The B8 enterprise SaaS readiness tracker documents the
> dimensions required for enterprise SaaS readiness. The
> enterprise_saas_readiness dimension is intentionally at
> 10% with a null target. Reaching 100% on that dimension
> requires a separate, dedicated governance change. We are
> not committing to a specific timeline in this
> conversation."

* **Color:** yellow
* **Required context:** "We are not committing to a specific
  timeline in this conversation" (mandatory).
* **No-go claim risk:** medium.
* **Escalation trigger:** if the investor presses for a
  specific date, the presenter refers the question to the
  project lead.

### 4.3 What is the timeline to external validation?

> "External validation is tracked in B16 (External Review
> Closeout Tracker). The B1 external review scaffolding is
> in place; 16 items are `ready_for_external_review` and
> several items are still pending. The actual third-party
> review has not been performed. We are not committing to a
> specific timeline in this conversation."

* **Color:** yellow
* **Required context:** "We are not committing to a specific
  timeline in this conversation" (mandatory).
* **No-go claim risk:** medium.
* **Escalation trigger:** if the investor presses for a
  specific date, the presenter refers the question to the
  project lead.

### 4.4 What is the ROI of the model?

> "We are not providing ROI claims. The model is an
> internal screening tool, not an investment vehicle. Any
> investment decision is the user's, not the project's."

* **Color:** yellow
* **Required context:** "We are not providing ROI claims"
  (mandatory).
* **No-go claim risk:** medium.
* **Escalation trigger:** if the investor presses for a
  specific ROI figure, the presenter refers the question to
  the project lead and ends the discussion.

### 4.5 Can a partner use this for their deals?

> "Finco1 is an internal screening tool. It is not a
> partner-facing product. The B11 commercial messaging
> guardrail explicitly does not authorize partner use. A
> partner engagement would require a separate governance
> change and is not in scope at this time."

* **Color:** yellow
* **Required context:** "A partner engagement would require
  a separate governance change and is not in scope at this
  time" (mandatory).
* **No-go claim risk:** medium.
* **Escalation trigger:** if the partner presses for a
  partner agreement, the presenter refers the question to
  the project lead.

## 5. Prohibited answers (red)

The following answers are red. They are prohibited in any
channel. The full prohibited claims register is in
`docs/commercial/prohibited_claims_register.md` (B11).

### 5.1 Is Finco1 bankable?

> **Prohibited.** Any answer that uses the word "bankable"
> is prohibited. The correct red response is the same as
> the B22 demo Q&A guardrail §5.1.

### 5.2 Can a lender rely on this?

> **Prohibited.** Same as the B22 demo Q&A guardrail §5.2.

### 5.3 Has Finco1 been audited?

> **Prohibited.** Same as the B22 demo Q&A guardrail §5.3.

### 5.4 Is Finco1 certified?

> **Prohibited.** Same as the B22 demo Q&A guardrail §5.4.

### 5.5 Is Finco1 regulatory-approved?

> **Prohibited.** Same as the B22 demo Q&A guardrail §5.5.

### 5.6 Is generic solar / wind validated?

> **Prohibited.** Same as the B22 demo Q&A guardrail §5.6 /
> §5.7.

### 5.7 Is Finco1 enterprise SaaS-ready?

> **Prohibited.** Same as the B22 demo Q&A guardrail §5.8.

### 5.8 Is Finco1 production-ready?

> **Prohibited.** Same as the B22 demo Q&A guardrail §5.9.

### 5.9 Does Finco1 provide investment advice?

> **Prohibited.** Same as the B22 demo Q&A guardrail §5.11.

### 5.10 Are returns guaranteed?

> **Prohibited.** Same as the B22 demo Q&A guardrail §5.12.

### 5.11 Are you raising capital?

> **Prohibited** to comment on capital plans in the context
> of model claims. The correct red response is: "Capital
> plans are not in scope for this conversation. The project
> does not currently make any production-ready or
> enterprise-SaaS-ready claim that would justify a capital
> raise based on the model alone."

* **Color:** red
* **No-go claim risk:** high. Any affirmative answer about
  capital plans based on the model's production / SaaS
  readiness is a high-risk external claim.
* **Escalation trigger:** if the investor presses for capital
  plans, the presenter refers the question to the project
  lead and ends the discussion.

### 5.12 Can a partner sign a deal today?

> **Prohibited.** The correct red response is: "The project
> does not currently have a partner-facing product. A
> partner agreement would require a separate governance
> change and is not in scope at this time. The B11
> commercial messaging guardrail explicitly does not
> authorize partner use."

* **Color:** red
* **No-go claim risk:** high.
* **Escalation trigger:** refer to the project lead.

### 5.13 What can be said about Claude review while it is in
        progress?

> Same as the B22 demo Q&A guardrail §5.13. **Prohibited to
> claim Claude review is complete.** The correct green
> response (with no claim of completion) is: "Claude review
> is a separate workstream. The Phase 51N checkpoint
> prepared a Claude review pack on the Agent A side; Claude
> review itself is performed outside the B-track branch.
> The Claude review result, when provided, will be reflected
> in B16 (External Review Closeout Tracker) only as a
> separate workstream, never as a side-effect of B15."

* **Color:** green (when given as above) / red (if claiming
  completion or making positive claims about findings).
* **No-go claim risk:** medium.
* **Escalation trigger:** refer to the project lead.

### 5.14 What can be said about external review readiness?

> Same as the B22 demo Q&A guardrail §5.14. Yellow with
> required context.

## 6. Required caveats

When a yellow or red answer is given, the presenter includes
the required caveat. A red answer is not softened by a caveat.

## 7. Escalation triggers

A presenter escalates a question to the project lead when:

* The question is on a red topic and the audience presses
  for an affirmative answer.
* The question is about ROI, capital, partner agreement, or
  timeline commitments.
* The question is on a topic not covered by the Q&A
  guardrail.
* The audience includes a regulator, a journalist, an
  external auditor, or a competitive intelligence
  representative.
* A red or yellow answer is given and the audience
  challenges the answer.

The escalation is performed in real time. The presenter
defers the question to the project lead and follows up
offline.

## 8. Per-question no-go claim mapping

Each Q&A item is mapped to a no-go claim category. The full
mapping is in `reports/commercial/qa_claims_matrix.json` (B22,
machine-readable).

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
  guardrail, the B19 demo script guardrail, the B22 demo
  Q&A guardrail, or any B-track artifact.
* It is not Claude review. Claude review is separate.

## 10. Cross-references

* `reports/commercial/qa_claims_matrix.json` (B22, machine-
  readable)
* `docs/commercial/demo_qa_guardrail.md` (B22)
* `docs/commercial/no_go_claims_commercial_guardrail.md` (B11)
* `docs/commercial/prohibited_claims_register.md` (B11)
* `docs/commercial/demo_script_guardrail.md` (B19)
* `docs/external_review/no_go_claims.md` (B1, no-go list)
* `docs/external_review/external_review_closeout_tracker.md`
  (B16)
* `docs/pilot/pilot_user_acknowledgement.md` (B21)

---

*End of investor / partner Q&A guardrail.*
