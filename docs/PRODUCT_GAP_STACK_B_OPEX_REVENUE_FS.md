# Product Reality Gap Stack B: OPEX + Revenue + Financial Statements

**Branch:** `product-gap-stack-b-opex-revenue-fs`
**Base SHA:** `465f68e98cdceaece46469c408e45a1c5b54d561`

---

## Summary

This sprint audited three areas for UX and presentation polish. After thorough
investigation of the prior-sprint outputs (PR2/PR3/PR4 for OPEX, PR5 for Revenue,
PR6 for Financial Statements, and the Product Acceptance Stack A audit PR13–PR17),
the conclusion is:

**All three areas were already brought to the required standard by prior sprints.**
No template, JS, or CSS changes were needed. This sprint's sole deliverables are:
- Comprehensive characterization tests (`tests/test_product_gap_stack_b_opex_revenue_fs.py`)
- This documentation file

---

## 1. OPEX — Excel-feel editing

### What was found

Prior sprint PR2/PR3/PR4 fully delivered OPEX Excel-feel editing:

- **Editable cells**: `sheet_opex_detail.html` uses `class="fc-input-native"` for
  editable OPEX Budget cells — identical to CAPEX's gold-standard pattern. No
  `name=` attribute on these inputs (preview-only, no persistence path yet, by
  deliberate design documented in C2-PR17).
- **Live totals JS**: `static/modelling/opex-sheet-live-totals.js` exists and is
  wired in `app/templates/base.html` (line 74: `<script src="..." defer>`).
- **Data attributes**: `data-opex-row="cat-subtotal-*"`, `data-opex-cat="*"`,
  `data-opex-row="operating-subtotal"`, and `data-opex-row="grand-total"` are all
  present in the template, enabling the live-total module to update Y1 figures on
  every keystroke.
- **Row structure**: Operating Subtotal (Y1) and Total OPEX (Y1) rows were added
  by PR3, rendered server-side first (correct before JS loads) and kept live by
  the JS module.
- **Governance note**: The C2-PR18 note (`#opex-preview-only-note`) was lightly
  extended by PR4 to mention "update the totals on this sheet", keeping the three
  required phrases intact. No internal jargon.
- **Banner, summary strip, toolbar, collapse/expand**: all present and styled
  consistently.

### What was changed

Nothing. Investigation confirmed full parity with CAPEX gold standard.

### What was already correct

Everything. PR2/PR3/PR4 completed this work. The Product Acceptance Sprint
Stack A (PR13) also audited OPEX vs CAPEX and found no inconsistency.

---

## 2. Revenue — Safe editable inputs + layout alignment

### What was found

Prior sprint PR5 delivered all required Revenue changes:

- **Code column**: completely absent from `sheet_revenue.html` — removed at
  template level (not CSS-hidden). Section-band colspan is 5, not 6. Both
  `fc-th--code` and `fc-cell--code` are absent from the template.
- **Editable cell**: `ppa_base_tariff` is the only editable Revenue item. It uses
  `class="fc-input-native"` and `name="rev_{{ item.code }}"` (real persistence
  path via `_collect_form_snapshot()` in `main_web.py`, predating PR5).
- **Read-only cells**: all use `<span class="fc-cell-runtime">` convention,
  consistent with CAPEX/OPEX.
- **Data attributes**: `data-fc-cell`, `data-fc-addr`, `data-fc-kind`, `data-fc-editable`,
  `data-fc-raw` all present on every item cell.
- **Layout**: 5-column grid (Line Item / Value / Unit / Group / Hint), four section
  bands, subtotal and grand-total rows, footer note with tariff summary. Structurally
  consistent with CAPEX/OPEX.
- **Copy**: no internal jargon. "Informational — backend computes actual" and "kEUR —
  runtime model is authoritative" on summary rows are honest and clear.
- **Empty states**: readonly notice for non-user projects uses standard pattern.
  No pre-Run empty state was needed (Revenue renders based on project context, not
  Run output).

### What was changed

Nothing. PR5 completed this work. The Product Acceptance Stack A audit confirmed
no inconsistency.

### No live-totals module added

Deliberately not added. Revenue's "Est. Total Y1 Revenue" and "Y1 PPA Revenue"
rows require a non-linear multiplication across four factors, of which only one
(`ppa_base_tariff`) is editable. Recomputing these client-side would duplicate the
backend formula in JavaScript — explicitly forbidden by the guardrails. The same
"if it cannot be honestly recomputed client-side, leave it frozen" rule applied by
CAPEX PR1 for C.17/C.18 and OPEX PR3 for Y2+ year columns applies here across the
entire summary section.

