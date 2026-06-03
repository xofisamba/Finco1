# Controlled Pilot Launch Checklist

This file is the **practical launch checklist** for the
controlled pilot. It is a checklist that the pilot operator
walks through on launch day, with allowed scope, excluded
scope, allowed data, prohibited data, evidence to collect,
screenshots / exports / logs to capture, pass / fail signal,
issue logging process, pilot-user acknowledgement, no-go
language acknowledgement, rollback / stop criteria, and
post-run evidence update handoff.

> **Controlled pilot only. Not a customer reference. Not
> production readiness. Not external validation. Not paid
> pilot authorization.** The paid pilot gate (B13) is separate
> and requires additional gates (PG-01 through PG-14) to be
> passed before any paid pilot can start. B18 does not
> authorize the paid pilot; B18 authorizes the controlled
> internal pilot only.
>
> **Claude review is separate.** The Phase 51N checkpoint
> includes a Claude review preparation pack on the Agent A
> side; Claude review itself is handled outside this branch.
> B18 does not depend on Claude review, and B18 does not
> represent Claude review as completed.

---

## 1. Pilot readiness prerequisites

Before the launch day, the following must be true (per B7 + B9 +
B13 + B14):

* [ ] **B7 runbook readiness checklist all-passed.** 10-item
      checklist in the B7 runbook §2.
* [ ] **B9 execution checklist (11 gates) all-passed.** G0
      through G10 (pilot execution checklist JSON).
* [ ] **B3 matrix reviewed for the pilot scope.** All
      pilot-claim-allowed areas reviewed; the pilot scope is
      covered by `pilot_claim_allowed: true` areas.
* [ ] **B11 commercial messaging guardrail reviewed.** The
      pilot user is briefed on what can and cannot be said
      about the model externally.
* [ ] **B12 heatmap reviewed.** The pilot scope areas are
      correctly labeled in the heatmap.
* [ ] **B13 paid pilot gate (PG-01 through PG-14) NOT
      authorized.** The paid pilot gate is for a different
      stage. B18 is for the controlled internal pilot, not
      the paid pilot.
* [ ] **B14 governance refresh tracker reviewed.** No
      in-flight B-track refresh that would change the pilot
      scope.
* [ ] **B15 governance refresh reviewed.** The B15 refresh
      has been executed and the post-Phase 51N state is
      reflected.
* [ ] **B17 remaining hotspots tracker reviewed.** The pilot
      scope does not include any of the 5 remaining inline
      hotspots (POST /projects/{code}/save-as; POST
      /scenarios/{id}/rename; POST /scenarios/{id}/archive;
      POST /scenarios/{id}/update-overrides; POST
      /scenarios/{id}/select) — these are still inline and
      are not in pilot scope.
* [ ] **B19 post-pilot evidence update template and demo
      script guardrail reviewed.** The pilot operator knows
      the post-pilot procedure.

## 2. Launch day checklist

On launch day, the pilot operator walks through the following:

* [ ] **G0 — Pilot scope and inputs documented.** The
      `pilot_scope_doc.md` exists and is signed by the project
      lead and the pilot user.
* [ ] **G1 — Pilot user identified and acknowledgement
      signed.** The pilot user is identified (anonymized for
      evidence), and the B7 pilot user acknowledgement is
      signed.
* [ ] **G2 — Pilot data loaded; non-pilot data excluded.**
      The data manifest is signed off. Production, customer,
      and NDA data are not loaded.
* [ ] **G3 — Pilot environment isolated.** The pilot
      environment is isolated from production. The isolation
      checklist is passed.
* [ ] **G4 — Pilot run window defined.** The run window
      (start date, end date, hours of operation) is recorded.
* [ ] **G5 — Issue triage in place.** The
      `pilot_issue_triage_process.md` reference is confirmed.
* [ ] **G6 — User feedback protocol in place.** The
      `pilot_user_feedback_protocol.md` reference is
      confirmed.
* [ ] **G7 — Support and incident response in place.** The
      `support_and_incident_response.md` reference is
      confirmed.
* [ ] **G8 — Pilot artifacts storage with retention.** The
      storage location and retention policy are recorded.
* [ ] **G9 — Exit criteria defined.** The success and
      failure criteria are documented per the runbook §7.
* [ ] **G10 — No-go acknowledgement.** The pilot user and
      operator have signed the no-go acknowledgement
      (no-go claim list).

