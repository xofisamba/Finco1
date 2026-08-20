# Pre-freeze PR-5: Canonical EBITDA Authority

## Decision

**Classification: `SOURCE_SIGNED_EBITDA`.** TUHO, Oborovo, and KUPI all keep
EBITDA signed. None of the three source formulas contains `MAX(..., 0)`, an
equivalent `IF` floor, or a project-specific EBITDA policy. PR-5 resolves the
signed-vs-floored authority for the currently modeled Finco Revenue/OPEX
components. The canonical Finco authority for those promoted components is:

```text
calculate_ebitda_keur(revenue_keur, opex_keur) = revenue_keur - opex_keur
```

Finco's `opex_keur` convention is a positive expense. The source workbooks use
negative OPEX rows and add them to revenue. Their literal EBITDA formulas also
include a separate Local (various) Taxes row: `CF!G63 = Macro!G46` for TUHO and
KUPI, and `CF!G73 = Macro!G46` for Oborovo. Active Base and Bank Case values are
zero throughout each current modeled horizon, so current calibration
numerically satisfies Revenue minus modeled OPEX. Runtime promotion of that
separate component is deferred as
`EBITDA_LOCAL_TAX_COMPONENT_MAPPING_NOT_YET_PROMOTED`; this PR adds no
adjustment parameter or balancing seam.

No typed EBITDA policy was introduced because the sources do not prove policy
variability. Construction-period zero values come from phase/activity inputs
being zero, not from a mathematical EBITDA floor.

## Source lock

| Model | SHA-256 | Revenue | Signed OPEX | Local tax | EBITDA | Bank CFADS |
|---|---|---|---|---|---|---|
| TUHO | `780779eba4278ccc2b8546a9411ccee24917d388f411ba60c88aa342cb5c727a` | `CF!G20 = G21+G31+G33+G35+G25` | `CF!G38 = SUM(G45:G61)` | `CF!G63 = Macro!G46` | `CF!G40 = G20+G38+G63` | `CF!G69 = SUM(G20,G38,G63,G66,G67)+$B$70*(G$3=0)` |
| Oborovo | `15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920` | `CF!G23 = G24+G42+G44+G46+G28+G40+G36+G32+G41` | `CF!G49 = SUM(G56:G71)` | `CF!G73 = Macro!G46` | `CF!G51 = G23+G49+G73` | `CF!G79 = SUM(G23,G49,G73,G76,G77)+$B$80*(G$4=0)` |
| KUPI | `111178fb21109f55df45c0cc1ea108104ac8b6ed60f010ba75b6c498795f5954` | `CF!G20 = G21+G31+G33+G35+G25` | `CF!G38 = SUM(G45:G61)` | `CF!G63 = Macro!G46` | `CF!G40 = G20+G38+G63` | `CF!G69 = SUM(G20,G38,G63,G66,G67)+$B$70*(G$3=0)` |

The active Local Tax value set is `{0.0}` kEUR for TUHO, Oborovo, and KUPI in
both Base and Bank Case across the current modeled horizons.

For all three workbooks, `P&L!G16 = G8-G14` derives EBIT after the P&L's
positive-display expense rows. Thin-cap `MAX` expressions in P&L rows 57/58
are downstream interest-deductibility/tax constraints, not EBITDA floors. Bank
CFADS reuses the same signed revenue/OPEX/local-tax treatment; it does not
define a second EBITDA policy.

## Authority inventory

| Location | Prior formula/status | Runtime role | Disposition |
|---|---|---|---|
| `finco_core/ebitda.py` | absent | shared authority | added pure signed helper |
| `financial_engine.orchestrator.run_operating_model` | inline `revenue - opex` | clean Base and Bank operating cases | delegates to shared helper |
| `app.waterfall_core.run_waterfall_v3_core` | `max(0, revenue - opex)` | legacy/UI production Run | floor retired; delegates to helper |
| `finco_core.waterfall.waterfall_engine.compute_ebitda_schedule` | `max(0, revenue - opex)` | reusable legacy schedule helper | floor retired; delegates to helper |
| `finco_core.waterfall.waterfall_engine.cached_run_waterfall` | `max(0, revenue - opex)` | cached/compatibility runtime | floor retired; delegates to helper |
| `finco_core.waterfall.cash_flow.calculate_period_waterfall` | signed inline formula | isolated period helper | delegates to shared helper; behavior unchanged |
| `finco_core.waterfall.waterfall_engine.run_waterfall` | `max(0, EBITDA * (1-tax))` | legacy sizing and DSCR | `SIGNED_CFADS_AUTHORITY`: signed proxy retained for DSCR; zero bound moved to capacity |
| `finco_core.debt.sculpting_iterative.closed_form_sculpt` | caller supplied floored CFADS | legacy sculpting kernel | `NON_NEGATIVE_DEBT_CAPACITY_BOUNDARY`: `max(0, signed CFADS / target DSCR)` |
| `domain.senior_debt_sizing.canonical_wiring.derive_sizing_cfads_from_ebitda` | `max(0, EBITDA) * (1-tax)` | runtime-capable sizing fallback | `SIGNED_CFADS_AUTHORITY`: proxy remains signed |
| `domain.senior_debt_sizing.engine.SeniorDebtSizingEngine` | capacity could inherit negative CFADS | canonical sizing capacity | `NON_NEGATIVE_DEBT_CAPACITY_BOUNDARY`: capacity is floored, CFADS is not |
| `financial_engine.cfads.calculate_canonical_cfads` | `EBITDA - cash tax` | canonical Base/Bank CFADS | downstream consumer; no change |
| `financial_engine.tax.engine.calculate_tax` | signed EBITDA into taxable income; CIT floors positive taxable profit | canonical tax | `TAX_BOUNDARY`; legitimate tax floors preserved |
| `financial_engine.senior_debt.solver` | non-negative debt-service/debt capacity | Senior sizing | `NON_NEGATIVE_DEBT_CAPACITY_BOUNDARY`; unchanged |
| `financial_engine.tax.atad` and `finco_core.tax.holdco_calculations` | EBITDA-based interest limitation | tax deductibility | `TAX_BOUNDARY`; unchanged |
| `finco_core.waterfall.waterfall_engine` unlevered-tax proxy | positive taxable-profit proxy | legacy tax diagnostic | `TAX_BOUNDARY`; unchanged |
| `domain.reporting.financial_statements` taxable-income gate | positive taxable EBT | reporting tax assembly | `TAX_BOUNDARY`; unchanged |
| `app.output_tables._cfads_value` | display fallback floors absent explicit CFADS | presentation fallback | `DIAGNOSTIC_ONLY`; not an authoritative CFADS or DSCR input |
| `app.reconciliation.project_cashflow` | simplified unlevered-tax proxy | reconciliation utility | `DIAGNOSTIC_ONLY`; unchanged |
| Monte Carlo utilities | simplified tax/distribution floors | analytics | `DIAGNOSTIC_ONLY`; unchanged |