---

## 3. Financial Statements — Real Run output + standardised unavailable state

### What was found

Prior sprint PR6 fully delivered the Financial Statements honesty pass:

- **`fs-unavailable-panel`**: present in `sheet_financials.html` using the
  standard `empty-state-notice empty-state-notice--warn` CSS classes (the same
  pattern as PR7/PR8/PR9 for Distribution/Sponsor, Senior Debt, Tax). Copy is
  plain, user-facing, and honest: explains that statements are not yet backed by
  Run output and where to continue modelling.
- **Static tables removed**: `fs-pnl-grid`, `fs-cf-grid`, `fs-bs-grid` are all
  absent. The "Static TUHO reference values" / "TUHO factory snapshot" footnote
  is absent. No banned jargon.
- **Runtime KPI block preserved**: `fs-runtime-block` and `_populateFSRuntimeBlock`
  script are intact. The block reads `sessionStorage.getItem("lastRuntimeSummary")`
  (written after a real `POST /run`) and populates IRR, DSCR, revenue, EBITDA,
  OPEX, distributions, and SHL opening KPI cards. This is the only genuinely
  Run-backed content on the sheet, and it was correctly kept.
- **Consistency with newer panels**: The `fs-unavailable-panel` was audited
  against the PR7/PR8/PR9 unavailable panels (Distribution, Senior Debt, Tax).
  All use `empty-state-notice--warn`. No inconsistency found.
- **All cards reviewed**: The sheet has the banner, runtime block (shown only
  after Run), section divider, and unavailable-state panel. No misleading
  placeholder, technical, or fabricated copy remains.

### What was changed

Nothing. PR6 completed this work. The Product Acceptance Stack A audit (PR14/PR15)
confirmed no inconsistency.

---

## Why no financial calculations were added

No client-side financial calculations, formula recomputation, live-totals modules,
or new KPI bindings were added for any of the three areas. The guardrail is
explicit: do not invent new financial logic, do not duplicate the backend's formulas
in JavaScript, do not show numbers that cannot be honestly derived from currently
available data.

For OPEX, the Y1 live totals are honest sums of editable Budget cells (pure
addition, no formula). Y2+ totals are left frozen because they require the backend's
inflation/active-flag formula.

For Revenue and Financial Statements, no live total can be honestly computed
client-side without reproducing non-trivial multi-factor backend formulas — so
none were added.

---

## Files changed in this sprint

| File | Change |
|---|---|
| `tests/test_product_gap_stack_b_opex_revenue_fs.py` | New — 42 characterization tests |
| `docs/PRODUCT_GAP_STACK_B_OPEX_REVENUE_FS.md` | New — this file |

No templates, JS, CSS, backend files, or any other source file was modified.

---

## Test results

All 42 new tests pass. Full regression suite
(`tests/test_c1_*.py tests/test_c2_*.py tests/test_product_gap_*.py`) shows no
new failures beyond the 3 confirmed pre-existing baseline failures:

1. `test_c2_pr1_live_model.py::TestStaticWiring::test_no_recalculation_formula_dependency_or_saverun_code_in_live_model`
2. `test_c2_pr7_backend_preview_endpoint.py::...::test_no_financial_engine_call`
3. `test_c2_pr9_runtime_request_hardening.py::TestNoRegressionForAuthorizedOrNullProject::test_authorized_project_behaviour_matches_pr8_contract`

The 6-failure cluster in `tests/test_phase9_5_output_tabs_runtime_summary_binding.py`
is also pre-existing and not caused by this sprint.

---

## Future work

- **OPEX Y2+ live totals**: would require reproducing the backend's per-line
  inflation/active-flag schedule in JavaScript. Out of scope.
- **Revenue live-totals**: would require reproducing the PPA tariff formula
  (`ppa_tariff × hours × capacity × availability / 1000`) in JavaScript and
  keeping it in sync with backend changes. Out of scope.
- **Financial Statement tables**: need a real, Run-backed Income Statement / Cash
  Flow / Balance Sheet engine. The `fs-unavailable-panel` added by PR6 is the
  correct placeholder until that engine is built. Out of scope.
- **OPEX Budget persistence**: the OPEX Budget inputs deliberately carry no `name=`
  attribute (preview-only). Adding real persistence would require a new
  server-side endpoint and domain changes — out of scope.

---

## Guardrail confirmation

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
- All export, persistence, Run, and Save logic — untouched

No financial formulas, Run logic, Save logic, persistence logic, export logic,
Preview Architecture, or Runtime Pipeline code was changed. Changes in this sprint
are documentation and tests only.
