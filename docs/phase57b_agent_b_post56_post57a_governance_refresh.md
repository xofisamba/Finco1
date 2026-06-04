# Phase 57B — Agent B post-56 / post-57A governance refresh

## Status

DRAFT → marked ready → squash merged in the 57B overnight branch
(see `reports/phase57b_agent_b_post56_post57a_governance_refresh.json`
for the merge SHA).

## Current main SHA (start of 57B)

`b173355b6021577f6567069ebd748aa3176f2475` (post-57A, LineItemGrid
CAPEX pilot merged)

## Current main SHA (after 57B)

Reported in the 57B combined report.

## Agent B docs reviewed

Reviewed the following Agent B governance / pilot / external-review
docs against the post-55E/55F/55G + 56A-56G + 56H-1 + 57-pre + 57A
state of main:

### Governance docs
- `docs/governance/agent_a_b_governance_refresh_plan.md`
- `docs/governance/b_track_phase53_refresh_cadence.md`
- `docs/governance/phase52_53_guardrail_adoption_tracker.md`
- `docs/governance/phase53_change_control_checklist.md`
- `docs/governance/phase53_progress_ledger.md`
- `docs/governance/phase53_risk_gate_matrix.md`
- `docs/governance/phase53_stop_go_checklist.md`
- `docs/governance/phase53ab_governance_refresh.md`
- `docs/governance/post_phase52_governance_refresh.md`
- `docs/governance/remaining_hotspots_governance_tracker.md`

### External review / pilot docs
- `docs/external_review/data_room_index.md`
- `docs/external_review/external_review_closeout_tracker.md`
- `docs/external_review/external_review_package_index.md`
- `docs/external_review/external_reviewer_question_bank.md`
- `docs/external_review/model_scope_and_limitations.md`
- `docs/external_review/no_go_claims.md`
- `docs/external_review/reviewer_evidence_checklist.md`
- `docs/external_review/reviewer_instructions.md`
- `docs/external_review/reviewer_qna_template.md`
- `docs/external_review/tuho_oborovo_validation_summary.md`

### Prior Agent B refresh PRs (already merged)
- PR #390 (B1, 2026-06-02) — External review preparation package
- PR #394 (B3/B2/B7/B8, 2026-06-02) — Governance pack
- PR #398 (B9-B14, 2026-06-02) — Pilot review pack
- PR #413 (B15-B19, 2026-06-03) — Phase 51N governance refresh and
  pilot closeout pack
- PR #421 (B20-B23, 2026-06-03) — Pilot operating and review prep pack
- Phase 55A (B24+, 2026-06-04) — Agent B post-UI-2 governance refresh

### Recent phase docs (post-55A)
- `docs/phase55a_agent_b_post_ui2_governance_refresh.md`
- `docs/phase56a_ux_cleanup_help_project_new_project_characterization.md`
- `docs/phase56b_help_section.md`
- `docs/phase56c_new_project_v1_form_simplification.md`
- `docs/phase56d_cod_derived_field.md`
- `docs/phase56e_project_switch_simplification.md`
- `docs/phase56f_state_banner_visual_hierarchy.md`
- `docs/phase56g_ux_cleanup_closeout_visual_review.md`
- `docs/phase56h_post_merge_visual_qa.md`
- `docs/phase57pre_route_render_smoke_context_contract.md`
- `docs/phase57a_ui3_line_item_grid_capex_summary.md`

## Stale statements found

