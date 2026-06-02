# Support and Incident Response

This file is the **support and incident response** procedure for
controlled pilot runs of the Finco1 model. It defines what counts
as an incident, the response tiers, on-call expectations,
communication, post-incident review, and the boundary between
support and external claims.

> **Pilot support is internal.** It is not customer support for a
> production system, and it does not constitute an SLA, warranty,
> or service-level commitment of any kind. See
> `docs/external_review/no_go_claims.md` §3.

---

## 1. Scope

This file applies to:

* controlled pilot runs documented in
  `docs/pilot/controlled_pilot_runbook.md`;
* the model runtime, including the web layer, the Streamlit UI,
  the API, and any pilot-deployed instance;
* the pilot environment itself, including deployment, networking,
  storage, and observability tooling scoped to the pilot.

This file does **not** apply to:

* production deployments (none at this time);
* customer support (no customers at this time);
* the project-internal engineering support process for the open
  codebase.

## 2. What counts as an incident

An **incident** is any event that:

* prevents a pilot user from completing a documented run;
* causes a model output that is incorrect per the pilot scope's
  expected output range, and the cause is not yet known;
* exposes pilot data, pilot outputs, or pilot experience outside
  the agreed channel;
* causes a no-go claim to be made or implied by any pilot user,
  pilot operator, or third party.

A **non-incident** is:

* a UX issue (handled per `pilot_issue_triage_process.md` §1, `ux`
  category);
* a doc issue (same);
* a pilot environment issue that does not affect model behavior
  (handled by the pilot operator);
* a scope misalignment (handled per
  `pilot_issue_triage_process.md` §5, `scope-misalignment`
  outcome).

## 3. Response tiers

Incidents are responded to in tiers:

* **Tier 1 — Pilot-blocker.** The incident prevents the pilot
  from continuing or producing valid evidence. Response within
  4 business hours. The pilot is paused.
* **Tier 2 — High.** The incident affects a significant portion
  of the pilot scope but does not block all of it. Response
  within 1 business day.
* **Tier 3 — Medium.** The incident affects a small portion of
  the pilot scope or has a clear workaround. Response within
  3 business days.
* **Tier 4 — Low.** The incident is cosmetic or has no impact on
  pilot evidence. Response within 1 week.

The pilot operator assigns the tier at incident creation. The
project lead may re-tier.

## 4. On-call expectations

The pilot operator is on-call during the pilot window. The
expectations are:

* **Tier 1** — on-call responds within 1 hour, begins
  investigation immediately, escalates to the project lead within
  4 hours if the incident is not resolved.
* **Tier 2** — on-call responds within 4 business hours, begins
  investigation within 1 business day.
* **Tier 3** — on-call responds within 1 business day, begins
  investigation within 3 business days.
* **Tier 4** — on-call responds within 3 business days, begins
  investigation within 1 week.

"On-call" here means: the operator is reachable via the agreed
pilot channel and can begin investigation. It does not mean the
operator is awake at 3 a.m. unless the pilot agreement specifies
extended hours.

## 5. Communication

Communication during an incident is:

* **internal** — only pilot users, pilot operators, the project
  team, and any explicitly authorized third party;
* **structured** — incident updates follow the agreed format
  (status, scope, mitigation, ETA);
* **time-stamped** — every update has a date and time;
* **retention-bound** — all incident communication is retained
  per the retention policy in `pilot_user_feedback_protocol.md` §5.

Communication is **not**:

* public;
* shared with anyone outside the agreed pilot channel;
* used in any external-claim language;
* attributed to a pilot user by name in any external context.

## 6. Post-incident review

Every Tier 1 and Tier 2 incident has a post-incident review. The
review is internal and produces:

* a timeline of the incident (detection, response, mitigation,
  resolution);
* a root-cause analysis (or a documented "unknown" with a follow-up
  plan);
* a list of contributing factors;
* a list of corrective actions, with owners and target dates;
* a classification (bug, configuration, environment, scope, other).

Tier 3 and Tier 4 incidents have a short post-incident note, not a
full review.

Post-incident reviews are **not**:

* public;
* shared outside the agreed pilot channel without consent;
* used as external claims.

## 7. The no-go boundary

The no-go claim list
(`docs/external_review/no_go_claims.md`) applies in full to
support and incident response. A pilot user, operator, or third
party making or implying a no-go claim during an incident is
escalated to the project lead. The incident is paused or
terminated per `controlled_pilot_runbook.md` §7.3.

## 8. What this file is not

This file is not:

* a customer support SLA;
* a production-incident response procedure;
* a substitute for the project's open-source engineering support;
* an external-facing process.

It is a **pilot-scoped** support and incident response procedure.
It does not create any obligation beyond the pilot agreement.

## 9. Cross-references

* `docs/pilot/controlled_pilot_runbook.md`
* `docs/pilot/pilot_issue_triage_process.md`
* `docs/pilot/pilot_user_feedback_protocol.md`
* `reports/pilot/pilot_readiness_checklist.json`
* `docs/validation/internal_vs_external_validation_boundaries.md`
* `docs/external_review/no_go_claims.md`

---

*End of support and incident response.*
