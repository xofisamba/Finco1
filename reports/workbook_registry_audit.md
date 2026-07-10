# Workbook V2 — Registry Audit Report

**Registry version:** 2.0.0
**Total sheets:** 5
**Total fields:** 59

## Summary

### By binding status

| Status | Count | Meaning |
|--------|-------|---------|
| BOUND | 42 | Fully wired: HTML → snapshot → engine → output |
| PARTIAL | 7 | Persisted but path to engine incomplete (see False-Editable section) |
| DISPLAY_ONLY | 5 | Computed/derived, never a direct user input |
| TEMPLATE_LOCKED | 5 | Excel/factory template anchor, user cannot change |
| UNSUPPORTED | 0 | No engine effect (none currently registered) |

### By field kind

| Kind | Count |
|------|-------|
| derived_display | 7 |
| input | 47 |
| template_input | 5 |

---

## False-Editable Surface

These fields appear editable in the HTML UI but do not drive the engine as primary inputs.
Each is classified PARTIAL or DISPLAY_ONLY and must not be treated as BOUND inputs in V2 code.

| Field ID | Snapshot Key | HTML Surface | Reason |
|----------|-------------|--------------|--------|
| `capex.summary.total` | `total_capex_keur` | inputs_section.html (editable input) | Engine derives CapexStructure.total_capex from per-line CapexItems; snapshot value is display anchor |
| `opex.summary.total_y1` | `opex_y1_keur` | inputs_section.html (editable input) | Engine derives OPEX Y1 from per-line OpexItems; snapshot value is display anchor |
| `revenue.ppa.tariff_legacy` | `tariff_eur_mwh` | inputs_section.html (editable input) | Legacy key; newer projects use rev_ppa_base_tariff as authoritative revenue input |
| `revenue.ppa.ppa_term_legacy` | `ppa_term_years` | inputs_section.html (editable input) | Legacy key; superseded by rev_ppa_term_years |
| `project_setup.technical.capacity_factor` | `capacity_factor` | inputs_section.html (calculated, stored in snapshot) | Shown as read-only/calculated in UI; stored in snapshot for display but derived from capacity_mw and p50_hours |
| `debt.senior.gearing_pct (senior-debt sheet)` | `gearing_pct (data-grid-source)` | sheet_senior_debt.html (draft workspace control) | Draft inputs in senior-debt sheet use data-grid-source, not form submission. inputs_section is the BOUND path. |
| `debt.senior.target_dscr (senior-debt sheet)` | `target_dscr (data-grid-source)` | sheet_senior_debt.html (draft workspace control) | Same as above — draft workspace path, not canonical form submission. |

---

## Full Field Inventory

### Sheet: `project_setup` — Project Setup

#### Section: Project Identity (`identity`)

| Semantic ID | Snapshot Key | Kind | Editable | Persisted | Scenario Policy | Engine Path | TUHO Excel | Oborovo Excel | Binding Status |
|-------------|-------------|------|----------|-----------|-----------------|-------------|------------|---------------|----------------|
| `project_setup.identity.project_name` | `project_name` | input | ✓ | ✓ | not allowed | `info.name` | `Inputs!B2` | `Inputs!B2` | **BOUND** |
| `project_setup.identity.project_type` | `project_type` | template_input | ✗ | ✓ | not allowed | — | `Inputs!B3` | `Inputs!B3` | **TEMPLATE_LOCKED** |
| `project_setup.identity.country_market` | `country_market` | input | ✓ | ✓ | not allowed | `info.country_iso` | `Inputs!B4` | `Inputs!B4` | **PARTIAL** |
| `project_setup.identity.currency` | `currency` | input | ✓ | ✓ | not allowed | — | `Inputs!B5` | `Inputs!B5` | **PARTIAL** |
| `project_setup.identity.scenario` | `scenario` | input | ✓ | ✓ | not allowed | — | — | — | **PARTIAL** |

#### Section: Technical Parameters (`technical`)

