import streamlit as st
import sys
sys.path.insert(0, '/root/.openclaw/workspace/finco1_new')

# LEGACY UI PAGES — these use ProjectInputs.create_default_* which no longer
# exists. Redirect to app.project_factories which has the actual implementations.
from app.project_factories import create_default_oborovo, create_default_tuho_wind1

st.set_page_config(page_title="Project Inputs", layout="wide")
st.title("Project Inputs")

# Let user select project
project = st.selectbox("Project", ["Oborovo Solar PV", "TUHO Wind 1"])
if project == "Oborovo Solar PV":
    inputs = create_default_oborovo()
else:
    inputs = create_default_tuho_wind1()

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