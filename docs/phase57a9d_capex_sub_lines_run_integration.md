# Phase 57A-9D — CAPEX Sub-Lines Run / Materialization Integration

**Type**: runtime model-input integration (DRAFT PR).

**Status**: DRAFT. **Do NOT mark ready.** Do NOT start
57A-9E / 57A-9F / 57A-10 before review and explicit
go-ahead.

**Base**: `f89b799` (post-57A-9C head of PR #507, the
57A-9C save/load + scenario allowlist wire-up).

**Branch**: `phase57a9d-capex-sub-lines-run-integration`

## 1. Summary

This is the first phase where user-added CAPEX rows
may affect model outputs. **Treat as high risk.**

The PR implements the Run/materialization wire-up that
folds persisted user-added CAPEX sub-lines into the
input `CapexStructure` of the financial model. The
fold runs ONLY in the user-created project path; factory
projects (TUHO, Oborovo, Generic Solar, Generic Wind)
are NOT touched. TUHO / Oborovo parity is preserved
by construction (the integration helper returns the
input capex unchanged for factory projects, and the
factory paths do not call the helper at all).

The change is purely an **input-materialization step**:
the helper modifies the `CapexItem.amount_keur` fields
of the 15 named fields in the `CapexStructure`, using
the locked `CAPEX_CATEGORY_TO_FIELD` mapping from 57A-9B.
No model formula path is touched, no Excel export is
touched, no UI / static asset is touched.

## 2. Exact Run / materialization insertion point

**File**: `app/services/run_service.py`
**Function**: `_execute_user_created_path`
**Insertion**: between `override = deps.build_projectinputs_from_snapshot(runtime_snapshot)`
and `result = deps.run_project(runtime_project_key, scenario_name, project_inputs_override=override)`.

The new code:

```python
# Phase 57A-9D: fold persisted user-added CAPEX
# sub-lines into the input CapexStructure. This
# is the explicit Run/materialization boundary.
# It runs ONLY in the user-created path — factory
# / template-seeded paths (TUHO, Oborovo, Generic
# Solar, Generic Wind) do NOT call this helper.
# 57A-8 in-memory preview rows are NOT persisted,
# so they cannot leak in here.
if active_scenario_record is not None:
    _scenario_overrides_for_fold = (
        active_scenario_record.overrides
    )
else:
    _scenario_overrides_for_fold = None
from app.services.capex_sub_lines_integration import (
    _apply_user_sub_lines_to_capex,
)
folded_capex = _apply_user_sub_lines_to_capex(
    override.capex,
    project_id=project_record.project_id,
    scenario_overrides=_scenario_overrides_for_fold,
)
if folded_capex is not override.capex:
    # The fold produced a new CapexStructure (it
    # is frozen, so it had to). Replace the
    # override's capex with the folded one.
    from dataclasses import replace as _dc_replace
    override = _dc_replace(override, capex=folded_capex)
```

This is the **explicit boundary** the design gate
required. The wire-up is:

1. **Explicit**: the helper call is visible in the
   run service code; there is no implicit magic.
2. **Scoped**: it runs only in the user-created path.
   The template-seeded path (TUHO/Oborovo) and the
   generic path (Generic Solar/Wind) do NOT call the
   helper. This is the TUHO/Oborovo parity guarantee.
3. **No fake IDs**: the helper uses persisted
   `sub_line_id` (UUID) values, which are the
   scenario-override key. No runtime-generated
   identifiers.
4. **No 57A-8 preview leakage**: 57A-8 in-memory
   preview rows (TMP markers) are NOT persisted in
   the `capex_sub_lines` table, so the helper
   literally cannot see them.

## 3. The integration helper

**File**: `app/services/capex_sub_lines_integration.py`
**Public function**: `_apply_user_sub_lines_to_capex(capex, *, project_id, scenario_overrides=None)`

```python
def _apply_user_sub_lines_to_capex(
    capex: Any,
    *,
    project_id: str,
    scenario_overrides: Optional[Mapping[str, Any]] = None,
) -> Any:
    """Fold persisted user sub-lines into a CapexStructure.

    1. Factory / template-seeded projects: the helper
       returns capex unchanged (the empty-input
       short-circuit in fold_sub_lines_into_capex).
    2. User projects: load active sub-lines from
       capex_sub_lines table, apply scenario overrides,
       fold into CapexStructure.
    3. The 57A-9B Claude delta review fix is preserved:
       override REPLACES default amount, not a delta.
    4. Unknown sub_line_id override UUIDs are ignored
       (line may have been removed since the scenario
       was saved). The Run does not crash; a warning
       is logged.
    5. Unknown parent categories raise ValueError
       loudly. C.17 / C.18 are rejected at persistence
       time.
    6. The helper does NOT mutate the input
       CapexStructure (it is frozen, so this is
       enforced).
    """
```

