# Phase 56F — State banner visual hierarchy polish

## Goal

Reduce the visual dominance of state banners while preserving
their information value. From the user feedback after 56B/56C/56D:

- State banners are useful but visually too dominant.
- State banners should feel like product UX, not debug output.
- The 11 banner contexts (from 55G) and 5 tones must remain
  supported.

This is a runtime UI visual polish change, draft-only. User
visual review is required before merge.

## Scope of changes

### Templates

`app/templates/partials/_state_banner.html` — the partial is
updated in two places:

1. **Icon glyphs are now simpler** (single Unicode symbol instead
   of 2-letter code). The old codes (`FT`, `UP`, `AS`, `SS`, `BD`,
   `UC`, `SR`, `LR`, `VF`, `DO`, `PR`) felt debug-like; the new
   glyphs (`◆`, `●`, `✓`, `◐`, `↻`, `!`, `◇`, `◌`) feel product-like.

2. **`banner-56f` modifier class** is added to the rendered `<div>`,
   so the new calmer visual style applies without breaking the
   original `.banner` style (which is preserved for backward
   compat).

### CSS (additive only)

`static/styles.css` — append a new section "Phase 56F: State
banner visual hierarchy polish" defining:

- `.banner-56f` base (smaller padding `0.5rem 0.85rem` vs
  original `0.75rem 1rem`; smaller font 0.8rem vs 0.85rem; no
  heavy box-shadow)
- `.banner-56f .banner-icon` (smaller 22px vs 28px; transparent
  background; tone-colored icon glyph)
- `.banner-56f .banner-body` / `.banner-title` / `.banner-desc`
  (tighter typography)
- `.banner-56f.banner-{tone}` for all 5 tones (softer
  backgrounds, no heavy left border; the icon glyph does the
  semantic signalling)

No `:root` variables added or modified (count remains 5).
The original `.banner` rule and all `.banner-{tone}` rules are
preserved for backward compat.

### No changes to

- `static/app.js`
- `app/main_web.py`
- `app/waterfall_core.py`
- `app/project_factories.py`
- `app/runtime_impact_taxonomy.py`
- `app/persistence/*`
- `app/services/*`
- `app/templates/partials/workspace_shell.html`
- `app/templates/partials/workspace_tabs.html`
- `app/templates/partials/index.html`
- Any test fixtures, schema, or migration

## Icon glyph mapping (Phase 56F)

| Context | Old code | New glyph | Meaning |
|---|---|---|---|
| `factory_template` | FT | ◆ | Reference diamond |
| `user_created_project` | UP | ● | Filled dot (active) |
| `active_scenario` | AS | ● | Filled dot (active) |
| `saved_scenario` | SS | ✓ | Check (saved) |
| `browser_draft` | BD | ◐ | Half-filled (partial) |
| `dirty_state` | UC | ◐ | Half-filled (partial) |
| `stale_result` | SR | ↻ | Refresh (re-run) |
| `last_run` | LR | ✓ | Check (last run) |
| `validation_failed` | VF | ! | Exclamation (warn) |
| `display_only_row` | DO | ◇ | Hollow diamond (read-only) |
| `pending_runtime_source` | PR | ◌ | Dotted circle (pending) |

## Behavior preservation

- **All 11 banner contexts still supported** (verified by
  `TestAllContextsSupported`).
- **All 5 banner tones still supported** (verified by
  `TestAllTonesSupported` and the CSS tone rules).
- **`role="status"` and `aria-label` accessibility attributes
  preserved**.
- **Banner context backend logic from 55G unchanged** — the
  helper in `main_web.py` (`_banner_context_for_index`) still
  computes the priority order; the partial just renders the
  result.
- **UI-2.1 banner tests still pass** — the partial's `<div>`
  structure and accessibility attributes are unchanged.
- **No backend changes** — only the visual template + CSS.

## Hard gates verified

- Only allowed template/CSS files modified
  (`_state_banner.html` + `styles.css`)
