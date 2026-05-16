# Phase 7K Senior DSCR Sculpting Runtime Design

## Purpose

This document designs a runtime-safe, default-off senior DSCR / sculpting basis
configuration before any senior repayment formula changes are made.

This is design-only. No runtime behavior is changed.

## Confirmed Starting Point

The Phase 7K bridges established:

- operating senior debt opens on principal only,
- senior IDC is excluded from operating senior debt,
- commitment fees are excluded from operating senior debt,
- the senior rate/day-count path can match first-period Excel interest,
- the remaining senior debt gap is principal / DSCR sculpting basis and
  repayment shape.

Known remaining first-period gaps after rate/day-count parity:

| Project | Principal gap | DS gap | Final DS gap |
|---|---:|---:|---:|
| TUHO | Python low by about 117 kEUR | Python low by about 117 kEUR | Python high by about 595 kEUR |
| Oborovo | Python low by about 171 kEUR | Python low by about 171 kEUR | Python high by about 1,038 kEUR |

## Current Python Sculpting Path

The current Python path is intentionally preserved by default.

### Where Senior DS Is Determined

The waterfall runner builds a `WaterfallRunConfig` from project inputs and
passes it to `run_waterfall_v3_core`. The core waterfall then delegates senior
debt schedule construction to the existing waterfall senior debt path.

Key inputs:

- `fixed_debt_keur`
- `debt_sizing_method`
- `target_dscr`
- `dscr_schedule`
- `rate_per_period`
- optional `rate_schedule`
- `tenor_periods`

### Target DSCR Application

Python supports:

- a scalar `target_dscr`,
- a per-period `dscr_schedule`,
- fixed debt sizing through `fixed_debt_keur`,
- sculpted amortization with the existing senior debt engine.

For TUHO, PR B1 already configured:

```text
amortization_type = "sculpted"
fixed_ds_keur = 0.0
dscr_schedule = [1.20] * 24 + [1.4125] * 4
fixed_debt_keur = 43,359.0
```

### CFADS Use

Python uses the existing model cash flow basis available to the senior debt
engine. Prior bridges showed first-period CFADS is close to Excel for both
projects, so CFADS level is not the first-order period-1 issue.

The current principal gap therefore appears to come from the senior debt
service sizing and repayment shape, not from a large first-period CFADS gap.

### Interest Subtraction

Interest is calculated from the senior opening balance and the period rate.
After the senior rate/day-count runtime flag, this can be either:

```text
legacy:      annual all-in rate / 2
flag-on:     annual all-in rate[t] * period_fraction[t]
```

The interest path is now isolated from the principal/sculpting issue.

### Principal Cap

The existing senior debt engine caps principal by available senior balance and
repays the residual in the final period. This creates a correct zero final
senior balance but a different amortization shape than Excel:

- early principal is too low,
- final repayment is too high.

### Final Repayment

Current Python final repayment is residual-balance driven. Excel also reaches
zero senior debt, but the final-period principal is much lower because more
principal was repaid earlier.

### Fixed Debt Interaction

`fixed_debt_keur` controls the opening operating senior balance. The opening
balance policy must stay principal-only:

- do not add senior IDC,
- do not add commitment fees,
- do not mutate construction capitalization.

## Excel Sculpting Basis

### TUHO

Workbook: `20260330_TUHO_BP.xlsm`

Known references from the bridge:

| Mechanic | Excel reference | Formula / value | Interpretation |
|---|---|---|---|
| CFADS / FCF banks | `CF!H69` | `3,070.176` | Senior repayment cash-flow reference. |
| Senior CF for repayment | `DS!H20` | `=(H17/H19+SUM(CF!H73:H73))*H9*$B20` | Debt sizing / repayment cash available. |
| DSCR target | `DS!H19` | `1.20` | PPA-period target DSCR. |
| Principal formula | `DS!H60` | `=MIN(H58,H$43*Inputs!$D$182*$B$57-H63)` | Principal equals an Excel senior DS basis less gross interest, capped by opening balance. |
| Interest formula | `DS!H61` | `=H58*H41*H6*(H88=0)` | Opening balance times all-in rate times period fraction. |

TUHO does not appear to use a plain first-period `CFADS / target_dscr` formula.
The principal formula references a senior DS basis row plus input multipliers,
then subtracts interest. The exact Python-equivalent basis needs to be exposed
before a formula change is safe.

