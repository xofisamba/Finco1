# Phase 20H — Model Cell Design System + Grid Consistency Foundation

**Branch:** `phase20h-model-cell-design-system`
**Base SHA:** `e0f23be63f81ffaea3ae412fa97272c32a3cac65`
**Date:** 2026-05-27
**Type:** UX / Systemization — no financial logic changes

---

## Goal

Create a unified, reusable visual/system layer for all grid/cell-based UI surfaces in FincoGPT. The app should feel like a structured institutional project-finance workbook, not disconnected web forms.

This phase is **NOT** about adding new financial functionality. It is a foundation phase before:
- CAPEX detail grids
- OPEX detail grids
- IDC construction grids
- Debt schedules
- Financial statement review tables

---

## What Changed

### CSS Architecture (`static/styles.css`)

Added ~700 lines of new CSS organized into these sections:

#### 20H.1 CSS Variable Extensions
```css
--color-accent: var(--accent, #059669);  /* was referenced but undefined in inline styles */
--border-subtle: rgba(0,0,0,0.07);
--border-muted: rgba(0,0,0,0.04);
--cell-pad-v: 0.4rem;
--cell-pad-h: 0.6rem;
--cell-h: 2rem;
--font-cell: 0.82rem;
--font-label: 0.78rem;
--font-badge: 0.68rem;
--cell-inherited-bg: color-mix(in srgb, var(--color-accent) 4%, var(--surface));
--cell-override-bg: color-mix(in srgb, var(--color-accent) 15%, var(--surface));
--cell-base-bg: color-mix(in srgb, var(--color-accent) 8%, var(--surface));
--cell-runtime-bg: color-mix(in srgb, var(--primary) 8%, var(--surface));
--cell-factory-bg: var(--surface-2);
--cell-warning-bg: var(--warn-bg, #fffbeb);
--cell-error-bg: var(--blocked-bg, #fef2f2);
--cell-dirty-bg: #fef9ec;
```

#### 20H.2 Cell Base (`.fc-cell`)
Base wrapper for all cells — padding, font-size, numeric font-variant, vertical alignment, nowrap/ellipsis, transition.

#### 20H.3 Cell Variants

| Class | Purpose | Visual |
|-------|---------|--------|
| `.fc-cell-input` | Editable input | White bg, visible border, hover/focus states |
| `.fc-cell-runtime` | Calculated/runtime | Muted gray bg, italic, readonly |
| `.fc-cell-factory` | Factory/baseline | Muted text |
| `.fc-cell-inherited` | Inherited scenario value | Light accent tint |
| `.fc-cell-override` | Override scenario value | Highlighted accent tint, bold |
| `.fc-cell-readonly` | Readonly cell | Transparent bg |
| `.fc-cell-dirty` | Unsaved indicator | Yellow-tinted bg, dashed border |
| `.fc-cell-warning` | Validation warning | Yellow bg, warning border |
| `.fc-cell-error` | Error state | Red bg, error border |
| `.fc-cell-empty` | Empty/null value | Muted italic |

#### 20H.4 State Badges (`.fc-badge-*`)
```css
.fc-badge--active       /* Green — active scenario */
.fc-badge--inherited   /* Gray tint — inherited value */
.fc-badge--override     /* Accent — override value */
.fc-badge--runtime      /* Blue — runtime output */
.fc-badge--dirty        /* Yellow — unsaved */
.fc-badge--blocked      /* Red — BLOCKED state */
.fc-badge--notapproved  /* Orange — NOT_APPROVED */
.fc-badge--factory      /* Gray — factory value */
.fc-badge--base         /* Base case column tint */
```

#### 20H.5 Total/Subtotal Rows
```css
.fc-total-row     /* Bold, top border, surface-2 bg */
.fc-subtotal-row  /* Semi-bold, lighter border */
```

