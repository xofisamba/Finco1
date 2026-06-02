# Reviewer Q&A Template

This file is the **structured Q&A template** for the external
reviewer's output. The reviewer is asked to address each question
in this template, with citations to the file and line range at the
base SHA, and a per-question go / conditional-go / no-go opinion.

> **The reviewer is bound by the no-go claim list
> (`docs/external_review/no_go_claims.md`) and is explicitly
> forbidden from producing any external-claim language.** This
> template is internal-validation scaffolding. See
> `docs/validation/internal_vs_external_validation_boundaries.md`.

---

## 1. Required output format

For each question, the reviewer provides:

* **Answer.** A short answer (1–3 sentences).
* **Citation.** File and line range at the base SHA.
* **Opinion.** Per-question go / conditional-go / no-go opinion.
* **Notes.** Any caveats, gaps, or counter-evidence.

The reviewer's overall go / no-go opinion is the intersection of
per-question opinions, plus an explicit acknowledgement of the
no-go claim list (the closing question in §6).

## 2. Top-level questions

The reviewer is asked to address the following top-level questions,
in order.

### 2.1 Scope reality check

* Is the model scope at the base SHA accurately described in
  `docs/external_review/model_scope_and_limitations.md` and
  `docs/validation/validation_evidence_matrix.md`?
* Is the code at the base SHA consistent with the documented
  scope? If not, where does it diverge?
* Are the known limitations honestly documented?

### 2.2 Phase 51F guardrails

* Do the Phase 51F engine-output golden tests (TUHO and Oborovo)
  pass at the base SHA?
* Do the Phase 51F parity-core SHA-256 values match the actual
  SHA-256 of the four parity-core files at the base SHA?
* Does the no-service-imports-main_web/main_api test pass?
* Is the Phase 51F design (`docs/phase51f_parallel_work_guardrails.md`)
  consistent with the code?

### 2.3 TUHO and Oborovo golden parity

* Do the pinned TUHO values match the model's observed output at
  the base SHA? (first_finite_dscr ≈ 1.450695, first_distribution_op_idx = 35, total_operating_periods = 61, opex_total_keur ≈ 85408.27, opex_y1_keur ≈ 1998.01)
* Do the pinned Oborovo values match? (first_finite_dscr ≈ 1.150038, first_distribution_op_idx = 39, total_operating_periods = 60, opex_total_keur ≈ 48847.50, opex_y1_keur ≈ 1338.56)
* Is the pre-flight evidence honest? Is the package-author run
  treated as informational, not as reviewer evidence?

### 2.4 Generic solar and wind

* Are generic solar and wind correctly marked as exploratory and
  unvalidated in the B3 matrix (AREA-003, AREA-004)?
* Is the B2 acquisition framework realistic? Are the
  acceptance thresholds and the no-go enforcement boundary
  appropriate?
* Is the empty inventory and the all-blocked readiness matrix
  consistent with the documented zero-references-acquired state?

### 2.5 B1 no-go list and validation boundaries

* Is the B1 no-go list complete and unambiguous?
* Is the internal vs external validation boundaries document
  consistent with the B1 no-go list and with the B3 matrix?
* Is the boundary between internal and external claims enforced
  consistently across the B-track artifacts?

### 2.6 Phase 51G-1/51G-2/51G-3/51H-1 and Agent A track

* Is the B3 matrix AREA-015 (Phase 51G-1) accurately described
  as characterization only?
* Is the B3 matrix AREA-019 (recent Agent A route / state work)
  accurate? Are 51G-2/51G-3/51H-1 correctly characterized?
* Does the B3 matrix correctly defer pilot claims for /save-run
  until the post-extraction surface area is defined?
* Is the B8 architecture dimension accurate with respect to
  Agent A's recent extractions?
* Is the B8 persistence dimension accurate?

### 2.7 B7 controlled pilot and B9 execution pack

* Is the B7 runbook realistic? Is the no-go enforcement clear?
* Is the B9 execution pack honest? Are the per-area pass/fail
  criteria conservative?
* Is the B9 evidence-capture template sufficient for the per-run
  records?
* Is the B9 result-summary template honest about the boundary
  between internal and external claims?

### 2.8 B10 data room and B11 commercial messaging

* Is the B10 data room complete? Does it cover all B-track
  artifacts? Is the cross-mapping correct?
* Is the B10 reviewer evidence checklist honest?
* Is the B11 commercial messaging guardrail complete? Are the
  prohibited claims exhaustive? Is the red/yellow/green
  language classification clear?

### 2.9 B12 model confidence heatmap

* Is the B12 heatmap honest? Are the confidence labels
  conservative?
* Does the heatmap avoid labels that imply bankability,
  certification, audit approval, or external validation?

### 2.10 B13 paid pilot readiness gate

* Is the B13 gate between controlled internal pilot and
  controlled paid pilot clearly drawn?
* Is the post-pilot evidence update process documented?
* Is the decision memo template honest about the boundary
  between internal and external claims?

### 2.11 B14 governance refresh plan

* Is the trigger for refreshing B3/B7/B8/B9/B10/B12/B13 clear?
* Is the "Agent B never modifies Agent A files" rule explicit?
* Is the tracker JSON for pending refreshes honest?

## 3. Per-B3-area questions

The reviewer is asked to address each B3 matrix area (currently
19) with the same structure as the top-level questions:

* `area_id` and `area_name`
* per-area pass / conditional-go / no-go opinion
* `area_id`'s specific issues, if any

The reviewer is asked to confirm the per-area `external_claim_allowed`
is `false` for every row, and to flag any row where they disagree.

## 4. Per-B1-readiness-matrix questions

The reviewer is asked to address each row in the B1 readiness
matrix (28 rows, A01–A28) with the same structure.

## 5. Documentation / code mismatches

The reviewer is asked to enumerate any documentation / code
mismatches they found, with citation. The package's
`model_scope_and_limitations.md` lists the kinds of mismatches
the reviewer is asked to flag.

## 6. No-go claim acknowledgement (required)

The reviewer's output **must** include, verbatim or substantively
equivalent, the following line:

> "I have read `docs/external_review/no_go_claims.md` and confirm
> I will not reproduce, endorse, or imply any of the no-go claims
> in my output."

The acknowledgement is a gate: a reviewer output that does not
include this line is not accepted.

## 7. The reviewer's overall opinion

The reviewer provides a per-area go / conditional-go / no-go
opinion, with the per-area opinion being the strictest of the
per-question opinions for that area. The reviewer then provides
an overall go / conditional-go / no-go opinion on the package as
a whole.

The reviewer's overall opinion is **not** external validation. It
is a third-party opinion on the project's documented posture. It
is internal validation, conditioned on the no-go claim list.

## 8. What this template is not

* It is not a contract. The reviewer's output is an opinion, not
  a binding agreement.
* It is not external validation.
* It is not a substitute for the B1 external review package or
  any B-track artifact.
* It is not a customer-facing artifact.

## 9. Cross-references

* `docs/external_review/data_room_index.md` (B10)
* `docs/external_review/reviewer_evidence_checklist.md` (B10)
* `reports/external_review/missing_evidence_tracker.json` (B10)
* `docs/external_review/reviewer_instructions.md` (B1)
* `docs/external_review/no_go_claims.md` (B1)
* `docs/validation/internal_vs_external_validation_boundaries.md` (B3)

---

*End of reviewer Q&A template.*
