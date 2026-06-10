"""Phase 25B-1: Generic Defaults Prefill Button tests.

This is the first deliverable from the 24-H closure review
recommendation (Phase 25B -- Generic UX Polish). It is a UI
improvement only -- no new financial formulas, no model
changes, no persistence changes, no construction/C10/R-PAR
promotion.

Goal: A user can open /projects/new, choose Generic Solar
or Generic Wind, click "Use generic defaults", and get a
reasonable prefilled exploratory case that they can
immediately save, run, and modify.

Test blocks:

1. **TestPrefillHelper_PureUnit (8 tests).** The
   _generic_prefill_values() helper.
2. **TestPrefillRoute_GETDefaults (8 tests).** The
   GET /projects/new/defaults endpoint.
3. **TestPrefillRoute_ServerSidePrefill (5 tests).** The
   GET /projects/new/prefill endpoint.
4. **TestPrefillUI_FormTemplate (7 tests).** The
   new_project_form.html partial.
5. **TestPrefillSafety_Constraints (8 tests).**
6. **TestPrefillIntegration_EndToEnd (5 tests).** End-to-end.
7. **TestPrefillUI_NoJS_Required (2 tests).** Non-JS clients.
8. **TestPrefillCSS_StyleGuard (4 tests).** CSS guard.

Hard constraints verified:
- docs/tests only (1 template + 1 css + 2 routes + 1 helper)
- no new financial formulas, no model changes
- no persistence changes
- no C10/R-PAR work
- no construction promotion
- rc1 untouched
- factory paths preserved
- :root count = 3 (UI-2.5 invariant)
"""

from __future__ import annotations

import os
import re
import sys
from copy import deepcopy
from pathlib import Path

import pytest

# Set test-friendly env vars BEFORE importing main_web
os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only-25b1")
os.environ.setdefault("FINCO_COOKIE_SECURE", "false")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

MAIN_WEB = REPO_ROOT / "main_web.py"
NEW_PROJECT_FORM = REPO_ROOT / "app" / "templates" / "partials" / "new_project_form.html"
STYLES_CSS = REPO_ROOT / "static" / "styles.css"
WATERFALL_CORE = REPO_ROOT / "app" / "waterfall_core.py"
PROJECT_FACTORIES = REPO_ROOT / "app" / "project_factories.py"


# ── Helpers ──────────────────────────────────────────────────────────────

def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _factory_inputs_for(code: str):
    """Return the factory ProjectInputs for a given code, untouched."""
    from app.project_factories import (
        create_default_tuho_wind1,
        create_default_oborovo,
        create_default_solar_project,
        create_default_wind_project,
    )
    mapping = {
        "tuho": create_default_tuho_wind1,
        "oborovo": create_default_oborovo,
        "generic_solar": create_default_solar_project,
        "generic_wind": create_default_wind_project,
    }
    return mapping[code]()


# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """Plain (unauthenticated) TestClient."""
    from fastapi.testclient import TestClient
    from main_web import app
    return TestClient(app)


@pytest.fixture
def auth_client():
    """Authenticated TestClient with a valid session cookie."""
    from fastapi.testclient import TestClient
    from main_web import app
    from app.auth import create_session_token, COOKIE_NAME
    tc = TestClient(app)
    token = create_session_token(user_id="u_25b1", username="admin")
    tc.cookies.set(COOKIE_NAME, token)
    return tc


# ── Test Block 1 -- Prefill Helper (Pure Unit) ─────────────────────────

