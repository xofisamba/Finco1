# Controlled Pilot UX Runbook

This file is the **controlled pilot UX runbook**. It is
the B-track governance wrapper for the UX-focused
controlled pilot testing after the UI improvements
(Phase 54A-56 and the pending Phase 57A LineItemGrid
CAPEX pilot).

> **The controlled pilot is internal, not external. It
> is not a customer reference. It does not authorize
> paid pilot.**
>
> **The controlled pilot is not the external review. The
> external review is a separate workstream.**
>
> **The B20 pilot issue log process, the B21 pilot user
> acknowledgement, the B22 demo / investor / partner
> QA guardrail, and the B23 reviewer question bank are
> the B-track governance artifacts that govern the
> controlled pilot. B39 is a UI-focused runbook that
> supplements the B20 / B21 / B22 / B23 artifacts.**

---

## 1. Pilot UX objective

The pilot UX objective is to validate the UI
improvements (Phase 54A-56 and the pending Phase 57A
LineItemGrid CAPEX pilot) with real users in a
controlled internal environment. The validation is
focused on:

* **UX clarity:** are the UI changes clear and
  understandable?
* **Task efficiency:** can users complete their tasks
  faster or with fewer errors?
* **Visual consistency:** are the visual changes
  consistent across the app?
* **No-regression:** do the UI changes break any
  existing user task?

The validation is **not**:

* A model validation.
* A financial formula validation.
* A parity-core lock validation.
* An engine-output golden validation.
* A customer reference.
* A paid pilot authorization.
* An external validation.
* A production readiness or enterprise SaaS readiness
  claim.

## 2. User task list

The controlled pilot covers the following user tasks:

* **T1:** Open the index page. Verify that the runtime
  summary, validation summary, and banner context are
  visible.
* **T2:** Navigate to the Inputs tab. Verify that the
  Inputs tab is functional in the post-UI-2.6 context.
* **T3:** Create a new project. Verify that the New
  Project form is functional in the post-56C context.
* **T4:** Switch projects. Verify that the project
  switcher is functional in the post-56E context.
* **T5:** Open the Help section. Verify that the Help
  section is accessible in the post-56B context.
* **T6:** View the CAPEX summary. Verify that the
  CAPEX summary grid is rendered correctly via the
  shared LineItemGrid partial.
* **T7:** Check the state banner. Verify that the
  state banner hierarchy is clear in the post-56F
  context.
* **T8:** View the COD. Verify that the COD is derived
  from construction_start_date and
  construction_duration_months in the post-56D
  context.
* **T9:** Submit a run. Verify that the run summary is
  updated correctly.
* **T10:** View the audit. Verify that the validation
  summary is shown correctly in the post-55F context.

## 3. Allowed data

The controlled pilot uses **TUHO and Oborovo only** as
test projects. TUHO and Oborovo are the canonical
reference projects for the Finco1 model.

The controlled pilot may also use the **sample
project** that the project creation flow generates
when no inputs are provided.

The controlled pilot may **not** use:

* Generic solar / wind projects. Generic solar / wind
  remain exploratory and unvalidated.
* Any project that is not in the canonical reference
  set.
* Any production customer data. No production
  customer data is available; the controlled pilot
  uses only the canonical reference projects.

## 4. Prohibited data

The controlled pilot is **prohibited** from using the
following:

* Production customer data (not available; canonical
  reference projects only).
* Generic solar / wind project data (exploratory and
  unvalidated).
* Any data that is not in the canonical reference set.
* Any data that is restricted by the project's
  security / privacy policy.

## 5. Setup checklist

* [ ] **The pilot environment is configured.** The
  controlled pilot uses a local or staging environment
  with the canonical reference projects loaded.
* [ ] **The pilot user is assigned.** A designated
  internal user is assigned to the controlled pilot.
  The pilot user is internal, not external.
* [ ] **The pilot user acknowledgement is signed.** The
  B21 pilot user acknowledgement checklist is
  completed by the pilot user. The acknowledgement is
  internal governance, not a legal contract.
