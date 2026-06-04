# Phase 56H — Post-merge visual QA and hotfix gate

## Status

**DRAFT — Outcome B.** A critical runtime regression was found on
`main` (post-56G). The `GET /` route raised `NameError:
name 'validation_errors' is not defined` because PR #475 (55G)
referenced a bare name inside a dict literal without binding it
in the enclosing scope.

The regression was **not caught by the existing test suite** because:

- 55G/55F/55E tests import the helper functions in isolation; they
  do not render the full index route via FastAPI TestClient.
- Parity Guardrails check structural invariants only (no HTTP 500).
- CI runs the Phase 51F + 51M-1 + revenue + opex + SHL waterfall
  tests, not the index route's `TemplateResponse` call.

A small hotfix PR was opened: **Phase 56H-1** (PR #485,
branch `phase56h-1-hotfix-index-validation-errors-nameerror`).
It is **DRAFT only** and does not auto-merge.

## Current main SHA

`df88b332e22a2920799d1ac376e564e1ed4efa22` (post-56G, post-56F,
post-56E). This SHA has the bug. Visual QA cannot proceed past
the login page until the hotfix is merged.

## Deferred stack

- **Tailwind** — DEFERRED. Token cleanup (Phase 55C follow-up)
  must come before any Tailwind-1 build config.
- **Alpine** — DEFERRED. Same reason. No Alpine component
  needed for the upcoming UI-3.1 LineItemGrid pilot.
- **Generic Solar / Wind** — remain exploratory / unvalidated.
  Productization is out of scope. Generic templates carry the
  `⚠️ Unvalidated · Derived path` label per 56B.
- **BESS / Hybrid / Portfolio** — DO NOT START. Out of scope
  for 56A-56H and the upcoming UI-3.1 pilot.

## Hotfix summary (56H-1)

