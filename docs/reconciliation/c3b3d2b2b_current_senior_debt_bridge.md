# C3B3D2B2B: Current Senior Debt Sizing Bridge

**Status:** R1 — BRIDGE CLOSED  
**Stage:** current-senior-debt-bridge  
**Branch:** stage-c3b3d2b2b-current-senior-debt-bridge  
**Base:** main at `4dfdc3bb579f959ce8e7b7348862a3f6c0e7aacb` (C3B3D2B2A merged)

---

## 1. Objective

Decompose the `CURRENT_GRID0_TO_SOURCE_DEBT_BRIDGE_NOT_YET_CLOSED` gap (+1,066.754 kEUR) between:

| Baseline | Value (kEUR) | Label |
|---|---|---|
| `CURRENT_GRID0_PRODUCTION_CANDIDATE` | 43,919.032698 | Clean engine runtime |
| `SOURCE_EXCEL_SENIOR_DEBT` | 42,852.278763 | DS!D51, source workbook |
| Gap | +1,066.754 | To be decomposed |

The `HISTORICAL_GENERIC_PHASE2C_SCALAR_DIAGNOSTIC` (46,053.402379 kEUR) is the starting point of the C3B2 historical bridge and is NOT used as a baseline here.

---

## 2. Governance

| Constraint | Status |
|---|---|
| No DS25/DS40 period boundary hardcoding | ENFORCED |
| No project-name dispatch | ENFORCED |
| No approved_delta or balancing plug | ENFORCED |
| No calibration of clean engine to source | ENFORCED |
| Protected C3B2 SHA: `f8f244c0...b5add7` | UNCHANGED |
| 13547.2 MUST NOT appear in clean SHL | ENFORCED |
| No DSRA implementation | ENFORCED |
| No production financial-engine modifications | ENFORCED |
| CURRENT_CAUSE_UNRESOLVED (Macro50 mechanism) | RECORDED |

---

## 3. Gate 1: CURRENT_GRID0_RUNTIME_BASELINE_REPRODUCED

The current clean engine is invoked via the production API:

```
create_default_oborovo()
→ build_senior_debt_model_input_from_project_inputs()
→ run_senior_debt_model()
→ sd.diagnostics["final_debt_size_keur"] = 43,919.032698 kEUR
```

Independent backward induction from the captured snapshot reproduces this within < 1e-6 kEUR:

```
BI from snapshot:  43,919.032697 kEUR
Engine actual:     43,919.032698 kEUR
Independence delta: −5.2e-7 kEUR
```

**Classification: CURRENT_GRID0_RUNTIME_BASELINE_REPRODUCED**

---

## 4. Gate 2: SOURCE_SENIOR_DEBT_CAPACITY_REPLAY_PROVEN

Backward induction from committed C3B2 source vectors reproduces the workbook:

```
G4 vector backward induction from DS!row20/22/9/44/6 = 42,852.278763 kEUR
DS!D51 fixture value                                  = 42,852.278763 kEUR
Replay residual                                       = 0.000 kEUR
```

**Classification: SOURCE_SENIOR_DEBT_CAPACITY_REPLAY_PROVEN**

Source vectors used (all from `excel_oborovo_debt_interest_truth.json`):

| Vector | Fixture path | Description |
|---|---|---|
| DS!row20 | `workstream_a.ds_row20_cfads.period_values_keur` | CFADS (Macro50 output) |
| DS!row22 | `workstream_a.ds_row22_dscr_target.period_values` | DSCR target (1.15/1.35) |
| DS!row9 | `workstream_b.period_vectors.row9_ops_flag.period_values` | Ops fraction |
| DS!row44 | `workstream_e.ds_row44_annual_sculpting_rate.period_values` | Annual sculpting rate |
| DS!row6 | `workstream_b.period_vectors.row6_day_frac.period_values` | Day fraction |

---

## 5. One-Factor Counterfactuals from CURRENT_GRID0

Each counterfactual swaps exactly one vector from clean engine to source while holding all others at current engine values.

Period mapping: engine period_index p → source period index (p − 1). The clean engine operates on period_indices [2..29]; source periods are [1..28].

### 5.1 CF1: Source CFADS (DS!row20 / Macro50)

| | Value |
|---|---|
| Baseline (clean engine) | 43,919.033 kEUR |
| CF1 (source CFADS) | 42,852.279 kEUR |
| Delta | −1,066.754 kEUR |
| Classification | `CF1_CFADS_CLOSES_CURRENT_GRID0_TO_SOURCE_BRIDGE` |

**CF1 alone closes the entire +1,066.754 kEUR gap.**

The clean engine uses Phase2A EBITDA − canonical cash_tax as CFADS. The source DS!row20 reflects the Macro50 bank/P90 transformation output, which is lower in later periods.

