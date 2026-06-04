# UI-3 LineItemGrid Migration Governance Plan

This file is the **UI-3 LineItemGrid migration
governance plan**. It is the B-track governance
wrapper for the UI-3 migration after the Phase 57A
LineItemGrid CAPEX pilot.

> **UI-3 is a UI migration. UI-3 is not a financial
> model migration. UI-3 is not a backend migration.
> UI-3 is not a persistence migration. UI-3 is not a
> schema / migration. UI-3 is not a parity-core
> migration.**
>
> **The Phase 57A LineItemGrid CAPEX pilot is the first
> UI-3 migration. The Phase 57A pilot is a single-
> sheet pilot. The full UI-3 migration is gated on
> the Phase 57A pilot succeeding.**
>
> **Agent B does not approve code correctness. Agent B
> does not approve financial output. Agent B does
> not authorize paid pilot. Agent B records the
> governance plan.**

---

## 1. One-sheet-at-a-time rule

The UI-3 migration follows the one-sheet-at-a-time
rule:

* **Each PR migrates exactly one sheet** to the shared
  LineItemGrid partial/macro.
* **No PR migrates multiple sheets.** Multiple-sheet
  migrations are out of scope for the UI-3
  governance plan and require an explicit governance
  update.
* **No PR migrates a sheet to a non-shared macro.**
  All UI-3 migrations must use the shared LineItemGrid
  partial/macro.

The one-sheet-at-a-time rule is enforced by the
following:

* Per-PR review by Agent A.
* Per-PR visual review by the user (per B36).
* Per-PR automated test by Agent A (route-render
  smoke + index context-contract + per-sheet
  regression).
* Per-PR B-track governance refresh (Agent B).

## 2. No formula / output change rule

The UI-3 migration follows the no-formula / output
change rule:

* **No PR changes any financial formula.** The
  financial formulas are owned by Agent A. The
  parity-core lock is unchanged.
* **No PR changes any engine output.** The engine
  output is owned by Agent A. The engine-output
  golden is unchanged.
* **No PR changes any model output.** The model
  output is owned by Agent A. The model output
  golden is unchanged.
* **No PR changes any fixture CSV.** The fixture CSVs
  are owned by Agent A.
* **No PR changes any schema / migration.** The
  schema / migration is owned by Agent A.
* **No PR changes any persistence / repository
  code.** The persistence / repository code is owned
  by Agent A.

The no-formula / output change rule is enforced by:

* Per-PR parity-core lock check (Phase 51F).
* Per-PR engine-output golden check (Phase 51T).
* Per-PR model-output golden check (Phase 51V).
* Per-PR B-track governance refresh (Agent B).

## 3. Template parity rule

The UI-3 migration follows the template parity rule:

* **The migrated sheet must render the same values
  as the original sheet.** The values are owned by
  the engine output. The engine output is unchanged.
* **The migrated sheet must preserve the original
  CSS class structure.** The CSS class structure is
  owned by Agent A. The CSS class structure is
  preserved.
* **The migrated sheet must preserve the original
  accessibility markers.** The accessibility markers
  are owned by Agent A. The accessibility markers are
  preserved.
* **The migrated sheet must preserve the original
  read-only state.** The read-only state is owned by
  Agent A. The read-only state is preserved.
* **The migrated sheet must not introduce any new
  console error.** The console error check is part
  of the per-PR visual review (per B36).
* **The migrated sheet must not introduce any new
  404 request.** The 404 check is part of the
  per-PR visual review (per B36).

The template parity rule is enforced by:

* Per-PR visual review (per B36).
* Per-PR automated test (route-render smoke + index
  context-contract + per-sheet regression).
* Per-PR B-track governance refresh (Agent B).

## 4. CSS class preservation rule

The UI-3 migration follows the CSS class preservation
rule:

* **No PR removes a CSS class.** All original CSS
  classes are preserved.
* **No PR renames a CSS class.** All original CSS
  class names are preserved.
* **No PR changes a CSS class to a non-equivalent
  class.** All original CSS class definitions are
  preserved.
* **The migrated sheet may add new CSS classes.** New
  CSS classes are allowed if they are scoped to the
  migrated sheet and do not affect other sheets.

The CSS class preservation rule is enforced by:

* Per-PR visual review (per B36).
* Per-PR automated test (CSS class check).
* Per-PR B-track governance refresh (Agent B).

## 5. Visual review requirement

