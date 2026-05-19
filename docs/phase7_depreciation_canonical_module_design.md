# Phase 7 — Depreciation Canonical Module Design

> **Status:** DESIGN ONLY — no runtime implementation  
> **Branch:** `phase7-depreciation-canonical-module-design`  
> **Merged PRs:** #97 (senior debt source map), #98 (SHL cash sweep source map), #99 (SHL canonical design), #100 (senior debt canonical design), #101 (SHL metric reconciliation)  

---

## 1. Executive Summary

Depreciation bridges EBITDA → EBT in the model income statement. It is a **non-cash expense** that reduces taxable income without affecting cash flow. Unlike debt service or SHL, depreciation does not appear in the cash flow waterfall — it lives in the P&L layer and feeds tax and distribution calculations.

This design document proposes a canonical `domain/depreciation/` module that:

1. **Owns** depreciation schedules per asset class, total per-period depreciation, and accumulated depreciation
2. **Does not** compute cash flows, tax, distribution, or sponsor IRR — only exposes outputs consumed by those modules
3. **Supports** multiple asset classes with independent depreciation lives and methods (straight-line, declining balance)
4. **Consumes** CapEx inputs and produces P&L depreciation expense and tax-deductible depreciation
5. **Maintains** R99/R102 as BLOCKED

---

## 2. TUHO Depreciation Structure

### 2.1 Depreciation source cells

| Cell / Row | Description | Value (per period, TUHO) |
|-----------|-------------|--------------------------:|
| `Dep!R30` | Total depreciation = `SUM(R7:R28)` | ~1,845–1,876 kEUR/period |
| `Dep!R7:R28` | Individual asset class depreciations | various |
| `Dep!R4` | Operating period index | 0–30 semiannual |
| `Dep!R31` | Unlevered depreciation (post-interest, for DSCR) | ~1,753–1,782 kEUR |
| `P&L!R13` | P&L depreciation expense | 1,845 kEUR (period 2) |

### 2.2 Depreciation schedule by asset class

The `Dep` sheet contains **22 asset class rows** (R7–R28), each representing a different category of the wind farm CAPEX:

| Row | Asset Class | Life (years) | Dep Method |
|-----|------------|-------------|------------|
| R7 | Wind Turbines | 20 | straight-line |
| R8 | Electrical BOP | 20 | straight-line |
| R9 | Civil BOP | 20 | straight-line |
| R10 | Grid Connection | 20 | straight-line |
| ... | (etc.) | | |

Total CAPEX = **11,028 kEUR** (from `CapEx!B1`)

### 2.3 TUHO depreciation totals

| Metric | Value (kEUR) |
|--------|-------------:|
| Total CAPEX | ~11,028 |
| Annual depreciation (straight-line, 20yr) | ~551/year |
| Semiannual depreciation (operating periods) | ~1,845/period |
| P&L Depreciation (period 2) | 1,845 kEUR |
| Unlevered Depreciation (period 2) | 1,753 kEUR |
| Construction-period depreciation | 0 (depreciation starts at COD) |

---

## 3. Inputs and Source Ownership

### 3.1 Who provides what

| Input | Source | Owned by |
|-------|--------|----------|
| Total CAPEX | `CapEx!B1` or `Dep!B1` | `DepreciationEngine` (read-only) |
| Asset class CAPEX breakdown | `Dep!R7:R28` / `CapEx!R4:R29` | `DepreciationEngine` (read-only) |
| Depreciation lives (years) | `Dep!D9` (e.g., 30 years) | `DepreciationEngine` (read-only) |
| Depreciation method | `straight-line` (TUHO) or declining balance | `DepreciationEngine` (config) |
| Operating period index | `CF!R3` (semiannual op_idx) | `DepreciationEngine` (read-only) |
| Construction period flag | `CF!R4` or `Dep!R4` | `DepreciationEngine` (read-only) |

### 3.2 Inputs dataclass

```python
@dataclass(frozen=True)
class DepreciationPeriodInput:
    """Canonical input for one semiannual period."""
    period_index: int
    operating_period_index: int              # CF!R3, semiannual op_idx (0–30)
    is_construction: bool                   # True for construction periods (no depreciation)
    asset_class_capex_keur: Tuple[float, ...]  # CAPEX per asset class
    asset_class_lives_years: Tuple[int, ...]   # depreciation life per asset class
    asset_class_method: str = "straight-line"   # TUHO: straight-line only


@dataclass(frozen=True)
class DepreciationEngineInputs:
    """Full model inputs for the Depreciation engine."""
    project_name: str
    period_count: int
    period_inputs: Tuple[DepreciationPeriodInput, ...]
    total_capex_keur: float
    asset_class_names: Tuple[str, ...]
    asset_class_capex_keur: Tuple[float, ...]
    asset_class_lives_years: Tuple[int, ...]
    asset_class_methods: Tuple[str, ...]
    start_period_index: int = 2             # first operating period (P2 = COD)
    construction_period_count: int = 1       # P1 is construction
```

