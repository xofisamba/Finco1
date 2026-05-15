# Phase 7F - TUHO R99/R102 Input Engine Design

**Date:** 2026-05-14
**Branch:** `phase7f-tuho-distribution-calibration`
**Scope:** Design only; do not implement in this step.

## Goal

Design the smallest TUHO-only engine that produces a Python R99/R102-equivalent
cash input for a future SHL `fcf_waterfall` retry.

Authoritative Excel mapping:

- R99 = R102 = `fcf_for_shl` input / cash available before SHL service.
- R104 = SHL cash outflow after the SHL waterfall.
- R119 = net dividends and remains the official calibration target.

## Why This Is Needed

PR B2 tested a mechanically correct cash-interest-first SHL waterfall, but used:

```text
fcf_for_shl = cf_after_tax_keur - senior_ds_keur
```

That input failed calibration:

- Proxy total gap vs Excel R99/R102: +14,800 kEUR.
- Early PIK-phase excess proxy cash explains about 60% of the SHL peak gap.
- No existing Python field is reliable enough.

Therefore, the next step is not another SHL formula tweak. The model first needs
a TUHO R99/R102 input engine that can feed the later SHL waterfall.

## Non-Goals

- No SHL `fcf_waterfall` implementation.
- No tax engine refactor.
- No revenue engine changes.
- No OPEX engine changes.
- No hardcoded Excel period values.
- No Oborovo factory changes.
- No global behavior change for non-TUHO projects.

## Feature Flag

Add a financing-level feature flag:

```python
use_tuho_r99_input_engine: bool = False
```

Rules:

- Default `False`.
- TUHO opt-in only after validation.
- Oborovo remains unchanged.
- The flag must propagate through `WaterfallRunConfig.from_inputs()` and into
  `run_waterfall_v3_core()` / `run_waterfall()`.
- Because the flag affects waterfall outputs, include it in any cache key or
  config identity path used by the app.

Recommended location:

- `domain.inputs.FinancingParams`
- `app.waterfall_runner.WaterfallRunConfig`
- `app.waterfall_core.run_waterfall_v3_core()`
- `domain.waterfall.waterfall_engine.run_waterfall()`

Do not set the TUHO factory flag to `True` in the first implementation commit
unless the implementation task explicitly asks to validate the engine live. The
safe sequencing is:

1. Add engine and tests with direct/unit invocation.
2. Measure against Excel fixtures.
3. Then opt TUHO in behind the flag.

## Formula Design

### Step 1 - R69 Equivalent

Compute R69 from existing Python components only:

```text
r69_fcf_banks_keur =
    revenue_keur
  - opex_keur
  + local_tax_keur
  + cash_interest_on_reserves_keur
  - corporate_tax_keur
```

Mapping:

| Excel row | Meaning | Python source |
| --- | --- | --- |
| R20 | Operating revenues | `period.revenue_keur` |
| R38 | Operating expenses after bank tax | `-period.opex_keur` |
| R63 | Local / other taxes | default `0.0` unless an existing field exists |
| R66 | Cash interest on reserves | default `0.0` unless an existing field exists |
| R67 | Corporate income tax | `period.tax_keur` as cash tax, subtracted |

Important:

- Use existing values only.
- Do not change how `tax_keur` is computed.
- Do not introduce a new tax basis in this PR.
- Missing R63/R66 components should be explicit named zero inputs in the engine,
  not hidden omissions.

### Step 2 - R84

Compute FCF Junior:

```text
r84_fcf_junior_keur =
    r69_fcf_banks_keur
  - senior_ds_keur
  + dsra_release_or_funding_keur
```

Use existing DSRA movement:

```text
dsra_release_or_funding_keur = dsra_withdrawal_keur - dsra_contribution_keur
```

Current `WaterfallPeriod` exposes `dsra_contribution_keur` and
`dsra_balance_keur`, but not `dsra_withdrawal_keur`. At the integration point in
`waterfall_engine.py`, both `dsra_contrib` and `dsra_withdrawal` exist as local
variables. Use those locals to call the R99 input engine rather than trying to
reconstruct withdrawals from the period object later.

### Step 3 - R98/R100 Carry-Forward

Compute distribution account before lockup:

```text
r98_distribution_account_keur =
    r84_fcf_junior_keur
  + junior_ds_keur
  + reserve_sweep_keur
  + previous_r100_carryforward_keur
```

Initial values for TUHO minimal implementation:

```text
junior_ds_keur = 0.0
reserve_sweep_keur = 0.0
previous_r100_carryforward_keur = prior period r100
```

Carry-forward rule:

```text
if locked:
    r100_carryforward_keur = r98_distribution_account_keur
else:
    r100_carryforward_keur = 0.0
```

Clamp final SHL input, not internal audit rows:

```text
fcf_for_shl_keur = max(0.0, r99_fcf_for_distribution_keur)
```

