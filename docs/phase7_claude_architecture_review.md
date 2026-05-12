# Phase 7 Architecture Review — Checkpoint (7A–7E)

**Date:** 2026-05-12
**Status:** All phases merged to `main`
**Test Suite:** 2952 passed | 1 skipped | 1 xfailed

---

## Overview

| Phase | PR | Topic | Status |
|-------|-----|-------|--------|
| 7A | #46 | Sponsor cashflow foundation | ✅ merged |
| 7B | #46 | Sponsor IRR/MOIC | ✅ merged |
| 7C | #50/51/52/53/54 | Waterfall foundation | ✅ merged |
| 7D | #55 | Multi-investor capital stack | ✅ merged |
| 7E | #56 | Persistence foundation | ✅ merged |

---

## 1. Architecture Consistency

### 1.1 Module map

```
domain/sponsor/
  equity_injection.py            # Phase 7A — frozen schema
  sponsor_cashflow_result.py      # Phase 7A — frozen results
  sponsor_cashflow_runner.py      # Phase 7A — pure runner
  sponsor_capital_account.py      # Phase 7A — capital account ledger
  sponsor_irr_result.py           # Phase 7B — frozen IRR/MOIC results
  sponsor_irr_runner.py           # Phase 7B — pure XIRR/MOIC runner
  xirr.py                         # Phase 7B — deterministic XIRR (Newton-Raphson + bisection)
  sponsor_waterfall_tier.py        # Phase 7C — tier schema (TierType, SponsorShare, SponsorWaterfallTier)
  preferred_return_calculator.py   # Phase 7C — PreferredReturnCalculator
  waterfall_runner.py              # Phase 7C — run_waterfall() (single-investor)
  waterfall_allocation_result.py  # Phase 7C — allocation result schemas
  capital_account_tier_annotation.py  # Phase 7C — tier annotation for capital accounts
  investor_registry.py             # Phase 7D — frozen investor registry
  capital_stack.py                 # Phase 7D — capital contribution records
  multi_investor_waterfall_runner.py  # Phase 7D — multi-investor runner

domain/persistence/
  snapshot_base.py                 # Phase 7E — primitives (SnapshotID, validation helpers)
  project_snapshot.py             # Phase 7E — ProjectSnapshot
  scenario_snapshot.py             # Phase 7E — ScenarioSnapshot, InputSnapshot, ResultSnapshot
  sponsor_snapshot.py              # Phase 7E — SponsorSnapshot, registry/stack snapshots
  snapshot_serializer.py           # Phase 7E — deterministic JSON + SHA-256 hashing
  snapshot_store.py                # Phase 7E — SnapshotStore interface + InMemorySnapshotStore
```

### 1.2 Consistency verdict: CLEAN ✅

- All sponsor domain runners are pure functions (no mutation, no I/O)
- All result dataclasses use `@dataclass(frozen=True)`
- All validation in `__post_init__` (or factory methods) — not in runners
- Domain/persistence separation is respected: persistence layer never mutates domain results
- Frozen `CapitalAccountEntry` and `SponsorCapitalAccount`; entries normalized to tuples on construction

### 1.3 Minor consistency notes

1. **`object.__setattr__` in frozen `__post_init__`** — used for tuple normalization in several places (`SponsorCashflowPeriodResult`, `SponsorCapitalAccount`, etc.). This is intentional and correct Python technique for enforcing immutability on `frozen=True` dataclasses. Auditors should understand this is not a mutation vulnerability.

2. **`HoldCoDistributionSchedule` gap (noted in 7AB review, still open)** — `holdco_distribution_by_period` is a raw `tuple[float, ...]` passed into `SponsorCashflowRunnerInputs`. No schema type enforces period alignment, WHT basis, or dividend/opex decomposition. This is a latent source of mis-wiring in future callers. *Recommended for Phase 7F.*

3. **PR #60 fixes (merged 2026-05-12):** GP catch-up threshold now uses `lp_invested_capital_keur`; PROMOTE uses explicit carry split; PREF removed from aggregate cascade. See `docs/phase7f_sponsor_integration_readiness.md` for full status.

---

## 2. Immutability and Audit-Safety

### 2.1 Frozen dataclasses

All result types confirmed frozen:

