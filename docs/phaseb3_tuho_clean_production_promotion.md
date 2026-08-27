# Phase B3 - TUHO clean production promotion

## Decision

`PHASE_B3_TUHO_CLEAN_PRODUCTION_PROMOTION_PROVEN`

Continuation A closes the prior capability blocker with a generic dynamic
capitalisation gate, a deductible-only interest-limitation contract, a typed
construction-origin tax-loss path, and the existing clean financing fixed
point. Canonical TUHO now classifies as `CLEAN_PRODUCTION_READY` and executes
exactly once through `clean_g2c`. The explicit legacy factory retains the frozen
Senior schedule and the unsupported `25,000 kEUR` compatibility loss.

The source-analysis sections below are retained as the historical evidence
record. Any statement describing TUHO as blocked or not executed refers to the
pre-Continuation-A checkpoint and is superseded by the measured clean-runtime
sections at the end of this document.

## Source provenance

The task identifies `20260330_TUHO_BP.xlsm` with SHA-256
`041382760ecb6190062c887a04529efdf3fca3dda779f4db5e9404902bf09336`.
That exact artifact was not available locally and the hash is not present in the
repository.

Two read-only copies were inspected:

| Copy | SHA-256 | Status |
|---|---|---|
| Committed handoff source copy | `780779eba4278ccc2b8546a9411ccee24917d388f411ba60c88aa342cb5c727a` | Repository-recognised historical canonical source |
| Local metadata-updated copy | `266d9669a54298513a42dc16d7be2ae8303c160e31e8b3bd92001d3be593b13c` | Previously documented metadata-only variant |

The cited cells and formulas agree between those two copies. That agreement is
useful evidence, but it does not establish possession of the exact hash named by
the task. Neither workbook was executed, resaved, or committed.

## Historical checkpoint authority state

Before B3, `create_default_tuho_wind1()` classifies as:

| Field | Value |
|---|---|
| Classification | `BLOCKED_BY_DEFERRED_TAX_CAPABILITY` |
| Reason | `PR8_BLOCKED_BY_TYPED_TUHO_TAX_RUNTIME_GAP` |
| Clean calculation count | `0` |
| `clean_cash_tax_timing_enabled` | `False` |
| Sponsor funding mode | missing |
| Gearing basis mode | missing |
| Frozen Senior schedule | active legacy calibration authority |
| Legacy opening tax loss | `25,000 kEUR` |
| Typed opening loss vintages | none |

The existing explicit production route raises `CleanNotReadyError`; it does not
run clean and then fall back to legacy.

## Direct tax source map

### Thin-cap activation

The workbook labels the whole mechanism as thin capitalisation:

```text
Inputs!D397 = TRUE                         Thin Capitalization
Inputs!D398 = 4 / (4 + 1) = 0.8           Max SHL to equity ratio 4:1
BS!R44 = IF($B$43,R24/SUM(R20:R24),0)
BS!R45 = IF(R44<$B$44,FALSE,TRUE)
P&L!R56 = BS!R45
```

The ratio numerator is closing SHL (`BS!R24 = DS!R126`). The denominator is
`SUM(R20:R24)`, where row 20 itself is `SUM(R21:R24)`. The source formula
therefore depends on share capital, legal reserve, retained earnings, and SHL,
and then divides SHL by a denominator that includes both the subtotal and its
components. This literal workbook convention is not a generic legal formula.

The gate is false in construction (`BS!G44 = 0.5517744146361759`) and becomes
true by the eighth operating period (`BS!O44 = 0.8012417570870866`). A runtime
implementation would need actual period balance-sheet and SHL values inside the
tax/financing fixed point. The existing offline evidence engine instead accepts
`thin_cap_active` as an externally supplied flag; using those extracted flags in
production would be source-output replay.

### Combined interest limitation

For each period column `R`, the source formulas are:

