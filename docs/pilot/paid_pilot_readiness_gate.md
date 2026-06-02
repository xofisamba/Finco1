# Paid Pilot Readiness Gate

This file is the **paid pilot readiness gate**. It defines the
four stages of pilot progression (internal working product,
controlled internal pilot, controlled paid pilot, enterprise SaaS
readiness), the gate between controlled internal pilot and
controlled paid pilot, the minimum evidence required to cross
that gate, the paid pilot exclusions, the approved pilot scope,
the post-pilot evidence update process, and the unresolved
blocker list.

> **The paid pilot is internal validation with a real human
> user, with an explicit commercial agreement, with documented
> no-go enforcement. It is not a customer reference. It is not
> external validation. It is not a production rollout.** See
> `docs/pilot/controlled_pilot_runbook.md`,
> `docs/external_review/no_go_claims.md`, and
> `docs/commercial/no_go_claims_commercial_guardrail.md`.

---

## 1. The four stages

The Finco1 pilot progression has four stages. The gate between
controlled internal pilot and controlled paid pilot is the
subject of this file. The other transitions are mentioned for
context.

### 1.1 Internal working product

* The model is implemented and tested internally.
* No pilot user has been onboarded.
* No commercial agreement is in place.
* The model is not exposed to any party outside the project.
* **Gate to next stage:** the controlled internal pilot, defined
  in `docs/pilot/controlled_pilot_runbook.md` (B7).

### 1.2 Controlled internal pilot

* A real human user has been onboarded with the B7 acknowledgement.
* The pilot runs in a controlled environment, with documented
  data isolation.
* The pilot produces internal validation evidence.
* No commercial agreement is in place; the pilot is a
  project-internal activity.
* **Gate to next stage:** the controlled paid pilot, defined in
  this file (B13).

### 1.3 Controlled paid pilot

* A real human user has been onboarded with a paid-pilot
  acknowledgement (see §6).
* The pilot runs in a controlled environment, with documented
  data isolation and documented commercial terms.
* The pilot produces internal validation evidence.
* The paid pilot is **not** a customer reference and is **not**
  external validation. It is internal validation with a real
  human in the loop, conducted under a commercial agreement.
* **Gate to next stage:** enterprise SaaS readiness, which is
  **explicitly not the current goal** and is governed separately
  by the B8 tracker and a separate governance change.

### 1.4 Enterprise SaaS readiness

* Multi-tenant architecture, SLA/SLO framework, audit-grade
  logging, pricing / packaging / customer onboarding, external
  security review, B1 external review output, generic solar
  and wind parity, completed pilot, and a separate governance
  change.
* None of this is in scope at this time.
* See `docs/roadmap/enterprise_saas_readiness_tracker.md` and
  `reports/roadmap/enterprise_saas_readiness_tracker.json`
  (B8).

## 2. Why a gate

The gate exists to prevent the project from skipping the
controlled internal pilot and going straight to a paid pilot.
Skipping the controlled internal pilot would mean:

* the B7 runbook, B9 execution pack, and B12 heatmap would not
  have been exercised in a real run;
* the B3 matrix would not have been updated with pilot results;
* the B11 commercial messaging guardrail would not have been
  tested against a real demo;
* the paid pilot would be the first time the model is exposed
  to a real user in a commercial setting, with all the
  associated risks.

The gate is conservative. The paid pilot is the **second**
controlled exposure, not the first.

## 3. The gate checklist

The gate between controlled internal pilot and controlled paid
pilot has the following minimum gates. Each gate must be `passed`
before the paid pilot can start. The
`reports/pilot/paid_pilot_readiness_gate.json` machine-readable
gate tracker mirrors this list and is the canonical status
record.

| Gate | Description | Pass criterion |
|---|---|---|
| PG-01 | Controlled internal pilot completed | Pilot result summary filed (B9 result summary template populated) |
| PG-02 | Pilot result reviewed by project lead | Signed review note in the pilot result summary |
| PG-03 | B3 matrix updated with pilot results | At least one B3 area moved to `pilot_user_tested` or higher; or a recorded demotion with rationale |
| PG-04 | B11 commercial messaging guardrail tested against a real demo | At least one demo run with no guardrail violations recorded |
| PG-05 | B12 heatmap updated to reflect pilot results | At least one B12 area's confidence label updated, or a recorded no-change rationale |
| PG-06 | Pilot user agreement for paid pilot drafted | Document exists; reviewed by project lead and legal if applicable |
| PG-07 | Paid pilot scope and inputs documented | Specific area, specific inputs, expected output range documented |
| PG-08 | Paid pilot data isolation verified | Production / customer / NDA data are not accessible |
| PG-09 | Paid pilot environment provisioned | Environment is up, observable, secure |
| PG-10 | Paid pilot no-go acknowledgement drafted | Pilot user and operator have signed an acknowledgement that forbids external-claim language |
| PG-11 | Paid pilot support / incident response in place | Tiers defined, on-call assigned, communication channel set |
| PG-12 | Paid pilot go/no-go decision memo filed | Memo records the decision, the rationale, and the unresolved blockers |
| PG-13 | B1 no-go list reviewed against the paid pilot scope | No conflict between the paid pilot scope and the no-go list |
| PG-14 | B11 commercial messaging guardrail reviewed against the paid pilot scope | No conflict between the paid pilot scope and the prohibited claims register |

When all gates PG-01 through PG-14 are `passed`, the paid pilot
is authorized to start. Any other status (failed, blocked,
pending, in_progress) blocks paid pilot start.

## 4. Minimum evidence required before paid pilot

In addition to the gate checklist, the paid pilot requires:

* **A completed controlled internal pilot.** At least one pilot
  run completed, with a result summary filed.