| Type | Frozen | Notes |
|------|--------|-------|
| `EquityInjection` | ✅ | `frozen=True` |
| `SponsorCashflowPeriodResult` | ✅ | `frozen=True`; `capital_account_balance_keur` uses `_finite` (allows negative in return phase — correct) |
| `SponsorCashflowResult` | ✅ | `frozen=True` |
| `CapitalAccountEntry` | ✅ | `frozen=True` |
| `SponsorCapitalAccount` | ✅ | `frozen=True` |
| `SponsorIrrResult` | ✅ | `frozen=True` |
| `SponsorMoicResult` | ✅ | `frozen=True` |
| `SponsorXirrResult` | ✅ | `frozen=True` |
| `SponsorWaterfallTier` | ✅ | `frozen=True` |
| `PreferredReturnResult` | ✅ | `frozen=True` |
| `WaterfallAllocationResult` | ✅ | `frozen=True` |
| `InvestorRegistry` | ✅ | `frozen=True` |
| `CapitalStack` | ✅ | `frozen=True` |
| All persistence snapshots | ✅ | `frozen=True` |

### 2.2 Audit-safety

- **No mutation of source objects** — `InMemorySnapshotStore.save()` and `load()` both use `deepcopy`; the persistence layer never aliases or mutates domain objects
- **Append-only store** — `SnapshotCorruptedError` raised on overwrite attempt
- **Schema version on every snapshot** — `SCHEMA_VERSION=1` on all types; `SchemaVersionMismatchError` on load of unknown version
- **NaN/Inf rejection** — `reject_nan_inf_float()` and `reject_nan_inf_container()` at construction time for all user-facing inputs in persistence layer
- **`capital_account_balance_keur` fix confirmed** — uses `_finite` (not `_finite_non_negative`), allowing negative balances during return phase. The previous 7AB review concern has been resolved.

---

## 3. Sponsor Cashflow → IRR → Waterfall → Capital Account → Persistence Flow

### 3.1 End-to-end data flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    SponsorCashflowRunnerInputs                   │
│  (investor_id, equity_injections, holdco_distribution_by_period,│
│   holdco_dividend_by_period, wht_rate, period_count)            │
└────────────────────────┬────────────────────────────────────────┘
                       │ run_sponsor_cashflows()
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│                 SponsorCashflowResult                           │
│  period_results[i]:                                             │
│    equity_injected_keur      → MOIC numerator                  │
│    distribution_received_keur → MOIC denominator               │
│    net_cashflow_keur          → XIRR cash flows                │
│    capital_account_balance_keur                                │
└────────┬────────────────────┬────────────────────────────────────┘
         │                    │
         ↓                    ↓
┌──────────────────┐  ┌────────────────────────────────────────────┐
│ run_sponsor_irr()│  │ WaterfallRunnerInputs                      │
│                  │  │  (tiers, available_cash_by_period,         │
│ → SponsorIrrResult│  │   pref_result, cumulative_invested_keur)  │
│   equity_irr     │  └──────────────┬─────────────────────────────┘
│   project_irr    │                 │ run_waterfall()
│   moic           │                 ↓
└──────────────────┘  ┌────────────────────────────────────────────┐
                      │ WaterfallAllocationResult                    │
                      │  period_results[].tier_entries[]           │
                      │    tier_type → capital_account_annotation  │
                      └──────────────┬─────────────────────────────┘
                                     │
                  ┌──────────────────┼──────────────────┐
                  ↓                  ↓                  ↓
          ┌──────────────┐  ┌────────────────┐  ┌─────────────────┐
          │ PerInvestor  │  │ CapitalAccount  │  │ SponsorSnapshot  │
          │ WaterfallResult│ │TierAnnotation   │  │ (Phase 7E)       │
          │ (Phase 7D)   │  │                 │  │                  │
          └──────────────┘  └────────────────┘  └─────────────────┘
```

### 3.2 Preferred Return path

```
PreferredReturnCalculator (Phase 7C)
  Inputs: invested_capital_by_period, hurdle_rate_pa, compounding_convention
  Output: PreferredReturnResult
    ├── total_accrued_pref_keur
    ├── unpaid_pref_balance_keur
    └── entries[].cumulative_distributions_keur  ← waterfall deduction base

  ↓ feeds into WaterfallRunnerInputs.pref_result (single-investor)
  ↓ feeds into PerInvestorWaterfallResult.pref_result (multi-investor, Phase 7D)
