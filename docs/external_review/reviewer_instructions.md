# Reviewer Instructions

This file tells the external reviewer **how to use this package**, what
they **must and must not assume**, and what output the project expects
from them.

If anything in this document is ambiguous, the reviewer should ask for
clarification **before** producing their final opinion.

---

## 1. What you are being asked to review

You are being asked to review the **model state of Finco1 at the current
base SHA** listed in the package index, **not** any in-flight work on
parallel branches.

Concretely:

* Review the model's **scope**, **guardrails**, and **documented
  validation posture** as described in this package.
* Cross-check those descriptions against the actual code, fixtures,
  and tests at the current base SHA.
* Identify mismatches, gaps, and overclaims.
* Review the **Phase 51F guardrails** as part of the state under
  review, but treat them as **project-internal refactor protection**,
  not as external validation.

You are **not** being asked to:

* certify the model for any lender, bank, audit, regulatory, or SaaS
  purpose;
* approve any closed, blocked, exploratory, or not-yet-approved area
  as fit for production use;
* treat the Phase 51F pinned golden values as external validation —
  they pin current model outputs against silent regression during
  refactor, not against any external truth;
* comment on parallel Agent A branch work, which is not part of the
  current base SHA.

## 2. First step — verify the base SHA

Before forming any opinion, verify the current base SHA locally:

```bash
git -C path/to/Finco1 rev-parse HEAD
```

Expected:

```
2e41b24f8c47ec544e1ef52e35084646df4d4d8f
```

If your local checkout does not match, stop and contact the package
owner. Do not review a different commit without an updated package.

The provenance chain documented in the index is
`a53d278` → `dfe13ab` → `a541d447` → `2e41b24`; only `2e41b24` is
what you are reviewing. The earlier SHAs are kept for provenance
only.

## 3. Reading order

1. `external_review_package_index.md`
2. this file (`reviewer_instructions.md`)
3. `model_scope_and_limitations.md`
4. `tuho_oborovo_validation_summary.md`
5. `no_go_claims.md`
6. `external_review_readiness_matrix.json` (treat as the working
   checklist)

If you are also reviewing the Phase 51F guardrails in detail (which you
are encouraged to do), also read:

* `docs/phase51f_parallel_work_guardrails.md` (project documentation
  of the guardrails)
* `tests/test_phase51f_parallel_work_guardrails.py` (the test file
  that enforces them)

Both of those are **on the base SHA** and are part of the state under
review. They are not part of this PR's diff.

## 4. What you may assume

* The project is honest about what is and is not pinned or validated.
* The current base SHA is the source of truth for "what the model does
  today."
* The package's description of guardrails (`no_go_claims.md`) reflects
  the project's current position.
* The package's split of "validated / pinned / internally tested /
  exploratory / unvalidated" is conservative and may understate
  internal coverage; it will not overstate it.
* The Phase 51F guardrails are project-internal refactor protection.
  Their purpose is to detect silent model-output, parity-core, or
  import-direction regressions during the next refactor. They are not
  an external assurance mechanism.

## 5. What you must NOT assume

* **Do not** assume any test, report, or number cited in this package
  is passing or current unless you verify it yourself at the current
  base SHA.
* **Do not** assume that a test file existing in the repo means it
  passes. Run it.
* **Do not** assume that internal tests are independent external
  validation.
* **Do not** assume that an exploratory feature is safe for production
  use just because the code is present.
* **Do not** assume that anything in the package constitutes lender-,
  bank-, audit-, certification-, regulatory-, or SaaS-grade assurance.
* **Do not** assume that generic solar / wind logic is validated; it
  is explicitly exploratory and unvalidated for any external claim.
* **Do not** assume that G20, R99, R102, `partial_pay_sweep`, or flat /
  min DSCR sculpting is approved; they are explicitly not.
* **Do not** assume that JavaScript or template-layer code performs any
  financial calculation; financial calculation lives in the Python
  backend.
* **Do not** assume that the Phase 51F pinned golden values are
  "ground truth" in any external sense. They pin the current model
  outputs against regression. The pin itself does not validate the
  model against an external benchmark.
* **Do not** reproduce or endorse any of the claims listed in
  `no_go_claims.md`.

## 6. Required output from the reviewer

Your deliverable must include, at minimum:

1. **SHA verification statement.** One line: "I verified the base SHA
   `2e41b24…` against my local checkout on `<date>`."
2. **Readiness matrix response.** For every row in
   `external_review_readiness_matrix.json`, supply:
   * `reviewer_agrees_with_status`: yes / no / partial
   * `reviewer_evidence_checked`: short summary of what you actually
     opened and inspected at the current base SHA
   * `reviewer_notes`: any caveats, gaps, or counter-evidence
3. **Answers to required reviewer questions.** See:
   * `model_scope_and_limitations.md` §6
   * `tuho_oborovo_validation_summary.md` §6
   * `model_scope_and_limitations.md` §3.4 (Phase 51F-specific
     questions)
4. **Per-area go / conditional-go / no-go opinion.** One of:
   * **Go** — model area is consistent with documentation and any
     stated pinning is intact at the base SHA.
   * **Conditional go** — model area is internally pinned or tested
     and consistent, but has known gaps that must be acknowledged.
   * **No-go** — model area is exploratory, blocked, not approved, or
     has documentation/code mismatches that block external claim.
5. **No-go claim acknowledgement.** An explicit line stating:
   "I have read `no_go_claims.md` and confirm I will not reproduce,
   endorse, or imply any of the no-go claims in my output."
6. **Optional but encouraged:** concrete suggestions for closing gaps,
   phrased as recommendations, not as approvals.

## 7. What to do if you find a mismatch

If you find that the package's description disagrees with the code,
fixtures, or test outcomes at the current base SHA:

1. Note the disagreement in your output, citing the file and line
   range.
2. Default to the more conservative interpretation.
3. Recommend that the package be updated in a follow-up B-track PR; do
   not attempt to fix the code in this review.

This is a docs/report-only review PR. It is **not** a code-fix PR.

If you find that the **Phase 51F guardrails themselves** are
inconsistent with their stated intent (e.g. the parity-core SHA-256
values in the test file do not match the SHA-256 of the files on the
base SHA), that is a real issue: it means the guardrails will fail on
the base SHA they purport to protect. Flag it explicitly.

## 8. Confidentiality and use of this package

* This package describes an internal model state and its documented
  limitations. It is not a marketing or sales artifact.
* Do not redistribute outside the agreed reviewer engagement.
* Do not quote the package in lender, investor, regulatory, or
  certification contexts.
* The project will not represent your review, in whole or in part, as
  lender-, bank-, audit-, certification-, regulatory-, or SaaS-grade
  assurance, regardless of your findings.

## 9. Point of contact

All reviewer questions and outputs should be returned through the
agreed review channel. The package owner will route any necessary
clarification back to the appropriate internal track (Agent A for
code/route/service items; Agent B for docs/report items).

---

*End of reviewer instructions.*