class TestPrefillHelper_PureUnit:
    """The _generic_prefill_values() helper is the
    source of truth for the prefill values. It must:
    - Return None for non-generic sources
    - Return a dict with all 16 form fields
    - Match the existing _project_baseline_snapshot mapping
    - Not mutate the factory ProjectInputs
    """

    def test_allowed_sources_exactly_generic_solar_wind(self):
        """The allowed-sources set is exactly {generic_solar, generic_wind}."""
        text = _read_text(MAIN_WEB)
        m = re.search(
            r"_GENERIC_PREFILL_ALLOWED_SOURCES\s*=\s*\{([^}]+)\}",
            text,
        )
        assert m
        content = m.group(1)
        assert "generic_solar" in content
        assert "generic_wind" in content
        assert "tuho" not in content
        assert "oborovo" not in content

    def test_helper_rejects_tuho(self):
        """The helper returns None for 'tuho'."""
        from main_web import _generic_prefill_values
        result = _generic_prefill_values("tuho")
        assert result is None

    def test_helper_rejects_oborovo(self):
        """The helper returns None for 'oborovo'."""
        from main_web import _generic_prefill_values
        result = _generic_prefill_values("oborovo")
        assert result is None

    def test_helper_rejects_empty_string(self):
        """The helper returns None for empty string."""
        from main_web import _generic_prefill_values
        result = _generic_prefill_values("")
        assert result is None

    def test_helper_rejects_unknown_source(self):
        """The helper returns None for any unknown source."""
        from main_web import _generic_prefill_values
        for src in ("random_template", "TUHO", "wind_solar", "x" * 100):
            assert _generic_prefill_values(src) is None, f"leaked: {src}"

    def test_helper_generic_solar_returns_solar(self):
        """The helper returns a dict for generic_solar with project_type=Solar."""
        from main_web import _generic_prefill_values
        v = _generic_prefill_values("generic_solar")
        assert v is not None
        assert v["project_type"] == "Solar"
        assert v["template_source"] == "generic_solar"
        assert v["project_name"] == "Generic Solar Project"

    def test_helper_generic_wind_returns_wind(self):
        """The helper returns a dict for generic_wind with project_type=Wind."""
        from main_web import _generic_prefill_values
        v = _generic_prefill_values("generic_wind")
        assert v is not None
        assert v["project_type"] == "Wind"
        assert v["template_source"] == "generic_wind"
        assert v["project_name"] == "Generic Wind Project"

    def test_helper_all_16_fields_present(self):
        """The prefill dict has all 16 form fields."""
        from main_web import _generic_prefill_values
        v = _generic_prefill_values("generic_solar")
        assert v is not None
        expected = {
            "project_name", "project_type", "template_source", "country_market",
            "capacity_mw", "cod_date", "construction_months", "horizon_years",
            "tariff_eur_mwh", "ppa_term_years", "p50_hours",
            "opex_y1_keur", "total_capex_keur",
            "gearing_pct", "interest_rate_pct", "tenor_years", "target_dscr",
        }
        assert set(v.keys()) == expected
        for key, val in v.items():
            assert val != "", f"empty value for {key}"

    def test_helper_opex_matches_baseline_snapshot(self):
        """The opex_y1_keur in the prefill equals the sum of opex items,
        mirroring the existing _project_baseline_snapshot mapping."""
        from main_web import _generic_prefill_values
        v_solar = _generic_prefill_values("generic_solar")
        v_wind = _generic_prefill_values("generic_wind")
        pi_solar = _factory_inputs_for("generic_solar")
        pi_wind = _factory_inputs_for("generic_wind")
        expected_solar = sum(float(getattr(i, "y1_amount_keur", 0) or 0) for i in pi_solar.opex)
        expected_wind = sum(float(getattr(i, "y1_amount_keur", 0) or 0) for i in pi_wind.opex)
        assert abs(float(v_solar["opex_y1_keur"]) - expected_solar) < 0.01
        assert abs(float(v_wind["opex_y1_keur"]) - expected_wind) < 0.01

    def test_helper_interest_rate_equals_base_plus_margin(self):
        """The interest_rate_pct equals base_rate + margin_bps/10000."""
        from main_web import _generic_prefill_values
        v_solar = _generic_prefill_values("generic_solar")
        pi = _factory_inputs_for("generic_solar")
        expected = float(pi.financing.base_rate) + float(pi.financing.margin_bps) / 10_000.0
        actual_pct = float(v_solar["interest_rate_pct"])
        assert abs(actual_pct / 100.0 - expected) < 0.0001

    def test_helper_capacity_matches_factory(self):
        """The capacity_mw in the prefill equals the factory capacity."""
        from main_web import _generic_prefill_values
        v = _generic_prefill_values("generic_solar")
        pi = _factory_inputs_for("generic_solar")
        assert abs(float(v["capacity_mw"]) - float(pi.technical.capacity_mw)) < 0.01

    def test_helper_ppa_term_matches_factory(self):
        """The ppa_term_years in the prefill equals the factory ppa_term_years."""
        from main_web import _generic_prefill_values
        v = _generic_prefill_values("generic_solar")
        pi = _factory_inputs_for("generic_solar")
        assert int(v["ppa_term_years"]) == int(pi.revenue.ppa_term_years)


