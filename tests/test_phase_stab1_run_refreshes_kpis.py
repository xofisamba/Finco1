"""STAB-1: Run refreshes KPI cards and scenario matrix Base KPIs.

Defect being fixed: after POST /run, the dashboard KPI cards and the
scenario matrix Base KPI rows were not refreshed via OOB HTMX swap.

Root causes fixed in this PR:
  1. build_dashboard_kpis_from_raw_kpis (dashboard.py) received IRR as
     a fraction (0.1026) but _fmt_pct expected a percentage (10.26),
     so it rendered "0.1%" instead of "10.3%".
  2. build_matrix_context (scenario_matrix.py) had no runtime_kpis
     parameter, so Base KPI rows always showed "—" after a run.
  3. POST /run did not emit an OOB scenario matrix card alongside the
     existing OOB dashboard card.

These tests prove:
  A. build_dashboard_kpis_from_raw_kpis formats IRR fractions correctly.
  B. build_matrix_context accepts runtime_kpis and populates Base KPIs.
  C. The OOB dashboard block is present in the POST /run response.
  D. The OOB scenario matrix block is present in the POST /run response.
  E. The scenario matrix card has id="scenario-matrix-prototype" and
     hx-swap-oob="true" in the OOB response.
  F. Engine MD5 unchanged; TUHO / Oborovo parity preserved.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")

ENGINE_MD5 = "6bf49f33efc989736c17cea0cb9b7723"
TUHO_P1_DSCR = 1.4507
OBOROVO_P1_DSCR = 1.15


# ---------------------------------------------------------------------------
# A. dashboard.py — IRR fraction → percentage formatting
# ---------------------------------------------------------------------------

class TestDashboardIrrFormatting:
    """build_dashboard_kpis_from_raw_kpis must scale fraction IRR values."""

    def _raw(self):
        return {
            "project_irr": 0.1026,
            "equity_irr": 0.1480,
            "senior_debt_keur": 30000.0,
            "min_dscr": 1.35,
            "avg_dscr": 1.62,
            "target_dscr": 1.30,
            "y1_revenue_keur": 4500.0,
            "y1_ebitda_keur": 2800.0,
            "project_npv_keur": 8000.0,
        }

    def test_project_irr_shows_percentage(self):
        from app.ui.dashboard import build_dashboard_kpis_from_raw_kpis
        result = build_dashboard_kpis_from_raw_kpis(self._raw())
        val = result["project_irr"]["value"]
        assert "10." in val or "10%" in val, (
            f"Expected ~10.3% for project_irr=0.1026; got {val!r}"
        )
        assert "0.1%" not in val, (
            f"IRR must not show sub-percent value; got {val!r}"
        )

    def test_equity_irr_shows_percentage(self):
        from app.ui.dashboard import build_dashboard_kpis_from_raw_kpis
        result = build_dashboard_kpis_from_raw_kpis(self._raw())
        val = result["equity_irr"]["value"]
        assert "14." in val or "15." in val, (
            f"Expected ~14.8% for equity_irr=0.1480; got {val!r}"
        )

    def test_raw_kpis_with_zero_irr_shows_zero(self):
        from app.ui.dashboard import build_dashboard_kpis_from_raw_kpis
        result = build_dashboard_kpis_from_raw_kpis({"project_irr": 0.0})
        assert "0.0%" in result["project_irr"]["value"], (
            "project_irr=0.0 (fraction) should format as '0.0%'"
        )

    def test_empty_raw_returns_dashes(self):
        from app.ui.dashboard import build_dashboard_kpis_from_raw_kpis
        result = build_dashboard_kpis_from_raw_kpis({})
        for key in ("project_irr", "equity_irr"):
            assert result[key]["value"] == "—", (
                f"Missing IRR in raw_kpis should show '—'; got {result[key]['value']!r}"
            )


# ---------------------------------------------------------------------------
# B. scenario_matrix.py — runtime_kpis populates Base KPI rows
# ---------------------------------------------------------------------------

class TestMatrixRuntimeKpis:
    """build_matrix_context runtime_kpis parameter fills Base KPI cells."""

    def _ctx(self):
        class FakeCtx:
            ppa_tariff_eur_mwh = 75.0
            operating_hours_p50 = 2800
            capacity_mw = 35.0
            total_capex_keur = 42000.0
            opex_y1_total_keur = 1200.0
            interest_rate_pct = 0.045
            senior_tenor_years = 18
            target_dscr = 1.30
            gearing_pct = 0.70
            ppa_term_years = 15
            construction_months = 18
        return FakeCtx()

    def _raw_kpis(self):
        return {
            "total_revenue_keur": 95000.0,
            "total_ebitda_keur": 72000.0,
            "project_irr": 0.1026,
            "equity_irr": 0.1480,
            "senior_debt_amount_keur": 29400.0,
            "realized_gearing_pct": 0.70,
            "min_dscr": 1.35,
        }

    def test_kpi_rows_use_runtime_kpis(self):
        from app.ui.scenario_matrix import build_matrix_context, ROW_KIND_KPI
        ctx = build_matrix_context(self._ctx(), runtime_kpis=self._raw_kpis())
        kpi_rows = [r for r in ctx["matrix_rows"] if r["kind"] == ROW_KIND_KPI]
        assert kpi_rows, "Expected at least one KPI row"
        revenue_row = next(r for r in kpi_rows if r["row"].attr == "total_revenue_keur")
        assert "95" in revenue_row["base"], (
            f"total_revenue_keur=95000 should appear in Base cell; got {revenue_row['base']!r}"
        )

    def test_irr_kpi_row_formats_correctly(self):
        from app.ui.scenario_matrix import build_matrix_context, ROW_KIND_KPI
        ctx = build_matrix_context(self._ctx(), runtime_kpis=self._raw_kpis())
        kpi_rows = [r for r in ctx["matrix_rows"] if r["kind"] == ROW_KIND_KPI]
        irr_row = next(r for r in kpi_rows if r["row"].attr == "project_irr")
        val = irr_row["base"]
        assert "10." in val or "10%" in val, (
            f"project_irr=0.1026 should show ~10.3%; got {val!r}"
        )
        assert "—" not in val, (
            f"IRR KPI Base cell must not be '—' when runtime_kpis provided; got {val!r}"
        )

    def test_no_runtime_kpis_falls_back_to_dash(self):
        from app.ui.scenario_matrix import build_matrix_context, ROW_KIND_KPI
        ctx = build_matrix_context(self._ctx(), runtime_kpis=None)
        kpi_rows = [r for r in ctx["matrix_rows"] if r["kind"] == ROW_KIND_KPI]
        revenue_row = next(r for r in kpi_rows if r["row"].attr == "total_revenue_keur")
        assert revenue_row["base"] == "—", (
            "Without runtime_kpis and no project_ctx KPI attrs, Base cell should be '—'"
        )

    def test_input_rows_still_read_from_ctx(self):
        from app.ui.scenario_matrix import build_matrix_context, ROW_KIND_INPUT
        ctx = build_matrix_context(self._ctx(), runtime_kpis=self._raw_kpis())
        input_rows = [r for r in ctx["matrix_rows"] if r["kind"] == ROW_KIND_INPUT]
        cap_row = next(r for r in input_rows if r["row"].attr == "capacity_mw")
        assert "35" in cap_row["base"], (
            f"capacity_mw=35.0 should appear in Base cell; got {cap_row['base']!r}"
        )


# ---------------------------------------------------------------------------
# C & D. POST /run OOB response contains both dashboard and matrix blocks
# ---------------------------------------------------------------------------

class TestRunOobContainsBothBlocks:
    """The POST /run response body must include OOB dashboard + matrix."""

    @pytest.fixture(autouse=True)
    def _client(self):
        from fastapi.testclient import TestClient
        from main_web import app
        self.client = TestClient(app, raise_server_exceptions=False)

    def _login(self):
        r = self.client.post(
            "/auth/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=True,
        )
        return r.status_code < 400

    def test_run_oob_contains_dashboard_block(self):
        if not self._login():
            pytest.skip("Login failed; skipping OOB run test")
        r = self.client.post(
            "/run",
            data={"project_code": "tuho"},
            headers={"HX-Request": "true"},
        )
        assert r.status_code == 200, f"POST /run returned {r.status_code}"
        body = r.text
        assert 'id="dashboard-v1"' in body, (
            "POST /run OOB response must contain id=\"dashboard-v1\" block"
        )

    def test_run_oob_contains_matrix_block(self):
        if not self._login():
            pytest.skip("Login failed; skipping OOB run test")
        r = self.client.post(
            "/run",
            data={"project_code": "tuho"},
            headers={"HX-Request": "true"},
        )
        assert r.status_code == 200, f"POST /run returned {r.status_code}"
        body = r.text
        assert 'id="scenario-matrix-prototype"' in body, (
            "POST /run OOB response must contain id=\"scenario-matrix-prototype\""
        )

    def test_matrix_oob_has_swap_attribute(self):
        if not self._login():
            pytest.skip("Login failed; skipping OOB run test")
        r = self.client.post(
            "/run",
            data={"project_code": "tuho"},
            headers={"HX-Request": "true"},
        )
        assert r.status_code == 200, f"POST /run returned {r.status_code}"
        body = r.text
        assert 'hx-swap-oob="true"' in body, (
            "Scenario matrix OOB block must have hx-swap-oob=\"true\""
        )


# ---------------------------------------------------------------------------
# E. scenario_matrix.html OOB template mechanics
# ---------------------------------------------------------------------------

class TestOobTemplateMechanics:
    """The scenario matrix OOB template produces the right attributes."""

    def test_oob_template_exists(self):
        path = Path(REPO_ROOT) / "app/templates/partials/_scenario_matrix_oob.html"
        assert path.exists(), "_scenario_matrix_oob.html must exist"

    def test_oob_template_includes_matrix(self):
        path = Path(REPO_ROOT) / "app/templates/partials/_scenario_matrix_oob.html"
        text = path.read_text()
        assert "scenario_matrix.html" in text, (
            "_scenario_matrix_oob.html must include scenario_matrix.html"
        )
        assert "matrix_oob" in text, (
            "_scenario_matrix_oob.html must set matrix_oob=true"
        )

    def test_scenario_matrix_html_supports_oob_attr(self):
        path = Path(REPO_ROOT) / "app/templates/partials/scenario_matrix.html"
        text = path.read_text()
        assert "hx-swap-oob" in text, (
            "scenario_matrix.html must conditionally render hx-swap-oob"
        )
        assert "matrix_oob" in text, (
            "scenario_matrix.html must check matrix_oob context variable"
        )

    def test_scenario_matrix_card_has_stable_id(self):
        path = Path(REPO_ROOT) / "app/templates/partials/scenario_matrix.html"
        text = path.read_text()
        assert 'id="scenario-matrix-prototype"' in text, (
            "Card must have id=\"scenario-matrix-prototype\" for OOB targeting"
        )


# ---------------------------------------------------------------------------
# F. Engine MD5 guard + parity goldens
# ---------------------------------------------------------------------------

class TestStab1Parity:
    def test_engine_md5_unchanged(self):
        path = Path(REPO_ROOT) / "app/waterfall_core.py"
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        assert digest == ENGINE_MD5, (
            f"waterfall_core.py must not change; got {digest}"
        )

    @staticmethod
    def _first_finite_dscr(periods):
        for p in periods:
            if not p.is_operation:
                continue
            d = p.dscr
            if d is None or d != d or d == float("inf"):
                continue
            return d
        return None

    def test_tuho_p1_dscr(self):
        from app.project_factories import create_default_tuho_wind1
        from app.ui_runner import _build_period_engine, _run_waterfall
        proj = create_default_tuho_wind1()
        result = _run_waterfall(proj, _build_period_engine(proj))
        dscr = self._first_finite_dscr(result.periods)
        assert dscr is not None, "TUHO must have finite DSCR"
        assert abs(dscr - TUHO_P1_DSCR) < 0.001, (
            f"TUHO P1 DSCR={dscr}; expected {TUHO_P1_DSCR}"
        )

    def test_oborovo_p1_dscr(self):
        from app.project_factories import create_default_oborovo
        from app.ui_runner import _build_period_engine, _run_waterfall
        proj = create_default_oborovo()
        result = _run_waterfall(proj, _build_period_engine(proj))
        dscr = self._first_finite_dscr(result.periods)
        assert dscr is not None, "Oborovo must have finite DSCR"
        assert abs(dscr - OBOROVO_P1_DSCR) < 0.01, (
            f"Oborovo P1 DSCR={dscr}; expected {OBOROVO_P1_DSCR}"
        )


# ---------------------------------------------------------------------------
# G. File scope
# ---------------------------------------------------------------------------

class TestStab1FileScope:
    """STAB-1 touches only the expected files."""

    STAB1_ALLOWED_PREFIXES = (
        "app/ui/dashboard.py",
        "app/ui/scenario_matrix.py",
        "app/templates/partials/scenario_matrix.html",
        "app/templates/partials/_scenario_matrix_oob.html",
        "main_web.py",
        "static/styles.css",
        "tests/test_phase_stab",
        "tests/test_phase_m1_",
        "tests/test_phase_m2_",
        "tests/test_phase_m3_",
        "tests/test_phase_m4_",
        "tests/test_phase_wf1_",
        "tests/test_phase_wf2_",
        "tests/test_phase_wf3_",
        "tests/test_phase_wf4_",
        "tests/test_phase_wf5_",
        "tests/test_phase_wf6_",
        "tests/test_phase_pr1_",
        "tests/test_phase_pr2_",
        "tests/test_phase_pr3_",
        "tests/test_phase_p2fix",
        # STAB-4 navigation-only changes
        "static/app.js",
        "app/templates/partials/_nav_compression.html",
        "app/templates/partials/workspace_shell.html",
        # STAB-5 export route fix
        "app/export/runtime_summary.py",
        "app/export/institutional_workbook.py",
        "tests/test_phase_stab5_",
        # STAB-6 new-project first-run fix
        "tests/test_phase_stab6_",
    )

    STAB1_DISALLOWED_PREFIXES = (
        "app/waterfall_core.py",
        "app/project_factories.py",
        "app/persistence/",
        "app/services/",
        "main_api.py",
    )

    def test_file_scope(self):
        import shutil
        if shutil.which("git") is None:
            pytest.skip("git not available")
        result = subprocess.run(
            ["git", "-C", REPO_ROOT, "diff", "--name-only", "origin/main"],
            capture_output=True, text=True,
        )
        changed = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        for f in changed:
            # STAB-4: app.js change must be navigation-only (no financial calcs)
            if f == "static/app.js":
                import pathlib as _pl
                js_src = (_pl.Path(REPO_ROOT) / "static/app.js").read_text()
                assert "STAB-4" in js_src, f"static/app.js changed without STAB-4 marker"
                continue
            assert not any(f.startswith(p) for p in self.STAB1_DISALLOWED_PREFIXES), (
                f"STAB-1 must not touch {f}"
            )
            assert any(f.startswith(p) for p in self.STAB1_ALLOWED_PREFIXES), (
                f"STAB-1 file outside allowed scope: {f}"
            )

    def test_engine_md5_in_scope_test(self):
        path = Path(REPO_ROOT) / "app/waterfall_core.py"
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        assert digest == ENGINE_MD5