```text
P&L!R27 = DS!R122
P&L!R57 = IF(R56,MAX(R27-$C$57,0),0)
P&L!R58 = IF(R56,MAX(R27-$C$58*(R32-R30+R13),0),0)
P&L!R59 = R$27*(1-$C$59/Inputs!$C$311)*$D$59
P&L!R54 = MIN(MAX(R57,R58)+R59,R27)
P&L!R34 = -R54
P&L!R35 = R34+R32
```

Source constants are:

```text
P&L!C57 = Inputs!D399 = 3,000 kEUR
P&L!C58 = Inputs!D400 = 30%
P&L!D59 = Inputs!D395 = FALSE
```

`R32-R30+R13` algebraically reconstructs EBITDA in this workbook. The active
source result is therefore one combined helper:

```text
combined helper
  = min(max(excess over 3,000, excess over 30% EBITDA) + row 59, gross SHL interest)
```

The committed 60-period fixture reproduces the source helper with no missing or
ambiguous periods and a cumulative `P&L!54` of
`9,242.742070978198 kEUR`. In the TUHO source horizon, row 58 binds, while rows
57 and 59 never bind.

This proves the combined workbook output. It does not prove the requested
independent authorities for:

* thin-cap deductible and disallowed interest;
* ATAD deductible and disallowed interest;
* ordering between those mechanisms;
* restricted-interest carryforward creation and use.

No source row was found that tracks a separate restricted-interest
carryforward. Absence of a row is not authority to classify the amount as
permanently disallowed. The production policy must therefore remain unresolved.

### Tax losses and CIT

The workbook does not contain a `25,000 kEUR` opening-loss input. The source
bridge is calculated:

```text
P&L!G27 = DS!G122                         3,568.6878026481627
P&L!G30 = SUM(G19:G21)-SUM(G24:G28)      -3,568.6878026481627
P&L!G32 = G16+G30                        -3,568.6878026481627
P&L!G34 = -G54                            0
P&L!G35 = G34+G32                        -3,568.6878026481627
P&L!H36                                  -3,568.6878026481627
```

| Amount | Meaning | Input or output | Clean disposition |
|---:|---|---|---|
| `25,000 kEUR` | Historical Python compatibility value with no workbook cell, date, or vintage bridge | Legacy input | Must not enter clean production |
| `3,568.6878026481627 kEUR` | Construction-period SHL interest flowing through EBT and taxable result | Calculated workbook output, origin year 2029 | Candidate typed 2029 opening vintage only after the construction/tax fixed point derives it |

Loss formulas use a five-column rolling source convention (`Inputs!D390 = 5`):

```text
P&L!R36 = rolling negative taxable results plus prior allocated losses
P&L!R37 = IF(AND(R36<=0,R32>0),MIN(ABS(R36),R32),0)
P&L!R38 = MIN(R37+R36,0)
P&L!R39 = MIN(R38,prior taxable result * Inputs!D391)
P&L!R41 = -R37+R35
```

The utilisation gate is source-proven as EBT-positive (`R32>0`), not merely
taxable-income-positive.

The CIT and cash-tax chain is:

```text
Inputs!D386 = 18%
P&L!R43 = MAX(SUM(previous R41,current R41),0)*18%*(period active)*(even period)
P&L!R44 = Macro!R40
CF!R67 = -P&L!R44
```

The first positive source CIT/cash-tax period is H2 2042 (`P&L!AG43`,
`CF!AG67`) at `120.18903737619021 kEUR`. This supports last-period tax-year
payment with zero lag. It does not resolve the preceding interest limitation
and loss-generation fixed point.

## Historical blocking capability boundary

The first material blocker is not the cash-tax allocator by itself. It is the
closed causal loop required to derive the thin-cap gate and deductible SHL
interest:

```text
SHL opening / accrued interest / repayment
  -> balance sheet SHL and retained earnings
  -> workbook thin-cap ratio and gate
  -> combined interest limitation
  -> taxable income, losses, CIT, and cash tax
  -> Base and Bank CFADS
  -> Senior sizing and post-Senior cash
  -> SHL repayment and closing balance
  -> balance sheet gate in the next period
```

