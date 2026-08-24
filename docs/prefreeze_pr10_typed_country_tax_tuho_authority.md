# PR-10 Typed Country Tax and TUHO Authority Review

## Status and boundary

This stage establishes an explicit, typed country-policy resolution boundary
and canonical opening-loss vintages. It does **not** promote TUHO to clean
production. TUHO requires deductible SHL interest subject to a source-model
limitation, and the resulting SHL -> tax -> CFADS -> Senior -> SHL feedback is
the still-open G2C boundary.

Classification:

`PR10_TYPED_COUNTRY_TAX_AUTHORITY_PROVEN_TUHO_PROMOTION_BLOCKED_BY_G2C_FEEDBACK`

The production calculation chain remains:

```text
typed ProjectInputs / approved policy resolution
  -> existing TaxCalculationInput / TaxPolicy
  -> financial_engine.tax.engine.calculate_tax
  -> cash tax / Base CFADS
  -> existing financing stack
```

No third tax engine is introduced. `finco_core.tax.engine` and the illustrative
template registry are not production authorities.

## Architecture inventory

| Surface | Responsibility | Runtime status |
|---|---|---|
| `financial_engine/tax/engine.py` | Annual taxable income, FIFO LCF, CIT and cash-tax allocation | Sole clean calculation authority |
| `financial_engine/tax/models.py` | Immutable annual, period, ATAD and vintage audit results | Active clean contracts |
| `financial_engine/tax/atad.py` | Annual EBITDA/de-minimis interest limitation and period allocation | Active when explicitly enabled with complete interest |
| `financial_engine/tax/loss_ledger.py` | Annual FIFO vintage generation, use and expiry | Active clean authority |
| `financial_engine/tax/tax_year.py` | Date-driven calendar-year fragmentation and payment-period selection | Active clean authority |
| `financial_engine/policies/tax.py` | Immutable tax policy, timing, periodisation, LCF gate and SHL deductibility modes | Active clean contract |
| `financial_engine/adapters/tax_inputs.py` | Typed ProjectInputs resolution and fail-closed clean contract construction | Active adapter; no formulas |
| `financial_engine/tax/jurisdiction.py` | Versioned identification, provenance, approved default and override resolution | Active only through explicit policy ID |
| `finco_core/inputs/_models.py::TaxParams` | Canonical project-owned tax inputs and explicit opening vintages | Active input authority |
| `finco_core/tax/` | Older tax/accounting compatibility modules | Not selected as the clean production calculator |
| `finco_core/tax/templates/` | Illustrative, non-binding examples | Never implicitly activated |

## Country-policy precedence

1. With no `country_tax_policy_id`, existing `TaxParams` behavior is unchanged.
2. Country metadata alone activates nothing.
3. An explicit policy ID resolves only approved defaults owned by that profile.
4. `corporate_rate_override`, when present, wins over the profile default.
5. A conflicting legacy `corporate_rate` without an explicit override fails
   closed rather than being silently replaced.
6. Fields not supplied by the profile remain explicit project inputs. In this
   stage that includes LCF duration, ATAD, tax depreciation, SHL treatment and
   cash-tax timing.

The approved profile `HR-approved-source-model-2026-v1` contains only the
source-workbook CIT primitive of 18%. It is source-model evidence, not a claim
about Croatian statute. In particular, the workbook's five-column loss window
is not promoted as a five-calendar-year legal default.

## TUHO source workbook

Local workbook: `20260330_TUHO_BP.xlsm`.

- Historical canonical hash: `780779eba4278ccc2b8546a9411ccee24917d388f411ba60c88aa342cb5c727a`.
- Local file hash: `266d9669a54298513a42dc16d7be2ae8303c160e31e8b3bd92001d3be593b13c`.
- The hash differs due to previously accepted metadata-only changes. The cells
  and formulas cited below agree with committed source-evidence documentation.

## TUHO source-truth inventory

