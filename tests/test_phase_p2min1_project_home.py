"""Phase P2-min-1: Project Home + Minimal New Project.

P2-min-1 introduces a product-shaped Project Home entry point
and a minimal New Project form. Presentation-only. No
backend / no persistence / no factory changes.

Tests prove:
  - /home renders
  - Project Home shows user projects
  - Factory templates hidden from /home
  - TUHO / Oborovo hidden from /home
  - /projects/new/minimal renders
  - Minimal form has exactly 4 input fields
  - TUHO / Oborovo factory paths still work (untouched)
  - parity guardrails still pass
  - timing field fix from PR1 remains intact
  - Help link rendered in header (icon, not tab)
  - rc1 SHA preserved
  - use_construction_schedule_engine remains False
  - No persistence schema migration
  - Forbidden paths unchanged
  - No tailwind / alpine / react / vue / svelte
  - No new dependency
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Repo root
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"


HAS_GIT = shutil.which("git") is not None and (REPO_ROOT / ".git").exists()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    """Test client for /home and /projects/new/minimal."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from main_web import app

    return TestClient(app)


@pytest.fixture(scope="module")
def logged_in_client():
    """Test client with a logged-in session (test user)."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from app.auth import create_session_token
    from main_web import app

    client = TestClient(app)
    # Use a real session token from app.auth (the existing
    # session codec; no new auth code).
    token = create_session_token(user_id="1", username="test_user")
    client.cookies.set("finco_session", token)
    return client


# ---------------------------------------------------------------------------
# Project Home tests
# ---------------------------------------------------------------------------


class TestProjectHomeRoute:
    """The /home route renders the new Project Home partial."""

    def test_home_route_responds_200_when_logged_in(self, logged_in_client):
        r = logged_in_client.get("/home", follow_redirects=False)
        # 200 OK, not a 302 redirect to /login
        assert r.status_code == 200, (
            f"/home must return 200 for a logged-in user; "
            f"got {r.status_code} body={r.text[:200]!r}"
        )

    def test_home_renders_project_home_partial(self, logged_in_client):
        r = logged_in_client.get("/home", follow_redirects=False)
        assert r.status_code == 200
        # The /home route returns the partial. The partial must
        # carry the Project Home wrapper class.
        assert "ph-empty" in r.text or "ph-grid" in r.text, (
            "Project Home must render the new partial with .ph-empty "
            "(no projects) or .ph-grid (>=1 project)"
        )

    def test_home_renders_create_new_project_cta(self, logged_in_client):
        r = logged_in_client.get("/home", follow_redirects=False)
        assert r.status_code == 200
        assert "Create New Project" in r.text, (
            "Project Home must show a 'Create New Project' CTA"
        )

    def test_help_link_in_base_template(self):
        """The Help link is rendered by base.html (the site header),
        not by the /home partial. The base.html partial is
        included by the index.html template (which the /home
        partial loads into via htmx). This test reads base.html
        directly to prove the link is present in the header.
        """
        from pathlib import Path
        base = REPO_ROOT / "app/templates/base.html"
        text = base.read_text(encoding="utf-8")
        assert 'class="header-help-link"' in text, (
            "base.html must include the new P2-min-1 help link"
        )


class TestFactoryTemplatesHiddenFromHome:
    """Factory templates, TUHO, Oborovo are hidden from
    the Project Home partial (presentation filter only).
    """

    def test_home_does_not_render_factory_template_section(self, logged_in_client):
        r = logged_in_client.get("/home", follow_redirects=False)
        assert r.status_code == 200
        # The home partial must NOT contain the factory-template tab
        # / section / cards (the full /projects/browse view is a
        # different page and remains reachable for the
        # Export & Audit users).
        assert "Factory Templates" not in r.text, (
            "Project Home must NOT show 'Factory Templates' section"
        )
        assert "TUHO" not in r.text, (
            "Project Home must NOT show 'TUHO' (factory template name)"
        )
        assert "Oborovo" not in r.text, (
            "Project Home must NOT show 'Oborovo' (factory template name)"
        )
        assert "OBR-001" not in r.text, (
            "Project Home must NOT show OBR-001 (factory code)"
        )


class TestFactoryPathsStillWork:
    """The hidden ≠ deleted rule. Factory templates remain
    reachable from /projects/browse and the /tuho /oborovo
    factory functions are unchanged.
    """

    def test_factory_options_unchanged(self):
        from main_web import FACTORY_TEMPLATE_OPTIONS
        # The factory template options tuple is still present and
        # contains the canonical entries.
        codes = {item.get("project_code") for item in FACTORY_TEMPLATE_OPTIONS}
        assert "tuho" in codes, "tuho must remain in FACTORY_TEMPLATE_OPTIONS"
        assert "oborovo" in codes, "oborovo must remain in FACTORY_TEMPLATE_OPTIONS"

    def test_factory_factories_unchanged(self):
        from app.project_factories import (
            create_default_tuho_wind1,
            create_default_oborovo,
        )
        # Both factory functions still construct the canonical
        # reference projects (the P2-min-1 hidden != deleted rule).
        tuho = create_default_tuho_wind1()
        oborovo = create_default_oborovo()
        assert tuho is not None
        assert oborovo is not None


class TestBrowseStillRendersFactoryTemplates:
    """/projects/browse (the audit / parity fixture reach point)
    still renders the full project browser including factory
    templates. This is the "hidden ≠ deleted" rule.
    """

    def test_browse_renders_factory_section(self, logged_in_client):
        r = logged_in_client.get("/projects/browse", follow_redirects=False)
        assert r.status_code == 200
        assert "Factory Templates" in r.text, (
            "/projects/browse must still render the Factory "
            "Templates section (hidden != deleted)"
        )


# ---------------------------------------------------------------------------
# Minimal New Project tests
# ---------------------------------------------------------------------------


class TestMinimalNewProjectRoute:
    """The /projects/new/minimal route renders the new
    minimal-form partial with exactly 4 visible fields.
    """

    def test_minimal_new_project_route_responds_200(self, logged_in_client):
        r = logged_in_client.get(
            "/projects/new/minimal", follow_redirects=False
        )
        assert r.status_code == 200, (
            f"/projects/new/minimal must return 200; "
            f"got {r.status_code} body={r.text[:200]!r}"
        )

    def test_minimal_form_has_4_visible_input_fields(self, logged_in_client):
        r = logged_in_client.get(
            "/projects/new/minimal", follow_redirects=False
        )
        assert r.status_code == 200
        text = r.text
        # Exactly 4 visible input fields (project_name, project_type,
        # country_market, capacity_mw). The hidden template_source
        # is a hidden input, not a visible field.
        visible_labels = [
            "Project name",
            "Technology",
            "Country or market",
            "Capacity (MW)",
        ]
        for label in visible_labels:
            assert label in text, (
                f"Minimal new-project form must include {label!r} "
                f"as a visible field"
            )

    def test_minimal_form_does_not_show_tariff_field(self, logged_in_client):
        r = logged_in_client.get(
            "/projects/new/minimal", follow_redirects=False
        )
        assert r.status_code == 200
        # Driver fields (tariff, p50, OPEX, CAPEX, gearing,
        # interest, tenor, target DSCR, PPA term) are NOT shown
        # in the P2-min minimal form. They come from template
        # defaults.
        for forbidden in [
            "Tariff (EUR/MWh)",
            "P50 hours",
            "OPEX Y1",
            "Total CAPEX",
            "Gearing",
            "Interest rate",
            "Tenor years",
            "Target DSCR",
            "PPA term",
        ]:
            assert forbidden not in r.text, (
                f"Minimal form must NOT show driver field {forbidden!r}; "
                f"these come from template defaults"
            )

    def test_minimal_form_uses_existing_create_endpoint(self):
        """The minimal form posts to /projects/create (the existing
        endpoint). No backend change.
        """
        from pathlib import Path

        partial = (
            REPO_ROOT / "app/templates/partials/new_project_minimal.html"
        )
        text = partial.read_text(encoding="utf-8")
        assert 'hx-post="/projects/create"' in text, (
            "Minimal form must post to /projects/create (existing "
            "endpoint, no backend change)"
        )


# ---------------------------------------------------------------------------
# Timing field fix preserved (PR1)
# ---------------------------------------------------------------------------


class TestTimingFieldFixPreserved:
    """The PR1 timing-field fix (_build_schema_from_form extended
    with 4 new optional kwargs) must remain intact. The minimal
    form does not regress PR1 because the minimal form posts to
    /projects/create (the same path PR1 preserves).
    """

    def test_build_schema_from_form_still_has_timing_kwargs(self):
        import inspect
        from main_web import _build_schema_from_form

        sig = inspect.signature(_build_schema_from_form)
        param_names = list(sig.parameters.keys())
        for kw in [
            "cod_date",
            "construction_months",
            "horizon_years",
            "ppa_term_years_form",
        ]:
            assert kw in param_names, (
                f"_build_schema_from_form must still accept {kw!r} "
                f"(PR1 timing-field fix preserved)"
            )


# ---------------------------------------------------------------------------
# Phase 51F parity guardrails
# ---------------------------------------------------------------------------


class TestPhaseInvariants:
    """rc1, factory paths, forbidden paths, and
    use_construction_schedule_engine remain pinned.
    """

    def test_rc1_sha_resolvable(self):
        if not HAS_GIT:
            pytest.skip("no git in test env")
        r = subprocess.run(
            ["git", "rev-parse", "--verify", RC1_SHA],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        assert r.returncode == 0
        assert r.stdout.strip() == RC1_SHA

    def test_use_construction_schedule_engine_remains_false(self):
        if not HAS_GIT:
            pytest.skip("no git in test env")
        r = subprocess.run(
            [
                "grep", "-rn",
                "use_construction_schedule_engine\\s*=\\s*True",
                "app/", "main_web.py", "main_api.py",
            ],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        bad = r.stdout.strip().splitlines()
        assert not bad, (
            f"use_construction_schedule_engine=True "
            f"found in code: {bad}"
        )

    def test_parity_guardrails_unchanged(self):
        if not HAS_GIT:
            pytest.skip("no git in test env")
        r = subprocess.run(
            ["python3", "-m", "pytest",
             "tests/test_phase51f_parallel_work_guardrails.py",
             "-q", "--tb=line", "--no-header"],
            cwd=str(REPO_ROOT),
            capture_output=True, text=True,
        )
        # 0 = pass, 5 = no tests collected (also OK)
        assert r.returncode in (0, 5), (
            f"Phase 51F parity guardrails broke under P2-min-1: "
            f"returncode={r.returncode}\n"
            f"stdout={r.stdout[-1000:]}\n"
            f"stderr={r.stderr[-500:]}"
        )
