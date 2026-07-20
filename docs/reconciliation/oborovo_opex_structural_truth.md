# Oborovo OPEX Structural Truth — Audit Report

**Workbook**: `20260414_BP_Oborovo_Sensitivity_FINAL_for_PPT.xlsm`  
**SHA256**: `15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920`  
**Extraction date**: 2026-07-20  
**Sheet**: `OpEx` (values), `Scenarios!E` (base-case budgets), `Inputs!D85/D196` (shared parameters)

---

## Summary

Oborovo has 13 OPEX categories (B.01–B.13) plus Claims (C), Salary (D), and Taxes (F). All values are in kEUR nominal. Salary and Taxes are zero for this project.

| Category | Name | Budget (kEUR) | Inflation | Y1 Actual |
|----------|------|--------------|-----------|-----------|
| B.01 | Technical Management | 198.0 | 2% | 198.0 |
| B.02 | Infrastructure Maintenance | 213.0 | 2% | 244.0 |
| B.03 | Maintain Site | 45.2 | 2% | 45.2 |
| B.04 | Clean Material | 40.0 | 2% | 40.0 |
| B.05 | Security | 30.1 | 2% | 30.1 |
| B.06 | Insurance | 255.0 | 2% | 255.0 |
| B.07 | Lease & property Tax | 204.0 | 2% | 208.1 |
| B.08 | Power Expenses | 549.8 | 0% | 176.9 |
| B.09 | Fees | 14.0 | 0% | 14.0 |
| B.10 | Audit & Accounting & Legal | 32.0 | 2% | 24.0 |
| B.11 | Bank Fees | 20.0 | 2% | 20.0 |
| B.12 | Environmental & Social | 32.0 | 2% | 32.0 |
| B.13 | Contingencies (4%) | 65.3 | n/a | 51.5 |
| **Total excl. contingencies** | | **1,633.1** | | **1,287.2** |
| **Total incl. contingencies** | | **1,698.4** | | **1,338.7** |

---

## Shared Parameters

| Parameter | Cell | Value |
|-----------|------|-------|
| EUR CPI (inflation) | `Inputs!D85` | 2.0% |
| Senior debt tenor | `Inputs!D196` | 14 years |
| Second debt tenor | `Inputs!D259` | 7 years |

---

## B.01 Technical Management (198 kEUR, 2% CPI)

Standard: 4 subitems, all active Y1-Y30.

| Code | Name | Budget (kEUR) | Flags |
|------|------|--------------|-------|
| B.01.1 | Asset Management Contract | 64 | Y1-Y30: all 1 |
| B.01.1b | Operation Management Contract | 105 | Y1-Y30: all 1 |
| B.01.2 | Bazefield | 29 | Y1-Y30: all 1 |
| B.01.3 | Others | 0 | Y1-Y30: all 1 |

---

## B.02 Infrastructure Maintenance (213 kEUR, 2% CPI)

**Two-regime O&M**: the budget cell formula is `=SUM(C11:C25)+AVERAGE(C9:C10)`, which blends the two O&M subitems. Annual SUMPRODUCT uses all 17 rows. As a result:

- Y1: 179 kEUR (B.02.1 active, B.02.2 inactive) → 244.0 kEUR actual (see note)
- Y2-Y30: 117 kEUR (B.02.2 active, B.02.1 inactive)

| Code | Name | Budget (kEUR) | Flags |
|------|------|--------------|-------|
| B.02.1 | O&M Preventive & Corrective Y1-2 | 179 | Y1: 1, Y2-30: 0 |
| B.02.2 | O&M Preventive & Corrective Y3-30 | 117 | Y1: 0, Y2-30: 1 |
| B.02.3 | Substation & O&M Building | 0 | all 0 |
| B.02.4 | Inverter service contract / MRA | 1 | Y1-Y30: all 1 |
| B.02.5 | Spare parts reprocurement | 64 | Y1-Y30: all 1 |
| B.02.6 | Sponsor Operation Mgt - BESS | 0 | Y1-Y30: all 1 |

> **Note**: B.02 Y1 actual (244 kEUR) includes B.02.1 (179) + B.02.4 (1) + B.02.5 (64) = 244. B.02.2 OFF in Y1.  
> B.02 Y2 actual (185.64 kEUR) = (117 + 1 + 64) * 1.00 + inflation.

---

## B.03 Maintain Site (45.2 kEUR, 2% CPI)

All subitems active Y1-Y30.

| Code | Name | Budget (kEUR) |
|------|------|--------------|
| B.03.1 | Clean Site | 29.3 |
| B.03.2 | Repair roads | 14.1 |
| B.03.3 | Others | 0 |

---

## B.04 Clean Material (40 kEUR, 2% CPI)

| Code | Name | Budget (kEUR) |
|------|------|--------------|
| B.04.1 | Clean Panels | 40 |
| B.04.2 | Subscription to water supply | 0 |
| B.04.9 | Others | 0 |

---

## B.05 Security (30.1 kEUR, 2% CPI)

| Code | Name | Budget (kEUR) |
|------|------|--------------|
| B.05.1 | Surveillance systems | 30.1 |
| B.05.2 | Surveillance patrols | 0 |
| B.05.9 | Others | 0 |

---

## B.06 Insurance (255 kEUR, 2% CPI)

| Code | Name | Budget (kEUR) |
|------|------|--------------|
| B.06.1 | OAR-BI | 250 |
| B.06.2 | Third Party Liability | 5 |
| B.06.3 | Substation and O&M Building Coverage | 0 |
| B.06.4 | Spare parts insurance | 0 |
| B.06.9 | Storage Insurance | 0 |

---

## B.07 Lease & property Tax (204 kEUR, 2% CPI)

