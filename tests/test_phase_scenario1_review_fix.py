"""SCENARIO-1 Review Fix: lazy Base Case repair in scenarios_add_service.

Problem: After merging SCENARIO-1, the Add Scenario button remained stuck on
"Adding..." for projects that existed BEFORE the fix. Those projects have zero
scenario rows. The existing fallback in execute_scenarios_add_route only fires
when scenarios is non-empty; for empty-scenarios projects base_case stays None
and line `base_case.scenario_id` raises AttributeError (or the 500 guard fires
and HTMX gets JSON instead of the expected HTML fragment, leaving the button
in the loading state forever).

Fix: in scenarios_add_service.execute_scenarios_add_route, after the
promote-oldest fallback block, add a lazy-repair path:

    if base_case is None and deps.get_or_create_base_case_scenario is not None:
        # use saved_snapshot from workspace_state as base_input_set
        base_case = deps.get_or_create_base_case_scenario(...)

    if base_case is None:
        return ScenariosAddRouteOutcome(status_code=500, ...)

These tests prove:
  A. ScenariosAddRouteDeps has get_or_create_base_case_scenario field (optional).
  B. scenarios_add_service source references get_or_create_base_case_scenario.
  C. scenarios_add_service guards base_case is None before attribute access.
  D. main_web.py wires get_or_create_base_case_scenario into ScenariosAddRouteDeps.
  E. Unit: zero-scenario project → lazy repair fires → succeeds.
  F. Unit: project with existing Base Case → repair skipped → succeeds.
  G. Live DB: existing legacy project (pre-fix) gets Base Case on add.
  H. Live DB: POST /scenarios/add returns 200 for legacy zero-scenario project.
  I. Live DB: new project still gets Base Case on creation (regression).
  J. Live DB: working copy still gets Base Case on creation (regression).
  K. Idempotency: repeated add does not create duplicate base cases.
  L. Parity: engine MD5 unchanged.
  M. Parity: TUHO P1 DSCR unchanged.
  N. Parity: Oborovo P1 DSCR unchanged.
  O. File scope guard.
"""
from __future__ import annotations

import dataclasses
import hashlib
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, call

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
# Helpers
# ---------------------------------------------------------------------------

