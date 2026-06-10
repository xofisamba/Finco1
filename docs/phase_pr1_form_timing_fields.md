# Phase PR1 — Form Timing Fields — Governance Doc

## Status

- **Type:** Helper module + regression tests
  for the create-form timing fields.
- **Branch:** `post-m1-form-timing-fields`
- **Base:** main @ `54edb091` (post-M1 merge, PR #605)
- **Goal:** Eliminate silent template-default drift between form-driven Generic runs and snapshot-driven Generic runs for the four timing fields.

## Problem statement

The create form in `app/templates/partials/new_project_form.html` already ships the four timing fields as `<input>` controls:

- `cod_date`
- `construction_months`
- `horizon_years`
- `ppa_term_years`

The form posts them to `/projects/create` and the route stores them in the baseline snapshot via `_apply_new_project_required_inputs` (in `main_web.py`). The snapshot path then reads them via `build_projectinputs_from_snapshot` → `_snapshot_to_dict` → `_resolve_user_inputs`. ✅ **Snapshot path (Path A) carries the four timing fields correctly.**

However, the legacy `_build_schema_from_form` helper in `main_web.py` (used by `compare_service`, `download_service`, and `run_service` for Path B schema builds) does **NOT** forward the four timing fields into the `ProjectInputsSchema`. This means Path B runs silently fall back to factory defaults for these four fields, while Path A runs use the user-supplied values. ❌ **Schema path (Path B) loses the four timing fields.**

This is the "silent template-default drift" that Claude's delta review flagged. The user types the same values into the same form, but Path A and Path B produce different `ProjectInputs`.

## Why PR1 ships only a sidecar, not a fix in `main_web.py`

The fix to the legacy `_build_schema_from_form` helper lives in `main_web.py` and the three downstream services (`compare_service`, `download_service`, `run_service`) that consume it. All four files are **forbidden paths** for the post-M1 trust-polish mini-arc (per the constraints the user pinned for the S3 / M1 chain).

PR1 therefore ships an **enrichment sidecar** in `app/services/form_timing_enrichment.py` that:

- Accepts a base `ProjectInputsSchema` and four timing kwargs
- Returns a new `ProjectInputsSchema` with the four timing fields populated
- Preserves the base schema's other fields verbatim
- Treats `None` and empty-string form values as "no value" (the base schema's existing value is preserved)

The sidecar is callable from any future fix in `main_web.py` (or directly from the three downstream services) without re-discovering the contract. It is the reference implementation for the four timing field names, types, and conversion rules.

A future PR (not in this arc) can adopt the sidecar in the legacy `_build_schema_from_form` to complete the fix; this PR1 only ships the sidecar and pins the contract with tests.

## What PR1 includes

### Production code (1 file)

- `app/services/form_timing_enrichment.py` (NEW) — read-only helper module
  - `FORM_TIMING_FIELDS` — the four canonical field names
  - `enrich_schema_with_timing_fields(base, **timing_kwargs) -> ProjectInputsSchema` — pure function
  - `timing_fields_from_form_dict(form_data) -> dict` — adapter for FastAPI Form flat dicts
  - `apply_timing_to_schema(base, form_data) -> ProjectInputsSchema` — one-shot entry point

### Tests (1 file)

- `tests/test_phase_pr1_form_timing_fields.py` (NEW) — 9 test classes, 30+ tests
  - Enrichment sidecar preserves base schema fields
  - Enrichment sidecar applies timing fields
  - `None` and empty-string semantics
  - Schema vs snapshot exact-equality (S1 contract extended to timing)
  - Timing field binding contracts (S3: ppa_term moves revenue/EBITDA, construction_months moves equity_irr only)
  - Form flat-dict extractor
  - Form field-name alignment with create form HTML
  - Forbidden paths unchanged + rc1 + factory paths
  - File-scope (PR1 touches exactly the 4 expected files)

### Docs (2 files)

- `docs/phase_pr1_form_timing_fields.md` (this file)
- `reports/phase_pr1_form_timing_fields.md` — pre-merge audit + test counts

## S1 exact-equality contract, extended

The S1 contract states: "form path and snapshot path produce exactly equal ProjectInputs/KPIs". PR1 extends this contract to the four timing fields explicitly. The regression tests in `TestSchemaSnapshotExactEquality` prove:

- A `ProjectInputsSchema` with all four timing fields populated, after running through the enrichment sidecar, produces the same `ProjectInputs` as a baseline snapshot with the same four timing fields populated.
- The contract holds for both Generic Solar and Generic Wind.

## S3 binding contracts, applied to timing

The S3 driver-to-KPI binding suite classified the four timing fields as follows:

- `cod_date` — wired (no badge, no KPI movement expected, just a date)
- `construction_months` — TIMING_DRIVER (moves equity_irr via financial_close timing; does NOT change revenue, EBITDA, senior debt, or DSCR)
- `horizon_years` — wired (no badge, no KPI movement expected, just a project horizon)
- `ppa_term_years` — wired (moves revenue, EBITDA via the PPA tariff duration)

The regression tests in `TestTimingFieldBindingContracts` prove that Path B (form-via-schema) honours these contracts — i.e. changing `ppa_term_years` from 10 to 20 changes the PPA term field, changing `construction_months` from 6 to 36 changes the construction_months field, etc.

## Hard no-go (preserved, all pinned by tests)

- No financial formula changes
- No model / factory / frozen-schedule changes
- No debt-sizing / tax / IDC / depreciation changes
- No construction / C10 / R-PAR changes
- No `manual_gearing` debt sizing method
- No `min(gearing cap, sculpt)` blend
- No senior IDC
- No persistence schema migration
- No R99 / R102 / G20 promotion
- No `static/app.js` changes
- No `main_web.py` / `main_api.py` changes
- No `app/services/projects_create_service.py` / `compare_service.py` / `download_service.py` / `run_service.py` / `save_run_service.py` changes
- No `app/project_factories.py` / `app/waterfall_runner.py` / `app/waterfall_core.py` / `app/services/` (other than the new sidecar) / `app/persistence/` changes
- No Tailwind / Alpine / React / Vue / Svelte
- No JS calc
- `use_construction_schedule_engine` remains False
- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` preserved

## Migration path to a true fix in `main_web.py`

When the post-M1 trust-polish mini-arc is complete, a future PR can adopt the sidecar in `main_web.py`. The future fix should:

1. Import `apply_timing_to_schema` from `app.services.form_timing_enrichment`.
2. After `_build_schema_from_form(...)`, call `apply_timing_to_schema(schema, form_data)` to carry the four timing fields.
3. Or extend `_build_schema_from_form`'s signature to accept the four timing kwargs and call `enrich_schema_with_timing_fields` internally.

Either approach is forward-compatible with PR1. The sidecar and its tests are the reference implementation for the contract.

## Stop-after-report contract

DRAFT PR only. Do NOT mark ready. Do NOT merge. Awaiting user review and explicit go-ahead.
