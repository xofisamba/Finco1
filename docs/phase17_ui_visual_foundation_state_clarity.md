# Phase 17 UI — Visual Foundation & State Clarity

## Purpose

Phase 17 UI improves FincoGPT visual quality and state clarity without changing any runtime, model, or persistence logic. This is a UI/UX polish sprint building on Phase 17A (new project foundation) and Phase 17B (required field input form).

## Scope

- **UI-only changes** — CSS classes, semantic markup, visual groupings
- **No runtime changes** — backend, financial formulas, export logic unchanged
- **No architecture changes** — FastAPI/Jinja/HTMX stays, no React/Vue/Tailwind

## Files Changed

| File | Change |
|------|--------|
| `static/styles.css` | Design tokens, badge classes, state styles, typography, button variants, table styles |
| `docs/phase17_ui_visual_foundation_state_clarity.md` | This document |
| `reports/phase17_ui_visual_foundation_matrix.csv` | Before/after matrix |
| `reports/phase17_ui_status_badge_inventory.csv` | Badge taxonomy |
| `reports/phase17_ui_state_clarity_matrix.csv` | State visual rules |
| `reports/phase17_ui_remaining_gaps.csv` | Deferred UI work |
| `tests/test_phase17_ui_visual_foundation_state_clarity.py` | Tests |

## Design Token Summary

CSS variables already defined (Phase 9.5/Phase 12 foundation):

### Colors
- `--primary`, `--primary-hover`, `--primary-light` — blue actions
- `--accent`, `--accent-hover`, `--accent-light` — green positive/save
- `--warn-bg/text/border` — amber warnings
- `--blocked-bg/text/border` — red destructive/blocked
- `--convention-bg/text/border` — blue informational
- `--missing-bg/text/border` — purple not-available
- `--notapproved-bg/text/border` — orange not-approved

### Spacing (4px base grid)
- `--sp-1` through `--sp-10`

