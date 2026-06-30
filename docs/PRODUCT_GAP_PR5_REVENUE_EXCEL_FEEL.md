# Product Gap PR5: Revenue Excel Feel

## Summary

Improves the Revenue sheet's UX so it feels like a professional Excel
financial model rather than a technical/debug screen, without touching
Preview Architecture, the financial engine, Save, Run, persistence, or
export. This PR is intentionally **lighter-weight** than CAPEX PR1 and
OPEX PR2/3/4: after inspecting the Revenue sheet's existing structure
and persistence paths, the only safe, honest changes available within
this PR's scope are (1) removing the user-visible Code column and (2)
confirming — not changing — that editable/read-only cell marking is
already consistent with CAPEX/OPEX conventions. No new editable fields
were added and no live-totals module was built; both are explained
below as deliberate, documented judgement calls rather than omissions.

## What changed

### 1. Code column removed from the Revenue grid

`app/templates/partials/sheet_revenue.html`:

- Removed the `<th class="fc-th fc-th--code">Code</th>` header cell and
  the four corresponding `<td class="fc-cell fc-cell--code">{{
  item.code }}</td>` data cells (one per revenue item group: Production,
  PPA / Tariff, Market / Merchant, CO2 / Certificates).
- **Approach chosen: template-level omission, not CSS-hide.** The Code
  column carried no functional behaviour distinct from the rest of the
  row (unlike the amount `<td>`, which must remain focusable/
  addressable for the C1 interaction layer) — it was pure inert display
  text. Removing it from the template avoids shipping dead DOM nodes to
  every client and keeps the markup simpler to reason about. CSS-hiding
  would have been the right call only if some other part of the page
  (JS, a print/export view, etc.) still needed to read the column's
  text content from the DOM — it does not; `item.code` is available
  server-side and is already exposed via the surviving
  `data-fc-addr="revenue!{{ item.code }}"` attribute on the amount
  cell, so no information was lost.
- Section-band and subtotal-row `colspan` attributes were reduced from
  `6` to `5` to match the grid's new 5-column shape (Line Item / Value
  / Unit / Group / Hint). This is a pure layout fix with no semantic
  change.
- All internal addressing metadata required by the C1 interaction layer
  is **fully preserved** on the amount `<td>` of every row:
  `data-fc-cell="true"`, `data-fc-addr="revenue!<code>"`,
  `data-fc-kind="text"`, `data-fc-editable="true|false"`,
  `data-fc-raw="<value>"`. None of these attributes reference the
  removed Code column — they were always sourced from `item.code` /
  `item.value` directly, not from the rendered `<td>` text.
- `tests/test_revenue_c1_markup_contract.py` (pre-existing, unmodified)
  continues to pass unchanged — it asserts against `data-fc-*`
  attributes only, never against the rendered Code column, confirming
  the C1 addressing contract was never coupled to that column.

**CAPEX and OPEX still have their own Code columns** — this was
explicitly out of scope for PR5 (Revenue-sheet-UX only) and was not
touched. `tests/test_product_gap_pr5_revenue_excel_feel.py` includes a
regression guard confirming `sheet_capex.html` and `sheet_opex.html`
still contain their Code column markup, i.e. this PR's Revenue change
did not leak into either sheet.

### 2. Editable Revenue input/editing surface — no new fields added

Before touching anything, the existing Revenue item list
(`_build_revenue_items` in `app/ui/project_context.py`) and the
existing Revenue template were inspected for already-editable vs
read-only assumptions:

| Item | Group | `editable` (pre-existing, unchanged by this PR) |
|---|---|---|
| `capacity_mw`, `operating_hours_p50`, `plant_availability`, `grid_availability`, `pv_degradation` | Production | `False` — "Set via inputs tab" |
| `ppa_base_tariff` | PPA / Tariff | **`True`** (pre-existing, already shipped before this PR) |
| `ppa_index`, `ppa_term_years`, `ppa_production_share` | PPA / Tariff | `False` — "Set via inputs tab" |
| `balancing_cost`, `first_merchant_period` | Market / Merchant | `False` — "Set via inputs tab" |
| `co2_enabled`, `co2_price` | CO2 / Certificates | `False` — "Set via inputs tab" |

