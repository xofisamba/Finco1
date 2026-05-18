# Phase 6 — Loss Window Design

## Branch
`phase6-loss-window-design`

## Status
**Design / diagnostics / governance. No production code changes.**

---

## 1. What This Branch Does

Creates a consolidated design and decision memo for the loss carryforward window used by the Phase 6 tax bridge. Clarifies the canonical implementation choice among:

- **A.** Croatian legal 5-year carryforward → 10 semiannual periods
- **B.** Excel TUHO 5-period rolling SUMIF behavior
- **C.** Dual-mode support behind explicit policy flag
- **D.** Defer pending external review

Creates:
- `docs/phase6_loss_window_design.md` (this file)

---

## 2. What This Branch Does NOT Do

- ❌ No runtime behavior changes
- ❌ No tax engine implementation changes
- ❌ No changes to `app/waterfall_core.py`, `app/waterfall_runner.py`, `app/project_factories.py`
- ❌ No factory opt-in
- ❌ No R99/R102 promotion
- ❌ No SHL FCF opt-in
- ❌ No scalar plugs or residual adjustments
- ❌ Oborovo remains guarded

---

## 3. Documented Context from Prior Branches

### Loss Rows Do NOT Affect R35
R36–R39 are loss-accounting rows that reduce R41 (Taxable Profit N) only. R35 (Taxable Income) is pure: `R35 = EBIT + Financial Earnings`. The loss window does not affect R35 formula construction.

### R37 Active Only Around yr13 Transition
R37 (Allocated Losses) is active around the year 13 transition where construction-period losses are consumed, then goes to zero for years 14–30.

### R39 Is Zero yr13–30 After Pool Clears
R39 (Carriable Losses) is 0.00 in years 13–30 after the opening loss balance from construction is exhausted. The prior R39 misinterpretation (thinking it carried forward indefinitely) is a known error that must not be recreated.

### Dep R30 Near-Parity Root Cause (PR #84)
Excel uses `capex_i / life_i × leap_frac` (annual rate × leap-year fraction). Engine uses flat `capex_i / (life_i × 2)`. Max diff 3.13 kEUR is a structural convention difference, not missing data. ±5 kEUR is diagnostic-only.

---

## 4. Current Python Loss Engine Behavior

### LossCarryforwardConfig
Defined in `domain/tax/loss_carryforward.py`:

```python
@dataclass(frozen=True)
class LossCarryforwardConfig:
    duration_years: int = 5           # Croatia: 5-year statutory
    periods_per_year: int = 2         # semiannual
    explicit_override_periods: int | None = None  # Excel parity override
    expiry_method: str = "fifo_per_vintage"
    country_template: str = "generic"
    expire_before_use: bool = False    # legacy: False = no expiry (pool survives forever)
```

### Key Config Properties
- `duration_periods = duration_years * periods_per_year` (unless `explicit_override_periods` set)
- `duration_periods = 5 * 2 = 10 periods` (Croatia semiannual)
- `explicit_override_periods = 5` (Excel compatibility mode)

### Python Modes

| Mode | Config | Duration | expire_before_use | CIT total (TUHO) |
|------|---------|----------:|-------------------|-----------------:|
| Legacy generic | `LossCarryforwardConfig()` | indefinite (no expiry) | `False` | ~36,092 kEUR |
| Croatia legal | `duration_years=5, periods_per_year=2` | 10 periods | `True` | ~36,284 kEUR |
| Excel parity | `explicit_override_periods=5` | 5 periods | `True` | ~38,241 kEUR |

### FIFO Per Vintage
Each loss bucket carries its own `expiry_period_index`. Buckets expire at the start of the period `>= expiry_period_index`. FIFO usage: oldest valid buckets consumed first.

### Construction Period Losses
Included in the loss pool. Opening loss balance supported via `opening_loss_keur` parameter to `compute_loss_carryforward_schedule()`.

### R36/R37/R38/R39 Mapping

| Excel Row | Python Field | Meaning |
|----------|-------------|---------|
| R36 | `losses_n_1_keur` | Opening loss balance (prior period carryforward) |
| R37 | `allocated_losses_keur` | Losses consumed against current taxable income |
| R38 | `losses_n_keur` | Closing loss balance after allocation (= new bucket if negative TI) |
| R39 | `carriable_losses_keur` | Same as `losses_n_keur` (carrying forward) |
| R41 | `taxable_profit_after_losses_keur` | R35 − R37 (never negative) |