**Pre-COD inflation base**: workbook inflates from pre-COD (exponent = `year`, not `year-1`).  
Y1 actual = 204 × 1.02 = **208.08 kEUR**.

| Code | Name | Budget (kEUR) | Flags |
|------|------|--------------|-------|
| B.07.1 | Land Leases (85 ha × 2.4 kEUR/ha/y) | 204 | Y1-Y30: all 1 |
| B.07.4 | Property tax | 0 | Y1-Y30: all 1 |

---

## B.08 Power Expenses (549.8 kEUR, 0% inflation)

**Step-change at Y11**: Balancing costs (B.08.3) OFF for Y1-Y10, ON from Y11.

| Years | Annual Total |
|-------|-------------|
| Y1-Y10 | 176.86 kEUR (B.08.1 + B.08.2 + B.08.8) |
| Y11-Y30 | 549.76 kEUR (all subitems) |

| Code | Name | Budget (kEUR) | Flags |
|------|------|--------------|-------|
| B.08.1 | Power consumption | 40 | Y1-Y30: all 1 |
| B.08.2 | Grid Usage fee | 86.86 | Y1-Y30: all 1 |
| B.08.3 | Balancing costs | 372.90 | Y1-Y10: 0, Y11-Y30: 1 |
| B.08.8 | Grid usage fee Storage | 50 | Y1-Y30: all 1 |

---

## B.09 Fees (14 kEUR, 0% inflation)

Flat 14 kEUR per year.

| Code | Name | Budget (kEUR) | Flags |
|------|------|--------------|-------|
| B.09.1 | Reporting Data | 5 | Y1-Y30: all 1 |
| B.09.2 | Local concession fee | 4 | Y1-Y30: all 1 |
| B.09.3 | SCADA | 5 | Y1-Y30: all 1 |
| B.09.4 | Alarm/Security | 0 | all 0 |

---

## B.10 Audit & Accounting & Legal Fees (32 kEUR, 2% CPI)

**Auditor step-down**: higher audit fee Y1-Y2, lower from Y3.

| Years | Annual Total (pre-inflation) |
|-------|---------------------------|
| Y1-Y2 | 24 kEUR (B.10.1 + B.10.3) |
| Y3-Y30 | 16 kEUR (B.10.2 + B.10.3) |

| Code | Name | Budget (kEUR) | Flags |
|------|------|--------------|-------|
| B.10.1 | Auditors closing Y1&2 | 16 | Y1-Y2: 1, Y3-30: 0 |
| B.10.2 | Auditors closing >=Y3 | 8 | Y1-Y2: 0, Y3-30: 1 |
| B.10.3 | Accounting closing | 8 | Y1-Y30: all 1 |
| B.10.4 | Legal closing | 0 | all 0 |
| B.10.5 | Accounting book-keeping | 0 | all 0 |

---

## B.11 Bank Fees (20 kEUR, 2% CPI)

**Formula-driven activation**: B.11.3 uses `=IF(year<=Inputs!$D$196,1,0)`.  
With debt tenor = 14 years → **active Y1-Y14, zero Y15-Y30**.

This is not a static flag — it tracks the senior debt tenor in `Inputs!D196`.

| Code | Name | Budget (kEUR) | Activation |
|------|------|--------------|-----------|
| B.11.1 | Agency Fee | 0 | all 0 |
| B.11.2 | Bonds | 0 | all 0 |
| B.11.3 | Bank Fees | 20 | Y1-Y14: 1, Y15-Y30: 0 (formula) |
| B.11.4 | Others | 0 | all 0 |

---

## B.12 Environmental & Social (32 kEUR, 2% CPI)

**Monitoring expiry**: B.12.3 and B.12.5 active Y1-Y2 only.

| Years | Annual Total (pre-inflation) |
|-------|---------------------------|
| Y1-Y2 | 32 kEUR |
| Y3-Y30 | 12 kEUR (B.12.1 + B.12.6 only) |

| Code | Name | Budget (kEUR) | Flags |
|------|------|--------------|-------|
| B.12.1 | Mitigation measures | 10 | Y1-Y30: all 1 |
| B.12.2 | Agrinergie | 0 | all 0 |
| B.12.3 | Fauna & Flora Monitoring | 10 | Y1-Y2: 1, Y3-30: 0 |
| B.12.5 | E&S monitoring | 10 | Y1-Y2: 1, Y3-30: 0 |
| B.12.6 | HSE visits & controls | 2 | Y1-Y30: all 1 |

---

## B.13 Contingencies (4% rate)

Rate = 4% applied to the sum of annual totals:
```
B.13_Yn = 0.04 × (B.01_Yn + B.02_Yn + … + B.12_Yn + D_Yn + F_Yn)
```
**Claims (C) excluded.** Salary (D) = 0, Taxes (F) = 0 for Oborovo.

| Year | B.13 (kEUR) |
|------|------------|
| Y1 | 51.49 |
| Y2 | 49.84 |
| Y10 | 55.74 |
| Y11 | 71.62 (step from B.08.3 activation) |
| Y15 | 74.61 (step from B.11 expiry) |
| Y30 | 92.62 |

---

## Claims (C) — Not Applicable

Category C (Claims: Attorney, Technical Advisor, Justice fees) is present in the sheet but marked "Not Applicable". All flags = 0, budgets = null. Claims are excluded from the B.13 contingency base.

---

## Totals (workbook)

| Metric | Budget (kEUR) | Y1 Actual (kEUR) |
|--------|--------------|-----------------|
| Total OPEX excl. Contingencies & Claims | 1,633.06 | 1,287.24 |
| Total OPEX incl. Contingencies, excl. Claims | 1,698.39 | 1,338.73 |
