# What Changed Delta Indicator Governance Review Pack

This file is the **What Changed Delta Indicator
governance review pack** for Phase 25B-3 (PR #586). It
is the B-track governance wrapper for the Runtime
"What Changed" delta indicator.

> **Agent B does not approve code correctness. Agent B
> does not validate persistence implementation. Agent
> B records governance / evidence requirements only.**
>
> **The "What Changed" panel is a UX explanation
> feature, not a valuation or investment tool. The
> deltas are explanatory indicators, not guaranteed
> accuracy claims. The "What Changed" panel does not
> provide investment advice. The "What Changed" panel
> does not provide guaranteed returns.**

---

## 1. PR #586 facts

* **PR number:** 586.
* **Title:** "Phase 25B-3 — Runtime \"What Changed\"
  Delta Indicator (UI + minimal metadata-persistence
  rotation)".
* **Status:** MERGED on main as
  `8042d0e8aadef7be05d97ccfde9f73ec86a954e5`.
* **Pre-merge head SHA:**
  `f6fd993412ac889f4bc827ac1f42bb8f391a6e78`.
* **Base SHA:** `92c5a33f03a3c49ad37f5b8ea9f0900c58d90920`.
* **Add/Del:** 2749/28. **Changed files:** 14.
* **Scope classification:** UI + minimal metadata-
  persistence rotation. NOT UI-only, NOT read-only in
  the strict sense. The UI panel itself is read-only
  (it never mutates input), but enabling it required
  a small behaviour change in
  `app/persistence/repository.py` (specifically
  `update_scenario_last_run_summary`).
* **Tests:** 84 new tests reported green in the PR
  body.

## 2. UI panel scope

The "What Changed" delta indicator is a runtime
explanation feature. After editing and re-running a
Generic Solar / Generic Wind scenario, the scenario-
version-history panel shows a compact "What changed
since previous run?" comparison.

The panel:

* Renders deltas across 10 KPIs: Project IRR, Equity
  IRR, Avg DSCR, Min DSCR, Revenue, OPEX, EBITDA,
  CAPEX, Distributions, Senior Debt.
* Is read-only: it never mutates the user's input.
* Is gated on `card.is_user_project`: factory
  projects (TUHO / Oborovo) do not render the panel
  even though the rotation happens for them too.
* Requires an EXPLORATORY banner for `generic_solar` /
  `generic_wind`. The banner makes it clear that the
  deltas are not Excel-parity validated.
* Has a helper module (`app/ui/what_changed.py`) that
  is pure: no DB, no I/O, no time, no random.

## 3. Minimal metadata-persistence rotation

`update_scenario_last_run_summary()` now stamps the
previous run summary into
`replay_metadata.previous_run_summary` before
overwriting `last_run_summary_json`:

| Run # | After-write `previous_run_summary` | After-write `second_last_run_summary` |
|---|---|---|
| 1 (first run) | absent | absent |
| 2 (second run) | run 1 summary | absent |
| 3 (third run) | run 2 summary | run 1 summary |
| 4+ (subsequent) | run N-1 summary | run N-2 summary |

Other `replay_metadata` keys are **preserved** across
writes. Corrupted or missing `replay_metadata` is
tolerated (rotation initialises a fresh dict). Factory
project run summary output is **byte-identical** to
the pre-Phase-25B-3 path.

## 4. `replay_metadata` optional keys

The following optional keys are added to the
`replay_metadata` JSON column:

* **`previous_run_summary`:** The previous run's
  summary. Used by the "What Changed" panel to compute
  deltas. Rotated on each new run.
* **`second_last_run_summary`:** The run before the
  previous run's summary. Used by the "What Changed"
  panel for multi-run comparison. Rotated on each new
  run.
* **`previous_run_at`:** An ISO timestamp of the
  previous run. Used by the "What Changed" panel to
  display when the previous run occurred.

## 5. No schema migration

Per PR #586, there is **no schema migration**:

* No new columns.
* No column type changes.
* No data backfill.
* The `replay_metadata` JSON column now carries two
  additional optional keys. The `replay_metadata`
  column itself is unchanged.

The backwards compatibility is preserved. Existing
rows in the `replay_metadata` column are valid
without migration.

## 6. Corrupted / missing metadata tolerance

The rotation is tolerant of corrupted or missing
metadata:

* If `replay_metadata` is `NULL`, the rotation
  initialises a fresh dict.
* If `replay_metadata` is corrupted (e.g., not a
  dict), the rotation initialises a fresh dict.
* If `replay_metadata` is missing a key (e.g.,
  `previous_run_summary`), the rotation initialises
  the key.

The tolerance is a defensive measure to ensure that
the rotation does not break existing flows.

## 7. Factory output byte-identical claim

The factory project run summary output is
**byte-identical** to the pre-Phase-25B-3 path. This
is internal test evidence (per PR #586); it is not
external validation. The byte-identical claim is
narrow: it applies to the factory project run summary
output only. It does not apply to the user project
output (which is the primary user of the "What
Changed" panel).

## 8. 10 KPI delta list

The "What Changed" panel computes deltas across the
following 10 KPIs:

* **Project IRR** (pct).
* **Equity IRR** (pct).
* **Avg DSCR** (x).
* **Min DSCR** (x).
* **Revenue** (kEUR).
* **OPEX** (kEUR).
* **EBITDA** (kEUR).
* **CAPEX** (kEUR).
* **Distributions** (kEUR).
* **Senior Debt** (kEUR).

The deltas are computed via subtraction and
percentage (per the helper module). The deltas are
explanatory; they are not guaranteed accuracy claims.

## 9. Exploratory banner requirement

For `generic_solar` / `generic_wind`, an EXPLORATORY
banner is required. The banner makes it clear that
the deltas are not Excel-parity validated.

The banner is required for the user-project gating
to be considered correct. Without the banner, the
generic deltas could be misread as Excel-parity
validated.

## 10. User-project gating

The "What Changed" panel is gated on
`card.is_user_project`. Factory projects (TUHO /
Oborovo) do not render the panel even though the
rotation happens for them too.

The gating is a safety measure to ensure that the
panel is not displayed for projects that should not
be subject to the "What Changed" UI. The rotation
still happens for factory projects (to maintain byte-
identical output), but the panel is suppressed.

## 11. Factory-project safety

The factory project run summary output is byte-
identical to the pre-Phase-25B-3 path. The factory
output safety is preserved.

The factory output safety is verified by internal
tests (per PR #586); it is not external validation.

## 12. No model formula change

Per PR #586, there are no model formula changes:

* No tax / debt / depreciation / IDC changes.
* No construction / C10 / R-PAR promotion.
* No senior IDC changes.
* No new financial formulas.
* The helper module only does subtraction and
  percentage.

The financial model is unchanged.

## 13. No investment advice

The "What Changed" panel does **not** provide
investment advice. The deltas are explanatory; they
are not investment recommendations.

The "What Changed" panel is a UX explanation feature,
not a valuation or investment tool.

## 14. No guaranteed returns

The "What Changed" panel does **not** provide
guaranteed returns. The deltas are explanatory; they
are not guaranteed accuracy claims.

The "What Changed" panel is a UX explanation feature,
not a returns tool.

## 15. What must be visually reviewed

The following items must be visually reviewed by the
user or the designated reviewer:

* The "What Changed" panel renders correctly for a
  Generic Solar scenario with at least 2 runs.
* The "What Changed" panel renders correctly for a
  Generic Wind scenario with at least 2 runs.
* The "What Changed" panel does NOT render for a
  factory project (TUHO / Oborovo).
* The exploratory banner is visible for Generic Solar
  / Generic Wind scenarios.
* The 10 KPIs are displayed with the correct units
  (pct, x, kEUR).
* The delta values are computed correctly (subtraction
  + percentage).
* The panel is accessible (keyboard navigation, screen
  reader).
* The panel is responsive (desktop, tablet, mobile).

## 16. What must be regression-tested

The following items must be regression-tested:

* The factory project run summary output is byte-
  identical to the pre-Phase-25B-3 path.
* The user project run summary output includes the
  new "What Changed" data.
* The `replay_metadata` rotation is correct for runs
  1, 2, 3, 4+.
* Corrupted `replay_metadata` is tolerated.
* Missing `replay_metadata` is tolerated.
* Other `replay_metadata` keys are preserved across
  writes.
* The exploratory banner is rendered for Generic
  Solar / Generic Wind scenarios.
* The panel is gated on `card.is_user_project`.
* The parity-core lock is unchanged for TUHO and
  Oborovo.
* No model output drift for any project.

## 17. What should block future pilot / demo if broken

The following items should block the future pilot or
demo if broken:

* The factory project run summary output is NOT byte-
  identical to the pre-Phase-25B-3 path. This is a
  hard blocker.
* The user project run summary output is corrupted
  (e.g., NaN, infinity, missing fields). This is a
  hard blocker.
* The exploratory banner is missing for Generic Solar
  / Generic Wind scenarios. This is a hard blocker.
* The panel renders for a factory project (TUHO /
  Oborovo). This is a hard blocker.
* The parity-core lock is broken for TUHO or Oborovo.
  This is a hard blocker.
* Any model output drift is detected. This is a hard
  blocker.
* Any schema migration is performed without explicit
  governance approval. This is a hard blocker.
* Any new financial formula is introduced without
  explicit governance approval. This is a hard
  blocker.

## 18. What B43 explicitly does not claim

* B43 does not claim that the "What Changed" panel is
  a valuation tool. The panel is a UX explanation
  feature, not a valuation tool.
* B43 does not claim that the deltas are guaranteed
  accuracy claims. The deltas are explanatory; they
  are not guaranteed accuracy claims.
* B43 does not claim that the "What Changed" panel
  provides investment advice. The panel does not
  provide investment advice.
* B43 does not claim that the "What Changed" panel
  provides guaranteed returns. The panel does not
  provide guaranteed returns.
* B43 does not claim that the "What Changed" panel
  is Excel-parity validated for Generic Solar /
  Generic Wind. The panel is exploratory for Generic
  Solar / Generic Wind; the banner is required.
* B43 does not claim that the factory project run
  summary output is "external validation". The
  factory output byte-identical claim is internal
  test evidence, not external validation.
* B43 does not claim that the "What Changed" panel
  authorizes the paid pilot. The paid pilot is not
  authorized.
* B43 does not claim that Agent B has performed a
  visual review of the "What Changed" panel. Agent B
  records the governance / evidence requirements
  only.

## 19. Cross-references

* `reports/governance/what_changed_delta_indicator_governance_review.json`
  (B43, machine-readable)
* `docs/governance/post_phase25b_generic_modelling_governance_refresh.md`
  (B41)
* `docs/validation/generic_scenario_loop_evidence_matrix.md`
  (B42)
* `docs/commercial/generic_solar_wind_demo_guardrail_refresh.md`
  (B44)
* `docs/pilot/controlled_generic_scenario_pilot_runbook.md`
  (B45)
* `docs/validation/scenario_compare_export_evidence_register.md`
  (B46)
* `docs/governance/post25b_readiness_delta_refresh_cadence.md`
  (B47)
* `docs/external_review/no_go_claims.md` (B1)
* `docs/commercial/no_go_claims_commercial_guardrail.md` (B11)
* `docs/commercial/demo_claims_checklist.json` (B19)
* `docs/commercial/qa_claims_matrix.json` (B22)

---

*End of What Changed Delta Indicator governance
review pack.*
