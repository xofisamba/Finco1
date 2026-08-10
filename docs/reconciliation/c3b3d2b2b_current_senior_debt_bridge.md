# C3B3D2B2B: Current Senior Debt Sizing Bridge

**Status:** R2 — SOURCE-CONTAMINATION FIXED, DAY-FRACTION ARM ADDED, BRIDGE CLOSED  
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
| Gap | +1,066.754 | Decomposed in this stage |

The `HISTORICAL_GENERIC_PHASE2C_SCALAR_DIAGNOSTIC` (46,053.402379 kEUR) is the C3B2 historical baseline and is NOT used here.

---

## 2. R2 Fixes Applied

| R1 issue | R2 fix |
|---|---|
| `capture_current_grid0_snapshot()` read source fixture (day fracs) | Removed: day fracs now derived from `period_day_fraction(period_start, period_end, convention)` |
| No explicit CF3 (day-count) arm | Added CF3: source DS!row6 vs current ACT/360 derived fracs |
| Baseline lock tolerance 5 kEUR (guard) / 1 kEUR (test) | Tightened to 1e-3 kEUR (tight, deterministic solver) |
| Silent `.get(..., default)` for required vector entries | Fail-closed: raises `CURRENT_GRID0_SNAPSHOT_REQUIRED_VECTOR_MISSING` |
| No per-period vector equality gates | Added: DSCR, day-frac, ops, rate each compared per-period |
| CI used `pip install -e ".[dev]"` (no 'dev' extra exists) | Fixed: `pip install -c constraints.txt pytest openpyxl numpy ...` |

---

## 3. Governance

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
| BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED | RECORDED |
| MISSING_GENERIC_BANK_SIZING_CFADS_SCENARIO_LAYER | RECORDED (future architecture) |

---

## 4. Gate 1: CURRENT_GRID0_RUNTIME_BASELINE_REPRODUCED

The current clean engine is invoked via the production API. The snapshot captures all sizing vectors from current runtime only — no source fixture is read.

```
Engine debt:            43,919.032698 kEUR  (locked baseline)
BI from current-only:   43,919.032697 kEUR  (independent)
Independence delta:     < 1e-6 kEUR
Lock tolerance:         1e-3 kEUR

Day-count convention:   ACT_360
Day-frac provenance:    period_day_fraction(period_start, period_end, ACT_360)
                        NOT read from any Excel fixture
```

**Classification: CURRENT_GRID0_RUNTIME_BASELINE_REPRODUCED**

---

## 5. Gate 2: SOURCE_SENIOR_DEBT_CAPACITY_REPLAY_PROVEN

Backward induction from committed C3B2 source vectors:

```
G4 BI from DS!row20/22/9/44/6:  42,852.278763 kEUR
DS!D51 fixture:                  42,852.278763 kEUR
Replay residual:                 0.000 kEUR
```

**Classification: SOURCE_SENIOR_DEBT_CAPACITY_REPLAY_PROVEN**

---

## 6. Vector Equality Gates (R2 — per-period, not inferred from debt delta)

Before asserting a vector contributes zero delta, R2 proves input equality directly:

| Vector | Current source | Source fixture | Max per-period delta | Classification |
|---|---|---|---|---|
| DSCR | `SeniorDebtInputs.period_dscr_targets` | DS!row22 | 0.000e+00 | `VECTOR_ALREADY_SOURCE_MATCHED` |
| Day fraction | `period_day_fraction(ACT_360)` | DS!row6 | 0.000e+00 | `VECTOR_ALREADY_SOURCE_MATCHED` |
| Ops fraction | `SeniorDebtInputs.period_debt_service_availability` | DS!row9 | 0.000e+00 | `VECTOR_ALREADY_SOURCE_MATCHED` |
| Annual rate | `SeniorDebtInputs.period_rates` | DS!row44 | 0.000e+00 | `VECTOR_ALREADY_SOURCE_MATCHED` |

All four non-CFADS vectors are exactly source-matched. This is proven at input level, not inferred from debt deltas.

---

## 7. One-Factor Counterfactuals from CURRENT_GRID0 (R2 ordering)

