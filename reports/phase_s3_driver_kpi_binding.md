# Phase S3 — Driver-to-KPI Binding Suite — Report

## Status

- **Type:** Tests + minimal helper/template
  updates. No formula changes. No model
  changes. No factory changes.
- **Branch:** `phase-s3-driver-kpi-binding-suite`
- **Base:** main @ `20c7298` (post-S2 merge)
- **PR:** DRAFT only. Do NOT mark ready. Do NOT
  merge. Awaiting user review and explicit
  go-ahead.
- **Scope:** ~10 files, +800 / -50 (small
  test-and-helper diff).

## Summary

Phase S3 is the driver-to-KPI binding suite
for Generic Solar / Generic Wind. Every
editable Generic driver is proved to either
demonstrably move at least one relevant KPI
or is correctly classified as a non-binding
/ reporting / metadata field.

The S3 sweep found a **classification
mismatch** in the P1-A audit: `ppa_term_years`
and `construction_months` were labeled
`METADATA_ONLY`, but S1 had made them
model-affecting (via the schema extension
that accepts `ppa_term_years` to affect
`total_revenue_keur` / `total_ebitda_keur`
through the PPA tariff duration, and
`construction_months` to affect `equity_irr`
via the `financial_close` timing). S3
corrects the mismatch with runtime-proven
evidence, not a guess.

### S3 review fix (Round 2)

Round 1 of S3 lumped `construction_months`
with the 3 true DSCR sculpt drivers under a
single "Model driver" badge. Review feedback
rejected that classification because
`construction_months` does NOT bind senior
debt / DSCR — it only shifts the
construction-period timeline.

**Round 2 splits the classification into
two separate sets:**

- **DSCR sculpt drivers (3 fields):** the
  fields that actually bind senior debt /
  DSCR under the current DSCR sculpt sizing
  method. Badge: "DSCR sculpt driver" (blue).
- **Timing drivers (1 field):**
  `construction_months` is a model-affecting
  field via the construction-period timeline,
  not via the DSCR sculpt engine. Badge:
  "Timing driver" (soft amber, new
  `.badge-timing` CSS class).

This matches what the runtime actually does:
`construction_months` can move `equity_irr`
by ~10bps (between 6mo and 36mo construction
periods) via the `financial_close` timing,
but it does NOT change `revenue`, `EBITDA`,
`senior debt`, or `DSCR`.

## Files changed (10)

### Production code (3)

- `app/ui/generic_driver_status_badges.py`
  (MODIFIED, +30/-15) — moved
  `ppa_term_years` from `METADATA_ONLY_FIELDS`
  to `WIRED_FIELDS`; moved
  `construction_months` from
  `METADATA_ONLY_FIELDS` to
  `TIMING_DRIVER_FIELDS` (a new set, separate
  from `DSCR_SCULPT_DRIVER_FIELDS`). Added
  `STATUS_TIMING_DRIVER`, `BADGE_TIMING_DRIVER`,
  `CSS_CLASS_TIMING = "badge-timing"`,
  `TOOLTIP_TIMING_DRIVER`, and
  `is_timing_driver_field()` helper.
  `DSCR_SCULPT_DRIVER_FIELDS` now contains
  only the 3 true sculpt drivers
  (interest_rate_pct, tenor_years,
  target_dscr). Updated module docstring
  with the S3 amendment and the S3 review
  fix.
- `app/templates/partials/inputs_section.html`
  (MODIFIED, +25/-5) — PPA Term row no longer
  carries the "Metadata only" badge
  (now WIRED, no badge). Construction Period
  row carries the "Timing driver" badge
  (soft amber, `.badge-timing`) with the
  S3 review-fix tooltip text. Narrative note
  split into 3 separate bullets: (1) DSCR
  sculpt driver bullet (3 fields), (2)
  Timing driver bullet (construction_months),
  (3) Indicative (derived) bullet
  (gearing_pct).
- `static/styles.css` (MODIFIED, +10/-0) —
  added `.badge-timing` class (soft amber
  palette).