#### 20H.6 Section Bands/Headers
```css
.fc-section-band    /* Section background band */
.fc-section-header   /* Sticky header cell */
.fc-section-label    /* Section label row */
.fc-sheet-section    /* Card wrapper for sheet sections */
.fc-sheet-section-header  /* Section title inside card */
```

#### 20H.7 Grid System
```css
.fc-grid-wrapper    /* Scrollable wrapper with border */
.fc-grid            /* Base table */
.fc-grid-col-label  /* Sticky first column */
.fc-grid-header     /* Sticky header row */
.fc-th             /* Header cell */
.fc-row            /* Data row with hover */
.fc-td-label       /* Label cell (sticky left) */
.fc-col--base      /* Base case column tint */
.fc-col--active    /* Active scenario column tint */
```

#### 20H.8 Numeric Formatting
```css
.fc-num           /* Monospace numeric cell */
.fc-num--right    /* Right-aligned */
.fc-num--negative /* Red for negative values */
.fc-num--empty    /* Muted dash for null */
.fc-delta--positive  /* Green delta */
.fc-delta--negative  /* Red delta */
.fc-delta--neutral   /* Gray delta */
```

#### 20H.9 Compare Tab Cells
```css
.fc-compare-base    /* Base scenario value */
.fc-compare-active  /* Active scenario value */
.fc-compare-delta   /* Delta value cell */
```

#### 20H.10–20H.15 Additional Components
- `.fc-dirty-indicator` — unsaved state banner
- `.fc-editable` / `.fc-select-btn` — interaction affordances
- `.fc-kpi-grid` / `.fc-kpi-card` — KPI display grid
- `.fc-run-banner` — runtime summary banner
- `.fc-compare-table` / `.fc-provenance-card` — compare tab layouts

### Legacy Aliases Added (`sc-*`, `ps-compare-*`, `run-*`)

To allow gradual migration without breaking existing templates, all previously inline or ad-hoc CSS classes are now aliased in `styles.css`:

- `sc-*` — scenario matrix (Phase 20E)
- `ps-compare-*` — compare tab (Phase 20G)
- `run-*` / `kpi-*` — runtime summary (Phase 9.5)

### Templates Updated

#### `app/templates/partials/scenario_tab.html`
- **Removed:** ~300 lines of inline `<style>` block
- **Now uses:** `sc-*` classes aliased in `styles.css`
- **Behavior:** Identical — no class changes required in HTML

#### `app/templates/partials/runtime_summary.html`
- **Removed:** ~80 lines of inline `<style>` block
- **Now uses:** `run-*`, `kpi-*` classes aliased in `styles.css`

#### `app/templates/partials/scenario_compare.html`
- **No change:** Already used `ps-compare-*` classes which are now aliased

#### `app/templates/partials/inputs_section.html`
- **No change:** Uses `inp-*` classes which were already in `styles.css`

---

## CSS Class Summary

### New Semantic Classes (`fc-*`)
```
fc-cell, fc-cell-input, fc-cell-runtime, fc-cell-factory,
fc-cell-inherited, fc-cell-override, fc-cell-readonly,
fc-cell-dirty, fc-cell-warning, fc-cell-error, fc-cell-empty,
fc-badge--active, fc-badge--inherited, fc-badge--override,
fc-badge--runtime, fc-badge--dirty, fc-badge--blocked,
fc-badge--notapproved, fc-badge--factory, fc-badge--base,
fc-total-row, fc-subtotal-row,
fc-section-band, fc-section-header, fc-section-label,
fc-sheet-section, fc-sheet-section-header,
fc-grid-wrapper, fc-grid, fc-grid-col-label, fc-grid-header,
fc-th, fc-row, fc-td-label,
fc-col--base, fc-col--active,
fc-num, fc-num--right, fc-num--negative, fc-num--empty,
fc-delta--positive, fc-delta--negative, fc-delta--neutral,
fc-compare-base, fc-compare-active, fc-compare-delta,
fc-dirty-indicator, fc-editable, fc-select-btn,
fc-kpi-grid, fc-kpi-card, fc-kpi-label, fc-kpi-value,
fc-run-banner, fc-compare-table, fc-provenance-card
```

