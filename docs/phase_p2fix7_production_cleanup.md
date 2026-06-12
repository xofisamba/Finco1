# Phase P2-FIX-7 — Production Reality Cleanup

**Status:** DRAFT PR
**Base:** `d1f597072c219d87801716d9ec0943c48c4702b1` (post P2-FIX-6)
**Type:** presentation only

## Goal

P2-FIX-VERIFY confirmed that production = main and
P2-FIX arc #615..#624 is code-complete, but 3
production-facing mismatches remain:

1. Unstyled standalone pages (P2-FIX-5A CSS gap)
2. "Unknown" Template Origin for Generic projects
   (Phase 20D bug)
3. Duplicate "Protected original" banner for Generic
   projects (P2-FIX-2 + P2-FIX-5/6 over-broad)

P2-FIX-7 closes all three.

## Fix 1 — Standalone page CSS

`app/templates/partials/_standalone_header.html` and
the 3 standalone page templates
(`project_home_page.html`, `project_new_page.html`,
`project_browse_page.html`) reference these classes
that P2-FIX-5A introduced but did not style:

- `body.standalone-page`
- `.standalone-main`
- `.standalone-main--minimal`
- `.standalone-main--browse`
- `.page-shell`
- `.page-shell--project-home`
- `.page-shell--project-new`
- `.page-shell--project-browse`
- `.page-shell-header`
- `.page-shell-title`
- `.page-shell-desc`
- `.page-shell-footer`

P2-FIX-7 adds the matching CSS rules to
`static/styles.css` (last 100 lines). The new rules
are scoped via `body.standalone-page` and use the
existing CSS variables (`--bg`, `--surface`,
`--border`, `--text`, etc.) so they inherit the
Finco One visual language without touching the
workspace pages.

The CSS includes a `@media (max-width: 640px)`
breakpoint that tightens padding on small screens.

## Fix 2 — "Unknown" Template Origin

`app/templates/partials/inputs_section.html` line 4
had:

```jinja
{{ field_row("Template Origin", project_ctx.template_source or "TUHO" if "tuho" in project_ctx.code|lower else "Oborovo" if "oborovo" in project_ctx.code|lower else "Unknown", badge="Reference", badge_class="badge-muted") }}
```

For Generic Solar / Generic Wind, the fallback chain
returns the literal string "Unknown", which is
internal vocabulary leaking into the user surface.

P2-FIX-7 replaces this with an explicit
`{% if %}{% elif %}{% else %}` block:

- `template_source` is set → render that value
- `code in {"tuho", "oborovo"}` (defensive) → render
  "TUHO" / "Oborovo"
- otherwise → render "Generic" with badge "Internal"

Hard-coded `badge="Reference"` was also wrong for
Generic projects. P2-FIX-7 uses `badge="Protected"`
for TUHO/Oborovo and `badge="Internal"` for
Generic.

## Fix 3 — "Protected original" banner restriction

`_state_banner.html` triggers `factory_template`
context for any non-user-created project, including
Generic Solar / Wind. The banner copy ("Protected
original — use Save As or create a scenario…") and
the "PROTECTED" badge are wrong for Generic
projects.

P2-FIX-7 narrows the gate:
- Before: `{% if _ctx == 'factory_template' %}`
- After: `{% if _ctx == 'factory_template' and is_protected_reference %}`

This means Generic Solar / Wind now skip the
state banner entirely. The authoritative
project-type-aware disclosure is the P2-FIX-2
`index.html` gov-banner, which P2-FIX-7 also
extends to recognise Generic factory projects
via `project_ctx.code`.

### P2-FIX-2 index.html extension

The P2-FIX-2 gov-banner logic in `app/templates/index.html`
matched only on `template_source in ("generic_solar",
"generic_wind")`. For factory-seeded Generic
records, `template_source` is empty (the value lives
on `source_project_template`), so the banner fell
through to the "Protected original" else branch.

P2-FIX-7 adds `project_ctx.code|lower` contains
"generic" as a second signal:

```jinja
{% elif template_source in ("generic_solar", "generic_wind")
       or (project_ctx.code and "generic" in project_ctx.code|lower) %}
```

This works because the factory context builder
(`app/ui/project_context.py`) uses code
"GENERIC_SOLAR" / "GENERIC_WIND" (uppercase) for
the `ProjectContext` object, while the lower-cased
check still matches.

## Files Changed (8, +533/-29)

| File | Change | Purpose |
|---|---|---|
| `static/styles.css` | M, +100/-0 | Add standalone page CSS |
| `app/templates/partials/inputs_section.html` | M, +24/-1 | Fix "Unknown" fallback |
| `app/templates/partials/_state_banner.html` | M, +13/-1 | Restrict factory_template gate |
| `app/templates/index.html` | M, +12/-1 | P2-FIX-2 logic extended for Generic |
| `tests/test_phase_p2fix7_production_cleanup.py` | NEW, +351 | 24 new tests in 5 classes |
| `tests/test_phase_p2fix3_c2_first_edit.py` | M, +9 | Cross-arc allowlist |
| `tests/test_phase_p2fix5b_normal_mode_shell_strip.py` | M, +3 | Cross-arc allowlist |
| `tests/test_phase_p2fix5c_dashboard_kpi.py` | M, +2 | Cross-arc allowlist |
| `tests/test_phase_p2fix5d_five_area_navigation.py` | M, +2 | Cross-arc allowlist |
| `tests/test_phase_p2fix5e_reference_ux.py` | M, +9 | Cross-arc allowlist |
| `tests/test_phase_p2fix6_c2_create_copy_ui.py` | M, +3 | Cross-arc allowlist |
| `docs/phase_p2fix7_production_cleanup.md` | NEW | this file |
| `reports/phase_p2fix7_production_cleanup.md` | NEW | execution report |

## Tests (24 new, all PASS)

- **TestStandalonePageCSS** (8): each new class
  defined in CSS
- **TestStandalonePagesRendered** (4): GET /, /projects/new, /projects/browse all include standalone-page + page-shell markers
- **TestTemplateOriginNoUnknown** (5): Generic Solar/Wind Template Origin ≠ "Unknown"; TUHO/Oborovo unchanged; no forbidden internal vocabulary
- **TestProtectedOriginalBannerRestricted** (6): TUHO/Oborovo keep Protected original + Create editable copy; Generic Solar/Wind/working copy do NOT
- **TestFileScope** (1): only allowed files changed

## Cross-arc Regression (cumulative 143 tests)

- 89 P2-FIX-{3,5B,5C,5D,5E,6} tests still PASS
- 24 P2-FIX-7 tests PASS
- 21/21 Phase 51F parallel-work guardrails PASS
- 9 P2-FIX-5A tests PASS

## Hard Constraints Preserved

- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` preserved
- No formula / model / debt / tax / IDC / construction / R-PAR / C10 / R99/R102 / G20 changes
- No persistence schema migration
- No `static/app.js` changes (0 lines diff)
- No `main_api.py` changes
- No new dependencies
- No factory / waterfall / capex_engine / excel_export / persistence changes
- TUHO / Oborovo factory paths intact
- P2-FIX-6 C2 first-edit-copy behaviour intact

## Stop-after-report Contract

- This PR is DRAFT, not marked ready, not merged
- Do NOT start M1, M2, Scenario Matrix work, or any
  new feature work until review/approval
