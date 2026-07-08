# CAPEX Sheet Mapping — Excel vs. App

Extracted from: TUHO (20260330_TUHO_BP.xlsm) and Oborovo (20260414_BP_Oborovo_Sensitivity_FINAL_for_PPT.xlsm)

---

## Column Layout (both models identical)

| Col | Header | Editable? | Notes |
|-----|--------|-----------|-------|
| A | Code (C.01, C.01.01…) | No | Row classifier |
| B | Description | No | Label |
| C | Amount kEUR | **Yes** (sub-lines only) | User input |
| D | Per MW | No | Formula: C / capacity |
| E | Contingency Level | **Yes** (group rows) | Rate applied to group total |
| F–H+ | Construction period profile | No for now | % per month — read-only in app v1 |

**Rule:** Only sub-line amount cells (C column, non-subtotal rows) are user-editable. Category rows, per-MW, and subtotals are always derived.

---

## C.01–C.18 Group Structure

### C.01 — Production Unit
- TUHO: Wind Turbines (C.01.01: Turbines 35,000 / TSA optionals / Flow Parts / Logistics)
- Oborovo: PV modules 10,912.70 (C.01.01: PV modules / Logistics)
- **Editable:** C.01.01 amount and sub-line amounts
- **Contingency:** ~6%

### C.02 — EPC Contract
- TUHO: Electrical BOP 720 / Civil BOP 2,040 / Grid connection 10,800
- Oborovo: Procurement 17,118 / Site Construction 9,312 / BESS supply+BOP
- **Editable:** All sub-line amounts

### C.03 — Grid Connection / EPC Other
- TUHO: Grid Connection Agreement 30 / Grid Usage Fees
- Oborovo: Project Management 1,543 / Take-over Commissioning 129 / Spare Parts 342
- **Note:** Oborovo splits this differently — C.03 used for "EPC Other" and a second C.03 for other construction

### C.04 — Monitoring & Telecom / Grid Connection
- TUHO: Telecom 50 / SCADA 50 / Energy Management System
- Oborovo: Grid Usage Sub. 0 / Grid connection fee 0 / OHL Supply 150 / SUBSTATION 3,900
- **Editable:** Sub-line amounts

### C.05 — Operation Investments
- TUHO: O&M Building 100 / Weather Station 300 / Temp Roads 100 / Special vehicles 500 / E&S Mitigation
- Oborovo: Utilities 10 / Telecom 5 / O&M Building 30 / Special vehicles 20 / Mitigation 15
- **Editable:** Sub-line amounts

### C.06 — Insurance
- TUHO: All Construction Risk 468.75 / Civil Liability / Marine Cargo DSU
- Oborovo: Operation All Risk 250 / TPL 5 / Substation / Spare parts
- **Editable:** Sub-line amounts

### C.07 — Land Securing
- TUHO: Land lease/acquisition 500 / Easement 12.44 / Expropriation
- Oborovo: (zero in extracted data)
- **Editable:** Sub-line amounts

### C.08 — Bank / Due Diligence
- TUHO: Bank 100 / Legal 100 / Technical Advisor / Insurance advisor / Energy yield
- Oborovo: Technical Advisor 10 / E&S Advisor 5 / Energy Yield 10 / Market Advisor 10 / Legal 60+60 / Tax Auditor 10
- **Editable:** Sub-line amounts

### C.09 — Construction Management (Third party)
- TUHO: 40 / Oborovo: 0
- **Editable:** Sub-line amounts

### C.10 — Commissioning
- TUHO: 0 / Oborovo: Advisors 10 / Power Curve Testing 5 / Commissioning 2
- **Editable:** Sub-line amounts

### C.11 — Audit / Accounting / Legal
- TUHO: Auditors 25 / Accounting 11 / Legal 1 / Legal Formalities
- Oborovo: 70 total
- **Editable:** Sub-line amounts

### C.12 — Construction Management (Sponsor)
- TUHO: Akuo Construction Services 1,742.25 / Geotech / Quality Control
- Oborovo: Sponsor Construction Services 1,071.13 / Geotech / HSE / Q&Q Control / Communication
- **Editable:** Sub-line amounts

