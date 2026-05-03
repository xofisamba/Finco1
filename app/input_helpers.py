"""Pure input summary builders — used by both UI and Excel export."""
from __future__ import annotations
from typing import Any
import pandas as pd


def build_inputs_summary_table(project_inputs) -> pd.DataFrame:
    """Build a clean summary table of key project inputs."""
    if project_inputs is None:
        return pd.DataFrame(columns=["Field", "Value"])
    info = getattr(project_inputs, 'info', None)
    technical = getattr(project_inputs, 'technical', None)
    revenue = getattr(project_inputs, 'revenue', None)
    financing = getattr(project_inputs, 'financing', None)
    rows = []
    if info:
        rows.extend([
            ("Name", getattr(info, 'name', 'n/a')),
            ("Code", getattr(info, 'code', 'n/a')),
            ("Country", getattr(info, 'country_iso', 'n/a')),
            ("Horizon Years", getattr(info, 'horizon_years', 'n/a')),
            ("Construction Months", getattr(info, 'construction_months', 'n/a')),
            ("PPA Term (years)", getattr(revenue, 'ppa_term_years', 'n/a') if revenue else 'n/a'),
            ("Financial Close", str(getattr(info, 'financial_close', 'n/a'))),
        ])
    if technical:
        rows.extend([
            ("Technology", getattr(technical, 'yield_scenario', 'n/a')),
            ("Capacity (MW)", getattr(technical, 'capacity_mw', 'n/a')),
            ("P50 Hours", getattr(technical, 'operating_hours_p50', 'n/a')),
            ("Availability", getattr(technical, 'plant_availability', 'n/a')),
            ("Degradation", getattr(technical, 'pv_degradation', 'n/a')),
        ])
    if revenue:
        rows.extend([
            ("PPA Tariff", getattr(revenue, 'ppa_base_tariff', 'n/a')),
            ("PPA Index", getattr(revenue, 'ppa_index', 'n/a')),
        ])
    if financing:
        rows.extend([
            ("Target DSCR", getattr(financing, 'target_dscr', 'n/a')),
            ("Senior Tenor (years)", getattr(financing, 'senior_tenor_years', 'n/a')),
            ("All-in Rate", getattr(financing, 'all_in_rate', 'n/a') if hasattr(financing, 'all_in_rate') else 'n/a'),
        ])
    if not rows:
        return pd.DataFrame(columns=["Field", "Value"])
    return pd.DataFrame(rows, columns=["Field", "Value"])


def build_capex_summary_table(project_inputs) -> pd.DataFrame:
    """Build CapEx summary table."""
    if project_inputs is None:
        return pd.DataFrame(columns=["Field", "Value"])
    capex = getattr(project_inputs, 'capex', None)
    if capex is None:
        return pd.DataFrame(columns=["Field", "Value"])
    total_capex = getattr(capex, 'total_capex', None) or getattr(capex, 'total_capex_keur', 'n/a')
    sculpt_capex = getattr(capex, 'sculpt_capex_keur', 'n/a')
    rows = [
        ("Total CapEx (kEUR)", total_capex),
        ("Sculpt CapEx (kEUR)", sculpt_capex),
    ]
    return pd.DataFrame(rows, columns=["Field", "Value"])


def build_capex_items_table(project_inputs) -> pd.DataFrame:
    """Build CapEx items table if available."""
    if project_inputs is None:
        return pd.DataFrame(columns=["Name", "Asset Class", "Amount (kEUR)", "Life (years)"])
    capex = getattr(project_inputs, 'capex', None)
    if capex is None:
        return pd.DataFrame(columns=["Name", "Asset Class", "Amount (kEUR)", "Life (years)"])
    items = getattr(capex, 'capex_items', None)()
    if not items:
        return pd.DataFrame(columns=["Name", "Asset Class", "Amount (kEUR)", "Life (years)"])
    rows = []
    for item in items:
        rows.append((
            getattr(item, 'name', getattr(item, 'description', 'n/a')),
            str(getattr(item, 'asset_class', 'n/a')),
            getattr(item, 'amount_keur', 'n/a'),
            getattr(item, 'useful_life_override', 'n/a'),
        ))
    return pd.DataFrame(rows, columns=["Name", "Asset Class", "Amount (kEUR)", "Life (years)"])
