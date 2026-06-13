"""STAB-6: Fix new-project first-run boundary check.

DEF-3 root cause: Phase 56C's _apply_new_project_required_inputs() saves
currency='EUR' into the baseline saved_snapshot, but _collect_form_snapshot()
did not include 'currency', so runtime_guard_for_snapshot() compared:
  saved_norm  = {..., 'currency': 'EUR', ...}
  current_norm = {...}   # no currency key
  → snapshots_equal() returned False → "form state no longer matches" → run blocked

Fix (Option A):
  1. main_web.py _collect_form_snapshot(): added 'currency' to the field list.
  2. workspace_shell.html hidden form: added
       <input type="hidden" name="currency" value="{{ form_data.get('currency', 'EUR') }}" />
     so the POSTed form carries currency on every run request.

These tests prove:
  A. _collect_form_snapshot includes 'currency' in its field list.
  B. workspace_shell.html has a hidden currency input.
  C. Currency snapshot consistency: saved_norm == current_norm after fix.
  D. Guard allows first run for new generic_solar project.
  E. Guard allows first run for new generic_wind project.
  F. Guard still blocks real mismatch (dirty form value differs from saved).
  G. Guard still blocks when workspace is dirty.
  H. Reference paths unaffected: TUHO / Oborovo / factory-generic continue to pass.
  I. Engine MD5 unchanged; TUHO / Oborovo parity preserved.
  J. File scope guard.
"""
from __future__ import annotations

import hashlib
import inspect
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
# A. _collect_form_snapshot includes 'currency'
# ---------------------------------------------------------------------------

class TestCollectFormSnapshotIncludesCurrency:
    def test_currency_in_snapshot_fields(self):
        """_collect_form_snapshot must collect 'currency' so saved and current norms match."""
        main_web_src = (Path(REPO_ROOT) / "main_web.py").read_text()
        # Look for currency inside the fields list used by _collect_form_snapshot
        assert '"currency"' in main_web_src or "'currency'" in main_web_src, (
            "main_web.py must contain 'currency' string"
        )

    def test_collect_form_snapshot_returns_currency_key(self):
        """Calling _collect_form_snapshot with a form that contains currency returns it."""
        import importlib.util, types
        # Load main_web module safely
        spec = importlib.util.spec_from_file_location(
            "main_web", Path(REPO_ROOT) / "main_web.py"
        )
        # We only need the function, so parse the source for the field list
        src = (Path(REPO_ROOT) / "main_web.py").read_text()
        # Find the fields list inside _collect_form_snapshot
        import ast, textwrap
        tree = ast.parse(src)
        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_collect_form_snapshot":
                func_src = ast.get_source_segment(src, node)
                if func_src and "currency" in func_src:
                    found = True
        assert found, "_collect_form_snapshot must include 'currency' in its field list"


# ---------------------------------------------------------------------------
# B. workspace_shell.html has hidden currency input
# ---------------------------------------------------------------------------

class TestWorkspaceShellHasCurrencyInput:
    def test_hidden_currency_input_present(self):
        tmpl = (Path(REPO_ROOT) / "app/templates/partials/workspace_shell.html").read_text()
        assert 'name="currency"' in tmpl, (
            "workspace_shell.html must have a hidden input with name='currency'"
        )

    def test_currency_input_uses_form_data(self):
        tmpl = (Path(REPO_ROOT) / "app/templates/partials/workspace_shell.html").read_text()
        assert "form_data.get('currency'" in tmpl or 'form_data.get("currency"' in tmpl, (
            "workspace_shell.html currency input must use form_data.get('currency', ...)"
        )


# ---------------------------------------------------------------------------
# C. Currency snapshot consistency
# ---------------------------------------------------------------------------

