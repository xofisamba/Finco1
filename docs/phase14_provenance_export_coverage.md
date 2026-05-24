# Phase 14 Provenance Export Coverage

## Conclusion

This branch reaches **B. Minor descriptive provenance gaps**.

The active export paths already carried a meaningful provenance spine through
persistence metadata and partial workbook/CSV coverage. The remaining work was
to standardize reviewer-readable export provenance so active artifacts expose the
same descriptive contract instead of forcing reviewers to infer what is missing,
not applicable, or legacy-frozen.

No runtime formulas were changed.
No workbook calculations were changed.
No persistence authority promotion occurred.
No replay engine behavior was added.

`audit_economic_mode` remains audit/reconciliation-only.
`runtime_economic_mode` remains the only explicit runtime staging path.
`G20` remains `BLOCKED`.
`R99/R102` remain `NOT APPROVED`.

## Active Export Paths

Current active web export paths:

1. `excel_model_export`
   - Route: `/download`
   - Artifact: values-only Excel workbook
   - Status: active/current
   - Provenance posture: now includes a descriptive Notes-sheet provenance block

2. `runtime_summary_csv`
   - Route: `/exports/runtime-summary.csv`
   - Artifact: runtime summary CSV
   - Status: active/current
   - Provenance posture: canonical field coverage standardized in CSV columns

3. `institutional_workbook`
   - Route: `/exports/institutional-workbook.xlsx`
   - Artifact: institutional workbook
   - Status: active/current
   - Provenance posture: canonical provenance rows standardized on cover and governance sheets

Legacy or generated historical reports remain legacy-frozen unless they are part
of one of the active export paths above.

## Canonical Provenance Standard

For active exports, the canonical provenance set is:

- `export_generated_at`
- `runtime_generated_at`
- `commit_sha`
- `branch_name`
- `active_project`
- `scenario_id`
- `scenario_name`
- `scenario_revision`
- `runtime_snapshot_id`
- `runtime_origin`
- `runtime_flag_snapshot` representation
- `template_origin`
- `template_revision`
- `export_template_version`
- governance posture summary

If a field is not available for a given export path, it must be explicitly
represented as one of:

- `unavailable`
- `not_applicable`
- `legacy_frozen`

It must not be silently omitted from active/current exports.

## Authority Boundary

Export provenance is descriptive only.

It does not:

- compute financial values
- override runtime outputs
- promote workbook/export into calculation authority
- become replay engine behavior
- imply approval
- promote audit/reconciliation-only outputs into runtime authority

Runtime calculations remain authoritative and backend-owned.
Workbook/export artifacts remain descriptive review outputs.

## Workbook Coverage

The institutional workbook now exposes canonical provenance on reviewer-facing
metadata rows without touching calculation sheets or formulas.

The values-only Excel export now exposes a richer provenance block on the Notes
sheet so the generic download path is interpretable without relying solely on
export registry persistence records.

## Remaining Gaps

- Active exports now carry standardized descriptive provenance, but some older
  historical/generated artifacts remain legacy-frozen and are intentionally not
  rewritten in this branch.
- Some paths do not have a persisted saved-scenario boundary at export time, so
  `scenario_id`, `scenario_name`, `scenario_revision`, or `runtime_snapshot_id`
  may legitimately appear as `not_applicable` or `unavailable`.
- Provenance improves traceability, but it does not create deterministic replay.

## Guardrails

- No runtime/model formula changes
- No workbook calculation changes
- No persistence authority promotion
- No replay engine behavior
- No governance behavior changes
- No new editable surfaces
- No JavaScript financial calculations
- `audit_economic_mode` / `runtime_economic_mode` contracts unchanged
- `G20` remains `BLOCKED`
- `R99/R102` remain `NOT APPROVED`
