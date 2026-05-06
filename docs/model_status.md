# Model Status

## Current Version
FincoGPT — v1.2-custom-input-foundation

## Architecture
Three interfaces (Streamlit, CLI, FastAPI) over shared `run_demo_project()` core.

---

## Supported Features

### Project Types
- **Solar** — fully validated
- **Wind** — fully validated

### Interfaces
- Streamlit UI
- CLI (`fincogpt run ...`)
- FastAPI (`POST /api/v1/run`)

### Financial Model
- Revenue, OPEX, CAPEX, Tax, DSCR, IRR — full waterfall for Solar/Wind
- Scenario v2 (Base/Downside/Upside) — Solar and Wind only
  - Revenue: tariff multipliers (×0.95 / ×1.03)
  - CAPEX: +5% / −3%
  - OPEX: +10% / −5%
  - P50 hours (curtailment proxy): ×0.90 / ×1.05
  - Degradation: ×1.15 / ×0.90 (scenario multiplier on base degradation)
- Excel export (values-only)

---

## Partial Features

| Feature | Status | Notes |
|---|---|---|
| BESS | Revenue-only | No dispatch optimization, no waterfall integration |
| Hybrid (Solar+BESS, Wind+BESS) | Revenue stack only | No joint CapEx/opex waterfall |
| Portfolio | Experimental | Pooled CFADS IRR; sponsor IRR placeholder (0.0) |

---

## Not Implemented

- Sponsor IRR — placeholder 0.0; requires equity-level CF aggregation
- Portfolio scenarios — uses Base case only; non-Base scenarios blocked with warning
- Financed LCOE — only Economic LCOE (excludes debt service)
- Monte Carlo / probabilistic sizing
- Tax optimization — standard corporate tax only
- Degradation — not modeled beyond scenario v2 multipliers (no asset-life degradation curves)
- Curtailment — simplified via P50 hours scaling; no explicit curtailment curve

---

## Known Limitations

### Financial Model
- **No authentication / multi-tenancy** — single-tenant only
- **No persistence** — no saved projects, no database
- **Debt sculpting uses CFADS proxy** — EBITDA × (1 − tax_rate), not full iterative after-tax sizing
- **CAPEX depreciation uses legacy path** — per-asset-class from `CapexItem` objects; not yet wired to `CapexLineItem` matrix
- **Inverter depreciation** — simplified as 25y linear (same as generation equipment)
- **Contingency depreciation** — 5y linear (conservative; actual contract-driven)
- **No mid-year convention** — all depreciation starts at period 0
- **No separate tax vs financial depreciation** — single straight-line schedule for both

### Validation
- Pydantic handles **structural validation only**
- Business-rule validation via `/validate` endpoint — NO waterfall execution
- `/validate` does **NOT** guarantee financially feasible project
- Cross-tab arithmetic consistency not enforced
- Debt schedule mathematical correctness not independently verified

### Export
- Values only — no Excel formulas
- No named ranges, no macros
- No workbook import (anti-pattern)

---

> ⚠️ **WARNING: This model is not a bankable investment model without further validation.**
> ⚠️ **Portfolio IRR = experimental pooled unlevered CFADS IRR, NOT sponsor/equity IRR.**
> ⚠️ **BESS/hybrid results are partial — revenue-only, no full waterfall integration.**

## B2B Pilot Readiness
These items must be addressed before any paid B2B pilot:
1. Authentication / multi-tenancy
2. Persistence / saved projects
3. Full BESS waterfall integration
4. Per-asset-class CAPEX depreciation
5. Independent financial model audit

## Next Major Roadmap Items
1. CAPEX depreciation integration — wire CapexLineItem → DepreciationSchedule → waterfall tax
2. HTMX frontend — thin web client replacing Streamlit
3. Scenario comparison / batch runner — multi-scenario Excel export
4. Persistence — saved projects, user accounts