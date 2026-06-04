# Phase 56B — Help section / remove full inline Help from sheets

## Goal

Move the full Help/onboarding content out of the default workspace/Overview area
into a dedicated Help tab. Replace the inline 302-LOC Help block on Overview
with a compact contextual pointer. Rephrase positive "Validated" framing to
internal-reference language.

This is a runtime UI change, draft-only. User visual review is required before
merge.

## Scope of changes

### Templates

- `app/templates/partials/workspace_tabs.html` — add a `Help` tab button.
- `app/templates/partials/workspace_shell.html` —
  - Remove the inline `{% include "partials/pilot_workflow_guide.html" %}` and
    `{% include "partials/pilot_help_onboarding.html" %}` lines from the
    `#panel-overview` block.
  - Add a compact `help-pointer` block as the only Help entry point in
    Overview.
  - Add a new `#panel-help` tab-panel block (placed after `#panel-compare`)
    that includes both `pilot_workflow_guide.html` and
    `pilot_help_onboarding.html`.
- `app/templates/partials/pilot_help_onboarding.html` — rephrase positive
  "Validated" language:
  - "Validated templates" → "Reference templates"
  - "[Validated] TUHO ..." → "[Reference] TUHO ... (has parity evidence against Excel)"
  - "[Validated] Oborovo ..." → "[Reference] Oborovo ... (has parity evidence against Excel)"
  - "validated results" → "parity-reviewed results"
  - "trusted internal review" wording preserved (factual, not a no-go claim)
- `app/templates/partials/pilot_workflow_guide.html` — rephrase the
  `pwg-limitations-strip`:
  - "Validated scope:" → "Reference scope:"
  - "parity-validated against Excel" → "has parity evidence against Excel"

### CSS (additive only)

- `static/styles.css` — append a new section "Phase 56B: Help pointer"
  defining `.help-pointer`, `.help-pointer__label`, `.help-pointer__text`,
  `.help-pointer__link`. Uses existing CSS variables with fallbacks. No
  `:root` blocks added or modified.

### No changes to

- `static/app.js` (existing `data-tab` mechanism + `hashchange` handler handle
  the new tab and the `href="#help"` link automatically)
- `app/main_web.py`
- `app/waterfall_core.py`
- `app/project_factories.py`
- `app/runtime_impact_taxonomy.py`
- `app/persistence/*`
- `app/services/projects_create_service.py` (no backend change for 56B)
- Any test fixtures, schema, or migration
- Any other tab panel in workspace_shell.html (CAPEX, Inputs, etc.)

## No-go copy treatment

| Before | After |
|---|---|
| "Validated templates" | "Reference templates" |
| `[Validated] TUHO Wind (72 MW, Croatia) - frozen-template, parity-validated against Excel ...` | `[Reference] TUHO Wind (72 MW, Croatia) - frozen-template, has parity evidence against Excel ...` |
| `[Validated] Oborovo Solar ...` | `[Reference] Oborovo Solar ...` |
| `Validated scope:` (in workflow guide) | `Reference scope:` |
| `parity-validated against Excel` | `has parity evidence against Excel` |
| `validated results` | `parity-reviewed results` |

