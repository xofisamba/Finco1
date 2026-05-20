# Phase 9 — DistributionAccount Runtime Design

## 1. Executive Summary

`DistributionAccountEngine` is currently **audit-only**. All output fields (`equity_distribution_paid_keur`, `closing_distribution_account_balance_keur`, gate results) are computed but never wired into the runtime waterfall, sponsor allocation, or R99/R102 chains.

This design doc maps the current ownership chain, defines what a runtime-authoritative `DistributionAccount` requires, and identifies the exact promotion preconditions before R99/R102 can safely be promoted to runtime.

**Key conclusion:** `equity_distribution_paid_keur` is structurally hard-coded to `0.0` in the engine. A real runtime path from `DistributionAccountEngine` to `WaterfallEngine` / Sponsor does not exist — only a `distribution_account_r102_sweep_candidate_keur` input exists in `ShlEngine` but is never populated.

## 2. Current Distribution Ownership Flow

### 2a. Runtime waterfall (what actually runs)

```
run_waterfall() [waterfall_engine.py]
  └── distribution_keur set per-period (lines 897–935)
        ├── shl_repayment_method == "fcf_waterfall": dist = fcf_waterfall_result.distribution_keur
        ├── shl_repayment_method == "pik_then_sweep": 3-tier logic → dist
        └── else: 2-tier → dist = max(0, cf_after_reserves)
  └── cf_after_tax = cf_after_reserves - tax
  └── cum_distribution tracks running total
  └── total_distribution_keur = final cum_distribution
```

**Runtime source of distributions:** `cf_after_reserves` (cash after senior debt service, reserves, SHL) → waterfall tier logic → `distribution_keur`. This is NOT from `DistributionAccountEngine`.

### 2b. DistributionAccount (audit-only)

```
DistributionAccountEngine.compute() [engine.py:31]
  └── _compute_period(): equity_distribution_candidate = cash_for_dist
  └── equity_distribution_paid_keur = 0.0 (hard-coded, line 167)
  └── cash_swept_to_shl_keur = 0.0 (hard-coded)
  └── r99_gate_result / r102_gate_result computed but discarded
  └── closing_balance = opening_balance + cash_retained + dsra_top_up
```

**Status:** Audit-only. All outputs are candidate values, never routed to runtime.

### 2c. SHL Engine (runtime, partial DistributionAccount integration)

```
ShlEngine.compute_period() [engine.py:73–78]
  └── r102_candidate = p.distribution_account_r102_sweep_candidate_keur (from period input)
  └── if r102_candidate is not None: available += r102_sweep_applied
```

**Status:** `distribution_account_r102_sweep_candidate_keur` is an input port on `ShlPeriodInput`. It is **never populated** from `waterfall_core.py`. The port exists but is unconnected.

### 2d. Sponsor / waterfall allocation (audit/adapter layer)

```
SponsorWaterfallTier.allocate() [sponsor_waterfall_tier.py]
  └── receives distribution_keur from waterfall result
  └── computes per-sponsor allocation tuples
  └── allocated_per_sponsor_keur: tuple[tuple[str, float], ...]
```

**Status:** Derived from `distribution_keur`. Audit/adapter layer — not authoritative over distribution ownership.

## 3. DistributionAccount Current Role

### 3a. What it computes

| Field | Value | Runtime? |
|---|---|---|
| `equity_distribution_candidate_keur` | `cash_for_dist` (simplified) | ❌ Audit |
| `equity_distribution_paid_keur` | `0.0` (hard-coded) | ❌ Audit |
| `cash_swept_to_shl_keur` | `0.0` (hard-coded) | ❌ Audit |
| `cash_retained_keur` | `min_cash - cash_for_dist` | ❌ Audit |
| `dsra_top_up_keur` | DSRA shortfall | ❌ Audit |
| `r99_gate_result` | Evaluated | ❌ Audit |
| `r102_gate_result` | Evaluated | ❌ Audit |
| `dscr_gate_result` | Evaluated | ❌ Audit |
| `lockup_gate_result` | Evaluated | ❌ Audit |

### 3b. What is NOT wired to runtime

1. `equity_distribution_paid_keur` — never flows to `WaterfallEngine.distribution_keur`
2. Gate results — R99/R102 gate decisions don't override runtime distribution
3. `cash_swept_to_shl_keur` — SHL sweep amount not validated against DistributionAccount candidate
4. `distribution_account_r102_sweep_candidate_keur` — SHL input port exists but is never populated

