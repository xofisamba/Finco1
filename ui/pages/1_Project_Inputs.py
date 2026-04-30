import streamlit as st
import sys
sys.path.insert(0, '/root/.openclaw/workspace/finco1_new')

from domain.inputs import ProjectInputs

st.set_page_config(page_title="Project Inputs", layout="wide")
st.title("Project Inputs")

# Let user select project
project = st.selectbox("Project", ["Oborovo Solar PV", "TUHO Wind 1"])
if project == "Oborovo Solar PV":
    inputs = ProjectInputs.create_default_oborovo()
else:
    inputs = ProjectInputs.create_default_tuho_wind1()

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
    st.write(f"PPA tariff: {inputs.revenue.ppa_base_tariff} EUR/MWh")
    st.write(f"PPA term: {inputs.revenue.ppa_term_years} years")

st.subheader("CAPEX")
st.write(f"Total CAPEX: {inputs.capex.total_capex:,.0f} kEUR")

st.subheader("Financing")
st.write(f"Gearing: {inputs.financing.gearing_ratio:.2%}")
st.write(f"Senior tenor: {inputs.financing.senior_tenor_years} years")
st.write(f"All-in rate: {inputs.financing.all_in_rate:.4f}")
st.write(f"SHL amount: {inputs.financing.shl_amount_keur:,.0f} kEUR")
st.write(f"SHL rate: {inputs.financing.shl_rate:.4f}")