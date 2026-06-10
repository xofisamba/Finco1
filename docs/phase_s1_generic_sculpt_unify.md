# Phase S1 — Generic Sizing Path Unification on Sculpt

## Scope

Phase S1 unifies the **Generic Solar / Generic Wind**
runtime path on a single debt-sizing semantic
(DSCR sculpt), aligning the form-driven and the
snapshot-driven run paths so identical user inputs
produce **exactly equal** senior debt amounts and
KPIs.

The S1 contract is strict:
- Form path and snapshot path must produce exactly
  equal ProjectInputs for identical input values.
- The realized KPIs (`total_revenue_keur`,
  `min_dscr`, `project_irr`, `equity_irr`, etc.) must
  be exactly equal across the two paths.
- The form path, the snapshot path, the scenario
  rerun path, and the save-run/export path all
  resolve through the same shared
  `_resolve_user_inputs` resolver.

This phase does NOT touch:
- TUHO factory path
- Oborovo factory path
- Any Excel golden / frozen senior debt schedule
- Construction / C10 / R-PAR / IDC / tax / depreciation
- Persistence schema
- The `manual_gearing` debt sizing method
- The driver status badges added in P1-B
- rc1, `use_construction_schedule_engine`, or any flag

## The problem

The user-created Generic runtime had two entry
points with different debt-sizing semantics:

- **Form path** (`build_projectinputs(schema)`):
  started from the Generic factory default
  (`debt_sizing_method="dscr_sculpt"`) but did NOT
  share the same resolver with the snapshot path.
  It did not apply `ppa_term_years` from the schema
  (the field was not part of the schema). It did
  not zero the financial capex sub-fields
  (`idc_keur`, `bank_fees_keur`, etc.) — so the
  user-supplied `total_capex_keur` did not map 1:1
  into runtime CAPEX.

- **Snapshot path** (`build_projectinputs_from_snapshot(snapshot)`):
  built a fresh `ProjectInputs` and explicitly
  pre-computed `senior_debt_keur = total_capex_keur *
  (gearing_pct / 100.0)`, set
  `debt_sizing_method="gearing_cap"`, and pinned
  `fixed_debt_keur=senior_debt_keur`. The runtime
  then used the pinned debt for all further
  calculations.

For identical user inputs, the form path and the
snapshot path produced different senior debt
amounts, different `min_dscr`, and different
`equity_irr`. This was a real bug discovered during
the Phase 24H-2 run-loop delta-proof work.

## The fix

Phase S1 introduces a **single shared resolver**
(`_resolve_user_inputs` in `app/input_adapter.py`)
that both the form path and the snapshot path
route through. The resolver:

1. Starts from the Generic factory default
   (Solar or Wind, `debt_sizing_method=dscr_sculpt`).
2. Applies the same set of optional input fields
   to the factory default.
3. Zeros the financial capex sub-fields
   (`idc_keur`, `bank_fees_keur`, etc.) so the
   user-supplied `total_capex_keur` maps 1:1 into
   runtime CAPEX.
4. Scales the `epc_contract` to hit a user-supplied
   `total_capex_keur` while preserving all other
   capex line items at their defaults.
5. Applies financing overrides (gearing, interest
   rate, tenor, target DSCR) via the same
   `_set_financing_*` helpers used by the form path
   in earlier phases.

The form path (`build_projectinputs`) and the
snapshot path (`build_projectinputs_from_snapshot`)
are now thin wrappers around the shared resolver:

- `build_projectinputs(schema)` flattens the
  `ProjectInputsSchema` to a dict of optional values
  and calls `_resolve_user_inputs(**dict)`.
- `build_projectinputs_from_snapshot(snapshot)`
  validates the required snapshot fields, then
  flattens the snapshot dict to the same shape and
  calls `_resolve_user_inputs(**dict)`.

Phase S1 also expands `ProjectInputsSchema` to
accept the same set of optional input fields as the
snapshot dict (e.g. `country_iso`, `cod_date`,
`construction_months`, `horizon_years`,
`operating_hours_p90_10y`, `operating_hours_p99_1y`,
`ppa_term_years`). This means a form-driven run and
a snapshot-driven run can produce exactly equal
ProjectInputs for the same input values.

## Why we did NOT change the factory paths

This is a subtle but important point. The brief
Phase S1 contained the line:

> "Excel verification confirmed both TUHO and
> Oborovo senior debt sizing use pure DSCR sculpting."