| Semantic ID | Snapshot Key | Kind | Editable | Persisted | Scenario Policy | Engine Path | TUHO Excel | Oborovo Excel | Binding Status |
|-------------|-------------|------|----------|-----------|-----------------|-------------|------------|---------------|----------------|
| `project_setup.technical.capacity_mw` | `capacity_mw` | input | ✓ | ✓ | override | `technical.capacity_mw` | `Inputs!H7` | `Inputs!H7` | **BOUND** |
| `project_setup.technical.p50_hours` | `p50_hours` | input | ✓ | ✓ | override | `technical.operating_hours_p50` | `Inputs!H8` | `Inputs!H8` | **BOUND** |
| `project_setup.technical.capacity_factor` | `capacity_factor` | derived_display | ✗ | ✓ | not allowed | — | — | — | **DISPLAY_ONLY** |
| `project_setup.technical.cod_date` | `cod_date` | input | ✓ | ✓ | not allowed | `info.cod_date` | `Inputs!H9` | `Inputs!H9` | **BOUND** |
| `project_setup.technical.construction_months` | `construction_months` | input | ✓ | ✓ | not allowed | `info.construction_months` | `Inputs!H10` | `Inputs!H10` | **BOUND** |
| `project_setup.technical.horizon_years` | `horizon_years` | input | ✓ | ✓ | not allowed | `info.horizon_years` | `Inputs!H11` | `Inputs!H11` | **BOUND** |

### Sheet: `capex` — CAPEX

#### Section: Construction & EPC (C.01–C.16) (`C`)

| Semantic ID | Snapshot Key | Kind | Editable | Persisted | Scenario Policy | Engine Path | TUHO Excel | Oborovo Excel | Binding Status |
|-------------|-------------|------|----------|-----------|-----------------|-------------|------------|---------------|----------------|
| `capex.C.epc_contract` | `capex_epc_contract_keur` | input | ✓ | ✓ | override | `capex.epc_contract.amount_keur` | `C.02.01` | `C.02.01` | **BOUND** |
| `capex.C.production_units` | `capex_production_units_keur` | input | ✓ | ✓ | override | `capex.production_units.amount_keur` | `C.01.01` | `C.01.01` | **BOUND** |
| `capex.C.epc_other` | `capex_epc_other_keur` | input | ✓ | ✓ | override | `capex.epc_other.amount_keur` | `C.02.02` | `C.02.02` | **BOUND** |
| `capex.C.grid_connection` | `capex_grid_connection_keur` | input | ✓ | ✓ | override | `capex.grid_connection.amount_keur` | `C.03.01` | `C.03.01` | **BOUND** |
| `capex.C.ops_preparation` | `capex_ops_prep_keur` | input | ✓ | ✓ | override | `capex.ops_prep.amount_keur` | `C.15.02` | `C.15.02` | **BOUND** |
| `capex.C.insurances` | `capex_insurances_keur` | input | ✓ | ✓ | override | `capex.insurances.amount_keur` | `C.06.01` | `C.06.01` | **BOUND** |
| `capex.C.lease_tax` | `capex_lease_tax_keur` | input | ✓ | ✓ | override | `capex.lease_tax.amount_keur` | `C.07.01` | `C.07.01` | **BOUND** |
| `capex.C.construction_mgmt_a` | `capex_construction_mgmt_a_keur` | input | ✓ | ✓ | override | `capex.construction_mgmt_a.amount_keur` | `C.09.01` | `C.09.01` | **BOUND** |
| `capex.C.commissioning` | `capex_commissioning_keur` | input | ✓ | ✓ | override | `capex.commissioning.amount_keur` | `C.10.01` | `C.10.01` | **BOUND** |
| `capex.C.contingencies` | `capex_contingencies_keur` | derived_display | ✗ | ✗ | not allowed | `capex.contingencies.amount_keur` | `C.13.01` | `C.13.01` | **DISPLAY_ONLY** |
| `capex.C.taxes` | `capex_taxes_keur` | input | ✓ | ✓ | override | `capex.taxes.amount_keur` | `C.14.01` | `C.14.01` | **BOUND** |

#### Section: Development (C.11, C.12, C.15, C.16) (`D`)

| Semantic ID | Snapshot Key | Kind | Editable | Persisted | Scenario Policy | Engine Path | TUHO Excel | Oborovo Excel | Binding Status |
|-------------|-------------|------|----------|-----------|-----------------|-------------|------------|---------------|----------------|
| `capex.D.project_acquisition` | `capex_project_acquisition_keur` | input | ✓ | ✓ | override | `capex.project_acquisition.amount_keur` | `C.15.01` | `C.15.01` | **BOUND** |
| `capex.D.project_rights` | `capex_project_rights_keur` | input | ✓ | ✓ | override | `capex.project_rights.amount_keur` | `C.16.01` | `C.16.01` | **BOUND** |
| `capex.D.audit_legal` | `capex_audit_legal_keur` | input | ✓ | ✓ | override | `capex.audit_legal.amount_keur` | `C.11.01` | `C.11.01` | **BOUND** |
| `capex.D.construction_mgmt_b` | `capex_construction_mgmt_b_keur` | input | ✓ | ✓ | override | `capex.construction_mgmt_b.amount_keur` | `C.09.02` | `C.09.02` | **BOUND** |

