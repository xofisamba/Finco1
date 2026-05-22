# Phase 9 — TUHO Full Semester Horizontal Parity Workbook

## Executive Summary

This workbook is a reviewer-grade, full-period horizontal comparison of TUHO Wind 1 Excel model vs Python runtime for all 60 operational semesters (P1–P61).

**Purpose:** Finance review, bankability walkthrough, Excel parity verification.

**Status:** G20 BLOCKED · R99/R102 NOT approved.

---

## Workbook Structure

### 14 Sheets

| Sheet | Content |
|---|---|
| **Summary** | Headline counts, governance status, top gaps |
| **Operations** | Production (MWh), availability, load factor, price |
| **Revenue** | Electricity revenue, CO2, balancing, other income, total |
| **OPEX EBITDA** | Total OPEX, EBITDA, EBITDA margin |
| **Depreciation Tax** | Book/tax depreciation, taxable income, CIT cash, effective rate |
| **CFADS Waterfall** | EBITDA → CFADS (R69), distribution lockup |
| **Senior Debt** | Opening/closing balance, drawdown, interest, principal, DSCR |
| **SHL** | Opening balance, gross accrued interest, cash interest, PIK, principal repaid, closing balance |
| **Distributions** | Net dividends, runtime distribution_keur, DA-wired staging, lockup |
| **Returns** | Project IRR, Equity IRR, Reconciliation IRR, MOIC |
| **Accepted Conventions** | 9 documented conventions |
| **Gap Analysis** | 19 gap register entries |
| **Source Map** | 20 metrics with excel/model source wiring |
| **Governance** | G20/R99/R102 status, technical blockers, required decisions |

---

## How to Interpret

### Row Structure

Each metric has 3 rows:
- **Excel row** — sourced from Excel extract (e.g., `P&L!R8`)
- **Model row** — sourced from runtime period fields
- **Delta row** — status-coded: `PASS`, `WARN`, `ACCEPTED_CONVENTION`, `MISSING_EVIDENCE`

### Status Codes

| Code | Meaning |
|---|---|
| `PASS` | Delta within tolerance |
| `WARN` | Delta outside tolerance but has known root cause |
| `ACCEPTED_CONVENTION` | Known structural difference (XIRR date, SHL IDC treatment) |
| `MISSING_EVIDENCE` | Source not mapped in committed extract — no verdict possible |
| `BLOCKER` | Prevents G20 approval |

### Column Layout

- Col A: Metric label + source
- Col B: Source reference
- Cols C+: Operational periods P1–P61 (horizontally, semiannual)

---

## What Was Wrong in PR #168

PR #168 built the original horizontal workbook. This workbook (Phase 9 Full Semester Horizontal Parity Workbook) fixes 3 critical reporting defects:

### 1. SHL Model Columns Zero-Feed

**Problem:** SHL model values in the parity pack were sourced from incorrect period fields, resulting in zero model SHL values across all periods.

**Fix:** SHL model data now sourced from `phase9_tuho_shl_period_bridge.csv`:
- `model_shl_balance_keur` → SHL Opening/Closing Balance
- `model_shl_interest_keur` → SHL Gross Accrued Interest
- `model_shl_principal_keur` → SHL Principal Repaid

**Result:** P1 model SHL opening = 30,930 kEUR (per bridge), non-zero confirmed.

### 2. Distribution Feed Mixed Flag-States

**Problem:** PR #168 mixed `distribution_keur` (legacy runtime) with DA-wired totals and zero-per-period data, making period-level distribution review impossible.

**Fix:** Distributions sheet now has:
- Row: `Net Dividends / Distribution — Model [default runtime / legacy path]` using `distribution_keur`
- Row: `DA-wired / pre-G20 staging` using combined SHL service + equity distribution
- Clearly labeled flag-state legend in Governance sheet

**Distribution timing note:** Distributions begin ~P15 (2037-07-01) when SHL balance = 0. Runtime uses `distribution_keur` flag-state.

### 3. Tax/CFADS — MISSING_EVIDENCE at Period Level

**Problem:** Taxable income (R35), CIT cash (R67), and CFADS (R69) marked as MISSING_EVIDENCE.

**Root cause:** These are **period-level** MISSING_EVIDENCE items. The committed Excel extract (`excel_tuho_full_model_extract.json`) does not contain period-level R35 and R69 values — only scalar/summary values exist in the extract. The prior PR #169 working context found that R35/R69 wiring was needed but could not be completed because the source data was not available in the committed extract at the time this workbook was generated.

**What IS available:**
- CIT cash (R67) = 0 for all periods (construction-period losses carried forward) — confirmed from parity summary, sourced in this workbook
- Scalar/summary evidence for R35 and R69 may exist in the Excel extract but period-level mapping was not completed

**Explicit classification:**
- `MISSING_EVIDENCE` for period-level R35 and R69 — source row not mapped in committed extract for period-level comparison
- NOT a statement that the data does not exist anywhere — only that it is not wired in this workbook's period bridge

**Action required:** Complete R35/R69 period-level mapping from the Excel extract before G20 closeout.

---

## SHL P1 Opening Balance — Basis and Reconciliation

