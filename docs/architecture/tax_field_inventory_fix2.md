# Tax Field Inventory — Fix 2 (C3B3FIX2B)

## Classification scheme

| Code | Meaning |
|---|---|
| A | Jurisdiction default — value from country law or binding treaty |
| B | Project override — explicitly set per project, not derivable from jurisdiction alone |
| C | Model convention — Finco engine modelling choice, not a legal rule |
| D | Workbook compatibility — copied from source workbook for numerical parity; NOT jurisdiction law |

## Runtime Status codes

| Code | Meaning |
|---|---|
| SUPPORTED_RUNTIME | Field is read and used by the production financial engine in this release |
| METADATA_ONLY | Field is stored and serialised but not yet consumed in a production calculation |
| FAIL_CLOSED_UNSUPPORTED | Field is declared; engine raises NotImplementedError if the mode is activated |
| DEPRECATED_COMPATIBILITY | Field retained only for backward-compatible deserialisation; must not be treated as law |

## Current TaxParams fields

These are the ACTUAL fields of `TaxParams` as of the current codebase.
**No invented or speculative fields appear in this section.**

| Field | Runtime Status | A/B/C/D | Jurisdiction Default? | Project Override? | Workbook Compat? | ResolvedTaxAssumptions? |
|---|---|---|---|---|---|---|
| `corporate_rate` | SUPPORTED_RUNTIME | A | Yes (corporate_tax_rate in TaxJurisdictionDefaults) | Yes (corporate_tax_rate_override in ProjectTaxOverrides) | No | Yes (corporate_tax_rate) |
| `loss_carryforward_years` | SUPPORTED_RUNTIME | A | No (not yet in jurisdiction catalog) | Yes | No | No |
| `loss_carryforward_cap` | SUPPORTED_RUNTIME | A | No | Yes | No | No |
| `country_tax_policy_id` | SUPPORTED_CLEAN_ADAPTER | A/C | No | No | Yes, explicit only | No |
| `corporate_rate_override` | SUPPORTED_CLEAN_ADAPTER | B | No | No | Yes | No |
| `prior_tax_loss_keur` | LEGACY_RUNTIME_ONLY | D | No | Yes | Fails closed when non-zero | No |
| `opening_tax_loss_vintages` | SUPPORTED_CLEAN_ADAPTER | B | No | No | Yes | No |
| `legal_reserve_cap` | SUPPORTED_RUNTIME | B | No | Yes | No | No |
| `construction_pl` | METADATA_ONLY | C | No | Optional | No | No |
| `thin_cap_enabled` | SUPPORTED_RUNTIME | A | No (not yet in jurisdiction catalog) | Yes | No | No |
| `thin_cap_de_ratio` | SUPPORTED_RUNTIME | A | No | Yes | No | No |
| `atad_enabled` | SUPPORTED_RUNTIME | A | No (not yet in jurisdiction catalog) | Yes | No | No |
| `atad_ebitda_limit` | SUPPORTED_RUNTIME | A | No | Yes | No | No |
| `atad_min_interest_keur` | SUPPORTED_RUNTIME | A | No | Yes | No | No |
| `wht_sponsor_dividends` | METADATA_ONLY | B | No (future catalog) | Yes | No | No (see WHT note) |
| `wht_sponsor_shl_interest` | SUPPORTED_RUNTIME | B | No (future catalog) | Yes | No | No (consumed via shl_wht_rate adapter) |
| `shl_cap_applies` | DEPRECATED_COMPATIBILITY | D | No | No | Yes (Oborovo/TUHO workbook compat) | No |
| `shl_interest_deductibility` | SUPPORTED_RUNTIME | C | No | Yes | No | No |
| `shl_interest_deductible_pct` | SUPPORTED_RUNTIME | C | No | Yes | No | No |
| `foreign_shl_interest_cap_enabled` | SUPPORTED_RUNTIME | B | No | Yes | No | No |
| `tax_loss_utilisation_gate` | SUPPORTED_RUNTIME | C | No | Yes | No | No |
| `tax_periodisation_mode` | FAIL_CLOSED_UNSUPPORTED | C | No | Yes | No | No |
| `shl_construction_accounting` | METADATA_ONLY | C | No | Yes | No | No |
| `shl_construction_payment` | METADATA_ONLY | C | No | Yes | No | No |
| `cit_cash_tax_start_operating_index` | SUPPORTED_RUNTIME | D | No | Yes | Yes (TUHO timing quirk) | No |
| `tax_depreciation_mode` | SUPPORTED_RUNTIME | C | No | Yes | No | No |
| `tax_deductible_book_dep_pct` | SUPPORTED_RUNTIME | C | No | Yes | No | No |
| `tax_dep_basis_source_owned` | METADATA_ONLY | B | No | Yes | No | No |
| `clean_cash_tax_timing_enabled` | FAIL_CLOSED_UNSUPPORTED | C | No | Yes | No | No |
| `shl_limitation_enabled` | SUPPORTED_RUNTIME | C | No | Yes | No | No |
| `shl_interest_cap_keur_annual` | SUPPORTED_RUNTIME | C | No | Yes | No | No |

