# C3B2 — Oborovo Debt Interest Source Closure

**Branch**: `stage-c3b2-oborovo-debt-interest-source-closure`
**PR**: #913 (Draft — DO NOT MERGE)
**Base SHA**: `c5f0b1f1643aad07df2f2d9e07acd21943328841` (post-C3B1 main)
**Verdict**: `C3B2_DEBT_INTEREST_SOURCE_TRUTH_PROVED`
**Tests**: 169 C3B2 + 177 C3B1 = 346 total (all passing)

---

## 1. Objective

Prove that the Oborovo senior debt capacity in the Excel workbook (DS sheet, `D47/D51`) is
fully reproduced by an independent backward induction from raw primitives, with zero unexplained
residual. No production formula changes are made in this PR.

---

## 2. Active Runtime Classification

The Oborovo project uses **FROZEN_EXCEL_SCHEDULE_RUNTIME**:

```
use_frozen_excel_senior_debt_schedule = True
frozen_senior_ds_fixture_path = "reports/phase23q_oborovo_senior_debt_sizing_extraction.csv"
```

Derived from `app.project_factories.create_default_oborovo()` → `proj.financing` attributes.
The debt service schedule is read from a pre-computed CSV fixture — **not** recomputed at
runtime by `solve_senior_debt`. G0 (`solve_senior_debt` at generic Phase 2C inputs) is a
diagnostic, not the active production configuration.

---

## 3. Complete Workbook Formula

The full DS sheet formula chain is:

```
DS!row23[p]  = (row20[p] / row22[p]  +  SUM(CF!H83:H83))  *  row9[p]  *  B23
DS!row46[p]  = row23[p] * row5[p]
DS!row47[p]  = SUM(
    IF(NOT(row7), (row46[p] + V[p+1]) / (1 + row44[p] * (1 + B54/(1-B54)) * row6[p]), 0),
    row82[p]
)
```

### 3a. Neutral-Term Proofs

All supplementary formula terms are proved neutral for the Oborovo workbook:

| Term | Value | Proof method |
|------|-------|--------------|
| `CF!row83` | 0 for all P1-P28 | Extracted from workbook; `row23_actual = (row20/row22)×row9` — max residual = 0.000 kEUR |
| `B23` (tranche enabled) | `True` | Extracted from workbook cell `DS!B23 = Inputs!$C$192`; `extracted_value=True` |
| `row5` (eligibility flag) | `1` for all P1-P28 | `row46_actual = row23_actual` — max residual = 0.000 kEUR |
| `row7` (refinancing flag) | `False` for all P1-P28 | Logical implication: `row47[p]>0` AND `row82[p]=0` → `IF(NOT(True), x, 0)+0=0` contradicts `row47>0`; therefore `row7=False` for all P1-P28 |
| `B54` (WHT rate) | `0` | Extracted from workbook cell `DS!B54 = Inputs!$D$422`; `extracted_value=0`; `B54=0 → 1+B54/(1-B54)=1.0` |
| `row82` (refinancing capacity) | `0` for all P1-P28 | Confirmed from cached fixture values |

**Simplified formula** (valid because all supplementary terms are neutral):

```
allowed_ds[p] = (row20[p] / row22[p]) * row9[p]
```

---

## 4. Backward-Induction Derivation (G3A / G4)

### Algorithm

```
allowed_ds[p] = (CFADS[p] / DSCR_policy[p]) * ops_flag[p]
V[maturity + 1] = 0
V[p] = (V[p + 1] + allowed_ds[p]) / (1 + rate[p] * day_frac[p])
capacity = V[first_active_period]
```

### Two Policies

| Label | DSCR policy | Result |
|-------|-------------|--------|
| **G3A** | `1.15` for all P1-P28 (scalar) | 43,368.224 kEUR |
| **G4**  | `DS!row22[p]` per period (1.15 at P1-P24, 1.35 at P25-P28) | 42,852.279 kEUR |

### Raw Inputs Used

All from the committed fixture (no hardcoded constants):

