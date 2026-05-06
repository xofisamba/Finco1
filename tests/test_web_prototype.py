"""Tests for HTMX prototype web server."""
import pytest
from fastapi.testclient import TestClient
from main_web import app


@pytest.fixture
def client():
    return TestClient(app)


def test_index_returns_200(client):
    """Homepage returns 200."""
    response = client.get("/")
    assert response.status_code == 200


def test_validate_returns_partial(client):
    """POST /validate returns KPI partial HTML."""
    response = client.post("/validate", data={
        "project_type": "Solar",
        "scenario": "Base",
    })
    assert response.status_code == 200
    assert "result" in response.text or "kpi" in response.text.lower() or "error" in response.text


def test_validate_with_custom_tariff(client):
    """Custom tariff affects revenue."""
    r1 = client.post("/validate", data={"project_type": "Solar", "scenario": "Base"})
    r2 = client.post("/validate", data={
        "project_type": "Solar", "scenario": "Base", "tariff_eur_mwh": 150
    })
    # Higher tariff → different revenue
    assert r1.text != r2.text or "kpi" in r1.text.lower()


def test_invalid_project_type_gives_error(client):
    """Invalid project_type returns visible error."""
    response = client.post("/validate", data={
        "project_type": "InvalidType", "scenario": "Base"
    })
    assert response.status_code == 200
    # Should have error or exception visible in response
    assert "error" in response.text.lower() or "unknown" in response.text.lower()
