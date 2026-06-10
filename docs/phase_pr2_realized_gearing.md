# Phase PR2 — Realized Gearing KPI — Governance Doc

## Status

- **Type:** Read-only derived output KPI
  + Scenario Matrix row + relabelled
  input row.
- **Branch:** `post-m1-realized-gearing-kpi`
- **Base:** main @ `33564cce` (post-PR1
  merge, PR #606)
- **PR:** DRAFT only. Do NOT mark ready.
  Do NOT merge. Awaiting user review.
- **Goal:** Surface the **realized
  gearing** as a read-only output KPI so
  users can see the actual gearing ratio
  the DSCR-sculpt produced, distinct from
  the indicative gearing input.

## Definition

**Realized gearing = senior debt / total
CAPEX × 100** (read-only derived KPI)

The senior_debt value used here is the
DSCR-sculpt-produced senior debt amount
that the runtime has already computed;
this is NOT a new calculation, it is a
read-only reformulation of values that
the runtime already produces.

The realized gearing is **derived** (a
**derived** badge is rendered next to
the row), distinct from the indicative
gearing input which carries an
**input** badge.

## Why this completes S2

S2 established that user-supplied
gearing is INDICATIVE / reporting-only
and NOT a binding debt sizing driver
(debt is sized by DSCR sculpt).

After S2, the application explains that
gearing is indicative, but does not
clearly show the **realized** gearing
output. PR2 surfaces the realized
gearing output, completing the S2
contract:

- The user can see the **input** they
  entered (indicative gearing, with
  badge).
- The user can see the **output** the
  DSCR-sculpt produced (realized
  gearing, with derived badge).
- The distinction is visually clear in
  the Scenario Matrix (different badges,
  different section: Inputs vs. Outputs
  (KPIs)).

## Source of calculation

- **Helper:**
  `app/ui/project_context.py::_compute_realized_gearing_pct(senior_debt_keur, total_capex_keur)`
- **Inputs:**
  - `senior_debt_keur` — from
    `financing.fixed_debt_keur` (the
    runtime-computed DSCR-sculpt senior
    debt amount; this is a pre-existing
    value, NOT a new calculation)
  - `total_capex_keur` — from
    `capex.total_capex` (pre-existing
    value)
- **Output:** a `float | None` (None
  when total_capex is 0 / None /
  negative, or when senior_debt is None
  / negative). The em-dash fallback
  preserves the M1 UX for
  uninitialised projects.

## Where it is displayed

- **Scenario Matrix — Outputs (KPIs)
  section:** new KPI row labelled
  "Realized Gearing" with a
  "derived" badge and the formula
  reminder in the title tooltip
  ("Read-only derived KPI: realized
  gearing = senior debt / total CAPEX.
  NOT a binding driver.").
- **Scenario Matrix — Inputs section:
  Indicative Gearing row:** relabelled
  to "Indicative Gearing (input)" with
  an "input" badge and a tooltip
  explaining that the debt is sized by
  DSCR sculpt and that the
  "Realized Gearing" output below shows
  the actual senior_debt / total_CAPEX
  ratio.

## Confirmation no sizing formula changed

- ✅ No debt sizing formula change
- ✅ No DSCR sculpt semantics change
- ✅ No financial formula change
- ✅ No factory path change
  (`app/project_factories.py` SHA
  unchanged, verified by
  `TestNoFinancialFormulaChanges::test_factory_paths_sha_unchanged`)
- ✅ No `app/waterfall_core.py` change
  (SHA unchanged, verified by
  `TestNoFinancialFormulaChanges::test_waterfall_core_sha_unchanged`)
- ✅ No tax / depreciation / IDC change
- ✅ No construction / C10 / R-PAR change
- ✅ No R99 / R102 / G20 promotion
- ✅ No persistence schema migration
- ✅ No `static/app.js` change
- ✅ No Tailwind / Alpine / React / Vue /
  Svelte
- ✅ `use_construction_schedule_engine`
  remains False (verified by
  `TestPhaseInvariants::test_use_construction_schedule_engine_remains_false`)
- ✅ rc1 SHA
  `b425a0708719eaa5e1d922b1008e5609758e0ad4`
  preserved (verified by
  `TestPhaseInvariants::test_rc1_sha_resolvable`)

## S2 contract preserved

- ✅ S2 tests still pass under PR2
  (verified by
  `TestS2IndicativeGearingNotBound::test_s2_tests_still_pass`).
- The indicative gearing_pct input
  remains a reporting-only field; the
  debt is still sized by DSCR sculpt;
  the senior_debt_keur that
  `realized_gearing_pct` reads is
  identical to the senior_debt_keur the
  runtime already produces. PR2 is
  strictly a read-only reformulation.

## Files in PR2 (7)

### Production code (3)

- `app/ui/project_context.py` (MODIFIED)
  - New `realized_gearing_pct: float | None`
    field on `ProjectContext` dataclass
    (default `None`).
  - New helper
    `_compute_realized_gearing_pct(senior_debt_keur, total_capex_keur)`
    that returns the percentage or
    `None` for uninitialised inputs.
  - `_build_context_from_project_inputs`
    populates
    `realized_gearing_pct=...` using
    `financing.fixed_debt_keur` and
    `capex.total_capex`.
  - `_build_user_snapshot_context`
    populates
    `realized_gearing_pct=...` using
    `base.senior_debt_keur` and
    `total_capex_keur` (the snapshot
    uses the already-sculpted senior
    debt from the baseline).

- `app/ui/scenario_matrix.py` (MODIFIED)
  - New `KPI_ROWS` entry:
    `MatrixRow("Realized Gearing",
    ROW_KIND_KPI, "realized_gearing_pct",
    _fmt_pct)`.
  - Distinct from the indicative gearing
    INPUT row (`gearing_pct`,
    `ROW_KIND_INPUT`).

- `app/templates/partials/scenario_matrix.html`
  (MODIFIED)
  - New KPI row "Realized Gearing" in
    the Outputs (KPIs) section with
    `data-pr2-badge="realized-gearing"`
    and a "derived" badge label.
  - Relabelled input row "Indicative
    Gearing" → "Indicative Gearing
    (input)" with
    `data-pr2-badge="indicative-gearing"`
    and an "input" badge label.
  - Both rows preserve the M1
    `is defined and ... is not none`
    guard pattern (PR1 latent-bug
    fixup preserved).

### Tests (3 — 1 new + 2 cross-arc patches)

- `tests/test_phase_pr2_realized_gearing.py`
  (NEW) — 9 test classes, 27 tests
  - `TestRealizedGearingComputation` (8
    tests) — helper correctness
    (basic ratio, high ratio, low ratio,
    None for None / 0 / negative inputs)
  - `TestProjectContextField` (2 tests)
    — `realized_gearing_pct` field
    exists on ProjectContext, default
    is `None`
  - `TestScenarioMatrixKpiRow` (3 tests)
    — KPI row added, marked as KPI (not
    input), indicative gearing remains
    an input
  - `TestScenarioMatrixTemplate` (4
    tests) — template renders new row,
    relabelled input row, derived
    badge, no double-render of
    indicative gearing
  - `TestS2IndicativeGearingNotBound`
    (1 test) — S2 tests still pass
    under PR2 (smoke)
  - `TestPhaseInvariants` (3 tests) —
    rc1 SHA resolvable,
    `use_construction_schedule_engine`
    remains False, no forbidden-path
    changes
  - `TestNoFinancialFormulaChanges` (3
    tests) — factory paths / waterfall
    core SHA unchanged, realized gearing
    helper does not import any forbidden
    module
  - `TestS1S2S3M1PR1TestsPreserved` (1
    test) — all prior-phase tests pass
    under PR2 (smoke)
  - `TestRouteSmokePreserved` (1 test) —
    route smoke still passes under PR2
  - `TestFileScope` (1 test) — PR2
    touches only the expected files
    (with forward-allowlist for PR1
    file-scope post-merge)

- `tests/test_phase_pr1_form_timing_fields.py`
  (MODIFIED) — cross-arc test patch:
  PR1 `TestPR1FileScope` is forward-
  fixed to remove `assert not missing`
  (after PR1 is merged, the PR1 files
  are no longer in `git diff --name-only
  origin/main` because they are already
  on the base; the forward-compatible
  check is `assert not extra` only).

- `tests/test_phase_m1_scenario_matrix.py`
  (MODIFIED) — cross-arc test patch:
  M1 `TestM1FileScope` post_m1_followup
  allowlist extended to include the PR2
  follow-up files (forward-compatible
  contract extension).

### Docs (2)

- `docs/phase_pr2_realized_gearing.md`
  (this file)
- `reports/phase_pr2_realized_gearing.md`
  (NEW) — test counts, file-scope
  audit, pre-merge checklist

## What PR2 does NOT do (preserved, all pinned by tests)

- No debt sizing change
- No DSCR sculpt semantics change
- No financial formula change
- No factory path change
  (`app/project_factories.py` SHA
  preserved)
- No model / runtime change
  (`app/waterfall_core.py` SHA
  preserved, `app/waterfall_runner.py`
  not touched)
- No tax / depreciation / IDC change
- No construction / C10 / R-PAR change
- No `manual_gearing` debt sizing method
- No `min(gearing cap, sculpt)` blend
- No senior IDC
- No persistence schema migration
- No R99 / R102 / G20 promotion
- No `static/app.js` change
- No `main_web.py` change
- No `main_api.py` change
- No `app/services/projects_create_service.py`
  / `compare_service.py` /
  `download_service.py` /
  `run_service.py` /
  `save_run_service.py` change
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

## Roadmap (post-PR2)

1. **PR2** (this PR) — Realized gearing
   KPI (read-only derived output)
2. **PR3** — Taxonomy / brief alignment
   (next, awaiting user go-ahead)

`manual_gearing` is **not** on this
roadmap.

DO NOT START: PR3 until PR2 report is
delivered and reviewed. DO NOT START:
C10, construction runtime promotion,
R-PAR, debt formula changes, tax, IDC,
senior IDC, depreciation, schema
migration, manual_gearing, Tailwind/
Alpine, factory path changes, R99 /
R102 / G20 promotion.

## Stop-after-report contract

DRAFT PR only. Do NOT mark ready. Do
NOT merge. Awaiting user review and
explicit go-ahead before PR2 lands on
main.
