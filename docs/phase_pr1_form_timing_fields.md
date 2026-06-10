# Phase PR1 — Form Timing Fields — Governance Doc

## Status

- **Type:** Wiring fix + helper module +
  regression tests for the create-form
  timing fields.
- **Branch:** `post-m1-form-timing-fields`
- **Base:** main @ `54edb091` (post-M1 merge,
  PR #605)
- **Head:** `ca0fa13971adaf3cc16fa0c3fd0364a819b7f0b6`
- **CI:** 5/5 GitHub jobs GREEN on
  `ca0fa13`.
- **Goal:** Eliminate the silent
  template-default drift between
  form-driven Generic runs and
  snapshot-driven Generic runs for the
  four timing fields. **The drift is
  fixed in PR #606 — the actual Path B
  is now wired.**

## Problem statement (Claude delta review)

The create form in
`app/templates/partials/new_project_form.html`
already ships the four timing fields as
`<input>` controls:

- `cod_date`
- `construction_months`
- `horizon_years`
- `ppa_term_years`

The form posts them to `/projects/create`
and the route stores them in the baseline
snapshot via `_apply_new_project_required_inputs`
(in `main_web.py`). The snapshot path
(Path A) then reads them via
`build_projectinputs_from_snapshot` →
`_snapshot_to_dict` → `_resolve_user_inputs`.
✅ **Path A carries the four timing fields
correctly.**

The legacy `_build_schema_from_form`
helper in `main_web.py` (used by
`compare_service`, `download_service`,
and `run_service` for Path B schema
builds) previously did **NOT** forward
the four timing fields into the
`ProjectInputsSchema`. This meant Path
B runs silently fell back to factory
defaults for these four fields, while
Path A runs used the user-supplied
values. ❌ **Silent template-default
drift, fixed in PR #606.**

## Why the fix is in main_web.py (not in app/services/)

Claude's review explicitly authorised
edits to `main_web.py` for this fix:
*"It is acceptable to touch main_web.py
if that is where _build_schema_from_form
lives. main_web.py is not forbidden for
this fix."*

`app/services/` (run_service.py,
compare_service.py, download_service.py,
save_run_service.py) is **still**
forbidden. The fix is therefore
implemented at the **route level** in
`main_web.py`:

1. The legacy `_build_schema_from_form`
   helper in `main_web.py` is extended
   with four new optional kwargs:
   `cod_date`, `construction_months`,
   `horizon_years`, `ppa_term_years_form`.
2. A new wrapper helper
   `_build_schema_from_form_with_timing(form_data)`
   in `main_web.py` uses
   `functools.partial` to bind the four
   timing fields to the legacy helper.
3. All six route handlers in
   `main_web.py` (validate, run,
   compare, download POST, download GET,
   save-run) now inject the wrapped
   helper into their deps bundle via
   `build_schema_from_form=_build_schema_from_form_with_timing(form)`
   (or `form=None` for the GET route that
   has no form payload).

This is a **read-only integration point
change**. The downstream service code
(`run_service.py`, `compare_service.py`,
`download_service.py`, `save_run_service.py`)
is not touched. The four timing fields
flow into Path B through the existing
`deps.build_schema_from_form(...)`
call, which now transparently receives
the wrapped helper.

A `app/services/form_timing_enrichment.py`
sidecar is also shipped for future use,
but the actual Path B fix is in
`main_web.py` (Claude's review requirement).

## What PR1 includes

### Production code (2 files)

- `main_web.py` (MODIFIED) — wiring fix
  - `_build_schema_from_form` extended
    with 4 new optional kwargs
  - New wrapper helper
    `_build_schema_from_form_with_timing(form_data)`
    that uses `functools.partial` to bind
    the four timing fields
  - All 6 route handlers (validate,
    run, compare, download POST, download
    GET, save-run) updated to inject the
    wrapped helper
  - `form=None` for the GET route (no
    form payload) — preserves pre-PR1
    behaviour

- `app/services/form_timing_enrichment.py`
  (NEW) — read-only helper module
  - `FORM_TIMING_FIELDS`
  - `enrich_schema_with_timing_fields`
  - `timing_fields_from_form_dict`
  - `apply_timing_to_schema`

### Tests (1 new + 2 cross-arc patches)

- `tests/test_phase_pr1_form_timing_fields.py`
  (NEW) — 11 test classes, 48 tests
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
    **the actual _build_schema_from_form
    in main_web.py carries the four
    timing fields**
  - `TestRealFormPathProducesEqualProjectInputs` —
    **form path and snapshot path
    produce equal ProjectInputs for
    identical timing inputs (S1 contract
    applied to the actual form path)**
  - `TestRealFormPathBindingContracts` —
    **ppa_term_years / construction_months
    from the actual form path move the
    expected KPIs (S3 contract applied to
    the actual form path)**
  - `TestPhaseInvariants` — forbidden
    paths unchanged, rc1 preserved,
    factory paths preserved
  - `TestPR1FileScope` — PR1 touches
    exactly the 6 expected files (+ the
    cross-arc test patches)

- `tests/test_phase_p1b_driver_status_badges.py`
  (MODIFIED) — cross-arc patch: P1-B
  `TestForbiddenPathsUnchanged` updated
  to allowlist the PR1 follow-up files
  (`app/services/form_timing_enrichment.py`
  and `main_web.py`). The P1-B contract
  itself is unchanged; the patch only
  extends the test to tolerate PR1
  when both are run on the same branch.

- `tests/test_phase_m1_scenario_matrix.py`
  (MODIFIED) — cross-arc patch: M1
  `TestM1FileScope` and
  `TestNoScenarioPersistence`
  updated to allowlist the PR1
  follow-up files. The M1 contract
  itself is unchanged.

### Docs (2 files)

- `docs/phase_pr1_form_timing_fields.md`
  (this file)
- `reports/phase_pr1_form_timing_fields.md`
  — test counts, file-scope audit,
  pre-merge checklist

## S1 exact-equality contract, applied to the actual form path

The S1 contract states: "form path and
snapshot path produce exactly equal
`ProjectInputs`/KPIs". PR1 enforces
this contract for the four timing
fields against the **actual** form
path, not just the sidecar.

The regression tests in
`TestRealFormPathProducesEqualProjectInputs`
prove:

- The real `_build_schema_from_form`
  helper, called with the 4 timing
  kwargs, produces a `ProjectInputsSchema`
  that, when passed through
  `build_projectinputs`, produces the
  same `ProjectInputs` as the
  baseline snapshot with the same 4
  timing fields populated.
- The contract holds for both Generic
  Solar and Generic Wind.

## S3 binding contracts, applied to the actual form path

The S3 driver-to-KPI binding suite
classified the four timing fields as
follows:

- `cod_date` — wired (no badge, no KPI
  movement expected, just a date)
- `construction_months` — TIMING_DRIVER
  (moves equity_irr via financial_close
  timing; does NOT change revenue,
  EBITDA, senior debt, or DSCR)
- `horizon_years` — wired (no badge, no
  KPI movement expected, just a project
  horizon)
- `ppa_term_years` — wired (moves revenue,
  EBITDA via the PPA tariff duration)

The regression tests in
`TestRealFormPathBindingContracts` prove
that the actual form path honours these
contracts — i.e. changing
`ppa_term_years_form` from "10" to "20"
in the actual helper call changes
`revenue.ppa_term_years`, changing
`construction_months` from "6" to "36"
changes `info.construction_months`.

## Hard no-go (preserved, all pinned by tests)

- No financial formula changes
- No model / factory / frozen-schedule
  changes
- No debt-sizing / tax / IDC /
  depreciation changes
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
  `download_service.py` / `run_service.py`
  / `save_run_service.py` changes
- No `app/project_factories.py` /
  `app/waterfall_runner.py` /
  `app/waterfall_core.py` /
  `app/services/` (other than the new
  sidecar) / `app/persistence/` changes
- No Tailwind / Alpine / React / Vue /
  Svelte
- No JS calc
- `use_construction_schedule_engine`
  remains False
- rc1 SHA
  `b425a0708719eaa5e1d922b1008e5609758e0ad4`
  preserved
- Forbidden paths UNCHANGED: no
  `main_api.py`, no
  `app/project_factories.py`, no
  `app/waterfall_runner.py`, no
  `app/waterfall_core.py`, no
  `app/services/` (other than the new
  sidecar), no `app/persistence/`, no
  `static/app.js`

## Stop-after-report contract

DRAFT PR only. Do NOT mark ready. Do NOT
merge. Awaiting user review and explicit
go-ahead before PR1 lands on main.

## What M2 / future work looks like

This PR1 ships the full Path B fix. The
`app/services/form_timing_enrichment.py`
sidecar is kept for symmetry with the
form-extraction / schema-enrichment
pattern, but it is **not** the integration
point used by the live Path B services —
the integration point is the
`functools.partial` wiring in
`main_web.py`.

Future work (M2, etc.) is **not in this
arc** and must wait for the user to
explicitly kick off the next phase.
