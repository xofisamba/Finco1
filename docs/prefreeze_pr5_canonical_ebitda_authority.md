# Pre-freeze PR-5: Canonical EBITDA Authority

## Decision

**Classification: `SOURCE_SIGNED_EBITDA`.** TUHO, Oborovo, and KUPI all keep
EBITDA signed. None of the three source formulas contains `MAX(..., 0)`, an
equivalent `IF` floor, or a project-specific EBITDA policy. The canonical Finco
authority is therefore:

```text
calculate_ebitda_keur(revenue_keur, opex_keur) = revenue_keur - opex_keur
```

Finco's `opex_keur` convention is a positive expense. The source workbooks use
negative OPEX rows and add them to revenue. They also show local tax as a
separate signed operating row. That component-placement distinction does not
alter the signed-vs-floored decision. A complete local-tax component mapping is
not claimed by this PR and remains a separate operating-scope evidence gap.

No typed EBITDA policy was introduced because the sources do not prove policy
variability. Construction-period zero values come from phase/activity inputs
being zero, not from a mathematical EBITDA floor.

## Source lock

| Model | SHA-256 | Revenue | Signed OPEX | Local tax | EBITDA | Bank CFADS |
|---|---|---|---|---|---|---|
| TUHO | `780779eba4278ccc2b8546a9411ccee24917d388f411ba60c88aa342cb5c727a` | `CF!G20 = G21+G31+G33+G35+G25` | `CF!G38 = SUM(G45:G61)` | `CF!G63 = Macro!G46` | `CF!G40 = G20+G38+G63` | `CF!G69 = SUM(G20,G38,G63,G66,G67)+$B$70*(G$3=0)` |
| Oborovo | `15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920` | `CF!G23 = G24+G42+G44+G46+G28+G40+G36+G32+G41` | `CF!G49 = SUM(G56:G71)` | `CF!G73 = Macro!G46` | `CF!G51 = G23+G49+G73` | `CF!G79 = SUM(G23,G49,G73,G76,G77)+$B$80*(G$4=0)` |
| KUPI | `111178fb21109f55df45c0cc1ea108104ac8b6ed60f010ba75b6c498795f5954` | `CF!G20 = G21+G31+G33+G35+G25` | `CF!G38 = SUM(G45:G61)` | `CF!G63 = Macro!G46` | `CF!G40 = G20+G38+G63` | `CF!G69 = SUM(G20,G38,G63,G66,G67)+$B$70*(G$3=0)` |

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
| `financial_engine.cfads.calculate_canonical_cfads` | `EBITDA - cash tax` | canonical Base/Bank CFADS | downstream consumer; no change |
| `financial_engine.tax.engine.calculate_tax` | signed EBITDA into taxable income; CIT floors positive taxable profit | canonical tax | legitimate tax floors preserved |
| `financial_engine.senior_debt.solver` | non-negative debt-service/debt capacity | Senior sizing | legitimate capacity boundary preserved |
| `domain.senior_debt_sizing.canonical_wiring` | legacy proxy `max(0, EBITDA) * (1-tax)` | pre-promotion proxy path | not an EBITDA derivation; remains explicitly labelled proxy |
| `app.output_tables._cfads_value` | display fallback floors absent explicit CFADS | presentation fallback | not EBITDA authority; outside this formula correction |
| reconciliation/Monte Carlo utilities | simplified tax/distribution floors | diagnostic/analytics | not EBITDA authority; unchanged |

## Negative discrimination

The focused production-function test supplies Revenue `100` and positive OPEX
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
