# Pilot Evidence Capture Template

This file is the **per-run evidence-capture template** for the
controlled pilot. It defines what to record, in what format, and
where. It is the source of truth for the contents of
`reports/pilot/pilot_result_summary_template.json` when the pilot
closes.

> **Pilot evidence is internal. It is not external validation, not
> a customer reference, and not a production-readiness
> statement.** See `docs/pilot/controlled_pilot_runbook.md` and
> `docs/external_review/no_go_claims.md`.

---

## 1. Scope

This template applies to every controlled pilot run documented in
`docs/pilot/controlled_pilot_runbook.md` (B7). Every run records
the items in §2.

## 2. What to record per run

### 2.1 Run identification

* `run_id` — unique identifier (assigned by the pilot operator).
* `pilot_user_id` — identifier of the pilot user (anonymized per
  the pilot agreement).
* `pilot_operator_id` — identifier of the pilot operator.
* `run_window_start` — start of the run window (date).
* `run_window_end` — end of the run window (date).
* `hours_of_operation` — recorded hours within the run window.
* `pilot_scope_doc` — path to the pilot scope document.
* `no_go_acknowledgement_on_file` — boolean.
* `pilot_user_acknowledgement_on_file` — boolean.

### 2.2 Run logs

* `start_time` — ISO-8601 timestamp.
* `end_time` — ISO-8601 timestamp.
* `duration_seconds` — computed.
* `run_time_warnings` — list of warning strings (may be empty).
* `model_output_path` — path to the model output file (CSV or
  similar).
* `model_output_size_bytes` — size of the model output.
* `model_output_sha256` — SHA-256 of the model output.
* `git_commit_at_run` — git HEAD SHA at the time of the run.
* `input_set_path` — path to the input set used.
* `input_set_sha256` — SHA-256 of the input set.

### 2.3 Validation records

For each metric evaluated per `pilot_pass_fail_criteria.md`:

* `area_id` — B3 matrix area identifier.
* `metric` — metric name.
* `expected_value` — expected value (or range).
* `expected_tolerance` — tolerance (absolute or percent).
* `observed_value` — observed value from the model output.
* `delta` — observed − expected.
* `decision` — `pass` / `fail` / `investigate`.
* `reviewer_comment` — short text (may be empty).

A metric not in the criteria document is recorded with
`classification: informational` and `decision: informational`.

### 2.4 Exports

* `export_id` — unique identifier.
* `export_format` — `xlsx` (Excel) or other.
* `export_filename` — file name.
* `export_path` — path.
* `export_size_bytes` — size.
* `export_sha256` — SHA-256.
* `worksheets_present` — list of worksheet names.
* `numeric_content_match` — boolean (true if all values match the
  model output within the same tolerance as the corresponding
  metric).

### 2.5 Screenshots and logs

Screenshots of the user-facing run are recorded when they document
something the run logs do not. Examples: a specific UI warning that
the operator needs to capture, a specific UI state during the run,
a specific error dialog.

* `screenshot_id` — unique identifier.
* `screenshot_path` — path.
* `screenshot_sha256` — SHA-256.
* `screenshot_caption` — short text explaining what the screenshot
  documents.
* `screenshot_taken_at` — ISO-8601 timestamp.

### 2.6 User feedback

Per `docs/pilot/pilot_user_feedback_protocol.md`:

* `feedback_id` — unique identifier.
* `pilot_user_id` — anonymized.
* `run_completed` — boolean.
* `output_range_pass` — boolean (or `not_applicable`).
* `output_range_deviation` — short text.
* `usability_observations` — short text.
* `suggestions` — short text.
* `blockers` — short text or list of issue IDs.
* `no_go_claim_made` — must be `false`.
* `feedback_date` — ISO-8601 date.
* `feedback_format_version` — version of the feedback protocol.

### 2.7 Issue log

For each issue observed, per `docs/pilot/pilot_issue_triage_process.md`:

* `issue_id` — unique identifier.
* `pilot_run_id` — run that surfaced the issue.
* `category` — `bug` / `unexpected-behavior` / `ux` / `doc` / `infra` /
  `scope`.
* `severity` — `pilot-blocker` / `high` / `medium` / `low`.
* `description` — short text.
* `repro_steps` — short text.
* `reported_at` — ISO-8601 timestamp.
* `status` — `reported` / `acknowledged` / `investigating` /
  `decided` / `resolved` / `closed` / `escalated`.
* `decision` — short text.
* `resolution_note` — short text.
* `closed_at` — ISO-8601 timestamp.
* `escalation_path` — short text (if escalated).

### 2.8 Required artifacts checklist

The following artifacts must be present at run close:

* [ ] `run_id` recorded
* [ ] `start_time` and `end_time` recorded
* [ ] `git_commit_at_run` recorded
* [ ] `model_output_sha256` recorded
* [ ] At least one validation record per area evaluated
* [ ] At least one export with `export_sha256` and
  `numeric_content_match` recorded
* [ ] At least one user feedback record
* [ ] All issues triaged
* [ ] No `no_go_claim_made: true` in any feedback record

If any of the above is missing at run close, the run is recorded as
`incomplete` and is not evaluated against pass / fail criteria.

## 3. Storage and retention

* All evidence is stored in the pilot-only location defined in the
  pilot scope.
* Retention is per `docs/pilot/pilot_user_feedback_protocol.md` §5.
* Evidence is internal. It is **not** shared with anyone outside the
  agreed pilot channel.
* Evidence is **not** used in any external-claim language, in any
  marketing material, in any sales conversation, or in any
  external review document, without the pilot user's explicit
  written consent.

## 4. Mapping to the result summary

The result summary template
(`reports/pilot/pilot_result_summary_template.json`) aggregates the
per-run evidence into a per-pilot summary. The mapping is:

* `runs_completed / runs_partial / runs_failed` ← counts of run
  decisions across the run window.
* `per_area_pass / per_area_fail / per_area_investigate` ← counts of
  per-area pass / fail / investigate decisions, summed across all
  runs in the run window.
* `per_issue_category_count` ← counts of issues by category.
* `anonymized_usability_themes` ← top themes from `usability_observations`
  across all feedback records.
* `top_suggestions` ← top suggestions from `suggestions` across all
  feedback records.
* `no_go_claims_made_or_implied` ← must be `false`. If any feedback
  record has `no_go_claim_made: true`, the pilot is escalated and
  the run window is paused or terminated.
* `pilot_operator_signature` — signed at summary close.

## 5. What this template is not

* It is not a customer satisfaction survey.
* It is not a user research protocol.
* It is not a marketing or sales feedback tool.
* It is not external validation.
* It is not a substitute for the B7 runbook, the B7 feedback
  protocol, the B7 triage process, or the support / incident
  response procedure.

## 6. Cross-references

* `docs/pilot/pilot_validation_execution_pack.md` (B9)
* `docs/pilot/pilot_pass_fail_criteria.md` (B9)
* `docs/pilot/controlled_pilot_runbook.md` (B7)
* `docs/pilot/pilot_user_feedback_protocol.md` (B7)
* `docs/pilot/pilot_issue_triage_process.md` (B7)
* `reports/pilot/pilot_result_summary_template.json` (B9, machine-readable)

---

*End of pilot evidence capture template.*
