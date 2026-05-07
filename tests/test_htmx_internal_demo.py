"""Tests for HTMX internal demo.

Uses TestClient (synchronous, in-process).
Starlette's TestClient handles requests directly via ASGI.
"""
import pytest
from fastapi.testclient import TestClient
import sys, os

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

    def test_validate_negative_value_returns_error(self, client):
        r = client.post("/validate",
                        data={"project_type": "Solar", "scenario": "Base", "gearing_pct": "-5"})
        assert r.status_code == 200
        assert "gearing_pct" in r.text.lower()

    def test_validate_gearing_over_100_returns_error(self, client):
        r = client.post("/validate",
                        data={"project_type": "Solar", "scenario": "Base", "gearing_pct": "120"})
        assert r.status_code == 200
        assert "gearing_pct" in r.text.lower()


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

    def test_blank_optional_fields_work(self, client):
        """Blank optional fields should not cause errors."""
        r = client.post("/run", data={"project_type": "Solar", "scenario": "Base", "capacity_mw": "", "tariff_eur_mwh": ""})
        assert r.status_code == 200
        assert "Project IRR" in r.text or "Equity IRR" in r.text


class TestCustomInputsBehavioral:
    """Behavioral tests: custom inputs actually change model outputs."""

    def test_custom_tariff_changes_revenue(self, client):
        """Higher tariff → higher total revenue (behavioral test)."""
        r_low = client.post("/run", data={
            "project_type": "Solar", "scenario": "Base",
            "tariff_eur_mwh": "60",
        })
        r_high = client.post("/run", data={
            "project_type": "Solar", "scenario": "Base",
            "tariff_eur_mwh": "120",
        })
        assert r_low.status_code == 200
        assert r_high.status_code == 200
        # Parse revenue from output
        import re
        def extract_revenue(text):
            m = re.search(
                r'<div class="kpi-card">\s*<div class="kpi-label">Total Revenue[^<]*</div>\s*<div[^>]*>\s*([\d,]+)',
                text, re.DOTALL
            )
            if not m:
                return None
            return float(m.group(1).replace(",", ""))
        rev_low = extract_revenue(r_low.text)
        rev_high = extract_revenue(r_high.text)
        assert rev_low is not None, f"Could not extract revenue from: {r_low.text[:200]}"
        assert rev_high is not None
        assert rev_high > rev_low, f"Expected higher tariff → higher revenue. Got low={rev_low}, high={rev_high}"

    def test_custom_capex_changes_irr(self, client):
        """Higher CAPEX → lower IRR (behavioral test)."""
        r_low = client.post("/run", data={
            "project_type": "Solar", "scenario": "Base",
            "total_capex_keur": "40000",
        })
        r_high = client.post("/run", data={
            "project_type": "Solar", "scenario": "Base",
            "total_capex_keur": "80000",
        })
        assert r_low.status_code == 200
        assert r_high.status_code == 200
        import re
        def extract_irr(text):
            m = re.search(
                r'<div class="kpi-card">\s*<div class="kpi-label">Project IRR</div>\s*<div[^>]*>\s*(\d+\.\d+)\s*%',
                text, re.DOTALL
            )
            if not m:
                return None
            return float(m.group(1))
        irr_low = extract_irr(r_low.text)
        irr_high = extract_irr(r_high.text)
        assert irr_low is not None, f"Could not extract IRR from: {r_low.text[:200]}"
        assert irr_high is not None
        assert irr_low > irr_high, f"Expected higher CAPEX → lower IRR. Got low_capex={irr_low}%, high_capex={irr_high}%"

    def test_invalid_capex_returns_validation_error(self, client):
        """Negative CAPEX should return validation error, not a 500."""
        r = client.post("/validate", data={
            "project_type": "Solar", "scenario": "Base",
            "total_capex_keur": "-5000",
        })
        assert r.status_code == 200
        assert "total_capex_keur" in r.text.lower()

    def test_invalid_gearing_returns_validation_error(self, client):
        """Gearing > 100% should return validation error."""
        r = client.post("/validate", data={
            "project_type": "Solar", "scenario": "Base",
            "gearing_pct": "150",
        })
        assert r.status_code == 200
        assert "gearing_pct" in r.text.lower()

    def test_no_traceback_exposed_to_ui(self, client):
        """Invalid input should not expose Python traceback."""
        r = client.post("/validate", data={"project_type": "Banana", "scenario": "Base"})
        assert r.status_code == 200
        assert "Traceback" not in r.text
        assert "AttributeError" not in r.text
        assert "must be one of" in r.text


