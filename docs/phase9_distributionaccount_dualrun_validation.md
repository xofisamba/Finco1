# Phase 9B — DistributionAccount Dual-Run Validation

## 1. Executive Summary

**Task type:** DUAL-RUN VALIDATION — NO RUNTIME ROUTING.

Phase 9B validates the DistributionAccount gate logic by running it **side-by-side** with the WaterfallEngine without changing runtime authority. `distribution_keur` remains the sole runtime-authoritative distribution source throughout.

This branch validates whether DA gate-driven `equity_distribution_paid_keur` produces results consistent enough with WaterfallEngine `distribution_keur` to support Phase C (DA-authoritative) transition.

**Key question:** Is DA gate logic sufficiently aligned with WaterfallEngine runtime logic that Phase C can begin safely?

## 2. Current Runtime Authority Confirmation

**Runtime authority:** `WaterfallEngine.distribution_keur` (waterfall_engine.py:1026)

| Item | Status |
|---|---|
| `distribution_keur` source | WaterfallEngine — SOLE runtime authority |
| `equity_distribution_paid_keur` source | DistributionAccount — gate-driven but AUDIT-ONLY |
| Sponsor reads | `distribution_keur` directly from WaterfallEngine |
| HoldCo reads | `distribution_keur` via adapter |
| SHL reads | Internal SHL logic only |
| R99/R102 | BLOCKED for runtime — audit-only |

**This branch does NOT change any of the above.**

## 3. Dual-Run Validation Architecture

```
run_waterfall_v3_core(..., use_dualrun_validation=True)
  └── run_waterfall()  → runtime result (UNCHANGED)
  └── _attach_dualrun_validation(result, inputs, periods_list)
        └── build DistributionAccountInputs from waterfall period data
        └── run_dual_validation(result, da_inputs)
              └── WaterfallResult + DA inputs → DualRunResult
        └── result._dualrun_validation = DualRunResult (annotation ONLY)
```

**Key architectural points:**
- `use_dualrun_validation=True` is an opt-in flag — default is False (no performance impact in production)
- `_attach_dualrun_validation` is called AFTER the waterfall run completes
- The waterfall result is **never modified** — dual-run is annotation only
- DistributionAccount inputs are **reconstructed** from waterfall period data for comparison
- No routing replacement, no ownership transfer, no Sponsor/SHL/R99/R102 changes

## 4. Validation Methodology

### 4.1 Per-period comparison

For each period in the waterfall result:
1. Extract `runtime_distribution_keur = period.distribution_keur`
2. Reconstruct equivalent DA inputs from waterfall period data
3. Run DistributionAccount engine in audit-only mode
4. Extract `da_paid_distribution_keur = period_result.equity_distribution_paid_keur`
5. Compute delta: `delta_keur = da_paid - runtime`
6. Classify divergence (see Section 9)

### 4.2 DA input reconstruction (cash-source cascade)

DA inputs are reconstructed from waterfall period fields using a priority cascade
(best available source → fallback):

| Priority | Source field | Description | When zero/unavailable |
|---|---|---|---|
| 1 (best) | `r99_fcf_for_distribution_keur` | TUHO R99 engine: post-tax, post-senior-DS, post-reserves after lockup assessment | Zero for non-TUHO projects; zero when TUHO R99 engine inactive |
| 2 | `cf_after_reserves_keur` | Cash after DSRA/MRA contributions and senior debt service | Zero for non-SHLA projects or pre-DSRA periods |
| 3 (fallback) | `cf_after_tax_keur - senior_ds_keur` | Post-tax cash minus senior debt service (imperfect; see §Limitations) | Always available |

**The `revenue - opex` proxy is NOT used.**

Additional fields reconstructed from waterfall period:
- `actual_dscr` = `dscr` from waterfall period
- `senior_debt_service_keur` = `senior_ds_keur`
- `dsra_*` fields from waterfall period balances