### Oborovo

Workbook: `20260414_BP_Oborovo_Sensitivity_FINAL for PPT.xlsm`

Known references from the bridge:

| Mechanic | Excel reference | Formula / value | Interpretation |
|---|---|---|---|
| CFADS / FCFB senior | `CF!H141` | `2,575.003` | Senior CFADS / FCFB senior. |
| Senior CF for repayment | `DS!H46` | `=H23*H5` | Available senior CF / debt-service amount. |
| DSCR actual | `CF!H138` | `=IF(H$80=0,10,ROUND(-H$141/H$80,3))` | Excel reported senior DSCR. |
| Principal formula | `DS!H63` | `=MIN(H61,H$46*Inputs!$D$199*$B$60-H66)` | Principal equals Excel senior DS basis less gross interest, capped by opening balance. |
| Interest formula | `DS!H64` | `=H61*H44*H6*(H91=0)` | Opening balance times all-in rate times period fraction. |

Oborovo first-period Excel senior DS reconciles closely to `CFADS / 1.15`, but
the formula still routes through a specific DS basis row. A shared runtime
change should not assume this simpler formula also applies to TUHO.

## Proposed Runtime Configuration

Add a default-off senior sculpting configuration in a future implementation
branch. The config should be separate from the rate/day-count config so each
axis can be validated independently.

### Proposed Enum

```python
class SeniorSculptingMode(Enum):
    LEGACY = "legacy"
    EXCEL_AVAILABLE_CFADS = "excel_available_cfads"
    EXPLICIT_DEBT_SERVICE_SCHEDULE = "explicit_debt_service_schedule"
    EXPLICIT_PRINCIPAL_SCHEDULE = "explicit_principal_schedule"
```

### Proposed Supporting Enums

```python
class SeniorFinalRepaymentPolicy(Enum):
    LEGACY_RESIDUAL = "legacy_residual"
    CAP_AT_EXPLICIT_SCHEDULE = "cap_at_explicit_schedule"
    FULL_BALANCE_AT_MATURITY = "full_balance_at_maturity"


class SeniorPrincipalCapPolicy(Enum):
    CAP_AT_OPENING_BALANCE = "cap_at_opening_balance"
    CAP_AT_EXPLICIT_AVAILABLE_CASH = "cap_at_explicit_available_cash"


class SeniorReserveTreatment(Enum):
    LEGACY = "legacy"
    INCLUDE_DSRA_MOVEMENTS = "include_dsra_movements"
    EXCLUDE_RESERVE_MOVEMENTS = "exclude_reserve_movements"
```

### Proposed Dataclass

```python
@dataclass(frozen=True)
class SeniorSculptingConfig:
    enabled: bool = False
    mode: SeniorSculptingMode = SeniorSculptingMode.LEGACY
    target_dscr_schedule: tuple[float, ...] = ()
    available_senior_cfads_schedule: tuple[float, ...] = ()
    explicit_debt_service_schedule: tuple[float, ...] = ()
    explicit_principal_schedule: tuple[float, ...] = ()
    final_repayment_policy: SeniorFinalRepaymentPolicy = (
        SeniorFinalRepaymentPolicy.LEGACY_RESIDUAL
    )
    principal_cap_policy: SeniorPrincipalCapPolicy = (
        SeniorPrincipalCapPolicy.CAP_AT_OPENING_BALANCE
    )
    reserve_treatment: SeniorReserveTreatment = SeniorReserveTreatment.LEGACY
```

### Flag

Use a separate project/input flag:

```python
use_senior_sculpting_basis_engine: bool = False
```

When false, the current senior debt path must be bit-identical.

## Mode Semantics

### `LEGACY`

Use current senior sculpting behavior exactly.

### `EXPLICIT_DEBT_SERVICE_SCHEDULE`

Use an explicit total senior debt service schedule:

```text
interest[t] = opening_balance[t] * period_rate[t]
principal[t] = min(opening_balance[t], max(0, explicit_ds[t] - interest[t]))
closing[t] = opening_balance[t] - principal[t]
```

This is the safest first implementation because it tests cash-flow routing and
amortization shape without re-implementing Excel formulas.

### `EXPLICIT_PRINCIPAL_SCHEDULE`

Use explicit principal values and compute DS as principal plus interest.