class TestCompare:
    def test_compare_solar_returns_comparison(self, client):
        r = client.post("/compare", data={"project_type": "Solar"})
        assert r.status_code == 200
        assert "Base" in r.text or "comparison" in r.text.lower()

    def test_compare_uses_custom_inputs(self, client):
        """Custom inputs are applied to all scenarios in compare."""
        r_custom = client.post("/compare", data={
            "project_type": "Solar",
            "tariff_eur_mwh": "120",
            "total_capex_keur": "50000",
        })
        assert r_custom.status_code == 200
        # Base should appear with other scenarios
        assert "Base" in r_custom.text

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

    def test_download_post_with_custom_inputs_returns_xlsx(self, client):
        """Download with custom inputs should still return valid xlsx."""
        r = client.post("/download", data={
            "project_type": "Solar", "scenario": "Base",
            "tariff_eur_mwh": "90",
            "total_capex_keur": "55000",
        })
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

class TestNoSilentFallback:
    """Regression tests: invalid inputs must return errors, not silent fallback to defaults."""

    def test_compare_invalid_gearing_returns_error_not_defaults(self, client):
        """Invalid gearing_pct=150 must return errors.html, NOT comparison with factory defaults."""
        r = client.post("/compare", data={
            "project_type": "Solar",
            "gearing_pct": "150",
        })
        assert r.status_code == 200
        # Must show error, not comparison table
        assert "error" in r.text.lower() or "Invalid" in r.text or "gearing" in r.text.lower()
        # Must NOT render comparison.html (which would mean silent fallback)
        assert "Base" not in r.text or "Downside" not in r.text or "Upside" not in r.text, \
            "comparison.html rendered on invalid input — silent fallback occurred"

    def test_compare_negative_capex_returns_error(self, client):
        """Negative CAPEX must return errors, not silent fallback."""
        r = client.post("/compare", data={
            "project_type": "Solar",
            "total_capex_keur": "-50000",
        })
        assert r.status_code == 200
        assert "error" in r.text.lower() or "Invalid" in r.text

    def test_download_invalid_gearing_returns_error_not_xlsx(self, client):
        """Invalid gearing on POST /download must return error HTML, not silent xlsx."""
        r = client.post("/download", data={
            "project_type": "Solar",
            "scenario": "Base",
            "gearing_pct": "200",
        })
        # Must return error (400), not 200 xlsx
        assert r.status_code == 400, f"Expected 400 error, got {r.status_code} — silent fallback to xlsx occurred"
        assert "Excel generation failed" in r.text or "Invalid input" in r.text
        # Not xlsx content-type
        ct = r.headers.get("content-type", "")
        assert "openxmlformats" not in ct, f"Got xlsx on invalid input — silent fallback occurred (content-type={ct})"

    def test_download_uses_custom_inputs_not_defaults(self, client):
        """POST /download with custom inputs must generate Excel with those inputs applied."""
        r_custom = client.post("/download", data={
            "project_type": "Solar",
            "scenario": "Base",
            "tariff_eur_mwh": "150",  # very high tariff
            "total_capex_keur": "30000",  # low capex
        })
        assert r_custom.status_code == 200
        assert "application/vnd.openxmlformats" in r_custom.headers["content-type"]
        # Verify the Excel is non-trivial (not just factory default)
        # High tariff + low capex → very high IRR, check content-length is reasonable
        content_len = len(r_custom.content)
        assert content_len > 5000, f"Excel seems too small ({content_len} bytes) — may be using defaults"

    def test_download_preserves_current_form_state(self, client):
        """Download must reflect the exact form values submitted, not some other values."""
        # Two downloads with different inputs must produce different results
        r_low = client.post("/download", data={
            "project_type": "Solar", "scenario": "Base",
            "tariff_eur_mwh": "50",
            "total_capex_keur": "60000",
        })
        r_high = client.post("/download", data={
            "project_type": "Solar", "scenario": "Base",
            "tariff_eur_mwh": "150",
            "total_capex_keur": "30000",
        })
        assert r_low.status_code == 200
        assert r_high.status_code == 200
        # Different inputs must produce different Excel sizes (proves form state is preserved)
        assert len(r_low.content) != len(r_high.content), \
            "Different inputs produced identical Excel size — form state not preserved"

    def test_run_invalid_tariff_returns_error_not_defaults(self, client):
        """Negative tariff must return error, not silent fallback to defaults."""
        r = client.post("/run", data={
            "project_type": "Solar", "scenario": "Base",
            "tariff_eur_mwh": "-10",
        })
        assert r.status_code == 200
        assert "error" in r.text.lower() or "Invalid" in r.text or "tariff" in r.text.lower()

    def test_no_silent_fallback_on_schema_failure(self, client):
        """Any schema build failure must surface as user-visible error."""
        # Invalid numeric that passes _validate_numeric_field but fails schema
        r = client.post("/run", data={
            "project_type": "Solar", "scenario": "Base",
            "gearing_pct": "not_a_number_at_all",
        })
        assert r.status_code == 200
        # Must show error in response
        assert "error" in r.text.lower() or "Invalid" in r.text or "gearing" in r.text.lower()
        # Response must NOT contain KPI results (which would mean silent fallback)
        assert "Project IRR" not in r.text
