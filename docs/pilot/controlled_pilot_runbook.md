# Controlled Pilot Runbook

This runbook is the **operational guide** for running a controlled
pilot of the Finco1 model with a real human user. It covers pilot
setup, the run / validate / export workflow, evidence collection,
known limitations, no-go claims, and what constitutes pilot success.

> **A pilot is internal validation with a real human in the loop.**
> It is not a production rollout, not a customer reference, not an
> external claim of any kind. See
> `docs/validation/internal_vs_external_validation_boundaries.md`
> and `docs/external_review/no_go_claims.md` for the full no-go
> scope.

---

## 1. Pilot scope

A controlled pilot is a time-boxed, scoped exercise in which one or
more pilot users run the Finco1 model through a defined workflow on
defined inputs, and report their experience.

The pilot is in scope only for areas that have been classified in
the B3 validation evidence matrix
(`reports/validation/validation_evidence_matrix.json`) as:

* `pilot_claim_allowed: true`, **and**
* `external_claim_allowed: false` (a pilot does not imply an
  external claim).

At the time of writing, the pilot-claim-allowed areas include TUHO,
Oborovo, senior debt (TUHO/Oborovo scope), distributions (TUHO/Oborovo
scope), tax (sub-area-by-sub-area), sponsor economics, Excel export,
Phase 51F guardrails, Phase 51G-1 `/save-run` (after Agent A's
Phase 51G-2 extraction), B1 external review package, and UI
warnings.

Out of pilot scope:

* generic solar and generic wind (B2 acquisition in progress;
  `pilot_claim_allowed: false`);
* BESS / hybrid full flow (waterfall in progress per README);
* G20, R99, R102, `partial_pay_sweep`, flat/min DSCR sculpting
  (blocked or not approved);
* any area where `pilot_claim_allowed: false`.

## 2. Pilot setup checklist

Before the pilot starts, the following must be in place. Each item
is a gate; missing any one blocks pilot start. The same checklist
in machine-readable form is in
`reports/pilot/pilot_readiness_checklist.json`.

* [ ] Pilot scope and inputs are documented, with the specific
      model area(s) under test, the specific input set, and the
      expected output range.
* [ ] Pilot users are identified, with a signed pilot-user
      acknowledgement (see §3).
* [ ] Pilot data is loaded; non-pilot data is excluded.
* [ ] Pilot environment is isolated; no production data, no
      customer data, no third-party NDA data is accessible.
* [ ] Pilot run window is defined (start date, end date, hours of
      operation).
* [ ] Issue triage process is in place (see
      `pilot_issue_triage_process.md`).
* [ ] User feedback protocol is in place (see
      `pilot_user_feedback_protocol.md`).
* [ ] Support and incident response are in place (see
      `support_and_incident_response.md`).
* [ ] All pilot artifacts (logs, exports, feedback) are stored in
      a pilot-only location, with retention policy defined.
* [ ] Pilot exit criteria are defined (see §7).
* [ ] No-go claim list is acknowledged by every pilot user and
      pilot operator.

## 3. Pilot user acknowledgement

Before a pilot user touches the model, the user signs an
acknowledgement that includes:

* the pilot scope (specific area, specific inputs, expected output
  range);
* the no-go claim list (the user is explicitly forbidden from
  making or implying any no-go claim based on the pilot);
* the feedback protocol (the user agrees to provide feedback in
  the documented format);
* the confidentiality boundary (the user agrees not to share pilot
  data, pilot outputs, or pilot experience outside the agreed
  channel);
* the exit conditions (the user agrees that the pilot ends on the
  documented end date, or earlier if exit criteria are met).

The acknowledgement is signed (or otherwise recorded) per the
project's pilot-user onboarding process.

## 4. Run / validate / export workflow

The pilot workflow is a defined sequence of model operations. The
pilot user is expected to follow it. Each step records evidence.

1. **Run.** Start a model run on the documented pilot input set.
   Record start time, end time, and any run-time warnings.
2. **Validate.** Compare the model output to the expected output
   range recorded in the pilot scope. Record any deviations.
3. **Export.** Export the model output to the documented export
   format (Excel). Record the export file name, size, and checksum.
4. **Inspect.** The pilot user inspects the export for the
   scenarios and metrics in the pilot scope. Record any
   observations.