### Runtime Flag Status
`use_tax_bridge_engine=True` for TUHO-WIND-1 activates Croatia 10-period mode in the runtime tax bridge. Oborovo raises `ValueError` (not yet supported). R99/R102 remain BLOCKED.

---

## 5. Excel TUHO Loss Window Behavior

### Formula Pattern (Reverse-Engineered)
Excel R36 uses a rolling-column SUMIF over the previous 5 spreadsheet columns:

```
R36 = SUMIF(IF(H4 <= $B$36, ..., prev:OFFSET(prev,0,-$B$36+1)), "<0")
$B$36 = 5
```

- Rolls over **5 spreadsheet columns** (5 semiannual periods, 2.5 years)
- Each period's R36 = sum of all negative R35 values in the prior 5 columns
- R37 = `IF(R36 ≤ 0 AND R32 > 0, MIN(ABS(R36), R32), 0)` — consumes opening balance
- R38 = `MIN(R37 + R36, 0)` — new loss for the period
- R39 = rolling carriable balance

### Key Questions

| Question | Answer |
|----------|--------|
| Does Excel use 5 periods or 5 years? | **5 periods** (2.5 calendar years semiannual) |
| Does Excel use a rolling SUMIF? | **Yes** — 5-column lookback |
| Does the rolling window include H1/H2 separately? | **Yes** — each column is one semiannual period |
| Does it expire construction losses differently? | **No** — same rolling window applies |
| Is the Excel behavior a workbook-specific shortcut? | **Likely yes** — 5 columns is a convention, not a named policy |

### Excel vs Python CIT Impact

| Scenario | Window | CIT total | Delta |
|---------|--------:|----------:|------:|
| Excel compatibility | 5 periods | 38,240.9 kEUR | baseline |
| Croatia tax-law-correct | 10 periods | 37,580.2 kEUR | −660.7 kEUR |

The 660.7 kEUR difference is entirely explained by 5-period vs 10-period expiry: in the 10-period mode, losses expire after 5 years and are unavailable for years 6–10 of operation, while in the 5-period mode they expire after 2.5 years.

### Why R39 Is Zero yr13–30
After year 13 H1/H2, the construction-period opening loss balance is fully consumed. R39 (carriable losses) becomes 0.00 because all prior losses have been used up. Excel does not create a new carryforward until a period generates new losses (R38 < 0), and TUHO years 13–30 generate positive taxable income every period.

---

## 6. Comparison Table

| Dimension | Python Legacy (generic) | Python Croatia (flag-on) | Excel TUHO | Recommended |
|----------|------------------------|-------------------------|-----------|-------------|
| Carryforward period | Indefinite (no expiry) | **10 periods** (5yr × 2) | **5 periods** (2.5yr) | Croatia legal (A) |
| Period granularity | Semiannual | Semiannual | Semiannual (5 columns) | Semiannual |
| Expiry semantics | Never expires | **expire_before_use** | FIFO per 5-column SUMIF | expire_before_use |
| Construction losses | Included | Included | Included via opening balance | Included |
| Opening balance | Supported | Supported | Supported (yr13 opening loss) | Supported |
| R37 allocation trigger | R36≤0 AND R32>0 | Same | Same | Same |
| Flag/runtime status | `use_tax_bridge_engine=False` default | `use_tax_bridge_engine=True` | N/A | Keep as canonical |
| CIT yr13–30 | ~36,092 kEUR | ~36,284 kEUR | ~38,241 kEUR | Python closer to Excel with Croatia mode |

---

## 7. Canonical Decision

### Recommended: **Option A — Preserve Croatian legal 5-year × 2 semiannual = 10-period vintage model as canonical.**

**Rationale:**

1. **Legal correctness**: Croatian corporate tax law provides for a 5-year loss carryforward. Converting to semiannual periods (10 periods) is the legally correct interpretation. The Excel 5-period behavior appears to be a workbook-specific convention, not an intentional tax policy.

2. **Evidence against Option B**: The Excel behavior (5 columns) is a literal column-count interpretation. In a semiannual model, 5 columns = 2.5 years, which does not match the statutory 5-year window.

