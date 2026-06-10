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


def _set_revenue_ppa_term(proj: "ProjectInputs", value: int) -> "ProjectInputs":
    """Set the PPA term in years on the revenue block."""
    return dc_replace(
        proj,
        revenue=dc_replace(
            proj.revenue,
            ppa_term_years=int(value),
        ),
    )


def _zero_financial_capex_subfields(proj: "ProjectInputs") -> "ProjectInputs":
    """Zero out the financial cost sub-fields on the
    capex structure.

    Phase S1 contract: user-supplied ``total_capex_keur``
    MUST map 1:1 into runtime CAPEX for both the form
    path and the snapshot path. The Generic factory
    defaults populate these financial sub-fields
    (idc, bank_fees, etc.) with non-zero values that
    come from generic financial cost-of-debt
    modelling, NOT from the user's CAPEX input.

    The cleanest way to preserve the user's CAPEX
    intent is to zero these sub-fields. The runtime
    sculpt does not depend on them (it uses
    total_capex - epc_contract_other for sizing).
    """
    return dc_replace(
        proj,
        capex=dc_replace(
            proj.capex,
            idc_keur=0.0,
            commitment_fees_keur=0.0,
            bank_fees_keur=0.0,
            other_financial_keur=0.0,
            vat_costs_keur=0.0,
            reserve_accounts_keur=0.0,
        ),
    )


def _apply_capex_total(proj: "ProjectInputs", target: float) -> "ProjectInputs":
    """Scale the epc_contract to hit a user-supplied
    ``target`` total capex, preserving all other
    capex line items at their defaults.

    If the target is below the sum of the other
    capex line items, the epc_contract is clamped
    to 0.0 (the runtime then sees the factory
    other capex items as the effective CAPEX).
    """
    other_keur = sum(
        getattr(proj.capex, f.name).amount_keur
        for f in proj.capex.__dataclass_fields__.values()
        if f.name not in ("idc_keur", "commitment_fees_keur", "bank_fees_keur",
                          "other_financial_keur", "vat_costs_keur", "reserve_accounts_keur",
                          "epc_contract")
        and getattr(proj.capex, f.name).amount_keur > 0
    )
    epc_target = max(target - other_keur, 0.0)
    new_epc = dc_replace(proj.capex.epc_contract, amount_keur=epc_target)
    return dc_replace(proj, capex=dc_replace(proj.capex, epc_contract=new_epc))


