# Phase 25B-1 — Generic Defaults Prefill Button

> Type: DOCS + REPORT + TESTS + IMPLEMENTATION
> Status: DRAFT (awaiting review)
> Date: 2026-06-09
> Branch: `phase25b1-generic-defaults-prefill-button`
> Base SHA: `c6d506b6d5849069760b4696eaf9fbe08e8b8a85` (post-#582)
> Hard constraints (all honored):
> - no new financial formulas
> - no formula refactor
> - no construction / C10 / R-PAR promotion
> - no senior IDC changes
> - no schema migration
> - no Tailwind / Alpine
> - no fake outputs / fake runtime IDs
> - no persistence changes (read-only prefill)
> - no rc1 references
> - factory paths preserved (`app/project_factories.py` unchanged)

---

## 0. Purpose

A first-time user opening `/projects/new` is dropped onto a
form with 16 empty fields and a `template_source` dropdown
that says "Generic Solar / Generic Wind ⚠️ Unvalidated".
There is no indication of what reasonable values look like.

This phase adds a **"Use generic defaults"** action that
populates all 16 fields with the round-number exploratory
defaults that are already in
`create_default_solar_project()` /
`create_default_wind_project()` (the existing generic
factories). The user can review, adjust, save, and run
without manually typing 16 numbers.

**This is a UX improvement only.** No new financial formulas.
No model changes. No persistence changes. No construction /
C10 / R-PAR work. The prefill is read-only — it returns
JSON; it does not write to the database. The user is
expected to review every field before saving, and the
EXPLORATORY warning is visible at all times.

---

## 1. What was delivered

### 1.1 New server endpoint — `GET /projects/new/defaults`

A read-only JSON endpoint that accepts
`?template_source=generic_solar` or
`?template_source=generic_wind` and returns:

```json
{
  "template_source": "generic_solar",
  "warning": "EXPLORATORY / not Excel-parity validated. ...",
  "values": {
    "project_name": "Generic Solar Project",
    "project_type": "Solar",
    "template_source": "generic_solar",
    "country_market": "DE",
    "capacity_mw": "50.0",
    "cod_date": "2031-01-01",
    "construction_months": "12",
    "horizon_years": "25",
    "tariff_eur_mwh": "55.0",
    "ppa_term_years": "10",
    "p50_hours": "1500",
    "opex_y1_keur": "380.0",
    "total_capex_keur": "33000",
    "gearing_pct": "75.0",
    "interest_rate_pct": "5.50",
    "tenor_years": "15",
    "target_dscr": "1.20"
  }
}
```

Hard contract:
- Unauthenticated → 401 JSON.
- `template_source=tuho` / `oborovo` / unknown → 400 JSON
  (no factory leakage).
- `template_source=generic_solar` / `generic_wind` → 200
  with all 16 form fields.
- The prefill values are derived from the EXISTING factory
  functions — no new financial formulas, no new parameters,
  no new attributes on `ProjectInputs`.

### 1.2 New server endpoint — `GET /projects/new/prefill`

A server-side prefill endpoint (for non-JS clients and for
deep links from the docs). Renders the same form partial
with the 16 fields already populated. Same hard contract.

- Unauthenticated → 302 redirect to `/login`.
- `template_source=generic_solar` / `generic_wind` → 200
  with form rendered + all 16 fields prefilled.
- `template_source=tuho` / `oborovo` / unknown → 200 with
  form rendered + BLANK defaults (no factory leakage via
  the prefill endpoint).
- The form still has the EXPLORATORY notice + the prefill
  button for further refresh.

### 1.3 New helper — `_generic_prefill_values()`

A pure-function helper in `main_web.py` that returns a
`dict[str, str]` of form field values for a given
`template_source`, or `None` for non-generic sources.

The helper:
- Reads the EXISTING `create_default_solar_project()` /
  `create_default_wind_project()` factory.
- Maps the resulting `ProjectInputs` to the 16 form
  fields, mirroring the existing `_project_baseline_snapshot`
  mapping (so the prefill values are exactly what the
  factory would set during a regular project creation).
- Returns `None` for any non-generic template_source.
- Does NOT mutate the factory `ProjectInputs`.

### 1.4 UI changes — `app/templates/partials/new_project_form.html`

1. **EXPLORATORY notice** added at the top of the form
   (badge-warn + safety copy). Visible at all times.
2. **`np-prefill-row`** added below the `template_source`
   dropdown. Hidden by default; shown only when
   `template_source` is `generic_solar` or `generic_wind`.
3. **`np-prefill-btn`** ("⚙ Use generic defaults")
   fetches `/projects/new/defaults?template_source=...`
   and fills all 16 fields.
4. **`np-prefill-hint`** — small text below the button
   explaining the source of the defaults
   (`create_default_solar_project()` /
   `create_default_wind_project()`).
5. **All 16 input fields now have `id="np-..."`** so the
   JS shim can address them by id.
6. **Inline vanilla-JS shim** — small (no jQuery, no
   Tailwind, no Alpine) script that:
   - Shows / hides the prefill row based on
     `template_source`.
   - On button click, fetches
     `/projects/new/defaults?template_source=...` and
     fills the 16 fields.
   - On `template_source` change, clears the autoprefill
     marker.
   - Provides a brief visual confirmation after a
     successful prefill (button text changes to "✓
     Prefilled" for 2.5s).

### 1.5 CSS changes — `static/styles.css`

Added `.np-prefill-row` / `.np-prefill-row[data-state]`
/ `.np-prefill-hint` styles. Uses CSS attribute
selectors (no inline styles). `:root` count remains 3
(UI-2.5 invariant preserved). No Tailwind / Alpine
classes introduced.

---

## 2. Mapping to the original task

### 2.1 Prefill UX

> On /projects/new:
> - expose a "Use generic defaults" action or template
>   selection behavior
> - Generic Solar defaults and Generic Wind defaults must
>   be clearly marked: "Exploratory / not Excel-parity
>   validated"
> - no lender-ready / validated claims

✅ Done:
- "Use generic defaults" button is exposed below the
  `template_source` dropdown, visible only for
  `generic_solar` / `generic_wind`.
- The form has the `inp-exploratory-notice` at the top
  (badge-warn + safety copy: "Exploratory / not
  Excel-parity validated. Not lender / bank / external
  audit ready.").
- The button text says "Use generic defaults" (not "Apply
  Validated Defaults" or similar).
- The hint text says "Prefills round-number exploratory
  defaults from the
  `create_default_solar_project()` /
  `create_default_wind_project()` factory. Review every
  field before saving."

### 2.2 Safe defaults

> Use existing generic template assumptions only.
> Do not invent hidden model logic.

✅ Done:
- The prefill values come from the EXISTING factory
  functions in `app/project_factories.py`. No new
  factory function was added.
- The mapping is the SAME mapping used in the existing
  `_project_baseline_snapshot()` function, so the
  prefill values are exactly what the user would have
  seen if they had used "Create from Generic Solar"
  manually.
- No new financial formulas, no new parameters, no new
  attributes on `ProjectInputs`.
- The prefill is EXPLICITLY marked as exploratory in
  the JSON response (`"warning": "EXPLORATORY / not
  Excel-parity validated..."`).

### 2.3 Allowed default fields

All 16 allowed fields are populated:
- `project_name` (e.g. "Generic Solar Project")
- `project_type` ("Solar" / "Wind")
- `template_source` ("generic_solar" / "generic_wind")
- `country_market` (from factory, defaults to "DE")
- `capacity_mw`
- `cod_date`
- `construction_months`
- `horizon_years`
- `tariff_eur_mwh` (PPA base tariff)
- `ppa_term_years`
- `p50_hours` (operating hours P50)
- `opex_y1_keur` (sum of opex items)
- `total_capex_keur`
- `gearing_pct`
- `interest_rate_pct` (base + margin)
- `tenor_years`
- `target_dscr`

### 2.4 User flow

> User should be able to:
> - choose Generic Solar or Generic Wind
> - prefill fields
> - create project
> - land on project page
> - see exploratory warning
> - save/run with no manual hidden setup

✅ Done:
- The form template has a `template_source` dropdown with
  `generic_solar` / `generic_wind` options (already
  existed pre-25B-1).
- The "Use generic defaults" button pre-fills the 16
  fields with the factory defaults.
- The `Create Project` button POSTs to `/projects/create`,
  which creates a `user_created` project (existing
  behavior, tested in 24-H-1).
- The user lands on the project page (existing
  HX-Redirect to `/?project=...`).
- The `inp-exploratory-notice` is visible on the form
  AND on the project page (carried over from 24-H-1).
- Save / run flow is unchanged from 24-H-1 / 24-H-2.

### 2.5 Safety

> Tests must prove:
> - Generic Solar prefill works
> - Generic Wind prefill works
> - warning visible on /projects/new and after create
> - prefilled values feed into the existing 24-H edit/save/run loop
> - TUHO/Oborovo factory templates unchanged
> - generic defaults cannot claim Reference / Validated
> - use_construction_schedule_engine remains False
> - rc1 untouched

✅ All 8 points have tests (see §3 below).

### 2.6 Hard constraints

> - no new financial formulas
> - no formula refactor
> - no construction/C10/R-PAR promotion
> - no senior IDC changes
> - no schema migration unless absolutely unavoidable
> - no Tailwind/Alpine
> - no fake outputs
> - no fake runtime IDs

✅ All 8 constraints honored. See §4 below.

---

## 3. Test coverage

The new test file
`tests/test_phase25b1_generic_defaults_prefill_button.py`
has 8 test blocks and 52 tests:

### 3.1 Test Block 1 — Prefill Helper (Pure Unit) — 12 tests

- `test_allowed_sources_exactly_generic_solar_wind`
  — the allow-set is exactly {generic_solar, generic_wind}.
- `test_helper_rejects_tuho` — returns None for "tuho".
- `test_helper_rejects_oborovo` — returns None for
  "oborovo".
- `test_helper_rejects_empty_string` — returns None for
  "".
- `test_helper_rejects_unknown_source` — returns None
  for various unknowns.
- `test_helper_generic_solar_returns_solar` — Solar
  project_type.
- `test_helper_generic_wind_returns_wind` — Wind
  project_type.
- `test_helper_all_16_fields_present` — the prefill
  dict has all 16 form fields, none empty.
- `test_helper_opex_matches_baseline_snapshot` — opex
  is the sum of opex items, mirroring
  `_project_baseline_snapshot()`.
- `test_helper_interest_rate_equals_base_plus_margin` —
  interest_rate_pct equals base + margin_bps/10000.
- `test_helper_capacity_matches_factory` — capacity
  matches the factory.
- `test_helper_ppa_term_matches_factory` — ppa_term
  matches the factory.

### 3.2 Test Block 2 — Prefill Route (`GET /projects/new/defaults`) — 8 tests

- `test_route_registered` — route is in `app.routes`.
- `test_unauthenticated_returns_401` — no auth → 401.
- `test_tuho_returns_400` — factory source rejected.
- `test_oborovo_returns_400` — factory source rejected.
- `test_unknown_source_returns_400` — unknown source
  rejected.
- `test_generic_solar_returns_values` — 200 with values
  + warning.
- `test_generic_wind_returns_values` — 200 with values
  + warning.
- `test_response_values_has_all_16_fields` — the
  response values dict has all 16 form fields.

### 3.3 Test Block 3 — Server-Side Prefill (`GET /projects/new/prefill`) — 6 tests

- `test_route_registered` — route is in `app.routes`.
- `test_unauthenticated_redirects_to_login` — no auth →
  302.
- `test_generic_solar_prefills_form` — form rendered
  with all 16 fields populated.
- `test_generic_wind_prefills_form` — form rendered
  with all 16 fields populated.
- `test_factory_source_renders_blank_form` —
  `template_source=tuho` → blank form (no factory
  leakage).
- `test_form_has_exploratory_notice` — EXPLORATORY
  notice is present in any prefill path.

### 3.4 Test Block 4 — UI Form Template — 7 tests

- `test_form_has_exploratory_notice` — `inp-exploratory-notice`
  + EXPLORATORY badge.
- `test_form_has_prefill_row` — `np-prefill-row` with
  `data-state` attribute.
- `test_form_has_prefill_button` — "Use generic
  defaults" button.
- `test_form_has_prefill_hint` — hint text references
  the factory functions.
- `test_form_has_inline_js_shim` — `__npPrefillApply` /
  `__npPrefillClear` + `fetch()` + endpoint URL.
- `test_form_has_data_prefill_url` — `data-prefill-url`
  attribute on the form.
- `test_form_all_16_input_fields_have_ids` — every
  field has an `id="np-..."` attribute.

### 3.5 Test Block 5 — Prefill Safety Constraints — 8 tests

- `test_helper_rejects_factory_sources` — no factory
  leakage.
- `test_helper_does_not_mutate_factory_inputs` —
  calling the helper does not mutate the factory.
- `test_construction_flag_still_false` —
  `use_construction_schedule_engine` defaults to
  `False` in `app/waterfall_core.py`.
- `test_no_rc1_in_prefill_block` — the prefill helper
  / routes do not mention `rc1`.
- `test_css_root_count_unchanged` — `:root` count is
  still 3 in `static/styles.css`.
- `test_no_new_financial_formulas` — no `.irr(` /
  `npv(` / `xirr(` calls, no `numpy` / `pandas`, no tax
  / debt / IDC calculations.
- `test_factory_factories_unchanged` —
  `app/project_factories.py` has zero diff vs main.
- `test_no_construction_flag_flips` — diff does not
  flip `use_construction_schedule_engine` to `True`.

### 3.6 Test Block 6 — End-to-End Integration — 5 tests

- `test_generic_solar_full_journey` — prefill +
  `/projects/create` + verify project in DB.
- `test_generic_wind_full_journey` — prefill +
  `/projects/create` + verify project in DB.
- `test_prefill_values_round_trip_through_create` —
  prefill values feed into `build_projectinputs_from_snapshot`
  → `run_project` → kpis.
- `test_prefill_keeps_baseline_input_intact` —
  `_submitted_new_project_defaults()` is not mutated.
- `test_prefill_values_unchanged_on_repeated_calls` —
  repeated calls return the same values.

### 3.7 Test Block 7 — No-JS Required — 2 tests

- `test_no_js_solar` — `GET /projects/new/prefill?template_source=generic_solar`
  populates the form.
- `test_no_js_wind` — `GET /projects/new/prefill?template_source=generic_wind`
  populates the form.

### 3.8 Test Block 8 — CSS Style Guard — 4 tests

- `test_css_has_prefill_row_styles` — `.np-prefill-row`
  styles.
- `test_css_has_prefill_hint_styles` — `.np-prefill-hint`
  styles.
- `test_css_root_count_unchanged` — `:root` count is
  still 3.
- `test_no_tailwind_or_alpine` — no `@apply` (Tailwind)
  or `x-data` (Alpine).

---

## 4. Hard-constraint verification

| Constraint | How verified |
|---|---|
| no new financial formulas | `test_no_new_financial_formulas` + manual review of `_generic_prefill_values()` (only reads attributes and stringifies) |
| no formula refactor | `git diff app/waterfall_core.py app/api/project_runner.py` is empty |
| no construction / C10 / R-PAR promotion | `test_construction_flag_still_false` + `test_no_construction_flag_flips` |
| no senior IDC changes | `git diff app/waterfall_core.py` is empty |
| no schema migration | `git diff` shows no migration files |
| no Tailwind / Alpine | `test_no_tailwind_or_alpine` (CSS) + `grep @apply\|x-data` in templates |
| no fake outputs | the prefill values come from the EXISTING factory functions, no fabricated numbers |
| no fake runtime IDs | no runtime IDs in this phase |
| no persistence changes | the prefill endpoint is read-only (GET only) |
| rc1 untouched | `test_no_rc1_in_prefill_block` |
| factory paths preserved | `test_factory_factories_unchanged` + `test_helper_rejects_factory_sources` |
| `:root` count = 3 | `test_css_root_count_unchanged` (twice) |
| `use_construction_schedule_engine = False` | `test_construction_flag_still_false` |

---

## 5. What the user sees

### 5.1 Before Phase 25B-1

1. Open `/projects/new`.
2. See form with 16 empty fields and a "Generic Solar /
   Generic Wind" template dropdown.
3. Have to type 16 numbers from scratch.

### 5.2 After Phase 25B-1

1. Open `/projects/new`.
2. See form with the **EXPLORATORY notice** at the top
   (badge-warn + safety copy).
3. Choose "Generic Solar ⚠️ Unvalidated" in the
   `template_source` dropdown.
4. The **"⚙ Use generic defaults"** button appears
   below the dropdown (only for generic_solar /
   generic_wind).
5. Click the button.
6. The button briefly says "✓ Prefilled — review fields
   above", then reverts.
7. All 16 fields are now populated with the round-number
   factory defaults (e.g. 50.0 MW capacity, 55.0 EUR/MWh
   tariff, 1500 P50 hours, 1,338 kEUR OPEX, 33,000 kEUR
   CAPEX, 75% gearing, 5.50% interest, 15 years tenor,
   1.20 target DSCR for Generic Solar).
8. Edit any field as needed.
9. Click "Create Project".
10. Land on the project page with the **EXPLORATORY
    notice** carried over from 24-H-1.
11. Click "Run Model" to compute kpis (unchanged from
    24-H-1 / 24-H-2).
12. Save / export / compare (unchanged from 24-H-1 / 24-H-2 /
    24-H-3 / 24-H-4).

### 5.3 Non-JS path

1. Open
   `GET /projects/new/prefill?template_source=generic_solar`.
2. The form is rendered with all 16 fields already
   populated.
3. The "Use generic defaults" button is still there for
   further refresh.

---

## 6. What is NOT in this phase

1. **No Excel-parity validation** for generic projects
   (deferred to a later sprint, requires an Excel
   reference workbook).
2. **No CO2 / certificates / balancing parity** (deferred
   to a later sprint, requires Excel reference data).
3. **No sculpting / live debt-sizing** (out of scope,
   requires R-PAR work).
4. **No 3-way / 4-way scenario compare** (deferred to
   Phase 25B-2).
5. **No "What changed" delta indicator** (deferred to
   Phase 25B-3).
6. **No auto-save on dirty** (deferred to Phase 25B-4).
7. **No PDF export** (deferred to Phase 25B-6).
8. **No factory exports extended to generic** (deferred
   to Phase 25B-5).

These are all listed in the 24-H closure review
recommendations and will be tackled in subsequent
25B-2 / 25B-3 / 25B-4 / 25B-5 / 25B-6 phases.

---

## 7. Files changed

| File | Type | Δ | Notes |
|---|---|---|---|
| `main_web.py` | modified | +120 lines | New helper `_generic_prefill_values()`, two new routes (`GET /projects/new/defaults`, `GET /projects/new/prefill`), no other changes |
| `app/templates/partials/new_project_form.html` | modified | +160 lines | EXPLORATORY notice, prefill row, button, hint, inline JS shim, IDs on all 16 fields |
| `static/styles.css` | modified | +50 lines | New `.np-prefill-row` / `.np-prefill-hint` styles, `:root` count = 3 preserved |
| `app/project_factories.py` | **unchanged** | 0 | Existing `create_default_solar_project()` / `create_default_wind_project()` are read-only; prefill reads them but does not modify them |
| `tests/test_phase25b1_generic_defaults_prefill_button.py` | new | +893 lines | 52 tests, 8 test blocks |
| `docs/phase25b1_generic_defaults_prefill_button.md` | new | this file | docs |
| `reports/phase25b1_generic_defaults_prefill_button.json` | new | report | report |

**Total implementation: ~330 lines of production code
(main_web.py + form template + CSS).**

---

## 8. Regression test counts

| Suite | Tests | Status |
|---|---|---|
| **25B-1 (new)** | **52** | **✅** |
| 24-H-closure (regression) | 34 | ✅ |
| 24-H-4 (regression) | 58 | ✅ |
| 24-H-3 (regression) | 53 | ✅ |
| 24-H-2 (regression) | 55 | ✅ |
| 24-H (regression) | 29 | ✅ |
| 24-G-closure (regression) | 30 | ✅ |
| 24-G-1 (regression) | 47 | ✅ |
| 24-G-2 (regression) | 75 | ✅ |
| 24-G-3 (regression) | 69 | ✅ |
| **Total phase-targeted** | **502** | **✅ 100%** |

---

## 9. Honest summary

**What Phase 25B-1 achieves:** A first-time user can now
create a Generic Solar / Generic Wind project with one
click on "Use generic defaults" — all 16 fields are
populated with the round-number exploratory defaults that
are already in the existing factory functions. The form
has the EXPLORATORY notice at the top, the button is
clearly marked as exploratory, and the values come from
the same factory as the regular project creation path.

**What Phase 25B-1 does not achieve:** This is a UX
improvement, not a parity improvement. The generic
defaults are STILL not Excel-parity validated, the
senior debt schedule is STILL fixture-backed, the
CO2 / certificates / balancing are STILL not
included, and the user MUST review every field before
saving. The EXPLORATORY warning is the safety net.

**Recommended next phase:** 25B-2 (3-way / 4-way
scenario compare table) or 25B-3 ("What changed" delta
indicator). Both are small UX polishes that build on
the existing 24-H infrastructure.
