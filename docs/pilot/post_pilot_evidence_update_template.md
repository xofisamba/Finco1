# Post-Pilot Evidence Update Template

This file is the **post-pilot evidence update template**. It is
populated at pilot close to record pilot findings, issues, and
evidence, and to drive the B3 matrix update, the B12 heatmap
update, the B11 commercial messaging guardrail review, the
B13 paid pilot gate impact assessment, and the B14 governance
refresh tracker update.

> **Do not claim a pilot happened unless actual pilot results
> are later provided.** This template is empty at package
> creation. It is populated only when a controlled pilot has
> actually run. Do not invent pilot results. Do not pre-populate
> the template with hypothetical results.
>
> **Demo script guardrail is internal, not marketing launch
> approval.** The companion document
> (`docs/commercial/demo_script_guardrail.md`) is internal
> governance. It is not a marketing playbook. It does not
> authorize the project to begin external communications. It
> is a guardrail that prevents external claims the project is
> not in a position to support.
>
> **Claude review is separate.** The Phase 51N checkpoint
> includes a Claude review preparation pack on the Agent A
> side; Claude review itself is handled outside this branch.
> B19 does not depend on Claude review.

---

## 1. Pilot findings summary

When the controlled pilot run window closes, the pilot
operator records the following:

* **Pilot run ID** — unique identifier.
* **Pilot user ID** — anonymized identifier of the pilot user.
* **Pilot operator ID** — identifier of the pilot operator.
* **Run window start / end** — date range.
* **Hours of operation** — total hours within the run window.
* **Git commit at run window start / end** — base SHAs.
* **Pilot scope** — the B3 areas covered by the pilot.
* **Pilot result summary path** — the populated result
  summary.
* **Pilot overall decision** — `pass` / `fail` / `investigate`
  / `not_evaluated` (per B9 result summary template).

## 2. Issues found

For each issue observed during the pilot, the pilot operator
records the following:

* **Issue ID** — unique identifier.
* **Pilot run ID** — the run that surfaced the issue.
* **Category** — `bug` / `unexpected-behavior` / `ux` /
  `doc` / `infra` / `scope`.
* **Severity** — `pilot-blocker` / `high` / `medium` / `low`.
* **Description** — short text.
* **Repro steps** — short text.
* **Status** — `reported` / `acknowledged` / `investigating`
  / `decided` / `resolved` / `closed` / `escalated`.
* **Decision** — short text.
* **Resolution note** — short text.
* **Closed at** — ISO-8601 timestamp.

The issues are aggregated into the B7 issue log summary.

## 3. Evidence collected

The pilot operator records:

* **Run logs** — start time, end time, warnings, model output.
* **Validation records** — per-metric decisions.
* **Exports** — Excel, with SHA-256 checksums.
* **Screenshots** — when they document something the run logs
  don't.
* **User feedback** — anonymized.
* **Issue log** — issues with category, severity, outcome.
* **No-go claim acknowledgement** — signed by pilot user and
  operator.

The evidence is stored in the pilot-only location defined in
the pilot scope. Retention is per
`docs/pilot/pilot_user_feedback_protocol.md` §5.

## 4. Matrix rows to update

The B3 matrix is updated with the pilot result. The
per-area update is per the B19 machine-readable template
(`reports/pilot/post_pilot_evidence_update_template.json`).

For each B3 area in the pilot scope:

* `current_status` is updated to reflect the pilot result.
* `evidence_category` may be promoted (e.g. from
  `internally_tested` to `pilot_user_tested`) if the pilot
  produced positive evidence.
* `missing_evidence` is updated to remove items now satisfied.
* `blockers` is updated.
* `notes` is updated with a short reference to the pilot
  summary (no client-identifying information; per the no-go
  boundary).
* `pilot_claim_allowed` is **not** relaxed by the pilot alone;
  it remains a project-internal flag.

The matrix update is a normal B-track operation. It does not
require Agent A coordination. It does require a fresh commit
and, if the change is material, a follow-up PR.

## 5. Heatmap updates

The B12 heatmap is updated if any area's confidence label
changes. The change is per the B12 heatmap update procedure
(`docs/validation/model_confidence_heatmap.md` §6).

A label change that introduces a new green / yellow / red
boundary in the B11 commercial messaging guardrail is also a
B11 update.

## 6. Paid pilot gate impact

The B13 paid pilot gate is updated with the pilot result. The
PG-01 (controlled internal pilot completed) gate is moved
from `pending` to `passed` (assuming the pilot closed with a
positive summary). The other gates remain pending until their
prerequisites are met.

A successful controlled internal pilot does **not** authorize
a paid pilot. The paid pilot gate (B13) is a separate stage
and requires additional gates (PG-01 through PG-14) to be
passed.

## 7. Commercial / no-go claim review

The B11 commercial messaging guardrail is reviewed for any
new claim categories that surfaced during the pilot. If a new
claim category is identified, the prohibited claims register
is updated, the commercial claims review matrix is updated,
and the approved demo language is updated.

A pilot user who violates the no-go language acknowledgement
triggers a pilot pause and a triage review. The guardrail is
strengthened if necessary.

## 8. What this template is not

* It is not a customer satisfaction survey.
* It is not a user research protocol.
* It is not a marketing or sales feedback tool.
* It is not external validation.
* It is not a substitute for the B7 runbook, the B9
  execution pack, the B11 commercial messaging guardrail, the
  B12 heatmap, the B13 paid pilot gate, the B17 remaining
  hotspots tracker, or the B18 controlled pilot launch
  checklist.
* It is not paid pilot authorization. The paid pilot gate
  (B13) is a separate stage.

## 9. Cross-references

* `reports/pilot/post_pilot_evidence_update_template.json`
  (B19, machine-readable)
* `docs/pilot/controlled_pilot_runbook.md` (B7)
* `docs/pilot/pilot_validation_execution_pack.md` (B9)
* `docs/pilot/pilot_pass_fail_criteria.md` (B9)
* `docs/pilot/pilot_evidence_capture_template.md` (B9)
* `reports/pilot/pilot_execution_checklist.json` (B9)
* `reports/pilot/pilot_result_summary_template.json` (B9)
* `docs/validation/validation_evidence_matrix.md` (B3 narrative)
* `reports/validation/validation_evidence_matrix.json` (B3
  matrix)
* `docs/commercial/no_go_claims_commercial_guardrail.md` (B11)
* `docs/validation/model_confidence_heatmap.md` (B12)
* `docs/pilot/paid_pilot_readiness_gate.md` (B13)
* `docs/governance/agent_a_b_governance_refresh_plan.md` (B14)
* `docs/governance/remaining_hotspots_governance_tracker.md`
  (B17)
* `docs/pilot/controlled_pilot_launch_checklist.md` (B18)
* `docs/commercial/demo_script_guardrail.md` (B19)
* `docs/external_review/no_go_claims.md` (B1, no-go list)

---

*End of post-pilot evidence update template.*