## 4. Sponsor Tuple Handoff Interaction

### 4a. Current tuple semantics

```python
allocated_per_sponsor_keur: tuple[tuple[str, float], ...]
# Example: (("LP-1", 4800.0), ("GP-1", 1200.0))
```

Each tuple entry is `(sponsor_code, amount_keur)`. The tuple is ordered (LP before GP per waterfall priority).

### 4b. Sponsor → DistributionAccount handoff

**No direct handoff exists today.** The `SponsorWaterfallTier` computes allocations from `distribution_keur` which comes directly from `WaterfallEngine`. There is no `DistributionAccount`-to-Sponsor ownership transfer.

### 4c. All-zero replacement semantics

If `distribution_keur = 0` for all periods (lockup / early tenor), the sponsor allocation tuples will contain zero amounts. This is currently handled implicitly — no explicit fallback rule exists.

## 5. SHL Downstream Dependency Analysis

### 5a. distribution_account_r102_sweep_candidate_keur

**Input port:** `ShlPeriodInput.distribution_account_r102_sweep_candidate_keur: float | None`
**Effect:** When not `None`, adds `r102_sweep_applied` to `available` cash for SHL service (before interest/PIK/principal)
**Current state:** Port exists, always `None` in practice (never wired)
**Dependency:** Requires `DistributionAccountEngine` → runtime wiring → SHL input

### 5b. SHL interaction with DistributionAccount

When `distribution_account_r102_sweep_candidate_keur` is wired and positive:
- SHL receives additional cash (R102 sweep)
- `cash_after_shl` (post-SHL cash) is reduced by the sweep amount
- This affects `distribution_keur` (post-SHL equity distributions)

**Implication:** Wiring `distribution_account_r102_sweep_candidate_keur` requires careful cash ordering analysis:
1. Senior debt service
2. Reserves (DSRA/JDSRA)
3. **R102 sweep from DistributionAccount** ← wire this
4. SHL service (interest + PIK + principal)
5. Equity distributions

## 6. Distribution Runtime-Authoritative Design

### 6a. Source-of-truth fields

**Runtime-authoritative fields (must be produced by runtime code):**

| Field | Source | Owner |
|---|---|---|
| `distribution_keur` | `WaterfallEngine.run_waterfall()` | WaterfallEngine |
| `equity_distribution_paid_keur` | `DistributionAccountEngine._compute_period()` | DistributionAccount |
| `cash_swept_to_shl_keur` | `DistributionAccountEngine._compute_period()` | DistributionAccount |
| `r99_gate_passed: bool` | `DistributionAccountEngine._compute_period()` | DistributionAccount |
| `r102_gate_passed: bool` | `DistributionAccountEngine._compute_period()` | DistributionAccount |

**Audit-only fields (read-only, for comparison):**

| Field | Source |
|---|---|
| `r99_fcf_for_distribution_keur` | Audit computation |
| `r102_fcf_for_shl_keur` | Audit computation |

### 6b. Ownership boundaries

**DistributionAccount owns:**
- Gate evaluation (R99/R102/DSCR/Lockup/Cash)
- `equity_distribution_paid_keur` computation
- `cash_swept_to_shl_keur` computation
- Opening/closing balance tracking

**WaterfallEngine owns:**
- `distribution_keur` per period (runtime)
- Cash ordering (senior → SHL → equity)

**Sponsor owns:**
- Per-sponsor allocation tuples
- `allocated_per_sponsor_keur` from `distribution_keur`

### 6c. Mutation boundaries

- `DistributionAccountEngine` outputs are **frozen dataclasses** — no mutation after creation
- `WaterfallEngine` outputs are **frozen dataclasses** — no mutation after creation
- Bridging must occur via **explicit parameter threading**, not shared mutable state

### 6d. DistributionAccount → Sponsor interface

```
DistributionAccountEngine.compute(DistributionAccountInputs)
  └── → DistributionAccountResult
        ├── equity_distribution_paid_keur (per period)
        └── total_equity_distribution_paid_keur
  └── Sponsor receives DistributionAccountResult
        └── validates equity_distribution_paid_keur against expected distributions
```

### 6e. DistributionAccount → R99/R102 interface

```
DistributionAccountEngine
  └── r99_gate_result.passed: bool
  └── r99_gate_result.blocked_reason: str
  └── r99_fcf_for_distribution_keur
  └── WaterfallEngine
        └── uses r99_gate_passed to determine if distribution is allowed
        └── if not passed: distribution_keur = 0
```

