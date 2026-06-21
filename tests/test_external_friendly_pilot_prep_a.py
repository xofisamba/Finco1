"""EXTERNAL-FRIENDLY-PILOT-PREP-A.

Pilot-readiness packaging only: pilot checklist/script docs, an in-app
Pilot Guide page, footer discoverability links (Pilot Guide, Known
Limitations, Validation Status), and a light-touch pilot caveat.

No model, formula, runtime, or validation-classification changes are
covered or required by these tests -- this is a presentation and
documentation-only check.
"""
from __future__ import annotations

import os
import pathlib
import re

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-pilot-prep-a")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_session_token  # noqa: E402
from main_web import app  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

FORBIDDEN_TERMS = (
    "create_default_",
    "golden",
    "bootstrap",
    "calibration",
    "factory",
    "baseline",
)


def _strip_jinja_and_html_comments(text: str) -> str:
    text = re.sub(r"\{#.*?#\}", "", text, flags=re.DOTALL)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    return text


@pytest.fixture(scope="module")
def logged_in_client():
    client = TestClient(app)
    token = create_session_token(user_id="1", username="test_user")
    client.cookies.set("finco_session", token)
    return client


class TestPilotChecklistAndScriptExist:
    def test_pilot_readiness_checklist_exists(self):
        path = REPO_ROOT / "docs" / "pilot_readiness_checklist.md"
        assert path.exists(), "docs/pilot_readiness_checklist.md must exist"
        text = path.read_text()
        for item in (
            "create project",
            "edit assumptions",
            "save",
            "run model",
            "view kpis",
            "create scenario",
            "compare scenarios",
            "export workbook",
            "read validation status",
            "read known limitations",
        ):
            assert item in text.lower(), (
                f"Pilot readiness checklist missing item: {item!r}"
            )

    def test_pilot_user_script_exists(self):
        path = REPO_ROOT / "docs" / "pilot_user_script.md"
        assert path.exists(), "docs/pilot_user_script.md must exist"
        text = path.read_text().lower()
        for step in (
            "standard solar",
            "capacity",
            "tariff",
            "opex",
            "run the model",
            "irr",
            "dscr",
            "downside",
            "compare",
            "export workbook",
            "known limitations",
        ):
            assert step in text, f"Pilot user script missing step keyword: {step!r}"


class TestPilotGuideReachable:
    def test_pilot_guide_route_returns_200(self, logged_in_client):
        r = logged_in_client.get("/pilot-guide", follow_redirects=True)
        assert r.status_code == 200

    def test_pilot_guide_route_renders_guide_content(self, logged_in_client):
        r = logged_in_client.get("/pilot-guide", follow_redirects=True)
        assert "External Pilot Guide" in r.text
        assert "recalibrated" in r.text

    def test_pilot_guide_linked_from_footer(self, logged_in_client):
        r = logged_in_client.get("/", follow_redirects=True)
        assert 'href="/pilot-guide"' in r.text

    def test_pilot_guide_linked_from_known_limitations_header(self, logged_in_client):
        r = logged_in_client.get("/known-limitations", follow_redirects=True)
        assert 'href="/pilot-guide"' in r.text


class TestKnownLimitationsReachable:
    def test_known_limitations_route_returns_200(self, logged_in_client):
        r = logged_in_client.get("/known-limitations", follow_redirects=True)
        assert r.status_code == 200

    def test_known_limitations_linked_from_footer(self, logged_in_client):
        r = logged_in_client.get("/", follow_redirects=True)
        assert 'href="/known-limitations"' in r.text


class TestValidationStatusReachable:
    def test_validation_status_linked_from_footer(self, logged_in_client):
        r = logged_in_client.get("/", follow_redirects=True)
        assert "Validation Status" in r.text
        assert "kl-validated-models" in r.text


class TestPilotCaveatPresent:
    def test_caveat_present_on_home(self, logged_in_client):
        r = logged_in_client.get("/", follow_redirects=True)
        assert "should be reviewed" in r.text
        assert "investment, lender, tax, accounting or legal" in r.text

    def test_caveat_present_on_known_limitations(self, logged_in_client):
        r = logged_in_client.get("/known-limitations", follow_redirects=True)
        assert "financial modelling estimates" in r.text

    def test_caveat_not_alarmist(self):
        text = (
            REPO_ROOT / "app/templates/partials/_app_footer.html"
        ).read_text().lower()
        for alarmist_word in ("danger", "warning!!", "critical risk", "do not use"):
            assert alarmist_word not in text


class TestNoInternalTerminologyLeaksInNewPilotSurfaces:
    def test_pilot_guide_page_template_clean(self):
        text = _strip_jinja_and_html_comments(
            (REPO_ROOT / "app/templates/pilot_guide_page.html").read_text()
        ).lower()
        # dominant-baseline is an SVG attribute on the favicon, not copy.
        text = text.replace("dominant-baseline", "")
        for term in FORBIDDEN_TERMS:
            assert term not in text, f"pilot_guide_page.html must not contain {term!r}"

    def test_footer_clean(self):
        text = _strip_jinja_and_html_comments(
            (REPO_ROOT / "app/templates/partials/_app_footer.html").read_text()
        ).lower()
        for term in FORBIDDEN_TERMS:
            assert term not in text, f"_app_footer.html must not contain {term!r}"

    def test_checklist_and_script_docs_clean(self):
        for relpath in (
            "docs/pilot_readiness_checklist.md",
            "docs/pilot_user_script.md",
        ):
            text = (REPO_ROOT / relpath).read_text().lower()
            for term in FORBIDDEN_TERMS:
                assert term not in text, f"{relpath} must not contain {term!r}"