The UI-3 migration requires a per-PR visual review:

* **The visual review is performed by the user or the
  designated reviewer.** Agent B records the visual
  review protocol (B36) but does not perform the
  visual review.
* **The visual review covers old-vs-new invariants,
  CSS class preservation, accessibility / read-only
  marker checks, no-overflow check, no-console-error
  check, network 404 check, tab navigation check, and
  GET / check.** (Per B36.)
* **The visual review is recorded in the B36 visual
  review pack.** (Per B36.)
* **The visual review is referenced in the per-PR
  B-track governance refresh.** (Per B35.)

The visual review requirement is enforced by:

* Per-PR B36 visual review.
* Per-PR B35 B-track governance refresh.
* Per-PR user approval.

## 6. Route smoke / context-contract requirement

The UI-3 migration requires a per-PR route smoke /
context-contract:

* **The route-render smoke test must pass on the
  migrated sheet's route.** The route-render smoke
  test is the Phase 57-pre test.
* **The index context-contract test must pass on the
  migrated sheet's index page.** The index context-
  contract test is the Phase 57-pre test.
* **The per-sheet regression test must pass on the
  migrated sheet.** The per-sheet regression test is
  added by Agent A in the migration PR.

The route smoke / context-contract requirement is
enforced by:

* Per-PR automated test (route-render smoke + index
  context-contract + per-sheet regression).
* Per-PR B-track governance refresh (Agent B).

## 7. Rollback condition

The UI-3 migration is rolled back when any of the
following conditions are met:

* **A financial output drift is detected on TUHO or
  Oborovo after the migration PR is merged.** The
  migration PR is reverted and the migration is
  paused.
* **A parity-core lock drift is detected after the
  migration PR is merged.** The migration PR is
  reverted and the migration is paused.
* **An engine-output golden drift is detected on
  TUHO or Oborovo after the migration PR is
  merged.** The migration PR is reverted and the
  migration is paused.
* **A model output drift is detected on TUHO or
  Oborovo after the migration PR is merged.** The
  migration PR is reverted and the migration is
  paused.
* **A visual invariant is broken in the visual
  review.** The migration PR is reverted and the
  migration is paused.
* **A CSS class preservation rule is broken in the
  visual review.** The migration PR is reverted and
  the migration is paused.
* **A high-severity UX issue is identified in the
  controlled pilot.** The migration PR is reverted
  and the migration is paused.

The rollback condition is enforced by:

* Per-PR parity-core lock check (Phase 51F).
* Per-PR engine-output golden check (Phase 51T).
* Per-PR model-output golden check (Phase 51V).
* Per-PR visual review (per B36).
* Per-PR B-track governance refresh (Agent B).

## 8. Out-of-scope sheets list

The following sheets are out of scope for the UI-3
migration (i.e., the migration to the shared
LineItemGrid partial/macro) at the time of B40
authoring:

* All sheets other than `app/templates/partials/sheet_capex.html`.

The out-of-scope sheets list is current at the time
of B40 authoring. The out-of-scope sheets list may
be updated by future B-track governance refreshes as
each sheet is migrated.

## 9. Future migration candidates

The following sheets are future migration candidates
for the UI-3 migration (i.e., the migration to the
shared LineItemGrid partial/macro):

* All sheets in the canonical reference project set
  (TUHO and Oborovo).
* All sheets in the canonical reference set that are
  not yet migrated.

The future migration candidates are listed in the
order of the canonical reference project set. The
order is subject to the user's priorities and Agent
A's capacity.

## 10. Evidence required per migration PR

The following evidence is required per migration PR:

* **Per-PR visual review** (per B36).
* **Per-PR automated test** (route-render smoke +
  index context-contract + per-sheet regression).
* **Per-PR parity-core lock check** (Phase 51F).
* **Per-PR engine-output golden check** (Phase 51T).
* **Per-PR model-output golden check** (Phase 51V).
* **Per-PR B-track governance refresh** (Agent B,
  per B35).
* **Per-PR user approval.**

The evidence is recorded in the per-PR B-track
governance refresh (per B35) and the per-PR visual
review (per B36).

## 11. Agent A ownership

Agent A owns the following for the UI-3 migration:

* **Code correctness** (template, partial, macro, CSS
  class preservation, accessibility markers,
  read-only state).
* **Automated tests** (route-render smoke + index
  context-contract + per-sheet regression).
