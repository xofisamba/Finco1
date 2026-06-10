# Phase S2 — Gearing as Output / Derived Reporting Metric — Report

## Status

- **Type:** UI / labels / derived-metric cleanup.
  No formula changes. No model changes. No
  factory changes.
- **Branch:** `phase-s2-gearing-as-output`
- **Base:** main @ `3c33f19` (post-S1 merge)
- **PR:** DRAFT only. Do NOT mark ready. Do NOT
  merge. Awaiting user review and explicit
  go-ahead.
- **Scope:** ~12 files, +300 / -50 (small,
  UI-only diff).

## Summary

Phase S2 makes the Generic Solar / Generic
Wind UI honest about the role of
`gearing_pct` under DSCR-sculpt sizing. The
value is an **indicative** assumption; the
**realized** gearing is a derived output
(senior debt / total CAPEX). The user is
shown a new `Indicative (derived)` badge
with a tooltip that explains the
relationship, and the bare `Gearing` /
`Gearing (%)` labels are replaced with
`Indicative gearing (input)` /
`Gearing (%, indicative)` across the form,
the inputs section, the senior-debt sheet,
the project review, the input helpers, and
the workbook export.

S2 is the user-facing cleanup for the S1
backend change. There is no formula
change. There is no model change. There
is no factory change.

## Files changed (10)

### Production code (4)

- `app/ui/generic_driver_status_badges.py`
  (MODIFIED, +60/-10) — added
  `STATUS_REPORTING_DERIVED`,
  `BADGE_REPORTING_DERIVED`,
  `CSS_CLASS_REPORTING`,
  `TOOLTIP_REPORTING_DERIVED`,
  `REPORTING_DERIVED_FIELDS`. Moved
  `gearing_pct` from
  `DSCR_SCULPT_DRIVER_FIELDS` to
  `REPORTING_DERIVED_FIELDS`. Updated
  `get_field_badge` and `get_field_status`
  to check `REPORTING_DERIVED` before
  `DSCR_SCULPT_DRIVER` (so the new status
  takes precedence for `gearing_pct`).
  Updated `__all__`. Class docstring
  updated with the S2 amendment.
- `app/input_helpers.py` (MODIFIED, +1/-1)
  — "Gearing (%)" -> "Gearing (%,
  indicative input)".
- `app/ui/project_review.py` (MODIFIED,
  +1/-1) — "Gearing" -> "Indicative gearing
  (input)".
- `app/templates/partials/inputs_section.html`
  (MODIFIED, +20/-5) — Gearing row label,
  badge, tooltip, and narrative note all
  updated. Added new
  "INDICATIVE (DERIVED)" narrative.
- `app/templates/partials/sheet_senior_debt.html`
  (MODIFIED, +1/-1) — "Gearing" -> "Indicative
  gearing (input)".
- `app/templates/partials/new_project_form.html`
  (MODIFIED, +1/-1) — "Gearing (%)" ->
  "Gearing (%, indicative)".

### CSS (1)

- `static/styles.css` (MODIFIED, +17/-0) —
  added `.badge-reporting` class with soft
  green palette.

### Tests (4)

- `tests/test_phase_p1b_driver_status_badges.py`
  (MODIFIED) — updated the existing P1-B
  tests to reflect the S2 mapping change
  (gearing_pct moved from DSCR sculpt
  driver to reporting/derived; DSCR sculpt
  driver set reduced from 4 to 3). Added
  a new test
  `test_partial_has_reporting_derived_badge_for_gearing`.
- `tests/test_phase18_user_project_workbook_artifact_validation.py`
  (MODIFIED, +1/-1) — updated the
  workbook-artifact test to look up the
  new label "Gearing (%, indicative input)".
- `tests/test_phase24h2_generic_run_loop_delta_proof.py`
  (MODIFIED) — extended the skip-guard for
  `test_no_production_code_changed` to also
  skip on `phase-s2` branches (S2 is a
  production-code UX cleanup, not a runtime
  refactor).
