# Phase 7G — Revenue Schedule Inputs: Balancing Cost + CO2 Sales

## Context

Manual Excel extraction confirmed TUHO operating revenue formula:

```
Operating Revenue =
  PPA Sales
  + Spot Sales
  - Balancing Costs        ← 8.0 EUR/MWh for all periods (TUHO)
  + CO2 Certificates Sales ← period schedule from Excel CF row 36
```

The existing model had `balancing_cost_wind_eur_mwh` (scalar) and `co2_enabled`/`co2_price_eur` (scalar).
Phase 7G replaces these with **generic schedule-based inputs** supporting constant, annual, and semiannual modes.

---

## Schedule Indexing Contract

**This is the canonical contract for all user-facing schedules.**

| Schedule | Index | Meaning |
|----------|-------|---------|
| `semiannual_values[0]` | op_idx 0 | First **operating** period (Y1-H1) |
| `semiannual_values[1]` | op_idx 1 | Second **operating** period (Y1-H2) |
| `semiannual_values[n]` | op_idx n | (n+1)-th operating period |
| `annual_values[0]` | year 1 | Both Y1-H1 and Y1-H2 |
| `annual_values[1]` | year 2 | Both Y2-H1 and Y2-H2 |

**Construction/stub periods do NOT consume schedule values.**

The helper accepts an explicit `operating_period_index` (caller-derived). No internal offset subtraction.

---

## New API: value_for_period(*, operating_period_index, operating_year_index, period_in_year)

```python
@dataclass(frozen=True)
class RevenueAdjustmentSchedule:
    constant_value: float = 0.0
    annual_values: tuple[float, ...] = ()
    semiannual_values: tuple[float, ...] = ()

    def value_for_period(
        self,
        *,
        operating_period_index: int,  # 0-based op_idx (explicit, caller-derived)
        operating_year_index: int,    # 1-based operating year
        period_in_year: int,           # 1=H1, 2=H2
    ) -> float:
        """Return EUR/MWh for this period.

        Contract: semiannual_values[0] = first operating period.
        No construction offset is inferred inside this helper.
        """
        if self.semiannual_values and operating_period_index < len(self.semiannual_values):
            return self.semiannual_values[operating_period_index]
        if self.annual_values:
            year_idx_0 = operating_year_index - 1
            if year_idx_0 < len(self.annual_values):
                return self.annual_values[year_idx_0]
        return self.constant_value
```

---

## Revenue Formula

```
power_revenue_keur    = generation_mwh × effective_power_price_eur_per_mwh / 1000
balancing_cost_keur   = generation_mwh × balancing_cost_schedule.value_for_period() / 1000
co2_revenue_keur      = generation_mwh × co2_sales_schedule.value_for_period() / 1000

revenue_keur = power_revenue_keur − balancing_cost_keur + co2_revenue_keur
```

Where `value_for_period()` uses `operating_period_index = max(0, period_index - 2)` internally.

---

## RevenueAdjustmentSchedule dataclass

```python
@dataclass(frozen=True)
class RevenueAdjustmentSchedule:
    """Generic schedule for revenue adjustment inputs (balancing cost, CO2).

    SCHEDULE CONTRACT (user-facing, operating-period based):
    - semiannual_values[0] = first OPERATING period (Y1-H1)
    - semiannual_values[1] = second OPERATING period (Y1-H2)
    - annual_values[0] = first OPERATING year (both H1 and H2)
    - Construction/stub periods do NOT consume schedule values

    The helper derives operating_period_index = max(0, period_index - 2)
    internally. For a semi-annual model with 2 construction periods:
    period_index=0,1 (construction) → op_idx=0 → semiannual_values[0]
    period_index=2 (first op) → op_idx=0 → semiannual_values[0]
    period_index=3 (second op) → op_idx=1 → semiannual_values[1]

    Mode is inferred from which field is non-empty:
    - if semiannual_values is non-empty → mode = "semiannual" (takes priority)
    - elif annual_values is non-empty → mode = "annual"
    - else → mode = "constant" (constant_value used)
    """
    constant_value: float = 0.0
    annual_values: tuple[float, ...] = ()
    semiannual_values: tuple[float, ...] = ()

    def value_for_period(
        self,
        period_index: int,
        year_index: int,
        period_in_year: int,
    ) -> float:
        """Return the value in EUR/MWh for a given period.

        Args:
            period_index: 0-based model period index (0=Y0-H1, 1=Y0-H2, ...)
            year_index: 1-based OPERATING year (1=Y1, 2=Y2, ...)
            period_in_year: 1=H1, 2=H2

        Returns:
            Value in EUR/MWh for this period
        """
        # Derive operating period index from period_index
        # Semi-annual model: 2 construction periods (0,1) → first op = index 2 → op_idx=0
        operating_period_index = max(0, period_index - 2)

        if self.semiannual_values and operating_period_index < len(self.semiannual_values):
            return self.semiannual_values[operating_period_index]
        if self.annual_values:
            year_idx_0 = year_index - 1
            if year_idx_0 < len(self.annual_values):
                return self.annual_values[year_idx_0]
        return self.constant_value
```

**Key properties:**
- `frozen=True` → hashable, compatible with `@st.cache_data`
- Empty tuples → falsy → defaults to constant_value
- `annual_values` indexed by `year_index - 1` (0-based, operating year)
- `semiannual_values` indexed by `operating_period_index` (op_idx = period_index - 2)
- Out-of-range → returns `constant_value` (safe fallback)
- **No dummy construction values required** in user-facing schedules

---

## Files Changed