#### Section: Financing Costs — C.17 (read-only) (`F`)

| Semantic ID | Snapshot Key | Kind | Editable | Persisted | Scenario Policy | Engine Path | TUHO Excel | Oborovo Excel | Binding Status |
|-------------|-------------|------|----------|-----------|-----------------|-------------|------------|---------------|----------------|
| `capex.F.idc` | `capex_idc_keur` | derived_display | ✗ | ✗ | not allowed | `capex.idc_keur` | `C.17 / Financing!IDC` | `C.17 / Financing!IDC` | **DISPLAY_ONLY** |
| `capex.F.bank_fees` | `capex_bank_fees_keur` | template_input | ✗ | ✗ | not allowed | `capex.bank_fees_keur` | `C.17 / Financing!BankFees` | `C.17 / Financing!BankFees` | **TEMPLATE_LOCKED** |
| `capex.F.commitment_fees` | `capex_commitment_fees_keur` | template_input | ✗ | ✗ | not allowed | `capex.commitment_fees_keur` | `C.17 / Financing!CommFees` | `C.17 / Financing!CommFees` | **TEMPLATE_LOCKED** |
| `capex.F.other_financial` | `capex_other_financial_keur` | template_input | ✗ | ✗ | not allowed | `capex.other_financial_keur` | `C.17 / Financing!OtherFin` | `C.17 / Financing!OtherFin` | **TEMPLATE_LOCKED** |
| `capex.F.vat_costs` | `capex_vat_costs_keur` | template_input | ✗ | ✗ | not allowed | `capex.vat_costs_keur` | `C.17 / Financing!VAT` | `C.17 / Financing!VAT` | **TEMPLATE_LOCKED** |

#### Section: Reserve Accounts — C.18 (read-only) (`R`)

| Semantic ID | Snapshot Key | Kind | Editable | Persisted | Scenario Policy | Engine Path | TUHO Excel | Oborovo Excel | Binding Status |
|-------------|-------------|------|----------|-----------|-----------------|-------------|------------|---------------|----------------|
| `capex.R.reserve_accounts` | `capex_reserve_accounts_keur` | derived_display | ✗ | ✗ | not allowed | `capex.reserve_accounts_keur` | `C.18 / Financing!Reserves` | `C.18 / Financing!Reserves` | **DISPLAY_ONLY** |

#### Section: CAPEX Summary (`summary`)

| Semantic ID | Snapshot Key | Kind | Editable | Persisted | Scenario Policy | Engine Path | TUHO Excel | Oborovo Excel | Binding Status |
|-------------|-------------|------|----------|-----------|-----------------|-------------|------------|---------------|----------------|
| `capex.summary.total` | `total_capex_keur` | derived_display | ✗ | ✓ | not allowed | — | — | — | **PARTIAL** |

### Sheet: `opex` — OPEX

#### Section: OPEX Line Items (B.01–B.13) (`lines`)

