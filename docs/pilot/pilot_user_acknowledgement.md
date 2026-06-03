# Pilot User Acknowledgement

This file is the **pilot user acknowledgement template** for the
controlled internal pilot. It is the document that a controlled
pilot participant must accept (i.e. sign) before the pilot
begins.

> **This is not a legal contract.** This is an internal pilot
> acknowledgement template. It is internal governance. The
> project lead assigns actual personnel and any contractual
> terms separately. This document does not give legal advice
> and does not constitute a binding agreement.
>
> **The controlled internal pilot is internal validation. It
> is not external validation, not a customer reference, and
> not production readiness.** The paid pilot gate (B13) is a
> separate stage. This acknowledgement does not authorize the
> paid pilot.
>
> **Claude review is separate.** The Phase 51N checkpoint
> includes a Claude review preparation pack on the Agent A
> side; Claude review itself is handled outside this branch.
> This acknowledgement does not represent Claude review as
> completed.
>
> **Do not claim a pilot has happened unless actual pilot
> results are later provided.** This template is empty at
> package creation. It is populated only when a controlled
> pilot has actually been authorized and a pilot user has
> been onboarded.

---

## 1. Identification

* **Pilot run ID:** `__________________`
* **Pilot user ID (anonymized):** `__________________`
* **Pilot user real name (stored separately, not in this
  public copy):** `__________________`
* **Pilot operator ID:** `__________________`
* **Project lead ID:** `__________________`
* **Acknowledgement date:** `__________________`
* **Acknowledgement version:** `B21 v0.1.0`

## 2. Controlled internal pilot scope

The pilot user acknowledges that the controlled internal
pilot is:

* An **internal validation** activity with a real human user.
* Conducted in a **controlled environment** (per the B7
  runbook, the B9 execution pack, the B18 launch checklist).
* **Not a customer relationship.** The pilot user is not a
  customer.
* **Not a production rollout.** The pilot is internal; the
  model is not exposed to any production setting.
* **Not external validation.** The pilot is internal
  validation, not a third-party review or a regulatory
  approval.
* **Not a paid pilot.** The paid pilot gate (B13) is a
  separate stage and requires additional gates (PG-01
  through PG-14) to be passed.

## 3. No external validation

The pilot user acknowledges that:

* The pilot is **internal validation with a real human in the
  loop**.
* The pilot does **not** constitute external validation of
  the model.
* The pilot does **not** authorize any external claim
  (lender, bank, audit, certification, regulatory, SaaS, or
  otherwise).
* The pilot does **not** establish bankability, lender-grade
  status, audit-grade status, certification-grade status, or
  regulatory-grade status.
* The pilot is **not** a substitute for any third-party
  review.

## 4. No investment advice / no reliance for real-world decisions

The pilot user acknowledges that:

* The model is a **screening tool**, not an investment
  advisor.
* The model output is **not investment advice**.
* The model output is **not a buy recommendation**.
* The model output is **not a guarantee of returns**,
  **guaranteed IRR**, or **guaranteed NPV**.
* The pilot user **must not rely** on the model's output for
  any real-world investment, lending, credit, or financing
  decision.
* The pilot user **must not encourage any third party** to
  rely on the model's output for any real-world decision.

## 5. No customer reference, no public endorsement

The pilot user acknowledges that:

* The pilot user is **not a customer**. The project does not
  currently have customers.
* The pilot user is **not a reference**. The pilot user's
  experience is not a customer reference.
* The pilot user is **forbidden from making any public
  endorsement** of the model.
* The pilot user is **forbidden from making any external
  claim** about the model, in any channel, at any time.
* The pilot user's anonymized identifier may be used
  internally for evidence-tagging purposes only.

## 6. Allowed data

The pilot user acknowledges that the pilot uses:

* **TUHO inputs** (the then-inline / now-frozen reference
  template).
* **Oborovo inputs** (the then-inline / now-frozen reference
  template).
