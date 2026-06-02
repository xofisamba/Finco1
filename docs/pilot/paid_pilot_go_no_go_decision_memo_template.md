# Paid Pilot Go / No-Go Decision Memo Template

This file is the **decision memo template** for the gate between
controlled internal pilot and controlled paid pilot, defined in
`docs/pilot/paid_pilot_readiness_gate.md` (B13). The template is
filled in at the gate decision point. A filled-in memo is required
to start the paid pilot; a "go" decision without a memo is a gate
violation.

> **The paid pilot is internal validation with a real human
> user, with an explicit commercial agreement, with documented
> no-go enforcement. It is not a customer reference. It is not
> external validation.** See
> `docs/commercial/no_go_claims_commercial_guardrail.md` (B11)
> and `docs/external_review/no_go_claims.md` (B1).

---

## 1. Memo metadata

* `memo_id` — unique identifier.
* `paid_pilot_name` — the name of the paid pilot (e.g. "Q3 2026
  Internal Validation Pilot").
* `pilot_user_id` — anonymized identifier of the paid pilot user.
* `pilot_operator_id` — identifier of the paid pilot operator.
* `memo_date` — date the memo is finalized.
* `gate_reference` — reference to the B13 gate document
  (`docs/pilot/paid_pilot_readiness_gate.md`).

## 2. Gate status

* **PG-01 — Controlled internal pilot completed.** Status:
  `pending` / `passed` / `failed` / `blocked` / `in_progress`.
  Reference: `reports/pilot/pilot_result_summary_template.json`
  populated for the controlled internal pilot.
* **PG-02 — Pilot result reviewed by project lead.** Status and
  reference.
* **PG-03 — B3 matrix updated with pilot results.** Status and
  reference (commit SHA).
* **PG-04 — B11 commercial messaging guardrail tested.** Status
  and reference.
* **PG-05 — B12 heatmap updated.** Status and reference.
* **PG-06 — Paid pilot user agreement drafted.** Status and
  reference.
* **PG-07 — Paid pilot scope and inputs documented.** Status
  and reference.
* **PG-08 — Paid pilot data isolation verified.** Status and
  reference.
* **PG-09 — Paid pilot environment provisioned.** Status and
  reference.
* **PG-10 — Paid pilot no-go acknowledgement drafted.** Status
  and reference.
* **PG-11 — Paid pilot support / incident response in place.**
  Status and reference.
* **PG-12 — Paid pilot go/no-go decision memo filed.** Status
  (this memo, when finalized).
* **PG-13 — B1 no-go list reviewed against paid pilot scope.**
  Status and reference.
* **PG-14 — B11 commercial messaging guardrail reviewed against
  paid pilot scope.** Status and reference.

All PG-01 through PG-14 must be `passed` for a "go" decision.

## 3. Pilot result summary reference

* `pilot_summary_id` — unique identifier of the controlled
  internal pilot summary.
* `pilot_summary_path` — path to the populated result summary.
* `pilot_decision` — `pass` / `fail` / `investigate` / `not_evaluated`.
* `pilot_decision_rationale` — short text.

## 4. B3 matrix update reference

* `b3_matrix_update_commit` — git commit SHA of the B3 matrix
  update.
* `b3_areas_updated` — list of B3 area IDs.
* `b3_categories_changed` — list of `evidence_category`
  transitions.

## 5. B11 commercial messaging guardrail test reference

* `b11_test_run_id` — unique identifier of the B11 guardrail
  test run.
* `b11_test_run_date` — date.
* `b11_violations_recorded` — count (must be 0 for "go" decision).
* `b11_violations_resolved` — count.

## 6. B12 heatmap update reference

* `b12_heatmap_update_commit` — git commit SHA of the B12
  heatmap update.
* `b12_areas_changed` — list of B12 area IDs.
* `b12_labels_changed` — list of `confidence_label` transitions.

## 7. Paid pilot user agreement reference

* `paid_pilot_agreement_path` — path to the agreement.
* `paid_pilot_agreement_status` — `draft` / `reviewed` /
  `signed`.
* `paid_pilot_agreement_signed_at` — date.
* `paid_pilot_agreement_signed_by_pilot_user` — boolean.
* `paid_pilot_agreement_signed_by_project_lead` — boolean.
* `paid_pilot_agreement_signed_by_legal_placeholder` — boolean
  (placeholder; actual legal review by appropriate party).

## 8. Paid pilot no-go acknowledgement reference

* `no_go_acknowledgement_path` — path to the signed
  acknowledgement.
* `no_go_acknowledgement_signed_at` — date.
* `no_go_acknowledgement_signed_by_pilot_user` — boolean.
* `no_go_acknowledgement_signed_by_pilot_operator` — boolean.
* `no_go_claims_acknowledged` — list of B1 no-go claim categories
  acknowledged (e.g. `lender`, `audit`, `saas`, `claim`,
  `approval`, `advice`).

## 9. Decision

* `decision` — `go` / `no_go` / `conditional_go`.
* `decision_rationale` — short text.
* `decision_date` — date.

A `conditional_go` decision records the conditions in
`decision_conditions` and the resolution plan in
`decision_resolution_plan`. A `no_go` decision records the
remediation in `no_go_remediation`.

## 10. Unresolved blockers

For each unresolved blocker:

* `blocker_id` — unique identifier.
* `blocker_description` — short text.
* `blocker_owner` — responsible owner placeholder.
* `blocker_target_resolution_date` — date.
* `blocker_status` — `open` / `in_progress` / `deferred` /
  `resolved` / `accepted`.

A `go` decision may have unresolved blockers only if the
decision is `conditional_go` and the blockers are recorded in
`decision_conditions`.

## 11. Signatures

* `project_lead_signature` — name, role, signed_at, signature_method.
* `pilot_operator_signature` — name, role, signed_at, signature_method.
* `b_track_owner_signature` — name, role, signed_at, signature_method.
* `legal_placeholder_signature` — name, role, signed_at,
  signature_method (placeholder; actual legal review by
  appropriate party).
* `security_placeholder_signature` — name, role, signed_at,
  signature_method (placeholder; actual security review by
  appropriate party).

A memo is not finalized until at least the project lead and
the b-track owner have signed. The legal and security
placeholders are required for a "go" decision; they are
optional for a "no_go" decision.

## 12. Post-decision actions

After a "go" decision, the post-pilot evidence update process
(see `docs/pilot/paid_pilot_readiness_gate.md` §7) applies. The
memo references the relevant update commits as they are made.

After a "no_go" decision, the no_go_remediation plan is
executed. A future decision memo can be filed after remediation.

## 13. What this template is not

* It is not a contract. The paid pilot user agreement is the
  contract.
* It is not a customer reference.
* It is not external validation.
* It is not a substitute for the B13 gate, the B7 runbook, the
  B9 execution pack, the B11 commercial messaging guardrail, or
  the B12 heatmap.

## 14. Cross-references

* `docs/pilot/paid_pilot_readiness_gate.md` (B13)
* `reports/pilot/paid_pilot_readiness_gate.json` (B13, machine-readable)
* `docs/pilot/controlled_pilot_runbook.md` (B7)
* `docs/pilot/pilot_validation_execution_pack.md` (B9)
* `docs/commercial/no_go_claims_commercial_guardrail.md` (B11)
* `docs/validation/model_confidence_heatmap.md` (B12)
* `docs/external_review/no_go_claims.md` (B1)

---

*End of paid pilot go / no-go decision memo template.*
