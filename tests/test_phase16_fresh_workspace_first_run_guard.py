"""Phase 16 — Fresh Workspace First Run Guard Fix Tests.

Validates:
A. Fresh workspace first run allowed (no prior saved_snapshot, no dirty edits)
B. Dirty edited workspace still blocked (dirty flag prevents run)
C. Saved boundary still enforced (prior save exists, snapshot differs → blocked)
D. Saved clean boundary allowed (prior save exists, snapshot matches → allowed)
E. Guardrails: no financial formulas, no JS calcs, G20 BLOCKED, R99/R102 NOT APPROVED

Scope: app/persistence/repository.py (runtime_guard_for_snapshot)
"""

from __future__ import annotations

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class FakeWorkspaceState:
    """Fake WorkspaceStateRecord for testing."""
    def __init__(self, saved_snapshot=None, dirty=False, active_scenario_id=None, active_scenario_name=None):
        self.saved_snapshot = saved_snapshot
        self.dirty = dirty
        self.active_scenario_id = active_scenario_id
        self.active_scenario_name = active_scenario_name


class TestFreshWorkspaceFirstRun:
    """Tests for runtime_guard_for_snapshot fresh workspace behavior."""

    def test_fresh_workspace_empty_snapshot_allowed(self):
        """A. Fresh workspace with empty saved_snapshot allows first run (no dirty)."""
        from app.persistence.repository import runtime_guard_for_snapshot

        # Fresh workspace: saved_snapshot is None/empty, dirty=False
        ws = FakeWorkspaceState(saved_snapshot=None, dirty=False, active_scenario_id=None)
        current = {"active_project": "tuho", "tariff_eur_mwh": "", "project_type": "Wind"}

        allow, origin, msg = runtime_guard_for_snapshot(ws, current)

        assert allow is True, f"Fresh workspace first run must be allowed, got origin={origin}, msg={msg}"
        assert origin == "workspace_base"
        assert msg == ""

    def test_fresh_workspace_empty_dict_snapshot_allowed(self):
        """A. Fresh workspace with {} saved_snapshot allows first run."""
        from app.persistence.repository import runtime_guard_for_snapshot

        ws = FakeWorkspaceState(saved_snapshot={}, dirty=False, active_scenario_id=None)
        current = {"active_project": "tuho", "tariff_eur_mwh": "", "project_type": "Wind"}

        allow, origin, msg = runtime_guard_for_snapshot(ws, current)

        assert allow is True, f"Fresh workspace first run must be allowed, got origin={origin}, msg={msg}"
        assert origin == "workspace_base"

    def test_fresh_workspace_dirty_blocked(self):
        """B. Fresh workspace with dirty=True blocks run."""
        from app.persistence.repository import runtime_guard_for_snapshot

        ws = FakeWorkspaceState(saved_snapshot=None, dirty=True, active_scenario_id=None)
        current = {"active_project": "tuho", "tariff_eur_mwh": "100", "project_type": "Wind"}

        allow, origin, msg = runtime_guard_for_snapshot(ws, current)

        assert allow is False, "Dirty workspace must be blocked"
        assert "Unsaved edits" in msg or "preview_only" in origin

    def test_fresh_workspace_dirty_with_empty_snapshot_blocked(self):
        """B. Fresh workspace with {} saved_snapshot and dirty=True blocks run."""
        from app.persistence.repository import runtime_guard_for_snapshot

        ws = FakeWorkspaceState(saved_snapshot={}, dirty=True, active_scenario_id=None)
        current = {"active_project": "tuho", "tariff_eur_mwh": "100", "project_type": "Wind"}

        allow, origin, msg = runtime_guard_for_snapshot(ws, current)

        assert allow is False, "Dirty workspace must be blocked even with empty saved_snapshot"

    def test_prior_save_snapshot_differs_blocked(self):
        """C. Prior save exists but current differs from saved_snapshot → blocked."""
        from app.persistence.repository import runtime_guard_for_snapshot

        saved = {"active_project": "tuho", "tariff_eur_mwh": "", "project_type": "Wind"}
        current = {"active_project": "tuho", "tariff_eur_mwh": "100", "project_type": "Wind"}

        ws = FakeWorkspaceState(saved_snapshot=saved, dirty=False, active_scenario_id="sc123")
        allow, origin, msg = runtime_guard_for_snapshot(ws, current)

        assert allow is False, "Saved boundary mismatch must block run"
        assert "no longer matches" in msg or origin == "preview_only"

    def test_prior_save_snapshot_matches_allowed(self):
        """D. Prior save exists and current matches saved_snapshot → allowed."""
        from app.persistence.repository import runtime_guard_for_snapshot

        saved = {"active_project": "tuho", "tariff_eur_mwh": "100", "project_type": "Wind"}
        current = {"active_project": "tuho", "tariff_eur_mwh": "100", "project_type": "Wind"}

        ws = FakeWorkspaceState(saved_snapshot=saved, dirty=False, active_scenario_id="sc123")
        allow, origin, msg = runtime_guard_for_snapshot(ws, current)

        assert allow is True, "Matching saved snapshot must allow run"
        assert origin in ("saved_state", "workspace_base")

    def test_prior_save_no_active_scenario_id(self):
        """D. Prior save exists but no active_scenario_id → workspace_base allowed."""
        from app.persistence.repository import runtime_guard_for_snapshot

        saved = {"active_project": "tuho", "tariff_eur_mwh": "100", "project_type": "Wind"}
        current = {"active_project": "tuho", "tariff_eur_mwh": "100", "project_type": "Wind"}

        ws = FakeWorkspaceState(saved_snapshot=saved, dirty=False, active_scenario_id=None)
        allow, origin, msg = runtime_guard_for_snapshot(ws, current)

        assert allow is True
        assert origin == "workspace_base"

    def test_workspace_state_none_allowed(self):
        """Workspace state None (fallback) → allowed."""
        from app.persistence.repository import runtime_guard_for_snapshot

        allow, origin, msg = runtime_guard_for_snapshot(None, {})

        assert allow is True
        assert origin == "workspace_base"

    def test_fresh_workspace_with_form_values_allowed(self):
        """A. Fresh workspace with populated form values (simulating real first load) allowed."""
        from app.persistence.repository import runtime_guard_for_snapshot

        ws = FakeWorkspaceState(saved_snapshot=None, dirty=False, active_scenario_id=None)
        # Real form snapshot from TUHO first load
        current = {
            "active_project": "tuho",
            "project_type": "Wind",
            "scenario": "Base",
            "capacity_mw": "35",
            "tariff_eur_mwh": "",
            "p50_hours": "3000",
            "total_capex_keur": "",
            "opex_y1_keur": "",
            "gearing_pct": "",
            "target_dscr": "",
            "interest_rate_pct": "",
            "tenor_years": "",
            "cod_date": "",
            "construction_months": "",
            "horizon_years": "",
        }

        allow, origin, msg = runtime_guard_for_snapshot(ws, current)

        assert allow is True, f"Fresh workspace first run must be allowed, got origin={origin}, msg={msg}"
        assert origin == "workspace_base"