3. **Evidence against Option D**: The decision can be made now based on existing legal analysis. Deferring adds delay without new information.

4. **Preserve Excel parity as non-default**: Excel compatibility mode (`explicit_override_periods=5`) is already implemented and can be used for diagnostics/regression testing without making it the canonical behavior.

5. **Preference constraint satisfied**: "Avoid TUHO-only hardcoded behavior. Prefer explicit policy-mode configuration if both legal and Excel parity modes need support." The Croatia mode is the canonical default; Excel mode is explicit and non-default.

### Why Not Option C (Dual-Mode)?
Dual-mode would add complexity (two code paths, two test suites) for a ~660 kEUR CIT difference. The Croatian legal interpretation is the correct canonical behavior. Excel parity mode is already available as an explicit override for diagnostic purposes only.

### Why Not Option D (Defer)?
The legal analysis is complete. The implementation exists. The only remaining work is confirming that the 10-period Croatia mode is the correct canonical default and ensuring it is wired as such. Deferring does not improve the decision.

---

## 8. Future Implementation Design (If Needed)

If future work requires dual-mode support, the design is:

```python
@dataclass(frozen=True)
class LossCarryforwardConfig:
    # Core fields
    duration_years: int = 5
    periods_per_year: int = 2
    explicit_override_periods: int | None = None  # non-default Excel parity
    expiry_method: str = "fifo_per_vintage"
    expire_before_use: bool = True
    
    # Policy mode (new)
    policy_mode: str = "legal_vintage"  # | "excel_rolling"
    
    # Computed
    @property
    def duration_periods(self) -> int:
        if self.policy_mode == "excel_rolling" and self.explicit_override_periods is None:
            return 5  # Excel 5-period rolling (non-default)
        return self.duration_years * self.periods_per_year
```

**Current default behavior**: `policy_mode="legal_vintage"` (10 periods semiannual)  
**Non-default Excel parity**: `policy_mode="excel_rolling"` or `explicit_override_periods=5`

---

## 9. R99/R102 Gate Impact

**R99/R102 remain BLOCKED.** This branch does not change that.

Loss-window design does NOT unblock R99. R99 design is only unblocked after:
1. Useful-life canonical decision
2. Loss-window canonical decision (this branch)
3. Residual recheck
4. External sign-off

Loss-window design is a prerequisite, not an unblocking event on its own.

---

## 10. Relationship to Prior Branches

| Branch | Key Finding | Status |
|--------|------------|--------|
| `phase6-loss-carryforward-rolling-engine` | Config model with `explicit_override_periods` | Merged |
| `phase6-loss-engine-vintage-tracking` | FIFO per vintage with bucket expiry | Merged |
| `phase6-loss-engine-runtime-flag` | Croatia 10-period mode wired to `use_tax_bridge_engine=True` | Merged |
| `phase6-tax-validation-pack` | Loss window CIT delta ~660 kEUR documented | Merged |
| `phase6-r35-formula-inspection` | R36–R39 do not affect R35; R39 zero after yr13 | Merged |
| `phase6-y13-30-residual-attribution` | R39 zero after pool clears; +4,106 kEUR plateau = R36, not R39 | Merged |

---

## 11. Deliverables Created

This branch creates only this document. No runtime code, no CSV report, no test changes.

- `docs/phase6_loss_window_design.md`

---

## 12. Tests

No new tests in this branch. Existing loss engine and tax bridge tests pass:

```
tests/test_loss_engine_runtime_flag.py
tests/test_tax_bridge_consumes_r35_sources.py
tests/test_r67_full_calibration_validation.py
tests/test_r67_yrs13to30_residual.py
tests/test_cit_h2_annual_trigger.py
```

**94 passed, 1 xfailed** (combined suite, unchanged)

---

## 13. Recommended Next Branch

**`phase6-depreciation-engine-runtime-adapter`** (Stage 3)

Prerequisites before Stage 3:
- Useful-life canonical decision
- Loss-window canonical decision (this branch — complete)
- Residual recheck
- External sign-off

OR, if useful-life decision is also pending: **`phase6-useful-life-canonical-design`**

**Do not proceed to Stage 3 until both canonical decisions are resolved.**