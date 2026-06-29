# C2-PR17 — OPEX Line Editability Bridge

## Summary

This is a narrow "bridge" PR. It makes the real OPEX Budget cells in
`app/templates/partials/sheet_opex_detail.html` (`data-fc-grid="opex"`)
genuinely editable for the first time, so that the already-built
OPEX → EBITDA → Operating Cash Flow preview chain (C2-PR14/PR15/PR16)
can actually produce non-null values in the browser. No financial
formula, persistence, or routing logic is touched.

## Exactly which cells are now editable

Each OPEX child (line-item) row's Budget cell —
`data-fc-addr="opex!{{ child.code }}.budget"`, `data-fc-kind="amount"` —
is now:

- `data-fc-editable="true"` **iff** `is_user_project` is true **and**
  `cat.is_contingency` is false (i.e. the line belongs to an ordinary,
  non-contingency OPEX category), with a real
  `<input type="number" step="any" min="0" class="fc-input-native">`
  descendant inside the cell — the exact same convention used by
  CAPEX's editable amount cells (`fc-input-native` class, `<input>`
  inside `[data-fc-cell]`).
- `data-fc-editable="false"` otherwise (protected/reference projects,
  or contingency-category lines), rendering the existing read-only
  `<span class="fc-cell-runtime">`.

This was verified against a real duplicated factory project
(`oborovo-copy-...`, via `POST /projects/oborovo/save-as`), which has a
genuine contingency category (`B.13`). After this change, every
non-contingency Budget cell (`B.01.01`–`B.12.2`) renders
`data-fc-editable="true"`, and the one contingency line (`B.13.1`)
correctly stays `data-fc-editable="false"`.

## What remains read-only, and why

- **Category/section-band total rows** (`opex!{{ cat.code }}.Y{{ y }}.subtotal`,
  `data-fc-kind="subtotal"`) — always read-only; they are derived sums
  of child lines, exactly like CAPEX's category subtotal rows.
- **Contingency category lines** (where `cat.is_contingency` is true,
  e.g. `B.13.1`) — always read-only. Contingency OPEX is
  formula-derived (`contingency_pct × sum(non-contingency OPEX)`,
  computed in `app/ui/project_context.py::_build_opex_detail_items`),
  not a user input, exactly mirroring the existing
  `cat.is_contingency` check the template already had.
- **Inflation %, WHT %, and Year (Y1…Yn) columns** — left exactly as
  they were (`data-fc-editable="false"`). These were explicitly out of
  scope for this bridge PR; only the Budget/amount cell needed to
  become editable for `_computeOpexTotalFromDom()` to find non-zero
  editable amount cells. Making these editable too is future C1 work,
  not part of this PR.
- **Protected/reference (non-`is_user_project`) projects** — entirely
  read-only, as before; editing is only ever possible after
  Duplicate/Save As, exactly like CAPEX and Revenue.

## Save behaviour decision: preview-only, NOT yet persisted

**Decision: OPEX Budget edits are preview-only.** Editing an OPEX
Budget cell updates the client-side runtime preview pipeline (dirties
the cell, feeds `_computeOpexTotalFromDom()` → OPEX preview → EBITDA
preview → Operating Cash Flow preview) but is **not** persisted by the
existing Save action.

### Evidence for this decision

CAPEX's editable amount cells are submitted with a real form `name`
attribute, `capex_{code}_keur` (see
`app/templates/partials/_line_item_grid.html`'s `lig_render` macro,
and `input_field_template="capex_{code}_keur"` in `sheet_capex.html`),
and `main_web.py` has a matching `Form(...)` parameter list
(`capex_epc_contract_keur`, `capex_production_units_keur`, … — see
`main_web.py` near line 344) that the project-save route reads back.

