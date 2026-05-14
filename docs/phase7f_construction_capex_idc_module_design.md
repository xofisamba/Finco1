# Phase 7F — Construction CAPEX & IDC Module Design

**Date:** 2026-05-14
**Type:** Design note (no implementation)
**Author:** OpenClaw agent
**Status:** Draft

---

## Context

Currently, `shl_idc_keur` is a **manual hardcoded input** for SHL IDC. The model should instead support a configurable construction-period CAPEX schedule that:
- Allocates CAPEX spending across construction months
- Calculates capitalized interest (IDC) per funding source (senior debt, SHL, equity)
- Produces opening balances at COD for senior debt and SHL
- Remains backward-compatible with existing manual `shl_idc_keur`

This is a **future module** — do not mix with current PR B2 SHL waterfall work.

---

## 1. Module Location

```
app/
  construction/
    __init__.py
    capex_schedule.py     # CAPEX spend profile logic
    funding_allocation.py # Funding source drawdown logic
    idc_calculator.py     # Monthly IDC computation
    result.py             # ConstructionIDCResult dataclass
    config.py             # ConstructionIDCConfig dataclass
```

Alternatively, as a subpackage under `app/models/` or alongside existing project factory logic.

**Decision:** `app/construction/` as a dedicated package — keeps IDC logic separate from operating-period waterfall, making it independently testable.

---

## 2. Recommended Dataclasses

### 2.1 Config dataclasses

```python
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, List, Literal

@dataclass
class MonthlySpendProfile:
    """Monthly CAPEX spend amounts for construction period."""
    spends: List[float]  # len = construction_months, amounts in kEUR
    
    def total(self) -> float:
        return sum(self.spends)
    
    def validate(self) -> List[str]:
        """Return list of validation errors (empty = valid)."""
        errors = []
        if any(s < 0 for s in self.spends):
            errors.append("Negative monthly spend not allowed")
        if abs(self.total()) < 1e-9:
            errors.append("Total CAPEX is zero")
        return errors


@dataclass
class FundingAllocation:
    """Defines how CAPEX is funded each month per source."""
    senior_debt_pct: float = 0.0      # e.g. 0.70 = 70%
    shl_pct: float = 0.0             # e.g. 0.20 = 20%
    equity_pct: float = 0.0           # e.g. 0.10 = 10%
    # grants/subsidies/VAT bridge reserved for future
    
    def validate(self) -> List[str]:
        errors = []
        total = self.senior_debt_pct + self.shl_pct + self.equity_pct
        if abs(total - 1.0) > 1e-9 and abs(total) > 1e-9:
            errors.append(f"Funding percentages sum to {total:.4f}, must equal 1.0")
        return errors


@dataclass 
class SpendProfileType:
    """Enum-like: which profile type to generate."""
    LINEAR = "linear"
    S_CURVE = "s_curve"
    FRONT_LOADED = "front_loaded"
    BACK_LOADED = "back_loaded"
    CUSTOM = "custom"  # user provides explicit monthly amounts


@dataclass
class ConstructionIDCConfig:
    """Top-level config for construction CAPEX & IDC module."""
    # Dates
    construction_start_date: date
    cod_date: date  # commercial operation date (first operating period start)
    
    # CAPEX
    total_capex_keur: float
    profile_type: str = SpendProfileType.LINEAR  # linear/s_curve/front/back/custom
    construction_months: int = 24  # derived from dates if not provided
    
    # S-curve params (if profile_type = s_curve)
    s_curve_peak_pct: float = 0.5   # what fraction of total is at peak month
    s_curve_peak_month: int = 12    # which month is peak (1-indexed)
    
    # Funding allocation
    funding: FundingAllocation = field(default_factory=FundingAllocation)
    
    # Interest rates
    senior_idc_rate: float = 0.0    # annual rate (e.g. 0.065 = 6.5%)
    shl_idc_rate: float = 0.0      # annual rate (e.g. 0.0793 = 7.93%)
    
    # Interest method
    interest_method: str = "average_balance"  # "average_balance" | "opening_balance"
    
    # Advanced (future)
    custom_monthly_spends: Optional[List[float]] = None  # for profile_type="custom"
    vat_bridge_pct: float = 0.0    # future
    grant_pct: float = 0.0          # future
    
    def validate(self) -> List[str]:
        errors = []
        if self.total_capex_keur <= 0:
            errors.append("total_capex_keur must be positive")
        if self.construction_months <= 0:
            errors.append("construction_months must be positive")
        # Date sanity: cod > construction_start
        if self.cod_date <= self.construction_start_date:
            errors.append("cod_date must be after construction_start_date")
        # Funding
        errors.extend(self.funding.validate())
        # Profile
        if self.profile_type not in ("linear", "s_curve", "front_loaded", "back_loaded", "custom"):
            errors.append(f"Unknown profile_type: {self.profile_type}")
        if self.profile_type == "custom" and not self.custom_monthly_spends:
            errors.append("profile_type=custom requires custom_monthly_spends")
        return errors
```