The following references / statements in the Agent B governance
corpus are now stale relative to main. They are **findings only**;
**fixes are out of scope for 57B** and would require a separate
docs-only refresh PR (Agent B's B-track cadence).

### 1. UI state components (post-55E-55G wiring)

Some references in `agent_a_b_governance_refresh_plan.md` and
`b_track_phase53_refresh_cadence.md` describe the UI state
components (state banner, validation summary, runtime summary,
last-run indicator) as **planned** or **pending activation**.

As of 55E/55F/55G (all merged, `12b82ca9`):

- `runtime_summary` is wired into the index context
  (`_runtime_summary_for_index` helper, 30 tests in 55E)
- `validation_summary` is wired into the index / audit context
  (`_validation_summary_for_context` helper, 26 tests in 55F)
- `banner_context` is wired into the index context
  (`_banner_context_for_index` helper, 40 tests in 55G)

All three helpers are read-only and operate on existing
`workspace_state` / `_governance_snapshot` fields. The 56H-1
hotfix preserved the wiring through a `NameError` regression;
the `validation_errors` local-variable hoist is pinned by 3
tests in `tests/test_phase56h1_index_validation_errors_hotfix.py`
and 3 tests in `tests/test_phase57pre_route_render_smoke.py`
(`Test56H1RegressionPin`).

### 2. UX cleanup arc (56A-56G)

The 56A-56G arc changed the user-facing help copy, the New
Project v1 form, the COD field policy, the project switch UX,
and the state banner visual hierarchy. The relevant Agent B
docs still reference the pre-56 help copy in a few places
(where it read "validated" — that word has been replaced with
"Reference" and "parity evidence" copy in 56B).

### 3. New Project v1 form (56C)

The 17-field form referenced in pilot operating docs has been
simplified to a 10-master-data + 1-derived (COD) v1 form in 56C.
The 11 detailed assumption fields are still editable but moved
to the Inputs tab. Pilot review pack docs should reference the
new field layout in any future update.

### 4. COD policy (56D)

COD is now derived server-side from `construction_start_date +
construction_duration_months`. The form input is read-only.
The Agent B reviewer evidence checklist and pilot review pack
should reference the 56D policy in any future update.

### 5. Project switch simplification (56E)

Project switching no longer requires reload or is now
cosmetic-only in 56E. Pilot review docs that describe the
pre-56E switcher should reference the new simplified flow.

### 6. State banner visual hierarchy (56F)

State banner hierarchy is more clearly defined: governance
guards (G20/R99/R102) take priority over run state, which
takes priority over factory reference. Pilot docs that
describe the prior flat banner should be refreshed.

### 7. LineItemGrid pilot (57A)

The CAPEX summary sheet is now a presentation refactor only.
It does **not** validate the model. The new
`app/templates/partials/_line_item_grid.html` partial is
shared, and `sheet_capex.html` is migrated. Other sheets
(OPEX, Revenue, Debt, SHL, Tax, Construction, Production,
Inputs, Financials, IDC, CAPEX detail) are **not** migrated.

Pilot docs should reference 57A explicitly as a **presentation
refactor** of the CAPEX summary sheet. The migration is
read-only-financing and respects the global `editable` arg
for ordinary hard CAPEX rows.

### 8. Route-render smoke (57-pre)

`tests/test_phase57pre_route_render_smoke.py` now covers 13
GET routes with a 56H-1 regression pin. Pilot review docs
that previously noted "no GET route smoke coverage" can be
refreshed to "GET route smoke is pinned (13 routes, 49 tests,
3 56H-1 regression pin tests)".

## Updated governance map

The 57B governance map reflects the post-57A state of main:

| Arc / phase | Status | Notes |
|---|---|---|
| 53 (persistence) | CLOSED | 23 PRs merged |
| 54 (UI-1 spec) | CLOSED | 5 PRs merged |
| 54F-J (UI-2 prep) | CLOSED | 5 PRs merged |
| UI-2.1..UI-2.6 runtime | CLOSED + WIRES LIVE | 6 PRs merged; 55E/55F/55G wires active |
| 55A-55D (post-UI-2 review response) | CLOSED | 4 PRs merged |
| 55E-55G (context wiring) | CLOSED | 3 PRs merged, all wires live |
| 56A-56G (UX cleanup) | CLOSED | 7 PRs merged |
| 56H-1 (NameError hotfix) | CLOSED | 1 PR merged, hoist pinned |
| 57-pre (route-render smoke) | CLOSED | 1 PR merged, 13 routes covered |
| 57A (LineItemGrid CAPEX pilot) | CLOSED | 1 PR merged, presentation refactor only |
| **57B (this refresh)** | CLOSED | 1 docs/report/test PR merged |

