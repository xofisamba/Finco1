# UI-2.4 — Factory Lock Indicator Partial

## Context

UI-2.4 is the fourth runtime UI implementation, the second in the
second runtime stack after UI-2.3. It adds a reusable factory lock
indicator partial and wires it minimally into the workspace shell.

**This is a DRAFT PR. NO auto-merge. User visual review required.**

## Branch

`phase-ui2-4-factory-lock-indicator`
**Base:** UI-2.3 branch head (rebased onto main post-UI-2.3)

## Files Changed

### New files
- `app/templates/partials/_factory_lock_indicator.html` (NEW, 40 lines)
- `tests/test_ui2_4_factory_lock_indicator.py` (NEW, 50 tests)
- `docs/ui2_4_factory_lock_indicator.md` (this file)
- `reports/ui2_4_factory_lock_indicator.json`

### Modified files (additive only)
- `app/templates/partials/workspace_shell.html` (added 4-line `{% with %}` + `{% include %}` block)
- `static/styles.css` (added 49 lines of `.factory-lock-*` classes)

### NOT changed
- `main_web.py`
- `app/services/`
- `app/persistence/`
- `app/runtime_impact_taxonomy.py`
- `static/app.js`
- All other templates
- All other CSS classes
- `:root` CSS variables

## Indicator Spec

### Detection logic (per Phase 54F-J workaround)

The partial renders the indicator when ANY of these conditions is met:

1. `is_factory_template` is supplied and is `true`/`'true'`/`'1'`
2. `template_source` contains "TUHO" or "Oborovo" (case-insensitive)
3. `project_origin` contains "TUHO" or "Oborovo" (case-insensitive)
4. `template_source` contains "factory" (case-insensitive)

If none of the above is true, the partial renders **NOTHING**.

### HTML structure

```html
<div class="factory-lock-indicator" role="status" aria-label="Factory template indicator">
  <span class="factory-lock-icon" aria-hidden="true">FL</span>
  <div class="factory-lock-body">
    <span class="factory-lock-title">Factory template — {name}</span>
    <span class="factory-lock-desc">Create a scenario or use Save As before editing controlled assumptions.</span>
  </div>
</div>
```

## Behavior

- **Safe fallback:** If no factory signal is found, renders NOTHING (no empty div, no whitespace)
- **Compact size:** Smaller than UI-2.1 banner (0.5rem padding vs 0.75rem)
- **No backend context required:** Uses only `form_data` keys already in the workspace_shell template
- **No enterprise permissioning implication:** Just a UI hint, no actual lock

## Safe Copy Used

- "Factory template — {name}"
- "Create a scenario or use Save As before editing controlled assumptions."

## No-Go Copy Check

- ✓ No "bankable", "lender-ready", "lender-grade"
- ✓ No "certified template", "approved model", "bank-ready template"
- ✓ No "locked by governance", "production control"
- ✓ No "investor-ready", "production-ready"
- ✓ No "guaranteed returns", "investment advice", "customer reference"
- ✓ No "external validation"
- ✓ No "audit-ready"
- ✓ No "validated" alone

## Hard Gates (UI-2.4)

- ✓ Only allowed files modified
- ✓ No backend/service/persistence changes
- ✓ No `runtime_impact_taxonomy.py` changes
- ✓ No `static/app.js` changes
- ✓ No `:root` CSS variable changes
- ✓ No new forbidden UI claims
- ✓ Phase 51F (21/21) + 52F G1-G6 (10/10) + 53I + 54x + UI-2.1 + UI-2.2 + UI-2.3 tests pass
- ✓ 50 new UI-2.4 tests pass
- ✓ 713 total tests pass
- ✓ rc1 (b425a07) untouched

## Visual Review Checklist

For the user (after PR is opened as DRAFT):

- [ ] Indicator appears at top of workspace shell (after project-browser-container)
- [ ] When no factory signal, NOTHING renders (no empty div, no whitespace)
- [ ] When `template_source` contains "TUHO" or "Oborovo", indicator appears
- [ ] Lock icon "FL" visible
- [ ] Indicator is compact and inline
- [ ] Copy says "Factory template" + "Create a scenario or use Save As..."
- [ ] No forbidden UI claims
- [ ] No regression in other workspace shell elements
- [ ] Accessible (role="status", aria-label, aria-hidden on icon)

## Test results

- `tests/test_ui2_4_*.py`: 50/50 pass
- `tests/test_ui2_3_*.py`: 50/50 pass
- `tests/test_ui2_2_*.py`: 50/50 pass
- `tests/test_ui2_1_*.py`: 56/56 pass
- `tests/test_phase54*.py`: 412/412 pass
- `tests/test_phase51f_*.py`: 21/21 pass
- `tests/test_phase52f_*.py`: 29/29 pass
- `tests/test_phase53i4_*.py`: 45/45 pass
- **Total: 713/713 pass**
