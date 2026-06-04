# Phase 55B — UI-3.1 LineItemGrid characterization

## Status

DRAFT, docs-only inventory of existing sheet/grid partials. No runtime
template changes.

## Current main SHA

`1b97a2b747331c10a848369cef1e3738ecea438d` (post-55A, post-UI-2.6)

## Sheet/grid partial inventory

Total of 13 sheet partials + 1 audit tab = 14 grid-bearing partials.

| Partial | LOC | Notes |
|---|---:|---|
| `sheet_capex.html` | 235 | CAPEX summary |
| `sheet_capex_detail.html` | 883 | CAPEX detail (most complex; uses `fc-grid` design system; uses Runtime Impact chip) |
| `sheet_construction.html` | 164 | Construction schedule |
| `sheet_financials.html` | 528 | Financial summary |
| `sheet_idc.html` | 169 | IDC schedule |
| `sheet_inputs.html` | 35 | Input form (minimal grid) |
| `sheet_opex.html` | 428 | OPEX summary (uses `fc-opex-grid-wrapper`) |
| `sheet_opex_detail.html` | 658 | OPEX detail (uses `fc-grid`, sticky) |
| `sheet_production.html` | 74 | Production schedule |
| `sheet_revenue.html` | 232 | Revenue schedule |
| `sheet_senior_debt.html` | 174 | Senior debt |
| `sheet_shl.html` | 123 | Shareholder loan |
| `sheet_tax.html` | 120 | Tax |
| `audit_reconciliation_tab.html` | 230 | Audit reconciliation (validation summary bar in here) |
| **Total** | **4,053** | |

**Frontend stack:** 47 templates total, 4,686 LOC of `static/styles.css`.

## Line-item row patterns observed

The existing `fc-grid` design system (introduced in Phase 20I, expanded in
UI-2) is the basis for all line-item rows. The patterns are:

### Cell classification (CAPEX detail)

```html
<td class="fc-grid-col-label fc-cell">{{ item.name }}</td>
<td class="fc-cell fc-cell--code">{{ item.code }}</td>
<td class="fc-cell fc-cell--amount {% if editable %}fc-cell-input{% else %}fc-cell-runtime{% endif %}">
  ...
</td>
```

Three cell states: `fc-cell-input` (editable, native input inside),
`fc-cell-runtime` (read-only, value from model), `fc-cell--code` (code
identifier).

### Period column patterns

- Summary sheets (`sheet_capex.html`, `sheet_opex.html`) have a single
  `Year 1 (kEUR)` column.
- Detail sheets (`sheet_capex_detail.html`, `sheet_opex_detail.html`)
  have multi-period columns (Year 1, Year 2, ..., full projection).
- `audit_reconciliation_tab.html` has comparative columns (left vs right
  scenario).

### Section band pattern

```html
<tr class="fc-section-band">
  <td colspan="{{ colspan }}" class="fc-section-band__label">{{ label }}</td>
</tr>
```

Used to group rows by category (e.g., "Wind turbines", "Solar panels",
"Battery storage").

### Subtotal / total row pattern

```html
<tr class="fc-total-row fc-subtotal-row">
  <td class="fc-grid-col-label fc-cell" colspan="2">{{ label }}</td>
  <td class="fc-cell fc-total-cell">
    <span class="fc-total-value">{{ "{:,.2f}".format(amount) }}</span>
  </td>
</tr>
```

### Input vs calculated vs display-only

- **Input** (`fc-cell-input`): contains native `<input type="number">` with
  `aria-label`, `data-capex-code`, `name="capex_<code>_keur"`. Only for
  user projects (`is_user_project`).
- **Calculated** (`fc-cell-runtime`): backend-computed value, no input.
  `aria-readonly="true"`.
- **Display-only** (factory templates): all cells are `fc-cell-runtime`,
  plus an `inp-readonly-notice` banner at the top.

## Runtime Impact chip usage

Only used in one place today:

- `sheet_capex_detail.html:335-337` — included via
  `{% include "partials/_runtime_impact_chip.html" %}` with
  `runtime_impact=child.runtime_impact`.

This means the chip is visible on CAPEX detail line items, but NOT yet
on OPEX detail, financial summary, or other sheets.

## Sticky/frozen column requirements

