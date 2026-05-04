# Sample Export Instructions

How to generate investor-ready Excel exports.

## Solar Export

1. Open Finco1 Streamlit app
2. Select: Project Type = Solar, Scenario = Base
3. Click: 🚀 Run Model
4. Wait for result, then click: 📊 Download Excel Export
5. Save as: `Finco1_Solar_Base_YYYY-MM-DD.xlsx`

## Wind Export

1. Select: Project Type = Wind, Scenario = Base
2. Run and download
3. Save as: `Finco1_Wind_Base_YYYY-MM-DD.xlsx`

## What to Verify in Excel

Sheets that MUST be present:
- Dashboard
- Returns
- DSCR Summary
- Waterfall
- Revenue
- Debt
- Tax & Depreciation (Tax_Depreciation)
- Notes

Expected KPI ranges (sanity check):
| Metric | Solar | Wind |
|---|---|---|
| Project IRR | 8–15% | 7–14% |
| Equity IRR | 10–18% | 9–17% |
| Min DSCR | 1.2–1.6x | 1.2–1.5x |
| Avg DSCR | 1.3–1.7x | 1.3–1.6x |

## What NOT to Present Yet

- Portfolio tab: experimental, scenarios not supported
- BESS/Solar+BESS/Wind+BESS: partial model — revenue only, waterfall in progress
- Sponsor IRR: placeholder value, not a real sponsor-level return
- Financed LCOE: debt service excluded (economic LCOE only)

## Notes Sheet

Verify:
- Model Version is present
- Run Timestamp is present
- Scenario matches selected scenario
- Integration Status: "full" for Solar/Wind, "partial" for BESS, "experimental" for Portfolio