* [ ] **The pilot evidence register is initialized.**
  The B20 pilot evidence register template is
  initialized with the pilot start date, the pilot
  end date, the pilot user, and the canonical
  reference projects.
* [ ] **The pilot issue log is initialized.** The B20
  pilot issue log template is initialized.
* [ ] **The pilot friction log is initialized.** The
  B39 friction log (in this runbook) is initialized.
* [ ] **The pilot confusion log is initialized.** The
  B39 confusion log (in this runbook) is initialized.

## 6. Run checklist

* [ ] **The pilot user opens the index page.** The
  pilot user records the screenshot, the console log,
  the network log, and the tab navigation trace.
* [ ] **The pilot user runs through tasks T1-T10.** The
  pilot user records the screenshot, the console log,
  the network log, and the tab navigation trace for
  each task.
* [ ] **The pilot user records friction points.** The
  pilot user records any friction point in the B39
  friction log.
* [ ] **The pilot user records confusion points.** The
  pilot user records any confusion point in the B39
  confusion log.
* [ ] **The pilot user records issues.** The pilot user
  records any issue in the B20 pilot issue log.
* [ ] **The pilot user records evidence.** The pilot
  user records any evidence in the B20 pilot evidence
  register.

## 7. Evidence to collect

The following evidence is collected during the controlled
pilot:

* **Screenshots** of the UI for each task.
* **Browser console logs** for each task.
* **Browser network logs** for each task.
* **Tab navigation traces** for each task.
* **Friction log entries** (per task).
* **Confusion log entries** (per task).
* **Issue log entries** (per issue).
* **Evidence register entries** (per evidence).

The evidence is collected manually by the pilot user
and is committed to the B-track artifacts at the end
of the pilot run.

## 8. Friction log

The friction log records any friction point the pilot
user encounters. A friction point is any interaction
that is slower, harder, or more error-prone than
expected.

* **FL-001:** `<filled in by the pilot user>`
* **FL-002:** `<filled in by the pilot user>`
* **FL-003:** `<filled in by the pilot user>`
* ...

Each friction log entry includes:

* Task ID (T1-T10).
* Severity: low / medium / high.
* Description.
* Screenshot.
* Pilot user.
* Date / time.

## 9. Confusion log

The confusion log records any confusion point the pilot
user encounters. A confusion point is any interaction
where the pilot user is unsure what to do, what the
result means, or how to proceed.

* **CL-001:** `<filled in by the pilot user>`
* **CL-002:** `<filled in by the pilot user>`
* **CL-003:** `<filled in by the pilot user>`
* ...

Each confusion log entry includes:

* Task ID (T1-T10).
* Severity: low / medium / high.
* Description.
* Screenshot.
* Pilot user.
* Date / time.

## 10. Issue severity

Issue severity is defined as:

* **Low:** cosmetic or minor UX issue. Does not block
  the controlled pilot.
* **Medium:** functional issue that the pilot user can
  work around. Does not block the controlled pilot
  but should be fixed in a follow-up PR.
* **High:** functional issue that blocks one or more
  tasks. Blocks the controlled pilot until fixed.

## 11. Stop criteria

The controlled pilot is stopped when any of the
following conditions are met:

* **High-severity issue** is identified that blocks one
  or more tasks. The controlled pilot is paused until
  the issue is fixed.
* **Critical data integrity issue** is identified. The
  controlled pilot is paused until the issue is fixed.
* **The pilot user is unable to complete any task** due
  to a UI or persistence issue. The controlled pilot is
  paused.
* **The pilot user requests a stop.** The controlled
  pilot is paused.

## 12. Rollback criteria

The controlled pilot is rolled back when any of the
following conditions are met:

* **A financial output drift** is detected on TUHO or
  Oborovo. The controlled pilot is rolled back to the
  pre-pilot state.
* **A parity-core lock drift** is detected. The
  controlled pilot is rolled back to the pre-pilot
  state.
