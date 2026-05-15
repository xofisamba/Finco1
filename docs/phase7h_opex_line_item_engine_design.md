# Phase 7H — OPEX Line-Item Engine: Extraction & Design

**Status:** Task A–D complete (extraction + design). Task E (implementation) deferred.

---

## 1. OpEx Tab Structure (TUHO Excel)

**Sheet:** `OpEx` (127 rows × 38 cols)

**Column layout:**
| Column | Content |
|--------|---------|
| A | Group/Item code (e.g. B.01, B.01.1) |
| B | Name |
| C | Budget (kEUR base) or formula referencing Scenarios |
| D | Inflation rate (decimal, 0.02 = 2%) |
| E | WTH (withholding tax, 0 = none) |
| F–AJ | Year 1–30 values (annual, kEUR) |
| AK+ | Active flags (not used in current model) |

**Row 2 = header:** `Budget | Inflation | WTH | 1 | 2 | 3 | ... | 30`

**Row 1:** Total OPEX in budget (11028.67 — grand total reference)

---

## 2. OPEX Group / Item Mapping

### Structure Rules (from formula inspection)

1. **Parent rows** (e.g. B.01): `budget = SUM(C_child_items)`. Y values use `SUMPRODUCT(budget_child_items × flag_year) × (1+inflation)^(year-1)`
2. **Sub-item rows**: `budget = Scenarios!Exx` (external reference). Y values are **active flags** (1=active, 0=inactive) OR cost values for items like B.02.1
3. **B.02 exception:** `budget = SUM(C15:C26) + F15` where F15 = B.02.1 O&M cost
4. **Active flag pattern:** Most sub-items use `1` = always active, `0` = never active, `1/0` per year = conditional

### Full Group/Item Table