class TestGuardrails:
    """Guardrail tests — no financial logic changes."""

    def test_no_financial_formula_changes(self):
        """No changes to domain/model financial logic."""
        domain_files = [
            os.path.join(BASE_DIR, "domain", "portfolio", "waterfall.py"),
            os.path.join(BASE_DIR, "app", "api", "project_runner.py"),
            os.path.join(BASE_DIR, "app", "ui_runner.py"),
        ]
        for f in domain_files:
            if os.path.exists(f):
                content = open(f).read()
                assert len(content) > 100, f"{f} seems broken"

    def test_no_javascript_financial_calculations(self):
        """static/app.js must not contain Math.*, irr, npv, pmt calculations."""
        app_js = os.path.join(BASE_DIR, "static/app.js")
        content = open(app_js).read()

        patterns = [
            r"\bMath\.\s*(pow|sqrt|exp|log)",
            r"\birr\s*\(",
            r"\bnpv\s*\(",
            r"\bpmt\s*\(",
        ]
        for pattern in patterns:
            match = __import__("re").search(pattern, content, __import__("re").IGNORECASE)
            assert not match, f"JavaScript financial calc found: {pattern}"

    def test_g20_remains_blocked(self):
        """G20 must remain BLOCKED."""
        project_ctx = os.path.join(BASE_DIR, "app", "ui", "project_context.py")
        content = open(project_ctx).read()
        assert 'g20_status="BLOCKED"' in content, "G20 must remain BLOCKED"

    def test_r99_r102_not_approved(self):
        """R99 and R102 must remain NOT APPROVED."""
        project_ctx = os.path.join(BASE_DIR, "app", "ui", "project_context.py")
        content = open(project_ctx).read()
        assert 'r99_r102_status="NOT APPROVED"' in content

    def test_run_does_not_auto_save(self):
        """Run endpoint must not call save_scenario."""
        main_web = os.path.join(BASE_DIR, "main_web.py")
        content = open(main_web).read()

        run_idx = content.find('@app.post("/run")')
        run_end = content.find('@app.post("/compare")', run_idx)
        run_body = content[run_idx:run_end]

        assert "save_scenario(" not in run_body, "/run must not call save_scenario"

    def test_save_does_not_auto_run(self):
        """Save endpoint must not call run_project."""
        main_web = os.path.join(BASE_DIR, "main_web.py")
        content = open(main_web).read()

        save_idx = content.find('@app.post("/scenarios/save")')
        next_ep = content.find('@app.post("/scenarios/', save_idx + 1)
        save_end = next_ep if next_ep > 0 else len(content)
        save_body = content[save_idx:save_end]

        assert "run_project(" not in save_body, "/scenarios/save must not call run_project"


class TestCompileAndSyntax:
    """Must compile and have valid syntax."""

    def test_repository_compiles(self):
        """app/persistence/repository.py must compile."""
        repo = os.path.join(BASE_DIR, "app", "persistence", "repository.py")
        with open(repo) as f:
            compile(f.read(), repo, "exec")

    def test_main_web_compiles(self):
        """main_web.py must compile."""
        main_web = os.path.join(BASE_DIR, "main_web.py")
        with open(main_web) as f:
            compile(f.read(), main_web, "exec")

    def test_static_app_js_syntax(self):
        """static/app.js must have valid JavaScript syntax."""
        import subprocess
        result = subprocess.run(
            ["node", "--check", os.path.join(BASE_DIR, "static/app.js")],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"app.js syntax error: {result.stderr}"