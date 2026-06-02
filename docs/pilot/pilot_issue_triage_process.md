# Pilot Issue Triage Process

This file is the **triage process** for issues encountered during a
controlled pilot run. It defines issue categories, severities, the
triage workflow, escalation, and the boundary between triage
outcomes and external claims.

> **Triage outcomes are internal.** They are not external claims
> and are not shared with anyone outside the agreed pilot channel
> without explicit, written consent.

---

## 1. Issue categories

Issues are categorized per
`controlled_pilot_runbook.md` §5:

* `bug` — model output is incorrect per the pilot scope.
* `unexpected-behavior` — model output is outside expected range
  but the source of the deviation is unknown.
* `ux` — model behaves as documented; user experience is poor.
* `doc` — documentation is incorrect or incomplete.
* `infra` — pilot environment has a problem (network, storage,
  deployment).
* `scope` — pilot user attempts to use the model outside the
  documented scope.

## 2. Severities

* **`pilot-blocker`** — the issue prevents the pilot from
  continuing or producing valid evidence. Triage must complete
  within 24 hours of issue report.
* **`high`** — the issue affects a significant portion of the pilot
  scope but does not block all of it. Triage within 3 business
  days.
* **`medium`** — the issue affects a small portion of the pilot
  scope or has a clear workaround. Triage within 1 week.
* **`low`** — the issue is cosmetic, doc-only, or a minor UX nit.
  Triage within 2 weeks.

## 3. Triage workflow

The triage workflow is a six-step process:

1. **Report.** The pilot user or pilot operator reports the issue
   using the issue form (see §4). The report includes the issue
   category, severity, run ID, and a short description.
2. **Acknowledge.** The pilot operator acknowledges the report
   within 4 business hours, by changing the issue status from
   `reported` to `acknowledged`.
3. **Investigate.** The pilot operator investigates the issue,
   possibly with help from the project team. The investigation
   produces one of the outcomes in §5.
4. **Decide.** The pilot operator decides the action: fix, defer,
   accept, or escalate.
5. **Resolve.** The action is executed. For `bug` and
   `unexpected-behavior`, resolution is required for the pilot to
   continue. For other categories, resolution is not required.
6. **Close.** The issue is closed. A short closure note is
   recorded. The pilot user is informed.

## 4. Issue form

Each issue has the following fields:

* `issue_id` — unique identifier.
* `pilot_run_id` — the run that surfaced the issue.
* `pilot_user_id` — identifier of the reporter (anonymized if
  required).
* `category` — one of the categories in §1.
* `severity` — one of the severities in §2.
* `description` — short text describing the issue.
* `repro_steps` — short text describing how to reproduce, if
  applicable.
* `reported_at` — date and time of the report.
* `status` — `reported` / `acknowledged` / `investigating` /
  `decided` / `resolved` / `closed` / `escalated`.
* `decision` — short text describing the action (fix, defer,
  accept, escalate).
* `resolution_note` — short text describing the resolution, if
  applicable.
* `closed_at` — date and time of closure.

The issue is stored in the pilot-only location.

## 5. Investigation outcomes

The investigation produces one of the following outcomes:

* **`confirmed-bug`** — the model has a bug. The fix is required
  before the pilot continues.
* **`known-acceptable-deviation`** — the deviation is known and
  acceptable per the pilot scope's tolerance. The pilot continues
  with the deviation recorded.
* **`transcription-error`** — the deviation is due to an input
  transcription error. The transcription is corrected and the
  pilot run is repeated.
* **`scope-misalignment`** — the deviation is because the pilot
  user or operator is using the model outside the documented
  scope. The pilot scope is reviewed and clarified.
* **`environment-issue`** — the deviation is due to the pilot
  environment. The environment is fixed; the model is not at
  fault.
* **`cannot-reproduce`** — the issue cannot be reproduced. The
  issue is closed with the cannot-reproduce note. If the issue
  recurs, it is reopened.

## 6. Escalation

Escalation is appropriate when:

* the issue is a `pilot-blocker` and the fix is not in the
  project's near-term scope;
* the issue crosses an area not in the pilot scope but appears to
  be a model bug;
* the issue involves a no-go claim (the pilot user has made or
  implied a no-go claim);
* the issue involves a confidentiality breach (pilot data,
  outputs, or experience shared outside the agreed channel).

Escalation goes to the project lead. The project lead decides the
next step. Escalation is recorded, not silent.

## 7. The no-go boundary

The no-go claim list
(`docs/external_review/no_go_claims.md`) applies in full during
triage. A pilot user or operator making or implying a no-go claim
is escalated per §6, and the pilot is paused or terminated per
`controlled_pilot_runbook.md` §7.3.

## 8. What this process is not

This process is not:

* a customer support process for a production system;
* a bug-tracking system for the open-source project;
* a substitute for the project's internal engineering triage;
* an external-facing process.

It is a **pilot-scoped** triage process. Its outputs are internal
pilot evidence.

## 9. Cross-references

* `docs/pilot/controlled_pilot_runbook.md`
* `docs/pilot/pilot_user_feedback_protocol.md`
* `docs/ops/support_and_incident_response.md`
* `reports/pilot/pilot_readiness_checklist.json`
* `docs/validation/internal_vs_external_validation_boundaries.md`
* `docs/external_review/no_go_claims.md`

---

*End of pilot issue triage process.*
