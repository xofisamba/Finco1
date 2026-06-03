# Phase 54E — UI-1 Closeout and UI-2 Implementation Plan

## Context

Phase 54E closes out UI-1 and prepares the first safe implementation
phase UI-2. **No runtime code changes. Docs/report/test only.**
This is the final phase of the 54 stack.

## Current Main SHA

`967639b5e33feaec96042ae80fc30b6aa8826780` (post-54D merge)

## Summary of 54A-54D

### 54A — Frontend inventory

- 44 templates (3 base/index + 41 partials), 7889 LOC
- Pure server-rendered Jinja + HTMX + custom CSS + one app.js
- No Alpine, no Tailwind, no React, no Vue, no Svelte, no bundler
- Runtime Impact taxonomy already in code (4 states)
- UI duplication hotspots identified (13 sheet_*.html, KPIs, banners)

### 54B — Information architecture

- 11 IA sections defined
- 10 core analyst workflows mapped
- 7 no-go copy risks documented
- Priority matrix (pilot vs enterprise)

### 54C — Design system and copy guardrails

- 9 components in vocabulary
- 4-state Runtime Impact chip standard with exact copy
- 11 state clarity banner copy contexts
- 13 forbidden UI claims
- 10 safe UI terms
- 16 component tokens

### 54D — Shared LineItemGrid

- 4 always + 4 audit + 4 compare columns
- 6 cell states
- 8 variants
- Jinja macro/partial implementation plan
- 11-step migration order

## Final Information Architecture (locked)

The 11 sections are now locked:

1. Dashboard / Overview
2. Projects
3. Inputs (Overview / Revenue / OPEX / CAPEX)
4. Financing (Senior Debt / DSCR / SHL / Distribution / Tax)
5. Scenarios
6. Compare
7. Audit & Reconciliation
8. Reports / Exports
9. Data Room (out of UI-1 scope)
10. Settings (out of UI-1 scope)
11. Help / Onboarding

**Locked means:** No structural changes in UI-2 without going
through the IA review process.

## Final Design System Recommendation (locked)

