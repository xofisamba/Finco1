# Controlled Generic Scenario Pilot Runbook

This file is the **controlled Generic Scenario pilot
runbook**. It is the B-track governance wrapper for
the UX-focused controlled pilot testing of the
Generic Modelling / Scenario Loop arc after Phase
25B.

> **The controlled pilot is internal, not external.
> It is not a customer reference. It does not
> authorize paid pilot.**
>
> **The controlled pilot is not the external review.
> The external review is a separate workstream.**
>
> **The B18 controlled pilot runbook, the B20 pilot
> issue log process, the B21 pilot user
> acknowledgement, the B22 demo / investor / partner
> QA guardrail, and the B23 reviewer question bank
> are the B-track governance artifacts that govern
> the controlled pilot. B45 is a Generic-Scenario-
> focused runbook that supplements the B18 / B20 /
> B21 / B22 / B23 artifacts.**

---

## 1. Objective

The pilot UX objective is to validate the Generic
Modelling / Scenario Loop arc (Phase 24H, 24H-2,
24H-3, 24H-4, 25B-1, 25B-2, 25B-2.1, 25B-3) with
real users in a controlled internal environment. The
validation is focused on:

* **UX clarity:** are the Generic Modelling UI
  changes clear and understandable?
* **Task efficiency:** can users complete their
  Generic Modelling tasks faster or with fewer
  errors?
* **Visual consistency:** are the visual changes
  consistent across the app?
* **No-regression:** do the UI changes break any
  existing user task?
* **Exploratory banner visibility:** is the
  exploratory banner visible for Generic Solar /
  Generic Wind?
* **What Changed panel:** does the What Changed
  panel render correctly for Generic Solar / Wind
  scenarios with at least 2 runs?

The validation is **not**:

* A model validation.
* A financial formula validation.
* A parity-core lock validation.
* An engine-output golden validation.
* A customer reference.
* A paid pilot authorization.
* An external validation.
* A production readiness or enterprise SaaS
  readiness claim.
* An Excel-parity validation for Generic Solar /
  Wind.

## 2. Allowed participants

* Internal designated pilot users only.
* The pilot user is internal, not external.
* The pilot user is assigned by the user (the
  project owner).

## 3. Allowed data

The controlled pilot uses **TUHO and Oborovo** as
canonical reference projects. TUHO and Oborovo are
the canonical reference projects for the Finco1
model.

The controlled pilot may also use **Generic Solar
and Generic Wind** projects. The Generic Solar /
Generic Wind projects are exploratory and unvalidated
at the time of B45 authoring; the exploratory banner
is required.

The controlled pilot may also use the **sample
project** that the project creation flow generates
when no inputs are provided.

The controlled pilot may **not** use:

* Any project that is not in the canonical reference
  set.
* Any production customer data. No production
  customer data is available; the controlled pilot
  uses only the canonical reference projects and the
  Generic Solar / Generic Wind projects.

## 4. Prohibited data

The controlled pilot is **prohibited** from using
the following:

* Production customer data (not available; canonical
  reference projects and Generic Solar / Wind only).
* Any data that is not in the canonical reference
  set or the Generic Solar / Wind projects.
* Any data that is restricted by the project's
  security / privacy policy.

## 5. Setup checklist

* [ ] **The pilot environment is configured.** The
  controlled pilot uses a local or staging
  environment with the canonical reference projects
  and the Generic Solar / Generic Wind projects
  loaded.
* [ ] **The pilot user is assigned.** A designated
  internal user is assigned to the controlled pilot.
  The pilot user is internal, not external.
* [ ] **The pilot user acknowledgement is signed.**
  The B21 pilot user acknowledgement checklist is
  completed by the pilot user. The acknowledgement
  is internal governance, not a legal contract.
* [ ] **The pilot evidence register is initialized.**
  The B20 pilot evidence register template is
  initialized with the pilot start date, the pilot
  end date, the pilot user, the canonical reference
  projects, and the Generic Solar / Generic Wind
  projects.
* [ ] **The pilot issue log is initialized.** The
  B20 pilot issue log template is initialized.
* [ ] **The pilot friction log is initialized.** The
  B45 friction log (in this runbook) is initialized.
* [ ] **The pilot confusion log is initialized.** The
  B45 confusion log (in this runbook) is initialized.

## 6. Run checklist

* [ ] **The pilot user opens the index page.** The
  pilot user records the screenshot, the console
  log, the network log, and the tab navigation
  trace.
* [ ] **The pilot user runs through tasks T1-T12.**
  The pilot user records the screenshot, the console
  log, the network log, and the tab navigation trace
  for each task.
* [ ] **The pilot user records friction points.**
  The pilot user records any friction point in the
  B45 friction log.
* [ ] **The pilot user records confusion points.**
  The pilot user records any confusion point in the
  B45 confusion log.