Searching `main_web.py` for an equivalent OPEX per-line save path
found **no such binding**. The only OPEX-related `Form(...)` fields
that the save route reads are aggregate fields —
`opex_y1_keur` (a single Y1 total) and a fixed list of
`opex_<group-name>_y1_keur` fields (e.g.
`opex_technical_management_y1_keur`,
`opex_o_and_m_preventive_and_corrective_y1_keur`, etc., see
`main_web.py` lines ~367-380) — there is no per-child-code OPEX field
(no `opex_{code}_keur` equivalent of CAPEX's `capex_{code}_keur`) and
no route reads or writes `child.budget_y1_keur` at all.

Given that, per the task brief, this PR must not invent a new save
route or fabricate a `name=` attribute the server doesn't actually
consume: the new `<input>` deliberately has **no `name` attribute**,
so it is never submitted as part of any HTML form post, and the
existing Save action is therefore guaranteed to leave the persisted
OPEX budget values completely unchanged regardless of any preview
edit made in the browser. This is proven by
`tests/test_c2_pr17_opex_line_editability.py::TestSaveDoesNotPersistOpexEdits`,
which edits an OPEX budget value in the live page, triggers Save, and
asserts the persisted/reloaded value is unchanged.

## Relationship to the Phase-21/24 deferral and PR14's documented gap

The original Phase 21/24 boundary (`title="Line editing deferred"`,
`data-fc-editable="false"` hard-coded on every OPEX cell) blocked *all*
OPEX editing, for *any* purpose — preview or persistence. C2-PR14
explicitly preserved that boundary and documented
(`docs/C2_PR14_OPEX_PREVIEW.md`) that `_computeOpexTotalFromDom()`
would always return `null` until "a future, dedicated C1 PR adds real
OPEX line-item editability."

This PR is that dedicated PR — but it deliberately narrows scope to
*only* the minimum needed to unblock the preview chain: it makes the
Budget/amount cell editable (client-side, preview-only), and leaves
the larger question of "how should OPEX line edits be persisted"
explicitly deferred (see below). The Phase-21/24 deferral is therefore
**partially** resolved: OPEX lines are now editable for preview
purposes; they are still not persisted by Save.

## What remains deferred for a future PR

- **Real OPEX budget persistence.** A future PR would need to: (a)
  add a per-line OPEX form field/name convention (e.g.
  `opex_{code}_keur`, mirroring CAPEX's `capex_{code}_keur`), (b) add
  matching `Form(...)` parameters and save-route handling in
  `main_web.py`, and (c) decide how a persisted per-line edit
  reconciles with `app/ui/project_context.py`'s existing
  `_build_opex_detail_items()` group/contingency totals computation
  (which currently derives `budget_y1_keur` from
  `project_inputs.opex` group records, not from a per-child-code
  store) — this is nontrivial domain/storage-shape work, not a
  template change, and is explicitly out of scope here.
- Inflation %, WHT %, and per-year (Y1…Yn) cell editability — still
  entirely out of scope, unaffected by this PR.
- OPEX line creation/deletion, category restructuring — unaffected,
  out of scope.

## No financial engine, no formula, no persistence change

Confirmed: this PR touches only `sheet_opex_detail.html` (template
markup) and adds tests/docs. No import of, or call into, `domain/*`,
`app/waterfall_core.py`, `app/input_adapter.py`, or
`app/project_factories.py`. No new route. No change to
`static/modelling/recalc-preview.js`, `static/modelling/runtime-renderer.js`,
`static/modelling/live-model.js`, `static/app.js`, or
`main_web.py`'s preview-validation/echo logic — all of that machinery
was already correct and simply needed real editable OPEX cells to
start producing non-null values, exactly as PR14/15/16 predicted.

## Tests added

- `tests/test_c2_pr17_opex_line_editability.py` — backend/template
  route-level tests: editable-cell markup correctness (editable
  non-contingency rows vs. read-only contingency/subtotal/protected
  rows), no financial-engine call as a side effect of rendering, no
  Run-output change from editing without Run, and Save does not
  persist an unsaved OPEX preview edit.
- Updated `tests/test_c2_pr14_opex_preview_browser.py`,
  `tests/test_c2_pr15_ebitda_preview_browser.py`, and
  `tests/test_c2_pr16_ocf_preview_browser.py`: replaced the now-outdated
  "OPEX/EBITDA/OCF preview always null because there are no editable
  OPEX cells" assertions with the now-correct "editing OPEX produces a
  real non-null preview, and EBITDA/OCF correctly chain from it"
  assertions, while preserving the "never fabricate when truly
  unavailable" tests for scenarios that remain genuinely null (e.g.
  before any edit, or editing only one of Revenue/OPEX).
