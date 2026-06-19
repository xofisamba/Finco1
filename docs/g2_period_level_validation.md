# G2 — Period-Level Validation for Generic Solar/Wind

G1D validated Generic Solar and Generic Wind against the bootstrap
reference workbooks at the total/KPI anchor level only (CAPEX, Revenue,
OPEX, EBITDA, IDC, Bank fees, Senior debt amount, Realized gearing, Equity
funding stack). This note extends that to the period (semi-annual) level.

This is validation/tests/reporting only — no model formula, factory
default, or engine file changed. See `tests/test_g2_period_level_validation.py`.

## New fixtures

`scripts/extract_generic_golden_periods.py` extracts per-period series from
the reference workbooks (cached formula values only, via openpyxl; no
formula evaluation engine or Finco1 runtime code is run) into:

- `tests/fixtures/excel_golden_generic_solar_periods.json`
- `tests/fixtures/excel_golden_generic_wind_periods.json`

This is additive to the existing `excel_golden_generic_{solar,wind}.json`
Tier-1 anchor fixtures (G1A) — neither of those files, nor
`scripts/extract_generic_golden.py`, was modified.

## Period-level metric coverage table

| Area | Series | Status |
|---|---|---|
| Revenue | Generation (MWh) | Tight-validated |
| Revenue | PPA tariff (EUR/MWh) | Not yet available from runtime |
| Revenue | Market price (EUR/MWh) | Not yet available from runtime |
| Revenue | Revenue by period (kEUR) | Tight-validated (one named exception, see below) |
| OPEX | Total OpEx by period (kEUR) | Tight-validated |
| EBITDA | EBITDA by period (kEUR) | Tight-validated (one named exception, see below) |
| Senior debt | Opening balance by period | Methodology-caveated |
| Senior debt | Interest by period | Methodology-caveated |
| Senior debt | Principal by period | Methodology-caveated |
| Senior debt | Debt service by period | Methodology-caveated |
| DSCR | DSCR by period | Methodology-caveated |
| Equity/cashflow | Distributions by period | Methodology-caveated |
| Equity/cashflow | Equity cash flow by period (IRR series) | Methodology-caveated |

"Methodology-caveated" here is the same classification G1D already applies
at the total level to `senior_debt_service_keur`, `avg_dscr`, `min_dscr`,
`project_irr`, and `equity_irr` (see `app/validation_status.py`): the
reference workbook sizes senior debt off a CFADS proxy that excludes the
interest tax shield (`docs/generic_validation_reference_excel_spec.md`
§6.2; `reports/g1f_debt_sizing_proxy_gap_analysis.md`), which the runtime
does not reproduce period-by-period. These period-level tests therefore
only assert the series exist, are finite, and are length-aligned with the
reference fixture — they do not assert close numerical agreement.

"Not yet available" means the reference workbook has the row, but
`domain.waterfall.waterfall_engine.WaterfallPeriod` has no equivalent
per-period field today, so there is nothing on the runtime side to compare
it against. `test_ppa_tariff_and_market_price_periods_not_yet_available_from_runtime`
documents this explicitly rather than silently skipping it.

## Tolerance table

| Series | Tolerance | Basis |
|---|---|---|
| Generation (MWh), OpEx (kEUR) | 2% relative per period (min abs 1 kEUR/MWh) | Observed max deviation ~0.82% (day-count/degradation-curve discretization); set with headroom over the observed max, not loosened after a failure. |
| Revenue (kEUR), EBITDA (kEUR) | 2% relative per period, **excluding** the single PPA-to-merchant transition period | Same basis as above for all periods except the transition boundary. |
| PPA-to-merchant transition period (revenue/EBITDA only) | 10% relative, named and isolated to exactly one period per project | The runtime's period-indexing places the PPA-expiry tariff step on a different period boundary than the reference workbook's; this produces one outlier period (~7–9% observed) that is identified by code (largest period-over-period revenue drop in the back half of the schedule) and bounded explicitly — it is not used to widen the tight tolerance above. |
| Senior debt service / balances / DSCR / distributions / equity cash flow, by period | None (existence/finiteness only) | Methodology-caveated, per above; period-level shape comparison is left for a future, tighter-tolerance review (same follow-up already flagged for the total-level caveat in G1D). |

The 2% per-period tolerance is deliberately wider than the 0.5% total-level
tolerance in `docs/generic_validation_reference_excel_spec.md` §8: the
total is a sum across all periods, so per-period noise that does not net
to zero in either direction still averages out, while a single period does
not get that benefit.

## Alignment note

The reference workbook and the runtime can split the same construction
duration into a different number of leading semi-annual columns before
operations start (observed: 0 periods of offset for Generic Solar, 1 period
of offset for Generic Wind, both using `construction_months` from the
factory defaults). The tests align by the first period with non-zero
generation in each series rather than assuming a fixed offset, and assert
the resulting series exist and have matching lengths — this is a
period-indexing alignment, not a numerical discrepancy.

## Test results (summary)

`tests/test_g2_period_level_validation.py`: all tests pass for both
Generic Solar and Generic Wind. See PR description / delivery report for
the full regression run.
