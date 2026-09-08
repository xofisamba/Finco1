"""Tests for HTMX internal demo.

Uses TestClient (synchronous, in-process).
Starlette's TestClient handles requests directly via ASGI.
Authentication: tests use a valid session cookie directly (no login round-trip needed).
"""
import os
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")

import pytest
from fastapi.testclient import TestClient
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main_web import app
from app.auth import create_session_token


@pytest.fixture
def client():
    """Test client with a valid session cookie (bypasses login round-trip)."""
    tc = TestClient(app)
    token = create_session_token()
    tc.cookies.set("finco_session", token)
    return tc


@pytest.fixture
def unauthenticated_client():
    """Test client without session cookie."""
    return TestClient(app)


class TestHealth:
    def test_health_returns_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestPublicHealth:
    def test_public_health_returns_200(self, unauthenticated_client):
        """Public health should work without authentication."""
        r = unauthenticated_client.get("/public-health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_public_health_contains_app_info(self, unauthenticated_client):
        r = unauthenticated_client.get("/public-health")
        data = r.json()
        assert data["status"] == "ok"
        assert data["app"] == "fincogpt"
        assert data["mode"] == "internal-demo"

    def test_public_health_no_model_execution(self, unauthenticated_client):
        """Public health should be fast — no model execution."""
        r = unauthenticated_client.get("/public-health")
        assert r.status_code == 200
        data = r.json()
        assert "project_irr" not in data
        assert "equity_irr" not in data


class TestIndex:
    def test_get_index_redirects_to_library(self, client):
        r = client.get("/")
        assert r.status_code == 200
        # / redirects to /library
        assert "Project Library" in r.text or "library" in r.url.lower()

    def test_index_has_htmx_script(self, client):
        r = client.get("/library")
        # htmx is now vendored locally under /static/vendor/htmx.min.js
        # verify the local vendor path is referenced and htmx is loaded
        assert "/static/vendor/htmx.min.js" in r.text, "htmx should be vendored locally at /static/vendor/htmx.min.js"

    def test_index_has_product_title(self, client):
        r = client.get("/library")
        # Product is now "Finco One" / "Project Library", not FincoGPT
        assert "Finco" in r.text or "Project Library" in r.text


BOUNDARY_MSG = "Current form state no longer matches the last saved runtime boundary"


class TestValidate:
    def test_validate_returns_200(self, client):
        r = client.post("/validate", data={"project_type": "Solar", "scenario": "Base"})
        assert r.status_code == 200

    def test_validate_fail_closed_boundary_message(self, client):
        # Current fail-closed contract: without a valid workspace snapshot the
        # route returns the canonical boundary-mismatch fragment.
        r = client.post("/validate", data={"project_type": "Solar", "scenario": "Base"})
        assert r.status_code == 200
        assert BOUNDARY_MSG in r.text, (
            f"Expected boundary mismatch message; got: {r.text[:300]}"
        )
        assert "Traceback" not in r.text
        assert "AttributeError" not in r.text

    def test_validate_no_traceback_on_bad_project_type(self, client):
        r = client.post("/validate", data={"project_type": "Nuclear", "scenario": "Base"})
        assert r.status_code == 200
        assert "Traceback" not in r.text
        assert "AttributeError" not in r.text

    def test_validate_no_traceback_on_bad_scenario(self, client):
        r = client.post("/validate", data={"project_type": "Solar", "scenario": "Extreme"})
        assert r.status_code == 200
        assert "Traceback" not in r.text

    def test_validate_no_traceback_on_non_numeric(self, client):
        r = client.post("/validate",
                        data={"project_type": "Solar", "scenario": "Base", "capacity_mw": "not-a-number"})
        assert r.status_code == 200
        assert "Traceback" not in r.text

    def test_validate_no_traceback_on_negative_value(self, client):
        r = client.post("/validate",
                        data={"project_type": "Solar", "scenario": "Base", "gearing_pct": "-5"})
        assert r.status_code == 200
        assert "Traceback" not in r.text

    def test_validate_no_traceback_on_gearing_over_100(self, client):
        r = client.post("/validate",
                        data={"project_type": "Solar", "scenario": "Base", "gearing_pct": "120"})
        assert r.status_code == 200
        assert "Traceback" not in r.text


class TestRun:
    def test_run_returns_200(self, client):
        r = client.post("/run", data={"project_type": "Solar", "scenario": "Base"})
        assert r.status_code == 200

    def test_run_fail_closed_boundary_message(self, client):
        # Current fail-closed contract: without a valid workspace snapshot the
        # route returns the canonical boundary-mismatch fragment.
        r = client.post("/run", data={"project_type": "Solar", "scenario": "Base"})
        assert r.status_code == 200
        assert BOUNDARY_MSG in r.text, (
            f"Expected boundary mismatch message; got: {r.text[:300]}"
        )
        assert "Traceback" not in r.text
        assert "AttributeError" not in r.text

    def test_run_no_traceback_on_invalid_project(self, client):
        r = client.post("/run", data={"project_type": "Nuclear", "scenario": "Base"})
        assert r.status_code == 200
        assert "Traceback" not in r.text

    def test_run_no_traceback_on_blank_optional_fields(self, client):
        r = client.post("/run", data={"project_type": "Solar", "scenario": "Base", "capacity_mw": "", "tariff_eur_mwh": ""})
        assert r.status_code == 200
        assert "Traceback" not in r.text


class TestCustomInputsBehavioral:
    """Behavioral tests: current fail-closed runtime boundary contract."""

    def test_run_no_traceback_on_custom_tariff(self, client):
        """Custom tariff input must not cause traceback (fail-closed boundary)."""
        r = client.post("/run", data={
            "project_type": "Solar", "scenario": "Base",
            "tariff_eur_mwh": "60",
        })
        assert r.status_code == 200
        assert "Traceback" not in r.text
        assert "AttributeError" not in r.text

    def test_run_no_traceback_on_custom_capex(self, client):
        """Custom CAPEX input must not cause traceback."""
        r = client.post("/run", data={
            "project_type": "Solar", "scenario": "Base",
            "total_capex_keur": "40000",
        })
        assert r.status_code == 200
        assert "Traceback" not in r.text

    def test_validate_no_traceback_on_invalid_capex(self, client):
        """Negative CAPEX should return error fragment, not a 500 or traceback."""
        r = client.post("/validate", data={
            "project_type": "Solar", "scenario": "Base",
            "total_capex_keur": "-5000",
        })
        assert r.status_code == 200
        assert "Traceback" not in r.text
        assert "AttributeError" not in r.text

    def test_validate_no_traceback_on_invalid_gearing(self, client):
        """Gearing > 100% should return error fragment, not traceback."""
        r = client.post("/validate", data={
            "project_type": "Solar", "scenario": "Base",
            "gearing_pct": "150",
        })
        assert r.status_code == 200
        assert "Traceback" not in r.text

    def test_no_traceback_exposed_to_ui(self, client):
        """Invalid input should not expose Python traceback."""
        r = client.post("/validate", data={"project_type": "Banana", "scenario": "Base"})
        assert r.status_code == 200
        assert "Traceback" not in r.text
        assert "AttributeError" not in r.text


class TestCompare:
    def test_compare_returns_200(self, client):
        r = client.post("/compare", data={"project_type": "Solar"})
        assert r.status_code == 200

    def test_compare_no_traceback(self, client):
        """Compare route must not expose traceback."""
        r = client.post("/compare", data={"project_type": "Solar"})
        assert r.status_code == 200
        assert "Traceback" not in r.text
        assert "AttributeError" not in r.text

    def test_compare_invalid_project_no_traceback(self, client):
        r = client.post("/compare", data={"project_type": "Nuclear"})
        assert r.status_code == 200
        assert "Traceback" not in r.text


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

    def test_download_response_has_attachment_disposition(self, client):
        """Content-Disposition must be 'attachment', not 'inline'."""
        r = client.get("/download?project_type=Solar&scenario=Base")
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd.lower(), f"Expected 'attachment' in Content-Disposition, got: {cd}"

    def test_download_response_starts_with_zip_magic(self, client):
        """Response body must start with ZIP magic bytes 'PK'."""
        r = client.get("/download?project_type=Solar&scenario=Base")
        assert r.content[:2] == b"PK", f"Expected ZIP magic bytes, got: {r.content[:4]}"

    def test_download_response_is_not_html(self, client):
        """Binary download must NOT contain HTML (no HTML rendered in browser)."""
        r = client.get("/download?project_type=Solar&scenario=Base")
        # Must not contain HTML doctype or tags
        assert b"<!DOCTYPE" not in r.content
        assert b"<html" not in r.content
        assert b"<body" not in r.content
        assert b"<head>" not in r.content

    def test_download_response_has_content_length(self, client):
        """Response must include Content-Length header for mobile browser support."""
        r = client.get("/download?project_type=Solar&scenario=Base")
        assert "content-length" in r.headers
        length = int(r.headers["content-length"])
        assert length > 1000, f"Expected large Excel file (>1KB), got {length} bytes"

    def test_download_mobile_safe_no_html_interpretation(self, client):
        """Mobile browsers must not interpret binary as HTML."""
        r = client.post("/download", data={"project_type": "Solar", "scenario": "Base"})
        # Should be treated as downloadable file, not rendered
        ct = r.headers.get("content-type", "")
        assert "html" not in ct.lower()
        assert r.content[:1] != ord(b"<"), "Binary content starts with '<' — would render as HTML"


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
