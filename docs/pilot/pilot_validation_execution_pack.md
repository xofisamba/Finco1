# Pilot Validation Execution Pack

This file is the **execution layer** for the controlled pilot
described in `docs/pilot/controlled_pilot_runbook.md` (B7). It turns
the runbook and the B3 validation evidence matrix into concrete,
executable pilot steps. It is **not** a substitute for the runbook;
it builds on top of it.

> **Pilot validation is internal and controlled. It is not external
> validation, not a customer reference, and not a production-readiness
> statement.** The pilot is internal validation with a real human in
> the loop. See `docs/pilot/controlled_pilot_runbook.md` and
> `docs/external_review/no_go_claims.md` for the no-go scope.

---

## 1. Purpose

The Pilot Validation Execution Pack exists to make a pilot
**reproducible**: another pilot operator, on another day, with
similar inputs, can run the same pilot and produce comparable
evidence. The pack converts the runbook's narrative into:

* a setup checklist (gate by gate);
* a run sequence (concrete steps, with expected output ranges);
* an evidence-capture template (what to record, in what format);
* a pass/fail criteria document (how to decide per run);
* a result-summary template (how to close out the pilot);
* an issue-to-evidence mapping (how issues feed back into the B3
  matrix and the no-go list).

It does **not** relax any guardrail in the runbook or the B3
matrix. The B7 runbook remains the authoritative pilot procedure;
this pack is its execution-grade companion.

## 2. Where this pack fits

The pack references the following existing documents. It does not
duplicate their content.

* `docs/pilot/controlled_pilot_runbook.md` — pilot scope, workflow,
  issue categories, success/failure criteria, post-incident review.
* `docs/pilot/pilot_user_feedback_protocol.md` — feedback form, storage,
  aggregation, no-go enforcement.
* `docs/pilot/pilot_issue_triage_process.md` — issue categories,
  severities, outcomes, escalation.
* `docs/ops/support_and_incident_response.md` — support tiers, on-call
  expectations, communication.
* `docs/validation/validation_evidence_matrix.md` and the
  `reports/validation/validation_evidence_matrix.json` — the
  authoritative evidence inventory and the source of truth for which
  areas are pilot-claim-allowed.
* `docs/external_review/no_go_claims.md` — the hard no-go list.
* `docs/validation/internal_vs_external_validation_boundaries.md` —
  the boundary between internal and external claims.

## 3. Files in this pack

| File | Role |
|---|---|
| `docs/pilot/pilot_validation_execution_pack.md` (this file) | Index and reading guide |
| `docs/pilot/pilot_pass_fail_criteria.md` | Per-area pass/fail criteria and decision rules |
| `docs/pilot/pilot_evidence_capture_template.md` | What to capture per run; in what format |
| `reports/pilot/pilot_execution_checklist.json` | Machine-readable gate checklist (initial state: empty) |
| `reports/pilot/pilot_result_summary_template.json` | Machine-readable result-summary template (initial state: empty) |

The two JSON files start in an empty / template state. They are
populated as part of pilot execution, not as part of this package.

## 4. Pilot setup checklist (gate by gate)

The runbook's §2 lists a 10-item setup checklist. The execution
pack turns that into a gate-by-gate sequence. Each gate must be
`passed` before the next gate is started. The
`reports/pilot/pilot_execution_checklist.json` machine-readable
checklist mirrors this list and is the canonical status record.

| Gate | Description | Pass criterion | Reference |
|---|---|---|---|
| G0 | Scope and inputs documented | pilot_scope_doc.md exists, signed | runbook §2 |
| G1 | Pilot user identified and acknowledgement signed | signed ack on file | runbook §3 |
| G2 | Pilot data loaded; non-pilot data excluded | data manifest signed off | runbook §2 |
| G3 | Pilot environment isolated | isolation checklist passed | runbook §2 |
| G4 | Pilot run window defined | start_date / end_date / hours_of_operation recorded | runbook §2 |
| G5 | Issue triage in place | `pilot_issue_triage_process.md` reference confirmed | runbook §2 |
| G6 | User feedback protocol in place | `pilot_user_feedback_protocol.md` reference confirmed | runbook §2 |
| G7 | Support and incident response in place | `support_and_incident_response.md` reference confirmed | runbook §2 |
| G8 | Pilot artifacts storage with retention | storage location and retention policy recorded | runbook §2 |
| G9 | Exit criteria defined | success and failure criteria documented | runbook §7 |
| G10 | No-go acknowledgement | pilot user and operator have signed no-go list | runbook §2 |

When all gates G0–G10 are `passed`, the pilot is authorized to start.

## 5. Pilot run sequence (concrete steps)

For each pilot run, the operator performs the following sequence. Each
step records evidence per the evidence-capture template
(`pilot_evidence_capture_template.md`).

1. **Pre-run.** Confirm the gate checklist is all-passed. Confirm
   the run is in the recorded run window. Confirm the no-go list
   is current.
2. **Run.** Start a model run on the documented pilot input set.
   Record start time, end time, run-time warnings.
