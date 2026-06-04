# Phase 53 Stop/Go Checklist

This file is the **Phase 53 stop/go checklist**. It is the
strict checklist Agent B (and the user) can use to evaluate
each Phase 53 PR for proceed / stop / manual review /
sign-off / rollback / escalation decisions.

> **Agent B does not approve code correctness. Agent B
> checks governance/evidence readiness only. Agent A owns
> code and tests. User approves merge/sign-off
> decisions.**
>
> **No persistence or repository code changes by Agent
> B.** Agent B is docs-only. The stop/go checklist is the
> B-track governance wrapper for the Agent A code work.
>
> **The checklist is conservative.** It is biased toward
> stopping or escalating rather than proceeding. The
> default response to a hard-stop condition is to stop and
> escalate, not to proceed.

---

## 1. Roles

* **Agent A:** Owns the code, the tests, the guardrails,
  the migration scripts, and the CI. Agent A produces
  the PR description, the diff narrative, the rollback
  procedure, and the test results.
* **Agent B:** Owns the B-track governance pack. Agent B
  checks governance/evidence readiness only. Agent B
  does not approve code correctness. Agent B applies
  this checklist to each Phase 53 PR.
* **User:** Approves merge and sign-off decisions. User
  has the final say on proceed / stop decisions.

## 2. Proceed conditions

The following conditions must all be true for Agent B to
recommend proceed. If any condition is false, Agent B
recommends stop, manual review, sign-off, or escalation
per the conditions below.

* [ ] **All hard-stop conditions are clear.** (See
  section 4 below.)
* [ ] **CI workflow `test` is passing on the PR's head
  commit.**
* [ ] **CI workflow `Parity Guardrails (Phase 51F)` is
  passing on the PR's head commit.**
* [ ] **All structural guardrails (G1-G6) are passing
  on the PR's head commit.** If the PR adds a new
  structural guardrail, the new guardrail is also
  passing.
* [ ] **All behavior guardrail tests (21 baseline + per-
  PR additions) are passing on the PR's head commit.**
* [ ] **The PR's diff narrative describes the change,
  the rationale, and the rollback procedure.**
* [ ] **The PR's affected must-pin items (per the B26
  tracker) are accounted for in the PR's pin tests.**
* [ ] **The PR's auto-merge class (per the B25 policy)
  is consistent with the PR's actual auto-merge
  status.**
* [ ] **Agent B has been notified of the PR.** (See
  section 9 below.)
* [ ] **The PR does not violate the do-not-parallelize
  rules** (per the B25 policy).
* [ ] **The PR is in the correct Phase 53 sequence
  position** (i.e., the PR's dependencies have merged
  on main).

## 3. Stop conditions

The following conditions trigger an immediate stop. Agent
B recommends stop and escalation to the user. The PR is
blocked until the user authorizes proceed.

* [ ] **Any must-pin item is broken or failing the pin
  test.** The PR is blocked. Agent B escalates to the
  user.
* [ ] **Any structural guardrail (G1-G6) is broken or
  failing the enforcement test.** The PR is blocked.
  Agent B escalates to the user.
* [ ] **Any behavior guardrail test is failing.** The
  PR is blocked. The rollback procedure is invoked.
  Agent B escalates to the user.
* [ ] **CI workflow `test` is failing on the PR's head
  commit.** The PR is blocked. Agent B escalates to the
  user.
* [ ] **CI workflow `Parity Guardrails (Phase 51F)` is
  failing on the PR's head commit.** The PR is blocked.
  Agent B escalates to the user.
* [ ] **The Phase 53 refactor order is violated.** The
  PR is blocked. Agent B escalates to the user.
* [ ] **The PR is merged with a non-passing check.** The
  PR is rolled back if possible. Agent B escalates to
  the user.
* [ ] **The PR touches a file outside the Agent A-owned
  file set (e.g., a B-track file, a fixture CSV, a
  schema / migration file, a template / static asset,
  a test file, a financial formula, a model output,
  a JS financial calculation).** The PR is blocked.
  Agent B escalates to the user.
