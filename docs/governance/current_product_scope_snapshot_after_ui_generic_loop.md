# Current Product Scope Snapshot after UI + Generic Loop

This file is the **current product scope snapshot**
after the UI governance arc (B35-B40, PR #489) and
the Generic Modelling Loop arc (B41-B47, PR #588).

> **This snapshot describes the current state of the
> product at the time of B48 authoring. It is not
> approval. It is not external validation. It is not
> bankability. It is not a paid pilot authorization.**
>
> **Internal pilot readiness does not equal paid
> pilot readiness. External reviewer evidence index
> does not equal external validation.**

---

## 1. What the app currently does

The Finco1 app currently supports:

* **Project creation flow** (factory, user, generic).
* **Inputs editing** (per-scenario input fields).
* **Run / save / load** of scenario runs.
* **Scenario compare** (2-way, 3-way, 4-way).
* **Multi-Compare Picker** (UI / navigation only).
* **Export / download pack** (Generic scenarios).
* **Runtime "What Changed" Delta Indicator** (UI +
  minimal metadata-persistence rotation, Phase 25B-3
  / PR #586).
* **Scenario version history** with rotation
  (`replay_metadata.previous_run_summary`,
  `second_last_run_summary`, `previous_run_at`).
* **Runtime summary, validation summary, banner
  context** wiring (Phase 55E-55G).
* **CAPEX summary grid** rendered via the shared
  LineItemGrid partial/macro (Phase 57A / PR #487).
* **Route-render smoke + index context-contract
  tests** (Phase 57-pre / PR #486).
* **New Project form** (Phase 56C / PR #480).
* **Help section** (Phase 56B / PR #477).
* **Project switcher** (Phase 56E / PR #482).
* **State banner hierarchy** (Phase 56F / PR #483).
* **UX cleanup closeout and visual review pack**
  (Phase 56G / PR #484).
* **Generic Defaults Prefill Button** (Phase 25B-1
  / PR #583).
* **3-Way / 4-Way Generic Scenario Compare** (Phase
  25B-2 / PR #584).

## 2. What is model-backed

The following are model-backed (i.e., the underlying
financial model computes the values):

* **Project IRR, Equity IRR** (pct).
* **Avg DSCR, Min DSCR** (x).
* **Revenue, OPEX, EBITDA, CAPEX, Distributions,
  Senior Debt** (kEUR).
* **All factory / reference project scenarios**
  (TUHO, Oborovo).
* **The factory project run summary output is byte-
  identical** to the pre-Phase-25B-3 path.
* **The parity-core lock** is preserved for TUHO and
  Oborovo.

## 3. What is UI-backed only

The following are UI-backed only (i.e., the underlying
state is unchanged by the UI):

* **The "What Changed" panel** is a UI-backed
  indicator. The deltas are computed via subtraction
  and percentage on the existing run summary data.
* **The scenario compare** is UI-backed. The compare
  is a side-by-side view of existing run summaries.
* **The Multi-Compare Picker** is UI / navigation
  only. The picker selects scenarios for the compare.
* **The CAPEX summary grid (LineItemGrid)** is a UI
  refactor. The underlying financial model is
  unchanged.
* **The state banner hierarchy** is a UI refactor.
  The underlying state is unchanged.
* **The Help section** is a UI refactor. The
  underlying instructions are unchanged.
* **The New Project form** is a UI refactor. The
  required fields and validation are unchanged.
* **The project switcher** is a UI refactor. The
  project selection logic is unchanged.

## 4. What is governance-backed only

The following are governance-backed only (i.e., the
B-track governance is the primary record):

* **The no-go claim list** (B1, B11, B19, B22, B38,
  B44).
* **The controlled pilot runbook** (B18, B39, B45).
* **The pilot issue log process** (B20).
* **The pilot user acknowledgement** (B21).
* **The demo / investor / partner QA guardrail**
  (B22).
* **The reviewer question bank** (B23).
* **The validation evidence matrix** (B3).
* **The UI regression evidence matrix** (B37).
* **The generic scenario loop evidence matrix**
  (B42).
* **The scenario compare / export / download
  evidence register** (B46).
* **The next refresh cadence** (B34, B47).

## 5. What is still experimental

The following are still experimental:

* **Generic Solar** — exploratory and unvalidated.
  Generic Solar defaults are illustrative until
  validated by reference models. The exploratory
  banner is required.
* **Generic Wind** — exploratory and unvalidated.
  Generic Wind defaults are illustrative until
  validated by reference models. The exploratory
  banner is required.
* **The Multi-Compare Picker** — UI / navigation
  only. The picker is the entry point for the multi-
  compare flow; the underlying compare is internal
  functionality.
* **The "What Changed" panel** — explanatory UI
  indicator. The deltas are explanatory, not
  guaranteed accuracy claims.

## 6. What is explicitly not validated

The following are explicitly not validated:

* **Generic Solar is not Excel-parity validated**
  against a reference solar model.
* **Generic Wind is not Excel-parity validated**
  against a reference wind model.
* **Generic Solar / Wind defaults are not market-
  validated assumptions.**
* **External validation has not occurred.**
* **No reference solar model** is available for
  Generic Solar output validation.
* **No reference wind model** is available for
  Generic Wind output validation.
* **No controlled pilot run with real users** has
  occurred.
* **No user visual review** of the "What Changed"
  panel, the compare panel, the multi-compare picker,
  or the export / download pack has been performed.
* **No paid pilot has been authorized.**
* **No customer reference has been made.**

## 7. Current UI capabilities

The current UI capabilities include:

* **Index page** with runtime summary, validation
  summary, and banner context.
* **Inputs tab** with per-scenario input editing.
* **Audit / summary** with validation summary.
* **CAPEX summary grid** (LineItemGrid).
* **Scenario compare** (2-way, 3-way, 4-way).
* **Multi-Compare Picker**.
* **Export / download pack** (Generic scenarios).
* **What Changed panel** (read-only UI panel; 10
  KPIs).
* **New Project form** (simplified).
* **Help section** (dedicated section).
* **Project switcher** (simplified).
* **State banner hierarchy** (polished).

## 8. Current Generic Solar / Wind capabilities

The current Generic Solar / Wind capabilities include:

* **Generic project creation**.
* **Generic defaults prefill** (the canonical
  reference project defaults are seeded into the
  Generic project; the defaults are illustrative
  until validated by reference models).
* **Edit → save → run loop** (the Generic Modelling
  Loop foundation).
* **Output delta proof** (the proof that editing a
  scenario input changes the corresponding scenario
  output).
* **Scenario compare** (2-way, 3-way, 4-way).
* **Multi-Compare Picker** (UI / navigation only).
* **Export / download pack** (internal artifact
  generation; exploratory banner required).
* **What Changed panel** (read-only UI panel; 10
  KPIs; exploratory banner required for Generic
  Solar / Wind).

## 9. Current scenario workflow

The current scenario workflow includes:

* Create or select a scenario.
* Edit scenario inputs.
* Save the scenario.
* Run the scenario.
* View the runtime summary, validation summary, and
  banner context.
* View the scenario version history.
* View the "What Changed" deltas (if at least 2
  runs; for Generic Solar / Wind, the exploratory
  banner is required).
* Compare 2, 3, or 4 scenarios.
* Export / download the scenario artifacts (for
  Generic scenarios; exploratory banner required).

## 10. Current compare / export / download workflow

The current compare / export / download workflow
includes:

* **Compare 2-way** (Phase 24-H-3 + Phase 25B-2).
* **Compare 3-way / 4-way** (Phase 25B-2 / PR #584).
* **Multi-Compare Picker** (Phase 25B-2.1 / PR
  #585).
* **Export / download pack** (Phase 24-H-4).
* The compare is a side-by-side view of existing run
  summaries. The compare is internal functionality,
  not model validation.
* The export / download pack is internal artifact
  generation, not bankability.

## 11. Current What Changed workflow

The current What Changed workflow includes:

* Edit a scenario, save it, run it.
* Edit the scenario again, save it, run it again.
* View the "What Changed" deltas (10 KPIs: Project
  IRR, Equity IRR, Avg DSCR, Min DSCR, Revenue,
  OPEX, EBITDA, CAPEX, Distributions, Senior Debt).
* For `generic_solar` / `generic_wind`, the
  exploratory banner is required.
* The panel is gated on `card.is_user_project`;
  factory projects do not render the panel.
* The factory project run summary output is byte-
  identical to the pre-Phase-25B-3 path.

## 12. Current persistence / saved scenario state

The current persistence / saved scenario state
includes:

* **Scenario inputs** are persisted.
* **Scenario run summaries** are persisted via
  `last_run_summary_json`.
* **`replay_metadata`** is persisted. The
  `replay_metadata` JSON column now carries two
  additional optional keys
  (`previous_run_summary`, `second_last_run_summary`)
  plus an ISO timestamp (`previous_run_at`).
* **The persistence rotation** in
  `update_scenario_last_run_summary` is minimal and
  scoped. Other `replay_metadata` keys are preserved
  across writes. Corrupted / missing `replay_metadata`
  is tolerated.
* **No schema migration** in Phase 25B-3.

## 13. Current factory / reference project state

The current factory / reference project state
includes:

* **TUHO and Oborovo** are the canonical reference
  projects.
* **The factory project run summary output is byte-
  identical** to the pre-Phase-25B-3 path.
* **The "What Changed" panel does not render** for
  factory projects (TUHO / Oborovo) — the panel is
  gated on `card.is_user_project`.
* **The factory output safety is preserved** (the
  rotation happens for factory projects too, to
  maintain byte-identical output, but the panel is
  suppressed).
* **The parity-core lock** is preserved for TUHO and
  Oborovo.

## 14. Current no-go boundaries

The current no-go boundaries include:

* **G20 remains BLOCKED.**
* **R99 remains NOT APPROVED.**
* **R102 remains NOT APPROVED.**
* **`partial_pay_sweep` is not promoted.**
* **Flat / min DSCR sculpting is not promoted.**
* **Generic Solar remains exploratory and
  unvalidated.**
* **Generic Wind remains exploratory and
  unvalidated.**
* **Generic assumptions are illustrative until
  validated by reference models.**
* **The scenario compare is internal functionality,
  not model validation.**
* **The export / download pack is internal artifact
  generation, not bankability.**
* **The "What Changed" deltas are explanatory, not
  guaranteed accuracy claims.**
* **No external validation has occurred.**
* **No paid pilot has been authorized.**
* **No customer reference has been made.**
* **No production readiness is claimed.**
* **No enterprise SaaS readiness is claimed.**
* **No lender / bank / audit / certification /
  regulatory / SaaS claim is made.**
* **No investment advice or guaranteed returns is
  claimed.**

## 15. Distinctions (must be maintained)

* **TUHO / Oborovo** are reference or factory flows.
  The factory output is byte-identical. The "What
  Changed" panel does not render.
* **Generic Solar / Generic Wind** are exploratory
  flows. The exploratory banner is required. The
  deltas are explanatory, not guaranteed accuracy
  claims.
* **Internal evidence** is evidence that is collected
  internally (e.g., automated tests, internal
  documentation, internal review).
* **External validation** is a separate workstream.
  External validation has not occurred.
* **Internal pilot readiness** is the readiness of
  the internal controlled pilot. Internal pilot
  readiness does not equal paid pilot readiness.
* **Paid pilot readiness** is the readiness of the
  paid pilot. Paid pilot is not authorized.
* **Enterprise SaaS readiness** is the readiness of
  the enterprise SaaS rollout. Enterprise SaaS
  readiness is not claimed.

## 16. What B48 is not

* B48 is not a code change. Agent B does not
  implement code.
* B48 is not external validation.
* B48 is not a paid pilot authorization.
* B48 is not a customer reference.
* B48 is not a production readiness claim.
* B48 is not an enterprise SaaS readiness claim.
* B48 is not a financial model validation.
* B48 is not a substitute for the user's decisions
  about pilot, marketing, or product.

## 17. Cross-references

* `reports/governance/current_product_scope_snapshot_after_ui_generic_loop.json`
  (B48, machine-readable)
* `docs/pilot/internal_pilot_readiness_matrix.md` (B49)
* `docs/review/external_reviewer_evidence_index_refresh.md`
  (B50)
* `docs/governance/known_limitations_no_go_claims_consolidation.md`
  (B51)
* `docs/pilot/controlled_pilot_data_room_index.md` (B52)
* `docs/governance/next_validation_roadmap_after_generic_loop.md`
  (B53)
* `docs/governance/post_phase56_ui_governance_refresh.md`
  (B35)
* `docs/governance/post_phase25b_generic_modelling_governance_refresh.md`
  (B41)

---

*End of current product scope snapshot after UI +
Generic Loop.*
