# Phase 15 Numeric Workbook Validation

## Purpose

This branch strengthens trust in the institutional workbook export by proving that
representative reviewer-visible workbook values match backend runtime outputs.

The validation is intentionally narrow and honest:

- it validates selected stable workbook metrics
- it uses backend runtime outputs as the comparison source
- it does **not** make the workbook authoritative
- it does **not** change workbook calculations or runtime formulas

## Validation Approach

The current institutional workbook already exposes stable labels that are suitable
for label-based lookup. This branch validates those labels directly instead of
depending on brittle hard-coded cell coordinates.

Validated workbook metrics:

- `Project IRR`
- `Total revenue`
- `Runtime total OPEX`
- `Average DSCR`
- governance marker: `G20 remains BLOCKED` / `R99/R102 remain NOT APPROVED`

Backend runtime comparison sources:

- `build_runtime_summary_rows("tuho")`
- representative runtime fields from the institutional workbook export bundle

## Tolerance Strategy

Tolerance is intentionally strict for the current workbook because the validated
cells are already exported as numeric values rather than display-only rounded text.

Current tolerances:

- `Project IRR`: `1e-9`
- `Total revenue`: `1e-6`
- `Runtime total OPEX`: `1e-6`
- `Average DSCR`: `1e-9`

If future workbook formatting introduces visible rounding before storage, these
tolerances may need to widen slightly. That would still be a validation concern,
not a shift in runtime authority.

## Why These Metrics

These metrics were chosen because they are:

- reviewer-visible
- stable across the current institutional workbook structure
- traceable to backend runtime output
- representative across returns, revenue, operating cost, and debt coverage

They provide a strong trust check without pretending the entire workbook has full
cell-by-cell parity coverage.

## Missing / Unavailable Handling

This branch also checks that missing or unavailable workbook metadata remains
explicitly labeled, not silently treated as zero.

Representative required markers:

- `Scenario ID` may be `not_applicable`
- `Runtime snapshot ID` may be `unavailable`

Those markers are intentional metadata semantics and must not be converted into
zero-like numeric values.

## What Remains Unvalidated

This branch does **not** numerically validate every sheet or line item.

Examples of currently unvalidated or partially validated areas:

- full construction schedule detail
- detailed CAPEX spend curve sections
- full SHL sub-line expansion
- full tax bridge residual breakdown
- every period-level row in P&L, cash flow, and balance sheet

Those gaps are documented in the numeric validation gap register rather than
being silently ignored.

## Authority Boundaries Confirmed

- Runtime remains the source of financial truth.
- Workbook/export remains descriptive only.
- Workbook values are validated **against** backend runtime outputs, not made authoritative.
- Missing or unavailable values are not silently treated as zero.
- Provenance and reviewer cover notes remain descriptive only.
- No runtime/model formulas were changed.
- No workbook calculations were changed.
- No workbook formulas were changed.
- No export calculation logic was changed.
- No persistence behavior was changed.
- No replay engine behavior was added.
- `audit_economic_mode` remains audit/reconciliation-only.
- `runtime_economic_mode` remains the only explicit runtime staging path.
- `G20` remains `BLOCKED`.
- `R99/R102` remain `NOT APPROVED`.

## Outcome

This branch gives the guided pilot a stronger numeric trust check for the
institutional workbook while keeping workbook/export firmly in the descriptive,
reviewer-facing layer.
