# Phase 7K Senior Rate Schedule Runtime Design

## Purpose

Design a runtime-safe senior debt rate schedule and day-count model before changing senior debt formulas.

This document is design-only. It does not change runtime behavior, senior debt calculations, repayment formulas, SHL, revenue, OPEX, tax, construction capitalization, project factories, UI, cache, or sponsor/R99 logic.

## Confirmed Context

Prior Phase 7K diagnostics established:

- senior operating debt opens on principal only,
- senior IDC is not capitalized into operating senior debt,
- commitment fees are not capitalized into operating senior debt,
- the remaining first-period senior interest gap is mainly rate and day-count basis,
- Excel uses workbook all-in senior rates and ACT/360-like period fractions,
- current Python uses a flat `all_in_rate / 2`.

First-period evidence:

| Project | Excel convention | Python convention |
|---|---|---|
| TUHO | `5.9500% * 181/360` | `5.7500% * 0.5` |
| Oborovo | `5.95136% * 184/360` | `5.6500% * 0.5` |

## Design Goals

1. Preserve legacy behavior by default.
2. Add explicit, opt-in senior interest configuration.
3. Support Excel-like rate schedules and period fractions without hardcoding Excel row values.
4. Keep the implementation small and local to senior interest calculations.
5. Avoid rewriting senior sculpting or amortization architecture.
6. Allow TUHO and Oborovo opt-in only after fixture-backed parity tests pass.

## Rate Schedule Model

Senior debt should model rate construction explicitly rather than relying only on a flat annual rate.

### Concepts

| Concept | Meaning |
|---|---|
| Base rate | Floating reference curve or fixed base rate before margin. |
| Margin | Contractual bank margin. |
| All-in rate | Base rate plus margin and any explicit add-ons. |
| Fixed component | Portion of debt using fixed base rate / hedge rate. |
| Floating component | Portion of debt using floating curve. |
| Hedge percentage | Share of senior debt priced from fixed component. |
| Per-period rate schedule | Final annual all-in rate by operating period. |
| Project-specific override | Explicit schedule for calibrated projects where workbook mechanics require it. |

### Proposed Enum: `SeniorRateMode`

```python
class SeniorRateMode(Enum):
    FLAT_ALL_IN = "flat_all_in"
    FIXED_PLUS_MARGIN = "fixed_plus_margin"
    FLOATING_PLUS_MARGIN = "floating_plus_margin"
    HEDGE_BLEND = "hedge_blend"
    EXPLICIT_ALL_IN_SCHEDULE = "explicit_all_in_schedule"
```

Recommended semantics:

- `FLAT_ALL_IN`: current behavior. Annual all-in rate comes from `financing.all_in_rate`; runtime uses existing fixed semiannual conversion unless day-count opt-in is enabled.
- `FIXED_PLUS_MARGIN`: all-in rate = fixed base rate + margin.
- `FLOATING_PLUS_MARGIN`: all-in rate = floating curve value + margin.
- `HEDGE_BLEND`: all-in rate = hedge_pct * fixed_base_rate + (1 - hedge_pct) * floating_base_rate + margin.
- `EXPLICIT_ALL_IN_SCHEDULE`: caller supplies annual all-in rates per senior period.

### Proposed Dataclass: `SeniorHedgeConfig`

```python
@dataclass(frozen=True)
class SeniorHedgeConfig:
    hedge_pct: float = 0.0
    fixed_base_rate: float | None = None
    floating_base_rate_curve: tuple[float, ...] = ()
    floating_curve_buffer_pct: float = 0.0
```

Validation:

- `0 <= hedge_pct <= 1`.
- If `hedge_pct > 0`, `fixed_base_rate` must be present unless using explicit all-in schedule.
- Floating curve values are annual rates, not semiannual rates.

### Proposed Dataclass: `SeniorRateSchedule`

```python
@dataclass(frozen=True)
class SeniorRateSchedule:
    mode: SeniorRateMode = SeniorRateMode.FLAT_ALL_IN
    flat_all_in_rate: float | None = None
    fixed_base_rate: float | None = None
    margin_rate: float = 0.0
    hedge: SeniorHedgeConfig | None = None
    explicit_all_in_rates: tuple[float, ...] = ()

    def all_in_rate_for_period(self, period_index: int) -> float:
        ...
```

Design notes:

- `explicit_all_in_rates` should be annual rates, e.g. `0.0595`.
- If the explicit schedule is shorter than senior tenor, either raise or extend only if a clear policy is configured.
- No Excel cell references should appear in runtime. Excel values may live in tests/fixtures or project templates only after validation.

## Day-Count Model

Senior interest should separate annual rate from period fraction.

### Proposed Enum: `SeniorDayCountConvention`

```python
class SeniorDayCountConvention(Enum):
    FIXED_SEMIANNUAL = "fixed_semiannual"
    ACT_360 = "act_360"
    ACT_365 = "act_365"
    EXPLICIT_FRACTIONS = "explicit_fractions"
```

### Proposed Dataclass: `SeniorDebtInterestConfig`

```python
@dataclass(frozen=True)
class SeniorDebtInterestConfig:
    enabled: bool = False
    rate_schedule: SeniorRateSchedule = field(default_factory=SeniorRateSchedule)
    day_count: SeniorDayCountConvention = SeniorDayCountConvention.FIXED_SEMIANNUAL
    explicit_period_fractions: tuple[float, ...] = ()
```

Recommended period fraction behavior:

| Convention | Fraction |
|---|---|
| `FIXED_SEMIANNUAL` | Always `0.5`; current behavior. |
| `ACT_360` | `(period_end - period_start + inclusive_day_policy) / 360`; must match Excel convention before enabling. |
| `ACT_365` | Calendar days divided by 365. |
| `EXPLICIT_FRACTIONS` | Use provided per-period fraction schedule, e.g. `181/360`, `184/360`. |