## Internal-only docs

The following docs are **internal-only**. They are not for
external review and must not be packaged into reviewer-facing
deliverables without explicit Agent B approval:

- `docs/governance/agent_a_b_governance_refresh_plan.md`
- `docs/governance/b_track_phase53_refresh_cadence.md`
- `docs/governance/phase52_53_guardrail_adoption_tracker.md`
- `docs/governance/phase53_change_control_checklist.md`
- `docs/governance/phase53_progress_ledger.md`
- `docs/governance/phase53_risk_gate_matrix.md`
- `docs/governance/phase53_stop_go_checklist.md`
- `docs/governance/phase53ab_governance_refresh.md`
- `docs/governance/post_phase52_governance_refresh.md`
- `docs/governance/remaining_hotspots_governance_tracker.md`

These docs may use operational terminology (BLOCKED, NOT
APPROVED, pilot, refresh, etc.) but must not use forbidden
positive claims (bankable, lender-ready, validated, certified,
audit-ready, investor-ready, SaaS-ready, production-ready,
external validation, customer reference, investment advice,
guaranteed returns).

## Controlled pilot docs

The following docs are **controlled-pilot**. They are
internal-facing but may be shared with a controlled pilot
group after explicit Agent B approval. They use Reference /
parity evidence / model evidence terminology. The word
"validated" is forbidden in positive user-facing contexts
(only allowed in no-go lists and explicit "not validated"
negative statements):

- `docs/external_review/data_room_index.md`
- `docs/external_review/external_review_closeout_tracker.md`
- `docs/external_review/external_review_package_index.md`
- `docs/external_review/external_reviewer_question_bank.md`
- `docs/external_review/model_scope_and_limitations.md`
- `docs/external_review/no_go_claims.md` (this one is the
  authoritative no-go list)
- `docs/external_review/reviewer_evidence_checklist.md`
- `docs/external_review/reviewer_instructions.md`
- `docs/external_review/reviewer_qna_template.md`
- `docs/external_review/tuho_oborovo_validation_summary.md`

The TUHO/Oborovo Reference summary uses "Reference" not
"validated" per the 56B rephrasing. The 56H-1 hotfix did
not affect the Reviewer-facing docs.

## No-go claims preserved

The forbidden positive claims list is unchanged from 55A and
prior refreshes:

- bankable
- bank-grade
- lender-ready
- certified
- audit-ready
- validated (in positive user-facing context)
- investor-ready
- SaaS-ready
- production-ready
- external validation
- customer reference
- investment advice
- guaranteed returns

The 57A documentation explicitly added a new forbidden claim
category to the existing 57A test (`TestNoGoCopy`):

- "model-validated"
- "LineItemGrid is validated"
- "LineItemGrid is audit-ready"
- "LineItemGrid is certified"

These are forbidden because LineItemGrid is a presentation
refactor only; it does not validate the model.

## UI state components are internal model-evidence tooling only

The UI-2.1 state banner, UI-2.2 runtime impact chip,
UI-2.3 validation summary bar, UI-2.4 factory lock
indicator, UI-2.5 stale result warning, and UI-2.6 last-run
indicator are **internal model-evidence tooling**. They
display the state of internal model checks, governance
guards, and run metadata. They are not external validation
tools and must not be marketed as such.

- The state banner (UI-2.1) reflects governance guard state
  (BLOCKED, NOT APPROVED, OK) and run state (clean, stale,
  has issues). It does not represent a third-party audit.
- The runtime impact chip (UI-2.2) is read-only internal
  metadata about runtime changes.
- The validation summary bar (UI-2.3) counts per-run
  model/check issues. It is not a validation seal.
- The factory lock indicator (UI-2.4) shows whether a
  project is bound to a factory reference. It is a
  provenance marker, not a quality seal.
- The stale result warning (UI-2.5) tells the user that
  inputs have changed since the last run. It is internal
  data freshness, not validation.
