# External Reviewer Question Bank

This file is the **neutral question bank** for a future
external reviewer. It is a list of questions that a third-party
reviewer may ask, organized by topic.

> **This is NOT the external review.** This is NOT Claude
> review. This does not represent reviewer findings. This
> does not claim external validation.**
>
> **Claude review is separate.** The Phase 51N checkpoint
> includes a Claude review preparation pack on the Agent A
> side; Claude review itself is handled outside this branch.
> The question bank does not represent Claude review as
> completed.

---

## 1. Purpose

The question bank is a neutral, pre-written list of questions
that a future external reviewer may address. The questions are
neutral: they do not assume any answer, they do not pre-judge
the reviewer's findings, and they do not authorize any
external claim.

The question bank is a companion to:

* the B1 external review package (PR #390, merged);
* the B10 data room index (PR #398, B15 refresh);
* the B16 external review closeout tracker (PR #413);
* the B22 demo / investor / partner Q&A guardrail (this
  branch).

The question bank does **not** include any reviewer findings.
A reviewer is free to answer the questions however the
reviewer sees fit, subject to the reviewer's acknowledgement
of the no-go claim list (B1) and the B16 closeout tracker's
reviewer rules.

## 2. What this question bank is not

* It is not external validation. The question bank is
  internal governance.
* It is not Claude review. Claude review is separate.
* It is not a substitute for the B1 external review
  package.
* It is not a substitute for the B10 data room index.
* It is not a substitute for the B16 closeout tracker.
* It is not a substitute for any B-track artifact.
* It is not a pre-judged review.
* It is not a marketing or sales artifact.

## 3. Question groups

The question bank has 21 question groups:

1. **Architecture and service boundaries**
2. **Phase 51 route extraction**
3. **Phase 51F guardrails**
4. **Repository / persistence risk**
5. **Scenario / project workflow**
6. **TUHO and Oborovo parity**
7. **Generic solar / wind validation gap**
8. **Senior debt**
9. **SHL**
10. **Tax**
11. **Sponsor economics**
12. **Distributions**
13. **Excel export**
14. **Scenario persistence**
15. **UI workflow**
16. **Pilot scope**
17. **Paid pilot gate**
18. **No-go claims**
19. **Security / auth / permissions**
20. **Deployment / observability**
21. **Enterprise SaaS readiness**

Each question group has 2–5 questions. Each question has:

* `question_id` — unique identifier (e.g. `QR-001`).
* `question_text` — the question to the reviewer.
* `target_area` — the B3 matrix area or B-track artifact
  the question targets.
* `why_it_matters` — short text explaining why the question
  is in the bank.
* `evidence_to_review` — short text pointing to the B-track
  artifacts the reviewer is expected to consult.
* `expected_answer_type` — `factual`, `narrative`, `judgment`,
  or `opinion`. A `judgment` or `opinion` answer is the
  reviewer's own.
* `no_go_claim_risk` — `none`, `low`, `medium`, `high`. The
  risk that the question's answer, if not handled carefully,
  could lead to a no-go claim.
* `current_internal_status` — short text describing the
  current internal state of the target area.
* `external_validation_status` — `not_performed`,
  `pending_external_review`, `in_progress_external`,
  `completed`. For most areas, this is `not_performed` or
  `pending_external_review`.
* `notes` — short text.

The full per-question bank is in
`reports/external_review/reviewer_question_bank.json` (B23,
machine-readable).

## 4. Sample question (illustrative, not a finding)

> **QR-001** — "What is the current state of the model's
> service-backed route count, service module count, and
> remaining inline hotspot count?"

* **Target area:** B8 architecture dimension; B17 remaining
  hotspots tracker.
* **Why it matters:** Establishes the post-Phase 51N state
  for the reviewer's analysis.
* **Evidence to review:** B3 matrix AREA-019 / AREA-020;
  B8 architecture dimension; B17 remaining hotspots
  tracker; B14 governance refresh tracker.
* **Expected answer type:** factual.
* **No-go claim risk:** none. The answer is internal-state
  only.
* **Current internal status:** 12 service-backed routes, 13
  service modules, 5 inline hotspots remaining.
* **External validation status:** not performed.
* **Notes:** This is a factual question; the answer is the
  project's self-assessment and is not externally validated.

## 5. Question groups (overview)

### 5.1 Architecture and service boundaries

* QR-001 to QR-005 (5 questions).
* Target: B8 architecture dimension; Phase 51N checkpoint.
* Why it matters: Establishes the current state of the
  service-extraction work for the reviewer's analysis.

### 5.2 Phase 51 route extraction

* QR-006 to QR-010 (5 questions).
* Target: B3 matrix AREA-019; B14 governance refresh
  tracker; Phase 51G-51N commits.
* Why it matters: Documents the Agent A track's work for the
  reviewer's analysis.

### 5.3 Phase 51F guardrails

* QR-011 to QR-014 (4 questions).
* Target: B3 matrix AREA-014; Phase 51F pins; parity-core
  SHA-256 lock.
* Why it matters: Establishes the project's internal
  regression-protection mechanism.

### 5.4 Repository / persistence risk

* QR-015 to QR-018 (4 questions).
* Target: B3 matrix AREA-013 (persistence); B8 persistence
  dimension; Phase 51G-2, 51H-2, 51J-2, 51K-2, 51L-2,
  51M-2 extractions.
* Why it matters: Documents the post-extraction persisted
  state shape and the pin refresh status.

### 5.5 Scenario / project workflow

* QR-019 to QR-022 (4 questions).
* Target: B3 matrix AREA-013; B17 remaining hotspots
  tracker.
* Why it matters: Documents the 5 remaining inline
  hotspots and the future Agent A work.

### 5.6 TUHO and Oborovo parity

* QR-023 to QR-026 (4 questions).
* Target: B3 matrix AREA-001 / AREA-002; Phase 51F pins.
* Why it matters: Documents the only pinned reference
  projects.

### 5.7 Generic solar / wind validation gap

* QR-027 to QR-029 (3 questions).
* Target: B3 matrix AREA-003 / AREA-004; B2 framework.
* Why it matters: Documents the explicit gap in generic
  validation evidence.

### 5.8 Senior debt

* QR-030 to QR-032 (3 questions).
* Target: B3 matrix AREA-008; Phase 51F parity-core lock.
* Why it matters: Documents the senior-debt policy scope
  and the partial_pay_sweep / flat / min DSCR sculpting
  exclusions.

### 5.9 SHL

* QR-033 to QR-034 (2 questions).
* Target: B3 matrix AREA-009.
* Why it matters: Documents the SHL scope and the gap in
  pilot readiness.

### 5.10 Tax

* QR-035 to QR-037 (3 questions).
* Target: B3 matrix AREA-007.
* Why it matters: Documents the tax sub-area decomposition
  gap and the pilot-readiness status.

### 5.11 Sponsor economics

* QR-038 to QR-040 (3 questions).
* Target: B3 matrix AREA-010.
* Why it matters: Documents the returns scope and the
  pinning gap.

### 5.12 Distributions

* QR-041 to QR-043 (3 questions).
* Target: B3 matrix AREA-011.
* Why it matters: Documents the partial pin and the
  total-distribution gap.

### 5.13 Excel export

* QR-044 to QR-046 (3 questions).
* Target: B3 matrix AREA-012.
* Why it matters: Documents the export scope and the
  format-drift risk.

### 5.14 Scenario persistence

* QR-047 to QR-049 (3 questions).
* Target: B3 matrix AREA-013; B12 heatmap HC-012.
* Why it matters: Documents the post-extraction persisted
  state shape.

### 5.15 UI workflow

* QR-050 to QR-052 (3 questions).
* Target: B3 matrix AREA-017.
* Why it matters: Documents the UI warnings scope and the
  pilot-evidence approach.

### 5.16 Pilot scope

* QR-053 to QR-055 (3 questions).
* Target: B7 runbook; B9 execution pack; B18 launch
  checklist; B20 issue log process.
* Why it matters: Documents the controlled pilot scope
  and the operating process.

### 5.17 Paid pilot gate

* QR-056 to QR-058 (3 questions).
* Target: B13 paid pilot gate; B13 paid pilot decision
  memo template.
* Why it matters: Documents the gate between controlled
  internal pilot and controlled paid pilot.

### 5.18 No-go claims

* QR-059 to QR-062 (4 questions).
* Target: B1 no-go list; B11 commercial messaging
  guardrail; B19 demo script guardrail; B22 Q&A guardrails.
* Why it matters: Documents the no-go claim enforcement
  posture.

### 5.19 Security / auth / permissions

* QR-063 to QR-065 (3 questions).
* Target: B8 security dimension; B8 enterprise SaaS
  readiness tracker; B11 commercial messaging guardrail
  (no SOC 2 / ISO 27001 claim).
* Why it matters: Documents the security posture and the
  external security review gap.

### 5.20 Deployment / observability

* QR-066 to QR-068 (3 questions).
* Target: B8 deployment dimension; B8 observability
  dimension; ops/support_and_incident_response.md.
* Why it matters: Documents the deployment and
  observability posture.

### 5.21 Enterprise SaaS readiness

* QR-069 to QR-071 (3 questions).
* Target: B8 enterprise_saas_readiness dimension; B11
  commercial messaging guardrail (no enterprise SaaS-ready
  claim).
* Why it matters: Documents the explicit non-goal of
  enterprise SaaS readiness and the separate governance
  change that would be required.

## 6. Per-question no-go claim risk

The full per-question no-go claim risk is in
`reports/external_review/reviewer_question_bank.json` (B23,
machine-readable). The risk levels are:

* **None** — the question's answer, if not handled
  carefully, would not lead to a no-go claim.
* **Low** — the question's answer requires context to
  avoid a no-go claim.
* **Medium** — the question's answer requires context and
  no-go claim enforcement.
* **High** — the question's answer is on a topic that is
  frequently misread; the reviewer is explicitly reminded
  of the no-go list.

## 7. What this question bank is not

* It is not external validation. The question bank is
  internal governance.
* It is not Claude review. Claude review is separate.
* It is not a substitute for the B1 external review
  package, the B10 data room, the B16 closeout tracker, or
  any B-track artifact.
* It is not a pre-judged review. The reviewer is free to
  answer the questions however the reviewer sees fit.
* It is not a marketing or sales artifact.

## 8. Cross-references

* `reports/external_review/reviewer_question_bank.json` (B23,
  machine-readable)
* `docs/external_review/external_review_package_index.md` (B1)
* `docs/external_review/reviewer_instructions.md` (B1)
* `docs/external_review/reviewer_evidence_checklist.md` (B10)
* `docs/external_review/reviewer_qna_template.md` (B10)
* `docs/external_review/no_go_claims.md` (B1, no-go list)
* `docs/external_review/data_room_index.md` (B10)
* `docs/external_review/external_review_closeout_tracker.md`
  (B16)
* `docs/external_review/external_review_closeout_status.json`
  (B16)
* `docs/commercial/no_go_claims_commercial_guardrail.md`
  (B11)
* `docs/commercial/demo_qa_guardrail.md` (B22)
* `docs/commercial/investor_partner_qa_guardrail.md` (B22)
* `docs/pilot/controlled_pilot_launch_checklist.md` (B18)
* `docs/pilot/pilot_user_acknowledgement.md` (B21)
* `docs/governance/remaining_hotspots_governance_tracker.md`
  (B17)
* `docs/governance/agent_a_b_governance_refresh_plan.md` (B14)

---

*End of external reviewer question bank.*
