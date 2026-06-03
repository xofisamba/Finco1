# Phase 54D — Shared LineItemGrid Specification

## Context

Phase 54D specifies the shared `LineItemGrid` component that will
replace the 13 duplicated `sheet_*.html` partials. **No runtime code
changes. Docs/report/test only.** Builds on 54A-54C.

## Current Main SHA

`dcfba47b0dd37bd22f4d4e29b466d8f3fe744d30` (post-54C merge)

## Problem statement

The current 13 `sheet_*.html` partials each re-implement:

- Row markup
- Period column layout
- Subtotal row styling
- Status cells
- Runtime Impact chip placement

This means any visual or interaction change must be made in 13
places, increasing the risk of inconsistency.

## Grid design grammar

### Orientation

- **Line items vertical** (one row per line item)
- **Periods horizontal** (one column per period)
- Period grouping: 1 year = 12 monthly columns, or 1 quarterly column

### Frozen and sticky elements

- **Frozen left columns:** Code, line item, runtime impact (always visible during horizontal scroll)
- **Sticky header:** Period column headers stay visible during vertical scroll
- **Sticky total row:** Total row may stick to bottom during vertical scroll

### Numeric formatting

- All numeric cells: `text-align: right; font-variant-numeric: tabular-nums;`
- Period cells: comma-separated thousands, no decimals for currency totals, 2 decimals for percentages
- Subtotal rows: bold, top border, slightly different background

### Subtotal rows

- Visual treatment: bold text, top border, `var(--grid-header-bg)` background
- May span all period columns or be a single cell on the right (decided per variant)
- May include a label like "Subtotal" or specific category name

### Period grouping

- Group periods by year if monthly: "2024", "2025", etc.
- Group periods by quarter if annual: "Q1 2024", "Q2 2024", etc.
- Group header row above the period header row

### Modes

- **Audit mode:** Adds source/audit columns on the right
- **Compare mode:** Adds delta columns (change vs base scenario) on the right
- **Compact mode:** Reduces padding, hides code/runtime columns, shows only line item + total

## Required columns

### Always present

1. **Code** (frozen left): 80-100px width
2. **Line item** (frozen left): 200-280px width
3. **Runtime impact** (frozen left): 100-120px width (chip)
4. **Total**: 100-120px width, right-aligned

### Period columns (one per period)

- 80-100px each
- Right-aligned numeric
- Comma-separated thousands
- Optional: 2 decimals for percentages

### Audit mode (only)

5. **Source**: 120px width
6. **Last modified**: 100px width
7. **Modified by**: 100px width
8. **Run ID**: 80px width

### Compare mode (only)

5. **Base value**: 100px width
6. **Delta**: 100px width (right-aligned, signed)
7. **Delta %**: 80px width (right-aligned, signed)
8. **Source scenario**: 120px width

## Cell states

| State | Visual | Editable | Notes |
|---|---|---|---|
| **Input** | white background, editable border | yes | For user-editable cells |
| **Calculated** | light gray background, no border | no | Computed by model |
| **Display-only** | light gray background, italic, no border | no | Reference only |
| **Pending** | amber-tinted background | no | Runtime source not yet wired |
| **Needs review** | red-tinted background, validation marker | no | Validation concern |
| **Validation issue** | red border | yes (but flagged) | Cell has validation problem |

## Variants (8)

| Variant | Use case | Period granularity | Subtotal style |
|---|---|---|---|
| **CAPEX** | `sheet_capex.html`, `sheet_capex_detail.html` | Annual | Per category subtotal |
| **OPEX** | `sheet_opex.html`, `sheet_opex_detail.html` | Annual | Per category subtotal |
| **Revenue** | `sheet_revenue.html` | Annual | Per source subtotal |
| **Debt/DSCR** | `sheet_senior_debt.html` | Annual | Per instrument |
| **SHL/Distribution** | `sheet_shl.html` | Annual | Per tranche |
| **CFADS/Cash Flow** | `sheet_financials.html` | Annual | Per period |
| **Scenario Compare** | `scenario_compare.html` | Annual | Side-by-side |
| **Audit/Reconciliation** | `audit_reconciliation_tab.html` | n/a | Badge list |

## Implementation recommendation

### Stack decision

- **Jinja macro/partial first:** Create `app/templates/macros/line_item_grid.html` as a Jinja macro. Variants implemented as separate macros that call the base.
- **HTMX for mode swaps:** Use `hx-get` to swap between audit/compare/compact modes without page reload.
- **Alpine only for local collapse/toggle later:** Do not add Alpine in UI-2. If a future phase needs local state (e.g., collapsible groups), add Alpine as a small vendor file with clear scoping.
- **Tailwind later after UI-1 review:** Do not add Tailwind in UI-2. Current custom CSS already uses tokens; Tailwind is a future optimization.
- **No client-side finance calculations:** Server is source of truth. Grid renders data; user edits submit via form post / HTMX.

