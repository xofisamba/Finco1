# Phase 6 - Interest Limitation / Fiscal Reintegration Design

Branch: `phase6-fiscal-reintegration-design`

Status: design only. No runtime logic, flags, tax formulas, depreciation formulas, R99/R102 source logic, SHL behavior, or project factory behavior is changed by this branch.

## 1. Executive Summary

The latest tax-basis depreciation discovery changes the Phase 6 tax roadmap. The original working hypothesis was that the remaining TUHO cash tax gap was mainly caused by depreciation basis. The forensic result is more precise:

- Python already matches Excel tax depreciation, P&L R31, for TUHO and nearly matches it for Oborovo.
- Python does not yet produce book depreciation, P&L R30, which remains important for P&L and balance sheet reporting.
- The remaining CIT gap is no longer dominated by depreciation. The largest remaining tax blocker is Excel P&L R34 Fiscal Reintegration.
- R34 is an interest limitation / fiscal reintegration mechanism driven by gross SHL interest, EBITDA caps, a 3,000 kEUR absolute cap, and a 4:1 ratio adjustment.
- TUHO and Oborovo use different sign conventions, so sign behavior must be explicit configuration rather than hardcoded tax logic.

This design specifies a future-safe `domain/tax/interest_limitation.py` architecture. The intent is to make the Excel R34/R54 mechanics reproducible offline first, then allow the tax bridge to consume the result in a later default-off runtime path.

Interest limitation should precede depreciation runtime work because Python's tax depreciation is already materially aligned while R34 is not. Depreciation still needs a separate book/tax ledger design, but R34 directly explains the remaining taxable-income bridge and must be isolated before changing CIT runtime behavior.

## 2. Exact Excel Formula Mapping

### 2.1 P&L Flow

Excel P&L calculates EBT broadly as:

```text
 Revenue
- OPEX
- Book depreciation
- Senior interest
- FULL gross SHL interest
= EBT
```

The SHL interest in EBT is the full gross SHL interest before any limitation. Deductibility is then adjusted through P&L R34 Fiscal Reintegration.

### 2.2 Fiscal Reintegration Formula Chain

The reverse-engineered Excel formula chain is:

```text
R34 = -R54

R54 = MIN(MAX(R57, R58) + R59, R27)

R57 = excess SHL interest above 3,000 cap
R58 = excess SHL interest above 30% EBITDA cap
R59 = 4:1 SHL/equity ratio adjustment
R27 = gross SHL interest
```

Expanded:

```text
R57 = IF(BS_R45_gate, MAX(R27 - absolute_cap, 0), 0)

R58 = IF(
    BS_R45_gate,
    MAX(R27 - ebitda_pct_cap * EBITDA, 0),
    0
)

R59 = project-specific ratio adjustment

R54 = MIN(MAX(R57, R58) + R59, R27)
R34 = -R54
```

The EBITDA term is reconstructed inside Excel as:

```text
EBITDA = R32 - R30 + R13
       = EBT - Financial Earnings + Depreciation
       = EBIT + Depreciation
```

This confirms the 30% EBITDA cap is applied to an EBITDA-style measure, not to net income or taxable profit after losses.

### 2.3 TUHO Behavior

TUHO uses:

- R34 = `-R54`.
- R58 becomes active once the BS R45 thin-cap gate is true.
- R59 4:1 ratio adjustment is disabled.
- R34 is negative when R54 is positive.
- This decreases taxable income under the workbook's convention.

This is a non-standard subtractive convention. It is nonetheless the Excel behavior to reproduce. It should not be "corrected" in code without a separate model-owner decision.

### 2.4 Oborovo Behavior

Oborovo uses a different R59 sign and active 4:1 ratio toggle:

- R59 can be negative and effectively disallow full SHL interest.
- R54 becomes negative.
- R34 = `-R54` becomes positive.
- This increases taxable income, the standard addback convention.

Oborovo therefore cannot safely share TUHO's sign semantics.

### 2.5 BS R45 Gate

Excel uses BS R45 as the thin-cap activation gate. The gate is period-specific and must be passed into the interest limitation engine as an input or derived by a separate balance-sheet diagnostics layer.

The first offline implementation should treat the gate as explicit period input, not recompute it internally. Recomputing R45 belongs to a later balance-sheet/tax integration branch.

## 3. Target Architecture

Target tax package structure:

```text
domain/tax/
  tax_engine.py
  reintegration.py
  interest_limitation.py
  loss_carryforward.py
  templates/
    croatia.py
```

Ownership boundaries:

