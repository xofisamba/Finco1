# Workbook V2 — Registry Audit Report

**Version:** 2.0.0
**Total sheets:** 5
**Total fields:** 59

## Sheet: `project_setup` — Project Setup

### Section: Project Identity (`identity`)

| Semantic ID | Label | Snapshot Key | Type | Unit | Required | Editable |
|---|---|---|---|---|---|---|
| `project_setup.identity.project_name` | Project Name | `project_name` | text |  | Y |  |
| `project_setup.identity.project_type` | Project Type | `project_type` | select |  | Y |  |
| `project_setup.identity.country_market` | Country / Market | `country_market` | text |  |  |  |
| `project_setup.identity.currency` | Currency | `currency` | select |  |  |  |
| `project_setup.identity.scenario` | Scenario | `scenario` | text |  |  |  |

### Section: Technical Parameters (`technical`)

| Semantic ID | Label | Snapshot Key | Type | Unit | Required | Editable |
|---|---|---|---|---|---|---|
| `project_setup.technical.capacity_mw` | Installed Capacity | `capacity_mw` | mw | MW | Y |  |
| `project_setup.technical.p50_hours` | P50 Operating Hours | `p50_hours` | mwh | h/yr | Y |  |
| `project_setup.technical.capacity_factor` | Capacity Factor | `capacity_factor` | float | % |  |  |
| `project_setup.technical.cod_date` | Commercial Operation Date | `cod_date` | date |  | Y |  |
| `project_setup.technical.construction_months` | Construction Duration | `construction_months` | months | months | Y |  |
| `project_setup.technical.horizon_years` | Project Horizon | `horizon_years` | years | years | Y |  |

## Sheet: `capex` — CAPEX

### Section: Construction & EPC (`C`)

| Semantic ID | Label | Snapshot Key | Type | Unit | Required | Editable |
|---|---|---|---|---|---|---|
| `capex.C.epc_contract` | EPC Contract | `capex_epc_contract_keur` | keur | kEUR |  |  |
| `capex.C.production_units` | Production Units | `capex_production_units_keur` | keur | kEUR |  |  |
| `capex.C.epc_other` | EPC Other | `capex_epc_other_keur` | keur | kEUR |  |  |
| `capex.C.grid_connection` | Grid Connection | `capex_grid_connection_keur` | keur | kEUR |  |  |
| `capex.C.ops_preparation` | Operations Preparation | `capex_ops_prep_keur` | keur | kEUR |  |  |
| `capex.C.insurances` | Insurances | `capex_insurances_keur` | keur | kEUR |  |  |
| `capex.C.lease_tax` | Lease & Tax | `capex_lease_tax_keur` | keur | kEUR |  |  |
| `capex.C.construction_mgmt_a` | Construction Management A | `capex_construction_mgmt_a_keur` | keur | kEUR |  |  |
| `capex.C.commissioning` | Commissioning | `capex_commissioning_keur` | keur | kEUR |  |  |
| `capex.C.contingencies` | Contingencies | `capex_contingencies_keur` | keur | kEUR |  |  |
| `capex.C.taxes` | Taxes | `capex_taxes_keur` | keur | kEUR |  |  |

### Section: Development (`D`)

| Semantic ID | Label | Snapshot Key | Type | Unit | Required | Editable |
|---|---|---|---|---|---|---|
| `capex.D.project_acquisition` | Project Acquisition | `capex_project_acquisition_keur` | keur | kEUR |  |  |
| `capex.D.project_rights` | Project Rights | `capex_project_rights_keur` | keur | kEUR |  |  |
| `capex.D.audit_legal` | Audit & Legal | `capex_audit_legal_keur` | keur | kEUR |  |  |
| `capex.D.construction_mgmt_b` | Construction Management B | `capex_construction_mgmt_b_keur` | keur | kEUR |  |  |

### Section: Financing Costs (`F`)

| Semantic ID | Label | Snapshot Key | Type | Unit | Required | Editable |
|---|---|---|---|---|---|---|
| `capex.F.idc` | IDC | `capex_idc_keur` | keur | kEUR |  |  |
| `capex.F.bank_fees` | Bank Fees | `capex_bank_fees_keur` | keur | kEUR |  |  |
| `capex.F.commitment_fees` | Commitment Fees | `capex_commitment_fees_keur` | keur | kEUR |  |  |
| `capex.F.other_financial` | Other Financial | `capex_other_financial_keur` | keur | kEUR |  |  |
| `capex.F.vat_costs` | VAT / Recoverable Costs | `capex_vat_costs_keur` | keur | kEUR |  |  |
| `capex.F.reserve_accounts` | Reserve Accounts | `capex_reserve_accounts_keur` | keur | kEUR |  |  |

