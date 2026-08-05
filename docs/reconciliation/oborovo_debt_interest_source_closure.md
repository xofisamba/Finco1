# C3B2 — Oborovo Debt Sizing & Interest Source Closure

**Stage:** C3B2  
**Branch:** `stage-c3b2-oborovo-debt-interest-source-closure`  
**Base:** C3B1 squash-merge SHA `1fb4943a4319eff8f4ac7a22add6f65f14bd8cec`  
**Verdict:** `C3B2_INPUT_OR_POLICY_MISMATCH_FULLY_EXPLAINED`  
**Extractor version:** `2.0.0`  
**Workbook SHA-256:** `15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920`

---

## Purpose

Close the five open questions left by C3B1 concerning senior debt sizing and interest mechanics in the Oborovo Excel workbook, and establish a complete equal-input / equal-policy contract for Phase 2C reconciliation.

This is a diagnostic gate — no production code is modified.

---

## Five Questions Answered

### A · CFADS composition used by DSCR sculpting

Excel formula verified via dual openpyxl load (formula text + cached values):

| Item | Value |
|---|---|
| Excel source row | CF!row79 |
| Formula (CF!H79) | `=SUM(H23, H49, H73, H76, H77) + B80*(H4=0)` |
| H23 | Revenues |
| H49 | OPEX (negative) |
| H73 | Local taxes (= 0 in this instance) |
| H76 | Interest income (= 0 in this instance) |
| H77 | CIT (negative in operating periods) |
| Period 1 cached value | 2 575.003 kEUR |
| Component identity | Verified to machine precision (max residual = 0) |

Component bridge (Period 1): `H23 + H49 + H73 + H76 + H77 = CFADS` — identity holds for all 28 periods.

Phase 2C uses `CFADS = EBITDA − cash_tax_paid`, which maps to `H23 + H49 + H77` (H73=0, H76=0 in this instance). When the Oborovo workbook has non-zero interest income from reserves, a residual arises. For this model instance the terms are zero → **aligned**.

Classification: **ALIGNED_FOR_THIS_INSTANCE** (H73 = H76 = 0)

---

### B · DSCR sculpting circular reference and convergence

Excel backward induction formula (DS!H47):

```
DS!H47 = SUM(
  IF(NOT(H7), (H46 + I47) / (1 + H44*(1+$B$54/(1-$B$54))*H6), 0),
  H82
)
```