### C.13 — Contingencies
- Formula: contingency % × sum of C.01–C.12
- **Editable:** Contingency % (rate field)
- TUHO: 6% → 3,036.94 / Oborovo: 3.5% → 1,986.44

### C.14 — Import Taxes / Taxes
- TUHO: 0 / Oborovo: 0
- **Editable:** Yes (usually zero)

### C.15 — Project Acquisition / Development
- TUHO: 0 / Oborovo: 18.33
- **Editable:** Sub-line amounts

### C.16 — Project Rights
- TUHO: Akuo Development Services 2,739.15 / Development costs 2,000 / Project Purchase 10,000
- Oborovo: Sponsor Development Services 2,024.48 / Market Services 0 / Project Purchase 6,500
- **Editable:** Sub-line amounts

### C.17 — Financing Costs ⚠ READ-ONLY
- TUHO: Bank Fees 467.11 / Structuring Fees / IDCs LT 1,519.56 / IDCs VAT 122.31 / Commitment Fees
- Oborovo: Structuring Fees 477.30 / IDCs LT 1,086.03 / IDCs VAT 208.45 / Commitment Fees
- **NOT editable** — backend calculated from debt parameters
- Sub-lines: C.17.01 Bank Fees / C.17.02 IDC / C.17.03 Equity Arrangement / C.17.04 Transaction Mgt

### C.18 — Reserve Accounts ⚠ READ-ONLY
- Both models: 0 (DSRA / MMRA / Working Capital)
- **NOT editable** — backend calculated
- Sub-lines: C.18.01 DSRA / C.18.02 MMRA / C.18.03 Working Capital

---

## Subtotal / Total Rows

| Row type | Description | Formula |
|----------|-------------|---------|
| Group subtotal | Sum of sub-lines for C.xx | SUM of direct children |
| Hard CAPEX subtotal | Sum C.01–C.12 | After contingency applied |
| Hard CAPEX incl. Bank Tax | C.01–C.16 | Includes taxes, acquisition, rights |
| Financing Costs | C.17 | Backend computed |
| Reserve Accounts | C.18 | Backend computed |
| **Total CAPEX** | C.01–C.18 | Grand total |
| VAT (separate row) | Total VAT on CAPEX | Shown separately |
| WTH | Withholding Tax | Shown separately |

---

## What the App Currently Exposes vs. Excel

| Feature | Excel | App current | Gap |
|---------|-------|-------------|-----|
| C.01–C.18 group structure | ✅ Full | ✅ via lig_render | Minor layout issues |
| Sub-line detail | ✅ Full | Partial (flat list) | Need proper hierarchy |
| Per-MW column | ✅ | ❌ Missing | Add derived column |
| Contingency % per group | ✅ | ❌ Missing | Add rate input |
| Construction spending profile | ✅ Monthly | ❌ | Out of scope v1 |
| C.17 read-only with breakdown | ✅ | Partial | Improve labelling |
| C.18 read-only | ✅ | Partial | Improve labelling |
| Hard CAPEX subtotal row | ✅ | ✅ | OK |
| Total CAPEX | ✅ | ✅ | OK |
| VAT / WTH rows | ✅ | ❌ | Low priority |

---

## App Data Model Requirements

```python
@dataclass
class CapexLine:
    code: str          # e.g. "C.01.01"
    parent_code: str   # e.g. "C.01"
    name: str
    amount_keur: float
    is_editable: bool  # False for C.17, C.18 and computed rows
    is_group: bool     # True for C.01, C.02... header rows
    contingency_rate: float | None  # Only on C.13 group row

@dataclass
class CapexGroup:
    code: str          # e.g. "C.01"
    name: str
    lines: list[CapexLine]
    subtotal_keur: float   # computed
    is_readonly: bool      # True for C.17, C.18

@dataclass
class CapexViewModel:
    groups: list[CapexGroup]
    hard_capex_keur: float      # C.01–C.16
    financing_keur: float       # C.17
    reserve_keur: float         # C.18
    total_capex_keur: float     # all
    capex_per_mw: float         # total / capacity_mw
```