### PR-11 field classification: shl_limitation_enabled and shl_interest_cap_keur_annual

Both fields were added in PR-11 to support the absolute SHL interest cap path.

**shl_limitation_enabled**
- canonical owner: `TaxParams` (finco_core/inputs/_models.py)
- project-owned (not policy-owned — it is a project input)
- dispatch role: forwarded to TaxPolicy.shl_limitation_enabled via build_tax_contract_from_project_inputs
- default: False
- None/0/False semantics: False = limitation disabled; only explicit True enables it
- serialization authority: finco_core/inputs/serialization.py
- cache relevance: included in hash_inputs_for_cache
- country/profile activation rule: no auto-activation; explicit opt-in only

**shl_interest_cap_keur_annual**
- canonical owner: `TaxParams` (finco_core/inputs/_models.py)
- project-owned (not policy-owned — it is a project input)
- dispatch role: forwarded to TaxPolicy.shl_interest_cap_keur_annual via build_tax_contract_from_project_inputs
- default: None
- None/0/False semantics: None = no cap; 0.0 = zero cap (all SHL interest disallowed under limitation); positive = annual cap in kEUR
- serialization authority: finco_core/inputs/serialization.py
- cache relevance: included in hash_inputs_for_cache
- country/profile activation rule: no auto-activation; explicit opt-in only

## FUTURE / NOT CURRENT — speculative fields NOT in current TaxParams

The following fields were present in an earlier version of the tax inventory document
but do NOT correspond to current TaxParams fields. They must NOT be listed as current.
They are reserved here as documentation of future catalog capability intent only.

| Speculative Field | Why Not Current | Future Map |
|---|---|---|
| `depreciation_method` | Not a TaxParams field; engine uses TaxDepreciationMode enum | Future typed policy |
| `useful_life_solar_years` | Not a TaxParams field | Future asset-life catalog |
| `useful_life_wind_years` | Not a TaxParams field | Future asset-life catalog |
| `useful_life_bess_years` | Not a TaxParams field | Future asset-life catalog |
| `accelerated_depreciation` | Not a TaxParams field | Future depreciation policy |
| `atad_applies` | Actual field is `atad_enabled` (bool) | Already current as atad_enabled |
| `atad_carryforward_years` | Not a TaxParams field | Future ATAD policy |
| `loss_carryforward_cap_pct` | Actual field is `loss_carryforward_cap` (float, not pct-named) | Already current |
| `thin_cap_ratio` | Actual field is `thin_cap_de_ratio` | Already current |
| `thin_cap_safe_harbor_keur` | Not a TaxParams field | Future thin-cap policy |
| `wht_dividends` | Actual field is `wht_sponsor_dividends` | See WHT note |
| `wht_interest` | Actual field is `wht_sponsor_shl_interest` | See WHT note |
| `wht_royalties` | Not a TaxParams field | Future WHT catalog |
| `dtt_country` | Not a TaxParams field | Future DTT catalog |
| `dtt_dividends_rate` | Not a TaxParams field | Future DTT catalog |
| `dtt_interest_rate` | Not a TaxParams field | Future DTT catalog |
| `tax_holiday_years` | Not a TaxParams field | Future project incentive layer |
| `investment_allowance_pct` | Not a TaxParams field | Future incentive policy |
| `green_energy_tax_credit` | Not a TaxParams field | Future incentive policy |
| `property_tax_pct_of_capex` | Not a TaxParams field | Future project cost layer |
| `land_use_fee_keur_per_ha` | Not a TaxParams field | Future project cost layer |
| `grid_access_annual_keur` | Not a TaxParams field | Future project cost layer |
| `vat_rate` | Not a TaxParams field | Future VAT engine |
| `vat_on_capex_recoverable` | Not a TaxParams field | Future VAT engine |
| `shl_interest_cap_rate` | Not a TaxParams field; was workbook compat only | DEPRECATED, removed |
| `jurisdiction` | Not a TaxParams field; TaxJurisdictionProfile is separate contract | TaxJurisdictionProfile |

