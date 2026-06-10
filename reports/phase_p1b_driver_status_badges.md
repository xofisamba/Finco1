# Phase P1-B — Generic Driver Status Badges — Report

## Status

- **Type:** UI explanation layer (read-only)
- **Branch:** `phase-p1b-driver-status-badges`
- **Base:** `f8ae19164a7a73f50c2964e7787ecdc5d1cbd46d`
  (post-PR #600 main, P1-A merge)
- **PR:** DRAFT (do NOT mark ready, do NOT merge —
  awaiting user review and explicit go-ahead)
- **Scope:** 4 files, ~+500 LOC (helper + CSS + partial
  edits + tests + this report + docs)

## What was delivered

### 1. Helper module

`app/ui/generic_driver_status_badges.py` (+~225 lines)

Exports:
- `STATUS_WIRED`, `STATUS_WIRED_PARTIAL`,
  `STATUS_METADATA_ONLY`, `STATUS_NOT_WIRED`
- `BADGE_METADATA_ONLY`, `BADGE_DSCR_SCULPT_DRIVER`
- `CSS_CLASS_METADATA`, `CSS_CLASS_DSCR_SCULPT`
- `TOOLTIP_METADATA_ONLY`, `TOOLTIP_DSCR_SCULPT_DRIVER`
- `METADATA_ONLY_FIELDS = ("ppa_term_years",
  "construction_months")`
- `DSCR_SCULPT_DRIVER_FIELDS = ("gearing_pct",
  "interest_rate_pct", "tenor_years", "target_dscr")`
- `WIRED_FIELDS = ("tariff_eur_mwh", "p50_hours",
  "capacity_mw", "total_capex_keur", "opex_y1_keur")`
- `NOT_WIRED_FIELDS = ()`
- `FieldDriverStatus` (frozen dataclass)
- `is_metadata_only_field(field) -> bool`
- `is_dscr_sculpt_driver_field(field) -> bool`
- `is_wired_field(field) -> bool`
- `get_field_status(field) -> str`
- `get_field_badge(field) -> FieldDriverStatus`
- `EXPLORATORY_NOTICE_TEXT`

### 2. Partial updates

`app/templates/partials/inputs_section.html`:
- 6 `field_row` calls swapped:
  - `construction_months` → `badge="Metadata only"`,
    `badge_class="badge-metadata"`,
    `badge_title="This field is saved/displayed for
    context but is not currently used by the Generic
    runtime calculation."`
  - `ppa_term_years` → same metadata setup
  - `gearing_pct`, `target_dscr`, `interest_rate_pct`,
    `tenor_years` → `badge="DSCR sculpt driver"`,
    `badge_class="badge-dscr-sculpt"`,
    `badge_title="This field affects debt / equity /
    DSCR outputs under the current DSCR sculpting
    method. Project IRR may not change."`
- `field_row` macro gains optional `badge_title`
  parameter and `data-driver-status` /
  `data-field-name` attributes on the badge
- New `inp-driver-status-note` block below the
  Phase 24-H exploratory warning, with
  `data-driver-status-legend="true"` attribute

### 3. CSS additions

`static/styles.css`:
- `.badge-metadata` — gray, uppercase, bordered
- `.badge-dscr-sculpt` — blue, uppercase, bordered
- `.inp-driver-status-note` — layout (flex, wrap,
  gap, surface, border, font-size 0.8rem)

### 4. Tests

`tests/test_phase_p1b_driver_status_badges.py` (+~530
lines), 78 tests across 13 test classes:

- `TestFieldStatusMapping` — counts and field sets
  match PR #600 audit
- `TestGetFieldStatus` — parametrized 11-field
  status lookup
- `TestGetFieldBadge` — metadata / DSCR sculpt /
  wired field returns the right badge metadata
- `TestTooltipCopy` — tooltips and exploratory copy
  are honest; no positive "lender-ready" /
  "bank-approved" claim in the helper tooltips
- `TestInputsSectionRenders` — the partial carries
  the right badge / class / tooltip for each of
  the 6 retagged fields; the new
  `data-driver-status-legend` block exists and
  lists the 6 fields
- `TestBadgeCSS` — the 3 CSS classes / 1 ID exist
- `TestSchemaUnchanged` — `ProjectInputsSchema`
  has 8 fields (unchanged), `ppa_term_years` and
  `construction_months` are still NOT in the schema
- `TestNoFormulaChanges` — `git diff origin/main
  -- <path>` is empty for `app/waterfall_core.py`,
  `app/waterfall_runner.py`, `app/input_adapter.py`,
  `app/ui_runner.py`, `app/project_factories.py`,
  `app/services/run_service.py`
- `TestFeatureFlagInvariant` — `use_construction_
  schedule_engine = True` does not appear in
  `app/`, `main_web.py`, `main_api.py`
- `TestForbiddenPathsUnchanged` — `app/persistence/`,
  `app/services/`, `app/construction/`, `app/debt/`,
  `app/tax/`, `app/depreciation/`, `app/idc/`,
  `domain/`, `app/excel_export.py`, `main_web.py`,
  `main_api.py` are all clean in `git diff origin/main`
- `TestRc1Frozen` — `git rev-parse --verify` resolves
  the rc1 SHA
- `TestTuhoOborovoUnaffected` — TUHO / Oborovo
  factory path files are clean in `git diff origin/main`
- `TestHelperSafety` — the helper does not import
  any of 8 forbidden modules, and does not set any
  construction / depreciation / tax feature flag

## Verification

```
$ /usr/local/bin/pytest tests/test_phase_p1b_driver_status_badges.py -q
78 passed, 1 warning in 1.56s
```

All 78 P1-B tests pass on the P1-B branch
(`phase-p1b-driver-status-badges`).

## Arc-suite verification

```
$ /usr/local/bin/pytest \
    tests/test_phase_p1b_driver_status_badges.py \
    tests/test_phase_p1a_generic_driver_response_audit.py \
    tests/test_phase25c3_feedback_capture_helpers.py \
    tests/test_phase25c_closure_third_party_test_readiness.py
245 passed, 2 warnings in 1.95s
```

P1-B + P1-A + 25C-3 + 25C closure all green on the
P1-B branch.

## Pre-existing infra rot (NOT P1-B regressions, verified
on P1-A base `f8ae191`)