5. **Feedback.** The pilot user provides feedback per
   `pilot_user_feedback_protocol.md`.
6. **Repeat or close.** If the pilot scope has multiple runs, the
   user repeats. Otherwise, the run is closed and the next step
   is feedback consolidation.

The pilot operator is responsible for ensuring each step is
followed. Deviations from the workflow are recorded, not enforced
silently.

## 5. Issue categories

Issues encountered during the pilot are categorized as:

* **`bug`** — the model produces an output that is incorrect per
  the pilot scope's expected output range. **Pilot-blocker.**
* **`unexpected-behavior`** — the model produces an output that is
  outside the expected range but the source of the deviation is
  not yet known. **Pilot-blocker until triaged.**
* **`ux`** — the model behaves as documented but the user
  experience is poor. **Not pilot-blocker.** Goes to UX backlog.
* **`doc`** — the documentation is incorrect or incomplete.
  **Not pilot-blocker.** Goes to docs backlog.
* **`infra`** — the pilot environment itself has a problem (network,
  storage, deployment). **Not a model issue.** Handled by the
  pilot operator.
* **`scope`** — the pilot user attempts to use the model outside
  the documented scope. **Handled per the scope agreement.**

The full triage process is in `pilot_issue_triage_process.md`.

## 6. Evidence collection

The pilot produces the following evidence. Each item is recorded
and stored in the pilot-only location.

* **Run logs** — start time, end time, run-time warnings, model
  output for each run.
* **Validation records** — expected output range, observed output,
  deviation, decision (pass / fail / investigate).
* **Exports** — exported Excel files with names, sizes, and
  checksums.
* **User feedback** — feedback per `pilot_user_feedback_protocol.md`.
* **Issue log** — every issue encountered, with category, severity,
  triage outcome, and resolution.
* **Pilot summary** — at the end of the pilot window, a summary
  report per the structure in §7.

The evidence is internal. It is not used for any external claim
and is not shared outside the agreed pilot channel.

## 7. Pilot exit and success criteria

### 7.1 Exit triggers

The pilot ends when any of the following is true:

* the documented end date is reached;
* the exit criteria in §7.2 are met (success);
* the exit criteria in §7.3 are met (failure);
* the pilot operator declares early termination, with a recorded
  rationale.

### 7.2 Success criteria

The pilot is **successful** when:

* all `bug` and `unexpected-behavior` issues are resolved or
  triaged to a known-and-accepted cause;
* `ux` issues are recorded and added to the UX backlog;
* `doc` issues are recorded and added to the docs backlog;
* the pilot user confirms, in writing, that the pilot scope
  behavior matches the documented expected behavior;
* the pilot summary report is filed.

A successful pilot does **not** constitute:

* an external claim of any kind;
* a relaxation of the no-go claim list;
* a production-readiness statement;
* a customer reference.

### 7.3 Failure criteria

The pilot is **unsuccessful** when:

* a `bug` or `unexpected-behavior` issue cannot be resolved within
  the pilot window;
* the pilot user reports that the model does not behave as
  documented in a way that affects the pilot scope;
* the pilot scope's expected output range is consistently violated;
* the pilot data, pilot outputs, or pilot experience are shared
  outside the agreed channel;
* a no-go claim is made or implied by any pilot user or operator.

An unsuccessful pilot does **not** mean the model is broken. It
means the pilot did not produce positive evidence within the
agreed scope. The model may still be correct in the narrow pilot
scope, or the issue may be in the documentation, or the pilot
scope may need adjustment.

## 8. What this runbook is not

This runbook is not:

* a production deployment guide;
* a customer onboarding guide;
* a sales or marketing artifact;
* a substitute for the B3 validation evidence matrix;
* a substitute for the no-go claim list.

A pilot run with this runbook produces **internal validation
evidence**. It does not produce external validation, external
claims, or any of the categories in the no-go list.

## 9. Cross-references

* `docs/pilot/pilot_user_feedback_protocol.md`
* `docs/pilot/pilot_issue_triage_process.md`
* `docs/ops/support_and_incident_response.md`
* `reports/pilot/pilot_readiness_checklist.json`
* `reports/validation/validation_evidence_matrix.json`
* `docs/validation/internal_vs_external_validation_boundaries.md`
* `docs/external_review/no_go_claims.md`

---

*End of controlled pilot runbook.*
