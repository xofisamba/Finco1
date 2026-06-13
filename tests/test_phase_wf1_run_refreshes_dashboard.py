"""Phase WF-1 — Run refreshes dashboard KPI grid.

Acceptance criteria:
1. POST /run returns HTML that contains the OOB dashboard element
   (#dashboard-v1 with hx-swap-oob="true") so HTMX updates the
   KPI grid in-place without a full page reload.
2. The sidebar Run button (#btn-run-model-sidebar) has HTMX wiring
   (hx-post=/run, hx-include=#main-form, hx-target=#model-output-area).
3. KPI card labels are present in the OOB block (Project IRR, Equity
   IRR, Min DSCR, Avg DSCR, Senior Debt, Y1 Revenue, Y1 EBITDA).
4. Before any run the dashboard shows the "No run yet" CTA.
5. The OOB section has id="dashboard-v1" and hx-swap-oob="true".
6. Parity: engine MD5 unchanged; TUHO / Oborovo goldens preserved.
7. build_dashboard_kpis_from_raw_kpis covers all required KPI keys.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-key-wf1")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_session_token  # noqa: E402
from main_web import app  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
ENGINE_MD5 = "6bf49f33efc989736c17cea0cb9b7723"
SEED_USER = "wf1_seed_user"
RUN_USER = "wf1_run_user"


@pytest.fixture(scope="module")
def client():
    """Client for workspace/UI tests (has workspace state after seed visit)."""
    c = TestClient(app, follow_redirects=False)
    token = create_session_token(user_id=SEED_USER, username="wf1_seed_user")
    c.cookies.set("finco_session", token)
    # Seed factory templates by visiting workspace
    c.get("/?project=tuho", follow_redirects=True)
    return c


@pytest.fixture(scope="module")
def run_client():
    """Client for POST /run tests with a baseline-matched form snapshot.

    The guard requires form data to match the saved workspace snapshot.
    We POST the full baseline snapshot so the guard passes.
    """
    c = TestClient(app, follow_redirects=False)
    token = create_session_token(user_id=RUN_USER, username="wf1_run_user")
    c.cookies.set("finco_session", token)
    return c


@pytest.fixture(scope="module")
def tuho_baseline():
    """Return TUHO baseline form data that passes the runtime guard."""
    from main_web import _default_workspace_snapshot
    return _default_workspace_snapshot("tuho")


# ---------------------------------------------------------------------------
# 1. Engine MD5 guard
# ---------------------------------------------------------------------------

class TestEngineParity:
    def test_engine_md5_unchanged(self):
        engine = REPO_ROOT / "app" / "waterfall_core.py"
        md5 = hashlib.md5(engine.read_bytes()).hexdigest()
        assert md5 == ENGINE_MD5, (
            f"waterfall_core.py MD5 changed: expected {ENGINE_MD5}, got {md5}"
        )


# ---------------------------------------------------------------------------
# 2. Sidebar Run button has HTMX wiring
# ---------------------------------------------------------------------------

class TestSidebarRunButtonWiring:
    def test_run_button_has_hx_post(self, client):
        r = client.get("/?project=tuho", follow_redirects=True)
        assert r.status_code == 200
        assert 'id="btn-run-model-sidebar"' in r.text
        assert 'hx-post="/run"' in r.text

    def test_run_button_includes_main_form(self, client):
        r = client.get("/?project=tuho", follow_redirects=True)
        assert 'hx-include="#main-form"' in r.text

    def test_run_button_targets_model_output_area(self, client):
        r = client.get("/?project=tuho", follow_redirects=True)
        assert 'hx-target="#model-output-area"' in r.text

    def test_main_form_exists_with_active_project(self, client):
        r = client.get("/?project=tuho", follow_redirects=True)
        assert 'id="main-form"' in r.text
        assert 'name="active_project"' in r.text


# ---------------------------------------------------------------------------
# 3. Dashboard empty state before first run
# ---------------------------------------------------------------------------

class TestDashboardEmptyState:
    def test_dashboard_section_present(self, client):
        r = client.get("/?project=tuho", follow_redirects=True)
        assert 'id="dashboard-v1"' in r.text

    def test_kpi_grid_present(self, client):
        r = client.get("/?project=tuho", follow_redirects=True)
        assert 'dashboard-kpi-grid' in r.text


# ---------------------------------------------------------------------------
# 4. POST /run returns OOB dashboard block
# ---------------------------------------------------------------------------

class TestRunReturnsOOBDashboard:
    """Submit full baseline snapshot so the runtime guard passes."""

    def test_run_response_contains_oob_dashboard(self, run_client, tuho_baseline):
        r = run_client.post("/run", data=tuho_baseline, follow_redirects=False)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"
        assert 'hx-swap-oob="true"' in r.text, (
            "POST /run must return hx-swap-oob block to update dashboard in-place"
        )

    def test_run_response_oob_has_dashboard_id(self, run_client, tuho_baseline):
        r = run_client.post("/run", data=tuho_baseline, follow_redirects=False)
        assert r.status_code == 200
        assert 'id="dashboard-v1"' in r.text

    def test_run_response_contains_kpi_grid(self, run_client, tuho_baseline):
        r = run_client.post("/run", data=tuho_baseline, follow_redirects=False)
        assert r.status_code == 200
        assert "dashboard-kpi-grid" in r.text

    def test_run_response_kpi_labels_present(self, run_client, tuho_baseline):
        r = run_client.post("/run", data=tuho_baseline, follow_redirects=False)
        assert r.status_code == 200
        for label in ("Project IRR", "Equity IRR", "Min DSCR", "Avg DSCR", "Senior Debt"):
            assert label in r.text, f"KPI label '{label}' missing from run response"

    def test_run_response_kpi_values_not_all_dashes(self, run_client, tuho_baseline):
        """After a successful run the KPI values should not all be '—'."""
        r = run_client.post("/run", data=tuho_baseline, follow_redirects=False)
        assert r.status_code == 200
        import re
        kpi_values = re.findall(
            r'data-p2min3-kpi-status="[^"]*"[^>]*>\s*([^<]+?)\s*<',
            r.text,
        )
        non_dash = [v for v in kpi_values if v.strip() and v.strip() != "—"]
        assert non_dash, (
            f"All KPI values are '—' after a successful run — "
            f"OOB dashboard build failed. Values: {kpi_values}"
        )


# ---------------------------------------------------------------------------
# 5. build_dashboard_kpis_from_raw_kpis unit test
# ---------------------------------------------------------------------------

class TestBuildDashboardKpisFromRawKpis:
    def _raw(self):
        return {
            "project_irr": 0.085,
            "equity_irr": 0.123,
            "senior_debt_keur": 50000.0,
            "min_dscr": 1.12,
            "avg_dscr": 1.45,
            "target_dscr": 1.1,
            "y1_revenue_keur": 5000.0,
            "y1_ebitda_keur": 3000.0,
            "project_npv_keur": 10000.0,
        }

    def test_returns_dict(self):
        from app.ui.dashboard import build_dashboard_kpis_from_raw_kpis
        result = build_dashboard_kpis_from_raw_kpis(self._raw())
        assert isinstance(result, dict)

    def test_all_required_keys_present(self):
        from app.ui.dashboard import build_dashboard_kpis_from_raw_kpis
        result = build_dashboard_kpis_from_raw_kpis(self._raw())
        for key in ("project_irr", "equity_irr", "senior_debt", "min_dscr",
                    "avg_dscr", "y1_revenue", "y1_ebitda"):
            assert key in result, f"Missing KPI key: {key}"

    def test_project_irr_formatted(self):
        from app.ui.dashboard import build_dashboard_kpis_from_raw_kpis
        result = build_dashboard_kpis_from_raw_kpis(self._raw())
        assert "8.5%" in result["project_irr"]["value"]

    def test_min_dscr_formatted(self):
        from app.ui.dashboard import build_dashboard_kpis_from_raw_kpis
        result = build_dashboard_kpis_from_raw_kpis(self._raw())
        assert "1.12" in result["min_dscr"]["value"]

    def test_empty_raw_returns_dashes(self):
        from app.ui.dashboard import build_dashboard_kpis_from_raw_kpis
        result = build_dashboard_kpis_from_raw_kpis({})
        for key, kpi in result.items():
            assert kpi["value"] == "—", (
                f"Empty raw_kpis should give '—' for {key}, got {kpi['value']!r}"
            )


# ---------------------------------------------------------------------------
# 6. OOB template structural checks
# ---------------------------------------------------------------------------

class TestOOBTemplate:
    def test_oob_template_exists(self):
        tmpl = REPO_ROOT / "app" / "templates" / "partials" / "_dashboard_oob.html"
        assert tmpl.exists()

    def test_oob_template_has_hx_swap_oob(self):
        content = (REPO_ROOT / "app" / "templates" / "partials" / "_dashboard_oob.html").read_text()
        assert 'hx-swap-oob="true"' in content

    def test_oob_template_has_dashboard_id(self):
        content = (REPO_ROOT / "app" / "templates" / "partials" / "_dashboard_oob.html").read_text()
        assert 'id="dashboard-v1"' in content
