# Product Acceptance Sprint — Stack A: PR13–PR17

## Summary

Branch: `product-acceptance-stack-a`  
Base: `main` @ `fd2c003943e6559c3abd79f7487f52f6257b1040`

This sprint prepared Finco1 for external pilot use by improving
consistency, discoverability, and usability across five audits
(PR13–PR17). No financial logic, Run logic, formulas, persistence,
or Preview Architecture was touched. Changes are template/markup-only
plus one new test file and this documentation file.

---

## PR13 — Input Consistency Audit

### What was audited

All input sheets: CAPEX (`sheet_capex.html`), OPEX (`sheet_opex_detail.html`),
Revenue (`sheet_revenue.html`), Senior Debt (`sheet_senior_debt.html`),
Tax (`sheet_tax.html`), SHL (`sheet_shl.html`), Inputs (`sheet_inputs.html`).

Checked:
- Editable cell class: `fc-input-native` (CAPEX/OPEX/Revenue) vs `editable-grid-input` (Senior Debt)
- Read-only cell pattern: `data-fc-editable="false"` + `<span class="fc-cell-runtime">`
- Number formatting: `{:,.2f}` (thousands separator, 2dp) for totals; `{:.2f}` for raw amounts
- HTMX/FC data attributes: `data-fc-cell`, `data-fc-addr`, `data-fc-kind`, `data-fc-editable`, `data-fc-raw`
- Sheet banners: all sheets use `sheet-banner` + `sheet-banner-tag` + `sheet-banner-badge`

### What was found

Already consistent across all sheets except one intentional difference:
- CAPEX, OPEX, Revenue: use `fc-input-native` for `<input>` elements (the gold-standard pattern from PR1/PR2/PR5).
- Senior Debt: uses `editable-grid-input` for its 4 draft inputs. This is an intentional structural difference — Senior Debt's inputs are in a "Debt Facility" table with a different layout from the spreadsheet-style fc-grid used by CAPEX/OPEX/Revenue. This is not an inconsistency; it is the correct pattern for that grid type, established in the Senior Debt C1 migration.
- All sheets use `data-fc-editable` / `data-fc-raw` / `data-fc-kind` consistently.
- All sheets have `sheet-banner` with consistent badge pattern.

### What was changed

Nothing. Investigation found no visual inconsistencies requiring a fix.

---

## PR14 — Labels & Terminology

### What was audited

All user-visible templates in `app/templates/` for:
- CAPEX / OPEX / Revenue / Run / Scenario / Compare / Export case variants
- Banned internal jargon: `Preview Architecture`, `Runtime Pipeline`, `stub`, `prototype`, `TODO`, `FIXME` (outside of Jinja `{# #}` comments which are stripped at render time)
- Consistency of the action button labels: "Run" vs "Run Model" in button elements

### What was found

Already consistent:
- The primary action button (`btn-run-model-sidebar`) is labeled "Run" — concise, consistent.
- Instructional copy (CTAs, banners, empty states) uses "Run the model" — also consistent and acceptable.
- Validation page uses "Run Model" as a call-to-action label in body text — acceptable variation in instructional context.
- `G20`/`R99`/`R102` appear only inside `{% if audit_mode %}` blocks (not user-visible in normal use) — same accepted pattern from PR9/PR10/PR12.
- No `Preview Architecture`, `Runtime Pipeline`, or `stub` found in rendered user copy.
- `CAPEX`, `OPEX`, `SHL`, `Revenue` use consistent all-caps form throughout user-visible text.

### What was changed

Nothing. Investigation found no clear user-visible terminology inconsistencies requiring a fix.

---

## PR15 — Empty States

### What was audited

Every screen/sheet for empty/unavailable states. Focus: consistent use of the `empty-state-notice` / `empty-state-notice--warn` CSS pattern established in PR6 (Financial Statements), PR7 (Distribution/Sponsor), PR8 (Senior Debt), PR9 (Tax).

### What was found

**SHL sheet (`sheet_shl.html`)** — INCONSISTENCY FOUND:

The "Output Preview" section used the OLD `preview-notice` CSS pattern with the copy:
> `Preview schedule — static reference values, not live calculated output. Run the model to see actual SHL output above.`

This was the same pre-PR8/PR9 pattern that was cleaned up on Senior Debt and Tax in those sprints. SHL was missed. The copy also said "static reference values" — misleading because there are no static values shown, just a notice.

All other sheets (Senior Debt, Tax, Financial Statements, Distribution, Sponsor) already used the `empty-state-notice--warn` pattern correctly.

### What was changed

**`app/templates/partials/sheet_shl.html`**:
- Removed: the `<div class="preview-notice">` block with "Preview schedule — static reference values" copy.
- Changed: section header from "Output Preview" to "SHL Schedule Output" (consistent with "Debt Schedule Output" on Senior Debt, "Tax Output" on Tax).
- Added: `<div class="empty-state-notice empty-state-notice--warn shl-unavailable-panel">` panel (same pattern as PR8/PR9), with copy:
  > "SHL schedule output is not available yet. Run-backed SHL repayment, interest, and distribution results will be shown here once this section is connected to the model engine."