### 2.2 Monthly row dataclass

```python
from dataclasses import dataclass
from datetime import date

@dataclass
class MonthlyIDCEntry:
    """Single month of construction IDC calculation."""
    month_index: int          # 1-based month number (1 = first month of construction)
    period_start: date
    period_end: date
    
    # CAPEX this month
    capex_spend_keur: float
    
    # Senior debt
    senior_drawdown_keur: float
    senior_opening_keur: float
    senior_closing_keur: float
    senior_idc_keur: float
    
    # SHL
    shl_drawdown_keur: float
    shl_opening_keur: float
    shl_closing_keur: float
    shl_idc_keur: float  # capitalized PIK during construction
    
    # Equity
    equity_drawdown_keur: float
    
    # Cumulative at end of month
    cumulative_capex_keur: float
    cumulative_senior_drawn_keur: float
    cumulative_shl_drawn_keur: float
    cumulative_equity_keur: float
```

### 2.3 Result dataclass

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class ConstructionIDCResult:
    """Output of the construction IDC module."""
    monthly: List[MonthlyIDCEntry] = field(default_factory=list)
    
    # Summary scalars
    total_capex_keur: float = 0.0
    total_senior_drawn_keur: float = 0.0
    total_senior_idc_keur: float = 0.0
    total_shl_drawn_keur: float = 0.0
    total_shl_idc_keur: float = 0.0  # this is the capitalized PIK during construction
    total_equity_drawn_keur: float = 0.0
    
    # Opening balances at COD (first operating period)
    opening_senior_balance_at_cod_keur: float = 0.0
    opening_shl_balance_at_cod_keur: float = 0.0  # = drawdown + idc
    
    # IDC breakdown
    total_senior_idc_keur: float = 0.0
    total_shl_idc_keur: float = 0.0
    
    # Verification
    @property
    def total_shl_opening_cod(self) -> float:
        """SHL opening at COD = drawdown + capitalized IDC."""
        return self.total_shl_drawn_keur + self.total_shl_idc_keur
    
    def validate(self) -> List[str]:
        errors = []
        if abs(self.total_capex_keur - sum(e.capex_spend_keur for e in self.monthly)) > 1.0:
            errors.append("Monthly CAPEX sums do not equal total_capex_keur")
        return errors
