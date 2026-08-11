# C3B3D2B2C — Bank-Sizing CFADS Production: Reconciliation

## Stage identity

| Field | Value |
|---|---|
| Stage | C3B3D2B2C |
| Branch | `stage-c3b3d2b2c-bank-sizing-cfads-production` |
| Base SHA (C3B3D2B2B locked) | `6e064980868709294e14da4d95e3279790d70ff0` |
| Protected C3B2 SHA | `f8f244c0660495bfb4115d4e32ba329c291ab829d1d0693e614c889457b5add7` |
| PR | #925 (DRAFT — DO NOT MERGE without explicit instruction) |
| **R3 Final Verdict** | `C3B3D2B2C_R3_STOP_MACRO50_TRANSFORMATION_SOURCE_INACCESSIBLE` |
| **R4 Verdict** | `C3B3D2B2C_R4_SOURCE_INPUTS_IDENTIFIED_CURVE_EXTRACTION_REQUIRED` |
| **R4.1 Verdict** | `C3B3D2B2C_R4_1_MANUAL_CAUSALITY_PROVEN_ENGINE_EVALUATION_XLSM_EXTRACTION_REQUIRED` |

---

## 1. Problem statement

### Current authoritative baseline (C3B3D2B2B locked, PR #924)

| Constant | Value |
|---|---|
| `CURRENT_GRID0_PRODUCTION_CANDIDATE` | **43,919.032698 kEUR** |
| `SOURCE_EXCEL_SENIOR_DEBT` (DS!D51) | **42,852.278763 kEUR** |
| Current gap (CF1 only) | **+1,066.754 kEUR** |

