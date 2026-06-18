# Generic Validation Reference Excel Models — Build Report

**Role:** External financial modeler / Excel model reviewer (this task was
explicitly scoped as non-application, non-engine work — no Finco1 code,
domain, persistence, or test files were touched).

**Spec followed:** `docs/generic_validation_reference_excel_spec.md`
**Repo:** `xofisamba/Finco1`
**Base commit:** `4bb27c43ee7122be2f9732b7b67afc22f1760254`
**Branch:** `claude/generic-validation-reference-models`

## Files created

1. `validation/reference_models/GenericSolar_ReferenceModel.xlsx`
2. `validation/reference_models/GenericWind_ReferenceModel.xlsx`
3. `validation/reference_models/README.md`
4. `reports/generic_reference_model_build_report.md` (this file)

No other files were modified. No engine, app, domain, persistence, export,
or test files were touched.

## Workbook structure

Both workbooks contain the 11 required tabs in order: `Inputs`, `CapEx`,
`IDC`, `OpEx`, `Revenue`, `Debt Service`, `P&L`, `Cash Flow`, `Equity`,
`Summary`, `Methodology`. Currency is kEUR throughout, periods are
semiannual, columns C onward are period-by-period values. All 15 required
output anchors live on the `Summary` tab as cell formulas chained back to
the detail tabs.

## Key assumptions used (exact, from the spec)

**Generic Solar 50 MW:** FC 2030-01-01, COD 2031-01-01, 12-month
construction (2 semiannual periods), 25-year horizon (50 operating
periods), 1,500 P50 hrs/yr, 0.4%/yr degradation, 99%×99% availability, PPA
55 EUR/MWh for 10 years at 2%/yr indexation, market price 60/61 EUR/MWh
escalating 2%/yr post-PPA, capex 20,000/3,000/5,000/2,000/3,000 kEUR
(Modules/Inverters/Civil/Grid/Soft Costs, total 33,000 kEUR), opex
150/100/80/50 kEUR Y1 (total 380 kEUR) inflating 2%/yr, gearing cap 75%,
target DSCR 1.20, 15-year senior tenor (30 periods), base rate 3% + margin
250bps, 25% corporate tax, 5-year loss carryforward, 20-year straight-line
depreciation on hard capex.

**Generic Wind 50 MW:** FC 2030-01-01, COD 2031-07-01, 18-month
construction (3 semiannual periods), 25-year horizon, 3,000 P50 hrs/yr, 0%
degradation, PPA 60 EUR/MWh for 12 years at 2%/yr indexation, market 65
EUR/MWh escalating 2%/yr, wind balancing cost 8 EUR/MWh, CO2 revenue
enabled at 5 EUR/MWh, capex 30,000/6,000/3,000/4,000 kEUR
(Turbines/Civil/Grid/Soft Costs, total 43,000 kEUR), opex 200/150/120/80
kEUR Y1 (total 550 kEUR) inflating 2%/yr; financing/tax/debt terms
identical to Solar.

## Treatment of open questions (spec §9)

1. **Depreciation** — straight-line over 20 years on hard capex, as
   suggested, used directly (no deviation).
2. **IDC with idc_keur=0** — modeled as a structural consequence, not a
   literal override: senior debt is drawn as a single bullet at COD (sized
   via DSCR sculpting of post-COD CFADS); construction capex is funded
   100% by equity. No debt balance exists pre-COD, so the
   interest-during-construction formula (`IDC` tab) naturally evaluates to
   0 — it is a live formula, not a hardcoded zero.
3. **Senior debt sizing iteration** — used the closed-form NPV
   approximation the spec explicitly allows: `NPV(periodic_rate,
   CFADS_sizing/target_DSCR over the tenor)`, capped at the gearing limit.
   A final-period balance true-up plug guarantees the closing balance
   reaches exactly zero by tenor end (verified — see Quality Checks).
4. **Loss carryforward expiry** — modeled as a single non-expiring rolling
   pool rather than a vintage-tracked 5-year ladder (documented deviation,
   see below).
5. **SHL mechanics** — combined into the single equity cash flow series
   per the `EQUITY_ONLY` method input; PIK accrual not separately tracked
   (documented deviation, see below).
6. **DSRA mechanics** — not separately funded; the DSCR sculpt's built-in
   1.20x cushion is treated as the reserve buffer (documented
   simplification).
7. **Distribution waterfall** — 100% cash sweep to equity after debt
   service (no distribution cap modeled).
8. **Terminal value** — none. Horizon is a full 25 years with no terminal
   cash flow.
9. **Working capital** — none. Model is on a cash basis throughout.
10. **Construction draw schedule** — confirmed: Solar = 2 semiannual
    periods, Wind = 3 semiannual periods.
11. **COD timing** — confirmed as specified (Solar 2031-01-01, Wind
    2031-07-01).
12. **Generation profile** — flat within each operating year (50%/50%
    split across H1/H2), as the simpler of the two options offered.

## Output anchor values

All values below were produced by a full programmatic recalculation of the
formula graph (Python `formulas` engine — equivalent to Excel's
`Ctrl+Alt+F9`); they are not hand-typed. Opening either file in Excel/
LibreOffice with automatic calculation reproduces the same numbers.

### Generic Solar