The helper is a thin integration layer. The actual
fold logic lives in `app.persistence.capex_sub_lines.
fold_sub_lines_into_capex` (57A-9B), which the
integration helper delegates to.

## 4. Before / after numeric example

**User project, single C.02 sub-line +5000 kEUR**:

```
Solar factory baseline:
  epc_contract = 20000.0 kEUR
  audit_legal  =     0.0 kEUR
  ...

User project, C.02 sub-line amount=5000.0 kEUR:
  After fold:
    epc_contract = 25000.0  (20000 + 5000)
    audit_legal  =     0.0  (unchanged)
  Total capex delta: +5000.0 kEUR on epc_contract
```

**C.08 + C.11 fold additively into audit_legal**:

```
Wind factory baseline:
  audit_legal = 0.0 kEUR

User project, C.08 = 300.0, C.11 = 400.0:
  After fold:
    audit_legal = 700.0  (0 + 300 + 400)
  Both C.08 and C.11 add into audit_legal
  (locked mapping, 57A-9B Claude delta review)
```

**Override REPLACES default**:

```
User project, C.02 sub-line default = 5000.0
Scenario override: {sub_line_id: 8000.0}

After fold:
  epc_contract = baseline + 8000.0
  (NOT baseline + 5000 + 8000)
```

**Stale override (line was soft-deleted) is ignored**:

```
User project, C.02 sub-line = 100.0
Scenario override: {deleted_uuid: 99999.0, deleted_uuid_2: 88888.0}

After fold:
  epc_contract = baseline + 100.0
  The stale overrides are ignored; only the real
  sub-line folds in. A warning is logged.
```

## 5. TUHO / Oborovo parity confirmation

**Captured before / after for TUHO and Oborovo** (factory
projects, the canonical parity references):

| Project | epc_contract before | epc_contract after | Total 15-field before | Total 15-field after | Same instance? |
|---|---|---|---|---|---|
| **TUHO** | 52800.0 | 52800.0 | 70691.54 | 70691.54 | ✅ true |
| **Oborovo** | 26430.0 | 26430.0 | 55999.09 | 55999.09 | ✅ true |

The integration helper returns the EXACT same object
instance for factory projects (`is_same_instance: true`).
The factory total capex is bit-for-bit identical to
the pre-57A-9D baseline. No mutation, no new object
allocation, no fold.

**Why this is the canonical guarantee**: factory
projects have no user sub-lines (the factory never
persists any in the `capex_sub_lines` table), and the
factory paths in `run_service.py` (template-seeded,
generic) do not call the integration helper. So the
factory capex flows from the factory function directly
to the model engine, unchanged.

## 6. Run / Excel / UI / static changes

**No Run path changes beyond CAPEX materialization**.
The only changes to the Run path are:

- `app/services/run_service.py::_execute_user_created_path`:
  one new code block (~25 lines) that calls
  `_apply_user_sub_lines_to_capex` and replaces
  `override.capex` with the folded result if the
  helper returned a new instance. The fold is a no-op
  for factory projects; the call is the only
  change. The downstream `deps.run_project(...)` call
  is unchanged.
- The template-seeded path (TUHO/Oborovo) and the
  generic path (Generic Solar/Wind) are NOT
  modified.

**No Excel export integration**. `advanced_capex_line_items`
parameter is still `None` everywhere. The Excel
export module (`app/excel_export.py`) is NOT touched.
57A-9E is the phase that wires the user sub-lines
into the Excel export; it is gated on review.

**No UI / static changes**. `app/templates/`,
`static/app.js`, `static/styles.css` are NOT touched.
The 57A-8 in-memory preview rows (TMP markers) are
NOT touched; 57A-8 is the in-memory preview, and it
is preserved by construction (the integration helper
only reads from the `capex_sub_lines` table, which
the preview rows never reach).

**No financial formula changes**. The 15 named
`CapexItem.amount_keur` fields are updated in place
(into a NEW `CapexStructure`, since the input is
frozen). The model formula path
(`app/waterfall_core.py`, `app/waterfall_runner.py`,
`app/opex_engine.py`, `app/depreciation_engine.py`,
`app/sponsor_runner.py`, `app/portfolio_runner.py`,
`app/holdco_tax_ui.py`, `app/tax_assumptions_ui.py`,
`app/tax_ui.py`, `domain/`) is NOT touched.