* **Pilot user inputs** (anonymized; recorded as part of the
  pilot run evidence per the B9 evidence-capture template
  and the B20 evidence register).
* **Internal test inputs** (the validation/cases/ inputs).

## 7. Prohibited data

The pilot user acknowledges that the pilot does **not** use:

* **Production data.**
* **Customer data** (the project does not currently have
  customers; this is forward-looking).
* **NDA-protected data** (any data subject to a non-
  disclosure agreement with a third party).
* **External model outputs** (no claims based on third-party
  model results).
* **Personal data** beyond what is necessary for the pilot
  (e.g. the pilot user's name and contact information; no
  financial personal data).

The pilot user agrees to **not introduce** any prohibited
data into the pilot environment. The pilot user agrees to
**report immediately** any accidental introduction of
prohibited data to the pilot operator.

## 8. Confidentiality expectations

The pilot user agrees to:

* Keep **internal pilot details** (issues, evidence, model
  behavior) confidential during the pilot and for the
  duration of the retention period after the pilot closes.
* Keep **internal pilot materials** (this acknowledgement,
  the pilot scope document, the B7 runbook, the B9
  execution pack, the B18 launch checklist) confidential.
* Keep **internal pilot evidence** (run logs, validation
  records, exports, screenshots, user feedback) confidential.
* **Not share** any of the above with any third party
  without the project lead's explicit written consent.
* **Not publish** any of the above in any blog post, social
  media post, conference talk, or external document,
  without the project lead's explicit written consent.

The pilot user understands that the project may share the
anonymized pilot result with the project lead, the pilot
operator, the B-track owner, and the third-party reviewer
(if and when the third-party review is performed and the
reviewer is bound by the no-go claim list).

## 9. Evidence collection consent

The pilot user consents to:

* **Run logs** being collected for each pilot run.
* **Validation records** being collected for each pilot run.
* **Exports** (Excel) being collected for each pilot run.
* **Screenshots** being collected when they document
  something the run logs do not.
* **User feedback** being collected per the B7 pilot user
  feedback protocol (anonymized).
* **Issue log entries** being collected per the B7 pilot
  issue triage process.

The pilot user understands that the evidence is **internal
evidence** and is not used in any external-claim language, in
any marketing material, in any sales conversation, or in any
external review document, without the pilot user's explicit
written consent.

The pilot user's anonymized identifier may be used internally
for evidence-tagging purposes only.

## 10. Issue reporting obligation

The pilot user agrees to:

* **Report any issue** observed during the pilot to the pilot
  operator, per the B7 pilot issue triage process.
* **Report any no-go violation** observed during the pilot
  immediately to the pilot operator.
* **Report any data isolation breach** (production, customer,
  or NDA data accessed) immediately to the pilot operator.
* **Report any security incident** (unauthorized access, data
  leak) immediately to the pilot operator.

The pilot user understands that a failure to report an issue
may compromise the integrity of the pilot and the safety of
the pilot data.

## 11. No-go language acknowledgement

The pilot user acknowledges the B1 no-go claim list
(`docs/external_review/no_go_claims.md`) and the B11
commercial messaging guardrail
(`docs/commercial/no_go_claims_commercial_guardrail.md`).

The pilot user explicitly acknowledges each of the following
no-go categories (per the B1 list):

* [ ] **Lender / bank** — claims about lender / bank /
      bankability.
* [ ] **Audit / certification / regulatory** — claims about
      audit / certification / regulatory.
* [ ] **SaaS / production / commercial** — claims about
      SaaS / production / commercial.
* [ ] **Generic validation** — claims about generic solar /
      generic wind.
* [ ] **Approval of not-approved areas** — claims about G20,
      R99, R102, partial_pay_sweep, flat / min DSCR
      sculpting.
* [ ] **Advice / guarantees** — claims about investment
      advice or guaranteed returns.

The pilot user is **forbidden from making any of the
prohibited claims** during the pilot, in any channel, at any
time. A pilot user who violates the no-go language
acknowledgement triggers a pilot pause and a triage review.
The pilot is paused until the violation is investigated and
resolved.

