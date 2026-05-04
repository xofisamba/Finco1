"""
DEPRECATED: Legacy entrypoint.
This module is kept only to avoid import errors in any archived references.
Please use: streamlit run streamlit_app.py
"""
import streamlit as st

st.set_page_config(page_title="Finco1 — Deprecated", page_icon="⚠️")
st.warning("⚠️ This entrypoint is deprecated.")
st.info("Please run: `streamlit run streamlit_app.py`")
st.markdown("---")
st.markdown("""
## Legacy src/app.py

This file is kept as a deprecated shim only.

The current application entrypoint is **streamlit_app.py**.

Default project factories are in **app/project_factories.py**, not in `domain/inputs.py`.
""")