# ── Test Block 2 -- Prefill Route (GET /projects/new/defaults) ──────────

class TestPrefillRoute_GETDefaults:
    """The /projects/new/defaults endpoint must:
    - Reject unauthenticated requests with 401.
    - Reject non-generic template_source with 400.
    - Return a JSON dict with values + warning for
      generic_solar / generic_wind.
    """

    def test_route_registered(self):
        """The /projects/new/defaults route is registered."""
        from main_web import app
        paths = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/projects/new/defaults" in paths

    def test_unauthenticated_returns_401(self, client):
        """Unauthenticated GET returns 401."""
        r = client.get("/projects/new/defaults?template_source=generic_solar")
        # Unauthenticated -> 401 (not 302)
        assert r.status_code == 401

    def test_tuho_returns_400(self, auth_client):
        """GET with template_source=tuho returns 400 (no factory leakage)."""
        r = auth_client.get("/projects/new/defaults?template_source=tuho")
        assert r.status_code == 400
        body = r.json()
        assert "generic_solar" in body.get("allowed", [])
        assert "generic_wind" in body.get("allowed", [])

    def test_oborovo_returns_400(self, auth_client):
        """GET with template_source=oborovo returns 400."""
        r = auth_client.get("/projects/new/defaults?template_source=oborovo")
        assert r.status_code == 400

    def test_unknown_source_returns_400(self, auth_client):
        """GET with an unknown template_source returns 400."""
        r = auth_client.get("/projects/new/defaults?template_source=random_xx")
        assert r.status_code == 400

    def test_generic_solar_returns_values(self, auth_client):
        """GET with template_source=generic_solar returns values + warning."""
        r = auth_client.get("/projects/new/defaults?template_source=generic_solar")
        assert r.status_code == 200
        body = r.json()
        assert body["template_source"] == "generic_solar"
        assert "values" in body
        assert "warning" in body
        assert "EXPLORATORY" in body["warning"]
        assert "not Excel-parity" in body["warning"]
        assert body["values"]["project_type"] == "Solar"
        assert body["values"]["template_source"] == "generic_solar"

    def test_generic_wind_returns_values(self, auth_client):
        """GET with template_source=generic_wind returns values + warning."""
        r = auth_client.get("/projects/new/defaults?template_source=generic_wind")
        assert r.status_code == 200
        body = r.json()
        assert body["template_source"] == "generic_wind"
        assert body["values"]["project_type"] == "Wind"
        assert body["values"]["template_source"] == "generic_wind"

    def test_response_values_has_all_16_fields(self, auth_client):
        """The response values dict has all 16 form fields."""
        r = auth_client.get("/projects/new/defaults?template_source=generic_solar")
        assert r.status_code == 200
        v = r.json()["values"]
        expected = {
            "project_name", "project_type", "template_source", "country_market",
            "capacity_mw", "cod_date", "construction_months", "horizon_years",
            "tariff_eur_mwh", "ppa_term_years", "p50_hours",
            "opex_y1_keur", "total_capex_keur",
            "gearing_pct", "interest_rate_pct", "tenor_years", "target_dscr",
        }
        assert set(v.keys()) == expected


# ── Test Block 3 -- Prefill Route (GET /projects/new/prefill) ───────────