**Visual:** Navy primary (#0f1b2d), controlled blue accent (#1a56db),
muted clean-energy green secondary (#0f7a52), semantic status
colors. Light mode first.

**Typography:** Inter or system fallback, tabular-numeric, right-aligned numbers.

**Components:** chip, badge, banner, card, grid, section, status_pill, tooltip, validation_marker.

**Locked means:** Component vocabulary, colors, and typography are
the design system contract. Any new component must go through the
design system review.

## Final Runtime Impact Chip Standard (locked)

| State | Chip label | Color | Icon |
|---|---|---|---|
| Drives model | "Drives model" | green-600 | ✓ |
| Display only | "Display only" | slate-600 | ◯ |
| Pending | "Pending" | amber-600 | ⏳ |
| Needs review | "Needs review" | red-600 | ⚠ |

**Locked means:** This is the canonical chip standard. No
alternative labels, colors, or icons in any UI-2 implementation.

## Final State Banner Copy (locked)

11 banner copy contexts:

1. Factory template
2. User-created project
3. Active scenario
4. Saved scenario
5. Browser draft
6. Dirty state (unsaved changes)
7. Stale result
8. Last run
9. Validation failed
10. Display-only row
11. Pending runtime source

**Locked means:** Banner copy is the canonical vocabulary. Any new
context must go through the design system review.

## Final LineItemGrid Spec (locked)

- Orientation: line items vertical, periods horizontal
- Frozen left: code, line_item, runtime_impact
- Sticky header: period column headers
- 4 modes: default, audit, compare, compact
- 6 cell states
- 8 variants
- Implementation: Jinja macro first
- HTMX for mode swaps
- No Alpine in UI-2
- No Tailwind in UI-2
- No client-side finance calculations

**Locked means:** Sheet_*.html migrations must use this spec.

## UI-2 Implementation Plan

UI-2 is the first runtime implementation phase after UI-1 review.
UI-2 work is divided into 6 ordered items.

### UI-2.1 — State clarity banner partial (DRAFT, REVIEW REQUIRED)

- **Scope:** Create `app/templates/partials/_state_banner.html` Jinja partial
- **Variants:** 11 banner copy contexts from 54C
- **Backend dependency:** None (partial uses context variables)
- **Files touched:**
  - `app/templates/partials/_state_banner.html` (NEW)
  - `static/styles.css` (add `.banner-*` classes — minimal additive)
  - 1-2 template includes (e.g., `index.html`, `scenario_workspace.html`)
- **Auto-merge eligibility:** NO — first runtime change, requires user review
- **Risk:** low (new partial, no removal)

### UI-2.2 — Runtime Impact chip partial (DRAFT, REVIEW REQUIRED)

- **Scope:** Create `app/templates/partials/_runtime_impact_chip.html` Jinja partial
- **Variants:** 4 chip states from 54C
- **Backend dependency:** `runtime_impact_taxonomy.py` (already in place)
- **Files touched:**
  - `app/templates/partials/_runtime_impact_chip.html` (NEW)
  - `static/styles.css` (add `.chip-*` classes — minimal additive)
  - `app/templates/partials/sheet_capex_detail.html` (replace inline chip with include)
- **Auto-merge eligibility:** NO — first runtime change, requires user review
- **Risk:** low (additive, replacing inline chips in one sheet)

### UI-2.3 — Validation summary bar (DRAFT, REVIEW REQUIRED)

- **Scope:** Add a validation summary bar to the top of `audit_reconciliation_tab.html`
- **Variants:** 4 tones (pass / warn / fail / info)
- **Backend dependency:** `validation_service` (existing)
- **Files touched:**
  - `app/templates/partials/_validation_summary_bar.html` (NEW)
  - `app/templates/partials/audit_reconciliation_tab.html` (include new partial)
  - `static/styles.css` (add `.validation-summary-bar` class)
- **Auto-merge eligibility:** NO — first runtime change, requires user review
- **Risk:** low (additive)

### UI-2.4 — Factory lock indicator (DRAFT, REVIEW REQUIRED)

- **Scope:** Show a "Factory template" lock indicator on factory projects
- **Variants:** Single variant (lock icon + label)
- **Backend dependency:** None (uses existing project factory flag)
- **Files touched:**
  - `app/templates/partials/_factory_lock_indicator.html` (NEW)
  - `app/templates/index.html` or `app/templates/partials/workspace_shell.html` (include)
  - `static/styles.css` (add `.factory-lock` class)
- **Auto-merge eligibility:** NO — first runtime change, requires user review
- **Risk:** low (additive)

### UI-2.5 — Stale result warning (DRAFT, REVIEW REQUIRED)

- **Scope:** Show "Stale result" banner when inputs have changed since last run
- **Variants:** Single variant
- **Backend dependency:** Existing run metadata (last_run timestamp vs current state)
- **Files touched:**
  - `app/templates/partials/_stale_result_warning.html` (NEW)
  - `app/templates/index.html` (include)
  - `static/styles.css` (add `.stale-warning` class)
- **Auto-merge eligibility:** NO — first runtime change, requires user review
- **Risk:** medium (depends on detecting dirty state correctly)

### UI-2.6 — Run-source indicator (DRAFT, REVIEW REQUIRED)

- **Scope:** Show "Last run: {timestamp} / Run ID: {id}" on relevant views
- **Variants:** Single variant
- **Backend dependency:** Existing run metadata
- **Files touched:**
  - `app/templates/partials/_last_run_indicator.html` (NEW)
  - `app/templates/index.html` or `scenario_workspace.html` (include)
  - `static/styles.css` (add `.last-run` class)
- **Auto-merge eligibility:** NO — first runtime change, requires user review
- **Risk:** low (display only)

## Implementation sequence

Recommended order (each as its own PR):

1. **UI-2.1** State clarity banner (foundation for UI-2.3, UI-2.4, UI-2.5, UI-2.6)
2. **UI-2.2** Runtime Impact chip (replaces inline chip in sheet_capex_detail)
3. **UI-2.3** Validation summary bar
4. **UI-2.4** Factory lock indicator
5. **UI-2.5** Stale result warning
6. **UI-2.6** Run-source indicator

## What can auto-merge in UI-2

**None.** UI-2 is the first runtime change after a long docs/spec
phase. Each UI-2.x PR must be:

- Reviewed by user
- Has screenshot or rendered HTML attached
- Passes all guardrails (51F, 52F, 53I, 54x)
- Does not change any of the "must not change" list below

## What requires review

- All UI-2.x PRs (each requires user review)
- Any change to locked specs (IA, design system, chip standard, banner copy, LineItemGrid)
- Any new template or CSS file

## What must not be changed

- `app/persistence/` (Phase 53 closed)
- `app/services/` (Phase 52-53 closed)
- `main_web.py` (route handlers)
- `app/waterfall_core.py`, `app/project_factories.py`
- `app/data/finance_tables.csv`, `app/data/finance_parity.json`
- `parity/` directory
- `static/vendor/htmx.min.js` (HTMX vendor)
- rc1 (b425a07) frozen SHA
- Model output, fixtures, schema
- No-go claims
- Agent B governance docs (out of 54 stack scope)

## No-go copy checklist (UI-2)

Before any UI-2 PR, verify:

- [ ] No template uses "bankable", "lender-ready", "certified"
- [ ] No template uses "audit-ready", "audit-grade" alone (only "audit trail")
- [ ] No template uses "validated" alone (only "model check" / "internal validation")
- [ ] No template uses "investor-ready", "SaaS-ready", "production-ready"
- [ ] No template uses "real-time", "live model" alone
- [ ] No template uses "auto-saved" (unless implemented)
- [ ] No template uses "locked" (use "saved" or "versioned")
- [ ] No template uses "guaranteed returns", "investment advice", "customer reference"
- [ ] No template uses "external validation"
- [ ] All copy in user-facing strings is on the safe terms list (54C)

## Recommendation: Claude review before UI-2?

**YES.** Run a Claude review checkpoint on the post-54E main state
before starting UI-2. The 7 questions in the 53H-2 review pack
should be re-asked with the new UI-1 stack in mind:

1. **Spec completeness:** Is the UI-1 stack (IA, design system, chip standard, banner copy, LineItemGrid) sufficient to begin UI-2?
2. **Spec consistency:** Are there any conflicts between 54A inventory, 54B workflows, 54C design system, and 54D grid?
3. **No-go copy risks:** Have we missed any no-go copy risk in the locked specs?
4. **UI-2 priority:** Is the recommended UI-2 implementation order correct?
5. **Locked spec quality:** Is the 4-state chip standard sufficient, or do we need a 5th state?
6. **Stack recommendations:** Should we add Alpine earlier than UI-3, or stay with HTMX-only?
7. **UI-1 closeout:** Is UI-1 ready to be marked complete?

The Claude review can be a 53H-3 (or 54F) docs-only phase, similar to
53H-2.

## Final UI-2 recommendation

After UI-1 review (Claude checkpoint recommended), proceed with
UI-2.1 (state clarity banner) as the first runtime change.

UI-2.x is documented, not implemented in this stack. Implementation
begins only after user review of UI-1.

## Recommendation: Agent B refresh or UI-2 next?

After UI-1 closeout (54E merge), two options:

### Option A: Agent B governance refresh (docs only, low risk)

- Recommended in 53H-2 review pack
- Agent B can now refresh governance docs with the post-53I
  persistence state and post-54 UI-1 stack
- Low risk: docs only, no runtime changes
- No overlap with UI-2 implementation

### Option B: UI-2 implementation (medium risk)

- 6 ordered UI-2.x PRs as documented above
- First runtime change after long docs phase
- Each PR requires user review
- Medium risk: any rendering change can break visual consistency

### Recommended: Option A first, then Option B

- Agent B refresh (docs) before UI-2 (runtime)
- This ensures the Agent B governance doc matches the post-53I
  persistence state and post-54 UI-1 stack
- Then UI-2 can begin with a fully refreshed governance baseline

## Hard Gates (54E)

- ✓ Only docs/report/test files added
- ✓ No templates/CSS/JS/services/persistence changes
- ✓ Branch based on post-54D main `967639b5e33feaec96042ae80fc30b6aa8826780`
- ✓ UI-1 summary covers 54A-54D
- ✓ Final IA locked
- ✓ Final design system locked
- ✓ Final Runtime Impact chip standard locked
- ✓ Final state banner copy locked
- ✓ Final LineItemGrid spec locked
- ✓ UI-2 implementation plan documented (6 items)
- ✓ Implementation sequence specified
- ✓ Auto-merge policy: NONE for UI-2 (each requires review)
- ✓ What must not be changed listed
- ✓ No-go copy checklist provided
- ✓ Claude review recommended before UI-2
- ✓ Agent B vs UI-2 next-step decision provided
- ✓ rc1 (b425a07) untouched

## Files Created in 54E

- `docs/phase54e_ui1_closeout_ui2_plan.md` (this file)
- `reports/phase54e_ui1_closeout_ui2_plan.json`
- `tests/test_phase54e_ui1_closeout_ui2_plan.py` (guardrail)