| Module | Owner responsibility | Not owner of |
|---|---|---|
| `tax_engine.py` | Orchestrates tax calculations and exposes runtime-safe tax outputs | Excel row extraction, SHL mechanics, senior debt formulas |
| `reintegration.py` | Combines fiscal reintegration components into taxable income adjustments | Rule-specific calculations that deserve standalone engines |
| `interest_limitation.py` | Computes R57/R58/R59/R54/R34-style interest limitation results | Loss carryforward, depreciation schedules, cash tax timing |
| `loss_carryforward.py` | Rolling 5-year loss buckets, allocation, expiry, FIFO/LIFO policy | Interest limitation amount calculation |
| `templates/croatia.py` | Croatia tax defaults and project-specific tax-rule configuration | Runtime project opt-in |
| `domain/depreciation/` | Future book/tax depreciation schedules | Interest limitation |
| `domain/financial_statements/` | P&L, BS, PF cash waterfall assembly and audit export | Runtime tax source of truth unless explicitly flagged later |

This separation lets Phase 6 build the tax bridge in layers:

```text
SHL and EBITDA inputs
  -> interest_limitation
  -> reintegration / tax bridge
  -> taxable income
  -> loss carryforward
  -> CIT accrual
  -> R67 cash tax timing
  -> R99/R102 diagnostics
```

## 4. Interest Limitation Engine Design

Future file:

```text
domain/tax/interest_limitation.py
```

### 4.1 Enums

```python
class InterestLimitationSignConvention(Enum):
    ADD_BACK = "add_back"
    SUBTRACT_FROM_TI = "subtract_from_ti"


class ThinCapGateMode(Enum):
    ALWAYS_OFF = "always_off"
    ALWAYS_ON = "always_on"
    EXPLICIT_PERIOD_FLAGS = "explicit_period_flags"
    BALANCE_SHEET_R45 = "balance_sheet_r45"
```

### 4.2 Config Dataclass

```python
@dataclass(frozen=True)
class InterestLimitationConfig:
    enabled: bool = False
    absolute_cap_keur: float = 3_000.0
    ebitda_pct_cap: float = 0.30
    ratio_4to1_enabled: bool = False
    ratio_4to1_denom: float = 1.0
    thin_cap_gate_mode: ThinCapGateMode = ThinCapGateMode.EXPLICIT_PERIOD_FLAGS
    sign_convention: InterestLimitationSignConvention = (
        InterestLimitationSignConvention.ADD_BACK
    )
    carryforward_enabled: bool = False
    jurisdiction: str = "HR"
    notes: str = ""
```

### 4.3 Period Input Dataclass

```python
@dataclass(frozen=True)
class InterestLimitationPeriodInput:
    period_index: int
    date: date | None
    gross_shl_interest_keur: float
    ebitda_keur: float
    thin_cap_active: bool
    ratio_adjustment_input_keur: float | None = None
    equity_or_ratio_base_keur: float | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)
```

The first implementation should require `thin_cap_active` explicitly. That keeps the offline R34 parity engine independent of balance-sheet formula risk.

### 4.4 Period Result Dataclass

```python
@dataclass(frozen=True)
class InterestLimitationPeriodResult:
    period_index: int
    gross_shl_interest_keur: float
    ebitda_keur: float
    thin_cap_active: bool
    excess_absolute_cap_keur: float
    excess_ebitda_cap_keur: float
    ratio_adjustment_keur: float
    combined_non_deductible_keur: float
    fiscal_reintegration_keur: float
    taxable_income_adjustment_keur: float
```

Field mapping:

| Result field | Excel equivalent |
|---|---|
| `gross_shl_interest_keur` | R27 |
| `ebitda_keur` | R32 - R30 + R13 |
| `excess_absolute_cap_keur` | R57 |
| `excess_ebitda_cap_keur` | R58 |
| `ratio_adjustment_keur` | R59 |
| `combined_non_deductible_keur` | R54 |
| `fiscal_reintegration_keur` | R34 |
| `taxable_income_adjustment_keur` | Contribution to taxable income |

### 4.5 Aggregate Result Dataclass

```python
@dataclass(frozen=True)
class InterestLimitationResult:
    periods: tuple[InterestLimitationPeriodResult, ...]
    total_gross_shl_interest_keur: float
    total_combined_non_deductible_keur: float
    total_fiscal_reintegration_keur: float
    total_taxable_income_adjustment_keur: float
    config: InterestLimitationConfig
    validation_notes: tuple[str, ...] = ()
```

### 4.6 Core Algorithm

Pseudo-code:

