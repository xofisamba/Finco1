# Scenario v2 Scope — Solar/Wind Only

> **Do NOT implement Scenario v2 in this sprint. This document defines scope and guardrails.**

## Current State (Scenario v1)

- **Scenarios:** Base / Downside / Upside
- **Supported project types:** Solar, Wind
- **Portfolio:** NOT supported — shows warning, forces Base
- **BESS/hybrid:** Partial — guardrails in place, no full dispatch model

## Proposed Scenario v2 Parameters (Solar/Wind Only)

| Parameter | Type | Description |
|---|---|---|
| `opex_multiplier` | float | Scales all OPEX items uniformly |
| `degradation_multiplier` | float | Scales `pv_degradation` rate |
| `curtailment_multiplier` | float | Scales generation (0=no curtailment, 1=full) |
| `merchant_price_multiplier` | float | Scales market price curve |
| `ppa_tariff_multiplier` | float | Scales PPA base tariff |
| `capex_multiplier` | float | Scales all CapEx items uniformly |

### Directional Tests Required

For each parameter, two tests minimum:
1. **Directional IRR test:** Parameter increase → IRR moves in expected direction
2. **LCOE direction test:** Parameter increase → LCOE moves in expected direction

| Parameter | IRR Effect | LCOE Effect |
|---|---|---|
| `opex_multiplier` ↑ | IRR ↓ | LCOE ↑ |
| `degradation_multiplier` ↑ | IRR ↓ | LCOE ↑ |
| `curtailment_multiplier` ↑ | IRR ↓ | LCOE ↑ |
| `merchant_price_multiplier` ↑ | IRR ↑ | LCOE ↓ (revenue up) |
| `ppa_tariff_multiplier` ↑ | IRR ↑ | LCOE ↓ (revenue up) |
| `capex_multiplier` ↑ | IRR ↓ | LCOE ↑ |

## Explicitly Out of Scope

### Portfolio Scenario Aggregation
Scenario v2 must NOT support Portfolio aggregation. Portfolio results are always Base case.
Do NOT implement scenario-parameter scaling across multiple projects.

### BESS Dispatch Scenario
BESS dispatch optimization is not part of Scenario v2.
Do NOT add BESS-specific scenario parameters.

### Hybrid Revenue Stack
Hybrid projects (Solar+BESS, Wind+BESS) revenue stacking is not part of Scenario v2.
Do NOT add hybrid scenario parameters.

### Monte Carlo / P90 Sizing
Stochastic scenarios, Monte Carlo simulation, P90 sizing — out of scope.
Do NOT add probabilistic scenario types.

## Guardrail Statement

> **Scenario v2 must NOT be implemented for Portfolio or BESS/hybrid without full model support.**
> Any PR adding scenario parameters must include:
> - Explicit guardrail test: `test_portfolio_scenario_still_not_supported`
> - Explicit guardrail test: `test_bess_hybrid_scenario_status_partial`
> - Scope doc updated to reflect implementation status

## Implementation Prerequisites

Before implementing Scenario v2, the following must be true:
1. Portfolio scenario blocking is enforced at UI and export levels
2. BESS/hybrid guardrails are documented and tested
3. Scenario v1 directional tests are passing for all 6 parameters
4. This scope document is updated to mark v2 as "in progress"