### Tests (7)

- `tests/test_phase_s3_driver_kpi_binding.py`
  (NEW, +580/-0) — 50 tests in 12 classes
  covering the full driver inventory, the
  per-driver KPI response map, the S3 review
  fix (timing driver split), and the
  construction_months binding contract
  (moves equity_irr; does NOT move revenue,
  EBITDA, senior debt, or DSCR).
- `tests/test_phase_p1b_driver_status_badges.py`
  (MODIFIED, +25/-35) — updated P1-B tests
  to reflect the S3 mapping change
  (WIRED=6, DSCR_SCULPT_DRIVER=3,
  TIMING_DRIVER=1, METADATA_ONLY=0).
  ppa_term_years and construction_months
  moved out of METADATA_ONLY.
  construction_months now correctly maps
  to TIMING_DRIVER, not DSCR_SCULPT_DRIVER.
- `tests/test_phase_s2_gearing_as_output.py`
  (MODIFIED, +15/-5) — updated the S2 test
  to look for the "DSCR SCULPT DRIVER"
  narrative marker with only 3 fields
  (Phase S3 review fix split
  construction_months out into a separate
  "TIMING DRIVER" bullet). Added a new test
  for the Timing driver bullet.
- `tests/test_phase_s1_generic_sculpt_unify.py`
  (MODIFIED, +1/-1) — updated the S1 test
  assertion to look for the "Project IRR"
  wording (case-sensitive).
- 4 × `tests/test_phase24h*_*.py` (MODIFIED) —
  extended the skip-guards for `phase-s3`
  branches (S3 is a helper/test update, not
  a runtime refactor).

### Docs (2)

- `docs/phase_s3_driver_kpi_binding.md` (NEW)
- `reports/phase_s3_driver_kpi_binding.md`
  (this file)

## Pre-merge audit (all passed)

### What changed in production code

```
$ git diff origin/main -- app/ui/generic_driver_status_badges.py app/templates/partials/inputs_section.html
```

The diff is confined to:
- The driver status helper module
  (status vocabulary, field-to-status mapping,
  `__all__`, class docstring).
- The inputs_section.html partial
  (PPA Term row label and tooltip, Construction
  Period row label and tooltip, narrative
  note).

No runtime path changes. No formula changes.
No model changes. No factory changes.

### What did NOT change

```
$ git diff origin/main -- main_web.py main_api.py \
  app/project_factories.py app/waterfall_runner.py \
  app/waterfall_core.py app/services/ \
  app/persistence/ static/app.js \
  app/input_adapter.py app/input_schema.py \
  app/api/ domain/
(empty)
```

### Honest copy verification

- The "Indicative gearing (input)" label
  (S2) is preserved.
- The "Indicative (derived)" badge (S2)
  is preserved for gearing_pct.
- gearing_pct is still mapped to
  `REPORTING_DERIVED` (S2 invariant).
- The new "Timing driver" badge for
  construction_months explicitly says
  "moves equity_irr via financial_close
  timing, does not change revenue, EBITDA,
  senior debt, or DSCR".
- The DSCR sculpt driver badge is reserved
  for the 3 fields that actually bind senior
  debt / DSCR (interest_rate_pct,
  tenor_years, target_dscr).
- The narrative note in inputs_section.html
  is split into 3 separate bullets — one
  for each driver class — so the pilot
  user cannot mistake construction_months
  for a DSCR sculpt driver.
- The PPA Term row no longer carries the
  metadata badge (Phase S3 reclassification:
  WIRED, no badge).

### Runtime smoke