| # | Source cell / row | Formula or primitive | Economic meaning | Candidate typed authority | Production status |
|---:|---|---|---|---|---|
| 1 | `Inputs!D386` | `0.18` | CIT rate | Explicit approved policy default / override | Resolvable, not TUHO-promoted |
| 2 | `P&L!R43`, period dates in rows 1-2 | H1+H2 annual aggregation, paid in H2 | Source model tax year convention | Typed calendar timing where dates support it | Source documented |
| 3 | `P&L!R43-R44`, `CF!R67` | Annual CIT in H2; cash tax in same H2 | Zero-period cash-tax lag | `TAX_YEAR_LAST_PERIOD`, lag 0 | Clean capability exists |
| 4 | `P&L!G35 -> H36` | `-3568.6878026481627` | Construction-period loss entering operations | Explicit opening vintage | Typed capability added |
| 5 | `P&L!G1:G2` | period ending `2029-12-31` | Opening-loss origin | calendar tax year 2029 | Typed capability added |
| 6 | `Inputs!D390`, `P&L!R36:R39` | `5`; rolling five-column formulas | Workbook loss window | Explicit project LCF input only | Not promoted as law |
| 7 | `P&L!R37` | positive income consumes available loss | Loss use in source row order | Clean FIFO ledger | Generic authority exists |
| 8 | `P&L!R13 = Dep!R30` | book depreciation | P&L depreciation | Existing book depreciation result | Existing authority |
| 9 | `P&L!R35` | EBT plus R34; no separate tax-dep row | Tax basis consumes book depreciation | `BOOK_BASED_PERCENTAGE` at 100% | Causal capability exists |
| 10 | `Dep!R30` vs `Dep!R31` | separate book/unlevered rows differ | Workbook exposes another depreciation view, but taxable row uses book | Do not replay either output vector | Source distinction documented |
| 11 | `P&L!R24 = DS!R50 - CF!R73` | actual Senior interest | Senior interest expense | Actual clean Senior schedule | Existing financing injection |
| 12 | `P&L!R27 = DS!R122` | actual SHL gross interest | SHL interest expense | Actual clean SHL schedule | Required for complete interest |
| 13 | No proven active Junior/VAT tax-interest row | none proven | Other financing interest | Actual schedule if later supported | Not active / VAT deferred |
| 14 | `Inputs!D399:D400`, `P&L!R57:R58` | max of 3,000 and 30% EBITDA tests | EBITDA-based SHL limitation evidence | Existing ATAD/limitation policy primitives | Source semantics not fully implementable for TUHO |
| 15 | `Inputs!D397`, `BS!R44:R45`, `P&L!R56` | debt/equity gate | Source thin-cap activation | Typed limitation mechanism | Missing generic source-equivalent execution |
| 16 | `Inputs!D399:D400` | 3,000 kEUR / 30% | de-minimis and EBITDA percentage | Existing typed ATAD fields | Available but cannot omit SHL feedback |
| 17 | No separately proven permanent-difference primitive | none | Permanent differences | Explicit period adjustments only | No new value introduced |
| 18 | `P&L!R34 = -R54` | subtractive source reintegration convention | Source financial-expense adjustment | Requires economic primitive, not residual | Not promoted; clean equation unchanged |
| 19 | No separately proven extraordinary taxable-income primitive | none | Extraordinary income | Explicit adjustment if proven | Not active |
| 20 | No separately proven grant/assistance tax primitive | none | Grants / assistance | Explicit adjustment if proven | Not active |
| 21 | No separately proven development/concession tax adjustment | none | Development fee treatment | Explicit adjustment if proven | Not active |
| 22 | `P&L!G27,G30,G32,G35` | construction SHL interest produces loss | Construction P&L creates opening fiscal position | Typed opening vintage; construction accounting remains separate | Source mapped, not promoted |
| 23 | `P&L!AG43`, `CF!AG67` | `120.18903737619021` | First positive CIT/cash-tax period, H2 2042 | Date-driven payment period | Evidence only |
| 24 | `P&L!R36:R39` | opening + generated - used - expired = closing | Loss closing balance | Clean annual FIFO ledger | Generic authority exists; source period mismatch remains |