- No backend/service/persistence/model changes
- No `static/app.js` changes
- No `runtime_impact_taxonomy.py` changes
- No `:root` CSS variable changes (count remains 5)
- No new forbidden UI claims (12 forbidden terms checked)
- No financial formula / model output changes
- No schema/migration changes
- No new persistence writes
- rc1 (`b425a0708719eaa5e1d922b1008e5609758e0ad4`) untouched
- Draft-only — does not auto-merge
- 97 new tests added
  (`tests/test_phase56f_state_banner_visual_hierarchy.py`)
- 932 relevant tests pass total (97 new 56F + 835 51-56A-E + UI-2)
- 55G `banner_context` tests still pass
- UI-2.1 `state_banner_partial` tests still pass
- 56B / 56C / 56D / 56E tests still pass

## Test coverage

`tests/test_phase56f_state_banner_visual_hierarchy.py` covers:

1. `TestAllContextsSupported` — all 11 contexts present, each has
   a `_title` and `_desc`
2. `TestAllTonesSupported` — all 5 tones referenced in template
   and defined in CSS
3. `TestAccessibilityPreserved` — `role="status"`, `aria-label`,
   `aria-hidden` all present
4. `Test56FVisualHierarchy` — `.banner-56f` class applied;
   padding smaller; icon smaller; no heavy shadow
5. `TestIconGlyphsCalmer` — each context uses a single Unicode
   glyph; old 2-letter codes are gone
6. `TestOriginalBannerPreserved` — original `.banner` rule
   preserved; new class is additive
7. `TestToneStylesForBothVariants` — all 5 tone styles defined
   for both old and new variants
8. `TestNoGoCopy` — 12 forbidden terms absent; no debug-style
   language (stack trace, exception, panic, etc.)
9. `TestCSSAdditive` — 10 new selectors; `:root` count remains 5
10. `TestScopeGuardrails` — `app.js`, `main_web.py`,
    `waterfall_core.py`, `project_factories.py`,
    `runtime_impact_taxonomy.py`, `persistence/*` all unchanged
11. `TestRc1Untouched` — rc1 SHA constant stable
12. `Test55GAndUI2Compat` — template still uses `banner_context`
    and `banner_tone|default('info')`

## Manual visual review checklist

When reviewing the running app, please verify:

- [ ] State banners are calmer and more compact than before
- [ ] Banner icon is smaller (22px vs original 28px) and uses
      a simple glyph (not 2-letter code)
- [ ] Banner padding is smaller (more product-like, less
      dominant)
- [ ] Banner background is softer (no heavy left border)
- [ ] All 11 banner contexts still render correctly when
      applicable
- [ ] All 5 banner tones (info / success / warn / fail /
      neutral) still render with distinct visuals
- [ ] Accessibility attributes (`role="status"`, `aria-label`)
      preserved
- [ ] Banner context priority order from 55G unchanged
- [ ] No debug-style language (no "stack trace", "exception",
      "panic", etc.)
- [ ] No positive "validated" / "lender-ready" / etc. claims
- [ ] 56B / 56C / 56D / 56E behavior preserved
- [ ] No console errors / no JS errors / no network 404s

## Files changed (summary)

| File | Change | Lines |
|---|---|---|
| `app/templates/partials/_state_banner.html` | Icon glyphs replaced (2-letter codes → simple Unicode); `banner-56f` modifier class added | +22 / -22 |
| `static/styles.css` | Appended Phase 56F section: 10 new selectors, 0 `:root` changes | +85 / -0 |
| `tests/test_phase56f_state_banner_visual_hierarchy.py` | New tests | +480 (new file) |
| `docs/phase56f_state_banner_visual_hierarchy.md` | New doc | (this file) |
| `reports/phase56f_state_banner_visual_hierarchy.json` | New report | (new file) |

## Stack: 56E → 56F → 56G

This PR is the **second** in the 56E → 56F → 56G UX cleanup
sequence. It is based on the 56E branch head. **56E can be reviewed
and merged independently** of 56F and 56G. 56F/56G will be stacked on
top after 56E is approved.
