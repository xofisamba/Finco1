"""Convert ProjectInputsSchema (DTO) into domain ProjectInputs.

Architecture:
  JSON/YAML/API request
       ↓
  ProjectInputsSchema (validation only — no business logic)
       ↓
  input_adapter.build_projectinputs()
       ↓
  existing domain ProjectInputs  (frozen dataclass)
       ↓
  run_demo_project(project_inputs_override=...)

This is a pure adapter — it applies only the overrides specified in the schema,
leaving all other factory defaults intact.
"""
from __future__ import annotations

from calendar import monthrange
from dataclasses import replace as dc_replace
from datetime import date
from typing import TYPE_CHECKING

from app.input_schema import ProjectInputsSchema

if TYPE_CHECKING:
    from domain.inputs import ProjectInputs


class SnapshotInputError(ValueError):
    """Raised when a saved user-project snapshot cannot build runtime inputs."""


# Map of domain field paths → (getter, setter) for clean replacement
# Each setter takes (parent_obj, value) → new parent_obj with value applied


def _set_technical_capacity(proj: "ProjectInputs", value: float) -> "ProjectInputs":
    return dc_replace(proj, technical=dc_replace(proj.technical, capacity_mw=value))


def _set_technical_p50_hours(proj: "ProjectInputs", value: float) -> "ProjectInputs":
    return dc_replace(proj, technical=dc_replace(proj.technical, operating_hours_p50=value))


def _set_technical_degradation(proj: "ProjectInputs", value: float) -> "ProjectInputs":
    return dc_replace(proj, technical=dc_replace(proj.technical, pv_degradation=value))


def _set_revenue_tariff(proj: "ProjectInputs", value: float) -> "ProjectInputs":
    return dc_replace(proj, revenue=dc_replace(proj.revenue, ppa_base_tariff=value))


def _set_opex_inflation(proj: "ProjectInputs", value: float) -> "ProjectInputs":
    """Set annual_inflation on all existing OPEX line items."""
    new_items = tuple(
        dc_replace(item, annual_inflation=value) for item in proj.opex
    )
    return dc_replace(proj, opex=new_items)


def _set_financing_gearing(proj: "ProjectInputs", value: float) -> "ProjectInputs":
    # schema passes gearing as 0-100, domain uses 0.0-1.0
    return dc_replace(proj, financing=dc_replace(proj.financing, gearing_ratio=value / 100.0))


def _set_financing_senior_debt(proj: "ProjectInputs", value: float) -> "ProjectInputs":
    return dc_replace(proj, financing=dc_replace(proj.financing, senior_debt_amount_keur=value))


def _set_financing_interest_rate(proj: "ProjectInputs", value: float) -> "ProjectInputs":
    """Set all-in interest rate by adjusting margin_bps, keeping base_rate fixed."""
    base_rate = proj.financing.base_rate
    all_in = value / 100.0
    margin_bps = int(round((all_in - base_rate) * 10_000))
    margin_bps = max(0, margin_bps)
    return dc_replace(proj, financing=dc_replace(proj.financing, margin_bps=margin_bps))


def _set_financing_tenor(proj: "ProjectInputs", value: int) -> "ProjectInputs":
    return dc_replace(proj, financing=dc_replace(proj.financing, senior_tenor_years=value))


def _set_financing_target_dscr(proj: "ProjectInputs", value: float) -> "ProjectInputs":
    return dc_replace(proj, financing=dc_replace(proj.financing, target_dscr=value))