| | |
|---|---|
| File | `main_web.py` (8 lines added, 1 line changed) |
| Test file | `tests/test_phase56h1_index_validation_errors_hotfix.py` (+345 lines, 12 tests) |
| Branch | `phase56h-1-hotfix-index-validation-errors-nameerror` |
| PR | [#485](https://github.com/xofisamba/Finco1/pull/485) |
| Status | DRAFT, awaiting user review |
| Head SHA | `6bf16f7` |
| CI | ✅ success |
| Parity Guardrails | ✅ success |

### Bug details

```python
# main_web.py, before the fix (post-55G, on main):
return templates.TemplateResponse(
    request=request, name='index.html',
    context={
        ...
        'validation_errors': [],            # key only, not a binding
        ...
        'banner_context': _banner_context_for_index(
            project_record, workspace_state, validation_errors  # NameError
        ),
    },
)
```

Python evaluates the dict-literal values in the enclosing scope.
`validation_errors` was never bound as a local variable, so the
bare-name reference raised `NameError` at runtime, returning
HTTP 500 on every `GET /`.

### Fix

Hoist `validation_errors` to a local variable before the context
dict, then bind the dict value to that local. The template
contract is preserved (the `validation_errors` key is still
exposed to the template).

```python
# main_web.py, after the hotfix:
validation_errors: list[str] = []
return templates.TemplateResponse(
    request=request, name='index.html',
    context={
        ...
        'validation_errors': validation_errors,  # now bound
        ...
        'banner_context': _banner_context_for_index(
            project_record, workspace_state, validation_errors
        ),
    },
)
```

The template context contract is preserved (the
`validation_errors` key is still exposed to the template).
No other routes are affected (only one `_banner_context_for_index`
call site in `main_web.py`).

### Hotfix hard gates verified

- ✅ No `static/app.js` changes
- ✅ No `app/waterfall_core.py` / `app/project_factories.py` changes
- ✅ No `app/runtime_impact_taxonomy.py` changes
- ✅ No `app/persistence/*` changes
- ✅ No financial formula / model output changes
- ✅ No schema/migration changes
- ✅ rc1 (`b425a07`) untouched
- ✅ No new frontend dependencies
- ✅ Minimal diff (+8 / -1 in `main_web.py`)
- ✅ 12 new tests pass
- ✅ 1013 total relevant tests pass
- ✅ CI ✅, Parity Guardrails ✅
- ✅ DRAFT only, no auto-merge

## Static visual QA (against templates/CSS, pre-hotfix)

The 56E / 56F / 56G template + CSS changes look correct on a
static read-through. Specifically:

### 1. Overview tab
- `pilot_help_onboarding.html` is no longer inline (was 302 LOC
  of inline help; now lives in the dedicated Help tab).
- Compact `.help-pointer` appears at the top of the Overview
  with a link to the Help tab.
- `index.html` and `workspace_shell.html` are unchanged in their
  data-binding shape.
- No layout overflow or debug-looking text observed in the
  template source.

### 2. Help tab
- `data-tab="help"` button exists in `workspace_tabs.html`.
- `#panel-help` div exists in `workspace_shell.html`.
- TUHO/Oborovo labels: `[Reference] TUHO ... (has parity
  evidence against Excel)`, `[Reference] Oborovo ...`.
- Generic templates: `[Warning] exploratory / unvalidated`.
- No positive "validated" language in the help copy.

### 3. Sidebar / project switcher
- Active project name is the primary label (`.ps-ap-name`).
- Project code is hidden by default in `<details>`.
- Origin pill: `Reference` / `My project` / `Saved baseline`.
- "New project" is the first action, with `.ps-action-btn--primary`.
- "Switch project" replaces "Load / Switch".
- Existing `openProjectBrowser()`, `closeProjectBrowser()`,
  `switchToProject()` JS calls preserved.

### 4. New Project flow
- Inline form in `workspace_shell.html` (#panel-new-project)
  has 10 master fields: project_name, spv_name, country_market,
  project_type, capacity_mw, currency, construction_start_date,
  construction_duration_months, cod_date, template_source.
- 11 detailed assumptions are hidden in `.np-hidden-defaults`
  block.
- Generic templates show `⚠️ Unvalidated · Derived path` warning.
- COD is read-only/derived server-side; manual override
  is not possible through the UI (56D policy).
- (Note: the side panel `new_project_form.html` retains the
  17-field form per 56C spec — this is intentional, not a
  regression.)

### 5. State banner
- Icon glyphs replaced: `FT/AS/SS/...` → `◆/●/✓/...`.
- `.banner-56f` modifier class added to the rendered `<div>`.
- Smaller padding (0.5rem 0.85rem), smaller font (0.8rem),
  smaller icon (22px), no heavy box-shadow.
- All 11 banner contexts (factory_template, user_created_project,
  active_scenario, saved_scenario, browser_draft, dirty_state,
  stale_result, last_run, validation_failed, display_only_row,
  pending_runtime_source) and 5 tones (info, success, warn,
  fail, neutral) are preserved.
- Accessibility attributes (`role="status"`, `aria-label`,
  `aria-hidden` on icon) preserved.

### 6. Inputs / Scenarios / Audit / Run
- Existing tab structure in `workspace_tabs.html` is unchanged.
- Existing Run Model flow uses `_runtime_summary_for_index` +
  `run_service.execute_run_route` (unchanged from 55E/51B).
- Existing validation/audit UI uses
  `_validation_summary_for_context` (unchanged from 55F).
- `_state_banner.html` is the only banner rendered in the
  workspace; `_validation_summary_bar.html` and
  `_last_run_indicator.html` are separate partials.

## Known limitations

1. **Cannot render the app end-to-end** until the 56H-1 hotfix
   is merged. The runtime regression on `GET /` blocks all
   visual review of 56E/56F until then.
2. **The `new_project_form.html` panel** (the full 17-field
   form at `/projects/new`) is intentionally preserved per
   56C spec. Users can still access all 17 fields via that
   path. This is a deliberate design choice, not a regression.
3. **No screenshots taken** in this QA pass — the QA was
   static (template/CSS source read-through + TestClient
   smoke test of `GET /login` and `GET /`).

## No-go copy check

- ✅ No bankability / lender-ready / audit-ready / certified
  claims introduced
- ✅ No positive "validated" claims in implemented templates
- ✅ G20 BLOCKED, R99/R102 NOT APPROVED preserved
- ✅ Generic Solar / Wind remain exploratory / unvalidated
- ✅ Backend remains source of truth
- ✅ No JS financial calculations
- ✅ rc1 (`b425a07`) frozen across all of 55G / 56A-G / 56H-1

## Recommendation

**Outcome B — fix the runtime regression first, then do the
visual review.**

1. **Merge PR #485 (56H-1 hotfix)** — required before any
   visual review can happen. The hotfix is small (8 lines)
   and well-tested (12 new tests).
2. **After merge, do the visual review** of 56E / 56F / 56G
   per the 56G closeout checklist. The runtime is now stable
   enough to render the index page.
3. **Then proceed to UI-3.1 LineItemGrid CAPEX summary
   pilot** (per 55B recommendation), once the user gives
   visual approval.

### What NOT to do

- ❌ Do NOT start UI-3.1 until 56H-1 is merged and the user
  has visually approved 56E/56F.
- ❌ Do NOT skip 56H-1 and start UI-3.1 — the index route
  is broken on main and no test will catch it for UI-3 either.
- ❌ Do NOT bundle additional fixes into 56H-1. If anything
  else turns up in the post-merge visual review, open a
  separate 56H-2 / 56H-3 / etc. PR.

### Hard no-go preserved

- ✅ G20 BLOCKED
- ✅ R99/R102 NOT APPROVED
- ✅ Generic Solar / Wind exploratory
- ✅ Backend source of truth
- ✅ No JS financial calculations
- ✅ rc1 frozen