| Semantic ID | Snapshot Key | Kind | Editable | Persisted | Scenario Policy | Engine Path | TUHO Excel | Oborovo Excel | Binding Status |
|-------------|-------------|------|----------|-----------|-----------------|-------------|------------|---------------|----------------|
| `opex.lines.technical_management` | `opex_technical_management_y1_keur` | input | ✓ | ✓ | override | `opex[technical_management].y1_amount_keur` | `Inputs!OPEX-B.01` | `Inputs!OPEX-B.01` | **BOUND** |
| `opex.lines.om_preventive` | `opex_o_and_m_preventive_and_corrective_y1_keur` | input | ✓ | ✓ | override | `opex[o_and_m_preventive_and_corrective].y1_amount_keur` | `Inputs!OPEX-B.02` | `Inputs!OPEX-B.02` | **BOUND** |
| `opex.lines.site_maintenance` | `opex_maintain_site_y1_keur` | input | ✓ | ✓ | override | `opex[maintain_site].y1_amount_keur` | `Inputs!OPEX-B.03` | `Inputs!OPEX-B.03` | **BOUND** |
| `opex.lines.cleaning_materials` | `opex_clean_material_y1_keur` | input | ✓ | ✓ | override | `opex[clean_material].y1_amount_keur` | `Inputs!OPEX-B.04` | `Inputs!OPEX-B.04` | **BOUND** |
| `opex.lines.security` | `opex_security_y1_keur` | input | ✓ | ✓ | override | `opex[security].y1_amount_keur` | `Inputs!OPEX-B.05` | `Inputs!OPEX-B.05` | **BOUND** |
| `opex.lines.insurance` | `opex_insurance_y1_keur` | input | ✓ | ✓ | override | `opex[insurance].y1_amount_keur` | `Inputs!OPEX-B.06` | `Inputs!OPEX-B.06` | **BOUND** |
| `opex.lines.lease_property_tax` | `opex_lease_and_property_tax_y1_keur` | input | ✓ | ✓ | override | `opex[lease_and_property_tax].y1_amount_keur` | `Inputs!OPEX-B.07` | `Inputs!OPEX-B.07` | **BOUND** |
| `opex.lines.power_expenses` | `opex_power_expenses_y1_keur` | input | ✓ | ✓ | override | `opex[power_expenses].y1_amount_keur` | `Inputs!OPEX-B.08` | `Inputs!OPEX-B.08` | **BOUND** |
| `opex.lines.audit_accounting_legal` | `opex_audit_and_accounting_and_legal_y1_keur` | input | ✓ | ✓ | override | `opex[audit_and_accounting_and_legal].y1_amount_keur` | `Inputs!OPEX-B.09` | `Inputs!OPEX-B.09` | **BOUND** |
| `opex.lines.bank_fees` | `opex_bank_fees_opex_y1_keur` | input | ✓ | ✓ | override | `opex[bank_fees_opex].y1_amount_keur` | `Inputs!OPEX-B.10` | `Inputs!OPEX-B.10` | **BOUND** |
| `opex.lines.environmental_social` | `opex_environmental_and_social_management_y1_keur` | input | ✓ | ✓ | override | `opex[environmental_and_social_management].y1_amount_keur` | `Inputs!OPEX-B.11` | `Inputs!OPEX-B.11` | **BOUND** |
| `opex.lines.contingencies` | `opex_contingencies_y1_keur` | derived_display | ✗ | ✗ | not allowed | — | `Inputs!OPEX-B.13` | `Inputs!OPEX-B.13` | **DISPLAY_ONLY** |

#### Section: OPEX Summary (`summary`)

| Semantic ID | Snapshot Key | Kind | Editable | Persisted | Scenario Policy | Engine Path | TUHO Excel | Oborovo Excel | Binding Status |
|-------------|-------------|------|----------|-----------|-----------------|-------------|------------|---------------|----------------|
| `opex.summary.total_y1` | `opex_y1_keur` | derived_display | ✗ | ✓ | not allowed | — | — | — | **PARTIAL** |

### Sheet: `revenue` — Revenue

#### Section: PPA / Tariff (`ppa`)

| Semantic ID | Snapshot Key | Kind | Editable | Persisted | Scenario Policy | Engine Path | TUHO Excel | Oborovo Excel | Binding Status |
|-------------|-------------|------|----------|-----------|-----------------|-------------|------------|---------------|----------------|
| `revenue.ppa.base_tariff` | `rev_ppa_base_tariff` | input | ✓ | ✓ | override | `revenue.ppa_base_tariff` | `Inputs!Revenue!B4` | `Inputs!Revenue!B4` | **BOUND** |
| `revenue.ppa.index` | `rev_ppa_index` | input | ✓ | ✓ | override | `revenue.ppa_index` | `Inputs!Revenue!B5` | `Inputs!Revenue!B5` | **BOUND** |
| `revenue.ppa.term_years` | `rev_ppa_term_years` | input | ✓ | ✓ | override | `revenue.ppa_term_years` | `Inputs!Revenue!B6` | `Inputs!Revenue!B6` | **BOUND** |
| `revenue.ppa.production_share` | `rev_ppa_production_share` | input | ✓ | ✓ | override | `revenue.ppa_production_share` | — | — | **BOUND** |
| `revenue.ppa.tariff_legacy` | `tariff_eur_mwh` | input | ✓ | ✓ | not allowed | — | — | — | **PARTIAL** |
| `revenue.ppa.ppa_term_legacy` | `ppa_term_years` | input | ✓ | ✓ | not allowed | — | — | — | **PARTIAL** |

#### Section: Balancing & CO2 (`balancing`)

