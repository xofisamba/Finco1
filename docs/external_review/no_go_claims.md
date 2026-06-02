# No-Go Claims

This file is a **hard list** of claims that the Finco1 project
**does not make, endorse, support, or imply** at the current base
SHA `a541d447063cf288b1a9ea0a7bbf199755e40d53`, and that this
external review package **does not make, endorse, support, or imply**.

The external reviewer is required to read this file, to acknowledge
it in their final output, and **not** to reproduce, endorse, or imply
any of the claims below.

If a claim is not on this list, that does **not** mean the project
endorses it. The list is a **floor**, not a ceiling.

---

## 1. Lender / bank / bankability claims

The project does **not** claim, and the reviewer must not imply, that
the model or any of its outputs are:

* lender-grade;
* bank-grade;
* bankable;
* acceptable to any specific lender, bank, or financial institution;
* sufficient for any loan-approval, debt-sizing, syndication, or
  refinancing decision;
* aligned with any specific lender's credit policy, ICG, credit
  committee, or risk-rating framework.

## 2. Audit / certification / regulatory claims

The project does **not** claim, and the reviewer must not imply, that
the model or any of its outputs are:

* audited;
* certified;
* accredited;
* compliant with any regulatory regime (banking, securities, energy,
  tax, accounting, or otherwise);
* suitable for filing with any regulator, tax authority, or
  statistical agency;
* aligned with IFRS, US GAAP, or any other accounting framework as a
  representation of compliance;
* subject to any external assurance opinion.

## 3. SaaS / product / commercial claims

The project does **not** claim, and the reviewer must not imply, that
the model is:

* a SaaS product;
* a commercial offering;
* production-ready for any specific customer;
* covered by any SLA, warranty, support commitment, or service-level
  objective;
* fit for any specific commercial, operational, or production use.

## 4. Model-output / financial-formula claims

The project does **not** claim, and the reviewer must not imply, that:

* any financial formula has been added, removed, or modified in this
  PR;
* any model output has been added, removed, or modified in this PR;
* any change to a financial formula is approved or recommended by
  this PR;
* any fixture CSV has been changed by this PR;
* any schema or migration has been changed by this PR;
* any persistence or repository behavior has been changed by this PR;
* any Phase 51F parity-core file has been changed by this PR;
* any Phase 51F pinned golden value has been changed by this PR.

This PR is **docs and report only**. It does not change the model.

## 5. Client-side financial-calculation claims

The project does **not** claim, and the reviewer must not imply, that:

* any JavaScript in the repository performs a financial calculation;
* any template, partial, or static asset performs a financial
  calculation;
* any client-side numeric behavior is part of the model's source of
  truth.

The backend is the source of truth. If the reviewer finds a
calculation in client-side code, that is a bug, not a feature, and
must be reported as such.

## 6. Blocked / not-approved / not-promoted areas

The project does **not** claim, and the reviewer must not imply, that
the following are approved, validated, or production-ready:

| Area | Posture |
|---|---|
| G20 | **BLOCKED.** Not approved, not validated, not externally claimable. |
| R99 | **NOT APPROVED.** Internal reference only. |
| R102 | **NOT APPROVED.** Internal reference only. |
| `partial_pay_sweep` | **Not promoted.** Internal reference only. |
| Flat / min DSCR sculpting | **Not promoted.** Internal reference only. |
| Generic solar modeling (external claim) | **Exploratory and unvalidated** for any external claim. Internal validation cases exist in `validation/cases/solar_case_*.py`; they are not external validation. |
| Generic wind modeling (external claim) | **Exploratory and unvalidated** for any external claim. Internal validation cases exist in `validation/cases/wind_case_*.py`; they are not external validation. |
| PR #299 | **Closed.** Not an active reference for current state. |
| `rc1` modifications | **Forbidden.** `rc1` is frozen. |

## 7. Track-isolation claims

The project does **not** claim, and the reviewer must not imply, that:

* this PR (Agent B / `parallel-b1-external-review-prep`) makes any
  change to files owned by the Agent A track
  (`main_web.py`, `main_api.py`, `app/services/**`, `app/waterfall_core.py`,
  `app/project_factories.py`, `domain/**`, `project_factories.py`,
  `repository.py`, Phase 51–58 test files, `reports/*senior_debt*.csv`,
  fixture CSVs, schema / migrations);
* the parallel Agent A track's behavior is part of the current base
  SHA being reviewed;
* behavior on either parallel track has been blessed by the other
  track;
* the `/save-run`, scenario routes, project save-as, or
  repository-extraction work is part of this PR;
* the prior base SHA `a53d278` is the state under review (it is not;
  it is preserved for provenance only).

## 8. Reviewer-claim claims

The project does **not** claim, and the reviewer must not imply, that:

* the reviewer's output, in whole or in part, constitutes lender-,
  bank-, audit-, certification-, regulatory-, or SaaS-grade
  assurance;
* the reviewer's output is a substitute for any required external
  review by an appropriately qualified party;
* the project will represent the reviewer's output externally in any
  of the above senses.

## 9. Phase 51F guardrail claims

The project does **not** claim, and the reviewer must not imply, that:

* the Phase 51F guardrails (engine-output golden, parity-core lock,
  no-service-imports) constitute external validation;
* the Phase 51F pinned golden values are externally verified;
* the Phase 51F pins guarantee model correctness — they only pin
  against regression since the pins were set;
* the Phase 51F parity-core lock covers routes, frontend, fixtures, or
  schema — it covers only the four listed files;
* the Phase 51F no-service-imports guardrail covers the reverse
  direction (routes importing services) — it does not, and that
  direction is intended by the Phase 51 architecture.

The Phase 51F guardrails are project-internal refactor protection.
They are a real, valuable engineering tool. They are not external
assurance.

## 10. What this PR does claim (positive list, narrow)

To balance the negative list, this PR claims only the following, all
of which are narrow and conservative:

* The package accurately **describes** the project posture as of the
  current base SHA, to the best of the package authors' knowledge.
* The package is **docs and report only**; it does not modify code,
  routes, services, templates, static assets, fixtures, schema, or
  persistence.
* The package **does not** modify any Phase 51F parity-core file or
  any Phase 51F pinned golden value.
* The package **identifies** what is and is not pinned, blocked, or
  approved, in language that does not overstate validation.
* The package **identifies** the no-go claims above.
* The package **points** the reviewer at the relevant tests and
  reports without asserting their pass/fail status.
* The package **requires** the reviewer to acknowledge this no-go
  list and not to reproduce it.

## 11. Acknowledgement (to be returned by the reviewer)

The reviewer is asked to include, verbatim or substantively
equivalent, the following line in their final output:

> "I have read `no_go_claims.md` and confirm I will not reproduce,
> endorse, or imply any of the no-go claims in my output."

---

*End of no-go claims.*