Per-period CFADS delta profile:
- Early periods (P1–P5): differences < 10 kEUR
- Middle periods (P9–P20): alternating positive/negative (no systematic bias)
- Late periods (P24–P28): clean CFADS consistently higher by 200–900 kEUR

**Macro50 mechanism: BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED**  
The VBA implementation is password-protected (`VBA_IMPLEMENTATION_NOT_VISIBLE`). The Macro50 cell transforms the bank/P90-10Y CFADS scenario. The specific adjustment applied is not decomposed in this stage.  
**BANK_SIZING_SCENARIO_P90_10Y_REVIEWER_CONFIRMED_NOT_COMMITTED**

### 5.2 CF2: DSCR Banding (DS!row22)

| | Value |
|---|---|
| Delta | 0.000 kEUR |
| Classification | `VECTOR_ALREADY_SOURCE_MATCHED` |

The current clean engine already applies the source DSCR banding:
- Periods P1–P24 (engine P2–P25): DSCR = 1.15
- Periods P25–P28 (engine P26–P29): DSCR = 1.35

### 5.3 CF3: Ops Fraction (DS!row9)

| | Value |
|---|---|
| Delta | 0.000 kEUR |
| Classification | `VECTOR_ALREADY_SOURCE_MATCHED` |

The current engine availability fractions already match DS!row9.

### 5.4 CF4: Annual Rate (DS!row44)

| | Value |
|---|---|
| Delta | 0.000 kEUR |
| Classification | `VECTOR_ALREADY_SOURCE_MATCHED` |

The current engine uses DS!row44 per-period rates directly (already source-matched). ACT/360 day-count convention is also already in use.

---

## 6. Sequential Bridge: CURRENT_GRID0 → SOURCE_ALL

| Step | Vector Applied | Cumulative (kEUR) | Step Delta |
|---|---|---|---|
| 0 (baseline) | CURRENT_GRID0 snapshot | 43,919.033 | — |
| 1 | CF1: Source CFADS (DS!row20) | 42,852.279 | −1,066.754 |
| 2 | CF2: Source DSCR (DS!row22) | 42,852.279 | 0.000 |
| 3 | CF3: Source Ops (DS!row9) | 42,852.279 | 0.000 |
| 4 | CF4: Source Rate (DS!row44) | 42,852.279 | 0.000 |

CF1 accounts for 100% of the total gap. Steps 2–4 contribute zero delta (vectors already matched).

---

## 7. SOURCE_ALL Gate

Apply all source vectors (CF1–CF4 simultaneously):

| | Value |
|---|---|
| SOURCE_ALL capacity | 42,852.278763 kEUR |
| SOURCE_EXCEL_SENIOR_DEBT | 42,852.278763 kEUR |
| Residual | 0.000 kEUR |
| Bridge closed | **TRUE** |

**Verdict: `CURRENT_GRID0_TO_SOURCE_SIZING_INPUT_BRIDGE_CLOSED`**

The sizing input bridge from CURRENT_GRID0 to SOURCE_EXCEL is fully closed. The clean engine, once supplied with source DS!row20 CFADS (Macro50 output), reproduces the Excel senior debt exactly.

---

## 8. CFADS Gap Interpretation

The CFADS gap is the difference between two legitimate representations of project CFADS:

| Representation | Source | Typical late-period range |
|---|---|---|
| Clean engine (Phase2A EBITDA) | `tac.cfads_keur` — EBITDA minus canonical cash tax | Higher (no bank scenario adjustment) |
| Source DS!row20 (Macro50) | Excel bank/P90-10Y scenario output | Lower in late periods |

The clean engine operates with standard Phase2A EBITDA inputs without the Macro50 bank scenario transformation. The Macro50 transformation is specific to the bank sizing scenario and is not implemented in the clean engine (which uses a scenario-neutral CFADS for sizing).

**No calibration of the clean engine to source is performed or proposed here.**  
**No production engine change is made or implied by this diagnostic.**  
The diagnostic identifies the source of the gap for audit purposes only.

---

## 9. Three-Baseline Separation

| Label | Value (kEUR) | Role |
|---|---|---|
| `CURRENT_GRID0_PRODUCTION_CANDIDATE` | 43,919.032698 | Bridge start — clean engine |
| `SOURCE_EXCEL_SENIOR_DEBT` | 42,852.278763 | Bridge target — DS!D51 |
| `HISTORICAL_GENERIC_PHASE2C_SCALAR_DIAGNOSTIC` | 46,053.402379 | Historical only — C3B2 bridge start |

The historical bridge (C3B2: 46,053 → 42,852 = −3,201 kEUR) is distinct from and must not be confused with the current bridge (C3B3D2B2B: 43,919 → 42,852 = −1,067 kEUR).