---

## 4. Depreciation Methods

### 4.1 Straight-line (TUHO default)

```
period_depreciation = capex / life_years / periods_per_year
```

For TUHO semiannual periods: `period_depr = capex / 20 / 2 = capex / 40`

### 4.2 Declining balance (future)

```
period_depreciation = opening_book_value × declining_rate
```

Where `declining_rate = 2 / life_years` for double-declining balance (future extension).

### 4.3 Units and consistency

- CAPEX entered in kEUR
- Lives entered in years
- Depreciation output in kEUR per semiannual period
- Consistent with CapEx sheet structure (per MW, per category)

---

## 5. Outputs and Audit Rows

### 5.1 Outputs dataclass

```python
@dataclass(frozen=True)
class DepreciationPeriodResult:
    """Canonical output for one semiannual period."""
    period_index: int
    operating_period_index: int
    is_construction: bool                    # True = no depreciation
    # Per asset class
    asset_class_depreciation_keur: Tuple[float, ...]
    asset_class_book_value_keur: Tuple[float, ...]
    asset_class_accumulated_depr_keur: Tuple[float, ...]
    # Totals
    total_depreciation_keur: float            # sum of all asset class depreciations
    total_book_value_keur: float              # remaining book value
    total_accumulated_depr_keur: float        # cumulative depreciation to date
    unlevered_depreciation_keur: float        # post-interest (Dep!R31) for DSCR
    # P&L inputs
    pnl_depreciation_keur: float             # goes to P&L!R13
    tax_deductible_depr_keur: float           # for TaxEngine


@dataclass(frozen=True)
class DepreciationEngineResult:
    """Full Depreciation engine result across all periods."""
    project_name: str
    period_count: int
    period_results: Tuple[DepreciationPeriodResult, ...]
    # Totals
    total_depreciation_keur: float
    total_capex_keur: float
    fully_depreciated_period_index: Optional[int]  # when book value → 0
    audit_table: Tuple["DepreciationAuditRow", ...]
```

### 5.2 Audit row dataclass

```python
@dataclass(frozen=True)
class DepreciationAuditRow:
    """One row of the Depreciation audit export."""
    period_index: int
    excel_col: str
    operating_period_index: int
    is_construction: bool
    asset_class_names: Tuple[str, ...]
    asset_class_capex_keur: Tuple[float, ...]
    asset_class_depr_keur: Tuple[float, ...]
    asset_class_book_value_keur: Tuple[float, ...]
    asset_class_accumulated_depr_keur: Tuple[float, ...]
    total_depreciation_keur: float
    total_book_value_keur: float
    total_accumulated_depr_keur: float
    unlevered_depr_keur: float
    pnl_depr_keur: float
    warnings: Tuple[str, ...]
```

---

## 6. Depreciation → P&L → Tax → Distribution Chain

### 6.1 The chain

```
DepreciationEngine
  → pnl_depreciation_keur[t] → P&L (reduces EBT)
  → tax_deductible_depr_keur[t] → TaxEngine (reduces taxable income)
  → unlevered_depr_keur[t] → CFADS / DSCR (added back as non-cash)
```

### 6.2 Unlevered depreciation (Dep!R31)

`Dep!R31 = Unlevered Depreciation` is the depreciation figure used in CFADS calculations to add back the non-cash charge. It differs from P&L depreciation because it excludes depreciation attributable to financing activities (lease accounting, etc.).

For TUHO: `Unlevered Depreciation ≈ P&L Depreciation × adjustment factor`.

### 6.3 P&L integration

```
P&L row 13 (Depreciation) = DepreciationEngine.pnl_depreciation_keur[t]
```

The P&L then computes:
```
EBITDA = Revenue - OpEx - Admin - Other
EBT = EBITDA - Depreciation - Interest
```

### 6.4 Tax integration

```python
# TaxEngine receives tax_deductible_depr_keur[t] from DepreciationEngine
taxable_income[t] = pnl_ebt[t] + tax_deductible_depr_keur[t]
```