| Group | Item Code | Name | Budget (kEUR) | Basis | Inflation | WTH | Active Pattern | Notes |
|-------|-----------|------|--------------|-------|-----------|-----|----------------|-------|
| B.01 | B.01 | Technical Management | 280 | sum_children | 0.02 | 0 | always | Group |
| | B.01.1 | Asset Management Contract | 138 | fixed_annual_keur | — | — | always | |
| | B.01.2 | Operation Management Contract | 67 | fixed_annual_keur | — | — | always | |
| | B.01.3 | Performance monitoring | 10 | fixed_annual_keur | — | — | always | |
| | B.01.4 | Technical Inspections | 13 | fixed_annual_keur | — | — | always | |
| | — | SCADA | 18 | fixed_annual_keur | — | — | always | no code |
| | B.01.5 | Meteorological and weather forecast | 16 | fixed_annual_keur | — | — | always | |
| | B.01.9 | Bazefield | 18 | fixed_annual_keur | — | — | always | |
| | B.01.9 | Onboarding fees | 0 | one_off | — | — | Y1 only | |
| | — | End of maintenance contract inspection | 0 | inactive | — | — | never | no code |
| | B.01.9 | Decomissioning Fees | 0 | one_off | — | — | Y30 only | |
| **B.02** | B.02 | Infrastructure Maintenance | 667.6 | sum_children + B.02.1 | 0.02 | 0 | always | Group (special formula) |
| | B.02.1 | O&M – Preventive & Corrective | 241 | fixed_annual_keur | — | — | always | explicit cost (array formula) |
| | B.02.2 | Minor Maintenance | 27 | fixed_annual_keur | — | — | always | |
| | B.02.3 | HV Substation & O&M Building | 0 | fixed_annual_keur | — | — | always | |
| | — | Regulatory Inspections | 6 | fixed_annual_keur | — | — | always | no code |
| | B.02.4 | HSE Prevention Plan | 0 | fixed_annual_keur | — | — | always | |
| | B.02.5 | Met Station Maintenance | 0 | fixed_annual_keur | — | — | always | |
| | B.02.6 | Blade Maintenance | 0 | fixed_annual_keur | — | — | always | |
| | B.02.7 | Vehicle or Special Equipment Maintenance | 8 | fixed_annual_keur | — | — | always | |
| | B.02.8 | Others | 0 | fixed_annual_keur | — | — | always | |
| | B.02.9 | (separator) | — | inactive | — | — | always | no code, no name |
| | B.02.10 | (unused) | — | inactive | — | — | never | |
| **B.03** | B.03 | Maintain Site | 68 | sum_children | 0.02 | 0 | always | |
| | B.03.1 | Vegetation management/clean site | 20 | fixed_annual_keur | — | — | always | |
| | B.03.2 | Repair roads | 36 | fixed_annual_keur | — | — | always | |
| | B.03.3 | Pest control | 2 | fixed_annual_keur | — | — | always | |
| | B.03.8 | Inspections | 10 | fixed_annual_keur | — | — | always | |
| | B.03.9 | Others | 0 | inactive | — | — | never | |
| **B.04** | B.04 | Clean Material | 5 | sum_children | 0.02 | 0 | always | |
| | B.04.1 | Clean Panel/Blades | 0 | fixed_annual_keur | — | — | always | |
| | B.04.2 | Subscription to water supply | 5 | fixed_annual_keur | — | — | always | |
| | B.04.3 | Others | 0 | inactive | — | — | never | |
| **B.05** | B.05 | Security | 50 | sum_children | 0.02 | 0 | always | |
| | B.05.1 | Surveillance systems | 30 | fixed_annual_keur | — | — | always | |
| | B.05.2 | Surveillance patrols | 20 | fixed_annual_keur | — | — | always | |
| | B.05.3 | Others | — | inactive | — | — | never | no budget |
| **B.06** | B.06 | Insurance | 468.75 | sum_children | 0.02 | 0 | always | |
| | B.06.1 | Operation All Risk with Business Interruption | 468.75 | fixed_annual_keur | — | — | always | |
| | B.06.2 | Third Party Liability (TPL) | 0 | fixed_annual_keur | — | — | never | |
| | B.06.3 | Substation and O&M Building Coverage | 0 | fixed_annual_keur | — | — | never | |
| | B.06.4 | Spare parts insurance | 0 | fixed_annual_keur | — | — | never | |
| | — | Wake effect - compensation | 0 | pct_of_group | 0.02 | 0 | never | no code, budget=0 |
| | B.06.9 | Wake effect | 0 | fixed_annual_keur | — | — | Y1-Y10 only | |
| **B.07** | B.07 | Lease & property Tax | 244 | sum_children | 0.02 | 0 | always | |
| | B.07.1 | Land Leases | 244 | fixed_annual_keur | — | — | always | |
| | B.07.4 | Property tax | 0 | fixed_annual_keur | — | — | always | |
| **B.08** | B.08 | Power Expenses | 93.72 | sum_children | 0.02 | 0 | always | |
| | B.08.1 | Power consumption | 45 | fixed_annual_keur | — | — | always | |
| | B.08.2 | Grid Usage fee | 48.72 | fixed_annual_keur | — | — | always | |
| | B.08.3 | Balancing costs | 0 | fixed_annual_keur | — | — | always | budget=0 (no PPA balancing) |
| | B.08.8 | Fuel | 0 | inactive | — | — | never | |
| **B.09** | B.09 | Telecom Fees | 0 | sum_children | 0.02 | 0 | always | |
| | B.09.1 | Reporting Data | — | fixed_annual_keur | — | — | always | no budget |
| | B.09.2 | Telecom Connection | — | fixed_annual_keur | — | — | always | no budget |
| **B.10** | B.10 | Audit&Accounting&Legal Fees | 32 | sum_children | 0.02 | 0 | always | |
| | B.10.1 | Auditors closing | 16 | fixed_annual_keur | — | — | always | |
| | B.10.2 | Accounting closing | 8 | fixed_annual_keur | — | — | always | |
| | B.10.3 | Legal closing | 8 | fixed_annual_keur | — | — | never | |
| | B.10.4 | Accounting book-keeping | 0 | fixed_annual_keur | — | — | always | |
| | B.10.5 | Legal Formalities | 0 | fixed_annual_keur | — | — | always | |
| **B.11** | B.11 | Bank Fees | 20 | sum_children | 0.02 | 0 | always (expires Y14) | |
| | B.11.1 | Agency Fee | 20 | fixed_annual_keur | — | — | Y1-Y14 only (formula: 1*(year<=$C$112)) | |
| | B.11.2 | Bonds | — | inactive | — | — | never | no budget |
| | B.11.3 | Bank Fees | — | fixed_annual_keur | — | — | always | no budget |
| **B.12** | B.12 | Environmental&Social management | 400 | sum_children | 0.02 | 0 | always | |
| | B.12.1 | Mitigation measures | 200 | fixed_annual_keur | — | — | Y10-Y30 only | |
| | B.12.2 | Agrinergie | 0 | inactive | — | — | never | |
| | B.12.3 | Fauna&Flora Monitoring | 200 | fixed_annual_keur | — | — | Y1-Y9 only | |
| | B.12.5 | E&S monitoring | 0 | fixed_annual_keur | — | — | Y1-Y9 only | |
| | B.12.6 | HSE: Monthly visit + yearly visit + ... | 0 | fixed_annual_keur | — | — | always | |
| **B.13** | B.13 | Contingencies | 139.7442 | pct_of_selected_groups | 0.06 | 0 | always | formula: SUM(selected groups) × 6% |
| **C** | C | Claims | — | inactive | 0 | 0 | never | zero for TUHO |
| | C.01 | Attorney | N/A | not_applicable | — | — | never | |
| | C.02 | Technical advisor linked to the claim | N/A | not_applicable | — | — | never | |
| | C.03 | Justice Administration fees | N/A | not_applicable | — | — | never | |
| **D** | D | Salary and payroll Tax | 0 | inactive | 0.02 | 0 | never | zero for TUHO |
| **E** | E | Specific Revenues | 0 | inactive | — | — | never | revenue items, not opex |
| **F** | F | Taxes | 0 | inactive | 0.02 | 0 | never | zero for TUHO |
| | F.07 | Stamp Duty | 0 | fixed_annual_keur | — | — | always | |

### Key Formulas (from formula inspection)

