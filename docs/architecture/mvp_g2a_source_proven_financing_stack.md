# MVP G2A Source-Proven Financing Stack

## Authority and scope

G2A adds a project-financing constraint and audit layer. It does not add a
second Senior schedule, a Junior engine, a VAT-facility engine, construction
IDC, distributions, sponsor IRR, or MOIC. G0 remains the authority for DSCR
debt capacity. The existing clean Senior and SHL/tax fixed-point kernels remain
the authorities for funded Senior and SHL schedules.

The canonical sequence is:

`total project uses -> Bank DSCR capacity -> gearing capacity -> lower-of final Senior -> fixed other funding -> fixed share capital -> residual SHL or additional equity`.

## Committed source evidence

| Evidence | Proven use |
|---|---|
| `tests/fixtures/excel_oborovo_debt_interest_truth.json` | `Inputs!D195 = MIN(DS!$D$47,G171*$D$230)` and `G171 = SUM(G165:G170)` |
| `tests/fixtures/excel_oborovo_financial_truth.json` | Independent D195/G171 formula lineage and cached source values |
| `docs/model_mapping/oborovo_model_manifest_v5.json` | D195, D255 and D325 are formula cells; D312 is a hard-coded share-capital input |
| `docs/model_mapping/source/oborovo_inputs_source_v2.json` | Source storage classification for the financing inputs |
| `tests/fixtures/excel_oborovo_shl_operating_truth.json` | Source-cached SHL cash principal and operating SHL schedule evidence |
| `docs/reconciliation/c3b3d2a_oborovo_shl_source_truth.md` | D325 SHL cash principal 14,620.773894815633 kEUR and construction PIK handshake |
| `docs/stage_b2_construction_idc_runtime_contract.md` | Construction uses and sponsor/SHL/Junior-before-Senior draw waterfall |
| `docs/phase7i_construction_schedule_engine.md` | Cumulative source caps and source-waterfall draw semantics |
| `domain/construction/funding_allocation.py` | Existing offline implementation of the documented source waterfall |

The user-supplied source bridge identifies `Inputs!D325 = G171 - SUM(D195,
D255,D312)`. The repository independently confirms that D325 is a formula cell
and confirms its cached authoritative value; no committed evidence contradicts
the bridge.

## Source workbook cell-reference quirk

The D195 formula references D230, while mapping material also labels D230 as
hedge coverage. Both the source hedge percentage and gearing cap happen to be
80%, so numeric equality cannot establish semantic ownership. This is classified
`SOURCE_WORKBOOK_CELL_REFERENCE_QUIRK`. Clean G2A uses the explicit project-owned
`gearing_ratio`; hedge coverage is never used as gearing.

## Project uses

`total_project_uses` includes hard project CAPEX, explicit capitalised financing
cost uses, reserve-account funding, and other explicit project uses. It is not
an alias for hard CAPEX. The current Generic Solar and Wind factories have zero
financing-cost and reserve uses, so their totals remain 33,000 and 43,000 kEUR.
The Oborovo source total also includes source-derived Senior IDC, commitment
fees, bank fees and VAT-facility financing costs. The nominal VAT facility is
not treated as permanent project funding.

## Senior and sponsor funding

G2A exposes DSCR capacity, gearing basis, gearing ratio, gearing capacity, final
Senior commitment and the binding constraint. Final Senior is the lower of the
two capacities. A gearing-bound case may therefore have Bank DSCR above target;
debt is never increased to force DSCR back to target.

`SponsorFundingMode.SHARE_CAPITAL_THEN_SHL` derives residual SHL cash principal.
`SponsorFundingMode.EQUITY_ONLY` derives zero SHL and classifies the residual as
additional legal equity/share premium. Instrument availability is explicit and
is not inferred from project identity, amount, rate, or repayment method.

Generic Solar and Wind retain their old factory SHL amounts temporarily as
compatibility assertions. `run_project_financing_model` starts its fixed point
from zero and never reads those amounts as G2A authority.

## Construction funding audit policy

Committed source evidence establishes a sponsor/SHL/Junior-before-Senior source
waterfall but does not establish a generic monthly CAPEX timing curve for the
fictional Solar/Wind projects. G2A therefore uses
`GENERIC_MVP_SPONSOR_FIRST_LINEAR_USES`: linear monthly project uses across the
explicit construction-month count, funded through fixed share capital,
additional equity, SHL cash, Junior/other funding, and finally Senior.

This is a transparent `GENERIC MVP POLICY`, not Excel source truth. It is audit
timing only and does not calculate IDC or alter operating outputs. Every period
and cumulative period must satisfy Sources minus Uses equal to zero without a
balancing account.

SHL construction PIK is never classified as a cash source. Opening operating
SHL equals cash principal plus construction PIK from the existing SHL schedule.
For current Generic Solar/Wind the explicit construction day-count fraction is
zero, so construction PIK is zero. Oborovo remains on its accepted source-proven
compatibility path.
