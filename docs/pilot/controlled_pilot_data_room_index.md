# Controlled Pilot Data Room Index

This file is the **controlled pilot data room index**.
It is the B-track governance wrapper for the data
room of the controlled internal pilot after the UI
governance arc (B35-B40, PR #489) and the Generic
Modelling Loop arc (B41-B47, PR #588).

> **Internal controlled pilot only. No real customer
> data unless approved separately. No production
> deployment. No paid pilot. No customer reference.
> No external reliance.**

---

## 1. Data room folders

The data room is organized into the following
folders / categories:

* Product scope.
* Model evidence.
* Scenario workflow evidence.
* Generic modelling evidence.
* UI evidence.
* CAPEX / LineItemGrid evidence.
* Persistence / save-load evidence.
* Export / download evidence.
* What Changed evidence.
* No-go claims.
* Known limitations.
* Pilot runbooks.
* Issue logs.
* Reviewer instructions.
* Sign-off records.

## 2. Per-folder data room index

### 2.1 Product scope

* **item_id:** DR-01.
* **folder:** product_scope.
* **document_title:** Current product scope snapshot
  after UI + Generic Loop.
* **source_path_or_placeholder:** B48
  (`docs/governance/current_product_scope_snapshot_after_ui_generic_loop.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per B47 cadence plan.
* **next_update_trigger:** Per B47 cadence plan.

* **item_id:** DR-02.
* **folder:** product_scope.
* **document_title:** Post-Phase54-56 UI governance
  refresh.
* **source_path_or_placeholder:** B35
  (`docs/governance/post_phase56_ui_governance_refresh.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per B47 cadence plan.
* **next_update_trigger:** Per B47 cadence plan.

* **item_id:** DR-03.
* **folder:** product_scope.
* **document_title:** Post-Phase24H/25B Generic
  Modelling governance refresh.
* **source_path_or_placeholder:** B41
  (`docs/governance/post_phase25b_generic_modelling_governance_refresh.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per B47 cadence plan.
* **next_update_trigger:** Per B47 cadence plan.

### 2.2 Model evidence

* **item_id:** DR-04.
* **folder:** model_evidence.
* **document_title:** Validation evidence matrix.
* **source_path_or_placeholder:** B3
  (`docs/validation/validation_evidence_matrix.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per B26 must-pin evidence
  tracker.
* **next_update_trigger:** Per B26 must-pin evidence
  tracker.

* **item_id:** DR-05.
* **folder:** model_evidence.
* **document_title:** Model confidence heatmap.
* **source_path_or_placeholder:** B12
  (`docs/validation/model_confidence_heatmap.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per B26 must-pin evidence
  tracker.
* **next_update_trigger:** Per B26 must-pin evidence
  tracker.

* **item_id:** DR-06.
* **folder:** model_evidence.
* **document_title:** Parity-core lock (CI).
* **source_path_or_placeholder:** Per Phase 51F
  Parity Guardrails CI check.
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent A (code) + Agent B (governance).
* **status:** available. CI green.
* **update_frequency:** Per PR / Phase.
* **next_update_trigger:** Per PR / Phase.

### 2.3 Scenario workflow evidence

* **item_id:** DR-07.
* **folder:** scenario_workflow_evidence.
* **document_title:** Generic Scenario Loop evidence
  matrix.
* **source_path_or_placeholder:** B42
  (`docs/validation/generic_scenario_loop_evidence_matrix.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available (empty at creation; no
  coverage invented).
* **update_frequency:** Per B47 cadence plan.
* **next_update_trigger:** Per B47 cadence plan.

* **item_id:** DR-08.
* **folder:** scenario_workflow_evidence.
* **document_title:** Controlled Generic Scenario
  pilot runbook.
* **source_path_or_placeholder:** B45
  (`docs/pilot/controlled_generic_scenario_pilot_runbook.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per B47 cadence plan.
* **next_update_trigger:** Per B47 cadence plan.

### 2.4 Generic modelling evidence

* **item_id:** DR-09.
* **folder:** generic_modelling_evidence.
* **document_title:** Generic Solar / Wind
  exploratory boundary & demo guardrail.
* **source_path_or_placeholder:** B44
  (`docs/commercial/generic_solar_wind_demo_guardrail_refresh.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per B47 cadence plan.
* **next_update_trigger:** Per B47 cadence plan.

* **item_id:** DR-10.
* **folder:** generic_modelling_evidence.
* **document_title:** Reference-model validation
  evidence (placeholder).
* **source_path_or_placeholder:** TBD.
* **required_before_internal_pilot:** no (not yet
  available).
* **required_before_paid_pilot:** yes.
* **owner:** User (reference-model validation).
* **status:** not yet available.
* **update_frequency:** Per B47 cadence plan.
* **next_update_trigger:** After first real Generic
  Solar / Wind reference model.

### 2.5 UI evidence

* **item_id:** DR-11.
* **folder:** ui_evidence.
* **document_title:** UI regression evidence matrix.
* **source_path_or_placeholder:** B37
  (`docs/validation/ui_regression_evidence_matrix.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available (empty at creation; no
  coverage invented).
* **update_frequency:** Per B47 cadence plan.
* **next_update_trigger:** Per B47 cadence plan.

* **item_id:** DR-12.
* **folder:** ui_evidence.
* **document_title:** UI no-go claim / demo guardrail
  refresh.
* **source_path_or_placeholder:** B38
  (`docs/commercial/ui demo_guardrail_refresh.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per B47 cadence plan.
* **next_update_trigger:** Per B47 cadence plan.

* **item_id:** DR-13.
* **folder:** ui_evidence.
* **document_title:** Phase 57A LineItemGrid visual
  review pack.
* **source_path_or_placeholder:** B36
  (`docs/ui/phase57a_line_item_grid_visual_review.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance) + User (visual
  review).
* **status:** available (empty protocol; visual
  review not yet performed).
* **update_frequency:** Per B47 cadence plan.
* **next_update_trigger:** After user visual review
  of the LineItemGrid CAPEX summary.

* **item_id:** DR-14.
* **folder:** ui_evidence.
* **document_title:** Controlled pilot UX runbook
  (post-Phase 54-56).
* **source_path_or_placeholder:** B39
  (`docs/pilot/controlled_pilot_ux_runbook.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per B47 cadence plan.
* **next_update_trigger:** Per B47 cadence plan.

### 2.6 CAPEX / LineItemGrid evidence

* **item_id:** DR-15.
* **folder:** capex_lineitemgrid_evidence.
* **document_title:** UI-3 LineItemGrid migration
  governance plan.
* **source_path_or_placeholder:** B40
  (`docs/governance/ui3_line_item_grid_migration_governance_plan.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per B47 cadence plan.
* **next_update_trigger:** Per B47 cadence plan.

### 2.7 Persistence / save-load evidence

* **item_id:** DR-16.
* **folder:** persistence_save_load_evidence.
* **document_title:** Persistence rotation in
  `update_scenario_last_run_summary` (PR #586).
* **source_path_or_placeholder:** PR #586 body.
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent A (code) + Agent B (governance).
* **status:** available.
* **update_frequency:** Per PR / Phase.
* **next_update_trigger:** Per PR / Phase.

* **item_id:** DR-17.
* **folder:** persistence_save_load_evidence.
* **document_title:** Persistence and records
  guardrails CI.
* **source_path_or_placeholder:** Per PR CI check.
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent A (code) + Agent B (governance).
* **status:** available. CI green.
* **update_frequency:** Per PR / Phase.
* **next_update_trigger:** Per PR / Phase.

### 2.8 Export / download evidence

* **item_id:** DR-18.
* **folder:** export_download_evidence.
* **document_title:** Scenario compare / export /
  download evidence register.
* **source_path_or_placeholder:** B46
  (`docs/validation/scenario_compare_export_evidence_register.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per B47 cadence plan.
* **next_update_trigger:** Per B47 cadence plan.

* **item_id:** DR-19.
* **folder:** export_download_evidence.
* **document_title:** Export / download artifacts
  (placeholder).
* **source_path_or_placeholder:** TBD.
* **required_before_internal_pilot:** no (collected
  during the controlled pilot, per B45 task T9).
* **required_before_paid_pilot:** yes.
* **owner:** User (visual review) + Agent B
  (governance).
* **status:** not yet available.
* **update_frequency:** Per B45 controlled pilot.
* **next_update_trigger:** After the first
  controlled pilot run.

### 2.9 What Changed evidence

* **item_id:** DR-20.
* **folder:** what_changed_evidence.
* **document_title:** What Changed Delta Indicator
  governance review pack.
* **source_path_or_placeholder:** B43
  (`docs/governance/what_changed_delta_indicator_governance_review.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per B47 cadence plan.
* **next_update_trigger:** Per B47 cadence plan.

### 2.10 No-go claims

* **item_id:** DR-21.
* **folder:** no_go_claims.
* **document_title:** No-go claim list.
* **source_path_or_placeholder:** B1
  (`docs/external_review/no_go_claims.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per PR / Phase.
* **next_update_trigger:** Per PR / Phase.

* **item_id:** DR-22.
* **folder:** no_go_claims.
* **document_title:** Commercial / demo guardrail.
* **source_path_or_placeholder:** B11
  (`docs/commercial/no_go_claims_commercial_guardrail.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per PR / Phase.
* **next_update_trigger:** Per PR / Phase.

* **item_id:** DR-23.
* **folder:** no_go_claims.
* **document_title:** Known limitations / no-go
  claims consolidation.
* **source_path_or_placeholder:** B51
  (`docs/governance/known_limitations_no_go_claims_consolidation.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per B47 cadence plan.
* **next_update_trigger:** Per B47 cadence plan.

### 2.11 Known limitations

* **item_id:** DR-24.
* **folder:** known_limitations.
* **document_title:** Known limitations / no-go
  claims consolidation.
* **source_path_or_placeholder:** B51
  (`docs/governance/known_limitations_no_go_claims_consolidation.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per B47 cadence plan.
* **next_update_trigger:** Per B47 cadence plan.

### 2.12 Pilot runbooks

* **item_id:** DR-25.
* **folder:** pilot_runbooks.
* **document_title:** Controlled pilot runbook.
* **source_path_or_placeholder:** B18
  (`docs/pilot/controlled_pilot_runbook.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per B47 cadence plan.
* **next_update_trigger:** Per B47 cadence plan.

* **item_id:** DR-26.
* **folder:** pilot_runbooks.
* **document_title:** Controlled pilot UX runbook
  (post-Phase 54-56).
* **source_path_or_placeholder:** B39
  (`docs/pilot/controlled_pilot_ux_runbook.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per B47 cadence plan.
* **next_update_trigger:** Per B47 cadence plan.

* **item_id:** DR-27.
* **folder:** pilot_runbooks.
* **document_title:** Controlled Generic Scenario
  pilot runbook.
* **source_path_or_placeholder:** B45
  (`docs/pilot/controlled_generic_scenario_pilot_runbook.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per B47 cadence plan.
* **next_update_trigger:** Per B47 cadence plan.

### 2.13 Issue logs

* **item_id:** DR-28.
* **folder:** issue_logs.
* **document_title:** Pilot issue log process.
* **source_path_or_placeholder:** B20
  (`docs/pilot/pilot_issue_log_process.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per controlled pilot run.
* **next_update_trigger:** After each controlled
  pilot run.

### 2.14 Reviewer instructions

* **item_id:** DR-29.
* **folder:** reviewer_instructions.
* **document_title:** External review package
  index.
* **source_path_or_placeholder:** B1
  (`docs/external_review/external_review_package_index.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per B47 cadence plan.
* **next_update_trigger:** Per B47 cadence plan.

* **item_id:** DR-30.
* **folder:** reviewer_instructions.
* **document_title:** Reviewer question bank.
* **source_path_or_placeholder:** B23
  (`docs/external_review/reviewer_question_bank.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per B47 cadence plan.
* **next_update_trigger:** Per B47 cadence plan.

* **item_id:** DR-31.
* **folder:** reviewer_instructions.
* **document_title:** External reviewer evidence
  index refresh.
* **source_path_or_placeholder:** B50
  (`docs/review/external_reviewer_evidence_index_refresh.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per B47 cadence plan.
* **next_update_trigger:** Per B47 cadence plan.

### 2.15 Sign-off records

* **item_id:** DR-32.
* **folder:** sign_off_records.
* **document_title:** Pilot user acknowledgement.
* **source_path_or_placeholder:** B21
  (`docs/pilot/pilot_user_acknowledgement.md`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per controlled pilot run.
* **next_update_trigger:** After each controlled
  pilot run.

* **item_id:** DR-33.
* **folder:** sign_off_records.
* **document_title:** Q&A matrix.
* **source_path_or_placeholder:** B22
  (`docs/commercial/qa_claims_matrix.json`).
* **required_before_internal_pilot:** yes.
* **required_before_paid_pilot:** yes.
* **owner:** Agent B (governance).
* **status:** available.
* **update_frequency:** Per B47 cadence plan.
* **next_update_trigger:** Per B47 cadence plan.

## 3. Internal pilot readiness summary

The internal pilot is **partially ready** based on
the data room:

* **Available:** DR-01 through DR-31 (most items).
* **Not yet available:** DR-10 (reference-model
  validation), DR-19 (export / download artifacts,
  collected during the controlled pilot).
* **Partially ready:** DR-13 (Phase 57A LineItemGrid
  visual review pack, empty protocol).

## 4. Paid pilot readiness summary

The paid pilot is **not ready** based on the data
room:

* **Missing:** DR-10 (reference-model validation) is
  a hard requirement for paid pilot.
* **Missing:** External reviewer feedback.
* **Missing:** Paid pilot gate review per B25 / B33 /
  B35 stop / go checklists.

## 5. What B52 is not

* B52 is not a code change. Agent B does not
  implement code.
* B52 is not external validation.
* B52 is not a paid pilot authorization.
* B52 is not a customer reference.
* B52 is not a production readiness claim.
* B52 is not an enterprise SaaS readiness claim.
* B52 is not a financial model validation.
* B52 is not a substitute for the user's pilot
  decisions or the user's marketing decisions.

## 6. Cross-references

* `reports/pilot/controlled_pilot_data_room_index.json`
  (B52, machine-readable)
* `docs/governance/current_product_scope_snapshot_after_ui_generic_loop.md`
  (B48)
* `docs/pilot/internal_pilot_readiness_matrix.md` (B49)
* `docs/review/external_reviewer_evidence_index_refresh.md`
  (B50)
* `docs/governance/known_limitations_no_go_claims_consolidation.md`
  (B51)
* `docs/governance/next_validation_roadmap_after_generic_loop.md`
  (B53)
* `docs/pilot/controlled_pilot_runbook.md` (B18)
* `docs/pilot/controlled_pilot_ux_runbook.md` (B39)
* `docs/pilot/controlled_generic_scenario_pilot_runbook.md`
  (B45)

---

*End of controlled pilot data room index.*
