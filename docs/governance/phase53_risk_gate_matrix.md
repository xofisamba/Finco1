# Phase 53 Risk & Gate Matrix

This file is the **Phase 53 risk and gate matrix**. It is
the B-track governance artifact that governs the Phase 53
persistence / repository refactor work that Agent A will
execute.

> **Agent B does not implement Phase 53.** Agent A executes
> Phase 53. Agent B tracks the risk and gate matrix and
> refreshes the B-track artifacts when Phase 53 lands.
>
> **Phase 53 is partially executed by Agent A.** As of branch
> creation (Phase 52G closeout, PR #428), Phase 53 was
> planned and ready but not yet executed. PRs #429 (Phase
> 53A) and #430 (Phase 53B) have since landed on main. The
> remaining Phase 53 PRs (53C-53J) are still planned. This
> B-track pack is the governance wrapper for the full
> sequence; the B24-B29 pack does not claim to reflect the
> 53A/53B results.
>
> **No persistence or repository code changes by Agent B.**
> Agent B is docs-only. The risk and gate matrix is the B-track
> governance wrapper for the Agent A code work.

---

## 1. Phase 53 context

Phase 53 is the **persistence / repository refactor** work
that follows Phase 52. Phase 52 mapped the persistence layer
(mapping / planning only; zero production code changes).
Phase 53 will refactor the persistence layer per the Phase 52
plan.

Phase 53 will be executed by Agent A as a sequence of 10
PRs (53A-53J). The 10 PRs are organized into 7 split groups
(A-F), with the recommended refactor order being F, D, E,
A-reads, A-2, C, B.

## 2. Group order and 10-PR sequence

### 2.1 Refactor order (F, D, E, A-reads, A-2, C, B)

