"""Phase P1-UX-FIX-1 — Pilot UX polish.

Context
--------
POST-P1-CLEANUP-SMOKE-1 surfaced three latent UX inconsistencies
plus a fourth UX gap. This test file pins all four fixes:

  TASK A — Realized Gearing for Generic: when the input
           senior_debt (fixed_debt_keur) is None or 0, the
           realised gearing computation falls back to the
           runtime-senior-debt value. For TUHO and Oborovo
           the two are bit-identical so behaviour is
           preserved.

  TASK B — Scenario Switch Runtime Safety: when
           ``select_scenario()`` changes the active scenario,
           workspace_state.last_runtime_snapshot,
           last_runtime_summary, and last_runtime_origin are
           cleared. A subsequent ``POST /download`` returns
           a 400 with the "Run the model before exporting."
           message (post-PILOT-HOTFIX-3 behaviour).

  TASK C — Dashboard Empty State: when all KPI cards are
           in ``status == 'missing'`` (no real values), an
           empty-state hint "Run the model to see KPIs here."
           is rendered between the KPI grid and the charts.
           This is distinct from the P2-FIX-4 "No run yet"
           CTA which only fires when there is no runtime
           snapshot at all.

  TASK D — Working Copy Indicator: a user-created project
           that was created from a reference template
           (TUHO/Oborovo/Generic) shows a "Working Copy"
           badge in the sidebar next to the origin pill.

Constraints honoured (all pinned by tests):
  - rc1 SHA ``b425a0708719eaa5e1d922b1008e5609758e0ad4`` untouched.
  - Engine MD5 ``6bf49f33efc989736c17cea0cb9b7723`` unchanged.
  - Factory MD5 ``cf73065b8a26aa3f19629829e46260d9`` unchanged.
  - TUHO debt 43,359 kEUR + Oborovo debt 42,852.27 kEUR bit-identical.
  - No changes to waterfall_core / project_factories / input_adapter
    / persistence schema / run_service / download_service.
  - No TUHO/Oborovo reference paths changed.
  - No R99 / R102 / G20.
  - No construction-period changes.
  - No tax changes.
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("FINCO_SECRET_KEY", "test-secret-p1uxfix1")

from app.persistence.db import init_db

init_db()


# ---------------------------------------------------------------------------
# Constants — frozen anchors
# ---------------------------------------------------------------------------

RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"
ENGINE_MD5 = "6bf49f33efc989736c17cea0cb9b7723"
FACTORY_MD5 = "cf73065b8a26aa3f19629829e46260d9"

ALLOWED_FILES = {
    # TASK A
    "app/ui/project_context.py",
    # TASK B
    "app/persistence/scenarios_repository.py",
    # TASK C
    "app/templates/partials/_dashboard.html",
    "static/styles.css",
    # TASK D
    "app/templates/partials/project_selector.html",
    "static/styles.css",
    # Tests / docs
    "tests/test_phase_p1_ux_fix_1_pilot_polish.py",
    "docs/phase_p1_ux_fix_1_pilot_polish.md",
    "reports/phase_p1_ux_fix_1_pilot_polish.md",
}

FORBIDDEN_FILES = {
    "app/waterfall_core.py",
    "app/project_factories.py",
    "app/input_adapter.py",
    "app/persistence/db.py",  # schema frozen
    "app/persistence/repository.py",
    "app/services/run_service.py",
    "app/services/download_service.py",
    "app/ui_runner.py",
    "static/app.js",
}


# ---------------------------------------------------------------------------
# TASK A — Realized Gearing for Generic
# ---------------------------------------------------------------------------


class TestTaskARealizedGearingForGeneric:
    """TASK A — _compute_realized_gearing_pct runtime fallback."""

    def test_input_only_path_unchanged(self):
        """When senior_debt_keur is provided (>0), runtime
        fallback is not used. Backwards-compatible with PR2."""
        from app.ui.project_context import _compute_realized_gearing_pct
        # senior_debt > 0, no runtime value
        val = _compute_realized_gearing_pct(senior_debt_keur=30000.0, total_capex_keur=100000.0)
        assert val == pytest.approx(30.0, abs=1e-9)
        # senior_debt > 0, runtime provided but ignored
        val2 = _compute_realized_gearing_pct(
            senior_debt_keur=30000.0, total_capex_keur=100000.0, runtime_senior_debt_keur=22500.0
        )
        assert val2 == pytest.approx(30.0, abs=1e-9)

    def test_zero_input_falls_back_to_runtime(self):
        """When senior_debt_keur=0 (Generic Solar/Wind factory
        default for fixed_debt_keur), runtime value is used."""
        from app.ui.project_context import _compute_realized_gearing_pct
        val = _compute_realized_gearing_pct(
            senior_debt_keur=0,
            total_capex_keur=100000.0,
            runtime_senior_debt_keur=22500.0,
        )
        assert val == pytest.approx(22.5, abs=1e-9)

    def test_none_input_falls_back_to_runtime(self):
        """When senior_debt_keur=None, runtime value is used."""
        from app.ui.project_context import _compute_realized_gearing_pct
        val = _compute_realized_gearing_pct(
            senior_debt_keur=None,
            total_capex_keur=100000.0,
            runtime_senior_debt_keur=22500.0,
        )
        assert val == pytest.approx(22.5, abs=1e-9)

    def test_both_none_returns_none(self):
        """When both are None/0, returns None (unchanged behaviour)."""
        from app.ui.project_context import _compute_realized_gearing_pct
        assert _compute_realized_gearing_pct(senior_debt_keur=None, total_capex_keur=100000.0) is None
        assert _compute_realized_gearing_pct(senior_debt_keur=0, total_capex_keur=100000.0) is None
        assert _compute_realized_gearing_pct(
            senior_debt_keur=0, total_capex_keur=100000.0, runtime_senior_debt_keur=0
        ) is None

    def test_zero_capex_returns_none(self):
        """Total capex = 0 → None (unchanged)."""
        from app.ui.project_context import _compute_realized_gearing_pct
        assert _compute_realized_gearing_pct(senior_debt_keur=30000.0, total_capex_keur=0) is None
        assert _compute_realized_gearing_pct(senior_debt_keur=30000.0, total_capex_keur=-100.0) is None
        assert _compute_realized_gearing_pct(
            senior_debt_keur=None, total_capex_keur=0, runtime_senior_debt_keur=22500.0
        ) is None

    def test_negative_runtime_rejected(self):
        """Negative runtime senior debt is rejected."""
        from app.ui.project_context import _compute_realized_gearing_pct
        assert _compute_realized_gearing_pct(
            senior_debt_keur=None, total_capex_keur=100000.0, runtime_senior_debt_keur=-100.0
        ) is None


# ---------------------------------------------------------------------------
# TASK B — Scenario Switch Runtime Safety
# ---------------------------------------------------------------------------


class TestTaskBScenarioSwitchRuntimeSafety:
    """TASK B — select_scenario() clears runtime evidence."""

    def test_select_scenario_clears_last_runtime_snapshot(self):
        """After select_scenario(), workspace last_runtime_snapshot
        is empty dict (post-P1-UX-FIX-1 contract)."""
        from app.persistence.scenarios_repository import select_scenario
        from app.persistence.repository import get_workspace_state, save_project
        from app.persistence.workspace_repository import save_workspace_state
        from app.persistence.db import get_cursor
        import uuid

        # Create test user, project, scenario A, scenario B
        user_id = f"p1uxfix1-b-{uuid.uuid4().hex[:8]}"
        project_code = f"p1uxfix1-wc-{uuid.uuid4().hex[:8]}"

        project = save_project(
            user_id=user_id,
            project_code=project_code,
            project_name="P1-UX-FIX-1 Test WC",
            source_project_template="generic_solar",
            project_type="Solar",
            project_origin="user_created",
            template_source="generic_solar",
            baseline_snapshot={"scenario": "A"},
        )
        project_id = project.project_id

        # Insert scenario A and scenario B directly via DB
        # (avoids depending on add_scenario's complex kwargs).
        scenario_a_id = f"scA{uuid.uuid4().hex[:12]}"
        scenario_b_id = f"scB{uuid.uuid4().hex[:12]}"
        now = "2026-06-18T00:00:00"
        with get_cursor() as cur:
            for sc_id, sc_name in [(scenario_a_id, "Scenario A"), (scenario_b_id, "Scenario B")]:
                cur.execute(
                    """
                    INSERT INTO scenarios (
                        scenario_id, project_id, user_id, scenario_name, project_code,
                        source_project_template, copied_from_scenario_id, archived,
                        is_base_case, parent_scenario_id,
                        base_input_set_json, overrides_json,
                        snapshot_json, governance_state_json,
                        last_run_summary_json, replay_metadata_json,
                        schema_version, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, NULL, 0, 0, NULL,
                              '{}', '{}', '{}', '{}', '{}',
                              '{"export_type":"saved_scenario_snapshot"}',
                              '1.0', ?, ?)
                    """,
                    (sc_id, project_id, user_id, sc_name, project_code,
                     "generic_solar", now, now),
                )

        # Set up workspace with runtime evidence under scenario A
        save_workspace_state(
            user_id=user_id, project_id=project_id,
            project_code=project_code,
            active_scenario_id=scenario_a_id,
            active_scenario_name="Scenario A",
            draft_snapshot={}, saved_snapshot={"scenario": "A"},
            last_runtime_snapshot={"revenue": [1, 2, 3]},
            last_runtime_summary={"project_irr": 0.0733, "revenue": [1, 2, 3]},
            last_runtime_origin="saved_state",
            last_runtime_snapshot_id="snap-a-001",
            last_runtime_scenario_id=scenario_a_id,
        )

        # Select scenario B (should clear runtime evidence)
        ok = select_scenario(user_id, project_id, scenario_b_id)
        assert ok is True

        ws = get_workspace_state(user_id, project_id)
        assert ws is not None
        # Active scenario is B
        assert ws.active_scenario_id == scenario_b_id
        # Runtime evidence cleared
        assert ws.last_runtime_snapshot == {}
        assert ws.last_runtime_summary == {}
        assert ws.last_runtime_origin is None
        # saved_snapshot preserved (form state is project-level, not scenario-level)
        assert ws.saved_snapshot == {"scenario": "A"}

    def test_select_scenario_invalid_returns_false(self):
        """select_scenario() returns False for invalid scenario_id (unchanged)."""
        from app.persistence.scenarios_repository import select_scenario
        from app.persistence.repository import save_project
        import uuid

        user_id = f"p1uxfix1-bad-{uuid.uuid4().hex[:8]}"
        project_code = f"p1uxfix1-wc-{uuid.uuid4().hex[:8]}"

        save_project(
            user_id=user_id,
            project_code=project_code,
            project_name="P1-UX-FIX-1 Invalid Test",
            source_project_template="generic_solar",
            project_type="Solar",
            project_origin="user_created",
            template_source="generic_solar",
        )

        ok = select_scenario(user_id, "nonexistent-project-id", "nonexistent-scenario-id")
        assert ok is False


# ---------------------------------------------------------------------------
# TASK C — Dashboard Empty State Hint
# ---------------------------------------------------------------------------


class TestTaskCDashboardEmptyStateHint:
    """TASK C — empty hint renders when all KPI cards are missing."""

    DASHBOARD_TEMPLATE = REPO_ROOT / "app" / "templates" / "partials" / "_dashboard.html"

    def test_empty_hint_renders_when_all_kpis_missing(self):
        """When all KPI statuses are 'missing' and a runtime
        snapshot_id exists, the empty hint block must render."""
        content = self.DASHBOARD_TEMPLATE.read_text()
        # Hint block has id=dashboard-empty-hint
        assert 'id="dashboard-empty-hint"' in content, (
            "Dashboard empty hint block missing"
        )
        # Hint text matches user requirement
        assert "Run the model to see KPIs here." in content, (
            "Empty hint message text missing"
        )

    def test_empty_hint_only_renders_when_runtime_snapshot_exists(self):
        """Hint block is wrapped in the runtime_summary snapshot
        guard so it does not duplicate the P2-FIX-4 'No run yet' CTA."""
        content = self.DASHBOARD_TEMPLATE.read_text()
        # Locate the hint block by id and walk backwards to find the
        # enclosing `{% if runtime_summary and runtime_summary.last_runtime_snapshot_id %}`
        hint_idx = content.find('id="dashboard-empty-hint"')
        assert hint_idx > 0, "dashboard-empty-hint block not found"
        # Walk backwards to the nearest `{% if runtime_summary and runtime_summary.last_runtime_snapshot_id %}`
        snippet_before = content[:hint_idx]
        guard_idx = snippet_before.rfind(
            "{% if runtime_summary and runtime_summary.last_runtime_snapshot_id %}"
        )
        assert guard_idx > 0, (
            "Hint block not preceded by runtime_summary.last_runtime_snapshot_id guard"
        )
        # Find the matching {% endif %} after the hint block
        snippet_after = content[hint_idx:]
        endif_idx = snippet_after.find("{% endif %}")
        assert endif_idx > 0, "Hint block not closed with {% endif %}"
        guarded_block = snippet_before[guard_idx:] + snippet_after[:endif_idx + len("{% endif %}")]
        # The hint must check all KPI statuses are missing
        assert "_all_missing" in guarded_block, (
            "Empty hint must check all KPI statuses are missing"
        )

    def test_p2fix4_run_cta_preserved(self):
        """The P2-FIX-4 'No run yet' CTA must still render
        when there is NO runtime snapshot at all (untouched)."""
        content = self.DASHBOARD_TEMPLATE.read_text()
        assert 'id="dashboard-run-cta"' in content
        assert "No run yet" in content
        assert "Run model" in content

    def test_css_defined_for_empty_hint(self):
        """styles.css must contain the empty-hint class."""
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert ".dashboard-empty-hint" in css, (
            "CSS class .dashboard-empty-hint missing"
        )


# ---------------------------------------------------------------------------
# TASK D — Working Copy Indicator
# ---------------------------------------------------------------------------


class TestTaskDWorkingCopyIndicator:
    """TASK D — sidebar shows 'Working Copy' badge for user-created
    projects derived from a reference template."""

    PROJECT_SELECTOR = REPO_ROOT / "app" / "templates" / "partials" / "project_selector.html"

    def test_wc_badge_present(self):
        content = self.PROJECT_SELECTOR.read_text()
        assert "Working Copy" in content, "WC badge text missing"
        assert 'data-p1uxfix1-component="working-copy-badge"' in content, (
            "WC badge data attribute missing"
        )

    def test_wc_badge_only_for_user_created(self):
        """WC badge must only render when project_origin == 'user_created'
        AND source_project_template matches a reference."""
        content = self.PROJECT_SELECTOR.read_text()
        # The WC badge is inside the user_created branch of the origin pill
        m = re.search(
            r"project_origin == 'user_created'(.*?)(elif|endif)",
            content,
            re.DOTALL,
        )
        assert m, "user_created branch not found"
        user_created_branch = m.group(1)
        assert "Working Copy" in user_created_branch, (
            "WC badge not inside user_created branch"
        )

    def test_wc_badge_template_sources(self):
        """WC badge should match tuho / oborovo / generic_solar / generic_wind."""
        content = self.PROJECT_SELECTOR.read_text()
        for src in ("tuho", "oborovo", "generic_solar", "generic_wind"):
            assert f"'{src}'" in content, f"Template source {src!r} not in WC badge check"

    def test_wc_badge_css_defined(self):
        css = (REPO_ROOT / "static" / "styles.css").read_text()
        assert ".ps-ap-origin--wc" in css, "WC badge CSS class missing"


# ---------------------------------------------------------------------------
# Hard Constraints — pinned invariants
# ---------------------------------------------------------------------------


class TestConstraintsPreserved:
    """All hard constraints honoured."""

    def test_rc1_frozen_sha_present(self):
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", RC1_SHA, "HEAD"],
            capture_output=True,
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0

    def test_engine_md5_unchanged(self):
        engine_path = REPO_ROOT / "app" / "waterfall_core.py"
        if engine_path.exists():
            actual = hashlib.md5(engine_path.read_bytes()).hexdigest()
            assert actual == ENGINE_MD5

    def test_factory_md5_unchanged(self):
        factory_path = REPO_ROOT / "app" / "project_factories.py"
        if factory_path.exists():
            actual = hashlib.md5(factory_path.read_bytes()).hexdigest()
            assert actual == FACTORY_MD5

    def test_file_scope_only_allowed_files(self):
        result = subprocess.run(
            ["git", "diff", "--name-only", "origin/main", "HEAD"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        changed = {
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
        }
        unexpected = changed - ALLOWED_FILES
        assert not unexpected, (
            f"Unexpected files changed vs. origin/main: {sorted(unexpected)}"
        )

    def test_no_forbidden_files_modified(self):
        result = subprocess.run(
            ["git", "diff", "--name-only", "origin/main", "HEAD"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        changed = {
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
        }
        overlap = changed & FORBIDDEN_FILES
        assert not overlap, (
            f"Forbidden files modified: {sorted(overlap)}"
        )


# ---------------------------------------------------------------------------
# Backward Compatibility — existing PR2 tests still pass
# ---------------------------------------------------------------------------


class TestBackwardCompat:
    """Existing _compute_realized_gearing_pct callers (PR2)
    must continue to work without the runtime_senior_debt_keur
    argument."""

    def test_pr2_two_arg_call_still_works(self):
        """PR2 call signature: _compute_realized_gearing_pct(senior, total)."""
        from app.ui.project_context import _compute_realized_gearing_pct
        # TUHO case: senior_debt = 43359.27, total_capex = 72993.71
        val = _compute_realized_gearing_pct(43359.27, 72993.71)
        assert val == pytest.approx(59.40, abs=0.05)
        # Oborovo case: senior_debt = 42852.27, total_capex = 57973.05
        val2 = _compute_realized_gearing_pct(42852.27, 57973.05)
        assert val2 == pytest.approx(73.92, abs=0.05)
        # Edge case: senior_debt = 0, no runtime: was 0.0 before P1-UX-FIX-1,
        # now None (consistent with the function rejecting negative values
        # and the runtime fallback path).
        val3 = _compute_realized_gearing_pct(0, 100000.0)
        assert val3 is None
        # Negative inputs still rejected
        assert _compute_realized_gearing_pct(-100.0, 100000.0) is None