| Semantic ID | Snapshot Key | Kind | Editable | Persisted | Scenario Policy | Engine Path | TUHO Excel | Oborovo Excel | Binding Status |
|-------------|-------------|------|----------|-----------|-----------------|-------------|------------|---------------|----------------|
| `revenue.balancing.cost` | `rev_balancing_cost` | input | ✓ | ✓ | override | `revenue.balancing_cost_eur_per_mwh` | — | — | **BOUND** |
| `revenue.balancing.co2_enabled` | `rev_co2_enabled` | input | ✓ | ✓ | override | `revenue.co2_enabled` | — | — | **BOUND** |
| `revenue.balancing.co2_price` | `rev_co2_price` | input | ✓ | ✓ | override | `revenue.co2_price_eur` | — | — | **BOUND** |

### Sheet: `debt` — Senior Debt

#### Section: Senior Debt Inputs (`senior`)

| Semantic ID | Snapshot Key | Kind | Editable | Persisted | Scenario Policy | Engine Path | TUHO Excel | Oborovo Excel | Binding Status |
|-------------|-------------|------|----------|-----------|-----------------|-------------|------------|---------------|----------------|
| `debt.senior.gearing_pct` | `gearing_pct` | input | ✓ | ✓ | override | `financing.gearing_ratio` | `Inputs!Debt!B4` | `Inputs!Debt!B4` | **BOUND** |
| `debt.senior.target_dscr` | `target_dscr` | input | ✓ | ✓ | override | `financing.target_dscr` | `Inputs!Debt!B5` | `Inputs!Debt!B5` | **BOUND** |
| `debt.senior.interest_rate_pct` | `interest_rate_pct` | input | ✓ | ✓ | override | `financing.margin_bps` | `Inputs!Debt!B6` | `Inputs!Debt!B6` | **BOUND** |
| `debt.senior.tenor_years` | `tenor_years` | input | ✓ | ✓ | override | `financing.senior_tenor_years` | `Inputs!Debt!B7` | `Inputs!Debt!B7` | **BOUND** |

---

## HTML Editable Field Inventory

Classification of every HTML `<input>` or editable control currently visible in the application,
by binding status.

### BOUND — Fully wired to engine

| HTML name / control | Sheet | Section | Semantic ID |
|---------------------|-------|---------|-------------|
| `capacity_mw` | inputs_section.html | Technical | `project_setup.technical.capacity_mw` |
| `p50_hours` | inputs_section.html | Technical | `project_setup.technical.p50_hours` |
| `cod_date` | inputs_section.html | Technical | `project_setup.technical.cod_date` |
| `construction_months` | inputs_section.html | Technical | `project_setup.technical.construction_months` |
| `horizon_years` | inputs_section.html | Technical | `project_setup.technical.horizon_years` |
| `project_name` | inputs_section.html | Identity | `project_setup.identity.project_name` |
| `rev_ppa_base_tariff` | sheet_revenue.html | PPA | `revenue.ppa.base_tariff` |
| `rev_ppa_index` | sheet_revenue.html | PPA | `revenue.ppa.index` |
| `rev_ppa_term_years` | sheet_revenue.html | PPA | `revenue.ppa.term_years` |
| `rev_ppa_production_share` | sheet_revenue.html | PPA | `revenue.ppa.production_share` |
| `rev_balancing_cost` | sheet_revenue.html | Balancing | `revenue.balancing.cost` |
| `rev_co2_enabled` | sheet_revenue.html | Balancing | `revenue.balancing.co2_enabled` |
| `rev_co2_price` | sheet_revenue.html | Balancing | `revenue.balancing.co2_price` |
| `gearing_pct` | inputs_section.html | Debt | `debt.senior.gearing_pct` |
| `target_dscr` | inputs_section.html | Debt | `debt.senior.target_dscr` |
| `interest_rate_pct` | inputs_section.html | Debt | `debt.senior.interest_rate_pct` |
| `tenor_years` | inputs_section.html | Debt | `debt.senior.tenor_years` |
| `capex_epc_contract_keur` | sheet_capex.html (lig_render) | C.02 | `capex.C.epc_contract` |
| `capex_production_units_keur` | sheet_capex.html (lig_render) | C.01 | `capex.C.production_units` |
| `capex_epc_other_keur` | sheet_capex.html (lig_render) | C.02 | `capex.C.epc_other` |
| `capex_grid_connection_keur` | sheet_capex.html (lig_render) | C.03 | `capex.C.grid_connection` |
| `capex_ops_prep_keur` | sheet_capex.html (lig_render) | C.15 | `capex.C.ops_preparation` |
| `capex_insurances_keur` | sheet_capex.html (lig_render) | C.06 | `capex.C.insurances` |
| `capex_lease_tax_keur` | sheet_capex.html (lig_render) | C.07 | `capex.C.lease_tax` |
| `capex_construction_mgmt_a_keur` | sheet_capex.html (lig_render) | C.09 | `capex.C.construction_mgmt_a` |
| `capex_commissioning_keur` | sheet_capex.html (lig_render) | C.10 | `capex.C.commissioning` |
| `capex_taxes_keur` | sheet_capex.html (lig_render) | C.14 | `capex.C.taxes` |
| `capex_project_acquisition_keur` | sheet_capex.html (lig_render) | C.15 | `capex.D.project_acquisition` |
| `capex_project_rights_keur` | sheet_capex.html (lig_render) | C.16 | `capex.D.project_rights` |
| `capex_audit_legal_keur` | sheet_capex.html (lig_render) | C.11 | `capex.D.audit_legal` |
| `capex_construction_mgmt_b_keur` | sheet_capex.html (lig_render) | C.09 | `capex.D.construction_mgmt_b` |
| `opex_{code}_y1_keur (×11)` | sheet_opex.html | B.01–B.12 | `opex.lines.*` |

