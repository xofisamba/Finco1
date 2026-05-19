# Phase 7 — Senior Debt Sizing Flag

> **Status:** RUNTIME BEHIND DEFAULT-OFF FLAG  
> **Branch:** `phase7-senior-debt-sizing-flag`  
> **PRs merged:** #97, #98, #99, #100, #101, #102, #103  

---

## 1. Executive Summary

This branch implements a small, isolated senior debt sizing policy abstraction in `domain/senior_debt_sizing/` without changing existing runtime behavior.

**Key decisions:**
- `domain/senior_debt_sizing/` module with `SeniorDebtSizingPolicy` and `SeniorDebtSizingEngine`
- `sizing_mode = "explicit_cfads"` (Macro!R50 parity) implemented
- `sizing_mode = "derive_from_minimum_dscr"` documented as future stub (`NotImplementedError`)
- No flag wired in project factory — pure domain code
- `inferred_minimum_dscr = 1.45` documented as inferred, not proven Excel formula
- R99/R102 remains BLOCKED

---

## 2. Module Structure

```
domain/senior_debt_sizing/
├── __init__.py       # Exports: SeniorDebtSizingPolicy, SeniorDebtDSCRPolicy, SizingMode, SeniorDebtSizingEngine
├── policy.py         # SeniorDebtSizingPolicy, SeniorDebtDSCRPolicy, SeniorDebtSizingResult, SizingMode
└── engine.py         # SeniorDebtSizingEngine.compute(policy, dscr_policy) -> result
```

---

## 3. Policy Design

### 3.1 `SeniorDebtSizingPolicy`

```python
@dataclass(frozen=True)
class SeniorDebtSizingPolicy:
    project_name: str
    sizing_mode: SizingMode           # EXPLICIT_CFADS or DERIVE_FROM_MINIMUM_DSCR
    sizing_cfads_keur_by_period: Tuple[float, ...]
    source_cell: str = "Macro!R50"
    inferred_minimum_dscr: Optional[float] = 1.45  # TUHO: inferred ≈1.45x
```

### 3.2 `SeniorDebtDSCRPolicy`

```python
@dataclass(frozen=True)
class SeniorDebtDSCRPolicy:
    target_dscr_by_period: Tuple[float, ...]
    ppa_dscr: float = 1.20      # TUHO PPA
    merchant_dscr: float = 1.41  # TUHO merchant
    switch_period: Optional[int] = 26  # PPA→merchant switch
```

### 3.3 `SizingMode`

```python
class SizingMode(Enum):
    EXPLICIT_CFADS = "explicit_cfads"          # TUHO Macro!R50 parity
    DERIVE_FROM_MINIMUM_DSCR = "derive_from_minimum_dscr"  # future canonical
```

---

## 4. Engine: `SeniorDebtSizingEngine.compute()`

```
For each period t:
    debt_service_capacity[t] = sizing_cfads[t] / target_dscr[t]

Returns SeniorDebtSizingResult:
    - debt_service_capacity_keur_by_period
    - sizing_cfads_keur_by_period (unchanged for EXPLICIT_CFADS mode)
    - target_dscr_by_period
    - total_sizing_cfads_keur
    - total_debt_service_capacity_keur
```

---

## 5. Runtime Flag Status

**Decision: No runtime flag wired.**

Adding `use_explicit_senior_debt_sizing_policy: bool = False` to `ProjectInfo` follows the existing pattern of similar flags (`use_shl_fcf_waterfall_engine`, etc.). However, to avoid any risk to the factory, the flag is NOT added in this branch.

The sizing policy module is implemented as **pure domain code**. Future integration:

```python
# Future: in ProjectInfo (domain/inputs.py)
use_explicit_senior_debt_sizing_policy: bool = False  # default OFF

# Future: in waterfall_core
if project.info.use_explicit_senior_debt_sizing_policy:
    sizing_result = SeniorDebtSizingEngine.compute(policy, dscr_policy)
    # wire to SeniorDebtEngine
else:
    # use existing senior_sculpting.py behavior
```