* [ ] **The pilot user records issues.** The pilot
  user records any issue in the B20 pilot issue log.
* [ ] **The pilot user records evidence.** The pilot
  user records any evidence in the B20 pilot
  evidence register.

## 7. User task list

The controlled pilot covers the following user tasks:

* **T1:** Open the index page. Verify that the
  runtime summary, validation summary, and banner
  context are visible.
* **T2:** Create a Generic Solar project. Verify
  that the project creation flow is functional and
  the exploratory banner is visible.
* **T3:** Generic Solar task: edit a Generic Solar
  scenario, save it, run it, and verify that the
  output is generated.
* **T4:** Generic Wind task: edit a Generic Wind
  scenario, save it, run it, and verify that the
  output is generated.
* **T5:** Scenario duplicate / edit / save / run
  task: duplicate a scenario, edit it, save it,
  run it, and verify that the output is generated.
* **T6:** Compare task: open the scenario compare
  and verify that the 2-way compare is functional.
* **T7:** 3-way / 4-way compare task: open the
  3-way / 4-way compare and verify that it is
  functional.
* **T8:** Multi-compare task: open the multi-compare
  picker and verify that the picker is functional.
* **T9:** Export / download task: export a Generic
  scenario as a downloadable artifact and verify
  that the artifact is generated correctly.
* **T10:** What Changed panel task: edit a Generic
  Solar scenario, re-run it, and verify that the
  What Changed panel renders the deltas correctly.
* **T11:** Exploratory banner task: verify that the
  exploratory banner is visible for Generic Solar /
  Generic Wind scenarios.
* **T12:** Factory project safety task: open a
  factory project (TUHO / Oborovo), verify that the
  What Changed panel is NOT rendered, and verify
  that the run summary output is unchanged.

## 8. Evidence to collect

The following evidence is collected during the
controlled pilot:

* **Screenshots** of the UI for each task.
* **Browser console logs** for each task.
* **Browser network logs** for each task.
* **Tab navigation traces** for each task.
* **Friction log entries** (per task).
* **Confusion log entries** (per task).
* **Issue log entries** (per issue).
* **Evidence register entries** (per evidence).
* **Export / download artifacts** (per task T9).

The evidence is collected manually by the pilot user
and is committed to the B-track artifacts at the end
of the pilot run.

## 9. Friction log

The friction log records any friction point the
pilot user encounters. A friction point is any
interaction that is slower, harder, or more error-
prone than expected.

* **FL-001:** `<filled in by the pilot user>`
* **FL-002:** `<filled in by the pilot user>`
* **FL-003:** `<filled in by the pilot user>`
* ...

Each friction log entry includes:

* Task ID (T1-T12).
* Severity: low / medium / high.
* Description.
* Screenshot.
* Pilot user.
* Date / time.

## 10. Confusion log

The confusion log records any confusion point the
pilot user encounters. A confusion point is any
interaction where the pilot user is unsure what to
do, what the result means, or how to proceed.

* **CL-001:** `<filled in by the pilot user>`
* **CL-002:** `<filled in by the pilot user>`
* **CL-003:** `<filled in by the pilot user>`
* ...

Each confusion log entry includes:

* Task ID (T1-T12).
* Severity: low / medium / high.
* Description.
* Screenshot.
* Pilot user.
* Date / time.

## 11. Issue severity

Issue severity is defined as:

* **Low:** cosmetic or minor UX issue. Does not
  block the controlled pilot.
* **Medium:** functional issue that the pilot user
  can work around. Does not block the controlled
  pilot but should be fixed in a follow-up PR.
* **High:** functional issue that blocks one or
  more tasks. Blocks the controlled pilot until
  fixed.

## 12. Stop criteria

The controlled pilot is stopped when any of the
following conditions are met:

* **High-severity issue** is identified that blocks
  one or more tasks. The controlled pilot is paused
  until the issue is fixed.
* **Critical data integrity issue** is identified.
  The controlled pilot is paused until the issue is
  fixed.
* **The pilot user is unable to complete any task**
  due to a UI or persistence issue. The controlled
  pilot is paused.
* **The pilot user requests a stop.** The
  controlled pilot is paused.

## 13. Rollback / escalation criteria

The controlled pilot is rolled back or escalated
when any of the following conditions are met:

* **A financial output drift** is detected on TUHO
  or Oborovo. The controlled pilot is rolled back to
  the pre-pilot state and escalated.
* **A parity-core lock drift** is detected. The
  controlled pilot is rolled back to the pre-pilot
  state and escalated.
* **An engine-output golden drift** is detected on
  TUHO or Oborovo. The controlled pilot is rolled
  back to the pre-pilot state and escalated.
* **A model output drift** is detected on TUHO or
  Oborovo. The controlled pilot is rolled back to
  the pre-pilot state and escalated.