```

---

## 3. Inputs Required

| Input | Type | Required | Default | Note |
|-------|------|----------|---------|------|
| `construction_start_date` | date | ✅ | — | First day of construction |
| `cod_date` | date | ✅ | — | COD = first operating period start |
| `total_capex_keur` | float | ✅ | — | Total CAPEX for the project |
| `profile_type` | str | ✅ | linear | linear/s_curve/front_loaded/back_loaded/custom |
| `s_curve_peak_pct` | float | If s_curve | 0.5 | Peak fraction |
| `s_curve_peak_month` | int | If s_curve | mid | Which month peaks |
| `funding.senior_debt_pct` | float | ✅ | — | e.g. 0.70 |
| `funding.shl_pct` | float | ✅ | — | e.g. 0.20 |
| `funding.equity_pct` | float | ✅ | — | e.g. 0.10 |
| `senior_idc_rate` | float | ✅ | — | Annual rate, e.g. 0.065 |
| `shl_idc_rate` | float | ✅ | — | Annual rate, e.g. 0.0793 |
| `interest_method` | str | No | average_balance | average_balance or opening_balance |
| `custom_monthly_spends` | List[float] | If custom | None | Must sum to total_capex |
| `construction_months` | int | No | derived from dates | Override |
| `vat_bridge_pct` | float | Future | 0.0 | Not implemented yet |
| `grant_pct` | float | Future | 0.0 | Not implemented yet |

---

## 4. Output Schema

```
ConstructionIDCResult:
  monthly: List[MonthlyIDCEntry]  # one per construction month
    month_index: int
    period_start: date
    period_end: date
    capex_spend_keur: float
    senior_drawdown_keur: float
    senior_opening_keur: float
    senior_closing_keur: float
    senior_idc_keur: float
    shl_drawdown_keur: float
    shl_opening_keur: float
    shl_closing_keur: float
    shl_idc_keur: float
    equity_drawdown_keur: float
    cumulative_capex_keur: float
    cumulative_senior_drawn_keur: float
    cumulative_shl_drawn_keur: float
    cumulative_equity_keur: float

  total_capex_keur: float
  total_senior_drawn_keur: float
  total_senior_idc_keur: float
  total_shl_drawn_keur: float
  total_shl_idc_keur: float
  total_equity_drawn_keur: float

  opening_senior_balance_at_cod_keur: float  # = total_senior_drawn + total_senior_idc
  opening_shl_balance_at_cod_keur: float      # = total_shl_drawn + total_shl_idc
```

---

## 5. CAPEX Spend Profile Generation

### 5.1 Linear
```python
def generate_linear(total, months):
    monthly = total / months
    return [monthly] * months
```

### 5.2 S-Curve
Uses logistic curve: `spend = total * peak_pct * (1 - 1/(1 + exp(-k*(month - peak_month))))`
Parameters: `peak_pct` (intensity), `peak_month` (timing), `k` (steepness, auto-calculated to hit peak_pct at peak_month).

### 5.3 Front-loaded
```python
def generate_front_loaded(total, months, decay_rate=0.05):
    # First month = total / months * factor, rest taper
    factor = 2.0  # first month gets 2x linear amount
    base = total / months
    spends = []
    for m in range(1, months + 1):
        if m == 1:
            spends.append(base * factor)
        else:
            spends.append(base * (2 - factor) * (1 - decay_rate) ** (m - 2))
    # Normalize to total
    s = sum(spends)
    return [t * total / s for t in spends]
```

### 5.4 Back-loaded
Mirror of front-loaded.

### 5.5 Custom
User provides explicit `custom_monthly_spends` list. Validate: length = construction_months, sum = total_capex, no negatives.

---

## 6. Funding Allocation

For each month, the drawdown by source = `capex_spend × source_pct`:

```python
senior_draw = capex_spend * funding.senior_debt_pct
shl_draw    = capex_spend * funding.shl_pct
equity_draw = capex_spend * funding.equity_pct
```

All sources draw simultaneously proportional to their funding percentages. No waterfall ordering needed unless future phase adds priority ordering.

---

## 7. IDC Calculation

### 7.1 Monthly period fraction

```python
def monthly_period_fraction(start: date, end: date) -> float:
    days = (end - start).days
    return days / 365.0  # actual/365 convention
```

Fallback if dates not available: `period_fraction = 1/12` (monthly).

### 7.2 Interest method: Average Balance

For each source and each month:
```python
average_balance = opening_balance + 0.5 * monthly_drawdown
interest = average_balance * annual_rate * period_fraction
```

### 7.3 Interest method: Opening Balance (simpler)

```python
interest = opening_balance * annual_rate * period_fraction
```

### 7.4 Monthly update loop

For each month `m`:
```
opening_senior = cumulative_senior_drawn[m-1] (prev closing)
drawdown_senior = capex_spend[m] * senior_pct
idc_senior = (opening_senior + 0.5 * drawdown_senior) * senior_rate * period_fraction
closing_senior = opening_senior + drawdown_senior + idc_senior

