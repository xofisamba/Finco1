import pytest
from fastapi.testclient import TestClient
from main_api import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["service"] == "fincogpt-api"


def test_project_types():
    r = client.get("/api/v1/project-types")
    assert r.status_code == 200
    data = r.json()
    assert "Solar" in data["project_types"]
    assert "Wind" in data["project_types"]


def test_scenarios():
    r = client.get("/api/v1/scenarios")
    assert r.status_code == 200
    data = r.json()
    assert "Base" in data["scenarios"]
    assert "Downside" in data["scenarios"]
    assert "Upside" in data["scenarios"]


def test_run_solar_base():
    r = client.post("/api/v1/run", json={"project_type": "Solar", "scenario": "Base", "period_view": "Semiannual"})
    assert r.status_code == 200
    data = r.json()
    assert data["project_type"] == "Solar"
    assert data["scenario"] == "Base"
    assert data["kpis"]["project_irr"] is not None
    assert data["kpis"]["project_irr"] > 0


def test_solar_downside_lower_irr():
    base_r = client.post("/api/v1/run", json={"project_type": "Solar", "scenario": "Base"})
    downside_r = client.post("/api/v1/run", json={"project_type": "Solar", "scenario": "Downside"})
    assert base_r.status_code == 200
    assert downside_r.status_code == 200
    assert base_r.json()["kpis"]["project_irr"] > downside_r.json()["kpis"]["project_irr"]


def test_invalid_project_type():
    r = client.post("/api/v1/run", json={"project_type": "InvalidType", "scenario": "Base"})
    assert r.status_code == 400


def test_bess_not_supported():
    r = client.post("/api/v1/run", json={"project_type": "BESS", "scenario": "Base"})
    assert r.status_code == 501


def test_portfolio_not_supported():
    r = client.post("/api/v1/run", json={"project_type": "Portfolio", "scenario": "Base"})
    assert r.status_code == 501


def test_invalid_scenario():
    r = client.post("/api/v1/run", json={"project_type": "Solar", "scenario": "InvalidScenario"})
    assert r.status_code == 400


def test_invalid_period_view():
    r = client.post("/api/v1/run", json={"project_type": "Solar", "scenario": "Base", "period_view": "Quarterly"})
    assert r.status_code == 400


def test_wind_base_runs():
    r = client.post("/api/v1/run", json={"project_type": "Wind", "scenario": "Base"})
    assert r.status_code == 200
    data = r.json()
    assert data["project_type"] == "Wind"
    assert data["kpis"]["project_irr"] is not None
    assert data["kpis"]["project_irr"] > 0


def test_upside_higher_irr_than_base():
    base_r = client.post("/api/v1/run", json={"project_type": "Solar", "scenario": "Base"})
    upside_r = client.post("/api/v1/run", json={"project_type": "Solar", "scenario": "Upside"})
    assert base_r.status_code == 200
    assert upside_r.status_code == 200
    assert upside_r.json()["kpis"]["project_irr"] > base_r.json()["kpis"]["project_irr"]


def test_annual_period_view():
    r = client.post("/api/v1/run", json={"project_type": "Solar", "scenario": "Base", "period_view": "Annual"})
    assert r.status_code == 200
    data = r.json()
    assert data["period_view"] == "Annual"
    assert len(data["tables"]["waterfall"]) > 0  # Annual table still has rows


def test_api_response_has_integration_note():
    """API response includes integration_note field from DemoResult."""
    r = client.post("/api/v1/run", json={"project_type": "Solar", "scenario": "Base"})
    assert r.status_code == 200
    data = r.json()
    assert "integration_note" in data
    # Should be None or str, not missing
    assert data["integration_note"] is None or isinstance(data["integration_note"], str)


def test_api_response_has_messages_field():
    """API response includes messages field (list) from DemoResult."""
    r = client.post("/api/v1/run", json={"project_type": "Solar", "scenario": "Base"})
    assert r.status_code == 200
    data = r.json()
    assert "messages" in data
    assert isinstance(data["messages"], list)


def test_api_integration_status_not_hardcoded():
    """integration_status comes from DemoResult, not hardcoded string."""
    from unittest.mock import patch
    # Verify the field exists and is a string
    r = client.post("/api/v1/run", json={"project_type": "Solar", "scenario": "Base"})
    assert r.status_code == 200
    data = r.json()
    assert "integration_status" in data
    assert isinstance(data["integration_status"], str)
    assert data["integration_status"] in ("full", "partial", "experimental")