## 7. Audit-Only vs Runtime Fields

### 7a. Audit-only fields (never wired to runtime)

- `r99_fcf_for_distribution_keur` — computed for Excel comparison only
- `r102_fcf_for_shl_keur` — computed for Excel comparison only
- `r99_input_result.*` — full R99InputResult audit row
- All gate `blocked_reason` strings (informational only)

### 7b. Runtime fields (currently wired)

- `distribution_keur` — from WaterfallEngine (2-tier / 3-tier / fcf_waterfall)
- `cf_after_tax` — from TaxEngine
- `cum_distribution_keur` — running total in WaterfallEngine

### 7c. Hybrid fields (not currently wired, candidate for wiring)

- `equity_distribution_paid_keur` — currently always 0.0, candidate for runtime
- `distribution_account_r102_sweep_candidate_keur` — port exists in SHL, needs wiring
- `r99_gate_passed` — gate evaluated but not controlling distribution

## 8. Deterministic Tuple Semantics

### 8a. Sponsor allocation tuple

```python
allocated_per_sponsor_keur: tuple[tuple[str, float], ...]
```

**Rules:**
1. Ordered by waterfall priority (LP before GP)
2. Each entry: `(sponsor_code: str, amount_keur: float)`
3. All amounts must be `>= 0`
4. Sum of amounts must equal `distribution_keur` for the period
5. Tuple length equals number of sponsors with non-zero allocation

### 8b. All-zero replacement semantics

If `distribution_keur == 0` for a period:
- All sponsor tuples for that period should be `(("LP-1", 0.0), ("GP-1", 0.0))`
- An empty tuple `()` is **not permitted** — must preserve sponsor structure

### 8c. Fallback prohibition rules

1. **No implicit zero substitution** — if no distribution is computed, explicit zero tuples must be produced
2. **No silently dropped sponsors** — all sponsors in the waterfall must appear in the tuple
3. **No reordering** — tuple order must match waterfall priority order
4. **No negative amounts** — negative distribution amounts are prohibited

## 9. Fallback Prohibition Rules

1. **No silent fallback to zero** — when `DistributionAccount` gate fails, distribution must be explicitly set to `0`, not implicitly derived from a missing value
2. **No fallback to waterfall-only path** — if `DistributionAccount` is not promoted, runtime distributions must NOT fall back to using `WaterfallEngine.distribution_keur` directly without gate validation
3. **No fallback to sponsor-only path** — sponsor allocation must not proceed without `DistributionAccount`-validated distribution amounts
4. **No implicit SHL sweep** — if `distribution_account_r102_sweep_candidate_keur` is not wired, SHL sweep must use internal logic only, not a guessed fallback value

## 10. actual_cfads vs sizing_cfads Implications

### 10a. sizing_cfads

- Used for **debt sculpting** (senior debt sizing)
- Derived from `ebitda_schedule` (pre-tax)
- **NOT affected** by `DistributionAccount` promotion
- Includes only EBITDA-based cash available for debt service

### 10b. actual_cfads

- Used for **distribution validation** and R99/R102
- Derived from `cf_after_tax` (post-tax, post-debt-service)
- **Affected** by `DistributionAccount` gate decisions
- When `DistributionAccount` gate fails: `actual_cfads < sizing_cfads`

### 10c. R99/R102 interaction

- R99: `fcf_for_distribution = actual_cfads - required_sweeps`
- R102: `fcf_for_shl = actual_cfads - senior_debt_service - required_sweeps`
- If `actual_cfads < sizing_cfads` due to gate failures, R99/R102 may show divergence from sizing

## 11. R99/R102 Dependency Analysis

### 11a. R99 (distribution gate)

**Current:** Audit-only, `r99_fcf_for_distribution_keur` computed in `compute_tuho_r99_input_period()` but not wired to runtime.

**R99 dependencies:**
- `actual_dscr` — from WaterfallEngine
- `target_distribution_dscr` — from inputs
- `r99_gate_passed` — from DistributionAccountEngine gate evaluation
- `enable_r99_r102_runtime` — flag (default False)

**R99 promotion requires:**
- `DistributionAccount` gate evaluation wired to `distribution_keur`
- `actual_cfads` validated against sizing_cfads
- Sponsor tuple semantics validated for zero-distribution periods

### 11b. R102 (SHL sweep gate)

