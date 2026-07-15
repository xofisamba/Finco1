# Implementation Backlog

## Ground Rule

This PR does not implement Inputs, Scenarios, exports, persistence, runtime behavior, or financial formulas.

Preliminary package metadata is inventory-only. Future implementation must not directly consume preliminary `hardcode_cells`, `formula_cells`, `active_formula_kind`, `editable_policy`, or scenario classifications. Each implemented field requires a curated canonical mapping and verified workbook storage type.

## Recommended Sequence

1. Runtime-aligned Inputs fields
   - bind existing canonical registry fields
   - use `canonical_registry_crosswalk_v5.csv` as the gate

2. Scenario override contract
   - implement only fields that have an approved canonical runtime target
   - preserve blank-vs-zero semantics

3. Workbook-only evidence review
   - review `unresolved_pack_id_evidence.csv`
   - review `support_package_metadata_audit_v5_3_1.json`
   - promote only explicitly approved concepts
   - keep absence-confirmed rows out of implementation

4. Read-only evidence surfaces
   - show workbook-only evidence as audit metadata where useful
   - do not turn formula-axis evidence into editable inputs

## Do Not Implement From This PR

- VAT/WHT reimbursement fields without distinct authoritative source
- formula-derived ownership shares as editable inputs
- DSRA balances as editable assumptions
- workbook-only tax concepts without design approval
- source workbook formulas or values in UI, docs, tests, or exports
- package-claim hardcodes as editable fields without workbook-verified hardcode storage
- package active-formula claims as scenario behavior without workbook-verified storage
