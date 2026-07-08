# Implementation Plan — Excel-Faithful CAPEX/OPEX/Inputs/Scenarios

Based on: TUHO + Oborovo Excel extraction (July 2026)
Status: **MAPPING ONLY — no UI implemented yet**

---

## Why Sprint 14 Failed

Sprint 14 used CSS-only fixes on an already-broken grid structure:
- The `_line_item_grid.html` macro (`lig_render`) rendered a 3-column table (Label / Code / Amount) — not the Excel 6+ column structure
- Sticky columns added via CSS fought with the macro's `table-layout: fixed`
- Y2–Y30 columns were added as Jinja display math on top of a grid not designed for wide tables
- The result: misaligned headers, broken sticky columns, unreadable rows

**Root cause:** The grid component was not designed for wide horizontal tables with frozen panes. CSS cannot fix a structural mismatch.

---

## Correct Approach: Data Model First, Then Grid

### PR A — CAPEX View Model

**Scope:** `app/ui/project_context.py` + `app/ui/capex_view_model.py` (new file)

Build a `CapexViewModel` that the template can iterate without logic:

```python
@dataclass
class CapexLineVM:
    code: str           # "C.01.01"
    parent_code: str    # "C.01"
    name: str
    amount_keur: float
    per_mw: float       # amount_keur / capacity_mw
    is_editable: bool
    is_group: bool      # True = category header row
    is_readonly_financing: bool  # C.17 / C.18

@dataclass
class CapexGroupVM:
    code: str           # "C.01"
    name: str
    lines: list[CapexLineVM]
    subtotal_keur: float
    subtotal_per_mw: float
    is_readonly: bool   # True for C.17, C.18

@dataclass
class CapexViewModel:
    project_name: str
    capacity_mw: float
    groups: list[CapexGroupVM]      # C.01–C.18
    hard_capex_keur: float          # C.01–C.16
    hard_capex_per_mw: float
    financing_keur: float           # C.17
    reserve_keur: float             # C.18
    total_capex_keur: float         # all
    total_per_mw: float
    is_user_project: bool
```

**Build from:** `project_ctx.capex_detail_items` (already populated by `_build_capex_detail_items()`)

**No engine changes. No persistence changes. No route changes.**

---

### PR B — CAPEX Excel Grid (new template)

**Scope:** New partial `app/templates/partials/sheet_capex_grid.html`

Render `capex_view_model` as a purpose-built wide table — NOT via `lig_render`.

**Table structure:**
```
<div class="cx-grid-wrapper">           ← overflow-x: auto; max-height: 75vh
  <table class="cx-grid">
    <thead>
      <tr>                              ← position: sticky; top: 0
        <th class="cx-col-code">Code</th>        ← sticky left: 0
        <th class="cx-col-label">Line Item</th>  ← sticky left: 60px
        <th class="cx-col-amount">Amount kEUR</th>
        <th class="cx-col-per-mw">per MW</th>
        <th class="cx-col-notes">Notes</th>
      </tr>
    </thead>
    <tbody>
      {% for group in capex_vm.groups %}
        <!-- Group header row: C.01 Production Unit -->
        <tr class="cx-group-row cx-group-row--{{ 'readonly' if group.is_readonly else 'editable' }}">
          <td class="cx-col-code cx-sticky-col">{{ group.code }}</td>
          <td class="cx-col-label cx-sticky-col">{{ group.name }}</td>
          <td class="cx-col-amount cx-group-subtotal">{{ group.subtotal_keur | fc_money }}</td>
          <td class="cx-col-per-mw">{{ group.subtotal_per_mw | fc_money }}</td>
          <td></td>
        </tr>
        <!-- Sub-line rows -->
        {% for line in group.lines if not line.is_group %}
        <tr class="cx-line-row">
          <td class="cx-col-code cx-sticky-col cx-line-indent">{{ line.code }}</td>
          <td class="cx-col-label cx-sticky-col">{{ line.name }}</td>
          <td class="cx-col-amount">
            {% if line.is_editable %}
              <input type="number" name="capex_{{ line.code }}_keur" value="{{ line.amount_keur }}" class="cx-input" />
            {% else %}
              <span class="cx-value cx-value--readonly">{{ line.amount_keur | fc_money }}</span>
            {% endif %}
          </td>
          <td class="cx-col-per-mw cx-value--muted">{{ line.per_mw | fc_money }}</td>
          <td></td>
        </tr>
        {% endfor %}
      {% endfor %}
      <!-- Totals -->
      <tr class="cx-total-row cx-total-row--hard">
        <td class="cx-sticky-col" colspan="2">Hard CAPEX (C.01–C.16)</td>
        <td class="cx-amount-total">{{ capex_vm.hard_capex_keur | fc_money }}</td>
        <td>{{ capex_vm.hard_capex_per_mw | fc_money }}</td>
        <td></td>
      </tr>
      <tr class="cx-total-row cx-total-row--grand">
        <td class="cx-sticky-col" colspan="2">Total CAPEX</td>
        <td class="cx-amount-total cx-amount-total--grand">{{ capex_vm.total_capex_keur | fc_money }}</td>
        <td>{{ capex_vm.total_per_mw | fc_money }}</td>
        <td></td>
      </tr>
    </tbody>
  </table>
</div>
```

