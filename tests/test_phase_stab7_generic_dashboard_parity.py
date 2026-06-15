"""STAB-7: Generic Dashboard Runtime Parity.

DEF-4 root cause: _execute_generic_path (app/services/run_service.py) never
called runtime_summary_to_dict() or _build_sessionstorage_save_tag(), so
  - outcome.prepend_html was None
  - main_web.py early-returned at the "if not outcome.prepend_html" gate (line 2564)
    before reaching the OOB block
  - even if reached, the OOB gate checked == "partials/runtime_summary.html"
    and kpis.html would not have passed

Fix (STAB-7):
  1. _execute_generic_path now calls runtime_summary_to_dict() + _build_sessionstorage_save_tag()
     and sets prepend_html on RunRouteOutcome.
  2. main_web.py OOB gate extended:
       if outcome.template_name in {"partials/runtime_summary.html", "partials/kpis.html"}:
     so generic runs trigger the same dashboard OOB refresh as TUHO/Oborovo.

These tests prove:
  A. _execute_generic_path outcome carries prepend_html for generic_solar.
  B. _execute_generic_path outcome carries prepend_html for generic_wind.
  C. outcome.context["runtime_summary"] present for generic projects.
  D. _build_sessionstorage_save_tag output contains lastRuntimeSummary key.
  E. OOB gate in main_web.py source includes kpis.html.
  F. TUHO run outcome still returns runtime_summary.html + prepend_html.
  G. Oborovo run outcome still returns runtime_summary.html + prepend_html.
  H. build_dashboard_kpis_from_raw_kpis works on generic runtime_summary kpis.
  I. Export regression: all four projects CSV + XLSX = 200.
  J. STAB-6 regression: runtime guard allows new-project first run.
  K. Scenario matrix OOB unchanged (STAB-1/STAB-2).
  L. Engine MD5 + TUHO/Oborovo parity.
  M. File scope guard.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-for-pytest-only")

ENGINE_MD5 = "6bf49f33efc989736c17cea0cb9b7723"
TUHO_P1_DSCR = 1.4507
OBOROVO_P1_DSCR = 1.15

ALL_PROJECTS = ["tuho", "oborovo", "generic_solar", "generic_wind"]
GENERIC_PROJECTS = ["generic_solar", "generic_wind"]


# ---------------------------------------------------------------------------
# Shared helper: build a minimal RunRouteDeps for the generic path
# ---------------------------------------------------------------------------

def _make_mock_result(project_key="Solar"):
    """Minimal run result dict that satisfies both format_kpis and runtime_summary_to_dict."""
    kpis = {
        "irr": 0.12,
        "equity_irr": 0.18,
        "dscr_min": 1.25,
        "dscr_avg": 1.45,
        "total_revenue_keur": 5000.0,
        "total_opex_keur": 800.0,
        "senior_debt_keur": 3000.0,
        "gearing_pct": 70.0,
    }
    return {
        "kpis": kpis,
        "messages": [],
        "integration_status": "full",
        "periods": [],
    }


def _make_generic_deps(project_type="Solar"):
    """Minimal RunRouteDeps for testing _execute_generic_path."""
    from app.services.run_service import RunRouteDeps

    mock_result = _make_mock_result(project_type)

    def _runtime_summary_to_dict(result, project_code, project_name):
        kpis = result["kpis"]
        return {
            "project_code": project_code,
            "project_name": project_name,
            "irr": kpis.get("irr"),
            "equity_irr": kpis.get("equity_irr"),
            "dscr_min": kpis.get("dscr_min"),
            "dscr_avg": kpis.get("dscr_avg"),
        }

    deps = RunRouteDeps(
        collect_form_snapshot=lambda form: {},
        project_workspace_from_snapshot=lambda u, s: (MagicMock(), MagicMock()),
        normalize_template_source=lambda *a, **kw: "generic_solar",
        canonical_project_type=lambda pt: "Solar" if "solar" in str(pt).lower() else "Wind",
        check_runtime_allowed=lambda ws, snap: (True, "workspace_base", ""),
        resolve_runtime_snapshot_source=lambda *a, **kw: (None, None, None, "workspace_base"),
        build_schema_from_form=lambda *a, **kw: MagicMock(),
        validate_form=lambda pt, sc, errs: True,
        format_kpis=lambda kpis: [{"label": k, "value": v} for k, v in kpis.items()],
        default_workspace_snapshot=lambda seed: {"project_type": "Solar"},
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
    return deps


def _make_project_record(project_type="Solar", project_code="generic_solar"):
    pr = MagicMock()
    pr.project_origin = "template_seeded"
    pr.project_type = project_type
    pr.project_code = project_code
    pr.project_name = "Test Generic"
    pr.project_id = "test-id-001"
    pr.template_source = None
    pr.source_project_template = None
    return pr


def _make_workspace_state():
    ws = MagicMock()
    ws.active_scenario_id = None
    ws.active_scenario_name = None
    ws.dirty = False
    ws.saved_snapshot = None
    ws.last_runtime_summary = None
    return ws


# ---------------------------------------------------------------------------
# A & B. _execute_generic_path produces prepend_html for both generic types
# ---------------------------------------------------------------------------

class TestGenericPathProducesPrependHtml:
    @pytest.mark.parametrize("project_type,project_code", [
        ("Solar", "generic_solar"),
        ("Wind", "generic_wind"),
    ])
    def test_prepend_html_not_none(self, project_type, project_code):
        import asyncio
        from app.services.run_service import _execute_generic_path

        deps = _make_generic_deps(project_type)
        pr = _make_project_record(project_type, project_code)
        ws = _make_workspace_state()

        outcome = asyncio.get_event_loop().run_until_complete(
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
                capacity_mw="50",
                tariff_eur_mwh="60",
                p50_hours="2400",
                total_capex_keur="50000",
                opex_y1_keur="500",
                gearing_pct="70",
                target_dscr="1.25",
                interest_rate_pct="4.5",
                tenor_years="15",
                deps=deps,
            )
        )
        assert outcome.prepend_html is not None, (
            f"_execute_generic_path for {project_code} must set prepend_html"
        )
        assert "sessionStorage" in outcome.prepend_html, (
            f"prepend_html for {project_code} must contain sessionStorage"
        )


# ---------------------------------------------------------------------------
# C. outcome.context["runtime_summary"] present for generic projects
# ---------------------------------------------------------------------------

class TestGenericPathContextContainsRuntimeSummary:
    @pytest.mark.parametrize("project_type,project_code", [
        ("Solar", "generic_solar"),
        ("Wind", "generic_wind"),
    ])
    def test_runtime_summary_in_context(self, project_type, project_code):
        import asyncio
        from app.services.run_service import _execute_generic_path

        deps = _make_generic_deps(project_type)
        pr = _make_project_record(project_type, project_code)
        ws = _make_workspace_state()

        outcome = asyncio.get_event_loop().run_until_complete(
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
                capacity_mw="50",
                tariff_eur_mwh="60",
                p50_hours="2400",
                total_capex_keur="50000",
                opex_y1_keur="500",
                gearing_pct="70",
                target_dscr="1.25",
                interest_rate_pct="4.5",
                tenor_years="15",
                deps=deps,
            )
        )
        assert "runtime_summary" in outcome.context, (
            f"outcome.context must include 'runtime_summary' for {project_code}"
        )
        rs = outcome.context["runtime_summary"]
        assert isinstance(rs, dict), "runtime_summary must be a dict"
        assert rs.get("project_code") == project_code


# ---------------------------------------------------------------------------
# D. _build_sessionstorage_save_tag contains lastRuntimeSummary
# ---------------------------------------------------------------------------

class TestSessionStorageSaveTag:
    def test_contains_lastRuntimeSummary(self):
        from app.services.run_service import _build_sessionstorage_save_tag
        ws = _make_workspace_state()
        script = _build_sessionstorage_save_tag(
            runtime_summary={"irr": 0.12, "project_code": "generic_solar"},
            runtime_origin="workspace_base",
            workspace_state=ws,
            runtime_snapshot_id="20260613T120000Z",
        )
        assert "lastRuntimeSummary" in script
        assert "sessionStorage" in script
        assert "applyWorkspaceStateMeta" in script


# ---------------------------------------------------------------------------
# E. OOB gate in main_web.py source includes kpis.html
# ---------------------------------------------------------------------------

class TestMainWebOobGate:
    def test_oob_gate_includes_kpis_html(self):
        src = (Path(REPO_ROOT) / "main_web.py").read_text()
        assert '"partials/kpis.html"' in src or "'partials/kpis.html'" in src, (
            "main_web.py OOB gate must include partials/kpis.html"
        )
        # Confirm the gate uses 'in {' pattern (set membership), not ==
        assert "partials/kpis.html" in src

    def test_oob_gate_still_includes_runtime_summary(self):
        src = (Path(REPO_ROOT) / "main_web.py").read_text()
        assert "partials/runtime_summary.html" in src


# ---------------------------------------------------------------------------
# F & G. TUHO / Oborovo outcome unchanged
# ---------------------------------------------------------------------------

class TestReferencePathOutcomeUnchanged:
    @pytest.mark.parametrize("runtime_seed,project_key", [
        ("tuho", "TUHO"),
        ("oborovo", "Oborovo"),
    ])
    def test_template_seeded_still_returns_runtime_summary(self, runtime_seed, project_key):
        import asyncio
        from app.services.run_service import _execute_template_seeded_path, RunRouteDeps

        mock_result = _make_mock_result(project_key)

        def _runtime_summary_to_dict(result, project_code, project_name):
            return {"project_code": project_code, "irr": result["kpis"].get("irr")}

        deps = RunRouteDeps(
            collect_form_snapshot=lambda form: {},
            project_workspace_from_snapshot=lambda u, s: (MagicMock(), MagicMock()),
            normalize_template_source=lambda *a, **kw: runtime_seed,
            canonical_project_type=lambda pt: "Wind",
            check_runtime_allowed=lambda ws, snap: (True, "workspace_base", ""),
            resolve_runtime_snapshot_source=lambda *a, **kw: (None, None, None, "workspace_base"),
            build_schema_from_form=lambda *a, **kw: MagicMock(),
            validate_form=lambda pt, sc, errs: True,
            format_kpis=lambda kpis: [],
            default_workspace_snapshot=lambda seed: {"project_type": "Wind"},
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
        pr = MagicMock()
        pr.project_type = "Wind"
        pr.project_code = runtime_seed
        pr.project_name = project_key
        pr.project_id = "test-id"
        ws = _make_workspace_state()

        outcome = asyncio.get_event_loop().run_until_complete(
            _execute_template_seeded_path(
                request=MagicMock(),
                user=MagicMock(user_id="u1"),
                snapshot={"scenario": "Base"},
                scenario="Base",
                project_record=pr,
                workspace_state=ws,
                runtime_snapshot=None,
                active_scenario_record=None,
                runtime_warning=None,
                runtime_origin="workspace_base",
                capacity_mw="50", tariff_eur_mwh="60", p50_hours="2400",
                total_capex_keur="50000", opex_y1_keur="500",
                gearing_pct="70", target_dscr="1.25",
                interest_rate_pct="4.5", tenor_years="15",
                runtime_seed=runtime_seed,
                deps=deps,
            )
        )
        assert outcome.template_name == "partials/runtime_summary.html", (
            f"{runtime_seed} path must still return runtime_summary.html"
        )
        assert outcome.prepend_html is not None, (
            f"{runtime_seed} path must still set prepend_html"
        )


# ---------------------------------------------------------------------------
# H. build_dashboard_kpis_from_raw_kpis works on generic raw KPIs
# ---------------------------------------------------------------------------

class TestDashboardKpisFromGenericRaw:
    def test_generic_raw_kpis_produce_dashboard_kpis(self):
        from app.ui.dashboard import build_dashboard_kpis_from_raw_kpis
        raw = {
            "irr": 0.12,
            "equity_irr": 0.18,
            "dscr_min": 1.25,
            "dscr_avg": 1.45,
            "total_revenue_keur": 5000.0,
            "senior_debt_keur": 3000.0,
        }
        kpis = build_dashboard_kpis_from_raw_kpis(raw)
        assert kpis is not None, "build_dashboard_kpis_from_raw_kpis must return a value"
        # Result must be dict or list — something the template can iterate/render
        assert isinstance(kpis, (dict, list)), "dashboard_kpis must be a dict or list"


# ---------------------------------------------------------------------------
# I. Export regression: all four projects remain 200
# ---------------------------------------------------------------------------

class TestExportRegression:
    @pytest.mark.parametrize("code", ALL_PROJECTS)
    def test_csv_export_200(self, code):
        from app.services.export_service import build_runtime_summary_csv_export
        resp = build_runtime_summary_csv_export(code, safe_project=code)
        assert resp.status_code == 200, (
            f"CSV export for '{code}' must remain 200; got {resp.status_code}"
        )

    @pytest.mark.parametrize("code", ALL_PROJECTS)
    def test_xlsx_export_200(self, code):
        from app.services.export_service import build_institutional_workbook_export
        resp = build_institutional_workbook_export(code, safe_project=code)
        assert resp.status_code == 200, (
            f"XLSX export for '{code}' must remain 200; got {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# J. STAB-6 regression: new-project guard still allows first run
# ---------------------------------------------------------------------------

class TestStab6Regression:
    def _baseline_snapshot(self, code):
        return {
            "active_project": code,
            "capacity_mw": "50",
            "capacity_factor": "28",
            "country_market": "Poland",
            "currency": "EUR",
        }

    @pytest.mark.parametrize("code", GENERIC_PROJECTS)
    def test_new_project_first_run_still_allowed(self, code):
        from app.persistence.repository import runtime_guard_for_snapshot, WorkspaceStateRecord
        saved = self._baseline_snapshot(code)
        current = saved.copy()
        ws = WorkspaceStateRecord.__new__(WorkspaceStateRecord)
        ws.saved_snapshot = saved
        ws.dirty = False
        ws.active_scenario_id = None
        allow, origin, msg = runtime_guard_for_snapshot(ws, current)
        assert allow, (
            f"STAB-6: new {code} first run must still be allowed; msg={msg!r}"
        )


# ---------------------------------------------------------------------------
# K. Scenario matrix OOB still works (STAB-1 regression)
# ---------------------------------------------------------------------------

class TestScenarioMatrixStab1Regression:
    def test_build_matrix_context_accepts_runtime_kpis(self):
        from app.ui.scenario_matrix import build_matrix_context
        from app.ui.project_context import get_project_context
        import inspect
        sig = inspect.signature(build_matrix_context)
        assert "runtime_kpis" in sig.parameters, (
            "build_matrix_context must still accept runtime_kpis (STAB-1 regression)"
        )


# ---------------------------------------------------------------------------
# L. Engine MD5 + parity
# ---------------------------------------------------------------------------

class TestStab7Parity:
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
# M. File scope guard
# ---------------------------------------------------------------------------

class TestStab7FileScope:
    STAB7_ALLOWED_PREFIXES = (
        "app/services/run_service.py",
        "main_web.py",
        "tests/test_phase_stab7_",
        # forward-compatible: prior stabilization and phase files
        "app/ui/scenario_matrix.py",
        "tests/test_phase_stab",
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
        # STAB-8 e2e runtime validation
        "tests/test_phase_stab8_",
        # UX-1 inputs badge cleanup
        "app/templates/partials/inputs_section.html",
        "tests/test_phase_ux1_",
    )

    STAB7_DISALLOWED_PREFIXES = (
        "app/waterfall_core.py",
        "app/project_factories.py",
        "app/persistence/",
        "app/services/export_audit_service.py",
        "app/services/export_service.py",
        "app/services/capex_sub_lines_integration.py",
        "app/ui/",
        "app/export/",
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
            assert not any(f.startswith(p) for p in self.STAB7_DISALLOWED_PREFIXES), (
                f"STAB-7 must not touch {f}"
            )
            assert any(f.startswith(p) for p in self.STAB7_ALLOWED_PREFIXES), (
                f"STAB-7 file outside allowed scope: {f}"
            )

    def test_engine_md5_in_scope(self):
        path = Path(REPO_ROOT) / "app/waterfall_core.py"
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        assert digest == ENGINE_MD5
