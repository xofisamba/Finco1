# Excel Input Coverage Gap Analysis

## Purpose

This folder contains the sanitized v5.3 mapping contract for the Excel input coverage gap analysis. It is an evidence model for future Inputs and Scenarios work, not an implementation PR.

The artifacts answer three questions:

1. Which canonical fields already exist in the runtime registry and input adapter.
2. Which workbook-only concepts are visible in the extracted model evidence.
3. Which gaps must remain unresolved until product design or client review confirms an authoritative canonical field.

## Evidence Standard

The v5.3.1 standard is `PROGRAMMATIC_WORKBOOK_INSPECTION`.

Committed evidence records cell coordinates, semantic roles, value kinds, units, and mapping status. It does not store source workbook formulas, source workbook values, proprietary package names, or binary source files.

Coordinates are separated into explicit axes:

- `verified_label_cell_*`
- `verified_value_cell_*`
- `verified_editable_cell_*`
- `verified_formula_cell_*`
- `verified_counterparty_label_cell_*`
- `verified_formula_period_cell_*`

`verified_editable_cell_*` is intentionally separate from `verified_value_cell_*` so editable hardcodes, toggles, dates, and text inputs cannot be confused with formula outputs or labels.

## Trust Hierarchy

1. Authoritative runtime evidence: Registry, input adapter, ProjectInputs, engine, persistence, and runtime tests.
2. Authoritative workbook semantic evidence: curated v5.3 evidence axes verified against the original workbook.
3. Verified workbook storage metadata: coordinate-level storage kind derived by read-only workbook inspection.
4. Preliminary package inventory: row names, sheet names, row ordering, domain hints, candidate identifiers, and preliminary cell lists.

Level 4 is inventory/search evidence only. It must not independently establish editability, formula status, canonical mapping, scenario eligibility, runtime binding, or implementation eligibility.

The preliminary mapping package is authoritative for row inventory only. Its `hardcode_cells`, `formula_cells`, `active_formula_kind`, candidate-input and scenario metadata are not implementation contracts unless revalidated against actual workbook storage or represented in the curated v5.3 evidence axes.

## Key Artifacts

- `canonical_field_catalog_v5.csv`
- `canonical_registry_crosswalk_v5.csv`
- `input_coverage_matrix_v5.csv`
- `unresolved_pack_id_evidence.csv`
- `canonical_to_pack_id_evidence.csv`
- `editable_input_disposition_v5_1.csv`
- `coverage_summary_v5.json`
- `validation_report_v5.json`
- `support_package_metadata_audit_v5_3_1.json`

## v5.3.1 Support Metadata Audit

The row inventory is structurally complete: 706 Input rows and 550 Scenario rows are present with zero missing or extra rows.

Structural completeness does not equal semantic correctness. Direct workbook inspection found preliminary package metadata noise:

- 330 preliminary hardcode-cell claims are formula-backed in the workbook.
- 14 depreciation candidate-input formula-backed cells are no longer verified hardcode evidence.
- 478 preliminary scenario active-formula claims disagree with workbook storage.
- The curated v5.3 value/editable/formula evidence set checked 94 coordinates with zero issues.

Blank scenario override cells still mean inherit, not zero.

## Status

This PR is analysis/report/test-only.

It does not change:

- runtime behavior
- model equations
- Inputs UI
- Scenarios UI
- persistence
- schema
- exports
- parity targets

## Current Recommendation

Do not begin Inputs or Scenarios implementation directly from workbook-only evidence. Use this contract as the acceptance gate for later implementation PRs:

1. bind already canonical runtime fields first
2. keep unresolved workbook-only concepts out of runtime
3. require explicit design approval before promoting workbook-only fields
4. keep formula-derived evidence read-only unless a backend source of truth is introduced

Implementation stop rule: future Inputs/Scenarios implementation must not directly consume preliminary `hardcode_cells`, `formula_cells`, `active_formula_kind`, `editable_policy`, or scenario classifications. Each implemented field requires a curated canonical mapping and verified workbook storage type.
