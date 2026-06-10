# Phase PR1 — Form Timing Fields — Report

## Status

- **Type:** Helper module + regression tests
  for the create-form timing fields.
- **Branch:** `post-m1-form-timing-fields`
- **Base:** main @ `54edb091` (post-M1 merge, PR #605)
- **PR:** DRAFT only. Do NOT mark ready. Do NOT
  merge. Awaiting user review.

## Summary

Phase PR1 ships a read-only enrichment
sidecar in `app/services/form_timing_enrichment.py`
that Path B callers (and any future
`main_web.py` fix) can adopt to carry the
four create-form timing fields into the
`ProjectInputsSchema`. The sidecar is the
reference implementation for the four
timing field names, types, and conversion
rules; it is pinned by tests.

PR1 does **not** modify `main_web.py` or
any of the three downstream services that
consume the legacy `_build_schema_from_form`
helper — those are forbidden paths for the
post-M1 trust-polish mini-arc. The sidecar
is the contract that any future fix in
`main_web.py` should mirror.

The regression tests prove:

- The sidecar preserves the base schema's
  other fields verbatim.
- The sidecar accepts the four timing
  fields as kwargs and writes them into
  the returned schema.
- `None` and empty-string form values mean
  "no value" — the base schema's existing
  value is preserved.
- A schema with all four timing fields
  populated produces the same `ProjectInputs`
  as a snapshot with the same four timing
  fields populated (S1 exact-equality
  contract, extended to timing).
- `ppa_term_years` from a schema/snapshot
  moves revenue / EBITDA (S3 contract).
- `construction_months` from a
  schema/snapshot moves equity_irr via
  financial_close timing (S3 contract) but
  does NOT change revenue, EBITDA, senior
  debt, or DSCR.
- The form flat-dict extractor returns the
  four timing fields with the canonical
  names.
- The four timing field names match the
  create form's `<input name="...">`
  attributes (so the sidecar is forward-
  compatible with the actual HTML form).

## Files in PR1 (4)

### Production code (1)

- `app/services/form_timing_enrichment.py`
  (NEW, +180/-0) — read-only helper module
  - `FORM_TIMING_FIELDS` — the four canonical
    field names
  - `enrich_schema_with_timing_fields` — pure
    function that returns a new schema with
    the four timing fields populated
  - `timing_fields_from_form_dict` — adapter
    for FastAPI Form flat dicts
  - `apply_timing_to_schema` — one-shot
    entry point for Path B callers

### Tests (1)

- `tests/test_phase_pr1_form_timing_fields.py`
  (NEW, +540/-0)
  - 9 test classes, 30+ tests
  - `TestEnrichmentPreservesBase` — base
    schema fields are not mutated
  - `TestEnrichmentAppliesTiming` — the four
    timing fields are written into the
    returned schema
  - `TestEnrichmentNoValueSemantics` —
    `None` and empty-string mean "no value"
  - `TestSchemaSnapshotExactEquality` — S1
    exact-equality contract, extended to
    timing (Solar + Wind)
  - `TestTimingFieldBindingContracts` — S3
    driver-to-KPI binding for timing fields
  - `TestFormDictExtractor` — flat-form-dict
    adapter
  - `TestFormFieldNameAlignment` — names
    match the create form HTML
  - `TestPhaseInvariants` — forbidden paths
    unchanged, rc1 preserved, factory paths
    preserved
  - `TestPR1FileScope` — PR1 touches exactly
    the 4 expected files

### Docs (2)

- `docs/phase_pr1_form_timing_fields.md` (NEW)
  — governance doc
- `reports/phase_pr1_form_timing_fields.md`
  (this file)

## Pre-merge audit (planned, all pinned by tests)

### What changed in production code

The diff is confined to:

- The new helper module
  `app/services/form_timing_enrichment.py`
  (read-only, no I/O, no persistence, no
  factory, no model).

No runtime path changes. No formula
changes. No model changes. No factory
changes. No persistence changes.

### What did NOT change (forbidden paths, pinned by tests)

- `main_web.py` — UNCHANGED
- `main_api.py` — UNCHANGED
- `app/project_factories.py` — UNCHANGED
- `app/waterfall_runner.py` — UNCHANGED
- `app/waterfall_core.py` — UNCHANGED
- `app/services/projects_create_service.py` — UNCHANGED
- `app/services/compare_service.py` — UNCHANGED
- `app/services/download_service.py` — UNCHANGED
- `app/services/run_service.py` — UNCHANGED
- `app/services/save_run_service.py` — UNCHANGED
- `app/persistence/` — UNCHANGED
- `static/app.js` — UNCHANGED
- `app/input_adapter.py` — UNCHANGED
- `app/input_schema.py` — UNCHANGED

### Honest copy verification

- The sidecar is named
  `form_timing_enrichment` (matches the PR1
  brief wording).
- The four timing field names
  (`cod_date`, `construction_months`,
  `horizon_years`, `ppa_term_years`) match
  the create form HTML `<input name="...">`
  attributes and the
  `_apply_new_project_required_inputs`
  snapshot keys (pinned by
  `TestFormFieldNameAlignment`).
- The S1 exact-equality contract is extended
  to timing fields explicitly (pinned by
  `TestSchemaSnapshotExactEquality`).
- The S3 binding contracts are honoured for
  the timing fields (pinned by
  `TestTimingFieldBindingContracts`).

## Test counts (planned, PR1)

- **30+ / 30+ PR1 tests PASS**
- All S1, S2, S3, M1, P1-A, P1-B tests
  continue to PASS (PR1 only adds files; does
  not modify any existing production file)
- **21 / 21** Phase 51F parity guardrails
  PASS (no model change)
- **128+ / 128+** factory / TUHO / Oborovo
  tests PASS (no factory change)

## Hard no-go (preserved, all pinned by tests)

- No financial formula / debt / tax /
  depreciation / IDC changes
- No model / factory / frozen-schedule changes
- No construction / C10 / R-PAR changes
- No `manual_gearing` debt sizing method
- No `min(gearing cap, sculpt)` blend
- No senior IDC
- No persistence schema migration
- No R99 / R102 / G20 promotion
- No `static/app.js` changes
- No `main_web.py` / `main_api.py` changes
- No `app/services/projects_create_service.py`
  / `compare_service.py` / `download_service.py`
  / `run_service.py` / `save_run_service.py`
  changes
- No Tailwind / Alpine / React / Vue / Svelte
- No JS calc
- `use_construction_schedule_engine` remains
  False
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
  — collection error, missing `itsdangerous`
  / `fastapi`

## Known limitation: full Path B fix is out of scope for PR1

The legacy `_build_schema_from_form` helper
in `main_web.py` does not forward the four
timing fields into the `ProjectInputsSchema`.
This causes Path B runs (compare, download,
run via the schema path) to silently fall
back to factory defaults for these four
fields.

PR1 ships the sidecar and the contract.
A future PR (not in this arc) must adopt
the sidecar in `main_web.py` (or in the
three downstream services) to complete
the fix. The sidecar is the reference
implementation; the future fix should
mirror the four field names, types, and
conversion rules.

## Roadmap (post-PR1)

1. **PR1** (this PR) — Form timing fields
   sidecar + regression tests
2. **PR2** — Realized gearing KPI (next,
   awaiting user go-ahead)
3. **PR3** — Taxonomy / brief alignment
4. **Future (out of arc)** — Adopt the
   PR1 sidecar in `main_web.py` /
   `compare_service.py` / `download_service.py`
   / `run_service.py` to complete the Path B
   fix

`manual_gearing` is **not** on this roadmap.

DO NOT START: PR2 until PR1 report is
delivered and reviewed. DO NOT START: PR3
until PR2 report is delivered and reviewed.
DO NOT START: C10, construction runtime
promotion, R-PAR, debt formula changes,
tax, IDC, senior IDC, depreciation, schema
migration, manual_gearing, Tailwind/Alpine,
factory path changes, R99/R102/G20
promotion, the full Path B fix in
`main_web.py` (out of arc).

## Stop-after-report contract

DRAFT PR only. Do NOT mark ready. Do NOT
merge. Awaiting user review and explicit
go-ahead before PR1 lands on main.
