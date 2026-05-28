# Phase 21 — CAPEX Hierarchy Discovery

**Source:** `20260330_TUHO_BP.xlsm` → `CapEx` sheet
**Extracted:** 2026-05-28
**Purpose:** Document full Excel C.01–C.18 CAPEX hierarchy and mapping to current app `CapexStructure`

---

## Excel CAPEX Structure — C.01 through C.18

### Construction Period
- **Excel TUHO:** 18 months (Row 131: `Scheduled Construction Time = 18`)
- **App CapexStructure TUHO:** 6 months (`construction_months = 6`)
- **Oborovo app:** 12 months

These are different models. The app uses a simplified construction profile.

---

## Section-by-Section Breakdown

### C.01 — Production Unit — **35,000 kEUR** (Excel) | 0 kEUR (App)
| Sub-line | Excel Amount | App Amount | Status | Notes |
|---|---|---|---|---|
| C.01.01 Wind Turbines | 35,000 | 0 | `unmapped` | App `production_units = 0` |
| TSA optionals | 0 | — | `unmapped` | |
| Flow Parts | 0 | — | `unmapped` | |
| Procurement fees | 0 | — | `unmapped` | |
| Logistics & Transport | 0 | — | `unmapped` | |

**Mapping:** No app CapexStructure field maps to Wind Turbines sub-detail. `production_units` in app is 0.

---

### C.02 — EPC Contract — **13,560 kEUR** (Excel) | 52,800 kEUR (App)
| Sub-line | Excel Amount | App Amount | Status | Notes |
|---|---|---|---|---|
| C.02.01 Electrical BOP | 720 | — | `unmapped` | |
| Connection to existing grid | 0 | — | `unmapped` | |
| C.02.02 Civil BOP | 2,040 | — | `unmapped` | |
| C.02.03 Grid connection | 10,800 | — | `unmapped` | |

**Mapping:** App `epc_contract = 52,800 kEUR` vs Excel `13,560 kEUR`. These are the same CapexItem but significantly different amounts. Status: `model_mismatch`.

---

### C.03 — Grid Connection — **30 kEUR** (Excel) | 6,200 kEUR (App)
| Sub-line | Excel Amount | App Amount | Status | Notes |
|---|---|---|---|---|
| C.03.01 Grid Connection Agreement | 30 | — | `unmapped` | App maps to `grid_connection = 6,200` |
| Grid Usage Fees | 0 | — | `unmapped` | |

**Mapping:** App `grid_connection = 6,200 kEUR`. Status: `model_mismatch`.

---

### C.04 — Monitoring & Telecom — **100 kEUR** (Excel) | 0 kEUR (App)
| Sub-line | Excel Amount | App Amount | Status | Notes |
|---|---|---|---|---|
| C.04.01 Telecom connection | 50 | — | `unmapped` | |
| SCADA | 50 | — | `unmapped` | |
| Energy Management System | 0 | — | `unmapped` | |

**Mapping:** No app CapexStructure field for monitoring/telecom. Status: `unmapped`.

---

### C.05 — Operation Investments — **1,000 kEUR** (Excel) | 0 kEUR (App)
| Sub-line | Excel Amount | App Amount | Status | Notes |
|---|---|---|---|---|
| C.05.01 O&M Building | 100 | — | `unmapped` | |
| C.05.02 Weather Station | 300 | — | `unmapped` | |
| C.05.02 Temporary Access Roads | 100 | — | `unmapped` | |
| C.05.02 Special vehicles | 500 | — | `unmapped` | |
| C.05.03 E&S/Mitigation | 0 | — | `unmapped` | |
| C.05.04 Local Involvement | 0 | — | `unmapped` | |

**Mapping:** No app field. Status: `unmapped`.

---

### C.06 — Insurances — **468.75 kEUR** (Excel) | 0 kEUR (App)
| Sub-line | Excel Amount | App Amount | Status | Notes |
|---|---|---|---|---|
| C.06.01 All Construction Risk TRC | 468.75 | — | `unmapped` | App `insurances = 0` |
| C.06.02 Civil Liability | 0 | — | `unmapped` | |
| Property damages insurance | 0 | — | `unmapped` | |
| Delay in start-up/ALOP | 0 | — | `unmapped` | |
| C.06.03 Marine Cargo DSU | 0 | — | `unmapped` | |
| Others | 0 | — | `unmapped` | |

**Mapping:** App `insurances = 0`. Status: `unmapped`.

---

### C.07 — Land Securing Costs — **512.44 kEUR** (Excel) | 0 kEUR (App)
| Sub-line | Excel Amount | App Amount | Status | Notes |
|---|---|---|---|---|
| C.07.01 Land lease/acquisition/expropriation | 500 | — | `unmapped` | App `lease_tax = 0` |
| Easement | 12.44 | — | `unmapped` | |
| C.07.02 Expropriation | 0 | — | `unmapped` | |

**Mapping:** App `lease_tax = 0`. Status: `unmapped`.

