# Phase B2 - Oborovo Clean Production Promotion

**Status:** `OBOROVO_CLEAN_PRODUCTION_PROMOTION_COMPLETE_CANDIDATE`
**Base:** `bd9a6fe59895d9675d67d872217143193a6fdedf`
**Scope:** Oborovo production routing plus generic typed construction/VAT facility authority.
**Not claimed:** `SINGLE_PRODUCTION_ENGINE_CUTOVER_COMPLETE` (TUHO remains blocked).

## Authority transition

Before B2, `run_project("Oborovo", "Base")` failed closed with
`BLOCKED_BY_TYPED_INPUT_GAP`, reason
`PR8_G2A_FINANCING_CONTRACT_FIELDS_NOT_TYPED`, and `calculation_count=0`.
The factory exposed no typed sponsor/gearing/construction contract and retained
the frozen Senior fixture plus manually stored financing costs.

After B2, the canonical Oborovo snapshot classifies naturally as
`CLEAN_PRODUCTION_READY`. Production executes exactly one
`run_project_shareholder_waterfall_model` call and zero legacy calls. Its
lineage contains:

| Metadata | Value |
|---|---|
| runtime authority | `clean_g2c` |
| calculation count | `1` |
| construction authority | `PR9_TYPED_CONSTRUCTION_FINANCING_IDC_AUTHORITY` |
| VAT facility authority | `TYPED_CONSTRUCTION_VAT_FACILITY_AUTHORITY` |

No identity branch was added to the classifier. Renaming project name, code,
and company leaves classification and clean financing unchanged.

## Sponsor and gearing proof

The runtime-derived funding identity is:

| Component | kEUR |
|---|---:|
| Total Project Uses | 57,973.042280034315 |
| Senior (DSCR binding) | 42,852.302723344226 |
| Share Capital | 500.000000000000 |
| SHL cash principal | 14,620.739556690089 |
| Sources minus Uses | 0.000000000000 |

This proves `SHARE_CAPITAL_THEN_SHL`: legal share capital is used first and SHL
funds the remaining sponsor requirement. It also proves
`TOTAL_PROJECT_USES`: the 75.24% gearing capacity is 43,618.91701149782 kEUR,
above the clean DSCR capacity, so DSCR binds at 42,852.302723344226 kEUR.
Neither setting was copied as an unexplained Generic Solar/Wind default.

## Typed construction axis and inputs

The construction calendar comprises 12 consecutive inclusive monthly periods:
29 June 2029 through 31 May 2030. CAPEX is payable only on that construction
axis. Senior IDC is active for the source-proven first 11 periods. A separate
VAT facility axis continues for six runoff periods through 30 November 2030;
it does not alter the operating axis. A 1-28 June 2030 SHL accrual-only tail
completes 365 ACT/365 Fixed days. The date-derived SHL construction DCF is
therefore exactly 1.0; the legacy scalar is validation only.

Senior construction pricing uses causal source primitives: 3.00% fixed/base,
2.65% margin, 80% hedge, 0.20% swap margin, zero forward adjustment/CVA, 20%
floating-curve buffer, the committed 12-month Euribor fixing curve, and
ACT/360. IDC uses closing drawn balance and next-period capitalization.

The commitment fee is 1.05% on closing undrawn balance with next-period
capitalization. The structuring fee is 1.00% on the source facility basis of
47,730.2687 kEUR and has explicit first-period payment timing. These are input
facts; no source draw, IDC, fee, or Total Uses output vector is consumed.

## Typed VAT facility

`ConstructionVatFacilityInput` is identity-free and carries only causal facts:

| Input | Oborovo value |
|---|---:|
| Commitment | 4,877.989945 kEUR |
| Interest rate | 5.65% |
| Commitment fee | 0.9275% |
| Day count | ACT/360 |
| Reimbursement lag | 6 periods |
| Commitment-fee active periods | 12 |
| Facility horizon | 18 periods |

Relevant CAPEX classes carry a 17% VAT rate. Production Units are exempt under
`AGGREGATE_RECONCILIATION_INFERENCE`; this is not represented as direct source
evidence. Other classifications retain `DIRECT_SOURCE`. A disabled typed VAT
facility produces no VAT requirement or financing cost even if VAT payable is
audited. Synthetic non-Oborovo tests prove VAT-rate and facility-rate direction,
zero VAT behavior, multiple classes, alternate period counts, and fee behavior.

## Derived construction outputs

The clean snapshot sets all manual derived construction fields to zero:
`idc_keur`, `commitment_fees_keur`, `bank_fees_keur`, `vat_costs_keur`,
`vat_facility_idc_keur`, `vat_facility_commitment_fee_keur`, and `shl_idc_keur`.
The runtime derives:

| Output | kEUR |
|---|---:|
| Hard CAPEX | 55,999.085500000000 |
| Senior IDC | 1,086.019113085831 |
| Senior commitment fee | 188.565408682822 |
| Structuring fee | 477.302687000000 |
| VAT facility IDC | 208.447618454567 |
| VAT facility commitment fee | 13.621952810813 |
| Total capitalized financing costs | 1,973.956780034032 |
| SHL construction PIK | 1,169.659164535207 |

