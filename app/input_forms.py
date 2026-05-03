"""Editable input forms for Solar and Wind demo projects."""
from __future__ import annotations
from dataclasses import replace
from typing import Any
import streamlit as st


def apply_project_overrides(project_inputs, overrides: dict[str, Any]) -> Any:
    """Apply overrides to a ProjectInputs dataclass using dataclasses.replace().
    
    Only modifies nested objects for keys present in overrides.
    Preserves all unmodified fields.
    """
    if not overrides:
        return project_inputs
    
    # Technical
    if 'technical' in overrides:
        old_tech = project_inputs.technical
        new_tech = replace(old_tech, **{k: v for k, v in overrides['technical'].items() if v is not None})
        project_inputs = replace(project_inputs, technical=new_tech)
    
    # Revenue
    if 'revenue' in overrides:
        old_rev = project_inputs.revenue
        new_rev = replace(old_rev, **{k: v for k, v in overrides['revenue'].items() if v is not None})
        project_inputs = replace(project_inputs, revenue=new_rev)
    
    # CapEx
    if 'capex' in overrides:
        old_capex = project_inputs.capex
        new_capex = replace(old_capex, **{k: v for k, v in overrides['capex'].items() if v is not None})
        project_inputs = replace(project_inputs, capex=new_capex)
    
    # Financing
    if 'financing' in overrides:
        old_fin = project_inputs.financing
        new_fin = replace(old_fin, **{k: v for k, v in overrides['financing'].items() if v is not None})
        project_inputs = replace(project_inputs, financing=new_fin)
    
    # Tax
    if 'tax' in overrides:
        old_tax = project_inputs.tax
        new_tax = replace(old_tax, **{k: v for k, v in overrides['tax'].items() if v is not None})
        project_inputs = replace(project_inputs, tax=new_tax)
    
    # Info
    if 'info' in overrides:
        old_info = project_inputs.info
        new_info = replace(old_info, **{k: v for k, v in overrides['info'].items() if v is not None})
        project_inputs = replace(project_inputs, info=new_info)
    
    return project_inputs


def render_solar_input_form(project_inputs) -> tuple[Any, bool]:
    """Render editable form for Solar project.
    
    Returns (modified_project_inputs, was_modified).
    """
    st.subheader("☀️ Solar Project Inputs")
    
    # Technical
    st.markdown("**Technical**")
    tech_cols = st.columns(2)
    with tech_cols[0]:
        capacity = st.number_input(
            "Capacity (MW)", value=float(project_inputs.technical.capacity_mw),
            min_value=0.1, max_value=2000.0, step=1.0, key="solar_capacity"
        )
        availability = st.number_input(
            "Availability (%)", value=float(project_inputs.technical.plant_availability * 100),
            min_value=80.0, max_value=99.9, step=0.1, key="solar_avail"
        )
    with tech_cols[1]:
        p50_h = st.number_input(
            "P50 Hours", value=float(project_inputs.technical.operating_hours_p50),
            min_value=500, max_value=3500, step=50, key="solar_p50"
        )
        degradation = st.number_input(
            "Degradation (%/yr)", value=float(project_inputs.technical.pv_degradation * 100),
            min_value=0.0, max_value=2.0, step=0.05, key="solar_deg"
        )
    
    # Revenue
    st.markdown("**Revenue**")
    rev_cols = st.columns(2)
    with rev_cols[0]:
        tariff = st.number_input(
            "PPA Tariff (EUR/MWh)", value=float(project_inputs.revenue.ppa_base_tariff),
            min_value=0.0, max_value=500.0, step=1.0, key="solar_tariff"
        )
    with rev_cols[1]:
        ppa_term = st.number_input(
            "PPA Term (years)", value=int(project_inputs.revenue.ppa_term_years),
            min_value=5, max_value=40, step=1, key="solar_ppa_term"
        )
    
    # CapEx
    st.markdown("**CapEx**")
    capex_cols = st.columns(2)
    with capex_cols[0]:
        total_capex = st.number_input(
            "Total CapEx (kEUR)", value=float(project_inputs.capex.total_capex),
            min_value=0.0, step=1000.0, key="solar_total_capex"
        )
    with capex_cols[1]:
        sculpt_capex = st.number_input(
            "Sculpt CapEx (kEUR)", value=float(getattr(project_inputs.capex, 'sculpt_capex_keur', 0.0)),
            min_value=0.0, step=1000.0, key="solar_sculpt_capex"
        )
    
    # Financing
    st.markdown("**Financing**")
    fin_cols = st.columns(3)
    with fin_cols[0]:
        target_dscr = st.number_input(
            "Target DSCR", value=float(project_inputs.financing.target_dscr),
            min_value=1.0, max_value=3.0, step=0.05, key="solar_dscr"
        )
    with fin_cols[1]:
        senior_tenor = st.number_input(
            "Senior Tenor (years)", value=int(project_inputs.financing.senior_tenor_years),
            min_value=1, max_value=30, step=1, key="solar_tenor"
        )
    with fin_cols[2]:
        all_in_rate = st.number_input(
            "All-in Rate (%)", value=float(project_inputs.financing.all_in_rate * 100),
            min_value=0.0, max_value=20.0, step=0.1, key="solar_rate"
        )
    
    # Tax
    st.markdown("**Tax**")
    corp_tax = st.number_input(
        "Corporate Tax Rate (%)", value=float(project_inputs.tax.corporate_rate * 100),
        min_value=0.0, max_value=50.0, step=0.5, key="solar_corp_tax"
    )
    
    modified = st.button("Apply Solar inputs and rerun", key="apply_solar")
    
    if modified:
        overrides = {
            'technical': {
                'capacity_mw': capacity,
                'plant_availability': availability / 100,
                'operating_hours_p50': p50_h,
                'pv_degradation': degradation / 100,
            },
            'revenue': {
                'ppa_base_tariff': tariff,
                'ppa_term_years': ppa_term,
            },
            'capex': {
                'total_capex': total_capex,
                'sculpt_capex_keur': sculpt_capex,
            },
            'financing': {
                'target_dscr': target_dscr,
                'senior_tenor_years': senior_tenor,
                'base_rate': all_in_rate / 100 - project_inputs.financing.margin_bps / 10000,
            },
            'tax': {
                'corporate_rate': corp_tax / 100,
            },
        }
        return apply_project_overrides(project_inputs, overrides), True
    
    return project_inputs, False