- The last-run indicator (UI-2.6) shows the timestamp
  and run id of the last computation. It is provenance,
  not validation.

The 57C phase (next in the overnight stack) will redesign
the validation bar semantics to reduce alarm fatigue and
clarify that the permanent governance guards (G20, R99,
R102) are not per-run issues.

## LineItemGrid is UI presentation refactor only, not model validation

The 57A LineItemGrid migration is a **UI presentation
refactor only**. It does not change the underlying model,
the CAPEX computation, the validation logic, or any
backend service. The macro `lig_render` in
`app/templates/partials/_line_item_grid.html` takes
already-computed data structures and renders them as a
table with consistent CSS classes.

Specifically:

- The macro does not perform any computation.
- The macro does not call any service.
- The macro does not access the database.
- The macro does not write to persistence.
- The macro does not change the values shown to the user
  (all values come from the same data structures as
  before).
- The macro does not change the editable / read-only
  semantics of any row (Financing Costs rows are
  read-only in user project mode, as they always were
  pre-57A; Fix A in 57A-1 enforces this through the
  `data_financing` row type).
- The macro does not change the column order, row order,
  or class names of the rendered HTML.

Any claim that LineItemGrid "validates" the model, is
"audit-ready", or provides any form of assurance is
forbidden and contradicts the design.

## No external readiness claims

The post-57A state of main is a **UI-3.1 presentation
pilot**. It is not a release, not a release candidate,
not a release branch, and not a production deployment.
Any claim that the system is "ready", "bankable",
"lender-ready", "investor-ready", "certified",
"audit-ready", "validated", "SaaS-ready",
"production-ready", or has "external validation",
"customer reference", "investment advice", or
"guaranteed returns" is forbidden.

The pre-rc1 state is the only frozen state. The pre-57A
main (`9d05c0c8de8e097c59cf7253ada5592cb6556905`) is the
last "shippable" anchor. Any post-57A main is a working
branch state, not a release.

## Recommended Agent B next refresh

The next Agent B refresh (post-57B) should:

1. **Update `phase52_53_guardrail_adoption_tracker.md`** to
   reflect the post-55E/55F/55G + 56A-56G + 56H-1 + 57-pre
   + 57A state. The current adoption tracker references
   51F / 52F / 53I guardrails but does not yet pin
   55E/55F/55G or 57-pre/57A.
2. **Update `phase53_progress_ledger.md`** to close out
   the 53 arc as COMPLETE and add 54, 55, 56, 56H-1, 57,
   57A, 57B as separate ledger sections.
3. **Update `phase53_risk_gate_matrix.md`** to add a new
   "UI-3.x runtime grid migrations" risk row, with
   current state "57A done, others deferred".
4. **Update `tuho_oborovo_validation_summary.md`** to use
   "Reference" instead of "validated" per 56B rephrasing.
5. **Update `reviewer_evidence_checklist.md`** to add a
   new section for the 57A LineItemGrid CAPEX pilot
   (presentation refactor only, not model validation).
6. **Update `no_go_claims.md`** to add the new
   LineItemGrid-related forbidden claims listed above.
7. **Update `external_review_closeout_tracker.md`** to
   add a row for 57A / 57B with status and merge SHAs.

The next refresh is B-track cadence; B-track PRs are
docs-only and auto-merge eligible.

## Hard no-go / scope

- No financial model changes.
- No `app/waterfall_core.py` changes.
- No `app/project_factories.py` changes.
- No `app/persistence/` changes.
- No `app/services/` changes.
- No `main_web.py` changes.
- No `static/app.js` changes.
- No `static/styles.css` changes.
- No schema / migration changes.
- No fixture CSV changes.
- No frontend dependency changes.
- No Tailwind / Alpine / React / Vue / Svelte.
- No G20/R99/R102 guard promotion.
- No generic Solar/Wind runtime work.
- No BESS / Hybrid / Portfolio work.
- No forbidden positive user-facing claims.
- rc1 frozen (`b425a0708719eaa5e1d922b1008e5609758e0ad4`).