### Aliased Classes (backward compat)
```
sc-*    → aliased to fc-* equivalents
ps-compare-* → aliased in styles.css
run-*   → aliased in styles.css
kpi-*   → aliased in styles.css
inp-*   → already in styles.css (unchanged)
```

---

## Runtime / Model Logic Changes

**NONE.** This phase:
- Does NOT change any Python code
- Does NOT change financial calculations
- Does NOT change scenario resolution logic
- Does NOT add JS financial calculations
- Does NOT change save/run behavior
- Backend remains source of truth

---

## Files Changed

| File | Change |
|------|--------|
| `static/styles.css` | +~700 lines: fc-* design system + legacy aliases |
| `app/templates/partials/scenario_tab.html` | Removed inline `<style>` (~300 lines) |
| `app/templates/partials/runtime_summary.html` | Removed inline `<style>` (~80 lines) |
| `docs/phase20h_model_cell_design_system.md` | New documentation |

---

## Testing

### Rendering Tests (Phase 20H)
- [ ] Inputs tab renders with `inp-*` classes (unchanged)
- [ ] Scenario tab renders with `sc-*` classes (aliased)
- [ ] Compare tab renders with `ps-compare-*` classes (aliased)
- [ ] Runtime summary renders with `run-*` classes (aliased)
- [ ] Section bands consistent across all tabs
- [ ] Sticky first column works in scenario matrix
- [ ] Sticky header row works in scenario matrix
- [ ] Grid scroll behavior works

### Regression Tests
- Phase 20G tests pass
- Phase 20F tests pass
- Phase 20E tests pass
- Phase 20D tests pass
- Auth/API tests pass
- `main_web.py` compiles without error

### Browser Smoke (manual)
1. Login
2. Open `user_created` project
3. **Inputs tab:** editable cells have white bg + border; readonly cells muted
4. **Scenario tab:** inherited cells light tint, override cells highlighted; sticky first column works
5. **Compare tab:** Base vs Active styling distinct; delta coloring works
6. **Section bands:** consistent uppercase headers across tabs
7. **Console errors:** 0
8. **Viewport:** layout readable on narrow screen

---

## Known Limitations

1. **No JS financial calculations added** — per constraint
2. **CAPEX/OPEX detail grids** — not implemented (deferred to next phase)
3. **IDC construction grids** — not implemented
4. **Debt schedule grids** — not implemented
5. **Collapse/expand sections** — structure is collapse-ready but full collapse not implemented
6. **Inline edit popover** — still uses inline JS (`sc-edit-popover`)
7. **Color-mix()** — uses CSS color-mix() which requires modern browsers; fallback provided via accent variable

---

## Recommended Next Phase

### Phase 20I — CAPEX Detail Grid Foundation
- Add CAPEX breakdown grid using `fc-grid` system
- Use `fc-cell-input` for editable CAPEX line items
- Use `fc-total-row` for CAPEX subtotals
- Use `fc-cell-runtime` for calculated derived values

### Phase 20J — OPEX Detail Grid Foundation
- Similar pattern to CAPEX grid
- Per-category OPEX breakdown

### Phase 20K — IDC Construction Grid
- Construction period cash flow grid
- Uses `fc-grid` with period columns

---

## Constraints Respected

- ✅ No Tailwind
- ✅ No Alpine
- ✅ No React/Vue rewrite
- ✅ HTMX/Jinja/custom CSS architecture preserved
- ✅ No JS financial calculations
- ✅ Backend remains source of truth
- ✅ Save does not auto-run
- ✅ Run does not auto-save
- ✅ G20 remains BLOCKED
- ✅ R99/R102 remains NOT_APPROVED
- ✅ No lender-ready/audit-certified/SaaS-ready claims
