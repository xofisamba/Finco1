# Scenarios Sheet Mapping — Excel vs. App

Extracted from: TUHO (20260330_TUHO_BP.xlsm) and Oborovo (20260414_BP_Oborovo_Sensitivity_FINAL_for_PPT.xlsm)

---

## Excel Structure: Input Matrix + Output Comparison

The Excel Scenarios sheet is **both input matrix AND output comparison** in a single sheet.

### Column Layout

| Col | TUHO | Oborovo |
|-----|------|---------|
| A | Code / Section label | "Accountable" (Dev/CTO/Finance/Insurance/S&E/Accounting/Legal/HSE) |
| B | Parameter label | Parameter label |
| C | Base Case / Scenario 4 | Base Case values |
| D | Scen 1 (NA) | Scenario 1 |
| E | Scen 2 (NA) | Scenario 2 |
| F | Scen 3 (Added Energy, 8 WTGs, 56MW) | Scenario 3 |
| G | Scen 4 (5 WTGs original) | — |

**TUHO had 4 scenarios. Oborovo has 3 + base.** Names are free-form.

### Oborovo "Accountable" column

Oborovo adds a responsibility column (Col A) that labels who owns each row:
- Dev/CTO → Technical assumptions
- Finance → Debt/equity sizing
- Insurance → Insurance costs
- S&E → Environmental & social
- Accounting → Accounting/audit
- Legal → Legal/permits
- HSE → Health, safety, environment

This is a governance feature — useful for lender packages but out of scope for app v1.

---

## Sections in Excel Scenarios Sheet

### Section 1 — TECHNICAL

| Parameter | TUHO example | Editable in scenarios? |
|-----------|-------------|------------------------|
| Turbine Type | 7 MW Vestas V172 | No (template) |
| Capacity (MW) | 35 / 35 / 35 / 56 / 35 | **Yes** |
| Number of turbines | 5 / 5 / 5 / 8 / 5 | **Yes** |
| Nominal capacity per turbine | 7 MW | Template |
| Yield P50 (hours) | 4,164 | **Yes** |
| Yield P90 (hours) | 3,620 | **Yes** |
| PV-specific: BESS modules, PCS, energy/power | Oborovo only | Template |

### Section 2 — CAPEX

Every C.01–C.18 sub-line amount appears as a row.
- Base Case column shows current values
- Scenario columns show overrides (empty = inherit base)
- **All CAPEX sub-line amounts are overridable per scenario**

### Section 3 — OPEX

Every B.01–B.13 sub-line amount appears as a row.
- Same override pattern as CAPEX
- **All OPEX Y1 budgets are overridable per scenario**

### Section 4 — REVENUES SCHEME

| Parameter | Editable in scenarios? |
|-----------|------------------------|
| PPA term (years) | **Yes** |
| PPA inflation | **Yes** |
| PPA Base Tariff (€/MWh) | **Yes** |
| cPPA % of P50 | **Yes** |
| Cumulated inflation | Derived |

### Section 5 — TAX (where applicable)

| Parameter | Editable in scenarios? |
|-----------|------------------------|
| Property Tax | **Yes** |
| Land Tax | **Yes** |
| Concession Fee | **Yes** |

### Section 6 — FINANCING

| Parameter | Editable in scenarios? |
|-----------|------------------------|
| Debt Maturity (years) | **Yes** |
| Credit Margin (bps) | **Yes** |
| Swap rate | **Yes** |
| Equity/Sizing case | **Yes** (dropdown) |
| Hedge coverage | **Yes** |
| Gearing | **Yes** |
| Target DSCR (PPA phase) | **Yes** |
| Target DSCR (merchant phase) | **Yes** |
| SHL rate | **Yes** |

### Section 7 — OUTPUTS (read-only comparison)

| Output | Notes |
|--------|-------|
| Project Hurdle Rate | Input (benchmark) |
| Project IRR | Computed output |
| Discount Rate | Input |
| NPV | Computed output |
| Equity Hurdle Rate | Input (benchmark) |
| Equity IRR | Computed output |

---

## Key Insight: Excel Scenarios ≠ Simple Overrides

In Excel, a scenario is a **full parallel model run** with its own column of every CAPEX, OPEX, revenue and financing assumption. The output section then compares IRRs and NPVs.

The app currently supports:
- ✅ Named scenarios with a subset of overridable fields
- ✅ Base Case + N additional scenarios
- ❌ Full CAPEX/OPEX line-item overrides per scenario (only summary totals)
- ❌ Side-by-side output comparison (IRR, NPV) after multiple runs

---

## App vs. Excel Gap Analysis

| Feature | Excel | App current | Gap |
|---------|-------|-------------|-----|
| Multiple named scenarios | ✅ | ✅ | OK |
| Technical overrides per scenario | ✅ | ✅ (capacity, P50 hours) | OK |
| Revenue overrides | ✅ | ✅ (tariff, PPA term) | Partial |
| Full CAPEX line-item overrides | ✅ | ❌ only total CAPEX | Gap |
| Full OPEX line-item overrides | ✅ | ❌ only Y1 total | Gap |
| Financing overrides | ✅ | ✅ (gearing, DSCR, tenor, rate) | OK |
| Tax overrides | ✅ | ❌ | Gap |
| Output comparison (IRR/NPV) | ✅ same sheet | Compare tab | Different UX, acceptable |
| Preset scenario names | ✅ | ❌ (was Sprint 14C, now reverted) | Easy fix |
| "Accountable" column | ✅ Oborovo | ❌ | Out of scope v1 |

---

## Recommended App Scenario Structure

For app v1 (what backend currently supports):

**Columns:** Base Case + user-named scenarios (Downside / Upside / Bank Case / Custom)

**Rows grouped by:**
1. Technical (Capacity, P50 Hours, P90 Hours)
2. Revenue (PPA Tariff, PPA Term, PPA Index, CO2)
3. CAPEX (Total CAPEX override — links to CAPEX detail)
4. OPEX (Y1 OPEX override — links to OPEX detail)
5. Debt (Gearing, Target DSCR, Tenor, Base Rate, Margin)
6. Tax (CIT Rate — read-only, country default)

**Unsupported (mark as "not yet available — set in Base via CAPEX/OPEX tabs"):**
- Per-scenario CAPEX line-item overrides
- Per-scenario OPEX line-item overrides

**Output comparison:** Remains in Compare tab (separate from input matrix).
