"""Tests for input MVP hardening: project_type/scenario consistency, CAPEX guard."""
import pytest

from app.input_schema import ProjectInputsSchema
from app.input_adapter import build_projectinputs


class TestProjectTypeMismatch:
    def test_adapter_accepts_valid_solar_schema(self):
        """Adapter correctly builds a valid Solar schema."""
        schema = ProjectInputsSchema(project_type="Solar", scenario="Base")
        proj = build_projectinputs(schema)
        assert proj is not None

    def test_adapter_raises_on_capex_too_low(self):
        """CAPEX override too low (total <= other) should raise ValueError."""
        schema = ProjectInputsSchema(
            project_type="Solar",
            scenario="Base",
            capex={"total_capex_keur": 100}  # Too low vs other_keur (~10700)
        )
        with pytest.raises(ValueError, match="must be greater than other"):
            build_projectinputs(schema)

    def test_capex_at_boundary_raises(self):
        """CAPEX exactly equal to other_keur should raise."""
        # other_keur for Solar is 10000.0, set total to exactly that
        schema = ProjectInputsSchema(
            project_type="Solar",
            scenario="Base",
            capex={"total_capex_keur": 10000.0}
        )
        with pytest.raises(ValueError, match="must be greater than other"):
            build_projectinputs(schema)


class TestScenarioMismatch:
    def test_scenario_in_schema_is_optional(self):
        """Scenario field is optional in schema."""
        schema = ProjectInputsSchema(project_type="Solar")  # no scenario
        assert schema.scenario == "Base"  # default

    def test_scenario_in_schema_defaults_to_base(self):
        """When not specified, scenario defaults to Base."""
        schema = ProjectInputsSchema(project_type="Solar")
        assert schema.scenario == "Base"

    def test_capex_valid_with_high_total(self):
        """CAPEX override with sufficient total should succeed."""
        schema = ProjectInputsSchema(
            project_type="Solar",
            scenario="Base",
            capex={"total_capex_keur": 50000.0}
        )
        proj = build_projectinputs(schema)
        assert proj is not None
