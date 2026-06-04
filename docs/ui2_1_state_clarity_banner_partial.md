# UI-2.1 — State Clarity Banner Partial

## Context

UI-2.1 is the first runtime UI implementation after a long
docs/spec phase. It adds a reusable state-clarity banner partial
and wires it minimally into `index.html`.

**This is a DRAFT PR. NO auto-merge. User visual review required.**

## Branch

`phase-ui2-1-state-clarity-banner`
**Base:** `075dc77b5953226b9115513ff208671da97030ef` (post-54J main)

## Files Changed

### New files
- `app/templates/partials/_state_banner.html` (NEW, 90 lines)
- `tests/test_ui2_1_state_banner_partial.py` (NEW, 56 tests)
- `docs/ui2_1_state_clarity_banner_partial.md` (this file)
- `reports/ui2_1_state_clarity_banner_partial.json`

### Modified files (additive only)
- `app/templates/index.html` (added 3-line include)
- `static/styles.css` (added 96 lines of `.banner-*` classes)

### NOT changed
- `main_web.py`
- `app/services/`
- `app/persistence/`
- `app/runtime_impact_taxonomy.py`
- `static/app.js`
- All other templates
- All other CSS classes
- `:root` CSS variables

## Banner Spec

### 11 supported contexts

| Context | Title | Description |
|---|---|---|
| `factory_template` | "Factory template" | "Factory template — use Save As or create a scenario before editing controlled assumptions." |
| `user_created_project` | "User-created project" | "You created this project. All inputs are editable unless source-locked." |
| `active_scenario` | "Active scenario" | "Editing the active scenario updates the model after save." |
| `saved_scenario` | "Saved scenario" | "Saved. Scenario ID on file. Use the scenario tab to load or duplicate." |
| `browser_draft` | "Browser draft" | "Unsaved browser draft — changes are not saved to a scenario yet." |
| `dirty_state` | "Unsaved changes" | "This scenario has unsaved changes. Save the scenario to create a clean snapshot, then run the model." |
| `stale_result` | "Stale result" | "Results may be stale — inputs changed after the last run. Re-run the model for current results." |
| `last_run` | "Last run available" | "Last run available — review model evidence before export." |
| `validation_failed` | "Validation failed" | "Validation checks need review before relying on this run." |
| `display_only_row` | "Display only" | "This row is for reference. Editing is disabled." |
| `pending_runtime_source` | "Pending runtime source" | "This input is captured but the runtime source is not yet wired. Display only." |

### 5 supported tones

| Tone | Color | Use for |
|---|---|---|
| `info` | blue (`#1a56db`) | informational banners |
| `success` | green (`#0f7a52`) | success / saved |
| `warn` | amber (`#b45309`) | warnings |
| `fail` | red (`#b91c1c`) | failures |
| `neutral` | slate (`#7a96b8`) | neutral / last run |

### HTML structure

```html
<div class="banner banner-{tone}" role="status" aria-label="{title}">
  <span class="banner-icon" aria-hidden="true">{icon}</span>
  <div class="banner-body">
    <span class="banner-title">{title}</span>
    <span class="banner-desc">{description}</span>
  </div>
</div>
```

## Behavior

- Renders NOTHING if `banner_context` is missing (safe default)
- Defaults `banner_tone` to `info` if not provided
- Renders icon as a 2-letter code (e.g., "FT" for factory template)
- Has `role="status"` and `aria-label` for accessibility

## No-Go Copy Check

- ✓ No "bankable", "lender-ready", "certified", "audit-ready", "validated" (alone)
- ✓ No "investor-ready", "SaaS-ready", "production-ready"
- ✓ No "guaranteed returns", "investment advice", "customer reference"
- ✓ No "external validation"
- ✓ All copy uses safe terms: "model evidence", "validation checks", "review"

## Hard Gates (UI-2.1)

- ✓ Only allowed files modified
- ✓ No backend/service/persistence changes
- ✓ No `runtime_impact_taxonomy.py` changes
- ✓ No `static/app.js` changes
- ✓ No `:root` CSS variable changes
- ✓ No new forbidden UI claims
- ✓ Phase 51F (21/21) + 52F G1-G6 (10/10) + 53I + 54x tests pass
- ✓ 56 new UI-2.1 tests pass
- ✓ 563 total tests pass
- ✓ rc1 (b425a07) untouched

## Visual Review Checklist

For the user (after PR is opened as DRAFT):

- [ ] Banner appears in correct position (between `gov-banner` and `workspace_shell`)
- [ ] When `banner_context` is not supplied, NOTHING renders (no empty div, no whitespace)
- [ ] Each of the 5 tones renders with correct color
- [ ] Each of the 11 contexts has correct title and description
- [ ] Icon is visible and uses 2-letter code
- [ ] Banner is responsive (works on narrow viewports)
- [ ] No regression in `gov-banner` (existing governance banner)
- [ ] No regression in other parts of the UI

## Test results

- `tests/test_ui2_1_*.py`: 56/56 pass
- `tests/test_phase54*.py`: 412/412 pass
- `tests/test_phase51f_*.py`: 21/21 pass
- `tests/test_phase52f_*.py`: 29/29 pass
- `tests/test_phase53i4_*.py`: 45/45 pass
- **Total: 563/563 pass**