def _resolve_user_inputs(
    *,
    project_type: str,
    project_name: str = None,
    project_code: str = None,
    country_iso: str = None,
    capacity_mw: float = None,
    cod_date: date = None,
    construction_months: int = None,
    horizon_years: int = None,
    tariff_eur_mwh: float = None,
    ppa_term_years: int = None,
    p50_hours: float = None,
    operating_hours_p90_10y: float = None,
    operating_hours_p99_1y: float = None,
    opex_y1_keur: float = None,
    total_capex_keur: float = None,
    gearing_pct: float = None,
    interest_rate_pct: float = None,
    tenor_years: int = None,
    target_dscr: float = None,
) -> "ProjectInputs":
    """Phase S1: shared resolver. Both the form path and the
    snapshot path route through this function. Identical
    input values produce identical ProjectInputs
    regardless of which entry point was used.

    All parameters are optional. ``None`` means "use
    the factory default for the project type".

    The resolver:
    1. Starts from the Generic factory default (DSCR_SCULPT).
    2. Applies identity / info overrides.
    3. Applies technical overrides.
    4. Applies revenue overrides.
    5. Zeros the financial capex sub-fields and scales
       the epc_contract to hit a user-supplied total.
    6. Applies opex as a single user-supplied Y1 line.
    7. Applies financing overrides via the same
       _set_financing_* helpers used by the form path.
    """
    from app.project_factories import (
        create_default_solar_project,
        create_default_wind_project,
    )
    from domain.inputs import OpexItem, TechnicalParams

    factory_map = {
        "Solar": create_default_solar_project,
        "Wind": create_default_wind_project,
    }
    proj: "ProjectInputs" = factory_map[project_type]()

    # ── Identity / Info ──────────────────────────────────────
    if country_iso is not None or construction_months is not None or cod_date is not None or horizon_years is not None:
        new_country = country_iso if country_iso is not None else proj.info.country_iso
        new_construction_months = int(construction_months) if construction_months is not None else proj.info.construction_months
        new_cod_date = cod_date if cod_date is not None else proj.info.cod_date
        new_horizon_years = int(horizon_years) if horizon_years is not None else proj.info.horizon_years
        if cod_date is not None and construction_months is not None:
            new_financial_close = _subtract_months(cod_date, int(construction_months))
        else:
            new_financial_close = proj.info.financial_close
        new_name = project_name if project_name is not None else proj.info.name
        # Preserve pre-S1 code logic: prefer project_code
        # (often stored as `active_project` on snapshots)
        # over project_name; fall back to project_name,
        # then to factory default code.
        code_source = project_code or project_name or proj.info.code
        new_code = (
            code_source.strip().upper()
            .replace(" ", "_")
        )
        proj = dc_replace(
            proj,
            info=dc_replace(
                proj.info,
                name=new_name,
                code=new_code,
                country_iso=_country_iso(new_country) if country_iso is not None else proj.info.country_iso,
                financial_close=new_financial_close,
                construction_months=new_construction_months,
                cod_date=new_cod_date,
                horizon_years=new_horizon_years,
                period_frequency=proj.info.period_frequency,
            ),
        )

    # ── Technical ────────────────────────────────────────────
    if capacity_mw is not None or p50_hours is not None or operating_hours_p90_10y is not None or operating_hours_p99_1y is not None:
        new_cap = capacity_mw if capacity_mw is not None else proj.technical.capacity_mw
        new_p50 = p50_hours if p50_hours is not None else proj.technical.operating_hours_p50
        new_p90_10y = operating_hours_p90_10y if operating_hours_p90_10y is not None else (new_p50 * 0.9)
        new_p99_1y = operating_hours_p99_1y if operating_hours_p99_1y is not None else (new_p50 * 0.8)
        proj = dc_replace(
            proj,
            technical=TechnicalParams(
                capacity_mw=new_cap,
                yield_scenario=proj.technical.yield_scenario,
                operating_hours_p50=new_p50,
                operating_hours_p90_10y=new_p90_10y,
                operating_hours_p99_1y=new_p99_1y,
                pv_degradation=proj.technical.pv_degradation,
                plant_availability=proj.technical.plant_availability,
                grid_availability=proj.technical.grid_availability,
                bess_enabled=proj.technical.bess_enabled,
                bess=proj.technical.bess,
            ),
        )

    # ── Revenue ──────────────────────────────────────────────
    if tariff_eur_mwh is not None:
        proj = _set_revenue_tariff(proj, tariff_eur_mwh)
    if ppa_term_years is not None:
        proj = _set_revenue_ppa_term(proj, ppa_term_years)

    # ── CAPEX (shared resolver) ──────────────────────────────
    proj = _zero_financial_capex_subfields(proj)
    if total_capex_keur is not None:
        proj = _apply_capex_total(proj, total_capex_keur)

    # ── OPEX (single user-supplied Y1 line) ──────────────────
    if opex_y1_keur is not None:
        proj = dc_replace(
            proj,
            opex=(
                OpexItem(
                    name="User provided year 1 operating expense",
                    y1_amount_keur=float(opex_y1_keur),
                    annual_inflation=0.02,
                ),
            ),
        )

    # ── Financing (DSCR sculpt semantics) ────────────────────
    if gearing_pct is not None:
        proj = _set_financing_gearing(proj, gearing_pct)
    if interest_rate_pct is not None:
        proj = _set_financing_interest_rate(proj, interest_rate_pct)
    if tenor_years is not None:
        proj = _set_financing_tenor(proj, tenor_years)
    if target_dscr is not None:
        proj = _set_financing_target_dscr(proj, target_dscr)

    return proj


def _schema_to_dict(schema: ProjectInputsSchema) -> dict:
    """Flatten a ProjectInputsSchema to a dict of optional
    input values, suitable for _resolve_user_inputs.

    None values mean "use factory default".

    Phase S1: the form path and the snapshot path route
    through this dict and the shared resolver. The form
    path can now pass every input field the snapshot
    path accepts (Phase S1 schema expansion).
    """
    from datetime import date as _date
    cod_date = None
    if schema.cod_date is not None:
        try:
            cod_date = _date.fromisoformat(schema.cod_date)
        except ValueError:
            cod_date = None
    return {
        "project_type": schema.project_type,
        "project_name": schema.project_name,
        "country_iso": schema.country_iso,
        "capacity_mw": schema.capacity_mw,
        "cod_date": cod_date,
        "construction_months": schema.construction_months,
        "horizon_years": schema.horizon_years,
        "tariff_eur_mwh": (
            schema.revenue.tariff_eur_mwh if schema.revenue else None
        ),
        "ppa_term_years": (
            schema.revenue.ppa_term_years if schema.revenue else None
        ),
        "p50_hours": (
            schema.revenue.p50_hours if schema.revenue else None
        ),
        "operating_hours_p90_10y": schema.operating_hours_p90_10y,
        "operating_hours_p99_1y": schema.operating_hours_p99_1y,
        "opex_y1_keur": (
            schema.opex.opex_y1_keur if schema.opex else None
        ),
        "total_capex_keur": (
            schema.capex.total_capex_keur if schema.capex else None
        ),
        "gearing_pct": (
            schema.debt.gearing_pct if schema.debt else None
        ),
        "interest_rate_pct": (
            schema.debt.interest_rate_pct if schema.debt else None
        ),
        "tenor_years": (
            schema.debt.tenor_years if schema.debt else None
        ),
        "target_dscr": (
            schema.debt.target_dscr if schema.debt else None
        ),
    }