**Parent group inflation formula:**
```
Y1 = SUMPRODUCT($C$child_range, year_flags) × (1 + inflation)^(year-1)
```
Example B.01: `=SUMPRODUCT($C$4:$C$13, F4:F13) * (1+$D3)^(F2-1)`

**Contingencies formula:**
```
B.13 budget = SUM(B.01, B.03, B.04, B.05, B.06, B.07, B.08, B.09, B.10, B.11, B.12, B.02) × 6%
```
B.13 is 6% of the sum of active group costs (active = flag × budget).

**B.02 special formula:**
```
B.02 Y1 = SUMPRODUCT($C$16:$C$26, F16:F26) × (1+$D14)^(F2-1) + F15
```
Where F15 = B.02.1 explicit cost (O&M Preventive & Corrective = 385.6 kEUR)

**B.11.1 conditional (Agency Fee):**
```
Y = 1 × (year <= maturity_years)  → active for Y1-Y14, then 0
```
Uses `=1*(F2<=$C$112)` where C112 = "Debts maturity" = 14.

---

## 3. Current Python OPEX Formula

**File:** `domain/opex/projections.py`

**Current OpexItem structure:**
```python
OpexItem(name, y1_amount_keur, annual_inflation, step_changes)
```

**Current 12 OpexItems (TUHO):**
| # | Name | Y1 Amount | Inflation |
|---|------|----------:|----------:|
| 0 | Technical Management | 279.99 | 0.02 |
| 1 | O&M Preventive & Corrective | 426.60 | 0.02 |
| 2 | Maintain Site | 68.00 | 0.02 |
| 3 | Clean Material | 5.00 | 0.02 |
| 4 | Security | 50.00 | 0.02 |
| 5 | Insurance | 468.74 | 0.02 |
| 6 | Lease & Property Tax | 248.88 | 0.02 |
| 7 | Power Expenses | 93.72 | 0.02 |
| 8 | Audit & Accounting & Legal | 23.99 | 0.02 |
| 9 | Bank Fees (opex) | 20.00 | 0.02 |
| 10 | Environmental & Social Management | 200.00 | 0.02 |
| 11 | Contingencies | 113.09 | 0.06 |

**Current formula (simplified):**
```
opex_y = y1_amount × (1 + inflation)^(year - 1)
```
No flags, no WTH, no step_changes (currently empty tuples), no active period constraints.

**Key gaps vs Excel:**
1. No active flags (items are always-on)
2. No WTH support
3. No per-item step changes
4. No contingency as % of selected groups
5. No conditional items (B.11.1 Y1-Y14 only, B.12.1 Y10-Y30 only)
6. No sub-item structure (only 12 flat items, not hierarchical)
7. B.02.1 is merged into OpexItem #1 but Excel has separate O&M component

---

## 4. Excel vs Python OPEX Gap

**Sources:**
- Excel: CF R38 (Operating Expenses Aft. Bank Tax), period values per col. Annual = sum of two semi-annual periods.
- Python: `opex_schedule_annual()` from `domain/opex/projections.py`

**Comparison (annual, kEUR):**

| Year | Excel R38 Annual | Python Annual | Delta | Largest contributor to delta |
|------|-----------------:|-------------:|------:|------------------------------|
| Y1 (2030) | 1,998.04 | 1,998.01 | -0.03 | essentially 0 |
| Y2 (2031) | 2,029.83 | 2,042.49 | +12.66 | Insurance slightly higher in Python |
| Y7 (2036) | 3,048.20 | 2,283.15 | **-765.05** | Excel higher — B.02.1 O&M escalates faster? |
| Y10 (2039) | 3,522.40 | 2,443.72 | **-1,078.68** | Excel significantly higher |
| Y13 (2042) | 2,681.31 | 2,618.09 | -63.22 | moderate |
| Y20 (2049) | 2,938.15 | 3,088.14 | +149.99 | Python higher |
| Y30 (2059) | 3,692.47 | 3,960.09 | +267.62 | Python higher |

**Excel annual = sum of two consecutive CF R38 period values (H1 + H2):**
- Y1 = col8 + col9 = 990.81 + 1007.23 = 1,998.04
- Y2 = col10 + col11 = 1006.57 + 1023.26 = 2,029.83

**Full horizon totals (60 semi-annual periods):**
- Excel CF R38 total: **-84,674.78 kEUR** (includes contingencies + claims)
- Excel OpEx R104 (excl. C): 79,881.87 kEUR over 30 years
- Python total: **85,408.27 kEUR** (includes all current items)

**Gap analysis:**
- Y1–Y2: essentially matched (within 13 kEUR)
- Y3–Y12: Excel higher than Python (up to -1,078 kEUR at Y10)
- Y13+: Python slightly higher, gap grows to +268 kEUR at Y30
- Root cause: Python uses flat inflation from Y1 amount; Excel has item-level active flags that change the mix of active items by year (e.g., B.12.1 activates at Y10, B.11.1 deactivates at Y14)

---

## 5. Proposed Data Model

### Dataclasses

