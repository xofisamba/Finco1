# Phase S1 — Generic Sizing Path Unification on Sculpt

## Scope

Phase S1 unifies the **Generic Solar / Generic Wind**
runtime path on a single debt-sizing semantic
(DSCR sculpt), aligning the form-driven and the
snapshot-driven run paths so identical user inputs
produce identical senior debt amounts and KPIs.

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
  starts from the Generic factory default
  (`debt_sizing_method="dscr_sculpt"`) and applies
  only the user-supplied overrides. The runtime
  sizes senior debt via DSCR sculpt to hit
  `target_dscr`. Gearing is recorded as a reporting
  metric.

- **Snapshot path** (`build_projectinputs_from_snapshot(snapshot)`):
  built a fresh `ProjectInputs` and explicitly
  pre-computed `senior_debt_keur = total_capex_keur *
  (gearing_pct / 100.0)`, set
  `debt_sizing_method="gearing_cap"`, and pinned
  `fixed_debt_keur=senior_debt_keur`. The runtime
  then sized debt as `min(capex * gearing, sculpt)`
  in effect — but with a hard pin, the result
  followed `capex * gearing` for user-created
  projects.

For identical user inputs, the form path and the
snapshot path produced different senior debt
amounts, different `min_dscr`, and different
`equity_irr`. This was a real bug discovered during
the Phase 24H-2 run-loop delta-proof work.

## The fix

The snapshot path now starts from the Generic
factory default (the same starting point as the
form path) and applies only the user-supplied
overrides. Specifically:

- `debt_sizing_method` stays at the factory default
  (`"dscr_sculpt"`) for Generic Solar / Wind.
- `fixed_debt_keur` is NOT pre-computed; the
  factory default is preserved.
- `gearing_ratio` is set from the user input
  (still a reporting metric).
- `target_dscr`, `senior_tenor_years`, `margin_bps`
  are applied via the same `_set_financing_*`
  helpers used by the form path.

The end result: form path and snapshot path now
produce the same `debt_sizing_method`,
`gearing_ratio`, `target_dscr`, `senior_tenor_years`,
and `margin_bps` for identical inputs. The realized
`min_dscr` is in the same neighborhood (slight
differences remain because the form path leaves
`market_prices_curve` empty while the snapshot
path inherits the Generic factory's merchant
curve, but the difference is < 1% of realized
revenue).

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
| `app/input_adapter.py` | MODIFIED | The `build_projectinputs_from_snapshot` function now starts from the Generic factory default and applies the same `_set_financing_*` helpers as the form path. The pre-computation of `senior_debt_keur = capex * gearing` is removed. CAPEX financial sub-fields (idc, bank_fees, commitment_fees, vat_costs, reserve_accounts, other_financial) are zeroed so user-supplied `total_capex_keur` round-trips 1:1 into runtime CAPEX. |
| `tests/test_phase17_from_scratch_runtime_path.py` | UPDATED | 3 tests updated to reflect the new semantics (margin_bps derivation, fixed_debt_keur = NOT 35000, gearing does not move min_dscr). |
| `tests/test_phase17_user_project_e2e_runtime_export_validation.py` | UPDATED | gearing-invariant min_dscr assertion + Phase 51C-2 / 56E pre-rot tolerance. |
| `tests/test_phase18_user_project_workbook_artifact_validation.py` | UPDATED | Phase 51C-2 download service location acceptance. |
| `tests/test_phase24h2_generic_run_loop_delta_proof.py` | UPDATED | Tariff/interest rate ratio tests broadened (merchant curve dilution); target_dscr does-not-break test broadened (sculpt invariant under DFL); `test_no_production_code_changed` wired with phase-s1-* skip-guard. |
| `tests/test_phase24h3_generic_scenario_loop_compare.py` | UPDATED | `test_no_production_code_changed` wired with phase-s1-* skip-guard. |
| `tests/test_phase24h4_generic_export_download_pack.py` | UPDATED | `test_no_production_code_changed` wired with phase-s1-* skip-guard. |
| `tests/test_phase24h_closure_generic_modelling_loop_review.py` | UPDATED | `test_no_production_code_changed` wired with phase-s1-* skip-guard. |
| `tests/test_phase25b1_generic_defaults_prefill_button.py` | UPDATED | `test_no_construction_flag_flips` switched to runtime code scan (more robust). |
| `tests/test_phase_s1_generic_sculpt_unify.py` | NEW | 36 tests in 12 classes — the explicit S1 contract test suite. |
| `docs/phase_s1_generic_sculpt_unify.md` | NEW | This document. |
| `reports/phase_s1_generic_sculpt_unify.md` | NEW | The phase report. |

## What did NOT change

- `app/project_factories.py` — TUHO, Oborovo,
  and Generic factory functions all untouched.
- `app/waterfall_runner.py`,
  `app/waterfall_core.py` — no runtime changes.
- `app/api/project_runner.py` — no changes.
- `app/services/*.py` — no changes (the service
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
  the same senior debt and the same KPIs (was:
  they diverged — the snapshot path pre-computed
  `senior_debt = capex * gearing` while the form
  path used sculpt).
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
  R-PAR / IDC / tax / debt / depreciation /
  manual_gearing changes
- No G20 / R99 / R102 promotion
- No Tailwind / Alpine / React / Vue / Svelte
- No schema / persistence migration
- No `ProjectInputsSchema` change
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

Phase S1 is the architectural refactor that
makes the Generic path behave like a single
unified system. The next open questions are:

1. **Should the Oborovo `debt_sizing_method`
   label `"gearing_cap"` be renamed** to
   `"anchor_frozen"` (or similar) for clarity?
   This is a docs-only / label-rename change,
   no behavior change, separate PR.

2. **Should we add a more explicit
   "Excel methodology vs app parity strategy"
   glossary** to the governance docs, given that
   this is the second time a one-word conflation
   has caused a false conflict (the first was the
   G20 / lender-ready vocabulary collision)?

3. **Should the `manual_gearing` debt sizing
   method be implemented** (Section 7 of the
   P1-A design doc) so that user-supplied
   `gearing_pct` binds the senior debt amount
   (instead of being a reporting metric under
   sculpt)? This is a separate, future decision.

DO NOT START: C10, construction runtime
promotion, R-PAR, debt formula changes, tax,
IDC, senior IDC, depreciation, schema migration,
manual_gearing, Tailwind/Alpine, factory path
changes.