**CSS principles (NEW dedicated stylesheet block in the partial, not in global styles.css):**
```css
.cx-grid-wrapper {
  overflow-x: auto;
  overflow-y: auto;
  max-height: 75vh;
  border: 1px solid var(--border);
  /* NO position: relative here — breaks sticky inside overflow */
}
.cx-grid { border-collapse: collapse; min-width: 600px; }

/* Sticky first two columns — key: the wrapper must be the scroll container */
.cx-sticky-col {
  position: sticky;
  background: var(--surface);
  z-index: 2;
}
.cx-col-code.cx-sticky-col { left: 0; width: 70px; min-width: 70px; }
.cx-col-label.cx-sticky-col { left: 70px; min-width: 220px; }

/* Sticky header — sticks to top of scroll container */
.cx-grid thead tr {
  position: sticky;
  top: 0;
  z-index: 3;
  background: var(--surface-2);
}

/* Row types */
.cx-group-row { background: var(--surface-2); font-weight: 600; }
.cx-group-row--readonly .cx-col-label { color: var(--muted); }
.cx-line-indent { padding-left: 1.5rem !important; }
.cx-line-row { font-size: 0.82rem; }
.cx-line-row:hover { background: var(--hover); }
.cx-total-row { border-top: 2px solid var(--border); font-weight: 700; }
.cx-total-row--grand { background: var(--surface-2); }

/* Amount cells */
.cx-col-amount, .cx-col-per-mw { text-align: right; font-variant-numeric: tabular-nums; }
.cx-amount-total { font-weight: 700; }
.cx-amount-total--grand { color: var(--primary); }
.cx-value--readonly { color: var(--muted); }
.cx-value--muted { color: var(--muted); font-size: 0.78rem; }

/* Input */
.cx-input {
  width: 90px; text-align: right; border: 1px solid var(--border);
  border-radius: 3px; padding: 0.2rem 0.3rem; font-size: 0.82rem;
  background: var(--input-bg, #fff);
}
.cx-input:focus { outline: 2px solid var(--primary); }
```

**Critical rule:** The `cx-grid-wrapper` div is the scroll container. Sticky elements inside it stick relative to it — not to the viewport. This ONLY works if `cx-grid-wrapper` has `overflow-y: auto`. Do not add `overflow: hidden` on any ancestor.

**Acceptance test:** Code and Label columns remain fixed when scrolling horizontally. Header row remains fixed when scrolling vertically. Amount inputs are right-aligned and tab-navigable.

---

### PR C — OPEX View Model

**Scope:** `app/ui/opex_view_model.py` (new file)

```python
@dataclass
class OpexLineVM:
    code: str           # "B.01.1"
    parent_code: str    # "B.01"
    name: str
    y1_keur: float
    inflation_pct: float
    wht_flag: bool
    is_editable: bool
    is_group: bool
    # Derived display values (computed in Python, never submitted to engine)
    year_values: list[float]  # index 0 = Y1, index 1 = Y2, ...

@dataclass
class OpexGroupVM:
    code: str
    name: str
    inflation_pct: float
    lines: list[OpexLineVM]
    subtotal_per_year: list[float]  # index 0 = Y1 subtotal, etc.

@dataclass
class OpexViewModel:
    project_name: str
    capacity_mw: float
    p50_annual_mwh: float
    groups: list[OpexGroupVM]       # B.01–B.13
    contingency_rate: float
    total_excl_contingency: list[float]   # per year
    total_incl_contingency: list[float]   # per year
    display_years: int              # how many year columns to show (default 10, max 30)
    opex_per_mw_y1: float
    opex_per_mwh_y1: float
    is_user_project: bool
```