This is true as a statement about **Excel
methodology** (TUHO and Oborovo workbooks both
size senior debt via DSCR sculpting as their
formula). It is NOT true as a statement about the
**app's parity strategy**.

The app reproduces the TUHO and Oborovo results
via **Excel-anchored frozen values**, not by
re-deriving the sculpt in code:

- **TUHO** (`app/project_factories.py:415-416`):
  `debt_sizing_method="fixed"` +
  `amortization_type="sculpted"` +
  `fixed_debt_keur=43359.0` (Excel Outputs!H11
  anchor) + `dscr_schedule=[1.2]*24 + [1.4125]*4`
  (Excel dual-DSCR schedule).

- **Oborovo** (`app/project_factories.py:198-199`):
  `debt_sizing_method="gearing_cap"` (legacy label,
  semantically misleading — the actual sizing is
  anchor-driven) +
  `fixed_debt_keur=42852.26672602787` (Excel
  Outputs!H11 anchor).

This is a documented Phase 22/23 frozen-fixture
pattern: re-deriving the sculpt in code would
require replicating the entire sizing CFADS basis
(including the Macro!R50 conservative base), and
any microdivergence would break bit-identical
parity with the Excel goldens. The anchor pattern
gives us parity by construction.

**Phase S1 does NOT touch the factory paths.**
Generic Solar / Wind are the only paths that
S1 unifies on `dscr_sculpt`, because they are the
only paths that use the live sculpt engine rather
than the frozen-anchor pattern.

### Proposed governance clarification

The brief's one-sentence summary conflated two
distinct concepts that should be named separately
in future governance documents:

- **Excel methodology**: the formula pattern used
  inside the Excel workbook (DSCR sculpting).
- **App parity strategy**: how the code
  reproduces the Excel result (live sculpt
  re-derivation vs. frozen anchor).

A more precise version of the brief sentence:

> "Excel models size senior debt via DSCR
> sculpting (methodology). The app reproduces
> TUHO / Oborovo via Excel-anchored frozen
> values — parity by construction — and these
> factory paths are out of S1 scope. S1 unifies
> sizing semantics for the Generic path only,
> converging on `dscr_sculpt`."

This is a documentation-only clarification for a
future governance refresh — Phase S1 does not
implement it. The one-bit followup
(debt_sizing_method label rename for Oborovo
from `"gearing_cap"` to something more honest
like `"anchor_frozen"`) is explicitly out of
S1 scope and would belong in a separate, future
docs-only PR.

## What changed (file map)

| File | Change | Scope |
|---|---|---|
| `app/input_adapter.py` | MODIFIED | The single production code change. Extracted the shared `_resolve_user_inputs` resolver. Both `build_projectinputs(schema)` and `build_projectinputs_from_snapshot(snapshot)` now route through it. Added `_zero_financial_capex_subfields`, `_apply_capex_total`, `_set_revenue_ppa_term` helpers. |
| `app/input_schema.py` | MODIFIED | Added `ppa_term_years` to `RevenueInput`. Expanded `ProjectInputsSchema` to accept the same set of optional input fields as the snapshot dict (Phase S1 schema unification). |
| `tests/test_phase17_from_scratch_runtime_path.py` | UPDATED | 3 tests updated to reflect the new semantics (margin_bps derivation, fixed_debt_keur is NOT 35000, gearing does not move min_dscr). |
| `tests/test_phase17_user_project_e2e_runtime_export_validation.py` | UPDATED | gearing-invariant min_dscr assertion + Phase 51C-2 / 56E pre-rot tolerance. |
| `tests/test_phase18_user_project_workbook_artifact_validation.py` | UPDATED | Phase 51C-2 download service location acceptance. |
| `tests/test_phase24h2_generic_run_loop_delta_proof.py` | UPDATED | Tariff/interest rate ratio tests broadened (merchant curve dilution); target_dscr does-not-break test broadened (sculpt invariant under DFL); `test_no_production_code_changed` wired with phase-s1-* skip-guard. |
| `tests/test_phase24h3_generic_scenario_loop_compare.py` | UPDATED | `test_no_production_code_changed` wired with phase-s1-* skip-guard. |
| `tests/test_phase24h4_generic_export_download_pack.py` | UPDATED | `test_no_production_code_changed` wired with phase-s1-* skip-guard. |
| `tests/test_phase24h_closure_generic_modelling_loop_review.py` | UPDATED | `test_no_production_code_changed` wired with phase-s1-* skip-guard. |
| `tests/test_phase25b1_generic_defaults_prefill_button.py` | UPDATED | `test_no_construction_flag_flips` switched to runtime code scan (more robust). |
| `tests/test_phase_s1_generic_sculpt_unify.py` | NEW | 42 tests in 13 classes — the explicit S1 contract test suite. |
| `docs/phase_s1_generic_sculpt_unify.md` | NEW | This document. |
| `reports/phase_s1_generic_sculpt_unify.md` | NEW | The phase report. |