No CSS invented. No Jinja variable binding changed. No financial data. The SHL Facility Summary card above (showing real `project_ctx` fields) is unchanged.

---

## PR16 — Loading & Feedback

### What was audited

All HTMX interactions in `app/templates/base.html` and key partials for:
- `hx-indicator` on key action buttons
- `hx-disabled-elt` (prevents double-click during request)
- Loading spinner elements with `htmx-indicator` class

### What was found

**Run button** — already had `hx-indicator="#run-spinner"` and `<span id="run-spinner" class="htmx-indicator run-spinner">` (correct).

**Save button** (`btn-save`) — MISSING `hx-indicator` and `hx-disabled-elt`. During a Save request, the button showed no visual feedback and could be clicked multiple times.

### What was changed

**`app/templates/base.html`**:
- Added `hx-indicator="#save-spinner"` to the Save button.
- Added `hx-disabled-elt="this"` to the Save button (disables it during the request, preventing double-click).
- Added `<span id="save-spinner" class="htmx-indicator save-spinner">…</span>` inside the button (same pattern as run-spinner).

No routing, request methods, or HTMX response handling was changed. The `hx-post`, `hx-include`, `hx-target`, and `hx-swap` attributes are unchanged.

---

## PR17 — Documentation Cleanup

### What was audited

All user-visible help text, tooltips (`title=""` attributes), hint text, and footnotes in templates. Checked for: outdated references, overly technical wording, internal jargon.

### What was found

**SHL "Output Preview" section** — the "Preview schedule — static reference values, not live calculated output" copy was both outdated (the PR8/PR9 sprint had already standardized better wording) and slightly misleading (there is no schedule at all, not a preview of one). Fixed as part of PR15 above.

**All other sheets** — copy is already concise and plain. Notable positives:
- CAPEX driving copy: "CAPEX line items drive the model-level CAPEX total." — clear.
- OPEX preview-only note: "OPEX line edits are preview-only for now: they update the totals on this sheet and the live preview right away, but are not saved yet. Run uses the saved model inputs." — accurate and plain.
- Revenue summary: "Informational — backend computes actual" — honest.
- Tax read-only note: "Tax country template assumptions. Read-only on this sheet — not yet editable via a saved input." — accurate.
- Senior Debt draft inputs have inline "Runtime remains blocked while edits are unsaved." — honest.

### What was changed

Nothing additional beyond the SHL fix in PR15. Investigation found no other outdated or problematic documentation in user-facing copy.

---

## Files Changed

| File | Change | PR |
|---|---|---|
| `app/templates/partials/sheet_shl.html` | Replace old `preview-notice` with `empty-state-notice--warn` panel; rename section header to "SHL Schedule Output" | PR15/PR17 |
| `app/templates/base.html` | Add `hx-indicator`, `hx-disabled-elt`, and save-spinner to Save button | PR16 |
| `tests/test_product_acceptance_stack_a_pr13_pr17.py` | New: characterization tests for all 5 sub-items | All |
| `docs/PRODUCT_ACCEPTANCE_STACK_A_PR13_PR17.md` | This file | All |

## Guardrail Confirmation

The following files were NOT touched:
- `domain/*` — untouched
- `app/waterfall_core.py` — untouched
- `app/input_adapter.py` — untouched
- `app/project_factories.py` — untouched
- `static/modelling/runtime-renderer.js` — untouched
- `app/services/model_preview.py` — untouched
- `app/services/preview_context.py` — untouched
- `app/services/previews/*` — untouched
- `main_web.py` — untouched

## Pre-existing Baseline Failures

The following pre-existing failures are not caused by this sprint:
- `test_c2_pr1_live_model.py::TestStaticWiring::test_no_recalculation_formula_dependency_or_saverun_code_in_live_model`
- `test_c2_pr7_backend_preview_endpoint.py::...::test_no_financial_engine_call`
- `test_c2_pr9_runtime_request_hardening.py::TestNoRegressionForAuthorizedOrNullProject::test_authorized_project_behaviour_matches_pr8_contract`
- 6-failure cluster in `tests/test_phase9_5_output_tabs_runtime_summary_binding.py`

## Judgment calls

- **PR13 Senior Debt `editable-grid-input`**: Not changed. The Senior Debt sheet intentionally uses a different grid layout (an assumption/draft table, not a spreadsheet fc-grid). Forcing `fc-input-native` there would break the visual design without improving consistency from the user's perspective.
- **PR14 "Run Model" in instructional text**: Not changed. "Run the model" as instructional CTA copy is clear and user-friendly. Only button labels were checked for consistency (all say "Run").
- **PR17 CAPEX Sheet Guide verbosity**: Not changed. The Sheet Guide is inside a `<details>` element (collapsed by default) so it does not clutter the primary working surface. The content is accurate and helpful for users who do open it.