```text
if not config.enabled:
    return zero adjustment audit result

if thin_cap_active:
    excess_absolute = max(gross_shl_interest - config.absolute_cap_keur, 0)
    excess_ebitda = max(gross_shl_interest - config.ebitda_pct_cap * ebitda, 0)
else:
    excess_absolute = 0
    excess_ebitda = 0

ratio_adjustment = compute_ratio_adjustment(...)

combined = min(max(excess_absolute, excess_ebitda) + ratio_adjustment, gross_shl_interest)

if sign_convention == ADD_BACK:
    fiscal_reintegration = abs(combined)
elif sign_convention == SUBTRACT_FROM_TI:
    fiscal_reintegration = -abs(combined)

taxable_income_adjustment = fiscal_reintegration
```

For exact Excel reproduction the engine must also support signed `ratio_adjustment_keur` because Oborovo's R59 is negative. A future implementation may need an `EXCEL_SIGNED_R59` compatibility mode to preserve exact workbook behavior.

## 5. Sign Convention Design

Sign convention is critical and cannot be hardcoded.

### 5.1 Why It Cannot Be Hardcoded

The same workbook row structure gives different effective behavior:

- TUHO: R34 is negative and reduces taxable income.
- Oborovo: R34 is positive and increases taxable income.

A single global "interest limitation addback" assumption would fail one of the projects. The engine must model Excel as configured, not as a generic tax textbook abstraction.

### 5.2 Enum

```python
class InterestLimitationSignConvention(Enum):
    ADD_BACK = "add_back"
    SUBTRACT_FROM_TI = "subtract_from_ti"
```

### 5.3 Runtime Implications

`ADD_BACK`:

- Fiscal reintegration increases taxable income.
- Standard non-deductible interest treatment.
- Required for Oborovo.

`SUBTRACT_FROM_TI`:

- Fiscal reintegration decreases taxable income.
- Non-standard but required to reproduce TUHO Excel.
- Should be documented loudly in audit output.

Every runtime or offline result should expose the sign convention used. The Excel audit export should show both the raw R54-style combined amount and the signed R34 taxable income adjustment.

## 6. Thin-Cap Gate Design

Excel's R57 and R58 are gated by BS R45. The engine should support multiple gate modes:

```python
class ThinCapGateMode(Enum):
    ALWAYS_OFF = "always_off"
    ALWAYS_ON = "always_on"
    EXPLICIT_PERIOD_FLAGS = "explicit_period_flags"
    BALANCE_SHEET_R45 = "balance_sheet_r45"
```

Recommended rollout:

1. Offline engine C1: `EXPLICIT_PERIOD_FLAGS`.
2. Tax bridge consumption E: still prefer explicit/audit gate until BS R45 parity is proven.
3. Later integration: `BALANCE_SHEET_R45` once financial statements balance-sheet rows are accepted as reliable audit inputs.

This avoids creating a hidden dependency from the tax engine back into a balance-sheet row that is itself still under reconciliation.

## 7. EBITDA Limitation Design

Excel reconstructs EBITDA for R58 as:

```text
EBITDA = EBT - Financial Earnings + Depreciation
```

The future engine should receive `ebitda_keur` directly for the first offline implementation. It should not infer EBITDA from P&L fields until financial statements P&L row ownership is stable.

Future extensibility:

- Period-based EBITDA, matching current semiannual workbook logic.
- Annual EBITDA aggregation, if a jurisdiction applies caps annually.
- Jurisdiction-specific EBITDA definitions.
- Exclusions for extraordinary items.
- Alternative ATAD-like caps.

The engine should retain both input EBITDA and computed cap amount in the result so audit users can trace:

```text
R58 = MAX(gross SHL interest - 30% * EBITDA, 0)
```

## 8. Future Carryforward Design

The current Excel files do not carry forward disallowed interest from R34/R54. The design should still leave space for future regimes.

Future options:

```python
class InterestDisallowanceCarryforwardPolicy(Enum):
    NONE = "none"
    FIFO_EXPIRING = "fifo_expiring"
    FIFO_UNLIMITED = "fifo_unlimited"
    LIFO = "lifo"
```

Potential config fields:

```python
carryforward_enabled: bool = False
carryforward_years: int | None = None
carryforward_policy: InterestDisallowanceCarryforwardPolicy = NONE
```

Carryforward should not be implemented in C1 unless Excel evidence requires it. It belongs after exact R34 parity and after the rolling tax loss engine is separated from interest limitation.

## 9. Integration Points

Future integration sequence:

```text
depreciation tax schedule
financial statements P&L rows
SHL gross interest
senior interest
EBITDA
thin-cap gate
    -> interest_limitation
    -> tax_bridge taxable income before losses
    -> loss_carryforward
    -> CIT accrual
    -> R67 cash tax timing
    -> R99/R102 diagnostics
```