Found in:

- `sheet_capex_detail.html` (sticky code column)
- `sheet_opex_detail.html` (sticky code column)

Pattern: `position: sticky; left: 0;` on the first `<th>` (line item
label) so it stays visible when scrolling horizontally through periods.

## CAPEX summary vs CAPEX detail complexity

| Dimension | `sheet_capex.html` (summary) | `sheet_capex_detail.html` (detail) |
|---|---|---|
| LOC | 235 | 883 (3.8×) |
| Grid | `fc-opex-grid-wrapper` (Year 1 only) | `fc-grid` (multi-period) |
| Sticky column | No | Yes |
| Runtime impact chip | No | Yes |
| Editable input | Single Year 1 amount | Multi-period amounts |
| Section bands | None | Multiple (per asset class) |
| Subtotal rows | Yes (one or two) | Yes (many, per section) |
| Read-only notice | `inp-readonly-notice--capex` | Same |

**Recommendation: `sheet_capex.html` (CAPEX summary) is the first pilot
grid** for any LineItemGrid migration. It is the smallest sheet that
exhibits the full `fc-grid` design system (section bands, subtotals,
input vs runtime cells, read-only notice) without the multi-period
complexity of the detail view.

## First pilot grid recommendation

**`sheet_capex.html` (CAPEX summary)** — first pilot.

Rationale:

- Smallest sheet (235 LOC).
- Has the full `fc-grid` design system already.
- Single period column (Year 1 kEUR).
- Has section bands, subtotals, input vs runtime cells.
- Has read-only notice for baselines.
- No multi-period complexity.
- Already tested by users daily.
- Migrating to a unified `LineItemGrid` macro is straightforward.

Migration order:

1. **`sheet_capex.html`** (CAPEX summary) — first pilot.
2. **`sheet_opex.html`** (OPEX summary) — second, similar structure.
3. **`sheet_revenue.html`** (Revenue) — third, adds variant for non-numeric cells.
4. **`sheet_capex_detail.html`** (CAPEX detail) — fourth, multi-period + sticky.
5. **`sheet_opex_detail.html`** (OPEX detail) — fifth, multi-period + sticky.
6. Other sheets (construction, IDC, senior_debt, shl, tax, financials)
   — bulk migration last.

## UI-3 test strategy

For each LineItemGrid migration PR:

1. **Snapshot test** of the rendered HTML before and after the
   migration. The new `LineItemGrid` macro must produce byte-equivalent
   output for the same input.
2. **Accessibility test** — `aria-label`, `aria-readonly`, `role` are
   preserved.
3. **Runtime impact chip** — chip is rendered when `runtime_impact`
   context is present.
4. **Read-only notice** — preserved on baseline templates.
5. **Edit/input behaviour** — input cells still POST to the same
   form action.
6. **Visual review** — manual, by user, before merge.

## Visual review checklist

When reviewing a LineItemGrid migration PR, check:

- [ ] Section bands render with correct colspan.
- [ ] Subtotal rows render with correct class and value.
- [ ] Input cells accept numeric values, validate.
- [ ] Runtime cells are read-only, formatted correctly.
- [ ] Read-only notice appears on baseline templates.
- [ ] Runtime impact chip renders on detail sheets.
- [ ] Sticky column works on horizontal scroll.
- [ ] No layout regression.
- [ ] No new no-go copy.
- [ ] rc1 untouched.

## Hard gates for runtime grid PRs

- Only allowed template files modified (sheet partial + new shared
  partial if needed)
- No backend/service/persistence/model changes
- No static CSS/JS class modifications (additive only)
- No `:root` changes
- No frontend dependency changes
- No new no-go copy claims
- rc1 untouched
- Snapshot tests pass
- 100% visual review by user before merge
- PR remains draft until user approval

## Tailwind / build consideration

- Do NOT introduce Tailwind build setup in the same PR as a grid
  migration. These are orthogonal workstreams.
- Do NOT introduce Alpine.js in the same PR. Alpine changes the mental
  model from "server-rendered with HTMX" to "client-side reactive".

## Recommended next step

**55C — Tailwind-0 / CSS token consolidation feasibility** (docs-only,
assess whether/how to introduce Tailwind later without big-bang rewrite).