Do not clamp R98/R100 internally unless Excel logic explicitly requires it.
Negative R98 is a lockup signal and should remain visible in audit output.

### Step 4 - R99/R102

Excel-style lockup:

```text
locked = (
    year_index <= senior_tenor_years
    and (
        dscr < lockup_dscr
        or year_index == 0
        or r98_distribution_account_keur < 0
        or dsra_balance_keur < dsra_target_keur
        or jdsra_balance_keur < jdsra_target_keur
    )
)

if locked:
    r99_fcf_for_distribution_keur = 0.0
    r100_carryforward_keur = r98_distribution_account_keur
else:
    r99_fcf_for_distribution_keur = r98_distribution_account_keur
    r100_carryforward_keur = 0.0

r102_fcf_for_shl_keur = r99_fcf_for_distribution_keur
fcf_for_shl_keur = max(0.0, r102_fcf_for_shl_keur)
```

Notes:

- For TUHO, DSRA target is currently zero because `dsra_months=0`, so DSRA lockup
  should normally be inactive.
- JDSRA is not currently modeled; use `0.0` target and balance unless a real
  project field exists.
- Use the already-computed DSCR from the waterfall loop, not a duplicate DSCR
  calculation.

## Files To Change

Implementation should be docs/tests first, then code:

| File | Change |
| --- | --- |
| `domain/inputs.py` | Add `FinancingParams.use_tuho_r99_input_engine: bool = False`. |
| `app/waterfall_runner.py` | Add matching `WaterfallRunConfig` flag and map from inputs. |
| `app/waterfall_core.py` | Pass the flag into the waterfall engine. |
| `domain/waterfall/waterfall_engine.py` | Add optional R99 input-engine call and output fields. |
| `domain/distribution_account/__init__.py` | New module package. |
| `domain/distribution_account/engine.py` | R99/R102 compute function. |
| `domain/distribution_account/result.py` | `R99InputResult` dataclass. |
| `tests/test_tuho_r99_input_engine.py` | New focused unit/fixture tests. |
| `tests/test_tuho_shl_calibration.py` | Only add/adjust tests if needed for B1 guard; no fcf_waterfall tests yet. |

Optional:

| File | Change |
| --- | --- |
| `app/project_factories.py` | Later opt TUHO into the flag after validation. Do not change Oborovo. |

## Fields Needed

### New Result Dataclass

```python
@dataclass(frozen=True)
class R99InputResult:
    r69_fcf_banks_keur: float
    r84_fcf_junior_keur: float
    r98_distribution_account_keur: float
    r99_fcf_for_distribution_keur: float
    r100_carryforward_keur: float
    r102_fcf_for_shl_keur: float
    fcf_for_shl_keur: float
    locked: bool
    lockup_reasons: tuple[str, ...] = ()
```

### Minimal Period Fields

Add only if needed for tests/export; otherwise keep audit results separate:

```python
r99_fcf_for_distribution_keur: float = 0.0
r102_fcf_for_shl_keur: float = 0.0
distribution_account_carryforward_keur: float = 0.0
distribution_account_locked: bool = False
```

Keep full audit rows in `R99InputResult`, not on every `WaterfallPeriod`, unless
the implementation needs period-level fixture comparison.

## Exact Waterfall Integration Point

Integrate inside `domain/waterfall/waterfall_engine.py`, after these values are
available:

- `revenue_keur`
- `opex_keur`
- `tax_keur`
- `cf_after_tax`
- `senior_ds`
- `dsra_contrib`
- `dsra_withdrawal`
- `dsra_balance`
- `dsra_target`
- `dscr`
- `lockup`

The current loop computes SHL service before DSRA, then computes DSRA and DSCR.
For the R99/R102 engine, the clean integration point is immediately after:

```python
cf_after_reserves = cf_after_ds + dsra_withdrawal - dsra_contrib
dscr = ebitda_minus_tax / senior_ds if senior_ds > 0 else float("inf")
lockup = dscr < lockup_dscr if senior_ds > 0 else False
```

At that point, call:

```python
if use_tuho_r99_input_engine:
    r99_result = compute_tuho_r99_input_period(
        revenue_keur=rev,
        opex_keur=opex_val,
        local_tax_keur=0.0,
        cash_interest_on_reserves_keur=0.0,
        corporate_tax_keur=tax_this_period,
        senior_ds_keur=senior_ds,
        dsra_release_or_funding_keur=dsra_withdrawal - dsra_contrib,
        junior_ds_keur=0.0,
        reserve_sweep_keur=0.0,
        previous_r100_carryforward_keur=r100_carryforward,
        year_index=period.year_index,
        senior_tenor_years=tenor_periods / 2,
        dscr=dscr,
        lockup_dscr=lockup_dscr,
        r98_dsra_balance_keur=dsra_balance,
        r98_dsra_target_keur=dsra_target,
        jdsra_balance_keur=0.0,
        jdsra_target_keur=0.0,
    )
    fcf_for_shl_keur = r99_result.fcf_for_shl_keur
    r100_carryforward = r99_result.r100_carryforward_keur
else:
    fcf_for_shl_keur = max(0.0, cf_after_tax - senior_ds)
```