Each arm swaps exactly one vector; all others remain at pure current engine values.

| CF | Vector swapped | From | To | Debt delta (kEUR) | Classification |
|---|---|---|---|---|---|
| CF1 | CFADS | Phase2A EBITDA | DS!row20 (Macro50) | **−1,066.754** | `VECTOR_DIFFERENCE_CONFIRMED` |
| CF2 | DSCR | current 1.15/1.35 | DS!row22 (1.15/1.35) | 0.000 | `VECTOR_ALREADY_SOURCE_MATCHED` |
| CF3 | Day fractions | ACT/360 derived | DS!row6 | 0.000 | `VECTOR_ALREADY_SOURCE_MATCHED` |
| CF4 | Ops fraction | current vector | DS!row9 | 0.000 | `VECTOR_ALREADY_SOURCE_MATCHED` |
| CF5 | Annual rate | current vector | DS!row44 | 0.000 | `VECTOR_ALREADY_SOURCE_MATCHED` |

**CF1 alone accounts for 100% of the +1,066.754 kEUR gap.**

---

## 8. Sequential Bridge: CURRENT_GRID0 → SOURCE_ALL (R2)

| Step | Vector applied | Cumulative (kEUR) | Step delta |
|---|---|---|---|
| 0 (baseline) | CURRENT_GRID0 snapshot | 43,919.033 | — |
| 1 | CF1: Source CFADS (DS!row20) | 42,852.279 | −1,066.754 |
| 2 | CF2: Source DSCR (DS!row22) | 42,852.279 | 0.000 |
| 3 | CF3: Source day fracs (DS!row6) | 42,852.279 | 0.000 |
| 4 | CF4: Source ops (DS!row9) | 42,852.279 | 0.000 |
| 5 | CF5: Source rates (DS!row44) | 42,852.279 | 0.000 |

---

## 9. SOURCE_ALL Gate

Apply all five source vectors simultaneously:

| | Value |
|---|---|
| SOURCE_ALL capacity | 42,852.278763 kEUR |
| SOURCE_EXCEL_SENIOR_DEBT | 42,852.278763 kEUR |
| Residual | 0.000 kEUR |
| Bridge closed | **TRUE** |

---

## 10. R2 Causal Classification

**Proven:**

```
CURRENT SENIOR DEBT SIZING INPUT GAP
= BASE/CANONICAL CFADS AUTHORITY vs SOURCE BANK-SIZING CFADS AUTHORITY
```

The entire +1,066.754 kEUR gap is explained by the difference between:
- Clean engine CFADS: Phase2A EBITDA − canonical cash_tax (no bank scenario)
- Source DS!row20: Macro50 bank/P90 scenario output (bank-adjusted CFADS)

**Still unresolved:**

```
HOW Macro50 transforms base CFADS into bank-sizing CFADS
BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED
VBA_IMPLEMENTATION_NOT_VISIBLE
BANK_SIZING_SCENARIO_P90_10Y_REVIEWER_CONFIRMED_NOT_COMMITTED
```

**Future architecture (not this PR):**

```
MISSING_GENERIC_BANK_SIZING_CFADS_SCENARIO_LAYER
```

The production engine does not yet implement a generic bank-sizing CFADS scenario. Future architecture should distinguish:
- `base_case_cfads` — clean Phase2A EBITDA (current)
- `bank_sizing_cfads` — Macro50 bank/P90 transformation output
- `debt_sizing_scenario` — allows a lender/P90 CFADS policy

No such architecture change is implemented or proposed in PR #924.

---

## 11. R2 Acceptance Report (46 items)

**Governance gates:**

1. ✅ CURRENT_GRID0_RUNTIME_BASELINE_REPRODUCED — engine = 43,919.032698 kEUR
2. ✅ SOURCE_SENIOR_DEBT_CAPACITY_REPLAY_PROVEN — G4 BI = 42,852.278763 = DS!D51
3. ✅ Three baseline authorities distinct and not conflated
4. ✅ No DS25/DS40 hardcoding (AST-verified)
5. ✅ No project-name dispatch
6. ✅ No approved_delta/plug (AST-verified)
7. ✅ No calibration of clean engine to source
8. ✅ Protected C3B2 SHA unchanged
9. ✅ 13547.2 not present as literal (AST-verified)
10. ✅ No DSRA implementation
11. ✅ No production financial-engine file modifications
12. ✅ BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED recorded
13. ✅ MISSING_GENERIC_BANK_SIZING_CFADS_SCENARIO_LAYER documented