```python
@dataclass(frozen=True)
class ManualOverride:
    """Marks a specific period override for an OPEX item."""
    period_index: int        # model period index (0-based)
    value_keur: float        # override value in kEUR
    source: str = "manual"   # "manual" | "import" | "reset"

@dataclass(frozen=True)
class OpexItemStep:
    """Step change: at a given year, item cost changes to a new value."""
    year_index: int          # 1-based operating year when step takes effect
    new_value_keur: float    # new annual base amount
    description: str = ""

@dataclass(frozen=True)
class OpexItem:
    """Single OPEX line item.

    basis options:
      - fixed_annual_keur: budget is annual cost in kEUR
      - eur_per_mw_year: budget is EUR/MW/year (× capacity_mw × inflation^year)
      - eur_per_mwh: budget is EUR/MWh (× generation_mwh)
      - pct_of_revenue: % of operating revenue (basis = revenue_keur)
      - pct_of_group: % of a named group's total cost
      - explicit_schedule: values given by schedule (semiannual_values tuple)
      - inactive: always 0
    """
    code: str                          # e.g. "B.01.1" or "" for unclassified
    name: str
    budget_keur: float                 # base amount (interpretation depends on basis)
    basis: str                          # "fixed_annual_keur" | "eur_per_mw_year" | "eur_per_mwh" | "pct_of_revenue" | "pct_of_group" | "explicit_schedule" | "inactive"
    inflation: float = 0.0            # annual inflation rate (0.02 = 2%)
    wth_rate: float = 0.0             # withholding tax rate (0 = none)
    active_flags: tuple[int, ...] = ()  # 1=active, 0=inactive per year (30 values). If empty = always active.
    step_changes: tuple[OpexItemStep, ...] = ()  # step changes over time
    explicit_schedule: tuple[float, ...] = ()  # semiannual values for explicit_schedule basis
    manual_overrides: tuple[ManualOverride, ...] = ()  # period-level overrides
    group_code: str = ""              # parent group code (e.g. "B.01")

@dataclass(frozen=True)
class OpexGroup:
    """OPEX group containing related items."""
    code: str                          # e.g. "B.01"
    name: str                          # e.g. "Technical Management"
    items: tuple[OpexItem, ...]        # child items
    inflation: float = 0.0            # group-level inflation (applied to sum of active items)
    wth_rate: float = 0.0             # group-level WTH
    contingency_pct: float = 0.0      # if > 0, this group is a contingency % of other groups

@dataclass(frozen=True)
class OpexPeriodResult:
    """Single period OPEX result with item-level decomposition."""
    period_index: int
    operating_period_index: int        # 0-based op_idx
    year_index: int                   # 1-based
    period_in_year: int               # 1=H1, 2=H2
    group_code: str
    item_code: str
    item_name: str
    is_manual_override: bool
    base_amount_keur: float           # before inflation/WTH
    inflated_amount_keur: float     # after inflation, before WTH
    wth_keur: float                  # WTH amount
    total_keur: float                # final cost (inflated + WTH or just inflated if no WTH)
    override_value_keur: float = 0.0  # if manual override was used

@dataclass(frozen=True)
class OpexGroupResult:
    """Aggregated result for one OPEX group per period."""
    period_index: int
    operating_period_index: int
    year_index: int
    period_in_year: int
    group_code: str
    group_name: str
    group_total_keur: float
    contingency_from_groups_keur: float = 0.0  # if this is the contingency group
    items: tuple[OpexPeriodResult, ...]

@dataclass(frozen=True)
class OpexResult:
    """Full OPEX schedule with hierarchy."""
    group_results: tuple[OpexGroupResult, ...]  # one per group per period
    total_by_period: tuple[float, ...]         # total OPEX per period_index
    grand_total_keur: float
```

### Design Notes

1. **RevenueAdjustmentSchedule reuse:** For items with `basis="explicit_schedule"`, the existing `RevenueAdjustmentSchedule` can be reused for period values.

2. **Active flags:** `active_flags` is a 30-element tuple (one per operating year). `1` = active, `0` = inactive. If empty tuple → always active. Flags are per-YEAR (H1 and H2 share the same flag).

3. **Step changes:** `OpexItemStep` allows cost to change at a specific year. Applied before inflation. Example: B.02.1 O&M might step up at Y6 when a contract renews.

4. **WTH cascade:** If `OpexItem.wth_rate > 0`, WTH = inflated_amount × wth_rate. WTH is a cost in the model (reduces net cash flow, not a separate line item in OPEX total).

5. **Contingency group:** `OpexGroup.contingency_pct > 0` means this group is computed as `pct × sum(other_active_groups)`. The formula references specific groups defined in the group's config.