def render_wind_input_form(project_inputs) -> tuple[Any, bool]:
    """Render editable form for Wind project."""
    st.subheader("🌬️ Wind Project Inputs")
    
    tech_cols = st.columns(2)
    with tech_cols[0]:
        capacity = st.number_input(
            "Capacity (MW)", value=float(project_inputs.technical.capacity_mw),
            min_value=0.1, max_value=3000.0, step=1.0, key="wind_capacity"
        )
        availability = st.number_input(
            "Availability (%)", value=float(project_inputs.technical.plant_availability * 100),
            min_value=80.0, max_value=99.9, step=0.1, key="wind_avail"
        )
    with tech_cols[1]:
        p50_h = st.number_input(
            "P50 Hours", value=float(project_inputs.technical.operating_hours_p50),
            min_value=1500, max_value=4500, step=50, key="wind_p50"
        )
        degradation = st.number_input(
            "Degradation (%/yr)", value=float(project_inputs.technical.pv_degradation * 100),
            min_value=0.0, max_value=2.0, step=0.05, key="wind_deg"
        )
    
    st.markdown("**Revenue**")
    rev_cols = st.columns(2)
    with rev_cols[0]:
        tariff = st.number_input(
            "PPA Tariff (EUR/MWh)", value=float(project_inputs.revenue.ppa_base_tariff),
            min_value=0.0, max_value=500.0, step=1.0, key="wind_tariff"
        )
    with rev_cols[1]:
        ppa_term = st.number_input(
            "PPA Term (years)", value=int(project_inputs.revenue.ppa_term_years),
            min_value=5, max_value=40, step=1, key="wind_ppa_term"
        )
    
    st.markdown("**CapEx**")
    capex_cols = st.columns(2)
    with capex_cols[0]:
        total_capex = st.number_input(
            "Total CapEx (kEUR)", value=float(project_inputs.capex.total_capex),
            min_value=0.0, step=1000.0, key="wind_total_capex"
        )
    with capex_cols[1]:
        sculpt_capex = st.number_input(
            "Sculpt CapEx (kEUR)", value=float(getattr(project_inputs.capex, 'sculpt_capex_keur', 0.0)),
            min_value=0.0, step=1000.0, key="wind_sculpt_capex"
        )
    
    st.markdown("**Financing**")
    fin_cols = st.columns(3)
    with fin_cols[0]:
        target_dscr = st.number_input(
            "Target DSCR", value=float(project_inputs.financing.target_dscr),
            min_value=1.0, max_value=3.0, step=0.05, key="wind_dscr"
        )
    with fin_cols[1]:
        senior_tenor = st.number_input(
            "Senior Tenor (years)", value=int(project_inputs.financing.senior_tenor_years),
            min_value=1, max_value=30, step=1, key="wind_tenor"
        )
    with fin_cols[2]:
        all_in_rate = st.number_input(
            "All-in Rate (%)", value=float(project_inputs.financing.all_in_rate * 100),
            min_value=0.0, max_value=20.0, step=0.1, key="wind_rate"
        )
    
    st.markdown("**Tax**")
    corp_tax = st.number_input(
        "Corporate Tax Rate (%)", value=float(project_inputs.tax.corporate_rate * 100),
        min_value=0.0, max_value=50.0, step=0.5, key="wind_corp_tax"
    )
    
    modified = st.button("Apply Wind inputs and rerun", key="apply_wind")
    
    if modified:
        overrides = {
            'technical': {
                'capacity_mw': capacity,
                'plant_availability': availability / 100,
                'operating_hours_p50': p50_h,
                'pv_degradation': degradation / 100,
            },
            'revenue': {
                'ppa_base_tariff': tariff,
                'ppa_term_years': ppa_term,
            },
            'capex': {
                'total_capex': total_capex,
                'sculpt_capex_keur': sculpt_capex,
            },
            'financing': {
                'target_dscr': target_dscr,
                'senior_tenor_years': senior_tenor,
                'base_rate': all_in_rate / 100 - project_inputs.financing.margin_bps / 10000,
            },
            'tax': {
                'corporate_rate': corp_tax / 100,
            },
        }
        return apply_project_overrides(project_inputs, overrides), True
    
    return project_inputs, False