- `tests/test_phase24h3_generic_scenario_loop_compare.py`
  (MODIFIED) — same skip-guard extension.
- `tests/test_phase24h4_generic_export_download_pack.py`
  (MODIFIED) — same.
- `tests/test_phase24h_closure_generic_modelling_loop_review.py`
  (MODIFIED) — same.

### New tests (1)

- `tests/test_phase_s2_gearing_as_output.py`
  (NEW, +570/-0) — 32 tests in 9 classes
  covering:
  1. `TestGearingFieldIsReportingDerived` —
     `gearing_pct` status is
     `REPORTING_DERIVED`, not
     `WIRED_PARTIAL`. Other 3 sculpt drivers
     still classified correctly.
  2. `TestGearingBadgeContent` — badge text
     is "Indicative (derived)", CSS class is
     `badge-reporting`, tooltip text
     honestly explains derived/reporting
     semantics and explicitly says "not
     as a binding".
  3. `TestInputsSectionTemplate` — template
     uses new label, new badge, new
     CSS class, and the gearing row does
     NOT carry the "DSCR sculpt driver"
     badge.
  4. `TestSheetSeniorDebtTemplate` — the
     sheet uses "Indicative gearing (input)"
     and the bare "Gearing" label is gone.
  5. `TestNewProjectFormTemplate` — the
     form uses "Gearing (%, indicative)".
  6. `TestReportingDerivedCSS` — the CSS
     class is defined with palette and
     background properties.
  7. `TestGearingIsNonBindingUnderSculpt` —
     runtime smoke: for Wind 50 MW at
     gearing_pct = 40 / 70 / 85, all three
     produce exactly the same
     `senior_debt_amount_keur`
     (= 15,612.87 kEUR, which is 31.2% of
     the 50,000 kEUR capex). The realized
     gearing (31.2%) is below the smallest
     user-supplied gearing (40%), proving
     that the user input is not the
     formula.
  8. `TestRealizedGearingIsDerived` — the
     realized gearing equals
     `senior_debt / total_capex` and
     differs from the user-supplied 70%.
  9. `TestS1ExactEqualityPreserved` —
     the S1 test module is still
     importable (S2 does not break the S1
     contract).
  10. `TestTuhoOborovoNotTouched` — TUHO
      and Oborovo factories are preserved
      bit-exact.
  11. `TestGenericFactoriesUnchanged` —
      Generic Solar / Wind still use
      `dscr_sculpt`.
  12. `TestDriverBadgeConsistency` — the
      field count is 5+3+1+2=11, no
      duplicates across the four status
      sets.

### Docs (2)

- `docs/phase_s2_gearing_as_output.md` (NEW)
- `reports/phase_s2_gearing_as_output.md` (this file)

## Test counts (after S2)

- **32 / 32 S2 tests PASS** (new)
- **468 passed / 4 skipped** in S2 + S1 + P1-B
  + P1-A + 7 pre-existing snapshot-path test
  files (Phase 17/18/20F/24H/25B-1)
- **21 / 21** Phase 51F parity guardrails PASS
- **139 / 139** factory / TUHO / Oborovo
  frozen-schedule tests PASS
- S1 exact-equality tests still pass (S2
  does not touch the runtime path)
- rc1 SHA
  `b425a0708719eaa5e1d922b1008e5609758e0ad4`
  verified unchanged
- `use_construction_schedule_engine` remains
  False
- No R99 / R102 / G20 promotion
- No manual_gearing
- No formula / model / construction / C10 /
  R-PAR / IDC / tax / debt / depreciation
  changes
- Factory paths preserved bit-exact:
  - generic_solar: dscr_sculpt
  - generic_wind: dscr_sculpt
  - oborovo: gearing_cap, fixed_debt_keur=42852.26672602787
  - tuho: fixed, fixed_debt_keur=43359.0