When all G0–G10 are passed, the pilot is authorized to start.

## 3. Allowed scope

The pilot scope is documented in the `pilot_scope_doc.md`. The
scope is one or more of the B3 matrix areas with
`pilot_claim_allowed: true`. The expected candidates are:

* AREA-001 (TUHO) — five pinned metrics, regression
  protection.
* AREA-002 (Oborovo) — five pinned metrics, regression
  protection.
* AREA-008 (Senior debt, TUHO / Oborovo scope) — pinned for
  TUHO and Oborovo only.
* AREA-010 (Sponsor economics) — internally tested, not
  pinned.
* AREA-011 (Distributions, TUHO / Oborovo scope) — partial
  Phase 51F pin (first_distribution_op_idx only).
* AREA-012 (Excel export) — internally tested, not pinned.
* AREA-013 (Persistence / scenarios) — pin refresh pending.
* AREA-016 (B1 external review package) — documentation
  review.
* AREA-017 (UI warnings) — pilot user testing is the
  evidence-gathering step.

The pilot scope is a subset of these, depending on the pilot
goal.

## 4. Excluded scope

The following are explicitly out of scope for the controlled
pilot:

* **Generic solar (AREA-003) and generic wind (AREA-004).**
  `pilot_claim_allowed: false`. If the pilot user attempts a
  generic-solar or generic-wind input set, the run is recorded
  as `scope` per the B7 issue categories and not evaluated
  against pass / fail criteria.
* **BESS / hybrid (AREA-005 / AREA-006).**
  `pilot_claim_allowed: false`.
* **Tax (AREA-007) without sub-area decomposition.**
  `pilot_claim_allowed: false` for the broad area. Tax
  sub-areas (CIT, LCF, ATAD, WHT, depreciation, cash-tax
  timing) are not yet decomposed.
* **SHL (AREA-009).** `pilot_claim_allowed: false`.
* **B9 / B11 / B12 / B13 / B14 / B15 / B16 / B17 / B18 / B19
  governance artifacts.** These are documentation / governance
  artifacts, not pilot-claimable areas.
* **Any of the 5 remaining inline hotspots** (POST
  /projects/{code}/save-as; POST /scenarios/{id}/rename; POST
  /scenarios/{id}/archive; POST
  /scenarios/{id}/update-overrides; POST
  /scenarios/{id}/select) — these are still inline and are
  not in pilot scope.
* **Production / customer / NDA data.** Prohibited by
  isolation rules.
* **Lending / banking / audit / certification / regulatory /
  SaaS use cases.** Prohibited by the no-go list.
* **Customer reference claims, investment advice, guaranteed
  returns, production-readiness claims.** Prohibited by the
  no-go list and the B11 commercial messaging guardrail.

## 5. Allowed data

The pilot can use:

* **TUHO inputs** (the then-inline / now-frozen reference
  template).
* **Oborovo inputs** (the then-inline / now-frozen reference
  template).
* **Pilot user inputs** (anonymized; recorded as part of the
  pilot run evidence).
* **Internal test inputs** (the validation/cases/ inputs).

The pilot cannot use:

* **Production data.**
* **Customer data.**
* **NDA-protected data.**
* **External model outputs** (no claims based on third-party
  model results).

## 6. Evidence to collect

Per the `pilot_evidence_capture_template.md`:

