"""Directionality/integration tests for custom input financial impact.

These tests prove that custom inputs actually change financial outputs.
Moved from test_input_adapter.py for cleaner test ownership.
"""
import pytest
from app.api.project_runner import run_project


class TestCustomInputDirectionality:
    """Prove custom inputs produce directional financial changes."""

    def test_higher_tariff_increases_revenue(self):
        """Higher tariff → higher total revenue."""
        r_base = run_project("Solar", "Base")
        base_rev = r_base["kpis"]["total_revenue_keur"]

        r_high = run_project("Solar", "Base", project_inputs_override={
            "project_type": "Solar",
            "revenue": {"tariff_eur_mwh": 150}
        })
        high_rev = r_high["kpis"]["total_revenue_keur"]
        assert high_rev > base_rev, f"150 tariff should increase revenue: {high_rev} vs {base_rev}"

    def test_higher_capex_reduces_irr(self):
        """Higher CAPEX → lower project IRR."""
        r_base = run_project("Solar", "Base")
        base_irr = r_base["kpis"]["project_irr"]

        r_high = run_project("Solar", "Base", project_inputs_override={
            "project_type": "Solar",
            "capex": {"total_capex_keur": 80000}
        })
        high_irr = r_high["kpis"]["project_irr"]
        assert high_irr < base_irr, f"High CAPEX should reduce IRR: {high_irr} vs {base_irr}"

    def test_higher_opex_reduces_ebitda(self):
        """Higher OPEX → lower EBITDA."""
        r_base = run_project("Solar", "Base")
        base_ebitda = r_base["kpis"]["total_ebitda_keur"]

        r_high = run_project("Solar", "Base", project_inputs_override={
            "project_type": "Solar",
            "opex": {"opex_y1_keur": 5000}
        })
        high_ebitda = r_high["kpis"]["total_ebitda_keur"]
        assert high_ebitda < base_ebitda, f"High OPEX should reduce EBITDA: {high_ebitda} vs {base_ebitda}"

    def test_lower_degradation_increases_revenue(self):
        """Lower degradation → higher long-term revenue."""
        r_high_deg = run_project("Solar", "Base", project_inputs_override={
            "project_type": "Solar",
            "revenue": {"degradation_pct": 1.0}
        })
        r_low_deg = run_project("Solar", "Base", project_inputs_override={
            "project_type": "Solar",
            "revenue": {"degradation_pct": 0.1}
        })
        assert r_low_deg["kpis"]["total_revenue_keur"] > r_high_deg["kpis"]["total_revenue_keur"]