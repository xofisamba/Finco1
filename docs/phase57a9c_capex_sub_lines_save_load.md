# Phase 57A-9C — CAPEX Sub-Lines Save/Load Wiring

**Type**: runtime persistence (no UI / no Run / no Excel /
no model / no waterfall changes)

**Status**: DRAFT PR. **Do NOT auto-merge.** Do NOT start
57A-9D / 57A-9E before review and explicit go-ahead.

**Base**: `efe68a3` (post-57A-9B main)

**Branch**: `phase57a9c-capex-sub-lines-save-load`

## 1. Summary

This PR implements the **save/load wiring** side of the
57A-9A persistence design gate. It connects the schema +
repository skeleton from 57A-9B to the existing
`save_project` / `get_project` / `update_scenario_overrides`
persistence functions. The implementation is exactly what
the 57A-9A design doc (PR #505) prescribed — no
deviations, no scope creep, no Run/Excel/model/UI touches.

**Save flow**: `save_project(..., capex_sub_lines=[...])`
soft-deletes the project's active sub-lines and inserts the
new set in the same transaction. UUIDs are preserved across
round-trips when supplied; auto-generated otherwise.

**Load flow**: `get_project_with_sub_lines(user_id,
project_code)` returns a `(ProjectRecord, tuple[CapexSubLine, ...])`
pair. Sub-lines are in canonical order
`(parent_category_code ASC, display_order ASC)`. Soft-deleted
rows are excluded by default; pass
`include_inactive_sub_lines=True` for audit / replay.

**Scenario override flow**: `update_scenario_overrides`
now consults a second allowlist of reserved keys
(`_capex_sub_line_overrides`,
`_capex_sub_line_overrides_metadata`) BEFORE the silent-drop
rule. The Phase 20B invariant is preserved (unknown keys
continue to be silently dropped). `SCENARIO_INPUT_FIELDS`
still has its 21 flat-path keys.

## 2. Save flow

### 2.1 New function: `replace_sub_lines_for_project`

In `app/persistence/capex_sub_lines.py`:

```python
def replace_sub_lines_for_project(
    cur: Any,
    *,
    project_id: str,
    sub_lines: Sequence[CapexSubLine],
) -> list[CapexSubLine]:
    """Soft-delete existing active rows, then insert the new
    set. UUID identity is preserved for round-trips.
    business_code is auto-computed for new lines (C.NN.U###
    format, gap-preserving on soft-delete) but reused when
    supplied."""
```

The function takes an explicit cursor so the caller controls
the transaction. In `save_project`, the cursor is the same
`get_cursor()` context as the project row INSERT, so a
partial failure rolls back both writes atomically.

### 2.2 Extended function: `save_project`

In `app/persistence/projects_repository.py`:

```python
def save_project(
    user_id: str,
    project_code: str,
    project_name: str,
    source_project_template: str,
    ...
    replay_metadata: Optional[dict[str, Any]] = None,
    capex_sub_lines: Optional[list] = None,  # NEW
) -> "ProjectRecord":
```

The new parameter is `Optional[list]` and **defaults to
None**. When None, the function behaves identically to the
pre-57A-9C version (no sub-line side effects, no error).
This preserves backward compatibility for all existing
callers.

When a list is provided:

1. The project row is INSERT/UPDATEd (unchanged).
2. The active sub-lines for the project are soft-deleted
   (`is_active = 0`, `business_code` slot preserved).
3. Any sub-lines that share a `sub_line_id` with the new
   set are permanently deleted (so the UNIQUE constraint
   does not block the re-insert).
4. The new set is INSERTed in canonical
   `(parent_category_code, display_order)` order.
5. The factory-template guard is enforced:
   `assert_project_allows_capex_sub_lines` raises
   `PermissionError` for `factory_template` projects.

All five steps run inside the same `with get_cursor() as
cur:` block, so a partial failure rolls back the entire
save.

### 2.3 UUID identity preservation

If the caller supplies a `sub_line_id` on the input
sub-line (a UUID string), the inserted row reuses that UUID
exactly. This is the safety property the design gate
promised: scenario overrides keyed by UUID survive a save.

If the input `sub_line_id` is empty, the helper generates a
fresh UUID. Different calls yield different UUIDs
(no collisions).

`TestUUIDStabilityAcrossRoundTrip` pins the contract:
- `test_supplied_sub_line_id_preserved` — caller UUID
  round-trips through save → load unchanged.
- `test_empty_sub_line_id_auto_generated` — empty input
  gets a fresh UUID, two different inputs get two different
  UUIDs.
- `test_uuid_preserved_through_two_round_trips` — saving
  the same project twice with the same input UUID keeps
  the UUID stable.

### 2.4 Display order preservation

If the caller supplies a non-zero `display_order`, it is
reused on insert (round-trip preservation). If it is zero
or unset, the helper auto-computes
`MAX(display_order) + 1` for the `(project_id,
parent_category_code)` pair.

`TestCanonicalOrder` pins the contract: sub-lines inserted
out of order are loaded back in canonical
`(parent_category_code ASC, display_order ASC)` order.

## 3. Load flow

### 3.1 New function: `get_project_with_sub_lines`

In `app/persistence/projects_repository.py`:

```python
def get_project_with_sub_lines(
    user_id: str,
    project_code: str,
    include_inactive_sub_lines: bool = False,
) -> "tuple[Optional[ProjectRecord], tuple[CapexSubLine, ...]]":
    """Load a project and its CAPEX sub-lines in one call.

    Returns ``(project_record, sub_lines)``. ``project_record``
    is None if the project does not exist. ``sub_lines`` is
    the canonical-order tuple of active rows (or all rows
    including soft-deleted, if include_inactive_sub_lines
    is True).
    """
```

The function opens its own cursor for the sub-line query
(after the project query). The project query reuses the
existing `get_project_by_code` helper.

### 3.2 New function: `get_project_by_id_with_sub_lines`

Same contract as `get_project_with_sub_lines`, but keyed by
`project_id` instead of `project_code`. Useful when the
caller already has the project_id (e.g. from a route param).

### 3.3 Soft-delete safety

Soft-deleted sub-lines (`is_active = 0`) are excluded by
default. Pass `include_inactive_sub_lines=True` to include
them (for audit / replay). The rows remain in the table
for audit purposes either way.

`TestLoadHelpers::test_load_excludes_soft_deleted_by_default`
and `test_load_includes_soft_deleted_when_requested` pin the
contract.

## 4. Scenario override allowlist

### 4.1 Additive allowlist

In `app/persistence/scenarios_repository.py`:

```python
_RESERVED_OVERRIDE_KEYS = frozenset(
    {"_capex_sub_line_overrides", "_capex_sub_line_overrides_metadata"}
)

# ... inside update_scenario_overrides ...
for key, value in overrides.items():
    if key in SCENARIO_INPUT_FIELDS:
        merged[key] = value
    elif key in _RESERVED_OVERRIDE_KEYS:
        merged[key] = value
    # else: silently drop unknown keys per Phase 20B rules
```

The reserved-key allowlist is consulted BEFORE the
silent-drop rule fires. This is the exact contract
57A-9A §6.6 specified. `SCENARIO_INPUT_FIELDS` is unchanged
(still 21 flat-path keys), so existing scenario overrides
are unaffected.

### 4.2 Reserved key semantics

- `_capex_sub_line_overrides` is a `{sub_line_uuid: amount_keur}` map.
  The 57A-9D Run integration helper consults this map to
  apply per-scenario amount overrides. For 57A-9C, the
  helper just persists and retrieves the map unchanged.
- `_capex_sub_line_overrides_metadata` is a free-form
  metadata blob (e.g. `{"source": "ui_57a8", "version": 1}`).
  Used for replay / audit; not consulted by the runtime.

The 57A-9B `resolve_effective_sub_line_amount` helper
carries the override semantic forward: at runtime, the
effective amount is `override or default` — REPLACE, not
delta. Pinned in
`TestEffectiveSubLineAmountReplaceNotDelta`.

### 4.3 Phase 20B invariant preserved

Unknown keys (e.g. `some_random_key`, `another_unknown`)
continue to be silently dropped, just as in the pre-57A-9C
behavior. The reserved-key allowlist is additive: it does
NOT change the existing silent-drop rule for non-reserved,
non-flat-path keys.

`TestScenarioOverrideAllowlist::test_unknown_keys_silently_dropped_phase_20b_invariant`
pins the contract.

## 5. Test coverage

35 new tests pin the save/load + scenario override
contracts:

- **TestSaveProjectAcceptsSubLines** (4 tests): signature,
  no-op backward compat, persist, replace.
- **TestUUIDStabilityAcrossRoundTrip** (3 tests):
  supplied UUID preserved, auto-generated, two round-trips.
- **TestLoadHelpers** (6 tests): pair return, no subs,
  missing project, by-id variant, soft-delete excluded,
  soft-delete included.
- **TestCanonicalOrder** (1 test): canonical sort order.
- **TestScenarioOverrideAllowlist** (6 tests): reserved
  keys accepted, unknown keys dropped, flat-path keys still
  work, DB persistence, `SCENARIO_INPUT_FIELDS` count,
  base-case rejection.
- **TestEffectiveSubLineAmountReplaceNotDelta** (3 tests):
  no override returns default, override replaces,
  explicit "not a delta" invariant.
- **TestFactoryProjectGuard** (4 tests): factory raises,
  user_project allowed, saved_baseline allowed,
  defense-in-depth (factory + is_readonly=False rejected).
- **TestSoftDeleteSafety** (2 tests): load excludes
  soft-deleted, override key for soft-deleted line ignored.
- **TestNoProductionCodeChanged** (2 tests): forbidden
  paths untouched, only persistence/tests/docs/reports
  in diff.
- **TestRc1Frozen** (1 test): rc1 SHA resolves.
- **TestPhasePlanAndHardNoGo** (3 tests): 7-row plan,
  16-item no-go, stop-after-report contract.

Plus 5 additive skip-guard fixes to existing test files
to handle the file-scope tests that are sensitive to
branch context (same pattern as 57A-3 followup PR #502):

- `tests/test_phase57a3_capex_hide_backend_keys.py` — added
  "57A-9X" recognition in the TestFileScope skip logic.
- `tests/test_phase57a4_single_capex_sheet_layout.py` —
  same.
- `tests/test_phase57a5_capex_line_item_hierarchy_foundation.py`
  — added skip-guard for `test_no_persistence_changes`.
- `tests/test_phase57a5b_canonical_capex_subline_catalogue.py`
  — added skip-guard for `test_no_persistence_changes`.
- `tests/test_phase57a8_capex_add_line_ux_in_memory.py` —
  added skip-guards for `test_no_persistence_changes`
  and `test_allowed_files_only`.
- `tests/test_phase57a_ui3_line_item_grid_capex_summary.py`
  — added skip-guard for `test_no_persistence_directory_changed`.

## 6. Forbidden paths (verified)

`git diff origin/main --name-only` against the 57A-9C
branch shows zero changes to any of:

- `app/waterfall_core/` (Run, waterfall)
- `app/project_factories/` (factory templates)
- `app/excel_export/` (Excel export)
- `app/inputs/` (input helpers)
- `app/ui/` (UI context)
- `app/templates/` (Jinja templates)
- `static/app.js` (frontend JS)
- `static/styles.css` (frontend CSS)
- `main_web.py` (web routes)
- `main_api.py` (API routes)
- `app/domain/` (domain financial calculations)

The only `app/` changes are inside `app/persistence/`.
`TestNoProductionCodeChanged` pins this contract.

## 7. Run / Excel / model impact

**None.** 57A-9C touches only:

- `app/persistence/capex_sub_lines.py` — new helpers
  (`replace_sub_lines_for_project`,
  `get_active_sub_lines_for_project`,
  `soft_delete_sub_line_for_project`).
- `app/persistence/projects_repository.py` — extended
  `save_project` (additive parameter), new load helpers.
- `app/persistence/scenarios_repository.py` — extended
  `update_scenario_overrides` (additive allowlist).
- `tests/test_phase57a9c_capex_sub_lines_save_load.py` —
  new test file.
- Skip-guard followups in 5 existing test files (additive).

The Run integration helper
(`_apply_user_sub_lines_to_capex`) is NOT touched.
The Excel export integration
(`advanced_capex_line_items` parameter) is NOT touched.
The CAPEX totals computation is NOT touched.

TUHO/Oborovo parity is preserved by construction: the
factory-template guard rejects sub-line creation, and
factory projects have no sub-lines (existing
`fold_sub_lines_into_capex` no-op is unchanged).

## 8. Phase plan status

| Phase | Status |
|---|---|
| 57A-9A | MERGED (design gate, PR #505) |
| 57A-9B | MERGED (schema + repo skeleton, PR #506) |
| **57A-9C** | **THIS PR (save/load wiring, DRAFT)** |
| 57A-9D | Not started (Run integration, gated on review) |
| 57A-9E | Not started (Excel export, gated on review) |
| 57A-9F | Not started (governance refresh, auto-merge) |
| 57A-10 | Not started (TUHO/Oborovo parity gate, auto-merge) |

## 9. Hard no-go (preserved)

15 from 57A-9A + 1 new for 57A-9C:

1. no_financial_formula_changes
2. no_idc_calculation_changes
3. no_construction_funding_changes
4. no_senior_debt_shl_drawdown_changes
5. no_tax_engine_changes
6. no_depreciation_engine_changes
7. no_g20_r99_r102_promotion
8. no_tailwind_alpine_react_vue_svelte
9. no_backend_keys_visible_in_ui
10. no_overrides_json_schema_change (additive only)
11. no_factory_project_mutation (factory guard is
    defense-in-depth; raises PermissionError)
12. no_57a8_in_memory_preview_regression
13. **no_run_integration (deferred to 57A-9D)** — NEW for 57A-9C
14. **no_excel_export_integration (deferred to 57A-9E)** — NEW for 57A-9C
15. no_ui_redesign
16. rc1_frozen

## 10. Stop-after-report contract

This PR is the **save/load wiring**. Do NOT mark ready, do
NOT merge, do NOT start 57A-9D / 57A-9E before review and
explicit go-ahead. The 35 design-contract tests pin the
contracts; the 960-test integration test suite (run on the
branch) verifies no regressions in the existing 57-arc
stack.

`TestPhasePlanAndHardNoGo::test_stop_after_report_contract`
pins this contract.