**Finding: `ppa_base_tariff` was already editable before this PR**, with
a real `<input name="rev_ppa_base_tariff">` and a genuine snapshot
persistence path: `rev_ppa_base_tariff` (and the other six `rev_*`
field names) are already present in `main_web.py`'s
`_collect_form_snapshot()` known-fields list (added in "Phase 20K —
Revenue snapshot fields", predating this PR), and a parallel hidden
`<input name="rev_ppa_base_tariff">` already exists in
`app/templates/partials/workspace_shell.html` inside `#main-form`. This
PR did not need to do anything to make this field editable — it already
was. No code change was required or made for this item.

**Judgement call: no additional Revenue items were promoted to
editable.** All other Revenue items are explicitly read-only with the
hint "Set via inputs tab" — this is intentional, pre-existing backend
behaviour (`editable: False` set in `_build_revenue_items`), and
changing any item's `editable` flag would mean editing
`app/ui/project_context.py`, which sits right at the boundary of
"domain/backend data shaping" rather than "Revenue sheet/template/
frontend." The spec's hard rule — *"only expose editability for fields
that already have a genuine save path... do not invent new financial
logic"* — combined with the guardrail against touching
`app/project_factories.py`/`app/input_adapter.py`/domain code, means
none of the remaining 12 read-only items have a safe path to editability
within this PR's file scope. Each of them is either:

- a derived/structural technical parameter set once at project creation
  (`capacity_mw`, `operating_hours_p50`, `plant_availability`,
  `grid_availability`, `pv_degradation`) — genuinely owned by the
  Technical/Inputs tab, not Revenue, and
- a PPA/merchant/CO2 structural assumption (`ppa_index`,
  `ppa_term_years`, `ppa_production_share`, `balancing_cost`,
  `first_merchant_period`, `co2_enabled`, `co2_price`) that, per
  `_build_revenue_items`'s own `editable: False` flag and "Set via
  inputs tab" hint, is explicitly designed to be edited from the Inputs
  tab, not duplicated as a second editable surface on the Revenue
  sheet — duplicating it here without backend wiring to keep both
  surfaces in sync would risk exactly the kind of inconsistent/
  fabricated state the spec forbids.

This is a valid, honestly-documented "do less" outcome per the spec's
own guidance: *"It is fully acceptable for this PR to do LESS than
CAPEX/OPEX did if Revenue's current structure doesn't safely support
more... that is a valid, honestly-documented outcome, not a failure."*

### 3. Grid behaviour alignment with CAPEX/OPEX

- **Editable vs read-only marking**: already consistent before this PR
  — every Revenue amount cell uses the same `data-fc-cell`,
  `data-fc-addr`, `data-fc-kind="text"`, `data-fc-editable`,
  `data-fc-raw` contract as CAPEX/OPEX, and editable cells render the
  same `<input class="fc-input-native">` / read-only cells render the
  same `<span class="fc-cell-runtime">` convention used by CAPEX/OPEX.
  No template change was needed for this point — confirmed by
  `tests/test_revenue_c1_markup_contract.py`'s pre-existing
  `test_editable_cells_match_existing_convention` test, unmodified and
  still green.
- **Number formatting**: unchanged — already consistent with
  CAPEX/OPEX precision conventions (`%.2f` / `{:,.1f}` for currency
  and rate fields).
- **No technical/debug columns**: the Code column (the only one
  identified) is now removed; see above.
- **No live-totals module added.** Unlike CAPEX (Hard CAPEX Total /
  Total CAPEX) and OPEX (Category Subtotal / Operating Subtotal /
  Total OPEX), the Revenue sheet's "Est. Total Y1 Revenue" and "Y1 PPA
  Revenue" rows are explicitly labelled in the template as
  *"Informational — backend computes actual"* / *"kEUR — runtime model
  is authoritative"*, and are computed from a **non-linear, compounding
  formula** involving multiple inputs
  (`ppa_tariff_eur_mwh × operating_hours_p50 × capacity_mw ×
  plant_availability / 1000`). Only one of those four inputs
  (`ppa_base_tariff`) is editable; the rest are read-only/derived. Even
  if a client-side live-recompute were added for the one editable
  field, it would need to reproduce this multiplication formula in
  JavaScript — exactly the "do not invent new financial logic, no
  client-side financial engine, no duplicate revenue formulas" rule the
  spec explicitly forbids. **This is the Revenue-sheet equivalent of
  CAPEX's C.17/C.18 freeze and OPEX's Y2+ freeze: the Y1 PPA Revenue
  estimate and Total Y1 Revenue rows remain exactly as the backend/
  template-level Jinja computed them at render time, frozen, and are
  not recomputed live as `ppa_base_tariff` is edited.** Building a
  partial live-total here would either (a) require duplicating the
  exact formula in JS — forbidden — or (b) only update one factor while
  leaving the rest stale, which would be misleading rather than
  "Excel-like." Leaving it frozen and documenting why is the only
  honest option available within this PR's guardrails.

## Copy / governance

The existing Revenue sheet copy was reviewed:

- `"Protected original — read only"` / `"Edit via Duplicate / Save As
  to create your own project, then adjust inputs."` (readonly notice)
- `"Set via inputs tab"` (per-item hint)
- `"Informational — backend computes actual"` / `"kEUR — runtime model
  is authoritative"` (summary row notes)
- `"Unsaved revenue edits"` (dirty indicator)

None of this copy contains internal architecture jargon ("preview
architecture", "runtime pipeline", "C1/C2", etc.) — it is already
plain, user-facing language. **No copy changes were made**, since there
was no confusing/technical wording to clarify; this is a documented
judgement call, not an omission.

## Tests

- **New:** `tests/test_product_gap_pr5_revenue_excel_feel.py`
  (route-level / static-content, no browser):
  - Revenue sheet template exists and the route renders successfully
    for a real user project (`data-fc-grid="revenue"` present).
  - Code column header/cells (`fc-th--code` / `fc-cell--code`) are
    absent from both the raw template source and the rendered
    `#revenue-grid` region of the live route response.
  - `data-fc-addr` / `data-fc-cell` / `data-fc-kind` /
    `data-fc-editable` / `data-fc-raw` are still present on every
    per-item amount cell, and the three `revenue!summary.*` addresses
    are still present.
  - The has-a-real-`<input>` iff `data-fc-editable="true"` convention
    is still encoded in the template.
  - No new `name=` attribute pattern was introduced beyond the
    pre-existing `name="rev_{{ item.code }}"` loop.
  - The Revenue template never references `model_preview`,
    `preview_context`, or `runtime-renderer` (Preview Architecture
    files), and confirms those guardrail files still exist unrenamed.
  - CAPEX and OPEX templates still retain their own Code columns,
    confirming no cross-sheet leakage from this Revenue-only change.
- **Pre-existing, unmodified, still green:**
  `tests/test_revenue_c1_markup_contract.py` (the canonical Revenue C1
  markup-contract suite — every assertion in it continues to pass
  after the Code-column removal, since none of its assertions ever
  depended on that column).
- **Browser test:** not added. The pre-existing
  `tests/test_revenue_c1_migration_browser.py` already provides
  Playwright coverage of the Revenue tab loading without page errors;
  re-running it (see Regression results below) confirms no regression.
  A dedicated PR5 browser smoke test was judged unnecessary because
  this PR makes no new interactive/JS behaviour (no new live-totals
  module, no new editable fields) — the only change is static markup
  removal, which the route-level test above already covers more
  precisely than a browser test could.

## Regression results

Full required regression command:

```
python -m pytest tests/test_c1_*.py tests/test_c2_*.py tests/test_product_gap_*.py -q
```

Result: all tests pass except the 3 known, independently-confirmed
pre-existing failures (present on a clean `origin/main` with zero
changes, unrelated to this PR):

- `test_c2_pr1_live_model.py::TestStaticWiring::test_no_recalculation_formula_dependency_or_saverun_code_in_live_model`
- `test_c2_pr7_backend_preview_endpoint.py::...::test_no_financial_engine_call`
- `test_c2_pr9_runtime_request_hardening.py::TestNoRegressionForAuthorizedOrNullProject::test_authorized_project_behaviour_matches_pr8_contract`

No new failures were introduced by this PR. CAPEX (PR1) and OPEX
(PR2/3/4) Product Gap test files were included in this run and remain
fully green, confirming no regression.

## Guardrail compliance

```
git diff --stat origin/main -- domain app/waterfall_core.py \
  app/input_adapter.py app/project_factories.py main_web.py \
  app/services/model_preview.py app/services/preview_context.py \
  app/services/previews app/excel_export.py app/export \
  app/services/export_service.py app/services/export_audit_service.py \
  app/persistence static/modelling/runtime-renderer.js
```

Output: **empty** — no guardrail file was touched.

Files actually changed by this PR:

- `app/templates/partials/sheet_revenue.html` (Code column removal,
  colspan fix)
- `tests/test_product_gap_pr5_revenue_excel_feel.py` (new)
- `docs/PRODUCT_GAP_PR5_REVENUE_EXCEL_FEEL.md` (new, this file)

No financial formulas, Run logic, Save logic, persistence logic, export
logic, Preview Architecture, or Runtime Pipeline code was changed.
`main_web.py` was inspected (to confirm the existing
`rev_ppa_base_tariff` snapshot persistence path) but **not modified**.

## Out of scope (explicitly not implemented)

- No new editable Revenue fields (see judgement call above).
- No client-side live-totals module for Revenue (see judgement call
  above — the Y1 PPA Revenue / Total Y1 Revenue formulas cannot be
  honestly recomputed client-side without duplicating financial logic).
- No CAPEX/OPEX changes (their Code columns remain, by design, out of
  scope for this PR).
- No Preview Architecture, backend, persistence, export, or Runtime
  Pipeline changes.
- No removal of the Revenue grid's "Group" column, even though it is
  visually redundant with the section-band headers above each group
  (CAPEX/OPEX have no equivalent redundant column) — the spec only
  explicitly called out the Code column, and removing Group as well
  would be opportunistic cleanup beyond the stated scope. Documented
  here as a judgement call rather than silently left alone.
