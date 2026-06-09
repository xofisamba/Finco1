# Next Validation Roadmap after Generic Loop

This file is the **next validation roadmap after
Generic Loop**. It is the B-track governance wrapper
for the validation roadmap after the Generic
Modelling / Scenario Loop arc.

> **Validation roadmap is not approval. Paid pilot
> requires separate gate review. External review
> requires external reviewer feedback. Generic
> output parity must be proven against reference
> models before any parity claim.**

---

## 1. Roadmap tracks

The roadmap covers the following tracks:

* Generic Solar reference model validation.
* Generic Wind reference model validation.
* CAPEX 2.0 / editable workspace validation.
* Scenario compare validation.
* Export / download validation.
* What Changed validation.
* Persistence metadata validation.
* UI / UX visual validation.
* External reviewer preparation.
* Controlled pilot evidence collection.
* Paid pilot gate review.

## 2. Per-track roadmap

### 2.1 Generic Solar reference model validation

* **roadmap_id:** RM-01.
* **objective:** Validate Generic Solar output
  against a real reference solar model.
* **current_status:** not_started.
* **blocker:** No reference solar model is
  available.
* **required_evidence:** reference solar model;
  reference solar output (IRR, EBITDA, DSCR, etc.);
  comparison report (Generic Solar vs reference
  solar).
* **recommended_next_PR_or_phase:** Phase 26-A
  (Reference Solar Model Onboarding) — TBD.
* **owner:** User (reference-model validation) +
  Agent A (implementation) + Agent B (governance).
* **priority:** high.
* **dependency:** reference solar model must be
  available.
* **success_criteria:** Generic Solar output is
  Excel-parity validated against the reference solar
  model.
* **hard_stop_condition:** Reference solar model
  unavailable; comparison report indicates non-
  trivial delta.

### 2.2 Generic Wind reference model validation

* **roadmap_id:** RM-02.
* **objective:** Validate Generic Wind output
  against a real reference wind model.
* **current_status:** not_started.
* **blocker:** No reference wind model is
  available.
* **required_evidence:** reference wind model;
  reference wind output (IRR, EBITDA, DSCR, etc.);
  comparison report (Generic Wind vs reference
  wind).
* **recommended_next_PR_or_phase:** Phase 26-B
  (Reference Wind Model Onboarding) — TBD.
* **owner:** User (reference-model validation) +
  Agent A (implementation) + Agent B (governance).
* **priority:** high.
* **dependency:** reference wind model must be
  available.
* **success_criteria:** Generic Wind output is
  Excel-parity validated against the reference wind
  model.
* **hard_stop_condition:** Reference wind model
  unavailable; comparison report indicates non-
  trivial delta.

### 2.3 CAPEX 2.0 / editable workspace validation

* **roadmap_id:** RM-03.
* **objective:** Validate the CAPEX 2.0 editable
  workspace (the editable CAPEX sub-lines) against
  the existing CAPEX model.
* **current_status:** partially_done.
* **blocker:** None.
* **required_evidence:** Per-PR validation evidence
  (Phase 57A-9B, 57A-9C, 57A-9D, 57A-9E, 57A-10, and
  later phases).
* **recommended_next_PR_or_phase:** Phase 57A-9C
  (Save/Load wiring), 57A-9D (Run integration),
  57A-9E (Excel export).
* **owner:** Agent A (implementation) + Agent B
  (governance).
* **priority:** medium.
* **dependency:** None.
* **success_criteria:** CAPEX sub-lines are saved,
  loaded, run, and exported correctly.
* **hard_stop_condition:** CAPEX sub-line delta
  detected for TUHO or Oborovo.

### 2.4 Scenario compare validation

* **roadmap_id:** RM-04.
* **objective:** Validate the scenario compare
  (2-way, 3-way, 4-way) internal functionality.
* **current_status:** partially_done.
* **blocker:** None.
* **required_evidence:** Per-PR validation evidence
  (Phase 24-H-3, 25B-2, 25B-2.1).
* **recommended_next_PR_or_phase:** User visual
  review of the compare panel; controlled pilot run
  per B45.
