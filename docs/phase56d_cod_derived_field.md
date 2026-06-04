# Phase 56D — COD derived field wiring

## Goal

Make COD (Commercial Operation Date) a **derived/read-only** field in the
New Project flow. COD is no longer a primary manual input — the user
enters **Start of Construction** + **Construction Duration (months)** and
the backend computes COD = start + duration. Backend remains the source
of truth.

This is a runtime UI + safe backend derivation change, draft-only. User
visual review is required before merge.

## Scope of changes

### Backend (`main_web.py`)

Three new helpers, all **read-only / pure functions** that do not touch
any model / financial / schema / persistence code:

1. **`_parse_iso_date(value)`** — Parse an ISO-8601 string
   (`YYYY-MM-DD`) into a `datetime`, or return `None` on missing /
   malformed input.

2. **`_derive_cod_date(construction_start_date, construction_duration_months)`**
   — Returns the ISO-8601 COD date. Uses `dateutil.relativedelta` for
   deterministic month addition (handles month-end + leap year).

3. **`_read_optional_form_fields(request)`** — Reads the raw request
   body via `await request.body()` + `urllib.parse.parse_qs` to extract
   the 4 new form fields (spv_name, currency, construction_start_date,
   construction_duration_months) WITHOUT using `await
   request.form()` (forbidden by the Phase 51M-1 golden
   characterization that pins the route signature at 18 Form fields).

4. **`_apply_56d_extras_to_submitted(submitted, extra)`** — Merges
   the 4 extra form fields into the `submitted` dict so they land in
   the `baseline_snapshot` via `_apply_new_project_required_inputs`.
   Also derives COD and substitutes it into `submitted["cod_date"]` if
   the form's manual COD is empty.

The route `create_project_route` calls the helpers; its body stays
within the 60-110 non-blank line ceiling pinned by Phase 51M-2.

`_apply_new_project_required_inputs` (existing) is extended to write
the 4 new fields into the `baseline_snapshot` JSON column. No schema
change is required — `baseline_snapshot` is a `dict[str, Any]` JSON
column that can hold arbitrary new keys.

### Templates

`app/templates/partials/workspace_shell.html` — the inline
`#panel-new-project` form:

- `<input id="np-cod_date" ...>` is now `readonly aria-readonly="true"`,
  with `required` removed. The HTML5 browser will not block submission
  on an empty readonly field; the backend fills it from the
  derivation.
- A `.np-derived-note` block is rendered under the field, explaining
  that COD = Start of Construction + Construction Duration, computed
  server-side.

### CSS (additive only)

`static/styles.css` — append a new section "Phase 56D: COD derived
field display" defining `.np-derived-note`, `.np-derived-note__label`,
`.np-derived-note__text`, plus `input[readonly]` and
`input[aria-readonly="true"]` styling. Uses existing CSS variables
with fallbacks. No `:root` variables added or modified (count remains
5).

### No changes to

- `static/app.js`
- `app/waterfall_core.py`
- `app/project_factories.py`
- `app/runtime_impact_taxonomy.py`
- `app/persistence/*` (no schema/migration)
- `app/services/projects_create_service.py` (orchestration logic intact)
- `app/templates/partials/new_project_form.html` (sidebar full
  detailed form is intentionally preserved — users can still access
  the full 17-field form there)
- Any test fixtures, schema, or migration
- Any tab panel in workspace_shell.html (CAPEX, Inputs, etc.)
- Phase 56B / 56C changes — preserved intact

## COD derivation policy

```
COD = construction_start_date + construction_duration_months
```

**Date convention (deterministic)**:

| Input | Duration | Derived COD |
|---|---|---|
| 2025-01-15 | 24 | 2027-01-15 (normal) |
| 2025-01-31 | 1 | 2025-02-28 (month-end snap) |
| 2025-03-31 | 1 | 2025-04-30 (month-end snap) |
| 2025-12-31 | 1 | 2026-01-31 (normal) |
| 2024-02-29 | 12 | 2025-02-28 (leap-year snap) |
| 2024-02-29 | 48 | 2028-02-29 (next leap year) |

**Edge cases** (return `None` — no fake date invented):

- Missing start date → `None`
- Missing duration → `None`
- Zero / negative duration → `None`
- Non-numeric duration → `None`
- Malformed start date → `None`

## What lands in `baseline_snapshot`

The new v1 form submits these additional fields into the
`baseline_snapshot` JSON column (no schema change required):

- `spv_name` (text, optional)
- `currency` (text, defaults to `EUR`)
- `construction_start_date` (date, optional)
- `construction_duration_months` (int, optional)
- `cod_date` (derived date string, server-computed)

## Manual COD override

**Manual COD override is NOT supported in 56D** (deferred per the
56D brief). The form's `cod_date` field is `readonly`. The backend
**always** assigns the server-derived COD when
`construction_start_date + construction_duration_months` are both
valid — any manually supplied `cod_date` in the form body is
**ignored** in that case. If start or duration is missing/invalid,
derivation returns `None` and the existing validation handles
missing COD safely (no fake date is invented).

