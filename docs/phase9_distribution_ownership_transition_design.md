# Phase 9 — Distribution Ownership Transition Design

## 1. Executive Summary

The central remaining structural blocker before any DistributionAccount runtime routing: **dual-ownership risk**.

Today:
- `WaterfallEngine.distribution_keur` is the single runtime-authoritative distribution source
- `DistributionAccount.equity_distribution_paid_keur` is audit-only (now gate-driven per PR #144)
- Sponsor reads `distribution_keur` directly from `WaterfallEngine`
- `distribution_keur` is consumed by Sponsor, HoldCo, and portfolio layers

Future risk: If DistributionAccount runtime routing begins without an ownership transition design, the model will have **two independently-computed distribution truths** — `distribution_keur` (WaterfallEngine) and `equity_distribution_paid_keur` (DistributionAccount). Sponsor and downstream consumers would receive conflicting values.

**This design resolves dual ownership by defining a single runtime-authoritative distribution source and a 4-phase transition plan.**

## 2. Current Runtime Distribution Flow

```
WaterfallEngine.run_waterfall() [waterfall_engine.py:897–935]
  └── distribution_keur = f(cash_after_reserves, shl_repayment_method)
        ├── shl_repayment_method == "fcf_waterfall": dist = fcf_waterfall_result.distribution_keur
        ├── shl_repayment_method == "pik_then_sweep": 3-tier logic → dist
        └── else: 2-tier → dist = max(0, cf_after_reserves)
  └── total_distribution_keur = cumsum(dist per period)
```

`distribution_keur` is set at waterfall_engine.py:1026 and is the **sole authoritative source** for equity distributions in the current runtime.

## 3. Current Sponsor Dependency Flow

```
SponsorProjectAdapter [sponsor_project_adapter.py:107–108]
  └── result = _run_waterfall(proj, engine)
  └── spv_distributions = tuple(p.distribution_keur for p in result.periods)
  └── builds SponsorRunConfig(available_cash_by_period = spv_distributions)
        └── SponsorWaterfallTier.allocate(distribution_keur)
              └── allocated_per_sponsor_keur: tuple[tuple[str, float], ...]
```

**Current contract:** Sponsor receives `distribution_keur` tuple directly from `WaterfallEngine`. No intermediary. No gate validation.

## 4. Current SHL Dependency Flow

```
WaterfallEngine → run_waterfall()
  └── passes period data to ShlEngine [waterfall_engine.py:650+]
        └── ShlPeriodInput.distribution_account_r102_sweep_candidate_keur (port, always None in practice)
```

`distribution_account_r102_sweep_candidate_keur` is defined in `ShlPeriodInput` and `ShlPeriodResult` but **never populated** from `waterfall_core.py`. SHL uses internal logic only.

## 5. Current DistributionAccount Dependency Flow

```
DistributionAccountEngine.compute(DistributionAccountInputs)
  └── equity_distribution_paid_keur = gate-driven (PR #144: all_gates_passed ? candidate : 0.0)
  └── equity_distribution_candidate_keur = cash_for_dist
  └── r99_gate_result / r102_gate_result evaluated (BLOCKED for runtime)
  └── output: DistributionAccountResult (audit-only)
        └── NOT routed to WaterfallEngine
        └── NOT routed to Sponsor
        └── NOT routed to SHL
```

## 6. Current R99/R102 Dependency Flow

```
DistributionAccountEngine
  └── evaluate_r99_gate() — always BLOCKED (enable_r99_r102_runtime=False)
  └── evaluate_r102_gate() — always BLOCKED (enable_r99_r102_runtime=False)
  └── compute_tuho_r99_input_period() — produces R99InputResult (audit only)
        └── r99_fcf_for_distribution_keur (Excel comparison only)
        └── r102_fcf_for_shl_keur (Excel comparison only)
```

## 7. Dual-Ownership Risk Analysis

### 7a. The core risk

If DistributionAccount is wired to runtime WITHOUT an ownership transition plan:

```
Scenario: DistributionAccount produces equity_distribution_paid_keur = 800 kEUR
          WaterfallEngine produces distribution_keur = 1000 kEUR
          Sponsor reads distribution_keur = 1000 kEUR (unchanged wiring)
          But DistributionAccount audit says only 800 kEUR was "paid"
          → Model has two distribution truths, no way to know which is authoritative
```

### 7b. Where dual ownership would manifest

| Consumer | Current source | DA future source | Conflict? |
|---|---|---|---|
| Sponsor | `distribution_keur` | `equity_distribution_paid_keur` | YES if both wired |
| HoldCo | `distribution_keur` | `equity_distribution_paid_keur` | YES if both wired |
| R99 audit | `r99_fcf_for_distribution_keur` | `equity_distribution_paid_keur` | YES if both wired |
| TaxEngine | N/A | N/A | No (CIT-side) |

### 7c. Why the risk is real

`equity_distribution_paid_keur` (PR #144) is now a **real computed value** — it is no longer hardcoded. When all gates pass, it equals `cash_for_dist`. This is economically meaningful. If it is ever wired to runtime without clearing up `distribution_keur`, two different distribution amounts exist simultaneously.

## 8. Future Authoritative Distribution Architecture

### 8a. Single source of truth

**Option A (recommended): DistributionAccount owns distributions**
- `distribution_keur` becomes a **pass-through alias** of `equity_distribution_paid_keur`
- WaterfallEngine computes cash available, DistributionAccount computes what passes gates
- Sponsor reads `equity_distribution_paid_keur` (via `distribution_keur` alias)
- `equity_distribution_paid_keur` is the authoritative field

**Option B: WaterfallEngine keeps ownership**
- DistributionAccount remains fully audit-only
- No runtime routing from DA to WE
- Risk: DA gate logic is never truly validated in production

### 8b. Field fate map (Option A)

| Field | Future status |
|---|---|
| `DistributionAccount.equity_distribution_paid_keur` | **Runtime-authoritative** (renamed `distribution_keur` in result) |
| `WaterfallEngine.distribution_keur` | **Pass-through alias** — reads from DA result |
| `DistributionAccount.equity_distribution_candidate_keur` | Audit-only (theoretical max) |
| `DistributionAccount.r99_gate_result` | Audit-only (R99 not promoted) |
| `DistributionAccount.r102_gate_result` | Audit-only (R102 not promoted) |

### 8c. What does NOT change in Option A

- `WaterfallEngine` cash sweep logic (senior → SHL → equity) remains the same
- SHL service logic remains the same
- TaxEngine remains the same
- Sponsor allocation tier logic remains the same
- HoldCo overlay remains the same

## 9. Transition Phase Design

### Phase A — Audit-Only (NOW, post PR #144)

- `equity_distribution_paid_keur` computed from gate logic (PR #144)
- `distribution_keur` remains sole runtime authority
- Sponsor reads `distribution_keur` from WaterfallEngine
- No routing between DA and runtime
- **Validates:** Gate logic correctness, audit vs Excel comparison

### Phase B — Dual-Run Validation (next)

- Run both WaterfallEngine AND DistributionAccount
- Compare `distribution_keur` vs `equity_distribution_paid_keur` per period
- Log divergence, do not route DA to runtime
- Sponsor still reads `distribution_keur`
- **Validates:** DA gate logic produces same result as WE for passing periods

### Phase C — Runtime-Authoritative DA (requires Phase B clean)

- `equity_distribution_paid_keur` becomes the authoritative distribution source
- `distribution_keur` becomes pass-through alias: `distribution_keur = equity_distribution_paid_keur`
- Sponsor reads `distribution_keur` (now from DA)
- WaterfallEngine still computes cash; DA applies gates
- **Validates:** Sponsor/HoldCo receive DA-authoritative distributions

### Phase D — Legacy Cleanup (after Phase C stable)

- Remove alias pattern, `distribution_keur` removed or deprecated
- `equity_distribution_paid_keur` is the sole field
- All consumers migrated to DA-authoritative path

## 10. Runtime Invariants

1. **Exactly ONE runtime distribution truth per period**
2. **No fallback semantics** — if DA gate fails, distribution = 0, never derived from WE
3. **Deterministic period mapping** — `distribution_keur[i]` corresponds to `period[i]`
4. **Deterministic sign conventions** — distributions >= 0, negative distributions prohibited
5. **Sponsor receives exactly one authoritative value per period**
6. **SHL receives exactly one authoritative sweep value per period**
7. **R99/R102 evaluated exactly once per period**

## 11. Fallback Prohibition Rules

1. **No fallback to WaterfallEngine-only** if DA gate fails — distribution = 0 explicitly
2. **No dual-path** — either DA is authoritative or WE is, never both
3. **No silent alias** — pass-through must be explicit and documented
4. **No implicit routing** — wiring must be explicit parameter threading, not shared mutable state

## 12. Sponsor Runtime Contract

**In Phase C (DA-authoritative):**

```python
# Sponsor reads distribution_keur which is now an alias
spv_distributions = tuple(p.distribution_keur for p in result.periods)
# where p.distribution_keur == p.equity_distribution_paid_keur (aliased)
```

**Sponsor tuple handoff:** `allocated_per_sponsor_keur` continues to be derived from `distribution_keur`. No change to tier allocation logic.

**Zero-distribution periods:** Explicit zero tuples `(("LP-1", 0.0), ("GP-1", 0.0))`, never empty tuple.

## 13. SHL Runtime Contract

**`distribution_account_r102_sweep_candidate_keur`:**
- Phase B: populated from DA, compared against WE internal value, divergence logged
- Phase C: authoritative value from DA wired to `ShlPeriodInput`
- Fallback: if DA not available, SHL uses internal logic (explicit None → internal)

**R102 sweep ordering (confirmed in code):**
1. Senior debt service
2. DSRA/JDSRA reserves
3. **R102 sweep from DA** (new)
4. SHL service (interest → PIK → principal)
5. Equity distributions

## 14. DistributionAccount Runtime Contract

**Phase C inputs required:**
```python
DistributionAccountInputs(
    period_inputs=[
        DistributionAccountPeriodInput(
            post_shl_cash_available_keur=...,  # from WaterfallEngine
            dsra_current_balance_keur=...,
            dsra_required_balance_keur=...,
            actual_dscr=...,  # from WaterfallEngine
            target_distribution_dscr=...,
            senior_tenor_years=...,
            is_oborovo=...,
        )
    ]
)
```

**Phase C outputs:**
```python
DistributionAccountResult(
    period_results=[
        DistributionAccountPeriodResult(
            equity_distribution_paid_keur=...,  # authoritative
            r99_gate_result=...,  # audit only
            r102_gate_result=...,  # audit only
        )
    ]
)
```

## 15. R99/R102 Evaluation Contract

**R99 evaluation:** Gate result evaluated by DA, passed to WE for `distribution_keur` suppression when blocked. Currently BLOCKED for runtime.

**R102 evaluation:** Gate result evaluated by DA, passed to SHL as `distribution_account_r102_sweep_candidate_keur`. Currently BLOCKED for runtime.

**Exactly-once evaluation:** Both gates are evaluated exactly once in DA. No re-evaluation downstream.

## 16. Migration Safety Gates

| Item | Current | Phase B | Phase C | Phase D |
|---|---|---|---|---|
| `distribution_keur` authority | WE (sole) | WE (sole) | DA (alias) | DA (sole) |
| `equity_distribution_paid_keur` | Audit only | Audit + compare | Runtime authority | Sole authority |
| Sponsor wiring | WE directly | WE directly | DA alias | DA direct |
| SHL R102 port | Unconnected | Compare mode | DA wired | DA wired |
| R99 runtime | BLOCKED | BLOCKED | BLOCKED | BLOCKED |
| R102 runtime | BLOCKED | BLOCKED | BLOCKED | BLOCKED |

**Safety gate classification:**

| Item | Classification | Notes |
|---|---|---|
| Phase B dual-run validation | SAFE NOW | No routing, compare only |
| `equity_distribution_paid_keur` gate logic | SAFE NOW | PR #144 complete |
| Phase C DA-authoritative | BLOCKED | Requires Phase B clean |
| SHL R102 wiring | BLOCKED | Requires Phase C |
| R99 runtime | BLOCKED | Requires Phase C + design |
| R102 runtime | BLOCKED | Requires Phase C + design |

## 17. Rollback Strategy

**Phase A → baseline:** Remove gate logic changes (revert PR #144). Not needed — gate logic is backward-compatible.

**Phase B → Phase A:** Stop running DA alongside WE. No routing changes.

**Phase C → Phase B:** Revert alias wiring. `distribution_keur` becomes WE-authoritative again. No data loss since WE was computing throughout.

**No rollback for Phase D** (aggressive cleanup) — by that point Phase C must be stable.

## 18. Recommended Promotion Order

| Step | Phase | Item | Gate | Notes |
|---|---|---|---|---|
| 0 | — | CO2→CIT bridge | ✅ DONE | PR #142 |
| 1 | A | Gate logic fix | ✅ DONE | PR #144 |
| 2 | A | Ownership transition design | THIS DOC | — |
| 3 | B | Dual-run validation wiring | SAFE AFTER design review | Compare WE vs DA per period |
| 4 | B | Divergence analysis + fix | BLOCKED by step 3 | — |
| 5 | C | DA-authoritative wiring | BLOCKED by step 4 | Phase C begins |
| 6 | C | Sponsor reads DA alias | BLOCKED by step 5 | — |
| 7 | C | SHL R102 wiring | BLOCKED by step 5 | — |
| 8 | D | Legacy `distribution_keur` cleanup | BLOCKED by step 6+7 stable | Phase D |

## 19. Explicit Blockers

| Blocker | Resolution |
|---|---|
| Dual-ownership risk | Ownership transition design (this doc) |
| No Phase B validation path | Dual-run wiring (Phase B) |
| SHL R102 port unconnected | Phase B/C wiring |
| Sponsor reads WE directly | Phase C alias wiring |
| R99/R102 not promoted | Separate promotion after Phase C |

## 20. Final Recommendation

**This design resolves the dual-ownership risk.**

The recommended path is **Option A**: DistributionAccount becomes the runtime-authoritative source for distributions, with `distribution_keur` becoming a pass-through alias in Phase C.

**Immediate next step (Phase B):** `phase9-distributionaccount-dualrun-validation`
- Wire DA to run alongside WE in `waterfall_core.py`
- Compare `equity_distribution_paid_keur` vs `distribution_keur` per period
- Log divergences, do not route DA to runtime yet
- Validate that gate-driven DA produces same result as WE when all gates pass

**This design is ready for governance review. No runtime routing until Phase B is clean.**

## Change Table (this branch — design only, no runtime changes)

| File | Change |
|---|---|
| `docs/phase9_distribution_ownership_transition_design.md` | New — this design doc |
| `reports/phase9_distribution_ownership_transition_matrix.csv` | New — ownership transition matrix |
| `tests/test_phase9_distribution_ownership_transition_design.py` | New — design validation tests |
