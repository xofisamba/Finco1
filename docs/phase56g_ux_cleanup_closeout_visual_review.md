# Phase 56G — UX cleanup closeout and visual review pack

## Status

**DRAFT — Phase 56 UX cleanup arc is ready for user visual
review and the next implementation decision.**

This document closes the **Phase 56 UX cleanup arc** and prepares
the next implementation decision before UI-3. It is a docs-only
PR (no runtime code, no CSS, no JS, no template changes
unless a regression is discovered).

**Hard guardrails preserved across the entire 56A-56F arc:**
- **Backend remains source of truth** for all financial
  outputs.
- **No JS financial calculations** anywhere in the app.
- **No frontend dependencies** added (no Tailwind, no Alpine,
  no React, no Vue, no Svelte).
- **No static/app.js changes** (except where explicitly
  noted).
- **No `:root` CSS variable changes** (count remains 5
  throughout).
- **No `app/waterfall_core.py` / `app/project_factories.py`
  changes**.
- **No persistence schema changes**.
- **No financial formula changes**.
- **No new persistence writes** beyond existing project
  creation path (56C).

## Summary of 56A–56F

| Phase | Title | PR | Status | Headline change |
|---|---|---|---|---|
| 56A | UX cleanup characterization | [#476](https://github.com/xofisamba/Finco1/pull/476) | ✅ MERGED | Inventory: Help is 302 LOC, project_selector is 185 LOC, New Project form has 17 fields, "Validated" wording flagged. |
| 56B | Help section | [#477](https://github.com/xofisamba/Finco1/pull/477) | ✅ MERGED | Help moved to dedicated Help tab; compact `.help-pointer` on Overview; "Validated" → "Reference" / "parity evidence". |
| 56C | New Project v1 form | [#480](https://github.com/xofisamba/Finco1/pull/480) | ✅ MERGED | Inline form reduced to 10 master fields; 11 detailed assumptions moved to hidden inputs (with safe defaults) to be filled later in Inputs. |
| 56D | COD derived field | [#481](https://github.com/xofisamba/Finco1/pull/481) | ✅ MERGED | COD auto-derived server-side from `construction_start_date + construction_duration_months`; manual override is deferred; derived COD always wins when derivable. |
| 56E | Project switch simplification | [#482](https://github.com/xofisamba/Finco1/pull/482) | 🔵 DRAFT | Active project card: project_name is primary label (font 0.85 → 0.95rem); project_code moved to `<details>` disclosure; origin pill (Reference / My project / Saved baseline); "New project" is the primary action. |
| 56F | State banner polish | [#483](https://github.com/xofisamba/Finco1/pull/483) | 🔵 DRAFT | Banner icons: 2-letter codes → simple Unicode glyphs; `.banner-56f` modifier class for calmer visual hierarchy (smaller padding, smaller icon, no heavy shadow). |
| 56G | UX cleanup closeout | this PR | 🔵 DRAFT | Docs/report/test only; visual review checklist; next-phase recommendation. |

## Before/after UX delta

### Help (56B)

| Before | After |
|---|---|
| 302-line inline Help block clutters Overview | Full Help lives in dedicated `Help` tab |
| "Validated templates" / `[Validated] TUHO` | "Reference templates" / `[Reference] TUHO` |
| "parity-validated" | "has parity evidence against Excel" |
| No navigation entry to Help | Compact `.help-pointer` on Overview + tab in top ribbon |

### New Project (56C + 56D)

| Before | After |
|---|---|
| 17 fields, 11 detailed assumptions visible | 10 master fields visible; 11 detailed assumptions hidden (with safe defaults) |
| User enters financial assumptions at create time | User enters them later in Inputs |
| Manual COD date | Auto-derived from `construction_start_date + construction_duration_months` |
| COD input editable | COD input `readonly`, server-side derived value wins |

### Project switch (56E)

| Before | After |
|---|---|
| Project code / slug shown as primary line below name | Project code moved to `<details>` "Details" disclosure |
| No origin indicator | Origin pill: `Reference` (factory) / `My project` (user) / `Saved baseline` |
| Technology badge on its own line | Technology badge inline with origin pill |
| "Load / Switch" button (debug icon ⎘) | "Switch project" button (product icon ⇄) |
| "New project" button below, ghost style | "New project" button is **first**, primary style |
| Empty state: "Use Load to open a project" | Empty state: "Choose an existing project or create a new one." |

### State banner (56F)

| Before | After |
|---|---|
| 2-letter code icons (FT / AS / SS / …) | Simple Unicode glyphs (◆ / ● / ✓ / ◐ / ↻ / …) |
| Padding 0.75rem 1rem, icon 28px | Padding 0.5rem 0.85rem, icon 22px |
| Bold left border (3px solid) | Softer border, no heavy left rule |
| Font 0.85rem / 0.8rem | Font 0.8rem / 0.74rem |
| Visual feel: debug-like | Visual feel: product-like |

## Manual visual review checklist

Run through the app manually and check each item:

### Overview tab
- [ ] Compact "Help · Open the Help tab" pointer is visible
- [ ] State banner (if applicable) is calm and product-like
- [ ] KPI grid renders normally
- [ ] Governance cards (G20 BLOCKED, R99/R102 NOT APPROVED) render
- [ ] Export lineage panel renders

### Help tab
- [ ] Help tab is visible in the top tab ribbon
- [ ] Workflow stepper renders
- [ ] TUHO / Oborovo labeled `[Reference]` (not `[Validated]`)
- [ ] Generic / new project exploratory warning visible
- [ ] "Not a lender / external audit / SaaS" disclaimers intact
- [ ] No positive "validated" / "lender-ready" claims

### New Project
- [ ] "New project" button is the **first** action in sidebar
- [ ] "New project" is visually primary (filled, bold)
- [ ] "Switch project" is the **second** action
- [ ] Inline form has 10 visible fields: project_name, spv_name,
      country_market, technology, capacity_mw, currency,
      construction_start_date, construction_duration_months,
      cod_date (readonly), template_source
- [ ] No detailed financial assumption inputs visible
- [ ] Template select shows ⚠️ Unvalidated for generic
- [ ] "Start of Construction" + "Duration" → COD auto-derived
- [ ] After submit, project is created and active

### Project switching
- [ ] Active project name is the primary label
- [ ] Project code is hidden by default
- [ ] "Details" disclosure reveals the code
- [ ] Origin pill shows `Reference` / `My project` / `Saved baseline`
- [ ] Active scenario shown with "Scenario" label
- [ ] Clicking "Switch project" opens the browser
- [ ] Browser tabs: Factory Templates / Saved Baselines / My Projects
- [ ] Active project is highlighted in the browser

### Active project display
- [ ] Sidebar card shows project name as largest label
- [ ] Compact metadata (tech + origin + scenario) below
- [ ] No debug-style code/slug in the primary view

### State banner
- [ ] Banner icon is a single Unicode glyph (not 2-letter code)
- [ ] Banner is compact (smaller padding than before)
- [ ] Tone is visually distinguishable (info / success / warn / fail / neutral)
- [ ] `role="status"` and `aria-label` preserved
- [ ] No debug-style language

### Inputs
- [ ] All 11 detailed financial assumption inputs are available
- [ ] Sidebar form (legacy `new_project_form.html`) unchanged

### Scenarios
- [ ] Save / duplicate / load scenarios work
- [ ] Scenario tab is scoped to the active project

### Audit / Validation
- [ ] Audit / Parity tab shows parity evidence for TUHO / Oborovo
- [ ] Validation summary bar (UI-2.3) renders
- [ ] G20 BLOCKED, R99/R102 NOT APPROVED preserved
- [ ] Generic projects are unvalidated (no positive "validated" claim)

### Run workflow
- [ ] Run button on sidebar works
- [ ] After run, KPI grid updates
- [ ] Last run indicator (UI-2.6) renders
- [ ] Stale result warning (UI-2.5) shows when appropriate
- [ ] Save / Run behavior unchanged from 56D

## Remaining UX issues

| Issue | Notes |
|---|---|
| Project switch limited to dropdown | 56E simplified the visual hierarchy but the underlying switch mechanism (`window.location.href = '/?project=...'`) is unchanged. A dedicated "Recent projects" quick-pick could be a future enhancement. |
| Detailed assumptions still hidden + default | 56C moved 11 detailed assumptions to hidden inputs. The user can still enter them later in Inputs (or via the sidebar full form). A more visible "Add assumptions" prompt after project creation could improve discoverability. |
| Generic Solar / Wind remain exploratory | Per spec, generic projects stay `⚠️ Unvalidated` until separately reviewed. Productization is out of scope. |
| Inputs sheet still needs LineItemGrid | Per 55B, `sheet_capex.html` is the first pilot. UI-3.1 is the next phase. |
| Tailwind not introduced | Per 55C, Tailwind is deferred until AFTER UI-3 closeout. Pre-Tailwind: token consolidation first. |
| CSS token cleanup still pending | `styles.css` has 5 `:root` blocks (per 55C). A token consolidation PR (1–2 PRs of `:root` block merging + ad-hoc hex replacement) is the recommended prerequisite for Tailwind. |

## Recommended next phases

### Phase UI-3.1: LineItemGrid CAPEX summary pilot
- **What**: Per 55B, `sheet_capex.html` (CAPEX summary, 235 LOC) is the
  first LineItemGrid pilot. Migrate the existing inline CAPEX table
  to the LineItemGrid macro.
- **Why**: LineItemGrid is the foundational shared UI component
  (per 54D spec). The CAPEX sheet is the highest-LOC sheet that
  benefits from the standard layout (4 always + 4 audit + 4 compare
  columns, 6 cell states, 8 variants).
- **When**: After 56E/56F are reviewed and merged.
- **Risk**: Low. Pure template migration; no backend changes.

### Phase Token Cleanup: `:root` block consolidation
- **What**: Merge the 5 `:root` blocks in `styles.css` (per 55C)
  into a single `:root` block, replacing ad-hoc hex with CSS
  variables.
- **Why**: 55C's CSS audit found 5 `:root` blocks (not 3 as
  originally estimated). Token consolidation is a prerequisite
  for Tailwind (per 55C's phased plan).
- **When**: BEFORE Tailwind-1 (Tailwind build config).
- **Risk**: Low. CSS-only.

### Phase Tailwind-1: build config (after UI-3 closeout)
- **What**: Add Tailwind config; map CSS variables to Tailwind
  theme tokens; pilot Tailwind in one new component.
- **Why**: Per 55C, Tailwind is deferred until AFTER UI-3
  closeout to avoid disrupting in-flight template work.
- **When**: After UI-3.1 + UI-3.2 + UI-3.3 are merged.
- **Risk**: Medium. New build dependency. Per spec, "No Tailwind
  / Alpine setup" is still in force for 56E/56F/56G.

### Phase Generic Solar / Wind productization (DEFERRED)
- **What**: Validate generic Solar / Wind against Excel; promote
  to parity-referenced templates.
- **Why**: Per spec, generic projects stay `⚠️ Unvalidated` until
  separately reviewed. Productization requires reviewer judgement.
- **When**: After UI-3 closeout. Out of scope for current arc.

## Merge guidance

### Whether 56E / 56F should be merged before UI-3
**YES.** 56E and 56F are pure visual / navigation polish. They
do not change:
- backend behavior,
- financial formulas,
- model outputs,
- persistence,
- schema.

Merging 56E/56F before UI-3 is safe and **recommended** because:

1. They are visually more important than UI-3 (sidebar is the
   first thing the user sees).
2. They are small, scoped changes (template + CSS only).
3. They have full test coverage (97 + 68 new tests).
4. They preserve all previous-phase behavior (verified).

### Whether visual review is required
**YES — both PRs are DRAFT-only** and require user visual review
before merge. The CI is green, all tests pass, but the visual
hierarchy changes (project switch, state banner) need the user's
eye.

### What not to start yet
- **DO NOT start UI-3 LineItemGrid** until 56E/56F are merged
  (or the user explicitly says to skip 56E/56F).
- **DO NOT start Tailwind / Alpine setup** — token cleanup first.
- **DO NOT start generic Solar / Wind productization** — needs
  reviewer judgement.
- **DO NOT start BESS / Hybrid / Portfolio** — out of scope.

## rc1 status
- rc1 SHA: `b425a0708719eaa5e1d922b1008e5609758e0ad4`
- **Untouched** across 56A, 56B, 56C, 56D, 56E, 56F, 56G.

## Summary

The Phase 56 UX cleanup arc is **complete in terms of work**:
- 56A characterized the cleanup surface.
- 56B made the Help a real product feature.
- 56C made New Project feel like onboarding, not data entry.
- 56D made COD auto-derived, not manual.
- 56E made the sidebar feel like product navigation.
- 56F made state banners feel like product feedback.
- 56G closes the arc and points to UI-3 as the next phase.

**Recommendation to user**: review PRs #482 (56E) and #483 (56F)
in your browser. If both feel right, merge them in order. Then
the next implementation decision is UI-3.1 (LineItemGrid CAPEX
pilot) per the 55B recommendation.

UI-3 should not start until the user has visually approved 56E
and 56F.