**R2 source-contamination fix:**

14. ✅ `capture_current_grid0_snapshot()` does not open/read Excel debt fixture
15. ✅ Day fractions derived via `period_day_fraction(period_start, period_end, ACT_360)`
16. ✅ Fail-closed: `CURRENT_GRID0_SNAPSHOT_REQUIRED_VECTOR_MISSING` on missing vector
17. ✅ Baseline lock tightened to 1e-3 kEUR

**Gate 1 (current snapshot):**

18. ✅ engine debt = 43,919.032698 kEUR (within 1e-3 of locked constant)
19. ✅ independent BI from pure current snapshot < 1e-3 kEUR from engine
20. ✅ 28 active source periods captured
21. ✅ all CFADS explicitly present and positive
22. ✅ all rates explicitly present and positive
23. ✅ all DSCR explicitly present and >= 1.15
24. ✅ all ops explicitly present
25. ✅ all day fracs explicitly present and positive
26. ✅ day-count convention = ACT_360

**Gate 2 (source replay):**

27. ✅ source capacity BI = DS!D51 within 1 kEUR
28. ✅ DSCR banding: 1.15 P1–P24, 1.35 P25–P28
29. ✅ all source CFADS positive
30. ✅ DS!D51 fixture = 42,852.278763 kEUR

**Vector equality gates (R2):**

31. ✅ DSCR vector max delta = 0.000 → VECTOR_ALREADY_SOURCE_MATCHED
32. ✅ Day-fraction vector max delta = 0.000 → VECTOR_ALREADY_SOURCE_MATCHED
33. ✅ Ops vector max delta = 0.000 → VECTOR_ALREADY_SOURCE_MATCHED
34. ✅ Rate vector max delta = 0.000 → VECTOR_ALREADY_SOURCE_MATCHED
35. ✅ Per-period DSCR equality: 28 periods confirmed
36. ✅ Per-period day-frac equality: 28 periods confirmed
37. ✅ Per-period ops equality: 28 periods confirmed
38. ✅ Per-period rate equality: 28 periods confirmed

**CF1–CF5 counterfactuals:**

39. ✅ CF1 moves debt to ~42,852 — closes gap (delta = −1,066.754)
40. ✅ CF2 (DSCR) delta = 0.000 kEUR
41. ✅ CF3 (day fracs) delta = 0.000 kEUR — R2 explicit arm
42. ✅ CF4 (ops) delta = 0.000 kEUR
43. ✅ CF5 (rate) delta = 0.000 kEUR

**Sequential bridge and SOURCE_ALL:**

44. ✅ 5-step bridge, step 1 closes entire gap
45. ✅ SOURCE_ALL capacity = 42,852.278763 kEUR (residual = 0.000)
46. ✅ Verdict: `C3B3D2B2B_R2_BANK_SIZING_CFADS_AUTHORITY_SOLE_GAP_READY_FOR_INDEPENDENT_REVIEW`

---

## 12. Summary Verdict

**`C3B3D2B2B_R2_BANK_SIZING_CFADS_AUTHORITY_SOLE_GAP_READY_FOR_INDEPENDENT_REVIEW`**

The entire +1,066.754 kEUR senior debt sizing gap between CURRENT_GRID0 and SOURCE_EXCEL is explained by **CF1 — the CFADS vector** (DS!row20 Macro50/bank output vs clean Phase2A EBITDA). Per-period vector equality gates confirm that DSCR banding, day-count fractions, ops fraction, and annual rates are already source-matched exactly.

The Macro50 bank/P90 transformation mechanism remains `BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED`. The future production gap is `MISSING_GENERIC_BANK_SIZING_CFADS_SCENARIO_LAYER`. No production engine changes are proposed or made.
