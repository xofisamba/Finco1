# Demo Smoke Test Checklist

Use this checklist before any investor demo.

## Solar — Base Case
- [ ] Run "Solar" with "Base" scenario
- [ ] Dashboard shows: Project IRR %, Equity IRR %, Min DSCR, Avg DSCR
- [ ] Project IRR between 8–15%
- [ ] Min DSCR > 1.2x
- [ ] Download Excel — DSCR Summary sheet matches Dashboard

## Solar — Downside
- [ ] Run "Solar" with "Downside"
- [ ] Project IRR lower than Base (confirm direction)
- [ ] Min DSCR lower than Base

## Solar — Upside
- [ ] Run "Solar" with "Upside"
- [ ] Project IRR higher than Base
- [ ] Min DSCR higher than Base

## Wind — Base / Downside / Upside
(same checks as Solar)

## Excel Export
- [ ] All sheets present: Dashboard, Returns, DSCR Summary, Waterfall, Revenue, Debt, Tax_Depreciation, Notes
- [ ] No raw key names (total_revenue_keur) — labels are clean
- [ ] Notes sheet shows scenario name and integration status
- [ ] DSCR Summary has: Target, Min, Avg, Deviation

## Model Warnings
- [ ] No W_DSCR_BELOW_TARGET in clean Solar/Wind Base runs
- [ ] Warnings expander exists and is labeled ⚠️ Model Warnings

## BESS / Portfolio Guardrails
- [ ] BESS + non-Base scenario → forced to Base, warning shown
- [ ] Portfolio → only Base case, warning shown
- [ ] Scenario selector note visible: "Scenarios apply to Solar/Wind only"

## KPI Sanity Ranges
- Project IRR: 5–25%
- Equity IRR: 5–30%
- Min DSCR: 1.0–2.0x
- Avg DSCR: 1.1–2.0x
- Total Revenue: positive kEUR values