```

### 3.3 Multi-investor assembly (Phase 7D — Option A)

Per-investor `PeriodWaterfallResult` fields are all investor-level:

| Field | Formula |
|-------|---------|
| `available_cash_before_tier_keur` | `ownership_pct × aggregate.available_before` |
| `allocated_amount_keur` | `entry.allocation_for(inv_id)` |
| `remaining_cash_after_tier_keur` | `ownership_pct × aggregate.remaining_after` |
| `total_allocated_keur` | sum of investor's own allocations |
| `total_remaining_cash_keur` | `ownership_pct × aggregate.available − investor_total` |

Invariant: `available − allocated = remaining` for every tier, period, investor.

### 3.4 Persistence wiring (Phase 7E)

```
ScenarioSnapshot
  input_snapshot: InputSnapshot (inputs_json + SHA-256 hash)
  result_snapshot: ResultSnapshot (results_json + inputs_hash reference)
  sponsor_snapshot: SponsorSnapshot  [NOT YET in ORM — Phase 7F scope]
    investor_registry: InvestorRegistrySnapshot
    capital_stack: CapitalStackSnapshot
    waterfall_result_json: dict

SnapshotSerializer.compute_hash()  ← content-addressable deduplication key
InMemorySnapshotStore             ← append-only, deepcopy on load
```

---

## 4. Known Gaps Before Phase 7F

### Gap 1: RESIDUAL tier exercised by PR #60 tests ✅ RESOLVED

The aggregate waterfall includes a `RESIDUAL` tier (tier_index=3, post-#60 cascade: `[ROC, GP_CATCH_UP, PROMOTE, RESIDUAL]`). PR #60 added `TestLpGpAllocation.test_residual_split_is_80_20` confirming the RESIDUAL tier allocates 80% to LP, 20% to GP on remaining cash distributions.

### Gap 2: No `HoldCoDistributionSchedule` schema type ⚠️ LOW-MEDIUM

`holdco_distribution_by_period` is a raw `tuple[float, ...]` with no validation wrapper. Callers must know to pass correctly-aligned distributions with the right WHT basis. A thin `HoldCoDistributionSchedule` input type (or at minimum a validated tuple alias) would prevent mis-wiring.

### Gap 3: No golden validation against Excel benchmarks ⚠️ MEDIUM

There is no comparison of sponsor IRR/XIRR against actual Excel outputs for TUHO or Oborovo. The `tests/test_waterfall_golden_validation.py` covers the waterfall but not the sponsor IRR path. Before Phase 8, actual Excel benchmarks should be captured.

### Gap 4: Sponsor IRR XIRR 183-day approximation ⚠️ LOW

`xirr.py` uses `period_index * 183` days as a constant semiannual period. Over 30-year project lives, this accumulates a ~0.8% per-period systematic undershoot vs real calendar semiannual periods. The deviation could shift equity IRR by ~0.1–0.3 pp vs Excel. Should be confirmed against Excel's actual date convention before Phase 8.

### Gap 5: No `balance_at_period()` on `SponsorCapitalAccount` ⚠️ LOW

`SponsorCapitalAccount` has `contributions_by_period` and `distributions_by_period` as read-only properties, but no method to compute the running balance at a given period. The runner computes balances imperatively. A `balance_at_period(period_index) -> float` method would make the capital account self-contained.

### Gap 6: Persistence not integrated with ORM ⚠️ MEDIUM — Phase 7F in progress

`SponsorSnapshot` and related types exist in `domain/persistence/` but are not yet wired to the SQLAlchemy `Project`/`Scenario` models in `persistence/models.py`. The `InputSnapshot` and `ResultSnapshot` ORM models exist but `sponsor_snapshot` has no ORM counterpart. Phase 7F (branch `phase7f-sponsor-integration-readiness`) is scoped to address this gap.

---

## 5. Risks Before Phase 8 Governance/Productization

### Risk 1: `inputs_hash` not validated against actual inputs_json ⚠️ MEDIUM

`InputSnapshot.create()` computes a SHA-256 hash from `inputs_json` and stores it in `inputs_hash`. However, `ResultSnapshot` accepts any `inputs_hash` string at construction time without checking that it matches the `InputSnapshot.inputs_hash` for the same scenario. A bug could store a `ResultSnapshot` with a mismatched `inputs_hash`, breaking cache invalidation.

**Recommendation:** Add a `ResultSnapshot.create()` overload that accepts the corresponding `InputSnapshot` and auto-fills `inputs_hash`, raising if there's a mismatch.

### Risk 2: Bisection iteration count always 0 ⚠️ LOW

`xirr_with_convergence()` returns `iterations=0` when bisection fallback is used. For audit purposes, knowing how hard a non-convergence case was to solve may matter.

### Risk 3: Co-investor has no separate ROC priority ⚠️ MEDIUM (future)

`InvestorRegistry` supports `CO_INVESTOR` role but the waterfall treats co-investors identically to LP (same proportional share). If co-investors require a separate priority ROC tier (before LP ROC), the waterfall tier structure would need redesign. This is a future product decision, not a current bug.

### Risk 4: Exactly 1 GP constraint ⚠️ LOW (future)

`InvestorRegistry` validates exactly 1 GP. Multiple GPs (e.g., multiple institutional sponsors) would require registry and waterfall changes. Current scope matches the project reality (single sponsor), but Phase 8 should consider whether this needs generalization.

### Risk 5: NaN/Inf rejection only in persistence layer ⚠️ LOW

The sponsor domain (`sponsor_cashflow_runner.py`, `sponsor_irr_runner.py`, `waterfall_runner.py`) does not explicitly reject NaN/Inf inputs. If a caller passes NaN values, the computation may produce NaN results silently. The persistence layer rejects NaN/Inf at snapshot creation time — but this means bad data could flow through the model and only be caught at save time.

**Recommendation:** Add NaN/Inf validation in the runner input dataclasses (`SponsorCashflowRunnerInputs`, `WaterfallRunnerInputs`) before Phase 8.

---

## 6. Validation Coverage

### Sponsor domain (Phase 7A–7B)
- ✅ Schema validation on all result types
- ✅ Capital account balance non-negative (fixed to allow negative — now uses `_finite`)
- ✅ `capital_account_balance_keur` allows negative during return phase
- ✅ XIRR deterministic (Newton-Raphson + bisection fallback)
- ✅ MOIC = 1.0 when no distributions
- ✅ Equity IRR undefined (None) when no equity injections
- ⚠️ No golden validation against Excel benchmarks (TUHO/Oborovo)

### Waterfall (Phase 7C)
- ✅ All 5 tier types exercised
- ✅ Tier ordering enforced (lower tier_index = earlier in waterfall)
- ✅ PROMOTE only allocated when cumulative distribution > GP catch-up threshold
- ✅ GP catch-up threshold correctly computed from invested capital + preferred return
- ✅ Capital account tier annotation
- ✅ Audit Excel export with per-tier rows + totals
- ✅ Golden validation tests (2869 → 2952 total)

### Multi-investor (Phase 7D)
- ✅ Exactly 1 GP enforced
- ✅ Ownership sums to 1.0 (±1e-6)
- ✅ LP/GP proportional ROC (single tier, not sequential — correctly prevents first-investor-takes-all)
- ✅ Per-investor allocations isolated (LP≠GP, GP≠LP)
- ✅ Sum of per-investor totals = aggregate total
- ✅ Option A: all per-investor tier fields investor-level (available/allocated/remaining)
- ✅ Cash conservation: `available − allocated = remaining` per investor per tier
- ✅ Preferred return computed independently per investor

### Persistence (Phase 7E)
- ✅ Frozen snapshots on all types
- ✅ Append-only store (overwrite rejected)
- ✅ Schema version enforced on all snapshot types and on store load
- ✅ NaN/Inf rejection (primitives + containers)
- ✅ Deterministic serialization (sorted keys, same object → same bytes)
- ✅ Load returns deep copy (not aliased)
- ✅ SHA-256 content hash on all snapshot types
- ⚠️ `inputs_hash` not cross-validated between InputSnapshot and ResultSnapshot (see Risk 1)

---

## 7. Export/Persistence Consistency

### Audit Excel export (Phase 7C)
- `app/sponsor_waterfall_excel_export.py` — produces waterfall audit sheets with tier rows
- Per-period: available, tier allocation, remaining
- Per-tier totals: LP/GP split
- `total_distributions_keur` reconciliation

**Consistency gap:** The Excel export is currently independent of the persistence layer. `SponsorSnapshot` is not yet wired to any export workflow. Phase 7F should consider whether sponsor waterfall results should be exportable from saved snapshots.

### Persistence → Export gap ⚠️ MEDIUM

```
SponsorSnapshot (domain/persistence/)
    → waterfall_result_json: dict
    → InvestorRegistrySnapshot
    → CapitalStackSnapshot