### Section: CAPEX Summary (`summary`)

| Semantic ID | Label | Snapshot Key | Type | Unit | Required | Editable |
|---|---|---|---|---|---|---|
| `capex.summary.total` | Total CAPEX | `total_capex_keur` | keur | kEUR |  | N |

## Sheet: `opex` — OPEX

### Section: OPEX Line Items (`lines`)

| Semantic ID | Label | Snapshot Key | Type | Unit | Required | Editable |
|---|---|---|---|---|---|---|
| `opex.lines.technical_management` | Technical Management | `opex_technical_management_y1_keur` | keur | kEUR/yr |  |  |
| `opex.lines.om_preventive` | O&M Preventive & Corrective | `opex_o_and_m_preventive_and_corrective_y1_keur` | keur | kEUR/yr |  |  |
| `opex.lines.site_maintenance` | Site Maintenance | `opex_maintain_site_y1_keur` | keur | kEUR/yr |  |  |
| `opex.lines.cleaning_materials` | Cleaning & Materials | `opex_clean_material_y1_keur` | keur | kEUR/yr |  |  |
| `opex.lines.security` | Security | `opex_security_y1_keur` | keur | kEUR/yr |  |  |
| `opex.lines.insurance` | Insurance | `opex_insurance_y1_keur` | keur | kEUR/yr |  |  |
| `opex.lines.lease_property_tax` | Lease & Property Tax | `opex_lease_and_property_tax_y1_keur` | keur | kEUR/yr |  |  |
| `opex.lines.power_expenses` | Power Expenses | `opex_power_expenses_y1_keur` | keur | kEUR/yr |  |  |
| `opex.lines.audit_accounting_legal` | Audit, Accounting & Legal | `opex_audit_and_accounting_and_legal_y1_keur` | keur | kEUR/yr |  |  |
| `opex.lines.bank_fees` | Bank Fees (OPEX) | `opex_bank_fees_opex_y1_keur` | keur | kEUR/yr |  |  |
| `opex.lines.environmental_social` | Environmental & Social Management | `opex_environmental_and_social_management_y1_keur` | keur | kEUR/yr |  |  |
| `opex.lines.contingencies` | Contingencies | `opex_contingencies_y1_keur` | keur | kEUR/yr |  |  |

### Section: OPEX Summary (`summary`)

| Semantic ID | Label | Snapshot Key | Type | Unit | Required | Editable |
|---|---|---|---|---|---|---|
| `opex.summary.total_y1` | Total OPEX Y1 | `opex_y1_keur` | keur | kEUR/yr |  | N |

## Sheet: `revenue` — Revenue

### Section: PPA / Tariff (`ppa`)

| Semantic ID | Label | Snapshot Key | Type | Unit | Required | Editable |
|---|---|---|---|---|---|---|
| `revenue.ppa.base_tariff` | Base Tariff | `rev_ppa_base_tariff` | float | EUR/MWh | Y |  |
| `revenue.ppa.index` | PPA Index | `rev_ppa_index` | float | %/yr |  |  |
| `revenue.ppa.term_years` | PPA Term | `rev_ppa_term_years` | years | years |  |  |
| `revenue.ppa.production_share` | Production Share | `rev_ppa_production_share` | float | % |  |  |
| `revenue.ppa.tariff_legacy` | Tariff (legacy) | `tariff_eur_mwh` | float | EUR/MWh |  | N |
| `revenue.ppa.term_legacy` | PPA Term (legacy) | `ppa_term_years` | years |  |  | N |

### Section: Balancing & CO2 (`balancing`)

| Semantic ID | Label | Snapshot Key | Type | Unit | Required | Editable |
|---|---|---|---|---|---|---|
| `revenue.balancing.cost` | Balancing Cost | `rev_balancing_cost` | float | EUR/MWh |  |  |
| `revenue.balancing.co2_enabled` | CO2 Revenue Enabled | `rev_co2_enabled` | bool |  |  |  |
| `revenue.balancing.co2_price` | CO2 Price | `rev_co2_price` | float | EUR/tCO2 |  |  |

## Sheet: `debt` — Senior Debt

### Section: Senior Debt (`senior`)

| Semantic ID | Label | Snapshot Key | Type | Unit | Required | Editable |
|---|---|---|---|---|---|---|
| `debt.senior.gearing_pct` | Gearing | `gearing_pct` | pct | % |  |  |
| `debt.senior.target_dscr` | Target DSCR | `target_dscr` | float | x |  |  |
| `debt.senior.interest_rate_pct` | All-in Interest Rate | `interest_rate_pct` | pct | % |  |  |
| `debt.senior.tenor_years` | Tenor | `tenor_years` | years | years |  |  |