**Current:** Audit-only, `r102_fcf_for_shl_keur` computed but not wired to runtime.

**R102 dependencies:**
- `distribution_account_r102_sweep_candidate_keur` — input to ShlEngine
- `cash_for_shl_service` — from WaterfallEngine
- `shl_balance` — from ShlEngine

**R102 promotion requires:**
- `distribution_account_r102_sweep_candidate_keur` wired from `DistributionAccountEngine` to `ShlPeriodInput`
- SHL cash ordering validated (R102 sweep before SHL service)
- Fallback prohibition rules enforced (None means internal logic only)

## 12. Promotion Dependency Graph

```
[CO2→CIT bridge] ─────────────────┐
                                  ▼
[canonical depreciation as CIT] ──► [TaxEngine authoritative]
                                              │
                                              ▼
[SeniorDebtSizing runtime] ────────────────────►│
                                              │
                                              ▼
                              [DistributionAccount runtime]
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
          [Sponsor tuple              [distribution_account_        [R102 runtime]
           validation]                r102_sweep_candidate wiring]         │
                    │                         │                         │
                    └─────────────────────────┼─────────────────────────┘
                                              ▼
                               [R99 runtime promotion]
                                              │
                                              ▼
                               [R99/R102 → runtime authoritative]
```

## 13. Recommended Promotion Order

| Step | Item | Status | Notes |
|---|---|---|---|
| 0 | CO2→CIT bridge | ✅ DONE (PR #142) | Taxable income CO2-aware |
| 1 | Canonical depreciation as CIT source | ❌ BLOCKED | Must complete before TaxEngine promotion |
| 2 | SeniorDebtSizing runtime | ❌ BLOCKED | Debt sizing must be stable before distribution |
| 3 | `distribution_account_r102_sweep_candidate_keur` wiring | ❌ BLOCKED | SHL port exists but disconnected |
| 4 | `equity_distribution_paid_keur` wired to Sponsor | ❌ BLOCKED | Currently always 0.0 |
| 5 | Sponsor tuple semantics validation | ❌ BLOCKED | Zero-distribution periods, tuple order |
| 6 | R102 runtime (SHL sweep from DistributionAccount) | ❌ BLOCKED | Requires step 3 |
| 7 | R99 runtime (distribution gate from DistributionAccount) | ❌ BLOCKED | Requires steps 4, 5 |
| 8 | R99/R102 → runtime authoritative | ❌ BLOCKED | Requires steps 6, 7 |

## 14. Explicit Blockers

| Blocker | Reason | Required Action |
|---|---|---|
| `equity_distribution_paid_keur` always 0.0 | Engine hard-codes `equity_paid = 0.0` | `_compute_period()` must compute real distribution |
| `distribution_account_r102_sweep_candidate_keur` not wired | SHL input port exists but unconnected | Populate from `DistributionAccountEngine` in `waterfall_core.py` |
| No `DistributionAccount` → `WaterfallEngine` wiring | Two systems are completely disconnected | Explicit parameter threading required |
| Sponsor tuple all-zero semantics undefined | No explicit rule for zero-distribution periods | Add fallback prohibition rules |
| Canonical depreciation not CIT-authoritative | TaxEngine uses legacy depreciation | Must resolve before R99 promotion |

## 15. Final Recommendation

**DistributionAccount cannot safely become runtime-authoritative in this branch.**

Required preconditions not met:
1. `equity_distribution_paid_keur` is structurally hard-coded to `0.0` — not a wiring issue, a logic issue
2. No runtime path from `DistributionAccountEngine` to `WaterfallEngine` exists
3. `distribution_account_r102_sweep_candidate_keur` port is unconnected
4. Sponsor tuple semantics for zero-distribution periods are undefined

**Recommended next branch:** `phase9-distributionaccount-runtime-wiring`
- Fix `equity_paid` computation in `_compute_period()` (replace hard-coded 0.0)
- Wire `distribution_account_r102_sweep_candidate_keur` in `waterfall_core.py`
- Add explicit Sponsor tuple fallback rules
- Add zero-distribution period tests

**Only after governance/design review is clean.**

## Change Table (this branch — design only, no runtime changes)

| File | Change |
|---|---|
| `docs/phase9_distributionaccount_runtime_design.md` | New — this design doc |
| `reports/phase9_distributionaccount_dependency_matrix.csv` | New — dependency matrix |
| `tests/test_phase9_distributionaccount_runtime_design.py` | New — design validation tests |
