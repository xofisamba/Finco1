# Model Status & Limitations

> ⚠️ **This model is not a bankable investment model without further validation.**

## Supported Features

| Feature | Status | Notes |
|---|---|---|
| Solar PV | ✅ Full | CapEx, OpEx, Revenue, Tax, DSCR, IRR |
| Wind | ✅ Full | CapEx, OpEx, Revenue, Tax, DSCR, IRR |
| Scenario v1 (Base/Downside/Upside) | ✅ Full | Solar/Wind only |
| Portfolio (project IRR) | ⚠️ Experimental | Pooled CFADS, date-aligned XIRR |
| Excel export | ✅ Full | Values-only, with Notes sheet |

## Partial Features

| Feature | Status | Notes |
|---|---|---|
| BESS | ⚠️ Partial | Revenue-only shown, no dispatch optimization, no waterfall integration |
| Hybrid (Solar+BESS, Wind+BESS) | ⚠️ Partial | Revenue stack not integrated in waterfall |

## Not Implemented

| Feature | Status |
|---|---|
| Sponsor IRR | ❌ Placeholder (0.0) — requires equity-level CF aggregation |
| Portfolio scenarios | ❌ Portfolio uses Base case only; non-Base scenarios are blocked with warning |
| Financed LCOE | ❌ Only Economic LCOE implemented (excludes debt service) |
| Monte Carlo / probabilistic | ❌ Not in scope |
| Tax optimization | ❌ Standard corporate tax only |
| Cross-default enforcement | ❌ Not implemented |

## Known Limitations

1. **Portfolio IRR is experimental**: Uses CFADS proxy (not true equity cash flows), date-aligned CapEx on project financial_close dates.
2. **BESS revenue is partial**: No dispatch optimization, no state-of-charge modeling, no integrated waterfall.
3. **Hybrid results are incomplete**: No joint CapEx/opex waterfall for hybrid projects.
4. **Economic LCOE only**: Does not include debt service, financing costs, or WACC.
5. **No P90/probabilistic sizing**: Deterministic scenarios only.
6. **No tax optimization features**: Thin cap, ATAD rules present but basic.

## Explicit Warnings

> **Portfolio IRR = experimental pooled unlevered CFADS IRR, NOT sponsor/equity IRR.**
> **Sponsor IRR = 0.0 placeholder — do not use for investment decisions.**
> **BESS/hybrid results are partial — revenue-only, no full waterfall integration.**
> **This model is not a bankable investment model without further validation.**

## Last Updated

2026-05-04 — Sprint 22 (industry-engine-refactor)