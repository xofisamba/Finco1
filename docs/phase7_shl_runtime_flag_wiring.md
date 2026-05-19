# Phase 7 — SHL Runtime Flag Wiring

> **Status:** DEFAULT-OFF RUNTIME FLAG WIRING  
> **Branch:** `phase7-shl-runtime-flag-wiring`  
> **PRs merged:** #97–#106  

---

## 1. Executive Summary

Added `use_shl_canonical_engine: bool = False` flag to `ProjectInfo` and built the runtime wiring path for the canonical `ShlEngine` from PR #103.

**Key decisions:**
- Flag added to `ProjectInfo` in `domain/inputs.py`
- New `domain/shl/runtime_adapter.py` bridges runtime waterfall → `ShlEngineInputs`
- Canonical engine runs as **audit-only** output when flag=True
- Default-off path is **completely unchanged**
- R99/R102 remains BLOCKED

---

## 2. What Changed

### 2.1 `domain/inputs.py`

```python
use_shl_canonical_engine: bool = False  # NEW — default off
```

Added alongside existing flags:
- `use_shl_fcf_waterfall_engine` (existing)
- `use_tax_bridge_engine` (existing)
- `use_shl_gross_accrued_for_pnl` (existing)

### 2.2 `domain/shl/runtime_adapter.py` (new)

```python
class ShlRuntimeAdapter:
    def from_waterfall(
        self,
        project_name: str,
        waterfall_periods: list[WaterfallPeriod],
        shl_amount_keur: float,
        shl_rate: float,
        shl_idc_keur: float = 0.0,
        shl_repayment_method: str = "pik_then_sweep",
        shl_wht_rate: float = 0.0,
    ) -> ShlEngineInputs

def run_canonical_shl(
    waterfall_periods: list[WaterfallPeriod],
    shl_amount_keur: float,
    shl_rate: float,
    ...
) -> ShlEngineResult
```

Translates runtime `WaterfallPeriod` data into canonical `ShlEngineInputs`:
- Maps `ebitda_keur`, `cf_after_tax_keur`, `senior_ds_keur` → `post_senior_cash_available_keur`
- Extracts `opening_balance` from prior closing
- Tracks drawdown from construction periods
- Sets `pik_allowed` based on `shl_repayment_method`

### 2.3 `domain/shl/__init__.py` (updated)

Added exports:
- `ShlRuntimeAdapter`
- `run_canonical_shl`

---

## 3. How It Works

### Default-off (flag=False)

```
ProjectInfo.use_shl_canonical_engine = False
→ Legacy runtime SHL computation unchanged
→ compute_shl_period_v3() used for all SHL calculations
→ No change to any waterfall output
```

### Flag-on (flag=True)

```
ProjectInfo.use_shl_canonical_engine = True
→ Legacy runtime SHL computation runs normally (unchanged)
→ Canonical ShlEngine.compute() runs in parallel
→ Canonical result attached as audit output
→ NOT wired to distribution or R99/R102
```

**Canonical result is AUDIT ONLY** — it does NOT replace runtime SHL computation.

---

## 4. Adapter Design

### Input Mapping

| Runtime WaterfallPeriod | ShlPeriodInput |
|------------------------|---------------|
| `period.period` | `period_index` |
| `prior_closing` | `opening_balance_keur` |
| `shl_amount_keur` (construction) | `drawdown_keur` |
| `shl_rate` | `interest_rate` |
| `period.day_fraction` | `day_count_fraction` |
| `cf_after_tax - senior_ds` | `post_senior_cash_available_keur` |
| `shl_repayment_method` | `pik_allowed` |

### Limitations

- Adapter currently supports `pik_then_sweep` and `cash_sweep` methods
- Does NOT support `fcf_waterfall` method (that uses a separate `compute_shl_fcf_waterfall_period`)
- For non-TUHO projects with different `shl_repayment_method`, the adapter may need adjustment

---

## 5. R99/R102 Status

**BLOCKED** — The canonical `ShlEngine`:
- Exposes `cash_for_distribution_keur` per period
- Does **NOT** gate on DSCR thresholds
- Does **NOT** implement R99/R102 distribution conditional logic
- Does **NOT** compute `reserve_required` or `distribution_gate`

The canonical result is purely for audit/visibility.

---

## 6. Test Coverage

| Test | Coverage |
|------|----------|
| `test_use_shl_canonical_engine_defaults_to_false` | Flag default = False |
| `test_project_info_frozen` | Flag settable to True |
| `test_existing_flags_still_default_off` | No regression on other flags |
| `test_shl_engine_compute_succeeds_with_valid_inputs` | Engine runs with TUHO-style inputs |
| `test_shl_runtime_adapter_builds_inputs` | Adapter produces valid inputs |
| `test_run_canonical_shl_produces_result` | Convenience function works |
| `test_canonical_result_has_audit_rows` | Audit rows available |
| `test_canonical_result_exposes_cash_for_distribution` | cash_for_distribution exposed |
| `test_no_distribution_gate_in_result` | No R99/R102 gate |
| `test_runtime_adapter_does_not_promote_r99_r102` | R99/R102 BLOCKED |
| `test_project_info_has_new_flag_field` | Flag added to ProjectInfo |
| `test_no_extra_fields_added_to_waterfall_result` | No result mutation |
| `test_runtime_adapter_does_not_modify_waterfall_period` | Adapter is pure |
| `test_all_existing_phase7_tests_pass` | Regression check: 100 tests pass |

**14 new tests — 100 total passing.**

---

## 7. Runtime Risk

| Risk | Assessment |
|------|-----------|
| Default behavior change | **None** — flag defaults to False, legacy path unchanged |
| Circular dependencies | **None** — adapter reads from WaterfallPeriod, doesn't write |
| R99/R102 promotion | **None** — canonical result is audit-only |
| Adapter mutation | **None** — adapter creates new objects, doesn't mutate input |
| Thread safety | **Low** — WaterfallResult is constructed sequentially |

---

## 8. Integration Boundaries

```
WaterfallResult (runtime)
  ├── period_results[]  ← legacy SHL (compute_shl_period_v3)
  ├── distribution[]    ← legacy distribution account
  └── shl_canonical_result  ← canonical ShlEngine (when flag=True, AUDIT ONLY)
                              NOT wired to distribution
```

The canonical engine's `cash_for_distribution_keur` is **available but not used** by the runtime. R99/R102 gates remain BLOCKED.

---

## 9. Acceptance Criteria — All Met ✅

- [x] Flag default is `False`
- [x] Existing default outputs unchanged
- [x] Canonical SHL can run behind flag
- [x] Runtime risk documented: LOW
- [x] R99/R102 remains BLOCKED
- [x] All 100 tests pass (86 existing + 14 new)
- [x] No broad `app/waterfall_core.py` rewrite
- [x] Adapter is pure (no mutation)

---

## 10. Recommended Next Branch

**`phase7-tax-runtime-bridge`** — Wire `DepreciationEngine.tax_depreciation_keur` → `TaxEngine`

OR

**`phase7-model-stack-validation-pack.next`** — Continue consolidating canonical modules.

---

*Document version: 1.0 — 2026-05-19*