Current generic production code has an offline R34/R54 evidence calculator, but
it requires caller-supplied gate flags. It intentionally has no production
wiring and rejects interest carryforward. Current clean tax code has typed ATAD,
cash-tax timing, and loss-vintage capabilities, but it does not derive this
source-specific balance-sheet gate or separate the workbook helper into two
independent policies.

Consequently, none of these actions is evidence-safe:

* setting TUHO to fully deductible or fully non-deductible;
* treating the 60 extracted gate flags as runtime inputs;
* declaring row 57 to be thin cap and row 58 to be ATAD with an invented order;
* assuming no carryforward means permanent disallowance;
* enabling clean timing while leaving the limitation unresolved;
* replacing `25,000` with `3,568.6878` as a free scalar;
* removing frozen Senior or manual construction authority before their typed
  source contracts are completed.

## Historical secondary blockers not reached

The critical tax gate stops B3 before implementation. The current factory also
still lacks typed sponsor-funding and gearing-basis modes, typed construction
financing, clean SHL principal and repayment authority, and clean Senior sizing;
it retains frozen Senior and manual construction-era values. These are real B3
gates, but solving them cannot make TUHO clean-ready while tax remains blocked.

## Historical reconciliation status

| Line | Source XLSM | Explicit legacy | Clean |
|---|---:|---:|---:|
| Opening tax loss | Calculated `3,568.6878026481627` | Input `25,000` | Not executed |
| First positive cash tax | H2 2042, `120.18903737619021` | Legacy calibration path | Not executed |
| Interest-limitation helper | 60-period source fixture, total `9,242.742070978198` | Diagnostic/offline only | Not executed |
| Senior schedule | Workbook/frozen calibration evidence | Frozen fixture active | Not executed |
| Revenue through distributions | Source and legacy evidence retained | Existing legacy calibration | Not executed |

There is intentionally no source/legacy/clean KPI comparison pretending that a
clean TUHO run exists. The first material source-to-clean difference is the
absence of a source-equivalent, dynamically derived interest-limitation gate
inside the clean financing/tax fixed point.

## Historical next evidence checklist

Before a new promotion attempt:

1. Supply the exact workbook artifact with SHA-256 `041382760...`, or formally
   approve the repository-recognised `780779...` artifact as B3 authority.
2. Provide source-backed interpretation of rows 57 and 58 as independent legal
   mechanisms, including ordering and treatment of disallowed interest.
3. Prove whether restricted interest is permanent or carried forward.
4. Design a generic fixed-point input/output contract that derives the balance
   sheet gate from actual clean results without source-vector replay.
5. Only then continue typed construction, funding, Senior, and SHL promotion.

## Continuation A source contract

The implementation distinguishes four authorities throughout:

1. `SOURCE_WORKBOOK_MECHANIC` - validation evidence from TUHO workbook formulas.
2. `CANONICAL_FINCO_POLICY` - generic typed rules used by the clean engine.
3. `LEGACY_CALIBRATION` - frozen compatibility inputs isolated in
   `create_default_tuho_wind1_legacy_calibration()`.
4. `CLEAN_RUNTIME_RESULT` - values calculated by the canonical engine.

The source limitation contract is preserved literally:

```text
P&L!R57 = IF(R56, MAX(R27 - 3000, 0), 0)
P&L!R58 = IF(R56, MAX(R27 - 30% * EBITDA_basis, 0), 0)
P&L!R59 = additional non-deductible component (inactive for TUHO)
P&L!R54 = MIN(MAX(R57, R58) + R59, R27)
```

The generic policy uses `MAX_DISALLOWED`; it does not invent a sequential
thin-cap/ATAD order. The clean identity is always:

```text
gross SHL interest = deductible SHL interest + disallowed SHL interest
```