---

## 10. Acceptance Report (46 items)

**Governance gates:**

1. ✅ CURRENT_GRID0_RUNTIME_BASELINE_REPRODUCED — engine = 43,919.032698 kEUR confirmed
2. ✅ SOURCE_SENIOR_DEBT_CAPACITY_REPLAY_PROVEN — G4 BI = 42,852.278763 = DS!D51
3. ✅ Three baseline authorities distinct and not conflated
4. ✅ No DS25/DS40 hardcoding in module (AST-verified)
5. ✅ No project-name dispatch
6. ✅ No approved_delta / balancing plug (AST-verified)
7. ✅ No calibration of clean engine to source
8. ✅ Protected C3B2 SHA unchanged
9. ✅ 13547.2 not present as literal in module (AST-verified)
10. ✅ No DSRA implementation
11. ✅ No production financial-engine file modifications
12. ✅ CURRENT_CAUSE_UNRESOLVED for Macro50 mechanism — recorded, no false attribution

**Gate 1 (CURRENT_GRID0 baseline):**

13. ✅ engine debt = 43,919.032698 kEUR
14. ✅ snapshot debt ≈ 43,919 (not 46,053)
15. ✅ independent BI from snapshot matches engine < 1e-3 kEUR
16. ✅ 28 active source periods in snapshot
17. ✅ all snapshot CFADS positive
18. ✅ all snapshot rates positive
19. ✅ all snapshot DSCR >= 1.15

**Gate 2 (source capacity replay):**

20. ✅ source capacity BI matches DS!D51 within 1 kEUR
21. ✅ source capacity matches SOURCE_EXCEL_SENIOR_DEBT_KEUR constant
22. ✅ source vectors cover 28 periods
23. ✅ DSCR banding: 1.15 P1–P24, 1.35 P25–P28
24. ✅ all source CFADS positive
25. ✅ DS!D51 fixture = 42,852.278763 kEUR

**CF1 (source CFADS):**

26. ✅ CF1 moves debt to ~42,852 — closes gap
27. ✅ CF1 delta = −1,066.754 kEUR (matches gap constant)
28. ✅ CF1 classified as real difference (not VECTOR_ALREADY_SOURCE_MATCHED)
29. ✅ source CFADS total < clean CFADS total
30. ✅ late-period CFADS differences > 100 kEUR max

**CF2–CF4 (already matched vectors):**

31. ✅ CF2 (DSCR) delta = 0.000 kEUR — VECTOR_ALREADY_SOURCE_MATCHED
32. ✅ CF2 classification = VECTOR_ALREADY_SOURCE_MATCHED
33. ✅ engine DSCR matches source DS!row22 for all 28 periods
34. ✅ CF3 (ops) delta = 0.000 kEUR — VECTOR_ALREADY_SOURCE_MATCHED
35. ✅ CF3 classification = VECTOR_ALREADY_SOURCE_MATCHED
36. ✅ CF4 (rate) delta = 0.000 kEUR — VECTOR_ALREADY_SOURCE_MATCHED
37. ✅ CF4 classification = VECTOR_ALREADY_SOURCE_MATCHED
38. ✅ engine rates match source DS!row44 for all 28 periods

**Sequential bridge:**

39. ✅ bridge has 4 steps
40. ✅ step 1 closes entire gap to ~42,852 kEUR
41. ✅ step 1 delta = −1,066.754 kEUR (full gap)
42. ✅ steps 2–4 each contribute < 1.0 kEUR
43. ✅ final step reaches SOURCE_EXCEL_SENIOR_DEBT within 1 kEUR
44. ✅ step 1 delta > 10× all subsequent steps combined

**SOURCE_ALL gate:**

45. ✅ SOURCE_ALL capacity = 42,852.278763 kEUR (residual = 0.000)
46. ✅ Verdict: `CURRENT_GRID0_TO_SOURCE_SIZING_INPUT_BRIDGE_CLOSED`

---

## 11. Summary Verdict

**`CURRENT_GRID0_TO_SOURCE_SIZING_INPUT_BRIDGE_CLOSED`**

The full +1,066.754 kEUR senior debt sizing gap between CURRENT_GRID0 and SOURCE_EXCEL is explained by a single factor: **CF1 — the CFADS vector (DS!row20 Macro50 output vs clean Phase2A EBITDA)**. All other sizing parameters (rates, DSCR banding, ops fraction, day-count convention) are already source-matched in the current clean engine.

The Macro50 bank/P90 transformation mechanism remains `BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED`. No production engine changes are proposed. No calibration is performed.

**`C3B3D2B2B_CURRENT_SENIOR_DEBT_BRIDGE_CLOSED_READY_FOR_INDEPENDENT_REVIEW`**
