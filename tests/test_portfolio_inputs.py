"""Tests for real PortfolioInputs (not weighted aggregation)."""
import pytest
from domain.portfolio.inputs import PortfolioInputs
from domain.inputs import (
    ProjectInfo, CapexStructure, FinancingParams, TaxParams,
    RevenueParams, TechnicalParams, CapexItem, AssetClass,
    ProjectInputs,
)
from datetime import date


def _epc_item(name: str, amount: float) -> CapexItem:
    return CapexItem(name=name, amount_keur=amount, y0_share=0.0, asset_class=AssetClass.CIVIL_GRID)


def _minimal_project(code: str) -> ProjectInputs:
    """Create a minimal ProjectInputs for testing."""
    epc = _epc_item("epc_contract", 1000.0)
    return ProjectInputs(
        info=ProjectInfo(
            name=code, code=code, company="TestCo",
            country_iso="XX",
            financial_close=date(2030, 1, 1),
            construction_months=12,
            cod_date=date(2031, 1, 1),
            horizon_years=25,
            period_frequency=None,
        ),
        technical=TechnicalParams(capacity_mw=50.0, yield_scenario="P_50",
                                  operating_hours_p50=1500.0),
        capex=CapexStructure(epc_contract=epc, production_units=epc,
                              epc_other=epc, grid_connection=epc,
                              ops_prep=epc, insurances=epc, lease_tax=epc,
                              construction_mgmt_a=epc, commissioning=epc,
                              audit_legal=epc, construction_mgmt_b=epc,
                              contingencies=epc, taxes=epc,
                              project_acquisition=epc, project_rights=epc),
        opex=(),
        revenue=RevenueParams(ppa_base_tariff=60.0, ppa_term_years=10.0),
        financing=FinancingParams(share_capital_keur=100.0, senior_debt_amount_keur=200.0,
                                  base_rate=0.03, margin_bps=500, senior_tenor_years=10,
                                  target_dscr=1.3),
        tax=TaxParams(corporate_rate=0.10),
    )


def test_portfolio_requires_at_least_two_projects():
    shared = FinancingParams(share_capital_keur=100.0, senior_debt_amount_keur=200.0,
                             base_rate=0.03, margin_bps=500, senior_tenor_years=10,
                             target_dscr=1.3)
    with pytest.raises(ValueError, match="at least 2"):
        PortfolioInputs(
            projects=(_minimal_project("SOL001"),),
            portfolio_name="Test",
            shared_financing=shared,
        )


def test_portfolio_requires_unique_project_codes():
    p1 = _minimal_project("SOL001")
    p2 = _minimal_project("SOL001")  # duplicate
    shared = FinancingParams(share_capital_keur=100.0, senior_debt_amount_keur=200.0,
                             base_rate=0.03, margin_bps=500, senior_tenor_years=10,
                             target_dscr=1.3)
    with pytest.raises(ValueError, match="unique"):
        PortfolioInputs(projects=(p1, p2), portfolio_name="Test", shared_financing=shared)


def test_portfolio_accepts_solar_and_wind_projects():
    solar = _minimal_project("SOL001")
    wind = _minimal_project("WIND001")
    shared = FinancingParams(share_capital_keur=100.0, senior_debt_amount_keur=200.0,
                             base_rate=0.03, margin_bps=500, senior_tenor_years=10,
                             target_dscr=1.3)
    pf = PortfolioInputs(projects=(solar, wind), portfolio_name="Mixed", shared_financing=shared)
    assert len(pf.projects) == 2


def test_portfolio_cash_pooling_defaults_true():
    shared = FinancingParams(share_capital_keur=100.0, senior_debt_amount_keur=200.0,
                             base_rate=0.03, margin_bps=500, senior_tenor_years=10,
                             target_dscr=1.3)
    pf = PortfolioInputs(
        projects=(_minimal_project("A"), _minimal_project("B")),
        portfolio_name="Test", shared_financing=shared,
    )
    assert pf.cash_pooling is True


def test_portfolio_cross_default_defaults_true():
    shared = FinancingParams(share_capital_keur=100.0, senior_debt_amount_keur=200.0,
                             base_rate=0.03, margin_bps=500, senior_tenor_years=10,
                             target_dscr=1.3)
    pf = PortfolioInputs(
        projects=(_minimal_project("A"), _minimal_project("B")),
        portfolio_name="Test", shared_financing=shared,
    )
    assert pf.cross_default is True


def test_portfolio_requires_shared_financing():
    p1 = _minimal_project("SOL001")
    p2 = _minimal_project("WIND001")
    with pytest.raises(TypeError):  # missing required field
        PortfolioInputs(projects=(p1, p2), portfolio_name="Test")


def test_weighted_aggregation_model_not_used_as_portfolio_inputs():
    """Verify the real PortfolioInputs does not use ProjectWeight."""
    shared = FinancingParams(share_capital_keur=100.0, senior_debt_amount_keur=200.0,
                             base_rate=0.03, margin_bps=500, senior_tenor_years=10,
                             target_dscr=1.3)
    pf = PortfolioInputs(
        projects=(_minimal_project("A"), _minimal_project("B")),
        portfolio_name="Test", shared_financing=shared,
    )
    # Real PortfolioInputs has projects as tuple[ProjectInputs, ...]
    assert hasattr(pf, "projects")
    assert hasattr(pf, "shared_financing")
    assert hasattr(pf, "cash_pooling")
    # It should NOT have 'weights' or 'aggregation_method'
    assert not hasattr(pf, "weights")
    assert not hasattr(pf, "aggregation_method")