---

## 6. `inferred_minimum_dscr = 1.45x` — Important Caveat

PR #97 analysis found that the TUHO Macro!R50 sizing CFADS appears calibrated to maintain a **minimum actual DSCR around 1.45x**.

This is an **inferred economic interpretation**, NOT a proven Excel formula. The actual Excel DSCR varies by period (1.20–1.41), and the 1.45x figure is the floor observed across the model life.

Treating 1.45x as an explicit design target would require verifying that all periods meet this constraint — which has NOT been proven in the Excel.

**Policy:** `inferred_minimum_dscr = 1.45` is recorded as metadata in `SeniorDebtSizingPolicy` for transparency. It is NOT used in any computation in this branch.

---

## 7. `DERIVE_FROM_MINIMUM_DSCR` — Future Mode

The `DERIVE_FROM_MINIMUM_DSCR` mode would compute sizing CFADS as:

```
sizing_cfads[t] = senior_debt_service_capacity[t] × minimum_dscr[t]
```

where `senior_debt_service_capacity[t]` is derived from available cash flow and the model's debt sculpting rules.

**Status:** NOT implemented. `SeniorDebtSizingEngine.compute()` raises `ValueError("not yet implemented")` if this mode is selected. A test (`TestSizingEngineDeriveMode.test_derive_mode_raises_error`) confirms this safe behavior.

---

## 8. TUHO Integration

For TUHO Excel parity:

```python
# From PR #97: Macro!R50 total = 204,669 kEUR
policy = SeniorDebtSizingPolicy(
    project_name="TUHO",
    sizing_mode=SizingMode.EXPLICIT_CFADS,
    sizing_cfads_keur_by_period=extract_from_macro_r50(),  # 63 values
    source_cell="Macro!R50",
    inferred_minimum_dscr=1.45,
)

dscr_policy = SeniorDebtDSCRPolicy(
    target_dscr_by_period=(1.20,) * 25 + (1.41,) * 38,
    ppa_dscr=1.20,
    merchant_dscr=1.41,
    switch_period=26,
)

result = SeniorDebtSizingEngine.compute(policy, dscr_policy)
# result.debt_service_capacity_keur_by_period[0] ≈ 2190 kEUR (P1, PPA)
```

---

## 9. Separation from SeniorDebtEngine

`SeniorDebtSizingPolicy` answers: **"how much debt can we service?"**

`SeniorDebtEngine` (designed in PR #100) answers: **"what is the actual debt service schedule, interest, and closing balance?"**

The sizing engine does NOT compute:
- Interest (done by SeniorDebtEngine)
- Principal repayment schedule (done by SeniorDebtEngine)
- Closing balance (done by SeniorDebtEngine)
- Actual DSCR (done by SeniorDebtEngine)
- Post-senior cash for SHL (done by SeniorDebtEngine)
- Tax (done by TaxEngine)
- R99/R102 gates (BLOCKED)

---

## 10. R99/R102 Status

**BLOCKED** — this module does not compute distribution gates. The sizing engine only determines debt capacity; the actual distribution logic remains unchanged.

---

## 11. Acceptance Criteria

- [x] `domain/senior_debt_sizing/` module created
- [x] `SeniorDebtSizingPolicy` with `EXPLICIT_CFADS` mode implemented
- [x] `SeniorDebtDSCRPolicy` with dual PPA/merchant regime support
- [x] `DERIVE_FROM_MINIMUM_DSCR` raises `NotImplementedError` (safe stub)
- [x] `SeniorDebtSizingEngine.compute()` returns `SeniorDebtSizingResult`
- [x] 11 tests pass
- [x] Existing 38 tests (SHL engine) pass
- [x] No runtime flag wired (pure domain code)
- [x] `inferred_minimum_dscr = 1.45` documented as inferred, not computed
- [x] No R99/R102 promotion
- [x] R99/R102 remains BLOCKED
- [x] No changes to app/waterfall_core.py
- [x] No changes to ProjectInfo factory

---

*Document version: 1.0 — 2026-05-19*