* **owner:** Agent A (implementation) + Agent B
  (governance) + User (visual review).
* **priority:** medium.
* **dependency:** None.
* **success_criteria:** Compare panel renders
  correctly; 3-way / 4-way compare renders
  correctly; multi-compare picker integrates with
  the compare panel.
* **hard_stop_condition:** Compare panel broken;
  multi-compare picker broken.

### 2.5 Export / download validation

* **roadmap_id:** RM-05.
* **objective:** Validate the export / download
  pack (Generic scenarios).
* **current_status:** partially_done.
* **blocker:** None.
* **required_evidence:** Per-PR validation evidence
  (Phase 24-H-4); export artifact evidence (collected
  during the controlled pilot, per B45 task T9).
* **recommended_next_PR_or_phase:** User visual
  review of the export / download artifacts;
  controlled pilot run per B45.
* **owner:** Agent A (implementation) + Agent B
  (governance) + User (visual review).
* **priority:** medium.
* **dependency:** None.
* **success_criteria:** Export artifacts are
  generated correctly; the exploratory banner is
  visible for Generic Solar / Wind exports.
* **hard_stop_condition:** Export artifacts broken;
  exploratory banner missing for Generic Solar /
  Wind exports.

### 2.6 What Changed validation

* **roadmap_id:** RM-06.
* **objective:** Validate the What Changed Delta
  Indicator (Phase 25B-3 / PR #586).
* **current_status:** partially_done.
* **blocker:** None.
* **required_evidence:** Per-PR validation evidence
  (Phase 25B-3 / PR #586, 84 new tests reported
  green in the PR body).
* **recommended_next_PR_or_phase:** User visual
  review of the What Changed panel; controlled
  pilot run per B45.
* **owner:** Agent A (implementation) + Agent B
  (governance) + User (visual review).
* **priority:** medium.
* **dependency:** None.
* **success_criteria:** What Changed panel renders
  correctly; the exploratory banner is visible for
  Generic Solar / Wind; the panel is gated on
  `card.is_user_project`; factory projects do not
  render the panel.
* **hard_stop_condition:** What Changed panel
  broken; exploratory banner missing for Generic
  Solar / Wind; panel rendering for factory
  projects.

### 2.7 Persistence metadata validation

* **roadmap_id:** RM-07.
* **objective:** Validate the persistence metadata
  rotation (Phase 25B-3 / PR #586).
* **current_status:** partially_done.
* **blocker:** None.
* **required_evidence:** Per-PR validation evidence
  (Phase 25B-3 / PR #586); persistence and records
  guardrails CI green.
* **recommended_next_PR_or_phase:** Long-term
  persistence reliability evidence (multi-month
  save-load cycles).
* **owner:** Agent A (implementation) + Agent B
  (governance).
* **priority:** medium.
* **dependency:** None.
* **success_criteria:** Persistence rotation is
  correct for runs 1, 2, 3, 4+; corrupted /
  missing `replay_metadata` is tolerated; other
  `replay_metadata` keys are preserved across
  writes; factory project run summary output is
  byte-identical to pre-Phase-25B-3 path.
* **hard_stop_condition:** Factory project run
  summary output is NOT byte-identical; persistence
  rotation drift detected.

### 2.8 UI / UX visual validation

* **roadmap_id:** RM-08.
* **objective:** Validate the UI / UX (post-Phase
  54-56 + post-Phase 25B-3) via user visual review
  and controlled pilot runs.
* **current_status:** partially_done.
* **blocker:** None.
* **required_evidence:** User visual review of the
  UI; controlled pilot runs per B18, B39, B45.
* **recommended_next_PR_or_phase:** Controlled
  pilot runs per B45 task list (T1-T12).
* **owner:** Agent A (implementation) + Agent B
  (governance) + User (visual review).
* **priority:** medium.
* **dependency:** None.
* **success_criteria:** UI is clear and
  understandable; UX is consistent; no-regression.
* **hard_stop_condition:** High-severity UX issue
  that blocks one or more tasks.

### 2.9 External reviewer preparation

* **roadmap_id:** RM-09.
* **objective:** Prepare the external reviewer
  evidence index and onboard an external reviewer.
* **current_status:** not_started.
* **blocker:** No external reviewer is onboarded.
* **required_evidence:** B50 external reviewer
  evidence index; B23 reviewer question bank;
  external reviewer feedback.
* **recommended_next_PR_or_phase:** Identify and
  onboard an external reviewer; collect external
  reviewer feedback.
* **owner:** User (external review) + Agent B
  (governance).
* **priority:** high.
* **dependency:** External reviewer must be
  available.
* **success_criteria:** External reviewer feedback
  is collected; external reviewer sign-off is
  received.
* **hard_stop_condition:** External reviewer
  unavailable; external reviewer feedback not
  collected.

### 2.10 Controlled pilot evidence collection

* **roadmap_id:** RM-10.
* **objective:** Collect controlled pilot evidence
  (per B45, B18, B39).
* **current_status:** not_started.
* **blocker:** No controlled pilot has been
  performed.
* **required_evidence:** B18 / B39 / B45 controlled
  pilot runbooks; B52 controlled pilot data room
  index; controlled pilot run results.
* **recommended_next_PR_or_phase:** First
  controlled pilot run per B45.
* **owner:** User (controlled pilot) + Agent B
  (governance).
* **priority:** medium.
* **dependency:** Controlled pilot must be
  authorized by the user.
* **success_criteria:** Controlled pilot run is
  complete; controlled pilot evidence is collected.
* **hard_stop_condition:** High-severity UX issue;
  critical data integrity issue; financial output
  drift on TUHO or Oborovo.

### 2.11 Paid pilot gate review

* **roadmap_id:** RM-11.
* **objective:** Review the paid pilot gate per the
  B25 / B33 / B35 stop / go checklists.
* **current_status:** not_started.
* **blocker:** Paid pilot gate review is gated on
  the completion of RM-01 / RM-02 / RM-09 / RM-10.
* **required_evidence:** Reference-model validation
  (RM-01, RM-02); external reviewer feedback
  (RM-09); controlled pilot evidence (RM-10); B25 /
  B33 / B35 stop / go checklists.
* **recommended_next_PR_or_phase:** Per the B25 /
  B33 / B35 stop / go checklists.
* **owner:** User (paid pilot gate review) + Agent B
  (governance).
* **priority:** high.
* **dependency:** RM-01, RM-02, RM-09, RM-10 must
  be complete.
* **success_criteria:** Paid pilot gate review
  passes; paid pilot is authorized by the user.
* **hard_stop_condition:** Any hard-stop condition
  in the B25 / B33 / B35 stop / go checklists;
  reference-model validation fails; external
  reviewer feedback negative; controlled pilot
  evidence missing.

## 3. What B53 is not

* B53 is not a code change. Agent B does not
  implement code.
* B53 is not external validation.
* B53 is not a paid pilot authorization.
* B53 is not a customer reference.
* B53 is not a production readiness claim.
* B53 is not an enterprise SaaS readiness claim.
* B53 is not a financial model validation.
* B53 is not a substitute for the user's validation
  decisions or the user's marketing decisions.

## 4. Cross-references

* `reports/governance/next_validation_roadmap_after_generic_loop.json`
  (B53, machine-readable)
* `docs/governance/current_product_scope_snapshot_after_ui_generic_loop.md`
  (B48)
* `docs/pilot/internal_pilot_readiness_matrix.md` (B49)
* `docs/review/external_reviewer_evidence_index_refresh.md`
  (B50)
* `docs/governance/known_limitations_no_go_claims_consolidation.md`
  (B51)
* `docs/pilot/controlled_pilot_data_room_index.md` (B52)
* `docs/governance/post_phase25b_generic_modelling_governance_refresh.md`
  (B41)
* `docs/governance/post25b_readiness_delta_refresh_cadence.md`
  (B47)
* `docs/governance/phase53_stop_go_checklist.md` (B33)

---

*End of next validation roadmap after Generic
Loop.*