def _snapshot_to_dict(snapshot: dict) -> dict:
    """Convert a saved user-project snapshot dict to the
    same shape as _schema_to_dict. Required fields are
    validated by build_projectinputs_from_snapshot before
    this function is called."""
    return {
        "project_type": _snapshot_text(snapshot, "project_type").title(),
        "project_name": _snapshot_text(snapshot, "project_name"),
        # Optional project_code (often stored as
        # `active_project` on saved snapshots). When
        # present, the resolver prefers it as info.code
        # over project_name (matches pre-S1 behavior).
        "project_code": (
            snapshot.get("active_project")
            or snapshot.get("project_code")
        ),
        "country_iso": _snapshot_text(snapshot, "country_market"),
        "capacity_mw": _snapshot_float(snapshot, "capacity_mw", positive=True),
        "cod_date": _snapshot_date(snapshot, "cod_date"),
        "construction_months": _snapshot_int(
            snapshot, "construction_months", positive=True
        ),
        "horizon_years": _snapshot_int(
            snapshot, "horizon_years", positive=True
        ),
        "tariff_eur_mwh": _snapshot_float(
            snapshot, "tariff_eur_mwh", non_negative=True
        ),
        "ppa_term_years": _snapshot_int(
            snapshot, "ppa_term_years", positive=True
        ),
        "p50_hours": _snapshot_float(
            snapshot, "p50_hours", positive=True
        ),
        "operating_hours_p90_10y": None,
        "operating_hours_p99_1y": None,
        "opex_y1_keur": _snapshot_float(
            snapshot, "opex_y1_keur", non_negative=True
        ),
        "total_capex_keur": _snapshot_float(
            snapshot, "total_capex_keur", positive=True
        ),
        "gearing_pct": _snapshot_float(
            snapshot, "gearing_pct", non_negative=True
        ),
        "interest_rate_pct": _snapshot_float(
            snapshot, "interest_rate_pct", non_negative=True
        ),
        "tenor_years": _snapshot_int(
            snapshot, "tenor_years", positive=True
        ),
        "target_dscr": _snapshot_float(
            snapshot, "target_dscr", positive=True
        ),
    }


def build_projectinputs(schema: ProjectInputsSchema) -> "ProjectInputs":
    """Build a domain ProjectInputs from a ProjectInputsSchema.

    Phase S1: this is a clean thin wrapper around the
    shared _resolve_user_inputs resolver. The schema
    is first flattened to a dict of optional values
    via _schema_to_dict, then the resolver applies
    them to the factory default. Both
    build_projectinputs(schema) and
    build_projectinputs_from_snapshot(snapshot) route
    through this resolver, so identical Generic user
    inputs produce exactly equal ProjectInputs and
    exactly equal KPIs.
    """
    return _resolve_user_inputs(**_schema_to_dict(schema))


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

    Phase S1: this is a clean thin wrapper around the
    shared _resolve_user_inputs resolver (same as
    build_projectinputs). The snapshot is first
    validated for required fields, then flattened via
    _snapshot_to_dict, then the resolver applies the
    values to the Generic factory default.

    Both build_projectinputs(schema) and
    build_projectinputs_from_snapshot(snapshot) route
    through _resolve_user_inputs, so identical Generic
    user inputs produce exactly equal ProjectInputs
    and exactly equal KPIs.
    """
    # Validate required fields (preserve SnapshotInputError
    # behavior).
    missing = [
        key for key in REQUIRED_USER_PROJECT_SNAPSHOT_FIELDS
        if snapshot.get(key) is None or str(snapshot.get(key)).strip() == ""
    ]
    if missing:
        raise SnapshotInputError(
            "Missing required user-created project runtime fields: "
            + ", ".join(missing)
        )

    # Validate gearing_pct range (preflight, before delegating
    # to the resolver).
    gearing_raw = _snapshot_float(
        snapshot, "gearing_pct", non_negative=True
    )
    if gearing_raw > 100:
        raise SnapshotInputError(
            "gearing_pct must be between 0 and 100 for user-created project runtime"
        )

    # Validate project_type is Solar or Wind (preserved
    # behavior).
    project_type = _snapshot_text(snapshot, "project_type").title()
    if project_type not in {"Solar", "Wind"}:
        raise SnapshotInputError(
            "project_type must be Solar or Wind for user-created project runtime"
        )

    # Delegate to the shared resolver. _snapshot_to_dict
    # applies the snapshot field validation (positive,
    # non_negative, ISO date, whole-number int) for the
    # remaining fields.
    return _resolve_user_inputs(**_snapshot_to_dict(snapshot))