* **An engine-output golden drift** is detected on
  TUHO or Oborovo. The controlled pilot is rolled back
  to the pre-pilot state.
* **A model output drift** is detected on TUHO or
  Oborovo. The controlled pilot is rolled back to the
  pre-pilot state.
* **A schema / migration drift** is detected. The
  controlled pilot is rolled back to the pre-pilot
  state.
* **A persistence / repository drift** is detected. The
  controlled pilot is rolled back to the pre-pilot
  state.

## 13. Post-run evidence update

After the controlled pilot is complete (or stopped /
rolled back), the pilot user updates the following
artifacts:

* **B20 pilot issue log** with the per-issue entries.
* **B20 pilot evidence register** with the per-
  evidence entries.
* **B21 pilot user acknowledgement** with the per-item
  sign-off entries.
* **B22 Q&A matrix** with the per-Q&A entries.
* **B23 reviewer question bank** with the per-question
  answers.
* **B39 friction log** (this runbook) with the per-
  friction entries.
* **B39 confusion log** (this runbook) with the per-
  confusion entries.

The post-run evidence update is the B-track governance
input to the next B-track governance refresh.

## 14. What blocks the controlled pilot

The following block the controlled pilot:

* High-severity UX issue that blocks one or more tasks.
* Critical data integrity issue.
* Financial output drift on TUHO or Oborovo.
* Parity-core lock drift.
* Engine-output golden drift on TUHO or Oborovo.
* Model output drift on TUHO or Oborovo.
* Schema / migration drift.
* Persistence / repository drift.
* Any hard-stop condition from the B25 / B33 stop/go
  checklist.
* Any prohibited no-go claim scenario.

## 15. What can be fixed later

The following can be fixed in a follow-up PR and do not
block the controlled pilot:

* Low-severity UX issues.
* Medium-severity UX issues that the pilot user can
  work around.
* Cosmetic issues.
* Minor color contrast improvements.
* Minor wording improvements.
* Minor visual polish.

## 16. No customer reference / no paid pilot authorization

The controlled pilot is **not** a customer reference.
The controlled pilot is **not** a paid pilot
authorization. The controlled pilot is internal
governance.

* No customer reference is made.
* No paid pilot is authorized.
* No production rollout is approved.
* No enterprise SaaS rollout is approved.
* No marketing launch is approved.
* No external validation is claimed.
* No lender / bank / audit / certification / regulatory
  / SaaS claim is made.
* No investment advice or guaranteed returns claim is
  made.
* Generic solar / wind remain exploratory and
  unvalidated.

## 17. What B39 is not

* B39 is not a code change. Agent B does not implement
  UI code.
* B39 is not external validation.
* B39 is not a paid pilot authorization.
* B39 is not a customer reference.
* B39 is not a production readiness claim.
* B39 is not an enterprise SaaS readiness claim.
* B39 is not a financial model validation.
* B39 is not a substitute for the user's pilot
  decisions or the user's marketing decisions.
* B39 is not a substitute for the B20 / B21 / B22 / B23
  pilot governance artifacts.

## 18. Cross-references

* `reports/pilot/controlled_pilot_ux_runbook.json` (B39,
  machine-readable)
* `docs/governance/post_phase56_ui_governance_refresh.md`
  (B35)
* `docs/ui/phase57a_line_item_grid_visual_review.md` (B36)
* `docs/validation/ui_regression_evidence_matrix.md` (B37)
* `docs/commercial/ui demo_guardrail_refresh.md` (B38)
* `docs/governance/ui3_line_item_grid_migration_governance_plan.md`
  (B40)
* `docs/pilot/controlled_pilot_runbook.md` (B18, the
  non-UX controlled pilot runbook)
* `docs/pilot/pilot_issue_log_process.md` (B20)
* `docs/pilot/pilot_user_acknowledgement.md` (B21)
* `docs/commercial/demo_qa_guardrail.md` (B22)
* `docs/external_review/reviewer_question_bank.md` (B23)

---

*End of controlled pilot UX runbook.*
