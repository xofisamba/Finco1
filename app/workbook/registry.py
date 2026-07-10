"""
Workbook V2 — canonical field registry.

Builds the singleton `WORKBOOK` (WorkbookSpec) that maps every editable field
in the application to a stable semantic ID.

Semantic ID convention:  <sheet>.<section>.<field>
  e.g.  "project_setup.technical.capacity_mw"
        "capex.C.epc_contract"
        "opex.lines.technical_management"
        "revenue.ppa.base_tariff"
        "debt.senior.gearing_pct"

The legacy snapshot_key mirrors the HTML form `name` attribute used today so
that V2 code can translate between representations without touching the engine.

Import the singleton:
    from app.workbook.registry import WORKBOOK
"""
from __future__ import annotations

from app.workbook.specs import (
    FieldSpec,
    FieldType,
    SectionSpec,
    SheetSpec,
    WorkbookSpec,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _f(
    field_id: str,
    label: str,
    snapshot_key: str,
    field_type: FieldType,
    sheet_id: str,
    section_id: str,
    *,
    unit: str | None = None,
    description: str | None = None,
    editable: bool = True,
    required: bool = False,
    options: tuple[str, ...] = (),
    min_value: float | None = None,
    max_value: float | None = None,
    decimals: int | None = None,
    order: int = 0,
) -> FieldSpec:
    return FieldSpec(
        field_id=field_id,
        label=label,
        snapshot_key=snapshot_key,
        field_type=field_type,
        sheet_id=sheet_id,
        section_id=section_id,
        unit=unit,
        description=description,
        editable=editable,
        required=required,
        options=options,
        min_value=min_value,
        max_value=max_value,
        decimals=decimals,
        order=order,
    )


def _section(section_id: str, label: str, sheet_id: str, fields: list[FieldSpec], order: int = 0) -> SectionSpec:
    return SectionSpec(
        section_id=section_id,
        label=label,
        sheet_id=sheet_id,
        order=order,
        fields=tuple(fields),
    )


def _sheet(sheet_id: str, label: str, sections: list[SectionSpec], icon: str | None = None, order: int = 0) -> SheetSpec:
    return SheetSpec(
        sheet_id=sheet_id,
        label=label,
        icon=icon,
        order=order,
        sections=tuple(sections),
    )


# ---------------------------------------------------------------------------
# Sheet: project_setup
# ---------------------------------------------------------------------------

_PS = "project_setup"
_ps_identity = _section("identity", "Project Identity", _PS, order=0, fields=[
    _f(f"{_PS}.identity.project_name",    "Project Name",    "project_name",    FieldType.TEXT,   _PS, "identity", required=True, order=0),
    _f(f"{_PS}.identity.project_type",    "Project Type",    "project_type",    FieldType.SELECT, _PS, "identity",
       options=("wind_onshore", "solar_pv", "bess", "hydro", "gas"), required=True, order=1),
    _f(f"{_PS}.identity.country_market",  "Country / Market","country_market",  FieldType.TEXT,   _PS, "identity", order=2),
    _f(f"{_PS}.identity.currency",        "Currency",        "currency",        FieldType.SELECT, _PS, "identity",
       options=("EUR", "USD", "GBP", "HRK", "PLN", "RON"), order=3),
    _f(f"{_PS}.identity.scenario",        "Scenario",        "scenario",        FieldType.TEXT,   _PS, "identity", order=4),
])

_ps_technical = _section("technical", "Technical Parameters", _PS, order=1, fields=[
    _f(f"{_PS}.technical.capacity_mw",        "Installed Capacity",     "capacity_mw",        FieldType.MW,    _PS, "technical", unit="MW",     required=True,  min_value=0.1,  decimals=2, order=0),
    _f(f"{_PS}.technical.p50_hours",           "P50 Operating Hours",    "p50_hours",           FieldType.MWH,   _PS, "technical", unit="h/yr",   required=True,  min_value=1,    decimals=0, order=1),
    _f(f"{_PS}.technical.capacity_factor",     "Capacity Factor",        "capacity_factor",     FieldType.FLOAT, _PS, "technical", unit="%",      decimals=1,     min_value=0,    max_value=100, order=2),
    _f(f"{_PS}.technical.cod_date",            "Commercial Operation Date","cod_date",           FieldType.DATE,  _PS, "technical", required=True,  order=3),
    _f(f"{_PS}.technical.construction_months", "Construction Duration",  "construction_months", FieldType.MONTHS,_PS, "technical", unit="months", required=True, min_value=1, max_value=120, order=4),
    _f(f"{_PS}.technical.horizon_years",       "Project Horizon",        "horizon_years",       FieldType.YEARS, _PS, "technical", unit="years",  required=True,  min_value=1,    max_value=50, order=5),
])

_SHEET_PROJECT_SETUP = _sheet(_PS, "Project Setup", [_ps_identity, _ps_technical], icon="⚙️", order=0)


# ---------------------------------------------------------------------------
# Sheet: capex
# ---------------------------------------------------------------------------

_CX = "capex"
_cx_group_c = _section("C", "Construction & EPC", _CX, order=0, fields=[
    _f(f"{_CX}.C.epc_contract",        "EPC Contract",             "capex_epc_contract_keur",         FieldType.KEUR, _CX, "C", unit="kEUR", decimals=0, order=0),
    _f(f"{_CX}.C.production_units",    "Production Units",         "capex_production_units_keur",     FieldType.KEUR, _CX, "C", unit="kEUR", decimals=0, order=1),
    _f(f"{_CX}.C.epc_other",           "EPC Other",                "capex_epc_other_keur",            FieldType.KEUR, _CX, "C", unit="kEUR", decimals=0, order=2),
    _f(f"{_CX}.C.grid_connection",     "Grid Connection",          "capex_grid_connection_keur",      FieldType.KEUR, _CX, "C", unit="kEUR", decimals=0, order=3),
    _f(f"{_CX}.C.ops_preparation",     "Operations Preparation",   "capex_ops_prep_keur",             FieldType.KEUR, _CX, "C", unit="kEUR", decimals=0, order=4),
    _f(f"{_CX}.C.insurances",          "Insurances",               "capex_insurances_keur",           FieldType.KEUR, _CX, "C", unit="kEUR", decimals=0, order=5),
    _f(f"{_CX}.C.lease_tax",           "Lease & Tax",              "capex_lease_tax_keur",            FieldType.KEUR, _CX, "C", unit="kEUR", decimals=0, order=6),
    _f(f"{_CX}.C.construction_mgmt_a", "Construction Management A","capex_construction_mgmt_a_keur",  FieldType.KEUR, _CX, "C", unit="kEUR", decimals=0, order=7),
    _f(f"{_CX}.C.commissioning",       "Commissioning",            "capex_commissioning_keur",        FieldType.KEUR, _CX, "C", unit="kEUR", decimals=0, order=8),
    _f(f"{_CX}.C.contingencies",       "Contingencies",            "capex_contingencies_keur",        FieldType.KEUR, _CX, "C", unit="kEUR", decimals=0, order=9),
    _f(f"{_CX}.C.taxes",               "Taxes",                    "capex_taxes_keur",                FieldType.KEUR, _CX, "C", unit="kEUR", decimals=0, order=10),
])

_cx_group_d = _section("D", "Development", _CX, order=1, fields=[
    _f(f"{_CX}.D.project_acquisition", "Project Acquisition",      "capex_project_acquisition_keur",  FieldType.KEUR, _CX, "D", unit="kEUR", decimals=0, order=0),
    _f(f"{_CX}.D.project_rights",      "Project Rights",           "capex_project_rights_keur",       FieldType.KEUR, _CX, "D", unit="kEUR", decimals=0, order=1),
    _f(f"{_CX}.D.audit_legal",         "Audit & Legal",            "capex_audit_legal_keur",          FieldType.KEUR, _CX, "D", unit="kEUR", decimals=0, order=2),
    _f(f"{_CX}.D.construction_mgmt_b", "Construction Management B","capex_construction_mgmt_b_keur",  FieldType.KEUR, _CX, "D", unit="kEUR", decimals=0, order=3),
])

_cx_group_f = _section("F", "Financing Costs", _CX, order=2, fields=[
    _f(f"{_CX}.F.idc",                "IDC",                       "capex_idc_keur",                  FieldType.KEUR, _CX, "F", unit="kEUR", decimals=0, order=0),
    _f(f"{_CX}.F.bank_fees",          "Bank Fees",                 "capex_bank_fees_keur",            FieldType.KEUR, _CX, "F", unit="kEUR", decimals=0, order=1),
    _f(f"{_CX}.F.commitment_fees",    "Commitment Fees",           "capex_commitment_fees_keur",      FieldType.KEUR, _CX, "F", unit="kEUR", decimals=0, order=2),
    _f(f"{_CX}.F.other_financial",    "Other Financial",           "capex_other_financial_keur",      FieldType.KEUR, _CX, "F", unit="kEUR", decimals=0, order=3),
    _f(f"{_CX}.F.vat_costs",          "VAT / Recoverable Costs",  "capex_vat_costs_keur",            FieldType.KEUR, _CX, "F", unit="kEUR", decimals=0, order=4),
    _f(f"{_CX}.F.reserve_accounts",   "Reserve Accounts",         "capex_reserve_accounts_keur",     FieldType.KEUR, _CX, "F", unit="kEUR", decimals=0, order=5),
])

_cx_summary = _section("summary", "CAPEX Summary", _CX, order=3, fields=[
    _f(f"{_CX}.summary.total",        "Total CAPEX",               "total_capex_keur",                FieldType.KEUR, _CX, "summary", unit="kEUR", decimals=0, editable=False, order=0),
])

_SHEET_CAPEX = _sheet(_CX, "CAPEX", [_cx_group_c, _cx_group_d, _cx_group_f, _cx_summary], icon="🏗️", order=1)


# ---------------------------------------------------------------------------
# Sheet: opex
# ---------------------------------------------------------------------------

_OX = "opex"
_ox_lines = _section("lines", "OPEX Line Items", _OX, order=0, fields=[
    _f(f"{_OX}.lines.technical_management",  "Technical Management",              "opex_technical_management_y1_keur",                          FieldType.KEUR, _OX, "lines", unit="kEUR/yr", decimals=0, order=0),
    _f(f"{_OX}.lines.om_preventive",         "O&M Preventive & Corrective",       "opex_o_and_m_preventive_and_corrective_y1_keur",             FieldType.KEUR, _OX, "lines", unit="kEUR/yr", decimals=0, order=1),
    _f(f"{_OX}.lines.site_maintenance",      "Site Maintenance",                  "opex_maintain_site_y1_keur",                                 FieldType.KEUR, _OX, "lines", unit="kEUR/yr", decimals=0, order=2),
    _f(f"{_OX}.lines.cleaning_materials",    "Cleaning & Materials",              "opex_clean_material_y1_keur",                                FieldType.KEUR, _OX, "lines", unit="kEUR/yr", decimals=0, order=3),
    _f(f"{_OX}.lines.security",              "Security",                          "opex_security_y1_keur",                                      FieldType.KEUR, _OX, "lines", unit="kEUR/yr", decimals=0, order=4),
    _f(f"{_OX}.lines.insurance",             "Insurance",                         "opex_insurance_y1_keur",                                     FieldType.KEUR, _OX, "lines", unit="kEUR/yr", decimals=0, order=5),
    _f(f"{_OX}.lines.lease_property_tax",    "Lease & Property Tax",              "opex_lease_and_property_tax_y1_keur",                        FieldType.KEUR, _OX, "lines", unit="kEUR/yr", decimals=0, order=6),
    _f(f"{_OX}.lines.power_expenses",        "Power Expenses",                    "opex_power_expenses_y1_keur",                                FieldType.KEUR, _OX, "lines", unit="kEUR/yr", decimals=0, order=7),
    _f(f"{_OX}.lines.audit_accounting_legal","Audit, Accounting & Legal",         "opex_audit_and_accounting_and_legal_y1_keur",                FieldType.KEUR, _OX, "lines", unit="kEUR/yr", decimals=0, order=8),
    _f(f"{_OX}.lines.bank_fees",             "Bank Fees (OPEX)",                  "opex_bank_fees_opex_y1_keur",                                FieldType.KEUR, _OX, "lines", unit="kEUR/yr", decimals=0, order=9),
    _f(f"{_OX}.lines.environmental_social",  "Environmental & Social Management", "opex_environmental_and_social_management_y1_keur",           FieldType.KEUR, _OX, "lines", unit="kEUR/yr", decimals=0, order=10),
    _f(f"{_OX}.lines.contingencies",         "Contingencies",                     "opex_contingencies_y1_keur",                                 FieldType.KEUR, _OX, "lines", unit="kEUR/yr", decimals=0, order=11),
])

_ox_summary = _section("summary", "OPEX Summary", _OX, order=1, fields=[
    _f(f"{_OX}.summary.total_y1",    "Total OPEX Y1",         "opex_y1_keur",     FieldType.KEUR, _OX, "summary", unit="kEUR/yr", decimals=0, editable=False, order=0),
])

_SHEET_OPEX = _sheet(_OX, "OPEX", [_ox_lines, _ox_summary], icon="🔧", order=2)


# ---------------------------------------------------------------------------
# Sheet: revenue
# ---------------------------------------------------------------------------

_RV = "revenue"
_rv_ppa = _section("ppa", "PPA / Tariff", _RV, order=0, fields=[
    _f(f"{_RV}.ppa.base_tariff",       "Base Tariff",         "rev_ppa_base_tariff",      FieldType.FLOAT, _RV, "ppa", unit="EUR/MWh", required=True, min_value=0, decimals=2, order=0),
    _f(f"{_RV}.ppa.index",             "PPA Index",           "rev_ppa_index",            FieldType.FLOAT, _RV, "ppa", unit="%/yr",   decimals=2, order=1),
    _f(f"{_RV}.ppa.term_years",        "PPA Term",            "rev_ppa_term_years",       FieldType.YEARS, _RV, "ppa", unit="years",   min_value=1, max_value=50, order=2),
    _f(f"{_RV}.ppa.production_share",  "Production Share",    "rev_ppa_production_share", FieldType.FLOAT, _RV, "ppa", unit="%",       decimals=1, min_value=0, max_value=100, order=3),
    # legacy alias (also used in snapshot)
    _f(f"{_RV}.ppa.tariff_legacy",     "Tariff (legacy)",     "tariff_eur_mwh",           FieldType.FLOAT, _RV, "ppa", unit="EUR/MWh", editable=False, order=4),
    _f(f"{_RV}.ppa.term_legacy",       "PPA Term (legacy)",   "ppa_term_years",           FieldType.YEARS, _RV, "ppa", editable=False, order=5),
])

_rv_balancing = _section("balancing", "Balancing & CO2", _RV, order=1, fields=[
    _f(f"{_RV}.balancing.cost",        "Balancing Cost",      "rev_balancing_cost",       FieldType.FLOAT, _RV, "balancing", unit="EUR/MWh", decimals=2, order=0),
    _f(f"{_RV}.balancing.co2_enabled", "CO2 Revenue Enabled", "rev_co2_enabled",          FieldType.BOOL,  _RV, "balancing", order=1),
    _f(f"{_RV}.balancing.co2_price",   "CO2 Price",           "rev_co2_price",            FieldType.FLOAT, _RV, "balancing", unit="EUR/tCO2", decimals=2, order=2),
])

_SHEET_REVENUE = _sheet(_RV, "Revenue", [_rv_ppa, _rv_balancing], icon="💰", order=3)


# ---------------------------------------------------------------------------
# Sheet: debt  (senior_debt tab)
# ---------------------------------------------------------------------------

_DT = "debt"
_dt_senior = _section("senior", "Senior Debt", _DT, order=0, fields=[
    _f(f"{_DT}.senior.gearing_pct",      "Gearing",             "gearing_pct",         FieldType.PCT,   _DT, "senior", unit="%",     min_value=0,   max_value=100, decimals=1, order=0),
    _f(f"{_DT}.senior.target_dscr",      "Target DSCR",         "target_dscr",         FieldType.FLOAT, _DT, "senior", unit="x",     min_value=1.0, max_value=3.0, decimals=2, order=1),
    _f(f"{_DT}.senior.interest_rate_pct","All-in Interest Rate", "interest_rate_pct",   FieldType.PCT,   _DT, "senior", unit="%",     min_value=0,   max_value=20,  decimals=2, order=2),
    _f(f"{_DT}.senior.tenor_years",      "Tenor",               "tenor_years",         FieldType.YEARS, _DT, "senior", unit="years", min_value=1,   max_value=30,  order=3),
])

_SHEET_DEBT = _sheet(_DT, "Senior Debt", [_dt_senior], icon="🏦", order=4)


# ---------------------------------------------------------------------------
# Build the singleton
# ---------------------------------------------------------------------------

WORKBOOK = WorkbookSpec(
    version="2.0.0",
    sheets=(
        _SHEET_PROJECT_SETUP,
        _SHEET_CAPEX,
        _SHEET_OPEX,
        _SHEET_REVENUE,
        _SHEET_DEBT,
    ),
)
