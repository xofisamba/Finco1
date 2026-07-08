# Inputs Sheet Mapping — Excel vs. App

Extracted from: TUHO (20260330_TUHO_BP.xlsm) and Oborovo (20260414_BP_Oborovo_Sensitivity_FINAL_for_PPT.xlsm)

---

## Classification of Every Input Field

### Identity

| Field | Excel Location | App surface | Classification |
|-------|---------------|-------------|----------------|
| Project Name | Inputs row 2 | Inputs — Identity | **Inputs** |
| Project Company | Inputs row 3 | — | Inputs (read-only) |
| Project Code | Inputs row 4 | Inputs — Identity | Inputs (read-only) |
| Country | Inputs row 5 | Inputs — Identity | Inputs (read-only) |

---

### Schedule

| Field | TUHO value | Oborovo value | App surface | Classification |
|-------|-----------|---------------|-------------|----------------|
| Financial Close | 2028-06-30 | 2029-06-29 | Inputs — Schedule | **Inputs** |
| Construction Time | 18 months | 12 months | Inputs — Schedule | **Inputs** |
| Operation Start (COD) | 2029-12-30 | 2030-06-29 | Inputs — Schedule | **Inputs** (derived or editable) |
| Model Period | Semestrial | Semestrial | Inputs — Runtime | Inputs (read-only) |
| Investment Horizon | 30 years | 30 years | Inputs — Schedule | **Inputs** |
| Year 0 | 2028 | 2029 | Inputs — Schedule | Derived |

---

### Technical / Yield

| Field | TUHO value | Oborovo value | App surface | Classification |
|-------|-----------|---------------|-------------|----------------|
| Capacity MW (DC) | 35 MW | 75.26 MW | Inputs — Technical | **Inputs** |
| Number of Turbines / Modules | 5 | — | Inputs — Technical | Inputs (template) |
| Production Scenario | P_50 | P_50 | Inputs — Technical | **Inputs** |
| Operating Hours P50 | 4,164 h/yr | 1,494 h/yr | Inputs — Technical | **Inputs** |
| Operating Hours P90 | 3,620 h/yr | 1,410 h/yr | Inputs — Technical | Inputs (template) |
| P90/P50 ratio | — | 0.9438 | Inputs — Technical | Derived |
| Curtailment | 0 | 0 | — | Inputs (advanced) |
| Power Curve Adjustment | 1.0 | — | — | Template |
| PV Degradation | — | 0.4%/yr | Inputs — Technical | Template |
| BESS Degradation | — | 0.3%/yr | — | Template |
| Plant Availability | 99% | 99% | Inputs — Technical (badge) | Template |
| Grid Availability | 99% | 99% | Inputs — Technical (badge) | Template |

---

### Revenue / PPA

| Field | TUHO value | Oborovo value | App surface | Classification |
|-------|-----------|---------------|-------------|----------------|
| PPA Base Tariff | 60 €/MWh | 57 €/MWh | Inputs — Revenue | **Inputs** |
| PPA Term | 12 years | 12 years | Inputs — Revenue | **Inputs** |
| PPA Index | 2% | 2% | Inputs — Revenue | **Inputs** |
| PPA Production % P50 | 100% | 100% | — | Inputs (advanced) |
| Market Price Y1 | 94.554 | 62.826 | — | Inputs (advanced) |
| Market Price Index | 2% | 2% | — | Inputs (advanced) |
| Market Curve Source | AFRY Q1 2026 | AFRY Q1 2026 | — | Template |
| Balancing Costs | 8 €/MWh | 0.025 | — | Inputs (advanced) |
| CO2 Certificates Active | False | True | Inputs — Revenue | **Inputs** |
| CO2 Price | — | 1.50 €/MWh | — | Inputs (advanced) |
| EMS Revenues (BESS) | — | 313.94 k€/MW | — | Output-only / template |

---

### CAPEX Summary (in Inputs sheet, not CapEx sheet)

| Field | TUHO value | Oborovo value | App surface | Classification |
|-------|-----------|---------------|-------------|----------------|
| Total Hard CAPEX | 70,691.54 | 55,999.09 | Inputs — CAPEX Summary | **CAPEX detail** (derived) |
| Financing Costs (C.17) | 2,302.17 | 1,973.97 | Inputs — CAPEX Summary | Output-only |
| Reserve Accounts (C.18) | 0 | 0 | Inputs — CAPEX Summary | Output-only |
| **Total CAPEX** | **72,993.71** | **57,973.05** | Inputs — CAPEX Summary | **Inputs** (editable override OR derived from CAPEX grid) |
| CAPEX / MW | ~2,085 | ~770 | Inputs — CAPEX Summary | Derived |
| VAT Rate | 13% | 17% | — | Template |
| Withholding Tax | 0% | 0% | — | Template |
| Scheduled Construction Time | 18 mo | 12 mo | Inputs — Schedule | Inputs (duplicate with Schedule section) |

