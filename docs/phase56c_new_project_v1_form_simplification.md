# Phase 56C — New Project v1 form simplification

## Goal

Simplify the inline New Project form so that creating a project asks only for
**core master data** (10 fields). The 11 detailed financial assumptions are
hidden with safe defaults and will be entered later in the Inputs sheet.

This is a runtime UI change, draft-only. User visual review is required before
merge.

## Scope of changes

### Templates

`app/templates/partials/workspace_shell.html` — the inline
`#panel-new-project` form is replaced with a v1 form:

| v1 master field | Type | Notes |
|---|---|---|
| `project_name` | text | kept, required |
| `spv_name` | text | **NEW** (lands in `baseline_snapshot`) |
| `country_market` | text | kept, required; label "Country / Market" |
| `project_type` | select | kept; label renamed to "Technology" (Solar/Wind) |
| `capacity_mw` | number | kept, required |
| `currency` | select | **NEW** (EUR/USD/HRK; default EUR) |
| `construction_start_date` | date | **NEW** (replaces manual `cod_date` as the primary input) |
| `construction_duration_months` | number | **renamed** from `construction_months` |
| `cod_date` | date | kept (still required input in 56C; will be derived in 56D) |
| `template_source` | select | kept; renders `{{ option.label }}` which carries `⚠️ Unvalidated` for generic |

The 11 detailed financial assumptions are still part of the form
submission — they are **hidden inputs** with safe defaults (empty strings
for required numerics, `"1.20"` for `target_dscr`):

```html
<div class="np-hidden-defaults" hidden aria-hidden="true">
  <input type="hidden" name="horizon_years" value="" />
  <input type="hidden" name="tariff_eur_mwh" value="" />
  <input type="hidden" name="ppa_term_years" value="" />
  <input type="hidden" name="p50_hours" value="" />
  <input type="hidden" name="opex_y1_keur" value="" />
  <input type="hidden" name="total_capex_keur" value="" />
  <input type="hidden" name="gearing_pct" value="" />
  <input type="hidden" name="interest_rate_pct" value="" />
  <input type="hidden" name="tenor_years" value="" />
  <input type="hidden" name="target_dscr" value="1.20" />
  <input type="hidden" name="construction_months" value="" />
</div>
```

Users fill in the real values in the Inputs sheet after the project is
created.

### Backend (`main_web.py`)

`_validate_new_project_payload` — the 11 detailed assumptions are now
**optional** (no error when missing/empty). They are still validated
**when present** so the legacy full-form path keeps working.

Master-data validation remains strict (still required):
- `project_name`
- `project_type` (must be in `PROJECT_TYPES`)
- `country_market`
- `capacity_mw`
- `cod_date` (still required in 56C; will be derived in 56D)

The route signature for `create_project_route` is **unchanged** — all
17 form fields are still accepted as `Form(...)` parameters. The
51M-1 golden characterization keeps passing.

### CSS (additive only)

`static/styles.css` — append a new section "Phase 56C: New Project v1
form helpers" defining `.np-helper`, `.np-warning`, `.np-hidden-defaults`.
Uses existing CSS variables with fallbacks. No `:root` variables added
or modified (count remains 5).

### No changes to

- `static/app.js`
- `app/waterfall_core.py`
- `app/project_factories.py`
- `app/runtime_impact_taxonomy.py`
- `app/persistence/*` (no schema/migration)
- `app/services/projects_create_service.py` (orchestration logic intact)
- `app/templates/partials/new_project_form.html` (the sidebar full
  detailed form is intentionally preserved — the user can still access
  all 17 fields via the sidebar)
- Any test fixtures, schema, or migration
- Any tab panel in workspace_shell.html (CAPEX, Inputs, etc.)
- Phase 56B changes (Help tab) — preserved intact

## What lands in `baseline_snapshot`

The new v1 form submits these additional fields into the
`baseline_snapshot` JSON column (no schema change required):

- `spv_name` (text, optional)
- `currency` (text, optional, default EUR)
- `construction_start_date` (date, optional)
- `construction_duration_months` (int, optional)

The 11 detailed assumptions are submitted as empty strings (or
`"1.20"` for `target_dscr`) and the user fills them in later.

`cod_date` remains in the form as a required input for 56C. Phase 56D
will:
- Mark the `cod_date` input as `readonly` in the form
- Compute `cod_date` server-side from `construction_start_date +
  construction_duration_months` in the create service
- Pass the derived value into the `baseline_snapshot`

## No-go copy treatment

The new `template_source` select already renders labels from
`NEW_PROJECT_TEMPLATE_OPTIONS`, which include `⚠️ Unvalidated · Derived
path` for generic templates. We add an explicit `np-warning` block
underneath:

> ⚠️ Generic templates are exploratory / unvalidated. They are not
> part of the trusted pilot evidence and should be reviewed
> independently before drawing conclusions.

TUHO and Oborovo templates do not carry the warning (they have parity
evidence against Excel).

## Forbidden changes (verified)