- `tests/test_phase24g3_capex_sheet_readability.py` —
  SyntaxError (`f-string expression part cannot include
  a backslash`). Pre-existing; not blocking.
- `tests/test_phase9_tuho_full_semester_horizontal_parity_workbook.py::test_no_runtime_files_changed` —
  flags `app/templates/partials/inputs_section.html` as
  a "runtime change" because that test is pinned to
  the phase9 allow-list. Pre-existing; not blocking.
- `tests/test_senior_dscr_sculpting_basis_bridge.py` —
  numeric `ds` deltas no longer match the expected
  (392.45 vs 392.10); pre-existing, unrelated to P1-B.
- `tests/test_senior_rate_schedule_project_opt_in.py` —
  same kind of numeric drift, pre-existing.

These are not introduced by P1-B; they reproduce on
the P1-A base `f8ae191` without P1-B applied.

## Hard constraints (preserved, all pinned by tests)

- No financial formula / IDC / funding / debt / tax /
  depreciation changes
- No G20 / R99 / R102 promotion
- No Tailwind / Alpine / React / Vue / Svelte
- No schema / persistence migration
- No `ProjectInputsSchema` change
- No `use_construction_schedule_engine` flip
- No construction / C10 / R-PAR changes
- No manual_gearing debt sizing method
- No TUHO / Oborovo factory changes
- No `main_web.py` / `main_api.py` changes
- `rc1` SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4`
  verified unchanged

## Stop-after-report contract

- DRAFT PR — do NOT mark ready
- Do NOT merge — awaiting user review and explicit
  go-ahead
- After approval: implement manual_gearing OR move
  on (separate decision)

## Recommended next step (post-P1-B)

1. Review this PR
2. Decide: implement `manual_gearing` debt sizing
   method (Section 7 of design doc) OR move on with
   the current DSCR sculpt + label approach
3. OR pause the arc
4. OR continue with another read-only P1-X audit
   (e.g. a wiring audit for non-driver form fields
   like CIT rate, loss carryforward, CO2 price, etc.)

DO NOT START: C10, construction runtime promotion,
R-PAR, debt formula changes, tax, IDC, senior IDC,
depreciation, schema migration, manual_gearing,
Tailwind/Alpine.
