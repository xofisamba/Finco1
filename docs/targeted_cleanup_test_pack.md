# Targeted Cleanup Test Pack

## Purpose

This cleanup pack adds focused pilot-readiness coverage without expanding
product scope. It exists to strengthen confidence around:

- editable-grid draft/saved/runtime boundaries
- backend-authoritative runtime execution
- workbook/export descriptive behavior
- legacy governance-label interpretation
- optional auth dependency isolation in tests

No runtime/model formulas are changed. No workbook calculations are changed. No
new editable surfaces are added. No persistence authority is promoted.

## What Was Added

### 1. End-to-end workflow test

`tests/test_targeted_cleanup_e2e_workflow.py` covers:

- project selection
- editable draft mutation
- dirty-state assertion
- explicit scenario save
- dirty-state clear after save
- runtime guard blocking while dirty
- backend run after clean save
- immutable runtime snapshot recording
- workbook export creation and readability
- governance posture preservation

This test is intentionally repository/helper driven rather than browser driven.
The goal is authority-boundary confidence, not UI animation coverage.

### 2. Numeric workbook-content test

`tests/test_targeted_cleanup_workbook_content.py` checks representative numeric
cells against backend runtime summary rows:

- `Runtime Summary -> Project IRR`
- `Runtime Summary -> Total Revenue`
- `OPEX -> Runtime total OPEX`

This proves the workbook export remains descriptive of backend runtime output.

### 3. Dependency-isolation test

`tests/test_targeted_cleanup_dependency_isolation.py` addresses the local test
collection issue where `tests/conftest.py` imported `app.auth`, which in turn
requires optional `bcrypt`.

The fix is test-harness only:

- `tests/conftest.py` now installs a tiny `bcrypt` shim only when the module is
  absent
- the production auth module is unchanged
- non-auth tests can collect without `--noconftest`

## RUNTIME_BINDING_PENDING Boundary

The re-audit found two current meanings:

1. **Active current semantics**
   - reporting breakout exists conceptually
   - runtime logic exists
   - reviewer-facing runtime/export binding is not yet first-class

2. **Legacy/frozen references**
   - older generated CSVs and historical docs preserve earlier status wording
   - those should not be mass-rewritten unless the artifact is still an active
     source-of-truth surface

New outputs should continue using the clarified governance semantics introduced
in Phase 12, while legacy historical artifacts may remain frozen when they are
part of prior branch evidence.

## Legacy Governance Artifact Boundary

Historical Phase 9/10 artifacts still contain `MISSING_EVIDENCE` in places where
current governance semantics would now prefer:

- `MISSING_EXCEL_EVIDENCE`
- `MISSING_REVIEW_SCALAR`
- `SOURCE_NOT_AVAILABLE`
- `RUNTIME_BINDING_PENDING`

This cleanup pack does not rewrite those historical artifacts. Instead it:

- documents which ones are legacy-frozen
- distinguishes them from active current semantics
- preserves the current source-of-truth in Phase 12 governance semantics docs

## Authority Boundaries Reconfirmed

- runtime remains backend-authoritative
- editable grids remain draft-only
- saved scenarios remain the persisted boundary
- workbook/export layers remain descriptive
- persistence remains non-authoritative metadata/snapshot storage
- `audit_economic_mode` remains audit/reconciliation-only
- `runtime_economic_mode` remains the only explicit runtime staging path
- `G20` remains `BLOCKED`
- `R99/R102` remain `NOT APPROVED`

## Remaining Limitations

- this pack does not add browser-level end-to-end automation
- workbook numeric coverage is intentionally representative, not exhaustive
- historical legacy governance artifacts still exist and should be treated as
  frozen evidence unless explicitly reissued
- the bcrypt shim is for test collection only and should not be mistaken for a
  production auth fallback