The Phase 52 closeout (PR #428) defines the refactor order
as F, D, E, A-reads, A-2, C, B. The order is not strictly
sequential; it is a recommendation that minimizes blast
radius and maximizes safety.

* **F** — Group F helpers (recommended first action: 53A
  Group F helpers). *(Recommended by the Phase 52G closeout;
  53A has since landed on main as PR #429.)*
* **D** — Group D.
* **E** — Group E.
* **A-reads** — Group A reads (sub-group of A).
* **A-2** — Group A writes (sub-group of A; review required).
* **C** — Group C (review required).
* **B** — Group B (sign-off required; highest blast radius).

### 2.2 Planned 10-PR sequence (53A-53J)

The 10 PRs are:

* **53A** — Group F helpers.
* **53B** — Group F consumers.
* **53C** — Group D.
* **53D** — Group E.
* **53E** — Group A reads.
* **53F** — Group A writes.
* **53G** — Group C.
* **53H** — Group B (first sub-PR).
* **53I** — Group B (second sub-PR).
* **53J** — Group B (third sub-PR; sign-off required).

The mapping from PRs to groups is the project's plan. Agent
A may adjust the PR-group mapping in execution as long as
the refactor order and the hard-stop conditions are
preserved.

## 3. Owner and auto-merge policy

* **Owner (code):** Agent A. Agent A writes the code, the
  tests, the guardrails, and the migration scripts.
* **Owner (governance review):** Agent B. Agent B reviews
  the governance implications, refreshes the B-track
  artifacts, and flags the B-track governance updates
  required by each Phase 53 PR.

### 3.1 Auto-merge policy

Per the Phase 52 closeout (PR #428):

* **F / D / E / A-reads** — auto-merge class allowed if checks
  pass. Agent A may enable auto-merge on these PRs.
* **A-2 / C** — review required. Agent A may not enable
  auto-merge on these PRs. Manual review by Agent B (and any
  other stakeholders) is required.
* **B** — sign-off required. Agent A may not enable auto-merge
  on these PRs. Manual sign-off by Agent B and the user is
  required before merge.

The auto-merge policy is enforced at the GitHub PR level
(branch protection rule on `main`, if configured). If branch
protection is not configured, the policy is a documented
governance expectation, not a hard technical gate.

## 4. Risk level per group

| Group | Risk level | Notes |
|---|---|---|
| F | low | Helpers only; no behavior change. |
| D | low-medium | Plan-driven; limited blast radius. |
| E | medium | Plan-driven; some blast radius. |
| A-reads | low | Read-only changes. |
| A-2 | medium-high | Writes; affects production data path. |
| C | medium-high | Significant refactor. |
| B | high | Highest blast radius; sign-off required. |

The risk level is the project's internal self-assessment.
It is not externally validated.

## 5. Expected evidence per group

Each Phase 53 PR is expected to provide the following
evidence:

* **Tests** — the PR's test suite (new + existing tests
  pass).
* **Behavior guardrail tests** — the 21 → 31 behavior
  guardrail test count increases per the Phase 52 closeout.
* **Structural guardrail enforcement** — at least one
  structural guardrail (G1-G6) is enforced by the PR.
* **Pin additions** — at least one must-pin item (per B26) is
  pinned by the PR.
* **Diff narrative** — a short narrative describing the
  change, the rationale, and the rollback procedure.

The evidence is recorded in the B26 must-pin / evidence
tracker and the B27 guardrail adoption tracker.

## 6. Required tests / checks per group

| Group | Required tests / checks |
|---|---|
| F | Helpers tested in isolation. |
| D | Plan conformance. Behavior unchanged. |
| E | Plan conformance. Behavior unchanged. |
| A-reads | Read-only tests; no production data path changes. |
| A-2 | Write path tests; rollback procedure documented. |
| C | Significant refactor tests; cross-module integration<br>tests. |
| B | Sign-off review; full regression suite. |

The required tests are the project's internal expectation.
The actual tests are determined by Agent A in the PR.

## 7. Hard-stop conditions

Per the Phase 52 closeout (PR #428), the following
hard-stop conditions are defined:

* **Any must-pin item is broken or fails the pin test.** The
  PR is blocked. The B-track governance refresh is required.
* **Any structural guardrail (G1-G6) is broken or fails the
  enforcement test.** The PR is blocked. The B-track
  governance refresh is required.
* **Any behavior guardrail test fails.** The PR is blocked.
  The rollback procedure is invoked.
* **The Phase 53 refactor order is violated.** The PR is
  blocked. Agent B escalates to the user.
* **Agent B is not notified of the PR.** The B-track
  governance refresh may be skipped. Agent B is
  subsequently informed.
* **The Phase 53 PR is merged with a non-passing check.** The
  PR is rolled back if possible. The B-track governance
  refresh is required.

The hard-stop conditions are the project's internal
governance expectations. They are not externally validated.

## 8. No-parallelization areas

Per the Phase 52 closeout (PR #428), the following 4 areas
are do-not-parallelize:

* **Group B writes** — the highest blast radius. Sign-off
  required.
* **Group C refactor** — significant refactor. Review
  required.
* **Group A-2 writes** — affects the production data path.
  Review required.
* **Persistence layer migration** — the persistence layer
  migration is not parallel-safe. The migration is performed
  by Agent A in a single coordinated step.

The do-not-parallelize areas are the project's internal
governance expectation. Agent B does not modify these
expectations.

## 9. Pilot impact per group

| Group | Pilot impact |
|---|---|
| F | None. Helpers only. |
| D | None. Plan-driven. |
| E | None. Plan-driven. |
| A-reads | None. Read-only. |
| A-2 | High. Affects the production data path. Pilot
  surface area may change. Pin refresh or forward-compatibility
  decision may be required. |
| C | High. Significant refactor. Pilot surface area may
  change. Pin refresh required. |
| B | Highest. Highest blast radius. Pilot surface area will
  change. Pin refresh required. |

The pilot impact is the project's internal self-assessment.
It is not externally validated.

## 10. External review impact per group

| Group | External review impact |
|---|---|
| F | None. |
| D | None. |
| E | None. |
| A-reads | None. |
| A-2 | Medium. The B3 matrix, B12 heatmap, and B16 closeout
  tracker may need a refresh. |
| C | High. The B3 matrix, B12 heatmap, and B16 closeout
  tracker need a refresh. |
| B | Highest. The B3 matrix, B12 heatmap, B16 closeout
  tracker, and B8 enterprise SaaS readiness tracker may
  need a refresh. |

The external review impact is the project's internal
self-assessment. It is not externally validated.

## 11. Paid pilot gate impact per group

| Group | Paid pilot gate impact |
|---|---|
| F | None. |
| D | None. |
| E | None. |
| A-reads | None. |
| A-2 | Medium. The B13 paid pilot gate may need a refresh. |
| C | High. The B13 paid pilot gate needs a refresh. |
| B | Highest. The B13 paid pilot gate needs a refresh. |

The paid pilot gate impact is the project's internal
self-assessment. The paid pilot gate is a separate stage and
is unaffected by Phase 53 directly. Phase 53 may trigger a
B13 gate refresh per the B29 Phase 53 change-control
checklist.

## 12. B-track refresh trigger per group

| Group | B-track refresh trigger |
|---|---|
| F | None. |
| D | None. |
| E | None. |
| A-reads | None. |
| A-2 | B3 matrix, B12 heatmap, B13 gate, B16 closeout, B26
  must-pin tracker refresh. |
| C | B3 matrix, B12 heatmap, B13 gate, B16 closeout, B26
  must-pin tracker, B27 guardrail adoption tracker refresh. |
| B | All B-track artifacts refresh. |

The B-track refresh trigger is the B29 Phase 53 change-
control checklist, which is performed by Agent B after each
Phase 53 PR.

## 13. What this matrix is not

* It is not a code change. Phase 53 is not yet implemented.
* It is not a contract. The Phase 53 work is governed by
  the B-track governance pack, not by this matrix alone.
* It is not external validation. The risk and gate matrix is
  internal governance.
* It is not a substitute for the B14 governance refresh
  plan or any B-track artifact.
* It is not Claude review. Claude review is separate.
* It is not the post-51T review. The post-51T review is
  separate.

## 14. Cross-references

* `reports/governance/phase53_risk_gate_matrix.json` (B25,
  machine-readable)
* `docs/governance/post_phase52_governance_refresh.md` (B24)
* `docs/validation/phase53_must_pin_evidence_tracker.md` (B26)
* `docs/governance/phase52_53_guardrail_adoption_tracker.md`
  (B27)
* `docs/pilot/post_phase52_pilot_external_readiness_delta.md`
  (B28)
* `docs/governance/phase53_change_control_checklist.md` (B29)
* `docs/governance/agent_a_b_governance_refresh_plan.md` (B14)
* `docs/external_review/external_review_closeout_tracker.md`
  (B16)

---

*End of Phase 53 risk & gate matrix.*