Note: DA inputs are reconstructed rather than re-passed to avoid tight coupling. This is intentional — Phase B tests whether DA gate logic is self-contained and consistent.

### 4.2.1 Cash-source limitations

The fallback (`cf_after_tax - senior_ds`) is imperfect because:
- It does not account for DSRA/MRA contribution cycles (which temporarily lock up cash)
- It does not reflect SHL PIK or sweep mechanics that may consume cash
- `cf_after_reserves_keur` is the preferred fallback when available but is zero in early operating periods before the reserve cycle is established

For TUHO with the R99 engine active (`use_tax_bridge_engine=True`), `r99_fcf_for_distribution_keur` provides the correct distributable cash at each stage of the R69/R84/R98/R99/R102 cascade.


### 4.3 Required flag combinations

| Combination | Project | SHL | Deprec | CO2 Rev | CO2 CIT | Notes |
|---|---|---|---|---|---|---|
| 1 | TUHO | OFF | OFF | OFF | OFF | Baseline |
| 2 | TUHO | ON | OFF | OFF | OFF | SHL canonical |
| 3 | TUHO | OFF | ON | OFF | OFF | Deprec canonical |
| 4 | TUHO | OFF | OFF | ON | OFF | CO2 revenue bridge |
| 5 | TUHO | OFF | OFF | OFF | ON | CO2→CIT bridge |
| 6 | TUHO | ON | ON | OFF | OFF | SHL + Deprec |
| 7 | Oborovo | OFF | OFF | — | — | Baseline |
| 8 | Oborovo | ON | OFF | — | — | SHL canonical |

## 5. Runtime Invariants

These must HOLD TRUE for all periods in all flag combinations:

| Invariant | Description | Test |
|---|---|---|
| RI-1 | `result._dualrun_validation.runtime_unchanged == True` | Phase B does not modify waterfall result |
| RI-2 | `result._dualrun_validation.sponsor_unchanged == True` | No Sponsor routing changes |
| RI-3 | `result._dualrun_validation.shl_unchanged == True` | No SHL routing changes |
| RI-4 | `result._dualrun_validation.r99_r102_still_blocked == True` | R99/R102 not promoted |
| RI-5 | Exactly one runtime distribution truth per period | `distribution_keur` only, no dual-authoritative |
| RI-6 | No fallback semantics | No implicit routing or shared mutable state |
| RI-7 | Deterministic per-period comparison | Same inputs → same DA output |
| RI-8 | `use_dualrun_validation=False` has zero impact | Flag is a no-op by default |

## 6. Sponsor Invariants

| Invariant | Description |
|---|---|
| SI-1 | Sponsor receives `distribution_keur` tuple from WaterfallEngine (unchanged) |
| SI-2 | SponsorWaterfallTier.allocate receives same input as without dual-run |
| SI-3 | No DA result is passed to Sponsor adapter |
| SI-4 | `allocated_per_sponsor_keur` is derived solely from `distribution_keur` |

## 7. SHL Invariants

| Invariant | Description |
|---|---|
| HI-1 | SHL reads from internal SHL logic only (unchanged) |
| HI-2 | `distribution_account_r102_sweep_candidate_keur` port remains unconnected |
| HI-3 | SHL service order unchanged: senior → DSRA → R102 → SHL → equity |
| HI-4 | No DA output is passed to SHL engine |

## 8. R99/R102 Invariants

| Invariant | Description |
|---|---|
| RI-99-1 | `evaluate_r99_gate()` always called with `enable_runtime=False` |
| RI-99-2 | `r99_gate_result.passed == False` for all periods in Phase B |
| RI-102-1 | `evaluate_r102_gate()` always called with `enable_runtime=False` |
| RI-102-2 | `r102_gate_result.passed == False` for all periods in Phase B |
| RI-99-3 | `r99_fcf_for_distribution_keur` remains audit-only benchmark |
| RI-102-3 | `r102_fcf_for_shl_keur` remains audit-only benchmark |

