"""Read-only project context builders for UI binding.

Reads from factory defaults or generic project factories.
Does NOT run model calculations.
Does NOT persist anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from app.project_factories import (
    create_default_oborovo,
    create_default_solar_project,
    create_default_tuho_wind1,
    create_default_wind_project,
)
from domain.opex.templates import build_oborovo_opex_template, build_tuho_opex_template


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
    revenue_items: tuple[dict[str, Any], ...] = field(default_factory=lambda: ())
    opex_items: tuple[dict[str, Any], ...] = field(default_factory=lambda: ())
    opex_detail_items: tuple[dict[str, Any], ...] = field(default_factory=lambda: ())  # hierarchical for detail OPEX tab
    opex_y1_total_keur: float = 0.0
    opex_contingency_method: str = ""
    opex_contingency_pct: float = 0.0
    total_capex_keur: float = 0.0
    epc_contract_keur: float = 0.0
    idc_keur: float = 0.0
    bank_fees_keur: float = 0.0
    capex_items: tuple[dict[str, Any], ...] = field(default_factory=lambda: ())
    capex_detail_items: tuple[dict[str, Any], ...] = field(default_factory=lambda: ())  # hierarchical for detail CAPEX tab
    capex_construction_months: int = 0
    capex_y1_total_keur: float = 0.0
    senior_debt_keur: float = 0.0
    interest_rate_pct: float = 0.0
    senior_tenor_years: int = 0
    target_dscr: float = 0.0
    gearing_pct: float | None = None
    shl_amount_keur: float = 0.0
    shl_rate_pct: float = 0.0
    shl_idc_keur: float = 0.0
    construction_items: tuple[dict[str, Any], ...] = field(default_factory=lambda: ())
    idc_items: tuple[dict[str, Any], ...] = field(default_factory=lambda: ())
    cit_rate_pct: float = 0.0
    loss_carryforward_years: int = 0
    g20_status: str = ""
    r99_r102_status: str = ""
    parity_status: str = ""
    data_source: str = ""
    missing_fields: tuple[str, ...] = ()

    @property
    def id(self) -> str:
        return self.code.lower()


def _slugify_code(name: str) -> str:
    """Create a URL-safe code from an item name."""
    import re
    # Lowercase, replace spaces/slashes with underscores, keep alphanumerics
    slug = re.sub(r'[^a-z0-9]+', '_', name.lower())
    slug = slug.strip('_')
    return slug or "item"


def _infer_opex_group(name: str) -> str:
    """Infer OPEX group from item name patterns (best-effort for display)."""
    n = name.lower()
    if any(k in n for k in ["technical", "o&m", "maintain", "clean", "security", "operational"]):
        return "Technical Management"
    if any(k in n for k in ["insurance", "insur"]):
        return "Insurance"
    if any(k in n for k in ["lease", "land", "property", "rent"]):
        return "Lease & Property Tax"
    if any(k in n for k in ["power", "balancing", "grid", "transmission"]):
        return "Power Expenses"
    if any(k in n for k in ["audit", "accounting", "legal", "bank fee", "admin", "management fee"]):
        return "Audit&Accounting&Legal"
    if any(k in n for k in ["environmental", "social", "e&s", "hse"]):
        return "Environmental&Social"
    if "contingen" in n:
        return "Contingencies"
    if any(k in n for k in ["infrastructure", "maintenance"]):
        return "Infrastructure Maintenance"
    return "Other Operating Costs"



def _build_construction_items(project_inputs) -> tuple[dict[str, Any], ...]:
    """Build serialisable construction schedule items from runtime construction engine.

    Uses build_runtime_construction_schedule() for TUHO/Oborovo.
    Returns monthly drawdown rows + funding source summary rows.
    Marked audit_only=True since monthly grid is not yet runtime-authoritative.
    """
    try:
        from domain.construction.runtime_adapter import build_runtime_construction_schedule
        result = build_runtime_construction_schedule(project_inputs)
    except Exception:
        return ()

    rows = []

    # ── Monthly Schedule Rows ────────────────────────────────────────────
    for entry in result.monthly_entries:
        rows.append({
            "type": "monthly",
            "month_index": entry.month_index,
            "label": f"Month {entry.month_index}",
            "unit": "kEUR",
            "equity_draw_keur": entry.equity_draw_keur,
            "shl_draw_keur": entry.shl_draw_keur,
            "junior_draw_keur": entry.junior_draw_keur,
            "senior_draw_keur": entry.senior_draw_keur,
            "senior_idc_keur": entry.senior_idc_keur,
            "cumulative_senior_idc_keur": entry.cumulative_senior_idc_keur,
            "total_draw_keur": entry.equity_draw_keur + entry.shl_draw_keur
                            + entry.junior_draw_keur + entry.senior_draw_keur,
            "cumulative_uses_keur": entry.cumulative_uses_keur,
            "audit_only": True,
        })

    # ── Funding Summary Rows ────────────────────────────────────────────
    rows.append({
        "type": "summary",
        "label": "Total Equity Draw",
        "unit": "kEUR",
        "value": result.equity_draw_keur,
        "audit_only": False,
    })
    rows.append({
        "type": "summary",
        "label": "Total SHL Principal Draw",
        "unit": "kEUR",
        "value": result.shl_principal_draw_keur,
        "audit_only": False,
    })
    rows.append({
        "type": "summary",
        "label": "Total Senior Principal Draw",
        "unit": "kEUR",
        "value": result.senior_principal_draw_keur,
        "audit_only": False,
    })
    rows.append({
        "type": "summary",
        "label": "Total Junior Draw",
        "unit": "kEUR",
        "value": result.junior_draw_keur,
        "audit_only": False,
    })
    rows.append({
        "type": "summary",
        "label": "Total Uses (CAPEX)",
        "unit": "kEUR",
        "value": result.total_uses_keur,
        "audit_only": False,
    })

    return tuple(rows)


def _build_idc_items(project_inputs) -> tuple[dict[str, Any], ...]:
    """Build serialisable IDC summary items from runtime construction engine.

    Uses build_runtime_construction_schedule() for TUHO/Oborovo.
    Returns IDC summary rows + COD opening balances.
    """
    try:
        from domain.construction.runtime_adapter import build_runtime_construction_schedule
        result = build_runtime_construction_schedule(project_inputs)
    except Exception:
        return ()

    rows = []

    # ── Senior Debt IDC ────────────────────────────────────────────────
    rows.append({
        "code": "senior_principal_draw",
        "name": "Senior Debt Principal Draw",
        "value": result.senior_principal_draw_keur,
        "unit": "kEUR",
        "group": "Senior Debt",
        "editable": False,
        "hint": "Runtime computed",
    })
    rows.append({
        "code": "senior_idc",
        "name": "Senior Debt IDC",
        "value": result.senior_idc_keur,
        "unit": "kEUR",
        "group": "Senior Debt",
        "editable": False,
        "hint": "Runtime computed",
    })
    rows.append({
        "code": "opening_senior_balance",
        "name": "Opening Senior Balance (COD)",
        "value": result.opening_senior_balance_keur,
        "unit": "kEUR",
        "group": "Senior Debt",
        "editable": False,
        "hint": "Runtime computed — senior_idc_capitalized applied",
    })

    # ── SHL IDC ────────────────────────────────────────────────────────
    rows.append({
        "code": "shl_principal_draw",
        "name": "SHL Principal Draw",
        "value": result.shl_principal_draw_keur,
        "unit": "kEUR",
        "group": "SHL",
        "editable": False,
        "hint": "Runtime computed",
    })
    rows.append({
        "code": "shl_idc",
        "name": "SHL IDC",
        "value": result.shl_idc_keur,
        "unit": "kEUR",
        "group": "SHL",
        "editable": False,
        "hint": "Runtime computed",
    })
    rows.append({
        "code": "opening_shl_balance",
        "name": "Opening SHL Balance (COD)",
        "value": result.opening_shl_balance_keur,
        "unit": "kEUR",
        "group": "SHL",
        "editable": False,
        "hint": "Runtime computed — shl_idc_capitalized applied",
    })

    # ── IDC Totals ─────────────────────────────────────────────────────
    rows.append({
        "code": "total_idc",
        "name": "Total IDC",
        "value": result.shl_idc_keur + result.senior_idc_keur,
        "unit": "kEUR",
        "group": "IDC Summary",
        "editable": False,
        "hint": "SHL IDC + Senior IDC",
    })
    rows.append({
        "code": "opening_senior_excl_idc",
        "name": "Opening Senior Excl. IDC",
        "value": result.opening_senior_balance_keur - result.senior_idc_keur,
        "unit": "kEUR",
        "group": "IDC Summary",
        "editable": False,
        "hint": "Computed from runtime",
    })

    # ── Monthly IDC entries ────────────────────────────────────────────
    for entry in result.monthly_entries:
        rows.append({
            "type": "monthly_idc",
            "month_index": entry.month_index,
            "label": f"Month {entry.month_index}",
            "unit": "kEUR",
            "senior_idc_keur": entry.senior_idc_keur,
            "cumulative_senior_idc_keur": entry.cumulative_senior_idc_keur,
            "audit_only": True,
        })

    return tuple(rows)


def _build_opex_items(project_inputs, horizon_years: int = 25) -> tuple[dict[str, Any], ...]:
    items = []
    for item in project_inputs.opex:
        code = _slugify_code(item.name)
        items.append(
            {
                "code": code,
                "name": item.name,
                "y1_keur": item.y1_amount_keur,
                "inflation_pct": item.annual_inflation,
                "group": _infer_opex_group(item.name),
                "unit": "kEUR",
                "fixed_variable": "Fixed",
                "recurring_oneoff": "Recurring",
                "escalation_pct": round(item.annual_inflation * 100, 1) if item.annual_inflation else 0.0,
                "start_year": 1,
                "end_year": horizon_years,
                "notes": "",
            }
        )
    return tuple(items)


# ── Group metadata for OPEX detail mapping ──────────────────────────────────────
_OPEX_GROUP_META = {
    # Maps group name → (code, display_order)
    "Technical Management":       ("B.01", 1),
    "Infrastructure Maintenance": ("B.02", 2),
    "Maintain Site":              ("B.03", 3),
    "Clean Material":             ("B.04", 4),
    "Security":                   ("B.05", 5),
    "Insurance":                  ("B.06", 6),
    "Lease & Property Tax":       ("B.07", 7),
    "Power Expenses":             ("B.08", 8),
    "Fees":                       ("B.09", 9),
    "Audit&Accounting&Legal":      ("B.10", 10),
    "Bank Fees":                  ("B.11", 11),
    "Environmental&Social":       ("B.12", 12),
    "Contingencies":              ("B.13", 13),
}


def _build_opex_detail_items(
    project_inputs,
    code: str,
    horizon_years: int = 25,
) -> dict[str, Any]:
    """Build hierarchical OPEX detail structure for the Excel-like OPEX grid.

    For Oborovo and TUHO: uses the detailed domain.opex.templates structures.
    For other projects: falls back to flat aggregated items from project_inputs.opex.

    Adds computed yearly display values for each child and category total.
    The contingency (B.13) yearly total = contingency_pct × sum(non-contingency totals).

    Returns:
        {
          "categories": [
            {
              "code": "B.01",
              "name": "Technical Management",
              "inflation_pct": 2.0,
              "wth_rate": 0.0,
              "source": "factory",
              "is_contingency": False,
              "contingency_pct": 0.0,
              "yearly_totals": [198.0, 198.0, 201.96, ...],
              "children": [
                {
                  "code": "B.01.01",
                  "name": "Asset Management Contract",
                  "budget_y1_keur": 60.0,
                  "inflation_pct": 2.0,
                  "wth_rate": 0.0,
                  "source": "factory",
                  "notes": "",
                  "yearly_values": [60.0, 61.2, 62.424, ...],
                  "active_flags": [1, 1, 1, ...],
                },
              ],
            },
          ],
        }
    """
    # Try to use detailed templates for known projects
    if code.upper() in ("OBOROVO",):
        template_groups = build_oborovo_opex_template()
    elif code.upper() in ("TUHO", "TUHO-WIND-1"):
        template_groups = build_tuho_opex_template()
    else:
        template_groups = None

    if template_groups is not None:
        categories = []
        for group in template_groups:
            is_contingency = (
                group.contingency_pct > 0
                and group.contingency_method.name == "PERCENTAGE_OF_OPEX"
            )

            cat = {
                "code": group.code,
                "name": group.name,
                "inflation_pct": group.inflation_rate * 100 if group.inflation_rate else 0.0,
                "wth_rate": group.wth_rate or 0.0,
                "source": "factory",
                "is_contingency": is_contingency,
                "contingency_pct": group.contingency_pct,
                "children": [],
                "yearly_totals": [],
            }

            for item in group.items:
                is_item_contingency = (
                    item.selected_group_codes
                    and all(
                        g.startswith("B.") and g != group.code
                        for g in item.selected_group_codes
                    )
                )

                if is_item_contingency:
                    formula_note = f"{group.contingency_pct}% x non-contingency OPEX"
                    budget_display = 0.0
                else:
                    formula_note = ""
                    budget_display = item.budget_keur

                # Compute yearly values: effective_budget × inflation^(y-1) × active_flag
                inflation_rate = item.inflation_rate or 0.0
                yearly_values = []
                active_flags = []
                for y in range(1, horizon_years + 1):
                    active = item.is_active(y)
                    active_flags.append(1 if active else 0)
                    if not active:
                        yearly_values.append(0.0)
                    else:
                        eff = item.effective_budget(y)
                        inflated = eff * ((1 + inflation_rate) ** (y - 1))
                        yearly_values.append(round(inflated, 4))

                child = {
                    "code": item.code,
                    "name": item.name,
                    "budget_y1_keur": budget_display,
                    "inflation_pct": inflation_rate * 100 if inflation_rate else 0.0,
                    "wth_rate": item.wth_rate or 0.0,
                    "source": "factory",
                    "notes": formula_note,
                    "yearly_values": yearly_values,
                    "active_flags": active_flags,
                }
                cat["children"].append(child)

            categories.append(cat)

        # ── Second pass: compute category yearly_totals ─────────────────────
        # Non-contingency categories: sum of children
        for cat in categories:
            if cat["is_contingency"]:
                continue
            totals = [0.0] * horizon_years
            for child in cat["children"]:
                for y_idx, y_val in enumerate(child["yearly_values"]):
                    totals[y_idx] += y_val
            cat["yearly_totals"] = [round(t, 4) for t in totals]

        # Contingency categories: contingency_pct × sum(non-contingency totals)
        for cat in categories:
            if not cat["is_contingency"]:
                continue
            contingency_pct = cat.get("contingency_pct", 0.0) / 100.0
            non_contingency_totals = [
                sum(
                    c["yearly_totals"][y_idx]
                    for c in categories
                    if not c["is_contingency"]
                )
                for y_idx in range(horizon_years)
            ]
            cat["yearly_totals"] = [
                round(contingency_pct * nc_total, 4)
                for nc_total in non_contingency_totals
            ]

        return {"categories": tuple(categories)}

    # Fallback: build flat structure from project_inputs.opex
    categories = []
    for item in project_inputs.opex:
        group_name = _infer_opex_group(item.name)
        code_slug = _slugify_code(item.name)
        is_contingency = item.percentage_of_opex > 0

        if is_contingency:
            budget_display = 0.0
            formula_note = f"{int(item.percentage_of_opex * 100)}% x non-contingency OPEX"
        else:
            budget_display = item.y1_amount_keur
            formula_note = ""

        inflation_rate = item.annual_inflation or 0.0
        yearly_values = []
        active_flags = []
        for y in range(1, horizon_years + 1):
            active_flags.append(1)
            inflated = budget_display * ((1 + inflation_rate) ** (y - 1))
            yearly_values.append(round(inflated, 4))

        child_item = {
            "code": code_slug,
            "name": item.name,
            "budget_y1_keur": budget_display,
            "inflation_pct": item.annual_inflation * 100 if item.annual_inflation else 0.0,
            "wth_rate": 0.0,
            "source": "factory",
            "notes": formula_note,
            "yearly_values": yearly_values,
            "active_flags": active_flags,
        }

        cat_code = _OPEX_GROUP_META.get(group_name, ("", 99))[0]
        cat_meta = next((c for c in categories if c["code"] == cat_code), None)
        if cat_meta is None:
            cat_meta = {
                "code": cat_code,
                "name": group_name,
                "inflation_pct": item.annual_inflation * 100 if item.annual_inflation else 0.0,
                "wth_rate": 0.0,
                "source": "factory",
                "is_contingency": is_contingency,
                "contingency_pct": 0.0,
                "children": [],
                "yearly_totals": [],
            }
            categories.append(cat_meta)

        cat_meta["children"].append(child_item)

    def _sort_key(c):
        return _OPEX_GROUP_META.get(c["name"], ("", 99))[1]

    categories.sort(key=_sort_key)

    # Compute yearly_totals for fallback categories
    for cat in categories:
        if cat["is_contingency"]:
            continue
        totals = [0.0] * horizon_years
        for child in cat["children"]:
            for y_idx, y_val in enumerate(child["yearly_values"]):
                totals[y_idx] += y_val
        cat["yearly_totals"] = [round(t, 4) for t in totals]

    # Handle contingency for fallback (if any)
    for cat in categories:
        if not cat["is_contingency"]:
            continue
        contingency_pct = cat.get("contingency_pct", 0.0) / 100.0
        non_contingency_totals = [
            sum(
                c["yearly_totals"][y_idx]
                for c in categories
                if not c["is_contingency"]
            )
            for y_idx in range(horizon_years)
        ]
        cat["yearly_totals"] = [
            round(contingency_pct * nc_total, 4)
            for nc_total in non_contingency_totals
        ]

    return {"categories": tuple(categories)}



def _build_revenue_items(revenue, technical, technology: str) -> tuple[dict[str, Any], ...]:
    """Build serialisable revenue item list from RevenueParams + TechnicalParams."""
    items = []

    # ── Production ────────────────────────────────────────────────────────
    items.append({
        "code": "capacity_mw",
        "name": "Installed Capacity",
        "value": technical.capacity_mw,
        "unit": "MW",
        "group": "Production",
        "editable": False,
        "hint": "Set via inputs tab",
    })
    items.append({
        "code": "operating_hours_p50",
        "name": "P50 Hours / Year",
        "value": technical.operating_hours_p50,
        "unit": "h/yr",
        "group": "Production",
        "editable": False,
        "hint": "Set via inputs tab",
    })
    items.append({
        "code": "plant_availability",
        "name": "Plant Availability",
        "value": technical.plant_availability,
        "unit": "%",
        "group": "Production",
        "editable": False,
        "hint": "Set via inputs tab",
    })
    items.append({
        "code": "grid_availability",
        "name": "Grid Availability",
        "value": technical.grid_availability,
        "unit": "%",
        "group": "Production",
        "editable": False,
        "hint": "Set via inputs tab",
    })
    if technology != "Wind":
        items.append({
            "code": "pv_degradation",
            "name": "PV Degradation",
            "value": technical.pv_degradation,
            "unit": "%/yr",
            "group": "Production",
            "editable": False,
            "hint": "Set via inputs tab",
        })

    # ── PPA / Tariff ────────────────────────────────────────────────────
    items.append({
        "code": "ppa_base_tariff",
        "name": "Base Tariff (PPA)",
        "value": revenue.ppa_base_tariff,
        "unit": "EUR/MWh",
        "group": "PPA / Tariff",
        "editable": True,
        "hint": "",
    })
    items.append({
        "code": "ppa_index",
        "name": "Tariff Escalation",
        "value": revenue.ppa_index,
        "unit": "%/yr",
        "group": "PPA / Tariff",
        "editable": False,
        "hint": "Set via inputs tab",
    })
    items.append({
        "code": "ppa_term_years",
        "name": "PPA Term",
        "value": int(revenue.ppa_term_years),
        "unit": "years",
        "group": "PPA / Tariff",
        "editable": False,
        "hint": "Set via inputs tab",
    })
    items.append({
        "code": "ppa_production_share",
        "name": "PPA Production Share",
        "value": getattr(revenue, "ppa_production_share", 1.0),
        "unit": "%",
        "group": "PPA / Tariff",
        "editable": False,
        "hint": "Set via inputs tab",
    })

    # ── Market / Merchant ───────────────────────────────────────────────
    balancing = getattr(revenue, "balancing_cost_eur_per_mwh", 0.0) or 0.0
    items.append({
        "code": "balancing_cost",
        "name": "Balancing Cost",
        "value": balancing,
        "unit": "EUR/MWh",
        "group": "Market / Merchant",
        "editable": False,
        "hint": "Set via inputs tab",
    })
    first_merchant = getattr(revenue, "first_merchant_operating_period_index", None)
    items.append({
        "code": "first_merchant_period",
        "name": "First Merchant Period",
        "value": first_merchant if first_merchant is not None else -1,
        "unit": "period index",
        "group": "Market / Merchant",
        "editable": False,
        "hint": "Set via inputs tab",
    })

    # ── CO2 / Certificates ─────────────────────────────────────────────
    items.append({
        "code": "co2_enabled",
        "name": "CO2 Certificates Enabled",
        "value": 1.0 if revenue.co2_enabled else 0.0,
        "unit": "flag",
        "group": "CO2 / Certificates",
        "editable": False,
        "hint": "Set via inputs tab",
    })
    co2_price = (
        getattr(revenue, "co2_certificate_price_eur_per_mwh", None)
        or getattr(revenue, "co2_price_eur", None)
        or 0.0
    )
    items.append({
        "code": "co2_price",
        "name": "CO2 Price (Y1)",
        "value": co2_price,
        "unit": "EUR/MWh",
        "group": "CO2 / Certificates",
        "editable": False,
        "hint": "Set via inputs tab",
    })

    return tuple(items)


def _capex_y1_total(capex) -> float:
    """Sum of all non-zero hard-capex items (excludes financing rows)."""
    total = 0.0
    for field in capex._CAPEX_ITEM_FIELDS:
        item = getattr(capex, field)
        total += item.amount_keur
    return total


def _build_capex_detail_items(
    capex,
    construction_months: int = 12,
) -> dict[str, Any]:
    """Build full Excel-like CAPEX detail structure (C.01–C.18).

    Source: 20260330_TUHO_BP.xlsm CapEx sheet.
    Maps each Excel row to current app CapexStructure where feasible.

    Returns:
        {
          "categories": tuple of {
            "code": str,          # "C.01" etc.
            "name": str,          # "Production Unit" etc.
            "is_backend_calculated": bool,
            "authority_summary": dict,  # counts per authority_status
            "children": tuple of {
              "code": str,          # "C.01.01" etc.
              "name": str,
              "amount_keur": float, # Excel reference amount
              "app_amount_keur": float | None,
              "per_mw": float | None,
              "mapping_status": str, # "mapped" | "unmapped" | "partial" | "model_mismatch" | "backend_calculated"
              "delta_keur": float | None,
              "contingency_pct": float | None,
              "contingency_cost_keur": float | None,
              "vat_rate_pct": float | None,
              "vat_cost_keur": float | None,
              "wth_rate_pct": float | None,
              "depreciable": bool,
              "comments": str,
              "monthly_schedule": tuple[float, ...] | None,  # M1–M18 fractions
              "is_backend_calculated": bool,
              # ── Phase 21B authority metadata ──────────────────────────────
              "authority_status": str,   # excel_reference_only | app_mapped | backend_authoritative | mismatch | missing_runtime_source | deferred | not_applicable
              "source_type": str,       # excel_reference | app_input | computed_runtime | static_reference | missing
              "runtime_source_field": str | None,  # e.g. "capex.idc_keur"
              "affects_runtime": bool,  # True if value feeds CFADS / debt sizing today
              "mapping_note": str,      # human-readable note
              "mismatch_amount_keur": float | None,
              "mismatch_pct": float | None,
              "monthly_schedule_source": str,  # excel_m1_m18 | app_profile | static_reference | missing
            },
          },
          "grand_total_keur": float,
          "hard_capex_total_keur": float,
          "financing_total_keur": float,
          "construction_months": int,
          "authority_summary": dict,  # top-level counts across all categories
        }
    """
    # ── Excel payment schedule constants ─────────────────────────────────
    # C.01–C.05, C.11: even spread over 18 months
    _EVEN18 = (1 / 18,) * 18
    # C.06–C.10, C.12–C.16: 100% at M1 (FC)
    _AT_FC = (1.0,) + (0.0,) * 17
    # C.17: backend-calculated, no payment schedule
    _NO_SCHEDULE = None

    # ── Excel reference data (C.01–C.18) ─────────────────────────────────
    # Format: (code, name, amount_keur, per_mw, cont_pct, cont_cost,
    #           vat_rate_pct, vat_cost, wth, depreciable, schedule, comments)
    _EXCEL_ROWS = [
        # C.01 Production Unit
        {
            "code": "C.01", "name": "Production Unit",
            "amount_keur": 35000.0, "per_mw": 1000.0,
            "cont_pct": None, "cont_cost": None,
            "vat_rate_pct": None, "vat_cost": None,
            "wth_pct": None, "depreciable": False,
            "schedule": _EVEN18,
            "comments": "Excel reference: 20260330_TUHO_BP CapEx",
            "children": [
                {
                    "code": "C.01.01", "name": "Wind Turbines",
                    "amount_keur": 35000.0, "per_mw": 1000.0,
                    "cont_pct": 6.0, "cont_cost": 2100.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
                {
                    "code": "C.01.02", "name": "TSA optionals",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 6.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
                {
                    "code": "C.01.03", "name": "Flow Parts",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 6.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
                {
                    "code": "C.01.04", "name": "Procurement fees",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 6.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
                {
                    "code": "C.01.05", "name": "Logistics & Transport & others",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 6.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
            ],
        },
        # C.02 EPC Contract
        {
            "code": "C.02", "name": "EPC Contract",
            "amount_keur": 13560.0, "per_mw": 387.43,
            "cont_pct": None, "cont_cost": None,
            "vat_rate_pct": None, "vat_cost": None,
            "wth_pct": None, "depreciable": False,
            "schedule": _EVEN18,
            "comments": "Excel reference: 20260330_TUHO_BP CapEx",
            "children": [
                {
                    "code": "C.02.01", "name": "Electrical BOP",
                    "amount_keur": 720.0, "per_mw": 20.57,
                    "cont_pct": 6.0, "cont_cost": 43.2,
                    "vat_rate_pct": 13.0, "vat_cost": 93.6,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
                {
                    "code": "C.02.02", "name": "Connection to existing grid",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 6.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
                {
                    "code": "C.02.03", "name": "Civil BOP",
                    "amount_keur": 2040.0, "per_mw": 58.29,
                    "cont_pct": 6.0, "cont_cost": 122.4,
                    "vat_rate_pct": 13.0, "vat_cost": 265.2,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
                {
                    "code": "C.02.04", "name": "Grid connection",
                    "amount_keur": 10800.0, "per_mw": 308.57,
                    "cont_pct": 6.0, "cont_cost": 648.0,
                    "vat_rate_pct": 13.0, "vat_cost": 1404.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
            ],
        },
        # C.03 Grid Connection
        {
            "code": "C.03", "name": "Grid Connection",
            "amount_keur": 30.0, "per_mw": 0.86,
            "cont_pct": None, "cont_cost": None,
            "vat_rate_pct": None, "vat_cost": None,
            "wth_pct": None, "depreciable": False,
            "schedule": _EVEN18,
            "comments": "Excel reference: 20260330_TUHO_BP CapEx",
            "children": [
                {
                    "code": "C.03.01", "name": "Grid Connection Agreement",
                    "amount_keur": 30.0, "per_mw": 0.86,
                    "cont_pct": 6.0, "cont_cost": 1.8,
                    "vat_rate_pct": 13.0, "vat_cost": 3.9,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
                {
                    "code": "C.03.02", "name": "Grid Usage Fees",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 6.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
            ],
        },
        # C.04 Monitoring & Telecom
        {
            "code": "C.04", "name": "Monitoring & Telecom",
            "amount_keur": 100.0, "per_mw": 2.86,
            "cont_pct": None, "cont_cost": None,
            "vat_rate_pct": None, "vat_cost": None,
            "wth_pct": None, "depreciable": False,
            "schedule": _EVEN18,
            "comments": "Excel reference: 20260330_TUHO_BP CapEx",
            "children": [
                {
                    "code": "C.04.01", "name": "Telecom connection",
                    "amount_keur": 50.0, "per_mw": 1.43,
                    "cont_pct": 6.0, "cont_cost": 3.0,
                    "vat_rate_pct": 13.0, "vat_cost": 6.5,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
                {
                    "code": "C.04.02", "name": "SCADA",
                    "amount_keur": 50.0, "per_mw": 1.43,
                    "cont_pct": 6.0, "cont_cost": 3.0,
                    "vat_rate_pct": 13.0, "vat_cost": 6.5,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
                {
                    "code": "C.04.03", "name": "Energy Management System",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 6.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
            ],
        },
        # C.05 Operation Investments
        {
            "code": "C.05", "name": "Operation Investments",
            "amount_keur": 1000.0, "per_mw": 28.57,
            "cont_pct": None, "cont_cost": None,
            "vat_rate_pct": None, "vat_cost": None,
            "wth_pct": None, "depreciable": False,
            "schedule": _EVEN18,
            "comments": "Excel reference: 20260330_TUHO_BP CapEx",
            "children": [
                {
                    "code": "C.05.01", "name": "O&M Building",
                    "amount_keur": 100.0, "per_mw": 2.86,
                    "cont_pct": 6.0, "cont_cost": 6.0,
                    "vat_rate_pct": 13.0, "vat_cost": 13.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
                {
                    "code": "C.05.02", "name": "Weather Station",
                    "amount_keur": 300.0, "per_mw": 8.57,
                    "cont_pct": 6.0, "cont_cost": 18.0,
                    "vat_rate_pct": 13.0, "vat_cost": 39.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
                {
                    "code": "C.05.03", "name": "Temporary Access Roads",
                    "amount_keur": 100.0, "per_mw": 2.86,
                    "cont_pct": 6.0, "cont_cost": 6.0,
                    "vat_rate_pct": 13.0, "vat_cost": 13.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
                {
                    "code": "C.05.04", "name": "Special vehicles and Operation equipment",
                    "amount_keur": 500.0, "per_mw": 14.29,
                    "cont_pct": 6.0, "cont_cost": 30.0,
                    "vat_rate_pct": 13.0, "vat_cost": 65.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
                {
                    "code": "C.05.05", "name": "E&S/Mitigation measures",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 6.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
                {
                    "code": "C.05.06", "name": "Local Involvement",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 6.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
            ],
        },
        # C.06 Insurances
        {
            "code": "C.06", "name": "Insurances",
            "amount_keur": 468.75, "per_mw": 13.39,
            "cont_pct": None, "cont_cost": None,
            "vat_rate_pct": None, "vat_cost": None,
            "wth_pct": None, "depreciable": False,
            "schedule": _AT_FC,
            "comments": "Excel reference: 20260330_TUHO_BP CapEx",
            "children": [
                {
                    "code": "C.06.01", "name": "All Construction Risk: Damage & Losses (TRC)",
                    "amount_keur": 468.75, "per_mw": 13.39,
                    "cont_pct": 6.0, "cont_cost": 28.13,
                    "vat_rate_pct": 13.0, "vat_cost": 60.94,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.06.02", "name": "Civil Liability (RC)",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.06.03", "name": "Property damages insurance (DO)",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.06.04", "name": "Delay in start-up / ALOP",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.06.05", "name": "Marine Cargo DSU",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.06.06", "name": "Others",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
            ],
        },
        # C.07 Land Securing Costs
        {
            "code": "C.07", "name": "Land Securing Costs",
            "amount_keur": 512.44, "per_mw": 14.64,
            "cont_pct": None, "cont_cost": None,
            "vat_rate_pct": None, "vat_cost": None,
            "wth_pct": None, "depreciable": False,
            "schedule": _AT_FC,
            "comments": "Excel reference: 20260330_TUHO_BP CapEx",
            "children": [
                {
                    "code": "C.07.01", "name": "Land lease reservation / acquisition / Expropriation",
                    "amount_keur": 500.0, "per_mw": 14.29,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 13.0, "vat_cost": 65.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.07.02", "name": "Easement",
                    "amount_keur": 12.44, "per_mw": 0.36,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.07.03", "name": "Expropriation",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
            ],
        },
        # C.08 Bank Due Diligence
        {
            "code": "C.08", "name": "Bank Due Diligence",
            "amount_keur": 420.0, "per_mw": 12.0,
            "cont_pct": None, "cont_cost": None,
            "vat_rate_pct": None, "vat_cost": None,
            "wth_pct": None, "depreciable": False,
            "schedule": _AT_FC,
            "comments": "Excel reference: 20260330_TUHO_BP CapEx",
            "children": [
                {
                    "code": "C.08.01", "name": "Owners' and Lenders' Advisors",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": None, "cont_cost": None,
                    "vat_rate_pct": None, "vat_cost": None,
                    "wth_pct": None, "depreciable": False,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.08.02", "name": "Bank due diligence",
                    "amount_keur": 100.0, "per_mw": 2.86,
                    "cont_pct": 6.0, "cont_cost": 6.0,
                    "vat_rate_pct": 13.0, "vat_cost": 13.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.08.03", "name": "Technical Advisor / Appraisal",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 6.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.08.04", "name": "E&S Advisor",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 6.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.08.05", "name": "Energy Yield Assessment",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 6.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.08.06", "name": "Market Advisor",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 6.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.08.07", "name": "Insurance Advisor",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 6.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.08.08", "name": "Legal Advisor",
                    "amount_keur": 100.0, "per_mw": 2.86,
                    "cont_pct": 6.0, "cont_cost": 6.0,
                    "vat_rate_pct": 13.0, "vat_cost": 13.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.08.09", "name": "Model & Tax Auditor",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 6.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.08.10", "name": "Travel Expenses & Others",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": None, "cont_cost": None,
                    "vat_rate_pct": None, "vat_cost": None,
                    "wth_pct": None, "depreciable": False,
                    "schedule": _AT_FC,
                    "comments": "",
                },
            ],
        },
        # C.09 Construction Management
        {
            "code": "C.09", "name": "Construction Management",
            "amount_keur": 40.0, "per_mw": 1.14,
            "cont_pct": None, "cont_cost": None,
            "vat_rate_pct": None, "vat_cost": None,
            "wth_pct": None, "depreciable": False,
            "schedule": _AT_FC,
            "comments": "Excel reference: 20260330_TUHO_BP CapEx",
            "children": [
                {
                    "code": "C.09.01", "name": "Lender's E&S Monitoring",
                    "amount_keur": 20.0, "per_mw": 0.57,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.09.02", "name": "Lender's Technical Monitoring",
                    "amount_keur": 20.0, "per_mw": 0.57,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.09.03", "name": "Environmental and Social Monitoring",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 6.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
            ],
        },
        # C.10 Commissioning
        {
            "code": "C.10", "name": "Commissioning",
            "amount_keur": 0.0, "per_mw": 0.0,
            "cont_pct": None, "cont_cost": None,
            "vat_rate_pct": None, "vat_cost": None,
            "wth_pct": None, "depreciable": False,
            "schedule": (0.0,) * 17 + (1.0,),  # M18 only
            "comments": "Excel reference: 20260330_TUHO_BP CapEx",
            "children": [
                {
                    "code": "C.10.01", "name": "Commissioning and Inspections advisors",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 6.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": (0.0,) * 17 + (1.0,),
                    "comments": "",
                },
                {
                    "code": "C.10.02", "name": "Power Curve Testing",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 6.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": (0.0,) * 17 + (1.0,),
                    "comments": "",
                },
                {
                    "code": "C.10.03", "name": "Commissioning costs and potential revenues",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 6.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": (0.0,) * 17 + (1.0,),
                    "comments": "",
                },
            ],
        },
        # C.11 Audit & Accounting & Legal
        {
            "code": "C.11", "name": "Audit & Accounting & Legal",
            "amount_keur": 42.0, "per_mw": 1.2,
            "cont_pct": None, "cont_cost": None,
            "vat_rate_pct": None, "vat_cost": None,
            "wth_pct": None, "depreciable": False,
            "schedule": _EVEN18,
            "comments": "Excel reference: 20260330_TUHO_BP CapEx",
            "children": [
                {
                    "code": "C.11.01", "name": "Auditors closing during construction",
                    "amount_keur": 25.0, "per_mw": 0.71,
                    "cont_pct": 6.0, "cont_cost": 1.5,
                    "vat_rate_pct": 13.0, "vat_cost": 3.25,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
                {
                    "code": "C.11.02", "name": "Accounting closing during construction",
                    "amount_keur": 11.0, "per_mw": 0.31,
                    "cont_pct": 6.0, "cont_cost": 0.66,
                    "vat_rate_pct": 13.0, "vat_cost": 1.43,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
                {
                    "code": "C.11.03", "name": "Legal closing during construction",
                    "amount_keur": 1.0, "per_mw": 0.03,
                    "cont_pct": 6.0, "cont_cost": 0.06,
                    "vat_rate_pct": 13.0, "vat_cost": 0.13,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
                {
                    "code": "C.11.04", "name": "Accounting book-keeping during construction",
                    "amount_keur": 5.0, "per_mw": 0.14,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 13.0, "vat_cost": 0.65,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
                {
                    "code": "C.11.05", "name": "Bank book-keeping during construction",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
                {
                    "code": "C.11.06", "name": "Legal Formalities during construction",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _EVEN18,
                    "comments": "",
                },
            ],
        },
        # C.12 Construction Management (Akuo)
        {
            "code": "C.12", "name": "Construction Mgmt (Akuo)",
            "amount_keur": 1742.25, "per_mw": 49.78,
            "cont_pct": None, "cont_cost": None,
            "vat_rate_pct": None, "vat_cost": None,
            "wth_pct": None, "depreciable": False,
            "schedule": _AT_FC,
            "comments": "Excel reference: 20260330_TUHO_BP CapEx",
            "children": [
                {
                    "code": "C.12.01", "name": "Akuo Construction Services",
                    "amount_keur": 1742.25, "per_mw": 49.78,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 13.0, "vat_cost": 226.49,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.12.02", "name": "External Construction Supervision",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.12.03", "name": "Geotechnical engineer",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.12.04", "name": "HSE (health and safety)",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.12.05", "name": "Quality & Quantities Control",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.12.06", "name": "Communication (inauguration etc.)",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.12.07", "name": "Others",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
            ],
        },
        # C.13 Contingencies
        {
            "code": "C.13", "name": "Contingencies",
            "amount_keur": 2991.54, "per_mw": 85.47,
            "cont_pct": 0.0, "cont_cost": None,
            "vat_rate_pct": 13.0, "vat_cost": 388.90,
            "wth_pct": 0.0, "depreciable": True,
            "schedule": _AT_FC,
            "comments": "Excel reference: 20260330_TUHO_BP CapEx",
            "children": [],
        },
        # C.14 Import Taxes
        {
            "code": "C.14", "name": "Import Taxes",
            "amount_keur": 0.0, "per_mw": 0.0,
            "cont_pct": None, "cont_cost": None,
            "vat_rate_pct": None, "vat_cost": None,
            "wth_pct": None, "depreciable": False,
            "schedule": _AT_FC,
            "comments": "Excel reference: 20260330_TUHO_BP CapEx",
            "children": [
                {
                    "code": "C.14.01", "name": "Import taxes, Customs clearance & Others",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.14.02", "name": "Taxes during construction",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
            ],
        },
        # C.15 Project Acquisition / Development
        {
            "code": "C.15", "name": "Project Acquisition / Development",
            "amount_keur": 0.0, "per_mw": 0.0,
            "cont_pct": None, "cont_cost": None,
            "vat_rate_pct": None, "vat_cost": None,
            "wth_pct": None, "depreciable": False,
            "schedule": _AT_FC,
            "comments": "Excel reference: 20260330_TUHO_BP CapEx",
            "children": [],
        },
        # C.16 Project Rights
        {
            "code": "C.16", "name": "Project Rights",
            "amount_keur": 14739.15, "per_mw": 421.12,
            "cont_pct": None, "cont_cost": None,
            "vat_rate_pct": None, "vat_cost": None,
            "wth_pct": None, "depreciable": False,
            "schedule": _AT_FC,
            "comments": "Excel reference: 20260330_TUHO_BP CapEx",
            "children": [
                {
                    "code": "C.16.01", "name": "Akuo Development Services",
                    "amount_keur": 2739.15, "per_mw": 78.26,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.16.02", "name": "Development costs",
                    "amount_keur": 2000.0, "per_mw": 57.14,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
                {
                    "code": "C.16.03", "name": "Project Purchase Cost",
                    "amount_keur": 10000.0, "per_mw": 285.71,
                    "cont_pct": 0.0, "cont_cost": 0.0,
                    "vat_rate_pct": 0.0, "vat_cost": 0.0,
                    "wth_pct": 0.0, "depreciable": True,
                    "schedule": _AT_FC,
                    "comments": "",
                },
            ],
        },
        # C.17 Financing Costs — backend-calculated
        {
            "code": "C.17", "name": "Financing Costs",
            "amount_keur": 2302.17, "per_mw": None,
            "cont_pct": None, "cont_cost": None,
            "vat_rate_pct": None, "vat_cost": None,
            "wth_pct": None, "depreciable": False,
            "schedule": _NO_SCHEDULE,
            "is_backend_calculated": True,
            "comments": "Excel reference: 20260330_TUHO_BP CapEx — backend-calculated",
            "children": [
                {
                    "code": "C.17.01", "name": "Bank Fees",
                    "amount_keur": 0.0, "per_mw": 0.0,
                    "cont_pct": None, "cont_cost": None,
                    "vat_rate_pct": None, "vat_cost": None,
                    "wth_pct": None, "depreciable": False,
                    "schedule": _NO_SCHEDULE,
                    "is_backend_calculated": True,
                    "comments": "",
                },
                {
                    "code": "C.17.02", "name": "IDCs LT debt",
                    "amount_keur": 1519.56, "per_mw": None,
                    "cont_pct": None, "cont_cost": None,
                    "vat_rate_pct": None, "vat_cost": None,
                    "wth_pct": None, "depreciable": False,
                    "schedule": _NO_SCHEDULE,
                    "is_backend_calculated": True,
                    "comments": "",
                },
                {
                    "code": "C.17.03", "name": "Commitment Fees LT debt",
                    "amount_keur": 166.72, "per_mw": None,
                    "cont_pct": None, "cont_cost": None,
                    "vat_rate_pct": None, "vat_cost": None,
                    "wth_pct": None, "depreciable": False,
                    "schedule": _NO_SCHEDULE,
                    "is_backend_calculated": True,
                    "comments": "",
                },
                {
                    "code": "C.17.04", "name": "Equity Arrangement Fees",
                    "amount_keur": 0.0, "per_mw": None,
                    "cont_pct": None, "cont_cost": None,
                    "vat_rate_pct": None, "vat_cost": None,
                    "wth_pct": None, "depreciable": False,
                    "schedule": _NO_SCHEDULE,
                    "is_backend_calculated": True,
                    "comments": "",
                },
                {
                    "code": "C.17.05", "name": "Transaction Management Costs",
                    "amount_keur": 0.0, "per_mw": None,
                    "cont_pct": None, "cont_cost": None,
                    "vat_rate_pct": None, "vat_cost": None,
                    "wth_pct": None, "depreciable": False,
                    "schedule": _NO_SCHEDULE,
                    "is_backend_calculated": True,
                    "comments": "",
                },
            ],
        },
        # C.18 Reserve Accounts — backend-calculated
        {
            "code": "C.18", "name": "Reserve Accounts",
            "amount_keur": 0.0, "per_mw": None,
            "cont_pct": None, "cont_cost": None,
            "vat_rate_pct": None, "vat_cost": None,
            "wth_pct": None, "depreciable": False,
            "schedule": _NO_SCHEDULE,
            "is_backend_calculated": True,
            "comments": "Excel reference: 20260330_TUHO_BP CapEx — backend-calculated",
            "children": [
                {
                    "code": "C.18.01", "name": "DSRA",
                    "amount_keur": 0.0, "per_mw": None,
                    "cont_pct": None, "cont_cost": None,
                    "vat_rate_pct": None, "vat_cost": None,
                    "wth_pct": None, "depreciable": False,
                    "schedule": _NO_SCHEDULE,
                    "is_backend_calculated": True,
                    "comments": "",
                },
                {
                    "code": "C.18.02", "name": "MMRA",
                    "amount_keur": 0.0, "per_mw": None,
                    "cont_pct": None, "cont_cost": None,
                    "vat_rate_pct": None, "vat_cost": None,
                    "wth_pct": None, "depreciable": False,
                    "schedule": _NO_SCHEDULE,
                    "is_backend_calculated": True,
                    "comments": "",
                },
                {
                    "code": "C.18.03", "name": "Working Capital + Cash equivalents",
                    "amount_keur": 0.0, "per_mw": None,
                    "cont_pct": None, "cont_cost": None,
                    "vat_rate_pct": None, "vat_cost": None,
                    "wth_pct": None, "depreciable": False,
                    "schedule": _NO_SCHEDULE,
                    "is_backend_calculated": True,
                    "comments": "",
                },
            ],
        },
    ]

    # ── App CapexStructure mapping ────────────────────────────────────────
    # Maps app CapexStructure field names → Excel category for app amount
    _APP_MAP = {
        "production_units":   ("C.01", 0.0),     # app=0, excel=35000 → unmapped
        "epc_contract":       ("C.02", 52800.0), # app=52800, excel=13560 → model_mismatch
        "epc_other":          ("C.02", 2100.0),  # app=2100, excel=0 → partial (dev&perm)
        "grid_connection":    ("C.03", 6200.0),   # app=6200, excel=30 → model_mismatch
        "ops_prep":           ("C.09", 1200.0),  # maps to C.09
        "insurances":         ("C.06", 0.0),      # app=0, excel=469 → unmapped
        "lease_tax":          ("C.07", 0.0),     # app=0, excel=512 → unmapped
        "construction_mgmt_a":("C.09", 5400.0),  # app=5400, excel=40 → model_mismatch
        "commissioning":      ("C.10", 0.0),      # app=0, excel=0 → unmapped
        "audit_legal":        ("C.11", 200.0),   # app=200, excel=42 → partial
        "construction_mgmt_b":("C.12", 0.0),     # app=0, excel=1742 → unmapped
        "contingencies":      ("C.13", 2991.54),  # app=2991, excel=3037 → partial
        "taxes":              ("C.14", 0.0),      # app=0, excel=0 → unmapped
        "project_acquisition":("C.15", 1000.0),  # app=1000, excel=0 → model_mismatch
        "project_rights":     ("C.16", 0.0),     # app=0, excel=14739 → unmapped
        "idc_keur":           ("C.17", 1519.56), # backend
        "bank_fees_keur":     ("C.17", 782.61),  # backend
        "commitment_fees_keur":("C.17", 188.60), # backend
        "other_financial_keur":("C.17", 0.0),   # backend
        "vat_costs_keur":     ("C.17", 33.49),   # backend (part of financing)
        "reserve_accounts_keur":("C.18", 0.0),  # backend
    }

    # Build app amount lookups
    # _app_amount_by_cat: Excel category code → total app amount (sum of mapped fields)
    _app_amount_by_cat: dict[str, float] = {}
    # _app_amount_by_code: Excel sub-code → app field name → amount (for sub-row display)
    _app_field_for_code: dict[str, str] = {}  # excel_code like "C.17.02" → app field name

    for fname, (cat_code, _app_val) in _APP_MAP.items():
        if not hasattr(capex, fname):
            continue
        actual = getattr(capex, fname)
        # CapexItem fields have .amount_keur; financing fields are floats
        if hasattr(actual, "amount_keur"):
            amount = actual.amount_keur
        elif isinstance(actual, (int, float)):
            amount = float(actual)
        else:
            continue
        _app_amount_by_cat[cat_code] = _app_amount_by_cat.get(cat_code, 0.0) + amount
        # Also store field name for per-sub-row lookup
        # C.17.xx → individual financing fields
        if cat_code == "C.17" and fname.endswith("_keur"):
            if fname == "idc_keur":
                _app_field_for_code["C.17.02"] = fname
            elif fname == "bank_fees_keur":
                _app_field_for_code["C.17.01"] = fname
            elif fname == "commitment_fees_keur":
                _app_field_for_code["C.17.03"] = fname
            elif fname == "vat_costs_keur":
                pass  # part of IDC in some models
            elif fname == "other_financial_keur":
                pass
        if cat_code == "C.18" and fname == "reserve_accounts_keur":
            _app_field_for_code["C.18.01"] = fname

    # ── Phase 21B: Runtime authority ──────────────────────────────────────
    # Which app fields are READ by runtime calculations (CFADS, debt sizing).
    # Only fields in this set may be marked backend_authoritative.
    _RUNTIME_SOURCE_FIELDS: set[str] = {
        "idc_keur",           # used in debt sizing (senior draw schedule)
        "bank_fees_keur",     # used in financing total → debt sizing
        "commitment_fees_keur", # used in financing total → debt sizing
        "shl_idc_keur",       # used in SHL tranche opening balance
        "reserve_accounts_keur", # DSRA / MMRA / working capital in cash model
        # contingencies is NOT directly read from capex in runtime;
        # it is embedded in the capex total which is used.
        # So we list it as runtime-affecting via the capex total.
    }

    # Which CapexStructure fields map to which Excel sub-code.
    # Key: Excel code like "C.02.01", Value: (app_field_name, affects_runtime)
    _EXCEL_CODE_TO_APP_FIELD: dict[str, tuple[str, bool]] = {
        # C.01 — Production Unit (no app field maps to sub-items)
        # C.02 — EPC Contract
        "C.02.01": ("epc_other",     False),  # Electrical BOP — part of epc_other
        "C.02.02": ("epc_other",     False),  # Connection to existing grid
        "C.02.03": ("epc_other",     False),  # Civil BOP
        "C.02.04": ("grid_connection", False), # Grid connection
        # C.03 — Grid Connection
        "C.03.01": ("grid_connection", False),
        "C.03.02": ("grid_connection", False),
        # C.04 — Monitoring (no app field)
        # C.05 — Operation Investments (no app field)
        # C.06 — Insurances
        "C.06.01": ("insurances",    False),
        # C.07 — Land Securing
        "C.07.01": ("lease_tax",     False),
        "C.07.02": ("lease_tax",     False),
        # C.08 — Bank Due Diligence
        "C.08.02": ("audit_legal",   False),  # bank due diligence mapped to audit_legal
        "C.08.08": ("audit_legal",   False),  # Legal Advisor
        # C.09 — Construction Management (Lender)
        "C.09.01": ("ops_prep",             False),
        "C.09.02": ("construction_mgmt_a",  False),
        # C.10 — Commissioning
        "C.10.01": ("commissioning",  False),
        # C.11 — Audit & Accounting & Legal
        "C.11.01": ("audit_legal",   False),
        "C.11.02": ("audit_legal",   False),
        "C.11.03": ("audit_legal",   False),
        # C.12 — Construction Mgmt (Akuo)
        "C.12.01": ("construction_mgmt_b", False),
        # C.13 — Contingencies
        "C.13":     ("contingencies", True),  # used in capex total → affects debt sizing
        # C.15 — Project Acquisition
        "C.15":     ("project_acquisition", False),
        # C.16 — Project Rights
        "C.16":     ("project_rights", False),
        # C.17 — Financing Costs (backend_calculated fields)
        "C.17.01": ("bank_fees_keur",         True),  # affects runtime (financing total)
        "C.17.02": ("idc_keur",               True),  # affects runtime (debt draw)
        "C.17.03": ("commitment_fees_keur",    True),  # affects runtime (financing total)
        # C.18 — Reserve Accounts (backend_calculated)
        "C.18.01": ("reserve_accounts_keur",  True),
        "C.18.02": ("reserve_accounts_keur",  True),
        "C.18.03": ("reserve_accounts_keur",  True),
    }

    def _get_field_value(field_name: str) -> float | None:
        """Resolve an app field value (handles CapexItem vs float types)."""
        if not hasattr(capex, field_name):
            return None
        actual = getattr(capex, field_name)
        if hasattr(actual, "amount_keur"):
            return actual.amount_keur
        elif isinstance(actual, (int, float)):
            return float(actual)
        return None

    def _scope_desc(code: str) -> str:
        """Return a short description of the app scope for scope_mismatch notes."""
        _SCOPE_DESCS = {
            "C.01.01": "no app production-unit field (Wind Turbines)",
            "C.02": "52,800 kEUR = 4-semester total EPC contract value",
            "C.03.01": "6,200 kEUR = full interconnection cost",
            "C.16.01": "no app field for Akuo development services",
            "C.16.02": "no app field for development costs",
            "C.16.03": "no app field for project purchase cost",
        }
        return _SCOPE_DESCS.get(code, "aggregate app value")

    def _classify_authority(
        excel_code: str,
        excel_amt: float,
        app_amt: float | None,
        runtime_field: str | None,
        affects_runtime: bool,
        is_backend_calculated: bool,
    ) -> tuple[str, str, str, bool, str, float | None, float | None]:
        """Classify authority status for a single child row.

        Returns: (authority_status, source_type, runtime_source_field,
                   affects_runtime, mapping_note,
                   mismatch_amount_keur, mismatch_pct)
        """
        if is_backend_calculated:
            # C.17 / C.18 — backend-calculated financing items
            src = runtime_field or ""
            note = f"Backend-calculated financing: {src}" if src else "Backend-calculated financing"
            if runtime_field and runtime_field in _RUNTIME_SOURCE_FIELDS:
                return ("backend_authoritative", "computed_runtime",
                        f"capex.{runtime_field}", True, note, None, None)
            else:
                return ("backend_authoritative", "computed_runtime",
                        f"capex.{runtime_field}" if runtime_field else None,
                        affects_runtime, note, None, None)

        if runtime_field and runtime_field in _RUNTIME_SOURCE_FIELDS:
            # App field that affects runtime — but this is a child row
            # and the category itself (C.13 contingencies) is the runtime source
            pass  # fall through to app_mapped

        if app_amt is None:
            # No app mapping at all
            if excel_amt > 0:
                return ("excel_reference_only", "excel_reference", None, False,
                        f"Excel reference only — no app field maps to {excel_code}",
                        None, None)
            else:
                return ("not_applicable", "excel_reference", None, False,
                        f"Zero or N/A in Excel and no app mapping", None, None)

        # App value exists
        if excel_amt == 0.0 and app_amt > 0:
            return ("mismatch", "app_input",
                    f"capex.{runtime_field}" if runtime_field else None, False,
                    f"App has {app_amt:,.2f} kEUR but Excel = 0 for {excel_code}",
                    app_amt, None)

        if excel_amt > 0:
            diff = abs(app_amt - excel_amt)
            diff_pct = diff / excel_amt * 100.0
            threshold = max(0.01 * excel_amt, 10.0)  # 1% or 10kEUR

            # Stage 1: detect scope-mismatch vs plain mismatch
            # EPC (C.02) app 52,800 = 4-semester total; Excel 13,560 = one-shot reference
            # C.03 Grid Connection app 6,200 = full interconnection; Excel 30 = GPA fee only
            # C.16 Project Rights app 0 ≠ Excel 14,739 — different model scope not comparable
            _SCM_CODES = {
                "C.01.01",  # Production Unit: app 0 (no field) vs Excel 35,000
                "C.02",     # EPC Contract: app 52,800 = 4-semester total; Excel 13,560 = per-batch reference
                "C.03.01",  # Grid Connection Agreement: app 6,200 vs Excel 30 (GPA fee only)
                "C.16.01",  # Akuo Development: app 0 vs Excel 2,739
                "C.16.02",  # Development costs: app 0 vs Excel 2,000
                "C.16.03",  # Project Purchase Cost: app 0 vs Excel 10,000
            }
            if excel_code in _SCM_CODES:
                return ("scope_mismatch", "app_input",
                        f"capex.{runtime_field}" if runtime_field else None, False,
                        f"App {app_amt:,.2f} vs Excel {excel_amt:,.2f} kEUR — "
                        f"scopes differ: app is aggregate ({_scope_desc(excel_code)}, "
                        f"Excel is one-shot reference; diff {diff:,.2f} kEUR ({diff_pct:.1f}%)",
                        diff, round(diff_pct, 2))

            if diff > threshold:
                return ("mismatch", "app_input",
                        f"capex.{runtime_field}" if runtime_field else None, False,
                        f"App {app_amt:,.2f} vs Excel {excel_amt:,.2f} for {excel_code} — diff {diff:,.2f} kEUR ({diff_pct:.1f}%)",
                        diff, round(diff_pct, 2))
            else:
                return ("app_mapped", "app_input",
                        f"capex.{runtime_field}" if runtime_field else None, False,
                        f"App {app_amt:,.2f} vs Excel {excel_amt:,.2f} — within tolerance",
                        None, None)

        # excel_amt == 0 and app_amt == 0
        return ("not_applicable", "app_input",
                f"capex.{runtime_field}" if runtime_field else None, False,
                "Both Excel and app are zero", None, None)

    def _resolve_status(excel_amt: float, app_amt: float | None,
                        is_backend: bool) -> str:
        if is_backend:
            return "backend_calculated"
        if app_amt is None:
            return "unmapped"
        if app_amt == 0.0:
            return "unmapped" if excel_amt == 0.0 else "model_mismatch"
        if excel_amt == 0.0:
            return "model_mismatch"
        if abs(excel_amt - app_amt) / max(excel_amt, 1.0) > 0.05:
            return "model_mismatch"
        return "mapped"

    def _child_row(data: dict, is_backend: bool) -> dict:
        excel_amt = data.get("amount_keur", 0.0) or 0.0
        cat_code = data.get("parent_code", "")
        excel_code = data.get("code", "")


        # Phase 21C: Per-sub-row app amount resolution:
        # 1. Direct field mapping (financing C.17/C.18): use individual app field value
        # 2. C.02.04 (Grid connection) and C.03.01/02 (Grid usage): use grid_connection
        #    which holds app total 6,200 kEUR (full interconnection scope)
        # 3. C.16.01/02/03 (Project Rights): resolve against project_rights (app=0)
        #    but pass excel=2739/2000/10000 so classify_authority can emit scope_mismatch
        # 4. C.02 category row: use epc_contract (52,800) for 4-semester totals
        # 5. Single-field categories (C.13, C.15): use category total
        # 6. Unmapped categories: app_amount=None, status=unmapped
        app_amt: float | None = None
        runtime_field: str | None = None
        affects_runtime = False

        if excel_code in _app_field_for_code:
            # Direct individual field mapping (financing sub-items)
            fname = _app_field_for_code[excel_code]
            actual = getattr(capex, fname)
            if hasattr(actual, "amount_keur"):
                app_amt = actual.amount_keur
            elif isinstance(actual, (int, float)):
                app_amt = float(actual)
            runtime_field = fname
            affects_runtime = fname in _RUNTIME_SOURCE_FIELDS
        elif excel_code in _EXCEL_CODE_TO_APP_FIELD:
            fname, afrt = _EXCEL_CODE_TO_APP_FIELD[excel_code]
            app_amt = _get_field_value(fname)
            runtime_field = fname
            affects_runtime = afrt
        elif cat_code in _app_amount_by_cat:
            # Single-field categories: C.13, C.15, C.16
            # (categories where the category row IS the child)
            if cat_code in ("C.13", "C.15", "C.16"):
                app_amt = _app_amount_by_cat.get(cat_code)
                if cat_code in _EXCEL_CODE_TO_APP_FIELD:
                    fname, afrt = _EXCEL_CODE_TO_APP_FIELD[cat_code]
                    runtime_field = fname
                    affects_runtime = afrt
            # C.09 maps two app fields (ops_prep + construction_mgmt_a) →
            # category total would be misleading per sub-item; skip

        status = _resolve_status(excel_amt, app_amt, is_backend)
        delta = (round(app_amt - excel_amt, 2)) if (app_amt is not None and excel_amt != 0) else None

        # ── Phase 21B authority classification ──────────────────────────
        (authority_status, source_type, rs_field,
         af_rt, mapping_note, mismatch_amt, mismatch_pct) = _classify_authority(
            excel_code, excel_amt, app_amt,
            runtime_field, affects_runtime, is_backend)

        # monthly_schedule_source
        sched = data.get("schedule")
        if sched is _NO_SCHEDULE or sched is None:
            sched_src = "missing" if not is_backend else "static_reference"
        elif sched == _EVEN18:
            sched_src = "excel_m1_m18"
        elif sched == _AT_FC:
            sched_src = "excel_m1_m18"  # FC = M1 in 18-month model
        elif isinstance(sched, tuple) and len(sched) == 18:
            sched_src = "excel_m1_m18"
        else:
            sched_src = "static_reference"

        return {
            "code": data["code"],
            "name": data["name"],
            "amount_keur": excel_amt,
            "app_amount_keur": app_amt,
            "per_mw": data.get("per_mw"),
            "mapping_status": status,
            "delta_keur": delta,
            "contingency_pct": data.get("cont_pct"),
            "contingency_cost_keur": data.get("cont_cost"),
            "vat_rate_pct": data.get("vat_rate_pct"),
            "vat_cost_keur": data.get("vat_cost"),
            "wth_rate_pct": data.get("wth_pct"),
            "depreciable": data.get("depreciable", False),
            "comments": data.get("comments", ""),
            "monthly_schedule": sched,
            "is_backend_calculated": is_backend,
            # ── Phase 21B authority metadata ──────────────────────────────
            "authority_status": authority_status,
            "source_type": source_type,
            "runtime_source_field": rs_field,
            "affects_runtime": af_rt,
            "mapping_note": mapping_note,
            "mismatch_amount_keur": mismatch_amt,
            "mismatch_pct": mismatch_pct,
            "monthly_schedule_source": sched_src,
        }

    # ── Build categories ──────────────────────────────────────────────────
    categories = []
    grand_total = 0.0
    hard_total = 0.0
    financing_total = 0.0

    for cat_data in _EXCEL_ROWS:
        is_backend = cat_data.get("is_backend_calculated", False)
        cat_amount = cat_data.get("amount_keur", 0.0) or 0.0

        if is_backend:
            financing_total += cat_amount
        else:
            hard_total += cat_amount
        grand_total += cat_amount

        children = []
        for child_data in cat_data.get("children", []):
            child_data["parent_code"] = cat_data["code"]
            children.append(_child_row(child_data, is_backend))

        # If no children, add the category as its own child (for C.13, C.15 with no sub-lines)
        if not children:
            child_data = {
                "code": cat_data["code"],
                "name": cat_data["name"],
                "amount_keur": cat_amount,
                "per_mw": cat_data.get("per_mw"),
                "parent_code": cat_data["code"],
                "cont_pct": cat_data.get("cont_pct"),
                "cont_cost": cat_data.get("cont_cost"),
                "vat_rate_pct": cat_data.get("vat_rate_pct"),
                "vat_cost": cat_data.get("vat_cost"),
                "wth_pct": cat_data.get("wth_pct"),
                "depreciable": cat_data.get("depreciable", False),
                "schedule": cat_data.get("schedule"),
                "comments": cat_data.get("comments", ""),
            }
            children.append(_child_row(child_data, is_backend))

        # ── Phase 21B: authority_summary per category ──────────────────
        _STATUS_COUNTS = {"backend_authoritative": 0, "app_mapped": 0,
                           "excel_reference_only": 0, "missing_runtime_source": 0,
                           "mismatch": 0, "deferred": 0, "not_applicable": 0,
                           "scope_mismatch": 0}
        for ch in children:
            s = ch.get("authority_status", "")
            if s in _STATUS_COUNTS:
                _STATUS_COUNTS[s] += 1

        cat = {
            "code": cat_data["code"],
            "name": cat_data["name"],
            "is_backend_calculated": is_backend,
            "comments": cat_data.get("comments", ""),
            "children": tuple(children),
            "authority_summary": dict(_STATUS_COUNTS),
        }
        categories.append(cat)

    # ── Phase 21B: top-level authority_summary ─────────────────────────────
    _TOP_COUNTS = {"backend_authoritative": 0, "app_mapped": 0,
                   "excel_reference_only": 0, "missing_runtime_source": 0,
                   "mismatch": 0, "deferred": 0, "not_applicable": 0,
                   "scope_mismatch": 0}
    _total_rows = 0
    for cat in categories:
        for k, v in cat["authority_summary"].items():
            if k in _TOP_COUNTS:
                _TOP_COUNTS[k] += v
        _total_rows += len(cat["children"])
    top_authority_summary = dict(_TOP_COUNTS)
    top_authority_summary["_total_child_rows"] = _total_rows

    return {
        "categories": tuple(categories),
        "grand_total_keur": round(grand_total, 2),
        "hard_capex_total_keur": round(hard_total, 2),
        "financing_total_keur": round(financing_total, 2),
        "construction_months": construction_months,
        "authority_summary": top_authority_summary,
    }


def _build_capex_items(capex) -> tuple[dict[str, Any], ...]:
    """"Build serialisable CAPEX item list from CapexStructure."""
    items = []
    for field in capex._CAPEX_ITEM_FIELDS:
        item = getattr(capex, field)
        items.append(
            {
                "code": field,
                "name": item.name,
                "amount_keur": item.amount_keur,
                "y0_share": item.y0_share,
            }
        )
    # Financing/legal
    items.append({"code": "idc", "name": "IDC", "amount_keur": capex.idc_keur, "y0_share": 0.0})
    items.append({"code": "bank_fees", "name": "Bank Fees", "amount_keur": capex.bank_fees_keur, "y0_share": 0.0})
    items.append({"code": "commitment_fees", "name": "Commitment Fees", "amount_keur": capex.commitment_fees_keur, "y0_share": 0.0})
    items.append({"code": "other_financial", "name": "Other Financial", "amount_keur": capex.other_financial_keur, "y0_share": 0.0})
    items.append({"code": "vat_costs", "name": "VAT Costs", "amount_keur": capex.vat_costs_keur, "y0_share": 0.0})
    items.append({"code": "reserve_accounts", "name": "Reserve Accounts", "amount_keur": capex.reserve_accounts_keur, "y0_share": 0.0})
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
    opex_items = _build_opex_items(project_inputs, horizon_years=project_inputs.info.horizon_years)
    opex_detail = _build_opex_detail_items(project_inputs, code=code, horizon_years=project_inputs.info.horizon_years)
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
        revenue_items=_build_revenue_items(revenue, technical, technology),
        opex_items=opex_items,
        opex_detail_items=opex_detail["categories"],
        opex_y1_total_keur=_opex_y1_total(project_inputs),
        opex_contingency_method=opex_contingency_method,
        opex_contingency_pct=opex_contingency_pct,
        capex_items=_build_capex_items(capex),
        capex_detail_items=_build_capex_detail_items(
            capex, construction_months=project_inputs.info.construction_months
        )["categories"],
        capex_construction_months=project_inputs.info.construction_months,
        capex_y1_total_keur=_capex_y1_total(capex),
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
        construction_items=_build_construction_items(project_inputs),
        idc_items=_build_idc_items(project_inputs),
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

    # ── For user-created projects: preserve full OPEX detail from template origin ──
    # If seeded from tuho/oborovo, use the full detailed opex_detail_items from
    # that base (B.01–B.13 with children) rather than falling back to flat generic.
    # For generic_wind/generic_solar without specific origin, keep existing behavior.
    opex_detail_items_for_user_project: tuple[dict[str, Any], ...] | None = None
    if seed_key in ("tuho", "oborovo"):
        opex_detail_items_for_user_project = base.opex_detail_items

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
        capex_items=base.capex_items,
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
