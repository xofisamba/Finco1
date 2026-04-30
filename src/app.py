import streamlit as st
import sys
sys.path.insert(0, '/root/.openclaw/workspace/finco1_new')

from datetime import date
from domain.inputs import ProjectInputs, EquityIRRMethod, DebtSizingMethod, SHLRepaymentMethod
from domain.period_engine import PeriodEngine
from app.cache import clear_all_caches
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig

st.set_page_config(page_title="Finco1", layout="wide")

st.title("Finco1 — Financial Model")

# Project selection
project = st.selectbox("Project", ["Oborovo Solar PV", "TUHO Wind 1"])

if project == "Oborovo Solar PV":
    inputs = ProjectInputs.create_default_oborovo()
else:
    inputs = ProjectInputs.create_default_tuho_wind1()

engine = PeriodEngine(
    financial_close=inputs.info.financial_close,
    construction_months=inputs.info.construction_months,
    horizon_years=inputs.info.horizon_years,
    ppa_years=inputs.revenue.ppa_term_years,
)

# Waterfall configuration
config = WaterfallRunConfig(
    rate_per_period=inputs.financing.all_in_rate / 2,
    tenor_periods=inputs.financing.senior_tenor_years * 2,
    target_dscr=inputs.financing.target_dscr,
    lockup_dscr=inputs.financing.lockup_dscr,
    shl_amount_keur=inputs.financing.shl_amount_keur,
    shl_rate=inputs.financing.shl_rate,
    shl_idc_keur=inputs.financing.shl_idc_keur,
    equity_irr_method=EquityIRRMethod.EQUITY_ONLY,
    debt_sizing_method=DebtSizingMethod.DSCR_SCULPT,
)

runner = WaterfallRunner(inputs, engine)

if st.button("Run Waterfall"):
    clear_all_caches()
    result = runner.run(config)
    st.success(f"Done! Equity IRR: {result.equity_irr:.2%}")

st.write(f"Project: {inputs.info.name}")
st.write(f"FC: {inputs.info.financial_close}, COD: {inputs.info.cod_date}")
st.write(f"CAPEX: {inputs.capex.total_capex:,.0f} kEUR")
st.write(f"Gearing: {inputs.financing.gearing_ratio:.2%}")
st.write(f"SHL: {inputs.financing.shl_amount_keur:,.0f} kEUR @ {inputs.financing.shl_rate:.2%}")