## 12. User stop / withdrawal right

The pilot user has the **right to stop the pilot at any
time**, for any reason. The pilot user exercises this right
by informing the pilot operator in writing (email, Slack, or
other documented channel).

When the pilot user stops the pilot:

* The pilot run window is closed.
* The evidence collected up to the stop point is preserved
  per the B7 retention policy.
* The pilot user's anonymized identifier is preserved for
  evidence-tagging purposes.
* The pilot user is **not** subject to any penalty, claim,
  or obligation for stopping the pilot.

## 13. Project stop / rollback criteria

The project may stop or roll back the pilot when any of the
following is observed (per the B18 launch checklist):

* A `pilot-blocker` issue that cannot be resolved within the
  pilot run window.
* A no-go claim made or implied by the pilot user or
  operator.
* A data isolation breach (production, customer, or NDA data
  accessed).
* A security incident (unauthorized access, data leak).
* A model output that is outside the documented output range
  for a `must-pass` metric and cannot be explained.
* The pilot user requests a stop.
* The project lead requests a stop.

The stop procedure is per the B7 support / incident response
procedure. The pilot user is informed of the stop. The
evidence is preserved. A post-stop review is conducted.

## 14. Explicit separation from paid pilot authorization

The pilot user acknowledges that:

* The **paid pilot gate (B13)** is a separate stage.
* The paid pilot gate requires additional gates (PG-01
  through PG-14) to be passed.
* The **paid pilot user agreement** is a separate document
  and is not this acknowledgement.
* This acknowledgement does **not** authorize the paid pilot.
* The paid pilot requires the project lead's explicit
  approval, the pilot user agreement being signed separately,
  and the no-go acknowledgement being signed separately.

The pilot user is not a paid pilot user. The pilot is
internal validation with a real human in the loop. The
paid pilot is a separate, gated stage.

## 15. Pilot user signature

* **Pilot user name:** `__________________`
* **Pilot user role:** `__________________`
* **Pilot user signature:** `__________________`
* **Pilot user signed at:** `__________________`
* **Signature method:** `__________________`

## 16. Pilot operator signature

* **Pilot operator name:** `__________________`
* **Pilot operator role:** `__________________`
* **Pilot operator signature:** `__________________`
* **Pilot operator signed at:** `__________________`
* **Signature method:** `__________________`

## 17. Project lead signature

* **Project lead name:** `__________________`
* **Project lead role:** `__________________`
* **Project lead signature:** `__________________`
* **Project lead signed at:** `__________________`
* **Signature method:** `__________________`

## 18. What this acknowledgement is not

* It is not a legal contract. The paid pilot user agreement
  is the contract (separate document; not this one).
* It is not external validation. The pilot is internal
  validation.
* It is not a customer reference. The pilot user is not a
  customer.
* It is not a substitute for any B-track governance
  artifact.
* It is not paid pilot authorization. The paid pilot gate
  (B13) is a separate stage.
* It is not Claude review. Claude review is separate.

## 19. Cross-references

* `reports/pilot/pilot_user_acknowledgement_checklist.json`
  (B21, machine-readable)
* `docs/pilot/pilot_data_handling_notice.md` (B21)
* `docs/pilot/controlled_pilot_runbook.md` (B7)
* `docs/pilot/pilot_user_feedback_protocol.md` (B7)
* `docs/pilot/pilot_issue_triage_process.md` (B7)
* `docs/pilot/pilot_validation_execution_pack.md` (B9)
* `docs/pilot/pilot_evidence_capture_template.md` (B9)
* `docs/pilot/controlled_pilot_launch_checklist.md` (B18)
* `docs/pilot/post_pilot_evidence_update_template.md` (B19)
* `docs/commercial/no_go_claims_commercial_guardrail.md` (B11)
* `docs/external_review/no_go_claims.md` (B1, no-go list)

---

*End of pilot user acknowledgement.*
