"""Directionality/integration tests for custom input financial impact.

These tests prove that custom inputs actually change financial outputs.
Moved from test_input_adapter.py for cleaner test ownership.
"""
import pytest
from app.api.project_runner import run_project_legacy as run_project  # PR-8: legacy characterization route
from app.input_schema import ProjectInputsSchema
from app.input_adapter import build_projectinputs
import json


class TestCustomInputDirectionality:
    """Prove custom inputs produce directional financial changes."""

    def _load_base_project(self, **overrides):
        """Load base Solar project and apply overrides."""
        with open("examples/custom_solar.json") as f:
            data = json.load(f)
        for key, value in overrides.items():
            if "." in key:
                section, field = key.split(".", 1)
                data[section][field] = value
            else:
                data[key] = value
        schema = ProjectInputsSchema(**data)
        return build_projectinputs(schema)

    def test_higher_tariff_increases_revenue(self):
        """Higher tariff → higher total revenue."""
        r_base = run_project("Solar", "Base")
        base_rev = r_base["kpis"]["total_revenue_keur"]

        proj = self._load_base_project(**{"revenue.tariff_eur_mwh": 150})
        r_high = run_project("Solar", "Base", project_inputs_override=proj)
        high_rev = r_high["kpis"]["total_revenue_keur"]
        assert high_rev > base_rev, f"150 tariff should increase revenue: {high_rev} vs {base_rev}"

    def test_higher_capex_reduces_irr(self):
        """Higher CAPEX → lower project IRR."""
        r_base = run_project("Solar", "Base")
        base_irr = r_base["kpis"]["project_irr"]

        proj = self._load_base_project(**{"capex.total_capex_keur": 80000})
        r_high = run_project("Solar", "Base", project_inputs_override=proj)
        high_irr = r_high["kpis"]["project_irr"]
        assert high_irr < base_irr, f"High CAPEX should reduce IRR: {high_irr} vs {base_irr}"

    def test_higher_opex_reduces_ebitda(self):
        """Higher OPEX → lower EBITDA."""
        r_base = run_project("Solar", "Base")
        base_ebitda = r_base["kpis"]["total_ebitda_keur"]

        proj = self._load_base_project(**{"opex.opex_y1_keur": 5000})
        r_high = run_project("Solar", "Base", project_inputs_override=proj)
        high_ebitda = r_high["kpis"]["total_ebitda_keur"]
        assert high_ebitda < base_ebitda, f"High OPEX should reduce EBITDA: {high_ebitda} vs {base_ebitda}"

    def test_lower_degradation_increases_revenue(self):
        """Lower degradation → higher long-term revenue."""
        proj_high = self._load_base_project(**{"revenue.degradation_pct": 1.0})
        proj_low = self._load_base_project(**{"revenue.degradation_pct": 0.1})
        r_high_deg = run_project("Solar", "Base", project_inputs_override=proj_high)
        r_low_deg = run_project("Solar", "Base", project_inputs_override=proj_low)
        assert r_low_deg["kpis"]["total_revenue_keur"] > r_high_deg["kpis"]["total_revenue_keur"]