* **A schema / migration drift** is detected. The
  controlled pilot is rolled back to the pre-pilot
  state and escalated.
* **A persistence / repository drift** is detected.
  The controlled pilot is rolled back to the pre-
  pilot state and escalated.
* **The factory project run summary output is NOT
  byte-identical to the pre-Phase-25B-3 path.** The
  controlled pilot is rolled back to the pre-pilot
  state and escalated.
* **The exploratory banner is missing for Generic
  Solar / Generic Wind scenarios.** The controlled
  pilot is rolled back to the pre-pilot state and
  escalated.

## 14. Post-run evidence update

After the controlled pilot is complete (or stopped
/ rolled back), the pilot user updates the following
artifacts:

* **B20 pilot issue log** with the per-issue
  entries.
* **B20 pilot evidence register** with the per-
  evidence entries.
* **B21 pilot user acknowledgement** with the per-
  item sign-off entries.
* **B22 Q&A matrix** with the per-Q&A entries.
* **B23 reviewer question bank** with the per-
  question answers.
* **B45 friction log** (this runbook) with the per-
  friction entries.
* **B45 confusion log** (this runbook) with the per-
  confusion entries.

The post-run evidence update is the B-track
governance input to the next B-track governance
refresh.

## 15. What blocks the controlled pilot

The following block the controlled pilot:

* High-severity UX issue that blocks one or more
  tasks.
* Critical data integrity issue.
* Financial output drift on TUHO or Oborovo.
* Parity-core lock drift.
* Engine-output golden drift on TUHO or Oborovo.
* Model output drift on TUHO or Oborovo.
* Schema / migration drift.
* Persistence / repository drift.
* Factory project run summary output is NOT byte-
  identical to the pre-Phase-25B-3 path.
* Exploratory banner is missing for Generic Solar /
  Generic Wind scenarios.
* Any hard-stop condition from the B25 / B33 / B35
  stop / go checklists.
* Any prohibited no-go claim scenario.

## 16. What can be fixed later

The following can be fixed in a follow-up PR and do
not block the controlled pilot:

* Low-severity UX issues.
* Medium-severity UX issues that the pilot user can
  work around.
* Cosmetic issues.
* Minor color contrast improvements.
* Minor wording improvements.
* Minor visual polish.

## 17. No customer reference / no paid pilot authorization

The controlled pilot is **not** a customer
reference. The controlled pilot is **not** a paid
pilot authorization. The controlled pilot is
internal governance.

* No customer reference is made.
* No paid pilot is authorized.
* No production rollout is approved.
* No enterprise SaaS rollout is approved.
* No marketing launch is approved.
* No external validation is claimed.
* No lender / bank / audit / certification /
  regulatory / SaaS claim is made.
* No investment advice or guaranteed returns claim
  is made.
* Generic Solar / Wind remain exploratory and
  unvalidated.
* The exploratory banner is required for Generic
  Solar / Wind.
* The deltas are explanatory; they are not
  investment advice or guaranteed returns.

## 18. What B45 is not

* B45 is not a code change. Agent B does not
  implement Generic Modelling code.
* B45 is not external validation.
* B45 is not a paid pilot authorization.
* B45 is not a customer reference.
* B45 is not a production readiness claim.
* B45 is not an enterprise SaaS readiness claim.
* B45 is not a financial model validation.
* B45 is not a substitute for the user's pilot
  decisions or the user's marketing decisions.
* B45 is not a substitute for the B18 / B20 / B21 /
  B22 / B23 pilot governance artifacts.

## 19. Cross-references

* `reports/pilot/controlled_generic_scenario_pilot_runbook.json`
  (B45, machine-readable)
* `docs/governance/post_phase25b_generic_modelling_governance_refresh.md`
  (B41)
* `docs/validation/generic_scenario_loop_evidence_matrix.md`
  (B42)
* `docs/governance/what_changed_delta_indicator_governance_review.md`
  (B43)
* `docs/commercial/generic_solar_wind_demo_guardrail_refresh.md`
  (B44)
* `docs/validation/scenario_compare_export_evidence_register.md`
  (B46)
* `docs/governance/post25b_readiness_delta_refresh_cadence.md`
  (B47)
* `docs/pilot/controlled_pilot_runbook.md` (B18, the
  non-Generic-Scenario controlled pilot runbook)
* `docs/pilot/controlled_pilot_ux_runbook.md` (B39,
  the post-Phase 54-56 UI pilot runbook)
* `docs/pilot/pilot_issue_log_process.md` (B20)
* `docs/pilot/pilot_user_acknowledgement.md` (B21)
* `docs/commercial/demo_qa_guardrail.md` (B22)
* `docs/external_review/reviewer_question_bank.md`
  (B23)

---

*End of controlled Generic Scenario pilot runbook.*