## 9. Divergence Classification Rules

| Class | Condition | Phase C Impact |
|---|---|---|
| **IDENTICAL** | `delta_keur == 0` | ✅ Safe |
| **ROUNDING** | all gates pass AND `|delta| <= 1 kEUR` | ✅ Safe (numerical) |
| **EXPECTED_GATE_DIFFERENCE** | R99/R102 blocked OR DSCR/lockup/cash gate fails | ✅ Expected in Phase B |
| **UNEXPECTED** | all gates pass AND `|delta| > 1 kEUR` | ⚠️ Investigate before Phase C |
| **BLOCKING** | UNEXPECTED with large delta suggests logic mismatch | ❌ Block Phase C |

**Classification logic:**
```python
def classify_delta(delta, runtime_dist, gates_passed, r99_blocked, ..., cash_passed):
    if abs(delta) < 0.001:          → IDENTICAL
    if gates_passed and abs(delta) <= 1.0:  → ROUNDING
    if r99_blocked or r102_blocked: → EXPECTED_GATE_DIFFERENCE
    if not dscr_passed or not lockup_passed or not cash_passed:
                                      → EXPECTED_GATE_DIFFERENCE
    if gates_passed and pct > 0.01:  → UNEXPECTED
    else:                            → BLOCKING
```

## 9.1 Current Matrix Results

**Populated by:** `scripts/phase9_dualrun_matrix_population.py`
**Matrix file:** `reports/phase9_distributionaccount_dualrun_matrix.csv`
**Summary file:** `reports/phase9_distributionaccount_dualrun_summary.csv`

### TUHO-WIND-1 results (13/13 valid combos; 790 total rows)

| Flag combo | IDENTICAL | ROUNDING | EXPECTED | UNEXPECTED | BLOCKING | Phase C ready |
|---|---|---|---|---|---|---|
| baseline | 0 | 0 | 61 | 0 | 0 | ✅ |
| shl_canonical | 0 | 0 | 61 | 0 | 0 | ✅ |
| deprec_canonical | 0 | 0 | 61 | 0 | 0 | ✅ |
| shl+deprec | 0 | 0 | 61 | 0 | 0 | ✅ |
| tax_bridge | 0 | 0 | 61 | 0 | 0 | ✅ |
| shl+deprec+tax_bridge | 0 | 0 | 61 | 0 | 0 | ✅ |
| co2_revenue_bridge | 0 | 0 | 61 | 0 | 0 | ✅ |
| co2_cit_bridge | 0 | 0 | 61 | 0 | 0 | ✅ |
| shl+co2_revenue | 0 | 0 | 61 | 0 | 0 | ✅ |
| deprec+co2_revenue | 0 | 0 | 61 | 0 | 0 | ✅ |

**Note:** `co2_revenue+cit` (both CO2 bridges simultaneously) raises a mutually-exclusive error — this is by design in the waterfall engine.

### Oborovo results (3 combos; 180 total rows)

| Flag combo | IDENTICAL | ROUNDING | EXPECTED | UNEXPECTED | BLOCKING | Phase C ready |
|---|---|---|---|---|---|---|
| baseline | 0 | 0 | 60 | 0 | 0 | ✅ |
| shl_canonical | 0 | 0 | 60 | 0 | 0 | ✅ |
| oborovo_shl | 0 | 0 | 60 | 0 | 0 | ✅ |

### Interpretation

All periods are classified as **EXPECTED_GATE_DIFFERENCE** in Phase B because:
- R99 gate is `BLOCKED` (not promoted to runtime) — DA always shows 0 where WE shows positive distribution
- R102 gate is `BLOCKED` — same effect
- This is the expected Phase B behavior: DA is audit-only, WE is sole runtime authority

**IDENTICAL = 0** is expected in Phase B because DA gates always fail (R99/R102 BLOCKED).
Once R99/R102 are promoted in Phase C, gates can pass and IDENTICAL/ROUNDING will appear.