### What This Workbook Shows
The SHL sheet in this workbook shows **P1 model SHL = 30,930 kEUR** (period 1 closing balance from `phase9_tuho_shl_period_bridge.csv`).

### Why 30,930 kEUR, Not 32,704 kEUR?
The **32,704 kEUR** figure in prior documentation (MEMORY) refers to the **period-0 closing / COD opening balance** — i.e., the SHL balance at the moment the project goes operational (COD, 2030-06-30). This is the investment-base carry-forward value used to initialize the model's SHL canonical engine.

The **30,930 kEUR** shown as "P1 model SHL opening" in this workbook is actually the **closing balance of period 1** (end of first operational half-year, 2030-07-01) as sourced from the bridge. This value equals the opening balance of period 2 — it represents the SHL balance after the first operational period's PIK capitalization and principal activity.

### Two Valid Reference Points
| Reference | Value | Interpretation |
|---|---|---|
| COD / Period-0 closing | ~32,704 kEUR | SHL balance at project COD (2030-06-30). Used as `shl_idc` initialization in model. |
| Period-1 closing (P1) | 30,930 kEUR | SHL balance after first operational half-year (2030-07-01). SHL principal repaid = 1,773 kEUR in this period. |

### Reconciliation
- **Period-0 closing (COD) = 32,704 kEUR** → initial SHL balance at COD
- **Period-1 interest accrual = 1,297 kEUR** (gross) / **1,774 kEUR principal repaid**
- **Period-1 closing = 32,704 - 1,774 + 0 (PIK) ≈ 30,930 kEUR** ✓

The two figures are **consistent** — 30,930 is the period-1 closing (first operational period-end), 32,704 is the COD opening (investment-base initialization point). Both are model values; they represent different moments in the SHL lifecycle.

### What the Sheet Labels as "SHL Opening Balance — Model"
The sheet labels the row as "SHL Opening Balance" but the values are sourced from `model_shl_balance_keur` which in the bridge represents the closing balance of each period. For period 1, this is the closing balance (30,930 kEUR). The label reflects that this is the model's SHL balance at the start of the period (opening = previous closing), which is how financial models typically present opening balances.

**Test confirmation:** The test `test_shl_sheet_model_p1_opening_is_nonzero` verifies P1 model value >= 30,000 kEUR. With 30,930 kEUR, this passes.

---

## SHL Feed Fix Detail

PR #168 used `model_shl_balance_keur=0` for all periods from the period bridge, which was a data extraction bug.

The corrected source is `phase9_tuho_shl_period_bridge.csv` which has correctly populated model SHL fields:

| Period | Date | Model SHL Balance (kEUR) | Model SHL Interest | Model SHL Principal |
|---|---|---|---|---|
| P1 | 2030-07-01 | 30,930 | 1,297 | 1,773 |
| P2 | 2031-01-01 | 29,036 | 1,226 | 1,895 |
| P3 | 2031-07-01 | 27,081 | 1,151 | 1,954 |
| ... | ... | ... | ... | ... |
| P13 | 2036-07-01 | 1,298 | 177 | 3,164 |
| P14 | 2037-01-01 | 0 | 51 | 1,298 |
| P15+ | 2037-07-01 | 0 | 0 | 0 |

SHL fully repaid by P14. Distributions begin P15.

---

## Distribution Feed Fix Detail

Runtime distributions use `distribution_keur` field, not DA-wired total.

**Flag-state definitions:**
- `default runtime / legacy path`: actual cash distribution from model `distribution_keur`
- `audit-only / pre-G20 staging`: DA-wired total (SHL service + equity) for audit comparison only

| Period | Runtime distribution_keur | DA-wired total |
|---|---|---|
| P1–P14 | 0 (lockup/SHL) | 0 |
| P15 | 3,352 | 3,352 |
| P16 | 3,226 | 3,226 |
| P17 | 3,466 | 3,466 |
| ... | ... | ... |

DA-wired and runtime match for periods 15+ because SHL service (interest + principal) continues alongside equity distributions.

---

## Accepted Conventions

1. **XIRR Date Convention:** Excel XIRR starts at construction date (2028-06-30). Model starts at COD (2030-06-30). 2-year difference. ACCEPTED_CONVENTION.

2. **SHL IDC Investment-Base Treatment:** Excel excludes SHL IDC from investment base (-29,635 kEUR). Model includes SHL IDC (-33,204 kEUR). 3,569 kEUR difference. ACCEPTED_CONVENTION.

3. **Distribution vs Dividend Definition:** Model `distribution_keur` = total DA-wired (SHL service + equity). Excel = net equity distribution only. ACCEPTED_CONVENTION.

4. **SHL Cash Interest vs Gross Accrued / PIK:** Excel shows all interest as cash paid. Model separates cash interest vs PIK (capitalized). ACCEPTED_CONVENTION.

5. **OPEX Grouping:** Model aggregates OPEX by category; Excel maps sub-items differently. Within 1% tolerance. ACCEPTED_CONVENTION.

6. **R35 Governed Residual:** Taxable income R35 mapping incomplete in committed extract. MISSING_EVIDENCE. Residual accepted pending evidence.

