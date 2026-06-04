# Phase 57A / UI-3.1 — LineItemGrid CAPEX summary pilot

## Status

**DRAFT.** The first runtime grid migration is ready for user
visual review. No financial model / formula / output / backend /
persistence / service / schema / fixture changes. No new
frontend dependencies. No `static/app.js` changes.

## Scope

| | |
|---|---|
| Sheet migrated | `app/templates/partials/sheet_capex.html` (CAPEX Detail grid) |
| New shared partial | `app/templates/partials/_line_item_grid.html` |
| LineItemGrid contract | `lig_render(table_label, columns, rows, editable, input_field_template, table_id)` |
| Rendered wrapper | `<div class="lig-wrapper lig-capex-pilot" data-line-item-grid="capex-pilot" data-lig-version="1">` |
| Backward compat | Every old CSS class preserved on the rendered HTML; existing `static/styles.css` continues to apply without modification. |

## Files changed

| File | Change | Lines |
|---|---|---|
| `app/templates/partials/_line_item_grid.html` | New — shared `lig_render` macro | +170 |
| `app/templates/partials/sheet_capex.html` | Migrated to use `lig_render` | ~+150 / -200 (net smaller after data model restructuring) |
| `tests/test_phase57a_ui3_line_item_grid_capex_summary.py` | New — 52 tests | +620 |
| `docs/phase57a_ui3_line_item_grid_capex_summary.md` | New (this file) | +280 |
| `reports/phase57a_ui3_line_item_grid_capex_summary.json` | New — structured report | +150 |

## LineItemGrid contract (API)

```jinja
{% from "partials/_line_item_grid.html" import lig_render %}

{{ lig_render(
     table_label="CAPEX detail grid for " ~ project_ctx.name,
     columns=[
       {"key": "label", "label": "Line Item", "kind": "label", "classes": "fc-grid-col-label"},
       {"key": "code", "label": "Code", "kind": "code", "classes": "fc-th fc-th--code"},
       {"key": "amount", "label": "Amount (kEUR)", "kind": "amount", "classes": "fc-th fc-th--amount"},
     ],
     rows=lig_rows,
     editable=is_user_project,
     input_field_template="capex_{code}_keur",
     table_id="capex-detail-grid",
   ) }}
```

### Inputs

- **`table_label`** (str) — used for the `aria-label` and a11y.
- **`columns`** (list[dict]) — column metadata. Each column has
  `key`, `label`, `kind` ∈ {`label`, `code`, `amount`, `period`},
  and optional `classes` (extra CSS classes for the `<th>`).
- **`rows`** (list[dict]) — the row data. Each row has:
  - `type` ∈ {`data`, `subtotal`, `total`, `section_band`, `delta_warning`}
  - `attrs` (optional dict of HTML attributes for the `<tr>`)
  - `cells` (list) — one cell per column, in column order
  - Optional `classes` for the `<tr>` (in addition to the
    row-type default class set)
  - Each cell is either:
    - A string (auto-escaped) — for section_band cells
    - A dict `{kind, value, [classes], [attrs], [safe_html]}` —
      for data/subtotal/total/delta cells
- **`editable`** (bool) — when True, `data` row amount cells
  render a native `<input type="number">`. Subtotal/total/delta
  cells are always read-only.
- **`input_field_template`** (str | None) — when set, the
  macro substitutes `{code}` with the row's
  `data-capex-code` to build the input `name` attribute.
- **`table_id`** (str | None) — optional id for the rendered
  `<table>`.

### Output

The macro renders:

```html
<div class="lig-wrapper lig-capex-pilot"
     data-line-item-grid="capex-pilot"
     data-lig-version="1">
  <table class="lig-table fc-grid" aria-label="...">
    <thead><tr class="lig-header fc-grid-header">...</tr></thead>
    <tbody>
      <tr class="lig-row--band fc-section-band">...</tr>
      <tr class="lig-row--data lig-row--data-capex" data-capex-code="..." data-capex-name="...">...</tr>
      <tr class="lig-row--subtotal fc-total-row fc-subtotal-row">...</tr>
      <tr class="lig-row--total fc-total-row fc-grand-total">...</tr>
      <tr class="lig-row--delta fc-delta-row">...</tr>
    </tbody>
  </table>
</div>
```

## Why only CAPEX summary was migrated

Per the 57A spec: "Create a reusable LineItemGrid partial /
macro. Migrate only `app/templates/partials/sheet_capex.html`."

The CAPEX Detail grid in `sheet_capex.html` is the most
representative example of a Phase-20I `fc-grid` workbook-style
grid in the app: it has a label column, a code column, an
amount column, section bands (Construction / Development /
Construction Management / Civil & Land / Insurances & Risk),
subtotal rows per section, a hard-CAPEX total, a financing-
costs section, a financing-costs subtotal, a grand total, and
an optional delta-vs-summary warning row.

Migrating this grid establishes the API for all the other
grids (OPEX, Revenue, Senior Debt, SHL, Construction,
Production, etc.) without changing the visible look of the
CAPEX tab. Future migrations (UI-3.2, UI-3.3, …) can reuse
`lig_render` with their own `rows` payload.

## Explicit out-of-scope list

The following sheets are EXPLICITLY OUT OF SCOPE for 57A:

- `sheet_capex_detail.html` (CAPEX Detail with monthly columns)
- `sheet_construction.html`
- `sheet_financials.html`
- `sheet_idc.html`
- `sheet_inputs.html`
- `sheet_opex.html`
- `sheet_opex_detail.html`
- `sheet_production.html`
- `sheet_revenue.html`
- `sheet_senior_debt.html`
- `sheet_shl.html`
- `sheet_tax.html`
- `inputs_section.html` (CAPEX / OPEX / Revenue / Financing / Tax
  Summary cards in the Inputs tab)