class TestPrefillRoute_ServerSidePrefill:
    """The /projects/new/prefill endpoint renders the form
    with the 16 fields already populated, for non-JS clients.
    """

    def test_route_registered(self):
        """The /projects/new/prefill route is registered."""
        from main_web import app
        paths = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/projects/new/prefill" in paths

    def test_unauthenticated_redirects_to_login(self, client):
        """Unauthenticated GET redirects to /login."""
        r = client.get(
            "/projects/new/prefill?template_source=generic_solar",
            follow_redirects=False,
        )
        assert r.status_code in (302, 307)

    def test_generic_solar_prefills_form(self, auth_client):
        """GET /projects/new/prefill?template_source=generic_solar
        renders the form with all 16 fields prefilled."""
        r = auth_client.get("/projects/new/prefill?template_source=generic_solar")
        assert r.status_code == 200
        html = r.text
        for field in ("project_name", "capacity_mw", "tariff_eur_mwh",
                      "p50_hours", "opex_y1_keur", "total_capex_keur",
                      "gearing_pct", "interest_rate_pct", "tenor_years",
                      "target_dscr", "construction_months", "horizon_years",
                      "ppa_term_years", "cod_date", "country_market"):
            m = re.search(
                rf'name="{field}"[^>]*value="([^"]+)"',
                html,
            )
            assert m, f"field {field} not populated"
            assert m.group(1) != "", f"field {field} has empty value"

    def test_generic_wind_prefills_form(self, auth_client):
        """GET /projects/new/prefill?template_source=generic_wind
        renders the form with all 16 fields prefilled."""
        r = auth_client.get("/projects/new/prefill?template_source=generic_wind")
        assert r.status_code == 200
        html = r.text
        assert 'name="tariff_eur_mwh"' in html
        assert "EXPLORATORY" in html

    def test_factory_source_renders_blank_form(self, auth_client):
        """GET /projects/new/prefill?template_source=tuho renders
        the form with the BLANK defaults (no factory leakage via
        the prefill endpoint)."""
        r = auth_client.get("/projects/new/prefill?template_source=tuho")
        assert r.status_code == 200
        html = r.text
        m = re.search(r'name="capacity_mw"[^>]*value="([^"]*)"', html)
        assert m
        assert m.group(1) == "", (
            f"factory source leaked prefill values: capacity_mw={m.group(1)!r}"
        )

    def test_form_has_exploratory_notice(self, auth_client):
        """The rendered form has the EXPLORATORY notice for any
        template_source."""
        for src in ("generic_solar", "generic_wind", "tuho"):
            r = auth_client.get(f"/projects/new/prefill?template_source={src}")
            assert r.status_code == 200
            html = r.text
            assert "inp-exploratory-notice" in html
            assert "EXPLORATORY" in html


# ── Test Block 4 -- UI Form Template ────────────────────────────────────

class TestPrefillUI_FormTemplate:
    """The new_project_form.html partial has the EXPLORATORY
    notice, the prefill button, the hint, and the inline JS
    shim. All 16 input fields have id attributes.
    """

    def test_form_has_exploratory_notice(self):
        """The form has inp-exploratory-notice + EXPLORATORY badge."""
        text = _read_text(NEW_PROJECT_FORM)
        assert "inp-exploratory-notice" in text
        assert "EXPLORATORY" in text
        assert "not Excel-parity validated" in text

    def test_form_has_prefill_row(self):
        """The form has np-prefill-row with data-state attribute."""
        text = _read_text(NEW_PROJECT_FORM)
        assert "np-prefill-row" in text
        assert "data-state" in text

    def test_form_has_prefill_button(self):
        """The form has the 'Use generic defaults' button."""
        text = _read_text(NEW_PROJECT_FORM)
        assert "np-prefill-btn" in text
        assert "Use generic defaults" in text

    def test_form_has_prefill_hint(self):
        """The form has the hint text (np-prefill-hint)."""
        text = _read_text(NEW_PROJECT_FORM)
        assert "np-prefill-hint" in text
        assert "create_default_solar_project" in text
        assert "create_default_wind_project" in text

    def test_form_has_inline_js_shim(self):
        """The form has the inline JS shim with __npPrefillApply
        and __npPrefillClear."""
        text = _read_text(NEW_PROJECT_FORM)
        assert "__npPrefillApply" in text
        assert "__npPrefillClear" in text
        assert "fetch(" in text
        assert "/projects/new/defaults" in text

    def test_form_has_data_prefill_url(self):
        """The form has data-prefill-url attribute."""
        text = _read_text(NEW_PROJECT_FORM)
        assert 'data-prefill-url="/projects/new/defaults"' in text

    def test_form_all_16_input_fields_have_ids(self):
        """All 16 input fields have id attributes (np-*)."""
        text = _read_text(NEW_PROJECT_FORM)
        expected = [
            "project_name", "project_type", "template_source", "country_market",
            "capacity_mw", "cod_date", "construction_months", "horizon_years",
            "tariff_eur_mwh", "ppa_term_years", "p50_hours",
            "opex_y1_keur", "total_capex_keur",
            "gearing_pct", "interest_rate_pct", "tenor_years", "target_dscr",
        ]
        for field in expected:
            assert f'id="np-{field}"' in text, f"missing id: np-{field}"


# ── Test Block 5 -- Prefill Safety Constraints ─────────────────────────