**No VAT/WHT/depreciation columns, payment schedule,
or IDC schedule wiring**. The integration helper
only affects the 15 named `CapexItem.amount_keur`
fields. The downstream financial engine computes
the same totals as before, with the modified input.
No new fields, no new formulas, no new schedules.

## 7. Changed files

| File | Type | LOC | Rationale |
|---|---|---|---|
| `app/services/capex_sub_lines_integration.py` | A | +280 | New integration helper module. Thin layer over `fold_sub_lines_into_capex` (57A-9B). Handles DB load, scenario-override extraction, soft-delete filter, stale-override warning. |
| `app/services/run_service.py` | M | +27 | Added the explicit fold call in `_execute_user_created_path`. Template-seeded and generic paths unchanged. |
| `tests/test_phase57a9d_capex_sub_lines_run_integration.py` | A | +990 | 22 new design-contract tests pinning: factory no-op parity, user-project fold, scenario-override REPLACE, soft-delete exclusion, validation fail-fast, immutability, no forbidden paths. |
| 4 test followups (skip-guards) | M | +104 | 57A-5, 57A-5B, 57A-8, 57A `app/services/` skip-guards (additive, same pattern as 57A-3 followup PR #502). |
| `tests/test_phase57a9c_capex_sub_lines_save_load.py` | M | +6 | Allow-list update: `app/services/run_service.py` + `app/services/capex_sub_lines_integration.py` are now in scope (57A-9D legitimately wires them). |
| `docs/phase57a9d_capex_sub_lines_run_integration.md` | A | +400 | This document. |
| `reports/phase57a9d_capex_sub_lines_run_integration.json` | A | +260 | Machine-readable summary. |

## 8. Test coverage (22 new tests)

- **TestFactoryNoOpParity** (3 tests): TUHO factory total
  unchanged, Oborovo factory total unchanged, empty
  project_id short-circuit.
- **TestUserProjectFold** (3 tests): single C.02 sub-line
  increases epc_contract, C.08+C.11 add into audit_legal
  additively, soft-deleted sub-lines excluded.
- **TestScenarioOverrideReplace** (3 tests): override
  replaces default amount (REPLACE not delta), unknown
  sub_line_id override ignored, malformed reserved-key
  value falls back to empty.
- **TestValidationFailFast** (3 tests): unknown parent
  category raises ValueError, C.17 rejected, C.18
  rejected.
- **TestRunMaterializationBoundary** (3 tests): helper
  does not mutate input capex, helper returns capex
  unchanged when no sub-lines, 57A-8 in-memory preview
  rows not loaded.
- **TestNoForbiddenChanges** (3 tests): forbidden
  paths not changed, only persistence/services/tests
  changed, no financial formula changes.
- **TestRc1Frozen** (1 test): rc1 SHA resolves.
- **TestPhasePlanAndHardNoGo** (3 tests): 7-row plan,
  18-item no-go (16 from 57A-9C + 2 new for 57A-9D),
  stop-after-report contract.

## 9. Hard no-go (18 items, all verified pre-commit)

1. **no_financial_formula_changes (NEW for 57A-9D)** —
   input materialization only; no model / formula / IDC
   / tax / depreciation / payment schedule changes
2. no_idc_calculation_changes
3. no_construction_funding_changes
4. no_senior_debt_shl_drawdown_changes
5. no_tax_engine_changes
6. no_depreciation_engine_changes
7. **no_payment_schedule_changes (NEW for 57A-9D)**
8. **no_idc_schedule_wiring (NEW for 57A-9D)**
9. no_g20_r99_r102_promotion
10. no_tailwind_alpine_react_vue_svelte
11. no_backend_keys_visible_in_ui
12. no_overrides_json_schema_change (additive only)
13. no_factory_project_mutation
14. no_57a8_in_memory_preview_regression
15. **no_run_path_changes_beyond_capex_materialization (NEW for 57A-9D)**
16. no_excel_export_integration (deferred to 57A-9E)
17. no_ui_redesign
18. rc1_frozen

## 10. Stop-after-report contract

This PR is the **Run/materialization wire-up**. Do NOT
mark ready. Do NOT merge. Do NOT start 57A-9E / 57A-9F
/ 57A-10 before review and explicit go-ahead. The
22 design-contract tests pin the contract; the
1010-test integration test suite (run on the branch)
verifies no regressions in the existing 57-arc stack.
