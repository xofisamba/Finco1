# UI Regression Evidence Matrix

This file is the **UI regression evidence matrix**. It
is the B-track governance artifact that tracks UI
regression coverage across the post-Phase 54-56 UI
work. The matrix defines the per-area evidence type,
current coverage, source PR or phase, gap, and pilot /
paid pilot / external review relevance.

> **The matrix is empty at creation. Coverage values
> are recorded only when actual evidence is available.
> No coverage is invented.**
>
> **Agent B does not implement UI code. Agent A
> implements UI code, tests, and visual review. Agent B
> records the matrix structure and the evidence as it
> is collected.**
>
> **The matrix does not validate the financial model.
> The matrix does not authorize paid pilot. The matrix
> does not claim external validation.**

---

## 1. Matrix scope

The matrix covers the following UI areas:

* Route-render smoke tests (Phase 57-pre).
* Index context-contract tests (Phase 57-pre).
* Template rendering.
* Visual review.
* Screenshot / manual review.
* Console error checks.
* Network 404 checks.
* Tab navigation.
* CAPEX summary grid (Phase 57A pending).
* New Project flow (Phase 56C DRAFT).
* Help tab (Phase 56B DRAFT).
* Project switcher (Phase 56E DRAFT).
* State banners (Phase 55G, Phase 56F DRAFT).
* Validation summary (Phase 55F).
* Runtime summary (Phase 55E).
* COD derived field (Phase 56D).
* Inputs tab.
* Generic no-go claim display.

## 2. Per-area matrix

### 2.1 Route-render smoke tests