Important sequencing warning:

- This first engine PR should only measure and expose `fcf_for_shl_keur`.
- It should not change current `pik_then_sweep` SHL behavior unless the task
  explicitly asks to wire it into SHL cash usage.
- Future PR B2 should consume `fcf_for_shl_keur` inside the new `fcf_waterfall`
  SHL method.

## Tests

Create `tests/test_tuho_r99_input_engine.py`.

Required tests:

1. `test_tuho_r99_engine_flag_defaults_false`
   - `create_default_oborovo().financing.use_tuho_r99_input_engine is False`
   - Generic defaults remain false.

2. `test_tuho_r99_engine_does_not_opt_in_until_validated`
   - If implementation phase keeps TUHO disabled initially, assert false.
   - If implementation phase is explicitly asked to opt in, replace with a
     validation test that confirms only TUHO is true.

3. `test_r99_formula_period_without_lockup`
   - Unit test direct helper:
     `r69 = revenue - opex + local_tax + reserve_interest - tax`
     `r84 = r69 - senior_ds + dsra_release_or_funding`
     unlocked `r99 == r98`.

4. `test_r99_formula_lockup_carryforward`
   - When locked, `r99 == 0` and `r100 == r98`.
   - Next unlocked period includes prior `r100`.

5. `test_tuho_r99_total_matches_excel_within_1pct`
   - Excel target: total R99/R102 = 234,745 kEUR.
   - Pass once engine is validated.

6. `test_tuho_r99_selected_periods_match_excel`
   - op_idx `0, 10, 20, 24, 28, 34, 36`
   - Tolerance: +/-100 kEUR.

7. `test_oborovo_unchanged_when_r99_engine_disabled`
   - Compare Oborovo result to pre-change snapshot/tolerance +/-0.01 kEUR.

8. `test_no_shl_fcf_waterfall_added`
   - Ensure implementation PR does not add `fcf_waterfall` enum/method.

Suggested fixture source:

- Use `tests/fixtures/excel_tuho_full_model_extract.json`
- Excel R99 column:
  `period_diagnostic_columns["CF.free_cash_flow_for_distribution_keur"]`

## Risks

| Risk | Why it matters | Mitigation |
| --- | --- | --- |
| R69 mismatch remains | R99 cannot match if the base cash row is wrong. | First acceptance gate is R69/R99 fixture comparison before SHL changes. |
| Corporate tax sign confusion | Excel rows are signed; Python `tax_keur` is positive expense. | Engine API takes positive `corporate_tax_keur` and subtracts it. |
| Hidden DSRA movement | Current period object lacks withdrawal. | Integrate inside waterfall loop where `dsra_withdrawal` local exists. |
| R100 carry-forward semantics | Incorrect carry-forward can shift R99 by period. | Unit test locked and next-unlocked periods separately. |
| Accidentally changing Oborovo | R99 engine is a core waterfall hook. | Default flag false and Oborovo snapshot guard. |
| Recreating PR B2 too early | R99 input must be validated first. | Keep SHL `fcf_waterfall` out of this implementation. |
| Period index/date confusion | Excel fixture includes all operating periods. | Always report `op_idx` and date in tests/failures. |

## Acceptance Criteria

Implementation is acceptable only when:

- Python R99/R102 total is within +/-1% of Excel 234,745 kEUR.
- Selected periods `0, 10, 20, 24, 28, 34, 36` are within +/-100 kEUR.
- Oborovo is unchanged within +/-0.01 kEUR.
- No SHL `fcf_waterfall` code is added.
- No tax engine changes are made.
- No Excel row values are hardcoded into runtime.
- TUHO opt-in happens only after validation, or is explicitly part of the
  implementation task.

## Implementation Readiness

This design is **implementation-ready with one gating condition**:

Before wiring the feature flag into the live TUHO factory, implement the engine
as a direct helper and validate R99/R102 against the Excel fixture. If the helper
does not meet the +/-1% total and selected-period tolerances using existing
components, stop and report the R69 component gap instead of expanding scope into
tax/revenue/OPEX changes.

Recommended PR sequence:

1. **PR C1a - R99 input engine helper and tests**
   - Add feature flag default false.
   - Add helper/result dataclass.
   - Validate direct helper against fixtures.
   - Keep TUHO runtime behavior unchanged unless validation passes.

2. **PR C1b - TUHO opt-in / waterfall audit fields**
   - Enable TUHO flag only if C1a proves the engine matches Excel.
   - Add minimal `WaterfallPeriod` audit fields if needed.
   - Confirm Oborovo unchanged.

3. **PR B2 retry - SHL fcf_waterfall**
   - Reintroduce `fcf_waterfall`.
   - Use `fcf_for_shl_keur` from validated R99/R102 engine.