`H47` references `I47` (the next period's capacity), creating a circular dependency. Excel resolves via **iterative calculation**.

Phase 2C uses forward Newton iteration. Equal-input comparison (see below) proves the two algorithms converge to identical results per period when the same DSCR target is applied to each period.

Total sculpted debt DS!D51 = **42 852.279 kEUR**.

Classification: **ECONOMICALLY_EQUIVALENT_WHEN_INPUTS_MATCHED**

---

### C · DSRA funding and release treatment

| Cell | Value |
|---|---|
| Inputs!I348 (DSRA target months) | 0 |
| CF rows 85–92 cached values | All zero |
| CF!H89 formula | `=(IF((H87)<H86,MAX(MIN(H86-H87-H88,SUM(H79:H80)+G$144),0),0)-IF((H87)>=H86,-H86+H87,0))` |

DSRA mechanism exists in the workbook but is deactivated by a zero target. Phase 2C likewise does not model DSRA for this scenario. **Aligned — no divergence.**

Classification: **ALIGNED_BOTH_ZERO**

---

### D · IDC and financing-cost eligibility in the gearing base

`Inputs!G171 = SUM(G165:G170)` = **57 973.053 kEUR** (total eligible project cost):

| Row | Description | kEUR |
|---|---|---|
| G165 | Hard CAPEX (`=CapEx!C117`) | 55 999.085 |
| G166 | IDC — Interest During Construction | 1 086.032 |
| G167 | Commitment and financing fees | 188.563 |
| G168 | Other financing costs | 477.303 |
| G169 | Working capital | 0.000 |
| G170 | Other / contingency | 222.070 |
| **G171** | **Total** | **57 973.053** |

**Gearing constraint chain (corrected from C3B1):**

| Cell | Formula | Value | Classification |
|---|---|---|---|
| Inputs!D230 | *(scalar)* | 0.80 | Hedge Coverage fraction; **dual-use**: also gearing cap fraction in D195 |
| Inputs!D192 | `=DS!D51` | 42 852.279 kEUR | **DEBT_AMOUNT_kEUR** (not a gearing fraction) |
| DS!D47 | `=MAX($G$47:$DW$47)` | 42 852.279 kEUR | Max backward-induction sculpted capacity |
| DS!D51 | `=SUM(G51:DW51)` | 42 852.279 kEUR | Total sculpted debt = D47 |
| Gearing cap | G171 × D230 | 46 378.442 kEUR | Not binding (> D47) |
| **Inputs!D195** | **`=MIN(DS!$D$47, G171*$D$230)`** | **42 852.279 kEUR** | **DSCR capacity binding** |

D195 = D47 → **DSCR constraint is binding**. Gearing cap is not binding.
D192 = DS!D51: this is the debt amount output in kEUR, carried forward as a result — not a gearing fraction input.

Classification: **IDC_INCLUDED — DSCR_CONSTRAINT_BINDING — GEARING_CAP_NOT_BINDING**

---

### E · Hedge percentage and fixed/floating rate split

**DS!H44 is the ANNUAL all-in sculpting rate.**

Evidence: `DS!H64 = H61 × H44 × H6` where H6 ≈ 0.511 (year fraction for period 1). This confirms H44 is the annual rate applied over the period fraction — do NOT multiply H44 by 2.

| Cell | Description | Value |
|---|---|---|
| DS!B40 (`=Inputs!D230`) | Fixed/hedge fraction | **80%** |
| DS!B39 (`=1−B40`) | Floating fraction | **20%** |
| DS!C40 | Swap / fixed rate | **3.20%** |
| DS!H39 | Floating rate (EURIBOR VLOOKUP) | 3.71% (period 1) |
| DS!H41 | Blended base = SUMPRODUCT([0.20, 0.80], [3.71%, 3.20%]) | 3.302% |
| DS!H43 | Margin (VLOOKUP on DS!D51 vs Inputs spread table) | 2.65% |
| DS!H44 | **Annual sculpting rate = H41 + H43** | **5.951%** |

Interest identity verification (Period 1):  
`DS!H64 = opening_balance × H44 × H6 = 42 852.279 × 0.059514 × 0.511111 = 1 303.483 kEUR`  
Matches cached cell value to machine precision (max residual across all 28 periods = 0).

Classification: **ANNUAL_RATE_CONFIRMED — IDENTITY_VERIFIED**

---

## Equal-Input / Equal-Policy Comparison

### Parameters used

| Parameter | Excel source | Value fed to Phase 2C |
|---|---|---|
| Eligible project cost | Inputs!G171 | 57 973.053 kEUR |
| Gearing fraction | Inputs!D230 | 0.80 |
| DSCR target (uniform) | DS!row22 nominal | 1.15 |
| DSCR target (Excel bands) | DS!row22 p1–24 = 1.15, p25–28 = 1.35 | — |
| Sculpting rate | DS!H44 per period (annual) | matched per period |
| CFADS | CF!row79 per period | matched per period |

### Result: DSCR banding as sole divergence source

Phase 2C `build_schedule` API called with single `target_dscr=1.15` and Excel-matched per-period CFADS and interest rates.

| Metric | Value |
|---|---|
| Maximum absolute period Δclosing balance | **854.415 kEUR** |
| Periods outside 1 kEUR tolerance | **[25, 26, 27]** |
| First differing period | **25** |
| Periods 1–24 max Δ | < 0.001 kEUR |

**Per-period DSCR custom validation:** Phase 2C forward pass with per-period DSCR matching Excel (1.15 for p1–24, 1.35 for p25–28) → `Δ = 0` for all 28 periods. This proves the forward Newton iteration and Excel backward induction are **economically equivalent** — the sole source of divergence is the DSCR banding mismatch.

### Mismatch root causes

1. **DSCR banding** — Excel row22 switches from 1.15 to 1.35 at period 25 (Scenarios sheet). Phase 2C `build_schedule` accepts a single scalar `target_dscr`. When fed 1.15 uniformly, periods 25–28 under-sculpt → debt excess vs Excel. Max Δclosing = 854.415 kEUR at period 27. **This is the sole source of divergence.**

2. **CFADS composition** — In this model instance: H73 (local taxes) = 0, H76 (interest income) = 0. Phase 2C CFADS = EBITDA − cash_tax_paid maps to H23+H49+H77, which is identical here. No residual.

3. **Rate convention** — Phase 2C `annual_fixed_rate` must equal DS!H44 directly (annual). Confirmed by identity check: max residual across all 28 periods = 0 when H44 values are matched per period.

### No unexplained residual in equal-input comparison

All divergence between DS!D51 (42 852.279 kEUR) and Phase 2C is fully attributable to DSCR banding (item 1 above). When per-period DSCR is matched, `Δ = 0` — proved numerically.

---

## Verdict

**`C3B2_INPUT_OR_POLICY_MISMATCH_FULLY_EXPLAINED`**

The five open questions from C3B1 are closed. Full source closure achieved. No production code changes required or made.

Divergence between DS!D51 and Phase 2C output with `target_dscr=1.15` is **854.415 kEUR** (max period Δclosing), attributable entirely to DSCR banding. When the equal-input policy (per-period DSCR) is applied, the schedules match to machine precision.

---

## Files

| File | Purpose |
|---|---|
| `finco_recon/extract_oborovo_debt_interest.py` | C3B2 dual-load extractor v2.0.0 (5 workstreams + equal-input comparison via Phase 2C API) |
| `tests/fixtures/excel_oborovo_debt_interest_truth.json` | Fixture generated from real workbook (SHA-256 verified) |
| `tests/test_stage_c3b2_oborovo_debt_interest_source_closure.py` | 87 CI-portable tests |
| `docs/reconciliation/oborovo_debt_interest_source_closure.md` | This document |
| `.github/workflows/c3b2_debt_interest_check.yml` | CI workflow |

---

## Deferred (out of C3B2 scope)

- Feeding equal-input per-period DSCR into Phase 2C `build_schedule` via a multi-band API — requires production API extension, deferred to C3D.
- Margin ratchet mechanics (VLOOKUP table in Inputs rows 300–310) — identified, not traced.
- Multi-scenario sensitivity (different EURIBOR fixing) — not in scope.
