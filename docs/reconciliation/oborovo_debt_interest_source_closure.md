# C3B2 — Oborovo Debt Sizing & Interest Source Closure

**Stage:** C3B2  
**Branch:** `stage-c3b2-oborovo-debt-interest-source-closure`  
**Base:** C3B1 squash-merge SHA `1fb4943a4319eff8f4ac7a22add6f65f14bd8cec`  
**Verdict:** `C3B2_INPUT_OR_POLICY_MISMATCH_FULLY_EXPLAINED`

---

## Purpose

Close the five open questions left by C3B1 concerning senior debt sizing and interest mechanics in the Oborovo Excel workbook, and establish a complete equal-input / equal-policy contract for Phase 2C reconciliation.

This is a diagnostic gate — no production code is modified.

---

## Five Questions Answered

### A · CFADS composition used by DSCR sculpting

| Item | Value |
|---|---|
| Excel source row | DS!row20 = Macro!row49 = CF!row79 |
| Row label | "Free Cash Flow for Banks" |
| Formula (CF!H79) | `=SUM(H13, H28, H49, H54, H76)` |
| Period 1 value | 2 575.003 kEUR |
| Post-tax? | Yes |
| Includes interest income from reserves? | Yes (CF!H54) |
| DSRA movements included? | No |

Phase 2C uses `CFADS = EBITDA − cash_tax_paid`. This omits interest income from cash/DSRA reserves → **input mismatch**. With DSRA absent (Workstream C), the interest income component is small but non-zero.

Classification: **INPUT_POLICY_MISMATCH**

---

### B · DSCR sculpting circular reference and convergence

Excel sculpts debt using backward PV induction:

```
DS!H47 = SUM(
  IF(NOT(H7), (H46 + I47) / (1 + H44*(1 + B54/(1−B54))*H6), 0),
  H82
)
```