This mode is useful for forensic parity but riskier as an operating model
because it bypasses DSCR sizing.

### `EXCEL_AVAILABLE_CFADS`

Use a supplied available senior CFADS / senior DS basis schedule:

```text
available_ds[t] = available_senior_cfads[t] / target_dscr[t]
interest[t] = opening_balance[t] * period_rate[t]
principal[t] = min(opening_balance[t], max(0, available_ds[t] - interest[t]))
```

This is the desired formula-based target, but only after the Excel DS basis rows
are mapped for both TUHO and Oborovo.

## Recommended Safe Implementation Path

### Stage A: Diagnostics Only

Add result-side diagnostics for:

- senior CFADS used for sculpting,
- target DSCR used,
- allowed senior debt service,
- interest,
- implied principal capacity,
- actual principal,
- final repayment residual.

No formula changes.

### Stage B: Explicit Debt-Service Schedule Behind Flag

Implement `EXPLICIT_DEBT_SERVICE_SCHEDULE` behind
`use_senior_sculpting_basis_engine=False` by default.

Purpose:

- prove runtime can consume an explicit senior DS schedule safely,
- preserve opening balance policy,
- observe downstream SHL/distribution effects separately,
- avoid guessing Excel formulas.

### Stage C: Excel-Style Available-CFADS Sculpting Behind Flag

Implement `EXCEL_AVAILABLE_CFADS` only after both projects have validated senior
DS basis schedules.

Purpose:

- replace explicit schedules with formula-driven cash-flow basis,
- test reserve treatment,
- reduce overfitting risk.

### Stage D: Project Factory Opt-In After Full-Period Parity

Only opt in TUHO / Oborovo factories after:

- full senior tenor parity is proven,
- default-off equivalence is protected,
- downstream SHL and distribution changes are measured,
- B2 SHL work remains separate.

## Test Strategy

Required tests for a future implementation:

1. `test_senior_sculpting_flag_defaults_false`
   - default false for all projects.

2. `test_legacy_flag_off_equivalence`
   - TUHO and Oborovo unchanged with config present but flag false.

3. `test_opening_balance_policy_preserved`
   - senior debt remains principal-only.
   - senior IDC and fees are not added.

4. `test_tuho_explicit_senior_ds_schedule_parity`
   - explicit DS schedule reproduces first four periods and final period.
   - closing balances follow expected Excel shape.

5. `test_oborovo_explicit_senior_ds_schedule_parity`
   - same for Oborovo.

6. `test_final_repayment_parity`
   - final principal and final DS match schedule under explicit mode.

7. `test_no_unrelated_runtime_drift`
   - revenue, OPEX, tax, construction diagnostics, R99, sponsor logic unchanged
     except downstream cash effects directly caused by senior DS.

8. `test_no_shl_fcf_waterfall`
   - SHL mechanics remain unchanged.

## Risks

| Risk | Mitigation |
|---|---|
| Overfitting TUHO / Oborovo | Start with explicit schedules only as parity harness, then generalize to available-CFADS mode. |
| Changing cash available to SHL | Keep SHL mechanics unchanged and measure downstream effects separately. |
| Interaction with future B2 SHL `fcf_waterfall` | Do not combine sculpting changes with B2. Rebaseline before B2. |
| Reserve timing ambiguity | Keep reserve treatment explicit in config. |
| Final-period balloon differences | Add a final repayment policy rather than changing residual logic globally. |
| Explicit schedule vs formula tradeoff | Use explicit schedule first for safety, then formula mode after evidence. |
| Multi-lender compatibility | Keep config isolated to senior debt and avoid lender-specific assumptions in core engine. |

## Runtime Fix Recommendation

Do not implement a formula-based sculpting fix yet.

The next implementation should be a default-off explicit senior debt service
schedule mode. This is narrower and safer than trying to infer Excel's DS basis
formula immediately.

Recommended next branch:

```text
phase7k-senior-dscr-sculpting-runtime-flag
```

Initial scope for that branch:

- add `SeniorSculptingConfig`,
- add `use_senior_sculpting_basis_engine=False`,
- implement only `EXPLICIT_DEBT_SERVICE_SCHEDULE`,
- keep project factories flag-off,
- add TUHO / Oborovo test-only explicit schedules,
- verify legacy flag-off equivalence,
- do not implement SHL `fcf_waterfall`.