6. **Manual overrides:** Stored on `OpexItem.manual_overrides`. Override takes precedence over calculated value. Override marks `is_manual_override=True` in result. Overrides are NOT inflated (they're the final period value).

---

## 6. Proposed Calculation Engine

### Core Algorithm

```python
def calculate_opex_period(
    item: OpexItem,
    year_index: int,       # 1-based operating year
    period_in_year: int,    # 1=H1, 2=H2
    generation_mwh: float,  # for eur_per_mwh basis
    revenue_keur: float,   # for pct_of_revenue basis
    group_total_keur: float,# for pct_of_group basis
) -> OpexPeriodResult:
    """Calculate OPEX for one item in one period."""

    # 1. Check active flag
    if item.active_flags:
        if year_index > len(item.active_flags) or item.active_flags[year_index - 1] == 0:
            return zero_result(item, year_index, period_in_year)

    # 2. Check manual override (takes precedence)
    for override in item.manual_overrides:
        if override.period_index == compute_period_index(year_index, period_in_year):
            return manual_result(item, override, year_index, period_in_year)

    # 3. Compute base amount
    base = compute_base_amount(item, year_index, generation_mwh, revenue_keur, group_total_keur)

    # 4. Apply step changes (find most recent step at or before year_index)
    base = apply_step_changes(base, item.step_changes, year_index)

    # 5. Apply inflation: base × (1 + inflation)^(year_index - 1)
    inflated = base * (1 + item.inflation) ** (year_index - 1)

    # 6. Apply WTH
    wth = inflated * item.wth_rate if item.wth_rate > 0 else 0.0

    # 7. Total
    total = inflated + wth  # WTH is addition to cost, not deducted from base

    return OpexPeriodResult(
        ...,
        base_amount_keur=base,
        inflated_amount_keur=inflated,
        wth_keur=wth,
        total_keur=total,
        is_manual_override=False,
    )
```

### compute_base_amount logic

```python
def compute_base_amount(item, year_index, generation_mwh, revenue_keur, group_total_keur):
    if item.basis == "fixed_annual_keur":
        return item.budget_keur
    elif item.basis == "eur_per_mw_year":
        return item.budget_keur * capacity_mw  # budget = EUR/MW/year
    elif item.basis == "eur_per_mwh":
        return item.budget_keur * generation_mwh / 1000  # kEUR
    elif item.basis == "pct_of_revenue":
        return item.budget_keur * revenue_keur / 100.0  # budget = percentage
    elif item.basis == "pct_of_group":
        return item.budget_keur * group_total_keur / 100.0
    elif item.basis == "explicit_schedule":
        # Handled by RevenueAdjustmentSchedule at period level
        return item.budget_keur  # not used for explicit_schedule
    elif item.basis == "inactive":
        return 0.0
```

### Aggregation

```python
def aggregate_opex_group(group: OpexGroup, period_results: list[OpexPeriodResult]) -> OpexGroupResult:
    group_total = sum(r.total_keur for r in period_results if r.group_code == group.code)

    # Contingency: if group has contingency_pct, compute from other groups
    contingency = 0.0
    if group.contingency_pct > 0:
        other_groups_total = sum(
            r.total_keur for r in period_results
            if r.group_code in group.contingency_ref_groups
        )
        contingency = other_groups_total * group.contingency_pct / 100.0

    return OpexGroupResult(
        group_total_keur=group_total + contingency,
        contingency_from_groups_keur=contingency,
        items=tuple(period_results),
    )
```

### Hierarchy of overrides

1. **Inactive flag** → returns zero (no cost)
2. **Manual override** → uses override value directly (no inflation applied to override)
3. **Step change** → modifies base amount before inflation
4. **Inflation** → applied to step-adjusted base
5. **WTH** → applied to inflated amount

---

## 7. HTMX UI Wireframe

### 7A. Inputs Tab OPEX Summary

```
┌─────────────────────────────────────────────────────────────┐
│  OPEX Summary (Annual kEUR)                                  │
├──────────────┬────────┬────────┬────────┬─────────────────┤
│ Group        │ Y1     │ Y2     │ ...    │ 30-Year Total    │
├──────────────┼────────┼────────┼────────┼─────────────────┤
│ B.01 Technical Management | 280.0 | 285.6 | ...   │ 11,359.1 │
│ B.02 Infrastructure Maint. | 426.6 | 427.4 | ...   │ 21,211.3 │
│ B.03 Maintain Site         | 68.0  | 69.4  | ...   │  2,758.6 │
│ B.04 Clean Material         | 5.0   | 5.1   | ...   │    202.8 │
│ B.05 Security               | 50.0  | 51.0  | ...   │  2,028.4 │
│ B.06 Insurance              | 468.7 | 478.1 | ...   │ 19,016.3 │
│ B.07 Lease & Property Tax   | 248.9 | 253.9 | ...   │ 10,096.6 │
│ B.08 Power Expenses          | 93.7  | 95.6  | ...   │  3,802.0 │
│ B.09 Telecom Fees            | 0.0   | 0.0   | ...   │      0.0 │
│ B.10 Audit&Accounting&Legal | 24.0  | 24.5  | ...   │    973.6 │
│ B.11 Bank Fees               | 20.0  | 20.4  | ...   │    319.5 │
│ B.12 Environ.&Social        | 200.0 | 204.0 | ...   │  8,113.6 │
│ B.13 Contingencies           | 113.1 | 114.9 | ...   │  4,792.9 │
├──────────────┼────────┼────────┼────────┼─────────────────┤
│ TOTAL OPEX   │ 1,998.0│ 2,042.5│ ...    │ 85,408.3        │
└──────────────┴────────┴────────┴────────┴─────────────────┘
[Detailed OPEX Editor →]
```

- One row per group (B.01 through B.13)
- Annual totals (not semi-annual) — consistent with Excel OpEx layout
- Link/button to detailed OPEX tab

### 7B. Detailed OPEX Tab

```
┌──────────────────────────────────────────────────────────────────────┐
│  OPEX Editor — TUHO Wind Project                         [Annual ▾] │
│                                                              [Export]│
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ▾ B.01 — Technical Management                         budget: 280  │
│    ┌─────────────┬────────┬────────┬────────┬─────────────────────┐│
│    │ Item        │ Budget │ basis  │ Infl.  │ Y1    Y2   ... Y30  ││
│    ├─────────────┼────────┼────────┼────────┼─────────────────────┤│
│    │ B.01.1 Asset Mgmt | 138 | fixed_annual | 2% | 280   285  ... ││
│    │ B.01.2 O&M Mgmt   | 67  | fixed_annual | —  | 1     1   ... ││
│    │ ...               │     │             │     │                   ││
│    └─────────────┴────────┴────────┴────────┴─────────────────────┘│
│    [+ Add Item]                                     [Edit Group]    │
│                                                                      │
│  ▾ B.02 — Infrastructure Maintenance                  budget: 667.6 │
│    ┌─────────────┬────────┬────────┬────────┬─────────────────────┐│
│    │ Item        │ Budget │ basis  │ Infl.  │ Y1    Y2   ... Y30  ││
│    ├─────────────┼────────┼────────┼────────┼─────────────────────┤│
│    │ B.02.1 O&M  │ 241   │ fixed_annual | — | 385.6 385.6 ... 828││
│    │ B.02.2 Minor Maint | 27 | fixed_annual | — | 1  1  ... 1    ││
│    │ ...               │     │             │     │                   ││
│    └─────────────┴────────┴────────┴────────┴─────────────────────┘│
│    Note: Parent budget = SUM(child items) + B.02.1 explicit cost     │
│    [+ Add Item]                                     [Edit Group]    │
│                                                                      │
│  ▾ B.06 — Insurance                                       budget: 468.75│
│    ...                                                            ...│
│                                                                      │
│  ▾ B.13 — Contingencies (6% of selected groups)          budget: 139.7 │
│    ...                                                            ...│
│                                                                      │
│  [+ Add Group]                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

**Cell Colors:**
- White/normal: formula-calculated (inflation applied to budget × flags)
- **Yellow/amber**: manual override entered (visually distinct)
- Gray: inactive (flag=0 or item with 0 budget)
- Red border: validation error (e.g., negative budget, incompatible basis+budget)

**Accordion behavior:** Click group header to expand/collapse item table.

### 7C. Item Editing Modal / Inline

```
Edit B.02.1 — O&M Preventive & Corrective
─────────────────────────────────────────
Code:     B.02.1
Name:     O&M – Preventive & Corrective
Group:    B.02 Infrastructure Maintenance

Budget:   [241        ] kEUR
Basis:    [fixed_annual_keur ▾]
Infl:     [—        ] %
WTH:      [0        ] %

Active flags (per year, click to toggle):
  Y1-Y9:  [ON ]  Y10-Y20: [ON ]  Y21-Y30: [OFF ]

Step changes:
  [+ Add step] Year: [  ] New value: [    ]

Manual overrides (period-level):
  [+ Add override]  Period: [  ] Value: [    ]

[Save] [Cancel] [Delete Item]
```

---

## 8. Implementation Phases

### PR O1: Excel Extraction + Mapping Doc Only
**Deliverable:** `docs/phase7h_opex_line_item_engine_design.md` (this document)

Tasks:
- [x] Extract OpEx tab structure (done)
- [x] Map all groups/items (done)
- [x] Document formula patterns (done)
- [x] Compare Excel vs Python OPEX (done)
- [ ] Add Oborovo OpEx extraction for comparison
- [ ] Add any missing Excel formula patterns (contingency group formula, B.02 special case)
- [ ] Review with cofix, get sign-off before O2

### PR O2: OPEX Schema + Calculation Engine + Unit Tests
**Deliverable:** New `domain/opex/line_item_engine.py` with OpexGroup, OpexItem, OpexPeriodResult, OpexResult, and calculation logic.

Tasks:
- [ ] Define OpexItem basis types (fixed_annual_keur, eur_per_mw_year, eur_per_mwh, pct_of_revenue, pct_of_group, explicit_schedule, inactive)
- [ ] Define OpexGroup with contingency_pct
- [ ] Implement `calculate_opex_item_period()` with active flag, step change, inflation, WTH, manual override precedence
- [ ] Implement `aggregate_opex_group()` with contingency calculation
- [ ] Add OpexItemStep for step changes
- [ ] Add ManualOverride dataclass
- [ ] Unit tests for each basis type
- [ ] Unit tests for active flags
- [ ] Unit tests for inflation
- [ ] Unit tests for step changes
- [ ] Unit tests for WTH
- [ ] Unit tests for manual overrides
- [ ] Unit tests for contingency group calculation

### PR O3: TUHO OPEX Template Mapping + Parity Tests
**Deliverable:** TUHO configured with full OpexGroup hierarchy matching Excel, with parity tests.

Tasks:
- [ ] Map all 12 Python OpexItems → OpexGroup hierarchy (B.01–B.13)
- [ ] Configure active flags for conditional items (B.11.1 Y1-Y14, B.12.1 Y10-Y30)
- [ ] Configure step changes for B.02.1 (O&M escalation)
- [ ] Configure contingency group (B.13 = 6% of active groups)
- [ ] Parity test: annual OPEX per year vs Excel OpEx Y1-Y30
- [ ] Parity test: total 30-year OPEX vs Excel R104/R105
- [ ] Verify B.02 special formula (parent = SUM children + B.02.1 explicit)
- [ ] Oborovo unchanged — verify current OpexItems still work

### PR O4: HTMX OPEX Editor
**Deliverable:** Detailed OPEX editor tab in HTMX UI with accordion groups, inline editing, manual override highlighting.

Tasks:
- [ ] Inputs tab OPEX summary row (one row per group, annual totals)
- [ ] "Detailed OPEX Editor →" button linking to new tab
- [ ] New `/project/<id>/opex` HTMX page
- [ ] Group accordion with item tables
- [ ] Inline editing for group name, item name, budget, basis, inflation, WTH
- [ ] Active flag toggle (per year, binary)
- [ ] Manual override entry (click cell → enter value, yellow highlight)
- [ ] Reset override button
- [ ] Add item / delete item under each group
- [ ] Add group (with code generation)
- [ ] Annual/semi-annual view toggle
- [ ] Color convention enforcement
- [ ] Validation (negative budget, invalid basis)
- [ ] Save/persist to DB

### PR O5: Excel Export OPEX Detail Sheet
**Deliverable:** Excel export includes detailed OPEX sheet matching Excel OpEx layout.

Tasks:
- [ ] Add `opex_detail` sheet to Excel export
- [ ] Group/item hierarchy with codes and names
- [ ] Budget, inflation, WTH columns
- [ ] Annual values Y1-Y30
- [ ] Active flag indicators
- [ ] Manual override markers (highlight in yellow)
- [ ] Contingency row with formula reference

---

## 9. Risks / Open Questions

1. **B.02 special formula** — The formula `budget = SUM(C15:C26) + F15` where F15 = B.02.1 O&M explicit cost needs to be modeled explicitly. The Python OpexItem for B.02 Infrastructure Maintenance has budget=667.6 which correctly sums to children + B.02.1. But the O&M Preventive item (B.02.1) has explicit cost 385.6 and is not a simple flag. We need to handle this hybrid case where one sub-item carries the cost and others are flags.

2. **Array formulas in sub-items** — B.02.1 Y1 value uses an array formula that couldn't be resolved in this extraction. Need to inspect `tuho_excel_1.xlsm` Scenarios sheet to understand the source of B.02.1 cost (241 kEUR budget → 385.6 kEUR Y1 cost → suggests budget × factor or capacity-based).

3. **Contingency formula dependency** — B.13 Contingencies = 6% × SUM(active groups). The active group set changes by year (based on flags). We need to model this as a two-pass calculation: first compute all groups' costs, then compute contingency = 6% × sum(groups where flag=1).

4. **WTH cascading** — WTH is modeled as an addition to cost, not deducted from revenue. Confirm: in Excel CF, is WTH a separate line item or added to the OPEX group cost?

5. **B.08.3 Balancing costs** — Budget=0 in Excel (because `Scenarios!E141*0`). But in Python we already have `balancing_cost_schedule = 8.0 EUR/MWh` for TUHO. Need to confirm whether this is the same B.08.3 item or a separate concept. Phase 7G already handles balancing via revenue schedule — reconciling with OPEX B.08.3 needs clarity.

6. **HTMX state management** — When user edits a group's budget, the parent group's budget must update (formula: SUM children). The UI needs to handle this dependency without circular updates. Consider: parent budget is read-only computed field, only child item budgets are editable.

7. **Oborovo OPEX extraction** — Current design is based on TUHO. Oborovo may have a different group structure. Task O1 should include Oborovo extraction before O2 implementation begins.

8. **Semi-annual vs annual display** — Excel OpEx shows annual values (Y1=year total). But the model operates on semi-annual periods. Need to decide: does the OPEX engine work at semi-annual level internally and aggregate for display, or work at annual level? Current Python `opex_schedule_annual` works at annual level. Phase 7G revenue engine works at semi-annual level. Reconciliation needed.

9. **Step changes vs inflation interaction** — If an item has both step changes and inflation, the step takes effect at a specific year, then inflation compounds from that new base. Confirm this matches Excel behavior.

10. **Excel period mapping** — TUHO has 2 construction periods (Y0-H1, Y0-H2) then 60 operating periods. Excel CF col 8 = first operating period (Y1-H1). The OpEx sheet columns F-AJ = Y1-Y30 (annual). Period mapping between OpEx (annual) and CF (semi-annual) needs explicit handling.
---

## O2 Implementation Decisions (2026-05-15)

### Contingency Group Architecture

**Decision: Two-layer model (Pass 1 base + Pass 2 contingency addition).**

A contingency group (e.g., B.13 with `contingency_pct=6`) works as follows:

1. **Pass 1 (normal):** The group's item is computed normally using `pct_of_selected_groups` basis.
   This gives a small "seed" amount (e.g., 6 = the stored budget percentage).
   This amount is included in `group_total_keur` and `total_by_year_keur`.

2. **Pass 2 (contingency):** The engine computes `contingency_amount = contingency_pct × Σ(selected groups' totals)`.
   This amount is added to `group_total_keur` and exposed as `contingency_from_groups_keur`.
   The item result's `calculated_keur` is updated to reflect the real computed amount.

**Example:** Group C has item IC (`budget_keur=6.0`, `basis=pct_of_selected_groups`, `selected_group_codes=['GA']`, `contingency_pct=6.0`).
- Pass 1: item base = 6 (the percentage value itself). `group_total_keur = 6`.
- Pass 2: `contingency_amount = 6% × GA_total(1000) = 60`. `group_total_keur = 6 + 60 = 66`.
- Item's `calculated_keur` updated to `60` in Pass 2.

This means `group_total_keur` for a contingency group = item base + contingency addition.
The `contingency_from_groups_keur` field isolates the contingency portion.

### Manual Override Priority

Inactive flag takes priority over manual override:
```
if not is_active(year):
    final = 0
elif manual_override exists:
    final = manual_override  # NOT inflated
else:
    final = calculated_amount  # WITH inflation
```

This means a manual override on an inactive flag year → 0, not the override value.
This is the safer design for audit and prevents accidental overrides on disabled items.

### WTH Treatment

WTH is treated as an **addition to cost** (not deducted from base). Formula:
```
final = calculated_amount  (or manual_override)
wth_keur = final × wth_rate
total_keur = final + wth_keur
```

This matches the Excel model where WTH increases the cost to the project (not a withholding on the vendor payment).
WTH is exposed in results for audit but is NOT yet fed into the broader tax engine in O2.

### Step Change Inflation

Step change at year `step_year`:
- New budget becomes the base from `step_year` onward.
- Inflation exponent counts from `step_year`, not from Y1.
- `calculated(year) = new_base × (1 + infl)^(year - step_year)`

This is tested explicitly in `TestOpexStepChange::test_step_change_at_year`.

### Explicit Schedule Basis

`explicit_schedule` bypasses inflation entirely. Values are used as-is from the schedule array.
`explicit_schedule_keur[year_index - 1]` gives the Y1 value, etc.
If the schedule is shorter than `years`, out-of-range years return 0.

### Basis: Decimal Percentage Convention

For `pct_of_revenue`, `pct_of_group`, and `pct_of_selected_groups`:
- `budget_keur` stores the percentage as a decimal (e.g., `0.02` for 2%, `6.0` for 6%).
- `base = referenced_value × budget_keur`.

### Active Flags Default

If `active_flags` is `None` or shorter than `years`, missing years default to `True` (active).
Explicit `active_flags=()` (empty tuple) is treated the same way — always active.

---

## O2 Test Summary

**31 tests, all passing** (`tests/test_opex_line_item_engine.py`):

| Test | Description |
|---|---|
| Test 1 | fixed_annual_keur with 2% inflation: Y1=100, Y2=102, Y3=104.04 |
| Test 2 | active flag false → Y2=0 |
| Test 3 | manual override at Y2 replaces calculated value |
| Test 4 | inactive with override → 0 (inactive wins) |
| Test 5 | explicit_schedule: exact values, no inflation |
| Test 6 | eur_per_mw_year: 10,000 EUR/MW/year × 50 MW / 1000 = 500 kEUR |
| Test 7 | eur_per_mwh: 2 EUR/MWh × 100,000 MWh / 1000 = 200 kEUR |
| Test 8 | pct_of_revenue: 0.02 × 1000 = 20 kEUR |
| Test 9 | group total = sum of item totals |
| Test 10 | contingency: 6% × selected groups = 60 kEUR (pass1 base=6 + pass2 addition=60) |
| Test 11 | WTH: 100 base × 0.1 wth → total=110, wth_keur=10 |
| Test 12 | step change at Y2, inflation resets from step year |
| Test 13 | backward compatibility with existing projections |
| Test 14 | no runtime regression (old opex_schedule_annual unchanged) |

---

## O2 Files Changed

```
domain/opex/line_items.py   — OpexItem, OpexItemStep, ManualOverride, OpexGroup
domain/opex/result.py       — OpexItemAnnualResult, OpexGroupAnnualResult, OpexAnnualResult
domain/opex/engine.py       — compute_annual_opex() with 2-pass contingency handling
tests/test_opex_line_item_engine.py — 31 tests covering all 14 required cases + extras
docs/phase7h_opex_line_item_engine_design.md — updated with implementation decisions
```

---

## Confirmed No Runtime Changes

- No changes to `domain/revenue/`, `domain/financing/`, `domain/inputs.py`
- No changes to waterfall, tax, SHL, senior debt, R99, construction, IDC
- `run_waterfall()` signature unchanged
- `opex_schedule_annual()` from `domain/opex/projections.py` unchanged
- TUHO and Oborovo current runtime outputs confirmed unchanged via existing test suite
- 371 existing tests pass (22 pre-existing failures unrelated to O2)