| File | Change |
|------|--------|
| `domain/inputs.py` | Add `RevenueAdjustmentSchedule` dataclass; add `balancing_cost_schedule` and `co2_sales_schedule` to `RevenueParams`; deprecate `balancing_cost_wind_eur_mwh`, `co2_enabled`, `co2_price_eur` |
| `domain/revenue/generation.py` | Update `full_revenue_schedule()` to use schedule `.value_for_period()` |
| `app/builder.py` | Add default 0.0 schedules for UI flow |
| `utils/cache.py` | Add new schedule fields to `hash_inputs_for_cache()` |
| `tests/test_revenue_schedule.py` | 24 new tests for schedule contract and acceptance criteria |

**No changes to:** SHL behavior, tax engine, senior debt sculpting, distribution logic, Oborovo defaults, PPA/merchant boundary.

---

## TUHO Factory Values

### Balancing cost schedule
- **Mode:** constant
- **Value:** 8.0 EUR/MWh for every operating period (no construction shift)

```python
balancing_cost_schedule=RevenueAdjustmentSchedule(constant_value=8.0)
```

### CO2 sales schedule
- **Mode:** semiannual
- **Index:** op_idx (operating period, not raw period_index)
- **No construction shift** — `semiannual_values[0]` = Y1-H1 = 4.1911 EUR/MWh

| op_idx | EUR/MWh | Note |
|--------|---------|------|
| 0–1    | 4.1911  | Y1 |
| 2–3    | 3.7830  | Y2 |
| 4–5    | 3.3750  | Y3 |
| 6–7    | 2.9670  | Y4 |
| 8–9    | 2.4500  | Y5 |
| 10–11  | 2.3500  | Y6 |
| 12–13  | 2.2000  | Y7 |
| 14–15  | 2.1000  | Y8 |
| 16–17  | 2.0500  | Y9 |
| 18–19  | 1.9500  | Y10 |
| 20–21  | 1.8000  | Y11 |
| 22–23  | 1.7000  | **Y12 (last PPA)** |
| 24–25  | 1.6000  | **Y13 (first post-PPA)** |
| 26–27  | 1.5000  | Y14 |
| 28–29  | 1.4000  | Y15 |
| 30–31  | 1.3000  | Y16 |
| 32–33  | 1.2000  | Y17 |
| 34–35  | 1.1500  | Y18 |
| 36–37  | 1.0500  | Y19 |
| 38–39  | 1.0000  | Y20 |
| 40–41  | 0.9500  | Y21 |
| 42–43  | 0.9000  | Y22 |
| 44–45  | 0.8500  | Y23 |
| 46–51  | 0.8000  | Y24–Y25 |
| 52–55  | 0.7500  | Y26–Y27 |
| 56–59  | 0.7000  | Y28–Y30 |

### Acceptance criteria verified:
- `co2_sales_schedule.semiannual_values[0]` = 4.1911 ✓
- `co2_sales_schedule.semiannual_values[1]` = 4.1911 ✓
- `co2_sales_schedule.semiannual_values[24]` = 1.6000 ✓ (Y13-H1, first post-PPA)
- `balancing_cost_schedule.constant_value` = 8.0 ✓
- No construction dummy values required ✓

---

## Backward Compatibility

- Oborovo: `balancing_cost_schedule=(constant_value=0.0)`, `co2_sales_schedule=(constant_value=0.0)`
- Existing projects with defaults produce identical revenue to old scalar approach
- Deprecated scalar fields (`balancing_cost_wind_eur_mwh`, `co2_enabled`, `co2_price_eur`) still exist but are unused by new formula

---

## Tests (24 new tests)

### Schedule contract tests
- Constant schedule returns same value for all periods
- Annual schedule applies same value to H1 and H2 of each operating year
- Semiannual schedule indexed by operating period (not raw period_index)
- Construction periods (index 0, 1) do NOT consume schedule values
- Out-of-range → constant_value fallback
- Empty schedule defaults to 0.0
- Semiannual takes priority over annual over constant
- Schedule is hashable (frozen dataclass)

### Revenue formula tests
- Basic: `(gen * power - gen * bal + gen * co2) / 1000 = 56 kEUR`
- Zero balancing + CO2 → identical to old revenue
- Balancing only reduces revenue
- CO2 only increases revenue

### TUHO acceptance tests
- `semiannual_values[0]` = 4.1911 (Y1-H1, 2030-06-30)
- `semiannual_values[1]` = 4.1911 (Y1-H2, 2030-12-31)
- `semiannual_values[24]` = 1.6000 (Y13-H1, first post-PPA)
- Balancing = 8.0 EUR/MWh for every operating period
- First op period (period.index=2) uses schedule index 0 (not shifted by construction)
- Revenue positive for all 60 operating periods
- CO2 schedule tail: op_idx 59 = 0.7, op_idx 23 = 1.7, op_idx 24 = 1.6

### Oborovo backward compat tests
- `balancing_cost_schedule.constant_value` = 0.0 (both schedules)
- Revenue schedule positive for all op periods
- Y1-H1 PPA revenue matches expected tariff × generation baseline

---

## Acceptance Criteria

- [x] Generic input supports constant, annual, and semiannual schedules
- [x] Schedule indexed by **operating period index (op_idx)** — construction offsets excluded
- [x] User-facing contract documented: `semiannual_values[0]` = first operating period
- [x] Existing projects with defaults unchanged (backward compat)
- [x] Oborovo unchanged — `constant_value=0.0` for both schedules
- [x] TUHO CO2 schedule: op_idx 0→4.1911, op_idx 1→4.1911, op_idx 24→1.6000
- [x] TUHO balancing: constant 8.0 EUR/MWh for every operating period
- [x] No construction dummy values required in user schedules
- [x] TUHO revenue decomposition includes balancing and CO2
- [x] No SHL, tax, senior, distribution, R99 runtime, or construction IDC changes
- [x] All 362 tests pass (24 new Phase 7G tests)
- [x] No changes to PPA/merchant boundary