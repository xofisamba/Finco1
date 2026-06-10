# Phase PR3 — Taxonomy / Brief Alignment — Governance Doc

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

## Goal

Phase PR3 creates ONE canonical source of
truth for driver classification and
sizing terminology. Pre-PR3, the same
vocabulary was spread across multiple
modules (P1-A audit, P1-B UI badges, S1
exact-equality, S2 gearing, S3 binding
suite) and was at risk of brief-vs-code
drift.

## Canonical source of truth

The canonical source of truth lives in
`app/ui/driver_taxonomy.py`. Future tests,
helpers, and UI surfaces MUST reference
this module.

## Canonical categories (6)

| Category | Meaning |
|---|---|
| `WIRED` | Fully model-affecting; moves revenue/EBITDA and/or IRR |
| `DSCR_SCULPT_DRIVER` | Binds senior debt / DSCR under DSCR sculpt sizing; IRR may not change |
| `TIMING_DRIVER` | Model-affecting via the construction-period timeline; moves equity_irr only (does NOT change revenue, EBITDA, senior debt, or DSCR) |
| `REPORTING_DERIVED` | User-supplied indicative assumption; the realised value is a derived output (e.g. realised gearing is computed as `senior_debt / total_capex` at runtime, not used to size debt) |
| `METADATA_ONLY` | Saved/displayed for context, not used by the runtime |
| `NOT_WIRED` | No runtime binding; not on the active editable form |

## Canonical field mapping (11 fields)

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

`METADATA_ONLY` and `NOT_WIRED` are empty
(current editable fields have already
been classified to the 4 other
categories; if a future field truly
belongs to one of these two categories,
add it explicitly with a test).

## Sizing terminology

### Excel methodology

DSCR sculpt sizing is the canonical
methodology under the TUHO / Oborovo
Excel workbooks. The app reproduces this
methodology on the live runtime path
(Generic Solar / Wind) and on the frozen
app paths (TUHO / Oborovo).

### App parity strategy

- TUHO / Oborovo app paths are FROZEN
  EXCEL ANCHORS (parity by construction).
- Generic Solar / Wind use the LIVE DSCR
  SCULPT path.

This is the honest distinction from the
misleading shorthand "TUHO and Oborovo
app sizing is pure live sculpt" (which
conflates Excel methodology with app
parity strategy). PR3 explicitly
distinguishes the two.

## Explicitly NOT on this roadmap

The following sizing concepts are
**explicitly NOT on this roadmap**:

- `manual_gearing` — no manual gearing
  sizing method
- `gearing_cap` — no gearing cap on the
  senior debt size
- `min(gearing_cap, sculpt)` — no blend
  of the gearing cap and the DSCR sculpt

They are deferred pending pilot feedback
and **MUST NOT be re-introduced without
explicit user go-ahead**. Active docs
MUST NOT advertise them as "near-term"
or "next-up".

## Future-agent warning

When classifying a new editable Generic
form field, follow these rules to avoid
brief-vs-code drift:

1. If the field moves revenue, EBITDA, or
   IRR when changed, it is `WIRED`.
2. If the field only binds senior debt /
   DSCR under DSCR sculpt sizing (with
   IRR potentially unchanged), it is
   `DSCR_SCULPT_DRIVER`.
3. If the field only moves the
   construction-period timeline and
   therefore equity_irr by a small
   amount, it is `TIMING_DRIVER` (not
   `DSCR_SCULPT_DRIVER`).
4. If the field is a user-supplied
   indicative assumption and the realised
   value is a derived output, it is
   `REPORTING_DERIVED`.
5. If the field is saved/displayed for
   context only and does not affect any
   runtime output, it is `METADATA_ONLY`.
6. If the field has no runtime binding at
   all, it is `NOT_WIRED`.

Update `CANONICAL_FIELD_MAPPING` in
`app/ui/driver_taxonomy.py` first, then
update the P1-A audit module, the P1-B
UI badges helper, and the S3 binding
suite to keep them in sync. Update the
S3 binding suite test and the P1-B
badges test to pin the new mapping. Do
**NOT** introduce a new category without
updating this module's
`CANONICAL_CATEGORIES` tuple.

## Cross-module consistency

The canonical mapping is verified by
tests to agree with the existing
per-phase modules:

- **P1-A audit module**
  (`app/ui/generic_driver_response_audit.py`)
  — uses `WIRED_PARTIAL` as the P1-A
  audit vocabulary. PR3 maps
  `DSCR_SCULPT_DRIVER` ↔ `WIRED_PARTIAL`
  for the cross-module consistency test.
- **P1-B UI badges helper**
  (`app/ui/generic_driver_status_badges.py`)
  — uses the full S2/S3 vocabulary and
  agrees with the canonical mapping.
- **S3 binding suite** — classifies the
  same 11 fields identically.

## Stale-claim guard tests

