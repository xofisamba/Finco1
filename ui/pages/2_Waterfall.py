import streamlit as st

from app.project_factories import create_default_solar_project, create_default_wind_project
from domain.period_engine import PeriodEngine
from app.waterfall_runner import WaterfallRunner, WaterfallRunConfig
from app.cache import clear_all_caches

st.set_page_config(page_title="Waterfall", layout="wide")
st.title("Waterfall Results")

project = st.selectbox("Project", ["Solar", "Wind"])
inputs = create_default_solar_project() if project == "Solar" else create_default_wind_project()

engine = PeriodEngine(
    financial_close=inputs.info.financial_close,
    construction_months=inputs.info.construction_months,
    horizon_years=inputs.info.horizon_years,
    ppa_years=inputs.revenue.ppa_term_years,
)

config = WaterfallRunConfig.from_inputs(inputs, engine)

runner = WaterfallRunner(inputs=inputs, engine=engine)

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