### Typography
- System font stack via `--font-sans`: `Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
- No Google Fonts CDN — loads from OS/system
- Typography classes: `.text-page-title`, `.text-section-heading`, `.text-card-heading`, `.text-table-heading`, `.text-form-label`, `.text-helper`, `.text-status`, `.text-mono`

## Status Badge Taxonomy

| Badge Class | Meaning | CSS Class |
|-------------|---------|-----------|
| PASS | Passed validation | `.badge-pass` |
| WARN | Warning / advisory | `.badge-warn` |
| BLOCKED | Blocked / error | `.badge-blocked` |
| NOT_APPROVED | Not yet approved | `.badge-notapproved` |
| ACCEPTED_CONVENTION | Accepted assumption | `.badge-convention` |
| SOURCE_NOT_AVAILABLE | Evidence unavailable | `.badge-missing` |
| RUNTIME_BINDING_PENDING | Awaiting runtime bind | `.badge-runtime-binding-pending` |
| DIRTY | Unsaved draft edits | `.badge-dirty` |
| SAVED | Saved scenario state | `.badge-saved` |
| PREVIEW_ONLY | Not runtime-backed | `.badge-preview-only` |
| RUNTIME | Runtime-backed value | `.badge-runtime` |
| TEMPLATE_SEEDED | Template default | `.badge-template-seeded` |
| USER_CREATED | User-created project | `.badge-user-created` |
| FACTORY_TEMPLATE | Factory template | `.badge-factory-template` |

**Authority boundary**: Badges indicate display/source only — they do not change governance status.

## Runtime / Preview / Saved / Dirty State Rules

| State | Visual Treatment | Source of Truth | Allowed Action |
|-------|-----------------|-----------------|----------------|
| DIRTY | `.dirty-state-banner` + `.badge-dirty` | Browser draft | Save or Revert |
| SAVED | `.badge-saved` + `.badge-factory-template` | Backend DB | Run, Compare |
| PREVIEW_ONLY | `.badge-preview-only` + amber tint | Form/session | None until saved |
| RUNTIME | `.badge-runtime` + KPI card `.kpi-card--runtime` | Backend runtime | Display, Export |
| TEMPLATE_SEEDED | `.badge-template-seeded` | Factory defaults | User may run |

## No-Runtime / No-Model Changes Statement

This branch makes **zero** changes to:
- `app/` Python code (except non-functional CSS class references)
- Runtime model formulas (`app/model/`, `app/excel_export/`)
- Export calculations (`app/excel_export.py`)
- Scenario compare behavior
- JavaScript financial calculations (none exist)
- Frontend state becoming runtime authority (not applicable — backend is authority)
- `save` auto-running (disabled)
- `run` auto-saving (disabled)

## Button Semantic Classes

| Action | Class | Behavior |
|--------|-------|----------|
| Run Model | `.btn-primary-action` | HTMX POST /run |
| Save Scenario | `.btn-secondary-action` | HTMX POST /scenarios/save |
| Compare / Validate | `.btn-neutral-action` | HTMX POST /compare, /validate |
| Revert Draft | `.btn-destructive-action` | HTMX POST /scenarios/state/discard |

**Note**: Existing `.btn`, `.btn-primary`, `.btn-secondary` etc. still work. New semantic classes are additive.

## HTMX Wiring Preserved

- `/run` — `hx-include="#main-form"`
- `/compare` — `hx-include="#main-form"`
- `/validate` — `hx-include="#main-form"`
- `/save-run` — `hx-include="#main-form"`
- `/scenarios/state/discard` — `hx-include="#main-form"` + `hx-swap="none"`
- New Project — existing routes unchanged

## New Project Form Visual Groups

Form sections now grouped with colored left borders:
- **Project metadata** (blue) — project name, type, template
- **Location / dates** (teal) — country, COD, construction months, horizon
- **Revenue / production** (green) — tariff, PPA term, P50 hours
- **OPEX** (amber) — OPEX Y1
- **CAPEX** (purple) — total CAPEX
- **Debt** (red) — gearing, interest rate, tenor, target DSCR

## Tailwind Migration Path

This CSS is designed to be **Tailwind-compatible**:

### CSS Variables → Tailwind Theme
```js
// tailwind.config.js future migration
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: 'var(--primary)',
        accent: 'var(--accent)',
        warn: 'var(--warn-text)',
        blocked: 'var(--blocked-text)',
        // ... map all CSS vars
      },
      fontFamily: {
        sans: ['var(--font-sans)'],
        mono: ['var(--font-mono)'],
      },
      spacing: {
        'sp-1': 'var(--sp-1)', // etc.
      }
    }
  }
}
```

### Semantic Classes → Tailwind Utilities
| Current | Tailwind Equivalent |
|---------|-------------------|
| `.ui-card` | `bg-white border rounded-lg shadow-sm` |
| `.ui-badge` | `text-xs font-bold px-2 py-0.5 rounded-full` |
| `.ui-btn` | `px-4 py-2 rounded font-semibold` |
| `.ui-state-strip` | `grid grid-cols-4 gap-4` |

### What Is Deferred
- Tailwind prototype branch (separate)
- Tailwind production build setup (`postcss`, `tailwind.config.js`, build pipeline)
- Full utility-class migration (not in this branch)
- No Tailwind CDN added (per policy)

## Remaining Gaps

| Gap | Reason | Deferred To |
|-----|--------|------------|
| Full Tailwind build pipeline | Separate design sprint | Tailwind prototype branch |
| Interactive component library | Needs design system audit | Future sprint |
| Responsive nav rewrite | Risk of regressions | Later sprint |
| Real-time collaboration indicators | Backend not ready | Future sprint |
| Advanced chart animations | Out of scope | Future sprint |
| Print/export stylesheet | Low priority | Future sprint |
| Dark mode | Needs design decision | Future sprint |

## Phase 17C Note

Phase 17C (from-scratch runtime for user-created projects) is **not** in this branch. The runtime disclosure on user-created projects states:

> "Runtime is template-seeded until Phase 17C from-scratch runtime path."

This notice is visible in the new project result panel and selector.