3. **Validate.** Compare the model output to the expected output
   range recorded in the pilot scope. Apply the per-area
   pass/fail criteria (`pilot_pass_fail_criteria.md`). Record
   pass / fail / investigate per metric.
4. **Capture.** Capture run logs, validation records, exports, and
   user feedback per the evidence-capture template.
5. **Triage.** If any issue is observed, file a triage record per
   `pilot_issue_triage_process.md` with category, severity, and
   outcome.
6. **Close-out (per run).** If the run is the last run in the
   scope, close out per the result-summary template
   (`pilot_result_summary_template.json`).
7. **Repeat or terminate.** If multiple runs are in scope, repeat
   from step 2. Otherwise, terminate the run window.

## 6. Run / validate / export evidence capture

Per step 4, the operator captures:

* **Run logs.** Start time, end time, run-time warnings, model
  output for each run.
* **Validation records.** Expected output range, observed output,
  per-metric decision (pass / fail / investigate), reviewer
  comment.
* **Exports.** Exported Excel files with names, sizes, and
  checksums (SHA-256).
* **User feedback.** Feedback per
  `pilot_user_feedback_protocol.md`.
* **Issue log.** Every issue observed, with category, severity,
  triage outcome, and resolution.

The full evidence-capture template is in
`pilot_evidence_capture_template.md`. The machine-readable version
is the result-summary template
(`pilot_result_summary_template.json`).

## 7. Pass / fail criteria (summary; full document in
   `pilot_pass_fail_criteria.md`)

The pass/fail criteria document is per area and per metric. It uses
the B3 evidence categories and the B7 issue categories. The full
document defines:

* per-area pass criteria (output range, deterministic behavior,
  audit-trail completeness);
* per-area fail criteria (output outside range, undocumented
  deviation, audit-trail gap);
* per-metric investigation triggers (borderline, ambiguous, or
  known-acceptable deviations).

The criteria are conservative. A pass is a positive internal
signal; it is not external validation.

## 8. Issue severity mapping

The B7 issue categories are `bug`, `unexpected-behavior`, `ux`,
`doc`, `infra`, `scope`. The B7 severities are `pilot-blocker`,
`high`, `medium`, `low`. The execution pack does not add new
categories or severities; it maps each combination to:

* `pilot-blocker` → issue blocks pilot continuation; must be
  resolved or accepted before the pilot continues.
* `high` → issue affects a significant portion of the pilot scope;
  resolution within 3 business days.
* `medium` → issue affects a small portion or has a clear
  workaround; resolution within 1 week.
* `low` → issue is cosmetic or doc-only; resolution within 2 weeks.

A `pilot-blocker` failure on a metric that the per-area pass/fail
criterion defines as `must-pass` is a pilot-blocker. A
`pilot-blocker` failure on a metric defined as `informational` is
recorded but does not block the pilot.

## 9. Pilot result summary template

When the run window closes, the operator files a pilot result
summary using the template in
`reports/pilot/pilot_result_summary_template.json`. The summary
records:

* run-window start / end / hours;
* runs completed / partial / failed;
* per-area pass / fail / investigate;
* per-issue category count;
* anonymized usability themes;
* top suggestions;
* confirmation of no no-go claims made or implied;
* pilot operator signature.

The summary is internal. It is not a customer reference and not
external validation. The summary feeds the B3 matrix update (see
§10).

## 10. Evidence-to-matrix update mapping

When a pilot closes, the operator updates the B3 matrix as follows:

* `current_status` of the affected area is updated to reflect the
  pilot result.
* `evidence_category` may be promoted (e.g. from `internally_tested`
  to `pilot_user_tested`) if the pilot produced positive evidence.
* `missing_evidence` is updated to remove items now satisfied.
* `blockers` is updated.
* `notes` is updated with a short reference to the pilot summary
  (no client-identifying information; per the no-go boundary).
* `pilot_claim_allowed` is **not** relaxed by the pilot alone; it
  remains a project-internal flag. A successful pilot does not
  authorize any external claim.

The matrix update is a normal B-track operation. It does not
require Agent A coordination. It does require a fresh commit and,
if the change is material, a follow-up PR.

## 11. What this pack is not

* It is not a production deployment guide.
* It is not a customer onboarding guide.
* It is not a sales or marketing artifact.
* It is not a substitute for the B7 runbook, the B7 feedback
  protocol, the B7 triage process, or the support / incident
  response procedure.
* It is not external validation. The pilot is internal.

## 12. Cross-references

* `docs/pilot/controlled_pilot_runbook.md` (B7)
* `docs/pilot/pilot_pass_fail_criteria.md` (B9)
* `docs/pilot/pilot_evidence_capture_template.md` (B9)
* `reports/pilot/pilot_execution_checklist.json` (B9, machine-readable)
* `reports/pilot/pilot_result_summary_template.json` (B9, machine-readable)
* `docs/validation/validation_evidence_matrix.md` (B3 narrative)
* `reports/validation/validation_evidence_matrix.json` (B3 matrix)
* `docs/external_review/no_go_claims.md`
* `docs/validation/internal_vs_external_validation_boundaries.md`

---

*End of pilot validation execution pack.*
