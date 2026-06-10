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
model-affecting (via `_set_revenue_ppa_term`
and the schema extension). S3 corrects the
mismatch with runtime-proven evidence, not a
guess.

## Files changed (10)

### Production code (3)

- `app/ui/generic_driver_status_badges.py`
  (MODIFIED, +20/-10) — moved
  `ppa_term_years` from `METADATA_ONLY_FIELDS`
  to `WIRED_FIELDS`; moved
  `construction_months` from
  `METADATA_ONLY_FIELDS` to
  `DSCR_SCULPT_DRIVER_FIELDS`. Updated
  module docstring with the S3 amendment.
- `app/templates/partials/inputs_section.html`
  (MODIFIED, +5/-5) — PPA Term row no longer
  carries the "Metadata only" badge
  (now WIRED, no badge). Construction Period
  row carries the "Model driver" badge with
  the S3 tooltip text. Narrative note
  updated to mention the 4 model drivers.
- `static/styles.css` — UNCHANGED (the
  `.badge-dscr-sculpt` class from P1-B is
  reused for the new "Model driver" badge).

### Tests (7)

- `tests/test_phase_s3_driver_kpi_binding.py`
  (NEW, +550/-0) — 39 tests in 11 classes
  covering the full driver inventory and
  the per-driver KPI response map.
- `tests/test_phase_p1b_driver_status_badges.py`
  (MODIFIED, +20/-30) — updated P1-B tests
  to reflect the S3 mapping change
  (WIRED=6, DSCR_SCULPT_DRIVER=4,
  METADATA_ONLY=0). ppa_term_years and
  construction_months moved out of METADATA_ONLY.
- `tests/test_phase_s2_gearing_as_output.py`
  (MODIFIED, +5/-5) — updated the S2 test
  to look for the renamed "MODEL DRIVER"
  narrative marker (Phase S3 renamed the
  badge from "DSCR SCULPT DRIVER" to
  "MODEL DRIVER" because construction_months
  joined the set and is not a strict sculpt
  driver, just a model-affecting field).
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
- The new "Model driver" badge for
  construction_months explicitly says
  "moves equity_irr (via timing) but not
  revenue, EBITDA, or senior debt".
- The PPA Term row no longer carries the
  metadata badge (Phase S3 reclassification).

### Runtime smoke

| Driver | Status | Pre-S3 effect | Post-S3 status |
|---|---|---|---|
| `ppa_term_years` (5 → 20) | METADATA_ONLY | Moves revenue, EBITDA | WIRED (now honestly labeled) |
| `construction_months` (6 → 36) | METADATA_ONLY | Moves equity_irr | WIRED_PARTIAL (now honestly labeled) |
| `gearing_pct` (40 → 85) | REPORTING_DERIVED | No movement | REPORTING_DERIVED (S2 invariant) |

## Test counts (after S3)

- **39 / 39 S3 tests PASS**
- **507 passed / 4 skipped** in S3 + S2 +
  S1 + P1-B + P1-A + 7 pre-existing
  snapshot-path test files
- **21 / 21** Phase 51F parity guardrails
  PASS
- **139 / 139** factory / TUHO / Oborovo
  frozen-schedule tests PASS
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