### Macro signature (Jinja)

```jinja
{% macro line_item_grid(
  items,         # list of dicts with code, name, runtime_impact, total, periods[]
  period_labels, # list of strings, e.g. ["2024", "2025", ...]
  mode,          # "default" | "audit" | "compare" | "compact"
  base_url,      # for HTMX mode swap
  show_subtotals=True,
  frozen_left=True
) %}
  ...
{% endmacro %}
```

### HTMX wiring

```html
<div hx-get="{{ base_url }}?mode=audit" hx-target="#grid" hx-trigger="click" hx-swap="outerHTML">
  Switch to audit mode
</div>
```

### CSS approach

- Add new classes: `.line-item-grid`, `.line-item-grid--frozen-left`, `.line-item-grid--compact`, `.line-item-grid--audit`, `.line-item-grid--compare`
- Reuse existing `.chip`, `.badge`, `.banner` from 54C vocabulary
- Use CSS Grid for the layout (already in `styles.css`)
- Use `position: sticky` for frozen columns and header

## Context key contract candidates

The grid macro needs a stable data contract from the backend. Candidates:

```python
# Candidate: list of LineItem dicts
items = [
    {
        "code": "rev.ppa.price",
        "name": "PPA price",
        "runtime_impact": "Drives model",
        "sub_reason": "Source locked",  # optional, for tooltip
        "values": [123.4, 125.0, 127.5, ...],  # one per period
        "total": sum(values),
        "subtotal": False,
        "metadata": {
            "source": "TUHO fixture",
            "last_modified": "2026-05-12T14:23:00Z",
            "modified_by": "user@example.com",
            "run_id": "run_abc123"
        }  # only in audit mode
    },
    ...
]
```

```python
# Candidate: separate per-mode response
{
  "items": [...],
  "periods": ["2024", "2025", "2026", "2027", "2028", "2029", "2030"],
  "mode": "default",
  "subtotals": [...],  # list of {label, period_index, value}
  "totals": {  # grand totals
    "label": "Total",
    "values": [...]
  }
}
```

**Decision deferred to UI-2 implementation.** The macro will accept either a list of dicts (for backward compat with current sheet_*.html data shape) or a structured response (new).

## Test strategy (UI-3)

1. **Unit tests for macro:** Render macro with mock data, verify HTML structure
2. **Visual regression tests:** Screenshot comparison (optional, requires tooling)
3. **Mode swap tests:** Verify HTMX mode swap returns correct partial
4. **Accessibility tests:** Verify `aria-*` attributes, keyboard navigation
5. **Data contract tests:** Verify backend response shape matches macro expectations

## Migration order (UI-3 candidate)

1. Create macro and base CSS
2. Migrate `sheet_capex.html` (most-used sheet)
3. Migrate `sheet_opex.html` (second most-used)
4. Migrate `sheet_revenue.html`
5. Migrate `sheet_senior_debt.html` and `sheet_shl.html`
6. Migrate `sheet_financials.html` and `sheet_inputs.html`
7. Migrate `sheet_production.html`, `sheet_construction.html`, `sheet_idc.html`
8. Migrate `sheet_tax.html`
9. Migrate `sheet_capex_detail.html`, `sheet_opex_detail.html`
10. Migrate `scenario_compare.html` and `comparison.html` to use compare mode
11. Migrate `audit_reconciliation_tab.html` to use audit mode

Each step is a small PR with screenshot tests.

## Recommendation for 54E

Proceed to **Phase 54E — UI-1 closeout and UI-2 implementation plan**:

1. Summarize 54A-54D
2. Lock the IA, design system, Runtime Impact chip, banner copy, and LineItemGrid
3. Define the UI-2 implementation plan
4. Define what can auto-merge in UI-2 vs what needs review
5. Define what must not be changed
6. Recommend whether to run Claude review before UI-2

## Hard Gates (54D)

- ✓ Only docs/report/test files added
- ✓ No templates/CSS/JS/services/persistence changes
- ✓ Branch based on post-54C main `dcfba47b0dd37bd22f4d4e29b466d8f3fe744d30`
- ✓ Grid design grammar defined (orientation, frozen, sticky, formatting)
- ✓ Required columns specified (4 always, 4 audit, 4 compare)
- ✓ 6 cell states documented
- ✓ 8 variants enumerated
- ✓ Implementation plan: Jinja macro first, HTMX, Alpine later, Tailwind later, no client calc
- ✓ Context key contract candidates provided
- ✓ Test strategy documented
- ✓ Migration order specified
- ✓ rc1 (b425a07) untouched

## Files Created in 54D

- `docs/phase54d_shared_line_item_grid_spec.md` (this file)
- `reports/phase54d_shared_line_item_grid_spec.json`
- `tests/test_phase54d_shared_line_item_grid_spec.py` (guardrail)
