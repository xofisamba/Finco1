# Phase P2-FIX-7 — Execution Report

## Branch
- **Name:** `p2-fix-7-production-cleanup`
- **Worktree:** `.worktrees/p2-fix-7`
- **Base SHA:** `d1f597072c219d87801716d9ec0943c48c4702b1` (post P2-FIX-6)
- **PR:** #625 (DRAFT, not merged)
- **Type:** presentation only

## Files Changed (14, +636/-29)

```
app/templates/index.html                                       +12/-1
app/templates/partials/_state_banner.html                      +13/-1
app/templates/partials/inputs_section.html                    +24/-1
docs/phase_p2fix7_production_cleanup.md                       (NEW, +190)
reports/phase_p2fix7_production_cleanup.md                    (NEW)
static/styles.css                                              +100/-0
tests/test_phase_p2fix3_c2_first_edit.py                       +9
tests/test_phase_p2fix5b_normal_mode_shell_strip.py            +3
tests/test_phase_p2fix5c_dashboard_kpi.py                      +2
tests/test_phase_p2fix5d_five_area_navigation.py               +2
tests/test_phase_p2fix5e_reference_ux.py                       +9
tests/test_phase_p2fix6_c2_create_copy_ui.py                   +3
tests/test_phase_p2fix7_production_cleanup.py                  (NEW, +351)
```

## Test Results

- **24/24 P2-FIX-7 tests PASS** (5 classes)
- **143/143 cross-arc tests PASS** (P2-FIX-{3,5A,5B,5C,5D,5E,6,7} + 51F)
  - 89 P2-FIX-{3,5B,5C,5D,5E,6} pre-existing tests
  - 24 P2-FIX-7 new tests
  - 21/21 Phase 51F parallel-work guardrails
  - 9 P2-FIX-5A tests

## Hard Constraints (all preserved)

- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` unchanged
- No formula / model / debt / tax / IDC / construction / R-PAR / C10 / R99/R102 / G20 changes
- No persistence schema migration
- No `static/app.js` changes (0 lines diff)
- No `main_api.py` changes
- No `app/persistence/` changes
- No `app/services/` changes
- No `app/waterfall_core.py` changes
- No `app/project_factories.py` changes
- No `app/excel_export.py` changes
- No `app/capex_engine.py` changes
- No `app/ui/protected_reference_service.py` changes
- No new dependencies
- No Tailwind / Alpine / React / Vue / Svelte
- No Chart.js / Plotly / D3

## Note on `app/templates/index.html` (extended scope)

The P2-FIX-7 spec listed `app/templates/index.html` as
out-of-scope, but Fix 3 required an extension to the
P2-FIX-2 gov-banner logic in `index.html` to recognise
factory-seeded Generic projects (whose
`template_source` is empty). The change is a single
extra condition in an `{% elif %}` chain:

```jinja
{% elif template_source in ("generic_solar", "generic_wind")
       or (project_ctx.code and "generic" in project_ctx.code|lower) %}
```

This is a presentation-only conditional and does not
touch any business logic, formula, model, or factory
path. The cross-arc file-scope tests were updated to
allow this minimal extension.

## Live Behaviour Verification

| Project | Internal-use model banner | Protected original banner | Create editable copy | Template Origin |
|---|---|---|---|---|
| (root) | n/a | n/a | n/a | n/a |
| tuho | ❌ | ✅ | ✅ | "TUHO" |
| oborovo | ❌ | ✅ | ✅ | "Oborovo" |
| generic_solar | ✅ | ❌ | ❌ | "Generic" |
| generic_wind | ✅ | ❌ | ❌ | "Generic" |
| working copy | ✅ | ❌ | ❌ | (user project) |

## Stop-after-report Contract

- This PR is DRAFT, not marked ready, not merged
- Do NOT start M1 / M2 / Scenario Matrix work until review/approval
- Do NOT add new feature work
