"""Tests for input_schema.py."""
import pytest
from pydantic import ValidationError

from app.input_schema import (
    ProjectInputsSchema,
    RevenueInput,
    CapexInput,
    OpexInput,
    DebtInput,
    ValidateRequest,
    ValidateResponse,
)


class TestSchemaValidation:
    def test_valid_solar_schema(self):
        s = ProjectInputsSchema(project_type="Solar", scenario="Base")
        assert s.project_type == "Solar"

    def test_valid_wind_schema(self):
        s = ProjectInputsSchema(project_type="Wind")
        assert s.project_type == "Wind"

    def test_invalid_project_type(self):
        with pytest.raises(ValidationError) as exc_info:
            ProjectInputsSchema(project_type="Invalid")
        assert "project_type must be Solar or Wind" in str(exc_info.value)

    def test_invalid_scenario(self):
        with pytest.raises(ValidationError) as exc_info:
            ProjectInputsSchema(project_type="Solar", scenario="Extreme")
        assert "scenario must be Base, Downside, or Upside" in str(exc_info.value)

    def test_negative_capacity_fails(self):
        with pytest.raises(ValidationError):
            ProjectInputsSchema(project_type="Solar", capacity_mw=-50)

    def test_zero_capacity_fails(self):
        with pytest.raises(ValidationError):
            ProjectInputsSchema(project_type="Solar", capacity_mw=0)

    def test_revenue_subfield_tariff(self):
        r = RevenueInput(tariff_eur_mwh=75.0)
        assert r.tariff_eur_mwh == 75.0

    def test_revenue_subfield_full(self):
        r = RevenueInput(tariff_eur_mwh=75.0, p50_hours=1350, degradation_pct=0.4)
        assert r.tariff_eur_mwh == 75.0
        assert r.p50_hours == 1350
        assert r.degradation_pct == 0.4

    def test_revenue_degradation_ceiling(self):
        with pytest.raises(ValidationError):
            RevenueInput(degradation_pct=6.0)  # > 5%

    def test_debt_subfield_gearing(self):
        d = DebtInput(gearing_pct=65, interest_rate_pct=5.0, tenor_years=14, target_dscr=1.3)
        assert d.gearing_pct == 65
        assert d.interest_rate_pct == 5.0
        assert d.tenor_years == 14
        assert d.target_dscr == 1.3

    def test_debt_gearing_0_to_100(self):
        d = DebtInput(gearing_pct=0)
        assert d.gearing_pct == 0
        d = DebtInput(gearing_pct=100)
        assert d.gearing_pct == 100

    def test_debt_gearing_out_of_range(self):
        with pytest.raises(ValidationError):
            DebtInput(gearing_pct=150)
        with pytest.raises(ValidationError):
            DebtInput(gearing_pct=-10)

    def test_tenor_must_be_positive(self):
        with pytest.raises(ValidationError):
            DebtInput(tenor_years=0)

    def test_full_schema_with_all_sections(self):
        s = ProjectInputsSchema(
            project_type="Solar",
            project_name="My Solar Farm",
            capacity_mw=75.0,
            scenario="Base",
            revenue={
                "tariff_eur_mwh": 65.0,
                "p50_hours": 1400,
                "degradation_pct": 0.5,
            },
            capex={
                "total_capex_keur": 50000,
            },
            opex={
                "opex_y1_keur": 500,
                "inflation_pct": 2.5,
            },
            debt={
                "gearing_pct": 75,
                "interest_rate_pct": 5.5,
                "tenor_years": 15,
                "target_dscr": 1.3,
            },
        )
        assert s.project_type == "Solar"
        assert s.capacity_mw == 75.0
        assert s.revenue.tariff_eur_mwh == 65.0
        assert s.capex.total_capex_keur == 50000
        assert s.debt.gearing_pct == 75

    def test_validate_request_response(self):
        req = ValidateRequest(inputs=ProjectInputsSchema(project_type="Solar", scenario="Base"))
        assert req.inputs.project_type == "Solar"
        resp = ValidateResponse(valid=True, errors=[])
        assert resp.valid is True
        assert resp.errors == []