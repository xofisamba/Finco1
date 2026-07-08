# OPEX Sheet Mapping — Excel vs. App

Extracted from: TUHO (20260330_TUHO_BP.xlsm) and Oborovo (20260414_BP_Oborovo_Sensitivity_FINAL_for_PPT.xlsm)

---

## Column Layout (both models identical)

| Col | Header | Editable? | Notes |
|-----|--------|-----------|-------|
| A | Code (B.01, B.01.1…) | No | Row classifier |
| B | Description | No | Label |
| C | Budget kEUR | **Yes** (sub-lines) | Y1 base budget |
| D | Inflation rate | **Yes** (group rows) | e.g. 0.02 = 2% |
| E | WTH | No | Withholding Tax flag (0 or 1) |
| F | Year 1 value | No | = Budget (may differ if step change in Y1) |
| G | Year 2 value | No | Formula: F × (1 + inflation) |
| H–AH | Years 3–30 | No | Same escalation formula |

**Year escalation formula:** `Yn = Y1_budget × (1 + inflation_rate)^(n-1)`
Some sub-lines use step schedules (e.g. TUHO B.02.1 ramp: Y1=385.6, Y3=465.6, Y6=588, Y11=628).

**Rule:** Only sub-line budget amounts (col C) and group inflation rates (col D) are user-editable. Year columns are always derived. WTH flag is set per project template.

---

## B.01–B.13 Group Structure

### B.01 — Technical Management
- TUHO: 280 kEUR / 2% inflation
  - B.01.1: Asset Management 138 / Operation Management 67 / Performance monitoring 10 / Technical Inspections 13 / SCADA 18 / Met/weather 16 / Bazefield 18
- Oborovo: 198 kEUR / 2%
  - Asset Management 64 / Operation Management 105 / Bazefield 29 / Others
- **Editable:** Sub-line amounts, group inflation rate

### B.02 — Infrastructure Maintenance
- TUHO: 667.6 kEUR / 2%
  - **Step schedule:** O&M Preventive (B.02.1): Y1=385.6 / Y3=465.6 / Y6=588 / Y11=628
  - Minor Maintenance 27 / HV Substation / HSE / Met Station / Blade Maintenance / Vehicle 8
- Oborovo: 213 kEUR / 2%
  - O&M (Y1-only rate) 179 / O&M (Y2+) 117 / Substation / Inverters / Regulatory / Inverter service / Spare parts 64 / BESS-specific maintenance tiers
- **Editable:** Sub-line amounts, inflation. Step schedules are template-defined.

### B.03 — Maintain Site
- TUHO: 68 kEUR / 2% — Vegetation 20 / Roads 36 / Pest 2 / Inspections 10
- Oborovo: 45.2 kEUR / 2% — Clean Site 29.3 / Roads 14.1 / Pest 1.8
- **Editable:** Sub-line amounts

### B.04 — Clean Material
- TUHO: 5 kEUR / 2% — Water supply 5
- Oborovo: 40 kEUR / 2% — Clean Panels 40 / Water supply (solar needs panel cleaning)
- **Editable:** Sub-line amounts

### B.05 — Security
- TUHO: 50 kEUR / 2% — Surveillance systems 30 / Surveillance patrols 20
- Oborovo: 30.1 kEUR / 2% — Surveillance systems 30.1 / Patrols
- **Editable:** Sub-line amounts

### B.06 — Insurance
- TUHO: 468.75 kEUR / 2% — Operation All Risk with BI 468.75 / TPL / Substation / Spare parts / Wake compensation
- Oborovo: 255 kEUR / 2% — Operation All Risk 250 / TPL 5 / Substation / Spare parts / Storage Insurance
- **Editable:** Sub-line amounts

### B.07 — Lease & Property Tax
- TUHO: 244 kEUR / 2% — Land Leases 244 / Property tax
- Oborovo: 204 kEUR / 2% — Land Leases 204 / Property tax
- **Editable:** Sub-line amounts

### B.08 — Power Expenses
- TUHO: 93.72 kEUR / 2% — Power consumption 45 / Grid Usage fee 48.72 / Balancing
- Oborovo: 549.76 kEUR / **0%** — Power 40 / Grid Usage 86.86 / Balancing 372.90 (Y11+) / Grid Storage 50
- **Note:** Oborovo B.08 has 0% inflation AND conditional line activation (Balancing zero Y1–Y10)
- **Editable:** Sub-line amounts, inflation rate

### B.09 — Telecom Fees / Fees
- TUHO: 0 kEUR / 2% — Reporting Data / Telecom Connection
- Oborovo: 14 kEUR / 0% — Reporting 5 / Local concession 4 / SCADA 5
- **Editable:** Sub-line amounts

