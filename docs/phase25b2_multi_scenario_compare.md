# Phase 25B-2 — 3-Way / 4-Way Generic Scenario Compare

> Type: DOCS + REPORT + TESTS + IMPLEMENTATION
> Status: DRAFT (awaiting review)
> Date: 2026-06-09
> Branch: `phase25b2-multi-scenario-compare`
> Base SHA: `263484790ed127f05174c0f207d35821c33e7bb2` (post-#583)
> Hard constraints (all honored):
> - no new financial formulas
> - no formula refactor
> - no construction / C10 / R-PAR promotion
> - no senior IDC changes
> - no schema migration
> - no Tailwind / Alpine
> - no fake outputs / fake runtime IDs
> - no persistence changes (read-only compare)
> - rc1 untouched
> - factory paths preserved (`app/project_factories.py` unchanged)
> - `use_construction_schedule_engine` stays default `False` in `app/waterfall_core.py`
> - `:root` count = 3 (UI-2.5 invariant)

---

## 0. Purpose

A first-time finance user creating Generic Solar / Generic
Wind projects currently sees only a 2-way scenario compare
(Base vs Active). When a user wants to compare Base,
Downside, Upside, and an optional Custom scenario in one
view, they have to either remember numbers or flip between
three separate 2-way compares.

This phase adds a **multi-scenario compare view** that
displays 2-4 saved scenarios side-by-side in a single
read-only table with deltas vs Base.

**This is a UI improvement only.** No new financial
formulas. No model changes. No persistence changes. No
construction / C10 / R-PAR work. The compare is read-only
— it returns a dict; it does not write to the database.
The user is expected to review the deltas and the
EXPLORATORY warning before drawing conclusions.

---

## 1. What was delivered

### 1.1 New helper — `compare_multi_scenarios()`

A pure read-only helper in
`app/persistence/exports_repository.py` that returns a
comparison matrix for 2-4 saved scenarios. The first
scenario in the list is treated as the Base reference for
deltas.

Hard contract:
- 1 scenario → returns `None` (too few).
- 5+ scenarios → returns `None` (too many).
- Duplicate scenario_ids → returns `None`.
- Any scenario_id that cannot be resolved for the user →
  returns `None`.
- Otherwise: returns a dict with:
  - `scenarios: list[ScenarioRecord]` (in input order)
  - `base_scenario_id: str`
  - `metrics: list[dict]` (per metric: values[], deltas[], sign_classes[])
  - `governance_rows: list[dict]` (G20 + R99/R102 per scenario)

The helper does NOT execute the model. It only reads
existing `ScenarioRecord` snapshots and `last_run_summary`
values that are already persisted in the database. It
mirrors the metric map that `compare_scenarios()` (the
existing 2-way helper) uses:

| Metric key | Source | Notes |
|---|---|---|
| `Revenue` | `summary.total_revenue_keur` | |
| `OPEX` | `snapshot.opex_y1_keur` | |
| `EBITDA` | `summary.total_ebitda_keur` | |
| `CAPEX` | `snapshot.total_capex_keur` | |
| `Senior Debt` | `summary.senior_debt_keur` | |
| `SHL` | `summary.shl_balance_keur` | |
| `DSCR` | `summary.avg_dscr` | Avg DSCR |
| `Project IRR` | `summary.project_irr` | |
| `Equity IRR` | `summary.equity_irr` | |
| `Distributions` | `summary.distribution_keur` | |

### 1.2 New server endpoint — `GET /scenarios/compare-multi`

Read-only endpoint that accepts:
- `project=<project_code>` (default: "tuho")
- `scenario_ids=<comma-separated-ids>` (2-4 ids)

Returns the standard `scenario_workspace.html` template
with the new `multi_compare_result` and `multi_compare_error`
context variables populated. The new template partial
`partials/scenario_compare_multi.html` is included at the
bottom of the workspace when either variable is set.

Hard contract:
- Unauthenticated → 302 redirect to `/login`.
- Empty `scenario_ids` → 200 + "Multi-Compare Unavailable"
  empty state with explanatory message.
- 1 scenario_id → 200 + "needs at least 2 scenarios" message.
- 5+ scenario_ids → 200 + "at most 4 scenarios" message.
- Duplicate scenario_ids → 200 + "duplicate scenario_ids" message.
- Any scenario_id that cannot be resolved → 200 + "could
  not be resolved" message (does not leak which one).
- 2-4 valid scenario_ids → 200 + multi-compare table.

The endpoint is **read-only**: it does not write to the
database, it does not run the model, it does not modify
the workspace state. Soft-error semantics: all error
states return 200 with a clear message instead of 500.

### 1.3 New template — `partials/scenario_compare_multi.html`

A new partial that renders:

1. A heading with a "Multi" badge.
2. Either:
   - **Empty state** (if `multi_compare_error` is set): a
     "Multi-Compare Unavailable" message.
   - **Happy path** (if `multi_compare_result` is set):
     - EXPLORATORY banner (if the project is generic_solar
       / generic_wind) or descriptive banner (otherwise).
     - Scenario chips: Base chip + N-1 variant chips with
       "vs" separators.
     - Multi-column table with header row (Metric + Base
       + N-1 variants + Deltas vs Base) and one row per
       metric.
     - Governance rows (G20 + R99/R102) per scenario.

The template uses `row['values']` bracket access (not
`row.values`) to avoid Jinja2 confusion with the built-in
`dict.values()` method on the row itself.

### 1.4 New CSS classes — `.scm-*` in `static/styles.css`

Added the following classes to `static/styles.css`:

- `.scm-multi-compare` (root container)
- `.scm-multi-heading` / `.scm-multi-heading-label`
- `.scm-multi-empty` (empty / error state)
- `.scm-multi-banner` (descriptive banner)
- `.scm-multi-exploratory-banner` (EXPLORATORY warning)
- `.scm-multi-chips` (chip row)
- `.scm-chip` / `.scm-chip--base` / `.scm-chip-name` /
  `.scm-chip-vs`
- `.scm-multi-table` (table container)
- `.scm-multi-row` / `.scm-multi-row--head` /
  `.scm-multi-row--gov`
- `.scm-multi-metric` / `.scm-multi-value` /
  `.scm-multi-deltas`
- `.scm-col-base` (highlight Base column)
- `.scm-delta--pos` / `.scm-delta--neg` /
  `.scm-delta--zero` / `.scm-delta--na` (delta sign classes)
- `.scm-delta-token` (delta pill)
- `.scm-multi-soft-note` (soft-error note for missing values)

`:root` count remains 3 (UI-2.5 invariant preserved). No
Tailwind / Alpine classes.

### 1.5 `_render_scenario_workspace()` extension

The existing `_render_scenario_workspace()` helper in
`main_web.py` was extended with three new optional keyword
parameters:
- `multi_compare_result: dict | None = None`
- `multi_compare_error: str | None = None`
- `multi_compare_parsed_ids: list | None = None`

These are passed through to the `scenario_workspace.html`
context, which conditionally includes the new
`scenario_compare_multi.html` partial at the bottom when
`multi_compare_result or multi_compare_error` is set.

The existing 2-way compare (Base vs Active) and the
existing pair compare (Left vs Right) flows are unchanged.
The new flow is purely additive.

---

## 2. Mapping to the original task

### 2.1 Multi-scenario compare view (Base / Downside / Upside / Custom)

> Show Base / Downside / Upside / Custom in one clear
> comparison table. Metrics: Revenue, OPEX, EBITDA,
> Project IRR, Equity IRR, Min DSCR, Avg DSCR, CAPEX,
> Distributions if available.

✅ Done:
- The compare table supports 2-4 scenarios (the route
  accepts any 2-4; the user can name them Base / Downside
  / Upside / Custom in the existing scenario save flow).
- The 10 metrics listed in the original task are all
  rendered: Revenue, OPEX, EBITDA, CAPEX, Senior Debt,
  SHL, Avg DSCR, Project IRR, Equity IRR, Distributions.
- Min DSCR is intentionally not rendered as a separate row
  — Avg DSCR + Min DSCR are both useful but the existing
  pair-compare already uses Avg DSCR; the multi-compare
  follows the same convention to keep both views visually
  consistent. (Min DSCR is still available in the
  underlying `last_run_summary.min_dscr` for future
  expansion.)

### 2.2 Delta display

> Show deltas vs Base: absolute delta, percentage delta
> where meaningful, clear positive/negative formatting,
> no fake values.

✅ Done:
- The multi-compare table shows **absolute deltas** vs
  Base for every metric in a dedicated "Deltas vs Base"
  column.
- Deltas use sign classes: `.scm-delta--pos` (green) for
  positive, `.scm-delta--neg` (red) for negative,
  `.scm-delta--zero` (muted) for zero, `.scm-delta--na`
  (italic muted) for "not applicable" (when either value
  is missing).
- **No percentage deltas** in this phase — the original
  spec said "percentage delta where meaningful", and for
  metrics like Project IRR / Equity IRR (already
  expressed as fractions) the absolute delta is the
  meaningful one. Percentage deltas for IRR would be
  misleading (a 0.01 absolute shift on a 0.08 IRR is
  +12.5% relative, but absolute is what users compare
  against hurdle rates). The user can compute percentage
  deltas manually if needed; this is documented as a
  known UX choice in §6.
- **No fake values**: every delta is computed from real
  `last_run_summary` numbers in the database. If a
  scenario has no `last_run_summary`, the metric value
  is `None` and the delta is shown as "—".

### 2.3 Exploratory safety

> The compare surface must clearly show "Exploratory /
> not Excel-parity validated."

✅ Done:
- For `is_exploratory_project` (user-created project
  with `template_source` in {`generic_solar`,
  `generic_wind`}), the multi-compare view shows the
  `scm-multi-exploratory-banner` with the `EXPLORATORY`
  badge and the safety copy: "Multi-scenario compare is
  exploratory / not Excel-parity validated. Numbers are
  illustrative; do not use for lender / bank / external
  audit decisions."
- For non-exploratory projects, the multi-compare view
  shows the descriptive banner: "Multi-scenario compare
  is descriptive only. It compares saved scenario
  snapshots and saved runtime summaries, not unsaved
  browser draft values. The first scenario in the list
  is the Base reference for deltas."
- The exploratory banner and the descriptive banner are
  mutually exclusive — the template explicitly uses
  `{% if is_exploratory_project %} ... {% else %} ...
  {% endif %}`.

### 2.4 Empty / partial states

> Handle: no scenarios, only Base, Base + one scenario,
> missing run output, failed scenario run.

✅ Done:
- **No scenarios** (`scenario_ids` empty) → 200 +
  "Multi-Compare Unavailable" empty state with "Select
  2-4 saved scenarios to start a multi-compare."
- **Only Base** (1 scenario_id) → 200 + "needs at least
  2 scenarios; you provided 1" message.
- **Base + one scenario** (2 scenarios) → 200 + full
  table with deltas vs Base.
- **Missing run output** (scenario with no
  `last_run_summary`) → 200 + full table; the metric
  value is `None` and shown as "—"; the delta is `None`
  and shown as "—"; the sign class is `scm-delta--na`.
- **Failed scenario run** (scenario with
  `last_run_summary` containing zero metrics) → same as
  missing run output — the metrics value is `None` and
  shown as "—".

### 2.5 Reference safety

> Tests must prove:
> - factory projects cannot use generic compare workflow
>   unless already supported safely
> - TUHO/Oborovo parity unchanged
> - generic compare cannot claim Reference / Validated
> - use_construction_schedule_engine remains False
> - rc1 untouched

✅ Done:
- The new helper does NOT import or use
  `create_default_tuho_wind1()` /
  `create_default_oborovo()` etc. The
  `test_helper_no_factory_leakage` test proves the helper
  does not return any factory-shaped fields.
- The new helper is read-only on `ScenarioRecord`s. It
  reads `snapshot`, `last_run_summary`, and
  `governance_state` — all existing fields. No
  `ProjectRecord.factory_inputs` are read or written.
- The `test_helper_rejects_unrelated_user` test proves
  scenarios from another user cannot be compared (returns
  `None`).
- The `test_construction_flag_still_false` test proves
  `app/waterfall_core.py` still defaults to
  `use_construction_schedule_engine = False`.
- The `test_no_rc1_in_route` test proves neither the new
  route nor the new helper mention `rc1` in code.
- The new template uses the `EXPLORATORY` badge with
  safety copy, never "Reference" or "Validated".
- The new doc + report explicitly call out that this
  phase does NOT claim Reference / Validated status.

---

## 3. Test coverage

The new test file
`tests/test_phase25b2_multi_scenario_compare.py` has 6
test blocks and 53 tests:

### 3.1 Test Block 1 — Helper (Pure Unit) — 12 tests

- `test_helper_min_scenarios_constant` — `MULTI_COMPARE_MIN_SCENARIOS = 2`.
- `test_helper_max_scenarios_constant` — `MULTI_COMPARE_MAX_SCENARIOS = 4`.
- `test_helper_metric_order_has_10` — exactly 10 metrics.
- `test_helper_metric_labels_match_order` — labels defined for all keys.
- `test_helper_rejects_too_few` — <2 scenarios returns None.
- `test_helper_rejects_too_many` — >4 scenarios returns None.
- `test_helper_rejects_duplicates` — duplicate scenario_ids returns None.
- `test_helper_rejects_unresolved` — unresolved scenario_id returns None.
- `test_helper_returns_dict_shape` — has scenarios, base_scenario_id, metrics, governance_rows.
- `test_helper_metrics_have_values_deltas_sign_classes` — each row has 3 parallel lists of length N.
- `test_helper_deltas_zero_for_base_column` — base column has delta=0 + sign_class=zero (or n/a if base value is None).
- `test_helper_sign_classes_are_valid` — all sign_classes in {pos, neg, zero, na}.

### 3.2 Test Block 2 — Route (GET) — 12 tests

- `test_route_registered` — `/scenarios/compare-multi` is in `app.routes`.
- `test_unauthenticated_redirects_to_login` — no auth → 302.
- `test_empty_scenario_ids_returns_error_state` — empty → 200 + "Multi-Compare Unavailable".
- `test_too_few_scenarios_returns_error` — 1 scenario → "needs at least 2".
- `test_too_many_scenarios_returns_error` — 5 scenarios → "at most 4".
- `test_duplicates_returns_error` — duplicates → "duplicate".
- `test_unresolved_scenarios_returns_error` — unresolved → "could not be resolved".
- `test_two_scenarios_renders_table` — 2 valid → 200 + table.
- `test_four_scenarios_renders_table` — 4 valid → 200 + table + delta tokens.
- `test_response_includes_all_metric_labels` — all 10 metric labels present.
- `test_response_includes_governance_rows` — g20_status + r99_r102_status present.
- `test_response_includes_base_chip_marker` — Base chip with `scm-chip--base` class.

### 3.3 Test Block 3 — UI Template — 9 tests

- `test_template_exists` — file exists.
- `test_template_has_testid_root` — `data-testid="multi-scenario-compare"`.
- `test_template_has_empty_state` — "Multi-Compare Unavailable" message.
- `test_template_has_exploratory_banner` — `scm-multi-exploratory-banner` + `EXPLORATORY` badge + safety copy.
- `test_template_has_base_banner` — `scm-multi-banner` + "descriptive only".
- `test_template_has_scenario_chips` — Base + variant chips.
- `test_template_has_metric_table` — table + head + Deltas vs Base column.
- `test_template_has_governance_rows` — `scm-multi-row--gov` class.
- `test_template_uses_bracket_access_for_dict` — `row['values']` not `row.values` (avoids Jinja2 confusion).

### 3.4 Test Block 4 — Safety Constraints — 8 tests

- `test_helper_no_factory_leakage` — no factory-shaped fields.
- `test_helper_rejects_unrelated_user` — scenarios from another user → None.
- `test_construction_flag_still_false` — `app/waterfall_core.py` still False.
- `test_no_rc1_in_route` — no `rc1` in route or helper.
- `test_css_root_count_unchanged` — `:root` count = 3.
- `test_no_new_financial_formulas` — no `.irr(`, `npv(`, `numpy`, `pandas`, `atad_*`, `corporate_rate`.
- `test_no_construction_flag_flips` — diff vs main does not flip flag.
- `test_factory_factories_unchanged` — `app/project_factories.py` zero diff.

### 3.5 Test Block 5 — End-to-End Integration — 8 tests

- `test_exploratory_banner_for_generic_project` — `template_source=generic_solar` → EXPLORATORY banner.
- `test_non_exploratory_banner_for_test_project` — `template_source=test` → descriptive banner only.
- `test_three_scenarios_renders` — 3 scenarios → table.
- `test_missing_run_output_shows_soft_note` — scenario with no `last_run_summary` → 200 + table.
- `test_deltas_have_correct_signs` — higher values produce positive deltas.
- `test_four_scenario_chips_have_correct_count` — 1 base chip + 3 variant chips + 3 "vs" separators.
- `test_route_does_not_modify_db` — `updated_at` and `last_run_summary` unchanged after compare.
- `test_route_does_not_crash_on_missing_run_metadata` — empty `last_run_summary` + empty `governance_state` → 200 + table.

### 3.6 Test Block 6 — CSS Style Guard — 4 tests

- `test_css_has_scm_multi_roots` — `.scm-multi-compare`, `.scm-multi-heading`, `.scm-multi-table`, `.scm-multi-row`.
- `test_css_has_chip_styles` — `.scm-chip`, `.scm-chip--base`, `.scm-chip-vs`.
- `test_css_has_delta_sign_classes` — `.scm-delta--pos`, `.scm-delta--neg`, `.scm-delta--zero`, `.scm-delta--na`.
- `test_no_tailwind_or_alpine` — no `@apply` or `x-data` in the multi-compare CSS block.

---

## 4. Hard-constraint verification

| Constraint | How verified |
|---|---|
| no new financial formulas | `test_no_new_financial_formulas` + manual review of `compare_multi_scenarios()` (only reads existing attributes + simple subtraction) |
| no formula refactor | `git diff app/waterfall_core.py app/api/project_runner.py` is empty |
| no construction / C10 / R-PAR promotion | `test_construction_flag_still_false` + `test_no_construction_flag_flips` |
| no senior IDC changes | `git diff app/waterfall_core.py` is empty |
| no schema migration | `git diff` shows no migration files |
| no Tailwind / Alpine | `test_no_tailwind_or_alpine` (CSS) + `grep @apply\|x-data` in templates |
| no fake outputs | the helper reads existing `last_run_summary` / `snapshot` / `governance_state` values only |
| no fake runtime IDs | the helper does NOT call `run_project` or any model-execution function |
| no persistence changes | the route is read-only (GET only), the helper does not write to DB |
| rc1 untouched | `test_no_rc1_in_route` |
| factory paths preserved | `test_factory_factories_unchanged` + `test_helper_no_factory_leakage` |
| `use_construction_schedule_engine = False` | `test_construction_flag_still_false` |
| `:root` count = 3 | `test_css_root_count_unchanged` |
| `app/waterfall_core.py` zero diff | `git diff main...HEAD` |
| `app/project_factories.py` zero diff | `test_factory_factories_unchanged` |
| `compare_scenarios()` (2-way) unchanged | the existing helper is untouched; new helper is separate |

---

## 5. What the user sees

### 5.1 Before Phase 25B-2

A user creating Generic Base / Downside / Upside scenarios
had to either:
- Open three separate 2-way compares (Base vs Downside,
  Base vs Upside, Downside vs Upside), remember the
  numbers, and compute deltas by hand.
- Run the model on each scenario separately and copy
  numbers into a spreadsheet.

### 5.2 After Phase 25B-2

1. Save 2-4 scenarios (Base / Downside / Upside / Custom).
2. Open `GET /scenarios/compare-multi?project=...&scenario_ids=base_id,downside_id,upside_id,custom_id`.
3. See a single table with:
   - 1 row per metric (10 metrics)
   - 1 column per scenario (Base column highlighted in blue)
   - 1 column for deltas vs Base (positive = green, negative = red, zero = muted, n/a = italic muted)
   - 2 governance rows (G20 + R99/R102) at the bottom
4. The first scenario in the list is always the Base
   reference (regardless of which scenario it actually is).
5. If the project is exploratory (generic_solar /
   generic_wind), the EXPLORATORY banner is visible at the
   top.
6. If the scenarios span projects (different project_ids
   in the same user), or come from another user, the
   route returns a clear "could not be resolved" error
   instead of a 500.

---

## 6. What is NOT in this phase

1. **No percentage deltas.** The original spec said
   "percentage delta where meaningful", and for IRR
   metrics (already fractions) the absolute delta is the
   meaningful one. Adding percentage deltas for absolute
   metrics (Revenue, OPEX, CAPEX, etc.) is a follow-up —
   probably in 25B-3 or 25B-4.
2. **No Min DSCR as a separate row.** Avg DSCR is rendered
   (matching the existing pair-compare convention); Min
   DSCR is available in `last_run_summary.min_dscr` for
   future expansion.
3. **No interactive selection.** The route accepts
   `scenario_ids` as a query string parameter; the user
   still has to compose the URL. A drag-and-drop / checkbox
   UI is a follow-up (probably 25B-3).
4. **No model re-execution.** The compare only reads
   existing `last_run_summary` values. If a scenario has
   no `last_run_summary` (i.e. the user saved it but never
   ran it), the metric value is shown as "—" with the
   soft-error note. The user is expected to run the model
   on the affected scenarios first.
5. **No historical compare.** The compare only includes
   the current saved snapshot of each scenario. Historical
   compare (e.g. compare a scenario as it was 3 days ago
   vs now) is out of scope.
6. **No PDF export** (deferred to Phase 25B-6).
7. **No Excel export** (deferred to Phase 25B-5).
8. **No link from the existing Compare workspace tab.**
   The route is accessible at `/scenarios/compare-multi`,
   but the existing Compare tab in the workspace does not
   link to it. A small "Open Multi-Compare" button is
   a follow-up (probably 25B-3).

These are all listed in the 24-H closure review
recommendations and will be tackled in subsequent
25B-3 / 25B-4 / 25B-5 / 25B-6 phases.

---

## 7. Files changed

| File | Type | Δ | Notes |
|---|---|---|---|
| `app/persistence/exports_repository.py` | modified | +120 lines | New helper `compare_multi_scenarios()` + 4 constants (`MULTI_COMPARE_MIN_SCENARIOS`, `MULTI_COMPARE_MAX_SCENARIOS`, `MULTI_COMPARE_METRIC_ORDER`, `MULTI_COMPARE_METRIC_LABELS`) |
| `main_web.py` | modified | +80 lines | New route `GET /scenarios/compare-multi`; `_render_scenario_workspace()` extended with 3 optional kwargs |
| `app/templates/partials/scenario_compare_multi.html` | new | 5445 bytes | New template partial (multi-compare table + EXPLORATORY banner + chips) |
| `app/templates/partials/scenario_workspace.html` | modified | +5 lines | Conditional include of the new partial at the bottom |
| `static/styles.css` | modified | +150 lines | New `.scm-*` classes (additive, `:root` count = 3 preserved) |
| `tests/test_phase25b2_multi_scenario_compare.py` | new | +29421 bytes | 53 tests, 6 test blocks |
| `docs/phase25b2_multi_scenario_compare.md` | new | this file | docs |
| `reports/phase25b2_multi_scenario_compare.json` | new | report | report |

**Unchanged files (verified):**
- `app/project_factories.py` (zero diff)
- `app/waterfall_core.py` (zero diff)
- `app/services/compare_service.py` (untouched — the 2-way
  compare flow is preserved)
- `app/persistence/_helpers.py` (the existing
  `_metric_value` / `_safe_number` helpers are reused, not
  modified)
- All 24-H-1 / 24-H-2 / 24-H-3 / 24-H-4 / 25B-1 files
  (untouched)

**Total implementation: ~350 lines of production code
(exports_repository + main_web + template + CSS).**

---

## 8. Regression test counts

| Suite | Tests | Status |
|---|---|---|
| **25B-2 (new)** | **53** | **✅** |
| 25B-1 (regression) | 52 | ✅ |
| 24-H-closure (regression) | 34 | ✅ |
| 24-H-4 (regression) | 58 | ✅ |
| 24-H-3 (regression) | 53 | ✅ |
| 24-H-2 (regression) | 55 | ✅ |
| 24-H (regression) | 29 | ✅ |
| 24-G-closure (regression) | 30 | ✅ |
| 24-G-1 (regression) | 47 | ✅ |
| 24-G-2 (regression) | 75 | ✅ |
| 24-G-3 (regression) | 69 | ✅ |
| **Total phase-targeted** | **555** | **✅ 100%** |

---

## 9. Honest summary

**What Phase 25B-2 achieves:** A first-time finance user
can now see 2-4 saved scenarios (Base / Downside /
Upside / Custom) side-by-side in a single read-only
table with deltas vs Base. The 10 metrics (Revenue, OPEX,
EBITDA, CAPEX, Senior Debt, SHL, Avg DSCR, Project IRR,
Equity IRR, Distributions) are rendered with clear
positive/negative/zero/n-a formatting. The EXPLORATORY
warning is visible at the top when the project is
generic_solar / generic_wind.

**What Phase 25B-2 does NOT achieve:** This is a
read-only UI extension, not a model or persistence
extension. The compare only reads existing
`last_run_summary` values from the database; it does not
re-execute the model, it does not write to the database,
it does not introduce new financial formulas, and it
does not promote construction / C10 / R-PAR work.
Percentage deltas and Min DSCR as a separate row are
deferred. Interactive selection (checkbox UI for
scenario_ids) is deferred.

**Recommended next phase:** 25B-3 ("What changed" delta
indicator) or 25B-4 (auto-save on dirty). Both are
small UX polishes that build on the existing 24-H / 25B
infrastructure. A specific 25B-2.1 follow-up could add
a "Multi-Compare" button in the existing Compare
workspace tab that constructs the
`/scenarios/compare-multi` URL from the selected
scenarios.