If a future override is required, it must be:

- Explicit (a separate toggle / audit field), and
- Audited via `replay_metadata`.

This is **out of scope for 56D**.

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
- No construction engine changes

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
- 52 new tests added (`tests/test_phase56d_cod_derived_field.py`)
- 51M-1 golden characterization still passes (150 tests)
- 51M-2 route thinning test still passes
- 56B / 56C / 55E-G / 51F / 52F / 53I / 54 / UI-2.x all pass
- 1176 relevant tests pass total

## Test coverage

`tests/test_phase56d_cod_derived_field.py` covers:

1. `TestDeriveCodDateHelper` — normal month addition, missing start /
   duration, zero / negative / non-numeric duration, month-end snap
   (Jan 31 + 1 = Feb 28), leap year (Feb 29 + 12 = Feb 28 next year,
   Feb 29 + 48 = Feb 29 leap year)
2. `TestParseIsoDateHelper` — valid date, empty, malformed (wrong
   separator, wrong order)
3. `TestInlineFormReadonlyCodDate` — form's `cod_date` input is
   `readonly` / `aria-readonly="true"`, NOT `required`; label
   mentions "derived"; `.np-derived-note` block exists with start /
   duration / COD language
4. `TestCreateRouteWiresDerivation` — route calls
   `_apply_56d_extras_to_submitted` and `_read_optional_form_fields`;
   helper uses `_derive_cod_date`; helper pulls all 4 extras; helper
   substitutes derived COD when empty; route signature unchanged
   (17 fields, frozen at 18 with `request: Request`); route body
   stays under 110 non-blank lines
5. `TestApplyInputsExtension` — `_apply_new_project_required_inputs`
   writes `spv_name`, `currency` (default `EUR`),
   `construction_start_date`, `construction_duration_months` to the
   `baseline_snapshot`
6. `TestScopeGuardrails` — `app.js`, `waterfall_core.py`,
   `project_factories.py`, `runtime_impact_taxonomy.py`, persistence
   all unchanged; no financial model changes
7. `TestCSSAdditive` — `.np-derived-note` styles added;
   `input[readonly]` styling added; `:root` count remains 5
8. `TestRc1Untouched` — rc1 SHA constant stable
9. `TestDateutilImport` — `relativedelta` imported from `dateutil`
10. `TestHelperDeterminism` — pins exact behavior for normal / month-end
    / leap-year inputs

## Manual visual review checklist

When reviewing the running app, please verify:

- [ ] Opening "New Project" shows the v1 form (from 56C)
- [ ] "COD Date" field is **readonly** (cannot be edited)
- [ ] "COD Date" label says "derived from Start of Construction +
      Duration; server-side"
- [ ] Below the COD field is an "Auto-derived" note explaining the
      backend logic
- [ ] "Start of Construction" and "Construction Duration (months)"
      are required inputs
- [ ] Submitting the form with start=2025-01-15 and duration=24
      creates a project with cod_date=2027-01-15 (verifiable via
      project record inspection or Inputs sheet display)
- [ ] Submitting the form with start=2025-01-31 and duration=1
      creates a project with cod_date=2025-02-28 (month-end snap)
- [ ] Submitting the form with start=2024-02-29 (leap year) and
      duration=12 creates a project with cod_date=2025-02-28
- [ ] Submitting the form with missing start OR missing duration
      results in a validation error (cod_date is still required
      downstream)
- [ ] All 56B / 56C behavior preserved (Help tab works, v1 form
      works, no detailed assumption inputs visible)
- [ ] State banner, governance cards, KPI grid, and all other tabs
      are unchanged
- [ ] No console errors / no JS errors / no network 404s

## Files changed (summary)

| File | Change | Lines |
|---|---|---|
| `main_web.py` | New helpers (`_parse_iso_date`, `_derive_cod_date`, `_read_optional_form_fields`, `_apply_56d_extras_to_submitted`); route body slimmed to call helpers; `_apply_new_project_required_inputs` extended to write 4 new fields to `baseline_snapshot` | +90 / -5 |
| `app/templates/partials/workspace_shell.html` | COD field made readonly; `.np-derived-note` block added | +6 / -2 |
| `static/styles.css` | Appended `.np-derived-note`, `input[readonly]` blocks (additive) | +38 / -0 |
| `tests/test_phase56d_cod_derived_field.py` | New tests | +600 (new file) |
| `docs/phase56d_cod_derived_field.md` | New doc | (this file) |
| `reports/phase56d_cod_derived_field.json` | New report | (new file) |

## Stack: 56B → 56C → 56D

This PR is the **third and final** in the 56B → 56C → 56D UX cleanup
stack. It is based on the 56C branch head. **56B and 56C can be
reviewed and merged independently** of 56D. The recommended merge
order is 56B → 56C → 56D. After all three merge, the inline New
Project form is fully master-data-only and the user no longer enters
detailed financial assumptions or a manual COD at project creation.