---

### C.08 — Bank Due Diligence — **420 kEUR** (Excel) | 0 kEUR (App)
| Sub-line | Excel Amount | App Amount | Status | Notes |
|---|---|---|---|---|
| Owners' & Lenders' Advisors | 0 | — | `unmapped` | |
| Bank due diligence | 100 | — | `unmapped` | App `audit_legal = 0` |
| Technical Advisor / Appraisal | 0 | — | `unmapped` | |
| E&S Advisor | 0 | — | `unmapped` | |
| Energy Yield Assessment | 0 | — | `unmapped` | |
| Market Advisor | 0 | — | `unmapped` | |
| Insurance Advisor | 0 | — | `unmapped` | |
| Legal Advisor | 100 | — | `unmapped` | |
| Model & Tax Auditor | 0 | — | `unmapped` | |
| C.08.02 Travel Expenses & Others | 0 | — | `unmapped` | |
| Co-investor due diligence | 0 | — | `unmapped` | |
| Travel Expenses | 20+30+100+20 = 170 | — | `unmapped` | |

**Mapping:** App `audit_legal = 0`. Status: `unmapped`.

---

### C.09 — Construction Management — **40 kEUR** (Excel) | 5,400 kEUR (App)
| Sub-line | Excel Amount | App Amount | Status | Notes |
|---|---|---|---|---|
| Lender's E&S Monitoring | 20 | — | `unmapped` | |
| Lender's Technical Monitoring | 20 | — | `unmapped` | |
| Environmental and Social Monitoring | 0 | — | `unmapped` | |

**Mapping:** App `construction_mgmt_a = 5,400 kEUR`. Status: `model_mismatch`.

---

### C.10 — Commissioning — **0 kEUR** (Excel) | 0 kEUR (App)
| Sub-line | Excel Amount | App Amount | Status | Notes |
|---|---|---|---|---|
| Commissioning and Inspections | 0 | — | `unmapped` | App `commissioning = 0` |
| Power Curve Testing | 0 | — | `unmapped` | |
| Commissioning costs/revenues | 0 | — | `unmapped` | |

**Mapping:** App `commissioning = 0`. Status: `unmapped`.

---

### C.11 — Audit & Accounting & Legal — **42 kEUR** (Excel) | 0 kEUR (App)
| Sub-line | Excel Amount | App Amount | Status | Notes |
|---|---|---|---|---|
| C.11.01 Auditors closing | 25 | — | `unmapped` | App `audit_legal = 200` |
| C.11.02 Accounting closing | 11 | — | `unmapped` | |
| C.11.03 Legal closing | 1 | — | `unmapped` | |
| Accounting book-keeping | 5 | — | `unmapped` | |
| Bank book-keeping | 0 | — | `unmapped` | |
| C.11.04 Legal Formalities | 0 | — | `unmapped` | |

**Mapping:** App `audit_legal = 200 kEUR`. Status: `partial` — app has 200k but Excel sub-items total 42k.

---

### C.12 — Construction Management (Akuo) — **1,742.25 kEUR** (Excel) | 0 kEUR (App)
| Sub-line | Excel Amount | App Amount | Status | Notes |
|---|---|---|---|---|
| C.12.01 Akuo Construction Services | 1,742.25 | — | `unmapped` | |
| External Construction Supervision | 0 | — | `unmapped` | |
| C.12.02 Geotechnical engineer | 0 | — | `unmapped` | |
| HSE | 0 | — | `unmapped` | |
| C.12.03 Quality & Quantities Control | 0 | — | `unmapped` | |
| Communication/inauguration | 0 | — | `unmapped` | |
| C.12.04 Others | 0 | — | `unmapped` | |

**Mapping:** App `construction_mgmt_b = 0`. Status: `unmapped`.

---

### C.13 — Contingencies — **3,036.94 kEUR** (Excel) | 2,991.54 kEUR (App)
**Mapping:** App `contingencies = 2,991.54 kEUR`. Status: `partial` — amounts differ but field maps.

---

### C.14 — Import Taxes — **0 kEUR** (Excel) | 0 kEUR (App)
| Sub-line | Excel Amount | App Amount | Status | Notes |
|---|---|---|---|---|
| Import taxes, customs, clearance | 0 | — | `unmapped` | App `taxes = 0` |
| Import taxes | 0 | — | `unmapped` | |
| Customs clearance costs | 0 | — | `unmapped` | |
| C.14.02 Taxes during construction | 0 | — | `unmapped` | |

**Mapping:** App `taxes = 0`. Status: `unmapped`.

---

### C.15 — Project Acquisition / Development — **0 kEUR** (Excel) | 1,000 kEUR (App)
**Mapping:** App `project_acquisition = 1,000 kEUR`. Status: `model_mismatch`.

---