---

### OPEX Summary (in Inputs sheet, not OpEx sheet)

| Field | Notes | App surface | Classification |
|-------|-------|-------------|----------------|
| Y1 OPEX per B.0x line | WTH flag + Y1 values repeated from OpEx | Inputs — OPEX Summary | **OPEX detail** |
| Total OPEX Y1 | Derived from OpEx sheet | Inputs — OPEX Summary | Derived |
| Contingency % | Rate from B.13 | Inputs — OPEX Summary | **Inputs** (or OPEX detail) |

---

### Debt / Sizing

| Field | TUHO value | Oborovo value | App surface | Classification |
|-------|-----------|---------------|-------------|----------------|
| Senior Debt Amount | 43,359 kEUR (59.40%) | 42,852 kEUR (73.92%) | Inputs — Debt | **Inputs** (or derived) |
| Equity | 500 kEUR (0.685%) | 500 kEUR (0.862%) | Inputs — Debt | Inputs |
| Shareholder Loan | 29,135 kEUR (39.91%) | 14,621 kEUR (25.22%) | Inputs — Debt | Inputs (derived) |
| VAT Facility | 3,362 kEUR | 4,878 kEUR | — | Output-only |
| Debt Maturity | 14 years | 14 years | Inputs — Debt | **Inputs** |
| Base Rate | 3.1% | 3.0% | Inputs — Debt | **Inputs** |
| Credit Margin | 265 bps | 265 bps | Inputs — Debt | **Inputs** |
| All-in Rate | 5.95% | 5.85% | Inputs — Debt | Derived |
| IDC Margin | 265 bps | 265 bps | — | Inputs (advanced) |
| Commitment Fee | 0.50% | 1.05% | — | Inputs (advanced) |
| Structuring Fee | 1.0% | 1.0% | — | Inputs (advanced) |
| Target DSCR | 1.2 | 1.15 | Inputs — Debt | **Inputs** |
| Lock-up DSCR | 1.1 | 1.1 | Inputs — Debt | **Inputs** |
| Min LLCR | 1.2 | 1.15 | — | Inputs (advanced) |
| Gearing Max Initial | 80% | 80% | — | Template |
| Hedge Coverage | 100% | 80% | — | Inputs (advanced) |
| Hedge Maturity | 14 years | 14 years | — | Inputs (advanced) |
| Swap Margin | 20 bps | 20 bps | — | Template |
| Bank Case Scenario | P_90-10y | P_90-10y | — | Inputs (advanced) |

---

### Tax

| Field | TUHO value | Oborovo value | App surface | Classification |
|-------|-----------|---------------|-------------|----------------|
| CIT Rate | Template (Croatia 18%) | Template | Inputs — Tax | Template |
| Property Tax | 0 | 0 | — | Template |
| Withholding Tax on dividends | 0% | 0% | — | Template |
| Loss Carryforward | Template | Template | Inputs — Tax | Template |

---

### Sponsor / SHL

| Field | TUHO value | Oborovo value | App surface | Classification |
|-------|-----------|---------------|-------------|----------------|
| Shareholder Loan Amount | 29,135 kEUR | 14,621 kEUR | Inputs — Sponsor | Derived |
| SHL Rate | Template | Template | — | Template |
| Equity Capital at FC | 500 kEUR | 500 kEUR | — | Inputs |
| Sponsor % | 100% | 100% | — | Inputs |

---

## Summary: Where Each Field Belongs in the App

| App Surface | Fields |
|-------------|--------|
| **Inputs — always editable** | Project Name, Financial Close, COD, Construction Months, Horizon, Capacity MW, P50 Hours, PPA Tariff, PPA Term, PPA Index, Total CAPEX (override), Y1 OPEX (override), Gearing, Target DSCR, Senior Tenor, Interest Rate |
| **Inputs — shown, template-locked** | Country, Model Period, P90 Hours, Plant/Grid Availability, Degradation %, CIT Rate, SHL Amount (derived) |
| **CAPEX detail grid** | All C.01–C.16 sub-line amounts, C.13 contingency rate |
| **OPEX detail grid** | All B.01–B.12 sub-line Y1 budgets, B.13 contingency rate, group inflation rates |
| **Output-only** | C.17, C.18, All-in Rate, Minimum DSCR (computed), VAT Facility, Year 2–30 OPEX values |
| **Advanced / future** | Market price curves, balancing costs, hedging parameters, commitment fee, structuring fee, LLCR |