* **A go/no-go decision memo.** The decision memo records the
  decision, the rationale, and the unresolved blockers.
* **A B3 matrix update.** The matrix reflects the pilot
  results, with at least one area moved to a stronger
  evidence_category or a recorded demotion.
* **A B11 guardrail test.** At least one demo run with no
  guardrail violations recorded.
* **A B12 heatmap update.** The heatmap reflects the pilot
  results.
* **A paid pilot user agreement.** The agreement is signed by
  the pilot user and the project lead.
* **A paid pilot no-go acknowledgement.** The pilot user and
  operator have signed the no-go acknowledgement.

The full list of gates and required evidence is in
`reports/pilot/paid_pilot_readiness_gate.json`.

## 5. Paid pilot exclusions

The paid pilot is **not** a customer reference. The following are
explicitly out of scope:

* Any lender / bank / audit / certification / regulatory / SaaS
  use case.
* Any claim that the pilot user endorses the model for any
  external purpose.
* Any claim that the pilot constitutes external validation.
* Any claim of production-readiness.
* Any claim of bankability, lender-approval, certification, or
  audit.
* Any use of the pilot result in marketing, sales, or
  external-facing materials, without the pilot user's explicit
  written consent.
* Any use of the pilot data, pilot outputs, or pilot experience
  outside the agreed paid pilot channel.

The paid pilot exclusions are reinforced by the B1 no-go list
and the B11 commercial messaging guardrail. The paid pilot
user agreement includes explicit acknowledgement of these
exclusions.

## 6. Approved pilot scope

The approved pilot scope is documented in the paid pilot
agreement. The scope must include:

* the specific model area(s) under test;
* the specific input set;
* the expected output range;
* the pilot run window (start / end / hours of operation);
* the pilot user's data isolation requirements;
* the no-go acknowledgement;
* the feedback protocol;
* the support / incident response process;
* the post-pilot evidence update process.

The scope is recorded in
`reports/pilot/paid_pilot_readiness_gate.json` (B13, machine-readable).

## 7. Post-pilot evidence update process

When the paid pilot closes, the following updates are made:

* The B3 matrix is updated with the paid pilot results.
* The B12 heatmap is updated to reflect the new evidence.
* The B7 / B9 / B13 artifacts are updated with the paid pilot
  result summary.
* The B14 governance refresh tracker is updated with any
  outstanding follow-ups.
* The B11 commercial messaging guardrail is updated if the paid
  pilot surfaced a new claim category or a new channel.

The updates are normal B-track operations, not code changes.

## 8. Decision memo template

The decision memo template is in
`docs/pilot/paid_pilot_go_no_go_decision_memo_template.md`. The
template records:

* the gate status (all-passed or not);
* the pilot result summary reference;
* the B3 matrix update reference;
* the B11 guardrail test reference;
* the B12 heatmap update reference;
* the paid pilot user agreement reference;
* the paid pilot no-go acknowledgement reference;
* the go / no-go decision;
* the rationale;
* the unresolved blockers;
* the responsible owner placeholders;
* the date and the signatures.

A decision memo is required to start the paid pilot. A
"go" decision without a memo is a gate violation.

## 9. Responsible owner placeholders

The gate defines responsible owner placeholders for each gate
and for the overall gate. The placeholders are:

* `project_lead` — overall responsibility for the gate.
* `pilot_operator` — operational responsibility for the paid
  pilot.
* `b_track_owner` — responsibility for the B-track artifacts
  (B3, B7, B9, B11, B12, B13).
* `legal_placeholder` — responsibility for the paid pilot user
  agreement (placeholder; actual legal review by appropriate
  party).
* `security_placeholder` — responsibility for the paid pilot
  environment security (placeholder; actual security review by
  appropriate party).

The placeholders are not personnel assignments. They are role
definitions. The project lead assigns actual personnel at the
start of the paid pilot scoping process.

## 10. Unresolved blocker list

The gate tracks unresolved blockers in
`reports/pilot/paid_pilot_readiness_gate.json` (B13, machine-readable).
The initial state has the following unresolved blockers (none
of which are actual issues at the time of package creation; they
are categories of blockers that the gate will track when populated):

* B1 external review output (scaffolding in place; review not yet
  performed)
* B2 generic reference acquisition (zero references acquired)
* B7 controlled internal pilot (not yet run)
* B9 pilot execution (gates pending)
* B12 heatmap update (initial state)
* B14 governance refresh (initial state)

A blocker is "unresolved" if it is the reason a gate is not
`passed`. Each blocker has an owner, a target resolution date,
and a status. The gate tracker is updated as part of normal
B-track work.

## 11. What this gate is not

* It is not a contract. The gate is internal governance. The
  paid pilot user agreement is the contract.
* It is not a customer reference. The paid pilot is internal
  validation with a real human user.
* It is not external validation.
* It is not a substitute for the B7 runbook, the B9 execution
  pack, the B11 commercial messaging guardrail, or the B12
  heatmap.

## 12. Cross-references

* `docs/pilot/controlled_pilot_runbook.md` (B7)
* `docs/pilot/pilot_validation_execution_pack.md` (B9)
* `docs/pilot/paid_pilot_go_no_go_decision_memo_template.md` (B13)
* `reports/pilot/paid_pilot_readiness_gate.json` (B13, machine-readable)
* `docs/commercial/no_go_claims_commercial_guardrail.md` (B11)
* `docs/validation/model_confidence_heatmap.md` (B12)
* `docs/roadmap/enterprise_saas_readiness_tracker.md` (B8)
* `docs/external_review/no_go_claims.md` (B1)
* `docs/governance/agent_a_b_governance_refresh_plan.md` (B14)

---

*End of paid pilot readiness gate.*