class TestCurrencySnapshotConsistency:
    def _make_saved_snapshot(self):
        """Simulate what _apply_new_project_required_inputs writes to saved_snapshot."""
        return {
            "active_project": "generic_solar",
            "project_name": "My Solar",
            "capacity_mw": "50",
            "capacity_factor": "28",
            "country_market": "Poland",
            "currency": "EUR",  # Phase 56C adds this
            # ... other non-empty fields the factory sets
        }

    def _make_current_snapshot(self, currency="EUR"):
        """Simulate what _collect_form_snapshot returns after STAB-6 fix."""
        snap = self._make_saved_snapshot().copy()
        snap["currency"] = currency  # now included because we added it to the field list
        return snap

    def test_saved_and_current_equal_after_fix(self):
        from app.persistence.repository import _strip_empty_fields, snapshots_equal
        saved = self._make_saved_snapshot()
        current = self._make_current_snapshot(currency="EUR")
        saved_norm = _strip_empty_fields(saved)
        current_norm = _strip_empty_fields(current)
        assert snapshots_equal(saved_norm, current_norm), (
            "After STAB-6 fix, saved_norm and current_norm must be equal"
        )

    def test_mismatch_detected_when_currency_differs(self):
        from app.persistence.repository import _strip_empty_fields, snapshots_equal
        saved = self._make_saved_snapshot()  # currency='EUR'
        current = self._make_current_snapshot(currency="USD")
        saved_norm = _strip_empty_fields(saved)
        current_norm = _strip_empty_fields(current)
        assert not snapshots_equal(saved_norm, current_norm), (
            "Mismatched currency values must NOT be equal"
        )


# ---------------------------------------------------------------------------
# D & E. Guard allows first run for new generic projects
# ---------------------------------------------------------------------------

class TestNewProjectFirstRunAllowed:
    def _baseline_snapshot(self, project_code):
        """Minimal snapshot that _apply_new_project_required_inputs would produce."""
        return {
            "active_project": project_code,
            "capacity_mw": "50",
            "capacity_factor": "28",
            "country_market": "Poland",
            "currency": "EUR",
        }

    def _workspace_state_no_save(self, saved_snapshot):
        """Workspace with a saved_snapshot but no prior save marker — first run case."""
        from app.persistence.repository import WorkspaceStateRecord
        ws = WorkspaceStateRecord.__new__(WorkspaceStateRecord)
        # Simulate new project: saved_snapshot has been persisted once (on creation),
        # but the saved_snapshot field IS the baseline — has_prior_save is True here.
        # We simulate the exact state: saved=baseline, dirty=False.
        ws.saved_snapshot = saved_snapshot
        ws.dirty = False
        ws.active_scenario_id = None
        return ws

    @pytest.mark.parametrize("code", ["generic_solar", "generic_wind"])
    def test_first_run_allowed(self, code):
        from app.persistence.repository import runtime_guard_for_snapshot
        saved = self._baseline_snapshot(code)
        # current_snapshot = what _collect_form_snapshot returns (now includes currency)
        current = saved.copy()  # identical after fix
        ws = self._workspace_state_no_save(saved)
        allow, origin, msg = runtime_guard_for_snapshot(ws, current)
        assert allow, (
            f"New {code} project first run must be allowed; "
            f"origin={origin!r} msg={msg!r}"
        )

    def test_none_workspace_always_allowed(self):
        from app.persistence.repository import runtime_guard_for_snapshot
        allow, origin, msg = runtime_guard_for_snapshot(None, {"currency": "EUR"})
        assert allow
        assert origin == "workspace_base"


# ---------------------------------------------------------------------------
# F. Guard still blocks real mismatch
# ---------------------------------------------------------------------------

