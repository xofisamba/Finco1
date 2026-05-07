"""Tests for HTMX internal demo.

Uses TestClient (synchronous, no actual HTTP server needed).
Starlette's TestClient handles requests in-process.
"""
import pytest
from fastapi.testclient import TestClient
import sys, os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main_web import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealth:
    def test_health_returns_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestIndex:
    def test_get_index_returns_200(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_index_has_htmx_script(self, client):
        r = client.get("/")
        assert "htmx.org" in r.text

    def test_index_has_fincogpt_title(self, client):
        r = client.get("/")
        assert "FincoGPT" in r.text


class TestValidate:
    def test_validate_valid_solar_returns_200(self, client):
        r = client.post("/validate", data={"project_type": "Solar", "scenario": "Base"})
        assert r.status_code == 200
        assert "passed" in r.text.lower() or "validation" in r.text.lower()

    def test_validate_invalid_project_type_returns_error(self, client):
        r = client.post("/validate", data={"project_type": "Nuclear", "scenario": "Base"})
        assert r.status_code == 200
        assert "must be one of" in r.text

    def test_validate_invalid_scenario_returns_error(self, client):
        r = client.post("/validate", data={"project_type": "Solar", "scenario": "Extreme"})
        assert r.status_code == 200
        assert "must be one of" in r.text

    def test_validate_non_numeric_field_shows_error(self, client):
        r = client.post("/validate",
                        data={"project_type": "Solar", "scenario": "Base", "capacity_mw": "not-a-number"})
        assert r.status_code == 200
        assert "capacity_mw" in r.text


class TestRun:
    def test_run_solar_base_returns_kpi_partial(self, client):
        r = client.post("/run", data={"project_type": "Solar", "scenario": "Base"})
        assert r.status_code == 200
        assert "Project IRR" in r.text or "Equity IRR" in r.text

    def test_run_wind_returns_kpi_partial(self, client):
        r = client.post("/run", data={"project_type": "Wind", "scenario": "Base"})
        assert r.status_code == 200
        assert "IRR" in r.text

    def test_run_invalid_returns_error(self, client):
        r = client.post("/run", data={"project_type": "Nuclear", "scenario": "Base"})
        assert r.status_code == 200
        assert "error" in r.text.lower() or "must be one of" in r.text


class TestCompare:
    def test_compare_solar_returns_comparison(self, client):
        r = client.post("/compare", data={"project_type": "Solar"})
        assert r.status_code == 200
        assert "Base" in r.text or "comparison" in r.text.lower()

    def test_compare_invalid_project_returns_error(self, client):
        r = client.post("/compare", data={"project_type": "Nuclear"})
        assert r.status_code == 200
        assert "error" in r.text.lower()


class TestDownload:
    def test_download_get_returns_xlsx(self, client):
        r = client.get("/download?project_type=Solar&scenario=Base")
        assert r.status_code == 200
        assert "application/vnd.openxmlformats" in r.headers["content-type"]
        assert "fincogpt" in r.headers.get("content-disposition", "").lower()

    def test_download_post_returns_xlsx(self, client):
        r = client.post("/download", data={"project_type": "Wind", "scenario": "Downside"})
        assert r.status_code == 200
        assert "application/vnd.openxmlformats" in r.headers["content-type"]


class TestNoStreamlit:
    def test_no_streamlit_import_in_router(self):
        """Verify main_web.py does not import Streamlit."""
        src = open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "main_web.py")).read()
        assert "import streamlit" not in src and "from streamlit" not in src


class TestValidationFriendly:
    def test_invalid_project_type_shows_friendly_error_not_traceback(self, client):
        r = client.post("/validate", data={"project_type": "Banana", "scenario": "Base"})
        assert r.status_code == 200
        assert "Traceback" not in r.text
        assert "AttributeError" not in r.text
        assert "must be one of" in r.text