SponsorWaterfallExcelExporter (app/)
    → reads SponsorWaterfallResult from domain
    → NOT reading from persistence layer
```

Phase 7F should wire the persistence layer as the source for sponsor waterfall Excel exports (save → reload → export from snapshot, not from live memory object).

---

## 8. Recommendations Before Phase 7F

### P0 — Must fix before any production use

1. **Cross-validate `inputs_hash`** — `ResultSnapshot` creation should verify `inputs_hash` matches the corresponding `InputSnapshot` for the same scenario. Prevents cache invalidation bugs.

2. **Add NaN/Inf validation to runner inputs** — `SponsorCashflowRunnerInputs` and `WaterfallRunnerInputs` should reject NaN/Inf at construction time, not just at persistence save time.

### P1 — Should fix before Phase 7F release

3. **`HoldCoDistributionSchedule` input type** — thin validated wrapper for `holdco_distribution_by_period` + `holdco_dividend_by_period` + `holdco_opex_by_period` to prevent mis-wiring by future callers.

4. **Wire sponsor persistence to ORM** — add `SponsorSnapshot` ORM model, add `sponsor_snapshot` FK to `Scenario`, update `ScenarioRepository` save/load.

5. **Add `balance_at_period()` to `SponsorCapitalAccount`** — makes capital account self-contained and queryable without imperative balance tracking.

6. **App/orchestrator wiring** — create `app/sponsor_runner.py` with `SponsorRunConfig`; call `run_multi_investor_waterfall()` from project inputs; wire to Excel export. See `docs/phase7f_sponsor_integration_readiness.md`.

### P2 — Before Phase 8 governance

7. **RESIDUAL tier golden test** — ✅ RESOLVED by PR #60 (`test_residual_split_is_80_20`).

8. **Excel golden validation for sponsor IRR** — capture actual XIRR benchmarks from TUHO/Oborovo Excel model to confirm the 183-day approximation is acceptable.

9. **Co-investor ROC priority decision** — clarify whether CO_INVESTOR requires a separate ROC tier before LP ROC, and design accordingly.

10. **Multiple GP preparation** — document whether the 1-GP constraint is a hard product requirement or a temporary simplification; if the latter, begin registry/waterfall generalization work.

---

## 9. Phase 7 Summary (Updated by PR #60)

| Property | Status |
|----------|--------|
| Architecture consistency | ✅ Clean — pure functions, frozen dataclasses, clean separation |
| Immutability | ✅ All results frozen; persistence append-only; no source mutation |
| Audit-safety | ✅ Schema version, NaN/Inf rejection, SHA-256 hashes, UTC timestamps |
| Data flow completeness | ✅ Sponsor CF → IRR → Waterfall → Capital account → Persistence |
| Multi-investor correctness | ✅ Option A per-investor assembly; LP/GP proportional ROC; GP catch-up GP-only; PROMOTE uses explicit carry split |
| PR #60 fixes | ✅ `lp_invested_capital_keur` added; PREF removed from aggregate; explicit `promote_shares`; `PreferredReturnAllocation.entry_for()` fixed |
| Validation coverage | ✅ 2974 tests; tier ordering, cash conservation, RESIDUAL exercised, GP catch-up GP-only |
| Persistence/domain separation | ✅ Persistence never mutates domain; domain has no persistence deps |
| Export/persistence consistency | ⚠️ Gap — not yet wired; persistence → export path missing |
| Known gaps | 5 identified (1 MEDIUM, 3 LOW, 1 MEDIUM-in-progress) |
| Risks for Phase 8 | 5 identified (1 MEDIUM, 4 LOW) |

**Phase 7 is a solid foundation.** PR #60 resolved the three critical waterfall bugs (GP catch-up threshold, PROMOTE carry economics, PREF double-counting). Remaining gaps are manageable and do not block Phase 7F integration work.
