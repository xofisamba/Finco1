# PR #857 — Financial Statements and Debt Output Honesty: Review

**Branch:** `claude/festive-cerf-uaq5hb`
**Date:** 2026-07-10

---

## Audit Findings: What Each Surface Can and Cannot Show

### Financial Statements (`sheet_financials.html`)

| Statement | Pre-Run state | Post-Run state |
|-----------|--------------|----------------|
| Income Statement (P&L) | "Run the model" empty state — honest | Populated from `assemble_financial_statements()` via OOB Jinja re-render if active tab, plus sessionStorage fallback. Real engine output. |
| Balance Sheet | Same | Same — all three statements live in the same template instance |
| PF Cash Waterfall | Same | Same |

**No fake or placeholder values exist.** The TUHO factory snapshot figures documented in Sprint 12 were removed prior to this PR. The empty state panel (`#fs-unavailable-panel`) was already correctly set to visible-by-default.

**Bug identified and fixed (PR #857):** The same template (`sheet_financials.html`) was included three times in `workspace_shell.html` — once per outer FS tab panel (P&L, Cash Flow, Balance Sheet). All three instances rendered the same element IDs (`fs-pnl-header`, `fs-bs-header`, etc.), but `document.getElementById()` only resolves to the first DOM match. This meant:
- After a Run, only the P&L tab panel received data from the sessionStorage path.
- Cash Flow and Balance Sheet panels continued to show "No model results available" even after a successful run — **misleading presentation**.

**Fix applied:**
- Added `_fs_panel_id = _active_statement|default("pl")` variable, set by workspace_shell.html's existing `_active_statement` variable.
- All element IDs now include the panel suffix: `fs-pnl-header-pl`, `fs-unavailable-panel-cf`, `fs-statements-block-bs`, etc.
- Outer container carries `data-fs-panel="{{ _fs_panel_id }}"`.
- JS IIFE captures `document.currentScript` at execution time and scopes all DOM queries to the panel container via `_container.querySelector('#' + id)` — eliminating cross-panel getElementById interference.

### Senior Debt / Debt Schedule (`sheet_senior_debt.html`)

| Section | Pre-Run state | Post-Run state |
|---------|--------------|----------------|
| Senior Debt banner | Hardcoded "Protected" badge — **misleading for user projects** | Fixed |
| Debt Assumptions grid | Shows live `project_ctx` saved inputs — correct | Same |
| Editable draft grid | Showed editable inputs for ALL projects including protected — **misleading** | Fixed: guarded with `{% if is_user_project %}` |
| Runtime debt outputs label | Missing — no distinction between assumptions and outputs | Fixed |
| Debt schedule table | Empty (correct) — populated from `WaterfallResult.periods` via sessionStorage | Real engine output |
| Unavailable panel | Started `display:none` — **inverted** (flash of invisible, JS then reveals) | Fixed: starts visible, JS hides after run |

**No fake amortization values exist.** The schedule table body is populated entirely by JS from `sessionStorage["lastDebtSchedule"]` (real `WaterfallResult.periods` engine output). No financial calculations in the template.

---

## Changes Made

### `sheet_financials.html`
- Added `_fs_panel_id` Jinja variable (from `_active_statement`)
- Wrapped content in `<div data-fs-panel="{{ _fs_panel_id }}">`
- Suffixed all element IDs with `-{{ _fs_panel_id }}`
- JS IIFE: captures `document.currentScript` → `_container` → scoped `_q(id)` helper
- `_panelId` JS variable reads `_container.dataset.fsPanel`
- All `getElementById` calls replaced with `_q("...-" + _panelId)`

### `sheet_senior_debt.html`
- Replaced hardcoded `<span class="badge badge-preview">Protected</span>` banner with a truthful `sc-section-banner` that shows "Protected original" for protected projects and "Editing" for user projects
- Editable draft grid (`editable-grid-shell`) wrapped in `{% if is_user_project %}` — protected projects see read-only assumption grid only
- Added "Debt Assumptions" section banner (inputs section)
- Added "Runtime Debt Outputs" section banner with "Draft schedule — not yet a full lender debt model" notice
- Fixed `#sd-unavailable-panel` display: removed `style="display:none;"` — panel now starts visible (consistent with `sheet_financials.html` pattern)

---

## What Was NOT Changed

| Area | Status |
|------|--------|
| Financial Statements engine (`app/api/`) | Unchanged |
| `assemble_financial_statements()` | Unchanged |
| Debt engine / waterfall | Unchanged |
| `WaterfallResult` schema | Unchanged |
| Debt sizing inputs persistence | Unchanged |
| CAPEX / OPEX / Revenue / Scenarios | Unchanged |
| `main_web.py` routes | Unchanged |
| `_RUNTIME_SHEET_MAP` | Unchanged (senior-debt OOB re-render gap documented below) |
| Session storage write path | Unchanged |

---

## Known Gaps / Follow-up Recommendations

### 1. Senior Debt has no OOB Jinja re-render path
`_RUNTIME_SHEET_MAP` in `main_web.py` includes `"pl"`, `"cashflow"`, `"balance"` but NOT `"senior-debt"`. The debt schedule always depends on the sessionStorage JS path post-run. This is functional but means:
- Refreshing the page after a run clears sessionStorage → debt schedule disappears
- Fix: add `"senior-debt": "partials/sheet_senior_debt.html"` to `_RUNTIME_SHEET_MAP` and pass `debt_schedule` context in the OOB render. **Requires engine work (serialising `WaterfallResult` as context).**

### 2. FS panels show all three statements in each outer tab
The current architecture includes all three statement tables in each outer tab panel. The inner statement selector (in `_statements_workspace_selector.html`) provides client-side switching between P&L, CF, and BS within each outer panel. The PR #857 fix ensures each panel correctly populates from sessionStorage independently. A future simplification could deduplicate the three outer panels into a single `sheet_financials.html` include with client-side tab switching.

### 3. No prior-run data on initial page load
`financial_statements` is not passed in the initial `GET /` render, even if the project has prior run results persisted. All three FS panels always render the empty state on first load. **Requires persistence work to store and reload the last FS result.**

### 4. Real Senior Debt input workflow not yet built
The editable draft grid (gearing, DSCR, rate, tenor) is a lightweight workspace-draft-only surface. A full Senior Debt input workflow would support:
- Per-tranche debt structures
- Variable rate structures
- Commitment fee / structuring fee inputs
- Lender-facing sensitivity outputs
This is out of scope for PR #857 and should be a separate workstream.

---

## Test Results

```
tests/test_financial_statements_output_honesty.py   34 passed
tests/test_debt_schedule_output_honesty.py          21 passed
tests/test_inputs_control_tower.py                  39 passed
tests/test_sheet_opex_grid.py                       44 passed
tests/test_scenarios_excel_matrix.py                30 passed
```

Total: 168 tests, all passing.

---

## Browser Evidence

Browser screenshots were not taken for this PR because the core changes (element ID scoping, panel display fixes, section labelling) are verifiable via Jinja2 template rendering and DOM inspection — no new visual design was introduced. The PR adds labels and fixes display logic rather than introducing new UI components.

The acceptance checklist was verified via the Jinja2 test suite (55 tests) which directly asserts DOM structure, element IDs, panel visibility state, and label presence.

---

## Verdict

All truthful presentation goals achieved. No engine/math/schema/persistence changes made.
PR #857 is ready for review.
