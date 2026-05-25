"""Read-only project context builders for UI binding — Phase 9.5.

Reads from existing factory defaults.
Does NOT run model calculations.
Does NOT persist anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.project_factories import create_default_tuho_wind1, create_default_oborovo


# Sentinel for unavailable values
MISSING = "MISSING"
NOT_AVAILABLE = "NOT_AVAILABLE"


@dataclass(frozen=True)
class ProjectContext:
    """Read-only UI context for one project."""

    code: str                       # "TUHO" | "OBOROVO"
    name: str
    company: str
    country_iso: str
    technology: str                 # "Wind" | "Solar PV"
    capacity_mw: float
    cod_date: str
    financial_close: str
    construction_months: int
    horizon_years: int
    period_frequency: str           # "SEMESTRIAL"

    # Technical
    yield_scenario: str
    operating_hours_p50: float
    plant_availability: float
    grid_availability: float
    pv_degradation: float | None    # None for wind

    # Revenue
    ppa_tariff_eur_mwh: float
    ppa_term_years: int
    ppa_index_pct: float
    co2_enabled: bool
    co2_price_eur_mwh: float | None

    # OPEX
    opex_items: tuple[dict[str, Any], ...]   # list of {name, y1_keur, inflation_pct}
    opex_y1_total_keur: float
    opex_contingency_method: str              # "percentage_of_opex" | "fixed_amount"
    opex_contingency_pct: float

    # CAPEX
    total_capex_keur: float
    epc_contract_keur: float
    idc_keur: float
    bank_fees_keur: float

    # Senior Debt
    senior_debt_keur: float
    interest_rate_pct: float
    senior_tenor_years: int
    target_dscr: float
    gearing_pct: float | None

    # SHL
    shl_amount_keur: float
    shl_rate_pct: float
    shl_idc_keur: float

    # Tax
    cit_rate_pct: float
    loss_carryforward_years: int

    # Governance / Status
    g20_status: str               # "BLOCKED" | "APPROVED"
    r99_r102_status: str           # "NOT APPROVED" | "APPROVED"
    parity_status: str             # "CONVENTION" | "AUDIT" | "MISSING_EVIDENCE"

    # UI badges
    data_source: str               # "Factory context — read-only template data"
    missing_fields: tuple[str, ...]

    @property
    def id(self) -> str:
        return self.code.lower()   # "tuho" | "oborovo"


def _pct(v: float) -> str:
    return f"{v * 100:.2f}%"


def _fmt_keur(v: float) -> str:
    return f"{v:,.0f}"


def _build_opex_items(pi) -> tuple[dict[str, Any], ...]:
    """Extract OPEX items from ProjectInputs opex tuple."""
    items = []
    for item in pi.opex:
        items.append({
            "name": item.name,
            "y1_keur": item.y1_amount_keur,
            "inflation_pct": item.annual_inflation,
        })
    return tuple(items)


def _opex_y1_total(pi) -> float:
    return sum(item.y1_amount_keur for item in pi.opex)


def _build_tuho_context() -> ProjectContext:
    pi = create_default_tuho_wind1()
    opex_items = _build_opex_items(pi)
    return ProjectContext(
        code="TUHO",
        name=pi.info.name,
        company=pi.info.company,
        country_iso=pi.info.country_iso,
        technology="Wind",
        capacity_mw=pi.technical.capacity_mw,
        cod_date=str(pi.info.cod_date),
        financial_close=str(pi.info.financial_close),
        construction_months=pi.info.construction_months,
        horizon_years=pi.info.horizon_years,
        period_frequency=pi.info.period_frequency.value,
        yield_scenario=pi.technical.yield_scenario,
        operating_hours_p50=pi.technical.operating_hours_p50,
        plant_availability=pi.technical.plant_availability,
        grid_availability=pi.technical.grid_availability,
        pv_degradation=None,
        ppa_tariff_eur_mwh=pi.revenue.ppa_base_tariff,
        ppa_term_years=int(pi.revenue.ppa_term_years),
        ppa_index_pct=pi.revenue.ppa_index,
        co2_enabled=pi.revenue.co2_enabled,
        co2_price_eur_mwh=pi.revenue.co2_certificate_price_eur_per_mwh,
        opex_items=opex_items,
        opex_y1_total_keur=_opex_y1_total(pi),
        opex_contingency_method="percentage_of_opex",   # Phase 9.5 fix
        opex_contingency_pct=6.0,
        total_capex_keur=pi.capex.total_capex,
        epc_contract_keur=pi.capex.epc_contract.amount_keur,
        idc_keur=pi.capex.idc_keur,
        bank_fees_keur=pi.capex.bank_fees_keur,
        senior_debt_keur=pi.financing.fixed_debt_keur,
        interest_rate_pct=pi.financing.base_rate + pi.financing.margin_bps / 10_000,
        senior_tenor_years=pi.financing.senior_tenor_years,
        target_dscr=pi.financing.target_dscr,
        gearing_pct=None,
        shl_amount_keur=pi.financing.shl_amount_keur,
        shl_rate_pct=pi.financing.shl_rate,
        shl_idc_keur=pi.financing.shl_idc_keur,
        cit_rate_pct=pi.tax.corporate_rate,
        loss_carryforward_years=pi.tax.loss_carryforward_years,
        g20_status="BLOCKED",
        r99_r102_status="NOT APPROVED",
        parity_status="AUDIT",
        data_source="Project workspace",
        missing_fields=(),
    )


def _build_oborovo_context() -> ProjectContext:
    pi = create_default_oborovo()
    opex_items = _build_opex_items(pi)
    return ProjectContext(
        code="OBOROVO",
        name=pi.info.name,
        company=pi.info.company,
        country_iso=pi.info.country_iso,
        technology="Solar PV",
        capacity_mw=pi.technical.capacity_mw,
        cod_date=str(pi.info.cod_date),
        financial_close=str(pi.info.financial_close),
        construction_months=pi.info.construction_months,
        horizon_years=pi.info.horizon_years,
        period_frequency=pi.info.period_frequency.value,
        yield_scenario=pi.technical.yield_scenario,
        operating_hours_p50=pi.technical.operating_hours_p50,
        plant_availability=pi.technical.plant_availability,
        grid_availability=pi.technical.grid_availability,
        pv_degradation=pi.technical.pv_degradation,
        ppa_tariff_eur_mwh=pi.revenue.ppa_base_tariff,
        ppa_term_years=int(pi.revenue.ppa_term_years),
        ppa_index_pct=pi.revenue.ppa_index,
        co2_enabled=pi.revenue.co2_enabled,
        co2_price_eur_mwh=pi.revenue.co2_certificate_price_eur_per_mwh,
        opex_items=opex_items,
        opex_y1_total_keur=_opex_y1_total(pi),
        opex_contingency_method="fixed_amount",   # Oborovo still uses legacy fixed-amount contingency
        opex_contingency_pct=2.0,                # Note: 2% is legacy — not yet fixed
        total_capex_keur=pi.capex.total_capex,
        epc_contract_keur=pi.capex.epc_contract.amount_keur,
        idc_keur=pi.capex.idc_keur,
        bank_fees_keur=pi.capex.bank_fees_keur,
        senior_debt_keur=pi.financing.fixed_debt_keur,
        interest_rate_pct=pi.financing.base_rate + pi.financing.margin_bps / 10_000,
        senior_tenor_years=pi.financing.senior_tenor_years,
        target_dscr=pi.financing.target_dscr,
        gearing_pct=getattr(pi.financing, "gearing_ratio", None),
        shl_amount_keur=pi.financing.shl_amount_keur,
        shl_rate_pct=pi.financing.shl_rate,
        shl_idc_keur=pi.financing.shl_idc_keur,
        cit_rate_pct=pi.tax.corporate_rate,
        loss_carryforward_years=pi.tax.loss_carryforward_years,
        g20_status="BLOCKED",
        r99_r102_status="NOT APPROVED",
        parity_status="CONVENTION",
        data_source="Project workspace",
        missing_fields=(),
    )


_Contexts: dict[str, ProjectContext] = {
    "tuho": _build_tuho_context(),
    "oborovo": _build_oborovo_context(),
}


def get_project_context(project_id: str | None) -> ProjectContext:
    """Return context for project_id ('tuho' | 'oborovo') or default to TUHO."""
    if project_id and project_id.lower() in _Contexts:
        return _Contexts[project_id.lower()]
    return _Contexts["tuho"]


def all_project_ids() -> list[str]:
    return list(_Contexts.keys())
