# Phase 57F — UI-3.2 next-grid readiness plan

## Status

DRAFT → marked ready → squash merged in the 57F overnight
branch (see `reports/phase57f_ui3_2_next_grid_readiness_plan.json`
for the merge SHA).

This is a **plan only**. 57F does NOT implement a runtime
grid migration. The next grid migration (UI-3.2) is a
future PR (57F-1 or similar) that must be approved by the
user before implementation.

## Current main SHA (start of 57F)

`9f194ed7bbaa792049573f72bb6699ba25fb701d` (post-57E, CSS
token consolidation inventory merged)

## Current main SHA (after 57F)

Reported in the 57F combined report.

## 57A results summary

Phase 57A merged the LineItemGrid CAPEX summary pilot
(PR #487, merge `b173355b`).

### What 57A achieved
- New shared partial `app/templates/partials/_line_item_grid.html`
  with a `lig_render` macro.
- `app/templates/partials/sheet_capex.html` migrated to use
  the new partial.
- 57 new tests; 96 new tests across 57A + 57pre updates.
- All hard gates passed; CI and Parity Guardrails green.
- rc1 frozen (`b425a0708719eaa5e1d922b1008e5609758e0ad4`).

### What 57A had to fix after review
- **Fix A (REQUIRED)**: financing rows were editable in user
  project mode. Added `data_financing` row type. New CSS
  class `lig-row--data-financing`. 3 new tests pin
  read-only semantics.
- **Fix B (REQUIRED)**: 57pre template-change relaxation
  was too broad. Tightened to diff-based allowlist of
  exactly the two 57A template files. New
  `TestTemplateChangeAllowlist` class with 5 tests.
- **Fix C (RECOMMENDED)**: section band labels used `| safe`,
  producing literal `&` in HTML. Removed `| safe`. New
  test pins `&amp;` escape.
- **Fix D (RECOMMENDED)**: macro contract comment listed
  unsupported cell kinds. Updated to match actual
  implementation.

These fixes demonstrate that **the migration review is
non-trivial** and should not be done in a single overnight
sprint.

## Candidate next grids

| Sheet | LOC | Estimated complexity | Visual similarity to 57A |
|---|---|---|---|
| `sheet_opex.html` | ~300-400 | Medium | High (similar row structure: data, subtotal, total) |
| `sheet_opex_detail.html` | ~250-350 | Medium | Medium (has period columns) |
| `sheet_revenue.html` | ~300-400 | Medium | High (similar row structure) |
| `sheet_capex_detail.html` | ~300-400 | Low | High (CAPEX family) |
| `sheet_senior_debt.html` | ~200-300 | Low | Medium (less granular) |
| `sheet_shl.html` | ~200-300 | Low | Medium (less granular) |
| `sheet_tax.html` | ~200-300 | Low | Low (different structure) |
| `sheet_construction.html` | ~200-300 | Low | Low (different structure) |
| `sheet_production.html` | ~200-300 | Low | Low (different structure) |
| `sheet_inputs.html` | varies | High | Low (form-like) |
| `sheet_financials.html` | varies | High | Low (summary) |
| `sheet_idc.html` | ~200-300 | Low | Medium |

(Exact LOC numbers depend on the current state of each
template. They are estimated from the 57A baseline.)

## Recommendation: do NOT migrate a second grid overnight

The 57A review required 4 fixes (Fix A was a behavior
regression). The risk of a second overnight grid migration
without user visual review is high.

**Recommendation:**

1. **Do NOT migrate a second grid in 57F.**
2. **Wait for user visual review of 57A** (the LineItemGrid
   CAPEX pilot) before starting UI-3.2.
3. **UI-3.2 should be a DRAFT PR only** (not auto-merged),
   even if all hard gates pass. The user must review and
   approve it.
4. **Likely next candidate** (after visual review of 57A
   passes): `sheet_opex.html` (OPEX summary). Reasons:
   - Similar row structure to CAPEX summary (data, subtotal,
     total), reducing migration risk.
   - High value to the user (OPEX is the second-most-edited
     sheet after CAPEX).
   - Tests the "per-run vs governance" semantics in a
     different sheet (per-run check family is different).
   - Generic Solar/Wind exploration can be deferred.

Alternative candidates if OPEX is not ready:
- `sheet_revenue.html` (similar to OPEX, but has tariff
  fields that are user-editable in user project mode).
- `sheet_capex_detail.html` (CAPEX family, but smaller
  win — most users look at the summary, not the detail).

## Auto-merge policy for UI-3.2

**No auto-merge for UI-3.2 runtime grid migration.** Even
if all hard gates pass, UI-3.2 must be:

- Marked as **DRAFT** in the PR.
- Reviewed by the user (visual + code).
- Marked ready explicitly by the user.
- Squash-merged only after explicit user approval.

The 57A experience (4 fixes after review) is a strong
argument for this policy. The user should be the gate.

## Required preparation for UI-3.2

If the user approves UI-3.2 after 57F:

### Allowed files
- `app/templates/partials/_line_item_grid.html`
  (only if LineItemGrid macro needs minor extension)
- `app/templates/partials/sheet_<chosen>.html` (the
  target sheet, e.g. `sheet_opex.html`)
- `tests/test_phase<phase>_ui3_2_<sheet>_grid_<summary>.py`
- `docs/phase<phase>_ui3_2_*.md`
- `reports/phase<phase>_ui3_2_*.json`
- `tests/test_phase57pre_route_render_smoke.py` (only the
  `ALLOWED_57A_TEMPLATE_PATHS` allowlist must be updated to
  include the new sheet path; default NO update — UI-3.2
  must add its own allowlist as a separate test or extend
  the existing one explicitly).

### Forbidden files
- `main_web.py`
- `app/waterfall_core.py`
- `app/project_factories.py`
- `app/persistence/` (any file)
- `app/services/` (any file)
- `static/app.js`
- `static/styles.css` (unless the user explicitly approves
  a CSS change as part of UI-3.2)
- `static/app.js`
- Any schema / migration file
- Any fixture CSV
- Any frontend dependency (`package.json`, etc.)

### Tests required
- All 57A test classes (10+ classes) extended for the new
  sheet
- A `test_<chosen>_rows_readonly_when_financing` test
  (mirror of Fix A)
- A `test_<chosen>_row_order_matches_<pre_migration>` test
- A `test_<chosen>_section_bands_escaped` test (Fix C)
- A `test_<chosen>_preserves_existing_<key_class>es` test
- A `test_ui_2_wires_still_active` test (regression for
  55E/55F/55G)
- A `test_56h1_hoist_still_present` test (regression for
  56H-1)
- A `test_57pre_template_change_allowlist_updated` test
  (extend the allowlist to include the new sheet)

### Visual review checklist
- [ ] Open the app in a browser
- [ ] Navigate to the migrated sheet
- [ ] Confirm row labels and order match the pre-UI-3.2
      hand-written table
- [ ] Confirm kEUR formatting matches pre-UI-3.2
- [ ] Confirm editable / read-only semantics match
      pre-UI-3.2 (financing rows are read-only in user
      project mode for sheets that have financing rows)
- [ ] Confirm column order is unchanged
- [ ] Confirm section bands / subtotals / totals are
      visually clear
- [ ] Confirm no horizontal overflow
- [ ] Confirm Inputs tab still opens
- [ ] Confirm GET / still works
- [ ] Confirm Overview / Inputs / Audit tabs all load
- [ ] Confirm no console errors / no network 404s

### Rollback plan
- The 57F-1 PR is squashed into main. To roll back:
  - `git revert <merge-sha>` and merge the revert.
  - OR: `git checkout <pre-merge-sha> && git branch -f
    main <pre-merge-sha>` and force-push (only if no
    follow-up commits depend on the UI-3.2 work).
- The LineItemGrid partial is not removed in the rollback
  unless explicitly removed; it remains available for
  future use.

### Should UI-3.2 wait for validation-bar semantics fix?

**Yes, if the validation bar changes the helper return type
or contract.** The 57C-1 design splits the
`validation_summary` into `governance_guard_summary` +
refined `validation_summary`. If the helper signature
changes, UI-3.2 should be done **after** 57C-1 to avoid
re-work.

If 57C-1 only **adds** a new `governance_guard_summary`
key without changing the existing `validation_summary`
contract, UI-3.2 can proceed in parallel.

**Recommendation: do UI-3.2 after 57C-1 is merged.** This
is the lower-risk path.

## Hard no-go / scope for 57F

- No financial model changes.
- No `app/waterfall_core.py` changes.
- No `app/project_factories.py` changes.
- No `app/persistence/` changes.
- No `app/services/` changes.
- No `main_web.py` changes.
- No `static/app.js` changes.
- No `static/styles.css` changes.
- No schema / migration changes.
- No fixture CSV changes.
- No frontend dependency changes.
- No Tailwind / Alpine / React / Vue / Svelte.
- No G20/R99/R102 guard promotion.
- No generic Solar/Wind runtime work.
- No BESS / Hybrid / Portfolio work.
- No forbidden user-facing claims.
- rc1 frozen.

## Auto-merge policy

57F is `docs/report/test-only`. It is auto-merge eligible
if all hard gates pass. The proposed UI-3.2 runtime
migration is **not** part of 57F; it is deferred to a
future PR (57F-1) that the user must approve.