- `DS!row20` — CFADS per period
- `DS!row22` — per-period DSCR target
- `DS!row9`  — ops_flag fraction
- `DS!row44` — annual sculpting rate
- `DS!row6`  — day fraction

**Forbidden inputs** (never used): `DS!row46`, `DS!D47`, `DS!D51`, `DS!row61/63/64/67`.

### P28 Ops-Flag Proof

P28 is the only partial terminal period. `DS!row9[28] < 1.0` (approx 0.989).

- P1-P27: `row9 = 1.0` (all confirmed)
- P28: `allowed_ds[28] = (CFADS[28] / DSCR[28]) * 0.989`
- Omitting `row9` (treating P28 as full) produces a ~7.44 kEUR residual

---

## 5. Causal Bridge (G0 to G4)

```
G0  (GENERIC_PHASE2C_SCALAR_DIAGNOSTIC)    46,053.402 kEUR
  + delta_rate      (Excel rates)            -543.807 kEUR
= G1  (Excel rates applied)                45,509.595 kEUR
  + delta_cfads     (DS!row20)            -1,918.036 kEUR
= G2  (Excel rates + CFADS)               43,591.559 kEUR
  + delta_daycount  (ACT_360)               -214.604 kEUR
= G3  (Excel rates + CFADS + ACT_360)     43,376.955 kEUR  [solver]
  + delta_solver_to_independent_scalar       -8.732 kEUR   [TERMINAL_PARTIAL_PERIOD_TREATMENT]
= G3A (scalar backward induction)         43,368.224 kEUR
  + delta_dscr_banding_g3a_to_g4           -515.945 kEUR   [pure DSCR banding: 1.35 at P25-P28]
= G4  (vector backward induction)         42,852.279 kEUR
  = Excel total debt                       42,852.279 kEUR  [residual = 0.000 kEUR]
```

Bridge closed: `bridge_closure_error = 0.000 kEUR < 1.0 kEUR tolerance`.

---

## 6. Implementation Architecture

### `finco_recon/extract_oborovo_debt_interest.py`

- Version `2.0.0`
- `_assemble_bridge_from_vectors()` — pure module-level callable; **mandatory** import of
  `derive_capacities_from_vectors`; no inline fallback; import failure fails loudly
- Extracts CF!row83 from workbook (`cf_row83_debt_cost_adj` key)
- Reads B23 and B54 from actual workbook cells (not hardcoded)
- `_row_to_periods_bool()` helper preserves `True`/`False` for boolean rows (row5, row7)
- Returns `neutral_terms_proof` and `runtime_inventory` in `phase2c_sizing_analysis`
- Uses `solve_senior_debt` API; never uses `build_schedule`

### `finco_recon/derive_c3b2_independent_capacity.py`

- Version `1.2.0`
- `_backward_induction_complete()` — authoritative single implementation accepting all 11
  formula parameters (cfads, dscr, ops_fraction, eligibility_fraction, tranche_enabled,
  cumulative_cf83, annual_rates, wht_rate, day_fractions, refinancing_flag,
  refinancing_capacity, active)
- Public API: `derive_capacities_from_vectors(cfads, dscr_vector, ops_vector, annual_rates, day_fractions, active_periods, eligibility_fraction=None, tranche_enabled=None, cumulative_cf83=None, wht_rate=None, refinancing_flag=None, refinancing_capacity=None)`
- Source vector hash: 13-field canonical payload (cfads, dscr, ops, row5_eligibility, b23_tranche, cf83_cumulative, rate, b54_wht, frac, row7_refinancing_flag, row82_refinancing_capacity, active_periods, maturity_period)
- Runtime inventory factory-derived: `app.project_factories.create_default_oborovo()` → `proj.financing`
- Idempotency guard: `_content_sha256` covers `independent_capacity_proof` + `neutral_terms_proof` + `runtime_inventory`
- First run on a committed fixture prints "already up-to-date"; fixture SHA unchanged

### `tests/fixtures/excel_oborovo_debt_interest_truth.json`

Key sections in `phase2c_sizing_analysis`:

