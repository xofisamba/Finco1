"""Phase P2-FIX-5C — Dashboard / KPI Restoration.

When a project opens, the user should see:
- A single Dashboard (Phase P2-min-3 Dashboard v1) with
  KPI cards: Project IRR, Equity IRR, NPV, Min DSCR,
  Avg DSCR, Senior Debt, Realized Gearing, Revenue,
  EBITDA.
- A clear "Run model" CTA when no runtime snapshot
  exists.
- No internal machinery text reintroduced.
- No legacy KPI grid (Phase P2-min-2 8-card placeholders)
  showing dash-only values.
"""

from __future__ import annotations

import os
import re

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-p2fix5c")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_session_token  # noqa: E402
from main_web import app  # noqa: E402

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


PROJECTS_TO_TEST = ["tuho", "oborovo", "generic_solar", "generic_wind"]


@pytest.fixture(scope="module")
def logged_in_client():
    client = TestClient(app)
    token = create_session_token(user_id="1", username="test_user")
    client.cookies.set("finco_session", token)
    return client


# ─────────────────────────────────────────────────────────────────────
# 1. Dashboard renders for every project type
# ─────────────────────────────────────────────────────────────────────


class TestDashboardRenders:
    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_dashboard_renders_for_all_projects(self):
        for project_code in PROJECTS_TO_TEST:
            r = self.client.get(
                f"/?project={project_code}", follow_redirects=True
            )
            assert r.status_code == 200
            assert "dashboard-v1" in r.text, (
                f"{project_code} workspace does not render the "
                f"P2-min-3 Dashboard v1"
            )

    def test_dashboard_includes_required_kpi_labels(self):
        """The dashboard must reference all 9 KPI keys."""
        for project_code in PROJECTS_TO_TEST:
            r = self.client.get(
                f"/?project={project_code}", follow_redirects=True
            )
            for kpi in (
                "Project IRR",
                "Equity IRR",
                "Senior Debt",
                "Realized Gearing",
                "Min DSCR",
                "Avg DSCR",
                "Project NPV",
                "Y1 Revenue",
                "Y1 EBITDA",
            ):
                assert kpi in r.text, (
                    f"{project_code} dashboard missing KPI label: "
                    f"{kpi!r}"
                )


# ─────────────────────────────────────────────────────────────────────
# 2. Run model CTA when no runtime snapshot exists
# ─────────────────────────────────────────────────────────────────────


class TestRunModelCTA:
    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_run_model_cta_for_fresh_open(self):
        """A fresh-open workspace (no runtime snapshot
        yet) shows a 'No run yet' CTA with a 'Run model'
        button."""
        for project_code in PROJECTS_TO_TEST:
            r = self.client.get(
                f"/?project={project_code}", follow_redirects=True
            )
            assert "dashboard-run-cta" in r.text, (
                f"{project_code} workspace missing dashboard-run-cta"
            )
            assert "No run yet" in r.text, (
                f"{project_code} workspace missing 'No run yet' copy"
            )
            assert "Run model" in r.text, (
                f"{project_code} workspace missing 'Run model' button"
            )

    def test_run_model_button_posts_to_run_endpoint(self):
        """The 'Run model' button uses HTMX hx-post to /run."""
        r = self.client.get(
            "/?project=generic_solar", follow_redirects=True
        )
        # Find the Run model button (HTMX pattern)
        m = re.search(
            r'hx-post="/run"[^>]+>Run model',
            r.text,
        )
        assert m is not None, (
            "Run model button does not post to /run endpoint"
        )


# ─────────────────────────────────────────────────────────────────────
# 3. Legacy KPI grid removed
# ─────────────────────────────────────────────────────────────────────


class TestLegacyKPIGridRemoved:
    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_legacy_kpi_grid_id_not_present(self):
        """The legacy <div id='kpi-grid'> with 8 dash-only
        placeholders must not be present in the rendered
        workspace."""
        for project_code in PROJECTS_TO_TEST:
            r = self.client.get(
                f"/?project={project_code}", follow_redirects=True
            )
            assert 'id="kpi-grid"' not in r.text, (
                f"{project_code} workspace still has legacy "
                f"id='kpi-grid' block"
            )

    def test_legacy_kpi_ids_not_present(self):
        """The legacy individual KPI IDs
        (kpi-project-irr, kpi-equity-irr, kpi-avg-dscr, ...)
        must not be present (they lived in the legacy
        dash-only grid)."""
        legacy_ids = (
            "kpi-project-irr",
            "kpi-equity-irr",
            "kpi-avg-dscr",
            "kpi-senior-debt",
            "kpi-revenue",
            "kpi-ebitda",
            "kpi-distributions",
            "kpi-warnings",
        )
        for project_code in PROJECTS_TO_TEST:
            r = self.client.get(
                f"/?project={project_code}", follow_redirects=True
            )
            for legacy_id in legacy_ids:
                assert f'id="{legacy_id}"' not in r.text, (
                    f"{project_code} workspace still has legacy "
                    f"id='{legacy_id}' element"
                )

    def test_only_one_dashboard_grid_present(self):
        """Only one KPI grid is rendered (the P2-min-3
        Dashboard v1, class='dashboard-kpi-grid'). The
        legacy class='kpi-grid' must not appear."""
        for project_code in PROJECTS_TO_TEST:
            r = self.client.get(
                f"/?project={project_code}", follow_redirects=True
            )
            # Count plain kpi-grid (not dashboard-kpi-grid)
            assert len(re.findall(
                r'class="kpi-grid"', r.text
            )) == 0, (
                f"{project_code} workspace has a legacy kpi-grid"
            )
            # The dashboard-kpi-grid should be present
            assert 'class="dashboard-kpi-grid"' in r.text, (
                f"{project_code} workspace missing the "
                f"dashboard-kpi-grid (P2-min-3 Dashboard v1)"
            )