* [ ] **The PR includes a paid pilot authorization
  claim, an external validation claim, a customer
  reference claim, a production-readiness claim, an
  enterprise SaaS-readiness claim, a bankability /
  audit / certification / lender / regulatory / SaaS
  claim, an investment advice claim, or a guaranteed
  returns claim.** The PR is blocked. Agent B escalates
  to the user.

## 4. Manual review triggers

The following conditions trigger manual review by Agent
B. The PR is not auto-merged. Agent B performs a per-PR
review using the B29 change-control checklist and the
B32 evidence intake template.

* [ ] **The PR's auto-merge class is `review_required`
  (Group A-2 or C).** Agent B reviews the PR per the
  B25 policy.
* [ ] **The PR's diff includes changes to `app/persistence/*`
  files.** Agent B reviews the persistence impact.
* [ ] **The PR's diff includes changes to `repository.py`.**
  Agent B reviews the repository impact.
* [ ] **The PR's diff includes changes to `app/services/*`.**
  Agent B reviews the service impact.
* [ ] **The PR's diff includes changes to the test
  files.** Agent B reviews the test impact.
* [ ] **The PR's title includes "REVIEW REQUIRED" or
  "DRAFT, REVIEW REQUIRED".** Agent B reviews the
  PR per the project's internal review policy.

## 5. Sign-off triggers

The following conditions require user sign-off. The PR is
not auto-merged or manually merged. The user must
explicitly authorize the merge.

* [ ] **The PR's auto-merge class is `sign_off_required`
  (Group B).** User sign-off required.
* [ ] **The PR is a Phase 53 closeout (53G-8, 53H-2,
  53I-4, 53J).** User sign-off required.
* [ ] **The PR touches a must-pin item that is currently
  marked as `pilot_blocker: yes` or `paid_pilot_blocker:
  yes`.** User sign-off required.
* [ ] **The PR is the first PR in a new Phase 53 group
  (e.g., the first PR in 53C, 53D, 53E, 53F, 53G,
  53H, 53I, 53J).** User sign-off recommended.

## 6. Rollback / escalation triggers

The following conditions trigger a rollback or escalation.
Agent B escalates to the user. The user decides whether
to roll back the PR (if possible) or to proceed with a
mitigation plan.

* [ ] **The PR breaks a parity-core lock (4 SHA-256
  files).** The PR is rolled back. Agent B escalates
  to the user.
* [ ] **The PR breaks an engine-output golden (TUHO +
  Oborovo).** The PR is rolled back. Agent B escalates
  to the user.
* [ ] **The PR produces a model output drift on TUHO
  or Oborovo.** The PR is rolled back. Agent B
  escalates to the user.
* [ ] **The PR breaks a financial formula.** The PR
  is rolled back. Agent B escalates to the user.
* [ ] **The PR produces a JS financial calculation
  change.** The PR is rolled back. Agent B escalates
  to the user.
* [ ] **The PR produces a fixture CSV change.** The
  PR is rolled back. Agent B escalates to the user.
* [ ] **The PR produces a schema / migration change
  that was not pre-authorized.** The PR is rolled
  back. Agent B escalates to the user.
* [ ] **The PR is merged without Agent B's
  notification.** Agent B performs an emergency
  review and escalates to the user.
* [ ] **The PR is the 53J final closeout and any
  hard-stop condition is unclear.** Agent B escalates
  to the user.

## 7. No-parallelization checks

The following checks verify that the PR does not violate
the do-not-parallelize rules.

* [ ] **The PR is not in a do-not-parallelize area**
  (Group B, Group C, Group A-2 writes, or the
  persistence layer migration) — or, if it is, the PR
  is reviewed with sign-off per the B25 auto-merge
  policy.
* [ ] **The PR is not run in parallel with a
  conflicting PR.** (E.g., a Group B PR run in
  parallel with a Group C PR is a violation.)
