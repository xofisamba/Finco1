# Phase 9: DistributionAccount Design

**Branch:** `phase9-distribution-account-design`
**Base:** `main` (PR #122 merge, SHA `588e266`)
**Date:** 2026-05-20
**Type:** DESIGN ONLY — NO RUNTIME IMPLEMENTATION
**R99/R102:** BLOCKED — design documents future promotion prerequisites

---

## 1. Executive Summary

Phase 9 DistributionAccount design establishes the canonical module layout for
**post-debt-service cash routing** — the missing runtime component that currently
blocks R99/R102 promotion.

- **What this branch delivers:** Design document + gate inventory CSV — zero runtime changes
- **What R99/R102 remains:** BLOCKED (audit-only fields `r99_fcf_for_distribution_keur` and `r102_fcf_for_shl_keur`)
- **Why it matters:** DistributionAccount is the prerequisite for R99/R102 runtime promotion (per G1 rule from Phase 8 closeout)
- **Design-only constraint:** No `DistributionAccount` class is implemented in this branch

---

## 2. Current State and Why DistributionAccount Is Required

### 2.1 What Exists Today

`domain/distribution_account/` contains an **audit stub only**:

```
domain/distribution_account/
├── engine.py      # compute_tuho_r99_input_period() → R99InputResult (audit values)
├── result.py      # R99InputResult dataclass
└── __init__.py    # exports
```

The `compute_tuho_r99_input_period()` function computes:
- `r69_fcf_banks_keur` — FCF for banks (audit bridge)
- `r84_fcf_junior_keur` — FCF after senior DS + DSRA (audit bridge)
- `r98_distribution_account_keur` — distribution account top-up (audit bridge)
- `r99_fcf_for_distribution_keur` — **equity distribution gate (audit only)**
- `r102_fcf_for_shl_keur` — **SHL sweep gate (audit only)**
- `locked` / `lockup_reasons` — lockup gate (audit only)

These values are written to `WaterfallPeriod` attributes but are **not wired** to any
downstream cash router. No equity distributions are paid. No SHL sweep is affected.

### 2.2 What Is Missing

There is **no `DistributionAccount` class** that:

1. Receives post-senior-DS FCF as input
2. Routes residual cash to equity distributions, SHL sweep, and DSRA top-up
3. Applies gate logic (R99 gate, R102 gate, DSCR gate, lockup gate)
4. Produces equity distribution cashflows for the SponsorEngine
5. Wires into `app/waterfall_core.py`

### 2.3 Why This Blocks R99/R102

R99 and R102 are **gate values** — they define the maximum cash available for
distribution or SHL sweep. But gates without a router are inert:

```
Current:
  SeniorDebtEngine → post_senior_cash → waterfall_engine (ad-hoc)
  → r99_fcf_for_distribution_keur = <computed>  [no downstream consumer]
  → r102_fcf_for_shl_keur = <computed>          [no downstream consumer]

After DistributionAccount:
  SeniorDebtEngine → post_senior_cash → DistributionAccount
  → routes equity distribution → SponsorEngine
  → routes SHL sweep → ShlEngine (R102 as runtime input)
  → routes DSRA top-up → DsraEngine
  → routes residual → distribution_account_balance
```

**G1 Rule (Phase 8 closeout):** No R99/R102 runtime promotion without DistributionAccount
implementation. This design fulfills that prerequisite.

---

## 3. Source Ownership Map

### 3.1 Before DistributionAccount (Current)

```
SeniorDebtEngine
  └── post_senior_cash_keur
          └── WaterfallEngine.run_waterfall()
                  ├── [senior debt, SHL, tax, reserves — existing]
                  └── r99_fcf_for_distribution_keur → audit field only
                  └── r102_fcf_for_shl_keur           → audit field only

No module owns equity distribution routing.
No module routes post-SHL cash to equity.
```

### 3.2 After DistributionAccount (Future Promotion)

```
SeniorDebtEngine
  └── post_senior_cash_keur
          └── WaterfallEngine.run_waterfall()
                  ├── [senior debt, SHL, tax, reserves — existing]
                  └── post_senior_cash_keur ─────────────────┐
                                                           ↓
                                              DistributionAccount.compute()
                                                           │
                              ┌────────────────────────────┼────────────────────────────┐
                              ↓                            ↓                            ↓
                    Equity distribution      SHL sweep (R102 input)      DSRA top-up
                    → SponsorEngine          → ShlEngine (runtime)       → DsraEngine
                              │                            │                            │
                              └────────────────────────────┼────────────────────────────┘
                                                           ↓
                                                 closing_distribution_account_balance_keur
```

**Key ownership boundaries preserved:**
- SeniorDebtEngine: does NOT compute distributions or SHL sweep
- ShlEngine: receives post-distribution cash; does NOT own R99 gate
- TaxEngine: independent; owns CIT computation
- DistributionAccount: owns equity distribution routing; does NOT compute senior debt, SHL, tax, or depreciation

---

## 4. R99/R102 Current Audit-Only Status

### 4.1 What R99 and R102 Mean

| Row | Formula | Current field | Status |
|-----|---------|--------------|--------|
| R99 | `max(0, R84 + R98 - SHL_required_cash)` | `r99_fcf_for_distribution_keur` | BLOCKED — audit only |
| R102 | `max(0, R99 - equity_distribution_taken)` | `r102_fcf_for_shl_keur` | BLOCKED — audit only |

R99 is the **equity distribution gate**: if R99 > 0, equity *may* receive a distribution.
R102 is the **SHL sweep gate**: cash swept to SHL principal before it accrues.

### 4.2 Why They Are Blocked

1. **No router exists** — the gate values are computed but no module consumes them
2. **DSCR stability unknown** — distributions change DSCR denominators; ±0.05 threshold not validated
3. **Circular dependency** — R99 → DSCR → debt sizing → FCF → R99 loop not analyzed
4. **Oborovo guard missing** — R99/R102 is TUHO-specific; Oborovo must not apply
5. **SHL sweep not connected** — R102 is not wired as runtime input to ShlEngine

### 4.3 G1 Rule Enforcement

From `docs/phase8_runtime_adapter_closeout.md` §15:
> **G1: No R99/R102 runtime promotion without DistributionAccount implementation.**
> R99/R102 promotion requires a `DistributionAccount` class that routes cash to
> equity, SHL, and DSRA. No exceptions.

This design branch is the prerequisite work for G1 compliance.

---

## 5. Proposed DistributionAccount Module Layout

```
domain/distribution_account/
├── __init__.py           # public exports
├── inputs.py             # DistributionAccountInputs, DistributionAccountPeriodInput
├── result.py             # DistributionAccountResult, DistributionAccountPeriodResult,
│                         # DistributionGateResult, DistributionAuditRow
├── engine.py             # DistributionAccountEngine.compute() — existing audit stub
│                         # + NEW: DistributionAccountEngine class (future implementation)
├── gates.py              # gate evaluation logic (r99_gate, r102_gate, dscr_gate,
│                         #   lockup_gate, cash_gate)
├── audit.py              # DistributionAuditRow dataclass (already exists: domain/distribution_account/audit.py)
└── validation.py         # optional DistributionValidationResult (future)
```

**Phase 9 (this branch):** Design only. Module layout defines where files go.

---

## 6. Proposed Dataclasses and Field Definitions

### 6.1 DistributionAccountInputs

Top-level inputs container (per project run):

```python
@dataclass
class DistributionAccountInputs:
    project_name: str
    periods: list[DistributionAccountPeriodInput]
```

### 6.2 DistributionAccountPeriodInput

Per-period inputs to `DistributionAccountEngine.compute()`:

```python
@dataclass
class DistributionAccountPeriodInput:
    # Period identification
    period_index: int
    operating_period_index: int  # 0 = first operating period
    period_date: date

    # Opening balance
    opening_distribution_account_balance_keur: float  # carried forward

    # Cash available from waterfall
    post_senior_cash_available_keur: float  # R84 equivalent; after senior DS + DSRA

    # SHL required cash (interest + PIK + sweep)
    shl_required_cash_keur: float  # from ShlEngine / waterfall output

    # Debt service
    senior_debt_service_keur: float  # for DSCR computation

    # DSCR
    actual_dscr: float
    target_distribution_dscr: float  # from FinancingParams (e.g., 1.15x)
    lockup_dscr: float  # distributions locked below this

    # TUHO-specific gate inputs (R99 / R102)
    r99_gate_inputs: R99GateInputs
    r102_gate_inputs: R102GateInputs

    # Flags
    enable_r99_r102_runtime: bool = False  # G1 default: always False
    is_tuho: bool = False
    is_oborovo: bool = False

    # DSRA (optional — may not apply to all projects)
    dsra_required_balance_keur: float | None = None
    dsra_current_balance_keur: float | None = None

    # Cash reserve (optional)
    minimum_cash_reserve_keur: float | None = None
```

### 6.3 R99GateInputs

```python
@dataclass
class R99GateInputs:
    cumulative_fcf_keur: float  # cumulative R84 from project start
    senior_debt_outstanding_keur: float  # from SeniorDebtEngine
    shl_balance_keur: float  # from ShlEngine
    dscr: float  # current period DSCR
    year_index: int  # 0 = first period
    senior_tenor_years: int  # lockup active during tenor
```

### 6.4 R102GateInputs

```python
@dataclass
class R102GateInputs:
    r99_result_keur: float  # output of R99 gate
    equity_distribution_taken_keur: float  # how much equity actually took
    shl_balance_keur: float  # current SHL balance
    shl_required_cash_keur: float  # total SHL cash requirement
```

### 6.5 DistributionAccountPeriodResult

```python
@dataclass
class DistributionAccountPeriodResult:
    # Balance movements
    opening_distribution_account_balance_keur: float
    closing_distribution_account_balance_keur: float

    # Cash routing
    cash_available_for_distribution_keur: float  # post-senior cash
    equity_distribution_paid_keur: float  # actual equity distribution
    cash_swept_to_shl_keur: float  # R102 — SHL sweep
    dsra_top_up_keur: float  # DSRA reserve top-up
    cash_retained_keur: float  # residual retained in distribution account

    # Gate results
    r99_gate_passed: bool
    r102_gate_passed: bool
    dscr_gate_passed: bool
    lockup_gate_passed: bool
    cash_sufficient_gate_passed: bool

    # Blocking
    blocked_reason: str  # primary blocker if any gate fails
    warnings: list[str]  # advisory warnings

    # Intermediate diagnostics
    r99_fcf_for_distribution_keur: float  # gate value (audit)
    r102_fcf_for_shl_keur: float  # gate value (audit)
```

### 6.6 DistributionAccountResult

```python
@dataclass
class DistributionAccountResult:
    project_name: str
    period_results: list[DistributionAccountPeriodResult]
    total_equity_distribution_keur: float  # sum across all periods
    total_cash_swept_to_shl_keur: float
    total_dsra_top_up_keur: float
    total_cash_retained_keur: float
    audit_rows: list[DistributionAuditRow]
```

### 6.7 DistributionGateResult

```python
@dataclass
class DistributionGateResult:
    gate_name: str  # "r99" | "r102" | "dscr" | "lockup" | "cash"
    passed: bool
    blocked_reason: str  # human-readable if failed
    inputs: dict  # gate inputs for audit traceability
```

### 6.8 DistributionAuditRow

```python
@dataclass
class DistributionAuditRow:
    period_index: int
    operating_period_index: int
    project_name: str
    period_date: date

    # Balance
    opening_balance_keur: float
    closing_balance_keur: float

    # Cash flows
    equity_paid_keur: float
    shl_sweep_keur: float
    dsra_top_up_keur: float
    cash_retained_keur: float

    # Gate inputs
    r99_gate_inputs: dict
    r102_gate_inputs: dict

    # Gate outputs
    gate_results: list[DistributionGateResult]

    # DSCR
    dscr: float
    target_dscr: float
```

---

## 7. Canonical Cash Routing Order

For each period, `DistributionAccountEngine.compute()` applies the following
**canonical routing order**:

```
Step 1: OPENING BALANCE
    opening = opening_distribution_account_balance_keur

Step 2: CASH AVAILABLE
    available = post_senior_cash_available_keur
              + opening_distribution_account_balance_keur

Step 3: DSRA TOP-UP (if applicable)
    if dsra_current_balance < dsra_required_balance:
        top_up = min(dsra_required_balance - dsra_current, available)
        available -= top_up
        dsra_top_up_keur = top_up

Step 4: SHL REQUIRED CASH (R99 pre-gate)
    R99 pre-gate = max(0, available - shl_required_cash_keur)
    (This mirrors the TUHO Excel: R99 = max(0, R84 + R98 - SHL_required))

Step 5: R99 GATE (TUHO equity distribution gate)
    Apply R99 gate criteria:
    - TUHO lockup (year <= senior_tenor AND conditions met) → R99 = 0
    - DSCR < lockup_dscr → blocked
    - DSCR < target_dscr → blocked (advisory)
    - Negative available → blocked
    If R99 gate FAILS:
        equity_distribution = 0
        r99_fcf_for_distribution_keur = 0
        blocked_reason = primary gate failure
    If R99 gate PASSES:
        equity_distribution = min(R99 pre-gate, available)  [per TUHO Excel]
        r99_fcf_for_distribution_keur = R99 pre-gate

Step 6: R102 GATE (SHL sweep gate)
    R102 = max(0, equity_distribution - equity_distribution_taken)
    R102 represents: cash swept to SHL after equity distribution
    (In current audit-only state: R102 = R99 because no equity distribution is taken)
    Future: R102 = max(0, R99 - equity_actual_taken)

Step 7: RESIDUAL AFTER R99/R102
    residual = available - equity_distribution - cash_swept_to_shl

Step 8: DSRA TOP-UP (already applied in Step 3)

Step 9: CLOSING BALANCE
    closing = opening + residual - cash_swept_to_shl - dsra_top_up
    [Note: residual already excludes equity + SHL sweep]

Step 10: WARNINGS
    - DSCR below target but distribution paid
    - SHL sweep consuming more than R99
    - Negative closing balance (guard)

Step 11: AUDIT ROW
    Emit DistributionAuditRow with all gate inputs/outputs for traceability
```

---

## 8. Gate Logic and Blocked Reasons

### 8.1 R99 Gate (TUHO Equity Distribution Gate)

**Purpose:** Determines whether equity can receive a distribution in this period.

**Inputs:** cumulative FCF, senior debt outstanding, SHL balance, DSCR, year index, tenor

**Blocked Reasons (r99_gate_passed = False):**

| Reason | Condition | TUHO Excel Equivalent |
|--------|-----------|----------------------|
| `dscr_below_lockup` | `dscr < lockup_dscr` | TUHO!DS!R19 lockup |
| `year_zero` | `year_index == 0` | Construction period |
| `negative_available` | `available < 0` | Insufficient cash |
| `dsra_below_target` | `dsra_balance < dsra_target` | DSRA not funded |
| `jdsra_below_target` | `jdsra_balance < jdsra_target` | JDSRA not funded |
| `cumulative_fcf_insufficient` | Future gate | R99 cumulative test |
| `senior_debt_outstanding` | Future gate | R99 senior debt test |

**TUHO Excel mapping:** `compute_tuho_r99_input_period()` in `engine.py` already implements
this logic. The `DistributionAccount` class would invoke this same gate function.

### 8.2 R102 Gate (SHL Sweep Gate)

**Purpose:** Determines whether SHL receives a sweep payment.

**Blocked Reasons (r102_gate_passed = False):**

| Reason | Condition |
|--------|-----------|
| `shl_balance_zero` | `shl_balance_keur <= 0` — nothing to sweep |
| `r99_zero` | `r99_fcf_for_distribution_keur <= 0` — no cash available |
| `shl_already_repaid` | Future gate |
| `sweep_cap_exceeded` | Future gate |

### 8.3 DSCR Gate

**Purpose:** Prevents distributions if DSCR falls below minimum.

| Reason | Condition |
|--------|-----------|
| `dscr_below_target` | `dscr < target_distribution_dscr` |
| `dscr_negative` | `dscr < 0` (guard) |

### 8.4 Lockup Gate

**Purpose:** TUHO lockup during senior tenor (analogous to existing `locked` flag
in `compute_tuho_r99_input_period()`).

**Conditions:**
- `year_index <= senior_tenor_years`
- AND at least one lockup condition is true:
  - DSCR below lockup threshold
  - DSRA below target
  - JDSRA below target

### 8.5 Cash Sufficiency Gate

**Purpose:** Guard against negative cash distributions.

| Reason | Condition |
|--------|-----------|
| `insufficient_cash` | `available < 0` |
| `distribution_exceeds_available` | `equity_distribution > available` |

### 8.6 Oborovo Guard

**Critical:** R99/R102 gates are **TUHO-specific**. Oborovo must not apply them.

```python
if is_oborovo:
    # Skip TUHO-specific gates
    r99_gate_passed = True  # or use Oborovo-specific logic (TBD)
    r102_gate_passed = True
    blocked_reason = "oborovo_guard"
```

This mirrors the Oborovo guard pattern used for `use_tax_bridge_engine`.

---

## 9. R99/R102 Ownership Model

### 9.1 Before Promotion

| Field | Owner | State |
|-------|-------|-------|
| `r99_fcf_for_distribution_keur` | `domain/distribution_account/engine` | Audit only |
| `r102_fcf_for_shl_keur` | `domain/distribution_account/engine` | Audit only |
| `r84_fcf_junior_keur` | `domain/waterfall/waterfall_engine` | Audit bridge |
| `r98_distribution_account_keur` | `domain/waterfall/waterfall_engine` | Audit bridge |

### 9.2 After DistributionAccount Promotion

| Field | Owner | State |
|-------|-------|-------|
| `r99_fcf_for_distribution_keur` | `domain/distribution_account/engine` | Audit + runtime input to DistributionAccount |
| `r102_fcf_for_shl_keur` | `domain/distribution_account/engine` | Audit + runtime input to SHL sweep |
| `equity_distribution_keur` | `domain/distribution_account/` | **New runtime output** |
| `shl_sweep_from_distribution_keur` | `domain/distribution_account/` | **New runtime input to ShlEngine** |
| `distribution_account_balance_keur` | `domain/distribution_account/` | **New runtime field** |

### 9.3 What DistributionAccount Does NOT Own

- Senior debt computation (SeniorDebtEngine)
- SHL interest, PIK, principal computation (ShlEngine)
- CIT computation (TaxBridge)
- Book/tax depreciation (DepreciationEngine / canonical wiring)
- Sponsor IRR computation (SponsorEngine — consumer of equity_distribution_keur)
- Revenue, OPEX, construction (WaterfallEngine)

---

## 10. SeniorDebt / SHL / Tax / Depreciation / Sponsor Boundaries

```
┌──────────────────────────────────────────────────────────────────────┐
│                        SeniorDebtEngine                              │
│  Output: senior_debt_schedule_keur, senior_ds_keur, post_senior_cash │
│  Must NOT: compute distributions, SHL sweep, tax, depreciation        │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │ post_senior_cash_keur
                                  ↓
┌──────────────────────────────────────────────────────────────────────┐
│                      WaterfallEngine                                  │
│  Owns: FCF bridge (R69, R84, R98), reserves, DSRA                    │
│  Calls: TaxBridge, ShlEngine, SeniorDebtEngine                       │
│  Must NOT: route equity distributions (future: DistributionAccount)  │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ↓
┌──────────────────────────────────────────────────────────────────────┐
│                   DistributionAccount (NEW)                           │
│  Input: post_senior_cash_keur, shl_required_cash_keur, DSCR, flags   │
│  Output: equity_distribution_keur, shl_sweep_input_keur,              │
│          dsra_top_up_keur, closing_distribution_account_balance_keur  │
│  Owns: gate evaluation, cash routing order, equity distributions    │
│  Must NOT: compute senior debt, SHL interest/PIK, tax, depreciation  │
└──────────┬───────────────────────────┬───────────────────┬───────────┘
           │                           │                   │
           ↓                           ↓                   ↓
┌──────────────────┐    ┌────────────────────────┐    ┌──────────────┐
│   SponsorEngine  │    │      ShlEngine         │    │  DsraEngine  │
│ (equity IRR etc) │    │ (receives R102 sweep   │    │ (top-up      │
│                  │    │  as runtime input)     │    │  if needed)  │
└──────────────────┘    └────────────────────────┘    └──────────────┘
```

---

## 11. Circular Dependency Analysis

### 11.1 Potential Loop: R99/R102 → DSCR → Debt Sizing → FCF → R99

```
R99 equity distribution → reduces cash held → reduces DSCR denominator
DSCR lower → could reduce debt sizing → reduces senior debt service
Senior debt service lower → more FCF available → R99 higher
R99 higher → more equity distribution → cycle continues
```

### 11.2 Proposed Containment Rule

**Distributions are subordinate to DSCR maintenance.**

1. **DSCR gate first:** If `dscr < target_distribution_dscr`, distribution = 0
   - This breaks the loop: distributions cannot degrade DSCR below target
2. **Lockup gate second:** If `dscr < lockup_dscr` OR DSRA/JDSRA below target, distribution = 0
   - TUHO Excel behavior already encoded in `compute_tuho_r99_input_period()`
3. **No feedback to debt sizing:** Debt sizing uses `sizing_cfads` (independent of distributions)
   - Invariant: `sizing_cfads` ≠ `actual_cfads` (separate inputs)
   - SeniorDebtSizing is calibrated independently from DistributionAccount

### 11.3 SHL Sweep → DistributionAccount Loop

```
DistributionAccount pays SHL sweep → SHL balance decreases
SHL balance lower → SHL required cash lower → R99 higher
R99 higher → more equity distribution → loop
```

**Proposed containment:** R102 (SHL sweep) is computed as `max(0, R99 - equity_taken)`.
SHL sweep reduces SHL balance for *next* period's R102 computation. No within-period
feedback loop because SHL balance update is end-of-period.

---

## 12. Oborovo Guard and Project-Specific Behavior

### 12.1 TUHO-Specific Gates

R99 and R102 are defined in the TUHO Excel model (TUHO!DS!R19 dual-DSCR structure).
They are **not** present in the Oborovo model.

| Project | R99 | R102 | SHL sweep |
|---------|-----|------|-----------|
| TUHO-WIND-1 | ✅ | ✅ | TUHO-specific sweep cap |
| OBOROVO-SOLAR-1 | ❌ N/A | ❌ N/A | No R99 equivalent |

### 12.2 Oborovo Guard Implementation

```python
def compute(inputs: DistributionAccountPeriodInput) -> DistributionAccountPeriodResult:
    if inputs.is_oborovo:
        # Skip TUHO-specific gates
        return _oborovo_distribution(inputs)
```

**Pattern mirrors existing guards:**
- `use_tax_bridge_engine`: raises `ValueError` for Oborovo
- R99/R102: must have similar explicit guard

### 12.3 Oborovo Distribution Behavior (Future Work)

Oborovo distribution routing is **not defined in this design**.
Future branch must specify:
- Oborovo source map for post-senior cash
- Whether Oborovo uses a different gate structure
- SHL sweep behavior for Oborovo

---

## 13. Validation and Audit Export Plan

### 13.1 DistributionAuditRow Export

`DistributionAuditRow` (already exists in `domain/distribution_account/audit.py`)
provides per-period audit output:

```python
# Per period:
audit_row = DistributionAuditRow(
    period_index=period_index,
    operating_period_index=operating_period_index,
    project_name=project_name,
    period_date=period_date,
    opening_balance_keur=opening,
    closing_balance_keur=closing,
    equity_paid_keur=equity_distribution_paid_keur,
    shl_sweep_keur=cash_swept_to_shl_keur,
    dsra_top_up_keur=dsra_top_up_keur,
    cash_retained_keur=cash_retained_keur,
    r99_gate_inputs=r99_gate_inputs_dict,
    r102_gate_inputs=r102_gate_inputs_dict,
    gate_results=[gate_results],
    dscr=actual_dscr,
    target_dscr=target_distribution_dscr,
)
```

### 13.2 CSV Export

Each `DistributionAccountResult` should export to:
```
reports/phase9_distribution_account_audit.csv
```

Columns: `period_index, period_date, project_name, opening_balance_keur,
closing_balance_keur, equity_paid_keur, shl_sweep_keur, dsra_top_up_keur,
cash_retained_keur, r99_gate_passed, r102_gate_passed, dscr_gate_passed,
lockup_gate_passed, dscr, target_dscr, blocked_reason`

### 13.3 R99/R102 Audit Fields Remain Audit-Only

In this branch and in the future Phase 9 implementation branch:
- `r99_fcf_for_distribution_keur` and `r102_fcf_for_shl_keur` remain audit fields
- They are **inputs** to the DistributionAccount gates, not outputs
- The **output** is `equity_distribution_paid_keur` (new field, not yet implemented)

---

## 14. Runtime Promotion Path and Default-Off Flag Strategy

### 14.1 Phased Rollout

```
Phase 1 (THIS BRANCH): Design only
  └── docs/phase9_distribution_account_design.md
  └── reports/phase9_distribution_account_gate_inventory.csv
  └── No implementation files created

Phase 2: Implementation — audit-first
  └── Branch: phase9-distribution-account-implementation-audit-first
  └── Add DistributionAccount class behind default-off flag
  └── enable_r99_r102_runtime = False (audit only)
  └── Validate audit output matches Phase 7F TUHO Excel fixtures
  └── No runtime cash routing activated

Phase 3: Audit-first validation
  └── Validate DistributionAccount audit output vs TUHO Excel
  └── Run full cross-module validation matrix
  └── DSCR stability analysis (+/-0.05 threshold)
  └── Circular dependency analysis

Phase 4: Explicit approval required (G2 rule)
  └── G2: No DistributionAccount implementation without explicit approval
  └── Requires sign-off on DSCR impact, circular dependency containment
  └── G2 approval gate before any flag is set to True

Phase 5: Cross-module validation before runtime activation
  └── Validate SHL sweep receives R102 correctly
  └── Validate SponsorEngine receives equity_distribution correctly
  └── Validate DSRA top-up wired correctly
  └── Validate no regressions in senior debt, tax, depreciation
```

### 14.2 Default-Off Flag Strategy

```python
@dataclass
class DistributionAccountConfig:
    # R99/R102 remains BLOCKED — must be explicitly enabled per G1 rule
    enable_r99_r102_runtime: bool = False  # Default: False (audit only)

    # TUHO-only guard — must be explicitly disabled for Oborovo
    enforce_tuho_gates: bool = True  # Default: True (TUHO projects only)
```

**Invariants:**
- `enable_r99_r102_runtime=False` → DistributionAccount runs in audit-only mode
- `enable_r99_r102_runtime=True` requires G2 explicit approval
- `enforce_tuho_gates=True` + Oborovo → raises `ValueError` (same pattern as TaxBridge)

---

## 15. Gate Matrix / Promotion Prerequisites

| Gate | ID | Current Status | Prerequisite For | Notes |
|------|----|---------------|------------------|-------|
| DistributionAccount class exists | G01 | NOT_STARTED | R99/R102 promotion | Design complete; implementation future |
| R99 gate defined and validated | G02 | READY (in engine.py) | R99 runtime | Already in compute_tuho_r99_input_period() |
| R102 gate defined and validated | G03 | READY (in engine.py) | R102 runtime | Already in compute_tuho_r99_input_period() |
| Equity distribution routing implemented | G04 | NOT_STARTED | R99 runtime | New field equity_distribution_keur |
| SHL sweep receives R102 as runtime input | G05 | NOT_STARTED | R102 runtime | ShlEngine needs R102 input |
| DSCR stability validation (±0.05) | G06 | NOT_STARTED | All runtime | Distributions change DSCR denominator |
| Circular dependency analysis | G07 | NOT_STARTED | All runtime | R99→DSCR→debt sizing→R99 loop |
| Oborovo guard for R99/R102 | G08 | NOT_STARTED | TUHO-only enforcement | Must raise ValueError for Oborovo |
| Oborovo distribution behavior defined | G09 | FUTURE_WORK | Oborovo support | Not defined yet |
| DSRA top-up wiring to DsraEngine | G10 | NOT_STARTED | DSRA top-up runtime | DsraEngine needs distribution_account input |
| Cross-module validation matrix | G11 | READY (Phase 8) | All runtime | PR #117 already passes all combos |
| TaxBridge fixture ledger independence | G12 | READY (Phase 8) | All runtime | TaxBridge owns CIT; independent of DistributionAccount |
| SHL canonical wiring bounded | G13 | READY (Phase 8) | R102 runtime | SHL canonical is post-processing only |
| SeniorDebtSizing is audit-only | G14 | READY (Phase 8) | All runtime | Does not affect post-DS FCF |
| R99/R102 audit vs TUHO Excel | G15 | NOT_STARTED | R99/R102 runtime | Must validate audit values match Excel fixtures |
| Default-off flag added | G16 | NOT_STARTED | All runtime | enable_r99_r102_runtime=False default |
| Explicit G2 approval received | G17 | NOT_STARTED | All runtime | Explicit sign-off required |
| Audit export available | G18 | NOT_STARTED | All runtime | reports/phase9_distribution_account_audit.csv |
| SponsorEngine receives equity distribution | G19 | NOT_STARTED | Sponsor IRR | SponsorEngine needs new input field |
| Phase 8 cross-module validation clean | G20 | READY (Phase 8) | All runtime | PR #117: all combos 0.00 drift |

**Summary:** G01–G07 are BLOCKERS (not started). G08–G10 are NOT_STARTED. G11–G13, G20 are READY.
G14–G19 are NOT_STARTED. R99/R102 remains BLOCKED.

---

## 16. Forbidden Scope and Non-Goals

**This branch is DESIGN ONLY. The following are explicitly NOT in scope:**

| Forbidden | Reason |
|-----------|--------|
| NO `DistributionAccount` class implementation | Future implementation branch only |
| NO R99/R102 runtime promotion | BLOCKED — G1 rule |
| NO changes to `app/waterfall_core.py` | Future wiring branch only |
| NO changes to `domain/waterfall/waterfall_engine.py` | No runtime ownership changes |
| NO changes to `domain/shl/engine.py` | No SHL runtime changes |
| NO changes to `domain/shl/canonical_wiring.py` | No SHL canonical changes |
| NO changes to `domain/tax/tuho_tax_bridge_runtime.py` | TaxBridge independent |
| NO changes to `domain/depreciation/canonical_wiring.py` | Depreciation independent |
| NO changes to `domain/senior_debt_sizing/engine.py` | Senior debt sizing independent |
| NO changes to `domain/sponsor/engine.py` | SponsorEngine is consumer only |
| NO changes to UI, Excel export, or scalar plugs | Non-goals |
| NO Oborovo runtime assumptions | Future work |
| NO DSRA runtime implementation | Future work |
| NO changes to senior debt service computation | SeniorDebtEngine owns this |

---

## 17. Recommended Next Branch

### Option A: `phase9-distribution-account-implementation-audit-first` (Recommended)

**Purpose:** Implement the DistributionAccount class in audit-only mode (flag-default
`enable_r99_r102_runtime=False`). Validate audit output against TUHO Excel fixtures
before any runtime activation.

**Scope:**
- Add `domain/distribution_account/` files: `inputs.py`, `result.py`, `gates.py`
- Add `DistributionAccountEngine` class with `compute()` method
- All outputs go to `DistributionAccountResult` / audit rows
- No runtime cash routing activated
- Add TUHO Excel fixture validation tests

**Constraints:**
- `enable_r99_r102_runtime=False` everywhere
- Zero changes to `app/waterfall_core.py`
- All existing tests pass

### Option B: `phase9-distribution-account-source-map` (If Unresolved Questions)

**Purpose:** If there are unresolved Excel/source-map questions about what cash
flows feed DistributionAccount, resolve them in a separate investigation branch
before implementation.

**Use when:**
- Post-senior cash source is ambiguous
- SHL required cash input definition is unclear
- DSRA top-up logic needs clarification

---

## Appendix A: Key Existing Files

| File | Role |
|------|------|
| `domain/distribution_account/engine.py` | Audit stub computing R99/R102 via `compute_tuho_r99_input_period()` |
| `domain/distribution_account/result.py` | `R99InputResult` dataclass |
| `domain/distribution_account/__init__.py` | Public exports |
| `docs/phase8_runtime_adapter_closeout.md` | Phase 8 freeze + G1-G8 governance rules |
| `docs/phase8_r99_r102_prepromotion_design.md` | R99/R102 semantics + gate matrix |
| `reports/phase8_r99_r102_prepromotion_gate_matrix.csv` | 20-gate prerequisite matrix |
| `docs/phase7l_shl_fcf_waterfall_design_refresh.md` | SHL FCF waterfall design |
| `app/waterfall_core.py` | Orchestrator — R99/R102 currently audit-only here |

## Appendix B: References

| Document | What it covers |
|----------|---------------|
| `docs/phase8_runtime_adapter_closeout.md` | Phase 8 freeze, governance rules G1–G8 |
| `docs/phase8_r99_r102_prepromotion_design.md` | R99/R102 ownership, gate matrix |
| `reports/phase8_r99_r102_prepromotion_gate_matrix.csv` | 20-gate prerequisite matrix |
| `docs/phase7l_shl_fcf_waterfall_design_refresh.md` | SHL FCF waterfall ordering |
| `domain/shl/engine.py` | ShlEngine — SHL interest, PIK, principal |
| `domain/waterfall/waterfall_engine.py` | WaterfallEngine — R69/R84/R98 bridge |

---

## Document History

| Date | Change |
|------|--------|
| 2026-05-20 | Initial design — phase9-distribution-account-design |