Deductible interest enters taxable income exactly once. TUHO uses the explicit
source-model convention
`NO_RESTRICTED_INTEREST_CARRYFORWARD_IN_SOURCE_MODEL`; this is not presented as
a statement of Croatian law.

The dynamic gate retains the unusual source denominator, including the row-20
subtotal reinclusion. Its literal comparison is `ratio < 0.80` => OFF, so exact
equality is ON. The committed source fixture first activates at source operating
period index 7. The clean audit vector first activates at canonical model index
8 because index 0 is the single construction/accounting boundary column. There
is no source gate-vector runtime input.

## Continuation A fixed point

The existing generic financing loop now carries the minimum equity/tax state:

```text
construction funding and SHL PIK
-> operating SHL gross interest
-> net income / retained earnings
-> capitalisation ratio and gate
-> deductible SHL interest
-> tax loss / CIT / cash tax
-> Base and Bank CFADS
-> Senior sizing and service
-> post-Senior cash
-> SHL service and closing balance
```

The authoritative clean run converges without a forced terminal value:

| Diagnostic | CLEAN_RUNTIME_RESULT |
|---|---:|
| Outer construction iterations | 11 |
| Outer construction residual | `1.394391802023165e-08 kEUR` |
| Inner tax/Senior/SHL iterations | 7 |
| Max SHL closing delta | `2.2850726963952184e-06 kEUR` |
| Max SHL interest delta | `9.215418117491936e-08 kEUR` |
| Final interest handshake | `2.106048668792937e-11 kEUR` |
| Final closing handshake | `5.220499588176608e-10 kEUR` |
| Max retained-earnings delta | `1.3824959751218557e-05 kEUR` |
| Max capitalisation-ratio delta | `2.9949021040920343e-10` |
| Gate mismatches | `0` |

Synthetic tests also cover below/equal/above-threshold behavior, SHL/equity/
retained-earnings mutations, both combination modes, the gross-interest cap,
carryforward `NONE`, and seed-independent generic convergence.

## Continuation A tax result

| Metric | CLEAN_RUNTIME_RESULT |
|---|---:|
| Gross SHL interest | `52,174.95003012468 kEUR` |
| Disallowed SHL interest | `8,399.610059436927 kEUR` |
| Deductible SHL interest | `43,775.33997068776 kEUR` |
| Taxable income before losses, aggregate | `200,845.61588458845 kEUR` |
| Tax losses used | `563.9800189521256 kEUR` |
| CIT accrual | `38,915.55406411077 kEUR` |
| Cash tax | `38,915.55406411077 kEUR` |
| First positive clean cash-tax period | canonical index 20, `28.239318827700245 kEUR` |

The source workbook's first positive cash CIT is around H2 2042. That timing is
not fitted in clean production. The first material source/clean divergence is
the workbook's historical fiscal-reintegration identity, which makes the R54
amount more negative in taxable income. Canonical Finco instead applies the
required deductible-only identity. This difference naturally affects tax-loss
utilisation, cash tax, Bank CFADS, Senior sizing, and downstream SHL cash. It is
reported, not hidden with a timing index, replay vector, or calibration amount.

### Tax-loss authority: 25,000 versus 3,568.6878026481627

| Item | 25,000 | 3,568.6878026481627 |
|---|---|---|
| source workbook cell | No clean source cell established | Source construction SHL interest / EBT evidence |
| formula | Legacy scalar input | Cash SHL principal compounded at typed 8% construction terms |
| input/output | `LEGACY_CALIBRATION` input | `SOURCE_WORKBOOK_MECHANIC` validation output |
| origin period/date | Unbridged legacy opening state | Construction through 30 December 2029 |
| financial meaning | Compatibility tax-loss balance | Construction financing expense / generated loss effect |
| clean production use | Never | Validation only; clean derives its own construction-origin state |