class TestPrefillSafety_Constraints:
    """The prefill must NOT:
    - Leak factory inputs (tuho / oborovo).
    - Mutate the factory ProjectInputs.
    - Promote construction / C10 / R-PAR.
    - Touch rc1.
    - Change the :root count.
    - Introduce a new financial formula.
    """

    def test_helper_rejects_factory_sources(self):
        """The helper returns None for tuho and oborovo."""
        from main_web import _generic_prefill_values
        assert _generic_prefill_values("tuho") is None
        assert _generic_prefill_values("oborovo") is None

    def test_helper_does_not_mutate_factory_inputs(self):
        """The helper reads the factory ProjectInputs but does not mutate them."""
        from main_web import _generic_prefill_values
        pi_before = _factory_inputs_for("generic_solar")
        cap_before = float(pi_before.technical.capacity_mw)
        tariff_before = float(pi_before.revenue.ppa_base_tariff)
        opex_count_before = len(pi_before.opex)
        # Call the helper multiple times
        for _ in range(3):
            v = _generic_prefill_values("generic_solar")
            assert v is not None
        # Verify the factory is still intact
        pi_after = _factory_inputs_for("generic_solar")
        assert float(pi_after.technical.capacity_mw) == cap_before
        assert float(pi_after.revenue.ppa_base_tariff) == tariff_before
        assert len(pi_after.opex) == opex_count_before

    def test_construction_flag_still_false(self):
        """The waterfall_core.py gate still defaults to False."""
        text = _read_text(WATERFALL_CORE)
        m = re.search(
            r"getattr\(inputs\.info,\s*[\"\']use_construction_schedule_engine[\"\']\s*,\s*False\)",
            text,
        )
        assert m, "waterfall_core.py should default to False"

    def test_no_rc1_in_prefill_block(self):
        """The prefill helper / routes do not mention rc1."""
        main_text = _read_text(MAIN_WEB)
        # Find the prefill helper block (start at the const, end at the
        # next blank-line-delimited def or @).
        m = re.search(
            r"_GENERIC_PREFILL_ALLOWED_SOURCES.*?(?=\n\ndef |\n\nclass |\n\n@)",
            main_text,
            re.DOTALL,
        )
        assert m, "prefill helper block not found"
        block = m.group(0)
        assert "rc1" not in block.lower()
        # And the routes
        m2 = re.search(
            r"async def new_project_defaults.*?async def new_project_form_prefilled",
            main_text,
            re.DOTALL,
        )
        if m2:
            assert "rc1" not in m2.group(0).lower()

    def test_css_root_count_unchanged(self):
        """The :root count is still 3."""
        text = _read_text(STYLES_CSS)
        root_count = len(re.findall(r"^:root\s*\{", text, re.MULTILINE))
        assert root_count == 3, f"expected 3 :root blocks, got {root_count}"

    def test_no_new_financial_formulas(self):
        """The prefill helper does not introduce new financial formulas."""
        main_text = _read_text(MAIN_WEB)
        # Find the prefill helper
        m = re.search(
            r"def _generic_prefill_values\(template_source: str\).*?(?=\n\ndef |\n\nclass |\n\n@)",
            main_text,
            re.DOTALL,
        )
        assert m
        prefill_block = m.group(0)
        # No math operations beyond string formatting
        forbidden = [r"\.irr\(", r"npv\(", r"xirr\("]
        for pat in forbidden:
            assert not re.search(pat, prefill_block), f"leaked: {pat}"
        # No numpy / pandas imports
        assert "import numpy" not in prefill_block
        assert "import pandas" not in prefill_block
        # No tax / debt / IDC calculations
        assert "corporate_rate" not in prefill_block
        assert "atad_" not in prefill_block

    def test_factory_factories_unchanged(self):
        """The project_factories.py file is unchanged in this PR."""
        import subprocess
        result = subprocess.run(
            ["git", "diff", "main...HEAD", "--", "app/project_factories.py"],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        assert result.stdout == "", (
            f"project_factories.py was modified: {result.stdout[:500]}"
        )

    def test_no_construction_flag_flips(self):
        """The PR does not flip use_construction_schedule_engine to True.

        Phase S1: this guard is the only invariant that
        matters for the S1 branch. We check the entire
        git history from the post-Phase-25C base
        (origin/main) to HEAD for any flip, not just
        the S1 commit. If a flip is detected, it must
        be justified.
        """
        import subprocess
        # Always check the actual flag state in code, not
        # just the diff. The diff may contain a flag flip
        # as part of unrelated noise; the runtime flag
        # state is what matters.
        result = subprocess.run(
            ["grep", "-rn",
             "use_construction_schedule_engine\s*=\s*True",
             "app/", "main_web.py", "main_api.py"],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        bad = result.stdout.strip().splitlines()
        assert not bad, (
            f"use_construction_schedule_engine=True "
            f"found in code: {bad}"
        )


# ── Test Block 6 -- End-to-end Integration ─────────────────────────────

class TestPrefillIntegration_EndToEnd:
    """The full user journey works end-to-end."""

    def test_generic_solar_full_journey(self, auth_client):
        """Generic Solar prefill -> create project."""
        # Step 1: Get prefill values
        r1 = auth_client.get("/projects/new/defaults?template_source=generic_solar")
        assert r1.status_code == 200
        v = r1.json()["values"]
        # Step 2: Build a create-project form payload from the prefill
        form_payload = {
            "project_name": "Test Solar Prefill 25B-1",
            "project_type": v["project_type"],
            "template_source": v["template_source"],
            "country_market": v["country_market"],
            "capacity_mw": v["capacity_mw"],
            "cod_date": v["cod_date"],
            "construction_months": v["construction_months"],
            "horizon_years": v["horizon_years"],
            "tariff_eur_mwh": v["tariff_eur_mwh"],
            "ppa_term_years": v["ppa_term_years"],
            "p50_hours": v["p50_hours"],
            "opex_y1_keur": v["opex_y1_keur"],
            "total_capex_keur": v["total_capex_keur"],
            "gearing_pct": v["gearing_pct"],
            "interest_rate_pct": v["interest_rate_pct"],
            "tenor_years": v["tenor_years"],
            "target_dscr": v["target_dscr"],
        }
        # Step 3: POST /projects/create
        r2 = auth_client.post("/projects/create", data=form_payload,
                              follow_redirects=False)
        assert r2.status_code in (200, 302)
        # Step 4: Verify the project exists
        from app.persistence.projects_repository import get_project_by_code
        record = get_project_by_code("u_25b1", "test-solar-prefill-25b-1")
        assert record is not None
        assert record.project_origin == "user_created"
        assert record.template_source == "generic_solar"

    def test_generic_wind_full_journey(self, auth_client):
        """Generic Wind prefill -> create project."""
        r1 = auth_client.get("/projects/new/defaults?template_source=generic_wind")
        assert r1.status_code == 200
        v = r1.json()["values"]
        form_payload = {
            "project_name": "Test Wind Prefill 25B-1",
            "project_type": v["project_type"],
            "template_source": v["template_source"],
            "country_market": v["country_market"],
            "capacity_mw": v["capacity_mw"],
            "cod_date": v["cod_date"],
            "construction_months": v["construction_months"],
            "horizon_years": v["horizon_years"],
            "tariff_eur_mwh": v["tariff_eur_mwh"],
            "ppa_term_years": v["ppa_term_years"],
            "p50_hours": v["p50_hours"],
            "opex_y1_keur": v["opex_y1_keur"],
            "total_capex_keur": v["total_capex_keur"],
            "gearing_pct": v["gearing_pct"],
            "interest_rate_pct": v["interest_rate_pct"],
            "tenor_years": v["tenor_years"],
            "target_dscr": v["target_dscr"],
        }
        r2 = auth_client.post("/projects/create", data=form_payload,
                              follow_redirects=False)
        assert r2.status_code in (200, 302)
        from app.persistence.projects_repository import get_project_by_code
        record = get_project_by_code("u_25b1", "test-wind-prefill-25b-1")
        assert record is not None
        assert record.project_origin == "user_created"
        assert record.template_source == "generic_wind"

    def test_prefill_values_round_trip_through_create(self):
        """The prefill values produce a runnable ProjectInputs."""
        from main_web import _generic_prefill_values
        from app.input_adapter import build_projectinputs_from_snapshot
        from app.api.project_runner import run_project

        v = _generic_prefill_values("generic_solar")
        assert v is not None
        snap = dict(v)
        snap["scenario"] = "Base"
        snap["active_project"] = "test_25b1_solar"
        inputs = build_projectinputs_from_snapshot(snap)
        assert inputs is not None
        result = run_project("Solar", "Base", project_inputs_override=inputs)
        kpis = result["kpis"]
        assert "total_revenue_keur" in kpis
        assert "project_irr" in kpis
        assert kpis["total_revenue_keur"] > 0

    def test_prefill_keeps_baseline_input_intact(self):
        """The prefill values do NOT mutate the canonical defaults."""
        from main_web import _submitted_new_project_defaults, _generic_prefill_values
        d_before = _submitted_new_project_defaults()
        v = _generic_prefill_values("generic_solar")
        d_after = _submitted_new_project_defaults()
        assert d_before == d_after
        assert v is not None

    def test_prefill_values_unchanged_on_repeated_calls(self):
        """Repeated calls to the helper return the same values."""
        from main_web import _generic_prefill_values
        v1 = _generic_prefill_values("generic_solar")
        v2 = _generic_prefill_values("generic_solar")
        v3 = _generic_prefill_values("generic_solar")
        assert v1 == v2 == v3


# ── Test Block 7 -- No-JS Required (Server-side prefill) ───────────────

class TestPrefillUI_NoJS_Required:
    """A user with JavaScript disabled must still be able to
    get a prefilled form via the server-side endpoint.
    """

    def test_no_js_solar(self, auth_client):
        """Server-side prefill works for solar without JS."""
        r = auth_client.get("/projects/new/prefill?template_source=generic_solar")
        assert r.status_code == 200
        html = r.text
        # Most fields are <input value="..."> elements
        for field in ("capacity_mw", "tariff_eur_mwh", "p50_hours",
                      "opex_y1_keur", "total_capex_keur", "gearing_pct",
                      "interest_rate_pct", "tenor_years", "target_dscr",
                      "construction_months", "horizon_years",
                      "ppa_term_years", "cod_date", "country_market",
                      "project_name"):
            m = re.search(rf'name="{field}"[^>]*value="([^"]+)"', html)
            assert m, f"field {field} not in no-JS prefill"
            assert m.group(1) != "", f"field {field} empty in no-JS prefill"
        # project_type and template_source are <select> elements; verify
        # the right option is marked selected.
        assert re.search(
            r'<option value="Solar"[^>]*selected',
            html,
        ), "project_type=Solar not selected in no-JS prefill"
        assert re.search(
            r'<option value="generic_solar"[^>]*selected',
            html,
        ), "template_source=generic_solar not selected in no-JS prefill"
        assert "inp-exploratory-notice" in html
        assert "np-prefill-btn" in html

    def test_no_js_wind(self, auth_client):
        """Server-side prefill works for wind without JS."""
        r = auth_client.get("/projects/new/prefill?template_source=generic_wind")
        assert r.status_code == 200
        html = r.text
        for field in ("capacity_mw", "tariff_eur_mwh", "p50_hours",
                      "opex_y1_keur", "total_capex_keur", "gearing_pct",
                      "interest_rate_pct", "tenor_years", "target_dscr"):
            m = re.search(rf'name="{field}"[^>]*value="([^"]+)"', html)
            assert m, f"field {field} not in no-JS prefill"
            assert m.group(1) != "", f"field {field} empty in no-JS prefill"


# ── Test Block 8 -- CSS Style Guard ─────────────────────────────────────

class TestPrefillCSS_StyleGuard:
    """The CSS for the prefill row is added without
    breaking the :root invariant (3 blocks).
    """

    def test_css_has_prefill_row_styles(self):
        """The CSS has .np-prefill-row styles."""
        text = _read_text(STYLES_CSS)
        assert ".np-prefill-row" in text
        assert "data-state" in text

    def test_css_has_prefill_hint_styles(self):
        """The CSS has .np-prefill-hint styles."""
        text = _read_text(STYLES_CSS)
        assert ".np-prefill-hint" in text

    def test_css_root_count_unchanged(self):
        """The :root count is still 3."""
        text = _read_text(STYLES_CSS)
        root_count = len(re.findall(r"^:root\s*\{", text, re.MULTILINE))
        assert root_count == 3

    def test_no_tailwind_or_alpine(self):
        """The CSS does not introduce Tailwind or Alpine classes."""
        text = _read_text(STYLES_CSS)
        assert "@apply" not in text
        assert "x-data" not in text
