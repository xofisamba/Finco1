# Phase PR3 — Taxonomy / Brief Alignment — Report

## Status

- **Type:** Canonical source of truth
  (single module) + cross-arc test
  alignment + brief-vs-code drift
  guard.
- **Branch:** `post-m1-taxonomy-brief-alignment`
- **Base:** main @ `f797cdd` (post-PR2
  merge, PR #607)
- **PR:** DRAFT only. Do NOT mark ready.
  Do NOT merge. Awaiting user review.

## Summary

Phase PR3 creates ONE canonical source
of truth for driver classification and
sizing terminology. Pre-PR3, the same
vocabulary was spread across multiple
modules (P1-A audit, P1-B UI badges, S1
exact-equality, S2 gearing, S3 binding
suite) and was at risk of brief-vs-code
drift.

The PR3 fix is:

1. A new `app/ui/driver_taxonomy.py`
   module that exposes
   `CANONICAL_CATEGORIES` (6
   categories), `CANONICAL_FIELD_MAPPING`
   (11 editable Generic form fields),
   and the sizing terminology
   constants (`EXCEL_METHODOLOGY`,
   `APP_PARITY_STRATEGY`,
   `NOT_ON_ROADMAP_HELPERS`,
   `NOT_ON_ROADMAP_TEXT`,
   `FUTURE_AGENT_WARNING`).
2. A new test file
   `tests/test_phase_pr3_taxonomy.py`
   with 12 test classes and 39 tests
   that:
   - Pin the canonical categories
     tuple (6 categories).
   - Pin the canonical field mapping
     (11 fields, 4 of which are
     pinned individually).
   - Verify `METADATA_ONLY` and
     `NOT_WIRED` are empty.
   - Verify the P1-B UI badges helper
     agrees with the canonical mapping.
   - Verify the sizing terminology
     constants exist and are not
     misleading.
   - Verify the `FUTURE_AGENT_WARNING`
     mentions all 6 categories.
   - Scan the active docs (P1-A, P1-B,
     S1, S2, S3, M1, PR1, PR2 phase
     docs) for stale claims about
     ppa_term_years,
     construction_months, gearing, and
     manual_gearing.
   - Verify rc1 SHA is preserved,
     `use_construction_schedule_engine`
     remains False, no forbidden-path
     changes, no forbidden imports in
     `driver_taxonomy`.
   - Verify factory paths / waterfall
     core SHA are unchanged.
   - Smoke-run the full prior-phase
     test suite (S1 + S2 + S3 + M1 +
     PR1 + PR2 + P1-A + P1-B + Phase
     51F parity + route smoke).
3. Cross-arc test patches (M1, PR1,
   PR2 file-scope allowlists extended
   for PR3).
4. New docs and report.

The `app/ui/driver_taxonomy.py` module
is a **pure constants + copy module**.
It does NOT import from any forbidden
module, does NOT change any runtime path,
does NOT change any formula, does NOT
change any model, does NOT change any
factory path, does NOT change any
service code. It is read-only
governance infrastructure.

## Files in PR3 (7)

### Production code (1)

- `app/ui/driver_taxonomy.py` (NEW) —
  canonical source of truth module
  (pure constants + copy, no I/O, no
  runtime, no forbidden imports)

### Tests (4 — 1 new + 3 cross-arc patches)

- `tests/test_phase_pr3_taxonomy.py`
  (NEW) — 12 test classes, 39 tests
- `tests/test_phase_m1_scenario_matrix.py`
  (MODIFIED) — M1 file-scope
  allowlist extension
- `tests/test_phase_pr1_form_timing_fields.py`
  (MODIFIED) — PR1 file-scope
  allowlist extension
- `tests/test_phase_pr2_realized_gearing.py`
  (MODIFIED) — PR2 file-scope
  allowlist extension

### Docs (2)

- `docs/phase_pr3_taxonomy_brief_alignment.md`
  (NEW)
- `reports/phase_pr3_taxonomy_brief_alignment.md`
  (this file)

## Test results (final, PR3)

- **39 / 39 PR3 tests PASS**
- **487 / 487** S1 + S2 + S3 + M1 + PR1
  + PR2 + P1-A + P1-B + Phase 51F
  parity guardrails + PR3 + route smoke
  (preserved)
- **51 / 51** route smoke
- **21 / 21** Phase 51F parity
  guardrails
- 0 failed
- rc1 SHA
  `b425a0708719eaa5e1d922b1008e5609758e0ad4`
  preserved

## Pre-merge audit (all pinned by tests)

### What changed in production code

- `app/ui/driver_taxonomy.py` (NEW) —
  pure constants + copy module. No
  runtime path changes. No formula
  changes. No model changes. No
  factory changes. No persistence
  changes. No service-code changes.
  No `app.js` changes. No
  forbidden-path changes.

### What did NOT change (forbidden paths, pinned by tests)

- `app/project_factories.py` —
  UNCHANGED (factory paths preserved
  bit-exact, SHA verified)
- `app/waterfall_core.py` — UNCHANGED
  (model SHA verified)
- `app/waterfall_runner.py` —
  UNCHANGED
- `main_web.py` — UNCHANGED
- `main_api.py` — UNCHANGED
- `app/persistence/` — UNCHANGED
- `app/services/` — UNCHANGED
- `app/excel_export.py` — UNCHANGED
- `static/app.js` — UNCHANGED

### `driver_taxonomy` purity

`driver_taxonomy` does NOT import from
any forbidden module. Verified by
`TestPhaseInvariants::test_taxonomy_helper_no_forbidden_imports`.

## Canonical mapping (pinned by tests)

| Field | Category |
|---|---|
| `tariff_eur_mwh` | WIRED |
| `p50_hours` | WIRED |
| `capacity_mw` | WIRED |
| `total_capex_keur` | WIRED |
| `opex_y1_keur` | WIRED |
| `ppa_term_years` | WIRED |
| `interest_rate_pct` | DSCR_SCULPT_DRIVER |
| `tenor_years` | DSCR_SCULPT_DRIVER |
| `target_dscr` | DSCR_SCULPT_DRIVER |
| `construction_months` | TIMING_DRIVER |
| `gearing_pct` | REPORTING_DERIVED |

`METADATA_ONLY` and `NOT_WIRED` are
empty.

## Cross-module consistency (pinned by tests)

- P1-B UI badges helper
  (`app/ui/generic_driver_status_badges.py`)
  agrees with the canonical mapping
  for `WIRED_FIELDS`,
  `DSCR_SCULPT_DRIVER_FIELDS`,
  `TIMING_DRIVER_FIELDS`, and
  `REPORTING_DERIVED_FIELDS`.
- P1-B `get_field_status` agrees with
  the canonical category (P1-B maps
  `DSCR_SCULPT_DRIVER` to
  `STATUS_WIRED_PARTIAL` for historical
  reasons; the cross-module test
  handles this mapping).

## Stale-claim guard (pinned by tests)

Active docs MUST NOT contain the
following stale claims:

- "ppa_term_years is METADATA_ONLY" or
  "ppa_term_years are METADATA_ONLY"
  → forbidden (S3 promoted it to
  WIRED)
- "construction_months is
  METADATA_ONLY" → forbidden (S3 moved
  it to TIMING_DRIVER)