* [ ] **The PR does not modify the persistence layer
  migration script.** (The persistence layer migration
  is performed by Agent A in a single coordinated
  step.)

## 8. Single-owner zone checks

The following checks verify that the PR does not violate
the single-owner zone rules (per the Phase 52C / Phase
52G closeout).

* [ ] **The PR's affected files are all in the
  single-owner zones for the PR's group.** (See Phase
  52G closeout for the 11 single-owner zones.)
* [ ] **The PR does not modify files in a different
  single-owner zone** without coordination with the
  other zone's owner.

## 9. Guardrail failure response

* [ ] **If G1 fails:** The PR is blocked. The PR
  introduces a direct sqlite3 / sqlalchemy import
  outside `app/persistence/*`. The PR is rolled back
  if merged.
* [ ] **If G2 fails:** The PR is blocked. The PR
  introduces a service import in `main_web.py` or
  `main_api.py`. The PR is rolled back if merged.
* [ ] **If G3 fails:** The PR is blocked. The PR
  introduces a `sqlite3.Connection` or `sqlite3.connect`
  instantiation outside `app/persistence/*`. The PR is
  rolled back if merged.
* [ ] **If G4 fails:** The PR is blocked. The PR
  introduces a direct `get_cursor` import in a service
  or route. The PR is rolled back if merged.
* [ ] **If G5 fails:** The PR is blocked. The PR breaks
  the single-transaction pattern in `repository.py`.
  The PR is rolled back if merged.
* [ ] **If G6 fails:** The PR is blocked. The PR uses
  a private attribute or function of the repository
  from a service. The PR is rolled back if merged.
* [ ] **If a new structural guardrail fails:** The PR
  is blocked. The new guardrail is documented in B27
  and the PR is re-evaluated.
* [ ] **If a deferred guardrail (D1-D4) is implemented
  in the PR:** The PR is documented in B27 and the
  guardrail is added to the active guardrail list.

## 10. CI failure response

* [ ] **If `test` workflow fails:** The PR is blocked.
  The PR is not merged. Agent B escalates to the user.
* [ ] **If `Parity Guardrails (Phase 51F)` workflow
  fails:** The PR is blocked. The PR is not merged.
  Agent B escalates to the user.
* [ ] **If any other CI workflow fails:** The PR is
  blocked. Agent B escalates to the user.
* [ ] **If CI reruns on draft->ready transition do
  not fire:** The PR is still considered against the
  original head commit's CI status. Agent B notes the
  CI status at the time of the original head commit.

## 11. Parity drift response

* [ ] **If a parity-core lock file (4 SHA-256 files)
  changes:** The PR is blocked. The parity-core lock
  is the source of truth for the engine output
  stability. The PR is rolled back if merged.
* [ ] **If an engine-output golden (TUHO or Oborovo)
  changes:** The PR is blocked. The engine-output
  golden is the source of truth for the model output
  stability. The PR is rolled back if merged.

## 12. Model output drift response

* [ ] **If the model output drifts on TUHO:** The PR
  is blocked. The model output is the source of
  truth for the financial model. The PR is rolled
  back if merged.
* [ ] **If the model output drifts on Oborovo:** The
  PR is blocked. The model output is the source of
  truth for the financial model. The PR is rolled
  back if merged.
* [ ] **If the model output drifts on a generic solar
  / wind scenario:** The PR is blocked. Generic
  solar / wind remain exploratory and unvalidated.
  The PR is rolled back if merged.

## 13. Unexpected file touch response

* [ ] **If the PR touches a B-track file** (any file
  in `docs/governance/`, `docs/validation/`, `docs/pilot/`,
  `docs/commercial/`, `docs/external_review/`,
  `reports/governance/`, `reports/validation/`,
  `reports/pilot/`, `reports/commercial/`,
  `reports/external_review/`, `reports/roadmap/`,
  `reports/generic_validation/`): The PR is blocked.
  Agent B escalates to the user.
* [ ] **If the PR touches a fixture CSV:** The PR is
  blocked. Agent B escalates to the user.
