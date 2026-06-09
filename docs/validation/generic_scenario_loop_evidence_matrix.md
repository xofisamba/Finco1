# Generic Scenario Loop Evidence Matrix

This file is the **Generic Scenario Loop evidence
matrix**. It is the B-track governance wrapper for the
evidence of the Generic Modelling / Scenario Loop arc.

> **The matrix is empty at creation. Coverage values
> are recorded only when actual evidence is available.
> No coverage is invented.**
>
> **The matrix is internal evidence, not external
> validation. The matrix does not authorize paid pilot.
> The matrix does not constitute bankability. The
> matrix does not constitute model validation.**
>
> **Agent B does not implement code. Agent A implements
> code, tests, and the persistence rotation. Agent B
> records the matrix structure and the evidence as it
> is collected.**

---

## 1. Matrix scope

The matrix covers the following evidence areas:

* Generic project creation
* Generic defaults prefill
* Edit → save → run loop
* Output delta proof
* Scenario compare
* 3-way / 4-way compare
* Multi-compare picker
* Export / download pack
* Scenario lineage
* Scenario version history
* Runtime summary
* "What Changed" delta panel
* Exploratory banner
* Generic Solar
* Generic Wind
* TUHO / Oborovo factory safety
* No model-output drift
* No schema migration
* No formula change
* Persistence metadata rotation

## 2. Per-area matrix

### 2.1 Generic project creation

* **area_id:** GSLEM-01.
* **area_name:** Generic project creation.
* **source_phase_or_pr:** Phase 24-H.
* **evidence_type:** automated test + manual review.
* **current_coverage:** Tests-only + docs + report on
  main. The actual test files are not enumerated in
  B42 (B42 is evidence-collecting; coverage values are
  recorded when actual evidence is available).
* **tests_or_docs_available:** per Phase 24-H.
* **gap:** per-test enumeration not available at B42
  authoring.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** medium.
* **no_go_claim_risk:** low.
* **next_action:** A future B-track governance refresh
  may add per-test enumeration.

### 2.2 Generic defaults prefill