def build_projectinputs(schema: ProjectInputsSchema) -> "ProjectInputs":
    """Build a domain ProjectInputs from a ProjectInputsSchema.

    Strategy: start from factory defaults for the project type, then apply
    only the overrides specified in the schema. This preserves all complex
    default logic that the schema doesn't cover.

    Parameters
    ----------
    schema :
        Validated Pydantic schema with optional overrides.

    Returns
    -------
    ProjectInputs
        A frozen domain object suitable for pass-through to run_demo_project().
    """
    from app.project_factories import create_default_solar_project, create_default_wind_project

    factory_map = {
        "Solar": create_default_solar_project,
        "Wind": create_default_wind_project,
    }
    factory = factory_map[schema.project_type]
    proj: "ProjectInputs" = factory()

    # ── Technical ────────────────────────────────────────────────────────────
    if schema.capacity_mw is not None:
        proj = _set_technical_capacity(proj, schema.capacity_mw)

    # ── Revenue ───────────────────────────────────────────────────────────────
    if schema.revenue is not None:
        rev = schema.revenue
        if rev.tariff_eur_mwh is not None:
            proj = _set_revenue_tariff(proj, rev.tariff_eur_mwh)
        if rev.p50_hours is not None:
            proj = _set_technical_p50_hours(proj, rev.p50_hours)
        if rev.degradation_pct is not None:
            # schema is e.g. 0.4%, domain is 0.004
            proj = _set_technical_degradation(proj, rev.degradation_pct / 100.0)

    # ── CAPEX ─────────────────────────────────────────────────────────────────
    if schema.capex is not None and schema.capex.total_capex_keur is not None:
        target = schema.capex.total_capex_keur
        # Scale the epc_contract (Solar Modules) to hit the target,
        # preserving all other capex items at their defaults.
        other_keur = sum(
            getattr(proj.capex, f.name).amount_keur
            for f in proj.capex.__dataclass_fields__.values()
            if f.name not in ("idc_keur", "commitment_fees_keur", "bank_fees_keur",
                              "other_financial_keur", "vat_costs_keur", "reserve_accounts_keur",
                              "epc_contract")
            and getattr(proj.capex, f.name).amount_keur > 0
        )
        epc_target = target - other_keur
        if epc_target <= 0:
            raise ValueError(
                f"total_capex_keur ({target}) must be greater than "
                f"other capex items ({other_keur} keur). "
                f"Cannot allocate to epc_contract. Increase total_capex_keur."
            )
        new_epc = dc_replace(proj.capex.epc_contract, amount_keur=epc_target)
        proj = dc_replace(proj, capex=dc_replace(proj.capex, epc_contract=new_epc))

    # ── OPEX ──────────────────────────────────────────────────────────────────
    if schema.opex is not None:
        op = schema.opex
        if op.inflation_pct is not None:
            proj = _set_opex_inflation(proj, op.inflation_pct / 100.0)
        if op.opex_y1_keur is not None:
            # Scale all existing OPEX line items proportionally to hit target Y1 total.
            old_total = sum(item.y1_amount_keur for item in proj.opex)
            if old_total > 0:
                ratio = op.opex_y1_keur / old_total
                new_items = tuple(
                    dc_replace(item, y1_amount_keur=item.y1_amount_keur * ratio)
                    for item in proj.opex
                )
                proj = dc_replace(proj, opex=new_items)

    # ── Debt / Financing ───────────────────────────────────────────────────────
    if schema.debt is not None:
        db = schema.debt
        if db.gearing_pct is not None:
            proj = _set_financing_gearing(proj, db.gearing_pct)
        if db.senior_debt_keur is not None:
            proj = _set_financing_senior_debt(proj, db.senior_debt_keur)
        if db.interest_rate_pct is not None:
            proj = _set_financing_interest_rate(proj, db.interest_rate_pct)
        if db.tenor_years is not None:
            proj = _set_financing_tenor(proj, db.tenor_years)
        if db.target_dscr is not None:
            proj = _set_financing_target_dscr(proj, db.target_dscr)

    return proj


REQUIRED_USER_PROJECT_SNAPSHOT_FIELDS = (
    "project_name",
    "project_type",
    "country_market",
    "capacity_mw",
    "cod_date",
    "construction_months",
    "horizon_years",
    "tariff_eur_mwh",
    "ppa_term_years",
    "p50_hours",
    "opex_y1_keur",
    "total_capex_keur",
    "gearing_pct",
    "interest_rate_pct",
    "tenor_years",
    "target_dscr",
)