Note: In many jurisdictions, tax depreciation differs from P&L depreciation (accelerated amortization, bonus depreciation, etc.). The `DepreciationEngine` should expose both P&L and tax depreciation separately.

---

## 7. Canonical Calculation Order

For each period `t`:

```
1.  IF is_construction[t]:
        total_depreciation[t] = 0
    ELSE:
        FOR each asset_class i:
            period_depr_i[t] = capex_i / life_years_i / 2  (semiannual)
            book_value_i[t] = capex_i - accumulated_depr_i[t]
            accumulated_depr_i[t] += period_depr_i[t]
        total_depreciation[t] = SUM(period_depr_i[t])

2.  unlevered_depr[t] = total_depreciation[t] × unlevered_factor
    # For TUHO, unlevered ≈ total (no complex lease adjustments)

3.  pnl_depr[t] = total_depreciation[t]

4.  tax_deductible_depr[t] = total_depreciation[t]
    # Future: separate tax depreciation schedule from P&L depreciation

5.  book_value_total[t] = SUM(book_value_i[t])
    accumulated_depr_total[t] = SUM(accumulated_depr_i[t])

6.  IF book_value_total[t] < 0.01:
        fully_depreciated_period_index = t
```

---

## 8. Proposed `domain/depreciation/` Module Layout

```
domain/depreciation/
├── __init__.py          # Exports: DepreciationEngine, inputs, results, audit
├── inputs.py            # DepreciationPeriodInput, DepreciationEngineInputs
├── result.py            # DepreciationPeriodResult, DepreciationEngineResult, DepreciationAuditRow
├── engine.py            # DepreciationEngine.compute(inputs) -> result
└── audit.py             # to_audit_dataframe(), to_csv(), to_model_summary()
```

Note: `sizing_policy.py` and `rate_schedule.py` are not needed for depreciation — these concepts belong to the debt modules.

---

## 9. Validation and TUHO Baseline

### 9.1 TUHO baseline assertions

| Assertion | Expected |
|-----------|----------|
| Period 2 (col H) P&L depreciation | 1,845 kEUR |
| Period 3 (col I) P&L depreciation | 1,876 kEUR |
| Total per-period depreciation (operating) | ~1,845–1,876 kEUR |
| Dep!R30 construction period (col G) | 0 |
| Total CAPEX | ~11,028 kEUR |
| Fully depreciated period | after period 40 (20 years × 2) |

### 9.2 Validation against Dep sheet

```python
def validate_against_dep_sheet(depr_result: DepreciationEngineResult,
                               dep_wb: openpyxl.Workbook) -> None:
    """Regress DepreciationEngineResult against Dep sheet."""
    dep = dep_wb["Dep"]
    for col in range(8, 66):
        expected = dep.cell(row=30, column=col).value
        actual = depr_result.period_results[col - 8].total_depreciation_keur
        assert_close(actual, expected, tol=0.1)
```

---

## 10. Oborovo Readiness

### 10.1 Oborovo status

Oborovo Excel workbook was **not available** in the workspace for this branch. The depreciation schedule for Oborovo (solar, 53.63 MW) is likely different from TUHO (wind, 72 MW):

- Different CAPEX per MW
- Different asset class mix (solar panels vs wind turbines)
- Possibly different depreciation lives
- Solar may use different tax depreciation rules (ITC, MACRS)

### 10.2 Required action before Oborovo integration

1. Obtain Oborovo Excel workbook
2. Extract depreciation rows from `Dep` sheet (or equivalent)
3. Verify total CAPEX, asset class breakdown, depreciation method
4. Confirm construction-period treatment (solar COD timing)
5. Write `reports/phase7_oborovo_depreciation_extraction.csv`

---

## 11. Migration Plan from Current Depreciation Logic

### 11.1 Current baseline

There is **no canonical depreciation module** in the current Python codebase. Depreciation may be:
- Hardcoded in fixtures
- Implicit in P&L sheet computation
- Not separately validated

The `Dep` sheet in Excel is the source of truth. Python currently reads the `Dep` sheet via openpyxl but may not have a dedicated depreciation engine.

### 11.2 Migration steps

```
Current: implicit / fixture-bound → Canonical:
─────────────────────────────────────────────────────────────
Dep sheet read via openpyxl    → domain/depreciation/engine.py
No separation of P&L/tax depr  → P&L depr + tax depr separate outputs
No audit export               → audit.py with to_csv(), to_dataframe()
No asset class detail         → per-asset-class results in DepreciationPeriodResult
```

---

## 12. Integration Boundaries

