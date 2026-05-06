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

from dataclasses import replace as dc_replace
from typing import TYPE_CHECKING

from app.input_schema import ProjectInputsSchema

if TYPE_CHECKING:
    from domain.inputs import ProjectInputs


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
        if epc_target > 0:
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