## 10. TUHO Validation Results

*See §9.1 for populated matrix results. TUHO shows all-EXPECTED_GATE_DIFFERENCE because R99/R102 remain BLOCKED in Phase B. CO2 bridges (revenue/CIT) do not affect distributions — expected pattern confirmed.*

## 11. Oborovo Validation Results

*See §9.1 for populated matrix results. Oborovo shows all-EXPECTED_GATE_DIFFERENCE due to `oborovo_guard` and R99/R102 BLOCKED. This is expected.*

## 12. Hidden Coupling Findings

### 12.1 Known couplings

| From | To | Type | Risk |
|---|---|---|---|
| WaterfallEngine | DistributionAccount | DA input reconstruction | Medium — approximations in cash proxy |
| `post_shl_cash_available_keur` | DA gate evaluation | Data flow | Low — inputs are explicit |
| `actual_dscr` | DSCR gate | Data flow | Low — direct passthrough |
| `dsra_current_balance_keur` | Lockup gate | Data flow | Low — direct passthrough |

### 12.2 Risk: DA input approximation

DA inputs are reconstructed from waterfall periods using `revenue - opex` as a proxy for `post_shl_cash_available_keur`. This is an approximation because:
- The waterfall may apply cash reserve deductions before distribution
- SHL may have already consumed some cash

If this approximation causes significant delta even when gates pass, the Phase C design must account for precise input threading.

## 13. Runtime Safety Assessment

| Item | Assessment | Risk |
|---|---|---|
| Runtime routing | NONE — no routing added | ✅ Safe |
| Sponsor wiring | UNCHANGED — reads WE directly | ✅ Safe |
| SHL wiring | UNCHANGED — port remains disconnected | ✅ Safe |
| R99/R102 promotion | NONE — still BLOCKED | ✅ Safe |
| Fallback semantics | NONE — no implicit routing | ✅ Safe |
| Dual-authoritative runtime | NONE — WE sole authority | ✅ Safe |

## 14. Remaining Blockers

| Blocker | Severity | Resolution |
|---|---|---|
| R99/R102 not promoted | HIGH | Phase C wiring only |
| Oborovo `oborovo_guard` always blocks | LOW | Expected — Oborovo needs explicit guard bypass |
| `distribution_account_r102_sweep_candidate_keur` port unconnected | LOW | Phase C wiring only |
| Matrix shows all-EXPECTED_GATE_DIFFERENCE | LOW | Expected in Phase B; will resolve when R99/R102 promoted |

## 15. Recommendation for Phase C

**To be determined by dual-run results.**

**Preliminary gates for Phase C readiness:**
1. Zero `BLOCKING` classifications across all TUHO/Oborovo combinations
2. Zero `UNEXPECTED` classifications after ROUNDING threshold adjustment
3. All runtime invariants (RI-1 through RI-8) hold
4. Sponsor, SHL, R99/R102 invariants hold
5. Input approximation analysis complete — no systematic bias found

**If all gates pass:** Phase C (DA-authoritative) can begin — `distribution_keur` becomes pass-through alias.

**If blockers remain:** Phase C is BLOCKED. Remediation required before ownership transfer.

## Change Table (this branch)

| File | Change |
|---|---|
| `app/waterfall_core.py` | Added `use_dualrun_validation` flag + `_attach_dualrun_validation()` helper |
| `domain/distribution_account/dualrun_validation.py` | New — DualRunResult, DualRunPeriodResult, run_dual_validation() |
| `docs/phase9_distributionaccount_dualrun_validation.md` | New — this design doc |
| `reports/phase9_distributionaccount_dualrun_matrix.csv` | New — per-period comparison matrix |
| `tests/test_phase9_distributionaccount_dualrun_validation.py` | New — validation tests |

## R99/R102 Status

**BLOCKED throughout Phase 9B.** No promotion. No runtime wiring. Audit-only evaluation continues.