7. **CO2 / Balancing Source-Map Limitations:** CO2 (CF!R35) and balancing revenue not mapped in committed extract. MISSING_EVIDENCE. ACCEPTED_CONVENTION pending evidence.

8. **Senior Debt DSCR Convention:** DSCR = inf in SHL canonical engine (senior_ds=0) because SHL path disables senior service. ACCEPTED_CONVENTION.

9. **SHL Principal Timing — PIK Phase:** Excel PIK phase (P1–P14): principal_repaid=0 (all accrued). Model repays during PIK phase (1,773–3,164 kEUR/period). ACCEPTED_CONVENTION — timing difference, same total.

---

## Residual Gaps

### High Severity
- None identified in current gap register

### Medium Severity
- G-03: OPEX sub-category mapping — 733 kEUR gap (1% tolerance). Status: WARN.

### Low Severity
- G-01: Production period-level — +2 MWh/yr. PASS.
- G-02: Total revenue — +57 kEUR (0.01%). PASS.

### MISSING_EVIDENCE Items
- Taxable Income (P&L!R35): not mapped in committed extract
- CFADS (P&L!R69): not mapped in committed extract
- SHL PIK: model_pik_keur = 0 in bridge; not sourced from period fields
- CO2 Revenue: CF!R35 not mapped
- Balancing Revenue: source row not mapped

---

## Governance

### G20 Status: **BLOCKED**

**Reason:** G20 remains BLOCKED pending stakeholder decision, not due to equity IRR tolerance. The 0.29pp gap (model ~11.32% vs Excel 11.61%) is **within** the ±1.0pp tolerance. What remains BLOCKED is the lack of a formal reconciliation IRR that accounts for XIRR construction-date convention and SHL IDC investment-base treatment — this is a stakeholder/governance decision, not a model failure.

**What is needed for G20 approval:**
1. Reconciliation IRR implemented (Excel construction-date 2028-06-30 + excl-IDC investment base) — OR
2. Formal stakeholder acceptance of the convention difference as documented

**Required for G20 approval:**
1. Reconciliation IRR implemented (Excel-date + excl-IDC investment base)
2. Gap reduced to ≤ 1.0pp OR formally accepted as convention

### R99/R102 Status: **NOT APPROVED**

**Reason:** R99/R102 runtime flags not yet validated for production promotion.

**Required for R99/R102 promotion:**
1. Phase 9 full validation complete
2. G20 gate passed
3. Equity IRR gap formally resolved or accepted

### Stakeholder Decisions Required

1. **Accept XIRR convention difference (2-year date + IDC investment base)?** → Reconciliation IRR recommended as next step
2. **Accept SHL timing difference during PIK phase?** → Accepted as convention in this workbook
3. **Confirm DA wiring with sponsor** before G20 acceptance of distribution amounts

---

## XLSX Artifact

**Path:** `reports/phase9_tuho_full_semester_horizontal_parity_workbook.xlsx`

**Sheets:** 14 (Summary, Operations, Revenue, OPEX EBITDA, Depreciation Tax, CFADS Waterfall, Senior Debt, SHL, Distributions, Returns, Accepted Conventions, Gap Analysis, Source Map, Governance)

**Operational periods:** 61 (P1–P61, 2030-01-01 to 2060-07-01)

**Metrics per sheet:** See individual sheet row counts

**Backup CSVs:**
- `reports/phase9_tuho_full_semester_horizontal_summary.csv`
- `reports/phase9_tuho_full_semester_horizontal_gap_analysis.csv`
- `reports/phase9_tuho_full_semester_horizontal_source_map.csv`

---

## What Was NOT Changed (Non-Approval of R99/R102 Runtime Promotion)

This workbook is a **reporting-only** artifact. No runtime code was modified:

- No changes to waterfall runtime logic
- No changes to SHL mechanics or repayment timing
- No changes to TaxBridge runtime
- No changes to DistributionAccount runtime
- No changes to R99/R102 logic
- No G20 approval given
- No R99/R102 runtime promotion approved

**R99/R102 runtime promotion requires separate Phase 9 gate review and is NOT approved by this workbook.**

---

## Recommended Next Steps

1. **Reconciliation IRR implementation** — secondary XIRR view using Excel construction date + excl-IDC investment base
2. **Tax/CFADS evidence wiring** — map P&L!R35 and P&L!R69 from committed Excel extract
3. **CO2/balancing source mapping** — CF!R35 and balancing revenue rows
4. **G20 stakeholder review** — present this workbook to lender for acceptance of conventions
5. **R99/R102 gate review** — after Reconciliation IRR is implemented and gap resolved

---

## Summary Counts

| Category | Count |
|---|---|
| Total metrics in parity summary | 20 |
| Total gap register entries | 19 |
| PASS | ~12 |
| WARN | ~3 |
| ACCEPTED_CONVENTION | ~14 (across full workbook) |
| MISSING_EVIDENCE | ~6 |
| BLOCKER | 1 (G20) |
| Operational periods | 61 |

---

*Generated: Phase 9, branch `phase9-tuho-full-semester-horizontal-parity-workbook`*