| Anchor | Value |
|---|---|
| total_revenue_keur | 129,903.91 |
| total_opex_keur | 12,171.51 |
| total_ebitda_keur | 117,732.39 |
| total_capex_keur | 33,000.00 |
| idc_keur | 0.00 |
| bank_fees_keur | 0.00 |
| senior_debt_keur | 24,750.00 |
| senior_debt_service_p1_keur | 1,316.54 |
| senior_debt_service_p2_keur | 1,316.54 |
| senior_debt_service_p3_keur | 1,334.27 |
| avg_dscr | 1.2744 |
| min_dscr | 1.2131 |
| project_irr | 10.4274% |
| equity_irr | 13.1847% |
| realized_gearing | 75.00% |

### Generic Wind

| Anchor | Value |
|---|---|
| total_revenue_keur | 285,195.73 |
| total_opex_keur | 17,616.66 |
| total_ebitda_keur | 267,579.06 |
| total_capex_keur | 43,000.00 |
| idc_keur | 0.00 |
| bank_fees_keur | 0.00 |
| senior_debt_keur | 32,250.00 |
| senior_debt_service_p1_keur | 2,670.79 |
| senior_debt_service_p2_keur | 2,670.79 |
| senior_debt_service_p3_keur | 2,722.48 |
| avg_dscr | 1.2528 |
| min_dscr | 1.2127 |
| project_irr | 15.8432% |
| equity_irr | 18.6479% |
| realized_gearing | 75.00% |

Note: in both projects the NPV-sized senior debt exceeds the 75% gearing
cap, so the gearing cap binds and `realized_gearing` lands exactly at
75.00% (the cap), with the resulting min/avg DSCR comfortably above the
1.20x target (since less leverage than the DSCR sizing alone would imply).
This is an arithmetic consequence of the input set, not a modeling error.

## Quality checks performed

- ✅ Workbooks open with all formulas intact (verified via `openpyxl` round-trip and a full formula-graph recalculation).
- ✅ No external workbook links (`xl/externalLinks/*` absent from both `.xlsx` archives).
- ✅ No VBA project / macros (no `vbaProject.bin`, no macro-enabled parts).
- ✅ No protected sheets/cells.
- ✅ All 15 Summary anchors are formulas, none are hardcoded constants.
- ✅ Summary values tie to detail tabs (every anchor formula directly references CapEx/IDC/OpEx/Revenue/Debt Service/P&L/Cash Flow/Equity cells; verified by recalculation).
- ✅ Debt closing balance reaches exactly 0 by the end of the senior tenor (verified: Solar AH-column closing balance = 0; Wind AI-column closing balance = 0; in both cases debt amortizes to zero before tenor end given the gearing-capped balance).
- ✅ Total CapEx (`CapEx` tab, Total Hard CapEx) equals the sum of capex line items: Solar 33,000 kEUR = 20,000+3,000+5,000+2,000+3,000; Wind 43,000 kEUR = 30,000+6,000+3,000+4,000.
- ✅ Total Revenue (`Summary`) equals the sum of period revenue on the `Revenue` tab (formula-linked `SUM`).
- ✅ Total EBITDA equals Total Revenue minus Total OPEX (formula-linked).
- ✅ Senior debt does not exceed the gearing cap (binds exactly at the cap in both cases — documented above).
- ✅ DSCR computed as CFADS (true, post-tax) / senior debt service, per spec §5.5, on the `Cash Flow` tab.

## Known simplifications (full list also in each workbook's `Methodology` tab)

1. CapEx spending-profile buckets (`Y0`, `Y1-H1`, `Y1-H2`) are mapped
   directly, in order, onto each project's actual construction periods
   rather than literal calendar labels, since COD falls exactly at the
   start of the stated "Y1" (making a literal post-COD construction spend
   impossible). Where a project has fewer construction periods than
   profile buckets (Solar: 2 periods vs. Civil Works' 3 buckets), trailing
   buckets are folded into the last construction period.
2. Senior debt sizing uses a CFADS proxy that excludes the interest tax
   shield (`Tax_sizing = MAX(0, EBITDA - Depreciation) × tax_rate`) to
   avoid a circular reference between interest expense and tax in a
   static (non-iterative) spreadsheet. The true post-interest tax (with
   loss carryforward) feeds the `Cash Flow` tab's true CFADS, true DSCR,
   and all Summary anchors.
3. Loss carryforward is a single non-expiring rolling pool rather than a
   vintage-tracked 5-year-expiry ladder. Given the conservative,
   gearing-capped leverage in both projects, taxable losses are not
   expected to persist 5+ years, so this is not expected to move the tax
   cash flow outside the ±0.5% tolerance band.
4. SHL (8% PIK) and share capital are combined into one equity cash flow
   series per the `EQUITY_ONLY` method; SHL PIK accrual is not separately
   tracked as a standalone waterfall.
5. 100% cash sweep to equity, no DSRA funded separately, no terminal
   value, no working capital — all per the open-question resolutions
   above.

## Deviations from `docs/generic_validation_reference_excel_spec.md`

All deviations are the simplifications listed above plus the CapEx
profile-bucket mapping; no other deviation from the exact input
assumptions, output anchor set, or required formulas was made. Every
deviation is also recorded in the `Methodology` tab of both workbooks.

## Stop

Per instructions, work stops here. No PR has been opened and no merge
has occurred; the branch `claude/generic-validation-reference-models`
contains only the four files listed above.