# ─────────────────────────────────────────────────────────────────────
# 4. No internal machinery text reintroduced
# ─────────────────────────────────────────────────────────────────────


class TestNoInternalMachineryReintroduced:
    @pytest.fixture(autouse=True)
    def inject(self, logged_in_client):
        self.client = logged_in_client

    def test_workspace_no_lifecycle_clarity_in_normal_mode(self):
        """'Lifecycle Clarity' must not appear in the
        normal-mode dashboard area (only in the audit
        tab)."""
        for project_code in PROJECTS_TO_TEST:
            r = self.client.get(
                f"/?project={project_code}", follow_redirects=True
            )
            # Find the dashboard section
            m = re.search(
                r'<section class="dashboard"[^>]*>(.*?)</section>',
                r.text,
                flags=re.DOTALL,
            )
            if m:
                dash_section = m.group(1)
                assert "Lifecycle Clarity" not in dash_section
                assert "Export Lineage" not in dash_section
                assert "Governance Posture" not in dash_section
                assert "Review boundary" not in dash_section

    def test_dashboard_does_not_show_factory_or_baseline(self):
        for project_code in PROJECTS_TO_TEST:
            r = self.client.get(
                f"/?project={project_code}", follow_redirects=True
            )
            m = re.search(
                r'<section class="dashboard"[^>]*>(.*?)</section>',
                r.text,
                flags=re.DOTALL,
            )
            if m:
                dash_section = m.group(1).lower()
                for term in ("factory", "baseline", "fixture"):
                    assert term not in dash_section


# ─────────────────────────────────────────────────────────────────────
# 5. File scope: P2-FIX-5C is presentation-only
# ─────────────────────────────────────────────────────────────────────


class TestFileScope:
    def test_only_allowed_files_changed(self):
        import shutil
        import subprocess
        if shutil.which("git") is None or not (REPO_ROOT / ".git").exists():
            pytest.skip("git not available")
        result = subprocess.run(
            [
                "git", "-C", str(REPO_ROOT),
                "diff", "--name-only", "origin/main",
            ],
            capture_output=True,
            text=True,
        )
        changed = [
            f.strip() for f in result.stdout.strip().split("\n")
            if f.strip()
        ]
        allowed_prefixes = (
            "app/templates/partials/workspace_shell.html",
            "app/templates/partials/_state_banner.html",
            "app/templates/partials/inputs_section.html",
            "app/templates/partials/_standalone_header.html",
            "app/templates/index.html",
            "main_web.py",
            "static/styles.css",
            "tests/test_phase_p2fix3_c2_first_edit.py",
            "tests/test_phase_p2fix5b_normal_mode_shell_strip.py",
            "tests/test_phase_p2fix5c_dashboard_kpi.py",
            "tests/test_phase_p2fix5d_five_area_navigation.py",
            "tests/test_phase_p2fix5e_reference_ux.py",
            "tests/test_phase_p2fix6_c2_create_copy_ui.py",
            "tests/test_phase_p2fix7_production_cleanup.py",
            "tests/test_phase_p2fix7a_css_parser_cleanup.py",
            "tests/test_phase_p2fix2_",  # P2-FIX-7A cross-arc
            "tests/test_phase_p2fix4_",  # P2-FIX-7A cross-arc
            "docs/phase_p2fix5c_",
            "reports/phase_p2fix5c_",
            "docs/phase_p2fix7_",
            "reports/phase_p2fix7_",
            "docs/phase_p2fix7a_",
            "reports/phase_p2fix7a_",
            # P2-FIX-8 cross-arc allowlist
            "app/templates/base.html",
            "app/templates/project_home_page.html",
            "app/templates/project_new_page.html",
            "app/templates/project_browse_page.html",
            "app/templates/partials/workspace_tabs.html",
            "app/templates/partials/project_home.html",
            "app/middleware/security_headers.py",
            "scripts/",
            "tests/test_phase_p2fix8_",
            "tests/test_phase_p2fix5a_",
            # WF cross-arc allowlist
            "app/ui/dashboard.py",
            "app/templates/partials/_dashboard_oob.html",
            "tests/test_phase_wf1_",
            "app/ui/scenario_matrix.py",
            "app/templates/partials/scenario_matrix.html",
            "tests/test_phase_m2_",
            "tests/test_phase_m1_",
            "tests/test_phase_m3_",
            "tests/test_phase_m4_",
            "app/templates/partials/_matrix_cell_updated.html",
            "app/templates/partials/_matrix_cell_edit.html",
            "app/templates/partials/_matrix_run_result.html",
            # WF-6 cross-arc patches
            "tests/test_phase_wf6_",
            "app/templates/partials/scenario_tab.html",
        )
        disallowed_prefixes = (
            "app/persistence/",
            "app/services/",
            "app/waterfall_core.py",
            "app/project_factories.py",
            "app/excel_export.py",
            "main_api.py",
            "static/app.js",
        )
        for f in changed:
            with_dash = [f.startswith(p) for p in disallowed_prefixes]
            assert not any(with_dash), (
                f"Disallowed file changed: {f}"
            )
            ok = [f.startswith(p) for p in allowed_prefixes]
            assert any(ok), (
                f"File outside allowed scope: {f}"
            )
