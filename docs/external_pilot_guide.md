# External Pilot Guide

Welcome to the Finco modelling platform external pilot. This guide walks
through the core workflow end to end: creating a project, editing inputs,
running the model, checking validation status, working with scenarios,
exporting results, and understanding the platform's known limitations.

This guide is written for an external pilot user evaluating the platform.
It assumes no prior familiarity with the codebase or internal terminology.

> **Disclaimer:** Outputs are financial modelling estimates and not legal, tax, accounting or investment advice.

---

## 1. Create a Project

1. From the project browser (`/projects/browse`), choose **New Project**.
2. Select a project type (Solar, Wind, BESS, Solar + BESS, Wind + BESS, or
   Portfolio) and, optionally, a starting template to prefill inputs.
3. Enter a project name, country/market, and capacity. These can be edited
   later.
4. Submit to create the project. You will land on the project's workspace.

Two example projects — **TUHO Wind** and **Oborovo Solar PV** — are
included as protected reference projects. They are read-only: you can
open and explore them, but the first edit you make automatically creates
your own editable copy, leaving the original reference untouched. This
lets you safely experiment with a known-good starting point.

Projects you create yourself are fully editable from the start.

## 2. Edit Inputs

1. Open a project to land on its workspace, which is organised into a
   small number of input/result areas (e.g. Inputs, Results, Scenarios,
   Export).
2. The **Inputs** area groups fields by category: CAPEX, OPEX, Revenue,
   Senior Debt, Tax, and similar sections depending on project type.
3. Edits are kept as an unsaved **draft** until you explicitly save or
   run. A draft indicator shows when you have unsaved changes.
4. Use **Save** to persist a named version of your inputs (see Section 5,
   Create a Scenario) without necessarily re-running the model.

Editing inputs never changes the underlying calculation engine — you are
only changing the assumptions fed into it.

## 3. Run the Model

1. From the workspace, choose **Run**.
2. The run uses your current saved/draft inputs and produces a runtime
   summary: revenue, OPEX, EBITDA, senior debt, DSCR, Project IRR, and
   Equity IRR, among other figures.
3. Run output reflects the last completed run, not necessarily your latest
   unsaved draft. If you have made changes since the last run, a "stale
   runtime" warning appears reminding you to re-run before relying on
   exports or comparisons.
4. Results are organised into tabs/panels (e.g. summary, P&L, cash flow,
   debt schedule) so you can drill into the figures behind the headline
   numbers.

## 4. Validation Status

Every project displays a validation status badge so you know how much
weight to put on its numbers:

| Status | Meaning |
|---|---|
| **Validated reference project** | TUHO and Oborovo. Inputs and results are held fixed and used as a known-good anchor for testing the model. |
| **Validated model with caveats** | Generic Solar and Generic Wind. Core cost and revenue figures (CAPEX, Revenue, OPEX, EBITDA, IDC, fees, senior debt amount, gearing) are validated against internal reference workbooks. Debt-service shape, DSCR, and IRR figures carry a documented methodology caveat — see Section 8, Known Limitations. |
| **Design-only, not externally validated** | BESS, Solar+BESS, Wind+BESS. Calculations run, but the configuration has not been validated against a reference workbook. |
| **Experimental, internal only** | Portfolio. Not validated and not intended for external use. |

The validation badge and its detail panel are visible on the project
browser and within each project's workspace.

> **Note on Generic Solar / Wind outputs:** Generic Solar and Generic Wind
> defaults were recalibrated during the validation program to align core
> cost and revenue figures with internal reference workbooks. If you saved
> a Generic Solar or Generic Wind project before this recalibration, its
> runtime outputs may differ from a project created from today's defaults.
> This reflects validation improvements and does not indicate model instability.

## 5. Create a Scenario

1. From the Scenarios area of a project workspace, choose **Save as
   Scenario** (or **Save**, depending on context) to create a new named
   snapshot of your current inputs.
2. Each scenario can be labelled as **Base**, **Downside**, **Upside**, or
   a **Custom** name, so you can keep a clear story across variants of the
   same project.
3. Saved scenarios are immutable snapshots — saving again creates a new
   version rather than overwriting the previous one. Your full version
   history remains available from the Scenarios area.
4. Each scenario shows a quick summary (key metrics) so you can identify
   it without opening it fully.

## 6. Compare Scenarios

1. From the Scenarios area, choose **Compare** to compare two scenarios in
   detail, or **Compare Multi** to compare 2-4 scenarios side by side.
2. Compare views show each scenario's headline metrics (Revenue, EBITDA,
   Senior Debt, Avg DSCR, Min DSCR, Project IRR, Equity IRR) and the delta
   versus the first ("Base") scenario in the list.
3. Comparison is descriptive only: it compares saved scenario snapshots
   and saved runtime summaries, not unsaved draft values. Save and re-run
   each scenario you want to include before comparing.
4. For projects without full Excel-parity validation, comparison views
   carry an exploratory notice reminding you the numbers are illustrative
   and not for external decision-making.

## 7. Export Results

1. From the Export area, choose the export you need (e.g. institutional
   workbook, CSV runtime summary).
2. The institutional workbook export includes a cover page, a validation
   summary describing the project's validation tier, and the standard
   financial sheets (Inputs, CAPEX, OPEX, Revenue, Senior Debt, Tax, P&L,
   Cash Flow, Balance Sheet).
3. Exports reflect the last completed run, not unsaved draft edits — run
   the model again first if you have made changes you want reflected in
   the export.
4. Exported values are static numbers, not live formulas; re-running the
   export after further edits produces a fresh snapshot.

## 8. Known Limitations

The platform has a dedicated **Known Limitations** page, reachable from
the Help menu and the page footer, that documents what is validated, what
carries a methodology caveat, what is not yet validated, and what is not
yet supported. Review it before relying on any project's numbers for an
external decision. In short:

- **Validated models:** Generic Solar and Generic Wind (with documented
  caveats on debt-service shape, DSCR, and IRR — see the page for detail).
- **Methodology caveats:** the debt-sizing proxy used by the runtime model
  differs structurally from the reference workbook's own proxy; Project
  IRR is calculated on an unlevered basis; scenario comparisons are
  descriptive, not Excel-parity validated for most project types; DSCR
  figures move directionally as expected under sensitivity but inherit
  the same debt-sizing caveat; one small, documented sensitivity-testing
  exception exists for Generic Solar's Equity IRR direction under a
  revenue increase.
- **Not yet validated:** BESS, Hybrid (Solar+BESS, Wind+BESS), and
  Portfolio configurations.
- **Not yet supported:** multi-lender debt structures, advanced tax
  structures beyond loss carryforward, the R99/R102 promoted workflow
  (these audit fields are visible for traceability only and are not
  approved for runtime cash-routing or distribution decisions), and
  advanced debt-sculpting/cash-sweep methods (not yet promoted for
  standard project runs).

> **Disclaimer:** Outputs are financial modelling estimates and not legal, tax, accounting or investment advice.
