"""Read-only project context builders for UI binding.

Reads from factory defaults or generic project factories.
Does NOT run model calculations.
Does NOT persist anything.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from app.project_factories import (
    create_default_oborovo,
    create_default_solar_project,
    create_default_tuho_wind1,
    create_default_wind_project,
)


MISSING = "MISSING"
NOT_AVAILABLE = "NOT_AVAILABLE"


@dataclass(frozen=True)
class ProjectContext:
    """Read-only UI context for one project."""

    code: str
    name: str
    company: str
    country_iso: str
    technology: str
    capacity_mw: float
    cod_date: str
    financial_close: str
    construction_months: int
    horizon_years: int
    period_frequency: str
    yield_scenario: str
    operating_hours_p50: float
    plant_availability: float
    grid_availability: float
    pv_degradation: float | None
    ppa_tariff_eur_mwh: float
    ppa_term_years: int
    ppa_index_pct: float
    co2_enabled: bool
    co2_price_eur_mwh: float | None
    opex_items: tuple[dict[str, Any], ...]
    opex_y1_total_keur: float
    opex_contingency_method: str
    opex_contingency_pct: float
    total_capex_keur: float
    epc_contract_keur: float
    idc_keur: float
    bank_fees_keur: float
    senior_debt_keur: float
    interest_rate_pct: float
    senior_tenor_years: int
    target_dscr: float
    gearing_pct: float | None
    shl_amount_keur: float
    shl_rate_pct: float
    shl_idc_keur: float
    cit_rate_pct: float
    loss_carryforward_years: int
    g20_status: str
    r99_r102_status: str
    parity_status: str
    data_source: str
    missing_fields: tuple[str, ...]

    @property
    def id(self) -> str:
        return self.code.lower()


def _build_opex_items(project_inputs) -> tuple[dict[str, Any], ...]:
    items = []
    for item in project_inputs.opex:
        items.append(
            {
                "name": item.name,
                "y1_keur": item.y1_amount_keur,
                "inflation_pct": item.annual_inflation,
            }
        )
    return tuple(items)


def _opex_y1_total(project_inputs) -> float:
    return sum(item.y1_amount_keur for item in project_inputs.opex)


def _build_context_from_project_inputs(
    project_inputs,
    *,
    code: str,
    technology: str,
    opex_contingency_method: str,
    opex_contingency_pct: float,
    parity_status: str,
    data_source: str,
) -> ProjectContext:
    opex_items = _build_opex_items(project_inputs)
    financing = project_inputs.financing
    revenue = project_inputs.revenue
    technical = project_inputs.technical
    capex = project_inputs.capex
    tax = project_inputs.tax
    return ProjectContext(
        code=code,
        name=project_inputs.info.name,
        company=project_inputs.info.company,
        country_iso=project_inputs.info.country_iso,
        technology=technology,
        capacity_mw=technical.capacity_mw,
        cod_date=str(project_inputs.info.cod_date),
        financial_close=str(project_inputs.info.financial_close),
        construction_months=project_inputs.info.construction_months,
        horizon_years=project_inputs.info.horizon_years,
        period_frequency=project_inputs.info.period_frequency.value,
        yield_scenario=technical.yield_scenario,
        operating_hours_p50=technical.operating_hours_p50,
        plant_availability=technical.plant_availability,
        grid_availability=technical.grid_availability,
        pv_degradation=technical.pv_degradation if technology != "Wind" else None,
        ppa_tariff_eur_mwh=revenue.ppa_base_tariff,
        ppa_term_years=int(revenue.ppa_term_years),
        ppa_index_pct=revenue.ppa_index,
        co2_enabled=revenue.co2_enabled,
        co2_price_eur_mwh=(
            getattr(revenue, "co2_certificate_price_eur_per_mwh", None)
            or getattr(revenue, "co2_price_eur", None)
        ),
        opex_items=opex_items,
        opex_y1_total_keur=_opex_y1_total(project_inputs),
        opex_contingency_method=opex_contingency_method,
        opex_contingency_pct=opex_contingency_pct,
        total_capex_keur=capex.total_capex,
        epc_contract_keur=capex.epc_contract.amount_keur,
        idc_keur=capex.idc_keur,
        bank_fees_keur=capex.bank_fees_keur,
        senior_debt_keur=financing.fixed_debt_keur,
        interest_rate_pct=financing.base_rate + financing.margin_bps / 10_000,
        senior_tenor_years=financing.senior_tenor_years,
        target_dscr=financing.target_dscr,
        gearing_pct=getattr(financing, "gearing_ratio", None),
        shl_amount_keur=financing.shl_amount_keur,
        shl_rate_pct=financing.shl_rate,
        shl_idc_keur=financing.shl_idc_keur,
        cit_rate_pct=tax.corporate_rate,
        loss_carryforward_years=tax.loss_carryforward_years,
        g20_status="BLOCKED",
        r99_r102_status="NOT APPROVED",
        parity_status=parity_status,
        data_source=data_source,
        missing_fields=(),
    )


def _build_tuho_context() -> ProjectContext:
    return _build_context_from_project_inputs(
        create_default_tuho_wind1(),
        code="TUHO",
        technology="Wind",
        opex_contingency_method="percentage_of_opex",
        opex_contingency_pct=6.0,
        parity_status="AUDIT",
        data_source="Factory context - read-only template data",
    )


def _build_oborovo_context() -> ProjectContext:
    return _build_context_from_project_inputs(
        create_default_oborovo(),
        code="OBOROVO",
        technology="Solar PV",
        opex_contingency_method="fixed_amount",
        opex_contingency_pct=2.0,
        parity_status="CONVENTION",
        data_source="Factory context - read-only template data",
    )


def _build_generic_wind_context() -> ProjectContext:
    return _build_context_from_project_inputs(
        create_default_wind_project(),
        code="GENERIC_WIND",
        technology="Wind",
        opex_contingency_method="percentage_of_opex",
        opex_contingency_pct=0.0,
        parity_status="ACCEPTED_CONVENTION",
        data_source="Generic wind template - user-project starter defaults",
    )


def _build_generic_solar_context() -> ProjectContext:
    return _build_context_from_project_inputs(
        create_default_solar_project(),
        code="GENERIC_SOLAR",
        technology="Solar PV",
        opex_contingency_method="percentage_of_opex",
        opex_contingency_pct=0.0,
        parity_status="ACCEPTED_CONVENTION",
        data_source="Generic solar template - user-project starter defaults",
    )


_CONTEXTS: dict[str, ProjectContext] = {
    "tuho": _build_tuho_context(),
    "oborovo": _build_oborovo_context(),
    "generic_wind": _build_generic_wind_context(),
    "generic_solar": _build_generic_solar_context(),
}


def get_project_context(project_id: str | None) -> ProjectContext:
    if project_id and project_id.lower() in _CONTEXTS:
        return _CONTEXTS[project_id.lower()]
    return _CONTEXTS["tuho"]


def _snapshot_float(snapshot: dict[str, Any], key: str, default: float) -> float:
    value = snapshot.get(key)
    if value in (None, "", NOT_AVAILABLE, MISSING):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _snapshot_int(snapshot: dict[str, Any], key: str, default: int) -> int:
    value = snapshot.get(key)
    if value in (None, "", NOT_AVAILABLE, MISSING):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _scaled_opex_items(base_items: tuple[dict[str, Any], ...], target_total: float) -> tuple[dict[str, Any], ...]:
    if not base_items:
        return base_items
    current_total = sum(float(item.get("y1_keur", 0.0) or 0.0) for item in base_items)
    if current_total <= 0:
        return base_items
    ratio = target_total / current_total
    return tuple(
        {
            **item,
            "y1_keur": float(item.get("y1_keur", 0.0) or 0.0) * ratio,
        }
        for item in base_items
    )


def build_project_context_for_record(
    *,
    project_code: str,
    project_name: str,
    project_type: str | None,
    project_origin: str,
    template_source: str | None,
    baseline_snapshot: dict[str, Any] | None = None,
) -> ProjectContext:
    seed_key = (template_source or "").strip().lower()
    if seed_key == "tuho":
        base = _CONTEXTS["tuho"]
    elif seed_key == "oborovo":
        base = _CONTEXTS["oborovo"]
    elif (project_type or "").strip().lower() == "solar":
        base = _CONTEXTS["generic_solar"]
    else:
        base = _CONTEXTS["generic_wind"]

    if project_origin == "factory_template":
        return base

    snapshot = dict(baseline_snapshot or {})
    resolved_project_type = (snapshot.get("project_type") or project_type or "").strip().lower()
    technology = "Solar PV" if resolved_project_type == "solar" else "Wind"
    capacity_mw = _snapshot_float(snapshot, "capacity_mw", base.capacity_mw)
    operating_hours_p50 = _snapshot_float(snapshot, "p50_hours", base.operating_hours_p50)
    opex_y1_total_keur = _snapshot_float(snapshot, "opex_y1_keur", base.opex_y1_total_keur)
    total_capex_keur = _snapshot_float(snapshot, "total_capex_keur", base.total_capex_keur)
    target_dscr = _snapshot_float(snapshot, "target_dscr", base.target_dscr)
    interest_rate_fraction = _snapshot_float(snapshot, "interest_rate_pct", base.interest_rate_pct * 100.0) / 100.0
    senior_tenor_years = _snapshot_int(snapshot, "tenor_years", base.senior_tenor_years)
    gearing_ratio = _snapshot_float(
        snapshot,
        "gearing_pct",
        (base.gearing_pct * 100.0) if base.gearing_pct is not None else 0.0,
    ) / 100.0
    country_market = (snapshot.get("country_market") or base.country_iso or "").strip() or base.country_iso
    ppa_term_years = _snapshot_int(snapshot, "ppa_term_years", base.ppa_term_years)
    ppa_tariff_eur_mwh = _snapshot_float(snapshot, "tariff_eur_mwh", base.ppa_tariff_eur_mwh)
    construction_months = _snapshot_int(snapshot, "construction_months", base.construction_months)
    horizon_years = _snapshot_int(snapshot, "horizon_years", base.horizon_years)
    cod_date = (snapshot.get("cod_date") or base.cod_date or "").strip() or base.cod_date
    opex_items = _scaled_opex_items(base.opex_items, opex_y1_total_keur)

    return replace(
        base,
        code=project_code.upper(),
        name=(snapshot.get("project_name") or project_name),
        company="User-created project record",
        country_iso=country_market,
        technology=technology,
        capacity_mw=capacity_mw,
        cod_date=cod_date,
        construction_months=construction_months,
        horizon_years=horizon_years,
        operating_hours_p50=operating_hours_p50,
        ppa_tariff_eur_mwh=ppa_tariff_eur_mwh,
        ppa_term_years=ppa_term_years,
        opex_items=opex_items,
        opex_y1_total_keur=opex_y1_total_keur,
        total_capex_keur=total_capex_keur,
        interest_rate_pct=interest_rate_fraction,
        senior_tenor_years=senior_tenor_years,
        target_dscr=target_dscr,
        gearing_pct=gearing_ratio,
        data_source=(
            "User-created project record - runtime built from saved project assumptions. "
            "Some secondary assumptions still use system defaults until later phases."
        ),
    )


def all_project_ids() -> list[str]:
    return list(_CONTEXTS.keys())