def _snapshot_text(snapshot: dict, key: str) -> str:
    value = snapshot.get(key)
    if value is None or str(value).strip() == "":
        raise SnapshotInputError(f"{key} is required for user-created project runtime")
    return str(value).strip()


def _snapshot_float(
    snapshot: dict,
    key: str,
    *,
    positive: bool = False,
    non_negative: bool = False,
) -> float:
    raw = _snapshot_text(snapshot, key)
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise SnapshotInputError(f"{key} must be numeric for user-created project runtime") from exc
    if positive and value <= 0:
        raise SnapshotInputError(f"{key} must be greater than zero for user-created project runtime")
    if non_negative and value < 0:
        raise SnapshotInputError(f"{key} must be zero or greater for user-created project runtime")
    return value


def _snapshot_int(snapshot: dict, key: str, *, positive: bool = False) -> int:
    value = _snapshot_float(snapshot, key, positive=positive)
    if int(value) != value:
        raise SnapshotInputError(f"{key} must be a whole number for user-created project runtime")
    return int(value)


def _snapshot_date(snapshot: dict, key: str) -> date:
    raw = _snapshot_text(snapshot, key)
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise SnapshotInputError(f"{key} must be an ISO date for user-created project runtime") from exc


def _subtract_months(value: date, months: int) -> date:
    month_index = value.month - months
    year = value.year + (month_index - 1) // 12
    month = (month_index - 1) % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def _country_iso(value: str) -> str:
    normalized = value.strip()
    if normalized.lower() in {"croatia", "hr", "hrv", "hrvatska"}:
        return "HR"
    return normalized.upper()[:2] or "HR"