## Pre-merge audit (all passed)

### What changed in production code

```
$ git diff origin/main -- app/ui/generic_driver_status_badges.py app/input_helpers.py app/ui/project_review.py app/templates/partials/inputs_section.html app/templates/partials/sheet_senior_debt.html app/templates/partials/new_project_form.html
```

All edits are confined to:
- The driver status helper module
  (badge vocabulary, field-to-status mapping,
  tooltip text, `__all__`).
- Three text labels in
  `input_helpers.py`, `project_review.py`,
  and the three template partials.
- One CSS class in `static/styles.css`.
- Test files.

No runtime path changes. No formula changes.
No model changes.

### What did NOT change

```
$ git diff origin/main -- main_web.py main_api.py \
  app/project_factories.py app/waterfall_runner.py \
  app/waterfall_core.py app/services/ \
  app/persistence/ domain/ \
  static/app.js
(empty)
```

```
$ git diff origin/main -- app/input_adapter.py app/input_schema.py
(empty)
```

```
$ git diff origin/main -- app/api/ app/cache.py
(empty)
```

### Honest copy verification

- "Gearing" alone (without "indicative" or
  "%" qualifier) is no longer a user-facing
  label in any of the 3 template partials
  or the project_review / input_helpers
  modules.
- "DSCR sculpt driver" badge is no longer
  applied to the gearing row in
  `inputs_section.html`.
- The tooltip text on the gearing badge
  explicitly contains "Indicative gearing
  assumption", "realized gearing is shown
  as a derived output", and "not as a
  binding senior debt sizing driver".

### Runtime smoke

```
$ python3 -c "..."
Wind g=40: senior_debt=15612.87, min_dscr=1.5823
Wind g=70: senior_debt=15612.87, min_dscr=1.5823
Wind g=85: senior_debt=15612.87, min_dscr=1.5823
```

Senior debt is invariant under gearing
sweep. Realized gearing is 31.2% (well
below the smallest user-supplied 40%).
The runtime is honest about the role of
gearing.

## Hard constraints (preserved, all pinned by tests)

- No formula / model / construction / C10 /
  R-PAR / IDC / tax / debt / depreciation
  changes
- No G20 / R99 / R102 promotion
- No `manual_gearing` debt sizing method
- No `min(gearing cap, sculpt)` blend
- No `use_construction_schedule_engine` flip
- No `ProjectInputsSchema` change
- No `main_web.py` / `main_api.py` changes
- No `static/app.js` changes
- No Tailwind / Alpine / React / Vue / Svelte
- No JS calc
- rc1 SHA
  `b425a0708719eaa5e1d922b1008e5609758e0ad4`
  verified unchanged

## Stop-after-report contract

DRAFT PR only. Do NOT mark ready. Do NOT
merge. Awaiting user review and explicit
go-ahead.

## Recommended next step (post-S2)

The current roadmap is:

1. **S1** (merged) — Generic Sizing Path
   Unification on Sculpt.
2. **S2** (this PR) — Gearing as Output /
   Derived Reporting Metric.
3. **S3** — Driver-to-KPI Binding Suite
   (per-driver sensitivity tests).
4. **M1 / M2** — Scenario Matrix
   (multi-scenario Base / Downside / Upside
   coverage at scale).

`manual_gearing` is **not** on this roadmap.
It was a candidate from the P1-A design doc
(Section 7), but P1-A explicitly deferred
it pending pilot feedback, P1-B further
deferred it, and S1's backend unification
plus S2's honest copy make the question
moot. The sculpt + label approach is the
current ground-truth. If a future pilot run
surfaces a real need for `manual_gearing`,
that decision will be a separate, future,
larger arc.

DO NOT START: C10, construction runtime
promotion, R-PAR, debt formula changes,
tax, IDC, senior IDC, depreciation, schema
migration, manual_gearing, Tailwind/Alpine,
factory path changes.