## WHT runtime decision

- `wht_sponsor_shl_interest`: **SUPPORTED_RUNTIME** — consumed by `waterfall_engine.py` via `shl_wht_rate` adapter parameter.
- `wht_sponsor_dividends`: **METADATA_ONLY** — present in TaxParams but NOT consumed by the current production financial engine. Retained for future WHT dividend calculation capability. `ProjectTaxOverrides.withholding_tax_rate_dividends_override` and `ResolvedTaxAssumptions.withholding_tax_rate_dividends` are kept for the resolver layer but marked as not yet wired to engine computation.

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

The KUPI profile is NOT in the production registry (`get_profile("KUPI-...")` raises `KeyError`).
It may be constructed locally in tests only.

## Jurisdiction resolution chain

The resolution chain for tax assumptions is:

  **Jurisdiction → defaults resolution → project override → immutable ResolvedTaxAssumptions → generic tax engine (NOT formula dispatch)**

Jurisdiction selects defaults profile at input resolution layer; must NOT dispatch financial
calculation formulas. The engine receives only the resolved immutable `ResolvedTaxAssumptions`
snapshot and is project-identity-free.

## TaxJurisdictionDefaults retained fields

`TaxJurisdictionDefaults` carries only fields that are:
1. Consumed by the current runtime tax engine (TaxParams fields with SUPPORTED_RUNTIME status), AND
2. Genuinely jurisdiction-owned (set by jurisdiction law, not project choice)

| Field | Maps to TaxParams | Rationale |
|---|---|---|
| `corporate_tax_rate` | `corporate_rate` | Country CIT rate from statute; jurisdiction-owned A-class |

Fields removed from `TaxJurisdictionDefaults` (FUTURE_COUNTRY_CATALOG_CAPABILITY):
- `withholding_tax_rate_dividends` → maps to `wht_sponsor_dividends` (METADATA_ONLY, not yet engine-consumed)
- `withholding_tax_rate_interest` → maps to `wht_sponsor_shl_interest` (runtime-consumed but B-class; project sets via override)
- `vat_standard_rate` → no current TaxParams VAT field

## Separation rules

1. **D-class fields must never become A-class fields.** `shl_cap_applies` reflects an Oborovo/TUHO workbook convention, not law.
2. **Workbook compatibility conventions must not be declared as jurisdiction defaults.**
   Setting `corporate_rate` from a workbook read is D-class, not A-class.
3. **Model conventions (C) must never be declared as jurisdiction law.** Tax periodisation mode is a Finco engine capability, not a statutory requirement.
4. **None/0/False are distinct.** A field not set (None) is different from a field set to zero or False. Never collapse None into 0.
5. **No unsourced legal values in the catalog.** `PROVENANCE_GENERIC_MVP_POLICY` profiles must not claim to represent statute.
6. **FUTURE fields are not CURRENT.** Speculative fields in the "FUTURE / NOT CURRENT" section above must not appear in the "Current TaxParams" section.