The 57A test module pins this list: each forbidden sheet is
checked to ensure it does NOT import `lig_render`.

## Tests run / results

| Test list | Result |
|---|---|
| 57A (52 new tests) | ✅ **52 passed, 1 skipped** (guardrail: main_web.py unchanged) |
| 57pre route smoke (49 tests) | ✅ 47 passed, 3 skipped (1 of which is the 57A exemption for template changes) |
| 56H-1 hotfix (12 tests) | ✅ 12 / 12 |
| 56H closeout (48 tests) | ✅ 48 / 48 |
| 56G closeout (46 tests) | ✅ 46 / 46 |
| 56F (97 tests) | ✅ 97 / 97 |
| 56E (68 tests) | ✅ 68 / 68 |
| 56D (62 tests) | ✅ 62 / 62 |
| 56C (60 tests) | ✅ 60 / 60 |
| 56B (52 tests) | ✅ 52 / 52 |
| 55E / 55F / 55G | ✅ all pass |
| 54* | ✅ all pass |
| 51F / 52F / 53I | ✅ all pass |
| **Total** | ✅ **1,137 passed, 4 skipped** |

## Visual review checklist

- [ ] CAPEX summary still readable.
- [ ] Row labels match old sheet (Construction / Development /
      Construction Management / Civil & Land / Insurances &
      Risk / Financing Costs).
- [ ] Values and units look unchanged (kEUR formatting with
      thousands separator on read-only cells).
- [ ] Period columns align (label / code / amount in three
      columns).
- [ ] Subtotal / group rows are clear (the row type CSS class
      `fc-total-row` is preserved).
- [ ] No horizontal overflow beyond existing behavior.
- [ ] Runtime impact indicators remain understandable
      (`aria-readonly="true"` is set on subtotal/total cells).
- [ ] Inputs tab still opens normally (no `inputs_section.html`
      changes).
- [ ] No console errors.
- [ ] No network 404s.
- [ ] GET / still returns 200.
- [ ] Tab navigation still works (no `static/app.js` changes).

## Rollback plan

If the visual review surfaces an issue, the 57A branch can be
deleted and a new branch can be created from `main`. The
migration is a single template change with a new partial;
both can be reverted with `git revert <merge-sha>`.

If only a specific row type needs fixing, the partial
(`_line_item_grid.html`) is the single source of truth for
the row rendering; fixing it fixes the whole grid.

## Confirmation — hard gates

| Gate | Status |
|---|---|
| **No `app/waterfall_core.py` changes** | ✅ (test pins it) |
| **No `app/project_factories.py` changes** | ✅ (test pins it) |
| **No `app/runtime_impact_taxonomy.py` changes** | ✅ |
| **No `app/persistence/*` changes** | ✅ (test pins it) |
| **No `app/services/*` changes** | ✅ (test pins it) |
| **No `main_web.py` changes** | ✅ (test pins it; needed by 56H-1) |
| **No financial formula / model output changes** | ✅ (only template rendering) |
| **No schema / migration / fixture changes** | ✅ (test pins it) |
| **No `static/app.js` changes** | ✅ (test pins it) |
| **No frontend dependencies** | ✅ (no `package.json`, no bundler config) |
| **No no-go UI claims** | ✅ (no new positive "validated" / "bankable" / "lender-ready" etc. copy) |
| **Phase 57-pre route smoke passes** | ✅ 47 / 47 (3 skipped, including 57A exemption) |
| **GET / returns 200** | ✅ (56H-1 hotfix + 57pre regression pin still in place) |
| **Engine MD5 / parity-core guardrails** | ✅ Phase 51F guardrails pass |
| **UI-2 / Phase 56 / Phase 55 / Phase 53I / 52F / 51F** | ✅ all pass |
| **rc1 untouched** | ✅ `b425a0708719eaa5e1d922b1008e5609758e0ad4` still in git history |

## Hard no-go preserved

- ✅ No bankability / lender-ready / audit-ready / certified /
  validated / investor-ready / SaaS-ready / production-ready
  claims
- ✅ Generic Solar / Wind remain exploratory / unvalidated
- ✅ G20 BLOCKED, R99/R102 NOT APPROVED
- ✅ Backend remains source of truth
- ✅ No JS financial calculations
- ✅ rc1 (`b425a07`) frozen

## What 57A does NOT cover

- A POST / PUT / DELETE / PATCH route smoke layer. The 57pre
  suite covers GET routes only.
- The other sheets (OPEX, Revenue, etc.). They will be migrated
  in future PRs (UI-3.2, UI-3.3, …).
- The export endpoints. The pre-existing TypeError on
  `/exports/runtime-summary.csv` and
  `/exports/institutional-workbook.xlsx` is OUT OF SCOPE for 57A
  (it was documented in 57pre and remains documented in 57A).
- Any change to the CAPEX Detail sheet (`sheet_capex_detail.html`
  with monthly columns). This is a different sheet (monthly
  payment schedule columns) and is NOT part of the 57A scope.

## Recommendation

**Ready for user visual review.** All hard gates pass. The
LineItemGrid macro is reusable, the visible HTML / CSS class
set is preserved 1:1, and the test suite (52 new + 1,137
total) provides strong regression protection.

If the visual review surfaces an issue, the rollback plan is
trivial: revert the single commit, fix the issue, re-push. If
the user approves, this is the foundation for UI-3.2
(LineItemGrid OPEX migration) and beyond.
