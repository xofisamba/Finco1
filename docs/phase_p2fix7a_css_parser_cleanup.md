# Phase P2-FIX-7A — CSS Parser Cleanup

**Status:** DRAFT PR
**Base:** `p2-fix-7-production-cleanup` (P2-FIX-7, PR #625 DRAFT)
**Type:** presentation only (CSS + template + tests)

## Goal

P2-FIX-7 added a temporary inline `<style>` block in
`app/templates/partials/_standalone_header.html`
because pre-existing CSS syntax errors in
`static/styles.css` caused browsers to abort CSS
parsing partway through the file, masking the
P2-FIX-7 standalone page rules.

P2-FIX-7A fixes the underlying CSS parser bugs
directly so the inline fallback is no longer
needed.

## Pre-existing CSS parser bugs

Phase P2-FIX-VERIFY and P2-FIX-7 discovered that
`static/styles.css` had a parser break around
line 6705 that prevented browsers from loading
any rules declared after that line. P2-FIX-7A
identified the root cause: **two commits added
section headers as malformed comments + unclosed
selector blocks**:

| Bug | Line | Origin | Defect |
|---|---|---|---|
| #1 | 6530 | 8c85168 (Phase 25B-5, Jun 10 2026) | Comment block "Phase 25B-5 — Scenario workflow polish" inserted without an opening `/*` |
| #2 | 6705 | 8c85168 (Phase 25B-5, Jun 10 2026) | `.ds-badge--factory {` opened but never closed |
| #3 | 6876 | 8c85168 (Phase 25B-5, Jun 10 2026) | `.workspace-dirty-state-bar__title {` opened but never closed |
| #4 | 6893 | 554599e (Phase 25B-6, Jun 10 2026) | Comment block "Phase 25B-6 — Generic Project Review Pack" inserted without an opening `/*` |
| #5 | 6900 | 554599e (Phase 25B-6, Jun 10 2026) | `.sw-quick-summary__row {` opened but never closed |
| #6 | 7172 | 554599e (Phase 25B-6, Jun 10 2026) | `.sw-empty--many {` opened but never closed |

All six defects were introduced during two
adjacent phases (25B-5 and 25B-6) that added
"SW polish" UI without an integrated CSS test.
The combination of malformed comments + unclosed
blocks caused browsers to abort parsing on the
external stylesheet, dropping every rule declared
after line 6530 (effectively all of P2-FIX-5A's
standalone page rules).

## Fix

P2-FIX-7A fixes all six defects:

1. **Bug #1 + #2**: Add the missing `}` for
   `.ds-badge {` and turn the malformed text
   into a real CSS comment header (with both
   opening `/*` and closing `*/`).
2. **Bug #3**: Add the missing `}` for
   `.workspace-dirty-state-bar__title`.
3. **Bug #4 + #5**: Add `/*` opening delimiter
   for the malformed comment block; add `{}`
   for the empty `.sw-quick-summary__row` block.
4. **Bug #6**: Add the missing `}` for
   `.sw-empty--many`.

For Bug #2 (`.ds-badge--factory`), the original
intent was to render a "Read-only protected
original" badge (used by `app/ui/dirty_state.py`
with `css_class="ds-badge--factory"`). The
malformed block had `background: #eef0f3;` (grey)
but no `color` or `border-color`. P2-FIX-7A adds
`color: #4a5566;` and `border-color: #cdd3dc;`
consistent with the other `.ds-badge--*` variants
(green, yellow, orange, grey).

The fixes preserve the visual intent of the
original (but malformed) CSS and add P2-FIX-7A
explanatory comments explaining the history.

## Validation

After the fix, the same cssutils parser that
previously stopped at line ~6705 now parses
**1337 CSS rules and reaches the end of the
file**, including the P2-FIX-7 standalone page
rules. A live Chromium browser loaded via
Playwright now reports:

- 5 standalone rules present
- 6 page-shell rules present
- `.standalone-main` computed `max-width: 1200px`
- `.standalone-main` computed `padding: 40px 24px 48px`
- `.page-shell` computed `border-radius: 12px`
- `.page-shell` computed `background-color: rgb(255, 255, 255)`

All of these match the values declared in
`static/styles.css`, confirming the external
stylesheet now delivers the rules on its own.

## Removal of inline `<style>` fallback

Once the CSS parser is fixed, the inline `<style>`
block P2-FIX-7 added in
`app/templates/partials/_standalone_header.html`
is dead weight. P2-FIX-7A removes it and restores
the template to the P2-FIX-5A markup (with a
P2-FIX-7A explanatory comment about the history).

The standalone pages (`/`, `/projects/new`,
`/projects/browse`) continue to render correctly
without the inline fallback — the standalone
page CSS now loads from the external stylesheet
only.

## Files Changed (12, +198/-71)

| File | Change | Purpose |
|---|---|---|
| `static/styles.css` | M, +37/-14 | Fix 6 CSS parser bugs |
| `app/templates/partials/_standalone_header.html` | M, +5/-60 | Remove inline `<style>` fallback |
| `tests/test_phase_p2fix7a_css_parser_cleanup.py` | NEW, +365 | 9 new tests in 3 classes |
| `tests/test_phase_p2fix2_shell_strip.py` | M, +9 | Cross-arc allowlist |
| `tests/test_phase_p2fix3_c2_first_edit.py` | M, +2 | Cross-arc allowlist |
| `tests/test_phase_p2fix4_five_area_navigation.py` | M, +7 | Cross-arc allowlist |
| `tests/test_phase_p2fix5b_normal_mode_shell_strip.py` | M, +2 | Cross-arc allowlist |
| `tests/test_phase_p2fix5c_dashboard_kpi.py` | M, +2 | Cross-arc allowlist |
| `tests/test_phase_p2fix5d_five_area_navigation.py` | M, +2 | Cross-arc allowlist |
| `tests/test_phase_p2fix5e_reference_ux.py` | M, +2 | Cross-arc allowlist |
| `tests/test_phase_p2fix6_c2_create_copy_ui.py` | M, +2 | Cross-arc allowlist |
| `tests/test_phase_p2fix7_production_cleanup.py` | M, +8 | Inline-style test inverted |
| `docs/phase_p2fix7a_css_parser_cleanup.md` | NEW | this file |
| `reports/phase_p2fix7a_css_parser_cleanup.md` | NEW | execution report |

## Test Results

- **9/9 P2-FIX-7A tests PASS** (3 classes: CSS
  parser bugs fixed, inline style fallback
  removed, file scope)
- **204/204 cross-arc tests PASS** (P2-FIX-{2,3,4,5A,5B,5C,5D,5E,6,7,7A} + 51F)
- 21/21 Phase 51F parity guardrails PASS

## Hard Constraints Preserved

- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` unchanged
- No formula / model / debt / tax / IDC / construction / R-PAR / C10 / R99/R102 / G20 changes
- No persistence schema migration
- No `static/app.js` or `main_api.py` changes
- No new dependencies
- No factory / waterfall / capex_engine / excel_export / persistence changes
- TUHO / Oborovo factory paths intact
- P2-FIX-3 C2 first-edit-copy behaviour intact
- P2-FIX-5A standalone page templates work (CSS
  now loads from external stylesheet)
- P2-FIX-6 Create Editable Copy button still
  works for TUHO/Oborovo only
- P2-FIX-7 "Unknown" / "Protected original" banner
  fixes intact

## Stop-after-report Contract

- This PR is DRAFT, not marked ready, not merged
- Do NOT start M1, M2, Scenario Matrix, new
  feature work, or any construction/C10/R-PAR
  work until review/approval