## Opening-loss bridge

The historical `25,000 kEUR` is a legacy factory compatibility input. It has no
workbook cell, origin year or vintage bridge and is therefore not accepted by
the clean adapter.

The source-derived bridge is:

```text
P&L!G27 construction SHL interest       3,568.6878026481627
P&L!G30 financial result               -3,568.6878026481627
P&L!G32 EBT                            -3,568.6878026481627
P&L!G34 fiscal reintegration                0.0
P&L!G35 taxable result                 -3,568.6878026481627
P&L!H36 opening losses                  3,568.6878026481627
origin calendar tax year                2029
```

It is one source-model vintage. Under the clean annual ledger and an explicit
five-year policy, its derived last usable calendar tax year is 2034. Under the
workbook's literal five-column semiannual window, the compatibility expiry is
different. That period/year mismatch is disclosed and not fitted.

The legacy scalar remains in the TUHO factory solely to preserve the frozen
legacy runtime while clean promotion is blocked. It never enters the clean
contract: a source-variant clean input must set it to zero and supply the typed
2029 vintage. A non-zero scalar still fails closed.

## Tax equation and financing authority

The clean equation is unchanged:

```text
taxable income before LCF
  = EBITDA
  - tax depreciation
  - deductible financing interest
  + explicit fiscal reintegration
```

Senior and SHL gross interest must come from their actual engine schedules.
ATAD remains fail-closed unless the caller promises and injects complete Senior,
SHL and other financing interest. Source interest vectors are test evidence only.

TUHO's SHL interest is not proven fully non-deductible. The workbook applies a
debt/equity gate and 3,000/30%-EBITDA limitation to actual SHL interest. The
clean `SUBJECT_TO_LIMITATIONS` mode therefore remains fail-closed. Freezing a
source SHL schedule would break the existing fixed-point authority and is not
permitted.

## Causal tests

Dedicated tests prove:

- CIT +100 bps increases CIT for positive taxable income.
- Increasing opening losses reduces early CIT and reconciles the ledger.
- Increasing tax depreciation reduces taxable income and CIT.
- Increasing deductible Senior interest reduces taxable income.
- Fully non-deductible SHL interest does not reduce taxable income.
- Positive fiscal reintegration increases taxable income by the same amount.
- An expired vintage cannot be used.
- Dates, not identity, determine the source periodisation.
- Renaming a project with unchanged typed policy produces identical tax results.
- Country metadata alone does not activate the illustrative registry.

## TUHO bridge and residual

The source first cash-tax period is H2 2042 (`P&L!AG43` / `CF!AG67`) at
`120.18903737619021 kEUR`. A production clean TUHO annual/cash-tax vector is not
reported because the required deductible-SHL feedback is unresolved. Therefore
there is no claimed source-versus-Finco residual and no fitted annual bridge.

The first causal divergence is the unsupported source-equivalent SHL limitation
inside the closed financing/tax fixed point. Country selection, CIT rate,
opening-vintage ownership, calendar timing capability, depreciation causality
and complete-interest fail-closed behavior are independently proven before that
boundary.

## Governance

Production code contains no project-name/code dispatch, identity branch,
source-output replay, expected/approved delta, balancing plug, target fitting,
magic tax period, terminal tax top-up, hidden post-tax mutation, swallowed
exception or clean-to-legacy fallback. No source parity vector enters
`ProjectInputs`, `TaxPolicy`, `TaxCalculationInput`, Senior sizing or SHL sizing.

VAT Facility remains deferred. KUPI remains diagnostic-only. Oborovo and the
generic Solar/Wind paths do not select the new policy and retain their existing
behavior.