PR3 includes tests that scan the active
docs (P1-A, P1-B, S1, S2, S3, M1, PR1,
PR2 phase docs) for stale claims:

- "ppa_term_years is METADATA_ONLY" →
  forbidden (S3 promoted it to WIRED)
- "construction_months is METADATA_ONLY"
  → forbidden (S3 moved it to
  TIMING_DRIVER)
- "gearing binds senior debt" /
  "gearing is the binding debt sizing
  driver" → forbidden (S2 moved
  gearing_pct to REPORTING_DERIVED)
- "near-term manual_gearing" /
  "next-up manual_gearing" /
  "manual_gearing is on the roadmap" →
  forbidden (PR3 explicitly defers
  manual_gearing)

## Files in PR3 (7)

### Production code (1)

- `app/ui/driver_taxonomy.py` (NEW) —
  canonical source of truth module
  - `CANONICAL_CATEGORIES` (6 categories)
  - `CANONICAL_FIELD_MAPPING` (11
    editable Generic form fields)
  - `WIRED_FIELDS` / `DSCR_SCULPT_DRIVER_FIELDS`
    / `TIMING_DRIVER_FIELDS` /
    `REPORTING_DERIVED_FIELDS` /
    `METADATA_ONLY_FIELDS` /
    `NOT_WIRED_FIELDS` (per-category
    field sets)
  - `EXCEL_METHODOLOGY` /
    `APP_PARITY_STRATEGY` /
    `NOT_ON_ROADMAP_HELPERS` /
    `NOT_ON_ROADMAP_TEXT` /
    `FUTURE_AGENT_WARNING` (terminology
    + governance copy)
  - No imports from any forbidden
    module (`app.project_factories`,
    `app.waterfall_core`,
    `app.waterfall_runner`,
    `app.services`, `app.excel_export`,
    `main_web`, `main_api`)

### Tests (4 — 1 new + 3 cross-arc patches)

- `tests/test_phase_pr3_taxonomy.py`
  (NEW) — 12 test classes, 39 tests
  - `TestCanonicalCategories` (2 tests)
    — 6 canonical categories exist
  - `TestCanonicalFieldMapping` (12
    tests) — each of the 11 editable
    fields maps to the correct
    category; 11 fields total; no
    duplicates
  - `TestEmptyCategoriesAreEmpty` (2
    tests) — `METADATA_ONLY` and
    `NOT_WIRED` are empty
  - `TestP1BBadgesHelperAgrees` (5
    tests) — P1-B UI badges helper
    agrees with the canonical mapping
  - `TestSizingTerminology` (4 tests) —
    `EXCEL_METHODOLOGY` and
    `APP_PARITY_STRATEGY` constants
    exist and don't use misleading
    shorthand
  - `TestFutureAgentWarning` (1 test) —
    `FUTURE_AGENT_WARNING` mentions
    all 6 categories
  - `TestNoStaleActiveClaims` (4 tests) —
    no stale claims in active docs
  - `TestPhaseInvariants` (4 tests) —
    rc1 SHA resolvable,
    `use_construction_schedule_engine`
    remains False, no forbidden-path
    changes, no forbidden imports in
    `driver_taxonomy`
  - `TestNoFinancialFormulaChanges` (2
    tests) — factory paths / waterfall
    core SHA unchanged
  - `TestS1S2S3M1PR1PR2TestsPreserved` (1
    test) — all prior-phase tests pass
    under PR3 (smoke)
  - `TestFileScope` (1 test) — PR3
    touches only the expected files

- `tests/test_phase_m1_scenario_matrix.py`
  (MODIFIED) — cross-arc test patch
  (M1 file-scope allowlist extended
  for PR3)
- `tests/test_phase_pr1_form_timing_fields.py`
  (MODIFIED) — cross-arc test patch
  (PR1 file-scope allowlist extended
  for PR3)
- `tests/test_phase_pr2_realized_gearing.py`
  (MODIFIED) — cross-arc test patch
  (PR2 file-scope allowlist extended
  for PR3)

### Docs (2)

- `docs/phase_pr3_taxonomy_brief_alignment.md`
  (this file)
- `reports/phase_pr3_taxonomy_brief_alignment.md`
  (NEW) — test counts, file-scope
  audit, pre-merge checklist

## What PR3 does NOT do (preserved, all pinned by tests)

- No financial formula change
- No debt sizing change
- No DSCR sculpt semantics change
- No factory path change
  (`app/project_factories.py` SHA
  preserved, verified)
- No model / runtime change
  (`app/waterfall_core.py` SHA
  preserved, verified)
- No tax / depreciation / IDC change
- No construction / C10 / R-PAR change
- No `manual_gearing` /
  `gearing_cap` / `min(gearing_cap, sculpt)`
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
- rc1 SHA
  `b425a0708719eaa5e1d922b1008e5609758e0ad4`
  preserved

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
