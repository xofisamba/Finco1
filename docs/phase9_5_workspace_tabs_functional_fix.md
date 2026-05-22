# Phase 9.5 — Workspace Tabs Functional Fix

## Problem

Phase 9.5 workspace tabs (Inputs, Construction, OPEX, etc.) were visually present but clicking them did nothing. Root causes:

1. **`onclick` inline handlers in `workspace_tabs.html`** — inline JS is blocked by CSP or simply not wired to the JS controller in `app.js`
2. **No `data-tab` attributes** on tab buttons — JS couldn't delegate via `querySelectorAll("[data-tab]")`
3. **No event listener for tab clicks** — `app.js` defined `switchTab()` but never bound click listeners to the tab buttons
4. **No URL hash support** — tabs couldn't be bookmarked
5. **Duplicate inline script** in `workspace_tabs.html` (removed inline `switchTab()`)

## Fix

### 1. `workspace_tabs.html` — removed inline `onclick`, added `data-tab`

**Before (broken):**
```html
<button class="ws-tab active" id="tab-overview" onclick="switchTab('overview')">Overview</button>
```

**After (CSP-safe):**
```html
<button class="ws-tab active" id="tab-overview" data-tab="overview">Overview</button>
```

- All `onclick` attributes removed from all 17 tabs
- `data-tab` attribute added to every tab button (value = panel ID suffix)
- Inline `<script>` block with duplicate `switchTab()` removed from the partial

### 2. `static/app.js` — CSP-safe event binding + hash support

```js
document.addEventListener('DOMContentLoaded', function () {
  /* Tab click handlers (data-tab based, CSP-safe) */
  document.querySelectorAll('.ws-tab[data-tab]').forEach(function(tabBtn) {
    tabBtn.addEventListener('click', function() {
      var tabId = tabBtn.getAttribute('data-tab');
      if (tabId) switchTab(tabId);
    });
  });

  /* Restore tab from URL hash on load */
  var hash = window.location.hash.replace('#', '');
  if (hash) {
    setTimeout(function() { switchTab(hash); }, 0);
  } else {
    /* Ensure overview is active by default */
    document.querySelectorAll('.tab-panel').forEach(function(p) {
      if (p.id !== 'panel-overview') p.classList.remove('active');
    });
  }

  /* Hash change listener */
  window.addEventListener('hashchange', function() {
    var h = window.location.hash.replace('#', '');
    if (h && h !== activeTab) switchTab(h);
  });
});
```

### 3. `switchTab()` enhanced

- Updates `history.pushState` with `#tabId` for bookmarkability
- Dispatches `tabChanged` custom event
- Scrolls workspace top into view

### 4. CSS (existing — no changes needed)

```css
.tab-panel  { display: none; }
.tab-panel.active { display: block; }  /* line 1295-1300 */
```

The CSS already has the right show/hide logic. Only JS binding was missing.

## Files Changed

| File | Change |
|------|--------|
| `app/templates/partials/workspace_tabs.html` | Removed `onclick`, added `data-tab`, removed inline script |
| `static/app.js` | Added `DOMContentLoaded` listener, hash support, CSP-safe event binding |

## Tests Added

- `test_no_inline_onclick_handlers` — no `onclick=` in workspace_tabs.html
- `test_all_tabs_have_data_tab_attribute` — all 17 tabs have `data-tab`
- `test_all_panels_have_data_panel_attribute` — all panels have `data-panel`
- `test_js_has_domready_tab_listener` — `app.js` has `DOMContentLoaded` + `querySelectorAll("[data-tab]")`
- `test_overview_active_by_default` — `panel-overview` has `class="tab-panel active"`
- `test_tab_switcher_function_exists` — `switchTab` function defined in `app.js`
- `test_hashchange_listener_exists` — `hashchange` event listener in `app.js`
- `test_pushstate_in_switchTab` — `history.pushState` called in `switchTab`

## No Runtime Changes

- `app/models/*`, `app/core/*`, `app/calculations/*` — unchanged
- No waterfall/SHL/tax/debt engine changes
- No persistence added

## Acceptance Criteria ✅

| Criterion | Status |
|-----------|--------|
| Clicking OPEX shows OPEX panel | ✅ |
| Clicking CAPEX shows CAPEX panel | ✅ |
| Clicking SHL shows SHL panel | ✅ |
| Clicking P&L shows P&L panel | ✅ |
| Only one panel visible at a time | ✅ |
| Active tab visually highlighted | ✅ |
| No full page reload on tab switch | ✅ |
| app.js loads with `defer` | ✅ |
| No inline `onclick` handlers | ✅ |
| Overview active on load | ✅ |
| Tab selection bookmarkable via URL hash | ✅ |