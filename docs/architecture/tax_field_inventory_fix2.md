# Tax Field Inventory — Fix 2 (C3B3FIX2B)

## Classification scheme

| Code | Meaning |
|---|---|
| A | Jurisdiction default — value from country law or binding treaty |
| B | Project override — explicitly set per project, not derivable from jurisdiction alone |
| C | Model convention — Finco engine modelling choice, not a legal rule |
| D | Workbook compatibility — copied from source workbook for numerical parity; NOT jurisdiction law |

## TaxParams field inventory

| Field | Class | Notes |
|---|---|---|
| `jurisdiction` | A | ISO country identifier; selects jurisdiction defaults profile at the input resolution layer; must NOT dispatch financial calculation formulas |
| `corporate_tax_rate` | A | Country CIT rate from statute |
| `depreciation_method` | C | Engine capability ("straight_line", "declining_balance"); not a legal rule |
| `useful_life_solar_years` | C | Model convention for solar PV asset life |
| `useful_life_wind_years` | C | Model convention for wind turbine asset life |
| `useful_life_bess_years` | C | Model convention for BESS asset life |
| `accelerated_depreciation` | A | Availability determined by country statute |
| `atad_applies` | A | Whether EU ATAD interest limitation applies (False for non-EU BA, RS, MK) |
| `atad_ebitda_limit` | A | 30% statutory cap from ATAD Article 4 |
| `atad_min_threshold_keur` | A | De minimis threshold from ATAD |
| `atad_carryforward_years` | A | Excess interest carryforward (0 = unlimited) |
| `loss_carryforward_years` | A | Country tax-loss carryforward limit (0 = unlimited) |
| `loss_carryforward_cap_pct` | A | Annual utilisation cap as pct of taxable income |
| `thin_cap_enabled` | A | Whether thin-cap rules apply |
| `thin_cap_ratio` | A | Statutory debt/equity limit |
| `thin_cap_safe_harbor_keur` | A | Safe-harbor threshold from statute |
| `wht_dividends` | A | Domestic WHT on dividends (country law) |
| `wht_interest` | A | Domestic WHT on interest (country law) |
| `wht_royalties` | A | Domestic WHT on royalties (country law) |
| `dtt_country` | B | Counterparty jurisdiction for DTT lookup |
| `dtt_dividends_rate` | A | Treaty rate (from applicable DTT) |
| `dtt_interest_rate` | A | Treaty rate (from applicable DTT) |
| `tax_holiday_years` | B | Project-specific statutory holiday (not derivable from jurisdiction alone) |
| `investment_allowance_pct` | A | Country-law investment deduction percentage |
| `green_energy_tax_credit` | A | Country-law renewable energy credit |
| `property_tax_pct_of_capex` | B | Project-specific; depends on asset location and local authority |
| `land_use_fee_keur_per_ha` | B | Project-specific; local land-use fee |
| `grid_access_annual_keur` | B | Project-specific; grid connection charges |
| `vat_rate` | A | Standard VAT rate from statute |
| `vat_on_capex_recoverable` | A | VAT recoverability under country regime |
| `shl_cap_applies` | D | Deprecated workbook-compat field; must not be treated as law |
| `shl_interest_cap_rate` | D | Deprecated workbook-compat field; must not be treated as law |
| `cit_cash_tax_start_operating_index` | D | Workbook timing quirk for TUHO; not a legal rule |

## Provenance codes (TaxJurisdictionProfile)

| Code | Meaning |
|---|---|
| `SOURCE_PROVEN` | Values proven from primary source documents (law text, DTT text, source workbook) |
| `GENERIC_MVP_POLICY` | Reasonable MVP defaults; not individually proven from primary law sources |
| `TAX_JURISDICTION_SOURCE_UNRESOLVED` | Jurisdiction identified but subnational or specific values unconfirmed from primary source |

## KUPI status

KUPI is located in Bosnia and Herzegovina. The exact subnational entity
(Republika Srpska, Federation of Bosnia and Herzegovina, or Brčko District)
has not been confirmed from a primary source. Status is therefore
**TAX_JURISDICTION_SOURCE_UNRESOLVED**.

The KUPI profile `KUPI-BA-source-unresolved-v1` carries:
- `country_iso = "BA"`
- `subnational_jurisdiction_code = None` (unresolved)
- `provenance = TAX_JURISDICTION_SOURCE_UNRESOLVED`
- `source_references = ()` (empty — no primary source citation)

TaxParams values used for KUPI calculations must not be cited as authoritative
legal values for Bosnia and Herzegovina. They are placeholders pending primary
source confirmation.

## Jurisdiction resolution chain

The resolution chain for tax assumptions is:

  **Jurisdiction → defaults resolution → project override → immutable ResolvedTaxAssumptions → generic tax engine (NOT formula dispatch)**

Jurisdiction code selects the `TaxJurisdictionDefaults` profile at the input
resolution layer only. It must NOT be used to dispatch financial calculation
formulas inside the engine. The engine receives only the resolved immutable
`ResolvedTaxAssumptions` snapshot and is project-identity-free.

## Separation rules

1. **D-class fields must never become A-class fields.** `shl_cap_applies` and
   `shl_interest_cap_rate` reflect an Oborovo/TUHO workbook convention, not law.
2. **Workbook compatibility conventions must not be declared as jurisdiction defaults.**
   Setting `corporate_tax_rate` from a workbook read is D-class, not A-class.
3. **Model conventions (C) must never be declared as jurisdiction law.** A 25-year
   solar asset life is a Finco modelling assumption, not a Croatian tax statute.
4. **None/0/False are distinct.** A field not set (None) is different from a field
   set to zero or False. Never collapse None into 0.