The general disclaimers ("not a lender or bank approval", "not an external
audit or certification", "not SaaS-ready", "single-user / internal pilot
mode") are preserved verbatim.

`pilot_limitations_notice.html` is intentionally left untouched in 56B —
it is shown on the Downloads tab (not the Overview Help area). Its
"Validated" wording is scope-flagged for a future no-go cleanup pass and
is not part of the Help relocation.

## Out of scope (per 56B brief)

- New Project form simplification → Phase 56C
- COD derived field → Phase 56D
- Project switch simplification → Phase 56E (deferred)
- State banner polish → Phase 56F (deferred)
- UI-3 grid work / Tailwind / Alpine → deferred, no work in this stack

## Hard gates verified

- Only allowed template/CSS files modified
- No backend/service/persistence/model changes
- No `runtime_impact_taxonomy.py` changes
- No `static/app.js` changes
- No `:root` CSS variable changes (count remains 5)
- No new forbidden UI claims
- No financial formula / model output changes
- No schema/migration changes
- No new persistence writes
- rc1 (`b425a0708719eaa5e1d922b1008e5609758e0ad4`) untouched
- Draft-only — does not auto-merge
- 30+ new tests added (`tests/test_phase56b_help_section.py`)
- 56A, UI-2.x, 55E-G, 51F, 52F, 53I guardrails still pass

## Test coverage

`tests/test_phase56b_help_section.py` covers:

1. `TestValidatedRephrasing` — "Validated" claim removed from Help partials;
   replaced with "Reference" / "parity evidence" / "Reference scope".
2. `TestHelpTab` — `workspace_tabs.html` includes a Help tab.
3. `TestHelpPanel` — `workspace_shell.html` includes a `#panel-help`
   tab-panel that includes both workflow_guide and pilot_help partials.
4. `TestHelpRemovedFromOverviewInline` — full Help partials no longer
   included inside `#panel-overview`; only the compact pointer remains.
5. `TestHelpReachable` — pointer link uses existing `href="#help"` +
   `hashchange` → `switchTab` flow.
6. `TestExploratoryWarningPreserved` — generic / new project warning
   retained.
7. `TestNoGoCopy` — 11 forbidden terms (`bankable`, `bank-grade`,
   `lender-ready`, `certified`, `audit-ready`, `investor-ready`,
   `saas-ready`, `production-ready`, `guaranteed returns`,
   `investment advice`, `customer reference`) absent from Help
   partials.
8. `TestNewProjectFormUnchanged` — 6 master fields in inline new-project
   panel; 17 fields in sidebar `new_project_form.html` (Phase 56C will
   scope the latter).
9. `TestScopeGuardrails` — `static/app.js`, `app/waterfall_core.py`,
   `app/project_factories.py`, `app/runtime_impact_taxonomy.py`, and
   `app/persistence/*` are unchanged.
10. `TestCSSAdditive` — `.help-pointer` styles added; `:root` block
    count remains 5.
11. `TestRc1Untouched` — rc1 SHA constant matches documented frozen SHA.
12. `TestPanelHelpDoesNotBreakOverview` — KPI grid and export-lineage
    panel still present in `#panel-overview`; panel-help placed after
    panel-compare.

## Manual visual review checklist

When reviewing the running app, please verify:

- [ ] The Overview tab no longer shows the long Help block inline. It
      shows a compact "Help · Open the Help tab" pointer instead.
- [ ] The new **Help** tab is visible in the top tab ribbon.
- [ ] Clicking the Help tab opens the full Help content (workflow
      stepper + onboarding sections).
- [ ] The Overview pointer link "Help" navigates to the Help tab.
- [ ] TUHO and Oborovo are labeled `[Reference]` (no `[Validated]`
      positive framing).
- [ ] Generic projects still carry the `[Warning] Exploratory`
      disclaimer.
- [ ] The "Not included" disclaimers (no lender approval, no external
      audit, no SaaS, no sculpting solver) are preserved.
- [ ] State banner, governance cards, and KPI grid on Overview are
      unchanged.
- [ ] The Downloads tab still works (pilot_limitations_notice is
      unchanged in 56B).
- [ ] All other tabs (Inputs, Scenarios, Construction, ...) are
      unchanged.
- [ ] No console errors; no JS errors; no network 404s.

## Files changed (summary)

| File | Change | Lines |
|---|---|---|
| `app/templates/partials/workspace_tabs.html` | +1 (Help tab button) | +1 |
| `app/templates/partials/workspace_shell.html` | Removed 2 includes, added panel-help block + compact pointer | +14 / -4 |
| `app/templates/partials/pilot_help_onboarding.html` | Rephrased 3 "Validated" lines + 2 cross-refs in comments | +/- |
| `app/templates/partials/pilot_workflow_guide.html` | Rephrased "Validated scope" → "Reference scope" | +/- |
| `static/styles.css` | Appended .help-pointer block (8 selectors) | +44 / -0 |
| `tests/test_phase56b_help_section.py` | New tests | +440 (new file) |
| `docs/phase56b_help_section.md` | New doc | (this file) |
| `reports/phase56b_help_section.json` | New report | (new file) |