def build_projectinputs_from_snapshot(snapshot: dict) -> "ProjectInputs":
    """Build runtime inputs for a user-created project from saved assumptions.

    This path is intentionally separate from ``build_projectinputs``: it does
    not start from TUHO, Oborovo, or generic factory defaults. Secondary values
    that Phase 17B does not yet collect are explicit system defaults documented
    in the Phase 17C remaining-gaps report.
    """
    from domain.inputs import (
        AssetClass,
        CapexItem,
        CapexStructure,
        FinancingParams,
        OpexItem,
        PeriodFrequency,
        ProjectInfo,
        ProjectInputs,
        RevenueParams,
        TaxParams,
        TechnicalParams,
    )

    missing = [
        key for key in REQUIRED_USER_PROJECT_SNAPSHOT_FIELDS
        if snapshot.get(key) is None or str(snapshot.get(key)).strip() == ""
    ]
    if missing:
        raise SnapshotInputError(
            "Missing required user-created project runtime fields: " + ", ".join(missing)
        )

    project_type = _snapshot_text(snapshot, "project_type").title()
    if project_type not in {"Solar", "Wind"}:
        raise SnapshotInputError("project_type must be Solar or Wind for user-created project runtime")

    project_name = _snapshot_text(snapshot, "project_name")
    country_market = _snapshot_text(snapshot, "country_market")
    capacity_mw = _snapshot_float(snapshot, "capacity_mw", positive=True)
    cod_date = _snapshot_date(snapshot, "cod_date")
    construction_months = _snapshot_int(snapshot, "construction_months", positive=True)
    horizon_years = _snapshot_int(snapshot, "horizon_years", positive=True)
    tariff_eur_mwh = _snapshot_float(snapshot, "tariff_eur_mwh", non_negative=True)
    ppa_term_years = _snapshot_int(snapshot, "ppa_term_years", positive=True)
    p50_hours = _snapshot_float(snapshot, "p50_hours", positive=True)
    opex_y1_keur = _snapshot_float(snapshot, "opex_y1_keur", non_negative=True)
    total_capex_keur = _snapshot_float(snapshot, "total_capex_keur", positive=True)
    gearing_pct = _snapshot_float(snapshot, "gearing_pct", non_negative=True)
    if gearing_pct > 100:
        raise SnapshotInputError("gearing_pct must be between 0 and 100 for user-created project runtime")
    interest_rate_pct = _snapshot_float(snapshot, "interest_rate_pct", non_negative=True)
    tenor_years = _snapshot_int(snapshot, "tenor_years", positive=True)
    target_dscr = _snapshot_float(snapshot, "target_dscr", positive=True)

    financial_close = _subtract_months(cod_date, construction_months)
    code = (
        str(snapshot.get("active_project") or snapshot.get("project_code") or project_name)
        .strip()
        .upper()
        .replace(" ", "_")
    )
    degradation = 0.004 if project_type == "Solar" else 0.0
    capex_asset = AssetClass.SOLAR_PANELS if project_type == "Solar" else AssetClass.WIND_TURBINES
    senior_debt_keur = total_capex_keur * (gearing_pct / 100.0)

    def capex_item(
        name: str,
        amount_keur: float = 0.0,
        asset_class: AssetClass = AssetClass.CIVIL_GRID,
    ) -> CapexItem:
        return CapexItem(
            name=name,
            amount_keur=amount_keur,
            y0_share=1.0 if amount_keur else 0.0,
            asset_class=asset_class,
        )

    capex = CapexStructure(
        epc_contract=capex_item("User provided total CAPEX", total_capex_keur, capex_asset),
        production_units=capex_item("System default production units"),
        epc_other=capex_item("System default EPC other"),
        grid_connection=capex_item("System default grid connection"),
        ops_prep=capex_item("System default operations preparation"),
        insurances=capex_item("System default insurances"),
        lease_tax=capex_item("System default lease tax"),
        construction_mgmt_a=capex_item("System default construction management A"),
        commissioning=capex_item("System default commissioning"),
        audit_legal=capex_item("System default audit and legal"),
        construction_mgmt_b=capex_item("System default construction management B"),
        contingencies=capex_item("System default contingencies"),
        taxes=capex_item("System default taxes"),
        project_acquisition=capex_item("System default project acquisition"),
        project_rights=capex_item("System default project rights"),
    )

    return ProjectInputs(
        info=ProjectInfo(
            name=project_name,
            company="User-created project record",
            code=code,
            country_iso=_country_iso(country_market),
            financial_close=financial_close,
            construction_months=construction_months,
            cod_date=cod_date,
            horizon_years=horizon_years,
            period_frequency=PeriodFrequency.SEMESTRIAL,
        ),
        technical=TechnicalParams(
            capacity_mw=capacity_mw,
            yield_scenario="P_50",
            operating_hours_p50=p50_hours,
            operating_hours_p90_10y=p50_hours * 0.9,
            operating_hours_p99_1y=p50_hours * 0.8,
            pv_degradation=degradation,
            plant_availability=0.99,
            grid_availability=0.99,
        ),
        capex=capex,
        opex=(
            OpexItem(
                name="User provided year 1 operating expense",
                y1_amount_keur=opex_y1_keur,
                annual_inflation=0.02,
            ),
        ),
        revenue=RevenueParams(
            ppa_base_tariff=tariff_eur_mwh,
            ppa_term_years=ppa_term_years,
            ppa_index=0.02,
            ppa_production_share=1.0,
            market_scenario="Central",
            market_prices_curve=(),
            market_inflation=0.02,
            balancing_cost_eur_per_mwh=0.0,
            co2_enabled=False,
        ),
        financing=FinancingParams(
            share_capital_keur=max(total_capex_keur - senior_debt_keur, 0.0),
            shl_amount_keur=0.0,
            shl_rate=0.0,
            shl_tenor_years=tenor_years,
            gearing_ratio=gearing_pct / 100.0,
            senior_debt_amount_keur=senior_debt_keur,
            senior_tenor_years=tenor_years,
            base_rate=0.0,
            margin_bps=int(round(interest_rate_pct * 100.0)),
            target_dscr=target_dscr,
            debt_sizing_method="gearing_cap",
            fixed_debt_keur=senior_debt_keur,
        ),
        tax=TaxParams(
            corporate_rate=0.10,
            loss_carryforward_years=5,
        ),
    )