### 12.1 Clear module boundaries

```
DepreciationEngine → pnl_depr → P&L → EBT → TaxEngine
                → tax_depr → TaxEngine
                → unlevered_depr → CFADS (add-back)
                → accumulated_depr → Balance Sheet
```

**DepreciationEngine does NOT call P&L, TaxEngine, or Balance Sheet.** It only exposes outputs.

### 12.2 Balance sheet integration

```python
# Balance sheet receives accumulated depreciation from DepreciationEngine
accumulated_depr_keur[t] = period_results[t].total_accumulated_depr_keur
book_value_keur[t] = total_capex_keur - accumulated_depr_keur[t]
```

---

## 13. Tax Deductibility Considerations

### 13.1 P&L vs Tax depreciation

In many jurisdictions (including Croatia and BIH for renewable energy):
- **P&L depreciation**: straight-line over useful life
- **Tax depreciation**: may be accelerated (e.g., 50% bonus depreciation in year 1, or MACRS tables)

For TUHO, the model may use straight-line for both P&L and tax. The `DepreciationEngine` should expose both:
- `pnl_depreciation_keur` for P&L
- `tax_deductible_depreciation_keur` for TaxEngine

```python
@dataclass(frozen=True)
class DepreciationTaxInterface:
    """Config for how depreciation feeds the tax engine."""
    tax_depr_method: str = "straight-line"   # or "accelerated", "MACRS"
    tax_lives_years: Tuple[int, ...]          # may differ from P&L lives
    bonus_depr_rate: float = 0.0              # e.g., 0.5 for 50% bonus first year
    allow_temporary_difference: bool = True   # P&L ≠ tax is allowed
```

---

## 14. Multi-Asset-Class Structure

### 14.1 TUHO asset classes

From `Dep!R7:R28`, TUHO has 22 asset classes covering:
- Wind turbines (main generation equipment)
- Electrical balance of plant
- Civil balance of plant
- Grid connection
- Monitoring and telecom
- Buildings and infrastructure
- Special vehicles and equipment

### 14.2 Per-asset-class tracking

Each `DepreciationPeriodResult` includes per-asset-class:
- `asset_class_depreciation_keur`
- `asset_class_book_value_keur`
- `asset_class_accumulated_depr_keur`

This allows the model to:
- Retire individual assets at different times
- Track lease vs owned assets separately
- Apply different depreciation methods per asset class (future)

---

## 15. R99/R102 Status

BLOCKED — no changes to distribution logic in this design branch.

---

## 16. Forbidden Scope / Non-Goals

- **No runtime implementation** of `DepreciationEngine` in this branch
- **No creation** of active `domain/depreciation/*.py` runtime files (only illustrative pseudocode)
- **No changes** to P&L sheet logic
- **No changes** to CapEx sheet logic
- **No changes** to tax module
- **No changes** to distribution account runtime
- **No R99/R102 promotion**
- **No flags** added to project factory
- **No changes** to `app/*` or `app/waterfall_core.py`
- **No scalar plugs**

---

## 17. Acceptance Criteria

- [x] Branch is docs/design/test-only
- [x] No production/runtime files changed
- [x] Depreciation engine owns asset class depreciation, book value, accumulated depreciation
- [x] Canonical inputs: `asset_class_capex_keur`, `asset_class_lives_years`, `asset_class_methods`
- [x] Canonical outputs: `total_depreciation_keur`, `pnl_depreciation_keur`, `tax_deductible_depr_keur`, `unlevered_depr_keur`, `book_value_keur`, `accumulated_depr_keur`
- [x] Depreciation → P&L → Tax → CFADS chain documented
- [x] Straight-line method for TUHO documented
- [x] Multiple asset class structure documented (22 classes in TUHO)
- [x] Oborovo missing extraction documented as open item
- [x] Balance sheet integration (book value, accumulated depreciation) documented
- [x] Tax deductibility interface documented (`DepreciationTaxInterface`)
- [x] Migration plan from current implicit depreciation described
- [x] R99/R102 remains BLOCKED
- [x] All tests pass

---

## 18. Recommended Next Branch

**`phase7-depreciation-source-map`** — extract TUHO depreciation data cell-by-cell and produce a `reports/phase7_tuho_depreciation_extraction.csv` analogous to the senior debt and SHL extraction CSVs. This will validate the depreciation baseline and confirm that the design is grounded in actual Excel values before the canonical module is implemented.

---

*Document version: 1.0 — 2026-05-19*  
*Authors: Phase 7 design branch — cofix + OpenClaw agent*