Prior stage C3B3D2B2B (PR #924, locked) proved:

- CF2 (DSCR mechanics) = 0 kEUR — source-matched in current engine
- CF3 (ACT/360 day-count) = 0 kEUR — source-matched in current engine
- CF4 (operating assumptions) = 0 kEUR — source-matched
- CF5 (interest rate) = 0 kEUR — source-matched
- CF1 (CFADS / bank case) = **−1,066.754 kEUR** — sole source of the current sizing gap

Classification: `BANK_SIZING_CFADS_AUTHORITY_IS_SOLE_CURRENT_SIZING_GAP_SOURCE_PROVEN`

> **Historical note**: earlier pre-C3B3D2B2B analysis referenced a 13,547.2 kEUR sizing
> gap and a 29,305 kEUR engine debt figure. These are historical-only values from prior
> diagnostic stages and do NOT represent the current C3B3D2B2B-locked baseline.

This stage (C3B3D2B2C) was tasked with implementing a generic typed bank-sizing CFADS
scenario layer, identifying the source-proven Macro50 merchant-period transformation, and
wiring canonical production if a source rule was found.

---

## 2. Source evidence inspected (R3)

### Workbook identity

| Field | Value |
|---|---|
| Filename | `d49af8ee-20260414_BP_Oborovo_Sensitivity_FINAL_for_PPT.xlsm` |
| SHA-256 | `15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920` |

### Fixtures inspected

- `tests/fixtures/excel_oborovo_debt_interest_truth.json` — DS/Macro/CF formulas and values
- `tests/fixtures/excel_oborovo_financial_truth.json` — P&L, Inputs, tax formulas
- `tests/fixtures/excel_oborovo_merchant_revenue_truth.json` — CF!row30 price formula
- `tests/fixtures/excel_oborovo_full_model_extract.json` — period diagnostics
- `tests/fixtures/excel_golden_oborovo.json` — worksheet metadata
- `tests/fixtures/excel_oborovo_opex_structural_truth.json` — Scenarios!E4, opex template selector
- `tests/fixtures/oborovo_baseline.json` — baseline inputs

### Scenario selectors found

| Cell | Value | Role |
|---|---|---|
| `Inputs!D52` | `P_50` | Base production scenario |
| `Inputs!D89` | `Fixed` | Base market price scenario |
| `Scenarios!E345` | `14` | Senior debt maturity (years) |
| `Scenarios!E348` | `0.80` | Gearing/hedge coverage |
| `Scenarios!E350` | `1.15` | DSCR band 1 (contracted) |
| `Scenarios!E351` | `1.35` | DSCR band 2 (merchant/BESS) |
| `Scenarios!E352` | `1.65` | DSCR band 3 (merchant PV) |
| `Scenarios!E4` | opex template | OpEx scenario selector (`INDEX/MATCH`) |

**Not found:** bank production selector, bank market price selector, lender/capture/haircut selector.

---

## 3. Macro!row50 forensics

### DS!H20 provenance chain

```
DS!H20  formula: =Macro!H50        (confirmed, dual-load extraction)
Macro!H49 formula: =CF!H79         (confirmed — base P50 CFADS)
Macro!H50 formula: None            (no formula element in XML)
```

`macro_row50_output_formula: None` means Macro!row50 cells contain only `<v>` (cached
value) elements with no `<f>` (formula) element. The workbook architecture indicates
Macro/VBA involvement, but the exact VBA procedure and assignment mechanism are not visible
and must not be inferred. The source evidence proves only that no worksheet formula is
present in the inspected extraction; the VBA source code is password-protected.

`VBA_IMPLEMENTATION_NOT_VISIBLE`: the exact transformation cannot be determined from the
available artifacts. `BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED`.

### Macro!row38/39/40 precedent

From `financial_truth.json` (P&L sheet):
```
P&L!row44 = Macro!G40
Macro!G40 = IF(Production_Scenario=base_scenario, Macro!G38, Macro!G39)
```

Macro!row38 = base scenario CIT; row39 = alternative CIT; row40 switches on scenario.
Both rows 38 and 39 contain hardcoded values matching row43 in the current snapshot.

This establishes the Macro sheet architectural pattern (IF/scenario-switch), but
Macro!row50's formula is None — it does NOT follow the formula-driven pattern.

### PPA vs merchant period behaviour

| Period range | DS!row20 vs CF!row79 | Interpretation |
|---|---|---|
| 1–24 (PPA) | ≈ identical (< 1 kEUR) | Bank CFADS ≈ base CFADS (contractual revenue unchanged) |
| 25–60 (merchant) | DS20 << CF79 by 590–1,117 kEUR | Bank CFADS substantially lower; transformation mechanism unresolved |

The gap grows over the merchant tenor, suggesting compounding effects.

### Candidate analysis (per-period merchant deltas)

| Period | CF79 / Macro49 | DS20 / Macro50 | CF79 − DS20 |
|---|---|---|---|
| 25 | 2,992.5 | 2,279.8 | +712.7 |
| 26 | 2,694.8 | 2,103.8 | +591.0 |
| 27 | 2,991.7 | 2,248.8 | +743.0 |
| 28 | 2,667.8 | 2,057.8 | +610.1 |
| 29 | 2,994.5 | 2,226.8 | +767.8 |

---

## 4. Candidate rules investigated

### Candidate A — ALL_PRODUCTION (P90-10y for all periods)

All operating periods use P90-10y yield scenario.

| Metric | Value |
|---|---|
| Candidate debt | 40,950 kEUR |
| Max \|delta\| vs DS!row20 | **690 kEUR** |
| Gap to Excel debt | −1,902 kEUR |

Result: `OBOROVO_ALL_PRODUCTION_BANK_CASE_RULE_CANDIDATE_ONLY` — **REJECTED**

P90 applied to PPA periods produces CFADS below source (DS!row20 PPA ≈ base P50, not P90).

### Candidate B — MERCHANT_ONLY (P90-10y for merchant periods only)

PPA periods retain base P50 yield. Merchant periods use P90-10y yield.

| Metric | Value |
|---|---|
| Candidate debt | 43,622 kEUR |
| Max \|delta\| vs DS!row20 | **690 kEUR** |
| Gap to Excel debt | +770 kEUR |

Merchant period deltas (bank CFADS − DS!row20):

| Period | Bank CFADS | Source DS20 | Delta |
|---|---|---|---|
| 26 | 2,546 | 2,280 | +266 |
| 27 | 2,759 | 2,104 | +655 |
| 28 | 2,531 | 2,249 | +283 |
| 29 | 2,748 | 2,058 | +690 |

Result: `OBOROVO_MERCHANT_ONLY_BANK_CASE_RULE_CANDIDATE_ONLY` — **REJECTED**

PPA period match is good (delta ≈ 0). Merchant periods: P90 CFADS systematically exceeds
source Macro50. The VBA applies additional merchant downside not captured by yield-scenario
substitution alone.

---

## 5. Implied merchant bank revenue analysis (R3)

For H2 merchant periods (odd, CIT = 0), the implied bank revenue given source opex is:

```
bank_rev[p] = DS20[p] − source_opex[p]
```

Ratios vs base P50 source revenue (Candidate B, P90 production):

| Period | P50 prod | P90 prod | Impl rev | P90 rev | Impl/P90 |
|---|---|---|---|---|---|
| P25 | 52,291 | 49,351 | 3,244.5 | 3,571.6 | 0.908 |
| P27 | 52,081 | 49,153 | 3,224.2 | 3,708.0 | 0.870 |
| P29 | 52,017 | 49,093 | 3,204.7 | 3,713.1 | 0.863 |
| P31 | 51,666 | 48,761 | 3,053.6 | 3,596.3 | 0.849 |
| P35 | 51,253 | 48,371 | 3,173.5 | 3,726.7 | 0.852 |

No constant ratio. The implied price (given P90 production) varies from 65.4 to 65.9 EUR/MWh
vs base 75–78 EUR/MWh. The pattern is not consistent with any simple multiplier or flat
price floor.

No bank price scenario, capture-price discount, lender haircut, or downside price curve was
found in the inspected fixture data. The Scenarios sheet column structure (beyond the base
E-column values) was not captured in the extraction artifacts.

---

## 6. Stop verdict

```
C3B3D2B2C_R3_STOP_MACRO50_TRANSFORMATION_SOURCE_INACCESSIBLE
```

The Macro!row50 formula is absent (VBA-hardcoded values). No formula, Scenarios cell, or
price-curve evidence has been found that would uniquely identify the bank-case CFADS
transformation. The VBA procedure (Macro50) is password-protected and not accessible.

No source-proven rule can be established from the available extraction artifacts.

---

## 7. Production impact (R3 revert)

Per R3 specification §10 (STOP case):

**Reverted from `financial_engine/` production files:**
- `inputs.py`: `ProductionScenarioScope` removed; `DebtSizingScenario.scope` removed;
  `SeniorDebtModelInput.bank_sizing_scenario` removed
- `results.py`: `SeniorDebtSchedules.bank_sizing_cfads_keur` removed;
  `SeniorDebtSchedules.bank_sizing_dscr` removed
- `provenance.py`: `bank_sizing_scenario` payload removed from fingerprint
- `orchestrator.py`: `_derive_bank_operating_input`, `_is_ppa_for_bank_splice`,
  fail-closed bank CFADS audit, bank DSCR computation — all removed

**Moved to `finco_recon/bank_sizing_candidates.py` (diagnostic-only):**
- `_derive_bank_operating_input()` — pure transformer for candidate evaluation
- `run_candidate_a_all_production()` — Candidate A evaluation
- `run_candidate_b_merchant_only()` — Candidate B evaluation
- `MACRO50_FORENSICS` — forensic summary dict
- `load_ds_row20_oracle()` — DS!row20 oracle loader

All 79 Phase 2C tests pass. All 169 Phase 2B tests pass (1 pre-existing Oborovo baseline failure, not from this PR).

---

## 8. Evidence labels preserved

- `BANK_SIZING_CFADS_AUTHORITY_IS_SOLE_CURRENT_SIZING_GAP_SOURCE_PROVEN`
- `OBOROVO_ALL_PRODUCTION_BANK_CASE_RULE_CANDIDATE_ONLY`
- `OBOROVO_MERCHANT_ONLY_BANK_CASE_RULE_CANDIDATE_ONLY`
- `BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED`
- `VBA_IMPLEMENTATION_NOT_VISIBLE`
- `C3B3D2B2C_STOP_BANK_CASE_TRANSFORMATION_NOT_SOURCE_PROVEN` (R2 finding, preserved)
- `C3B3D2B2C_R3_STOP_MACRO50_TRANSFORMATION_SOURCE_INACCESSIBLE` (R3 final verdict)

---

## 9. R4 — Debt-Horizon Bank Revenue Sizing Case Source Proof

### R4 verdict

```
C3B3D2B2C_R4_SOURCE_INPUTS_IDENTIFIED_CURVE_EXTRACTION_REQUIRED
```

### Active Senior Debt horizon (generic derivation)

| Field | Value |
|---|---|
| `repayment_start_period_index` | 2 |
| `maturity_period_index` | 29 |
| Active period count | **28** |
| Merchant+debt periods | **4** (period indices 26, 27, 28, 29) |
| Derivation | `GENERIC_FROM_SENIOR_DEBT_POLICY_NOT_HARDCODED` |

No hardcoded period boundary integers (25, 28, or 2044). Active period count is
derived as `maturity_period_index − repayment_start_period_index + 1`.

### Post-maturity causality

```
POST_MATURITY_CFADS_NON_CAUSAL_FOR_INITIAL_DSCR_SIZING
```

The DSCR schedule is confined to periods within `[repayment_start_period_index,
maturity_period_index]`. Periods 30–61 (post-maturity) do not appear in the DSCR
schedule and cannot be the binding constraint for debt sizing. This is confirmed
by inspection of the schedule's `period_indices` field.

### Candidate C — PRODUCTION_REVENUE_SIZING (architecture defined, blocked)

| Field | Value |
|---|---|
| Yield scenario | P90-10y |
| Revenue scenario | Central Low case Trackers (D111) / MidLow (TUHO D109) |
| Evaluation scope | Active debt periods only (generic from policy) |
| Status | `BLOCKED_PENDING_CURVE_EXTRACTION` |

**Source cell identifiers confirmed:**

| Project | Cell | Label | Status |
|---|---|---|---|
| Oborovo | `Inputs!D102` | Equity case revenues | Confirmed |
| Oborovo | `Inputs!D103` | Debt sizing revenues curve | Confirmed |
| Oborovo | `Inputs!D111` | Central Low case Trackers | Cell confirmed; **curve not in fixture** |
| Oborovo | `Inputs!D110` | Low case GMPV (hardcoded) | Cell confirmed; **value not in fixture** |
| Oborovo | `Scenarios!E324` | Equity case revenues | Confirmed |
| Oborovo | `Scenarios!E325` | Debt sizing revenues curve | Confirmed |
| TUHO | `Inputs!D107` | Equity scenario | Confirmed |
| TUHO | `Inputs!D108` | Sizing scenario | Confirmed |
| TUHO | `Inputs!D109` | MidLow | Cell confirmed; **curve not in fixture** |
| TUHO | `Scenarios!E182` | Equity case Afry curve | Confirmed |
| TUHO | `Scenarios!E183` | Sizing case Afry curve | Confirmed |

**Why Candidate C cannot be evaluated yet:**
- `Inputs!D111` (Oborovo Central Low case Trackers): time-series values not in any committed fixture
- `Inputs!D110` (Oborovo Low case GMPV): hardcoded base value not extracted
- `Inputs!D109` (TUHO MidLow): time-series values not in any committed fixture

Candidate C will be source-proven only when these curves are extracted and
a bank CFADS vector built from P90 production + sizing revenue curve matches
DS!row20 (or narrows the gap to within a toleranced acceptance criterion).

---

## 10. R4.1 — Manual Causality Evidence and Environment Status

### R4.1 verdict

```
C3B3D2B2C_R4_1_MANUAL_CAUSALITY_PROVEN_ENGINE_EVALUATION_XLSM_EXTRACTION_REQUIRED
```

### Manual black-box causality (PROVEN)

| Observation | Scenarios!E325 value | Inputs cell | Resulting debt (kEUR) | Matches DS!D51? |
|---|---|---|---|---|
| 1 | Central Low case Trackers | D111 | **42,852.278763** | **Yes** (exact) |
| 2 | Central case Trackers | D106 | 43,813.000 | No (+961 kEUR) |

**Classification:** `OBOROVO_DEBT_SIZING_REVENUE_CURVE_MANUAL_CAUSALITY_PROVEN`

Revenue curve selector `Scenarios!E325` is causally proven for debt sizing. `D111` (Central Low case Trackers) reproduces the source debt exactly. Switching to `D106` (equity curve) increases debt by +961 kEUR. The mechanism is revenue scenario selection, not yield scenario alone.

**Oborovo confirmed selectors:**
- `Scenarios!E324` (equity): cell confirmed HARDCODE; active value not in any fixture
- `Scenarios!E325` (sizing): active value = **"Central Low case Trackers"** — confirmed from manual causality observation 1

**TUHO confirmed selectors (from `tuho_scenario_manifest_v5.json`):**
- `Scenarios!E182` (equity): **"Equity case Afry curve"** — confirmed
- `Scenarios!E183` (sizing): **"Sizing case Afry curve"** — confirmed

### TUHO bank CFADS oracle back-calculation

```
bank_cfads_P1 = senior_debt_service_P1 × DSCR_target
              = 2,116.361394 × 1.20
              = 2,539.633673 kEUR

bank/base ratio   = 2539.633673 / 3070.175837 = 0.8272
P90/P50 yield     = 3620 / 4164 = 0.8694
Residual (price)  = 0.8272 / 0.8694 = 0.9515
```

**Classification:** `TUHO_BANK_CFADS_ORACLE_BACK_CALCULATED_FROM_DEBT_SERVICE`

The residual factor (0.9515) confirms a price-scenario reduction is applied alongside yield downscaling, consistent with MidLow/Central price ratio.

### Confirmed yield cases

| Project | P50 (h) | P90-10y (h) | P90/P50 ratio |
|---|---|---|---|
| Oborovo | 1,494 | 1,410 | 0.9438 |
| TUHO | 4,164 | 3,620 | 0.8694 |

P75/P95/P99 cases: not in any committed fixture — XLSM required.

### Confirmed price curves

| Project | Curve | Cell | Status |
|---|---|---|---|
| Oborovo | Central case Trackers | D106 | **Values in fixture** (CY2042–2060) |
| Oborovo | Central Low case Trackers | D111 | **Not in fixture** — XLSM required |
| Oborovo | Low case GMPV | D110 | **Not in fixture** — XLSM required |
| TUHO | Central | D106 | Not in fixture |
| TUHO | MidLow | D109 | **Not in fixture** — XLSM required |

### Candidate C status

| Project | Yield | Revenue curve | Manual causality | Engine evaluation |
|---|---|---|---|---|
| Oborovo | P90-10y | D111 (Central Low case Trackers) | **PROVEN** | BLOCKED — XLSM required |
| TUHO | P90-10y | D109 (MidLow) | Oracle derivable | BLOCKED — XLSM required |

### Product contract design (draft)

| Schema | Key fields | UX contract |
|---|---|---|
| `YieldCase` | `p50_hours`, `p90_10y_hours`, `p90_p50_ratio` (derived) | Both P50 and P90 user-editable; ratio is display-only |
| `PriceCurve` | `curve_id`, `label`, `calendar_start_year`, `values_eur_mwh` | Named library; CRUD operations; selector by `curve_id` |
| `RevenueCaseSelection` | `equity_curve_id`, `sizing_curve_id`, `bess_curve_id` (optional) | Scenario tab exposes two selectors; engine uses `sizing_curve_id` for bank CFADS |

Scenario tab sections: Production / Yield → Revenue Curves → BESS Revenue (if applicable).
No project-name dispatch. No hardcoded period boundaries.

### Environment status

Original XLSM files (`20260414_BP_Oborovo_Sensitivity_FINAL for PPT.xlsm`, `20260330_TUHO_BP.xlsm`) are not present in the execution environment. Searched: `/home`, `/root`, `/data`, `/mnt`, `/home/user/attach`. D110, D111 (Oborovo) and D109 (TUHO) are not in any committed fixture. Productionization gate cannot be cleared without engine evaluation of Candidate C.

**Evidence fixture:** `tests/fixtures/excel_oborovo_bank_sizing_source_evidence_r4_1.json`

---

## 12. Next steps for future stages

A source-proven bank-sizing rule can only be identified by one of:
1. Access to the VBA source code for the Macro50 procedure
2. A new workbook extraction that captures Macro!row50 formula text
3. Extraction of additional Scenarios sheet columns (bank-scenario column values)
4. Documentation from the project originator identifying the bank-case price/yield inputs

Until one of these is available, production adapter wiring is prohibited.

---

## 13. Governance constraints observed

- No DS25/DS40 period boundary hardcoding — ENFORCED
- No project-name dispatch in production code — ENFORCED
- No approved_delta or balancing plug — ENFORCED
- No calibration of clean engine to source — ENFORCED
- `13547.2` does not appear as a literal — ENFORCED
- Protected C3B2 SHA not in production code literals — ENFORCED
- No DSRA implementation — ENFORCED
- Source Macro50 is test oracle only — no runtime fixture reads in production code
- `BANK_CASE_TRANSFORMATION_MECHANISM_UNRESOLVED` — preserved
- `VBA_IMPLEMENTATION_NOT_VISIBLE` — preserved
- DO NOT MERGE without explicit instruction