| Key | Description |
|-----|-------------|
| `independent_capacity_proof` | G3A/G4, banding, P28 proof, residual, verdict |
| `neutral_terms_proof` | CF!row83=0, B23=True (extracted), row5=1, row7=False (logical proof), B54=0 (extracted), row82=0 |
| `runtime_inventory` | FROZEN_EXCEL_SCHEDULE_RUNTIME, factory-derived from `proj.financing` |
| `causal_bridge` | G0 to G1 to G2 to G3 to G3A to G4 decomposition, bridge_closed=True |
| `current_phase2c_solver_result` | G0 (GENERIC_PHASE2C_SCALAR_DIAGNOSTIC, not production runtime) |

---

## 7. Test Coverage

**169 C3B2 tests** across 22 classes:

- `TestExtractorVersion` — version 2.0.0
- `TestWorkstreamA_CFADS` — DS!row20, DS!row22 raw values
- `TestWorkstreamB_Sculpting` — DS!row9, DS!row6 vectors
- `TestWorkstreamC_DSRA` — DSRA parameters
- `TestWorkstreamD_SizingBase` — sizing base inputs
- `TestWorkstreamE_InterestRate` — DS!row44 rates
- `TestPhase2CSizingAnalysis` — top-level structure and verdict
- `TestCurrentPhase2CSolverResult` — G0 diagnostic label
- `TestScalarExcelMatchedSolverResult` — G3 convergence
- `TestIndependentVectorDSRCapacity` — G3A/G4 fixture values
- `TestCausalBridge` — bridge closure, G3A/G4 deltas
- `TestConvergenceInvariance` — deterministic convergence
- `TestSizingConstraintIdentity` — algebraic identities
- `TestProductionFileIntegrity` — source-guard (solve_senior_debt, not build_schedule)
- `TestExtractorSynthetic` — import/callable checks
- `TestCompleteFormulaTerms` — neutrality of all 6 formula terms (including extracted B23, B54, logical row7 proof)
- `TestRuntimeInventory` — FROZEN_EXCEL_SCHEDULE_RUNTIME classification
- `TestIndependentRecomputation` — G3A/G4/bridge/residual computed independently
- `TestSourceVectorProvenance` — 13-field source-vector SHA reconstruction
- `TestExtractorExecutionPath` — `_assemble_bridge_from_vectors` with synthetic inputs
- `TestDirectionalSensitivity` — higher DSCR/rate/lower ops reduces capacity
- `TestRuntimeInventoryFactory` — factory function recorded, fields match live factory
- `TestCausalBridgeIntermediateIdentities` — G0→G1→G2→G3→G3A→G4 step identities
- `TestCompleteHelperDirectional` — 9 directional tests for complete formula helper

---

## 8. Verdict Discipline

`C3B2_DEBT_INTEREST_SOURCE_TRUTH_PROVED` is used because:

1. All 6 supplementary formula terms proved neutral (max residual = 0.000 kEUR), with B23 and B54 extracted from actual workbook cells and row7=False proved by logical implication
2. Independent backward induction (G4) matches Excel debt exactly (residual = 0.000 kEUR < 0.001 tolerance)
3. Causal bridge closed (closure error < 1.0 kEUR); G0=46,053.402 kEUR correctly labelled GENERIC_PHASE2C_SCALAR_DIAGNOSTIC
4. No production code modified; `financial_engine/`, `app/`, `finco_core/` diffs are empty
5. Runtime inventory factory-derived (not hardcoded)
6. Source vector hash covers all 13 formula inputs

---

## 9. Files Changed

```
finco_recon/extract_oborovo_debt_interest.py
finco_recon/derive_c3b2_independent_capacity.py
tests/fixtures/excel_oborovo_debt_interest_truth.json
tests/test_stage_c3b2_oborovo_debt_interest_source_closure.py
tests/test_stage_c3b1_oborovo_tax_source_truth.py
docs/reconciliation/oborovo_debt_interest_source_closure.md
.github/workflows/c3b2_debt_interest_check.yml
```

**No production code changes**: `financial_engine/`, `app/`, `finco_core/` are untouched.