### B.10 — Audit / Accounting / Legal
- TUHO: 32 kEUR / 2% — Auditors 16 / Accounting 8 / Legal 8 / Book-keeping / Legal Formalities
- Oborovo: 32 kEUR / 2% — Auditors Y1–Y2 only 16 / Auditors Y3+ 8 / Accounting 8
- **Note:** Oborovo uses step schedule — auditor fee higher in first 2 years

### B.11 — Bank Fees
- TUHO: 20 kEUR / 2% — Agency Fee 20 / Bonds / Bank Fees
- Oborovo: 20 kEUR / 2% — same
- **Editable:** Sub-line amounts

### B.12 — Environmental & Social
- TUHO: 400 kEUR / 2% — Mitigation measures 200 / Fauna&Flora Monitoring 200 (Y1–Y2 only) / E&S monitoring / HSE visits
- Oborovo: 32 kEUR / 2% — Mitigation 10 / Fauna&Flora (Y1–Y2) 10 / E&S monitoring (Y1–Y2) 10 / HSE visits 2
- **Note:** E&S monitoring often time-limited (Y1–Y2 or Y1–Y5)

### B.13 — Contingencies
- Formula: contingency_rate % × TOTAL OPEX excl. Contingencies
- TUHO: 6% → 139.74 kEUR / Oborovo: 4% → 65.32 kEUR
- **Editable:** Contingency rate (not the amount — derived)

---

## Additional Sections Below B.13 (TUHO only, all zero)

| Section | Description |
|---------|-------------|
| C / C.01–C.03 | Claims (Attorney, Technical advisor, Justice) — zero |
| D / D.01–D.03 | Salary and payroll — zero |
| E / E.01–E.03 | Specific Revenues (Connection Repayment, Subsidy) — zero |
| F / F.07–F.09 | Other Taxes (Stamp Duty) — zero |

These are project-specific overrides. Show as read-only in app if value is non-zero.

---

## Total / KPI Rows

| Row | Formula |
|-----|---------|
| TOTAL OPEX excl. Contingencies | SUM B.01–B.12 per year |
| TOTAL OPEX incl. Contingencies | Above + B.13 per year |
| OPEX/MW | Total Y1 / capacity_mw |
| OPEX/MWh | Total Y1 × 1000 / (p50_hours × capacity_mw) |

---

## Year Column Rules

1. **Y1:** budget amount (col C). If step schedule, may differ.
2. **Y2–Y30:** `Y1_budget × (1 + inflation)^(year-1)` for simple lines
3. **Step schedule lines:** fixed amounts at specific years (template-defined, not user-editable in v1)
4. **Conditional active lines:** some lines are zero for a range of years then activate (e.g. Oborovo B.08 Balancing zero Y1–Y10)

---

## What the App Currently Exposes vs. Excel

| Feature | Excel | App current | Gap |
|---------|-------|-------------|-----|
| B.01–B.13 groups | ✅ | ✅ dynamic loop | OK |
| Sub-line detail | ✅ | ✅ per item | OK |
| Y1 editable | ✅ | ✅ | OK |
| Inflation % per group | ✅ Col D | ✅ shown | Not editable |
| WTH % per line | ✅ Col E | ❌ not shown | Add column |
| Y2–Y30 display | ✅ | ❌ | Add display columns |
| Step schedules | ✅ template | ❌ | Out of scope v1 |
| Contingency rate editable | ✅ | ❌ | Add |
| OPEX/MW KPI | ✅ | ❌ | Add to summary |
| OPEX/MWh KPI | ✅ | ❌ | Add to summary |
| Subtotal rows | ✅ | ✅ | OK |
| Grand total rows | ✅ | ✅ | OK |
| Sticky header | ✅ frozen pane | ❌ broken | Fix properly |
| Sticky first column | ✅ frozen pane | ❌ broken | Fix properly |

---

## App Data Model Requirements

```python
@dataclass
class OpexLine:
    code: str           # e.g. "B.01.1"
    parent_code: str    # e.g. "B.01"
    name: str
    y1_keur: float
    inflation_pct: float
    wht_flag: bool
    is_editable: bool
    is_group: bool
    # Derived (display only, never submitted to engine)
    year_values: dict[int, float]  # {1: 280.0, 2: 285.6, ...}

@dataclass
class OpexGroup:
    code: str           # e.g. "B.01"
    name: str
    lines: list[OpexLine]
    inflation_pct: float   # group-level default
    subtotal_per_year: dict[int, float]  # {1: 280.0, ...}

@dataclass
class OpexViewModel:
    groups: list[OpexGroup]
    contingency_rate: float
    total_excl_contingency_per_year: dict[int, float]
    total_incl_contingency_per_year: dict[int, float]
    opex_per_mw: float
    opex_per_mwh: float
    display_years: list[int]  # [1, 2, ..., 30] or subset
```