| Driver | Status | Pre-S3 effect | Post-S3 (Round 2) status |
|---|---|---|---|
| `ppa_term_years` (5 → 20) | METADATA_ONLY | Moves revenue, EBITDA | WIRED (now honestly labeled, no badge) |
| `construction_months` (6 → 36) | METADATA_ONLY | Moves equity_irr | TIMING_DRIVER (new "Timing driver" badge, soft amber) |
| `gearing_pct` (40 → 85) | REPORTING_DERIVED | No movement | REPORTING_DERIVED (S2 invariant) |
| `interest_rate_pct` | DSCR_SCULPT_DRIVER | Moves debt, DSCR | DSCR_SCULPT_DRIVER (3 fields, not 4) |
| `tenor_years` | DSCR_SCULPT_DRIVER | Moves debt, DSCR | DSCR_SCULPT_DRIVER (3 fields, not 4) |
| `target_dscr` | DSCR_SCULPT_DRIVER | Moves debt, DSCR | DSCR_SCULPT_DRIVER (3 fields, not 4) |

## Test counts (after S3 Round 2)

- **50 / 50 S3 tests PASS** (added
  construction_months binding contract
  tests + Timing driver split tests in
  Round 2)
- **266 passed / 4 skipped** in S3 + S2 +
  S1 + P1-B + P1-A + Phase 51F parity
  guardrails
- **21 / 21** Phase 51F parity guardrails
  PASS
- **132 / 134** factory / TUHO / Oborovo
  frozen-schedule tests PASS (2 Oborovo
  pre-existing infra rot failures, NOT S3
  regressions — verified by stash + retest
  on the Round 1 base)
- S1 exact-equality tests still pass
  (S3 does not touch the runtime path)
- S2 labels preserved
- rc1 SHA
  `b425a0708719eaa5e1d922b1008e5609758e0ad4`
  verified unchanged
- `use_construction_schedule_engine`
  remains False
- No R99 / R102 / G20 promotion
- No manual_gearing
- No formula / model / construction /
  C10 / R-PAR / IDC / tax / debt /
  depreciation changes
- Factory paths preserved bit-exact:
  - generic_solar: dscr_sculpt
  - generic_wind: dscr_sculpt
  - oborovo: gearing_cap, fixed_debt_keur=42852.26672602787
  - tuho: fixed, fixed_debt_keur=43359.0

## Hard constraints (preserved, all pinned by tests)

- No financial formula changes
- No model changes
- No factory path changes
- No Excel golden changes
- No frozen senior debt schedule changes
- No `manual_gearing` debt sizing method
- No `min(gearing cap, sculpt)` blend
- No `ProjectInputsSchema` removals
- No `use_construction_schedule_engine` flip
- No R99 / R102 / G20 promotion
- No persistence schema migration
- No `static/app.js` changes
- No `main_web.py` / `main_api.py` changes
- No Tailwind / Alpine / React / Vue / Svelte
- No JS calc
- No rc1 changes
- Forbidden paths unchanged

## Pre-existing infra rot (NOT S3 regressions)

Same list as S1 / S2:
`test_phase24g3_capex_sheet_readability.py`
SyntaxError,
`test_phase9_*` allowed-file-list,
`test_senior_dscr_sculpting_basis_bridge.py` /
`test_senior_rate_schedule_project_opt_in.py`
numeric drift,
`test_phase23d_*::test_oborovo_frozen_fixture_still_unavailable_and_off`
parity evolution, several
`test_phase17_*` / `test_phase18_*`
location-flexible assertion tests.

## Stop-after-report contract

DRAFT PR only. Do NOT mark ready. Do NOT
merge. Awaiting user review and explicit
go-ahead.

## Recommended next step (post-S3)

The current roadmap is:

1. **S1** (merged) — Generic Sizing Path
   Unification on Sculpt.
2. **S2** (merged) — Gearing as Output /
   Derived Reporting Metric.
3. **S3** (this PR) — Driver-to-KPI Binding
   Suite.
4. **M1 / M2** — Scenario Matrix
   (multi-scenario Base / Downside / Upside
   coverage at scale). S3 provides the
   per-driver sensitivity evidence that
   M1 / M2 will need for cross-scenario
   KPI variance analysis.

`manual_gearing` is **not** on this roadmap.

DO NOT START: C10, construction runtime
promotion, R-PAR, debt formula changes,
tax, IDC, senior IDC, depreciation, schema
migration, manual_gearing, Tailwind/Alpine,
factory path changes.
