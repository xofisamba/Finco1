# Phase P2-FIX-6 — C2 Create Editable Copy UI

**Status:** DRAFT PR (in review)
**Base:** `09ca2417bf1856803aeb9e0c3547af7877d53f8c` (post P2-FIX-5E)
**Type:** presentation only (no model, no schema, no formula, no debt/tax/IDC)

## Goal

Phase P2-FIX-3 (PR #617) added the C2 first-edit-copy flow for
TUHO / Oborovo protected reference projects: opening a protected
project is free, but the first edit attempt returns 409
`needs_copy_confirmation=true` and the user must POST to
`/projects/{code}/confirm-first-edit-copy` to create a
user-owned working copy.

The backend was wired in P2-FIX-3. The **UI button** for that
backend action was missing. Pilots running on TUHO/Oborovo
saw the "Protected original" banner but had no visible way
to convert the read-only reference into an editable
working copy.

P2-FIX-6 completes the C2 UX by adding a visible
**"Create editable copy"** button in the state banner.

## Architecture

The state banner is rendered by the shared partial
`app/templates/partials/_state_banner.html`. It fires when
`_banner_context_for_index` returns `"factory_template"`
(meaning the active project's `project_origin != "user_created"`).

P2-FIX-6 adds an **additional guard** inside the partial:
the button is only rendered when the active project is a
**protected reference** AND the user is NOT already viewing
a user-created working copy.

```jinja
{% if _ctx == 'factory_template' and is_protected_reference and not is_user_project %}
  <form method="POST"
        action="/projects/{{ active_project_code }}/confirm-first-edit-copy">
    <button class="btn btn-primary"
            data-p2fix6-cta="create-editable-copy">
      Create editable copy
    </button>
  </form>
{% endif %}
```

The backend C2 route was added in P2-FIX-3:
- `POST /projects/{code}/confirm-first-edit-copy` returns
  302 redirect to the new working copy
- The new working copy has `project_origin = "user_created"`
  and `template_source` cleared
- The original fixture is unchanged
- `replay_metadata` records the source for lineage

The button preserves the existing C2 backend contract
verbatim — it just gives the pilot a UI to trigger the
existing endpoint.

## Files Changed (8, +113/-15)

| File | Change | Purpose |
|---|---|---|
| `app/templates/partials/_state_banner.html` | M, +27/-0 | Add conditional CTA form |
| `main_web.py` | M, +7/-0 | Add `is_protected_reference` to render context + import |
| `tests/test_phase_p2fix6_c2_create_copy_ui.py` | NEW, +311 | 15 new tests in 5 classes |
| `tests/test_phase_p2fix3_c2_first_edit.py` | M, +15 | Extend allowlist for cross-arc |
| `tests/test_phase_p2fix5b_normal_mode_shell_strip.py` | M, +5 | Extend allowlist for cross-arc |
| `tests/test_phase_p2fix5c_dashboard_kpi.py` | M, +3 | Extend allowlist for cross-arc |
| `tests/test_phase_p2fix5d_five_area_navigation.py` | M, +3 | Extend allowlist for cross-arc |
| `tests/test_phase_p2fix5e_reference_ux.py` | M, +3 | Extend allowlist for cross-arc |
| `docs/phase_p2fix6_c2_create_copy_ui.md` | NEW | this file |
| `reports/phase_p2fix6_c2_create_copy_ui.md` | NEW | execution report |

## Tests (15 new, all PASS)

- **TestCreateEditableCopyButtonVisible** (5):
  - TUHO workspace has button
  - Oborovo workspace has button
  - Button form action is `/projects/tuho/confirm-first-edit-copy`
  - Form method is POST
  - Button has `data-p2fix6-cta` marker
- **TestButtonNotShownForNonProtected** (3):
  - Generic Solar no button
  - Generic Wind no button
  - No confirm route link in generic
- **TestConfirmRouteStillWorks** (4):
  - TUHO confirm returns 200/302
  - Oborovo confirm returns 200/302
  - Generic Solar confirm returns 400
  - Unknown project confirm returns 404
- **TestProtectedReferenceFirstEditGuard** (2):
  - TUHO first edit returns 409 with `needs_copy_confirmation=true`
  - Oborovo first edit returns 409
- **TestFileScope** (1):
  - Only allowed files changed, no persistence/services/debt/etc

## Cross-arc Regression

- 89 P2-FIX-{3,5B,5C,5D,5E,6} tests PASS
- 21/21 Phase 51F parallel-work guardrails PASS

## Hard Constraints Preserved

- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` preserved
- TUHO/Oborovo parity preserved (factory paths intact)
- No formula / model / debt / tax / IDC / construction / R-PAR / C10 / R99/R102 / G20 changes
- No persistence schema migration
- No `static/app.js` changes (0 lines diff)
- No `main_api.py` changes
- No new dependencies
- No Tailwind / Alpine / React / Vue / Svelte
- No Chart.js / Plotly / D3
- The P2-FIX-3 first-edit guard is preserved (verified
  by `TestProtectedReferenceFirstEditGuard`)

## Stop-after-report Contract

This PR is DRAFT, not marked ready, not merged.
Do NOT start P2-FIX-7 until P2-FIX-6 review/approval.