same for SHL:
opening_shl = cumulative_shl_drawn[m-1]
drawdown_shl = capex_spend[m] * shl_pct
idc_shl = (opening_shl + 0.5 * drawdown_shl) * shl_rate * period_fraction
closing_shl = opening_shl + drawdown_shl + idc_shl
```

**Note:** SHL IDC during construction is **capitalized** (PIK) — it accrues to the SHL balance and is not paid in cash. This matches the `ds_pik` treatment in Excel.

### 7.5 TUHO golden reference check

For TUHO: SHL drawdown ≈ 29,135 kEUR, construction SHL IDC ≈ 3,569 kEUR, opening SHL balance at COD ≈ 32,704 kEUR.

```
opening_shl_balance_at_cod = total_shl_drawn + total_shl_idc
= 29,135 + 3,569 = 32,704 kEUR ✅
```

---

## 8. Integration Points

### 8.1 Backward compatibility

The existing `shl_idc_keur` manual input in `Project` must continue to work:

```python
# In project factory or period engine build:
if construction_idc_result is not None:
    proj.shl_idc_keur = construction_idc_result.total_shl_idc_keur
    proj.shl_opening_balance_keur = construction_idc_result.opening_shl_balance_at_cod_keur
else:
    # Use existing manual shl_idc_keur as-is
    pass
```

### 8.2 Project factory integration

```python
@dataclass
class Project:
    # ... existing fields ...
    shl_idc_keur: float = 0.0          # existing manual input
    # New optional field:
    construction_idc_config: Optional[ConstructionIDCConfig] = None

# In create_default_tuho_wind1() or similar:
def create_default_tuho_wind1():
    proj = Project(...)
    # If construction_idc_config is set, run module
    if proj.construction_idc_config:
        idc_result = compute_construction_idc(proj.construction_idc_config)
        proj.shl_idc_keur = idc_result.total_shl_idc_keur
        proj.shl_opening_balance_keur = idc_result.opening_shl_balance_at_cod_keur
    return proj
