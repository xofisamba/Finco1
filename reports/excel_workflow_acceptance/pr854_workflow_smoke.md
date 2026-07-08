# PR 854 Excel Workflow Acceptance Lock

## Scope

This report locks the current Excel-style workflow introduced by PRs #850-#853.

Covered surfaces:

- Inputs
- CAPEX
- OPEX
- Revenue
- Scenarios
- Run
- Post-Run return to Inputs/CAPEX/OPEX
- Protected reference project
- User-created project

No product UI, engine, math, schema, persistence, parity target, Revenue,
Scenario, Financial Statements, or Senior Debt behavior was changed.

## Evidence Summary

Automated acceptance coverage:

- `tests/test_excel_workflow_smoke.py`
- Protected TUHO workspace renders Inputs, Revenue, Scenarios, CAPEX, OPEX, and Run entrypoint.
- Protected TUHO CAPEX/OPEX grids render with `.cx-*` and `.ox-*` grid namespaces.
- Protected TUHO CAPEX/OPEX grid fallbacks do not appear during normal navigation.
- Protected TUHO CAPEX/OPEX editable grid inputs are absent.
- Protected TUHO read-only notice is visible.
- Protected TUHO Run smoke returns without HTTP 500, then workspace re-render still shows CAPEX/OPEX grids.
- User-created Generic Wind project is created through `/projects/create`.
- User-created project renders editable CAPEX and OPEX grid inputs.
- User-created project does not show the protected reference notice.
- Workspace shell includes the current `sheet_capex_grid.html` and `sheet_opex_grid.html` partials.
- Inputs control tower uses `capex_vm` and `opex_vm`.

## Screenshot Checklist

Binary screenshot artifacts are not committed. Local Playwright/Chromium is an
optional dependency in this repo and is not installed in this environment. The
route/render acceptance test above is the committed lock; the checklist below is
the browser evidence list for reviewer/manual validation.

Expected screenshot directory when browser evidence is captured:

`reports/excel_workflow_acceptance/screenshots/pr854/`

Checklist:

| # | View | Expected evidence |
|---|------|-------------------|
| 1 | Inputs control tower top | Inputs page renders, lifecycle/header visible, no white screen |
| 2 | Inputs CAPEX/OPEX summaries | CAPEX Summary and OPEX Summary use view-model-backed rows |
| 3 | CAPEX top | `.cx-grid-wrapper`, Code/Line Item sticky columns, protected notice for TUHO |
| 4 | CAPEX bottom | Total CAPEX / Hard CAPEX rows visible, no fallback copy |
| 5 | OPEX top | `.ox-grid-wrapper`, Code/Line Item sticky columns, protected notice for TUHO |
| 6 | OPEX year columns scrolled | Y1-Y30 horizontal grid available, Y30 reachable by horizontal scroll |
| 7 | OPEX bottom | Total OPEX rows visible, no fallback copy |
| 8 | User-created editable CAPEX | Editable `.cx-input` controls visible where allowed |
| 9 | User-created editable OPEX | Editable `.ox-input` Y1 controls visible where allowed |
| 10 | Post-Run return to CAPEX/OPEX | After Run, returning to CAPEX/OPEX still renders grids without fallback |

## Protected Reference Project

Project checked by automated route smoke: `tuho`.

Acceptance:

- Inputs loads.
- CAPEX loads with `.cx-*` grid.
- OPEX loads with `.ox-*` grid.
- No editable CAPEX/OPEX line-item grid inputs are visible.
- Protected read-only notice is visible.
- CAPEX sticky Code/Line Item column classes are present.
- OPEX sticky Code/Line Item column classes are present.
- OPEX Y1-Y30 columns are present in markup.
- Run returns without HTTP 500.
- Post-Run workspace return still renders Inputs/CAPEX/OPEX grids.
- No `capex_vm unavailable` or `opex_vm unavailable` fallback appears in normal navigation.

## User-Created Project

Project checked by automated route smoke: a Generic Wind project created through
`/projects/create` in the test session.

Acceptance:

- Inputs loads.
- CAPEX editable inputs are visible where allowed.
- OPEX editable Y1 inputs are visible where allowed.
- Protected notice is not shown.
- CAPEX/OPEX totals are visible.
- No white screen or grid fallback appears.

## Stop Condition Review

Revenue, Scenarios, Financial Statements, and Senior Debt were not expanded in
this PR. The acceptance test only verifies that their current workflow entry
points render in the workbook shell. Follow-up redesign or feature work remains
out of scope.

## Result

Status: acceptance lock added.

Runtime/model impact: none.

Persistence/schema impact: none.

Math/parity impact: none.