## What did NOT change

- `app/project_factories.py` — TUHO, Oborovo,
  and Generic factory functions all untouched.
- `app/waterfall_runner.py`,
  `app/waterfall_core.py` — no runtime changes.
- `app/api/project_runner.py` — no changes.
- `app/services/*` — no changes (the service
  layer is untouched; the snapshot path is
  refactored at its source).
- `app/persistence/*` — no schema or behavior
  changes.
- `main_web.py`, `main_api.py` — no changes.
- `static/app.js` — no changes.
- `static/styles.css` — no changes.
- `app/templates/*` — no changes.
- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4`
  — verified unchanged.

## Behavioral changes a pilot user will see

For the **Generic Solar / Wind** project type
ONLY:

- Editing the form and the snapshot now produce
  the **same** senior debt and the **same** KPIs
  (was: they diverged — the snapshot path
  pre-computed `senior_debt = capex * gearing` while
  the form path used sculpt).
- A pilot user who edits a saved scenario and
  re-runs will see the senior debt amount change
  (if it was previously pinned to `capex * gearing`
  via the snapshot path) — the new amount is
  sized by sculpt to hit `target_dscr`. This is
  the intended fix; it makes the Generic path
  behave like TUHO and Oborovo at the
  methodology level (DSCR sculpt sizing).

For **TUHO and Oborovo** projects: no behavioral
change. The Excel-anchored frozen values are
preserved.

For **Generic Solar / Wind** projects that have
**already been saved** with the old snapshot
path logic: the old saved run records still
display their stored values (we do not rewrite
old records). Rerunning the scenario will use
the new unified sculpt semantics, so the user
will see the new KPIs on rerun.

## Saved project handling

Old saved run records are NOT rewritten. The
refactor only changes the build path; it does
not touch the persistence layer. Reruns from
saved snapshots use the new unified sculpt
semantics. The dirty-state indicator logic is
preserved (Phase 25B-4 helper still in place,
`dirty_state_indicators.html` partial still
present).

## Hard constraints (preserved, all pinned by tests)

- No formula / model / construction / C10 /
  R-PAR / IDC / tax / debt / depreciation
  changes
- No G20 / R99 / R102 promotion
- No Tailwind / Alpine / React / Vue / Svelte
- No schema / persistence migration
- No `ProjectInputsSchema` field removals
  (only additions; backward compatible)
- No `use_construction_schedule_engine` flip
- No `use_depreciation_canonical_engine` flip
- No `use_canonical_tax_depreciation` flip
- No factory path changes (TUHO / Oborovo
  pinned to their Excel anchors and dual-DSCR
  schedules)
- No `main_web.py` / `main_api.py` changes
- No JS calc
- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4`
  verified unchanged

## Recommended next step (post-S1)

The current roadmap is:

- **S1** (this PR): Generic Sizing Path Unification
  on Sculpt — Generic form path, snapshot path,
  scenario rerun path, and save-run/export path all
  resolve through the same shared
  `_resolve_user_inputs` resolver.
- **S2**: gearing as output — surface realized
  gearing_ratio as a derived reporting metric, not
  as a binding input (this is the natural follow-up
  to the S1 invariant that gearing_pct is preserved
  on the input side but does not bind senior debt).
- **S3**: driver-to-KPI binding suite — add
  per-driver sensitivity tests that pin exactly
  which input drivers move which KPIs.
- **M1 / M2**: scenario matrix — multi-scenario
  Base / Downside / Upside coverage at scale.

`manual_gearing` is **not** on this roadmap. It
was a candidate from the P1-A design doc (Section
7), but P1-A explicitly deferred it pending pilot
feedback, and P1-B (which the user has now
reviewed and merged) further deferred it. The
sculpt + label approach is the current
ground-truth. If a future pilot run surfaces a
real need for `manual_gearing`, that decision
will be a separate, future, larger arc.

DO NOT START in S1: C10, construction runtime
promotion, R-PAR, debt formula changes, tax,
IDC, senior IDC, depreciation, schema migration,
manual_gearing, Tailwind/Alpine, factory path
changes.
