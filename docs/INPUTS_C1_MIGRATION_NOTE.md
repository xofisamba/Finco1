# Inputs C1 Integration — Third Real-Sheet Migration

## Scope

This migrates the production Inputs sheet
(`app/templates/partials/inputs_section.html`, the `{% include %}`
target rendered into `<div class="inp-sheet-wrapper">` by
`app/templates/partials/sheet_inputs.html`, itself included into
`<div class="tab-panel" id="panel-inputs">` in `workspace_shell.html`)
onto the C1 Spreadsheet Interaction Layer, using exactly the same
`data-fc-*` contract proven on CAPEX
(`docs/CAPEX_C1_MIGRATION_NOTE.md`) and OPEX
(`docs/OPEX_C1_MIGRATION_NOTE.md`).

It does **not** start C2-PR2, implement recalculation or a dependency
graph, migrate any other sheet (Revenue, Debt, Tax, Compare,
dashboard) beyond what already lives on the Inputs sheet, or change
financial formulas, persistence, export, validation, Save/Run
behaviour, or project factories. No `domain/*` file,
`app/waterfall_core.py`, `app/input_adapter.py`, or
`app/project_factories.py` was touched.

Two of the spec's named reference documents —
`docs/C1_INTERACTION_LAYER_DESIGN.md` and
`Finco1_PostImpl_Review_UISprint_C1_C2.md` — do not exist anywhere in
this repository (confirmed via direct lookup and a repo-wide search).
This migration instead used the explicitly-designated CAPEX and OPEX
migration notes as the reference implementation, which do exist and
match the requested C1 contract exactly.

## What's different about Inputs vs. CAPEX/OPEX

Unlike CAPEX and OPEX — both grid/table sheets (`<table>` /
`<tbody>`/`<tr>`/`<td>`) — the Inputs sheet is a card-based form: eight
`section_card(...)` blocks (Identity, Schedule, Technical, Revenue /
PPA Summary, CAPEX Summary, OPEX Summary, Debt Summary, Tax Summary),
each built from a shared `field_row(label, value, ...)` macro that
renders a `<div class="inp-row">` / `<span class="inp-cell">` pair, not
table markup. `FcGridRegistry`'s row/cell discovery (`.closest('[data-
fc-row]')` with a `tr` fallback) and `FcFocusManager`'s `tabindex`
assignment have no table-specific assumptions, so no C1 JS changes
were needed to support this different DOM shape — confirmed by reading
`grid-registry.js` and `focus-manager.js` in full before starting.

Inputs is also the first of the three real-sheet migrations where the
production sheet has a real mix of editable and non-editable fields on
the same grid (CAPEX already had this; OPEX had none editable) and the
first where `data-fc-kind` is genuinely heterogeneous (text, date,
percentage, currency, count) rather than the amount/subtotal/total
vocabulary used by CAPEX/OPEX. This migration uses a single uniform
`data-fc-kind="text"` value for every Inputs cell — the spec requires
only that the attribute be present, not a specific vocabulary, and a
finer-grained kind taxonomy for Inputs is left for a future PR if
needed.

## What was implemented

### 1. C1 markup contract on the production Inputs sheet

**Grid root** — `sheet_inputs.html`'s `<div class="inp-sheet-wrapper">`
gained `data-fc-grid="inputs" data-fc-scroll-container="true"`, in
both the `is_user_project=True` branch and the read-only
(`inp-readonly-shell`) branch, mirroring how CAPEX/OPEX added their
contract to both branches.

**`field_row` macro** (`inputs_section.html`) — extended with three new
optional keyword-only parameters appended at the end of the existing
signature: `section=None, field_key=None, raw=None`. This is safe
because every existing call site in the file uses keyword arguments,
never positional, so no caller's behaviour changes unless it
explicitly passes the new params. When both `section` and `field_key`
are supplied, the macro emits:

- `data-fc-row="true"` on the row `<div>`
- `data-fc-cell="true"`, `data-fc-addr`, `data-fc-kind="text"`,
  `data-fc-editable="{{ 'true' if editable else 'false' }}"` on the
  `<span class="inp-cell">`