### PARTIAL — Persisted but not fully wired

| HTML name / control | Sheet | Why PARTIAL |
|---------------------|-------|-------------|
| `total_capex_keur` | inputs_section.html | Shown editable; engine derives total from per-line CapexItems |
| `opex_y1_keur` | inputs_section.html | Shown editable; engine derives OPEX Y1 from per-line OpexItems |
| `tariff_eur_mwh` | inputs_section.html | Legacy key; newer projects use rev_ppa_base_tariff |
| `ppa_term_years` | inputs_section.html | Legacy key; superseded by rev_ppa_term_years |
| `country_market` | inputs_section.html | Text string mapped to country_iso enum internally; mapping not explicitly registered |
| `currency` | inputs_section.html | Display label; engine uses EUR internally; no direct ProjectInputs field |
| `scenario` | inputs_section.html | Drives ScenarioRunner label selection; not a ProjectInputs field directly |
| `gearing_pct (data-grid-source)` | sheet_senior_debt.html | Draft workspace control; not canonical form submission path |
| `target_dscr (data-grid-source)` | sheet_senior_debt.html | Draft workspace control; not canonical form submission path |
| `interest_rate_pct (data-grid-source)` | sheet_senior_debt.html | Draft workspace control; not canonical form submission path |
| `tenor_years (data-grid-source)` | sheet_senior_debt.html | Draft workspace control; not canonical form submission path |

### DISPLAY_ONLY — Shown in UI, never a user input

| HTML name / element | Sheet | Value source |
|---------------------|-------|--------------|
| `capacity_factor (calculated)` | inputs_section.html | derived_ui: p50_hours / (8760 × capacity_mw) |
| `capex_contingencies_keur (C.13)` | sheet_capex.html | derived_ui: contingency % × non-contingency CAPEX |
| `capex_idc_keur (C.17)` | sheet_capex.html / inputs_section.html | engine: IDC fixed-point iteration (domain/capex/idc.py) |
| `capex_bank_fees_keur (C.17)` | sheet_capex.html / inputs_section.html | template: Excel/factory anchor, frozen per project |
| `capex_commitment_fees_keur (C.17)` | sheet_capex.html | template: Excel/factory anchor |
| `capex_vat_costs_keur (C.17)` | sheet_capex.html | template: Excel/factory anchor (Oborovo calibration) |
| `capex_reserve_accounts_keur (C.18)` | sheet_capex.html | engine: DSRA funding from waterfall |
| `opex_contingencies_y1_keur (B.13)` | sheet_opex.html | derived_ui: contingency % × non-contingency OPEX |
| `FS/Debt runtime outputs` | sheet_financials.html / sheet_senior_debt.html | runtime_output: WaterfallResult periods via sessionStorage |

### TEMPLATE_LOCKED — Template-set, not user-changeable

| Field | Location | Template source |
|-------|----------|-----------------|
| `project_type` | inputs_section.html | Set at project creation from factory template; frozen thereafter |
| `bank_fees_keur`, `commitment_fees_keur`, `other_financial_keur`, `vat_costs_keur` | C.17 CAPEX | Excel-extracted calibration constants from TUHO / Oborovo workbooks |

