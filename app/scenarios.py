"""Scenario engine — pure functions, no Streamlit imports."""
from dataclasses import is_dataclass, replace
from app.capex_overrides import scale_capex_items


def _first_existing_field(obj, candidates):
    """Return first existing field name found on obj."""
    for c in candidates:
        if hasattr(obj, c):
            return c
    return None


# ── scenario rules ──────────────────────────────────────────────────────────

SCENARIO_RULES = {
    "base": {
        "p50_multiplier": 1.0,
        "capex_multiplier": 1.0,
        "tariff_multiplier": 1.0,
    },
    "downside": {
        "p50_multiplier": 0.90,   # -10%
        "capex_multiplier": 1.05,  # +5%
        "tariff_multiplier": 0.95, # -5%
    },
    "upside": {
        "p50_multiplier": 1.05,   # +5%
        "capex_multiplier": 0.97, # -3%
        "tariff_multiplier": 1.03, # +3%
    },
}

P50_FIELDS = ("p50_hours", "operating_hours_p50", "full_load_hours", "equivalent_hours")
TARIFF_FIELDS = ("ppa_base_tariff", "merchant_price", "merchant_price_eur_mwh", "base_price", "tariff")

def get_scenario_rules(scenario: str):
    """Return explicit rule dict for a scenario."""
    key = scenario.lower()
    if key not in SCENARIO_RULES:
        raise ValueError(f"Unknown scenario {scenario!r}. Valid: Base, Downside, Upside")
    return SCENARIO_RULES[key]

def apply_scenario(project_inputs, scenario: str):
    """Apply scenario to project inputs. Returns NEW ProjectInputs, original unchanged."""
    scenario = scenario.lower()
    if scenario not in SCENARIO_RULES:
        raise ValueError(f"Unknown scenario {scenario!r}. Valid: Base, Downside, Upside")

    rules = SCENARIO_RULES[scenario]
    p50_mult = rules["p50_multiplier"]
    capex_mult = rules["capex_multiplier"]
    tariff_mult = rules["tariff_multiplier"]

    # P50 hours — only use replace() on dataclass sub-objects
    tech = project_inputs.technical
    p50_field = _first_existing_field(tech, P50_FIELDS)
    if p50_field and p50_mult != 1.0:
        new_val = getattr(tech, p50_field) * p50_mult
        if is_dataclass(tech):
            tech = replace(tech, **{p50_field: new_val})
        else:
            tech = _set_attribute(tech, p50_field, new_val)

    # CapEx
    capex = project_inputs.capex
    if capex_mult != 1.0 and capex.total_capex > 0:
        capex = scale_capex_items(capex, capex.total_capex * capex_mult)

    # Tariff
    rev = project_inputs.revenue
    tariff_field = _first_existing_field(rev, TARIFF_FIELDS)
    if tariff_field and tariff_mult != 1.0:
        new_val = getattr(rev, tariff_field) * tariff_mult
        if is_dataclass(rev):
            rev = replace(rev, **{tariff_field: new_val})
        else:
            rev = _set_attribute(rev, tariff_field, new_val)

    # Only use replace() on ProjectInputs if it's a dataclass
    if is_dataclass(project_inputs):
        result = replace(project_inputs, technical=tech, capex=capex, revenue=rev)
    else:
        result = project_inputs
        result = _set_attribute(result, "technical", tech)
        result = _set_attribute(result, "capex", capex)
        result = _set_attribute(result, "revenue", rev)
    return result


def _set_attribute(obj, name, value):
    """Set attribute on an object without replace(). For non-dataclass objects."""
    import copy
    obj = copy.copy(obj)
    setattr(obj, name, value)
    return obj

def scenario_summary(scenario: str):
    """Return list of dicts describing scenario deltas."""
    rules = get_scenario_rules(scenario)
    rows = []
    p50_mult = rules["p50_multiplier"]
    capex_mult = rules["capex_multiplier"]
    tariff_mult = rules["tariff_multiplier"]

    if p50_mult != 1.0:
        rows.append({"assumption": "P50 Hours", "base": "—", "scenario": f"{p50_mult:.0%}",
                     "change": f"{'+' if p50_mult > 1 else ''}{(p50_mult - 1) * 100:.0f}%",
                     "note": "applied to first available p50 field"})
    if capex_mult != 1.0:
        rows.append({"assumption": "Total CapEx", "base": "—", "scenario": f"{capex_mult:.0%}",
                     "change": f"{'+' if capex_mult > 1 else ''}{(capex_mult - 1) * 100:.0f}%",
                     "note": "CapexItem line items scaled proportionally"})
    if tariff_mult != 1.0:
        rows.append({"assumption": "PPA Tariff", "base": "—", "scenario": f"{tariff_mult:.0%}",
                     "change": f"{'+' if tariff_mult > 1 else ''}{(tariff_mult - 1) * 100:.0f}%",
                     "note": "applied to first available tariff field"})

    if not rows:
        rows.append({"assumption": "All assumptions", "base": "—", "scenario": "Base",
                     "change": "0%", "note": "no changes from base case"})
    return rows