Dependencies:

| Dependency | Needed for | Integration rule |
|---|---|---|
| Depreciation module | Book EBITDA, tax depreciation, P&L/BS bridge | Do not block C1 offline R34 parity; pass EBITDA explicitly first |
| Financial statements | P&L R13/R27/R32/R34 audit export | Consume interest limitation result after offline parity |
| SHL engine | Gross SHL interest R27 | Must use full gross SHL interest before limitation |
| Senior debt engine | EBT and financial earnings bridge | No senior formula changes in interest limitation branch |
| Loss carryforward | Taxable profit after losses | Separate Stage D engine |

The interest limitation result should be an audit object until the tax bridge explicitly consumes it behind a default-off flag.

## 10. Runtime Flag Strategy

Current default-off runtime tax flag:

```text
use_tax_bridge_engine = False
```

Future flag:

```text
use_interest_limitation_engine = False
```

Recommended discipline:

- No flag in this design branch.
- C1 offline engine: no runtime flag, no runtime wiring.
- E tax bridge consumption: add or activate flag only when tests prove TUHO/Oborovo R34 parity offline.
- TUHO first runtime rollout.
- Oborovo diagnostic-only initially unless its R34, loss carryforward, and tax bridge parity are proven.
- Default behavior must remain bit-identical when all flags are false.

Unsupported projects should fail closed if a future runtime flag is on without a supported template.

## 11. Offline Engine Acceptance Criteria

Future `phase6-interest-limitation-offline-engine` acceptance:

TUHO:

- R34 within +/- 0.5 kEUR per period.
- R54/R57/R58/R59 audit rows reproduced where source data is available.
- Total R34 within +/- 1.0 kEUR over the operating horizon.
- Sign convention explicitly `SUBTRACT_FROM_TI`.

Oborovo:

- R34 within +/- 0.5 kEUR per period.
- R54/R57/R58/R59 audit rows reproduced where source data is available.
- Total R34 within +/- 1.0 kEUR over the operating horizon.
- Sign convention explicitly `ADD_BACK`.

Regression exclusions:

- No revenue drift.
- No OPEX drift.
- No senior debt drift.
- No SHL runtime drift.
- No construction drift.
- No R99/R102 source acceptance.
- No project factory opt-in.

## 12. Updated Roadmap

Updated Phase 6 roadmap:

| Stage | Branch | Scope | Status |
|---|---|---|---|
| A | `phase6-tax-basis-depreciation-discovery` | Depreciation and fiscal reintegration discovery | Done / source evidence |
| B1 | `phase6-fiscal-reintegration-design` | This design document | This branch |
| B2 | `phase6-depreciation-ledger-design` | Book/tax depreciation ledger design | Next design track |
| C1 | `phase6-interest-limitation-offline-engine` | Offline R34/R54 engine with sign conventions | Recommended next implementation |
| C2 | `phase6-depreciation-offline-engine` | Offline book/tax depreciation engine | After B2 |
| D | `phase6-loss-carryforward-rolling-engine` | 5-year rolling loss buckets | After C1/C2 |
| E | `phase6-tax-bridge-consumes-interest-limitation` | Tax bridge consumes R34 output behind flag | After offline parity |
| F | `phase6-bs-consumes-depreciation` | BS consumes book depreciation | After depreciation parity |
| G | `phase6-r99-runtime-source-from-tax-bridge` | R99 runtime source from accepted tax bridge | After tax bridge parity |
| H | `phase6-tuho-factory-opt-in` | TUHO opt-in to accepted engines | Final controlled rollout |

Critical sequencing change: interest limitation comes before depreciation runtime migration because tax depreciation is already aligned and R34 is the primary remaining CIT blocker.

## 13. Scope Discipline

Allowed in this branch:

- `docs/phase6_interest_limitation_design.md`
- Optional docs-contract tests only, if added later.

Explicitly not allowed:

- Runtime code.
- Formula changes.
- New flags.
- Tax behavior changes.
- Depreciation behavior changes.
- SHL changes.
- R99/R102 source changes.
- Project factory changes.
- UI/cache/persistence changes.

## 14. Recommended Next Branch

Recommended next branch:

```text
phase6-interest-limitation-offline-engine
```

Scope:

- Add offline `domain/tax/interest_limitation.py`.
- Add Croatia/TUHO/Oborovo templates.
- Reproduce R34/R54/R57/R58/R59 from explicit period inputs.
- Add TUHO and Oborovo parity tests.
- Keep runtime untouched.
- Keep all flags absent or default-off.

The branch after that should be `phase6-depreciation-ledger-design`, unless the team wants the book/tax depreciation design reviewed before implementing C1.