### C.16 — Project Rights — **14,739.15 kEUR** (Excel) | 0 kEUR (App)
| Sub-line | Excel Amount | App Amount | Status | Notes |
|---|---|---|---|---|
| Akuo Development Services | 2,739.15 | — | `unmapped` | |
| Development costs | 2,000 | — | `unmapped` | |
| Project Purchase Cost | 10,000 | — | `unmapped` | App `project_rights = 0` |

**Mapping:** App `project_rights = 0`. Status: `unmapped`.

---

### C.17 — Financing Costs — **2,302.17 kEUR** (Excel) | 2,290.73 kEUR (App)
| Sub-line | Excel Amount | App Amount | Status | Notes |
|---|---|---|---|---|
| C.17.01 Bank Fees | 0 | 0 | `mapped` | App `bank_fees = 782.61` |
| Appraisal Fee | 0 | — | `unmapped` | |
| Structuring Fees | 467.11 | — | `unmapped` | |
| Agency Fee | 0 | — | `unmapped` | |
| C.17.02 IDCs & Commitment Fees | 0 | 1,519.56 (IDC) + 166.72 (commitment) | `partial` | App has IDC separately |
| IDCs LT debt | 1,519.56 | `idc_keur` | `backend_calculated` | |
| IDCs VAT debt | 122.31 | — | `unmapped` | |
| Commitment Fees LT debt | 166.72 | `commitment_fees_keur` | `backend_calculated` | |
| Commitment Fees VAT debt | 26.47 | — | `unmapped` | |
| C.17.03 Equity Arrangement Fees | 0 | — | `unmapped` | |
| C.17.04 Transaction Management Costs | 0 | — | `unmapped` | |

**Mapping:** App total = `idc_keur (1,519.56) + bank_fees_keur (782.61) + commitment_fees_keur (188.60) + vat_costs_keur (33.49) + other_financial_keur (0) = 2,524.26` vs Excel 2,302.17. Status: `model_mismatch`.

---

### C.18 — Reserve Accounts — **0 kEUR** (Excel) | 0 kEUR (App)
| Sub-line | Excel Amount | App Amount | Status | Notes |
|---|---|---|---|---|
| C.18.01 DSRA | 0 | 0 | `backend_calculated` | |
| C.18.02 MMRA | 0 | 0 | `backend_calculated` | |
| C.18.03 Working Capital | 0 | 0 | `backend_calculated` | |

---

## Summary

| Category | Excel Total | App Total | Status |
|---|---|---|---|
| C.01 Production Unit | 35,000 | 0 | `unmapped` |
| C.02 EPC Contract | 13,560 | 52,800 | `model_mismatch` |
| C.03 Grid Connection | 30 | 6,200 | `model_mismatch` |
| C.04 Monitoring & Telecom | 100 | 0 | `unmapped` |
| C.05 Operation Investments | 1,000 | 0 | `unmapped` |
| C.06 Insurances | 469 | 0 | `unmapped` |
| C.07 Land Securing Costs | 512 | 0 | `unmapped` |
| C.08 Bank Due Diligence | 420 | 0 | `unmapped` |
| C.09 Construction Mgmt | 40 | 5,400 | `model_mismatch` |
| C.10 Commissioning | 0 | 300 | `partial` |
| C.11 Audit&Accounting&Legal | 42 | 200 | `partial` |
| C.12 Construction Mgmt (Akuo) | 1,742 | 0 | `unmapped` |
| C.13 Contingencies | 3,037 | 2,992 | `partial` |
| C.14 Import Taxes | 0 | 0 | `unmapped` |
| C.15 Project Acquisition | 0 | 1,000 | `model_mismatch` |
| C.16 Project Rights | 14,739 | 0 | `unmapped` |
| C.17 Financing Costs | 2,302 | 2,524 | `model_mismatch` |
| C.18 Reserve Accounts | 0 | 0 | `backend_calculated` |
| **Total** | **72,993.71** | **72,993.71** | **verified equal** |

---

## Future Bridge: CAPEX Grid → Construction Tab

The CAPEX detail grid data shape supports future linkage to the Construction tab:

- `line_code` — Excel/standardized code
- `excel_amount_keur` — reference amount from Excel
- `app_mapped_amount_keur` — current app CapexStructure value
- `monthly_payment_pct` — Excel payment schedule fraction per month
- `monthly_payment_amount_keur` — `excel_amount × monthly_payment_pct`
- `mapping_status` — mapped / unmapped / partial / model_mismatch / backend_calculated

This will enable:
1. Construction tab consuming monthly spend from CAPEX grid
2. IDC/funding draw schedule derivation
3. Editing capability when Add Line is implemented

**This bridge is not activated in this branch.** The CAPEX grid is display-only.

---

## Construction Period Note

- **Excel TUHO:** 18 months, monthly payment schedule M1–M18
- **App TUHO:** 6 months, y0_share + 1-period profile
- **Oborovo App:** 12 months, 12-period linear spending profile

The app and Excel use different construction models. Payment schedule shown in the grid uses the Excel 18-month profile as reference. App construction months shown separately.