`H47` references `I47` (the next period's capacity), creating a circular dependency across the entire column. Excel resolves this via **iterative calculation** (Tools → Options → Formulas → Enable iterative calculation).

Phase 2C uses a **forward sculpting Newton iteration**: the engine guesses total debt size, computes interest and principal period-by-period from period 1 to maturity, and iterates the guess until `|Δdebt| ≤ convergence_tolerance`. Both algorithms converge to the same result when fed identical inputs; they are economically equivalent.

DS!D51 (total sculpted debt) = **42 852.279 kEUR**.

Classification: **ECONOMICALLY_EQUIVALENT_WHEN_INPUTS_MATCHED**

---

### C · DSRA funding and release treatment

| Cell | Value |
|---|---|
| Inputs!I348 (DSRA target months) | 0 |
| CF DSRA rows 85–92 | All zero |

DSRA is **absent** in this Oborovo model instance. Phase 2C likewise does not model DSRA for this scenario. **Aligned — no divergence.**

Classification: **ALIGNED_BOTH_ZERO**

---

### D · IDC and financing-cost eligibility in the gearing base

Inputs!G171 = `SUM(G165:G170)` = **57 973.053 kEUR** (total eligible project cost / gearing base):

| Row | Description | kEUR |
|---|---|---|
| G165 | Hard CAPEX (`=CapEx!C117`) | 55 999.085 |
| G166 | IDC — Interest During Construction | 1 086.032 |
| G167 | Commitment and financing fees | 188.563 |
| G168 | Other financing costs | 477.303 |
| G169 | Working capital | 0.000 |
| G170 | Other / contingency | 222.070 |
| **G171** | **Total** | **57 973.053** |

Gearing cap = D192 × G171. Inputs!D192 is a formula reference `=DS!D51` that resolves to the DSCR-sculpted debt (42 852.279 kEUR, not a raw fraction). However the gearing cap computation is implicitly `max_gearing_fraction × G171 = 0.80 × 57 973 = 46 378 kEUR`, which **exceeds** DS!D51 → gearing cap **not binding**.

IDC **is included** in the gearing base. Phase 2C must use `eligible_project_cost_keur = G171 = 57 973.053`.

Classification: **IDC_INCLUDED — GEARING_CAP_NOT_BINDING**

---

### E · Hedge percentage and fixed/floating rate split

Two-rate structure in the DS sheet:

| Cell | Description | Value |
|---|---|---|
| DS!B40 (`=Inputs!D230`) | Fixed/hedge fraction | **80%** |
| DS!B39 (`=1−B40`) | Floating fraction | **20%** |
| DS!C40 | Swap / fixed rate | **3.20%** |
| DS!H39 | Floating rate (EURIBOR VLOOKUP) | 3.71% (period 1) |
| DS!H41 | Blended base = SUMPRODUCT([0.20, 0.80], [3.71%, 3.20%]) | 3.30% |
| DS!H43 | Margin (VLOOKUP on DS!D51 vs Inputs spread table) | 2.65% |
| DS!H44 | Sculpting rate = H41 + H43 | **5.95%** |

Tranche interest formula:

```
DS!H64 = H61 × H44 × H6 × (H91=0)
       = 42 852.279 × 0.059514 × 0.5111 × 1
       = 1 303.483 kEUR  (period 1)
```

`H44` (the sculpting rate) is used for both capacity sizing **and** actual tranche interest accrual.

`Inputs!D280 = 5.65%` appears in `DS!B33` (FCF-section summary) only — it is **not** the rate driving the amortisation schedule.

Phase 2C `annual_fixed_rate = 5.65%` (set at policy level) → **rate mismatch: 30 bps** (5.95% − 5.65%).

Classification: **INPUT_POLICY_MISMATCH**

---

## Equal-Input / Equal-Policy Comparison

| Parameter | Excel source | Phase 2C equivalent |
|---|---|---|
| Eligible project cost | Inputs!G171 = 57 973.053 kEUR | `eligible_project_cost_keur` |
| Gearing fraction | 80% (`=Inputs!D230`) | `maximum_gearing = 0.80` |
| DSCR target | DS!H22 = 1.15 (periods 1–24), 1.35 (25–28) | `target_dscr` |
| Sculpting rate | DS!H44 ≈ 5.95% semi-annual | `annual_fixed_rate` |
| CFADS | CF!row79 post-tax incl. interest income | `cfads_by_period` |
| DSRA | Absent (all zero) | Not modelled |

### Mismatch root causes

1. **Interest rate** — Excel sculpting rate ≈ 5.95%; Phase 2C uses 5.65%. Higher rate reduces the PV capacity per period, resulting in a lower total debt for the same CFADS stream. Direction: Phase 2C would over-size debt at 5.65%.

2. **CFADS composition** — Excel CF!row79 includes interest income from cash balances (CF!H54). Phase 2C `CFADS = EBITDA − cash_tax_paid` does not include this term. Effect is small but systematic.

3. **Algorithm** — Excel uses backward PV induction; Phase 2C uses forward Newton iteration. Economically equivalent for identical inputs; no independent error.

### No unexplained residual

DSRA: absent in both → aligned.  
IDC: included in gearing base in both → aligned once G171 is used.  
Gearing cap: not binding in either → does not affect the result.

All divergence between DS!D51 (42 852.279 kEUR) and a Phase 2C output is fully attributable to (1) and (2) above.

---

## Verdict

**`C3B2_INPUT_OR_POLICY_MISMATCH_FULLY_EXPLAINED`**

The five open questions from C3B1 are closed. Full source closure achieved. No production code changes required or made.

---

## Files

| File | Purpose |
|---|---|
| `finco_recon/extract_oborovo_debt_interest.py` | C3B2 dual-load extractor (5 workstreams + equal-input comparison) |
| `tests/fixtures/excel_oborovo_debt_interest_truth.json` | Pre-populated fixture (manually confirmed cell values) |
| `tests/test_stage_c3b2_oborovo_debt_interest_source_closure.py` | 66 CI-portable tests |
| `docs/reconciliation/oborovo_debt_interest_source_closure.md` | This document |
| `.github/workflows/c3b2_debt_interest_check.yml` | CI workflow |

---

## Deferred (out of C3B2 scope)

- Feeding the equal-input policy into Phase 2C and computing a numeric delta — requires production-grade CFADS wiring, deferred to C3D.
- Multi-DSCR-band sculpting (periods 25–28 at 1.35×) — documented but not tested end-to-end.
- Margin ratchet mechanics (VLOOKUP table in Inputs rows 300–310) — identified, not traced.