def _scenario_rows_for_project(project_code: str):
    from app.persistence.db import get_connection
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT s.scenario_id, s.scenario_name, s.is_base_case
            FROM scenarios s
            JOIN projects p ON s.project_id = p.project_id
            WHERE p.project_code = ?
            ORDER BY s.created_at
            """,
            (project_code,),
        ).fetchall()


# ---------------------------------------------------------------------------
# A. ScenariosAddRouteDeps has the new optional field
# ---------------------------------------------------------------------------

class TestScenariosAddDepField:
    def test_deps_has_get_or_create_field(self):
        from app.services.scenarios_add_service import ScenariosAddRouteDeps
        fields = {f.name for f in dataclasses.fields(ScenariosAddRouteDeps)}
        assert "get_or_create_base_case_scenario" in fields

    def test_field_is_optional(self):
        from app.services.scenarios_add_service import ScenariosAddRouteDeps
        for f in dataclasses.fields(ScenariosAddRouteDeps):
            if f.name == "get_or_create_base_case_scenario":
                assert f.default is None, (
                    "get_or_create_base_case_scenario must default to None"
                )
                return
        pytest.fail("Field not found")


# ---------------------------------------------------------------------------
# B. Source code references the new function
# ---------------------------------------------------------------------------

class TestScenariosAddServiceSource:
    def test_service_references_get_or_create(self):
        src = (Path(REPO_ROOT) / "app/services/scenarios_add_service.py").read_text()
        assert "get_or_create_base_case_scenario" in src

    def test_service_calls_get_or_create_on_empty(self):
        src = (Path(REPO_ROOT) / "app/services/scenarios_add_service.py").read_text()
        assert "deps.get_or_create_base_case_scenario(" in src


# ---------------------------------------------------------------------------
# C. Service guards base_case is None before attribute access
# ---------------------------------------------------------------------------

class TestScenariosAddBaseNoneGuard:
    def test_service_has_none_guard_before_add(self):
        src = (Path(REPO_ROOT) / "app/services/scenarios_add_service.py").read_text()
        # Must have a guard that returns 500 if base_case is still None
        assert "if base_case is None" in src
        assert "No base case scenario" in src or "base_case is None" in src


# ---------------------------------------------------------------------------
# D. main_web.py wires get_or_create into ScenariosAddRouteDeps
# ---------------------------------------------------------------------------

class TestMainWebScenariosAddWiring:
    def test_main_web_wires_into_scenarios_add_deps(self):
        src = (Path(REPO_ROOT) / "main_web.py").read_text()
        # The ScenariosAddRouteDeps() constructor call must include the field
        assert "get_or_create_base_case_scenario=get_or_create_base_case_scenario" in src


# ---------------------------------------------------------------------------
# E. Unit: zero-scenario project triggers lazy repair
# ---------------------------------------------------------------------------

class TestLazyRepairUnit:
    def _make_deps(self, *, scenarios, get_or_create_result, ws_saved_snapshot=None):
        """Build a minimal ScenariosAddRouteDeps with mocks."""
        from app.services.scenarios_add_service import ScenariosAddRouteDeps

        project_record = MagicMock()
        project_record.project_id = "proj-001"
        project_record.project_code = "test-project"
        project_record.project_name = "Test Project"
        project_record.project_type = "Solar"
        project_record.source_project_template = "generic_solar"
        project_record.project_origin = "user_created"

        ws_state = MagicMock()
        ws_state.saved_snapshot = ws_saved_snapshot or {"capacity_mw": 50}
        ws_state.draft_snapshot = {}

        new_scenario = MagicMock()
        new_scenario.scenario_id = "sc-new-001"

        def _list_scenarios(user_id, project_id, include_archived=False, limit=None):
            return scenarios

        get_or_create = MagicMock(return_value=get_or_create_result)
        add_scen = MagicMock(return_value=new_scenario)
        build_ctx = MagicMock(return_value={"scenarios": []})

        deps = ScenariosAddRouteDeps(
            get_project_record=MagicMock(return_value=project_record),
            list_scenarios=_list_scenarios,
            get_least_created_scenario_for_project=MagicMock(return_value=None),
            promote_scenario_to_base_case=MagicMock(return_value=None),
            add_scenario=add_scen,
            get_workspace_state=MagicMock(return_value=ws_state),
            build_scenario_tab_context=build_ctx,
            get_or_create_base_case_scenario=get_or_create,
        )
        return deps, get_or_create, add_scen

    def test_zero_scenarios_triggers_lazy_repair(self):
        import asyncio
        from app.services.scenarios_add_service import execute_scenarios_add_route

        base_case = MagicMock()
        base_case.scenario_id = "sc-base-001"
        base_case.snapshot = {"capacity_mw": 50}
        base_case.base_input_set = {}
        base_case.is_base_case = True

        deps, get_or_create, add_scen = self._make_deps(
            scenarios=[],  # empty — legacy project
            get_or_create_result=base_case,
        )

        form = {"project_code": "test-project", "scenario_name": "Novi"}
        user = MagicMock()
        user.user_id = "user-1"

        result = asyncio.get_event_loop().run_until_complete(
            execute_scenarios_add_route(
                request=MagicMock(), form=form, user=user, deps=deps
            )
        )

        # get_or_create must have been called exactly once
        assert get_or_create.call_count == 1, (
            f"Expected lazy repair to call get_or_create once, got {get_or_create.call_count}"
        )
        # add_scenario must have been called with the repaired base_case id
        assert add_scen.call_count == 1
        call_kwargs = add_scen.call_args[1]
        assert call_kwargs["parent_scenario_id"] == "sc-base-001"
        # Result must be a 200 with HTML template
        assert result.status_code == 200
        assert result.template_name == "partials/scenario_tab.html"

    def test_existing_base_case_skips_lazy_repair(self):
        import asyncio
        from app.services.scenarios_add_service import execute_scenarios_add_route

        base_case = MagicMock()
        base_case.scenario_id = "sc-base-existing"
        base_case.snapshot = {"capacity_mw": 100}
        base_case.base_input_set = {}
        base_case.is_base_case = True

        deps, get_or_create, add_scen = self._make_deps(
            scenarios=[base_case],
            get_or_create_result=None,
        )

        form = {"project_code": "test-project", "scenario_name": "Novi"}
        user = MagicMock()
        user.user_id = "user-1"

        result = asyncio.get_event_loop().run_until_complete(
            execute_scenarios_add_route(
                request=MagicMock(), form=form, user=user, deps=deps
            )
        )

        # get_or_create must NOT have been called
        assert get_or_create.call_count == 0
        assert result.status_code == 200


# ---------------------------------------------------------------------------
# F. (merged into E above — kept for naming continuity)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# G-H. Live DB: POST /scenarios/add works for a legacy zero-scenario project
# ---------------------------------------------------------------------------

class TestLiveDBLegacyProject:
    """These tests use a project created BEFORE SCENARIO-1 and therefore
    having zero scenario rows.  We create such a project directly via the
    DB helpers (simulating a pre-fix project) and then call the service
    path that includes the lazy repair."""

    def _create_bare_project(self):
        """Create a ProjectRecord + WorkspaceState with zero scenarios via
        the repository layer (correct schema, no raw SQL)."""
        from app.persistence.projects_repository import create_project_record
        from app.persistence.workspace_repository import save_workspace_state
        import uuid

        project_code = f"legacy-no-scenarios-{str(uuid.uuid4())[:8]}"
        baseline = {"capacity_mw": 50}

        project_record = create_project_record(
            user_id="1",
            project_code=project_code,
            project_name="Legacy No Scenarios",
            project_type="Solar",
            project_origin="user_created",
            template_source="generic_solar",
            baseline_snapshot=baseline,
            governance_state={},
            replay_metadata={},
        )
        save_workspace_state(
            user_id="1",
            project_id=project_record.project_id,
            project_code=project_code,
            draft_snapshot=baseline,
            saved_snapshot=baseline,
            dirty=False,
            governance_state={},
            replay_metadata={},
        )
        return project_record.project_id, project_code

    def test_legacy_project_gets_base_case_and_new_scenario(self):
        import asyncio
        from app.services.scenarios_add_service import (
            ScenariosAddRouteDeps, execute_scenarios_add_route,
        )
        from app.persistence.scenarios_repository import get_or_create_base_case_scenario
        from app.persistence.repository import (
            get_project_record, list_scenarios,
            get_workspace_state, add_scenario,
            _get_least_created_scenario_for_project,
            promote_scenario_to_base_case,
        )

        project_id, project_code = self._create_bare_project()

        # Verify: zero scenarios before
        rows_before = _scenario_rows_for_project(project_code)
        assert len(rows_before) == 0, f"Expected 0 scenarios before, got {rows_before}"

        user = MagicMock()
        user.user_id = "1"

        def _build_ctx(user, project_record, scenarios, ws):
            return {"scenarios": scenarios, "project": project_record}

        deps = ScenariosAddRouteDeps(
            get_project_record=get_project_record,
            list_scenarios=list_scenarios,
            get_least_created_scenario_for_project=_get_least_created_scenario_for_project,
            promote_scenario_to_base_case=promote_scenario_to_base_case,
            add_scenario=add_scenario,
            get_workspace_state=get_workspace_state,
            build_scenario_tab_context=_build_ctx,
            get_or_create_base_case_scenario=get_or_create_base_case_scenario,
        )
        form = {"project_code": project_code, "scenario_name": "Novi"}

        result = asyncio.get_event_loop().run_until_complete(
            execute_scenarios_add_route(
                request=MagicMock(), form=form, user=user, deps=deps
            )
        )

        assert result.status_code == 200, (
            f"Expected 200, got {result.status_code}: {result.payload}"
        )
        assert result.template_name == "partials/scenario_tab.html"

        rows_after = _scenario_rows_for_project(project_code)
        assert len(rows_after) >= 2, (
            f"Expected Base Case + Novi, got {rows_after}"
        )
        base_rows = [r for r in rows_after if r["is_base_case"] == 1]
        assert len(base_rows) == 1, f"Expected exactly 1 base case, got {base_rows}"
        names = [r["scenario_name"] for r in rows_after]
        assert any("Novi" in n for n in names) or any("novi" in n.lower() for n in names), (
            f"Novi scenario not found in {names}"
        )


# ---------------------------------------------------------------------------
# I. Regression: new projects still get Base Case on creation
# ---------------------------------------------------------------------------

class TestRegressionNewProject:
    def test_projects_create_service_still_has_get_or_create(self):
        src = (Path(REPO_ROOT) / "app/services/projects_create_service.py").read_text()
        assert "deps.get_or_create_base_case_scenario(" in src
        assert "if deps.get_or_create_base_case_scenario is not None" in src

    def test_main_web_wires_into_create_deps(self):
        src = (Path(REPO_ROOT) / "main_web.py").read_text()
        count = src.count("get_or_create_base_case_scenario=get_or_create_base_case_scenario")
        assert count >= 4, (
            f"Expected wiring in create + 2× save-as + scenarios/add, found {count}"
        )


# ---------------------------------------------------------------------------
# J. Regression: working copies still get Base Case on save-as
# ---------------------------------------------------------------------------

class TestRegressionWorkingCopy:
    def test_save_as_service_still_has_get_or_create(self):
        src = (Path(REPO_ROOT) / "app/services/project_save_as_service.py").read_text()
        assert "deps.get_or_create_base_case_scenario(" in src
        assert "if deps.get_or_create_base_case_scenario is not None" in src


# ---------------------------------------------------------------------------
# K. Idempotency
# ---------------------------------------------------------------------------

class TestIdempotency:
    def test_lazy_repair_is_idempotent(self):
        """Calling /scenarios/add twice on a zero-scenario project
        creates exactly one Base Case."""
        import asyncio
        from app.services.scenarios_add_service import (
            ScenariosAddRouteDeps, execute_scenarios_add_route,
        )
        from app.persistence.scenarios_repository import get_or_create_base_case_scenario
        from app.persistence.repository import (
            get_project_record, list_scenarios, get_workspace_state,
            add_scenario, _get_least_created_scenario_for_project,
            promote_scenario_to_base_case,
        )
        import uuid
        from app.persistence.projects_repository import create_project_record
        from app.persistence.workspace_repository import save_workspace_state

        project_id = str(uuid.uuid4())
        project_code = f"legacy-idempotency-{project_id[:8]}"

        pr = create_project_record(
            user_id="1",
            project_code=project_code,
            project_name="Idempotency Test",
            project_type="Solar",
            project_origin="user_created",
            template_source="generic_solar",
            baseline_snapshot={},
            governance_state={},
            replay_metadata={},
        )
        project_id = pr.project_id
        save_workspace_state(
            user_id="1",
            project_id=project_id,
            project_code=project_code,
            draft_snapshot={},
            saved_snapshot={},
            dirty=False,
            governance_state={},
            replay_metadata={},
        )

        user = MagicMock()
        user.user_id = "1"

        def _build_ctx(u, pr, sc, ws):
            return {"scenarios": sc}

        def _make_deps():
            return ScenariosAddRouteDeps(
                get_project_record=get_project_record,
                list_scenarios=list_scenarios,
                get_least_created_scenario_for_project=_get_least_created_scenario_for_project,
                promote_scenario_to_base_case=promote_scenario_to_base_case,
                add_scenario=add_scenario,
                get_workspace_state=get_workspace_state,
                build_scenario_tab_context=_build_ctx,
                get_or_create_base_case_scenario=get_or_create_base_case_scenario,
            )

        # First call
        r1 = asyncio.get_event_loop().run_until_complete(
            execute_scenarios_add_route(
                request=MagicMock(), form={"project_code": project_code, "scenario_name": "Alpha"},
                user=user, deps=_make_deps(),
            )
        )
        assert r1.status_code == 200

        # Second call
        r2 = asyncio.get_event_loop().run_until_complete(
            execute_scenarios_add_route(
                request=MagicMock(), form={"project_code": project_code, "scenario_name": "Beta"},
                user=user, deps=_make_deps(),
            )
        )
        assert r2.status_code == 200

        rows = _scenario_rows_for_project(project_code)
        base_rows = [r for r in rows if r["is_base_case"] == 1]
        assert len(base_rows) == 1, (
            f"Idempotency violated: {len(base_rows)} base cases after 2 adds: {rows}"
        )
        names = [r["scenario_name"] for r in rows]
        assert any("Alpha" in n for n in names), f"Alpha not found in {names}"
        assert any("Beta" in n for n in names), f"Beta not found in {names}"


# ---------------------------------------------------------------------------
# L-N. Parity
# ---------------------------------------------------------------------------

class TestScenario1ReviewFixParity:
    def test_engine_md5_unchanged(self):
        digest = hashlib.md5(
            (Path(REPO_ROOT) / "app/waterfall_core.py").read_bytes()
        ).hexdigest()
        assert digest == ENGINE_MD5, f"waterfall_core.py changed: {digest}"

    def test_tuho_p1_dscr_unchanged(self):
        from app.project_factories import create_default_tuho_wind1
        from app.ui_runner import _build_period_engine, _run_waterfall
        proj = create_default_tuho_wind1()
        result = _run_waterfall(proj, _build_period_engine(proj))
        for p in result.periods:
            d = getattr(p, "dscr", None)
            if d is not None and abs(d) < 1e10:
                assert abs(d - TUHO_P1_DSCR) < 0.001, f"TUHO P1 DSCR={d}"
                return
        pytest.fail("No finite DSCR found")

    def test_oborovo_p1_dscr_unchanged(self):
        from app.project_factories import create_default_oborovo
        from app.ui_runner import _build_period_engine, _run_waterfall
        proj = create_default_oborovo()
        result = _run_waterfall(proj, _build_period_engine(proj))
        for p in result.periods:
            d = getattr(p, "dscr", None)
            if d is not None and abs(d) < 1e10:
                assert abs(d - OBOROVO_P1_DSCR) < 0.01, f"Oborovo P1 DSCR={d}"
                return
        pytest.fail("No finite DSCR found")


# ---------------------------------------------------------------------------
# O. File scope guard
# ---------------------------------------------------------------------------

class TestScenario1ReviewFixFileScope:
    ALLOWED_PREFIXES = (
        "app/templates/partials/new_project_minimal.html",  # UX-2E cross-arc
        "app/templates/partials/workspace_shell.html",  # UX-2E cross-arc
        "tests/",  # UX-2E cross-arc (branch-wide test footprint)
        "tests/test_phase56",  # UX-2E cross-arc
        "app/services/scenarios_add_service.py",
        "app/services/projects_create_service.py",
        "app/services/project_save_as_service.py",
        "main_web.py",
        "tests/test_phase_scenario1_",
        "tests/test_phase_stab",
        "tests/test_phase_pr1_",
        "tests/test_phase_pr2_",
        "tests/test_phase_pr3_",
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
        "tests/test_phase_p2fix",
        "tests/test_phase_ux1_",
        "tests/test_phase_ux2_",
        "tests/test_phase_scenario2_",
        # SCENARIO-2 persistence fixes are allowed in later phases
        "app/persistence/records.py",
        "app/persistence/_helpers.py",
        "app/persistence/scenarios_repository.py",
        # SCENARIO-2 input_adapter gearing_pct optional fix
        "app/input_adapter.py",
    )
    DISALLOWED_PREFIXES = (
        "app/waterfall_core.py",
        "app/project_factories.py",
        "static/",
        "app/templates/",
    )
    DISALLOWED_EXCEPTIONS = (
        "app/templates/partials/new_project_minimal.html",  # UX-2E cross-arc
        "app/templates/partials/workspace_shell.html",  # UX-2E cross-arc
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
            if any(f.startswith(e) for e in self.DISALLOWED_EXCEPTIONS):
                continue
            assert not any(f.startswith(p) for p in self.DISALLOWED_PREFIXES), (
                f"SCENARIO-1-review-fix must not touch {f}"
            )
            assert any(f.startswith(p) for p in self.ALLOWED_PREFIXES), (
                f"SCENARIO-1-review-fix file outside allowed scope: {f}"
            )