* Run logs (start time, end time, warnings, model output).
* Validation records (expected vs observed, per metric).
* Exports (Excel, with checksums).
* Screenshots (when they document something the run logs
  don't).
* User feedback (anonymized).
* Issue log (category, severity, outcome).

## 7. Pass / fail signal

Per the `pilot_pass_fail_criteria.md`:

* Per-area decisions: `pass` / `fail` / `investigate` /
  `not_evaluated`.
* Per-run decision: `pass` (all `must-pass` metrics pass) /
  `fail` (any `must-pass` metric fails) / `investigate` (any
  `should-pass` metric fails, no `must-pass` metric fails).
* Pilot overall: `pass` / `fail` / `investigate`, per the
  per-run decisions.

A `pass` is a positive internal signal. It is not external
validation. It is not a customer reference. It is not
production readiness.

## 8. Issue logging process

Per the `pilot_issue_triage_process.md`:

* Categories: `bug` / `unexpected-behavior` / `ux` / `doc` /
  `infra` / `scope`.
* Severities: `pilot-blocker` / `high` / `medium` / `low`.
* Resolution windows: `pilot-blocker` immediate, `high` 3
  business days, `medium` 1 week, `low` 2 weeks.
* Outcome: `confirmed_bug` / `known_acceptable_deviation` /
  `transcription_error` / `scope_misalignment` /
  `environment_issue` / `cannot_reproduce` / `open`.

## 9. Pilot-user acknowledgement

The pilot user signs the B7 pilot user acknowledgement,
which:

* Acknowledges that the pilot is internal validation with a
  real human user.
* Acknowledges that the pilot is not external validation,
  not a customer reference, not production readiness.
* Acknowledges the no-go claim list.
* Forbids the pilot user from making any external-claim
  language about the model.
* Records the pilot user's anonymized identifier.
* Records the pilot user's data isolation requirements.

## 10. No-go language acknowledgement

The pilot user signs the no-go language acknowledgement,
which:

* Acknowledges the B1 no-go list.
* Acknowledges the B11 commercial messaging guardrail.
* Forbids the pilot user from making any of the prohibited
  claims during the pilot.
* Records the no-go categories acknowledged (lender, audit,
  saas, claim, approval, advice).

A pilot user who violates the no-go language acknowledgement
triggers a pilot pause and a triage review. The pilot is
paused until the violation is investigated and resolved.

## 11. Rollback / stop criteria

The pilot is stopped or rolled back when any of the following
is observed:

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
procedure (`docs/ops/support_and_incident_response.md`). The
pilot user is informed of the stop. The evidence is preserved.
A post-stop review is conducted.

## 12. Post-run evidence update handoff

When the pilot run window closes, the pilot operator hands
off to the B3 matrix update procedure (B19 post-pilot
evidence update template):

* The per-run evidence is aggregated.
* The per-area decisions are computed.
* The pilot result summary is filed (per the B9 result
  summary template).
* The B3 matrix is updated with the pilot result
  (`current_status`, `evidence_category`, `missing_evidence`,
  `blockers`, `notes`).
* The B12 heatmap is updated if any area's confidence label
  changes.
* The B11 commercial messaging guardrail is reviewed for any
  new claim categories that surfaced during the pilot.
* The B14 governance refresh tracker is updated with any
  follow-up items.

The handoff is signed by the pilot operator and the project
lead.

## 13. What this checklist is not

* It is not a customer satisfaction survey.
* It is not a user research protocol.
* It is not a marketing or sales feedback tool.
* It is not external validation.
* It is not a substitute for the B7 runbook, the B9
  execution pack, the B11 commercial messaging guardrail, the
  B12 heatmap, the B13 paid pilot gate, the B19 post-pilot
  evidence update template, or the B17 remaining hotspots
  tracker.
* It is not paid pilot authorization. The paid pilot gate
  (B13) is a separate stage.

## 14. Cross-references

* `reports/pilot/controlled_pilot_launch_checklist.json` (B18,
  machine-readable)
* `docs/pilot/controlled_pilot_runbook.md` (B7)
* `docs/pilot/pilot_user_feedback_protocol.md` (B7)
* `docs/pilot/pilot_issue_triage_process.md` (B7)
* `docs/ops/support_and_incident_response.md` (B7)
* `docs/pilot/pilot_validation_execution_pack.md` (B9)
* `docs/pilot/pilot_pass_fail_criteria.md` (B9)
* `docs/pilot/pilot_evidence_capture_template.md` (B9)
* `reports/pilot/pilot_execution_checklist.json` (B9)
* `reports/pilot/pilot_result_summary_template.json` (B9)
* `docs/validation/validation_evidence_matrix.md` (B3 narrative)
* `reports/validation/validation_evidence_matrix.json` (B3
  matrix)
* `docs/commercial/no_go_claims_commercial_guardrail.md` (B11)
* `docs/validation/model_confidence_heatmap.md` (B12)
* `docs/pilot/paid_pilot_readiness_gate.md` (B13)
* `docs/governance/agent_a_b_governance_refresh_plan.md` (B14)
* `docs/governance/remaining_hotspots_governance_tracker.md`
  (B17)
* `docs/pilot/post_pilot_evidence_update_template.md` (B19)
* `docs/external_review/no_go_claims.md` (B1, no-go list)

---

*End of controlled pilot launch checklist.*