**Year value computation (Python, not Jinja):**
```python
def compute_year_values(y1_keur: float, inflation_pct: float, n_years: int) -> list[float]:
    return [y1_keur * (1 + inflation_pct/100) ** (yr - 1) for yr in range(1, n_years + 1)]
```

Compute in `_build_opex_view_model()` — NOT in Jinja template. This keeps the template clean and avoids Jinja numeric precision issues.

**No engine changes. No persistence changes. No route changes.**

---

### PR D — OPEX Excel Grid (new template)

**Scope:** New partial `app/templates/partials/sheet_opex_grid.html`

**Table structure:** Wider than CAPEX — needs horizontal scroll for year columns.

```
Columns: Code (sticky) | Line Item (sticky) | Budget Y1 kEUR | Infl % | WHT | Y1 | Y2 | Y3 | ... | YN | Notes
```

**Key decisions:**
- Default show Y1–Y10 (10 columns). "Show Y11–Y30" toggle optional in v1.
- Code + Label sticky at left. Header row sticky at top.
- Y1 column: editable input for user projects. Shows value for protected.
- Y2–YN: read-only display from `opex_vm.groups[i].lines[j].year_values[yr]`
- Group header rows span all year columns with subtotals per year.
- Total row at bottom: Total OPEX excl. Contingencies + Total OPEX incl. Contingencies.
- KPI strip above the table: OPEX/MW and OPEX/MWh.

**Minimum column widths:**
- Code: 60px
- Label: 220px (sticky)
- Budget/Inflation/WHT: 70px each
- Year columns: 70px each
- Notes: 140px

At 10 year columns: min-width = 60+220+70+70+70+700+140 = **1,330px** → horizontal scroll is mandatory.

---

### PR E — Inputs Control Tower (after CAPEX/OPEX fixed)

**Only implement after PR B and PR D pass browser screenshot review.**

Scope:
- Rebuild `inputs_section.html` with all 10 sections per inputs_mapping.md
- CAPEX summary → clear "kEUR — detail in CAPEX tab" link
- OPEX summary → clear "kEUR — detail in OPEX tab" link
- Sponsor/SHL section
- Runtime/Governance section

---

## Implementation Sequence

```
1. PR A — CapexViewModel Python class (2 days)
   → Unit test: CapexViewModel builds correctly from project_ctx for TUHO and Oborovo
   → No UI change

2. PR B — CAPEX grid template (2 days)
   → Browser screenshot required before merge
   → Acceptance: C.01–C.18 visible, sticky columns work, amounts editable

3. PR C — OpexViewModel Python class (2 days)
   → Unit test: year values computed correctly, totals match engine output
   → No UI change

4. PR D — OPEX grid template (3 days)
   → Browser screenshot required before merge
   → Acceptance: B.01–B.13 visible, Y1–Y10 aligned, totals correct

5. PR E — Inputs control tower (2 days)
   → After PR B + D pass browser review
```

Total: ~11 dev-days

---

## What NOT To Do (lessons from Sprint 14)

| ❌ Don't | ✅ Do instead |
|---------|-------------|
| Add CSS sticky to existing `lig_render` macro output | Build a new purpose-built grid partial |
| Compute year values in Jinja `{{ y1 * (1 + esc)^yr }}` | Compute in Python, pass pre-computed list |
| Use `table-layout: fixed` on a wide table | Use `table-layout: auto` with min-width on cells |
| Add `overflow: hidden` on any ancestor of the grid | Only the direct wrapper div gets `overflow: auto` |
| Add sticky CSS to classes shared with other tables | Use new `.cx-*` / `.ox-*` namespace |
| Claim "looks like Excel" without a screenshot | Require screenshot before merge |

---

## Screenshot Requirement

Before any PR B or PR D merge, provide screenshots of:
1. CAPEX grid top (group headers visible, Code + Label columns sticky)
2. CAPEX grid scrolled right (Code + Label still visible, amounts scrolled)
3. CAPEX total rows (Hard CAPEX / Total CAPEX clearly readable)
4. OPEX grid top (B.01–B.05 visible, Y1–Y5 columns aligned)
5. OPEX grid scrolled right (Code + Label still visible, Y6–Y10 visible)
6. OPEX total rows (Total excl./incl. Contingencies, OPEX/MW, OPEX/MWh)

Playwright is available at `/opt/pw-browsers/chromium`. Use it.
