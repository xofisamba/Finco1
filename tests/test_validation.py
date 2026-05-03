"""Tests for domain/validation.py."""
import pytest
from dataclasses import replace
from app.project_factories import create_default_solar_project, create_default_wind_project
from domain.portfolio.inputs import PortfolioInputs
from domain.inputs import FinancingParams
from domain.validation import validate_project_inputs, validate_portfolio_inputs


def test_valid_default_solar_has_no_errors():
    proj = create_default_solar_project()
    issues = validate_project_inputs(proj)
    errors = [i for i in issues if i.severity == "error"]
    assert len(errors) == 0, f"Unexpected errors: {errors}"


def test_invalid_capacity_is_error():
    proj = create_default_solar_project()
    proj = replace(proj, technical=replace(proj.technical, capacity_mw=0.0))
    issues = validate_project_inputs(proj)
    assert any(i.field == "capacity_mw" and i.severity == "error" for i in issues)


def test_invalid_tax_rate_is_error():
    proj = create_default_solar_project()
    proj = replace(proj, tax=replace(proj.tax, corporate_rate=1.5))
    issues = validate_project_inputs(proj)
    assert any(i.field == "corporate_rate" and i.severity == "error" for i in issues)


def test_invalid_dscr_is_error():
    proj = create_default_solar_project()
    proj = replace(proj, financing=replace(proj.financing, target_dscr=0.9))
    issues = validate_project_inputs(proj)
    assert any(i.field == "target_dscr" and i.severity == "error" for i in issues)


def test_debt_tenor_longer_than_horizon_is_error():
    proj = create_default_solar_project()
    proj = replace(proj, financing=replace(proj.financing, senior_tenor_years=999))
    issues = validate_project_inputs(proj)
    assert any(i.field == "senior_tenor_years" and i.severity == "error" for i in issues)


def test_portfolio_duplicate_project_codes_is_error():
    proj1 = create_default_solar_project()
    proj2 = create_default_wind_project()
    # Force duplicate code - PortfolioInputs raises ValueError in __post_init__
    # before validate_portfolio_inputs can run, so we test the constructor directly
    proj2 = replace(proj2, info=replace(proj2.info, code=proj1.info.code))
    with pytest.raises(ValueError, match="Project codes must be unique"):
        PortfolioInputs(projects=(proj1, proj2), portfolio_name="Test",
                        shared_financing=FinancingParams(share_capital_keur=100, senior_debt_amount_keur=200, senior_tenor_years=10, target_dscr=1.3))


def test_portfolio_requires_two_projects():
    proj = create_default_solar_project()
    # PortfolioInputs constructor raises ValueError for <2 projects, so test via mock
    class SingleProjectPortfolio:
        def __init__(self):
            self.projects = (proj,)
            self.shared_financing = FinancingParams(share_capital_keur=100, senior_debt_amount_keur=200, senior_tenor_years=10, target_dscr=1.3)
    issues = validate_portfolio_inputs(SingleProjectPortfolio())
    assert any(i.field == "projects" and i.severity == "error" for i in issues)


def test_validation_returns_warnings_for_zero_tariff():
    proj = create_default_solar_project()
    proj = replace(proj, revenue=replace(proj.revenue, ppa_base_tariff=0.0))
    issues = validate_project_inputs(proj)
    assert any(i.field == "ppa_base_tariff" and i.severity == "warning" for i in issues)