- "gearing binds senior debt" or
  "gearing is the binding debt sizing
  driver" → forbidden (S2 moved
  gearing_pct to REPORTING_DERIVED)
- "near-term manual_gearing" /
  "next-up manual_gearing" /
  "manual_gearing is on the roadmap" →
  forbidden (PR3 explicitly defers
  manual_gearing)

## Hard no-go (preserved, all pinned by tests)

- No financial formula change
- No debt sizing change
- No DSCR sculpt semantics change
- No factory path change
- No model / runtime change
- No tax / depreciation / IDC change
- No construction / C10 / R-PAR change
- No `manual_gearing` / `gearing_cap` /
  `min(gearing_cap, sculpt)`
  re-introduction
- No senior IDC
- No persistence schema migration
- No R99 / R102 / G20 promotion
- No `static/app.js` change
- No `main_web.py` change
- No `main_api.py` change
- No `app/services/` change
- No `app/persistence/` change
- No `app/excel_export.py` change
- No Tailwind / Alpine / React / Vue /
  Svelte
- No JS calc
- `use_construction_schedule_engine`
  remains False
- rc1 SHA preserved

## Pre-existing infra rot (NOT PR3 regressions)

Same list as S1 / S2 / S3 / M1 / PR1 /
PR2:

- `tests/test_phase24g3_capex_sheet_readability.py`
  — f-string + backslash SyntaxError
- `tests/test_phase9_tuho_full_semester_horizontal_parity_workbook.py::test_no_runtime_files_changed`
  — pre-S1 allowed-file-list
- `tests/test_senior_dscr_sculpting_basis_bridge.py`
  / `tests/test_senior_rate_schedule_project_opt_in.py`
  — numeric drift pre-existing
- `tests/test_phase23d_prep_tuho_fixture_backed_frozen_senior_ds.py::test_oborovo_frozen_fixture_still_unavailable_and_off`
  — Oborovo has
  `use_frozen_excel_senior_debt_schedule=True`
- `tests/test_oborovo_parity.py::TestBaselineInputs::test_shl_amount`
  / `TestBaselineFinancing::test_total_equity_shl` —
  pre-existing numeric drift
- `tests/test_auth_lite.py` /
  `tests/test_ui2_6_run_source_indicator.py` —
  collection error, missing
  `itsdangerous` / `fastapi`

## Roadmap (post-PR3)

PR3 is the final arc of the post-M1
trust-polish mini-arc (S1 + S2 + S3 + M1
+ PR1 + PR2 + PR3). No further follow-up
PR is planned in this arc. The next arc
will be chosen with explicit user
go-ahead.

`manual_gearing` is **not** on this
roadmap.

DO NOT START: any further arc PR until
PR3 report is delivered and reviewed. DO
NOT START: C10, construction runtime
promotion, R-PAR, debt formula changes,
tax, IDC, senior IDC, depreciation,
schema migration, manual_gearing,
Tailwind/Alpine, factory path changes,
R99/R102/G20 promotion.

## Stop-after-report contract

DRAFT PR only. Do NOT mark ready. Do
NOT merge. Awaiting user review and
explicit go-ahead before PR3 lands on
main.
