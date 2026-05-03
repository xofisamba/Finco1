"""Shared UI components."""
import streamlit as st

def kpi_card(label: str, value: float | str | None, delta: float | None = None):
    """Render a single KPI metric card."""
    if value is None:
        value = "n/a"
    if delta is not None:
        st.metric(label=label, value=value, delta=delta)
    else:
        st.metric(label=label, value=value)

def section_header(text: str, color: str | None = None):
    """Render a section header."""
    st.markdown(f"**{text}**")

def warning_banner(message: str):
    """Render a warning banner."""
    st.warning(message)