* **area_id:** GSLEM-02.
* **area_name:** Generic defaults prefill.
* **source_phase_or_pr:** Phase 25B-1 (PR #583).
* **evidence_type:** automated test + manual review.
* **current_coverage:** PR #583 merged on main. The
  prefill button is implemented. Generic defaults are
  illustrative until validated by reference models.
* **tests_or_docs_available:** per PR #583.
* **gap:** per-test enumeration not available at B42
  authoring. Market validation of defaults not
  available.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** medium.
* **no_go_claim_risk:** medium (defaults are
  illustrative; market validation would relax the
  risk).
* **next_action:** A future B-track governance refresh
  may add per-test enumeration and reference-model
  validation.

### 2.3 Edit → save → run loop

* **area_id:** GSLEM-03.
* **area_name:** Edit → save → run loop.
* **source_phase_or_pr:** Phase 24-H.
* **evidence_type:** automated test + manual review.
* **current_coverage:** Tests-only + docs + report on
  main. The edit → save → run loop is the foundation
  for the Generic Modelling arc.
* **tests_or_docs_available:** per Phase 24-H.
* **gap:** per-test enumeration not available at B42
  authoring.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** medium.
* **no_go_claim_risk:** low.
* **next_action:** A future B-track governance refresh
  may add per-test enumeration.

### 2.4 Output delta proof

* **area_id:** GSLEM-04.
* **area_name:** Output delta proof.
* **source_phase_or_pr:** Phase 24-H-2.
* **evidence_type:** automated test.
* **current_coverage:** Tests-only + docs + report on
  main. The output delta proof is the evidence that
  editing a scenario input changes the corresponding
  scenario output.
* **tests_or_docs_available:** per Phase 24-H-2.
* **gap:** per-test enumeration not available at B42
  authoring.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** medium.
* **no_go_claim_risk:** low.
* **next_action:** A future B-track governance refresh
  may add per-test enumeration.

### 2.5 Scenario compare

* **area_id:** GSLEM-05.
* **area_name:** Scenario compare.
* **source_phase_or_pr:** Phase 24-H-3.
* **evidence_type:** automated test + manual review.
* **current_coverage:** Tests-only + docs + report on
  main. The scenario compare is internal functionality.
  It does not validate the model.
* **tests_or_docs_available:** per Phase 24-H-3.
* **gap:** per-test enumeration not available at B42
  authoring.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** medium.
* **external_review_relevance:** medium.
* **no_go_claim_risk:** low.
* **next_action:** A future B-track governance refresh
  may add per-test enumeration.

### 2.6 3-way / 4-way compare

* **area_id:** GSLEM-06.
* **area_name:** 3-way / 4-way compare.
* **source_phase_or_pr:** Phase 25B-2 (PR #584).
* **evidence_type:** automated test + manual review.
* **current_coverage:** PR #584 merged on main. The
  3-way / 4-way compare is implemented. It is internal
  functionality, not model validation.
* **tests_or_docs_available:** per PR #584.
* **gap:** per-test enumeration not available at B42
  authoring. User visual review of the compare panel
  not yet performed.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** medium.
* **external_review_relevance:** medium.
* **no_go_claim_risk:** low.
* **next_action:** A future B-track governance refresh
  may add per-test enumeration and user visual review.

### 2.7 Multi-compare picker

* **area_id:** GSLEM-07.
* **area_name:** Multi-compare picker.
* **source_phase_or_pr:** Phase 25B-2.1 (PR #585).
* **evidence_type:** automated test + manual review.
* **current_coverage:** PR #585 merged on main. The
  multi-compare picker is implemented (UI / navigation
  only).
* **tests_or_docs_available:** per PR #585.
* **gap:** per-test enumeration not available at B42
  authoring. User visual review of the picker not yet
  performed.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** low.
* **external_review_relevance:** low.
* **no_go_claim_risk:** low.
* **next_action:** A future B-track governance refresh
  may add per-test enumeration and user visual review.

### 2.8 Export / download pack

* **area_id:** GSLEM-08.
* **area_name:** Export / download pack.
* **source_phase_or_pr:** Phase 24-H-4.
* **evidence_type:** automated test + manual review.
* **current_coverage:** Tests-only + docs + report on
  main. The export / download pack is internal artifact
  generation. The exploratory banner is required.
* **tests_or_docs_available:** per Phase 24-H-4.
* **gap:** per-test enumeration not available at B42
  authoring. User visual review of the export / download
  pack not yet performed.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** medium.
* **no_go_claim_risk:** medium (export / download
  evidence does not equal bankability).
* **next_action:** A future B-track governance refresh
  may add per-test enumeration and user visual review.

### 2.9 Scenario lineage

* **area_id:** GSLEM-09.
* **area_name:** Scenario lineage.
* **source_phase_or_pr:** Phase 24-H, 25B-3.
* **evidence_type:** automated test.
* **current_coverage:** Per Phase 25B-3 (PR #586) the
  scenario lineage is captured via
  `replay_metadata` optional keys
  (`previous_run_summary`,
  `second_last_run_summary`, `previous_run_at`).
* **tests_or_docs_available:** per PR #586.
* **gap:** per-test enumeration not available at B42
  authoring.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** medium.
* **no_go_claim_risk:** low.
* **next_action:** A future B-track governance refresh
  may add per-test enumeration.

### 2.10 Scenario version history

* **area_id:** GSLEM-10.
* **area_name:** Scenario version history.
* **source_phase_or_pr:** Phase 24-H, 25B-3.
* **evidence_type:** automated test + manual review.
* **current_coverage:** Per Phase 25B-3 the scenario
  version history panel is implemented. The "What
  Changed" delta indicator surfaces a compact
  comparison.
* **tests_or_docs_available:** per PR #586.
* **gap:** per-test enumeration not available at B42
  authoring. User visual review of the version history
  panel not yet performed.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** medium.
* **no_go_claim_risk:** low.
* **next_action:** A future B-track governance refresh
  may add per-test enumeration and user visual review.

### 2.11 Runtime summary

* **area_id:** GSLEM-11.
* **area_name:** Runtime summary.
* **source_phase_or_pr:** Phase 55E (predecessor).
* **evidence_type:** automated test + manual review.
* **current_coverage:** Per Phase 55E (PR #473) the
  runtime summary is wired into the index context. Per
  Phase 57-pre the index context-contract tests verify
  the context key is present.
* **tests_or_docs_available:** per PR #473, PR #486.
* **gap:** per-template visual review of the runtime
  summary display in the post-Phase-25B-3 context is
  not yet performed.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** high.
* **no_go_claim_risk:** low.
* **next_action:** A future B-track governance refresh
  may add user visual review.

### 2.12 "What Changed" delta panel

* **area_id:** GSLEM-12.
* **area_name:** "What Changed" delta panel.
* **source_phase_or_pr:** Phase 25B-3 (PR #586).
* **evidence_type:** automated test + manual review.
* **current_coverage:** PR #586 merged on main. The
  "What Changed" delta panel is implemented (read-only
  UI panel; 10 KPIs). The exploratory banner is
  required for `generic_solar` / `generic_wind`. The
  panel is gated on `card.is_user_project`. Factory
  projects (TUHO / Oborovo) do not render the panel.
* **tests_or_docs_available:** per PR #586 (84 new
  tests reported green in the PR body).
* **gap:** per-test enumeration not available at B42
  authoring. User visual review of the panel not yet
  performed.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** high.
* **no_go_claim_risk:** medium (the deltas are
  explanatory; they are not guaranteed accuracy
  claims).
* **next_action:** A future B-track governance refresh
  may add per-test enumeration and user visual review.

### 2.13 Exploratory banner

* **area_id:** GSLEM-13.
* **area_name:** Exploratory banner.
* **source_phase_or_pr:** Phase 25B-3 (PR #586).
* **evidence_type:** automated test.
* **current_coverage:** Per PR #586 the exploratory
  banner is required for `generic_solar` /
  `generic_wind`. The banner makes it clear that the
  deltas are not Excel-parity validated.
* **tests_or_docs_available:** per PR #586.
* **gap:** per-test enumeration not available at B42
  authoring.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** high.
* **no_go_claim_risk:** high (without the banner, the
  generic deltas could be misread as Excel-parity
  validated).
* **next_action:** A future B-track governance refresh
  may add per-test enumeration.

### 2.14 Generic Solar

* **area_id:** GSLEM-14.
* **area_name:** Generic Solar.
* **source_phase_or_pr:** Phase 24-H, 25B-1, 25B-3.
* **evidence_type:** automated test + manual review.
* **current_coverage:** Generic Solar is implemented
  end-to-end. Generic Solar remains exploratory and
  unvalidated. The exploratory banner is required.
* **tests_or_docs_available:** per Phase 24-H, 25B-1,
  25B-3.
* **gap:** reference solar model for Generic Solar
  output validation not available. Market validation of
  Generic Solar defaults not available.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** low (until validated).
* **external_review_relevance:** high.
* **no_go_claim_risk:** high (without reference model
  validation, Generic Solar cannot be claimed as
  Excel-parity validated).
* **next_action:** A future B-track governance refresh
  may add reference-model validation.

### 2.15 Generic Wind

* **area_id:** GSLEM-15.
* **area_name:** Generic Wind.
* **source_phase_or_pr:** Phase 24-H, 25B-1, 25B-3.
* **evidence_type:** automated test + manual review.
* **current_coverage:** Generic Wind is implemented
  end-to-end. Generic Wind remains exploratory and
  unvalidated. The exploratory banner is required.
* **tests_or_docs_available:** per Phase 24-H, 25B-1,
  25B-3.
* **gap:** reference wind model for Generic Wind output
  validation not available. Market validation of Generic
  Wind defaults not available.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** low (until validated).
* **external_review_relevance:** high.
* **no_go_claim_risk:** high (without reference model
  validation, Generic Wind cannot be claimed as
  Excel-parity validated).
* **next_action:** A future B-track governance refresh
  may add reference-model validation.

### 2.16 TUHO / Oborovo factory safety

* **area_id:** GSLEM-16.
* **area_name:** TUHO / Oborovo factory safety.
* **source_phase_or_pr:** Phase 25B-3 (PR #586).
* **evidence_type:** automated test.
* **current_coverage:** Per PR #586 factory project run
  summary output is byte-identical to the pre-Phase-
  25B-3 path. The "What Changed" panel is gated on
  `card.is_user_project`; factory projects (TUHO /
  Oborovo) do not render the panel.
* **tests_or_docs_available:** per PR #586.
* **gap:** per-test enumeration not available at B42
  authoring.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** high.
* **no_go_claim_risk:** low (factory safety is
  preserved).
* **next_action:** A future B-track governance refresh
  may add per-test enumeration.

### 2.17 No model-output drift

* **area_id:** GSLEM-17.
* **area_name:** No model-output drift.
* **source_phase_or_pr:** Phase 25B-3 (PR #586) +
  parity-core lock.
* **evidence_type:** automated test.
* **current_coverage:** Per PR #586 the parity-core lock
  is unchanged for TUHO and Oborovo. Factory project run
  summary output is byte-identical to the pre-Phase-
  25B-3 path.
* **tests_or_docs_available:** per PR #586.
* **gap:** per-test enumeration not available at B42
  authoring. Full parity-core lock re-verification not
  available at B42 authoring.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** high.
* **no_go_claim_risk:** high (model-output drift would
  invalidate the financial model).
* **next_action:** A future B-track governance refresh
  may add per-test enumeration and full parity-core
  lock re-verification.

### 2.18 No schema migration

* **area_id:** GSLEM-18.
* **area_name:** No schema migration.
* **source_phase_or_pr:** Phase 25B-3 (PR #586).
* **evidence_type:** automated test.
* **current_coverage:** Per PR #586 there is no schema
  migration. No new columns. No column type changes.
  No data backfill. The `replay_metadata` JSON column
  now carries two additional optional keys.
* **tests_or_docs_available:** per PR #586.
* **gap:** per-test enumeration not available at B42
  authoring.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** medium.
* **no_go_claim_risk:** low (no schema migration
  preserves backwards compatibility).
* **next_action:** A future B-track governance refresh
  may add per-test enumeration.

### 2.19 No formula change

* **area_id:** GSLEM-19.
* **area_name:** No formula change.
* **source_phase_or_pr:** Phase 25B-3 (PR #586).
* **evidence_type:** automated test.
* **current_coverage:** Per PR #586 there are no model
  formula changes. The helper module only does
  subtraction and percentage. No tax / debt /
  depreciation / IDC changes. No construction / C10 /
  R-PAR promotion. No senior IDC changes. No new
  financial formulas.
* **tests_or_docs_available:** per PR #586.
* **gap:** per-test enumeration not available at B42
  authoring.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** high.
* **no_go_claim_risk:** low (no formula change
  preserves the financial model).
* **next_action:** A future B-track governance refresh
  may add per-test enumeration.

### 2.20 Persistence metadata rotation

* **area_id:** GSLEM-20.
* **area_name:** Persistence metadata rotation.
* **source_phase_or_pr:** Phase 25B-3 (PR #586).
* **evidence_type:** automated test.
* **current_coverage:** Per PR #586 the
  `update_scenario_last_run_summary` function has
  minimal rotation behavior. The previous run summary
  is stamped into `replay_metadata.previous_run_summary`
  before overwriting `last_run_summary_json`. Other
  `replay_metadata` keys are preserved across writes.
  Corrupted or missing `replay_metadata` is tolerated
  (rotation initialises a fresh dict).
* **tests_or_docs_available:** per PR #586.
* **gap:** per-test enumeration not available at B42
  authoring.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** medium.
* **external_review_relevance:** medium.
* **no_go_claim_risk:** low (the rotation is minimal
  and scoped).
* **next_action:** A future B-track governance refresh
  may add per-test enumeration.

## 3. Evidence status

The matrix is **empty at creation**. Coverage values
are recorded only when actual evidence is available.
No coverage is invented. The per-area matrix records
the per-area scope and the per-area source phase or
PR; the actual evidence is collected during the
controlled pilot and the user visual review.

## 4. What B42 is not

* B42 is not a code change. Agent B does not implement
  Generic Modelling code.
* B42 is not external validation. The matrix is
  internal governance.
* B42 is not a paid pilot authorization.
* B42 is not a customer reference.
* B42 is not a production readiness claim.
* B42 is not an enterprise SaaS readiness claim.
* B42 is not a financial model validation.
* B42 is not a substitute for the user's visual
  review or the user's merge decisions.

## 5. Cross-references

* `reports/validation/generic_scenario_loop_evidence_matrix.json`
  (B42, machine-readable)
* `docs/governance/post_phase25b_generic_modelling_governance_refresh.md`
  (B41)
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
* `docs/validation/ui_regression_evidence_matrix.md` (B37)
* `docs/validation/validation_evidence_matrix.md` (B3)
* `docs/validation/model_confidence_heatmap.md` (B12)

---

*End of Generic Scenario Loop evidence matrix.*