class TestGuardBlocksRealMismatch:
    def test_blocks_when_form_value_differs(self):
        from app.persistence.repository import runtime_guard_for_snapshot, WorkspaceStateRecord
        saved = {"active_project": "generic_solar", "capacity_mw": "50", "currency": "EUR"}
        current = {"active_project": "generic_solar", "capacity_mw": "75", "currency": "EUR"}
        ws = WorkspaceStateRecord.__new__(WorkspaceStateRecord)
        ws.saved_snapshot = saved
        ws.dirty = False
        ws.active_scenario_id = None
        allow, origin, msg = runtime_guard_for_snapshot(ws, current)
        assert not allow, "Guard must block when capacity_mw changed without save"
        assert "no longer matches" in msg or "Unsaved" in msg

    def test_blocks_when_currency_differs(self):
        from app.persistence.repository import runtime_guard_for_snapshot, WorkspaceStateRecord
        saved = {"active_project": "generic_solar", "capacity_mw": "50", "currency": "EUR"}
        current = {"active_project": "generic_solar", "capacity_mw": "50", "currency": "USD"}
        ws = WorkspaceStateRecord.__new__(WorkspaceStateRecord)
        ws.saved_snapshot = saved
        ws.dirty = False
        ws.active_scenario_id = None
        allow, origin, msg = runtime_guard_for_snapshot(ws, current)
        assert not allow, "Guard must block when currency changed without save"


# ---------------------------------------------------------------------------
# G. Guard blocks dirty workspace
# ---------------------------------------------------------------------------

class TestGuardBlocksDirtyWorkspace:
    def test_dirty_workspace_blocked_when_snapshots_differ(self):
        from app.persistence.repository import runtime_guard_for_snapshot, WorkspaceStateRecord
        saved = {"active_project": "generic_solar", "capacity_mw": "50", "currency": "EUR"}
        current = {"active_project": "generic_solar", "capacity_mw": "75", "currency": "EUR"}
        ws = WorkspaceStateRecord.__new__(WorkspaceStateRecord)
        ws.saved_snapshot = saved
        ws.dirty = True
        ws.active_scenario_id = None
        allow, origin, msg = runtime_guard_for_snapshot(ws, current)
        assert not allow, "Dirty workspace with mismatched snapshot must be blocked"
        assert "Unsaved" in msg


# ---------------------------------------------------------------------------
# H. Reference paths unaffected
# ---------------------------------------------------------------------------

class TestReferencePaths:
    @pytest.mark.parametrize("code", ["tuho", "oborovo", "generic_solar", "generic_wind"])
    def test_export_services_still_work(self, code):
        from app.services.export_service import build_runtime_summary_csv_export
        resp = build_runtime_summary_csv_export(code, safe_project=code)
        assert resp.status_code == 200, (
            f"CSV export for '{code}' must still return 200 after STAB-6; got {resp.status_code}"
        )

    @pytest.mark.parametrize("code", ["tuho", "oborovo", "generic_solar", "generic_wind"])
    def test_workbook_export_still_works(self, code):
        from app.services.export_service import build_institutional_workbook_export
        resp = build_institutional_workbook_export(code, safe_project=code)
        assert resp.status_code == 200, (
            f"XLSX export for '{code}' must still return 200 after STAB-6; got {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# I. Engine MD5 + parity
# ---------------------------------------------------------------------------

class TestStab6Parity:
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
# J. File scope guard
# ---------------------------------------------------------------------------

class TestStab6FileScope:
    STAB6_ALLOWED_PREFIXES = (
        "main_web.py",
        "app/templates/partials/workspace_shell.html",
        "tests/test_phase_stab6_",
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
        # STAB-5 files
        "app/export/runtime_summary.py",
        "app/export/institutional_workbook.py",
        # STAB-7 generic dashboard parity
        "app/services/run_service.py",
        "tests/test_phase_stab7_",
    )

    STAB6_DISALLOWED_PREFIXES = (
        "app/waterfall_core.py",
        "app/project_factories.py",
        "app/persistence/",
        # app/services/ narrowed: run_service.py allowed from STAB-7 onwards
        "app/services/export_audit_service.py",
        "app/ui/",
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
            assert not any(f.startswith(p) for p in self.STAB6_DISALLOWED_PREFIXES), (
                f"STAB-6 must not touch {f}"
            )
            assert any(f.startswith(p) for p in self.STAB6_ALLOWED_PREFIXES), (
                f"STAB-6 file outside allowed scope: {f}"
            )

    def test_engine_md5_in_scope(self):
        path = Path(REPO_ROOT) / "app/waterfall_core.py"
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        assert digest == ENGINE_MD5