* [ ] **If the PR touches a schema / migration file:**
  The PR is blocked. Agent B escalates to the user.
* [ ] **If the PR touches a template / static asset:**
  The PR is blocked. Agent B escalates to the user.
* [ ] **If the PR touches a test file:** The PR is
  reviewed by Agent B. Test changes are generally OK
  if the test count increases and the test results
  are passing.
* [ ] **If the PR touches a JS financial calculation:**
  The PR is blocked. Agent B escalates to the user.
* [ ] **If the PR touches a financial formula:** The
  PR is blocked. Agent B escalates to the user.

## 14. Paid-pilot / no-go claim response

* [ ] **If the PR includes a paid pilot authorization
  claim:** The PR is blocked. Agent B escalates to
  the user.
* [ ] **If the PR includes an external validation
  claim:** The PR is blocked. Agent B escalates to
  the user.
* [ ] **If the PR includes a customer reference
  claim:** The PR is blocked. Agent B escalates to
  the user.
* [ ] **If the PR includes a production-readiness
  claim:** The PR is blocked. Agent B escalates to
  the user.
* [ ] **If the PR includes an enterprise SaaS-readiness
  claim:** The PR is blocked. Agent B escalates to
  the user.
* [ ] **If the PR includes a bankability / audit /
  certification / lender / regulatory / SaaS claim:**
  The PR is blocked. Agent B escalates to the user.
* [ ] **If the PR includes an investment advice
  claim:** The PR is blocked. Agent B escalates to
  the user.
* [ ] **If the PR includes a guaranteed returns
  claim:** The PR is blocked. Agent B escalates to
  the user.
* [ ] **If the PR relaxes a no-go claim:** The PR is
  blocked. Agent B escalates to the user.

## 15. Decision tree

For each Phase 53 PR, Agent B applies the following
decision tree:

1. **Are all hard-stop conditions clear?**
   * No -> Stop. Escalate to user.
   * Yes -> Continue.
2. **Is the PR's auto-merge class `sign_off_required`?**
   * Yes -> User sign-off required. Escalate to user.
   * No -> Continue.
3. **Is the PR's auto-merge class `review_required`?**
   * Yes -> Agent B performs manual review.
     * Are all review conditions clear? Yes -> Recommend
       proceed. No -> Stop. Escalate to user.
     * No -> Continue.
4. **Is the PR's auto-merge class `auto_merge_allowed`?**
   * Yes -> Recommend proceed. Agent B notes the
     recommendation in the B32 evidence intake record.
   * No -> Stop. Escalate to user.

## 16. What this checklist is not

* It is not a code change. Agent B does not implement
  Phase 53.
* It is not external validation. The checklist is
  internal governance.
* It is not a substitute for the Phase 53 PR descriptions
  or any Agent A report.
* It is not a contract. The checklist is the B-track
  governance wrapper for the Agent A code work.
* It is not Claude review. Claude review is separate.
* It is not the post-51T review. The post-51T review is
  separate.

## 17. Cross-references

* `reports/governance/phase53_stop_go_checklist.json`
  (B33, machine-readable)
* `docs/governance/phase53ab_governance_refresh.md` (B30)
* `docs/governance/phase53_progress_ledger.md` (B31)
* `docs/validation/phase53_evidence_intake_template.md` (B32)
* `docs/governance/b_track_phase53_refresh_cadence.md` (B34)
* `docs/governance/phase53_change_control_checklist.md` (B29)
* `docs/governance/phase53_risk_gate_matrix.md` (B25)
* `docs/validation/phase53_must_pin_evidence_tracker.md` (B26)
* `docs/governance/phase52_53_guardrail_adoption_tracker.md`
  (B27)
* `docs/pilot/post_phase52_pilot_external_readiness_delta.md`
  (B28)
* `docs/external_review/no_go_claims.md` (B1, no-go list)
* `docs/commercial/no_go_claims_commercial_guardrail.md` (B11)

---

*End of Phase 53 stop/go checklist.*