- `data-fc-raw` on the same `<span>`, when `raw` is not `None`

The macro's existing `value`-bound `<input value="...">` /
`<span class="inp-value">` rendering, `name=` attribute, `onchange`
handler, and badge/caveat-icon markup are all completely unchanged.

**Address scheme** — deterministic, built from a stable
`section.field_key` pair, never display text:

| Field (Identity) | Address |
|---|---|
| Project Name | `inputs!identity.project_name` |
| Type | `inputs!identity.technology` |
| Country | `inputs!identity.country_iso` |
| Capacity (summary) | `inputs!identity.capacity_summary` |
| Template Origin | `inputs!identity.template_origin` |

| Field (Schedule) | Address |
|---|---|
| Financial Close | `inputs!schedule.financial_close` |
| COD Date | `inputs!schedule.cod_date` |
| Construction Period | `inputs!schedule.construction_months` |
| Project Horizon | `inputs!schedule.horizon_years` |
| Period Frequency | `inputs!schedule.period_frequency` |

| Field (Technical) | Address |
|---|---|
| Installed Capacity | `inputs!technical.capacity_mw` |
| P50 Hours | `inputs!technical.p50_hours` |
| P90/P10 Hours | `inputs!technical.p90_p10_hours` |
| Availability | `inputs!technical.availability` |
| Capacity Factor | `inputs!technical.capacity_factor` |
| Degradation | `inputs!technical.degradation` |

| Field (Revenue / PPA Summary) | Address |
|---|---|
| Base Tariff | `inputs!revenue.price` |
| PPA Term | `inputs!revenue.ppa_term_years` |
| PPA Index | `inputs!revenue.ppa_index_pct` |
| CO2 Revenue | `inputs!revenue.co2_revenue` |

| Field (CAPEX Summary) | Address |
|---|---|
| Total CAPEX | `inputs!capex.total_capex_keur` |
| Senior Debt | `inputs!debt.senior_debt` |
| IDC | `inputs!capex.idc` |
| Bank Fees | `inputs!capex.bank_fees` |

| Field (OPEX Summary) | Address |
|---|---|
| Y1 OPEX Total | `inputs!opex.opex_y1_total` |
| Contingency | `inputs!opex.contingency_pct` |

| Field (Debt Summary) | Address |
|---|---|
| Indicative gearing | `inputs!debt.gearing_pct` |
| Target DSCR | `inputs!debt.target_dscr` |
| Interest Rate | `inputs!debt.interest_rate_pct` |
| Senior Tenor | `inputs!debt.tenor_years` |
| SHL Amount | `inputs!debt.shl_amount` |

| Field (Tax Summary) | Address |
|---|---|
| CIT Rate | `inputs!tax.cit_rate` |
| Loss Carryforward | `inputs!tax.loss_carryforward` |
| G20 Status (audit mode only) | `inputs!tax.g20_status` |
| R99/R102 (audit mode only) | `inputs!tax.r99_r102_status` |

**Note on "Senior Debt"**: this field is rendered visually inside the
"CAPEX Summary" card, but is addressed `inputs!debt.senior_debt` (not
`inputs!capex.senior_debt`) to match the spec's literal illustrative
example exactly. Addresses are semantic/stable-key-based, not tied to
which visual card a field happens to render under — the same
distinction CAPEX/OPEX draw between display labels and `cat.code`/
`child.code` addressing.

### 2. The pre-existing `value`-vs-raw formatting quirk

Several editable (and some read-only) fields bind their rendered
`value`/text to a pre-formatted display string, not the raw underlying
`project_ctx` field — e.g. "Y1 OPEX Total" renders
`"{:,.0f} kEUR".format(project_ctx.opex_y1_total_keur)`. This is
pre-existing, must-preserve behaviour. The new `raw=` macro parameter
is populated, per call site, from the actual underlying numeric/raw
`project_ctx` field (e.g. `raw=project_ctx.opex_y1_total_keur`), used
only for `data-fc-raw` — the macro's existing formatted `value`-bound
rendering is completely untouched.