VAT peak requirement is 4,877.989945 kEUR and terminal requirement is below
`1e-9` kEUR. Stage B2 converges in 7 iterations with residual
`2.1367219105172808e-10` kEUR. Maximum period and cumulative Sources/Uses
residuals are both zero. The outer financing verification residual is below
`1e-8` kEUR. Each financing cost appears once as a typed output and never also
as a manual CAPEX input.

## Senior and SHL authority

The frozen Senior fixture path is absent from the production snapshot and a
spy test rejects any attempted read. Clean Senior is derived from Bank CFADS,
typed sizing/sculpting/rate schedules, and the DSCR constraint. Mutating the
legacy `fixed_debt_keur` anchor to 1 kEUR leaves clean Senior unchanged within
solver tolerance.

Clean sponsor/SHL results are:

| Output | kEUR |
|---|---:|
| SHL cash principal | 14,620.739556690089 |
| SHL construction PIK | 1,169.659164535207 |
| First operating SHL opening | 15,790.398721225296 |
| Operating gross interest | 30,940.671686301303 |
| Operating principal paid | 26,713.379909759595 |
| Terminal SHL closing | 0.000000000000 |

Typed construction allocations, typed SHL rate, dates, and ACT/365 Fixed day
count are the single clean construction-interest authority.

## Source, legacy, and clean review

Source totals are read only from committed source-evidence fixtures. Legacy is
the explicit calibration route. Clean values come from the single G2C result.

| Line | Source evidence | Explicit legacy | Clean production | First causal classification |
|---|---:|---:|---:|---|
| Revenue | 237,686.922417 | 238,438.177588 | 237,686.922417 | Legacy differs: `LEGACY_CALIBRATION_ARTIFACT` |
| OPEX | 55,782.950839 | 55,782.950839 | 55,782.950839 | closed |
| EBITDA | 181,903.971578 | 182,655.226749 | 181,903.971578 | Legacy revenue artifact; clean closed |
| Book depreciation basis | 57,973.052657 | not exposed | 57,973.042280 | `ROUNDING_TIMING_DIFFERENCE` in typed financing costs |
| Cash tax | 10,443.088330 | 8,490.320140 | 10,437.904767 | `SOURCE_WORKBOOK_METHOD` / clean tax periodisation |
| Base CFADS | 171,515.883248 | not exposed | 171,466.066811 | source CF row 79 method follows the tax boundary |
| Senior principal | 42,852.278763 | not exposed | 42,852.302723 | natural DSCR solve; no forced source amount |
| Senior interest | 20,133.079290 | not exposed | 20,133.090175 | follows natural debt quantum/timing |
| Senior debt service | 62,985.358053 | 63,191.174225 | 62,985.392898 | follows natural debt quantum/timing |
| Post-Senior cash | 108,530.525195 | not exposed | 108,480.673913 | follows Base CFADS and Senior service |
| SHL opening | 15,790.435806 | legacy calibration basis | 15,790.398721 | typed construction allocation/DCF |
| SHL gross interest | 30,935.249197 | not exposed | 30,940.671686 | follows clean opening and cash path |
| SHL principal | 26,771.882877 | not exposed | 26,713.379910 | clean cash-sweep policy |
| Legal-equity distributions | 58,192.098182 | 64,006.489082 | 61,689.902655 | clean covenant/reserve/SHL policy boundary |

Revenue, OPEX, and signed EBITDA close to source at numerical precision. The
existing B8 reconciliation identifies the first material source-to-clean
operating divergence at period 1 Taxable Income (72.099172298129 kEUR); this is an explicit
source-workbook/clean-tax methodology boundary, not a construction calibration.
No output target is used by production.

## Legacy and remaining boundaries

`create_default_oborovo_legacy_calibration()` overlays only the historical
manual financing values, frozen Senior fixture, and legacy flags on the shared
economic factory. `run_project_legacy("Oborovo")` uses that overlay and retains
its pre-B2 KPI fingerprint. Production never uses it.

Generic Solar and Generic Wind retain their frozen clean fingerprints. TUHO
remains `BLOCKED_BY_DEFERRED_TAX_CAPABILITY`; its production route performs zero
calculations. PR #938 remains untouched. Clean Project IRR/NPV/LLCR and clean
financial-statement assembly remain unavailable as previously documented.
The next Phase B stage should address TUHO's typed tax/financing blockers; it
must not infer that the generic VAT capability alone makes TUHO promotable.

## Governance classification

`OBOROVO_CLEAN_G2C_AUTHORITY`
`OBOROVO_FROZEN_SENIOR_PRODUCTION_AUTHORITY_REMOVED`
`TYPED_CONSTRUCTION_VAT_AUTHORITY_ACTIVE`
`NO_SOURCE_OUTPUT_REPLAY`
