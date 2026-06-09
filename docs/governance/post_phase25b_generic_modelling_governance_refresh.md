# Post-Phase24H/25B Generic Modelling Governance Refresh

This file is the **post-Phase 24H / 25B Generic
Modelling governance refresh**. It is the B-track
governance wrapper for the Generic Modelling / Scenario
Loop arc that Agent A has been working on since the
B35-B40 (post-Phase 56 / 57A) refresh.

> **The Generic Modelling / Scenario Loop arc is
> internal functionality. It is not external
> validation. It is not bankability. It is not a
> market-validated generic template.**
>
> **Generic Solar and Generic Wind remain exploratory
> and unvalidated. Generic defaults are illustrative
> until validated by reference models. The scenario
> compare, the export / download pack, and the
> "What Changed" delta panel are internal functionality
> — not model validation, not bankability, not
> investment advice.**
>
> **Agent B does not implement code. Agent A implements
> code, tests, and the persistence rotation. Agent B
> records the B-track governance state for the Generic
> Modelling / Scenario Loop arc.**

---

## 1. Phase coverage

B41 covers the following Generic Modelling / Scenario
Loop phases and their B-track governance posture.

### 1.1 Phase 24-H — Editable Generic Project Run Loop

* **Phase 24-H (PR #562 or equivalent):** Editable
  Generic Project Run Loop (UI + minimal-orchestration).
  The edit → save → run loop is the foundation for the
  Generic Modelling arc. Tests-only + docs + report in
  some PRs; UI + minimal-orchestration in others.

### 1.2 Phase 24-H-2 — Edit → Save → Run → Output Delta Proof

* **Phase 24-H-2:** Edit → Save → Run → Output Delta
  Proof. The output delta proof is the evidence that
  editing a scenario input changes the corresponding
  scenario output. Tests-only + docs + report.

### 1.3 Phase 24-H-3 — Generic Scenario Loop + Compare

* **Phase 24-H-3:** Generic Scenario Loop + Compare.
  The compare is the internal functionality that
  surfaces side-by-side scenario results. Tests-only
  + docs + report.

### 1.4 Phase 24-H-4 — Generic Export / Download Pack With Exploratory Banner

* **Phase 24-H-4:** Generic Export / Download Pack.
  The export / download pack is the internal artifact
  generation for Generic scenarios. The exploratory
  banner is required. Tests-only + docs + report.

### 1.5 Phase 24-H Closure Review

* **Phase 24-H closure:** Generic Modelling Loop
  Testability Review (PR #582). The closure review is
  the testability review for the Phase 24-H arc.

### 1.6 Phase 25B-1 — Generic Defaults Prefill Button

* **Phase 25B-1 (PR #583):** Generic Defaults Prefill
  Button. The prefill button seeds the canonical
  reference project's defaults into a new Generic
  project. The prefill button is internal
  functionality; the defaults are illustrative until
  validated by reference models.

### 1.7 Phase 25B-2 — 3-Way / 4-Way Generic Scenario Compare

* **Phase 25B-2 (PR #584):** 3-Way / 4-Way Generic
  Scenario Compare. The 3-way / 4-way compare is the
  internal functionality that surfaces side-by-side
  scenario results across three or four scenarios.

### 1.8 Phase 25B-2.1 — Multi-Compare Picker

* **Phase 25B-2.1 (PR #585):** Multi-Compare Picker.
  The picker is the UI entry point for the multi-
  compare flow. UI / navigation only.

### 1.9 Phase 25B-3 — Runtime "What Changed" Delta Indicator

* **Phase 25B-3 (PR #586, MERGED on main as
  `8042d0e8aadef7be05d97ccfde9f73ec86a954e5`):**
  Runtime "What Changed" Delta Indicator (UI + minimal
  metadata-persistence rotation).
  * Adds the Runtime "What Changed" delta indicator.
  * Computes deltas across 10 KPIs: Project IRR,
    Equity IRR, Avg DSCR, Min DSCR, Revenue, OPEX,
    EBITDA, CAPEX, Distributions, Senior Debt.
  * Uses `replay_metadata` optional keys:
    `previous_run_summary`, `second_last_run_summary`,
    `previous_run_at`.
  * No schema migration. No new columns. No data
    backfill.
  * `update_scenario_last_run_summary` has minimal
    rotation behavior.
  * Factory project run summary output is byte-
    identical to the pre-Phase-25B-3 path.
  * For `generic_solar` / `generic_wind`, an
    EXPLORATORY banner is required.
  * Panel is gated on `card.is_user_project` —
    factory projects (TUHO/Oborovo) do not render the
    panel.
  * No model formula changes. No tax / debt /
    depreciation / IDC changes. No construction / C10
    / R-PAR promotion. No senior IDC changes. No new
    financial formulas. No Tailwind / Alpine / inline
    `<script>` in partials. rc1 flow untouched.

## 2. What improved

* The Generic Modelling Loop is implemented end-to-end:
  generic project creation, generic defaults prefill,
  edit → save → run, output delta proof, scenario
  compare, 3-way / 4-way compare, multi-compare picker,
  export / download pack, and the Runtime "What
  Changed" delta indicator.
* The persistence rotation in
  `update_scenario_last_run_summary` is minimal and
  scoped. Other `replay_metadata` keys are preserved
  across writes. Corrupted or missing `replay_metadata`
  is tolerated.
* The factory project safety is preserved. Factory
  project run summary output is byte-identical to the
  pre-Phase-25B-3 path.
* The exploratory banner is required for `generic_solar`
  / `generic_wind`. The banner makes it clear that the
  deltas are not Excel-parity validated.
* The 10 KPI delta list is documented and tested. The
  delta computation is explanatory; it does not
  constitute investment advice or guaranteed returns.

## 3. What remains exploratory

* Generic Solar remains exploratory. The generic
  defaults for solar are illustrative until validated
  by reference models.
* Generic Wind remains exploratory. The generic
  defaults for wind are illustrative until validated by
  reference models.
* The exploratory banner is required for the
  `generic_solar` / `generic_wind` deltas. The banner
  must remain in place until the generic templates are
  validated.
* The scenario compare is internal functionality, not
  model validation. The compare does not validate the
  engine.
* The export / download pack is internal artifact
  generation, not bankability. The export / download
  pack does not constitute a bankable artifact.

## 4. What remains unvalidated

* Generic Solar output is not Excel-parity validated
  against a reference solar model.
* Generic Wind output is not Excel-parity validated
  against a reference wind model.
* Generic Solar / Wind defaults are not market-validated
  assumptions.
* The "What Changed" deltas are explanatory; they are
  not guaranteed accuracy claims.
* The 3-way / 4-way compare is internal functionality;
  it does not constitute model validation.
* The multi-compare picker is UI / navigation only; it
  does not constitute model validation.
* The export / download pack is internal artifact
  generation; it does not constitute bankability.
* No external validation has occurred.
* No paid pilot has been authorized.
* No customer reference has been made.

## 5. What evidence exists

* Phase 24-H, 24-H-2, 24-H-3, 24-H-4 tests-only + docs
  + report on main.
* Phase 24-H closure testability review (PR #582) on
  main.
* Phase 25B-1, 25B-2, 25B-2.1, 25B-3 PRs on main.
* Phase 25B-3 (PR #586): 84 new tests reported green in
  the PR body.
* Phase 25B-3 factory project safety: factory project
  run summary output is byte-identical to the pre-
  Phase-25B-3 path.
* Phase 25B-3 `replay_metadata` rotation: minimal
  rotation behavior with corrupted / missing metadata
  tolerance.
* Phase 25B-3 panel: read-only UI panel; no input
  mutation; no DB, no I/O, no time, no random in the
  helper module.
* Phase 25B-3 user-project gating: panel is gated on
  `card.is_user_project`. Factory projects do not
  render the panel.
* Phase 25B-3 exploratory banner: required for
  `generic_solar` / `generic_wind`.
* Phase 25B-3 rc1 flow: untouched.
* B1, B11, B19, B22, B35, B36, B37, B38, B39, B40 B-
  track governance artifacts on main (precedent for the
  no-go claim and commercial guardrail).

## 6. What evidence is still missing

* External reviewer run on the Generic Modelling /
  Scenario Loop arc.
* External reviewer run on the Phase 25B-3 "What
  Changed" delta indicator.
* Reference solar model for the Generic Solar output
  validation.
* Reference wind model for the Generic Wind output
  validation.
* Market validation for the Generic Solar / Wind
  defaults.
* Controlled pilot run with real users on the Generic
  Solar / Wind scenario workflow.
* User visual review of the "What Changed" delta panel
  (post-merge).
* User visual review of the 3-way / 4-way compare
  panel.
* User visual review of the multi-compare picker.
* User visual review of the export / download pack.

## 7. Effect on controlled pilot readiness

The Generic Modelling / Scenario Loop arc is
**partially ready** for the controlled pilot:

* The Generic Modelling Loop is implemented end-to-end.
* The "What Changed" delta indicator is implemented
  (read-only UI panel).
* The 3-way / 4-way compare is implemented.
* The multi-compare picker is implemented.
* The export / download pack is implemented with the
  exploratory banner.
* The factory project safety is preserved.

The Generic Modelling / Scenario Loop arc is **not
ready** for the controlled pilot because:

* Generic Solar / Wind remain exploratory and
  unvalidated.
* The controlled pilot would require the user visual
  review of the "What Changed" panel, the compare
  panel, the multi-compare picker, and the export /
  download pack.
* The controlled pilot would require the Generic Solar
  / Wind defaults to be reviewed by a designated
  reviewer.

The controlled pilot is **internal only**, not paid
pilot, not external.

## 8. Effect on paid pilot gate

**Unchanged.** The Generic Modelling / Scenario Loop
arc does not authorize the paid pilot. The paid pilot
remains not authorized.

The Generic Modelling / Scenario Loop arc does not
relax the paid pilot gate. The paid pilot gate is
governed by the B25 / B33 / B35 stop / go checklists
and the B45 controlled pilot runbook.

## 9. Effect on external review

**Unchanged.** No external validation has occurred.
The Generic Modelling / Scenario Loop arc is internal
functionality; it is not external validation.

The external review remains a separate workstream.
The external review is referenced only as review
evidence, not as external validation or certification.

## 10. Effect on commercial / demo claims

**Partially improved but not promoted.** The Generic
Modelling / Scenario Loop arc enables new internal
demo scenarios (e.g., "the scenario compare is now
available", "the export / download pack is now
available"). The arc does not promote any commercial
claim.

The following claims remain **prohibited**:

* Excel parity for Generic Solar / Wind.
* Bankability.
* Lender reliance.
* Audit / certification / regulatory approval.
* Production readiness.
* Enterprise SaaS readiness.
* Investment advice.
* Guaranteed returns.
* Customer reference.
* Paid pilot authorization.
* External validation.

The B44 workstream (Generic Solar / Wind Exploratory
Boundary & Demo Guardrail) provides the detailed
allowed / prohibited demo statements for the Generic
Modelling / Scenario Loop arc.

## 11. What B41 explicitly does not claim

* B41 does not claim that Generic Solar / Wind are
  validated. Generic Solar / Wind remain exploratory
  and unvalidated.
* B41 does not claim that the scenario compare
  validates the model. The scenario compare is
  internal functionality, not model validation.
* B41 does not claim that the export / download pack
  equals bankability. The export / download pack is
  internal artifact generation, not bankability.
* B41 does not claim that the "What Changed" deltas
  are guaranteed accuracy claims. The deltas are
  explanatory; they are not investment advice or
  guaranteed returns.
* B41 does not claim that the paid pilot is authorized.
  The paid pilot is not authorized.
* B41 does not claim that external validation has
  occurred. External validation has not occurred.
* B41 does not claim a customer reference.
* B41 does not claim production readiness or
  enterprise SaaS readiness.
* B41 does not claim that the Generic Modelling /
  Scenario Loop arc is complete. The arc is partially
  ready for the controlled pilot; the controlled
  pilot is not yet authorized.

## 12. Cross-references

* `reports/governance/post_phase25b_generic_modelling_governance_refresh.json`
  (B41, machine-readable)
* `docs/validation/generic_scenario_loop_evidence_matrix.md`
  (B42)
* `docs/governance/what_changed_delta_indicator_governance_review.md`
  (B43)
* `docs/commercial/generic_solar_wind_demo_guardrail_refresh.md`
  (B44)
* `docs/pilot/controlled_generic_scenario_pilot_runbook.md`
  (B45)
* `docs/validation/scenario_compare_export_evidence_register.md`
  (B46)
* `docs/governance/post25b_readiness_delta_refresh_cadence.md`
  (B47)
* `docs/governance/post_phase56_ui_governance_refresh.md` (B35)
* `docs/ui/phase57a_line_item_grid_visual_review.md` (B36)
* `docs/validation/ui_regression_evidence_matrix.md` (B37)
* `docs/commercial/ui demo_guardrail_refresh.md` (B38)
* `docs/pilot/controlled_pilot_ux_runbook.md` (B39)
* `docs/governance/ui3_line_item_grid_migration_governance_plan.md`
  (B40)
* `docs/external_review/no_go_claims.md` (B1)
* `docs/commercial/no_go_claims_commercial_guardrail.md` (B11)
* `docs/governance/phase53_stop_go_checklist.md` (B33)
* `docs/pilot/controlled_pilot_runbook.md` (B18)
* `docs/pilot/pilot_issue_log_process.md` (B20)
* `docs/commercial/demo_qa_guardrail.md` (B22)
* `docs/external_review/reviewer_question_bank.md` (B23)

---

*End of post-Phase 24H / 25B Generic Modelling
governance refresh.*
