import streamlit as st

from app.project_factories import create_default_solar_project, create_default_wind_project

st.set_page_config(page_title="Project Inputs", layout="wide")
st.title("Project Inputs")

project = st.selectbox("Project", ["Solar", "Wind"])
inputs = create_default_solar_project() if project == "Solar" else create_default_wind_project()

col1, col2 = st.columns(2)
with col1:
    st.subheader("Info")
    st.write(f"Name: {inputs.info.name}")
    st.write(f"Country: {inputs.info.country_iso}")
    st.write(f"FC: {inputs.info.financial_close}")
    st.write(f"COD: {inputs.info.cod_date}")
    st.write(f"Horizon: {inputs.info.horizon_years} years")
with col2:
    st.subheader("Technical")
    st.write(f"Capacity: {inputs.technical.capacity_mw} MW")
    st.write(f"Yield scenario: {inputs.technical.yield_scenario}")
    st.write(f"P50 Hours: {inputs.technical.operating_hours_p50}")
    st.write(f"Availability: {inputs.technical.availability:.1%}")

st.divider()
st.subheader("Revenue")
st.write(f"PPA Tariff: €{inputs.revenue.ppa_base_tariff:.2f}/MWh")
st.write(f"PPA Term: {inputs.revenue.ppa_term_years} years")

st.divider()
st.subheader("Financing")
fin = inputs.financing
st.write(f"Share Capital: €{fin.share_capital_keur:,.0f} kEUR")
st.write(f"Senior Debt: €{fin.senior_debt_amount_keur:,.0f} kEUR")
st.write(f"All-in Rate: {fin.all_in_rate:.2%}")
st.write(f"Target DSCR: {fin.target_dscr:.2f}x")