* **Per-PR parity-core lock check** (Phase 51F).
* **Per-PR engine-output golden check** (Phase 51T).
* **Per-PR model-output golden check** (Phase 51V).
* **Per-PR fixture CSV updates** (if any; usually
  none).
* **Per-PR schema / migration** (if any; usually
  none).
* **Per-PR persistence / repository code** (if any;
  usually none).

Agent A does not authorize the migration. Agent A
implements the migration. The user authorizes the
migration.

## 12. Agent B review role

Agent B records the following for the UI-3 migration:

* **Per-PR B35 B-track governance refresh** (UI
  governance refresh).
* **Per-PR B36 visual review pack** (visual review
  protocol; the visual review itself is performed by
  the user or the designated reviewer).
* **Per-PR B37 UI regression evidence matrix**
  (per-PR visual review state).
* **Per-PR B38 UI no-go claim / demo guardrail
  refresh** (per-PR commercial guardrail).
* **Per-PR B39 controlled pilot UX runbook** (per-PR
  pilot user task list and evidence collection).
* **Per-PR B40 UI-3 migration governance plan**
  (this plan).

Agent B does not approve code correctness. Agent B
records the governance plan. The user approves the
migration.

## 13. When to refresh the B-track

The B-track governance refresh is required when any
of the following conditions are met:

* **A new migration PR is opened.** A per-PR B35
  refresh is required.
* **A migration PR is merged.** A post-merge B35
  refresh is required.
* **A new Phase 5X PR is opened or merged.** A per-
  phase B35 refresh is required.
* **A new B-track workstream is opened.** A per-
  workstream B35 refresh is required.

## 14. When to stop / escalate

The B-track stops and escalates when any of the
following conditions are met:

* **A migration PR is identified that changes a
  financial formula.** Agent B escalates to the
  user.
* **A migration PR is identified that changes an
  engine output.** Agent B escalates to the user.
* **A migration PR is identified that changes a
  model output.** Agent B escalates to the user.
* **A migration PR is identified that changes a
  fixture CSV.** Agent B escalates to the user.
* **A migration PR is identified that changes a
  schema / migration.** Agent B escalates to the
  user.
* **A migration PR is identified that changes a
  persistence / repository code.** Agent B
  escalates to the user.
* **A migration PR is identified that violates the
  B1 / B11 / B19 / B22 / B38 no-go claim list.**
  Agent B escalates to the user.
* **A migration PR is identified that is described
  as a customer reference.** Agent B escalates to
  the user.
* **A migration PR is identified that is described
  as a paid pilot authorization.** Agent B
  escalates to the user.
* **A migration PR is identified that is described
  as an external validation.** Agent B escalates to
  the user.
* **A migration PR is identified that is described
  as a production readiness or enterprise SaaS
  readiness claim.** Agent B escalates to the user.

## 15. What B40 is not

* B40 is not a code change. Agent B does not
  implement UI code.
* B40 is not external validation.
* B40 is not a paid pilot authorization.
* B40 is not a customer reference.
* B40 is not a production readiness claim.
* B40 is not an enterprise SaaS readiness claim.
* B40 is not a financial model validation.
* B40 is not a substitute for the user's migration
  decisions or the user's marketing decisions.
* B40 is not a substitute for the B35 / B36 / B37 /
  B38 / B39 governance artifacts.

## 16. Cross-references

* `reports/governance/ui3_line_item_grid_migration_governance_plan.json`
  (B40, machine-readable)
* `docs/governance/post_phase56_ui_governance_refresh.md`
  (B35)
* `docs/ui/phase57a_line_item_grid_visual_review.md` (B36)
* `docs/validation/ui_regression_evidence_matrix.md` (B37)
* `docs/commercial/ui demo_guardrail_refresh.md` (B38)
* `docs/pilot/controlled_pilot_ux_runbook.md` (B39)
* `docs/external_review/no_go_claims.md` (B1)
* `docs/commercial/no_go_claims_commercial_guardrail.md` (B11)
* `docs/commercial/demo_claims_checklist.json` (B19)
* `docs/commercial/qa_claims_matrix.json` (B22)
* `docs/governance/phase53_stop_go_checklist.md` (B33)
* `docs/roadmap/enterprise_saas_readiness_tracker.md` (B8)
* `docs/validation/validation_evidence_matrix.md` (B3)

---

*End of UI-3 LineItemGrid migration governance plan.*
