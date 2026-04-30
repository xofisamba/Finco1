import streamlit as st
import sys
sys.path.insert(0, '/root/.openclaw/workspace/finco1_new')

from domain.inputs import ProjectInputs, EquityIRRMethod, DebtSizingMethod, SHLRepaymentMethod
from domain.period_engine import PeriodEngine
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
from app.cache import clear_all_caches

st.set_page_config(page_title="Waterfall", layout="wide")
st.title("Waterfall Results")

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

if st.button("Run Waterfall", type="primary"):
    clear_all_caches()
    result = runner.run(config)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Project IRR", f"{result.project_irr:.2%}")
    col2.metric("Equity IRR", f"{result.equity_irr:.2%}")
    col3.metric("Avg DSCR", f"{result.avg_dscr:.3f}x")
    col4.metric("Debt", f"{result.debt_keur:,.0f} kEUR")

    st.divider()
    st.subheader("Period Summary")

    rows = []
    for i, wp in enumerate(result.waterfall_periods):
        rows.append({
            "Period": i,
            "Revenue": f"{wp.revenue_keur:,.0f}",
            "OPEX": f"{wp.opex_keur:,.0f}",
            "EBITDA": f"{wp.ebitda_keur:,.0f}",
            "Tax": f"{wp.tax_keur:,.0f}",
            "DSCR": f"{wp.dscr:.3f}x" if wp.dscr > 0 else "-",
        })
    st.dataframe(rows)
else:
    st.info("Click 'Run Waterfall' to compute results.")