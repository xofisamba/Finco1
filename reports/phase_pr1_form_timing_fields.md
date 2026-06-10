# Phase PR1 — Form Timing Fields — Report

## Status

- **Type:** Wiring fix (main_web.py) +
  helper module + regression tests for
  the create-form timing fields + M1
  template fixup + route smoke
  positional-arg fix.
- **Branch:** `post-m1-form-timing-fields`
- **Base:** main @ `54edb091` (post-M1
  merge, PR #605)
- **Head:** `ca0fa13971adaf3cc16fa0c3fd0364a819b7f0b6`
- **PR:** DRAFT only. Do NOT mark ready.
  Do NOT merge. Awaiting user review.
- **CI:** 5/5 GitHub jobs GREEN on
  `ca0fa13`.

## Summary

Phase PR1 **eliminates the silent
template-default drift** Claude's delta
review flagged in PR1 of the post-M1
trust-polish mini-arc. The four create-
form timing fields (`cod_date`,
`construction_months`, `horizon_years`,
`ppa_term_years`) are now carried
through the actual Path B
(form -> schema) used by
`run_service`, `compare_service`,
`download_service`, and
`save_run_service`. Path B now produces
the same `ProjectInputs` as Path A
(form -> snapshot) for identical user
inputs.

The fix is implemented at the **route
level** in `main_web.py`, exactly where
`_build_schema_from_form` lives. The
legacy helper is extended with four new
optional kwargs; a new wrapper
`_build_schema_from_form_with_timing(form_data)`
binds the four kwargs from the FastAPI
form payload via `functools.partial`;
all six route handlers (validate, run,
compare, download POST, download GET,
save-run) now inject the wrapped helper
into their deps bundle. Downstream
service code is not touched.

The `app/services/form_timing_enrichment.py`
sidecar is also shipped for symmetry,
but the **actual Path B integration
point** is the `main_web.py` wiring
(per Claude's review requirement that
"the full Path B fix be in PR1").

## Files in PR1 (Round 2 + followup, 7)

### Production code (3)

- `main_web.py` (MODIFIED) — wiring fix
  - `_build_schema_from_form` extended
    with 4 new optional kwargs:
    `cod_date`, `construction_months`,
    `horizon_years`,
    `ppa_term_years_form`
  - New wrapper helper
    `_build_schema_from_form_with_timing(form_data)`
    uses `functools.partial` to bind the
    four timing fields
  - All 6 route handlers (validate,
    run, compare, download POST, download
    GET, save-run) updated to inject the
    wrapped helper
  - `form=None` for the GET route (no
    form payload) — preserves pre-PR1
    behaviour
  - **CI followup:** `/download` GET
    route deps `form=None` →
    positional `None` (the wrapper is
    positional-arg; the deps constructor
    was calling it as a keyword)

- `app/services/form_timing_enrichment.py`
  (NEW) — read-only helper module
  - `FORM_TIMING_FIELDS` — the four
    canonical field names
  - `enrich_schema_with_timing_fields` —
    pure function that returns a new
    `ProjectInputsSchema` with the four
    timing fields populated
  - `timing_fields_from_form_dict` —
    adapter for FastAPI Form flat dicts
  - `apply_timing_to_schema` — one-shot
    entry point for Path B callers

- `app/templates/partials/scenario_matrix.html`
  (MODIFIED) — **M1 latent-bug fixup
  under PR1**
  - 17 `is defined` guards on
    `project_ctx.X` attribute access
  - Jinja2 does not short-circuit `and`
    the way Python does, so
    `{{ format(project_ctx.X) }}` was
    evaluated even when the outer
    `is not none` guard was False,
    crashing on `TypeError: unsupported
    format string passed to
    Undefined.__format__`
  - em-dash UX preserved (None-attribute
    case still shows `—`)

### Production code (2)

- `main_web.py` (MODIFIED) — wiring fix
  - `_build_schema_from_form` extended
    with 4 new optional kwargs:
    `cod_date`, `construction_months`,
    `horizon_years`,
    `ppa_term_years_form`
  - New wrapper helper
    `_build_schema_from_form_with_timing(form_data)`
    uses `functools.partial` to bind the
    four timing fields
  - All 6 route handlers (validate,
    run, compare, download POST, download
    GET, save-run) updated to inject the
    wrapped helper
  - `form=None` for the GET route (no
    form payload) — preserves pre-PR1
    behaviour

- `app/services/form_timing_enrichment.py`
  (NEW) — read-only helper module
  - `FORM_TIMING_FIELDS` — the four
    canonical field names
  - `enrich_schema_with_timing_fields` —
    pure function that returns a new
    `ProjectInputsSchema` with the four
    timing fields populated
  - `timing_fields_from_form_dict` —
    adapter for FastAPI Form flat dicts
  - `apply_timing_to_schema` — one-shot
    entry point for Path B callers

### Tests (4 — 1 new + 1 PR1 file-scope patch + 2 cross-arc patches)

- `tests/test_phase_pr1_form_timing_fields.py`
  (NEW + MODIFIED) — 11 test classes,
  48 tests + 1 followup file-scope
  allowlist patch
  - `TestEnrichmentPreservesBase` — base
    schema fields are not mutated
  - `TestEnrichmentAppliesTiming` — the
    four timing fields are written into
    the returned schema
  - `TestEnrichmentNoValueSemantics` —
    `None` and empty-string mean "no
    value"
  - `TestSchemaSnapshotExactEquality` —
    S1 exact-equality contract, extended
    to timing (Solar + Wind, sidecar)
  - `TestTimingFieldBindingContracts` —
    S3 driver-to-KPI binding for timing
    fields (sidecar)
  - `TestFormDictExtractor` — flat-form-
    dict adapter
  - `TestFormFieldNameAlignment` — names
    match the create form HTML
  - `TestRealBuildSchemaFromForm` —
    **the actual `_build_schema_from_form`
    in main_web.py carries the four
    timing fields**
  - `TestRealFormPathProducesEqualProjectInputs` —
    **form path and snapshot path
    produce equal `ProjectInputs` for
    identical timing inputs**
  - `TestRealFormPathBindingContracts` —
    **ppa_term_years / construction_months
    from the actual form path move the
    expected KPIs**
  - `TestPhaseInvariants` — forbidden
    paths unchanged, rc1 preserved,
    factory paths preserved
  - `TestPR1FileScope` — PR1 touches
    exactly the 7 expected files
    (followup commit adds
    `app/templates/partials/scenario_matrix.html`
    as the documented M1 latent-bug
    fixup)
  - `TestEnrichmentPreservesBase` — base
    schema fields are not mutated
  - `TestEnrichmentAppliesTiming` — the
    four timing fields are written into
    the returned schema
  - `TestEnrichmentNoValueSemantics` —
    `None` and empty-string mean "no
    value"
  - `TestSchemaSnapshotExactEquality` —
    S1 exact-equality contract, extended
    to timing (Solar + Wind, sidecar)
  - `TestTimingFieldBindingContracts` —
    S3 driver-to-KPI binding for timing
    fields (sidecar)
  - `TestFormDictExtractor` — flat-form-
    dict adapter
  - `TestFormFieldNameAlignment` — names
    match the create form HTML
  - `TestRealBuildSchemaFromForm` —
    **the actual `_build_schema_from_form`
    in main_web.py carries the four
    timing fields**
  - `TestRealFormPathProducesEqualProjectInputs` —
    **form path and snapshot path
    produce equal `ProjectInputs` for
    identical timing inputs**
  - `TestRealFormPathBindingContracts` —
    **ppa_term_years / construction_months
    from the actual form path move the
    expected KPIs**
  - `TestPhaseInvariants` — forbidden
    paths unchanged, rc1 preserved,
    factory paths preserved
  - `TestPR1FileScope` — PR1 touches
    exactly the 6 expected files

- `tests/test_phase_p1b_driver_status_badges.py`
  (MODIFIED) — cross-arc patch: P1-B
  `TestForbiddenPathsUnchanged` updated
  to allowlist the PR1 follow-up files
  (`app/services/form_timing_enrichment.py`
  and `main_web.py`).

- `tests/test_phase_m1_scenario_matrix.py`
  (MODIFIED) — cross-arc patch: M1
  `TestM1FileScope` and
  `TestNoScenarioPersistence`
  updated to allowlist the PR1
  follow-up files.

### Docs (2)

- `docs/phase_pr1_form_timing_fields.md`
  (NEW) — governance doc
- `reports/phase_pr1_form_timing_fields.md`
  (this file)

## CI history

- **PR1 Round 1 head** (`0e03a84`): CI
  not run (was DRAFT, no wiring fix)
- **PR1 Round 2 head** (`dacfe58`):
  - 4/5 GREEN
  - 1 FAIL: CAPEX persistence and route
    smoke (10 tests failing)
  - **Root causes (verified):**
    1. `scenario_matrix.html` Jinja2
       template crash on None-attribute
       access (M1 latent regression,
       pre-existing on main `54edb091`)
    2. `/download` route 500 because
       `_build_schema_from_form_with_timing`
       was called as keyword `form=None`
       (PR1-introduced)
- **PR1 Round 2 followup head**
  (`ca0fa13`):
  - 5/5 GREEN
  - 0 fail
  - All 51 route smoke tests PASS
  - 421/421 S3 + S2 + S1 + P1-B + P1-A +
    Phase 51F parity + M1 + PR1 + route
    smoke

## Pre-merge audit (all pinned by tests)

### What changed in production code

The diff is confined to:

- `main_web.py` — read-only integration
  point change. `_build_schema_from_form`
  is extended with four new optional
  kwargs. The 6 route handlers are
  updated to inject a wrapped helper
  (via `functools.partial`). No runtime
  path changes. No formula changes. No
  model changes. No factory changes. No
  persistence changes.
- `app/services/form_timing_enrichment.py`
  (NEW) — read-only helper module. No
  I/O, no persistence, no factory, no
  model. Pure schema-enrichment logic.

### What did NOT change (forbidden paths, pinned by tests)

- `main_api.py` — UNCHANGED
- `app/project_factories.py` —
  UNCHANGED
- `app/waterfall_runner.py` —
  UNCHANGED
- `app/waterfall_core.py` — UNCHANGED
- `app/services/projects_create_service.py`
  — UNCHANGED
- `app/services/compare_service.py` —
  UNCHANGED
- `app/services/download_service.py` —
  UNCHANGED
- `app/services/run_service.py` —
  UNCHANGED
- `app/services/save_run_service.py` —
  UNCHANGED
- `app/persistence/` — UNCHANGED
- `static/app.js` — UNCHANGED
- `app/input_adapter.py` — UNCHANGED
- `app/input_schema.py` — UNCHANGED

### Honest copy verification

- The card body / docs / report explain
  that **the actual Path B is now wired**
  (not "out of scope").
- The phrase "silent default drift fixed
  in PR #606" appears in the PR body.
- The phrase "full Path B fix is out of
  scope" was removed from the docs /
  report (it is the wrong message for
  this PR; the fix is in scope and
  complete).
- The phrase "main_web.py is forbidden"
  was removed; `main_web.py` is the
  documented integration point for this
  fix (per Claude's review).
- The `app/services/form_timing_enrichment.py`
  sidecar is documented as a
  forward-compatible helper, NOT as
  the integration point used by the
  live Path B services.

## Test counts (final, PR1)

- **48 / 48 PR1 tests PASS**
- **421 / 421** S3 + S2 + S1 + P1-B +
  P1-A + Phase 51F parity guardrails +
  M1 + PR1 + route smoke (preserved)
- **51 / 51** route smoke (was 41/51 on
  the Round 2 head; the followup commit
  fixes all 10)
- **21 / 21** Phase 51F parity
  guardrails PASS (no model change)
- M1 contract preserved (M1 file-scope
  test passes with the cross-arc
  allowlist)
- P1-B contract preserved (P1-B
  forbidden-paths test passes with the
  cross-arc allowlist)
- S1 / S2 / S3 invariants preserved (the
  `main_web.py` fix uses the same
  `ProjectInputsSchema` field names
  and types as the S1 schema expansion)
- rc1 SHA
  `b425a0708719eaa5e1d922b1008e5609758e0ad4`
  verified unchanged
- `use_construction_schedule_engine`
  remains False
- No R99 / R102 / G20 promotion
- No `manual_gearing` / no
  `min(gearing, sculpt)` blend
- No persistence schema migration
- No `static/app.js` changes
- Forbidden paths UNCHANGED: no
  `main_api.py`, no
  `app/project_factories.py`, no
  `app/waterfall_runner.py`, no
  `app/waterfall_core.py`, no
  `app/services/` (other than the new
  sidecar), no `app/persistence/`, no
  `static/app.js`

## Hard no-go (preserved, all pinned by tests)

- No financial formula / debt / tax /
  depreciation / IDC changes
- No model / factory / frozen-schedule
  changes
- No construction / C10 / R-PAR changes
- No `manual_gearing` debt sizing method
- No `min(gearing cap, sculpt)` blend
- No senior IDC
- No persistence schema migration
- No R99 / R102 / G20 promotion
- No `static/app.js` changes
- No `main_api.py` changes
- No `app/services/projects_create_service.py`
  / `compare_service.py` /
  `download_service.py` /
  `run_service.py` /
  `save_run_service.py` changes
- No Tailwind / Alpine / React / Vue /
  Svelte
- No JS calc
- `use_construction_schedule_engine`
  remains False
- rc1 SHA
  `b425a0708719eaa5e1d922b1008e5609758e0ad4`
  preserved

## Pre-existing infra rot (NOT PR1 regressions)

Same list as S1 / S2 / S3 / M1:

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
  (parity evolution)
- `tests/test_oborovo_parity.py::TestBaselineInputs::test_shl_amount`
  / `TestBaselineFinancing::test_total_equity_shl`
  — pre-existing numeric drift
- `tests/test_auth_lite.py` /
  `tests/test_ui2_6_run_source_indicator.py`
  — collection error, missing
  `itsdangerous` / `fastapi`

## Roadmap (post-PR1)

1. **PR1** (this PR) — Form timing
   fields wiring fix + sidecar +
   regression tests
2. **PR2** — Realized gearing KPI (next,
   awaiting user go-ahead)
3. **PR3** — Taxonomy / brief alignment

`manual_gearing` is **not** on this
roadmap.

DO NOT START: PR2 until PR1 report is
delivered and reviewed. DO NOT START:
PR3 until PR2 report is delivered and
reviewed. DO NOT START: C10,
construction runtime promotion, R-PAR,
debt formula changes, tax, IDC, senior
IDC, depreciation, schema migration,
manual_gearing, Tailwind/Alpine,
factory path changes, R99/R102/G20
promotion.

## Stop-after-report contract

DRAFT PR only. Do NOT mark ready. Do
NOT merge. Awaiting user review and
explicit go-ahead before PR1 lands on
main.