```

### 8.3 Senior debt integration

Similarly, `senior_opening_balance_keur` can be populated from `opening_senior_balance_at_cod_keur`.

### 8.4 No impact on existing code

The module is opt-in. If `construction_idc_config = None`, existing manual inputs work unchanged. No changes to operating-period waterfall, no changes to Oborovo calibration unless explicitly enabled.

---

## 9. Validation Rules

| Rule | Description | Severity |
|------|-------------|---------|
| V1 | `construction_months = (cod_date - construction_start_date).days / 30.44` must be ≥ 1 | Error |
| V2 | `sum(monthly_spends) == total_capex_keur` (within 1 kEUR tolerance) | Error |
| V3 | No negative monthly spend | Error |
| V4 | Funding percentages sum to 1.0 (±1e-9) | Error |
| V5 | `profile_type=custom` requires `custom_monthly_spends` of correct length | Error |
| V6 | All rates ≥ 0 | Error |
| V7 | `cod_date > construction_start_date` | Error |
| V8 | `opening_shl_balance_at_cod = total_shl_drawn + total_shl_idc` must be consistent | Error (self-check) |
| V9 | `total_capex_keur > 0` | Error |

---

## 10. Test Plan

### 10.1 Unit tests (capex_schedule.py)

- [ ] `test_linear_profile_sums_to_total` — linear(100, 12).sum() == 100
- [ ] `test_s_curve_profile_sums_to_total` — s_curve(100, 12).sum() ≈ 100 (within 1e-6)
- [ ] `test_front_loaded_sums_to_total` — front_loaded(100, 12).sum() == 100
- [ ] `test_back_loaded_sums_to_total` — back_loaded(100, 12).sum() == 100
- [ ] `test_custom_profile_accepts_explicit_values` — custom([10,20,30], 3).sum() == 60
- [ ] `test_negative_spend_raises_validation_error`
- [ ] `test_wrong_length_raises_validation_error`

### 10.2 Unit tests (idc_calculator.py)

- [ ] `test_one_source_simple_idc` — 100 kEUR, 1 month, 10% rate, average_balance method:
  - drawdown = 100, opening = 0, avg = 50, interest = 5
  - closing = 105
- [ ] `test_two_source_split` — 100 kEUR total, 70% senior / 30% equity, 1 month, 6% / 8% rates
- [ ] `test_senior_opening_balance_accumulates_idc` — multi-month, senior balance grows
- [ ] `test_shl_idc_is_capitalized_not_paid` — SHL IDC increases SHL balance, no cash payment
- [ ] `test_average_balance_vs_opening_balance_differ` — same inputs, different methods give different results
- [ ] `test_three_month_linear_spend` — verify cumulative drawdowns match expected

### 10.3 Integration tests (result.py)

- [ ] `test_shl_opening_balance_equals_drawdown_plus_idc` — always true by construction
- [ ] `test_total_capex_equals_sum_of_monthly_spends`
- [ ] `test_funding_split_proportions` — senior_drawdown / total_capex ≈ senior_pct ± 0.01

### 10.4 Backward compatibility

- [ ] `test_manual_shl_idc_still_works` — set shl_idc_keur=1169, verify waterfall uses 1169
- [ ] `test_construction_module_does_not_break_existing_projects` — existing TUHO project without config loads correctly

### 10.5 TUHO golden reference test

- [ ] `test_tuho_construction_idc_reproduces_3569`:
  - config: 29,135 kEUR SHL draw, 7.93% SHL rate, 24 months construction, linear or as per TUHO actual
  - verify total_shl_idc_keur ≈ 3,569 kEUR within ±50 kEUR (1.4% tolerance)
  - verify opening_shl_balance_at_cod_keur ≈ 32,704 kEUR within ±50 kEUR

---

## 11. Implementation Roadmap

### Phase A — Foundation (new file, no existing code changes)
1. `app/construction/__init__.py`
2. `app/construction/config.py` — dataclasses only
3. `app/construction/capex_schedule.py` — profile generation (linear, s_curve, front/back, custom)
4. `app/construction/result.py` — MonthlyIDCEntry + ConstructionIDCResult dataclasses
5. Unit tests for capex_schedule.py

### Phase B — IDC Calculator
6. `app/construction/idc_calculator.py` — monthly IDC loop with both methods
7. Unit tests for idc_calculator.py (simple cases)
8. Integration test for result.validate()

### Phase C — Funding Allocation
9. `app/construction/funding_allocation.py` — funding percentage → monthly drawdowns (or fold into idc_calculator)
10. Integration test with two-source split

### Phase D — Integration
11. Update `Project` dataclass to add `Optional[ConstructionIDCConfig] construction_idc_config = None`
12. Add `compute_construction_idc(config: ConstructionIDCConfig) -> ConstructionIDCResult`
13. Add backward-compat hook in project factory
14. TUHO golden reference test (3569 kEUR within tolerance)

### Phase E — Documentation & Edge cases
15. S-curve parameter validation
16. Actual-day vs monthly fallback period fraction
17. VAT bridge placeholder (future)
18. Grant placeholder (future)

**Total estimated: ~200–300 lines of new code + tests**

---

## 12. Open Questions

| # | Question | Resolution Path |
|---|----------|----------------|
| OQ1 | Should construction months be auto-derived from dates or explicitly set? | Auto-derive from `(cod_date - construction_start_date).days / 30.44`, allow override |
| OQ2 | Should S-curve k (steepness) be configurable or auto? | Auto-calculate from peak_pct and peak_month; expose if needed |
| OQ3 | Does senior IDC get capitalized into senior balance or paid during construction? | Typically capitalized in project finance; model as capitalized |
| OQ4 | Should the module support multiple construction phases (phased COD)? | Not in v1; reserve for future |
| OQ5 | What happens if construction IDC config produces different IDC than manual shl_idc_keur? | Warn but don't override; user must reconcile manually |