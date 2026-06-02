# Pilot User Feedback Protocol

This file is the **protocol** for collecting feedback from a pilot
user during a controlled pilot run. It defines the feedback format,
the storage and retention rules, and the boundary between feedback
and external claims.

> **Pilot user feedback is internal validation evidence.** It is
> not an external claim, not a customer reference, and not a
> production-readiness statement. See
> `docs/validation/internal_vs_external_validation_boundaries.md`.

---

## 1. Scope

This protocol applies to:

* every controlled pilot run documented in
  `docs/pilot/controlled_pilot_runbook.md`;
* every pilot user who has signed the pilot user acknowledgement
  (§3 of the runbook);
* every pilot operator responsible for collecting and storing the
  feedback.

## 2. What the pilot user is asked to provide

For each run, the pilot user provides:

* **Confirmation of completion.** Did the run, validate, and
  export steps complete? If not, where did it stop?
* **Output range check.** Did the model output fall within the
  expected output range recorded in the pilot scope? If not, by
  how much, and in which metrics?
* **Usability observations.** Anything the user noticed about the
  experience: confusing UI, missing context, slow operations,
  unexpected behavior, etc.
* **Suggestions.** Any change the user would suggest, with a short
  rationale. Suggestions are not commitments.
* **Blockers.** Anything that prevented the user from completing
  the run as documented. Blockers are recorded and triaged per
  `pilot_issue_triage_process.md`.

The user is **not** asked to provide:

* a statement of confidence in the model's correctness for any
  external use;
* a comparison to any other model or tool the user has used;
* a forward-looking statement about the model's fitness for any
  purpose;
* any claim, quote, or attribution that could be used externally.

## 3. Feedback format

Feedback is recorded in a structured form. The form has the
following fields:

* `pilot_run_id` — unique identifier for the run.
* `pilot_user_id` — identifier of the pilot user (anonymized if
  required by the pilot agreement).
* `run_completed` — `true` / `false` / `partial`.
* `output_range_pass` — `true` / `false` / `not_applicable`.
* `output_range_deviation` — short summary, if applicable.
* `usability_observations` — short text.
* `suggestions` — short text.
* `blockers` — short text or list of issue IDs.
* `no_go_claim_made` — `true` / `false`. Must be `false`.
* `feedback_date` — date of feedback.
* `feedback_format_version` — version of this protocol used.

The form is stored in the pilot-only location with retention per
§5.

## 4. Storage and confidentiality

* Feedback is stored in a pilot-only location, with access
  limited to the pilot operator, the project team, and any
  explicitly authorized third party (e.g. an internal auditor).
* Feedback is **not** shared with anyone outside the agreed pilot
  channel, including other pilot users, unless the user explicitly
  consents in writing.
* Feedback is **not** used in any external-claim language, in any
  marketing material, in any sales conversation, or in any
  external review document, without the pilot user's explicit
  written consent.
* Feedback is **not** attributed to the pilot user by name in any
  external context.

## 5. Retention

* Feedback is retained for the duration of the pilot plus 12
  months, unless the pilot agreement specifies a different
  retention period.
* After the retention period, feedback is anonymized or deleted
  per the pilot agreement.
* The pilot summary report (per
  `controlled_pilot_runbook.md` §7) is retained for the lifetime
  of the project, but is also internal-only.

## 6. Aggregation and reporting

The pilot operator aggregates feedback across runs and users. The
aggregation is internal and includes:

* counts of runs completed / partial / failed;
* counts of output range pass / fail / not applicable;
* counts of issue categories;
* anonymized usability themes;
* a short list of top suggestions.

The aggregated report is internal. It is **not** a customer
satisfaction score, **not** an NPS, **not** a Net Promoter Score
or any equivalent. It is an internal pilot evidence summary.

## 7. The boundary

The boundary between internal feedback and external claim is
enforced by:

* the no-go claim list
  (`docs/external_review/no_go_claims.md`);
* the runbook's no-go enforcement
  (`controlled_pilot_runbook.md` §7.3);
* the pilot user acknowledgement
  (`controlled_pilot_runbook.md` §3);
* the protocol's storage and confidentiality rules (§4).

A breach of the boundary is a serious issue. The remedy is to
revert the breach, identify how it happened, and update the
process to prevent recurrence.

## 8. What this protocol is not

This protocol is not:

* a customer satisfaction survey;
* a user research protocol;
* a marketing or sales feedback tool;
* a substitute for the B3 validation evidence matrix.

It is an internal validation protocol. Its outputs are internal
validation evidence.

## 9. Cross-references

* `docs/pilot/controlled_pilot_runbook.md`
* `docs/pilot/pilot_issue_triage_process.md`
* `docs/ops/support_and_incident_response.md`
* `reports/pilot/pilot_readiness_checklist.json`
* `docs/validation/internal_vs_external_validation_boundaries.md`
* `docs/external_review/no_go_claims.md`

---

*End of pilot user feedback protocol.*
