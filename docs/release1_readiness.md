# Release 1 Readiness

## Scope: What Release 1 Covers

Release 1 delivers an investor-facing Solar/Wind screening model:

- **Solar PV and Wind**: Full financial model (CapEx, OpEx, Revenue, Tax, DSCR, IRR)
- **Scenario v2**: `apply_scenario()` with parameters:
  - `capex` multiplier
  - `opex` multiplier
  - `degradation` multiplier
  - `curtailment` multiplier
  - `tariff` multiplier
- **Values-only Excel export**: No formulas in exported workbook
- **DSCR Summary sheet**: Target, actual min, actual avg, deviation
- **Model Warnings**: `warn_model_unrealistic()` surfaced in UI and Excel Notes
- **Economic LCOE**: `(CapEx + OpEx) / Total Generation` — tariff/revenue excluded by definition

---

## Out of Scope (Do Not Implement in Release 1)

The following must NOT be added:

- **Sponsor IRR**: placeholder value, no sponsor-level return modeling
- **Portfolio scenarios**: blocked with explicit warning; only Base case supported
- **BESS/hybrid financial presentation**: partial/design-only; scenarios forced to Base
- **Financed LCOE**: debt service not included in LCOE
- **Monte Carlo / P90**: stochastic scenarios not supported

---

## Known Limitations

1. **Debt sculpting**: uses CFADS proxy (`ebitda * (1 - tax_rate)`), not full iterative sculpting
2. **Portfolio**: experimental status — pooled CFADS, date-aligned XIRR; no scenario support
3. **BESS/hybrid**: partial integration — revenue-only shown, waterfall in progress; scenarios blocked

---

## Claude Re-check Focus

When reviewing Release 1, verify:

1. **DSCR actual** vs Waterfall sheet: `actual_min_dscr`/`actual_avg_dscr` computed from real period DSCR values (not sculpting proxy)
2. **Warnings surfaced**: `warn_model_unrealistic()` output appears in UI messages and Excel Notes sheet
3. **BESS scenario guardrail**: BESS/Solar+BESS/Wind+BESS + non-Base scenario → forced to Base + user-facing warning
4. **Documentation consistency**: model_status.md says "Scenario v2" with parameter list; scenario_v2_scope.md has "Implemented in Phase 2" section
5. **No vacuous tests**: warning tests use monkeypatch or synthetic injection, not manual message construction