## Negative discrimination

The clean production-function test supplies Revenue `100` and positive OPEX
`150`. Results are:

| Output | Result | Causal source |
|---|---:|---|
| EBITDA | `-50` | canonical signed helper |
| EBIT | `-50` | zero book depreciation control |
| taxable income before losses | `-50` | existing tax engine |
| cash tax | `0` | existing positive-taxable-profit CIT gate |
| Base CFADS | `-50` | canonical CFADS = EBITDA - cash tax |
| Bank CFADS control | `-50` | same source-supported EBITDA/tax chain |
| Senior capacity | `0` | existing non-negative debt-capacity constraint |

The zero boundary returns exactly `0`; the positive control returns exactly
`50`; and a construction-neutral Revenue/OPEX pair returns exactly `0`.

The real legacy `run_waterfall()` discrimination uses three operating periods.
Its first period has Revenue `100`, OPEX `150`, EBITDA `-50`, a signed sizing
CFADS proxy of `-45`, and positive Senior service of
`3.3203757693553615` kEUR. Actual period DSCR is `-15.058536585365852`;
proxy/sculpt DSCR is `-13.552682926829267`. Principal capacity in that period
is exactly zero while opening debt remains non-negative. The positive control
produces EBITDA `50`, debt `102.12180110139293` kEUR and proxy DSCR `1.20`.
The zero control produces EBITDA `0`, debt `0`, and principal `0` throughout.

## Cross-arc guardrails

Phase57A8 and Phase57A9D remain fail-closed. Their checks accept either no
`app/waterfall_core.py` diff or exactly the approved import plus replacement of
`max(0, rev - opex)` with the shared helper. The domain exception likewise
accepts only the signed fallback and non-negative capacity hunks. A synthetic
extra `tax_rate = 0.0` waterfall hunk is rejected. No protected path is broadly
exempted.

## Calibration and governance

TUHO, Oborovo, and KUPI currently have no operating period in which OPEX exceeds
Revenue, so retiring the floor is expected to produce zero delta across their
existing schedules. Before/after fingerprints cover Revenue, OPEX, EBITDA,
EBIT, cash tax, Base CFADS, Bank CFADS where enabled, Senior, DSCR, SHL, and
sponsor distributions where the current path exposes them.

| Path | Revenue | OPEX | EBITDA | EBIT | Cash tax | Base CFADS | Bank CFADS | Senior | DSCR | SHL | Sponsor distributions | Before/after delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| TUHO legacy | 423843.61137671326 | 85408.27413448403 | 338435.33724222926 | 265441.62724222924 | 37004.37271846072 | 305476.7854442677 | n/a | 43359.0 | 1.3785647255425093 | 37326.33183100554 | 165479.31957618406 | `0` |
| TUHO clean operating | 423843.61137671326 | 85408.27413448403 | 338435.33724222926 | 265441.62724222924 | blocked by pre-existing tax-input authority | n/a | n/a | n/a | n/a | n/a | n/a | `0` |
| Oborovo legacy | 238424.08727754717 | 55778.97100392451 | 182645.11627362267 | 124672.06277362265 | 8489.215657119626 | 174155.90061650303 | n/a | 42852.26672602787 | 1.1785714285714286 | 14716.2 | 63997.38013609859 | `0` |
| Oborovo clean | 237686.92241665165 | 55782.95083863444 | 181903.97157801723 | 123930.9180780172 | 10437.903855993205 | 171466.06772202402 | 141761.64252202827 | 42852.30326225287 | 1.068191847453114 | 0.0 | unavailable | `0` |
| KUPI clean P0 | 1451797.2161462924 | 224760.28891183925 | 1227036.9272344531 | 1011233.4350818624 | 94864.75043518859 | 1132172.1767992645 | 829906.9514193471 | 133956.81297351522 | 1.6717402403762338 | unavailable | unavailable | `0` |

Production code contains no TUHO/Oborovo/KUPI identity dispatch for EBITDA and
no `approved_delta`, `expected_delta`, balancing plug, target fitting, hardcoded
EBITDA vector, or source-output replay. PR-3/PR-3B/PR-4 DSRA and SHL cash
authority are unchanged. `G2C_DEDUCTIBLE_SHL_COVENANT_FEEDBACK_NOT_YET_CLOSED`
remains open. This PR does not claim single-financial-flow closure or begin PR-6.