### 3. Existing behaviour preserved

No `<input>` element was added or removed; every `name=` attribute,
the existing `onchange` handler (which still calls `markInputDirty`
and toggles `#dirty-indicator`), the `editable=is_user_project` /
`calculated=True` gating, default values, validation, and the
Save/Run wiring are all byte-identical to before this migration. Only
`data-fc-*` attributes were added to existing `<div>`/`<span>`
elements, and only `data-fc-grid`/`data-fc-scroll-container` were
added to the existing `<div class="inp-sheet-wrapper">` wrapper.

### 4. `FcCellIO`, `FcLiveModel`, `FcUndoManager` reused as-is

No changes to `static/interaction/cell-io.js`,
`static/modelling/live-model.js`, or `static/interaction/undo-
manager.js` were needed. `FcLiveModel` already attaches a single
document-level delegated `change` listener
(`document.addEventListener('change', _onChange)`); it picks up real
edits to Inputs' real `<input>` elements with zero Inputs-specific
code, exactly as it already does for CAPEX. `FcCellIO.writeValue`
already refuses to write to non-editable cells, giving the
calculated/read-only Inputs fields (Senior Debt, IDC, Bank Fees, SHL
Amount, CIT Rate, etc.) the correct paste-no-op behaviour automatically.

### 5. Cross-cutting interaction-layer fixes required

None. `grid-registry.js` and `focus-manager.js` were read in full
before starting specifically to rule out any table-cell-specific
assumption (Inputs cells are `<span>`, not `<td>`) — both already use
generic `.closest()`/attribute-based discovery with no DOM-shape
assumption, so this migration's different markup shape needed no JS
changes.

## A pre-existing, unrelated bug found (not fixed, out of scope)

While rendering `sheet_inputs.html` standalone to write this
migration's tests, an existing, unrelated Jinja2 escaping bug was
found in the `audit_mode=False` branch of the Tax Summary section: the
`tax_rows_normal` variable is built as a Python-style list literal of
`field_row(...)` macro-call return values
(`{% set tax_rows_normal = [field_row(...), field_row(...)] %}`)
rather than via `{% set X %}...{% endset %}` block capture (as every
other section in the file uses). Because `section_card(title, rows)`
renders `{{ rows }}` and Jinja2's autoescaping double-escapes a
*list* of `Markup` objects (each item is individually marked safe, but
the list itself is not), the `audit_mode=False` Tax Summary renders
visibly-escaped HTML source instead of the intended markup. Confirmed
via `git stash` to be present and identical on unmodified `main` —
this migration did not introduce or touch this code path's bug and
does not fix it (no opportunistic refactoring, per the task's
guardrails); it is flagged here for visibility. The `audit_mode=True`
branch (`tax_rows`, built via the standard `{% set %}...{% endset %}`
pattern) is unaffected and was used for this migration's tests.

## New tests

- `tests/test_inputs_c1_markup_contract.py` — static (non-browser)
  assertions against `sheet_inputs.html` rendered standalone with a
  hand-built sample `project_ctx` (`is_user_project` True and False):
  grid root, scroll container, every fc-cell has addr/kind/editable,
  no duplicate addresses, all six of the spec's illustrative addresses
  are present and correctly scoped, editable cells exactly match the
  pre-existing has-a-real-`<input>` convention (cross-checked
  programmatically, not just asserted), known calculated cells are
  non-editable, addresses are deterministic across repeated renders,
  and the read-only mode correctly flips every cell to
  `data-fc-editable="false"`. 12/12 passing.
