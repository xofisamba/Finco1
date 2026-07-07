# Sprint 13 Lender Readiness Report

## Executive conclusion

Sprint 13 materially improved institutional reporting consistency, lender-facing wording, export metadata clarity, and cross-project route coverage without changing model calculations or runtime financial logic.

Overall institutional readiness: **88 / 100**

Pilot readiness: **High for guided pilot review; not yet suitable for unguided lender reliance.**

Commercial readiness: **Strong for investment-committee demonstration and controlled lender walkthroughs; final browser evidence and export artifact review are still required before v1.0 pilot freeze.**

Estimated days remaining until v1.0 pilot freeze: **5-7 working days**, assuming Playwright/Chromium screenshot capture is enabled and no new route-level regressions appear.

## Sprint 13 PR stack

| PR | Area | Result |
| --- | --- | --- |
| #836 | Report and export wording hardening | Removed legacy lender-facing wording from export/report surfaces. |
| #837 | Canonical reporting KPI consistency | Centralized read-only report KPI sourcing from canonical runtime output. |
| #838 | Lender-facing UI wording | Replaced pilot/developer wording across visible lender-facing UI surfaces. |
| #839 | Export metadata wording | Renamed export-facing metadata labels from preview/placeholder wording to evidence/gap wording. |
| #840 | Institutional route matrix | Added TUHO, Oborovo, Generic Solar, and Generic Wind route matrix coverage. |

## Reporting consistency

Status: **Strong**

Canonical KPI sourcing is now consolidated for executive, IC, credit, lender, and reporting surfaces through a read-only helper. This reduces the risk that IRR, NPV, Revenue, EBITDA, Debt, Tax, Cash, Distributions, LLCR, or DSCR are assembled differently by report-specific code.

Remaining reporting gaps:

- Full generated PDF/DOCX visual review still requires an artifact capture pass.
- Some older calibration/audit packs still contain historical review terminology in archived evidence files; those were not part of active runtime UI.
- Distribution and sponsor-return derivation transparency remain deferred by prior metadata-readiness decisions.

## Institutional presentation

Status: **Improved**

Visible copy was moved away from "preview", "demo", "temporary", "internal", "TODO", and "placeholder" phrasing on the active reporting and lender-facing surfaces touched by Sprint 13. Disabled or unavailable areas now use controlled scope language such as "outside current reporting scope", "outside current runtime view", and "unavailable in current reporting package".

Remaining UI gaps:

- Full Playwright screenshot evidence is blocked locally because Playwright/Chromium is not installed.
- A wider visual pass should still inspect spacing, number alignment, subtotal styling, negative number treatment, and print layout in real browser screenshots.
- Some legacy CSS class names still include historical terms where they are structural selectors rather than visible copy; replacing those should be a later compatibility-managed cleanup.

## Runtime audit

Status: **Good**

Backend route matrix coverage now checks TUHO, Oborovo, Generic Solar, and Generic Wind across core reporting and export routes. The matrix verifies no HTTP 500, no blank responses, no blank visible HTML, and no selected developer wording.

Remaining runtime gaps:

- Browser-level console error capture is not complete until Playwright is available.
- The route matrix is not a substitute for a full create/save/run/reload/export workflow in a real browser.
- Generic Solar/Wind remain preliminary review models and are not promoted to Excel-parity status.

## Lender readiness

Status: **Guided-review ready**

The lender-facing language is now more consistent and conservative. The app avoids overstating runtime authority, export readiness, or lender reliance. Scope limitations are explicit and more professional.

Remaining lender-readiness gaps:

- External model audit is still required before lender reliance.
- G20 remains blocked where applicable.
- R99/R102 remain not approved where applicable.
- Generic Solar/Wind outputs remain non-parity-reviewed.

## Export audit

Status: **Improved**

Export-facing metadata now uses `runtime_or_evidence` and `remaining_evidence_gaps` instead of `runtime_or_preview` and `remaining_placeholders`. This better matches institutional review terminology.

Remaining export gaps:

- Generated XLSX/DOCX/PDF artifacts should be opened and visually inspected in the next environment with browser/document tooling available.
- Export dates, scenario names, project names, units, metadata, version labels, and engine version labels need final screenshot/workbook capture.
- Archived evidence reports may still contain historical wording and should remain archive-only unless deliberately refreshed.

## QA evidence

Test evidence captured in Sprint 13:

- PR A: `84 passed, 17 skipped` route/report/export wording set.
- PR B: `93 passed` canonical KPI service/report set; `53 passed, 16 skipped` route smoke.
- PR C: `223 passed, 17 skipped` lender wording + render legacy set; follow-up focused `82 passed, 16 skipped`.
- PR D: `89 passed` export metadata/reporting wording set.
- PR E: `36 passed, 1 skipped` institutional route matrix.

Playwright evidence:

- Status: **Blocked in this local environment**.
- Reason: Playwright/Chromium dependency is not installed.
- Guardrail: `tests/test_sprint13_institutional_route_matrix.py` documents the skip explicitly.

## Top 10 remaining improvements

1. Install Playwright/Chromium and run full screenshot workflow for TUHO, Oborovo, Generic Solar, and Generic Wind.
2. Capture screenshots for Executive Summary, Financial Statements, IC Pack, Credit Pack, Lender Case, and Export Registry.
3. Open generated XLSX/DOCX/PDF artifacts and verify title, date, scenario, project, units, metadata, and version fields.
4. Add browser-console error checks to the institutional route matrix.
5. Add post-run workflow capture for Income Statement, Balance Sheet, and PF Cash Waterfall.
6. Add a visual spacing/alignment pass for negative numbers, subtotals, totals, and table headers.
7. Add a report navigation test that follows visible report links instead of only direct routes.
8. Add generated-artifact text extraction checks for developer wording.
9. Refresh archive-only report copies only if they are still linked from active UI.
10. Run a final parity guardrail bundle after all Sprint 13 PRs are merged.

## GO / NO-GO

GO for: **controlled pilot demos, investment committee walkthroughs, and guided lender-readiness review.**

NO-GO for: **unguided lender reliance or v1.0 pilot freeze until browser screenshots and generated export artifacts are captured and reviewed.**

## Confirmations

- No `waterfall_core.py` changes in Sprint 13 reporting PRs.
- No financial equation changes.
- No tax engine changes.
- No debt engine changes.
- No CAPEX calculation changes.
- No OPEX calculation changes.
- No Revenue calculation changes.
- No Financial Statement engine changes.
- No persistence changes.
- No schema changes.
- No Excel calibration changes.
- No parity target changes.
- No project factory changes.