- No app/waterfall_core.py changes
- No app/project_factories.py changes
- No senior-debt CSV changes
- No financial model calculation changes
- No schema/migration changes
- No fixture changes
- No runtime_impact_taxonomy.py changes
- No frontend dependency changes
- No Tailwind/Alpine setup
- No broad CSS refactor
- No static/app.js changes
- No persistence schema changes
- No new persistence writes beyond existing project creation path
- No changes to run/save/scenario behavior except project creation form inputs

## Hard gates verified

- Only allowed template/CSS/backend-validation files modified
- No `static/app.js` changes
- No `app/waterfall_core.py` changes
- No `app/project_factories.py` changes
- No `app/runtime_impact_taxonomy.py` changes
- No `app/persistence/*` changes
- No `:root` CSS variable changes (count remains 5)
- No new forbidden UI claims
- No financial formula / model output changes
- No schema/migration changes
- rc1 (`b425a0708719eaa5e1d922b1008e5609758e0ad4`) untouched
- Draft-only — does not auto-merge
- 60 new tests added (`tests/test_phase56c_new_project_v1_form_simplification.py`)
- 51M-1 golden characterization still passes (150 tests)
- 51F / 52F / 53I / 54 / 55E-G / 56A / 56B all pass
- 1124 relevant tests pass total

## Test coverage

`tests/test_phase56c_new_project_v1_form_simplification.py` covers:

1. `TestV1MasterFieldsPresent` — all 10 master fields present in inline form
2. `TestDetailedAssumptionsHidden` — 11 detailed assumptions are hidden
   inputs (not visible)
3. `TestHiddenDefaults` — `np-hidden-defaults` block exists with all
   11 hidden inputs
4. `TestLabelRenames` — `project_type` label says "Technology",
   `construction_duration_months` label says "Construction duration"
5. `TestNewFields` — `spv_name` (optional), `currency` (EUR/USD/HRK
   with EUR default), `construction_start_date` (date type)
6. `TestTemplateSourceLabel` — uses `new_project_template_options`
   and includes an explicit `np-warning` for generic templates
7. `TestBackendValidationRelaxes` — 11 detailed assumptions use
   `optional_float` / `optional_int` in the validation function;
   `capacity_mw` and `cod_date` remain required
8. `TestRouteSignatureUnchanged` — `create_project_route` signature
   still has all 17 Form fields (51M-1 golden test stays green)
9. `TestSidebarFormUnchanged` — sidebar `new_project_form.html` keeps
   all 17 fields (users can still access the detailed form)
10. `TestScopeGuardrails` — `app.js`, `waterfall_core.py`,
    `project_factories.py`, `runtime_impact_taxonomy.py`,
    persistence migrations all unchanged
11. `TestCSSAdditive` — `.np-helper`, `.np-warning` styles added;
    `:root` count remains 5
12. `TestRc1Untouched` — rc1 SHA constant stable
13. `TestPersistenceUnchanged` — no persistence writes added; no
    financial model changes

## Manual visual review checklist

When reviewing the running app, please verify:

- [ ] Opening "New Project" shows the v1 form with 10 visible fields
- [ ] Field order: project_name, spv_name, country_market, project_type
      (labeled "Technology"), capacity_mw, currency, construction_start_date,
      construction_duration_months, cod_date, template_source
- [ ] "Technology" select shows only Solar / Wind
- [ ] "Currency" select defaults to EUR; USD and HRK are options
- [ ] "Start of Construction" is a date input
- [ ] "Construction Duration (months)" is a numeric input
- [ ] "COD Date" is still a required date input in 56C (will become
      derived/read-only in 56D)
- [ ] "Template" select shows the 4 options with the ⚠️ Unvalidated
      label for generic templates
- [ ] An explicit "exploratory / unvalidated" warning appears under
      the Template field
- [ ] No detailed financial assumption inputs are visible to the user
- [ ] Submitting the form creates the project (verifiable: redirect
      to new project, no validation errors)
- [ ] After project creation, the Inputs sheet allows entering the
      11 detailed assumptions
- [ ] Help tab (from 56B) still works
- [ ] State banner, governance cards, KPI grid, and all other tabs
      are unchanged
- [ ] No console errors / no JS errors / no network 404s

## Files changed (summary)

| File | Change | Lines |
|---|---|---|
| `app/templates/partials/workspace_shell.html` | Inline `#panel-new-project` form replaced with v1 (10 master + 11 hidden) | +60 / -25 |
| `main_web.py` | `_validate_new_project_payload`: 11 detailed assumptions now `optional_*` (still validated when present) | +28 / -11 |
| `static/styles.css` | Appended `.np-helper`, `.np-warning`, `.np-hidden-defaults` blocks (additive) | +34 / -0 |
| `tests/test_phase56c_new_project_v1_form_simplification.py` | New tests | +560 (new file) |
| `docs/phase56c_new_project_v1_form_simplification.md` | New doc | (this file) |
| `reports/phase56c_new_project_v1_form_simplification.json` | New report | (new file) |

## Stack: 56B → 56C → 56D

This PR is the **second** in the 56B → 56C → 56D UX cleanup stack. It is
based on the 56B branch head. **56B can be reviewed and merged
independently** of 56C and 56D; merging 56B does not block reviewing
56C and 56D in parallel. The recommended merge order is 56B → 56C → 56D.