* **area_id:** URE-01.
* **area_name:** Route-render smoke tests.
* **evidence_type:** automated test.
* **current_coverage:** Phase 57-pre (PR #486) merged
  on main. The route-render smoke tests cover the index
  route and the related template rendering. Per-Phase
  57-pre, the tests are guardrails for the UI-3 work.
* **source_pr_or_phase:** PR #486 (Phase 57-pre).
* **gap:** Other routes are not yet covered by route-
  render smoke tests. A future B-track governance
  refresh may add per-route coverage.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** medium.
* **next_action:** None for the controlled pilot. A
  future B-track governance refresh may add per-route
  coverage.

### 2.2 Index context-contract tests

* **area_id:** URE-02.
* **area_name:** Index context-contract tests.
* **evidence_type:** automated test.
* **current_coverage:** Phase 57-pre (PR #486) merged
  on main. The index context-contract tests verify that
  the context keys expected by the templates are
  present in the index page context.
* **source_pr_or_phase:** PR #486 (Phase 57-pre).
* **gap:** Other pages' context-contract tests are not
  yet defined. A future B-track governance refresh may
  add per-page context-contract tests.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** medium.
* **next_action:** None for the controlled pilot. A
  future B-track governance refresh may add per-page
  context-contract tests.

### 2.3 Template rendering

* **area_id:** URE-03.
* **area_name:** Template rendering (general).
* **evidence_type:** automated test + manual review.
* **current_coverage:** Partial. The route-render smoke
  tests cover the index route. Other templates (Inputs,
  Audit, Project switcher) are covered by ad-hoc manual
  review.
* **source_pr_or_phase:** PR #486 (Phase 57-pre) for
  automated; per-phase manual review for others.
* **gap:** Per-template automated tests are not yet in
  place. The B40 UI-3 migration governance plan defines
  the protocol for per-template regression tests.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** medium.
* **next_action:** B40 defines the per-migration
  regression test protocol.

### 2.4 Visual review (general)

* **area_id:** URE-04.
* **area_name:** Visual review (general).
* **evidence_type:** manual review.
* **current_coverage:** Per Phase 56G (DRAFT) the UX
  cleanup closeout visual review pack is in progress.
  PR #487 (Phase 57A) visual review is the B36 protocol.
* **source_pr_or_phase:** PR #484 (Phase 56G, DRAFT) +
  B36 (this branch).
* **gap:** Per-PR visual review is not yet performed
  for PR #487. The B36 protocol is the empty template.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** high.
* **next_action:** User or designated reviewer performs
  the B36 visual review for PR #487 after PR #487 is
  approved for visual review.

### 2.5 Screenshot / manual review

* **area_id:** URE-05.
* **area_name:** Screenshot / manual review.
* **evidence_type:** screenshot + manual review.
* **current_coverage:** Empty at creation. No
  screenshots are committed to the B-track artifacts.
* **source_pr_or_phase:** None.
* **gap:** Screenshots are required for the B36 visual
  review and for the B39 controlled pilot UX runbook.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** high.
* **next_action:** Screenshot collection is the
  responsibility of the user or the designated reviewer.

### 2.6 Console error checks

* **area_id:** URE-06.
* **area_name:** Console error checks.
* **evidence_type:** browser console log.
* **current_coverage:** Empty at creation. No console
  logs are committed to the B-track artifacts.
* **source_pr_or_phase:** None.
* **gap:** Console error checks are required for the
  B36 visual review and for the B39 controlled pilot
  UX runbook.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** high.
* **next_action:** Console error check is the
  responsibility of the user or the designated reviewer.

### 2.7 Network 404 checks

* **area_id:** URE-07.
* **area_name:** Network 404 checks.
* **evidence_type:** browser network log.
* **current_coverage:** Empty at creation. No network
  logs are committed to the B-track artifacts.
* **source_pr_or_phase:** None.
* **gap:** Network 404 checks are required for the
  B36 visual review and for the B39 controlled pilot
  UX runbook.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** high.
* **next_action:** Network 404 check is the
  responsibility of the user or the designated reviewer.

### 2.8 Tab navigation

* **area_id:** URE-08.
* **area_name:** Tab navigation.
* **evidence_type:** manual review.
* **current_coverage:** Empty at creation. No tab
  navigation traces are committed to the B-track
  artifacts.
* **source_pr_or_phase:** None.
* **gap:** Tab navigation traces are required for the
  B36 visual review and for the B39 controlled pilot
  UX runbook.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** high.
* **next_action:** Tab navigation trace is the
  responsibility of the user or the designated reviewer.

### 2.9 CAPEX summary grid

* **area_id:** URE-09.
* **area_name:** CAPEX summary grid.
* **evidence_type:** visual review + screenshot.
* **current_coverage:** Empty at creation. PR #487
  (Phase 57A) is open draft. The B36 visual review
  protocol is the empty template.
* **source_pr_or_phase:** PR #487 (Phase 57A, open
  draft) + B36 (this branch).
* **gap:** Visual review, console log, network log,
  tab navigation trace, and screenshots are required.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** high.
* **next_action:** User or designated reviewer performs
  the B36 visual review for PR #487 after PR #487 is
  approved for visual review.

### 2.10 New Project flow

* **area_id:** URE-10.
* **area_name:** New Project flow.
* **evidence_type:** visual review + automated test.
* **current_coverage:** Per Phase 56C (DRAFT, PR #480)
  the New Project form simplification is in progress.
  Per Phase 57-pre, the route-render smoke tests cover
  the index route (not the New Project flow).
* **source_pr_or_phase:** PR #480 (Phase 56C, DRAFT) +
  B36 visual review for PR #480 (after PR #480 is
  approved for visual review).
* **gap:** Visual review, console log, network log,
  tab navigation trace, and screenshots are required
  for the New Project flow.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** medium.
* **next_action:** User or designated reviewer performs
  the visual review for PR #480 after PR #480 is
  approved for visual review.

### 2.11 Help tab

* **area_id:** URE-11.
* **area_name:** Help tab.
* **evidence_type:** visual review.
* **current_coverage:** Per Phase 56B (DRAFT, PR #477)
  the Help section move is in progress.
* **source_pr_or_phase:** PR #477 (Phase 56B, DRAFT) +
  B36 visual review for PR #477 (after PR #477 is
  approved for visual review).
* **gap:** Visual review, console log, network log,
  tab navigation trace, and screenshots are required.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** medium.
* **external_review_relevance:** medium.
* **next_action:** User or designated reviewer performs
  the visual review for PR #477 after PR #477 is
  approved for visual review.

### 2.12 Project switcher

* **area_id:** URE-12.
* **area_name:** Project switcher.
* **evidence_type:** visual review.
* **current_coverage:** Per Phase 56E (DRAFT, PR #482)
  the project switcher simplification is in progress.
* **source_pr_or_phase:** PR #482 (Phase 56E, DRAFT) +
  B36 visual review for PR #482 (after PR #482 is
  approved for visual review).
* **gap:** Visual review, console log, network log,
  tab navigation trace, and screenshots are required.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** medium.
* **external_review_relevance:** medium.
* **next_action:** User or designated reviewer performs
  the visual review for PR #482 after PR #482 is
  approved for visual review.

### 2.13 State banners

* **area_id:** URE-13.
* **area_name:** State banners.
* **evidence_type:** visual review + automated test.
* **current_coverage:** Per Phase 55G (PR #475) the
  banner context is wired into the index page context.
  Per Phase 56F (DRAFT, PR #483) the state banner
  hierarchy polish is in progress.
* **source_pr_or_phase:** PR #475 (Phase 55G) + PR #483
  (Phase 56F, DRAFT) + B36 visual review for PR #483
  (after PR #483 is approved for visual review).
* **gap:** Visual review for PR #483 is required.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** medium.
* **next_action:** User or designated reviewer performs
  the visual review for PR #483 after PR #483 is
  approved for visual review.

### 2.14 Validation summary

* **area_id:** URE-14.
* **area_name:** Validation summary.
* **evidence_type:** visual review + automated test.
* **current_coverage:** Per Phase 55F (PR #474) the
  validation summary is wired into the index / audit
  context. Per Phase 57-pre the index context-contract
  tests verify the context key is present.
* **source_pr_or_phase:** PR #474 (Phase 55F) + PR #486
  (Phase 57-pre).
* **gap:** Per-template visual review of the validation
  summary display is not yet performed.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** high.
* **next_action:** User or designated reviewer performs
  the visual review of the validation summary display.

### 2.15 Runtime summary

* **area_id:** URE-15.
* **area_name:** Runtime summary.
* **evidence_type:** visual review + automated test.
* **current_coverage:** Per Phase 55E (PR #473) the
  runtime summary is wired into the index context. Per
  Phase 57-pre the index context-contract tests verify
  the context key is present.
* **source_pr_or_phase:** PR #473 (Phase 55E) + PR #486
  (Phase 57-pre).
* **gap:** Per-template visual review of the runtime
  summary display is not yet performed.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** high.
* **next_action:** User or designated reviewer performs
  the visual review of the runtime summary display.

### 2.16 COD derived field

* **area_id:** URE-16.
* **area_name:** COD derived field.
* **evidence_type:** automated test.
* **current_coverage:** Per Phase 56D (PR #481) the COD
  is derived from construction_start_date and
  construction_duration_months (post-fix policy). The
  derivation is a UI-side display calculation; the
  underlying financial model is unchanged.
* **source_pr_or_phase:** PR #481 (Phase 56D).
* **gap:** Visual review of the COD display is not
  yet performed.
* **pilot_relevance:** medium.
* **paid_pilot_relevance:** medium.
* **external_review_relevance:** low.
* **next_action:** User or designated reviewer performs
  the visual review of the COD display.

### 2.17 Inputs tab

* **area_id:** URE-17.
* **area_name:** Inputs tab.
* **evidence_type:** visual review + manual review.
* **current_coverage:** Per Phase 51 / Phase 50 work
  the Inputs tab is functional. The post-UI-2.6
  context wiring (Phase 55E-55G) does not affect the
  Inputs tab directly.
* **source_pr_or_phase:** Per Phase 50 (Inputs tab
  characterizations).
* **gap:** Per-template visual review of the Inputs
  tab in the post-UI-2.6 context is not yet
  performed.
* **pilot_relevance:** high.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** high.
* **next_action:** User or designated reviewer performs
  the visual review of the Inputs tab in the post-
  UI-2.6 context.

### 2.18 Generic no-go claim display

* **area_id:** URE-18.
* **area_name:** Generic no-go claim display.
* **evidence_type:** visual review + content review.
* **current_coverage:** The no-go claim list (B1) and
  the commercial guardrail (B11) are in place. The
  generic no-go claim display is a UI element that
  surfaces the no-go claim list. Per Phase 54C the
  design system tokens and copy guardrails are in
  place. Per Phase 54H the no-go copy scanner is a
  governance guardrail (in development).
* **source_pr_or_phase:** B1 (no-go list) + B11
  (commercial guardrail) + B38 (this branch, UI no-go
  claim refresh) + Phase 54C / Phase 54H.
* **gap:** Per-template visual review of the no-go
  claim display is not yet performed.
* **pilot_relevance:** medium.
* **paid_pilot_relevance:** high.
* **external_review_relevance:** high.
* **next_action:** User or designated reviewer performs
  the visual review of the no-go claim display.

## 3. Per-PR review summary

The following per-PR visual review state is recorded:

* **PR #487 (Phase 57A, open draft):** B36 visual review
  protocol is empty. Visual review not yet performed.
* **PR #480 (Phase 56C, DRAFT):** B36 visual review
  protocol is empty. Visual review not yet performed.
* **PR #477 (Phase 56B, DRAFT):** B36 visual review
  protocol is empty. Visual review not yet performed.
* **PR #482 (Phase 56E, DRAFT):** B36 visual review
  protocol is empty. Visual review not yet performed.
* **PR #483 (Phase 56F, DRAFT):** B36 visual review
  protocol is empty. Visual review not yet performed.
* **PR #484 (Phase 56G, DRAFT):** B36 visual review
  protocol is empty. Visual review not yet performed.
* **PR #481 (Phase 56D, merged):** Per-template visual
  review of the COD display is not yet performed.
* **PR #485 (Phase 56H-1, merged):** Visual review not
  yet performed (the hotfix is targeted; visual review
  is the GET / regression check).
* **PR #486 (Phase 57-pre, merged):** Automated tests
  in place. Visual review of the route-render smoke
  and context-contract tests not yet performed.

## 4. What B37 is not

* B37 is not a code change. Agent B does not implement
  UI code.
* B37 is not external validation. The matrix is
  internal governance.
* B37 is not a paid pilot authorization.
* B37 is not a customer reference.
* B37 is not a production readiness claim.
* B37 is not an enterprise SaaS readiness claim.
* B37 is not a financial model validation.
* B37 is not a substitute for the user's visual
  review or the user's merge decisions.

## 5. Cross-references

* `reports/validation/ui_regression_evidence_matrix.json`
  (B37, machine-readable)
* `docs/governance/post_phase56_ui_governance_refresh.md`
  (B35)
* `docs/ui/phase57a_line_item_grid_visual_review.md` (B36)
* `docs/commercial/ui demo_guardrail_refresh.md` (B38)
* `docs/pilot/controlled_pilot_ux_runbook.md` (B39)
* `docs/governance/ui3_line_item_grid_migration_governance_plan.md`
  (B40)
* `docs/validation/validation_evidence_matrix.md` (B3)
* `docs/validation/model_confidence_heatmap.md` (B12)

---

*End of UI regression evidence matrix.*