- `tests/test_inputs_c1_migration_browser.py` — production-route
  Playwright smoke test, modeled on
  `tests/test_capex_c1_migration_browser.py` /
  `tests/test_opex_c1_migration_browser.py` (real `uvicorn`
  subprocess, `app.auth.create_session_token()`, a real user project
  seeded from the Oborovo template via `/projects/create`, the real
  `/?project=...` route, `window.switchTab('inputs')` to reveal the
  hidden tab panel). Covers: grid presence, unique addresses, editable
  cells have a real `<input>`, calculated cells are non-editable and
  have no `<input>`, click sets active cell, keyboard nav
  (`ArrowDown`), Shift+Arrow extends the selection, copy reads the raw
  value, paste succeeds and writes into an editable cell, paste onto a
  read-only cell is a no-op, an edit marks the cell dirty in
  `FcLiveModel.isCellDirty('inputs', addr)` and enables Undo,
  Ctrl+Z reverts the edit, the pre-existing `#dirty-indicator` /
  `markInputDirty` Save/Run wiring still fires unchanged from a real
  `change` event and the `name=` attribute is unchanged, and an
  `FcGridRegistry.scan()` re-scan (the same call `FcSwapLifecycle`
  makes after a real htmx swap) leaves the grid correctly registered.
  13/13 passing.

## Test results

- New tests: 13/13 (`test_inputs_c1_migration_browser.py`) + 12/12
  (`test_inputs_c1_markup_contract.py`) passing.
- Full C1 PR1–PR9 + C2-PR1 + CAPEX C1 + OPEX C1 + Inputs C1 regression
  suite (`tests/test_c1_*.py`, `tests/test_c2_*.py`,
  `tests/test_capex_c1_*.py`, `tests/test_opex_c1_*.py`,
  `tests/test_inputs_c1_*.py`): 263/263 passing, zero regressions.
- A literal whole-repo `pytest` run (~17.6k tests, not the curated C1
  regression set above) shows pre-existing, unrelated failures
  (TUHO calibration/audit-field tests, factory-lock-indicator,
  compare-panel, UX file-scope tests, etc.) and several CAPEX/OPEX/
  Inputs browser-test `ERROR`s; both were confirmed via `git stash` to
  reproduce identically on unmodified `main`, and the browser-test
  `ERROR`s were confirmed to be resource contention from running every
  Playwright/uvicorn-subprocess test in the repo back-to-back in one
  process (each of those same files passes cleanly — 8/8, 13/13,
  13/13 — when run in isolation or as part of the curated C1
  regression set above). Neither failure category is caused by this
  migration's diff (which touches only the two files listed below).
- `tests/test_phase24g3_capex_sheet_readability.py` fails to even
  collect on unmodified `main` (a pre-existing Python 3.11 f-string
  syntax error unrelated to any C1 work), as already documented in
  `docs/CAPEX_C1_MIGRATION_NOTE.md` and `docs/OPEX_C1_MIGRATION_NOTE.md`.

## Guardrail diff

`git diff --stat main` for this branch touches exactly two files:

```
app/templates/partials/inputs_section.html | 94 ++++++++++++++++--------------
app/templates/partials/sheet_inputs.html   |  4 +-
```

Plus the two new test files and this document. No `domain/*`,
`app/waterfall_core.py`, `app/input_adapter.py`,
`app/project_factories.py`, persistence, export, or calculation-engine
file was touched.

## Out of scope / deferred

- C2-PR2, incremental recalculation, a dependency graph, or formula
  evaluation.
- A new validation engine, or any change to existing validation
  behaviour.
- Save/Run refactor, persistence changes, export changes.
- Any financial formula change.
- Any change to CAPEX or OPEX.
- Migrating Debt, Revenue, or Tax as standalone sheets (their fields
  that already exist on the Inputs summary card are addressed here;
  any future dedicated Debt/Revenue/Tax sheet is a separate migration).
- Fixing the pre-existing `tax_rows_normal` list-literal escaping bug
  described above.
- A finer-grained `data-fc-kind` vocabulary for Inputs (date/
  percentage/currency/count) beyond the uniform `"text"` used here.

## Suggested next sheet

With Inputs now on the C1 contract alongside CAPEX and OPEX, a
dedicated Debt or Revenue detail sheet (if/when one exists as its own
tab, distinct from the Inputs summary fields already migrated here)
is a reasonable next candidate.