Important design choice:

Excel appears to use an inclusive-day ACT/360-like basis for senior debt period fractions. TUHO first operating period is `181/360`; Oborovo first operating period is `184/360`. The implementation branch must verify the exact inclusive/exclusive rule across all operating periods before using calculated ACT/360 instead of explicit fractions.

## Runtime Integration

### Current Runtime

The current senior debt path builds:

- a per-period `rate_schedule`, currently derived from `rate_per_period`,
- sculpted debt service using `closed_form_sculpt`,
- interest from opening balance times the per-period rate,
- principal as payment minus interest.

### Proposed Minimal Integration

Add a default-off config path:

```python
use_senior_rate_schedule_engine: bool = False
senior_interest_config: SeniorDebtInterestConfig | None = None
```

When disabled:

- preserve current `all_in_rate / 2` behavior exactly,
- no changes to existing projects,
- no changes to cached behavior except adding stable default fields if needed.

When enabled:

1. Build annual all-in rates for senior tenor periods.
2. Build period fractions for senior tenor periods.
3. Convert to per-period rates:

```python
period_rate[t] = annual_all_in_rate[t] * period_fraction[t]
```

4. Pass the resulting per-period `rate_schedule` into existing sculpting and interest calculation.
5. Keep opening balance principal-only.
6. Do not alter SHL, tax, revenue, OPEX, construction capitalization, R99, or sponsor waterfall.

### Why This Avoids A Rewrite

The existing engine already accepts a per-period `rate_schedule`. The runtime flag should only change how that schedule is produced. It should not change:

- debt sizing method,
- fixed debt amount,
- DSCR schedule,
- payment formulas,
- principal cap logic,
- final repayment behavior,
- opening senior debt policy.

## Project Opt-In Strategy

Default:

- all projects use legacy behavior.

TUHO / Oborovo validation phase:

- build explicit schedule tests first,
- opt in only in tests or project-specific templates after period-by-period parity is proven,
- do not enable globally.

Unsupported projects:

- if a project sets the new flag without a valid schedule/config, raise a clear error or fall back only if explicitly configured.

## Test Plan

### Unit Tests

1. `test_fixed_semiannual_legacy_fraction`
   - `FIXED_SEMIANNUAL` returns `0.5`.

2. `test_act_360_fraction`
   - validates first-period fractions such as `181/360` and `184/360` using the agreed inclusive-day rule.

3. `test_explicit_fraction_schedule`
   - explicit fractions are used as-is and validated for length.

4. `test_flat_all_in_rate_mode`
   - reproduces current all-in rate behavior.

5. `test_hedge_blend_rate_mode`
   - confirms `hedge_pct * fixed + (1 - hedge_pct) * floating + margin`.

6. `test_explicit_all_in_schedule`
   - explicit annual all-in rates are applied period by period.

### Runtime Tests

1. `test_legacy_flag_off_equivalence`
   - TUHO and Oborovo outputs unchanged when flag is false.

2. `test_no_change_to_opening_balance_policy`
   - senior opening debt remains principal-only.

3. `test_senior_idc_not_added_to_operating_debt`
   - computed senior IDC remains diagnostic / CapEx-side only.

4. `test_tuho_first_period_interest_parity_when_flag_on`
   - TUHO period 0 interest matches `43,358.531 * 0.0595 * 181/360`.

5. `test_oborovo_first_period_interest_parity_when_flag_on`
   - Oborovo period 0 interest matches `42,852.279 * 0.0595136 * 184/360`.

6. `test_senior_ds_period_bridge_improves_without_shl_changes`
   - senior DS improves for first periods without changing SHL mechanics.

7. `test_no_revenue_opex_tax_r99_shl_drift`
   - key non-senior totals remain unchanged except downstream effects explicitly caused by senior interest/debt service.

## Risks

| Risk | Mitigation |
|---|---|
| Hardcoding Excel rows | Keep Excel references in docs/tests/fixtures only. Runtime uses project inputs and typed schedules. |
| Overfitting TUHO and Oborovo | Use generic `SeniorRateSchedule` and `SeniorDayCountConvention`; TUHO/Oborovo become opt-in templates, not global behavior. |
| DSCR sculpting interaction | Rate schedule affects sculpted payments. Validate period-by-period senior interest, principal, DS, and closing balance before enabling. |
| Future multi-lender design | Keep schedule object lender-neutral now, but avoid baking in only one facility's formulas. Later support can wrap multiple schedules. |
| SHL waterfall interaction | Senior DS changes cash available to SHL. Do not combine this with B2 SHL fcf_waterfall. |
| Construction IDC confusion | Keep construction senior IDC separate from operating senior debt. New rate config is for operating senior interest only. |
| Cache identity drift | If config is added to cache keys, default false/empty config must preserve legacy cache behavior. |

## Recommended Implementation Branch

Next branch: `phase7k-senior-rate-schedule-runtime-flag`.

Recommended scope:

- add enums/dataclasses for senior rate/day-count config,
- add default-off flag,
- add schedule builder that produces per-period rates,
- wire only into the existing `rate_schedule` path,
- add TUHO/Oborovo tests with explicit schedules,
- preserve legacy default behavior,
- do not change SHL, revenue, OPEX, tax, construction capitalization, R99, sponsor waterfall, UI, or cache beyond required config identity.

## Non-Goals

- No senior debt engine rewrite.
- No DSCR sculpting redesign.
- No SHL fcf_waterfall implementation.
- No opening balance change to include IDC or fees.
- No revenue/OPEX/tax/R99/sponsor/UI/cache work.
