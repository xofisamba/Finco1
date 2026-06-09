# Internal Pilot Readiness Matrix

This file is the **internal pilot readiness matrix**.
It is the B-track governance wrapper for the
readiness of the internal controlled pilot after the
UI governance arc (B35-B40, PR #489) and the Generic
Modelling Loop arc (B41-B47, PR #588).

> **Internal pilot readiness is not paid pilot
> readiness. Internal pilot does not create customer
> reference. No reliance for credit / investment
> decisions.**

---

## 1. Readiness dimensions

The matrix covers the following readiness dimensions:

* Model calculation reliability.
* Persistence / save-load reliability.
* Scenario workflow reliability.
* Generic defaults workflow.
* Compare / multi-compare workflow.
* Export / download workflow.
* What Changed indicator.
* UI navigation / UX clarity.
* CAPEX / LineItemGrid visual readiness.
* Evidence / auditability.
* No-go guardrails.
* Documentation readiness.
* Operational support readiness.
* External review readiness.
* Paid pilot readiness.
* Enterprise readiness.

## 2. Per-dimension matrix

### 2.1 Model calculation reliability

* **dimension_id:** DIM-01.
* **dimension_name:** Model calculation reliability.
* **readiness_status:** ready.
* **evidence_available:** Internal test evidence;
  parity-core lock preserved for TUHO and Oborovo;
  factory project run summary output is byte-
  identical to pre-Phase-25B-3 path.
* **evidence_missing:** Reference solar / wind model
  for Generic Solar / Wind output validation.
* **key_risks:** Model output drift on TUHO or
  Oborovo would invalidate the financial model.
* **required_next_action:** Continue parity-core lock
  re-verification per PR / Phase.
* **owner:** Agent A (code) + Agent B (governance).
* **can_be_used_in_internal_pilot:** yes.
* **can_be_shown_in_demo:** yes (with the B11 / B44
  commercial guardrail caveats).
* **paid_pilot_impact:** Must be re-verified before
  paid pilot authorization.
* **external_review_impact:** High. The model is
  internal evidence; the external review is a
  separate workstream.

### 2.2 Persistence / save-load reliability

* **dimension_id:** DIM-02.
* **dimension_name:** Persistence / save-load
  reliability.
* **readiness_status:** ready.
* **evidence_available:** Internal test evidence;
  persistence rotation in
  `update_scenario_last_run_summary` is minimal and
  scoped; other `replay_metadata` keys are preserved
  across writes; corrupted / missing `replay_metadata`
  is tolerated; no schema migration in Phase 25B-3.
* **evidence_missing:** Long-term persistence
  reliability evidence (multi-month save-load
  cycles).
* **key_risks:** Schema migration drift; persistence
  rotation drift; corruption of `replay_metadata`.
* **required_next_action:** Continue per-PR
  persistence guardrails tests (CI check).
* **owner:** Agent A (code) + Agent B (governance).
* **can_be_used_in_internal_pilot:** yes.
* **can_be_shown_in_demo:** yes.
* **paid_pilot_impact:** Must be re-verified before
  paid pilot authorization.
* **external_review_impact:** High. The persistence
  layer is internal evidence.

### 2.3 Scenario workflow reliability

* **dimension_id:** DIM-03.
* **dimension_name:** Scenario workflow reliability.
* **readiness_status:** ready.
* **evidence_available:** Internal test evidence
  (Phase 24-H, 24-H-2, 24-H-3, 24-H-4, 25B-1, 25B-2,
  25B-2.1, 25B-3 PRs).
* **evidence_missing:** User visual review of the
  scenario workflow; controlled pilot run with real
  users.
* **key_risks:** UX issues that block the scenario
  workflow; critical data integrity issues.
* **required_next_action:** User visual review of the
  scenario workflow; controlled pilot run per B45.
* **owner:** Agent A (code) + Agent B (governance) +
  User (visual review).
* **can_be_used_in_internal_pilot:** yes.
* **can_be_shown_in_demo:** yes.
* **paid_pilot_impact:** Must be re-verified before
  paid pilot authorization.
* **external_review_impact:** High. The scenario
  workflow is internal evidence.

### 2.4 Generic defaults workflow

* **dimension_id:** DIM-04.
* **dimension_name:** Generic defaults workflow.
* **readiness_status:** partially_ready.
* **evidence_available:** Internal test evidence
  (Phase 25B-1 / PR #583).
* **evidence_missing:** Reference solar / wind model
  for Generic Solar / Wind defaults validation;
  market validation of defaults; user visual review
  of the prefill button.
* **key_risks:** Generic defaults are illustrative
  until validated by reference models. Misreading
  the defaults as market-validated would be a no-go
  claim violation.
* **required_next_action:** Reference-model validation
  for Generic Solar / Wind (per B53 roadmap); user
  visual review of the prefill button.
* **owner:** Agent A (code) + Agent B (governance) +
  User (visual review) + external reviewer (when
  available).
* **can_be_used_in_internal_pilot:** yes (with
  exploratory banner).
* **can_be_shown_in_demo:** yes (with the B44
  commercial guardrail caveats).
* **paid_pilot_impact:** Must NOT be used for credit /
  investment decisions until reference-model
  validation is complete.
* **external_review_impact:** High. The Generic
  defaults are exploratory and unvalidated.

### 2.5 Compare / multi-compare workflow

* **dimension_id:** DIM-05.
* **dimension_name:** Compare / multi-compare
  workflow.
* **readiness_status:** ready.
* **evidence_available:** Internal test evidence
  (Phase 24-H-3 + Phase 25B-2 / PR #584 + Phase
  25B-2.1 / PR #585).
* **evidence_missing:** User visual review of the
  compare panel and the multi-compare picker.
* **key_risks:** UX issues that block the compare
  workflow; multi-compare picker integration with
  the compare panel.
* **required_next_action:** User visual review of the
  compare panel and the multi-compare picker.
* **owner:** Agent A (code) + Agent B (governance) +
  User (visual review).
* **can_be_used_in_internal_pilot:** yes.
* **can_be_shown_in_demo:** yes (with the B44
  commercial guardrail caveats that the compare is
  internal functionality, not model validation).
* **paid_pilot_impact:** Must be re-verified before
  paid pilot authorization.
* **external_review_impact:** Medium. The compare is
  internal functionality.

### 2.6 Export / download workflow

* **dimension_id:** DIM-06.
* **dimension_name:** Export / download workflow.
* **readiness_status:** ready.
* **evidence_available:** Internal test evidence
  (Phase 24-H-4).
* **evidence_missing:** Export artifact evidence
  (collected during the controlled pilot, per B45
  task T9); user visual review of the export /
  download artifacts.
* **key_risks:** Export artifact drift; misreading
  the export as bankability would be a no-go claim
  violation.
* **required_next_action:** Export artifact evidence
  collection during the controlled pilot; user
  visual review.
* **owner:** Agent A (code) + Agent B (governance) +
  User (visual review).
* **can_be_used_in_internal_pilot:** yes (with
  exploratory banner for Generic Solar / Wind).
* **can_be_shown_in_demo:** yes (with the B44
  commercial guardrail caveats that the export is
  internal artifact generation, not bankability).
* **paid_pilot_impact:** Must NOT be used for credit /
  investment decisions.
* **external_review_impact:** Medium. The export /
  download pack is internal artifact generation.

### 2.7 What Changed indicator

* **dimension_id:** DIM-07.
* **dimension_name:** What Changed indicator.
* **readiness_status:** ready.
* **evidence_available:** Internal test evidence (84
  new tests reported green in the PR #586 body).
* **evidence_missing:** User visual review of the
  What Changed panel; controlled pilot run with
  real users.
* **key_risks:** Deltas misread as guaranteed
  accuracy claims; missing exploratory banner for
  Generic Solar / Wind; panel rendering for factory
  projects (should NOT render).
* **required_next_action:** User visual review of the
  What Changed panel; controlled pilot run.
* **owner:** Agent A (code) + Agent B (governance) +
  User (visual review).
* **can_be_used_in_internal_pilot:** yes.
* **can_be_shown_in_demo:** yes (with the B44
  commercial guardrail caveats that the deltas are
  explanatory, not guaranteed accuracy claims).
* **paid_pilot_impact:** Must NOT be used for credit /
  investment decisions.
* **external_review_impact:** High. The What Changed
  panel is a new UI feature; the external review is
  a separate workstream.

### 2.8 UI navigation / UX clarity

* **dimension_id:** DIM-08.
* **dimension_name:** UI navigation / UX clarity.
* **readiness_status:** partially_ready.
* **evidence_available:** Internal test evidence;
  route-render smoke + index context-contract tests
  (Phase 57-pre / PR #486); UX cleanup
  characterization (Phase 56A-56G).
* **evidence_missing:** User visual review of the UI
  navigation; controlled pilot run with real users.
* **key_risks:** UX issues that block the navigation;
  accessibility issues.
* **required_next_action:** User visual review of the
  UI navigation; controlled pilot run.
* **owner:** Agent A (code) + Agent B (governance) +
  User (visual review).
* **can_be_used_in_internal_pilot:** yes.
* **can_be_shown_in_demo:** yes.
* **paid_pilot_impact:** Must be re-verified before
  paid pilot authorization.
* **external_review_impact:** Medium. The UI
  navigation is internal evidence.

### 2.9 CAPEX / LineItemGrid visual readiness

* **dimension_id:** DIM-09.
* **dimension_name:** CAPEX / LineItemGrid visual
  readiness.
* **readiness_status:** ready.
* **evidence_available:** Internal test evidence
  (Phase 57A / PR #487).
* **evidence_missing:** User visual review of the
  CAPEX summary grid; controlled pilot run with
  real users.
* **key_risks:** Visual invariant break; CSS class
  preservation rule break; new console error; new
  404 request.
* **required_next_action:** User visual review of the
  CAPEX summary grid; controlled pilot run.
* **owner:** Agent A (code) + Agent B (governance) +
  User (visual review).
* **can_be_used_in_internal_pilot:** yes.
* **can_be_shown_in_demo:** yes.
* **paid_pilot_impact:** Must be re-verified before
  paid pilot authorization.
* **external_review_impact:** Medium. The CAPEX
  summary grid is a UI refactor.

### 2.10 Evidence / auditability

* **dimension_id:** DIM-10.
* **dimension_name:** Evidence / auditability.
* **readiness_status:** ready.
* **evidence_available:** B1, B3, B11, B19, B22, B37,
  B42, B46 evidence artifacts on main.
* **evidence_missing:** External reviewer evidence;
  controlled pilot evidence (collected during the
  controlled pilot).
* **key_risks:** Misreading internal evidence as
  external validation.
* **required_next_action:** Continue per-PR B-track
  governance refreshes.
* **owner:** Agent B (governance).
* **can_be_used_in_internal_pilot:** yes.
* **can_be_shown_in_demo:** yes (with the B11 / B22 /
  B38 / B44 commercial guardrail caveats).
* **paid_pilot_impact:** Must be re-verified before
  paid pilot authorization.
* **external_review_impact:** High. The evidence /
  auditability is the input to the external review.

### 2.11 No-go guardrails

* **dimension_id:** DIM-11.
* **dimension_name:** No-go guardrails.
* **readiness_status:** ready.
* **evidence_available:** B1, B11, B19, B22, B38, B44
  no-go claim artifacts on main.
* **evidence_missing:** None. The no-go guardrails
  are in place.
* **key_risks:** No-go claim violation in demo /
  commercial language.
* **required_next_action:** Continue per-PR B-track
  governance refreshes; per-demo language review.
* **owner:** Agent B (governance).
* **can_be_used_in_internal_pilot:** yes.
* **can_be_shown_in_demo:** yes.
* **paid_pilot_impact:** No-go guardrails block
  paid pilot authorization.
* **external_review_impact:** High. The no-go
  guardrails are the primary claim-control
  mechanism.

### 2.12 Documentation readiness

* **dimension_id:** DIM-12.
* **dimension_name:** Documentation readiness.
* **readiness_status:** ready.
* **evidence_available:** B1, B3, B11, B14, B18, B19,
  B20, B21, B22, B23, B24, B25, B26, B27, B28, B29,
  B30, B31, B32, B33, B34, B35, B36, B37, B38, B39,
  B40, B41, B42, B43, B44, B45, B46, B47 documentation
  artifacts on main.
* **evidence_missing:** None. The documentation is
  in place.
* **key_risks:** Stale documentation; missing
  documentation for new phases.
* **required_next_action:** Continue per-PR B-track
  governance refreshes.
* **owner:** Agent B (governance).
* **can_be_used_in_internal_pilot:** yes.
* **can_be_shown_in_demo:** yes.
* **paid_pilot_impact:** None (documentation does not
  affect paid pilot authorization).
* **external_review_impact:** High. The documentation
  is the input to the external review.

### 2.13 Operational support readiness

* **dimension_id:** DIM-13.
* **dimension_name:** Operational support readiness.
* **readiness_status:** not_ready.
* **evidence_available:** None.
* **evidence_missing:** Operational support
  documentation; support runbook; incident response
  plan.
* **key_risks:** Operational issues that block the
  internal pilot.
* **required_next_action:** Develop operational
  support documentation per B17 (support and
  incident response).
* **owner:** Agent B (governance) + User (operations).
* **can_be_used_in_internal_pilot:** no (not yet).
* **can_be_shown_in_demo:** no.
* **paid_pilot_impact:** Must be developed before
  paid pilot authorization.
* **external_review_impact:** Low. The operational
  support is internal evidence.

### 2.14 External review readiness

* **dimension_id:** DIM-14.
* **dimension_name:** External review readiness.
* **readiness_status:** not_ready.
* **evidence_available:** Internal evidence index
  (B50); B23 reviewer question bank.
* **evidence_missing:** External reviewer feedback;
  external reviewer sign-off.
* **key_risks:** External reviewer unavailable;
  external reviewer feedback not collected.
* **required_next_action:** Identify and onboard an
  external reviewer; collect external reviewer
  feedback.
* **owner:** User (external review) + Agent B
  (governance).
* **can_be_used_in_internal_pilot:** n/a (external
  review is separate from internal pilot).
* **can_be_shown_in_demo:** n/a.
* **paid_pilot_impact:** Must be re-verified before
  paid pilot authorization.
* **external_review_impact:** N/A. The external
  review is a separate workstream.

### 2.15 Paid pilot readiness

* **dimension_id:** DIM-15.
* **dimension_name:** Paid pilot readiness.
* **readiness_status:** not_ready.
* **evidence_available:** None.
* **evidence_missing:** Reference-model validation
  for Generic Solar / Wind; controlled pilot run
  with real users; external reviewer feedback; paid
  pilot gate review per B25 / B33 / B35 stop / go
  checklists.
* **key_risks:** Paid pilot authorized prematurely.
* **required_next_action:** Reference-model validation
  + controlled pilot + external reviewer feedback +
  paid pilot gate review.
* **owner:** User (paid pilot gate review) + Agent B
  (governance).
* **can_be_used_in_internal_pilot:** n/a.
* **can_be_shown_in_demo:** n/a.
* **paid_pilot_impact:** N/A.
* **external_review_impact:** N/A.

### 2.16 Enterprise readiness

* **dimension_id:** DIM-16.
* **dimension_name:** Enterprise readiness.
* **readiness_status:** not_ready.
* **evidence_available:** B8 enterprise SaaS
  readiness tracker; B17 operational support; B25 /
  B33 / B35 stop / go checklists.
* **evidence_missing:** Multi-tenant readiness; SSO;
  RBAC; audit log; SOC 2; ISO 27001; GDPR; etc.
* **key_risks:** Enterprise SaaS readiness claimed
  prematurely.
* **required_next_action:** Develop the enterprise
  SaaS readiness dimensions per the B8 tracker.
* **owner:** User (enterprise readiness) + Agent B
  (governance).
* **can_be_used_in_internal_pilot:** n/a.
* **can_be_shown_in_demo:** n/a.
* **paid_pilot_impact:** N/A.
* **external_review_impact:** N/A.

## 3. Readiness summary

* **Ready:** DIM-01, DIM-02, DIM-03, DIM-05, DIM-06,
  DIM-07, DIM-09, DIM-10, DIM-11, DIM-12.
* **Partially ready:** DIM-04 (Generic defaults
  workflow), DIM-08 (UI navigation / UX clarity).
* **Not ready:** DIM-13 (operational support), DIM-14
  (external review), DIM-15 (paid pilot), DIM-16
  (enterprise readiness).

## 4. What B49 is not

* B49 is not a code change. Agent B does not
  implement code.
* B49 is not external validation.
* B49 is not a paid pilot authorization.
* B49 is not a customer reference.
* B49 is not a production readiness claim.
* B49 is not an enterprise SaaS readiness claim.
* B49 is not a financial model validation.
* B49 is not a substitute for the user's pilot
  decisions or the user's marketing decisions.

## 5. Cross-references

* `reports/pilot/internal_pilot_readiness_matrix.json`
  (B49, machine-readable)
* `docs/governance/current_product_scope_snapshot_after_ui_generic_loop.md`
  (B48)
* `docs/review/external_reviewer_evidence_index_refresh.md`
  (B50)
* `docs/governance/known_limitations_no_go_claims_consolidation.md`
  (B51)
* `docs/pilot/controlled_pilot_data_room_index.md` (B52)
* `docs/governance/next_validation_roadmap_after_generic_loop.md`
  (B53)
* `docs/pilot/controlled_pilot_runbook.md` (B18)
* `docs/pilot/controlled_pilot_ux_runbook.md` (B39)
* `docs/pilot/controlled_generic_scenario_pilot_runbook.md`
  (B45)

---

*End of internal pilot readiness matrix.*