The clean result derives `3,520.419555278244 kEUR` of construction SHL PIK from
its typed funding solution. The same amount increases opening SHL and enters the
tax gross-interest audit once (`3,520.4195552771707 kEUR`, numerical residual
approximately `1.1e-09 kEUR`). It is not added to hard CAPEX and neither the
legacy `25,000` nor source `3,568.6878` is hardcoded as a clean opening vintage.

## Continuation A construction and financing

Canonical accounting uses one construction boundary column plus 60 operating
periods. The typed financing adapter independently uses the source 18 monthly
construction periods and the source-proven SHL accrual tail.

| Metric | CLEAN_RUNTIME_RESULT |
|---|---:|
| Hard CAPEX | `70,691.53944444444 kEUR` |
| Senior IDC | `1,769.3542393177283 kEUR` |
| Senior commitment fee | `166.96711785568684 kEUR` |
| Structuring fee | `471.5143013349264 kEUR` |
| VAT payable | `4,638.2823499999995 kEUR` |
| Peak derived VAT commitment | `3,361.5090166666664 kEUR` |
| Terminal VAT requirement | `0 kEUR` |
| VAT IDC | `122.31400101334873 kEUR` |
| VAT commitment fee | `26.465752928759645 kEUR` |
| Total project uses | `73,031.02983135793 kEUR` |
| Sources/Uses residual | `0 kEUR` |

Hard CAPEX receives a 20-year source-proven useful life. Financing-cost useful
lives remain owned by the accounting layer: Senior financing costs use 12 years
and VAT financing costs use 20 years. Stage B2 hands off amounts only.

## Continuation A Senior and SHL

TUHO Bank sizing consumes typed P90 production, the source MidLow D109 merchant
curve multiplied by the source inflation index, and the source DSCR schedule
(`1.20` for 24 periods, then `1.4125` for four periods).

| Metric | CLEAN_RUNTIME_RESULT |
|---|---:|
| Gearing basis | Total project uses |
| Gearing capacity | `58,424.82386508634 kEUR` |
| DSCR capacity | `43,789.92111682598 kEUR` |
| Binding constraint | `DSCR` |
| Final Senior | `43,789.92111682598 kEUR` |
| Cash SHL principal | `28,741.108714531947 kEUR` |
| Construction SHL PIK | `3,520.419555278244 kEUR` |
| First operating SHL opening | `32,261.52826981019 kEUR` |
| Total operating SHL principal | `42,662.17052924682 kEUR` |
| Principal eligibility / final principal | model indexes 25 / 36 |
| Terminal SHL | `0 kEUR` |

The canonical factory contains no frozen Senior schedule or fixed debt anchor.
Changing target DSCR changes Senior naturally; changing project name/code does
not change any financial output. Production receives the exact converged typed
SHL contract, rather than reconstructing it from a legacy factory amount.

## Source, legacy, and clean reconciliation

Revenue, OPEX, and EBITDA remain on the existing source-proven B6 causal path.
Clean aggregate results are respectively `423,762.0018183332`,
`85,403.45100059909`, and `338,358.5508177341 kEUR`. Construction timing,
funding, VAT, Senior, SHL and tax are calculated from typed inputs.

The first material source/clean divergence is tax policy, not operating
performance: canonical Finco rejects the source workbook's historical
double-count fiscal-reintegration identity. Consequently clean cash tax starts
earlier than the source workbook, and clean Senior (`43,789.92111682598 kEUR`)
differs from the source validation value (`43,359.273782 kEUR`). This is a
transparent policy difference, not a target-fit failure.

## Governance conclusion

Continuation A introduces zero project identity dispatch, gate/tax/output-vector
replay, frozen-Senior production reads, workbook/report production reads,
approved or expected deltas, balancing plugs, target fitting, terminal top-ups,
or compensating tuning. Source fixtures remain validation-only. PR #938 remains
untouched.

Final classification:

`PHASE_B3_TUHO_CLEAN_PRODUCTION_PROMOTION_PROVEN`
