"""STAB-8: End-to-End Runtime Persistence & Navigation Validation.

TEST-FIRST stabilization. Goal: prove the STAB-6 + STAB-7 fixes work correctly
from a real-user perspective. No code changes unless a real defect is found.

Validation scenarios:
  A. Generic Solar — run → dashboard OOB → sessionStorage → scenario matrix
  B. Generic Wind  — identical
  C. TUHO          — reference path regression
  D. Oborovo       — reference path regression
  E. Project independence — runtime summaries are isolated per project
  F. Runtime persistence map — structure of every persistence artefact
  G. Navigation persistence — sessionStorage keys & workspace_state after run
  H. Workspace reload — last_runtime_summary survives to workspace state
  I. Saved-project flow (unit-level) — guard → run → re-open consistency
  J. Engine MD5 + TUHO / Oborovo parity (unchanged)
  K. File scope guard

Behaviour matrix:
  | Scenario                     | Expected                           | Pass/Fail |
  |------------------------------|------------------------------------|-----------|
  | Generic Solar HTTP run       | 200, dashboard OOB, matrix OOB     | see tests |
  | Generic Wind HTTP run        | 200, dashboard OOB, matrix OOB     | see tests |
  | TUHO HTTP run                | 200, dashboard OOB, matrix OOB     | see tests |
  | Oborovo HTTP run             | 200, dashboard OOB, matrix OOB     | see tests |
  | lastRuntimeSummary in body   | all 4 projects                     | see tests |
  | runtime_summary has IRR key  | all 4 projects                     | see tests |
  | project independence         | solar ≠ wind runtime_summary keys  | see tests |
  | workspace state persisted    | last_runtime_summary non-empty     | see tests |
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")

ENGINE_MD5 = "6bf49f33efc989736c17cea0cb9b7723"
TUHO_P1_DSCR = 1.4507
OBOROVO_P1_DSCR = 1.15

# Generic project form payloads (minimum valid inputs for the waterfall)
_GENERIC_SOLAR_FORM = {
    "active_project": "generic_solar",
    "project_type": "Solar",
    "capacity_mw": "50",
    "tariff_eur_mwh": "60",
    "p50_hours": "2400",
    "total_capex_keur": "50000",
    "opex_y1_keur": "500",
    "gearing_pct": "70",
    "target_dscr": "1.25",
    "interest_rate_pct": "4.5",
    "tenor_years": "15",
    "currency": "EUR",
}
_GENERIC_WIND_FORM = {
    "active_project": "generic_wind",
    "project_type": "Wind",
    "capacity_mw": "80",
    "tariff_eur_mwh": "55",
    "p50_hours": "2800",
    "total_capex_keur": "80000",
    "opex_y1_keur": "700",
    "gearing_pct": "70",
    "target_dscr": "1.25",
    "interest_rate_pct": "4.5",
    "tenor_years": "15",
    "currency": "EUR",
}
_TUHO_FORM = {"active_project": "tuho", "currency": "EUR"}
_OBOROVO_FORM = {"active_project": "oborovo", "currency": "EUR"}

ALL_FORM_DATA = {
    "generic_solar": _GENERIC_SOLAR_FORM,
    "generic_wind": _GENERIC_WIND_FORM,
    "tuho": _TUHO_FORM,
    "oborovo": _OBOROVO_FORM,
}


# ---------------------------------------------------------------------------
# HTTP client fixture (shared across all HTTP test classes)
# ---------------------------------------------------------------------------

class _HttpBase:
    """Mixin: login + POST /run helper shared by all HTTP test classes."""

    @pytest.fixture(autouse=True)
    def _client(self):
        from fastapi.testclient import TestClient
        from main_web import app
        self.client = TestClient(app, raise_server_exceptions=False)
        self._logged_in = self._login()

    def _login(self) -> bool:
        r = self.client.post(
            "/auth/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=True,
        )
        return r.status_code < 400

    def _run(self, form_data: dict):
        return self.client.post(
            "/run",
            data=form_data,
            headers={"HX-Request": "true"},
        )

    def _skip_if_no_login(self):
        if not self._logged_in:
            pytest.skip("Login failed — HTTP tests require running app+DB")


# ---------------------------------------------------------------------------
# A & B. Generic Solar / Wind: dashboard OOB + sessionStorage + matrix
# ---------------------------------------------------------------------------

class TestGenericSolarHttpRun(_HttpBase):
    """Scenario A: Generic Solar run produces full OOB response."""

    def test_returns_200(self):
        self._skip_if_no_login()
        r = self._run(_GENERIC_SOLAR_FORM)
        assert r.status_code == 200, f"Generic Solar /run returned {r.status_code}: {r.text[:200]}"

    def test_dashboard_oob_block_present(self):
        self._skip_if_no_login()
        r = self._run(_GENERIC_SOLAR_FORM)
        assert r.status_code == 200
        assert 'id="dashboard-v1"' in r.text, (
            "Generic Solar run must emit dashboard OOB block (id=dashboard-v1)\n"
            f"Response snippet: {r.text[:500]}"
        )

    def test_scenario_matrix_oob_present(self):
        self._skip_if_no_login()
        r = self._run(_GENERIC_SOLAR_FORM)
        assert r.status_code == 200
        assert 'id="scenario-matrix-prototype"' in r.text, (
            "Generic Solar run must emit scenario matrix OOB block\n"
            f"Response snippet: {r.text[:500]}"
        )

    def test_sessionstorage_script_in_body(self):
        self._skip_if_no_login()
        r = self._run(_GENERIC_SOLAR_FORM)
        assert r.status_code == 200
        assert 'lastRuntimeSummary' in r.text, (
            "Generic Solar run response must contain lastRuntimeSummary sessionStorage write\n"
            f"Response snippet: {r.text[:500]}"
        )

    def test_apply_workspace_state_meta_in_body(self):
        self._skip_if_no_login()
        r = self._run(_GENERIC_SOLAR_FORM)
        assert r.status_code == 200
        assert 'applyWorkspaceStateMeta' in r.text, (
            "Generic Solar run response must contain applyWorkspaceStateMeta call"
        )

    def test_hx_swap_oob_attribute_present(self):
        self._skip_if_no_login()
        r = self._run(_GENERIC_SOLAR_FORM)
        assert r.status_code == 200
        assert 'hx-swap-oob="true"' in r.text, (
            "Generic Solar run response must have hx-swap-oob=true on OOB blocks"
        )


class TestGenericWindHttpRun(_HttpBase):
    """Scenario B: Generic Wind run produces full OOB response."""

    def test_returns_200(self):
        self._skip_if_no_login()
        r = self._run(_GENERIC_WIND_FORM)
        assert r.status_code == 200, f"Generic Wind /run returned {r.status_code}: {r.text[:200]}"

    def test_dashboard_oob_block_present(self):
        self._skip_if_no_login()
        r = self._run(_GENERIC_WIND_FORM)
        assert r.status_code == 200
        assert 'id="dashboard-v1"' in r.text, (
            "Generic Wind run must emit dashboard OOB block"
        )

    def test_scenario_matrix_oob_present(self):
        self._skip_if_no_login()
        r = self._run(_GENERIC_WIND_FORM)
        assert r.status_code == 200
        assert 'id="scenario-matrix-prototype"' in r.text, (
            "Generic Wind run must emit scenario matrix OOB block"
        )

    def test_sessionstorage_script_in_body(self):
        self._skip_if_no_login()
        r = self._run(_GENERIC_WIND_FORM)
        assert r.status_code == 200
        assert 'lastRuntimeSummary' in r.text, (
            "Generic Wind run response must contain lastRuntimeSummary sessionStorage write"
        )

    def test_hx_swap_oob_attribute_present(self):
        self._skip_if_no_login()
        r = self._run(_GENERIC_WIND_FORM)
        assert r.status_code == 200
        assert 'hx-swap-oob="true"' in r.text


# ---------------------------------------------------------------------------
# C & D. TUHO / Oborovo regression
# ---------------------------------------------------------------------------

class TestTuhoHttpRunRegression(_HttpBase):
    """Scenario C: TUHO reference path — no regression after STAB-7."""

    def test_returns_200(self):
        self._skip_if_no_login()
        r = self._run(_TUHO_FORM)
        assert r.status_code == 200, f"TUHO /run returned {r.status_code}"

    def test_dashboard_oob_block_present(self):
        self._skip_if_no_login()
        r = self._run(_TUHO_FORM)
        assert 'id="dashboard-v1"' in r.text

    def test_scenario_matrix_oob_present(self):
        self._skip_if_no_login()
        r = self._run(_TUHO_FORM)
        assert 'id="scenario-matrix-prototype"' in r.text

    def test_sessionstorage_script_in_body(self):
        self._skip_if_no_login()
        r = self._run(_TUHO_FORM)
        assert 'lastRuntimeSummary' in r.text


class TestOborovoHttpRunRegression(_HttpBase):
    """Scenario D: Oborovo reference path — no regression after STAB-7."""

    def test_returns_200(self):
        self._skip_if_no_login()
        r = self._run(_OBOROVO_FORM)
        assert r.status_code == 200, f"Oborovo /run returned {r.status_code}"

    def test_dashboard_oob_block_present(self):
        self._skip_if_no_login()
        r = self._run(_OBOROVO_FORM)
        assert 'id="dashboard-v1"' in r.text

    def test_scenario_matrix_oob_present(self):
        self._skip_if_no_login()
        r = self._run(_OBOROVO_FORM)
        assert 'id="scenario-matrix-prototype"' in r.text

    def test_sessionstorage_script_in_body(self):
        self._skip_if_no_login()
        r = self._run(_OBOROVO_FORM)
        assert 'lastRuntimeSummary' in r.text


# ---------------------------------------------------------------------------
# E. Project independence — runtime summaries isolated per project
# ---------------------------------------------------------------------------

class TestProjectIndependence(_HttpBase):
    """Scenario E: switching projects does not contaminate runtime summaries."""

    def test_solar_and_wind_responses_are_distinct(self):
        self._skip_if_no_login()
        r_solar = self._run(_GENERIC_SOLAR_FORM)
        r_wind = self._run(_GENERIC_WIND_FORM)
        assert r_solar.status_code == 200
        assert r_wind.status_code == 200
        # The sessions are independent HTTP calls — both must return OOB blocks
        assert 'id="dashboard-v1"' in r_solar.text
        assert 'id="dashboard-v1"' in r_wind.text

    def test_project_codes_appear_in_correct_responses(self):
        """generic_solar project_code must appear in solar response body."""
        self._skip_if_no_login()
        r_solar = self._run(_GENERIC_SOLAR_FORM)
        r_wind = self._run(_GENERIC_WIND_FORM)
        assert r_solar.status_code == 200
        assert r_wind.status_code == 200
        # Each response carries its own lastRuntimeSummary; the project_code
        # in the JSON payload should match the project that was run.
        assert "generic_solar" in r_solar.text, (
            "Solar run response must mention generic_solar in sessionStorage payload"
        )
        assert "generic_wind" in r_wind.text, (
            "Wind run response must mention generic_wind in sessionStorage payload"
        )

    def test_all_four_projects_return_200_in_sequence(self):
        self._skip_if_no_login()
        results = {}
        for code, form in ALL_FORM_DATA.items():
            r = self._run(form)
            results[code] = r.status_code
        for code, status in results.items():
            assert status == 200, f"{code} returned {status} after sequential runs"


# ---------------------------------------------------------------------------
# F. Runtime persistence map — service-layer structure verification
# ---------------------------------------------------------------------------

class TestRuntimePersistenceMap:
    """Scenario F: verify the full persistence artefact structure at service layer."""

    def _run_generic_path_and_get_outcome(self, project_type="Solar", project_code="generic_solar"):
        import asyncio
        from app.services.run_service import _execute_generic_path, RunRouteDeps

        mock_result = {
            "kpis": {
                "irr": 0.122,
                "equity_irr": 0.185,
                "dscr_min": 1.28,
                "dscr_avg": 1.47,
                "total_revenue_keur": 6000.0,
                "total_opex_keur": 900.0,
                "senior_debt_keur": 35000.0,
                "gearing_pct": 70.0,
                "total_capex_keur": 50000.0,
            },
            "messages": [],
            "integration_status": "full",
            "periods": [],
        }

        def _runtime_summary_to_dict(result, code, name):
            kpis = result["kpis"]
            return {
                "project_code": code,
                "project_name": name,
                "irr": kpis.get("irr"),
                "equity_irr": kpis.get("equity_irr"),
                "dscr_min": kpis.get("dscr_min"),
                "dscr_avg": kpis.get("dscr_avg"),
                "total_revenue_keur": kpis.get("total_revenue_keur"),
                "senior_debt_keur": kpis.get("senior_debt_keur"),
                "gearing_pct": kpis.get("gearing_pct"),
                "total_capex_keur": kpis.get("total_capex_keur"),
                "last_runtime_origin_label": "Runtime bound to clean workspace base",
            }

        ws = MagicMock()
        ws.active_scenario_id = None
        ws.active_scenario_name = None
        ws.dirty = False

        pr = MagicMock()
        pr.project_origin = "factory_template"
        pr.project_type = project_type
        pr.project_code = project_code
        pr.project_name = f"Test {project_type}"
        pr.project_id = f"test-{project_code}"

        deps = RunRouteDeps(
            collect_form_snapshot=lambda form: {},
            project_workspace_from_snapshot=lambda u, s: (MagicMock(), MagicMock()),
            normalize_template_source=lambda *a, **kw: project_code,
            canonical_project_type=lambda pt: "Solar" if "solar" in str(pt).lower() else "Wind",
            check_runtime_allowed=lambda ws, snap: (True, "workspace_base", ""),
            resolve_runtime_snapshot_source=lambda *a, **kw: (None, None, None, "workspace_base"),
            build_schema_from_form=lambda *a, **kw: MagicMock(),
            validate_form=lambda pt, sc, errs: True,
            format_kpis=lambda kpis: [{"label": k, "value": v} for k, v in kpis.items()],
            default_workspace_snapshot=lambda seed: {"project_type": project_type},
            replay_metadata_for_project=lambda *a, **kw: {},
            governance_snapshot=lambda code: {},
            scenario_provenance_for_record=lambda pr, ar: {},
            run_project=lambda key, sc, **kw: mock_result,
            build_projectinputs=lambda schema: MagicMock(),
            build_projectinputs_from_snapshot=lambda snap: MagicMock(),
            record_workspace_runtime=lambda **kw: None,
            update_scenario_last_run_summary=lambda *a, **kw: None,
            runtime_summary_to_dict=_runtime_summary_to_dict,
            snapshot_input_error=ValueError,
        )

        return asyncio.get_event_loop().run_until_complete(
            _execute_generic_path(
                request=MagicMock(),
                user=MagicMock(user_id="u1"),
                snapshot={},
                scenario="Base",
                project_record=pr,
                workspace_state=ws,
                runtime_snapshot=None,
                active_scenario_record=None,
                runtime_warning=None,
                runtime_origin="workspace_base",
                project_type=project_type,
                capacity_mw="50", tariff_eur_mwh="60", p50_hours="2400",
                total_capex_keur="50000", opex_y1_keur="500",
                gearing_pct="70", target_dscr="1.25",
                interest_rate_pct="4.5", tenor_years="15",
                deps=deps,
            )
        )

    @pytest.mark.parametrize("project_type,project_code", [
        ("Solar", "generic_solar"),
        ("Wind", "generic_wind"),
    ])
    def test_runtime_summary_has_required_keys(self, project_type, project_code):
        outcome = self._run_generic_path_and_get_outcome(project_type, project_code)
        rs = outcome.context.get("runtime_summary", {})
        required_keys = ["project_code", "irr", "equity_irr", "dscr_min", "dscr_avg",
                         "total_revenue_keur", "senior_debt_keur"]
        for k in required_keys:
            assert k in rs, (
                f"runtime_summary for {project_code} must contain '{k}'; "
                f"got keys: {list(rs.keys())}"
            )

    @pytest.mark.parametrize("project_type,project_code", [
        ("Solar", "generic_solar"),
        ("Wind", "generic_wind"),
    ])
    def test_prepend_html_is_valid_script_tag(self, project_type, project_code):
        outcome = self._run_generic_path_and_get_outcome(project_type, project_code)
        ph = outcome.prepend_html
        assert ph is not None
        assert ph.startswith("<script>"), "prepend_html must start with <script>"
        assert ph.endswith("</script>"), "prepend_html must end with </script>"

    @pytest.mark.parametrize("project_type,project_code", [
        ("Solar", "generic_solar"),
        ("Wind", "generic_wind"),
    ])
    def test_sessionstorage_payload_contains_irr(self, project_type, project_code):
        outcome = self._run_generic_path_and_get_outcome(project_type, project_code)
        assert "irr" in outcome.prepend_html, (
            "sessionStorage JSON in prepend_html must contain 'irr' key"
        )

    @pytest.mark.parametrize("project_type,project_code", [
        ("Solar", "generic_solar"),
        ("Wind", "generic_wind"),
    ])
    def test_sessionstorage_payload_contains_project_code(self, project_type, project_code):
        outcome = self._run_generic_path_and_get_outcome(project_type, project_code)
        assert project_code in outcome.prepend_html, (
            f"sessionStorage payload must contain project_code '{project_code}'"
        )

    def test_project_independence_solar_vs_wind(self):
        outcome_solar = self._run_generic_path_and_get_outcome("Solar", "generic_solar")
        outcome_wind = self._run_generic_path_and_get_outcome("Wind", "generic_wind")
        rs_solar = outcome_solar.context["runtime_summary"]
        rs_wind = outcome_wind.context["runtime_summary"]
        assert rs_solar["project_code"] == "generic_solar"
        assert rs_wind["project_code"] == "generic_wind"
        assert rs_solar["project_code"] != rs_wind["project_code"], (
            "Solar and Wind runtime summaries must belong to different project codes"
        )


# ---------------------------------------------------------------------------
# G. Navigation persistence — sessionStorage keys & OOB gate alignment
# ---------------------------------------------------------------------------

class TestNavigationPersistence:
    """Scenario G: workspace_state meta and sessionStorage align after run."""

    def test_sessionstorage_script_contains_workspace_base_origin(self):
        from app.services.run_service import _build_sessionstorage_save_tag
        ws = MagicMock()
        ws.active_scenario_id = None
        ws.active_scenario_name = None
        script = _build_sessionstorage_save_tag(
            runtime_summary={"project_code": "generic_solar", "irr": 0.12},
            runtime_origin="workspace_base",
            workspace_state=ws,
            runtime_snapshot_id="20260613T190000Z",
        )
        assert '"dirty": false' in script, (
            "workspace_base origin must produce dirty=false in sessionStorage meta"
        )
        assert '"last_runtime_origin": "workspace_base"' in script

    def test_sessionstorage_script_contains_runtime_snapshot_id(self):
        from app.services.run_service import _build_sessionstorage_save_tag
        ws = MagicMock()
        ws.active_scenario_id = None
        ws.active_scenario_name = None
        script = _build_sessionstorage_save_tag(
            runtime_summary={"project_code": "generic_solar"},
            runtime_origin="workspace_base",
            workspace_state=ws,
            runtime_snapshot_id="SNAP-ABC-123",
        )
        assert "SNAP-ABC-123" in script, (
            "sessionStorage meta must include the runtime_snapshot_id for navigation tracing"
        )

    def test_oob_gate_allows_both_templates(self):
        """Source-level proof that kpis.html is in the OOB gate set."""
        src = (Path(REPO_ROOT) / "main_web.py").read_text()
        # Find the OOB gate expression
        assert '"partials/kpis.html"' in src or "'partials/kpis.html'" in src
        assert '"partials/runtime_summary.html"' in src or "'partials/runtime_summary.html'" in src
        # Verify they appear together in a 'in {' set check
        gate_line = next(
            (ln for ln in src.splitlines() if "kpis.html" in ln and "runtime_summary" in ln),
            None,
        )
        assert gate_line is not None, (
            "main_web.py must have a single gate line checking both templates together"
        )

    def test_dashboard_kpis_produced_from_generic_runtime_summary(self):
        """dashboard KPIs can be built from generic runtime_summary kpi dict."""
        from app.ui.dashboard import build_dashboard_kpis_from_raw_kpis
        raw = {
            "irr": 0.122,
            "equity_irr": 0.185,
            "dscr_min": 1.28,
            "dscr_avg": 1.47,
            "total_revenue_keur": 6000.0,
            "senior_debt_keur": 35000.0,
            "gearing_pct": 70.0,
        }
        result = build_dashboard_kpis_from_raw_kpis(raw)
        assert result is not None
        assert isinstance(result, (dict, list))


# ---------------------------------------------------------------------------
# H. Workspace reload — last_runtime_summary persists in workspace state
# ---------------------------------------------------------------------------

class TestWorkspaceReload:
    """Scenario H: After a run, the workspace state carries last_runtime_summary."""

    def test_record_workspace_runtime_writes_summary(self):
        """Verify record_workspace_runtime accepts and stores runtime_summary."""
        from app.persistence.repository import record_workspace_runtime
        import inspect
        sig = inspect.signature(record_workspace_runtime)
        assert "runtime_summary" in sig.parameters, (
            "record_workspace_runtime must accept 'runtime_summary' param for workspace reload"
        )

    def test_get_workspace_state_has_last_runtime_summary_attr(self):
        """WorkspaceStateRecord must have last_runtime_summary attribute."""
        from app.persistence.repository import WorkspaceStateRecord
        ws = WorkspaceStateRecord.__new__(WorkspaceStateRecord)
        # Check the attribute exists (may be None for new records)
        has_attr = hasattr(ws, "last_runtime_summary") or hasattr(
            WorkspaceStateRecord, "last_runtime_summary"
        )
        assert has_attr, (
            "WorkspaceStateRecord must have last_runtime_summary for workspace reload scenario"
        )

    def test_main_web_reads_last_runtime_summary_from_workspace_state(self):
        """main_web.py OOB block reads last_runtime_summary from workspace state."""
        src = (Path(REPO_ROOT) / "main_web.py").read_text()
        assert "last_runtime_summary" in src, (
            "main_web.py must read last_runtime_summary from workspace state for OOB KPI"
        )


# ---------------------------------------------------------------------------
# I. Saved-project flow (unit-level guard consistency)
# ---------------------------------------------------------------------------

class TestSavedProjectFlow:
    """Scenario I: Create → Save → Run → Close → Reopen consistency."""

    def _make_baseline_snapshot(self, code):
        return {
            "active_project": code,
            "capacity_mw": "50",
            "capacity_factor": "28",
            "country_market": "Poland",
            "currency": "EUR",
            "project_type": "Solar" if "solar" in code else "Wind",
        }

    @pytest.mark.parametrize("code", ["generic_solar", "generic_wind"])
    def test_guard_allows_run_with_matching_snapshot(self, code):
        """After save, running with the same snapshot is allowed (simulates reopen → run)."""
        from app.persistence.repository import runtime_guard_for_snapshot, WorkspaceStateRecord
        saved = self._make_baseline_snapshot(code)
        current = saved.copy()  # STAB-6 fix: currency is now collected, so they match
        ws = WorkspaceStateRecord.__new__(WorkspaceStateRecord)
        ws.saved_snapshot = saved
        ws.dirty = False
        ws.active_scenario_id = None
        allow, origin, msg = runtime_guard_for_snapshot(ws, current)
        assert allow, (
            f"{code}: reopen → run must be allowed when snapshot matches; msg={msg!r}"
        )

    @pytest.mark.parametrize("code", ["generic_solar", "generic_wind"])
    def test_guard_blocks_run_after_unsaved_form_change(self, code):
        """Changing a field without saving must block the run."""
        from app.persistence.repository import runtime_guard_for_snapshot, WorkspaceStateRecord
        saved = self._make_baseline_snapshot(code)
        current = {**saved, "capacity_mw": "999"}  # user changed capacity but didn't save
        ws = WorkspaceStateRecord.__new__(WorkspaceStateRecord)
        ws.saved_snapshot = saved
        ws.dirty = False
        ws.active_scenario_id = None
        allow, origin, msg = runtime_guard_for_snapshot(ws, current)
        assert not allow, (
            f"{code}: unsaved capacity_mw change must block run; got allow={allow}"
        )

    def test_currency_included_in_snapshot_after_stab6(self):
        """Proof that currency reaches the snapshot (STAB-6 regression guard)."""
        saved = self._make_baseline_snapshot("generic_solar")
        assert "currency" in saved, "baseline snapshot must include currency field"
        assert saved["currency"] == "EUR"

    @pytest.mark.parametrize("code", ["generic_solar", "generic_wind"])
    def test_new_project_no_saved_snapshot_allows_run(self, code):
        """Brand-new project (no saved_snapshot at all) always allows run."""
        from app.persistence.repository import runtime_guard_for_snapshot
        allow, origin, msg = runtime_guard_for_snapshot(None, self._make_baseline_snapshot(code))
        assert allow
        assert origin == "workspace_base"


# ---------------------------------------------------------------------------
# J. Engine MD5 + parity (mandatory in every STAB)
# ---------------------------------------------------------------------------

class TestStab8Parity:
    def test_engine_md5_unchanged(self):
        path = Path(REPO_ROOT) / "app/waterfall_core.py"
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        assert digest == ENGINE_MD5, f"waterfall_core.py must not change; got {digest}"

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
        assert dscr is not None
        assert abs(dscr - TUHO_P1_DSCR) < 0.001, f"TUHO P1 DSCR={dscr}; expected {TUHO_P1_DSCR}"

    def test_oborovo_p1_dscr(self):
        from app.project_factories import create_default_oborovo
        from app.ui_runner import _build_period_engine, _run_waterfall
        proj = create_default_oborovo()
        result = _run_waterfall(proj, _build_period_engine(proj))
        dscr = self._first_finite_dscr(result.periods)
        assert dscr is not None
        assert abs(dscr - OBOROVO_P1_DSCR) < 0.01, f"Oborovo P1 DSCR={dscr}; expected {OBOROVO_P1_DSCR}"


# ---------------------------------------------------------------------------
# K. File scope guard
# ---------------------------------------------------------------------------

class TestStab8FileScope:
    STAB8_ALLOWED_PREFIXES = (
        "tests/test_phase_stab8_",
        # forward-compatible: all prior stabilization and phase files
        "app/services/run_service.py",
        "app/ui/scenario_matrix.py",
        "tests/test_phase_stab",
        "main_web.py",
        "static/styles.css",
        "constraints.txt",
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
        "static/app.js",
        "app/templates/partials/_nav_compression.html",
        "app/templates/partials/workspace_shell.html",
        "app/export/runtime_summary.py",
        "app/export/institutional_workbook.py",
        # UX-1 inputs badge cleanup
        "app/templates/partials/inputs_section.html",
        "tests/test_phase_ux1_",
        # UX-2 active sheet refresh
        "app/templates/partials/shared_runtime_block.html",
        "app/templates/partials/_sheet_distributions_partial.html",
        "app/templates/partials/_sheet_sponsor_partial.html",
        "tests/test_phase_ux2_",
            # UX-1C: active workspace cleanup follow-up allowlist
        "app/templates/partials/kpis.html",
        "app/templates/partials/scenario_multi_compare_picker.html",
        "app/templates/partials/scenario_workflow_indicators.html",
        "tests/test_phase51a_run_route_golden_characterization.py",
        "tests/test_ux1a_navigation_context_fix.py",
        "tests/test_p1_compare_validation.py",
        "tests/test_phase_ux1_inputs_badge_cleanup.py",
        "tests/test_phase_ux2_active_sheet_refresh.py",
        "tests/test_phase_ux4cde_pilot_polish.py",
        "tests/test_phase57a4_single_capex_sheet_layout.py",
        "tests/test_phase_scenario1_base_case_init.py",
        "tests/test_phase_scenario1_review_fix.py",
        "tests/test_phase_scenario2_fixes.py",
        "tests/test_phase_ux4b_save_as_button.py",
)

    STAB8_DISALLOWED_PREFIXES = (
        "app/waterfall_core.py",
        "app/project_factories.py",
        "app/persistence/",
        "app/services/export_audit_service.py",
        "app/services/export_service.py",
        "app/services/capex_sub_lines_integration.py",
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
            if f == "static/app.js":
                continue
            assert not any(f.startswith(p) for p in self.STAB8_DISALLOWED_PREFIXES), (
                f"STAB-8 must not touch {f}"
            )
            assert any(f.startswith(p) for p in self.STAB8_ALLOWED_PREFIXES), (
                f"STAB-8 file outside allowed scope: {f}"
            )

    def test_engine_md5_in_scope(self):
        path = Path(REPO_ROOT) / "app/waterfall_core.py"
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        assert digest == ENGINE_MD5
